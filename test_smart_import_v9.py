"""实测：拼图图纸智能导入 v9 - force click + 完整流程
样本: /workspace/测试图.jpg
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

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
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:3000]
            except: body='<err>'
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body})
    page.on('response', on_response)

    # console errors
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text[:200]}'))

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => b.innerText && (b.innerText.trim() === '登录' || b.innerText.trim() === '登入'));
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    # 验证登录
    auth = page.evaluate('''() => {
        const sidebar = document.body.innerText;
        return sidebar.includes('登录') ? 'NOT_LOGGED_IN' : 'LOGGED_IN';
    }''')
    print(f"  登录状态: {auth}")

    print("\n=== 1. 进 create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    print("\n=== 2. 触发 smartImport modal ===")
    page.locator('input[type="file"][accept*="image"]').nth(2).set_input_files(IMG)
    page.wait_for_timeout(3000)
    # 关干扰 dialog
    cancel = page.locator('button:has-text("取消")').first
    if cancel.count() > 0:
        cancel.click(timeout=2000)
        page.wait_for_timeout(1000)
        print("  关了取消")

    print("\n=== 3. force click MARD 视觉识别 ===")
    # 用 force click 绕过 focus trap
    try:
        page.get_by_text("MARD 视觉识别", exact=False).first.click(force=True, timeout=5000)
        print("  ✓ force click MARD")
    except Exception as e:
        print(f"  force click 失败: {e}")
        # 试 radio role
        radios = page.locator('[role="radio"]')
        print(f"  radio count: {radios.count()}")
        if radios.count() > 0:
            radios.first.click(force=True, timeout=5000)
            print("  ✓ 点了第一个 radio")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si9_after_mard.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
    print(f"  body:\n{body[:400]}")

    # 如果有 下一步/确认 按钮, 点它
    print("\n=== 4. 找下一步/确认按钮 ===")
    for btn_text in ['下一步', '确认', '确定', '继续', 'Next', 'Confirm', 'Continue']:
        btn = page.locator(f'button:has-text("{btn_text}")').first
        if btn.count() > 0:
            print(f"  找到 '{btn_text}' 按钮, 点击")
            btn.click(force=True, timeout=3000)
            page.wait_for_timeout(2000)
            break
    else:
        print("  没找到下一步按钮")

    print("\n=== 5. 检查是否进了上传步骤 ===")
    file_info = page.evaluate('''() => {
        const inps = [...document.querySelectorAll('input[type="file"]')];
        return inps.map((i, idx) => ({idx, accept: i.accept||'', visible: i.offsetParent !== null}));
    }''')
    print(f"  file inputs: {file_info}")
    body2 = page.evaluate('''() => document.body.innerText.slice(0,400)''')
    print(f"  body:\n{body2[:300]}")
    page.screenshot(path='/workspace/si9_step2.png')

    # 如果在上传步骤, 上传
    print("\n=== 6. 上传 ===")
    vis_inp = page.locator('input[type="file"][accept*="image"]:visible').first
    if vis_inp.count() > 0:
        vis_inp.set_input_files(IMG)
        print("  ✓ 上传")
    else:
        page.locator('input[type="file"][accept*="image"]').last.set_input_files(IMG)
        print("  ✓ 上传到最后")

    print("\n=== 7. 等识别 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,300)''')
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            break
        if any(k in body for k in ['色号','网格','创建','完成','裁剪','分割','成功']) and '选择导入' not in body:
            print(f"  [{i*2}s] 识别结果出现")
            page.wait_for_timeout(3000)
            break
    page.screenshot(path='/workspace/si9_final.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
    print(f"  URL: {page.url}")
    print(f"  body:\n{body[:400]}")

    print("\n=== 8. console errors ===")
    for m in console_msgs[-10:]:
        print(f"  {m}")

    print("\n=== 9. XHR ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:500]}")

    ctx.close(); browser.close()
print("\nDONE")
