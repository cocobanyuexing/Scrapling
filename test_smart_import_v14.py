"""拼图图纸智能导入 v14 + 导出 .pbp 综合
样本: /workspace/测试图.jpg
流程: 上传 -> 图片转换 -> 选 MARD -> dump 所有按钮找提交 -> 执行转换 -> 等进编辑器
     + 导出 .pbp (用 get_by_text + force click 触发 React onClick)
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'
PBP_OUT_DIR = '/workspace/exports'

def click_leaf(page, text, exact=False, timeout=5000):
    """精准点击: 优先 get_by_text + force click (能触发 React onClick)"""
    try:
        loc = page.get_by_text(text, exact=exact).first
        if loc.count() > 0:
            loc.click(force=True, timeout=timeout)
            return {'ok': True, 'method': 'get_by_text', 'text': text}
    except Exception as e:
        return {'ok': False, 'reason': f'get_by_text err: {e}'}
    # 备选: evaluate dispatchEvent (绕 focus trap, 但 React onClick 可能不触发)
    r = page.evaluate('''(args) => {
        const text = args.text, exact = args.exact;
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

def body_head(page, n=800):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

def list_buttons(page):
    """dump 所有可见按钮(含文字/aria)"""
    return page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].filter(b => {
            const r = b.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        }).map(b => ({
            text: (b.innerText||'').trim().slice(0,40),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            disabled: b.disabled,
            x: Math.round(b.getBoundingClientRect().x),
            y: Math.round(b.getBoundingClientRect().y)
        })).filter(x => (x.text || x.aria || x.title) && !x.disabled);
    }''')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    downloads = []
    def on_download(dl):
        try:
            os.makedirs(PBP_OUT_DIR, exist_ok=True)
            fn = dl.suggested_filename or f'export_{int(time.time())}.pbp'
            save = os.path.join(PBP_OUT_DIR, fn)
            dl.save_as(save)
            downloads.append({'path': save, 'filename': fn, 'size': os.path.getsize(save) if os.path.exists(save) else 0})
            print(f"  [download] saved: {save} ({os.path.getsize(save) if os.path.exists(save) else 0} bytes)")
        except Exception as e:
            downloads.append({'error': str(e)})
            print(f"  [download] err: {e}")
    page.on('download', on_download)

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

    print("\n=== 2. 直接上传 测试图.jpg ===")
    page.locator('input[type="file"][accept*="image"]').first.set_input_files(IMG)
    page.wait_for_timeout(3500)
    print("  ✓ 已上传, '选择转换模式' modal 应已弹出")

    print("\n=== 3. 点 '图片转换' ===")
    click_leaf(page, '图片转换', exact=False)
    page.wait_for_timeout(3500)
    page.screenshot(path='/workspace/si14_after_pick_img.png')

    print("\n=== 4. 点 'MARD' (色号范围) ===")
    # 等 MARD 出现
    try:
        page.get_by_text('MARD', exact=False).first.wait_for(state='visible', timeout=15000)
    except: pass
    click_leaf(page, 'MARD', exact=False)
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/si14_after_mard.png')
    print("  ✓ MARD 已选")

    print("\n=== 5. dump 所有按钮找提交按钮 ===")
    btns = list_buttons(page)
    print(f"  按钮({len(btns)}个):")
    for b in btns:
        print(f"    text='{b['text']}' aria='{b['aria']}' title='{b['title']}' @({b['x']},{b['y']})")

    print("\n=== 6. 找并点击提交按钮 ===")
    # 候选关键词: 开始转换, 转换, 生成, 开始, 确认, 确定, 下一步, 应用, 生成像素画, 转换为像素画
    submitted = False
    for kw in ['开始转换', '转换', '生成像素画', '生成', '开始', '确认', '确定', '下一步', '应用', '转换为', '继续']:
        r = click_leaf(page, kw, exact=False)
        if r.get('ok'):
            print(f"  ✓ 点了 '{kw}': {r}")
            page.wait_for_timeout(3000)
            submitted = True
            break
    if not submitted:
        # 兜底: 找最右下角的按钮(提交按钮通常在 modal 右下)
        if btns:
            sorted_btns = sorted(btns, key=lambda b: (-b['y'], -b['x']))
            for b in sorted_btns[:3]:
                if b['text'] and b['text'] not in ['取消', 'Close', '高级选项', '重置裁剪']:
                    print(f"  尝试点右下角按钮: '{b['text']}'")
                    r = click_leaf(page, b['text'], exact=True)
                    if r.get('ok'):
                        print(f"  ✓ 点了 '{b['text']}'")
                        page.wait_for_timeout(3000)
                        submitted = True
                        break
    page.screenshot(path='/workspace/si14_after_submit.png')
    print(f"  body 末尾:\n{body_head(page, 2000)[-800:]}")

    print("\n=== 7. 等识别 + 进编辑器 (最长 300s) ===")
    entered_editor = False
    last_url = ''
    for i in range(150):
        page.wait_for_timeout(2000)
        url = page.url
        body = body_head(page, 1000)
        if url != last_url:
            print(f"  [{i*2}s] URL 变: {url}")
            last_url = url
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器! URL={url}")
            entered_editor = True
            page.wait_for_timeout(5000)
            break
        # 进度关键词
        if any(k in body for k in ['正在','进度','处理中','识别中','转换中','%','完成']) and '选择转换模式' not in body:
            if i % 3 == 0:
                # dump 进度文字
                prog = page.evaluate('''() => {
                    const all = [...document.querySelectorAll('*')];
                    const t = all.find(e => /\\d+%|进度|正在|处理中|识别中|转换中/.test(e.innerText||'') && e.children.length < 5);
                    return t ? t.innerText.slice(0,100) : '';
                }''')
                if prog: print(f"  [{i*2}s] 进度: {prog}")
        if i % 10 == 0 and i > 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si14_final.png')
    print(f"  最终 URL: {page.url}")
    print(f"  最终 body:\n{body_head(page, 800)}")

    if entered_editor:
        print("\n=== 8. 编辑器中 - 找'导出作品'按钮 ===")
        # 等顶栏按钮
        try:
            page.wait_for_selector('button:has-text("导出作品")', timeout=30000)
            print("  ✓ 编辑器顶栏已渲染")
        except: 
            page.wait_for_timeout(8000)
        page.screenshot(path='/workspace/si14_in_editor.png')

        print("\n=== 9. 点 '导出作品' (用 get_by_text + force click) ===")
        try:
            page.get_by_text('导出作品', exact=True).first.click(force=True, timeout=5000)
            print("  ✓ 点了'导出作品'")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  点击失败: {e}")
        page.screenshot(path='/workspace/si14_export_modal.png')
        # dump 导出弹窗
        export_modal = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [data-state="open"]')].filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 100 && r.height > 100;
            });
            if (dlgs.length === 0) return {found: false};
            const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
            return {
                found: true,
                text: d.innerText.slice(0,1000),
                buttons: [...d.querySelectorAll('button')].map(b => ({
                    text: (b.innerText||'').trim().slice(0,40),
                    aria: b.getAttribute('aria-label')||'',
                    disabled: b.disabled
                })).filter(x => x.text || x.aria)
            };
        }''')
        print(f"  导出弹窗 found: {export_modal.get('found')}")
        if export_modal.get('found'):
            print(f"  弹窗 text:\n{export_modal.get('text','')[:600]}")
            print(f"  弹窗 buttons:")
            for b in export_modal.get('buttons',[]):
                print(f"    text='{b['text']}' aria='{b['aria']}' disabled={b['disabled']}")

        print("\n=== 10. 选 .pbp 格式 + 确认导出 ===")
        # 找含 pbp 的选项
        picked = False
        for kw in ['pbp', '.pbp', '工程文件', '项目文件', '作品文件', '导出为']:
            try:
                loc = page.get_by_text(kw, exact=False).first
                if loc.count() > 0:
                    loc.click(force=True, timeout=3000)
                    print(f"  ✓ 选了 '{kw}'")
                    page.wait_for_timeout(1500)
                    picked = True
                    break
            except: pass
        if not picked:
            # 兜底: evaluate 找
            page.evaluate('''() => {
                const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
                if (dlgs.length === 0) return;
                const d = dlgs[dlgs.length-1];
                const cands = [...d.querySelectorAll('button, [role="option"], [role="radio"], div, li')];
                const t = cands.find(x => /pbp|工程|项目文件/.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
                if (t) t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }''')
            print("  ✓ 兜底选了 .pbp")
            page.wait_for_timeout(1500)
        page.screenshot(path='/workspace/si14_export_picked.png')

        # 点 确认/导出/下载 按钮
        for btn_text in ['导出', '确认', '确定', '下载', '保存', 'Export', 'Download', 'Save']:
            try:
                loc = page.get_by_text(btn_text, exact=True).first
                if loc.count() > 0:
                    loc.click(force=True, timeout=5000)
                    print(f"  ✓ 点了 '{btn_text}' 触发下载")
                    page.wait_for_timeout(5000)
                    break
            except: pass
        page.screenshot(path='/workspace/si14_export_done.png')

        print(f"\n=== 11. 下载文件 ===")
        for d in downloads:
            print(f"  {d}")
        if not downloads:
            print("  没捕获到下载事件, 列出 exports 目录:")
            try:
                for f in os.listdir(PBP_OUT_DIR):
                    print(f"    {f}: {os.path.getsize(os.path.join(PBP_OUT_DIR, f))} bytes")
            except: pass

    print("\n=== 12. console errors ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 13. XHR (识别/导出相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','pixel','image','vision','图纸','export','download']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:1000]}")

    ctx.close(); browser.close()
print("\nDONE")
