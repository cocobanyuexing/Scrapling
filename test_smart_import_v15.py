"""拼图图纸智能导入 v15 - 点'创建项目'完成转换 + 导出 .pbp
样本: /workspace/测试图.jpg
流程: 上传 -> 图片转换 -> MARD -> 创建项目 -> 等进编辑器 -> 导出作品(.pbp)
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'
PBP_OUT_DIR = '/workspace/exports'

def body_head(page, n=800):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

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
            sz = os.path.getsize(save) if os.path.exists(save) else 0
            downloads.append({'path': save, 'filename': fn, 'size': sz})
            print(f"  [download] saved: {save} ({sz} bytes)")
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

    print("\n=== 2. 上传 测试图.jpg ===")
    page.locator('input[type="file"][accept*="image"]').first.set_input_files(IMG)
    page.wait_for_timeout(3500)

    print("\n=== 3. 点 '图片转换' ===")
    page.get_by_text('图片转换', exact=False).first.click(force=True, timeout=10000)
    page.wait_for_timeout(3500)
    page.screenshot(path='/workspace/si15_after_pick_img.png')

    print("\n=== 4. 点 'MARD' (色号范围) ===")
    try:
        page.get_by_text('MARD', exact=False).first.wait_for(state='visible', timeout=15000)
    except: pass
    page.get_by_text('MARD', exact=False).first.click(force=True, timeout=5000)
    page.wait_for_timeout(2000)
    print("  ✓ MARD 已选")
    page.screenshot(path='/workspace/si15_after_mard.png')

    print("\n=== 5. 点 '创建项目' 提交转换 ===")
    # 等按钮出现 + 可点击
    try:
        page.locator('button:has-text("创建项目")').first.wait_for(state='visible', timeout=10000)
    except: pass
    submitted = False
    # 方法 A: page.locator button:has-text (让 Playwright 自己处理 actionability, 不 force)
    try:
        page.locator('button:has-text("创建项目")').first.click(timeout=10000)
        print("  ✓ 方法A: locator click 成功")
        submitted = True
    except Exception as e:
        print(f"  方法A失败: {e}")
    # 方法 B: evaluate 调用 button.click() 原生方法 (会触发 React onClick)
    if not submitted:
        r = page.evaluate('''() => {
            const all = [...document.querySelectorAll('button')];
            const t = all.find(b => (b.innerText||'').trim() === '创建项目');
            if (!t) return {ok: false, reason: 'not_found'};
            // 原生 click() 方法 (会触发 React onClick, 比 dispatchEvent 可靠)
            t.click();
            return {ok: true, tag: t.tagName, disabled: t.disabled};
        }''')
        print(f"  方法B (evaluate button.click): {r}")
        if r.get('ok'): submitted = True
    # 方法 C: get_by_role
    if not submitted:
        try:
            page.get_by_role('button', name='创建项目').click(timeout=5000)
            print("  ✓ 方法C: get_by_role 成功")
            submitted = True
        except Exception as e:
            print(f"  方法C失败: {e}")
    # 方法 D: 键盘 Enter (按钮可能聚焦)
    if not submitted:
        try:
            page.locator('button:has-text("创建项目")').first.focus()
            page.keyboard.press('Enter')
            print("  ✓ 方法D: Enter 键")
            submitted = True
        except Exception as e:
            print(f"  方法D失败: {e}")
    page.wait_for_timeout(4000)
    page.screenshot(path='/workspace/si15_after_submit.png')
    print(f"  body 末尾:\n{body_head(page, 2000)[-1000:]}")

    print("\n=== 6. 等进编辑器 (最长 300s) ===")
    entered_editor = False
    last_url = ''
    for i in range(150):
        page.wait_for_timeout(2000)
        url = page.url
        if url != last_url:
            print(f"  [{i*2}s] URL 变: {url}")
            last_url = url
        if '/editor' in url:
            print(f"  [{i*2}s] ✓ 进编辑器!")
            entered_editor = True
            # 等顶栏渲染
            try:
                page.wait_for_selector('button:has-text("导出作品")', timeout=30000)
                print("  ✓ 编辑器顶栏已渲染")
            except:
                page.wait_for_timeout(8000)
            break
        # 进度
        body = body_head(page, 800)
        if any(k in body for k in ['正在','进度','处理中','识别中','转换中','%','完成','生成中']) and '选择转换模式' not in body:
            if i % 3 == 0:
                prog = page.evaluate('''() => {
                    const all = [...document.querySelectorAll('*')];
                    const t = all.find(e => /\\d+%|进度|正在|处理中|识别中|转换中|生成中/.test(e.innerText||'') && e.children.length < 5);
                    return t ? t.innerText.slice(0,100) : '';
                }''')
                if prog: print(f"  [{i*2}s] 进度: {prog}")
        if i % 10 == 0 and i > 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si15_final.png')
    print(f"  最终 URL: {page.url}")

    if entered_editor:
        print("\n=== 7. 导出 .pbp ===")
        page.screenshot(path='/workspace/si15_in_editor.png')
        # 点 '导出作品'
        try:
            page.get_by_text('导出作品', exact=True).first.click(force=True, timeout=10000)
            print("  ✓ 点了'导出作品'")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  点'导出作品'失败: {e}")
        page.screenshot(path='/workspace/si15_export_modal.png')
        # dump 导出弹窗
        export_modal = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [data-state="open"]')].filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 100 && r.height > 100;
            });
            if (dlgs.length === 0) return {found: false, body_head: document.body.innerText.slice(0,400)};
            const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
            return {
                found: true,
                text: d.innerText.slice(0,1500),
                buttons: [...d.querySelectorAll('button')].map(b => ({
                    text: (b.innerText||'').trim().slice(0,40),
                    aria: b.getAttribute('aria-label')||'',
                    disabled: b.disabled
                })).filter(x => x.text || x.aria)
            };
        }''')
        print(f"  导出弹窗 found: {export_modal.get('found')}")
        if export_modal.get('found'):
            print(f"  弹窗 text:\n{export_modal.get('text','')[:1000]}")
            print(f"  弹窗 buttons:")
            for b in export_modal.get('buttons',[]):
                print(f"    text='{b['text']}' aria='{b['aria']}' disabled={b['disabled']}")

        # 选 .pbp 格式
        for kw in ['pbp', '.pbp', '工程文件', '项目文件', '作品文件', '导出为', 'pbp 工程']:
            try:
                loc = page.get_by_text(kw, exact=False).first
                if loc.count() > 0:
                    loc.click(force=True, timeout=3000)
                    print(f"  ✓ 选了 '{kw}'")
                    page.wait_for_timeout(1500)
                    break
            except: pass
        page.screenshot(path='/workspace/si15_export_picked.png')

        # 点 导出/确认/下载
        for btn_text in ['导出', '确认', '确定', '下载', '保存', 'Export', 'Download', 'Save']:
            try:
                loc = page.get_by_text(btn_text, exact=True).first
                if loc.count() > 0:
                    loc.click(force=True, timeout=5000)
                    print(f"  ✓ 点了 '{btn_text}'")
                    page.wait_for_timeout(5000)
                    break
            except: pass
        page.screenshot(path='/workspace/si15_export_done.png')

        print(f"\n=== 8. 下载文件 ===")
        for d in downloads:
            print(f"  {d}")
        if not downloads:
            print("  没捕获到下载, exports 目录:")
            try:
                for f in os.listdir(PBP_OUT_DIR):
                    print(f"    {f}: {os.path.getsize(os.path.join(PBP_OUT_DIR, f))} bytes")
            except: pass

    print("\n=== 9. console errors ===")
    for m in console_msgs[-10:]:
        print(f"  {m}")

    print("\n=== 10. XHR (识别/导出相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','pixel','image','vision','图纸','export','download','create','project']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:1500]}")

    ctx.close(); browser.close()
print("\nDONE")
