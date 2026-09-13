"""综合测试: 后处理算法弹窗 + 导出 .pbp
流程: 登录 -> 导入 .pbp -> 编辑器 -> 后处理(去杂色/降噪/色号合并) -> 应用 -> 导出 .pbp -> 验证
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP_IN = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'
PBP_OUT_DIR = '/workspace/exports'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    # 下载拦截: 捕获 .pbp 导出文件
    downloads = []
    def on_download(dl):
        try:
            os.makedirs(PBP_OUT_DIR, exist_ok=True)
            fn = dl.suggested_filename or f'export_{int(time.time())}.pbp'
            save = os.path.join(PBP_OUT_DIR, fn)
            dl.save_as(save)
            downloads.append({'path': save, 'filename': fn, 'size': os.path.getsize(save) if os.path.exists(save) else 0})
            print(f"  [download] saved: {save}")
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

    print("\n=== 1. 导入 .pbp 进编辑器 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.locator('input[type="file"][accept=".pbp"]').first.set_input_files(PBP_IN)
    # 等待跳转到 /editor (最长 30s)
    try:
        page.wait_for_url('**/editor**', timeout=30000)
    except: pass
    page.wait_for_timeout(3000)
    # 等待顶栏按钮出现 (编辑器顶栏应有 '导出作品' 等按钮)
    try:
        page.wait_for_selector('button:has-text("导出作品")', timeout=30000)
        print("  ✓ 编辑器顶栏已渲染")
    except Exception as e:
        print(f"  等顶栏按钮超时: {e}")
        # 再等久点
        page.wait_for_timeout(8000)
    print(f"  导入后 URL: {page.url}")
    page.screenshot(path='/workspace/pp_v2_after_import.png')

    # 记录初始色号数 (用于算法生效对比)
    initial_colors = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        const colorEls = all.filter(e => /^[A-Z]\\d+$/.test((e.innerText||'').trim()) && e.children.length === 0);
        return colorEls.map(e => (e.innerText||'').trim());
    }''')
    print(f"  初始色号样本({len(initial_colors)}个): {initial_colors[:15]}")

    print("\n=== 2. dump 所有顶栏按钮(找后处理入口) ===")
    all_btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].filter(b => {
            const r = b.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        }).map(b => ({
            text: (b.innerText||'').trim().slice(0,40),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            cls: (b.className||'').toString().slice(0,100),
            x: Math.round(b.getBoundingClientRect().x),
            y: Math.round(b.getBoundingClientRect().y),
        })).filter(x => x.text || x.aria || x.title);
    }''')
    postproc_btns = [b for b in all_btns if any(k in (b['text']+b['aria']+b['title']) for k in ['色号合并','去除杂色','降噪','合并','杂色','降噪','denoise','merge','noise','stray','cleanup','去杂','杂色','噪','清'])]
    print(f"  全部按钮: {len(all_btns)}, 后处理相关: {len(postproc_btns)}")
    for b in postproc_btns:
        print(f"    text='{b['text']}' aria='{b['aria']}' title='{b['title']}' cls='{b['cls'][:60]}' @({b['x']},{b['y']})")
    # 也 dump 顶栏所有按钮(便于发现入口)
    print("  --- 顶栏所有按钮(text非空) ---")
    for b in all_btns:
        if b['text']:
            print(f"    '{b['text']}' @({b['x']},{b['y']})")

    print("\n=== 3. 依次点击 色号合并/去除杂色/降噪 测试弹窗 ===")
    target_keywords = [
        ('色号合并', ['色号合并','合并']),
        ('去除杂色', ['去除杂色','去杂色','杂色']),
        ('降噪', ['降噪','噪','denoise']),
    ]
    dialog_results = {}
    for name, kws in target_keywords:
        target = None
        for b in postproc_btns:
            s = b['text'] + b['aria'] + b['title']
            if any(k in s for k in kws):
                target = b; break
        if not target:
            # 兜底: 全部按钮里再找
            for b in all_btns:
                s = b['text'] + b['aria'] + b['title']
                if any(k in s for k in kws):
                    target = b; break
        if not target:
            print(f"\n  [{name}] 没找到对应按钮")
            continue
        print(f"\n  [{name}] 找到按钮: text='{target['text']}' aria='{target['aria']}'")
        # 关掉之前的弹窗
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
        # 点击 (用 evaluate dispatchEvent 绕开 focus trap)
        try:
            page.evaluate('''(b) => {
                const all = [...document.querySelectorAll('button, [role="button"]')];
                const t = all.find(x => (x.innerText||'').trim() === b.text || x.getAttribute('aria-label') === b.aria);
                if (t) {
                    t.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                }
            }''', target)
            page.wait_for_timeout(2500)
        except Exception as e:
            print(f"    click 失败: {e}")
            # force click 兜底
            try:
                page.get_by_text(target['text'] or target['aria'], exact=False).first.click(force=True, timeout=3000)
                page.wait_for_timeout(2500)
            except: pass
        page.screenshot(path=f'/workspace/pp_v2_{name}_dialog.png')
        # dump 弹窗内容
        dlg = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
            if (dlgs.length === 0) return {found: false, body_head: document.body.innerText.slice(0,300)};
            const d = dlgs[dlgs.length-1];
            return {
                found: true,
                text: d.innerText.slice(0,600),
                buttons: [...d.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t),
                radios: [...d.querySelectorAll('[role="radio"], [role="option"]')].map(r => ({
                    label: r.getAttribute('aria-label') || (r.innerText||'').trim().slice(0,40),
                    checked: r.getAttribute('aria-checked') === 'true'
                })),
                sliders: [...d.querySelectorAll('input[type="range"], [role="slider"]')].map(s => ({
                    label: s.getAttribute('aria-label')||'',
                    value: s.value || s.getAttribute('aria-valuenow') || ''
                }))
            };
        }''')
        print(f"    弹窗 found: {dlg.get('found')}")
        if dlg.get('found'):
            print(f"    text:\n{dlg.get('text','')[:400]}")
            if dlg.get('buttons'): print(f"    buttons: {dlg['buttons']}")
            if dlg.get('radios'): 
                print(f"    radios:")
                for r in dlg['radios']: print(f"      {r}")
            if dlg.get('sliders'): print(f"    sliders: {dlg['sliders']}")
        dialog_results[name] = dlg

    print("\n=== 4. 测试一个预设 + 应用 (以去除杂色为例) ===")
    # 先确保 去除杂色 弹窗打开
    target = None
    for b in postproc_btns:
        if any(k in b['text']+b['aria']+b['title'] for k in ['去除杂色','去杂色','杂色']):
            target = b; break
    if target:
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
        try:
            page.evaluate('''(b) => {
                const all = [...document.querySelectorAll('button, [role="button"]')];
                const t = all.find(x => (x.innerText||'').trim() === b.text || x.getAttribute('aria-label') === b.aria);
                if (t) t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }''', target)
            page.wait_for_timeout(2500)
        except: pass
        # 选 strong 预设
        presets = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
            if (dlgs.length === 0) return [];
            const d = dlgs[dlgs.length-1];
            const cands = [...d.querySelectorAll('[role="radio"], [role="option"], button')];
            return cands.map(c => ({
                text: (c.innerText||'').trim().slice(0,40),
                aria: c.getAttribute('aria-label')||''
            })).filter(x => x.text || x.aria);
        }''')
        print(f"  预设选项: {presets}")
        # 尝试选 strong/强
        for kw in ['strong','强','aggressive','激进','balanced','平衡','light','轻']:
            ok = page.evaluate('''(kw) => {
                const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
                if (dlgs.length === 0) return false;
                const d = dlgs[dlgs.length-1];
                const cands = [...d.querySelectorAll('[role="radio"], [role="option"], button, div')];
                const t = cands.find(x => {
                    const s = (x.innerText||'') + (x.getAttribute('aria-label')||'');
                    return s.toLowerCase().includes(kw.toLowerCase()) || s.includes(kw);
                });
                if (t) {
                    t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    return (t.innerText||'').trim();
                }
                return false;
            }''', kw)
            if ok:
                print(f"  ✓ 选了预设: '{ok}' (匹配 kw='{kw}')")
                page.wait_for_timeout(1000)
                break
        # 点 应用/确认
        applied = False
        for btn_text in ['应用','确认','确定','执行','Apply','Confirm','开始']:
            ok = page.evaluate('''(t) => {
                const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
                if (dlgs.length === 0) return false;
                const d = dlgs[dlgs.length-1];
                const btn = [...d.querySelectorAll('button')].find(b => (b.innerText||'').trim() === t);
                if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); return true; }
                return false;
            }''', btn_text)
            if ok:
                print(f"  ✓ 点了 '{btn_text}' 执行算法")
                page.wait_for_timeout(4000)
                applied = True
                break
        if not applied:
            print("  没找到应用按钮")
        page.screenshot(path='/workspace/pp_v2_after_apply.png')
        # 对比色号变化
        after_colors = page.evaluate('''() => {
            const all = [...document.querySelectorAll('*')];
            const colorEls = all.filter(e => /^[A-Z]\\d+$/.test((e.innerText||'').trim()) && e.children.length === 0);
            return colorEls.map(e => (e.innerText||'').trim());
        }''')
        print(f"  应用后色号样本({len(after_colors)}个): {after_colors[:15]}")
        print(f"  色号数变化: {len(initial_colors)} -> {len(after_colors)}")
        # dump toast
        toast = page.evaluate('''() => {
            const t = document.querySelector('[class*="toast" i], [role="alert"], [class*="notification" i]');
            return t ? t.innerText.slice(0,200) : '';
        }''')
        if toast: print(f"  toast: {toast}")

    print("\n=== 5. 导出 .pbp ===")
    # 找 导出作品 按钮
    export_btn = None
    for b in all_btns:
        s = b['text'] + b['aria'] + b['title']
        if any(k in s for k in ['导出作品','导出','Export','export']):
            export_btn = b; break
    if not export_btn:
        # 再扫一次
        all_btns = page.evaluate('''() => [...document.querySelectorAll('button, [role="button"]')].filter(b => b.getBoundingClientRect().width>0).map(b => ({text:(b.innerText||'').trim().slice(0,40), aria:b.getAttribute('aria-label')||'', title:b.getAttribute('title')||''}))''')
        for b in all_btns:
            s = b['text']+b['aria']+b['title']
            if any(k in s for k in ['导出','Export']):
                export_btn = b; break
    if export_btn:
        print(f"  找到导出按钮: text='{export_btn['text']}' aria='{export_btn['aria']}'")
        # 关掉任何弹窗
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
        try:
            page.evaluate('''(b) => {
                const all = [...document.querySelectorAll('button, [role="button"]')];
                const t = all.find(x => (x.innerText||'').trim() === b.text || x.getAttribute('aria-label') === b.aria);
                if (t) t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }''', export_btn)
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  点击失败: {e}")
        page.screenshot(path='/workspace/pp_v2_export_modal.png')
        # dump 导出弹窗
        export_modal = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
            if (dlgs.length === 0) return {found: false};
            const d = dlgs[dlgs.length-1];
            return {
                found: true,
                text: d.innerText.slice(0,500),
                buttons: [...d.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t),
                has_pbp: !!d.querySelector('input[type="file"]') || /pbp/.test(d.innerText||'')
            };
        }''')
        print(f"  导出弹窗: {json.dumps(export_modal, ensure_ascii=False)[:500]}")
        # 找 .pbp 选项并点
        ok = page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
            if (dlgs.length === 0) return false;
            const d = dlgs[dlgs.length-1];
            const cands = [...d.querySelectorAll('button, [role="option"], [role="radio"], div, li')];
            const t = cands.find(x => /pbp|工程|项目文件|作品|像素画/.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
            if (t) {
                t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                return (t.innerText||'').trim().slice(0,40);
            }
            return false;
        }''')
        if ok:
            print(f"  ✓ 选了导出格式: '{ok}'")
            page.wait_for_timeout(1500)
        # 找 确认/导出 按钮触发下载
        for btn_text in ['导出','确认','确定','下载','保存','Export','Download','Save']:
            ok = page.evaluate('''(t) => {
                const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
                if (dlgs.length === 0) return false;
                const d = dlgs[dlgs.length-1];
                const btn = [...d.querySelectorAll('button')].find(b => (b.innerText||'').trim() === t);
                if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); return true; }
                return false;
            }''', btn_text)
            if ok:
                print(f"  ✓ 点了 '{btn_text}' 触发下载")
                page.wait_for_timeout(5000)
                break
        page.screenshot(path='/workspace/pp_v2_export_done.png')
    else:
        print("  ❌ 没找到导出按钮")

    print(f"\n=== 6. 下载文件 ===")
    for d in downloads:
        print(f"  {d}")
    if not downloads:
        # 兜底: 也看 /tmp 是否有 .pbp
        print("  没捕获到下载事件, 列出 exports 目录:")
        try:
            for f in os.listdir(PBP_OUT_DIR):
                print(f"    {f}: {os.path.getsize(os.path.join(PBP_OUT_DIR, f))} bytes")
        except: pass

    print("\n=== 7. XHR (导出/后处理相关) ===")
    for x in xhr_log:
        u = x['url']
        if any(k in u.lower() for k in ['export','post','proc','denoise','merge','stray','cleanup','color']) or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
