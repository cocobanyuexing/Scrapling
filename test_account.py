"""测试账户中心剩余3个功能：每日签到、订阅管理、个人资料。"""
from patchright.sync_api import sync_playwright

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
            try:
                req_body = resp.request.post_data
                body = ''
                if 'json' in resp.headers.get('content-type', ''):
                    body = resp.body()[:600].decode('utf-8', errors='replace')
                xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status, 'req': (req_body or '')[:200], 'body': body})
            except:
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

    # 进账户中心
    print("\n=== 1. 进 /workspace/account ===")
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    page.screenshot(path='/workspace/acc_main.png')
    print(f"  URL: {page.url}")
    info = page.evaluate(r'''() => ({
        body: document.body.innerText.slice(0, 1500),
        btns: [...document.querySelectorAll('button, a')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            href: b.getAttribute('href') || ''
        })).filter(x => x.text && x.text.length < 30).slice(0, 40)
    })''')
    print(f"\n  body:\n{info['body']}")
    print(f"\n  按钮/链接: ")
    for b in info['btns']:
        print(f"    {b}")

    # 测每日签到
    print("\n=== 2. 测「每日签到」 ===")
    loc = page.locator('button:has-text("每日签到"), a:has-text("每日签到"), [role="button"]:has-text("每日签到")').first
    try:
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(3000)
            print(f"  ✓ 点了「每日签到」 -> {page.url}")
            page.screenshot(path='/workspace/acc_checkin.png')
            # 看签到页
            chk = page.evaluate(r'''() => ({
                url: location.href,
                body: document.body.innerText.slice(0, 1000),
                btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 20)
            })''')
            print(f"  URL: {chk['url']}")
            print(f"  body: {chk['body']}")
            print(f"  按钮: {chk['btns']}")
            # 尝试点签到按钮
            for txt in ['签到', '今日签到', '立即签到', '打卡']:
                loc2 = page.locator(f'button:has-text("{txt}")').first
                if loc2.count() > 0:
                    try:
                        loc2.click(timeout=3000)
                        page.wait_for_timeout(3000)
                        print(f"  ✓ 点了「{txt}」")
                        page.screenshot(path='/workspace/acc_checkin_done.png')
                        break
                    except: pass
    except Exception as e:
        print(f"  {e}")

    # 测订阅管理
    print("\n=== 3. 测「订阅管理」 ===")
    # 回到 account 页
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    loc = page.locator('button:has-text("订阅管理"), a:has-text("订阅管理"), [role="button"]:has-text("订阅管理")').first
    try:
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(3000)
            print(f"  ✓ 点了「订阅管理」 -> {page.url}")
            page.screenshot(path='/workspace/acc_sub.png')
            sub = page.evaluate(r'''() => ({
                url: location.href,
                body: document.body.innerText.slice(0, 1000),
                btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 20)
            })''')
            print(f"  URL: {sub['url']}")
            print(f"  body: {sub['body']}")
            print(f"  按钮: {sub['btns']}")
    except Exception as e:
        print(f"  {e}")

    # 测个人资料
    print("\n=== 4. 测「个人资料」 ===")
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    loc = page.locator('button:has-text("个人资料"), a:has-text("个人资料"), [role="button"]:has-text("个人资料")').first
    try:
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(3000)
            print(f"  ✓ 点了「个人资料」 -> {page.url}")
            page.screenshot(path='/workspace/acc_profile.png')
            prof = page.evaluate(r'''() => ({
                url: location.href,
                body: document.body.innerText.slice(0, 1200),
                inputs: [...document.querySelectorAll('input, textarea')].map(i => ({
                    type: i.type, name: i.name, value: i.value, placeholder: i.placeholder
                })),
                btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 20)
            })''')
            print(f"  URL: {prof['url']}")
            print(f"  body: {prof['body']}")
            print(f"  inputs: {prof['inputs']}")
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
