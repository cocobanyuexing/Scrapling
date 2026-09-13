"""实测 3 v8: 先确认登录态, 再进库存, 再点'调整' 触发 UI 真扣减
策略:
1. 登录后停首页, dump 验证已登录(用户头像 + 用户名显示)
2. 进 /workspace/inventory 不直接跳, 而是从首页 sidebar 点 '库存'
3. 等 inventory 加载完(看到 '库存' 标题 + 色号卡片)
4. 找右上角'调整'按钮 -> 打开弹窗 -> 选色号 -> 输数量 -> 点'减号' -> 确认
5. 看真实 XHR
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

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button')].filter(b => {
            const t = (b.innerText||'').trim();
            return t === '登录' || t === '登入';
        });
        if (bs[0]) bs[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
    }''')
    page.wait_for_timeout(3000)
    page.locator('[data-slot="dialog-content"] input[type="email"]').first.fill(EMAIL, timeout=5000)
    page.locator('[data-slot="dialog-content"] input[type="password"]').first.fill(PWD, timeout=5000)
    try:
        page.locator('[data-slot="dialog-content"] [role="checkbox"]').first.click(timeout=3000)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(6000)

    # 验证登录状态 - 看是否能看到用户信息
    body = body_head(page, 800)
    print(f"  登录后 URL: {page.url}")
    print(f"  body 前 500: {body[:500]}")

    # dump nav 链接看登录状态
    nav = page.evaluate('''() => {
        const links = [...document.querySelectorAll('a[href]')].map(a => ({href: a.getAttribute('href'), text: (a.innerText||'').trim().slice(0,20)}));
        return links.filter(l => l.text);
    }''')
    print(f"  nav 链接: {nav[:10]}")

    print("\n=== 1. 从 sidebar 点'库存' ===")
    # 等首页稳定
    page.wait_for_timeout(2000)
    # 找 sidebar 含'库存'的链接
    clicked = page.evaluate('''() => {
        const links = [...document.querySelectorAll('a[href]')];
        const target = links.find(a => {
            const t = (a.innerText||'').trim();
            return t === '库存' || t.includes('库存');
        });
        if (target) { target.click(); return target.getAttribute('href'); }
        return null;
    }''')
    print(f"  点了'库存' 链接 href: {clicked}")
    page.wait_for_timeout(4000)
    print(f"  当前 URL: {page.url}")
    page.screenshot(path='/workspace/inv_v8_landed.png')

    body = body_head(page, 1500)
    print(f"  body 前 800: {body[:800]}")

    print("\n=== 2. 找'批量调整'或'调整'按钮 ===")
    btns = page.evaluate('''() => {
        return [...document.querySelectorAll('button, [role="button"]')].map(b => ({
            text: (b.innerText||'').trim().slice(0,30),
            aria: b.getAttribute('aria-label')||'',
            title: b.getAttribute('title')||'',
            visible: b.offsetParent !== null
        })).filter(x => x.visible && (x.text || x.aria));
    }''')
    print(f"  可见按钮数: {len(btns)}")
    for b in btns[:30]:
        print(f"    - {b['text']!r} / {b['aria']!r}")

    # 找调整/批量调整/管理
    target_btns = [b for b in btns if any(k in (b['text']+b['aria']) for k in ['批量','调整','管理','编辑','修改','加减','批量调整','调整数量'])]
    print(f"\n  命中目标按钮: {len(target_btns)}")
    for b in target_btns:
        print(f"    - {b}")

    print("\n=== 3. 点'批量调整'/'调整' ===")
    clicked = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        // 优先级: 批量调整 > 调整库存 > 管理 > 编辑
        for (const targetText of ['批量调整', '调整库存', '管理库存', '管理', '编辑']) {
            const target = bs.find(b => (b.innerText||'').trim() === targetText);
            if (target) { target.click(); return targetText; }
        }
        // 模糊匹配
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t.includes('批量') || t.includes('调整');
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点击: {clicked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/inv_v8_modal.png')

    body = body_head(page, 1500)
    print(f"  body 前 1000: {body[:1000]}")

    print("\n=== 4. 弹窗内按钮 ===")
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

    print("\n=== 5. 所有 XHR (看是否调用 inventory API) ===")
    print(f"  总 XHR 数: {len(xhr_log)}")
    for x in xhr_log:
        u = x['url']
        if 'inventory' in u.lower() or 'operations' in u or 'auth' in u.lower() or 'user' in u.lower() or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('body'):
                print(f"    body: {x['body'][:300]}")

    ctx.close(); browser.close()
print("\nDONE")
