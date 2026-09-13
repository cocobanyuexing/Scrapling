"""下载 ai-pixel-art 真实结果图 + 探索 perfect-pixel 工具入口。"""
from patchright.sync_api import sync_playwright
import json
import base64

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
RESULT_URL = 'https://oss-cdn.i2tools.com/ai-results/bead-conversion/TASK20260913185502422649/1/0.webp'
THUMB_URL = 'https://oss-cdn.i2tools.com/ai-results/bead-conversion/TASK20260913185502422649/1/0.thumb.webp'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='zh-CN')
    page = ctx.new_page()

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
    except Exception as e:
        print(f"  checkbox: {e}")
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(5000)

    print("\n=== 1. 下载真实结果图（主图 + 缩略图）===")
    for name, url in [('result', RESULT_URL), ('thumb', THUMB_URL)]:
        r = page.evaluate('''async (url) => {
            try {
                const r = await fetch(url);
                const blob = await r.blob();
                const reader = new FileReader();
                return new Promise(res => {
                    reader.onload = () => res({ok: true, b64: reader.result, type: blob.type, size: blob.size, status: r.status});
                    reader.onerror = () => res({ok: false, err: 'reader err', status: r.status});
                    reader.readAsDataURL(blob);
                });
            } catch(e) { return {ok: false, err: String(e)}; }
        }''', url)
        print(f"  {name}: ok={r.get('ok')} status={r.get('status')} type={r.get('type')} size={r.get('size')}")
        if r.get('ok') and r.get('b64'):
            data = r['b64'].split(',', 1)[1]
            ext = r.get('type', 'image/webp').split('/')[-1].split(';')[0] or 'webp'
            out = f'/workspace/pixelart_{name}.{ext}'
            with open(out, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f"    ✓ 已保存 {out}")

    print("\n=== 2. 导航 /tools/perfect-pixel 探索入口 ===")
    page.goto('https://i2tools.com/tools/perfect-pixel', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1000)
    page.screenshot(path='/workspace/pp_init.png')
    print(f"  URL: {page.url}")
    info = page.evaluate('''() => {
        const body = document.body.innerText.slice(0, 1000);
        const btns = [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 30);
        const links = [...document.querySelectorAll('a[href]')].map(a => ({t:(a.innerText||'').trim().slice(0,40), h:a.getAttribute('href')})).filter(x=>x.h).slice(0,20);
        const inputs = [...document.querySelectorAll('input')].map(i => ({type:i.type, ph:i.placeholder, name:i.name})).slice(0,10);
        return {body, btns, links, inputs};
    }''')
    print(f"\n  body 前1000:\n{info['body']}")
    print(f"\n  按钮 ({len(info['btns'])}): {info['btns']}")
    print(f"\n  链接 ({len(info['links'])}):")
    for l in info['links']:
        print(f"    {l['t']!r} -> {l['h']}")
    print(f"\n  inputs: {info['inputs']}")

    browser.close()
