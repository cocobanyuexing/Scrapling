"""检查按钮 disabled 状态，并尝试通过 React state 触发后处理算法。"""
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

    print("=== 0. 登录 + 进 ai-pixel-art 创建项目 ===")
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

    # 直接进 ai-pixel-art 创建项目
    page.goto('https://i2tools.com/tools/ai-pixel-art', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    page.locator('button:has-text("创建项目")').first.click(timeout=3000)
    page.wait_for_timeout(3000)
    page.locator('button:has-text("应用")').first.click(timeout=3000)
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")

    print("\n=== 1. 检查后处理按钮 disabled 状态 ===")
    btns_state = page.evaluate(r'''() => {
        const titles = ['扣减库存', '色号合并', '去除杂色', '降噪'];
        return titles.map(t => {
            const b = document.querySelector(`button[title="${t}"]`);
            if (!b) return {title: t, found: false};
            return {
                title: t,
                found: true,
                disabled: b.disabled,
                ariaDisabled: b.getAttribute('aria-disabled'),
                ariaExpanded: b.getAttribute('aria-expanded'),
                dataState: b.getAttribute('data-state'),
                cls: (b.className||'').toString().slice(0, 100),
                parent: b.parentElement?.tagName + '.' + (b.parentElement?.className||'').toString().slice(0, 60)
            };
        });
    }''')
    for b in btns_state:
        print(f"  {b}")

    # 试着用 React 内部触发 - 先看 zustand store
    print("\n=== 2. 看 zustand store keys ===")
    store_keys = page.evaluate(r'''() => {
        // zustand 通常存在 module-level，react 内部 _store 字段
        const rootEl = document.getElementById('__next') || document.querySelector('#root, body');
        if (!rootEl) return {err: 'no root'};
        const reactKeys = Object.keys(rootEl).filter(k => k.startsWith('__react'));
        // 找内部 store
        let storeInfo = null;
        for (const k of reactKeys) {
            const v = rootEl[k];
            if (v && v.memoizedState) {
                // 这是 React fiber root
                storeInfo = {key: k, hasMemoizedState: true};
                break;
            }
        }
        return {reactKeys, storeInfo};
    }''')
    print(f"  {store_keys}")

    # 尝试用 page.locator + click + 等
    print("\n=== 3. 用真实 click 试「降噪」（无 force） ===")
    # 先点画布激活编辑器焦点
    page.mouse.click(640, 482)
    page.wait_for_timeout(500)

    for op in ['降噪', '去除杂色', '色号合并']:
        print(f"\n  --- 试 {op} ---")
        # 先 hover 让按钮可点击
        try:
            loc = page.locator(f'button[title="{op}"]').first
            loc.hover(timeout=2000)
            page.wait_for_timeout(300)
            btn_info = page.evaluate(r'''(op) => {
                const b = document.querySelector(`button[title="${op}"]`);
                if (!b) return null;
                const r = b.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height, cx: r.x + r.width/2, cy: r.y + r.height/2, disabled: b.disabled};
            }''', op)
            print(f"  按钮 rect: {btn_info}")
            if btn_info and not btn_info.get('disabled'):
                # 直接 dispatch pointer events
                ev_result = page.evaluate(r'''(op) => {
                    const b = document.querySelector(`button[title="${op}"]`);
                    if (!b) return {err: 'no btn'};
                    b.focus();
                    b.click();
                    return {clicked: true, ariaExpanded: b.getAttribute('aria-expanded'), ariaHasPopup: b.getAttribute('aria-haspopup')};
                }''', op)
                print(f"  click 结果: {ev_result}")
                page.wait_for_timeout(2000)
                # 看弹窗
                popup = page.evaluate(r'''() => {
                    // 找 popover / dropdown / inline panel
                    const pops = [...document.querySelectorAll('[data-slot="popover-content"], [data-slot="dropdown-content"], [role="tooltip"], [role="listbox"]')];
                    const visible = pops.filter(p => p.offsetParent !== null);
                    if (visible.length > 0) {
                        return visible.map(p => ({
                            slot: p.getAttribute('data-slot'),
                            body: p.innerText.slice(0, 500)
                        }));
                    }
                    // 找 dialog
                    const dlgs = [...document.querySelectorAll('[data-slot="dialog-content"], [role="dialog"]')];
                    const vis_dlgs = dlgs.filter(d => d.offsetParent !== null);
                    if (vis_dlgs.length > 0) {
                        return vis_dlgs.map(d => ({
                            slot: 'dialog',
                            body: d.innerText.slice(0, 500)
                        }));
                    }
                    return {none: true};
                }''')
                print(f"  弹出: {popup}")
                page.screenshot(path=f'/workspace/op2_{op}.png')
                page.keyboard.press('Escape')
                page.wait_for_timeout(500)
        except Exception as e:
            print(f"  {op}: {e}")

    browser.close()
