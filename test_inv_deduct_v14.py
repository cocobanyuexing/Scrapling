"""实测 3 v14: 真发 inventory 接口 全路径 (修正字段名 + 真实 MARD 色号 H1)
反编译发现:
  - 字段: actionType (不是 operationType)
  - 枚举值: manual_adjust | project_consume | import | rollback
  - items: 必须是数组, 每项含 brandCode/colorCode/changeQty
  - MARD 真实色号: H1/H2/H3/H4... (不带0, 来自 chunk 9350 色号索引表)
  - 5 个品牌: MARD | COCO | 漫漫 | 盼盼 | 咪小窝
  - requestId 必须 >= 16 字符
  - rollback 路径必须 numeric string (数字)
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
            method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        return {st: r.status, body: await r.text()};
    }''', {"email": EMAIL, "password": PWD})
    access_token = json.loads(login_resp['body'])['data']['accessToken']
    print(f"  token: {access_token[:60]}...")

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
        if payload: print(f"  req:  {json.dumps(payload, ensure_ascii=False)[:400]}")
        print(f"  resp: {r['body'][:1500]}")
        return r

    print("\n=== 1. 看初始库存 ===")
    s_before = json.loads(call('GET', '/v1/app/inventory/summary', label='summary-before').get('body', '{}')).get('data',{})

    print("\n=== 2. POST /v1/app/inventory/operations 手动加色号 H1 (+10) ===")
    # 真实字段名 actionType + items 数组 + 真 MARD 色号 H1
    add_payload = {
        "actionType": "manual_adjust",
        "items": [{
            "brandCode": "MARD",
            "colorCode": "H1",
            "changeQty": 10
        }],
        "remark": "trae_v14_test_add"
    }
    r_add = call('POST', '/v1/app/inventory/operations', add_payload, label='manual-adjust-add-H1-+10')
    op_id = None
    try:
        d = json.loads(r_add['body']).get('data', {})
        op_id = d.get('id') or d.get('operationId') or d.get('operation', {}).get('id')
        print(f"  ✓ operationId: {op_id}")
    except: pass

    print("\n=== 3. 看加色号后的库存 ===")
    s_after_add = json.loads(call('GET', '/v1/app/inventory/summary', label='summary-after-add').get('body', '{}')).get('data',{})

    print("\n=== 4. GET /v1/app/inventory/colors 看色号列表 ===")
    c_resp = call('GET', '/v1/app/inventory/colors?pageIndex=1&pageSize=2000', label='colors-list')
    try:
        items = json.loads(c_resp['body']).get('data',{}).get('items',[])
        print(f"  ✓ items 总数: {len(items)}")
        for it in items[:5]:
            print(f"    {json.dumps(it, ensure_ascii=False)[:200]}")
    except: pass

    if op_id:
        print(f"\n=== 5. POST /v1/app/inventory/operations/{op_id}/rollback 真回滚 ===")
        r_rollback = call('POST', f'/v1/app/inventory/operations/{op_id}/rollback', {}, label='rollback')
    else:
        print("\n=== 5. rollback 跳过 (没拿到 op_id) ===")

    print("\n=== 6. 真扣减 H1 (-3) ===")
    deduct_payload = {
        "actionType": "manual_adjust",
        "items": [{
            "brandCode": "MARD",
            "colorCode": "H1",
            "changeQty": -3
        }],
        "remark": "trae_v14_test_deduct"
    }
    r_deduct = call('POST', '/v1/app/inventory/operations', deduct_payload, label='manual-adjust-deduct-H1-(-3)')
    op_id2 = None
    try:
        d2 = json.loads(r_deduct['body']).get('data', {})
        op_id2 = d2.get('id') or d2.get('operationId')
        print(f"  ✓ operationId: {op_id2}")
    except: pass

    if op_id2:
        print(f"\n=== 7. 回滚扣减 op={op_id2} ===")
        call('POST', f'/v1/app/inventory/operations/{op_id2}/rollback', {}, label='rollback-deduct')

    print("\n=== 8. 看 final 库存 ===")
    s_final = json.loads(call('GET', '/v1/app/inventory/summary', label='summary-final').get('body', '{}')).get('data',{})

    print("\n=== 9. POST /v1/app/inventory/operations/project-consume 真实项目消耗 ===")
    # materialsCompact 用真实色号格式 "H1:1,H2:2"
    pc_payload = {
        "snapshotTitle": "trae_v14_consume_test",
        "colorSystem": "MARD",
        "materialsCompact": "H1:1,H2:2",
        "remark": "trae_v14_consume_remark"
    }
    r_pc = call('POST', '/v1/app/inventory/operations/project-consume', pc_payload, label='project-consume-real')

    print("\n=== 10. POST /v1/app/inventory/import/ai-preview 真实 AI 预览 ===")
    ai_payload = {
        "requestId": f"trae-test-{int(time.time())}-abcd",  # >= 16 字符
        "brandCode": "MARD",
        "text": "测试拼豆图纸文本",  # <= 10000 字符
        "imageUrl": "https://oss-cdn.i2tools.com/test.png"
    }
    r_ai = call('POST', '/v1/app/inventory/import/ai-preview', ai_payload, label='ai-preview-real')

    print("\n=== 11. 库存变化总结 ===")
    print(f"  初始:  totalQuantity={s_before.get('totalQuantity')}, trackedColorCount={s_before.get('trackedColorCount')}")
    print(f"  加后:  totalQuantity={s_after_add.get('totalQuantity')}, trackedColorCount={s_after_add.get('trackedColorCount')}")
    print(f"  最终:  totalQuantity={s_final.get('totalQuantity')}, trackedColorCount={s_final.get('trackedColorCount')}")

    print("\n=== 12. 全部 XHR ===")
    for x in xhr_log:
        u = x['url']
        if 'inventory' in u:
            print(f"  {x['st']} {x['m']} {u[:130]}")
            if x.get('req_body'):
                print(f"    req: {x['req_body'][:300]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
