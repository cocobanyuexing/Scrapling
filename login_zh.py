"""中文版直接登录：i2tools.com（不带 /en）+ 正确邮箱，全程无验证码。"""
from patchright.sync_api import sync_playwright
import json

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
            x = {'method': resp.request.method, 'url': resp.url, 'status': resp.status}
            try:
                req_body = resp.request.post_data
                if req_body:
                    x['req'] = req_body[:300]
                ct = resp.headers.get('content-type', '')
                if 'json' in ct:
                    x['body'] = resp.body()[:800].decode('utf-8', errors='replace')
            except Exception:
                pass
            xhr_log.append(x)
    page.on('response', on_response)

    # 关键：中文版入口，不带 /en
    print("=== 0. 打开中文版首页 https://i2tools.com/ ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    print(f"  当前 URL: {page.url}")
    print(f"  lang 标签: {page.evaluate('document.documentElement.lang')}")

    # 1. ESC 关闭所有 dialog（更新日志等）
    print("\n=== 1. ESC 关闭所有 dialog ===")
    page.keyboard.press('Escape')
    page.wait_for_timeout(1500)
    n = page.evaluate('document.querySelectorAll("[data-slot=dialog-content]").length')
    print(f"  剩余 dialog: {n}")

    # 2. 点击登录按钮
    print("\n=== 2. 点击登录按钮 ===")
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => b.innerText && (b.innerText.trim() === '登录' || b.innerText.trim() === '登入'));
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    n = page.evaluate('document.querySelectorAll("[data-slot=dialog-content]").length')
    print(f"  打开 dialog 数: {n}")

    # 3. 填邮箱密码
    print("\n=== 3. 填邮箱密码 ===")
    email_loc = page.locator('[data-slot="dialog-content"] input[type="email"]').first
    pwd_loc = page.locator('[data-slot="dialog-content"] input[type="password"]').first
    email_loc.fill(EMAIL, timeout=5000)
    pwd_loc.fill(PWD, timeout=5000)
    print(f"  ✓ 邮箱={EMAIL} 密码已填")

    # 4. 勾选 checkbox
    print("\n=== 4. 勾选同意条款 ===")
    try:
        cb = page.locator('[data-slot="dialog-content"] [role="checkbox"], [data-slot="dialog-content"] input[type="checkbox"]').first
        state_before = cb.get_attribute('aria-checked') or 'false'
        print(f"  勾选前: {state_before}")
        cb.click(timeout=3000)
        page.wait_for_timeout(500)
        state_after = cb.get_attribute('aria-checked') or 'false'
        print(f"  勾选后: {state_after}")
    except Exception as e:
        print(f"  ✗ 勾选失败: {e}")
        try:
            label = page.locator('[data-slot="dialog-content"] label:has([role="checkbox"]), [data-slot="dialog-content"] label:has(input[type="checkbox"])').first
            label.click(timeout=3000)
            page.wait_for_timeout(500)
            print(f"  ✓ 用 label 点击成功")
        except Exception as e2:
            print(f"  ✗ label 也失败: {e2}")

    page.screenshot(path='/workspace/login_filled_zh.png')

    # 5. 提交登录
    print("\n=== 5. 提交登录 ===")
    clicked = False
    for txt in ['开始游戏', '開始遊戲', '登录', '登入', 'Login', 'Sign in']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 已点击「{txt}」")
                page.wait_for_timeout(6000)
                clicked = True
                break
            except Exception as e:
                print(f"  ✗「{txt}」点击失败: {e}")
    if not clicked:
        try:
            page.locator('[data-slot="dialog-content"] button[type="submit"]').first.click(timeout=5000)
            print("  ✓ 用 type=submit 兜底点击")
            page.wait_for_timeout(6000)
            clicked = True
        except Exception as e:
            print(f"  ✗ 兜底也失败: {e}")

    page.screenshot(path='/workspace/login_result_zh.png')

    # 6. 看登录后状态
    print("\n=== 6. 登录后状态 ===")
    state = page.evaluate('''() => {
        const ds = [...document.querySelectorAll('[data-slot="dialog-content"]')];
        const authStillOpen = ds.some(d => d.innerText && (d.innerText.includes('Authentication') || d.innerText.includes('登錄') || d.innerText.includes('登录')));
        let err = '';
        for (const d of ds) {
            const els = [...d.querySelectorAll('*')].map(el => el.innerText?.trim()).filter(Boolean);
            const found = els.filter(t => t.length < 100 && /错误|錯誤|失敗|失败|不存在|无效|wrong|invalid|incorrect|密码|凭证|凭證/.test(t)).join(' | ');
            if (found) err = found;
        }
        return {authStillOpen, err, nav: document.querySelector('nav,header')?.innerText?.slice(0, 300)};
    }''')
    print(f"  auth dialog 仍打开: {state['authStillOpen']}")
    print(f"  错误提示: '{state['err']}'")
    print(f"  导航区: {state['nav']}")

    # 7. cookies
    print("\n=== 7. Cookies (token类) ===")
    token_cookies = []
    for c in ctx.cookies():
        if any(k in c['name'].lower() for k in ['token', 'xsrf', 'auth', 'session']):
            print(f"  {c['name']}={c['value'][:60]}... httpOnly={c.get('httpOnly')} path={c.get('path')}")
            token_cookies.append(c)

    # 8. XHR
    print(f"\n=== 8. 全部 XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        print(f"\n  {x['method']} {x['url'][:120]}")
        print(f"    状态: {x['status']}")
        if 'req' in x:
            print(f"    请求: {x['req']}")
        if 'body' in x:
            print(f"    响应: {x['body']}")

    # 9. 持久化 cookies
    with open('/workspace/login_cookies.json', 'w') as f:
        json.dump(token_cookies, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ token cookies 已保存到 /workspace/login_cookies.json ({len(token_cookies)} 个)")

    browser.close()
