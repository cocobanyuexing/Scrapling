"""抓 chunk 9308 (SmartImportModal 向导逻辑) 源码并保存"""
from patchright.sync_api import sync_playwright
import os, re

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(locale='zh-CN')
    page = ctx.new_page()

    # 拦截 chunk
    chunks = {}
    def on_resp(resp):
        u = resp.url
        if '/_next/static/chunks/' in u and '.js' in u:
            try:
                chunks[u.split('/')[-1]] = resp.text()
            except: pass
    page.on('response', on_resp)

    # 登录
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => b.innerText && (b.innerText.trim() === '登录' || b.innerText.trim() === '登入'));
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill('aq.jinlong@163.com', timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill('abc123456', timeout=5000)
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

    # 进 create + 触发 smartImport
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.locator('input[type="file"][accept*="image"]').nth(2).set_input_files('/workspace/测试图.jpg')
    page.wait_for_timeout(5000)

    # 保存所有抓到的 chunk
    print(f"抓到 {len(chunks)} 个 chunk")
    for fn, src in chunks.items():
        if any(k in src for k in ['SmartImport','MardCnn','ModeSelect','recogni','perler-pattern','pattern-recog']):
            path = f'/workspace/chunk_{fn}'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(src)
            print(f"  ✓ 保存 {fn} ({len(src)} chars) -> {path}")
            # 打印 API 端点
            apis = sorted(set(re.findall(r'["\'](/v1/[a-zA-Z0-9/_-]+)["\']', src)))
            if apis:
                print(f"    API: {apis}")
            for kw in ['MardCnn','mard-cnn','recogni','upload','scan','cnn','grid','palette','ModeSelect','ColorData','GridAlign','Verification']:
                m = re.search(kw, src, re.IGNORECASE)
                if m:
                    i = m.start()
                    print(f"    [{kw}]: ...{src[max(0,i-50):i+100]}...")

    ctx.close(); browser.close()
print("DONE")
