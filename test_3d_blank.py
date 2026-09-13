"""新建空白项目快速进编辑器，测试 3D 预览面板和三工艺。"""
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
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)

    # 看菜单项
    menu = page.evaluate(r'''() => {
        const items = [...document.querySelectorAll('button, [role="button"], a')].filter(b => {
            const txt = (b.innerText||'').trim();
            return txt && /新建空白|空白项目|导入项目|拼图图纸|小红书|图片生成|选择图片/.test(txt);
        });
        return items.map(b => ({
            tag: b.tagName,
            text: (b.innerText||'').trim().slice(0,40),
            href: b.getAttribute('href') || '',
            cls: (b.className||'').toString().slice(0,80),
            parent_text: b.parentElement?.innerText?.trim().slice(0, 80)
        }));
    }''')
    print(f"  菜单候选项 ({len(menu)}):")
    for m in menu:
        print(f"    {m}")

    print("\n=== 2. 点 navbar「新建」打开下拉 ===")
    # 先点 navbar 第一个「新建」按钮（aria-label=新建）打开下拉菜单
    nav_btn = page.locator('button[aria-label="新建"]').first
    if nav_btn.count() > 0:
        nav_btn.click(timeout=3000)
        page.wait_for_timeout(1500)
        print("  ✓ 点开下拉")

    print("\n=== 2b. 点「新建空白项目」 ===")
    clicked_blank = False
    for txt in ['新建空白项目', '新建空白', '空白项目']:
        loc = page.locator(f'[role="menuitem"]:has-text("{txt}"), [role="option"]:has-text("{txt}"), button:has-text("{txt}"):visible').first
        if loc.count() == 0:
            loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(2000)
                print(f"  ✓ 点了「{txt}」 -> {page.url}")
                clicked_blank = True
                break
            except Exception as e:
                print(f"  {txt}: {e}")

    # 看空白画布对话框
    print("\n=== 2c. 填宽高 + 点「创建」 ===")
    # 找 dialog 中的 number input
    num_inputs = page.evaluate(r'''() => {
        const dlg = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"]')].find(d => d.innerText && d.innerText.includes('空白画布'));
        if (!dlg) return {found: false};
        const inputs = [...dlg.querySelectorAll('input')].map(i => ({
            type: i.type, name: i.name, value: i.value, placeholder: i.placeholder, aria: i.getAttribute('aria-label') || ''
        }));
        return {found: true, inputs};
    }''')
    print(f"  对话框 input: {num_inputs}")

    # 填宽高（默认值应该已经存在，直接点「创建」）
    # 用默认尺寸 50x50（如果输入框为空就填 50）
    try:
        # 找到 dialog 里的所有 number input
        dlg = page.locator('[data-slot="dialog-content"], [role="dialog"]').filter(has_text="空白画布").first
        # 宽度：找 label 包含 宽 的 input
        w_loc = dlg.locator('input[type="number"]').nth(0)
        h_loc = dlg.locator('input[type="number"]').nth(1)
        # 如果默认值是 0 或空，填 50
        w_val = w_loc.input_value()
        h_val = h_loc.input_value()
        print(f"  默认宽={w_val}, 高={h_val}")
        if not w_val or w_val == '0':
            w_loc.fill('32', timeout=2000)
        if not h_val or h_val == '0':
            h_loc.fill('32', timeout=2000)
    except Exception as e:
        print(f"  填宽高: {e}")

    # 点「创建」
    try:
        create_btn = page.locator('button:has-text("创建")').last
        if create_btn.count() > 0:
            create_btn.click(timeout=3000)
            page.wait_for_timeout(5000)
            print(f"  ✓ 点了「创建」 -> {page.url}")
    except Exception as e:
        print(f"  创建失败: {e}")

    page.screenshot(path='/workspace/ed_after_create.png')

    # 再点主按钮「开始制作」下拉，看选项
    if not clicked_blank:
        print("\n  尝试点「开始制作」下拉")
        loc = page.locator('button:has-text("开始制作"), [role="button"]:has-text("开始制作")').first
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(1500)
            opts = page.evaluate(r'''() => [...document.querySelectorAll('[role="menuitem"], [role="option"], button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 20)''')
            print(f"  下拉选项: {opts}")
            # 再点「新建空白项目」
            for txt in ['新建空白项目', '新建空白', '空白项目']:
                loc2 = page.locator(f'[role="menuitem"]:has-text("{txt}"), [role="option"]:has-text("{txt}"), button:has-text("{txt}")').first
                if loc2.count() > 0:
                    loc2.click(timeout=3000)
                    page.wait_for_timeout(4000)
                    print(f"  ✓ 点了「{txt}」 -> {page.url}")
                    clicked_blank = True
                    break

    page.screenshot(path='/workspace/ws_after_blank.png')
    print(f"\n  当前 URL: {page.url}")
    print(f"  title: {page.title()}")

    # 看是否进了编辑器
    info = page.evaluate('''() => ({
        url: location.href,
        body: document.body.innerText.slice(0, 800),
        canvas: [...document.querySelectorAll('canvas')].map(c => {
            let type='none';
            try { if(c.getContext('webgl2')) type='webgl2'; else if(c.getContext('webgl')) type='webgl'; else if(c.getContext('2d')) type='2d'; } catch(e){}
            return {w: c.width, h: c.height, type};
        }),
        all_btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 25).slice(0, 50),
        all_icons: [...document.querySelectorAll('button[aria-label], button[title]')].map(b => ({
            aria: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || ''
        })).filter(x => x.aria || x.title).slice(0, 50)
    })''')
    print(f"\n  body 前 800:\n{info['body']}")
    print(f"\n  canvas: {info['canvas']}")
    print(f"\n  按钮 ({len(info['all_btns'])}): {info['all_btns']}")
    print(f"\n  图标按钮 ({len(info['all_icons'])}):")
    for ic in info['all_icons']:
        print(f"    {ic}")

    # 找 3D 预览按钮
    print("\n=== 3. 找 3D 预览按钮 ===")
    d3_btn = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('button, [role="button"], [role="tab"]')];
        const matches = [];
        for (const b of all) {
            const al = b.getAttribute('aria-label') || '';
            const ti = b.getAttribute('title') || '';
            const txt = (b.innerText || '').trim();
            const combined = (al + ' ' + ti + ' ' + txt).toLowerCase();
            if (/3d|preview|预览|预覽|三维|3d 预览|cube/.test(combined)) {
                matches.push({tag: b.tagName, text: txt.slice(0,20), aria: al, title: ti, cls: (b.className||'').toString().slice(0,80)});
            }
        }
        return matches.slice(0, 10);
    }''')
    print(f"  3D 候选: {d3_btn}")

    # svg 图标找 3D cube
    d3_icons = page.evaluate(r'''() => {
        const svgs = [...document.querySelectorAll('svg')].filter(s => {
            const cls = (s.getAttribute('class') || '').toLowerCase();
            return /cube|box-3d|3d|preview|rotate-3d|boxes/.test(cls);
        });
        return svgs.map(s => {
            const p = s.closest('button, [role="button"]');
            return {
                svg_cls: s.getAttribute('class') || '',
                parent_aria: p?.getAttribute('aria-label') || '',
                parent_title: p?.getAttribute('title') || '',
                parent_text: (p?.innerText || '').trim().slice(0, 20)
            };
        });
    }''')
    print(f"  cube/3d svg 图标 ({len(d3_icons)}):")
    for ic in d3_icons:
        print(f"    {ic}")

    # 点击候选
    if d3_btn:
        for cand in d3_btn:
            loc = page.locator(f'button[aria-label="{cand["aria"]}"]').first
            if loc.count() == 0 and cand['title']:
                loc = page.locator(f'button[title="{cand["title"]}"]').first
            if loc.count() == 0 and cand['text']:
                loc = page.locator(f'button:has-text("{cand["text"]}")').first
            if loc.count() > 0:
                try:
                    loc.click(timeout=3000)
                    page.wait_for_timeout(3000)
                    print(f"  ✓ 点了「{cand['text'] or cand['aria'] or cand['title']}」")
                    break
                except Exception as e:
                    print(f"  click err: {e}")

    page.screenshot(path='/workspace/ed_3d_panel.png')

    print("\n=== 4. 重看 3D 面板控件 ===")
    panel = page.evaluate(r'''() => {
        const checks = [...document.querySelectorAll('[role="checkbox"], input[type="checkbox"]')].map(c => ({
            label: c.closest('label')?.innerText?.trim().slice(0,30) || c.getAttribute('aria-label') || '',
            checked: c.getAttribute('aria-checked') || c.checked
        })).filter(c => c.label);
        const radios = [...document.querySelectorAll('[role="radio"], input[type="radio"]')].map(r => ({
            label: r.closest('label')?.innerText?.trim().slice(0,30) || r.getAttribute('aria-label') || '',
            checked: r.getAttribute('aria-checked') || r.checked
        })).filter(r => r.label);
        const tabs = [...document.querySelectorAll('[role="tab"], [role="switch"]')].map(t => ({
            label: (t.innerText||'').trim().slice(0,30) || t.getAttribute('aria-label') || '',
            active: t.getAttribute('data-state') === 'active' || t.getAttribute('aria-selected') === 'true'
        })).filter(t => t.label);
        const canvases = [...document.querySelectorAll('canvas')].map(c => {
            let type='none';
            try { if(c.getContext('webgl2')) type='webgl2'; else if(c.getContext('webgl')) type='webgl'; else if(c.getContext('2d')) type='2d'; } catch(e){}
            return {w: c.width, h: c.height, type};
        });
        return {checks, radios, tabs, canvases};
    }''')
    print(f"  canvas: {panel['canvases']}")
    print(f"  tabs: {panel['tabs']}")
    print(f"  checkboxes ({len(panel['checks'])}): {panel['checks']}")
    print(f"  radios ({len(panel['radios'])}): {panel['radios']}")

    # 切三工艺
    print("\n=== 5. 切三工艺 ===")
    for mode in ['拼豆', '烫豆', '毛巾烫']:
        loc = page.locator(f'[role="radio"]:has-text("{mode}"), [role="tab"]:has-text("{mode}"), button:has-text("{mode}"), [role="switch"]:has-text("{mode}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(2000)
                page.screenshot(path=f'/workspace/ed_3d_mode_{mode}.png')
                cv = page.evaluate('''() => [...document.querySelectorAll('canvas')].map(c => ({w:c.width, h:c.height}))''')
                print(f"  ✓ {mode}: canvas={cv}")
            except Exception as e:
                print(f"  {mode}: {e}")

    # 切复选框
    print("\n=== 6. 切换复选框 ===")
    for chk in ['显示阴影', '自动旋转', '环境光', '拼豆板', '背景色']:
        loc = page.locator(f'label:has-text("{chk}"), [role="checkbox"][aria-label*="{chk}"]').first
        if loc.count() > 0:
            try:
                loc.click(timeout=2000)
                page.wait_for_timeout(1500)
                page.screenshot(path=f'/workspace/ed_3d_chk_{chk}.png')
                print(f"  ✓ 切「{chk}」")
            except Exception as e:
                print(f"  {chk}: {e}")

    print(f"\n=== 7. XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")

    browser.close()
