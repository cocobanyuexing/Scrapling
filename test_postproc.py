"""实测：后处理算法弹窗（色号合并/去除杂色/降噪）
流程: 登录 -> 导入 .pbp -> 编辑器 -> 点后处理按钮 -> 调参数 -> 验证算法
"""
from patchright.sync_api import sync_playwright
import json, os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'

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
                if 'json' in ct: body = resp.text()[:1000]
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
    print(f"  登录后: {page.url}")

    print("\n=== 1. 导入 .pbp 进编辑器 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.locator('input[type="file"][accept=".pbp"]').first.set_input_files(PBP)
    page.wait_for_timeout(8000)
    print(f"  导入后 URL: {page.url}")
    page.screenshot(path='/workspace/pp_1_editor.png')

    print("\n=== 2. 找后处理按钮 ===")
    # 找 色号合并/去除杂色/降噪 按钮
    btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            visible: b.offsetParent !== null
        })).filter(x => x.visible && (x.text || x.aria));
    }''')
    postproc = [b for b in btns if any(k in (b['text']+b['aria']+b['title']) for k in ['色号合并','去除杂色','降噪','合并','杂色','降噪','denoise','merge','noise','stray','cleanup'])]
    print(f"  后处理按钮 ({len(postproc)}):")
    for b in postproc:
        print(f"    text='{b['text']}' aria='{b['aria']}'")

    print("\n=== 3. 点 '去除杂色' (测试降噪算法) ===")
    # 先试去除杂色
    target = None
    for b in postproc:
        if '杂色' in b['text'] or '杂色' in b['aria']:
            target = b
            break
    if target:
        try:
            page.get_by_text(target['text'] or target['aria'], exact=False).first.click(force=True, timeout=5000)
            print(f"  ✓ 点了 '{target['text'] or target['aria']}'")
        except Exception as e:
            print(f"  click 失败: {e}")
    else:
        print("  ❌ 没找到去除杂色按钮")
    
    page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/pp_2_stray_dialog.png')
    
    # dump 弹窗内容
    dlg = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
        if (dlgs.length === 0) {
            // fallback: 找含 去杂色/降噪 文字的容器
            const all = [...document.querySelectorAll('*')];
            const t = all.find(e => /杂色|降噪|去噪/.test(e.innerText||'') && e.children.length < 30 && e.getBoundingClientRect().width > 100);
            if (t) return {found: true, text: t.innerText.slice(0, 500), tag: t.tagName};
            return {found: false};
        }
        const d = dlgs[dlgs.length-1]; // 最后一个(最新弹的)
        return {
            found: true,
            text: d.innerText.slice(0, 500),
            tag: d.tagName,
            buttons: [...d.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t),
            inputs: [...d.querySelectorAll('input, [role="slider"], [role="radio"]')].map(i => ({
                type: i.type || i.getAttribute('role'),
                label: i.getAttribute('aria-label') || '',
                value: i.value || i.getAttribute('aria-checked') || ''
            })),
            radios: [...d.querySelectorAll('[role="radio"]')].map(r => ({
                label: r.getAttribute('aria-label') || r.innerText.trim(),
                checked: r.getAttribute('aria-checked') === 'true'
            }))
        };
    }''')
    print(f"\n  弹窗 found: {dlg.get('found')}")
    if dlg.get('found'):
        if 'text' in dlg:
            print(f"  text:\n{dlg['text'][:400]}")
        if 'buttons' in dlg:
            print(f"  buttons: {dlg['buttons']}")
        if 'inputs' in dlg:
            print(f"  inputs: {dlg['inputs']}")
        if 'radios' in dlg:
            print(f"  radios: {dlg['radios']}")

    print("\n=== 4. 试选不同预设 (light/balanced/strong/aggressive) ===")
    # 找预设 radio
    presets = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
        if (dlgs.length === 0) return [];
        const d = dlgs[dlgs.length-1];
        const radios = [...d.querySelectorAll('[role="radio"], button')];
        return radios.map(r => ({
            text: (r.innerText||'').trim().slice(0,40),
            checked: r.getAttribute('aria-checked') === 'true',
            tag: r.tagName
        })).filter(x => x.text);
    }''')
    print(f"  预设选项: {presets}")
    # 点 'strong' 预设
    for p_text in ['strong', '强', 'strong', 'aggressive', '激进']:
        try:
            loc = page.get_by_text(p_text, exact=False).first
            if loc.count() > 0:
                loc.click(force=True, timeout=3000)
                print(f"  ✓ 选了 '{p_text}'")
                page.wait_for_timeout(1000)
                break
        except: pass

    print("\n=== 5. 点确认/应用 执行算法 ===")
    for btn_text in ['应用', '确认', '确定', '执行', 'Apply', 'Confirm']:
        btn = page.locator(f'button:has-text("{btn_text}")').last
        if btn.count() > 0:
            btn.click(force=True, timeout=5000)
            print(f"  ✓ 点了 '{btn_text}'")
            page.wait_for_timeout(3000)
            break
    page.screenshot(path='/workspace/pp_3_after_apply.png')
    body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
    print(f"  body:\n{body[:300]}")

    print("\n=== 6. 检查色号数量是否变化(算法生效) ===")
    # 色号面板的色号数应该变化
    colors = page.evaluate('''() => {
        const all = [...document.querySelectorAll('*')];
        // 色号面板通常显示色号(如 H2, M12)和数量
        const colorEls = all.filter(e => /^[A-Z]\d+$/.test((e.innerText||'').trim()) && e.children.length === 0);
        return colorEls.map(e => (e.innerText||'').trim()).slice(0, 20);
    }''')
    print(f"  色号: {colors}")

    print("\n=== 7. XHR ===")
    for x in xhr_log[-15:]:
        print(f"  {x['st']} {x['m']} {x['url'][:120]}")

    ctx.close(); browser.close()
print("\nDONE")
