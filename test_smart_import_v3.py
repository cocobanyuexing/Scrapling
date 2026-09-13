"""实测：拼图图纸智能导入 v3 - 直接点"导入拼豆图纸生成"文案
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
                if 'json' in ct: body = resp.text()[:1500]
            except: body='<err>'
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body})
    page.on('response', on_response)

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
        page.locator('[data-slot="dialog-content"] [role="checkbox"], [data-slot="dialog-content"] input[type="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    print(f"  登录后: {page.url}")

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    # 点"新建"按钮打开下拉
    print("\n=== 2. 打开新建下拉 + 点'导入拼豆图纸生成' ===")
    # 找侧边栏/顶部的"新建"按钮
    page.evaluate('''() => {
        const btns = [...document.querySelectorAll('button')];
        // 找文本恰好是"新建"的按钮(不是含"新建"的长文本)
        const t = btns.find(b => (b.innerText||'').trim() === '新建' || (b.innerText||'').trim() === '创建');
        if (t) t.click();
    }''')
    page.wait_for_timeout(1500)

    # 直接点"导入拼豆图纸生成"
    loc = page.locator('text=导入拼豆图纸生成').first
    print(f"  '导入拼豆图纸生成' count: {loc.count()}")
    if loc.count() > 0:
        loc.click(timeout=5000)
        print("  ✓ 点中")
    else:
        # 备选: 直接找含"图纸"的可点元素
        page.evaluate('''() => {
            const el = [...document.querySelectorAll('*')].find(e => (e.innerText||'').trim() === '导入拼豆图纸生成');
            if (el) el.click();
        }''')
        print("  用 evaluate 点")
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/si3_modal.png')

    # 现在 SmartImportModal 应弹出了, 它有自己的 file input
    # ea handler: B(SMART_IMPORT); z.current.click()  -> z 是第3个 image input
    # 但 modal 弹出后, modal 内可能有自己的 input, 或者 z input 在 modal 之外
    print("\n=== 3. 上传 测试图.jpg ===")
    inps = page.locator('input[type="file"]')
    cnt = inps.count()
    print(f"  file input 总数: {cnt}")
    # 找 modal 内的 input (data-slot=dialog-content 内)
    modal_inp = page.locator('[data-slot="dialog-content"] input[type="file"], [role="dialog"] input[type="file"]').first
    print(f"  modal 内 file input: {modal_inp.count()}")
    
    target = modal_inp if modal_inp.count() > 0 else inps.last
    target.set_input_files(IMG)
    print(f"  ✓ 上传: {os.path.basename(IMG)}")

    # 等识别(最多 120s)
    print("\n=== 4. 等待识别完成 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
        # 识别完成标志: 进编辑器, 或出现"识别失败/成功/网格"
        if '/editor' in url:
            print(f"  [{i*2}s] 进编辑器!")
            break
        if any(k in body for k in ['识别失败','识别成功','网格','色号','创建项目','无法识别','Error','错误','失败']):
            print(f"  [{i*2}s] body 含关键词")
            break
    page.screenshot(path='/workspace/si3_after.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,700)''')
    print(f"  URL: {page.url}")
    print(f"  body 前700:\n{body}")

    print("\n=== 5. XHR 摘要 ===")
    for x in xhr_log:
        u = x['url']
        if any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','conversion','analyze','detect']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300:
                print(f"    body: {x['body'][:500]}")

    ctx.close(); browser.close()
print("\nDONE")
