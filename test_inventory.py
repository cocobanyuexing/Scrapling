"""测试库存管理模块 + 色号合并/去除杂色/降噪 3 个后处理算法。"""
from patchright.sync_api import sync_playwright

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

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
                req_body = resp.request.post_data
                body = ''
                if 'json' in resp.headers.get('content-type', ''):
                    body = resp.body()[:400].decode('utf-8', errors='replace')
                xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status, 'req': (req_body or '')[:200], 'body': body})
            except:
                xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status})
    page.on('response', on_response)

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
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
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(4000)

    print("\n=== 1. 进 /workspace/inventory 库存管理 ===")
    page.goto('https://i2tools.com/workspace/inventory', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    print(f"  URL: {page.url}")
    print(f"  title: {page.title()}")
    page.screenshot(path='/workspace/inv_main.png')

    inv_info = page.evaluate(r'''() => ({
        body: document.body.innerText.slice(0, 1500),
        btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 50),
        tabs: [...document.querySelectorAll('[role="tab"], [role="radio"]')].map(t => ({
            label: (t.innerText||'').trim().slice(0, 20),
            active: t.getAttribute('data-state') === 'active' || t.getAttribute('aria-selected') === 'true'
        })).filter(t => t.label),
        swatches: [...document.querySelectorAll('button, [role="button"]')].filter(b => {
            const ti = b.getAttribute('title') || '';
            return /^[A-Z]\d+/.test(ti);
        }).slice(0, 10).map(b => ({
            title: b.getAttribute('title'),
            cls: (b.className||'').toString().slice(0, 80)
        })),
        selects: [...document.querySelectorAll('select')].map(s => ({
            name: s.name, value: s.value,
            options: [...s.options].slice(0, 10).map(o => o.text)
        }))
    })''')
    print(f"\n  body 前 1500:\n{inv_info['body']}")
    print(f"\n  按钮 ({len(inv_info['btns'])}): {inv_info['btns']}")
    print(f"\n  tabs: {inv_info['tabs']}")
    print(f"\n  色号按钮: {inv_info['swatches']}")
    print(f"\n  下拉选择: {inv_info['selects']}")

    # 切色号体系 (MARD H/G/C/M 系列)
    print("\n=== 2. 切换色号体系 (H/G/C/M 系列) ===")
    for series in ['H系列', 'G系列', 'C系列', 'M系列', 'H', 'G', 'C', 'M', '心雪', '米酱', 'MARD']:
        loc = page.locator(f'[role="tab"]:has-text("{series}"), [role="radio"]:has-text("{series}"), button:has-text("{series}")').first
        try:
            if loc.count() > 0:
                loc.click(timeout=2000)
                page.wait_for_timeout(1500)
                page.screenshot(path=f'/workspace/inv_series_{series}.png')
                print(f"  ✓ 切到「{series}」")
                break
        except: pass

    # 重新看色号列表
    print("\n=== 3. 看色号列表 ===")
    swatches_after = page.evaluate(r'''() => {
        // 找色号卡片
        const items = [...document.querySelectorAll('button, [role="button"], [role="listitem"]')].filter(b => {
            const ti = b.getAttribute('title') || '';
            const txt = (b.innerText||'').trim();
            return /^[A-Z]\d+/.test(ti) || /^[A-Z]\d+/.test(txt);
        });
        return items.slice(0, 30).map(b => ({
            title: b.getAttribute('title') || '',
            text: (b.innerText||'').trim().slice(0, 50),
            has_stock: /[\d]+/.test((b.innerText||'').trim())
        }));
    }''')
    print(f"  色号 ({len(swatches_after)}): ")
    for s in swatches_after[:15]:
        print(f"    {s}")

    # 切回编辑器，测试扣减库存
    print("\n=== 4. 回到之前编辑器测扣减库存 ===")
    # 找最后一个项目的 projectId（之前的 5×5 项目）
    # 直接打开 ai-pixel-art 历史，点最新结果的「创建项目」
    page.goto('https://i2tools.com/tools/ai-pixel-art', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    # 点最新结果的「创建项目」按钮
    btns = page.locator('button:has-text("创建项目")')
    cnt = btns.count()
    print(f"  创建项目按钮数: {cnt}")
    if cnt > 0:
        btns.first.click(timeout=3000)
        page.wait_for_timeout(3000)
        # 点应用
        loc = page.locator('button:has-text("应用")').first
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(5000)
            print(f"  ✓ 进编辑器: {page.url}")
    page.screenshot(path='/workspace/inv_in_editor.png')

    # 看色号统计 + 扣减库存按钮
    editor_info = page.evaluate(r'''() => ({
        body: document.body.innerText.slice(0, 1000),
        bead_stats: (() => {
            const text = document.body.innerText;
            const m = text.match(/色号统计[\s\S]*?(\d+)[\s\S]*?(扣减库存|色号合并)/);
            return m ? {count: m[1], hasBtn: m[2]} : null;
        })()
    })''')
    print(f"\n  编辑器 body 前 1000:\n{editor_info['body']}")
    print(f"\n  色号统计: {editor_info['bead_stats']}")

    # 点扣减库存
    print("\n=== 5. 点「扣减库存」 ===")
    loc = page.locator('button:has-text("扣减库存"), [title="扣减库存"]').first
    if loc.count() > 0:
        try:
            loc.click(timeout=3000, force=True)
            page.wait_for_timeout(2000)
            print("  ✓ 点了「扣减库存」")
            page.screenshot(path='/workspace/inv_deduct_dialog.png')
            # 看弹窗
            dialog = page.evaluate(r'''() => {
                const dlgs = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"]')];
                const d = dlgs.find(d => d.innerText && (d.innerText.includes('库存') || d.innerText.includes('扣减')));
                return d ? d.innerText.slice(0, 600) : 'no dialog';
            }''')
            print(f"  弹窗: {dialog}")
            # 关闭
            page.keyboard.press('Escape')
            page.wait_for_timeout(1000)
        except Exception as e:
            # 备用：JS 直接 dispatch
            print(f"  force click err: {e}, 试 JS dispatch")
            clicked = page.evaluate(r'''() => {
                const b = [...document.querySelectorAll('button[title="扣减库存"]')];
                if (b.length > 0) {
                    b[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    return true;
                }
                return false;
            }''')
            print(f"  JS dispatch: {clicked}")
            page.wait_for_timeout(2000)
            page.screenshot(path='/workspace/inv_deduct_dialog.png')
            dialog = page.evaluate(r'''() => {
                const dlgs = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"]')];
                const d = dlgs.find(d => d.innerText && (d.innerText.includes('库存') || d.innerText.includes('扣减')));
                return d ? d.innerText.slice(0, 600) : 'no dialog';
            }''')
            print(f"  弹窗: {dialog}")
            page.keyboard.press('Escape')
            page.wait_for_timeout(1000)
    else:
        print("  ✗ 没找到「扣减库存」按钮")

    # 测 3 个后处理：色号合并 / 去除杂色 / 降噪
    print("\n=== 6. 测 3 个后处理算法 ===")
    for op in ['色号合并', '去除杂色', '降噪']:
        loc = page.locator(f'button:has-text("{op}"), [title="{op}"]').first
        try:
            if loc.count() > 0:
                loc.click(timeout=3000, force=True)
                page.wait_for_timeout(2500)
                page.screenshot(path=f'/workspace/inv_op_{op}.png')
                # 看弹窗或滑块
                result = page.evaluate(r'''() => {
                    const dlgs = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"], [role="alertdialog"]')];
                    const active = dlgs.find(d => d.offsetParent !== null);
                    if (active) {
                        const sliders = [...active.querySelectorAll('input[type="range"], [role="slider"]')].map(s => ({
                            value: s.value, min: s.min, max: s.max, aria: s.getAttribute('aria-label') || ''
                        }));
                        const radios = [...active.querySelectorAll('[role="radio"], [role="option"]')].map(r => ({
                            label: (r.innerText||'').trim().slice(0,30),
                            checked: r.getAttribute('aria-checked') === 'true' || r.getAttribute('data-state') === 'active'
                        }));
                        const presets = [...active.querySelectorAll('button, [role="button"]')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30 && /light|balanced|strong|aggressive|轻|中|重|强|预设|应用|取消|确定|阈值|距离|面积/.test(t));
                        return {open: true, body: active.innerText.slice(0, 500), sliders, radios, presets};
                    }
                    return {open: false};
                }''')
                print(f"\n  「{op}」 弹窗: {result}")
                # 关弹窗
                page.keyboard.press('Escape')
                page.wait_for_timeout(800)
        except Exception as e:
            print(f"  {op}: {e}")

    print(f"\n=== XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")
            if x.get('req'):
                print(f"    req: {x['req']}")
            if x.get('body'):
                print(f"    resp: {x['body']}")

    browser.close()
