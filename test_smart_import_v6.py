"""实测：拼图图纸智能导入 v6 - 直接触发 z input + 按文本定位 modal
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

    print("\n=== 2. 直接触发 smartImport 的 z input (第3个 image input) ===")
    # z = 第3个 input[accept*="image"]
    img_inps = page.locator('input[type="file"][accept*="image"]')
    n = img_inps.count()
    print(f"  image input 数: {n}")
    # 第3个 (index 2) 是 z = smartImport
    img_inps.nth(2).set_input_files(IMG)
    print(f"  ✓ 设文件到 z input (index 2)")
    page.wait_for_timeout(3000)

    # 现在用文本定位 modal 容器
    print("\n=== 3. 找 SmartImportModal 容器 ===")
    modal_info = page.evaluate('''() => {
        // 找含 "选择导入方式" 的元素, 向上找容器
        const all = [...document.querySelectorAll('*')];
        const target = all.find(e => (e.innerText||'').includes('选择导入方式') && e.children.length < 50);
        if (!target) return {found: false};
        // 向上找最近的带 dialog 特征的容器
        let container = target;
        for (let i = 0; i < 15; i++) {
            if (!container.parentElement) break;
            container = container.parentElement;
            const cls = container.className || '';
            const role = container.getAttribute('role') || '';
            const slot = container.getAttribute('data-slot') || '';
            if (/dialog|modal|overlay|portal/i.test(cls + role + slot) || container.getAttribute('aria-modal') === 'true') break;
        }
        const rect = container.getBoundingClientRect();
        return {
            found: true,
            container_tag: container.tagName,
            container_class: (container.className||'').slice(0,100),
            container_role: container.getAttribute('role'),
            container_slot: container.getAttribute('data-slot'),
            container_aria_modal: container.getAttribute('aria-modal'),
            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height},
            text: container.innerText.slice(0, 400),
            buttons: [...container.querySelectorAll('button')].map(b => ({
                text: (b.innerText||'').trim().slice(0,40),
                aria: b.getAttribute('aria-label')||''
            })).filter(b => b.text || b.aria),
            options: [...container.querySelectorAll('[role="option"], [role="button"], [class*="cursor-pointer"], [data-slot="radio-group-item"]')].map(c => ({
                text: (c.innerText||'').trim().slice(0,50),
                role: c.getAttribute('role')||'',
                slot: c.getAttribute('data-slot')||''
            })).filter(o => o.text).slice(0, 15)
        };
    }''')
    print(f"  found: {modal_info.get('found')}")
    if modal_info.get('found'):
        print(f"  container: <{modal_info['container_tag']} class={modal_info['container_class'][:60]} role={modal_info['container_role']} slot={modal_info['container_slot']}>")
        print(f"  rect: {modal_info['rect']}")
        print(f"  text: {modal_info['text'][:300]}")
        print(f"  buttons: {[b['text'] or b['aria'] for b in modal_info['buttons']]}")
        print(f"  options: {[(o['text'][:30], o['role'], o['slot']) for o in modal_info['options']]}")

    page.screenshot(path='/workspace/si6_modal.png')

    print("\n=== 4. 点 MARD 视觉识别 ===")
    # 用 Playwright 的 has-text 在全页找, 限制在 modal 容器内
    clicked = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        // 找含 "MARD 视觉识别" 且是可点击卡片(不是大容器)的元素
        const candidates = all.filter(e => {
            const t = (e.innerText||'').trim();
            return t === 'MARD 视觉识别' || (t.includes('MARD 视觉识别') && t.length < 80 && e.children.length < 8);
        });
        // 找最内层的(文字本身或最近的小容器)
        const target = candidates.sort((a,b) => (a.innerText||'').length - (b.innerText||'').length)[0];
        if (target) {
            // 向上找可点击的
            let clickTarget = target;
            for (let i = 0; i < 5; i++) {
                if (!clickTarget.parentElement) break;
                const cls = clickTarget.className || '';
                if (/cursor-pointer|clickable|card|option|button/i.test(cls)) break;
                clickTarget = clickTarget.parentElement;
            }
            clickTarget.click();
            return clickTarget.innerText.trim().slice(0, 60);
        }
        return null;
    }''')
    print(f"  点 MARD: {clicked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si6_after_mard.png')

    # 再 dump modal
    modal2 = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        const target = all.find(e => (e.innerText||'').includes('导入拼豆图纸') && e.children.length < 50);
        if (!target) return {found: false, body: document.body.innerText.slice(0, 300)};
        return {found: true, text: target.innerText.slice(0, 400)};
    }''')
    print(f"  modal2: {modal2}")

    print("\n=== 5. 找上传 input ===")
    file_info = page.evaluate('''() => {
        const inps = [...document.querySelectorAll('input[type="file"]')];
        return inps.map((i, idx) => ({
            idx, accept: i.accept||'',
            visible: i.offsetParent !== null,
            in_smart_modal: !!i.closest('[class*="modal"], [class*="dialog"], [data-slot*="dialog"]')
        }));
    }''')
    print(f"  file inputs: {file_info}")
    # 找 modal 内或最后出现的 image input
    modal_inp = page.locator('input[type="file"][accept*="image"]').last
    modal_inp.set_input_files(IMG)
    print(f"  ✓ 上传到最后 image input")

    # 等识别
    print("\n=== 6. 等待识别 ===")
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            break
        if any(k in body for k in ['识别失败','无法识别','色号','网格','创建项目','完成','识别完成','识别成功']) and '选择导入方式' not in body:
            print(f"  [{i*2}s] 识别完成")
            page.wait_for_timeout(3000)
            break
    page.screenshot(path='/workspace/si6_recognized.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,700)''')
    print(f"  URL: {page.url}")
    print(f"  body:\n{body}")

    print("\n=== 7. XHR ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/app' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','import','upload','analyz','detect','convers','scan']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:600]}")

    ctx.close(); browser.close()
print("\nDONE")
