"""实测 3 v13: 真发 POST /v1/app/auth/email/login + 真调 inventory API 全路径
反编译 chunk 3244 发现的真实接口路径：
  - GET  /v1/app/inventory/colors           (色号列表)
  - GET  /v1/app/inventory/summary          (库存汇总)
  - GET  /v1/app/inventory/operations       (操作历史)
  - POST /v1/app/inventory/operations       (手动调整: 加/减色号)
  - POST /v1/app/inventory/operations/{id}/rollback  (回滚)
  - POST /v1/app/inventory/operations/project-consume (项目消耗库存)
  - POST /v1/app/inventory/operations/project-consume/{projectId}
  - POST /v1/app/inventory/operations/project-consume/batch
  - POST /v1/app/inventory/import/ai-preview (AI 预览)
  - GET  /v1/app/inventory/import/ai-quota   (AI 配额)
"""
from patchright.sync_api import sync_playwright
import json, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    # 监听 XHR (用于事后查证请求体)
    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:3000]
            except: body='<err>'
            req_body = ''
            try:
                if resp.request.method in ('POST','PUT','PATCH'):
                    req_body = (resp.request.post_data or '')[:1000]
            except: pass
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body, 'req_body': req_body})
    page.on('response', on_response)

    print("=== 0. POST /v1/app/auth/email/login 真登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)

    login_resp = page.evaluate('''async (payload) => {
        const r = await fetch('/v1/app/auth/email/login', {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        return {st: r.status, body: await r.text()};
    }''', {"email": EMAIL, "password": PWD})
    print(f"  POST status: {login_resp['st']}")
    login_data = json.loads(login_resp['body'])
    access_token = login_data['data']['accessToken']
    user = login_data['data'].get('user')
    uid = login_data['data'].get('uid') or (user and user.get('id'))
    print(f"  accessToken: {access_token[:60]}...")
    print(f"  user/uid: {user or uid}")

    # 携带 Authorization 调用各 inventory 接口
    def call(method, path, payload=None, label=''):
        args = {'m': method, 'p': path, 'payload': payload, 'token': access_token}
        r = page.evaluate('''async (a) => {
            const opt = {method: a.m, credentials: 'include', headers: {'Authorization': 'Bearer ' + a.token}};
            if (a.payload) {
                opt.headers['Content-Type'] = 'application/json';
                opt.body = JSON.stringify(a.payload);
            }
            const r = await fetch(a.p, opt);
            return {st: r.status, body: await r.text()};
        }''', args)
        print(f"\n--- {label} ---")
        print(f"  {method} {path}  status={r['st']}")
        print(f"  resp: {r['body'][:1500]}")
        return r

    print("\n=== 1. GET /v1/app/inventory/summary 库存汇总 ===")
    summary_r = call('GET', '/v1/app/inventory/summary', label='summary')

    print("\n=== 2. GET /v1/app/inventory/colors 色号列表 ===")
    colors_r = call('GET', '/v1/app/inventory/colors?pageIndex=1&pageSize=2000', label='colors')

    print("\n=== 3. GET /v1/app/inventory/operations 操作历史 ===")
    ops_r = call('GET', '/v1/app/inventory/operations?pageIndex=1&pageSize=20', label='operations-history')

    print("\n=== 4. GET /v1/app/inventory/brands 品牌列表 ===")
    brands_r = call('GET', '/v1/app/inventory/brands', label='brands')

    print("\n=== 5. GET /v1/app/inventory/import/ai-quota AI 配额 ===")
    quota_r = call('GET', '/v1/app/inventory/import/ai-quota', label='ai-quota')

    print("\n=== 6. POST /v1/app/inventory/operations 手动调整(测试扣减 H01 不存在色号) ===")
    # payload 格式来自反编译 m(e){return o.L.post("/app/inventory/operations",e)}
    # 因为我们没看到完整字段名, 先发一个保守的测试 payload, 让后端报错暴露真实 schema
    test_payload_v1 = {
        "brandCode": "MARD",
        "colorCode": "H01",
        "changeQty": -1,
        "operationType": "manual_adjust",
        "sourceType": "user",
        "remark": "trae_real_test_v13"
    }
    r1 = call('POST', '/v1/app/inventory/operations', test_payload_v1, label='manual-adjust-v1')

    print("\n=== 7. POST /v1/app/inventory/operations 手动调整 v2 (猜测字段) ===")
    test_payload_v2 = {
        "items": [{
            "brandCode": "MARD",
            "colorCode": "H01",
            "changeQty": -1
        }],
        "operationType": "manual_adjust",
        "remark": "trae_real_test_v13_v2"
    }
    r2 = call('POST', '/v1/app/inventory/operations', test_payload_v2, label='manual-adjust-v2')

    print("\n=== 8. POST /v1/app/inventory/operations/project-consume 项目消耗(测试) ===")
    # 来自反编译 y(e){...colorSystem:e.colorSystem,materialsCompact:t...}
    pc_payload = {
        "snapshotTitle": "trae_test_consume",
        "colorSystem": "MARD",
        "materialsCompact": "H01:1",
        "remark": "trae_real_test_v13_consume"
    }
    r3 = call('POST', '/v1/app/inventory/operations/project-consume', pc_payload, label='project-consume')

    print("\n=== 9. POST /v1/app/inventory/import/ai-preview AI 预览(空数据测试 schema) ===")
    # u(e){return o.L.post("/app/inventory/import/ai-preview",{...e,requestId:...})}
    ai_payload = {
        "requestId": f"trae-{int(time.time())}",
        "imageUrl": "https://oss-cdn.i2tools.com/test.png"
    }
    r4 = call('POST', '/v1/app/inventory/import/ai-preview', ai_payload, label='ai-preview')

    print("\n=== 10. POST /v1/app/inventory/operations/{fakeId}/rollback 回滚(查不存在ID) ===")
    rollback_r = call('POST', '/v1/app/inventory/operations/trae-fake-id-12345/rollback', label='rollback-fake')

    print("\n=== 11. 全部 XHR (含请求体) ===")
    for x in xhr_log:
        u = x['url']
        if 'inventory' in u or 'auth' in u.lower():
            print(f"  {x['st']} {x['m']} {u[:130]}")
            if x.get('req_body'):
                print(f"    req: {x['req_body'][:300]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
