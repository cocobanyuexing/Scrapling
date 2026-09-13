"""实测 3 v9: 正确登录流程 + axios 拦截器 + UI 真触发扣减
1. 用 v15 的登录流程(确保 checkbox 勾上)
2. 进 /workspace (而不是 inventory)
3. 在 sidebar 点'库存' 路由
4. 等 inventory 加载完
5. 找'批量调整'按钮 -> 打开弹窗 -> 选色号 -> 输数量 -> 点减号 -> 确认
6. 看真实 XHR
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

def body_head(page, n=1000):
    return page.evaluate('''(n) => document.body.innerText.slice(0,n)''', n)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

    xhr_log = []
    def on_response(resp):
        if resp.request.resource_type in ('xhr', 'fetch'):
            try:
                body = ''
                ct = resp.headers.get('content-type','')
                if 'json' in ct: body = resp.text()[:2000]
            except: body='<err>'
            req_body = ''
            try:
                if resp.request.method in ('POST','PUT','PATCH'):
                    req_body = (resp.request.post_data or '')[:1500]
            except: pass
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body, 'req_body': req_body})
    page.on('response', on_response)

    print("=== 0. 登录 (v15 流程) ===")
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
    page.wait_for_timeout(2500)  # 等 modal 出现
    # 先 dump 看是不是弹窗真的开了
    modal_check = page.evaluate('''() => {
        const dc = document.querySelector('[data-slot="dialog-content"]');
        const emailInp = document.querySelector('[data-slot="dialog-content"] input[type="email"]');
        const pwdInp = document.querySelector('[data-slot="dialog-content"] input[type="password"]');
        const cb = document.querySelector('[data-slot="dialog-content"] [role="checkbox"]');
        return {
            has_dialog: !!dc,
            has_email: !!emailInp,
            has_pwd: !!pwdInp,
            has_checkbox: !!cb,
            body_head: document.body.innerText.slice(0, 300)
        };
    }''')
    print(f"  modal_check: {modal_check}")
    if not modal_check['has_email']:
        # 再多按 ESC 关闭其它弹窗
        for _ in range(3):
            page.keyboard.press('Escape'); page.wait_for_timeout(700)
        # 再次点登录
        page.evaluate('''() => {
            const bs = [...document.querySelectorAll('button')].filter(b => {
                const t = (b.innerText||'').trim();
                return t === '登录' || t === '登入';
            });
            if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        }''')
        page.wait_for_timeout(3000)
    try:
        page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=8000)
    except Exception as e:
        print(f"  fill email 失败: {e}")
    try:
        page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    except: pass
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
        page.wait_for_timeout(800)
    except: pass
    # 再确认 checkbox 已勾
    checked = page.evaluate('''() => {
        const cb = document.querySelector('[data-slot="dialog-content"] [role="checkbox"]');
        return cb ? cb.getAttribute('data-state') : 'no_checkbox';
    }''')
    print(f"  checkbox state: {checked}")
    if checked != 'checked':
        # 再点一次
        try:
            page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(force=True)
            page.wait_for_timeout(500)
        except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(6000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    print(f"  登录后 URL: {page.url}")
    body = body_head(page, 500)
    print(f"  body 前 200: {body[:200]}")

    print("\n=== 1. 进 /workspace/create (v15 验证过能进) ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    print(f"  URL: {page.url}")
    page.screenshot(path='/workspace/inv_v9_workspace.png')
    body = body_head(page, 600)
    print(f"  body 前 600: {body[:600]}")

    # 等 axios 拦截器初始化 + 触发 /v1/app/auth/me 自检刷新 token
    print("\n=== 1.5 触发 /v1/app/auth/me 自检 ===")
    auth_resp = page.evaluate('''async () => {
        // 通过 axios 拦截器调用
        // 找全局的 fetch 包装 - 直接走 page fetch (会自动带 cookie)
        const r = await fetch('/v1/app/auth/me', {credentials: 'include'});
        return {st: r.status, body: (await r.text()).slice(0, 500)};
    }''')
    print(f"  /v1/app/auth/me status: {auth_resp['st']}")
    print(f"  body: {auth_resp['body'][:300]}")

    print("\n=== 2. 点 sidebar '库存' ===")
    # 找 sidebar 含'库存'文字的可点击元素
    clicked = page.evaluate('''() => {
        // 找含'库存'文字的链接/按钮, 不限定 a
        const all = [...document.querySelectorAll('a[href], button, [role="button"], [role="link"]')];
        const target = all.find(e => {
            const t = (e.innerText||'').trim();
            return t === '库存' || (t.includes('库存') && t.length < 30);
        });
        if (target) {
            target.click();
            return target.getAttribute('href') || target.innerText.trim();
        }
        return null;
    }''')
    print(f"  点击库存: {clicked}")
    page.wait_for_timeout(5000)
    print(f"  URL: {page.url}")
    page.screenshot(path='/workspace/inv_v9_main.png')
    body = body_head(page, 1500)
    print(f"  body 前 800: {body[:800]}")

    print("\n=== 3. 找所有按钮 ===")
    btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            visible: b.offsetParent !== null
        })).filter(x => x.visible && (x.text || x.aria));
    }''')
    print(f"  可见按钮数: {len(btns)}")
    for b in btns[:25]:
        print(f"    - {b['text']!r} / {b['aria']!r}")

    print("\n=== 4. 找'批量调整'/'调整' ===")
    target_btns = [b for b in btns if any(k in (b['text']+b['aria']) for k in ['批量','调整','管理','加减','批量调整','调整数量','调整库存'])]
    print(f"  命中: {len(target_btns)}")
    for b in target_btns:
        print(f"    - {b}")

    print("\n=== 5. 点击'批量调整'或'调整' ===")
    clicked = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        for (const targetText of ['批量调整', '调整库存', '管理库存', '管理', '编辑', '调整']) {
            const target = bs.find(b => (b.innerText||'').trim() === targetText);
            if (target) { target.click(); return targetText; }
        }
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t.includes('批量') || t.includes('调整');
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点击: {clicked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/inv_v9_modal.png')
    body = body_head(page, 1500)
    print(f"  body 前 1500: {body[:1500]}")

    print("\n=== 6. 弹窗按钮 ===")
    modal_btns = page.evaluate('''() => {
        return [...document.querySelectorAll('[role="dialog"] button, [data-slot="dialog-content"] button')]
            .map(b => ({
                text: (b.innerText||'').trim().slice(0,30),
                aria: b.getAttribute('aria-label')||'',
                title: b.getAttribute('title')||''
            }))
            .filter(b => b.text || b.aria);
    }''')
    print(f"  弹窗按钮数: {len(modal_btns)}")
    for b in modal_btns[:25]:
        print(f"    - {b['text']!r} / {b['aria']!r}")

    print("\n=== 7. 所有 inventory 相关 XHR ===")
    print(f"  总 XHR: {len(xhr_log)}")
    for x in xhr_log:
        u = x['url']
        if 'inventory' in u.lower() or 'operations' in u or 'auth' in u.lower() or 'user' in u.lower() or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:130]}")
            if x.get('req_body'):
                print(f"    req: {x['req_body'][:400]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
