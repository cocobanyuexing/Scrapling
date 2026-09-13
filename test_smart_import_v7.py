"""实测：拼图图纸智能导入 v7 - 只触发 z input, 关干扰 dialog, 精确点 MARD
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
                if 'json' in ct: body = resp.text()[:2500]
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

    print("\n=== 1. 进 create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    print("\n=== 2. 只触发 z input (smartImport) ===")
    img_inps = page.locator('input[type="file"][accept*="image"]')
    n = img_inps.count()
    print(f"  image input 数: {n}")
    # 只设 z (index 2), 不设其他
    img_inps.nth(2).set_input_files(IMG)
    print(f"  ✓ 设文件到 z (index 2)")
    page.wait_for_timeout(3000)

    # 检查有几个 modal
    print("\n=== 3. 检查 modal 状态 ===")
    modals = page.evaluate('''() => {
        // 找所有含 "选择" 文字的可视容器
        const all = [...document.querySelectorAll('*')];
        const results = [];
        for (const el of all) {
            const t = (el.innerText||'').trim();
            if ((t.includes('选择转换模式') || t.includes('选择导入方式')) && t.length < 200) {
                const r = el.getBoundingClientRect();
                if (r.width > 100 && r.height > 100) {
                    results.push({
                        text: t.slice(0, 100),
                        tag: el.tagName,
                        cls: (el.className||'').slice(0,80),
                        rect: {w: r.width, h: r.height}
                    });
                }
            }
        }
        return results;
    }''')
    print(f"  找到 {len(modals)} 个 modal:")
    for m in modals:
        print(f"    {m['tag']} cls={m['cls'][:40]} {m['rect']}")
        print(f"    text: {m['text'][:80]}")

    # 如果有 "选择转换模式" 干扰 dialog, 关掉它
    print("\n=== 4. 关掉干扰的 '选择转换模式' dialog ===")
    # 点 "取消" 按钮
    cancel = page.locator('button:has-text("取消")').first
    if cancel.count() > 0:
        cancel.click(timeout=3000)
        print("  ✓ 点了取消")
    else:
        page.keyboard.press('Escape')
        print("  按 Escape")
    page.wait_for_timeout(1500)

    # 现在只剩 SmartImportModal
    page.screenshot(path='/workspace/si7_modal_only.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
    print(f"  body:\n{body[:300]}")

    print("\n=== 5. 用 Playwright 原生 locator 点 MARD 视觉识别 ===")
    # 用 get_by_text 精确匹配
    mard = page.get_by_text("MARD 视觉识别", exact=False)
    print(f"  get_by_text count: {mard.count()}")
    if mard.count() > 0:
        mard.first.click(timeout=5000)
        print("  ✓ 点中 MARD 视觉识别")
    else:
        # fallback: 找含 MARD 的按钮
        mard2 = page.locator('button:has-text("MARD"), [role="button"]:has-text("MARD"), [role="radio"]:has-text("MARD")').first
        print(f"  fallback count: {mard2.count()}")
        if mard2.count() > 0:
            mard2.click(timeout=5000)
            print("  ✓ fallback 点中")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si7_after_mard.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
    print(f"  body:\n{body[:400]}")

    print("\n=== 6. 找上传 input 并上传 ===")
    # SmartImportModal step2 应该有 file input
    file_info = page.evaluate('''() => {
        const inps = [...document.querySelectorAll('input[type="file"]')];
        return inps.map((i, idx) => ({
            idx, accept: i.accept||'', visible: i.offsetParent !== null
        }));
    }''')
    print(f"  file inputs: {file_info}")
    # 找新增的 image input (modal 的)
    new_inp = page.locator('input[type="file"][accept*="image"]').last
    new_inp.set_input_files(IMG)
    print(f"  ✓ 上传到最后 image input")
    
    # 等识别
    print("\n=== 7. 等待识别 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            break
        if any(k in body for k in ['识别失败','无法识别','色号','网格','创建项目','完成','识别完成','成功']) and '选择导入方式' not in body:
            print(f"  [{i*2}s] 识别完成?")
            page.wait_for_timeout(3000)
            break
    page.screenshot(path='/workspace/si7_recognized.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,700)''')
    print(f"  URL: {page.url}")
    print(f"  body:\n{body[:500]}")

    print("\n=== 8. XHR ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/app' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','analyz','detect','convers','scan']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:600]}")

    ctx.close(); browser.close()
print("\nDONE")
