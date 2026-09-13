"""3D 预览面板实测：所有选项逐一开关 + 三工艺模式对比截图。"""
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
                    x['body'] = resp.body()[:800].decode('utf-8', errors='replace')
            except: pass
            xhr_log.append(x)
    page.on('response', on_response)

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1500)
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

    # 复用之前的项目（之前保存的 1789297487536-ia8zup1），直接进编辑器
    print("\n=== 1. 进入之前的项目编辑器 ===")
    page.goto('https://i2tools.com/editor?projectId=1789297487536-ia8zup1', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(4000)
    print(f"  URL: {page.url}")
    page.screenshot(path='/workspace/3d_editor_init.png')

    # 找 3D 预览按钮/面板
    print("\n=== 2. 探查 3D 预览入口 ===")
    info = page.evaluate('''() => {
        const btns = [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 20);
        const allText = document.body.innerText;
        const has3D = /3D\s*预览|3D\s*预覽|3D Preview/.test(allText);
        // 找包含 3D 文字的元素
        const d3Els = [...document.querySelectorAll('*')].filter(el => {
            const t = (el.innerText||'').trim();
            return t && t.length < 30 && /3D|预览|预覽|Preview|拼豆|烫豆|毛巾/.test(t);
        }).slice(0, 20).map(el => ({tag: el.tagName, text: (el.innerText||'').trim().slice(0,30), cls: el.className?.toString().slice(0,50)}));
        return {btns, has3D, d3Els, snip: allText.slice(0, 800)};
    }''')
    print(f"  has3D 文字: {info['has3D']}")
    print(f"  body 前800:\n{info['snip']}")
    print(f"  按钮 ({len(info['btns'])}): {info['btns']}")
    print(f"  3D 相关元素: {info['d3Els']}")

    # 点 3D 预览
    print("\n=== 3. 点「3D 预览」按钮 ===")
    for txt in ['3D 预览', '3D 预覽', '3D Preview', '3D预览']:
        loc = page.locator(f'button:has-text("{txt}"), [role="button"]:has-text("{txt}"), [role="tab"]:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 点了「{txt}」")
                page.wait_for_timeout(3000)
                break
            except Exception as e:
                print(f"  {txt}: {e}")

    page.screenshot(path='/workspace/3d_panel_default.png')

    # 看面板所有控件
    print("\n=== 4. 探查 3D 面板控件 ===")
    panel = page.evaluate('''() => {
        // 找所有 checkbox / radio / select / 颜色选择器
        const checks = [...document.querySelectorAll('[role="checkbox"], input[type="checkbox"]')].map(c => ({
            label: c.closest('label')?.innerText?.trim().slice(0,30) || c.getAttribute('aria-label') || '',
            checked: c.getAttribute('aria-checked') || c.checked
        }));
        const radios = [...document.querySelectorAll('[role="radio"], input[type="radio"]')].map(r => ({
            label: r.closest('label')?.innerText?.trim().slice(0,30) || r.getAttribute('aria-label') || '',
            checked: r.getAttribute('aria-checked') || r.checked
        }));
        const selects = [...document.querySelectorAll('select')].map(s => ({
            options: [...s.options].map(o => o.text)
        }));
        const canvases = [...document.querySelectorAll('canvas')].map(c => ({w: c.width, h: c.height, ctx: (()=>{try{c.getContext('webgl2');return 'webgl2'}catch(e){try{c.getContext('webgl');return 'webgl'}catch(e){return 'none'}}})()}));
        const colorInputs = [...document.querySelectorAll('input[type="color"]')].length;
        return {checks, radios, selects, canvases, colorInputs};
    }''')
    print(f"  canvas: {panel['canvases']}")
    print(f"  checkboxes ({len(panel['checks'])}):")
    for c in panel['checks']:
        print(f"    {c['label']!r} checked={c['checked']}")
    print(f"  radios ({len(panel['radios'])}):")
    for r in panel['radios']:
        print(f"    {r['label']!r} checked={r['checked']}")
    print(f"  selects: {panel['selects']}")
    print(f"  color inputs: {panel['colorInputs']}")

    # 三工艺模式切换测试
    print("\n=== 5. 三工艺模式切换（拼豆→烫豆→毛巾烫）===")
    for mode in ['拼豆', '烫豆', '毛巾烫']:
        loc = page.locator(f'[role="radio"]:has-text("{mode}"), [role="tab"]:has-text("{mode}"), button:has-text("{mode}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(2000)
                page.screenshot(path=f'/workspace/3d_mode_{mode}.png')
                # 查 canvas 上下文
                cv = page.evaluate('''() => {
                    const cs = [...document.querySelectorAll('canvas')];
                    return cs.map(c => ({w: c.width, h: c.height}));
                }''')
                print(f"  ✓ {mode}: canvas={cv}")
            except Exception as e:
                print(f"  {mode} 失败: {e}")
        else:
            print(f"  ✗ {mode} 没找到")

    # 选项逐一开关测试
    print("\n=== 6. 选项逐一开关 ===")
    for opt in ['显示阴影', '顯示陰影', '自动旋转', '自動旋轉', '环境光', '環境光', '拼豆板', '背景色']:
        loc = page.locator(f'[role="checkbox"]:has-text("{opt}"), label:has([role="checkbox"]):has-text("{opt}"), [role="radio"]:has-text("{opt}")').first
        if loc.count() > 0:
            try:
                before = loc.get_attribute('aria-checked')
                loc.click(timeout=2000)
                page.wait_for_timeout(1500)
                after = loc.get_attribute('aria-checked')
                page.screenshot(path=f'/workspace/3d_opt_{opt}_toggle.png')
                print(f"  ✓ {opt}: {before} → {after}")
            except Exception as e:
                print(f"  {opt}: {e}")

    print(f"\n=== 7. 全部 XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:100]} [{x['status']}]")
            if 'body' in x:
                print(f"    {x['body'][:200]}")

    browser.close()
