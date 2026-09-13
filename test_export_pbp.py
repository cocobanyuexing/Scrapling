"""修正：先在 ai-pixel-art 选已存在任务的创建项目，进编辑器导出 .pbp。"""
from patchright.sync_api import sync_playwright
import os

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
DOWNLOAD_DIR = '/workspace/samples'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 900},
        locale='zh-CN',
        accept_downloads=True
    )
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

    print("\n=== 1. 进 ai-pixel-art 看历史任务 ===")
    page.goto('https://i2tools.com/tools/ai-pixel-art', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape')
        page.wait_for_timeout(500)

    # 看页面所有按钮
    btns_all = page.evaluate(r'''() => [...document.querySelectorAll('button')].map(b => ({
        text: (b.innerText||'').trim().slice(0, 30),
        aria: b.getAttribute('aria-label') || '',
        title: b.getAttribute('title') || '',
        disabled: b.disabled
    })).filter(x => x.text || x.aria || x.title)''')
    print(f"  页面按钮 ({len(btns_all)}): ")
    for b in btns_all[:30]:
        print(f"    {b}")

    # 找所有「创建项目」按钮，包括 disabled
    create_btns = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('button, a')].filter(b => /创建项目/.test((b.innerText||'') + (b.getAttribute('title')||'')));
        return all.map(b => ({
            tag: b.tagName,
            text: (b.innerText||'').trim(),
            disabled: b.disabled,
            aria: b.getAttribute('aria-label') || '',
            cls: (b.className||'').toString().slice(0, 80)
        }));
    }''')
    print(f"\n  「创建项目」按钮: {create_btns}")

    # 直接点第一个「创建项目」按钮（已 4 个都可用）
    print("\n=== 2. 直接点第一个「创建项目」 ===")
    loc = page.locator('button[aria-label="创建项目"]').first
    if loc.count() > 0:
        loc.click(timeout=3000)
        page.wait_for_timeout(3000)
        print(f"  -> {page.url}")
        # 点应用
        loc2 = page.locator('button:has-text("应用")').first
        if loc2.count() > 0:
            loc2.click(timeout=3000)
            page.wait_for_timeout(5000)
            print(f"  ✓ 进编辑器: {page.url}")

    page.screenshot(path='/workspace/ed_in_editor.png')

    print("\n=== 3. 在编辑器找导出作品按钮 ===")
    # 看顶部 navbar 所有按钮
    navbar_btns = page.evaluate(r'''() => {
        // 找顶栏的按钮
        const navs = [...document.querySelectorAll('nav, header, [class*="top-bar"], [class*="navbar"]')];
        const btns = [];
        for (const nav of navs) {
            for (const b of nav.querySelectorAll('button, a, [role="button"]')) {
                btns.push({
                    text: (b.innerText||'').trim().slice(0, 30),
                    aria: b.getAttribute('aria-label') || '',
                    title: b.getAttribute('title') || ''
                });
            }
        }
        return btns.filter(x => x.text || x.aria || x.title);
    }''')
    print(f"  navbar 按钮 ({len(navbar_btns)}): {navbar_btns[:30]}")

    # 全局找「导出」按钮
    export_all = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('button, a, [role="button"], [role="menuitem"]')];
        return all.filter(b => {
            const t = (b.innerText||'').trim();
            const a = b.getAttribute('aria-label') || '';
            const ti = b.getAttribute('title') || '';
            return /导出|export/i.test(t + a + ti);
        }).slice(0, 10).map(b => ({
            tag: b.tagName,
            text: (b.innerText||'').trim().slice(0, 30),
            aria: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || '',
            disabled: b.disabled
        }));
    }''')
    print(f"\n  导出按钮: {export_all}")

    # 找菜单触发器（aria-haspopup=menu 中不是语言的）
    menu_triggers = page.evaluate(r'''() => {
        const all = [...document.querySelectorAll('[aria-haspopup="menu"], [data-slot="dropdown-menu-trigger"]')];
        return all.filter(b => {
            const a = (b.getAttribute('aria-label') || '').toLowerCase();
            const t = (b.innerText || '').trim();
            return !/简体|繁體|english|日本|profile|个人资料/.test(a + t);
        }).slice(0, 5).map(b => ({
            tag: b.tagName,
            aria: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || '',
            text: (b.innerText||'').trim().slice(0, 30),
            cls: (b.className||'').toString().slice(0, 80)
        }));
    }''')
    print(f"\n  菜单触发器（非语言）: {menu_triggers}")

    # 试着点这些菜单触发器
    print("\n=== 4. 试触发菜单找导出 ===")
    for trigger in menu_triggers:
        aria = trigger.get('aria', '')
        title = trigger.get('title', '')
        try:
            if aria:
                loc = page.locator(f'button[aria-label="{aria}"]').first
            elif title:
                loc = page.locator(f'button[title="{title}"]').first
            else:
                continue
            if loc.count() > 0:
                loc.click(timeout=2000)
                page.wait_for_timeout(1500)
                # 看菜单项
                menu_items = page.evaluate(r'''() => [...document.querySelectorAll('[role="menuitem"]')].map(b => (b.innerText||'').trim()).filter(t => t)''')
                if menu_items:
                    print(f"  「{aria or title}」菜单: {menu_items}")
                    # 找导出
                    for item in menu_items:
                        if '导出' in item:
                            print(f"  ✓ 找到导出项: {item}")
                            try:
                                with page.expect_download(timeout=10000) as download_info:
                                    page.locator(f'[role="menuitem"]:has-text("导出")').first.click(timeout=3000)
                                download = download_info.value
                                save_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
                                download.save_as(save_path)
                                print(f"  ✓ 下载: {save_path}, 大小: {os.path.getsize(save_path)}")
                            except Exception as e:
                                print(f"  导出下载: {e}")
                                # 可能不是下载而是弹窗选择
                                page.wait_for_timeout(2000)
                                page.screenshot(path='/workspace/ed_export_dialog.png')
                                # 看弹窗
                                dialog = page.evaluate(r'''() => {
                                    const dlgs = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"]')];
                                    const vis = dlgs.filter(d => d.offsetParent !== null);
                                    return vis.length > 0 ? vis[0].innerText.slice(0, 600) : 'no visible dialog';
                                }''')
                                print(f"  导出弹窗: {dialog}")
                            break
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(500)
        except Exception as e:
            print(f"  {aria or title}: {e}")
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)

    browser.close()
