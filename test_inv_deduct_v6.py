"""实测 3 v6: 真发 POST /v1/app/inventory/operations 真扣减
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

    # 进库存页激活 cookie
    page.goto('https://i2tools.com/workspace/inventory', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)

    # 拿 baseline inventory
    print("\n=== 1. GET /v1/app/inventory/summary baseline ===")
    baseline = page.evaluate('''async () => {
        const r = await fetch('/v1/app/inventory/summary', {credentials: 'include'});
        const j = await r.json();
        // 找第一个有色号的库存条目
        const colors = j.data?.colors || j.data?.items || j.data?.inventory || [];
        return {
            st: r.status,
            keys: Object.keys(j.data||{}),
            total: colors.length,
            first3: colors.slice(0, 3).map(c => ({
                brandCode: c.brandCode || c.brand,
                colorCode: c.colorCode || c.code,
                quantity: c.quantity || c.count || c.stock,
                allKeys: Object.keys(c)
            }))
        };
    }''')
    print(f"  status: {baseline['st']}")
    print(f"  data keys: {baseline.get('keys')}")
    print(f"  总条目: {baseline.get('total')}")
    print(f"  前 3 条: {json.dumps(baseline.get('first3',[]), ensure_ascii=False, indent=2)}")

    # POST /v1/app/inventory/operations 真扣减
    print("\n=== 2. POST /v1/app/inventory/operations 真扣减 ===")
    # 用 baseline 第一个色号扣 1 个
    test_color = baseline.get('first3', [{}])[0]
    if test_color.get('colorCode'):
        payload = {
            "actionType": "manual_adjust",
            "sourceType": "user",
            "remark": "test_deduct_by_trae",
            "items": [{
                "brandCode": test_color.get('brandCode') or 'MARD',
                "colorCode": test_color.get('colorCode'),
                "changeQty": -1  # 负数 = 扣减
            }]
        }
        print(f"  请求 payload: {json.dumps(payload, ensure_ascii=False)}")
        result = page.evaluate('''async (payload) => {
            const r = await fetch('/v1/app/inventory/operations', {
                method: 'POST',
                credentials: 'include',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const text = await r.text();
            return {st: r.status, body: text.slice(0, 1500)};
        }''', payload)
        print(f"  POST status: {result['st']}")
        print(f"  POST body: {result['body']}")

    # 验证 baseline -> after 数量变化
    print("\n=== 3. GET /v1/app/inventory/summary after ===")
    after = page.evaluate('''async (targetCode) => {
        const r = await fetch('/v1/app/inventory/summary', {credentials: 'include'});
        const j = await r.json();
        const colors = j.data?.colors || j.data?.items || j.data?.inventory || [];
        // 找目标色号
        const target = colors.find(c => (c.colorCode || c.code) === targetCode);
        return {
            st: r.status,
            total: colors.length,
            target: target ? {code: target.colorCode||target.code, qty: target.quantity||target.count||target.stock} : null
        };
    }''', test_color.get('colorCode'))
    print(f"  status: {after['st']}")
    print(f"  总条目: {after.get('total')}")
    print(f"  目标色号 after: {after.get('target')}")

    # 回滚 - 加回去
    print("\n=== 4. 回滚 - 加回 1 个 ===")
    payload['items'][0]['changeQty'] = 1  # 正数 = 添加
    payload['remark'] = 'rollback_by_trae'
    rollback = page.evaluate('''async (payload) => {
        const r = await fetch('/v1/app/inventory/operations', {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const text = await r.text();
        return {st: r.status, body: text.slice(0, 600)};
    }''', payload)
    print(f"  回滚 status: {rollback['st']}")
    print(f"  回滚 body: {rollback['body']}")

    # 验证回滚后
    print("\n=== 5. 验证回滚后数量 ===")
    final = page.evaluate('''async (targetCode) => {
        const r = await fetch('/v1/app/inventory/summary', {credentials: 'include'});
        const j = await r.json();
        const colors = j.data?.colors || j.data?.items || j.data?.inventory || [];
        const target = colors.find(c => (c.colorCode || c.code) === targetCode);
        return target ? {code: target.colorCode||target.code, qty: target.quantity||target.count||target.stock} : null;
    }''', test_color.get('colorCode'))
    print(f"  回滚后: {final}")

    ctx.close(); browser.close()
print("\nDONE")
