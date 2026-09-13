"""实测：拼图图纸智能导入 v2 - 打开下拉菜单选 smartImport
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
                if 'json' in ct: body = resp.text()[:1200]
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
        page.locator('[data-slot="dialog-content"] [role="checkbox"], [data-slot="dialog-content"] input[type="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    print(f"  登录后: {page.url}")

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    # 找"新建"按钮打开下拉
    print("\n=== 2. 打开新建下拉菜单 ===")
    # create page 顶部有"新建"按钮，或者直接找触发下拉的按钮
    opened = page.evaluate('''() => {
        // 找含"新建"或"创建"的按钮
        const btns = [...document.querySelectorAll('button')];
        const t = btns.find(b => /新建|创建|开始|Create/.test(b.innerText||'') && (b.innerText||'').length < 20);
        if (t) { t.click(); return t.innerText.trim(); }
        return null;
    }''')
    print(f"  点开下拉: {opened}")
    page.wait_for_timeout(1500)
    page.screenshot(path='/workspace/si_dropdown.png')

    # 读下拉项
    items = page.evaluate('''() => {
        // radix dropdown 用 role="menuitem" 或 data-slot
        const items = [...document.querySelectorAll('[role="menuitem"], [data-slot="dropdown-menu-item"], [data-slot*="menu-item"]')];
        return items.map(i => ({
            text: (i.innerText||'').trim(),
            aria: i.getAttribute('aria-label')||''
        })).filter(x => x.text || x.aria);
    }''')
    print(f"  下拉项: {items}")

    # 选 smartImport - 第2项(image 之后), 或文案含"智能/图纸/识别"
    picked = page.evaluate('''() => {
        const items = [...document.querySelectorAll('[role="menuitem"], [data-slot="dropdown-menu-item"], [data-slot*="menu-item"]')];
        // smartImport 是第2项 (image, smartImport, xhsLink, ...)
        // 或文案匹配
        const target = items.find(i => /智能|图纸|识别|拼图|smart/i.test(i.innerText||'')) || (items.length >= 2 ? items[1] : null);
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  选中 smartImport: {picked}")
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/si_modal.png')

    # SmartImportModal 应该弹出了。找 modal 里的 file input (第3个 image input = z)
    print("\n=== 3. 找 modal 里 file input 并上传 ===")
    # 现在页面有3个 image input, 最后一个是 smartImport 的 z
    inps = page.locator('input[type="file"][accept*="image"]')
    print(f"  image input 总数: {inps.count()}")
    if inps.count() >= 3:
        inps.nth(2).set_input_files(IMG)  # z = 第3个
        print(f"  ✓ 上传到第3个 input(z): {os.path.basename(IMG)}")
    elif inps.count() >= 1:
        inps.last.set_input_files(IMG)
        print(f"  ✓ 上传到最后一个 input: {os.path.basename(IMG)}")
    
    # 等识别(最多 90s)
    for _ in range(45):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
        if '/editor' in url or '识别' in body and ('失败' in body or '成功' in body) or '色号' in body:
            break
    page.screenshot(path='/workspace/si_after_upload.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,600)''')
    print(f"  URL: {page.url}")
    print(f"  body 前600:\n{body}")

    print("\n=== 4. XHR 摘要(找识别 API) ===")
    for x in xhr_log:
        u = x['url']
        if any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','conversion']) or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:130]}")
            if x.get('body') and x['st'] < 300:
                print(f"    body: {x['body'][:400]}")

    ctx.close(); browser.close()
print("\nDONE")
