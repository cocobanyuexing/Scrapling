"""实测 3 v11: 复现 v15 登录成功, 抓 access_token + XSRF-TOKEN, 然后真调 inventory API
关键: v15 是怎么登录的? 看真实 XHR, 然后用相同 flow
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

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
    def on_request(req):
        if req.resource_type in ('xhr', 'fetch'):
            url = req.url
            if 'auth' in url.lower() or 'login' in url.lower() or 'token' in url.lower():
                try:
                    body = req.post_data or ''
                except: body = ''
                xhr_log.append({'phase': 'req', 'm': req.method, 'url': url, 'body': body[:500]})
    page.on('request', on_request)

    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            url = resp.url
            if 'auth' in url.lower() or 'login' in url.lower() or 'token' in url.lower():
                try:
                    body = ''
                    ct = resp.headers.get('content-type','')
                    if 'json' in ct: body = resp.text()[:1500]
                except: body='<err>'
                xhr_log.append({'phase': 'resp', 'm': resp.request.method, 'url': url, 'st': resp.status, 'body': body})
    page.on('response', on_response)

    print("=== 0. 登录 (v15 完整流程) ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    # v15: 3 次 ESC
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
    page.wait_for_timeout(6000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    print("\n=== 1. 验证登录状态 ===")
    ls = page.evaluate('''() => localStorage.getItem('auth-storage')''')
    print(f"  auth-storage: {ls[:300] if ls else 'null'}")
    cookies = ctx.cookies()
    auth_cookies = [c for c in cookies if any(k in c['name'].lower() for k in ['token', 'session', 'xsrf', 'csrf', 'auth'])]
    print(f"  auth cookies: {len(auth_cookies)}")
    for c in auth_cookies:
        print(f"    {c['name']}: httpOnly={c.get('httpOnly')} value={c['value'][:80]}")

    print(f"\n=== 2. 登录 XHR 全部 (req + resp) ===")
    print(f"  XHR 总数: {len(xhr_log)}")
    for x in xhr_log:
        if x['phase'] == 'req':
            print(f"\n  [REQ] {x['m']} {x['url'][:120]}")
            if x.get('body'):
                print(f"    body: {x['body']}")
        else:
            print(f"  [RESP] {x['st']} {x['url'][:120]}")
            if x.get('body'):
                print(f"    body: {x['body'][:600]}")

    # 跟 v15 一样, 走 create 看是否进了带登录态的页面
    print("\n=== 3. 进 /workspace/create 看登录态 UI ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    body = body_head(page, 800)
    print(f"  body 前 600: {body[:600]}")
    # 看 localStorage 是不是有 user
    ls_after = page.evaluate('''() => localStorage.getItem('auth-storage')''')
    print(f"  create 后 auth-storage: {ls_after[:300] if ls_after else 'null'}")

    ctx.close(); browser.close()
print("\nDONE")
