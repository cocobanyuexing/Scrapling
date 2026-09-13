"""实测 2 v3: 用 IndexedDB 抓 baseline 和 after 项目快照, 验证 layer 变化"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
PBP = '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp'

def body_head(page, n=600):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

def get_idb_stats(page):
    """通过 IndexedDB 取项目快照, 看色号统计"""
    return page.evaluate('''async () => {
        return new Promise((resolve) => {
            const req = indexedDB.open('magic-perler-projects');
            req.onsuccess = () => {
                const db = req.result;
                const tnames = Array.from(db.objectStoreNames);
                const result = {stores: tnames, projects: [], snapshots: []};
                // 读 projects
                try {
                    const tx = db.transaction(['projects'], 'readonly');
                    const store = tx.objectStore('projects');
                    const r = store.getAll();
                    r.onsuccess = () => {
                        for (const p of (r.result || [])) {
                            result.projects.push({
                                id: p.id,
                                name: p.name,
                                beadCount: p.totalBeadCount || p.beadCount,
                                gridN: p.gridDimensions?.N,
                                gridM: p.gridDimensions?.M,
                                colorCount: p.layers?.length || p.colorCounts?.length || p.colors?.length,
                                dataVersion: p.dataVersion,
                                pbpVersion: p.pbpVersion,
                                layers_length: p.layers?.length,
                                colorCounts_keys: p.colorCounts ? Object.keys(p.colorCounts).length : null,
                            });
                        }
                        resolve(result);
                    };
                    r.onerror = () => resolve(result);
                } catch(e) { resolve({err: String(e), ...result}); }
            };
            req.onerror = () => resolve({err: 'open failed'});
        });
    }''')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => {
            const t = (b.innerText||'').trim();
            return t === '登录' || t === '登入';
        });
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(2000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)

    print("\n=== 1. 导入 .pbp ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    inp = page.locator('input[type="file"][accept=".pbp"]').first
    if inp.count() == 0:
        inp = page.locator('input[type="file"][accept*="image"]').first
    inp.set_input_files(PBP)
    page.wait_for_timeout(8000)
    for i in range(10):
        if '/editor' in page.url: break
        page.wait_for_timeout(2000)
    page.wait_for_timeout(3000)
    print(f"  编辑器 URL: {page.url}")

    print("\n=== 2. baseline 项目 IDB 快照 ===")
    base = get_idb_stats(page)
    print(f"  项目数: {len(base.get('projects', []))}")
    for proj in base.get('projects', [])[-2:]:
        print(f"    {proj}")
    # UI 色号数
    body = body_head(page, 1500)
    import re
    m = re.search(r'(\d+)\s*色号', body)
    base_colors = m.group(1) if m else 'unknown'
    print(f"  UI 显示色号数: {base_colors}")

    print("\n=== 3. 点降噪 + 点确认 ===")
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        const target = bs.find(b => (b.innerText||'').trim() === '降噪');
        if (target) target.click();
    }''')
    page.wait_for_timeout(2500)
    modal_body = body_head(page, 800)
    print(f"  弹窗预计算(候选/预计处理/受保护):")
    # 抓候选/预计处理统计
    for kw in ['候选像素', '预计处理', '可清理', '受保护']:
        m = re.search(rf'{kw}[\s\S]{{0,30}}?(\d+)', modal_body)
        if m:
            print(f"    {kw}: {m.group(1)}")

    # 点确认 - 强制 evaluate click
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '确认' || t === '确定';
        });
        if (target) target.click();
    }''')
    print(f"  ✓ 点确认")

    print("\n=== 4. 等待算法执行 ===")
    for i in range(15):
        page.wait_for_timeout(1500)
        body = body_head(page, 200)
        if '处理中' not in body and i > 2:
            page.wait_for_timeout(2000)
            break

    print("\n=== 5. after 项目 IDB 快照 ===")
    after = get_idb_stats(page)
    print(f"  项目数: {len(after.get('projects', []))}")
    for proj in after.get('projects', [])[-2:]:
        print(f"    {proj}")
    body = body_head(page, 1500)
    m = re.search(r'(\d+)\s*色号', body)
    after_colors = m.group(1) if m else 'unknown'
    print(f"  UI 显示色号数: {after_colors}")

    print(f"\n=== 6. 对比 ===")
    print(f"  baseline UI 色号: {base_colors}")
    print(f"  after    UI 色号: {after_colors}")
    if base_colors != 'unknown' and after_colors != 'unknown' and base_colors != after_colors:
        print(f"  ✅ 色号数从 {base_colors} -> {after_colors} 变化, 算法真执行了!")
    else:
        print(f"  ⚠ 色号数未变化或无法对比")

    ctx.close(); browser.close()
print("\nDONE")
