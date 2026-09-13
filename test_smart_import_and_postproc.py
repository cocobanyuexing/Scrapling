"""实测：拼图图纸智能导入(smartImport) + 后处理算法弹窗
样本: /workspace/测试图.jpg
流程:
  /workspace/create -> smartImport 卡 -> SmartImportModal -> 上传 -> 识别 API -> 建项目 -> 编辑器
  编辑器 -> 色号合并/去除杂色/降噪 弹窗 -> 调算法
"""
from patchright.sync_api import sync_playwright
import json, os, time

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
                if 'json' in ct:
                    body = resp.text()[:800]
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

    # 找 smartImport 卡片并点击。卡片有 onSelect -> openSmartImportDialog
    # 直接通过 React 调用: 找到带 violet/紫色 class 的卡片或文案
    clicked = page.evaluate('''() => {
        // 找文案含"智能"的卡片
        const cards = [...document.querySelectorAll('[role="button"], button, div')];
        const target = cards.find(c => {
            const t = (c.innerText||'').trim();
            return t.includes('智能') && t.length < 40;
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点智能卡片: {clicked}")
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/si_1_modal.png')

    # SmartImportModal 应该弹出了。找 file input
    print("\n=== 2. 找 modal 里的 file input 并上传 ===")
    # modal 里可能有 input[type=file][accept=image]
    inp = page.locator('input[type="file"][accept*="image"]').first
    print(f"  image input count: {inp.count()}")
    if inp.count() == 0:
        # 可能需要点"上传"按钮触发
        page.evaluate('''() => {
            const btns = [...document.querySelectorAll('button')];
            const u = btns.find(b => /上传|选择|导入|upload/i.test(b.innerText||'') || /上传/.test(b.getAttribute('aria-label')||''));
            if (u) u.click();
        }''')
        page.wait_for_timeout(1000)
        inp = page.locator('input[type="file"][accept*="image"]').first
        print(f"  再找 image input: {inp.count()}")
    if inp.count() > 0:
        inp.set_input_files(IMG)
        print(f"  ✓ 上传: {os.path.basename(IMG)}")
        # 等识别完成（最多 60s）
        for _ in range(30):
            page.wait_for_timeout(2000)
            body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
            if any(k in body for k in ['识别','完成','网格','色号','失败','错误','错误','创建','Error','失败']):
                break
        page.screenshot(path='/workspace/si_2_after_upload.png')
        body = page.evaluate('''() => document.body.innerText.slice(0,600)''')
        print(f"  body 前600:\n{body}")
        print(f"  URL: {page.url}")
    else:
        print("  ❌ 没找到 image input")
        page.screenshot(path='/workspace/si_2_noinp.png')

    print("\n=== 3. XHR 摘要（找识别 API）===")
    # 过滤出可能的识别 API
    for x in xhr_log:
        u = x['url']
        if any(k in u for k in ['smart','pattern','recogn','perler','import','upload']) or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('body') and x['st'] < 300:
                print(f"    body: {x['body'][:300]}")

    print("\n=== 4. 如果进了编辑器, 找后处理按钮 ===")
    page.wait_for_timeout(3000)
    btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            aria: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || ''
        })).filter(x => x.text || x.aria).slice(0, 80);
    }''')
    postproc_keywords = ['色号合并','去除杂色','降噪','合并','杂色','denoise','merge','noise','色号']
    found_post = [b for b in btns if any(k in (b['text']+b['aria']+b['title']) for k in postproc_keywords)]
    print(f"  后处理相关按钮: {found_post}")
    page.screenshot(path='/workspace/si_3_editor.png')

    ctx.close(); browser.close()
print("\nDONE")
