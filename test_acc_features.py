"""移动端测每日签到和订阅管理。"""
from patchright.sync_api import sync_playwright

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(
        viewport={'width': 390, 'height': 844},
        locale='zh-CN',
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1',
        is_mobile=True,
        has_touch=True
    )
    page = ctx.new_page()

    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                req_body = resp.request.post_data
                body = ''
                if 'json' in resp.headers.get('content-type', ''):
                    body = resp.body()[:600].decode('utf-8', errors='replace')
                xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status, 'req': (req_body or '')[:200], 'body': body})
            except:
                xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status})
    page.on('response', on_response)

    print("=== 0. 移动端登录 ===")
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

    print("\n=== 1. 进 /workspace/account ===")
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)

    # 测每日签到
    print("\n=== 2. 点「每日签到」 ===")
    loc = page.locator('button:has-text("每日签到")').first
    if loc.count() > 0:
        loc.click(timeout=3000)
        page.wait_for_timeout(3000)
        print(f"  -> {page.url}")
        page.screenshot(path='/workspace/acc_checkin.png')
        chk = page.evaluate(r'''() => ({
            url: location.href,
            body: document.body.innerText.slice(0, 1200),
            btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 30)
        })''')
        print(f"  URL: {chk['url']}")
        print(f"  body: {chk['body']}")
        print(f"  按钮: {chk['btns']}")
        # 尝试点签到按钮
        for txt in ['签到', '今日签到', '立即签到', '打卡', '领取']:
            loc2 = page.locator(f'button:has-text("{txt}")').first
            try:
                if loc2.count() > 0:
                    loc2.click(timeout=3000)
                    page.wait_for_timeout(3000)
                    print(f"  ✓ 点了「{txt}」")
                    page.screenshot(path='/workspace/acc_checkin_done.png')
                    break
            except: pass
        # 回账户页
        page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)

    # 测订阅管理
    print("\n=== 3. 点「订阅管理」 ===")
    loc = page.locator('button:has-text("订阅管理")').first
    if loc.count() > 0:
        loc.click(timeout=3000)
        page.wait_for_timeout(3000)
        print(f"  -> {page.url}")
        page.screenshot(path='/workspace/acc_subscription.png')
        sub = page.evaluate(r'''() => ({
            url: location.href,
            body: document.body.innerText.slice(0, 1200),
            btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 30)
        })''')
        print(f"  URL: {sub['url']}")
        print(f"  body: {sub['body']}")
        print(f"  按钮: {sub['btns']}")

    # 测个人资料 (实际是顶部「User_pm6v8r」)
    print("\n=== 4. 点用户名进个人资料 ===")
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    # 点头像或用户名区域
    loc = page.locator('text=User_pm6v8r').first
    try:
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(3000)
            print(f"  -> {page.url}")
            page.screenshot(path='/workspace/acc_profile_mobile.png')
            prof = page.evaluate(r'''() => ({
                url: location.href,
                body: document.body.innerText.slice(0, 1200),
                btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 30)
            })''')
            print(f"  URL: {prof['url']}")
            print(f"  body: {prof['body']}")
            print(f"  按钮: {prof['btns']}")
    except Exception as e:
        print(f"  {e}")

    print(f"\n=== XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")
            if x.get('body'):
                print(f"    resp: {x['body']}")

    browser.close()
