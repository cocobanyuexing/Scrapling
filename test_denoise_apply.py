"""实测 2: 真正点'确认'执行去噪算法
样本: /workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp
流程: 登录 -> 进编辑器导入.pbp -> 点去除杂色/降噪 -> 点'确认'按钮真正执行 -> 看 XHR -> 看前后对比
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'

def body_head(page, n=1000):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:3000]
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
    print(f"  登录后 URL: {page.url}")

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    print("\n=== 2. 上传 .pbp 触发导入 ===")
    inp = page.locator('input[type="file"][accept=".pbp"]').first
    if inp.count() == 0:
        # 兜底用 image
        inp = page.locator('input[type="file"][accept*="image"]').first
    print(f"  input count: {inp.count()}")
    inp.set_input_files(PBP)
    page.wait_for_timeout(8000)
    print(f"  URL: {page.url}")

    # 等进编辑器
    for i in range(10):
        if '/editor' in page.url:
            print(f"  ✓ 已进编辑器")
            break
        page.wait_for_timeout(2000)
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/dn_editor_loaded.png')

    print("\n=== 3. 找后处理按钮(色号合并/去除杂色/降噪) ===")
    btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            visible: b.offsetParent !== null
        })).filter(x => x.visible && (x.text || x.aria));
    }''')
    postproc = [b for b in btns if any(k in (b['text']+b['aria']+b['title']) for k in ['色号合并','去除杂色','降噪','合并','杂色','降噪','denoise','merge','noise','stray','cleanup'])]
    print(f"  后处理按钮数: {len(postproc)}")
    for b in postproc[:5]:
        print(f"    - {b}")

    print("\n=== 4. 点'降噪'按钮打开弹窗 ===")
    # 找'降噪' 按钮
    clicked = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '降噪' || (t.includes('降噪') && t.length < 20);
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点击: {clicked}")
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/dn_denoise_modal.png')

    print("\n=== 5. dump 弹窗内容 ===")
    modal_info = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        const target = all.find(e => {
            const t = (e.innerText||'');
            return t.includes('降噪') && t.includes('候选像素') && e.children.length < 30;
        });
        if (!target) return {found: false};
        // 找所有按钮
        const btns = [...target.querySelectorAll('button')].map(b => ({
            text: (b.innerText||'').trim().slice(0,20),
            classes: (b.className||'').slice(0,80),
        }));
        return {
            found: true,
            text: target.innerText.slice(0, 1500),
            btns
        };
    }''')
    print(f"  弹窗找到: {modal_info.get('found')}")
    if modal_info.get('found'):
        print(f"\n  弹窗文字:\n{modal_info['text']}")
        print(f"\n  按钮:")
        for b in modal_info['btns']:
            print(f"    - {b['text']!r} classes={b['classes'][:60]}")

    print("\n=== 6. 真正点'确认'按钮执行算法 ===")
    # 点 确认/确定/应用 按钮
    confirmed = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')];
        // 优先确认按钮
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '确认' || t === '确定' || t === '应用' || t === '应用降噪' || t === '确认降噪';
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点确认: {confirmed}")
    page.wait_for_timeout(5000)
    page.screenshot(path='/workspace/dn_after_apply.png')
    body = body_head(page, 600)
    print(f"  body:\n{body}")

    print("\n=== 7. 等待处理完成 ===")
    for i in range(15):
        page.wait_for_timeout(2000)
        body = body_head(page, 300)
        url = page.url
        print(f"  [{i*2}s] url={url[:60]} body头100: {body[:100]}")
        # 看是否还有处理中
        if '处理中' not in body and '正在' not in body:
            page.wait_for_timeout(2000)
            break
    page.screenshot(path='/workspace/dn_final.png')

    print("\n=== 8. XHR 日志(后处理相关) ===")
    for x in xhr_log:
        u = x['url']
        if any(k in u.lower() for k in ['denoise','noise','stray','cleanup','merge','process','post-proc','postproc','apply','worker']) or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body'):
                print(f"    body: {x['body'][:400]}")

    print("\n=== 9. 关闭弹窗, 再看色号合并 ===")
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    # 点色号合并
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '色号合并' || (t.includes('色号合并') && t.length < 20);
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/dn_merge_modal.png')
    body = body_head(page, 800)
    print(f"  色号合并弹窗:\n{body}")

    ctx.close(); browser.close()
print("\nDONE")
