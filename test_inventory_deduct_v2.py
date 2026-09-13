"""实测 3: 库存扣减 API - 真调用 POST 接口
反编译 chunk 9350 找扣减 API URL -> 浏览器内登录后真发 POST -> 验证数量变化
"""
from patchright.sync_api import sync_playwright
import json, os, time, re

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

def body_head(page, n=800):
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
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body, 'req_body': ''})
            try:
                if resp.request.method == 'POST':
                    xhr_log[-1]['req_body'] = resp.request.post_data[:1500] if resp.request.post_data else ''
            except: pass
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
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    # 抓 cookie 和 token
    cookies = ctx.cookies()
    cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
    xsrf_cookie = next((c['value'] for c in cookies if c['name'] == 'XSRF-TOKEN'), '')
    access_token = next((c['value'] for c in cookies if c['name'] == 'access_token'), '')
    print(f"  access_token: {access_token[:50]}...")
    print(f"  XSRF-TOKEN: {xsrf_cookie[:30]}...")

    print("\n=== 1. GET 库存列表 baseline ===")
    # 真发 GET 拿库存列表
    inventory = page.evaluate('''async (xsrf) => {
        const r = await fetch('/v1/app/inventory/summary', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'X-XSRF-TOKEN': decodeURIComponent(xsrf),
                'Accept': 'application/json'
            }
        });
        return {st: r.status, body: await r.text()};
    }''', xsrf_cookie)
    print(f"  GET status: {inventory['st']}")
    print(f"  body 前 800: {inventory['body'][:800]}")

    # 解析库存结构
    try:
        inv_json = json.loads(inventory['body'])
        print(f"  data keys: {list(inv_json.get('data', {}).keys())[:10]}")
        # 找第一个色号
        data = inv_json.get('data', {})
        if 'items' in data:
            first_item = data['items'][0] if data['items'] else {}
            print(f"  第一个 item: {json.dumps(first_item, ensure_ascii=False)[:300]}")
        elif 'inventory' in data:
            first_item = data['inventory'][0] if data['inventory'] else {}
            print(f"  第一个 inventory: {json.dumps(first_item, ensure_ascii=False)[:300]}")
    except Exception as e:
        print(f"  解析 err: {e}")

    print("\n=== 2. 反编译 chunk 找扣减 API URL ===")
    # 读 chunk 9350 找扣减相关 URL
    import re
    with open('/workspace/i2tools/i2tools.com/_next/static/chunks/9350-9895fcf460f5295c.js', encoding='utf-8') as f:
        c9350 = f.read()
    # 找扣减关键字
    for kw in ['deduct', 'consume', 'use', 'subtract', 'inventory/', 'stock', 'bead-count', 'decrement']:
        ms = list(re.finditer(re.escape(kw), c9350, re.IGNORECASE))
        if ms:
            print(f"  [{kw}] 命中 {len(ms)} 处:")
            for m in ms[:1]:
                s = max(0, m.start() - 150)
                e = min(len(c9350), m.end() + 400)
                print(f"    {c9350[s:e]}")
            print()

    print("\n=== 3. 找所有 /v1/app/inventory/* API ===")
    inv_apis = set(re.findall(r'/v1/app/inventory[\w/\-]*', c9350))
    print(f"  库存 API: {inv_apis}")

    print("\n=== 4. 尝试 POST 扣减 ===")
    # 看反编译结果决定怎么调
    # 先抓项目当前 layer 的色号+颗数, 模拟库存扣减的请求
    # 看是否有色号提交 API
    deduct_apis = []
    for api in inv_apis:
        if any(k in api.lower() for k in ['deduct', 'consume', 'use', 'subtract', 'decrement']):
            deduct_apis.append(api)
    print(f"  扣减 API: {deduct_apis}")

    # 找其它路径
    other_paths = set(re.findall(r'["\'`](/v1/app/[\w/\-{}:]+)["\'`]', c9350))
    print(f"  其它 API 路径: {len(other_paths)}")
    for u in sorted(other_paths)[:30]:
        print(f"    {u}")

    ctx.close(); browser.close()
print("\nDONE")
