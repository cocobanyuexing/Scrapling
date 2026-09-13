"""实测 3 v10: 通过 Zustand store 拿 token + 通过 axios 实例调用 inventory API
关键洞察: axios 拦截器从 Zustand store 拿 access_token, 不是 cookie
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
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:2000]
            except: body='<err>'
            req_body = ''
            try:
                if resp.request.method in ('POST','PUT','PATCH'):
                    req_body = (resp.request.post_data or '')[:1500]
            except: pass
            # 抓所有请求 header
            req_headers = {}
            try:
                for h in resp.request.headers:
                    if h.lower() in ['authorization', 'x-xsrf-token', 'cookie', 'x-access-token']:
                        req_headers[h] = resp.request.headers[h][:100]
            except: pass
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body, 'req_body': req_body, 'req_headers': req_headers})
    page.on('response', on_response)

    print("=== 0. 登录 (v15 流程) ===")
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
    page.wait_for_timeout(2500)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=8000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(800)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(6000)

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    print("\n=== 2. 从 Zustand store 拿 token ===")
    token_info = page.evaluate('''() => {
        const result = {};
        // 试 localStorage
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (k && (k.includes('token') || k.includes('auth') || k.includes('user') || k.includes('session'))) {
                result['ls_' + k] = localStorage.getItem(k).slice(0, 200);
            }
        }
        // 试找 Zustand store 全局
        for (const k of Object.keys(window)) {
            if (k.includes('store') || k.includes('Store') || k.includes('zustand')) {
                result['global_' + k] = typeof window[k];
            }
        }
        // 试 cookie
        result.cookie = document.cookie.slice(0, 500);
        return result;
    }''')
    print(f"  token_info: {json.dumps(token_info, ensure_ascii=False, indent=2)[:800]}")

    print("\n=== 3. 看登录后 XHR 抓 access_token ===")
    print(f"  总 XHR: {len(xhr_log)}")
    for x in xhr_log:
        u = x['url']
        if 'auth' in u.lower() or 'login' in u.lower() or 'token' in u.lower() or 'refresh' in u.lower():
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:500]}")
            if x.get('req_headers'):
                print(f"    headers: {x['req_headers']}")

    print("\n=== 4. 用 axios 实例调 inventory summary ===")
    # 通过 page.evaluate 找全局 axios 实例 + 调用
    inv_resp = page.evaluate('''async () => {
        // 看是不是有全局 axios 实例, 或者通过 import 拿到
        // 试通过 page fetch + 显式从 cookie 拿 XSRF
        const cookies = document.cookie.split(';').reduce((acc, c) => {
            const [k, v] = c.trim().split('=');
            acc[k] = v;
            return acc;
        }, {});
        const xsrf = decodeURIComponent(cookies['XSRF-TOKEN'] || '');
        // 加 authorization: Bearer + access_token cookie
        const accessToken = cookies['access_token'] || '';
        const r = await fetch('/v1/app/inventory/summary', {
            credentials: 'include',
            headers: {
                'X-XSRF-TOKEN': xsrf,
                'Authorization': accessToken ? `Bearer ${accessToken}` : '',
                'Accept': 'application/json'
            }
        });
        return {st: r.status, body: (await r.text()).slice(0, 1500)};
    }''')
    print(f"  status: {inv_resp['st']}")
    print(f"  body: {inv_resp['body'][:600]}")

    print("\n=== 5. dump 所有 cookie ===")
    cookies = ctx.cookies()
    for c in cookies:
        print(f"  {c['name']}: httpOnly={c.get('httpOnly')} value={c['value'][:80]}")

    ctx.close(); browser.close()
print("\nDONE")
