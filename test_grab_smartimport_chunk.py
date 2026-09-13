"""抓 SmartImportModal chunk 39193 源码 + 找识别 API
策略: 在浏览器里拦截 chunk 加载, 或直接 fetch 它
"""
from patchright.sync_api import sync_playwright
import json, os, re

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='zh-CN')
    page = ctx.new_page()

    # 拦截所有 chunk 加载, 保存 39193
    chunk_src = {}
    def on_response(resp):
        url = resp.url
        if '/_next/static/chunks/' in url and '.js' in url:
            try:
                txt = resp.text()
                if '39193' in txt or 'SmartImport' in txt or 'smartImport' in txt or 'pattern' in txt.lower():
                    chunk_src[url] = txt
            except: pass
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
        page.locator('[data-slot="dialog-content"] [role="checkbox"], [data-slot="dialog-content"] input[type="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    print("\n=== 1. 进 create + 触发 smartImport modal ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    # 触发 z input 打开 modal
    img_inps = page.locator('input[type="file"][accept*="image"]')
    img_inps.nth(2).set_input_files('/workspace/测试图.jpg')
    page.wait_for_timeout(5000)  # 等 modal 加载 + chunk 39193 下载

    print(f"\n=== 2. 抓到的 chunk ({len(chunk_src)} 个) ===")
    for url, src in chunk_src.items():
        fn = url.split('/')[-1]
        print(f"  {fn} ({len(src)} chars)")
        # 找 API 端点
        apis = re.findall(r'["\'](/v1/[a-zA-Z0-9/_-]+)["\']', src)
        if apis:
            print(f"    API 端点: {list(set(apis))}")
        # 找识别相关关键词
        for kw in ['recogn','pattern','scan','detect','MARD','视觉','识别','图纸','grid','palette','analyze']:
            if kw.lower() in src.lower():
                # 找上下文
                for m in re.finditer(re.escape(kw), src, re.IGNORECASE):
                    i = m.start()
                    ctx_str = src[max(0,i-60):i+120].replace('\n',' ')
                    print(f"    [{kw}] ...{ctx_str}...")
                    break  # 只第一个

    # 也直接从 webpack 缓存读 module 39193
    print("\n=== 3. 直接从 webpack 读 module 39193 ===")
    mod_src = page.evaluate('''() => {
        try {
            // Next.js webpack chunk
            const chunks = window.webpackChunk_N_E || [];
            let found = null;
            for (const c of chunks) {
                if (c[1] && c[1][39193]) {
                    found = c[1][39193].toString().slice(0, 8000);
                    break;
                }
            }
            return found;
        } catch(e) { return 'ERR: ' + e.message; }
    }''')
    if mod_src and mod_src != 'null' and not mod_src.startswith('ERR'):
        print(f"  module 39193 ({len(mod_src)} chars):")
        print(mod_src[:3000])
    else:
        print(f"  mod_src: {mod_src}")

    ctx.close(); browser.close()
print("\nDONE")
