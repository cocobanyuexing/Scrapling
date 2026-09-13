"""实测：拼图图纸智能导入 v4 - 选 MARD 视觉识别 + 上传 + 识别
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
                if 'json' in ct: body = resp.text()[:2000]
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

    print("\n=== 1. 进 create + 开下拉 + 点'导入拼豆图纸生成' ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.evaluate('''() => {
        const btns = [...document.querySelectorAll('button')];
        const t = btns.find(b => (b.innerText||'').trim() === '新建' || (b.innerText||'').trim() === '创建');
        if (t) t.click();
    }''')
    page.wait_for_timeout(1500)
    page.locator('text=导入拼豆图纸生成').first.click(timeout=5000)
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/si4_modal_step1.png')

    print("\n=== 2. 选 'MARD 视觉识别' ===")
    # 点 MARD 视觉识别
    loc = page.locator('text=MARD 视觉识别').first
    print(f"  'MARD 视觉识别' count: {loc.count()}")
    if loc.count() > 0:
        loc.click(timeout=5000)
        print("  ✓ 选 MARD 视觉识别")
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/si4_step2.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,600)''')
    print(f"  body 前600:\n{body}")

    print("\n=== 3. 找 file input 上传 测试图.jpg ===")
    inps = page.locator('input[type="file"]')
    print(f"  file input 总数: {inps.count()}")
    # 列出每个 input 的 accept
    accs = page.evaluate('''() => [...document.querySelectorAll('input[type="file"]')].map(i => ({
        accept: i.accept, visible: i.offsetParent !== null, in_dialog: !!i.closest('[role="dialog"], [data-slot="dialog-content"]')
    }))''')
    print(f"  inputs 详情: {accs}")

    # 找 modal 内的 input
    modal_inp = page.locator('[role="dialog"] input[type="file"], [data-slot="dialog-content"] input[type="file"]').first
    if modal_inp.count() > 0:
        modal_inp.set_input_files(IMG)
        print(f"  ✓ 上传到 modal 内 input")
    else:
        # 找 accept 含 image 的最后一个
        img_inps = page.locator('input[type="file"][accept*="image"]')
        n = img_inps.count()
        print(f"  image inputs: {n}")
        if n > 0:
            img_inps.nth(n-1).set_input_files(IMG)
            print(f"  ✓ 上传到最后一个 image input")
    
    # 等识别(最多 120s)
    print("\n=== 4. 等待识别 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            break
        if any(k in body for k in ['识别失败','无法识别','错误','失败','色号','网格','创建','完成','成功']):
            if any(k in body for k in ['色号','网格','创建','完成','成功']) and '选择导入方式' not in body:
                print(f"  [{i*2}s] 似乎识别完成")
                break
            if any(k in body for k in ['识别失败','无法识别','错误','失败']):
                print(f"  [{i*2}s] 识别可能失败")
                break
    page.screenshot(path='/workspace/si4_after_recognize.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,700)''')
    print(f"  URL: {page.url}")
    print(f"  body 前700:\n{body}")

    print("\n=== 5. 全部 XHR (找识别 API) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','analyz','detect','convers']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300:
                print(f"    body: {x['body'][:600]}")

    ctx.close(); browser.close()
print("\nDONE")
