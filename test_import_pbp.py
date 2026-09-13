"""实测：导入项目 .pbp
路径: /workspace/create -> 点 "导入项目" 卡 -> 隐藏 input accept=".pbp" -> R(t) 解密建项目 -> 跳编辑器
样本: /workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'

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

    print("=== 0. 登录 + 关弹窗 ===")
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
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape')
        page.wait_for_timeout(700)
    print(f"  登录后 URL: {page.url}")

    print("\n=== 1. 进 /workspace/create 创建页 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)
    print(f"  URL: {page.url}")
    page.screenshot(path='/workspace/pbp_1_create.png')

    # 看卡片
    cards = page.evaluate('''() => {
        return [...document.querySelectorAll('[class*="card"], button, [role="button"], div')].map(el => {
            const t = (el.innerText||'').trim();
            return t;
        }).filter(t => t && t.length < 40 && (t.includes('导入') || t.includes('项目') || t.includes('图片') || t.includes('智能') || t.includes('小红书') || t.includes('空白')));
    }''')
    print(f"  候选卡片文案: {cards[:15]}")

    print("\n=== 2. 找 .pbp 隐藏 input + 直接 setInputFiles ===")
    # 隐藏 input accept=".pbp"
    inp = page.locator('input[type="file"][accept=".pbp"]').first
    print(f"  input.pbp count: {inp.count()}")
    if inp.count() == 0:
        print("  ❌ 找不到 .pbp input, dump 页面")
        page.screenshot(path='/workspace/pbp_2_noinp.png')
    else:
        # 直接给隐藏 input 设文件（绕过点击卡片，模拟选中文件）
        inp.set_input_files(PBP)
        print(f"  ✓ 已 setInputFiles: {os.path.basename(PBP)}")
        page.wait_for_timeout(8000)  # 等解密 + 建项目 + 跳转

        print(f"\n  跳转后 URL: {page.url}")
        page.screenshot(path='/workspace/pbp_3_after_import.png')

        # 看是否进了编辑器
        ed = page.evaluate('''() => ({
            url: location.href,
            title: document.title,
            canvas_count: document.querySelectorAll('canvas').length,
            body_head: document.body.innerText.slice(0, 300)
        })''')
        print(f"  title: {ed['title']}")
        print(f"  canvas: {ed['canvas_count']}")
        print(f"  body 前300:\n{ed['body_head']}")

        print("\n=== 3. 检查 IndexedDB 是否多了项目 ===")
        idb = page.evaluate('''async () => {
            try {
                const db = await new Promise((res, rej) => {
                    const r = indexedDB.open('magic-perler-projects');
                    r.onsuccess = () => res(r.result);
                    r.onerror = () => rej(r.error);
                });
                // 列出所有 store
                const stores = [...db.objectStoreNames];
                const out = {};
                for (const sname of ['projects','project_snapshots']) {
                    if (!stores.includes(sname)) continue;
                    const tx = db.transaction(sname, 'readonly');
                    const all = await new Promise((res, rej) => {
                        const r = tx.objectStore(sname).getAll();
                        r.onsuccess = () => res(r.result);
                        r.onerror = () => rej(r.error);
                    });
                    out[sname] = (all||[]).map(p => ({
                        id: p.id,
                        name: p.name,
                        gridDimensions: p.gridDimensions,
                        totalBeadCount: p.totalBeadCount,
                        dataVersion: p.dataVersion,
                        layer_count: p.layers ? p.layers.length : null,
                        layer_types: p.layers ? p.layers.map(l=>l.type) : null,
                        originalAssetId: p.originalAssetId,
                        updatedAt: p.updatedAt,
                        createdAt: p.createdAt
                    }));
                }
                return {stores, projects: out};
            } catch(e) { return {error: e.message}; }
        }''')
        print(f"  IDB stores: {idb.get('stores')}")
        projs = idb.get('projects', {}).get('projects', [])
        print(f"  IDB projects count: {len(projs)}")
        for p in projs[-5:]:
            print(f"    - {p.get('name')} | {p.get('gridDimensions')} | beads={p.get('totalBeadCount')} | layers={p.get('layer_types')} | dv={p.get('dataVersion')}")

    print("\n=== 4. XHR 摘要 ===")
    for x in xhr_log[-20:]:
        print(f"  {x['status']} {x['method']} {x['url'][:110]}")

    ctx.close()
    browser.close()
print("\nDONE")
