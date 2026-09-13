"""用现有 pixelart_result.webp 跑 ai-pixel-art，进编辑器拿真实豆子数据再开 3D 预览。"""
from patchright.sync_api import sync_playwright
import os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/pixelart_result.webp'

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

    print("\n=== 1. 进 ai-pixel-art 工具 ===")
    page.goto('https://i2tools.com/tools/ai-pixel-art', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    print(f"  URL: {page.url}")

    print("\n=== 2. 上传图片 ===")
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(IMG)
    page.wait_for_timeout(3000)
    print("  ✓ 上传完成")
    page.screenshot(path='/workspace/real_uploaded.png')

    # 选小尺寸（少豆数快）
    print("\n=== 3. 选最小尺寸 ===")
    # 点预设标签
    try:
        page.locator('text=预设').first.click(timeout=3000)
        page.wait_for_timeout(500)
    except: pass
    # 点最小尺寸 32 或 30
    for sz in ['30', '32', '25', '20', '16']:
        loc = page.locator(f'button:has-text("{sz}"), [role="radio"]:has-text("{sz}")').first
        try:
            if loc.count() > 0:
                loc.click(timeout=3000)
                page.wait_for_timeout(500)
                print(f"  ✓ 选了 {sz}")
                break
        except Exception as e:
            print(f"  {sz}: {e}")

    print("\n=== 4. 点开始生成 ===")
    for txt in ['开始生成', '開始生成', '生成', '开始制作']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 点了「{txt}」")
                break
            except: pass

    print("\n=== 5. 等任务创建 + 跳转 ===")
    # 通常点击后会跳转到 /workspace/create 的任务详情页
    for i in range(20):
        page.wait_for_timeout(2000)
        url = page.url
        if '/task' in url or '/conversion' in url or '/result' in url or '/editor' in url:
            print(f"  [{(i+1)*2}s] 跳转: {url}")
            break
        # 检查页面上是否有任务进度
        body_chunk = page.evaluate('document.body.innerText.slice(0, 300)')
        if '处理中' in body_chunk or 'SUCCESS' in body_chunk or '完成' in body_chunk:
            print(f"  [{(i+1)*2}s] {body_chunk[:80]}")
    page.screenshot(path='/workspace/real_progress.png')
    print(f"  当前 URL: {page.url}")

    # 看页面内容
    info = page.evaluate(r'''() => ({
        url: location.href,
        body: document.body.innerText.slice(0, 1200),
        btns: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(t => t && t.length < 30).slice(0, 30)
    })''')
    print(f"\n  body:\n{info['body']}")
    print(f"\n  按钮: {info['btns']}")

    # 找"继续编辑"或"创建项目"按钮
    print("\n=== 6. 找「继续编辑」/「创建项目」按钮 ===")
    edit_btn_clicked = False
    for txt in ['继续编辑', '创建项目', '在编辑器中打开', '进入编辑器', '继续制作']:
        loc = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(5000)
                print(f"  ✓ 点了「{txt}」 -> {page.url}")
                edit_btn_clicked = True
                break
            except: pass

    # 如果还在结果页，等任务完成
    if not edit_btn_clicked:
        print("\n  等任务完成...")
        for i in range(60):
            page.wait_for_timeout(3000)
            status = page.evaluate(r'''() => {
                const t = document.body.innerText;
                if (t.includes('SUCCESS') || t.includes('已完成') || t.includes('继续编辑') || t.includes('创建项目')) return 'done';
                if (t.includes('处理中') || t.includes('PROCESSING') || t.includes('PENDING')) return 'processing';
                if (t.includes('FAILED') || t.includes('失败')) return 'failed';
                return 'unknown';
            }''')
            if status == 'done' or status == 'failed':
                print(f"  [{(i+1)*3}s] {status}")
                break
            if (i+1) % 5 == 0:
                print(f"  [{(i+1)*3}s] {status}")
        # 再找按钮
        for txt in ['继续编辑', '创建项目', '在编辑器中打开', '进入编辑器', '继续制作']:
            loc = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}")').first
            if loc.count() > 0:
                try:
                    loc.click(timeout=3000)
                    page.wait_for_timeout(5000)
                    print(f"  ✓ 点了「{txt}」 -> {page.url}")
                    edit_btn_clicked = True
                    break
                except: pass

    page.screenshot(path='/workspace/real_in_editor.png')
    print(f"\n  最终 URL: {page.url}")
    print(f"  title: {page.title()}")

    # 如果有「应用」按钮（网格对齐对话框），点应用
    print("\n=== 6b. 点「应用」进入编辑器 ===")
    for _ in range(3):
        loc = page.locator('button:has-text("应用")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(5000)
                print(f"  ✓ 点了「应用」 -> {page.url}")
                # 进入编辑器后退出循环
                if '/editor' in page.url:
                    break
            except: pass
        page.wait_for_timeout(2000)
    page.screenshot(path='/workspace/real_in_editor2.png')

    # 看是否进了编辑器
    ed_info = page.evaluate(r'''() => ({
        body: document.body.innerText.slice(0, 800),
        bead_count_text: (() => {
            const m = document.body.innerText.match(/色号统计[\s\S]*?(\d[\d,]*)/);
            return m ? m[1] : null;
        })(),
        canvas: [...document.querySelectorAll('canvas')].map(c => ({w:c.width, h:c.height}))
    })''')
    print(f"\n  body 前 800:\n{ed_info['body']}")
    print(f"\n  色号统计: {ed_info['bead_count_text']}")
    print(f"  canvas: {ed_info['canvas']}")

    # 如果进了编辑器，开 3D
    if '/editor' in page.url:
        print("\n=== 7. 开 3D 预览 ===")
        page.locator('button[title="3D 预览"], button:has-text("3D 预览")').first.click(timeout=3000)
        for i in range(15):
            page.wait_for_timeout(2000)
            progress = page.evaluate(r'''() => {
                const t = document.body.innerText;
                const m = t.match(/处理中[^\n]*?(\d+)%/);
                if (m) return m[1] + '%';
                if (t.includes('处理中')) return 'pending';
                return 'done';
            }''')
            print(f"  [{(i+1)*2}s] {progress}")
            if progress == 'done':
                break
        page.screenshot(path='/workspace/real_3d.png')
        print("  ✓ 3D 截图保存")
        # 切三工艺对比
        for mode in ['拼豆', '烫豆', '毛巾烫']:
            loc = page.locator(f'button:has-text("{mode}")').first
            if loc.count() > 0:
                try:
                    loc.click(timeout=3000)
                    page.wait_for_timeout(2500)
                    page.screenshot(path=f'/workspace/real_3d_{mode}.png')
                    print(f"  ✓ {mode} 截图")
                except: pass

    print(f"\n=== XHR ({len(xhr_log)}) ===")
    for x in xhr_log[-15:]:
        if '/v1/' in x['url']:
            print(f"  {x['method']} {x['url'][:90]} [{x['status']}]")

    browser.close()
