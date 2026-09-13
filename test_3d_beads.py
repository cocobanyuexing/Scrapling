"""精准在编辑器网格上点击放置豆子，然后开 3D 预览。"""
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

    print("\n=== 1. 新建空白项目 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.locator('button[aria-label="新建"]').first.click(timeout=3000)
    page.wait_for_timeout(1500)
    page.locator('button:has-text("新建空白项目")').first.click(timeout=3000)
    page.wait_for_timeout(2000)
    page.locator('button:has-text("创建")').last.click(timeout=3000)
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    print("\n=== 2. 找主画布 + 选画笔 + 选颜色 ===")
    # 找最大的 2D canvas (是编辑器主画布)
    canvas_info = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')];
        const info = cs.map((c, i) => {
            const r = c.getBoundingClientRect();
            return {idx: i, w: c.width, h: c.height, x: r.x, y: r.y, cw: r.width, ch: r.height};
        });
        return info;
    }''')
    print(f"  所有 canvas: {canvas_info}")

    # 选画笔 (title 含 画笔)
    page.locator('button[title*="画笔"], button[title*="Brush"]').first.click(timeout=3000)
    page.wait_for_timeout(800)
    print("  ✓ 画笔已选")

    # 选一个红色或黑色色块 - 找色板第一个色块
    swatch_info = page.evaluate(r'''() => {
        // 色号面板：button[title] 包含色号，或有 data-color 之类
        const cs = [...document.querySelectorAll('button')].filter(b => {
            const ti = b.getAttribute('title') || '';
            const cls = (b.className || '').toString();
            // 色号 button 通常 title 是色号字符串如 "H1" "C23" 等
            return /^[A-Z]\d+/.test(ti) || /color-swatch|palette/.test(cls);
        });
        return cs.slice(0, 10).map(b => ({
            title: b.getAttribute('title') || '',
            cls: (b.className || '').toString().slice(0, 60),
            inner: b.innerHTML.slice(0, 100)
        }));
    }''')
    print(f"  色号按钮候选: {swatch_info}")

    # 直接点第一个色号按钮
    swatch_clicked = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('button')].filter(b => {
            const ti = b.getAttribute('title') || '';
            return /^[A-Z]\d+/.test(ti);
        });
        if (cs.length > 0) {
            cs[0].click();
            return {count: cs.length, picked: cs[0].getAttribute('title')};
        }
        return {count: 0};
    }''')
    print(f"  点色号: {swatch_clicked}")
    page.wait_for_timeout(500)

    # 在编辑器主画布上单击放置豆子（不要拖动）
    # 找编辑器 canvas（最大的）
    main_canvas = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')].filter(c => c.width > 500);
        // 最大的那个是编辑器
        cs.sort((a, b) => b.width * b.height - a.width * a.height);
        if (cs.length === 0) return null;
        const c = cs[0];
        const r = c.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height, cx: r.x + r.width/2, cy: r.y + r.height/2};
    }''')
    print(f"  主画布: {main_canvas}")

    if main_canvas:
        cx, cy = main_canvas['cx'], main_canvas['cy']
        # 单击放豆
        print(f"\n=== 3. 在 ({cx:.0f}, {cy:.0f}) 单击放豆 ===")
        # 多次点击在不同位置，画一个十字图案
        points = [(cx, cy)]
        for d in [10, 20, 30, 40, 50]:
            points.append((cx + d, cy))
            points.append((cx - d, cy))
            points.append((cx, cy + d))
            points.append((cx, cy - d))
        for i, (x, y) in enumerate(points):
            page.mouse.move(x, y)
            page.wait_for_timeout(50)
            page.mouse.click(x, y)
            page.wait_for_timeout(80)
        print(f"  ✓ 单击了 {len(points)} 个点")

    page.wait_for_timeout(1000)
    page.screenshot(path='/workspace/ed_after_beads.png')

    # 看画布内容
    cnt = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')].filter(c => c.width > 500 && c.width < 1500);
        return cs.map((c, i) => {
            try {
                const ctx = c.getContext('2d');
                if (!ctx) return {idx: i, w: c.width, h: c.height, err: 'no 2d ctx'};
                // 扫描中心区域
                const cx = c.width/2, cy = c.height/2;
                const data = ctx.getImageData(cx-100, cy-100, 200, 200).data;
                let nonZero = 0;
                let colors = new Set();
                for (let i = 0; i < data.length; i += 4) {
                    if (data[i+3] > 0) {
                        nonZero++;
                        colors.add(`${data[i]},${data[i+1]},${data[i+2]}`);
                    }
                }
                return {idx: i, w: c.width, h: c.height, nonZero, uniqueColors: colors.size, sampleColors: [...colors].slice(0, 5)};
            } catch(e) { return {idx: i, err: String(e)}; }
        });
    }''')
    print(f"  画布像素: {cnt}")

    print("\n=== 4. 开 3D 预览 ===")
    page.locator('button[title="3D 预览"], button:has-text("3D 预览")').first.click(timeout=3000)
    # 等 3D 生成（最长 30s）
    for i in range(10):
        page.wait_for_timeout(3000)
        # 看处理进度
        progress = page.evaluate(r'''() => {
            const text = document.body.innerText;
            const m = text.match(/处理中[^\n]*?(\d+)%/);
            return m ? m[1] : (text.includes('处理中') ? 'pending' : 'no-proc-text');
        }''')
        print(f"  [{(i+1)*3}s] 进度: {progress}")
        if progress == 'no-proc-text':
            # 没有处理中文本 = 可能已完成或没启动
            break

    page.screenshot(path='/workspace/ed_3d_with_beads.png')

    # 看 webgl canvas 像素 (用 toDataURL 转 base64 比对)
    canvases = page.evaluate(r'''() => {
        const cs = [...document.querySelectorAll('canvas')];
        return cs.map((c, i) => {
            let type = 'none';
            try { if(c.getContext('webgl2')) type='webgl2'; else if(c.getContext('webgl')) type='webgl'; else if(c.getContext('2d')) type='2d'; } catch(e){}
            // 看大小判断
            const r = c.getBoundingClientRect();
            return {idx: i, w: c.width, h: c.height, type, vw: r.width, vh: r.height, visible: r.width > 0 && r.height > 0};
        });
    }''')
    print(f"  canvas 列表: {canvases}")

    # 切三工艺对比截图
    print("\n=== 5. 切三工艺对比 ===")
    for mode in ['拼豆', '烫豆', '毛巾烫']:
        loc = page.locator(f'button:has-text("{mode}")').first
        if loc.count() > 0:
            try:
                loc.click(timeout=3000)
                page.wait_for_timeout(3000)
                page.screenshot(path=f'/workspace/ed_3d_v2_{mode}.png')
                print(f"  ✓ {mode} 已截")
            except Exception as e:
                print(f"  {mode}: {e}")

    browser.close()
