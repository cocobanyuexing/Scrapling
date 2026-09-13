"""拼图图纸智能导入 v13 - 直接上传触发 + 精准点击
样本: /workspace/测试图.jpg
流程: 上传图片 -> '选择转换模式' modal -> '图片转换' -> 下一步 -> 'MARD 视觉识别' -> 等识别
关键改进: 1) 不点'新建', 直接上传触发流程
         2) 用 get_by_text(exact=True).click(force=True) 精准点叶子元素
         3) 用 querySelector 找 button/role=menuitem 的叶子节点
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

def click_leaf(page, text, exact=True, timeout=5000):
    """精准点击叶子元素: 优先 button/role=menuitem/role=radio, 用 get_by_text + force=True"""
    # 方案 A: get_by_text (Playwright 原生, 精准)
    try:
        loc = page.get_by_text(text, exact=exact).first
        if loc.count() > 0:
            loc.click(force=True, timeout=timeout)
            return {'ok': True, 'method': 'get_by_text', 'text': text}
    except Exception as e:
        pass
    # 方案 B: evaluate 找 button/role=menuitem/role=radio 等叶子, dispatchEvent
    r = page.evaluate('''(args) => {
        const text = args.text;
        const exact = args.exact;
        const sel = 'button, [role="menuitem"], [role="radio"], [role="option"], [role="tab"], a';
        const all = [...document.querySelectorAll(sel)];
        const match = all.find(el => {
            const t = (el.innerText||'').trim();
            const al = el.getAttribute('aria-label')||'';
            if (exact) return t === text || al === text;
            return t.includes(text) || al.includes(text);
        });
        if (!match) return {ok: false, reason: 'not_found_in_leaf'};
        try {
            match.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}));
            match.dispatchEvent(new PointerEvent('pointerup', {bubbles: true}));
        } catch(e){}
        match.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
        match.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
        match.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        return {ok: true, method: 'evaluate', tag: match.tagName, text: (match.innerText||'').trim().slice(0,40)};
    }''', {'text': text, 'exact': exact})
    return r

def body_head(page, n=600):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

def list_text_blocks(page):
    return page.evaluate('''() => {
        const all = [...document.querySelectorAll('button, [role="menuitem"], [role="radio"], [role="option"], [role="tab"], li, label, h1, h2, h3, p, span')];
        const leaves = all.filter(e => {
            const t = (e.innerText||'').trim();
            const r = e.getBoundingClientRect();
            return t.length >= 2 && t.length <= 200 && r.width > 0 && r.height > 0;
        });
        const seen = new Set();
        const out = [];
        for (const e of leaves) {
            const t = (e.innerText||'').trim().slice(0,80);
            if (!seen.has(t) && t) { seen.add(t); out.push(t); }
        }
        return out.slice(0, 80);
    }''')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:5000]
            except: body='<err>'
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body})
    page.on('response', on_response)
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text[:200]}'))

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => {
            const t = (b.innerText||'').trim();
            return t === '登录' || t === '登入';
        });
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
    print(f"  登录后 URL: {page.url}")

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(4000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    print(f"  URL: {page.url}")

    print("\n=== 2. 直接上传 测试图.jpg 触发流程 ===")
    # 找 image file input 上传
    inp = page.locator('input[type="file"][accept*="image"]').first
    inp.set_input_files(IMG)
    print("  ✓ 已上传图片")
    page.wait_for_timeout(3500)
    page.screenshot(path='/workspace/si13_after_upload.png')
    print(f"  body 末尾 600 字符:\n{body_head(page, 3000)[-1500:]}")

    print("\n=== 3. dump 当前文字块(确认'选择转换模式' modal 出现) ===")
    blocks = list_text_blocks(page)
    print(f"  文字块({len(blocks)}个):")
    for b in blocks:
        print(f"    {b}")

    print("\n=== 4. 点 '图片转换' ===")
    # 等文字出现
    try:
        page.get_by_text('图片转换', exact=False).first.wait_for(state='visible', timeout=10000)
    except: pass
    r = click_leaf(page, '图片转换', exact=False)
    print(f"  结果: {r}")
    page.wait_for_timeout(3500)
    page.screenshot(path='/workspace/si13_after_pick_img.png')
    blocks = list_text_blocks(page)
    print(f"  点击后文字块({len(blocks)}个):")
    for b in blocks[:30]:
        print(f"    {b}")

    print("\n=== 5. 找 'MARD 视觉识别' ===")
    # 等文字出现
    try:
        page.get_by_text('MARD', exact=False).first.wait_for(state='visible', timeout=15000)
        print("  ✓ MARD 文字已出现")
    except Exception as e:
        print(f"  等 MARD 超时: {e}")
    # dump 当前文字块
    blocks = list_text_blocks(page)
    print(f"  当前文字块:")
    for b in blocks[:40]:
        print(f"    {b}")
    r = click_leaf(page, 'MARD', exact=False)
    print(f"  点 MARD 结果: {r}")
    # 备选: 视觉识别
    if not r.get('ok'):
        r = click_leaf(page, '视觉识别', exact=False)
        print(f"  点'视觉识别'结果: {r}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si13_after_mard.png')
    blocks = list_text_blocks(page)
    print(f"  选 MARD 后文字块:")
    for b in blocks[:40]:
        print(f"    {b}")

    print("\n=== 6. 找 '下一步'/'确认' 按钮进入上传/识别 ===")
    for btn_text in ['下一步', '确认', '确定', '继续', 'Next', 'Confirm', 'Continue', '开始', '上传图片', '开始识别']:
        r = click_leaf(page, btn_text, exact=False)
        if r.get('ok'):
            print(f"  ✓ 点了 '{btn_text}': {r}")
            page.wait_for_timeout(2500)
            break
    page.screenshot(path='/workspace/si13_after_next.png')
    blocks = list_text_blocks(page)
    print(f"  下一步后文字块:")
    for b in blocks[:40]:
        print(f"    {b}")
    # 看是否需要再上传一次(下一步可能要求选文件)
    file_info = page.evaluate('''() => {
        return [...document.querySelectorAll('input[type="file"]')].map((i, idx) => ({
            idx, accept: i.accept||'', visible: i.offsetParent !== null
        }));
    }''')
    print(f"  file inputs: {file_info}")
    vis_inp = [f for f in file_info if f['visible'] and ('image' in f['accept'] or f['accept']=='')]
    if vis_inp:
        try:
            page.locator('input[type="file"]').nth(vis_inp[0]['idx']).set_input_files(IMG)
            print(f"  ✓ 再次上传到 visible 第 {vis_inp[0]['idx']} 个 input")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  再次上传失败: {e}")

    print("\n=== 7. 等识别 (最长 240s) ===")
    recognized = False
    last_url = ''
    for i in range(120):
        page.wait_for_timeout(2000)
        url = page.url
        body = body_head(page, 1000)
        if url != last_url:
            print(f"  [{i*2}s] URL 变: {url}")
            last_url = url
        if '/editor' in url or ('/workspace' in url and '/create' not in url):
            print(f"  [{i*2}s] ✓ 进编辑器! URL={url}")
            recognized = True
            page.wait_for_timeout(5000)
            break
        # 关键词
        kws_found = [k for k in ['识别完成','识别成功','色号','网格','创建项目','导入成功','分析完成','正在识别','识别中','进度','处理中','MARD','转换中','处理完成','裁剪','分割'] if k in body]
        if kws_found and '选择转换模式' not in body:
            print(f"  [{i*2}s] 识别关键词: {kws_found}")
            recognized = True
            # 继续等进入编辑器, 不break
        if i % 5 == 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si13_final.png')
    body_final = body_head(page, 800)
    print(f"  最终 URL: {page.url}")
    print(f"  最终 body:\n{body_final[:700]}")

    print("\n=== 8. console errors ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 9. XHR (识别相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','pixel','image','vision','图纸','preprocess','palette','quantiz']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:1500]}")

    ctx.close(); browser.close()
print("\nDONE")
