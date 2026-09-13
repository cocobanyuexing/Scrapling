"""探索新工作台入口路径，定位 3D 预览面板。"""
from patchright.sync_api import sync_playwright
import json

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

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
            xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status})
    page.on('response', on_response)

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
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
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(4000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)

    # 看首页所有链接和按钮
    print("\n=== 1. 首页所有链接 ===")
    links = page.evaluate('''() => {
        const as = [...document.querySelectorAll('a[href]')].map(a => ({text: (a.innerText||'').trim().slice(0,30), href: a.href})).filter(x => x.href && !x.href.startsWith('javascript'));
        return as;
    }''')
    for l in links:
        print(f"  {l['text'][:25]:25} -> {l['href']}")

    print("\n=== 2. 点「立刻前往」找新工作台 ===")
    # 立刻前往按钮
    clicked = False
    for txt in ['立刻前往', '前往工作台', '工作台']:
        loc = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(4000)
                print(f"  ✓ 点了「{txt}」 -> {page.url}")
                clicked = True
                break
            except Exception as e:
                print(f"  {txt}: {e}")
    
    page.screenshot(path='/workspace/ws_landed.png')
    print(f"\n  当前 URL: {page.url}")
    print(f"  title: {page.title()}")

    # 看新工作台页面内容
    info = page.evaluate('''() => ({
        body: document.body.innerText.slice(0, 1500),
        buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 25).slice(0, 30),
        links: [...document.querySelectorAll('a[href]')].map(a => ({text: (a.innerText||'').trim().slice(0,20), href: a.href})).filter(x => x.href && !x.href.startsWith('javascript')).slice(0, 20),
        localStorage_keys: Object.keys(localStorage),
        projects_in_storage: (() => {
            try {
                const auth = JSON.parse(localStorage.getItem('auth-storage')||'{}');
                return {hasAuth: !!auth.state?.accessToken};
            } catch(e) { return {err: String(e)} }
        })()
    })''')
    print(f"\n  body 前 1500:\n{info['body']}")
    print(f"\n  按钮 ({len(info['buttons'])}): {info['buttons']}")
    print(f"\n  链接: ")
    for l in info['links']:
        print(f"    {l['text']:20} -> {l['href']}")
    print(f"\n  localStorage keys: {info['localStorage_keys']}")
    print(f"  auth: {info['projects_in_storage']}")

    browser.close()
