"""实测：拼图图纸智能导入 v5 - 逐步截图 + DOM dump
样本: /workspace/测试图.jpg
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

def dump_modal(page, tag):
    """dump modal 结构"""
    info = page.evaluate('''() => {
        // 找 dialog
        const dlg = document.querySelector('[role="dialog"], [data-slot="dialog-content"], [data-slot="dialog"]');
        if (!dlg) return {modal: false};
        const rect = dlg.getBoundingClientRect();
        return {
            modal: true,
            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height},
            text: dlg.innerText.slice(0, 500),
            buttons: [...dlg.querySelectorAll('button')].map(b => ({
                text: (b.innerText||'').trim().slice(0,40),
                aria: b.getAttribute('aria-label')||'',
                classes: (b.className||'').slice(0,80)
            })).filter(b => b.text || b.aria),
            inputs: [...dlg.querySelectorAll('input')].map(i => ({
                type: i.type, accept: i.accept||'', visible: i.offsetParent !== null
            })),
            // 找可点选项卡片
            cards: [...dlg.querySelectorAll('[role="option"], [role="button"], [class*="cursor-pointer"], [class*="card"]')].map(c => ({
                text: (c.innerText||'').trim().slice(0,60),
                role: c.getAttribute('role')||'',
                classes: (c.className||'').slice(0,60)
            })).filter(c => c.text).slice(0, 20)
        };
    }''')
    print(f"\n  [{tag}] modal: {info.get('modal')}")
    if info.get('modal'):
        print(f"  rect: {info['rect']}")
        print(f"  text: {info['text'][:300]}")
        print(f"  buttons ({len(info['buttons'])}): {[b['text'] or b['aria'] for b in info['buttons']]}")
        print(f"  inputs: {info['inputs']}")
        print(f"  cards ({len(info['cards'])}): {[(c['text'][:30], c['role']) for c in info['cards']]}")
    return info

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

    print("\n=== 1. 进 create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)

    print("\n=== 2. 开下拉, 点'导入拼豆图纸生成' ===")
    page.evaluate('''() => {
        const btns = [...document.querySelectorAll('button')];
        const t = btns.find(b => (b.innerText||'').trim() === '新建' || (b.innerText||'').trim() === '创建');
        if (t) t.click();
    }''')
    page.wait_for_timeout(1500)
    # 点下拉项
    page.locator('text=导入拼豆图纸生成').first.click(timeout=5000)
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/si5_step1.png')
    dump_modal(page, 'step1-选模式')

    print("\n=== 3. 点 MARD 视觉识别 卡片 ===")
    # 不点 text, 点 modal 内 role=option 或 role=button
    mard = page.locator('[role="dialog"] [role="option"]:has-text("MARD"), [role="dialog"] [role="button"]:has-text("MARD"), [role="dialog"] button:has-text("MARD")').first
    if mard.count() == 0:
        # fallback: 找含 MARD 的可点元素
        mard = page.locator('[role="dialog"] :is(div, button, [role="button"]):has-text("MARD 视觉识别")').first
    print(f"  MARD 元素 count: {mard.count()}")
    if mard.count() > 0:
        mard.click(timeout=5000)
        print("  ✓ 点 MARD")
    else:
        print("  ❌ 没找到 MARD 卡片, 试其他方式")
        page.evaluate('''() => {
            const dlg = document.querySelector('[role="dialog"]');
            if (!dlg) return;
            const els = [...dlg.querySelectorAll('*')].filter(e => (e.innerText||'').includes('MARD 视觉识别') && e.children.length < 5);
            if (els[0]) els[0].click();
        }''')
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si5_step2_after_mard.png')
    dump_modal(page, 'step2-MARD后')

    print("\n=== 4. 如有上传 input, 上传 测试图.jpg ===")
    info = page.evaluate('''() => {
        const dlg = document.querySelector('[role="dialog"]');
        if (!dlg) return null;
        const inp = dlg.querySelector('input[type="file"]');
        return inp ? {accept: inp.accept, visible: inp.offsetParent !== null} : null;
    }''')
    print(f"  modal 内 file input: {info}")
    if info:
        page.locator('[role="dialog"] input[type="file"]').first.set_input_files(IMG)
        print(f"  ✓ 上传 {os.path.basename(IMG)}")
        # 等识别
        for i in range(60):
            page.wait_for_timeout(2000)
            url = page.url
            body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
            if '/editor' in url:
                print(f"  [{i*2}s] 进编辑器!")
                break
            if '识别' in body and ('失败' in body or '成功' in body or '色号' in body or '网格' in body):
                print(f"  [{i*2}s] 识别结果出现")
                break
        page.wait_for_timeout(3000)
        page.screenshot(path='/workspace/si5_step3_recognized.png')
        dump_modal(page, 'step3-识别后')
        print(f"  URL: {page.url}")

    print("\n=== 5. XHR ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/app' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','analyz','detect','convers','scan']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 20:
                print(f"    body: {x['body'][:500]}")

    ctx.close(); browser.close()
print("\nDONE")
