"""实测 3 v12: 真发 POST /v1/app/auth/email/login + 拿 token + 真调 inventory API + 真扣减
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    # 监听 XHR
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
                    req_body = (resp.request.post_data or '')[:1000]
            except: pass
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body, 'req_body': req_body})
    page.on('response', on_response)

    print("=== 0. 直接 POST /v1/app/auth/email/login ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)

    # 真发登录请求
    login_payload = {"email": EMAIL, "password": PWD}
    login_resp = page.evaluate('''async (payload) => {
        const r = await fetch('/v1/app/auth/email/login', {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        return {st: r.status, body: await r.text()};
    }''', login_payload)
    print(f"  POST status: {login_resp['st']}")
    print(f"  body: {login_resp['body'][:1000]}")

    # 解析返回的 token
    try:
        login_data = json.loads(login_resp['body'])
        data = login_data.get('data', {})
        access_token = data.get('accessToken') or data.get('access_token')
        refresh_token = data.get('refreshToken') or data.get('refresh_token')
        user = data.get('user')
        print(f"\n  accessToken: {access_token[:80] if access_token else 'null'}...")
        print(f"  refreshToken: {refresh_token[:40] if refresh_token else 'null'}...")
        print(f"  user: {json.dumps(user, ensure_ascii=False)[:300] if user else 'null'}")
    except Exception as e:
        print(f"  解析失败: {e}")

    # dump cookies
    cookies = ctx.cookies()
    print(f"\n  所有 cookie ({len(cookies)} 个):")
    for c in cookies:
        if any(k in c['name'].lower() for k in ['token', 'session', 'xsrf', 'csrf', 'auth']):
            print(f"    {c['name']} httpOnly={c.get('httpOnly')} value={c['value'][:80]}")

    # 真调 inventory summary
    print(f"\n=== 1. GET /v1/app/inventory/summary (带 Authorization) ===")
    if access_token:
        inv_resp = page.evaluate('''async (token) => {
            const r = await fetch('/v1/app/inventory/summary', {
                credentials: 'include',
                headers: {'Authorization': 'Bearer ' + token}
            });
            return {st: r.status, body: await r.text()};
        }''', access_token)
        print(f"  status: {inv_resp['st']}")
        print(f"  body: {inv_resp['body'][:1500]}")

        # 解析色号
        try:
            inv_data = json.loads(inv_resp['body'])
            colors = inv_data.get('data', {}).get('colors') or inv_data.get('data', {}).get('items') or []
            print(f"\n  色号总数: {len(colors)}")
            if colors:
                first = colors[0]
                print(f"  第一个色号: {json.dumps(first, ensure_ascii=False)[:300]}")
        except: pass

        # 真扣减
        if colors:
            print(f"\n=== 2. POST /v1/app/inventory/operations 真扣减 ===")
            first_color = colors[0]
            payload = {
                "actionType": "manual_adjust",
                "sourceType": "user",
                "remark": "trae_test",
                "items": [{
                    "brandCode": first_color.get('brandCode') or 'MARD',
                    "colorCode": first_color.get('colorCode'),
                    "changeQty": -1
                }]
            }
            print(f"  payload: {json.dumps(payload, ensure_ascii=False)}")
            deduct_resp = page.evaluate('''async (args) => {
                const r = await fetch('/v1/app/inventory/operations', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Authorization': 'Bearer ' + args.token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(args.payload)
                });
                return {st: r.status, body: await r.text()};
            }''', {'token': access_token, 'payload': payload})
            print(f"  POST status: {deduct_resp['st']}")
            print(f"  body: {deduct_resp['body'][:600]}")

            # 看扣减前后数量变化
            print(f"\n=== 3. 验证数量变化 ===")
            after_resp = page.evaluate('''async (token) => {
                const r = await fetch('/v1/app/inventory/summary', {
                    credentials: 'include',
                    headers: {'Authorization': 'Bearer ' + token}
                });
                return {st: r.status, body: await r.text()};
            }''', access_token)
            try:
                after_data = json.loads(after_resp['body'])
                after_colors = after_data.get('data', {}).get('colors') or after_data.get('data', {}).get('items') or []
                target = next((c for c in after_colors if c.get('colorCode') == first_color.get('colorCode')), None)
                if target:
                    print(f"  扣减前 quantity: {first_color.get('quantity')}")
                    print(f"  扣减后 quantity: {target.get('quantity')}")
                    if first_color.get('quantity') != target.get('quantity'):
                        print(f"  ✅ 算法真执行了, 数量变化: {first_color.get('quantity')} -> {target.get('quantity')}")
            except Exception as e:
                print(f"  解析失败: {e}")

            # 回滚
            print(f"\n=== 4. 回滚加回 ===")
            payload['items'][0]['changeQty'] = 1
            payload['remark'] = 'trae_rollback'
            rollback_resp = page.evaluate('''async (args) => {
                const r = await fetch('/v1/app/inventory/operations', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Authorization': 'Bearer ' + args.token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(args.payload)
                });
                return {st: r.status, body: await r.text()};
            }''', {'token': access_token, 'payload': payload})
            print(f"  回滚 status: {rollback_resp['st']}")
            print(f"  body: {rollback_resp['body'][:300]}")

    print(f"\n=== 5. 全部 XHR ===")
    for x in xhr_log:
        u = x['url']
        if 'auth' in u.lower() or 'inventory' in u.lower() or 'operations' in u:
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('req_body'):
                print(f"    req: {x['req_body'][:300]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
