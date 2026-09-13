"""perfect-pixel 修正 + 点「创建项目继续编辑」保存项目，记录后端 API。"""
from patchright.sync_api import sync_playwright
import json

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
INPUT_IMG = '/workspace/pixelart_result.webp'

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
                    x['req'] = req_body[:600]
                ct = resp.headers.get('content-type', '')
                if 'json' in ct:
                    x['body'] = resp.body()[:1500].decode('utf-8', errors='replace')
            except Exception:
                pass
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
    except Exception as e:
        print(f"  checkbox: {e}")
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(5000)

    print("\n=== 1. perfect-pixel 上传 + 修正 ===")
    page.goto('https://i2tools.com/tools/perfect-pixel', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1000)
    page.locator('input[type="file"]').first.set_input_files(INPUT_IMG)
    page.wait_for_timeout(3000)
    # 点修正
    for txt in ['开始修正', '開始修正', '修正']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000)
            print(f"  ✓ 点了「{txt}」")
            break
    # 等修正结果 canvas 出现（第二个 canvas 有内容）
    print("  等待修正完成...")
    for i in range(20):
        page.wait_for_timeout(3000)
        n = page.evaluate('''() => {
            const cs = [...document.querySelectorAll('canvas')];
            // 第二个 canvas 是结果，要有内容
            if (cs.length >= 2) {
                try {
                    const ctx = cs[1].getContext('2d');
                    const d = ctx.getImageData(0, 0, Math.min(cs[1].width, 10), Math.min(cs[1].height, 10)).data;
                    // 看是否有非透明像素
                    let nonZero = 0;
                    for (let j = 0; j < d.length; j += 4) {
                        if (d[j+3] > 0) nonZero++;
                    }
                    return {cnt: cs.length, hasResult: nonZero > 0, w: cs[1].width, h: cs[1].height};
                } catch(e) { return {cnt: cs.length, err: String(e)}; }
            }
            return {cnt: cs.length};
        }''')
        print(f"    [{(i+1)*3}s] {n}")
        if n.get('hasResult'):
            print("    ✓ 修正结果已生成")
            break

    page.screenshot(path='/workspace/pp_before_save.png')

    print("\n=== 2. 点「创建项目继续编辑」 ===")
    clicked_save = False
    for txt in ['创建项目继续编辑', '創建項目繼續編輯', '创建项目', '继续编辑']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 点了「{txt}」")
                clicked_save = True
                break
            except Exception as e:
                print(f"  {txt}: {e}")
    if not clicked_save:
        print("  ✗ 没找到保存按钮")
        # 看所有按钮
        btns = page.evaluate('''() => [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean)''')
        print(f"  当前所有按钮: {btns}")

    # 等待跳转 + 项目保存
    print("\n=== 3. 等待跳转到编辑器 / 项目保存 ===")
    for i in range(12):
        page.wait_for_timeout(3000)
        url = page.url
        print(f"  [{(i+1)*3}s] URL: {url}")
        if '/workspace/create/' in url or '/editor' in url or '/workspace/project' in url:
            print(f"    ✓ 已跳转到编辑器/项目页")
            break

    page.screenshot(path='/workspace/pp_after_save.png')
    print(f"  最终 URL: {page.url}")

    # 看当前页面状态
    info = page.evaluate('''() => ({
        url: location.href,
        title: document.title,
        body: document.body.innerText.slice(0, 500)
    })''')
    print(f"\n  页面标题: {info['title']}")
    print(f"  body 前500:\n{info['body']}")

    print(f"\n=== 4. 全部 XHR ({len(xhr_log)}) ===")
    # 重点看项目相关 API
    for x in xhr_log:
        u = x['url']
        if any(k in u for k in ['project', 'workspace', 'save', 'cloud', 'backup', 'pixel-art', 'perfect']) or '/v1/app' in u:
            print(f"\n  {x['method']} {u[:130]}")
            print(f"    状态: {x['status']}")
            if 'req' in x:
                print(f"    请求: {x['req']}")
            if 'body' in x:
                print(f"    响应: {x['body']}")

    browser.close()
