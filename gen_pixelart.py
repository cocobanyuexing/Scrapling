"""ai-pixel-art 上传图片 + 生成像素画，全程记录 XHR。"""
from patchright.sync_api import sync_playwright
import json
import os
import glob

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

# 挑一张测试图（取第一张 webp）
imgs = sorted(glob.glob('/workspace/i2tools/gallery-images/*.webp'))
TEST_IMG = imgs[0]
print(f"测试图: {TEST_IMG}  ({os.path.getsize(TEST_IMG)} bytes)")

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
                    x['req'] = req_body[:500]
                ct = resp.headers.get('content-type', '')
                if 'json' in ct:
                    x['body'] = resp.body()[:1500].decode('utf-8', errors='replace')
            except Exception:
                pass
            xhr_log.append(x)
    page.on('response', on_response)

    print("=== 0. 中文版首页 + 登录 ===")
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
    print(f"  登录后 URL: {page.url}")

    print("\n=== 1. 导航 /tools/ai-pixel-art ===")
    page.goto('https://i2tools.com/tools/ai-pixel-art', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1000)
    page.screenshot(path='/workspace/apa_init.png')
    print(f"  URL: {page.url}")

    # 找上传 input
    file_input = page.locator('input[type="file"]').first
    print(f"  file input count: {file_input.count()}")

    print("\n=== 2. 上传图片 ===")
    file_input.set_input_files(TEST_IMG)
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/apa_uploaded.png')
    # 看上传后状态
    up_state = page.evaluate('''() => {
        const body = document.body.innerText.slice(0, 600);
        // 找上传后的图片预览
        const imgs = [...document.querySelectorAll('img')].map(i => i.src).filter(s => s && (s.includes('oss') || s.includes('blob:') || s.includes('i2tools'))).slice(0, 5);
        return {body, imgs};
    }''')
    print(f"  body 前600:\n{up_state['body']}")
    print(f"  预览图: {up_state['imgs']}")

    print("\n=== 3. 选预设尺寸 50 ===")
    # 点"预设"模式 + 选 50
    try:
        # 先点"预设"标签
        loc = page.locator('text=预设').first
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(500)
            print("  ✓ 点了「预设」")
    except Exception as e:
        print(f"  预设点击: {e}")
    try:
        # 点 50
        loc = page.locator('button:has-text("50"), [role="radio"]:has-text("50"), text=50').first
        if loc.count() > 0:
            loc.click(timeout=3000)
            page.wait_for_timeout(500)
            print("  ✓ 选了 50")
    except Exception as e:
        print(f"  50 点击: {e}")
    page.screenshot(path='/workspace/apa_sized.png')

    print("\n=== 4. 点「开始生成」 ===")
    clicked_gen = False
    for txt in ['开始生成', '開始生成', '生成']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 点了「{txt}」")
                clicked_gen = True
                break
            except Exception as e:
                print(f"  {txt} 失败: {e}")
    if not clicked_gen:
        print("  ✗ 没找到生成按钮，截图排查")
        page.screenshot(path='/workspace/apa_nogenbtn.png')

    # 等待生成（轮询最多 90s）
    print("\n=== 5. 等待生成完成（最多 90s）===")
    for i in range(18):
        page.wait_for_timeout(5000)
        # 看页面是否出现"下载"或"完成"或结果图
        st = page.evaluate('''() => {
            const t = document.body.innerText;
            const done = /完成|下载|成功|已生成|生成成功/.test(t);
            const processing = /生成中|处理中|排队|PROCESSING|PENDING/.test(t);
            // 结果图
            const resultImgs = [...document.querySelectorAll('img')].map(i=>i.src).filter(s=>s && s.includes('oss')).slice(-3);
            return {done, processing, resultImgs, snip: t.slice(0,200)};
        }''')
        print(f"  [{(i+1)*5}s] done={st['done']} processing={st['processing']} imgs={len(st['resultImgs'])}")
        if st['done'] and not st['processing']:
            print(f"    ✓ 生成完成")
            print(f"    结果图: {st['resultImgs']}")
            break
    page.screenshot(path='/workspace/apa_result.png')

    print(f"\n=== 6. 全部 XHR ({len(xhr_log)}) ===")
    # 只关注关键 API
    for x in xhr_log:
        u = x['url']
        if any(k in u for k in ['conversions','points','oss','upload','pixel-art','auth/info']):
            print(f"\n  {x['method']} {u[:130]}")
            print(f"    状态: {x['status']}")
            if 'req' in x:
                print(f"    请求: {x['req']}")
            if 'body' in x:
                print(f"    响应: {x['body']}")

    browser.close()
