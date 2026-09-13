"""拼图图纸智能导入 v12 - 精准流程
样本: /workspace/测试图.jpg
真实流程: 点'新建' -> '导入拼豆图纸生成' -> '选择转换模式'(图片转换) -> 'MARD 视觉识别' -> 上传 -> 识别
策略: 每步用 evaluate 直接 get_by_text 定位元素 + dispatchEvent click, 不依赖复杂 modal 选择器
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

def click_text(page, text, exact=False, timeout_ms=3000):
    """用 evaluate 在 DOM 找含指定文字的元素并 dispatchEvent click(绕过 focus trap)"""
    return page.evaluate('''(args) => {
        const text = args.text;
        const exact = args.exact;
        const all = [...document.querySelectorAll('button, [role="button"], [role="radio"], [role="option"], [role="menuitem"], a, div, li, label, span')];
        const match = all.find(el => {
            const t = (el.innerText||'').trim();
            const al = el.getAttribute('aria-label')||'';
            if (exact) return t === text || al === text;
            return t.includes(text) || al.includes(text);
        });
        if (!match) return {ok: false, reason: 'not_found'};
        // 多事件触发(React/Radix 受控组件)
        try {
            match.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}));
            match.dispatchEvent(new PointerEvent('pointerup', {bubbles: true}));
        } catch(e){}
        match.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
        match.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
        match.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        return {ok: true, text: (match.innerText||'').trim().slice(0,60), tag: match.tagName};
    }''', {'text': text, 'exact': exact})

def body_head(page, n=600):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

def list_text_blocks(page):
    """dump body 里所有文字块, 用于看 modal 切换"""
    return page.evaluate('''() => {
        const all = [...document.querySelectorAll('div, section, article, ul, li, button, [role="dialog"], [data-slot]')];
        // 收集 innerText 长度 5-300 且 children 为 0 或少量 的元素(叶子文字)
        const leaves = all.filter(e => {
            const t = (e.innerText||'').trim();
            const r = e.getBoundingClientRect();
            return t.length >= 2 && t.length <= 200 && r.width > 0 && r.height > 0 && e.children.length <= 2;
        });
        // 去重并截短
        const seen = new Set();
        const out = [];
        for (const e of leaves) {
            const t = (e.innerText||'').trim().slice(0,80);
            if (!seen.has(t) && t) { seen.add(t); out.push(t); }
        }
        return out.slice(0, 60);
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

    print("\n=== 2. 点 '新建' 按钮 ===")
    r = click_text(page, '新建', exact=True)
    print(f"  结果: {r}")
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/si12_after_new.png')
    print(f"  body:\n{body_head(page, 600)}")

    print("\n=== 3. 点 '导入拼豆图纸生成' ===")
    r = click_text(page, '导入拼豆图纸生成', exact=False)
    print(f"  结果: {r}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si12_after_puzzle_import.png')
    print(f"  body:\n{body_head(page, 600)}")
    # dump 当前文字块
    blocks = list_text_blocks(page)
    print(f"  文字块: {blocks[:30]}")

    print("\n=== 4. 点 '图片转换' ===")
    r = click_text(page, '图片转换', exact=False)
    print(f"  结果: {r}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si12_after_pick_img.png')
    print(f"  body:\n{body_head(page, 600)}")
    blocks = list_text_blocks(page)
    print(f"  文字块: {blocks[:30]}")

    print("\n=== 5. 找 'MARD 视觉识别' ===")
    # 先 dump 文字块看是否有 MARD
    blocks_before = list_text_blocks(page)
    print(f"  当前文字块: {blocks_before[:30]}")
    r = click_text(page, 'MARD', exact=False)
    print(f"  点 MARD 结果: {r}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si12_after_mard.png')
    print(f"  body:\n{body_head(page, 600)}")
    blocks = list_text_blocks(page)
    print(f"  文字块: {blocks[:30]}")

    # 如果 MARD 没找到, 试找'视觉识别' 或 'MARD 视觉'
    if not r.get('ok'):
        for kw in ['视觉识别', '视觉', 'vision', 'recogni']:
            r2 = click_text(page, kw, exact=False)
            if r2.get('ok'):
                print(f"  ✓ 用 '{kw}' 找到并点了: {r2}")
                page.wait_for_timeout(3000)
                break
        page.screenshot(path='/workspace/si12_after_mard_alt.png')
        print(f"  body:\n{body_head(page, 600)}")

    print("\n=== 6. 点 '下一步'/'确认' ===")
    for btn_text in ['下一步', '确认', '确定', '继续', 'Next', 'Confirm', 'Continue', '开始', '上传图片']:
        r = click_text(page, btn_text, exact=False)
        if r.get('ok'):
            print(f"  ✓ 点了 '{btn_text}': {r}")
            page.wait_for_timeout(2500)
            break
    page.screenshot(path='/workspace/si12_after_next.png')
    print(f"  body:\n{body_head(page, 600)}")

    print("\n=== 7. 上传 测试图.jpg ===")
    # dump 所有 file input 信息
    file_info = page.evaluate('''() => {
        return [...document.querySelectorAll('input[type="file"]')].map((i, idx) => ({
            idx, accept: i.accept||'', multiple: i.multiple,
            visible: i.offsetParent !== null,
            parent_text: (i.parentElement?.innerText||'').trim().slice(0,60)
        }));
    }''')
    print(f"  file inputs: {file_info}")
    uploaded = False
    # 优先 visible 的
    for i, info in enumerate(file_info):
        if info['visible'] and ('image' in info['accept'] or info['accept']==''):
            try:
                page.locator('input[type="file"]').nth(i).set_input_files(IMG)
                print(f"  ✓ 上传到第 {i} 个 input")
                uploaded = True
                break
            except Exception as e:
                print(f"  第{i}个失败: {e}")
    if not uploaded:
        # 兜底
        for i, info in enumerate(file_info):
            try:
                page.locator('input[type="file"]').nth(i).set_input_files(IMG)
                print(f"  ✓ 兜底上传到第 {i} 个 input")
                uploaded = True
                break
            except Exception as e:
                pass
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si12_after_upload.png')
    print(f"  上传后 body:\n{body_head(page, 600)}")

    print("\n=== 8. 等识别 (最长 180s) ===")
    recognized = False
    for i in range(90):
        page.wait_for_timeout(2000)
        url = page.url
        body = body_head(page, 800)
        if '/editor' in url or ('/workspace' in url and '/create' not in url):
            print(f"  [{i*2}s] ✓ 进编辑器! URL={url}")
            recognized = True
            page.wait_for_timeout(5000)
            break
        # 关键词
        if any(k in body for k in ['识别完成','识别成功','色号','网格','创建项目','导入成功','分析完成','MARD','正在识别','识别中','进度']) and '选择转换模式' not in body and '新建空白' not in body:
            print(f"  [{i*2}s] 识别关键词出现: {[k for k in ['识别完成','识别成功','色号','网格','创建项目','导入成功','分析完成','MARD','正在识别','识别中','进度'] if k in body]}")
            recognized = True
            # 不break, 继续等进入编辑器
        if i % 5 == 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si12_final.png')
    body_final = body_head(page, 800)
    print(f"  最终 URL: {page.url}")
    print(f"  最终 body:\n{body_final[:700]}")

    print("\n=== 9. console errors ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 10. XHR (识别相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','pixel','image','vision','图纸','preprocess']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:1000]}")

    ctx.close(); browser.close()
print("\nDONE")
