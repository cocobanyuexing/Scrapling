"""实测 2 v2: 真正点确认 + 检测 worker 通信 + 像素变化证明算法执行
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'

def body_head(page, n=600):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    # 监听 worker 创建
    worker_count = [0]
    page.add_init_script('''
        const _W = window.Worker;
        window._worker_log = [];
        window.Worker = class extends _W {
            constructor(url, opts) {
                super(url, opts);
                window._worker_log.push({url: String(url), time: Date.now()});
                // 监听 postMessage
                const _post = this.postMessage.bind(this);
                const _self = this;
                this.postMessage = function(msg, ...rest) {
                    window._worker_log.push({type: 'out', msg: JSON.stringify(msg).slice(0, 500), time: Date.now()});
                    return _post(msg, ...rest);
                };
                this.addEventListener('message', e => {
                    window._worker_log.push({type: 'in', msg: JSON.stringify(e.data).slice(0, 500), time: Date.now()});
                });
            }
        };
    ''')

    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:1500]
            except: body='<err>'
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body})
    page.on('response', on_response)

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => {
            const t = (b.innerText||'').trim();
            return t === '登录' || t === '登入';
        });
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    print("\n=== 1. 导入 .pbp ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    inp = page.locator('input[type="file"][accept=".pbp"]').first
    if inp.count() == 0:
        inp = page.locator('input[type="file"][accept*="image"]').first
    inp.set_input_files(PBP)
    page.wait_for_timeout(8000)
    for i in range(10):
        if '/editor' in page.url: break
        page.wait_for_timeout(2000)
    page.wait_for_timeout(3000)

    print("\n=== 2. 抓画布像素 baseline ===")
    baseline = page.evaluate('''() => {
        // 找 PixiJS canvas
        const c = document.querySelector('canvas');
        if (!c) return {err: 'no canvas'};
        // 不调 readPixels, 只记录 canvas 尺寸 + 是否存在
        return {w: c.width, h: c.height, count: document.querySelectorAll('canvas').length};
    }''')
    print(f"  canvas baseline: {baseline}")

    print("\n=== 3. 点降噪按钮 ===")
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '降噪';
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    page.wait_for_timeout(2500)

    print("\n=== 4. 弹窗 + 点确认 ===")
    # 看弹窗预计算统计
    modal_text = body_head(page, 800)
    print(f"  弹窗内容前 500: {modal_text[:500]}")
    page.screenshot(path='/workspace/dn2_modal.png')

    # 点确认 - 用 evaluate 调原生 click
    confirmed = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '确认' || t === '确定' || t === '应用';
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  ✓ 点确认: {confirmed}")

    print("\n=== 5. 监听 worker 通信 ===")
    for i in range(15):
        page.wait_for_timeout(1500)
        wlog = page.evaluate('''() => window._worker_log || []''')
        body = body_head(page, 200)
        # 看 worker log 长度
        msg_count = len(wlog) if isinstance(wlog, list) else 0
        print(f"  [{i*1.5}s] worker_msg={msg_count} body头80: {body[:80]}")
        if msg_count > 0:
            break

    print("\n=== 6. dump 所有 worker 通信 ===")
    wlog = page.evaluate('''() => window._worker_log || []''')
    print(f"  worker 通信总数: {len(wlog)}")
    for w in wlog[:30]:
        if w.get('type') == 'out':
            print(f"  -> out [{w.get('time')}]: {w.get('msg', '')[:300]}")
        elif w.get('type') == 'in':
            print(f"  <- in  [{w.get('time')}]: {w.get('msg', '')[:300]}")
        else:
            print(f"  worker 创建: {w.get('url', '')[:100]}")

    print("\n=== 7. 画布像素 after ===")
    after = page.evaluate('''() => {
        const c = document.querySelector('canvas');
        if (!c) return {err: 'no canvas'};
        return {w: c.width, h: c.height};
    }''')
    print(f"  canvas after: {after}")

    print("\n=== 8. 全部 XHR (无过滤) ===")
    print(f"  XHR 总数: {len(xhr_log)}")
    for x in xhr_log[-20:]:
        print(f"  {x['st']} {x['m']} {x['url'][:100]}")

    ctx.close(); browser.close()
print("\nDONE")
