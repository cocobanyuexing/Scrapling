"""实测 3 v7: 监听真实 XHR, 触发 UI 真扣减 (走 axios 拦截器自动加 token)
策略: 进库存页 -> 点 '管理'/'批量调整' -> 选色号 -> 输入数量 -> 点减号 -> 看真实 XHR
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

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
            xhr_log.append({
                'm': resp.request.method, 'url': resp.url, 'st': resp.status,
                'body': body, 'req_body': req_body
            })
    page.on('response', on_response)

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

    print("\n=== 1. 进库存页 ===")
    page.goto('https://i2tools.com/workspace/inventory', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(4000)
    page.screenshot(path='/workspace/inv_main_v7.png')

    # 看 UI 全部按钮
    print("\n=== 2. 找所有按钮 ===")
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

    print("\n=== 3. 找'批量调整'或'管理'按钮 ===")
    target_btns = [b for b in btns if any(k in (b['text']+b['aria']) for k in ['批量','调整','管理','编辑','修改','加减','调整库存','批量调整','调整数量'])]
    print(f"  命中: {len(target_btns)}")
    for b in target_btns:
        print(f"    - {b}")

    print("\n=== 4. 点'批量调整' ===")
    clicked = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('button, [role="button"]')];
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            return t === '批量调整' || t === '调整库存' || t === '管理库存' || t === '管理' || t.includes('批量');
        });
        if (target) { target.click(); return target.innerText.trim(); }
        return null;
    }''')
    print(f"  点击: {clicked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/inv_adjust_modal.png')

    body = page.evaluate('''() => document.body.innerText.slice(0,1500)''')
    print(f"  body 前 800:\n{body[:800]}")

    print("\n=== 5. 找色号 + 加/减按钮 ===")
    # 选第一个色号 + 输入数量 + 点减号
    # dump 弹窗内所有可点击元素
    modal_btns = page.evaluate('''() => {
        return [...document.querySelectorAll('[role="dialog"] button, [data-slot="dialog-content"] button, [class*="modal"] button, [class*="dialog"] button')]
            .map(b => ({
                text: (b.innerText||'').trim().slice(0,20),
                aria: b.getAttribute('aria-label')||'',
                classes: (b.className||'').slice(0,80)
            }))
            .filter(b => b.text || b.aria);
    }''')
    print(f"  弹窗按钮数: {len(modal_btns)}")
    for b in modal_btns[:20]:
        print(f"    - {b['text']!r}/{b['aria']!r} cls={b['classes'][:50]}")

    print("\n=== 6. 选第一个色号 + 点减号 ===")
    # 用 UI: 点一个色号卡片 + 点减号 + 点确认
    # 先点第一个色号
    picked = page.evaluate('''() => {
        // 找色号列表第一个
        const cards = [...document.querySelectorAll('[role="dialog"] [class*="cursor-pointer"], [role="dialog"] [class*="card"], [data-slot="dialog-content"] [class*="cursor-pointer"]')];
        if (cards[0]) { cards[0].click(); return cards.length; }
        return 0;
    }''')
    print(f"  点色号卡片: 共 {picked} 个, 点了第 1 个")
    page.wait_for_timeout(1500)

    # 找减号按钮(subtract / minus / -)
    minus_clicked = page.evaluate('''() => {
        const bs = [...document.querySelectorAll('[role="dialog"] button, [data-slot="dialog-content"] button')];
        // 找减号按钮
        const target = bs.find(b => {
            const t = (b.innerText||'').trim();
            const aria = (b.getAttribute('aria-label')||'').toLowerCase();
            return t === '−' || t === '-' || t === '减' || t === '减去' || aria.includes('subtract') || aria.includes('minus') || aria.includes('decrement');
        });
        if (target) { target.click(); return target.innerText.trim() || target.getAttribute('aria-label'); }
        return null;
    }''')
    print(f"  点减号: {minus_clicked}")
    page.wait_for_timeout(1500)

    print("\n=== 7. XHR 日志(扣减相关) ===")
    print(f"  总 XHR 数: {len(xhr_log)}")
    for x in xhr_log:
        u = x['url']
        if 'operations' in u or 'inventory' in u.lower() or x['st'] >= 400:
            print(f"  {x['st']} {x['m']} {u[:120]}")
            if x.get('req_body'):
                print(f"    req: {x['req_body'][:400]}")
            if x.get('body'):
                print(f"    resp: {x['body'][:400]}")

    ctx.close(); browser.close()
print("\nDONE")
