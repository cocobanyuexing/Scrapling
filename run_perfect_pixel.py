"""perfect-pixel 上传像素画结果图 + 修正 + 下载结果，全程记录 XHR。"""
from patchright.sync_api import sync_playwright
import json
import base64

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
INPUT_IMG = '/workspace/pixelart_result.webp'  # 上一步 ai-pixel-art 的结果图

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

    print("\n=== 1. 导航 /tools/perfect-pixel ===")
    page.goto('https://i2tools.com/tools/perfect-pixel', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1000)
    print(f"  URL: {page.url}")

    print("\n=== 2. 上传像素画结果图 ===")
    file_input = page.locator('input[type="file"]').first
    print(f"  file input count: {file_input.count()}")
    file_input.set_input_files(INPUT_IMG)
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/pp_uploaded.png')
    # 看上传后状态
    up = page.evaluate('''() => {
        const body = document.body.innerText.slice(0, 600);
        const canvases = document.querySelectorAll('canvas').length;
        const imgs = [...document.querySelectorAll('img')].map(i => ({src: i.src.slice(0, 80), w: i.naturalWidth, h: i.naturalHeight})).filter(x => x.w > 0).slice(0, 5);
        return {body, canvases, imgs};
    }''')
    print(f"  body 前600:\n{up['body']}")
    print(f"  canvases: {up['canvases']}")
    print(f"  imgs: {up['imgs']}")

    print("\n=== 3. 点「开始修正」 ===")
    clicked = False
    for txt in ['开始修正', '開始修正', '修正']:
        loc = page.locator(f'button:has-text("{txt}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=5000)
                print(f"  ✓ 点了「{txt}」")
                clicked = True
                break
            except Exception as e:
                print(f"  {txt} 失败: {e}")
    if not clicked:
        print("  ✗ 没找到修正按钮")

    # 等待修正完成（最多 60s）
    print("\n=== 4. 等待修正完成（最多 60s）===")
    for i in range(12):
        page.wait_for_timeout(5000)
        st = page.evaluate('''() => {
            const t = document.body.innerText;
            const done = /修正完成|完成|成功|已生成/.test(t);
            const processing = /修正中|处理中|进行中|生成中/.test(t);
            const canvases = [...document.querySelectorAll('canvas')].map(c => ({w: c.width, h: c.height})).filter(c => c.w > 0);
            const err = [...document.querySelectorAll('*')].map(el => el.innerText?.trim() || '').filter(t => t && t.length < 80 && /错误|失败|失败|error|fail/i.test(t)).slice(0, 3);
            return {done, processing, canvases, err, snip: t.slice(0, 150)};
        }''')
        print(f"  [{(i+1)*5}s] done={st['done']} processing={st['processing']} canvases={st['canvases']} err={st['err']}")
        if st['done'] and not st['processing']:
            print(f"    ✓ 修正完成")
            break
        if st['err']:
            print(f"    错误提示: {st['err']}")
    page.screenshot(path='/workspace/pp_result.png')

    # 看结果区 canvas
    print("\n=== 5. 提取修正结果 ===")
    res = page.evaluate('''() => {
        // 结果区一般在"修正结果"标题之后
        const allCanvas = [...document.querySelectorAll('canvas')];
        const allImg = [...document.querySelectorAll('img')].filter(i => i.src && i.naturalWidth > 0);
        return {
            canvasCount: allCanvas.length,
            canvases: allCanvas.map(c => ({w: c.width, h: c.height})),
            imgs: allImg.map(i => ({src: i.src.slice(0, 100), w: i.naturalWidth, h: i.naturalHeight}))
        };
    }''')
    print(f"  canvases: {res['canvasCount']} 个 {res['canvases']}")
    print(f"  imgs: {res['imgs']}")

    # 尝试从结果 canvas 导出
    print("\n=== 6. 导出结果 canvas ===")
    # 通常第 2 个 canvas 是结果（第 1 个是原图）
    canvases_info = page.evaluate('''() => {
        const cs = [...document.querySelectorAll('canvas')];
        return cs.map((c, i) => {
            try {
                const ctx = c.getContext('2d');
                const hasContent = c.width > 0 && c.height > 0;
                return {idx: i, w: c.width, h: c.height, hasContent, dataUrl: hasContent ? c.toDataURL('image/png').slice(0, 50) + '...' : null};
            } catch(e) { return {idx: i, err: String(e)}; }
        });
    }''')
    print(f"  canvas 详情: {canvases_info}")

    # 导出最后一个有内容的 canvas 为 PNG
    print("\n=== 7. 下载结果 canvas 为 PNG ===")
    for idx in range(len(canvases_info) - 1, -1, -1):
        info = canvases_info[idx] if isinstance(canvases_info, list) and idx < len(canvases_info) else None
        if info and info.get('hasContent'):
            b64 = page.evaluate('''(idx) => {
                const c = document.querySelectorAll('canvas')[idx];
                if (!c || c.width === 0) return null;
                return c.toDataURL('image/png');
            }''', idx)
            if b64:
                data = b64.split(',', 1)[1]
                out = f'/workspace/perfectpixel_result_canvas{idx}.png'
                with open(out, 'wb') as f:
                    f.write(base64.b64decode(data))
                print(f"  ✓ canvas[{idx}] ({info['w']}x{info['h']}) 已保存到 {out}")
                break

    print(f"\n=== 8. 全部 XHR ({len(xhr_log)}) ===")
    for x in xhr_log:
        u = x['url']
        if any(k in u for k in ['pixel', 'perfect', 'correct', 'fix', 'recognition', 'points', 'upload', 'oss', 'r2']) or 'i2tools.com/v1' in u:
            print(f"\n  {x['method']} {u[:130]}")
            print(f"    状态: {x['status']}")
            if 'req' in x:
                print(f"    请求: {x['req']}")
            if 'body' in x:
                print(f"    响应: {x['body']}")

    browser.close()
