"""登录后探索 ai-pixel-art 工具入口结构。"""
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
                req_body = resp.request.post_data
                if req_body:
                    x['req'] = req_body[:300]
                ct = resp.headers.get('content-type', '')
                if 'json' in ct:
                    x['body'] = resp.body()[:600].decode('utf-8', errors='replace')
            except Exception:
                pass
            xhr_log.append(x)
    page.on('response', on_response)

    print("=== 0. 中文版首页 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1500)

    print("=== 1. 登录 ===")
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => b.innerText && (b.innerText.trim() === '登录' || b.innerText.trim() === '登入'));
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        cb = page.locator('[data-slot="dialog-content"] [role="checkbox"], [data-slot="dialog-content"] input[type="checkbox"]').first
        cb.click(timeout=3000)
        page.wait_for_timeout(500)
    except Exception as e:
        print(f"  checkbox: {e}")
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(5000)
    # 确认登录成功
    me = page.evaluate('''() => {
        try { return JSON.parse(localStorage.getItem('auth-storage') || localStorage.getItem('auth') || '{}'); } catch(e) { return String(e); }
    }''')
    print(f"  localStorage auth: {json.dumps(me, ensure_ascii=False)[:300] if isinstance(me, dict) else me}")

    print("\n=== 2. 导航 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1000)
    print(f"  URL: {page.url}")
    page.screenshot(path='/workspace/ws_create.png')

    # 打印页面所有链接 + 工具卡片
    info = page.evaluate('''() => {
        const links = [...document.querySelectorAll('a[href]')].map(a => ({t: (a.innerText||'').trim().slice(0,40), h: a.getAttribute('href')})).filter(x => x.h).slice(0, 40);
        const cards = [...document.querySelectorAll('[class*="card"], [class*="tool"], [class*="Card"], [class*="Tool"]')].map(c => (c.innerText||'').trim().slice(0,80)).filter(Boolean).slice(0, 30);
        const btns = [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 40);
        const bodyHead = document.body.innerText.slice(0, 800);
        return {links, cards, btns, bodyHead};
    }''')
    print(f"\n  body 前800字:\n{info['bodyHead']}")
    print(f"\n  链接 ({len(info['links'])}):")
    for l in info['links']:
        print(f"    {l['t']!r} -> {l['h']}")
    print(f"\n  按钮 ({len(info['btns'])}):")
    for b in info['btns']:
        print(f"    {b!r}")
    print(f"\n  卡片/工具 ({len(info['cards'])}):")
    for c in info['cards']:
        print(f"    {c!r}")

    print("\n=== 3. 尝试 /tools 和 /tools/ai-pixel-art ===")
    for path in ['/tools', '/tools/ai-pixel-art', '/workspace']:
        try:
            page.goto(f'https://i2tools.com{path}', wait_until='domcontentloaded', timeout=20000)
            page.wait_for_timeout(2000)
            final_url = page.url
            title = page.title()
            head = page.evaluate('document.body.innerText.slice(0,200)')
            print(f"\n  {path} -> {final_url}")
            print(f"    title: {title}")
            print(f"    head: {head[:150]}")
        except Exception as e:
            print(f"\n  {path} -> error: {e}")

    print(f"\n=== 4. XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        print(f"  {x['method']} {x['url'][:110]} [{x['status']}]")

    browser.close()
