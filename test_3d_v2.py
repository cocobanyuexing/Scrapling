"""3D 预览面板实测 v2：关弹窗 + 新建空白项目 + 进编辑器 + 开 3D 面板。"""
from patchright.sync_api import sync_playwright
import json

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
            x = {'method': resp.request.method, 'url': resp.url, 'status': resp.status}
            try:
                ct = resp.headers.get('content-type', '')
                if 'json' in ct:
                    x['body'] = resp.body()[:600].decode('utf-8', errors='replace')
            except: pass
            xhr_log.append(x)
    page.on('response', on_response)

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    # ESC 多按几次关所有 dialog
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(800)
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
    page.wait_for_timeout(5000)

    print("\n=== 1. 关掉所有更新日志弹窗 + 进工作台 ===")
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(800)
    # 点"工作台"
    for txt in ['工作台', '前往', '立刻前往', '新工作台已上线']:
        loc = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                print(f"  ✓ 点了「{txt}」")
                page.wait_for_timeout(2000)
                break
            except: pass
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(800)
    print(f"  当前 URL: {page.url}")

    print("\n=== 2. 进 /workspace/create 工作台主页 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    print(f"  URL: {page.url}")

    # 点"新建"按钮调起新建菜单（截图1的菜单）
    print("\n=== 3. 点「新建」调起 5 选项菜单 ===")
    for txt in ['新建', '創建', 'New']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(1500)
                print(f"  ✓ 点了「{txt}」")
                break
            except: pass
    page.screenshot(path='/workspace/new_menu.png')

    # 看菜单内容
    menu = page.evaluate('''() => {
        // 找所有 dialog/菜单内的项
        const ds = [...document.querySelectorAll('[data-slot="dialog-content"], [role="menu"], [role="dialog"]')];
        let items = [];
        for (const d of ds) {
            const txt = (d.innerText||'').trim();
            if (txt && txt.length < 500 && (txt.includes('选择图片') || txt.includes('拼图图纸') || txt.includes('小红书') || txt.includes('空白') || txt.includes('导入项目'))) {
                items.push(txt.slice(0, 300));
            }
        }
        return items;
    }''')
    print(f"  菜单项: {menu}")

    print("\n=== 4. 点「新建空白项目」进编辑器 ===")
    for txt in ['新建空白项目', '空白项目', '空白画布']:
        loc = page.locator(f'button:has-text("{txt}"), [role="button"]:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                print(f"  ✓ 点了「{txt}」")
                page.wait_for_timeout(3000)
                break
            except: pass
    # 可能弹尺寸选择
    page.wait_for_timeout(2000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    # 选尺寸 32×32 之类
    for txt in ['32', '50', '确定', '创建', '确认']:
        loc = page.locator(f'button:has-text("{txt}"), [role="radio"]:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=2000)
                page.wait_for_timeout(1500)
                # 可能需要再点确认
                page.locator('button:has-text("确定"), button:has-text("创建"), button:has-text("确认")').first.click(timeout=2000)
                break
            except: pass
    page.wait_for_timeout(3000)
    print(f"  跳转后 URL: {page.url}")
    page.screenshot(path='/workspace/blank_editor.png')

    print("\n=== 5. 在编辑器里找 3D 预览按钮 ===")
    info = page.evaluate('''() => {
        const btns = [...document.querySelectorAll('button, [role="button"], [role="tab"]')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 25);
        const canvas3d = [...document.querySelectorAll('canvas')].map(c => {
            let gl = null;
            try { gl = c.getContext('webgl2') || c.getContext('webgl'); } catch(e) {}
            return {w: c.width, h: c.height, gl: gl ? gl.constructor.name : null};
        });
        return {btns, canvas3d, title: document.title, body: document.body.innerText.slice(0, 400)};
    }''')
    print(f"  title: {info['title']}")
    print(f"  body 前400:\n{info['body']}")
    print(f"  canvas: {info['canvas3d']}")
    print(f"  按钮: {info['btns'][:30]}")

    # 找3D预览按钮
    print("\n=== 6. 点「3D 预览」 ===")
    for txt in ['3D 预览', '3D 预覽', '3D Preview', '3D预览']:
        loc = page.locator(f'button:has-text("{txt}"), [role="tab"]:has-text("{txt}"), [role="button"]:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                print(f"  ✓ 点了「{txt}」")
                page.wait_for_timeout(3000)
                break
            except Exception as e:
                print(f"  {txt}: {e}")

    page.screenshot(path='/workspace/3d_panel_v2.png')

    # 看 3D 面板控件
    print("\n=== 7. 探查 3D 面板控件 ===")
    panel = page.evaluate(r'''() => {
        const checks = [...document.querySelectorAll('[role="checkbox"], input[type="checkbox"]')].map(c => ({
            label: c.closest('label')?.innerText?.trim().slice(0,30) || c.getAttribute('aria-label') || '',
            checked: c.getAttribute('aria-checked') || c.checked
        })).filter(c => c.label);
        const radios = [...document.querySelectorAll('[role="radio"], input[type="radio"]')].map(r => ({
            label: r.closest('label')?.innerText?.trim().slice(0,30) || r.getAttribute('aria-label') || '',
            checked: r.getAttribute('aria-checked') || r.checked
        })).filter(r => r.label);
        const tabs = [...document.querySelectorAll('[role="tab"]')].map(t => ({
            label: (t.innerText||'').trim().slice(0,30),
            active: t.getAttribute('data-state') === 'active' || t.getAttribute('aria-selected') === 'true'
        })).filter(t => t.label);
        const canvases = [...document.querySelectorAll('canvas')].map(c => {
            let gl = null, type = 'none';
            try { gl = c.getContext('webgl2'); if (gl) type = 'webgl2'; else { gl = c.getContext('webgl'); if (gl) type = 'webgl'; } } catch(e) {}
            return {w: c.width, h: c.height, type};
        });
        const colorInputs = [...document.querySelectorAll('input[type="color"]')].length;
        return {checks, radios, tabs, canvases, colorInputs};
    }''')
    print(f"  canvas: {panel['canvases']}")
    print(f"  tabs: {panel['tabs']}")
    print(f"  checkboxes ({len(panel['checks'])}):")
    for c in panel['checks']:
        print(f"    {c['label']!r} checked={c['checked']}")
    print(f"  radios ({len(panel['radios'])}):")
    for r in panel['radios']:
        print(f"    {r['label']!r} checked={r['checked']}")
    print(f"  color inputs: {panel['colorInputs']}")

    # 切三工艺模式
    print("\n=== 8. 切三工艺模式 ===")
    for mode in ['拼豆', '烫豆', '毛巾烫']:
        loc = page.locator(f'[role="radio"]:has-text("{mode}"), [role="tab"]:has-text("{mode}"), button:has-text("{mode}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(2000)
                page.screenshot(path=f'/workspace/3d_mode_{mode}_v2.png')
                cv = page.evaluate('''() => [...document.querySelectorAll('canvas')].map(c => ({w:c.width, h:c.height}))''')
                print(f"  ✓ {mode}: canvas={cv}")
            except Exception as e:
                print(f"  {mode}: {e}")

    print(f"\n=== 9. XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:100]} [{x['status']}]")

    browser.close()
