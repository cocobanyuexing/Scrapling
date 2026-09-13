"""先在画布上画像素，再开 3D 预览，看实际 3D 渲染。"""
from patchright.sync_api import sync_playwright

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

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

    print("\n=== 1. 新建空白项目 50×50 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.locator('button[aria-label="新建"]').first.click(timeout=3000)
    page.wait_for_timeout(1500)
    page.locator('button:has-text("新建空白项目")').first.click(timeout=3000)
    page.wait_for_timeout(2000)
    # 默认 50×50，直接点创建
    page.locator('button:has-text("创建")').last.click(timeout=3000)
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    print("\n=== 2. 选画笔工具 + 选颜色 ===")
    # 选画笔 (F2)
    page.locator('button[title*="画笔"], button[title*="Brush"]').first.click(timeout=3000)
    page.wait_for_timeout(800)
    print("  ✓ 画笔已选")

    # 选个色号 (点第一个色块)
    # 用 page.evaluate 找颜色按钮，点第一个
    swatch_clicked = page.evaluate(r'''() => {
        // 找色号面板里的色块 button，点第一个非透明的
        const swatches = [...document.querySelectorAll('button, [role="button"]')].filter(b => {
            const cls = (b.className||'').toString();
            const s = b.querySelector('span, div');
            return s && s.style && (s.style.backgroundColor || s.style.background);
        });
        if (swatches.length > 0) {
            swatches[0].click();
            return {count: swatches.length, picked: true};
        }
        return {count: 0};
    }''')
    print(f"  色块: {swatch_clicked}")
    page.wait_for_timeout(500)

    # 直接在画布中心画一些像素
    print("\n=== 3. 在画布上画像素 ===")
    # 找主画布 canvas (2D，1280×836)
    canvas_box = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')].filter(c => c.width > 1000 && c.getContext('2d'));
        if (cs.length === 0) return null;
        const c = cs[0];
        const r = c.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height, cx: r.x + r.width/2, cy: r.y + r.height/2};
    }''')
    print(f"  主画布位置: {canvas_box}")

    if canvas_box:
        # 在中心区域画一个方块 (5×5 像素)
        cx, cy = canvas_box['cx'], canvas_box['cy']
        # 鼠标按下 + 移动（模拟拖动画笔）
        page.mouse.move(cx, cy)
        page.mouse.down()
        for dx in range(-40, 41, 8):
            for dy in range(-40, 41, 8):
                page.mouse.move(cx + dx, cy + dy)
        page.mouse.up()
        page.wait_for_timeout(800)
        print("  ✓ 已画像素块")
    
    page.screenshot(path='/workspace/ed_painted.png')

    # 看画了几个像素
    cnt = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')].filter(c => c.width > 1000 && c.getContext('2d'));
        if (cs.length === 0) return {err: 'no 2d canvas'};
        const c = cs[0];
        const ctx = c.getContext('2d');
        // 扫描中心 400×400 区域的非透明像素数
        const cx = c.width/2, cy = c.height/2;
        const data = ctx.getImageData(cx-200, cy-200, 400, 400).data;
        let nonZero = 0;
        for (let i = 3; i < data.length; i += 4) if (data[i] > 0) nonZero++;
        return {nonZero, sampleW: 400, sampleH: 400};
    }''')
    print(f"  画布中心区域非透明像素数: {cnt}")

    print("\n=== 4. 开 3D 预览 ===")
    # 用快捷键 / 按钮：点 button[title="3D 预览"]
    page.locator('button[title="3D 预览"], button:has-text("3D 预览")').first.click(timeout=3000)
    page.wait_for_timeout(5000)
    page.screenshot(path='/workspace/ed_3d_with_pixels.png')
    print("  ✓ 3D 预览已开")

    # 重看 3D 面板 canvas
    panel = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')].map(c => {
            let type='none';
            try { if(c.getContext('webgl2')) type='webgl2'; else if(c.getContext('webgl')) type='webgl'; else if(c.getContext('2d')) type='2d'; } catch(e){}
            // 看 webgl canvas 是否真的有内容（gl 判断）
            let hasContent = false;
            if (type === 'webgl2' || type === 'webgl') {
                const gl = c.getContext(type === 'webgl2' ? 'webgl2' : 'webgl');
                if (gl) {
                    // 读取一个像素
                    try {
                        const px = new Uint8Array(4);
                        gl.readPixels(c.width/2, c.height/2, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
                        hasContent = (px[0] + px[1] + px[2] + px[3]) > 0;
                        return {w: c.width, h: c.height, type, hasContent, pixel: [px[0], px[1], px[2], px[3]]};
                    } catch(e) { return {w: c.width, h: c.height, type, err: String(e)}; }
                }
            }
            return {w: c.width, h: c.height, type, hasContent};
        });
        return cs;
    }''')
    print(f"  canvas: {panel}")

    # 切三工艺
    print("\n=== 5. 切三工艺对比 ===")
    for mode in ['拼豆', '烫豆', '毛巾烫']:
        # 工艺按钮是 button:has-text
        loc = page.locator(f'button:has-text("{mode}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(3000)
                page.screenshot(path=f'/workspace/ed_3d_painted_{mode}.png')
                # 读 webgl canvas 中心像素
                px = page.evaluate(r'''(modeName) => {
                    const cs = [...document.querySelectorAll('canvas')].filter(c => {
                        try { return c.getContext('webgl2') && c.width > 500; } catch(e) { return false; }
                    });
                    if (cs.length === 0) return {err: 'no webgl2 canvas'};
                    const c = cs[0];
                    const gl = c.getContext('webgl2');
                    const px = new Uint8Array(4);
                    // 读多个采样点
                    const samples = [];
                    for (const [x, y] of [[c.width/2, c.height/2], [c.width/4, c.height/2], [c.width*3/4, c.height/2]]) {
                        gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
                        samples.push([px[0], px[1], px[2], px[3]]);
                    }
                    return {mode: modeName, samples};
                }''', mode)
                print(f"  ✓ {mode}: {px}")
            except Exception as e:
                print(f"  {mode}: {e}")

    print("\n=== 6. 关 3D 预览回到编辑器 ===")
    page.keyboard.press('Escape')
    page.wait_for_timeout(1500)

    browser.close()
