"""移动端 viewport 测账户中心，看每日签到/订阅管理是否是移动端独有。"""
from patchright.sync_api import sync_playwright

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    # 移动端 viewport
    ctx = browser.new_context(
        viewport={'width': 390, 'height': 844},  # iPhone 14
        locale='zh-CN',
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
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

    print("\n=== 1. 移动端 /workspace/account ===")
    page.goto('https://i2tools.com/workspace/account', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    page.screenshot(path='/workspace/acc_mobile_main.png')

    info = page.evaluate(r'''() => ({
        url: location.href,
        body: document.body.innerText.slice(0, 1500),
        btns: [...document.querySelectorAll('button, a')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            href: b.getAttribute('href') || ''
        })).filter(x => x.text && x.text.length < 30).slice(0, 60)
    })''')
    print(f"  URL: {info['url']}")
    print(f"\n  body:\n{info['body']}")
    print(f"\n  按钮/链接:")
    for b in info['btns']:
        print(f"    {b}")

    # 看是否有「每日签到」「订阅管理」
    print("\n=== 2. 找「每日签到」/「订阅管理」 ===")
    found_checkin = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('*')].filter(el => el.innerText && el.innerText.trim() === '每日签到');
        return all.map(el => ({
            tag: el.tagName,
            cls: (el.className||'').toString().slice(0, 80),
            parent: el.parentElement?.tagName
        }));
    }''')
    found_sub = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('*')].filter(el => el.innerText && el.innerText.trim() === '订阅管理');
        return all.map(el => ({
            tag: el.tagName,
            cls: (el.className||'').toString().slice(0, 80),
            parent: el.parentElement?.tagName
        }));
    }''')
    print(f"  每日签到: {found_checkin}")
    print(f"  订阅管理: {found_sub}")

    # 如果找不到，试着找底部 tab bar / 头像下拉
    print("\n=== 3. 看是否有底部 tab 或菜单 ===")
    tabbar = page.evaluate(r'''() => {
        // 找底部 fixed 元素
        const fixed = [...document.querySelectorAll('[class*="fixed"], [class*="bottom"]')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.bottom > window.innerHeight * 0.7 && r.width > 100;
        });
        return fixed.slice(0, 5).map(el => ({
            tag: el.tagName,
            cls: (el.className||'').toString().slice(0, 80),
            text: (el.innerText||'').trim().slice(0, 100)
        }));
    }''')
    print(f"  底部 fixed 元素: {tabbar}")

    # 找「我的」入口
    print("\n=== 4. 找「我的」入口 ===")
    me_btn = page.locator('a:has-text("我的"), button:has-text("我的"), [role="button"]:has-text("我的")').first
    if me_btn.count() > 0:
        me_btn.click(timeout=3000)
        page.wait_for_timeout(3000)
        print(f"  ✓ 点了「我的」 -> {page.url}")
        page.screenshot(path='/workspace/acc_mobile_me.png')
        me_info = page.evaluate(r'''() => ({
            url: location.href,
            body: document.body.innerText.slice(0, 1500),
            btns: [...document.querySelectorAll('button, a, [role="button"]')].map(b => ({
                text: (b.innerText||'').trim().slice(0,30),
                href: b.getAttribute('href') || ''
            })).filter(x => x.text && x.text.length < 30).slice(0, 50)
        })''')
        print(f"  URL: {me_info['url']}")
        print(f"\n  body:\n{me_info['body']}")
        print(f"\n  按钮:")
        for b in me_info['btns']:
            print(f"    {b}")

    print(f"\n=== XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")
            if x.get('body') and 'checkin' in x['url'].lower() or 'subscription' in x['url'].lower():
                print(f"    resp: {x['body']}")

    browser.close()
