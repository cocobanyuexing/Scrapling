"""3D 实测 v3：进编辑器后用 page.evaluate 直接走 react 状态找 3D 预览开关 + 用图标按钮定位。"""
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
            xhr_log.append({'method': resp.request.method, 'url': resp.url, 'status': resp.status})
    page.on('response', on_response)

    print("=== 0. 登录 + 关弹窗 ===")
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
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)

    print("\n=== 1. 复用之前 perfect-pixel 保存的项目进编辑器 ===")
    page.goto('https://i2tools.com/editor?projectId=1789297487536-ia8zup1', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    print(f"  URL: {page.url}")
    print(f"  title: {page.title()}")
    page.screenshot(path='/workspace/ed_init.png')

    # 看编辑器状态
    info = page.evaluate('''() => ({
        url: location.href,
        title: document.title,
        body: document.body.innerText.slice(0, 600),
        buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 25),
        icons: [...document.querySelectorAll('button svg, [role="button"] svg')].map(s => {
            const parent = s.closest('button, [role="button"]');
            const label = parent?.getAttribute('aria-label') || parent?.getAttribute('title') || '';
            const cls = s.getAttribute('class') || '';
            return {label, cls: cls.slice(0, 40)};
        }).filter(x => x.label).slice(0, 40),
        canvas: [...document.querySelectorAll('canvas')].map(c => {
            let type='none';
            try { if(c.getContext('webgl2')) type='webgl2'; else if(c.getContext('webgl')) type='webgl'; else if(c.getContext('2d')) type='2d'; } catch(e){}
            return {w: c.width, h: c.height, type};
        })
    })''')
    print(f"\n  body 前600:\n{info['body']}")
    print(f"\n  canvas: {info['canvas']}")
    print(f"\n  按钮 ({len(info['buttons'])}): {info['buttons']}")
    print(f"\n  带标签图标按钮 ({len(info['icons'])}):")
    for ic in info['icons']:
        print(f"    {ic}")

    # 找 3D 预览按钮（可能 aria-label 含 3D/预览/preview/3d）
    print("\n=== 2. 找 3D 预览按钮 ===")
    d3_btn = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('button, [role="button"], [role="tab"]')];
        const matches = [];
        for (const b of all) {
            const al = b.getAttribute('aria-label') || '';
            const ti = b.getAttribute('title') || '';
            const txt = (b.innerText || '').trim();
            const combined = (al + ' ' + ti + ' ' + txt).toLowerCase();
            if (/3d|preview|预览|预覽|三维/.test(combined)) {
                matches.push({tag: b.tagName, text: txt.slice(0,20), aria: al, title: ti, cls: (b.className||'').toString().slice(0,80)});
            }
        }
        return matches.slice(0, 10);
    }''')
    print(f"  3D 候选按钮: {d3_btn}")

    # 点第一个候选
    if d3_btn:
        print("\n=== 3. 点击 3D 预览按钮 ===")
        # 优先 aria-label 含 '3d' 的
        for cand in d3_btn:
            if '3d' in (cand.get('aria','') + cand.get('title','')).lower() or '3d' in cand.get('text','').lower():
                # 重新定位
                loc = page.locator(f'button[aria-label="{cand["aria"]}"]').first
                if loc.count() == 0:
                    loc = page.locator(f'button[title="{cand["title"]}"]').first
                if loc.count() == 0:
                    loc = page.locator(f'button:has-text("{cand["text"]}")').first
                if loc.count() > 0:
                    try:
                        loc.click(timeout=3000)
                        print(f"  ✓ 点了「{cand['text'] or cand['aria'] or cand['title']}」")
                        page.wait_for_timeout(3000)
                        break
                    except Exception as e:
                        print(f"  click err: {e}")

    page.screenshot(path='/workspace/ed_3d_panel.png')

    # 重看控件
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

    # 切三工艺模式
    print("\n=== 5. 切三工艺模式 ===")
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

    print(f"\n=== 6. XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")

    browser.close()
