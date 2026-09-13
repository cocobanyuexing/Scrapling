"""实测：拼图图纸智能导入 v8 - 用 visible 选择器精确点 MARD
样本: /workspace/测试图.jpg
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='zh-CN')
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
        const bs = [...document.querySelectorAll('button')].filter(b => b.innerText && (b.innerText.trim() === '登录' || b.innerText.trim() === '登入'));
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

    print("\n=== 1. 进 create + 触发 smartImport ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.locator('input[type="file"][accept*="image"]').nth(2).set_input_files(IMG)
    page.wait_for_timeout(3000)

    # 关掉可能存在的 选择转换模式 dialog
    print("\n=== 2. 关干扰 dialog ===")
    cancel = page.locator('button:has-text("取消")').first
    if cancel.count() > 0:
        cancel.click(timeout=2000)
        print("  ✓ 关了取消")
        page.wait_for_timeout(1000)

    print("\n=== 3. dump MARD 附近完整 HTML ===")
    html = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        // 找含 "MARD 视觉识别" 的最小元素
        const targets = all.filter(e => {
            const t = (e.innerText||'').trim();
            return t === 'MARD 视觉识别';
        });
        if (targets.length === 0) return 'NOT FOUND';
        // 取第一个的 outerHTML 和向上 3 层
        const t = targets[0];
        let result = 'TARGET: ' + t.tagName + ' class=' + (t.className||'').slice(0,100) + '\\n';
        let p = t;
        for (let i = 0; i < 6; i++) {
            if (!p.parentElement) break;
            p = p.parentElement;
            result += `PARENT[${i}]: <${p.tagName} class="${(p.className||'').slice(0,100)}" role="${p.getAttribute('role')||''}" slot="${p.getAttribute('data-slot')||''}" tabindex="${p.tabIndex}">\\n`;
            // 检查是否有 onClick
            if (p.onclick || p.getAttribute('role') === 'option' || p.getAttribute('role') === 'button' || /cursor-pointer|clickable/.test(p.className||'')) {
                result += '  >>> CLICKABLE <<<\\n';
            }
        }
        // 也返回所有 MARD 元素的信息
        result += '\\nALL MARD ELEMENTS:\\n';
        for (const e of targets) {
            const r = e.getBoundingClientRect();
            result += `${e.tagName} cls=${(e.className||'').slice(0,60)} visible=${r.width>0} rect=${JSON.stringify({w:r.width,h:r.height,x:r.x,y:r.y})}\\n`;
        }
        return result;
    }''')
    print(html)

    print("\n=== 4. 用 Playwright force click 点 MARD 的可点击父级 ===")
    # 找 cursor-pointer 的父级
    clicked = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        const targets = all.filter(e => (e.innerText||'').trim() === 'MARD 视觉识别');
        if (targets.length === 0) return 'NOT FOUND';
        // 找 visible 的
        const visible = targets.filter(e => {
            const r = e.getBoundingClientRect();
            return r.width > 50 && r.height > 20;
        });
        if (visible.length === 0) return 'NONE VISIBLE';
        const t = visible[0];
        // 向上找 clickable
        let p = t;
        for (let i = 0; i < 8; i++) {
            if (!p.parentElement) break;
            p = p.parentElement;
            const cls = p.className || '';
            const role = p.getAttribute('role') || '';
            if (/cursor-pointer|clickable|card|option|radio/i.test(cls + role) || role === 'button') {
                p.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                return 'CLICKED: ' + p.tagName + ' cls=' + cls.slice(0,60) + ' role=' + role;
            }
        }
        // fallback: 直接点 target
        t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        return 'CLICKED TARGET: ' + t.tagName;
    }''')
    print(f"  {clicked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si8_after_mard.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
    print(f"  body:\n{body[:400]}")

    print("\n=== 5. 如果进了上传步骤, 上传 ===")
    file_info = page.evaluate('''() => {
        const inps = [...document.querySelectorAll('input[type="file"]')];
        return inps.map((i, idx) => ({idx, accept: i.accept||'', visible: i.offsetParent !== null}));
    }''')
    print(f"  file inputs: {file_info}")
    # 找 visible 的 image input
    vis_inp = page.locator('input[type="file"][accept*="image"]:visible').first
    if vis_inp.count() > 0:
        vis_inp.set_input_files(IMG)
        print("  ✓ 上传到 visible input")
    else:
        # 最后一个 image input
        page.locator('input[type="file"][accept*="image"]').last.set_input_files(IMG)
        print("  ✓ 上传到最后 image input")

    print("\n=== 6. 等识别 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            break
        if any(k in body for k in ['识别失败','色号','网格','创建','完成','成功','裁剪','分割']) and '选择导入' not in body:
            print(f"  [{i*2}s] 识别结果?")
            page.wait_for_timeout(3000)
            break
    page.screenshot(path='/workspace/si8_recognized.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,700)''')
    print(f"  URL: {page.url}")
    print(f"  body:\n{body[:500]}")

    print("\n=== 7. XHR ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:600]}")

    ctx.close(); browser.close()
print("\nDONE")
