"""拼图图纸智能导入 v10 - 探索入口 + 完整流程
样本: /workspace/测试图.jpg
策略: 登录 -> 进编辑器 -> dump 所有顶栏按钮 -> 找智能导入入口 -> 触发 modal
      -> 选 MARD 视觉识别 -> 上传 -> 等识别 -> dump XHR
"""
from patchright.sync_api import sync_playwright
import json, os, re

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

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
                if 'json' in ct: body = resp.text()[:4000]
            except: body='<err>'
            xhr_log.append({'m': resp.request.method, 'url': resp.url, 'st': resp.status, 'body': body})
    page.on('response', on_response)
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text[:200]}'))

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
        page.wait_for_timeout(500)
    except: pass
    for txt in ['开始游戏', '登录']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000); break
    page.wait_for_timeout(5000)
    for _ in range(3):
        page.keyboard.press('Escape'); page.wait_for_timeout(700)
    print(f"  登录后 URL: {page.url}")

    print("\n=== 1. 进 /workspace/create 编辑器 ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(4000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    page.screenshot(path='/workspace/si10_editor_init.png')
    print(f"  当前 URL: {page.url}")

    print("\n=== 2. dump 顶栏所有按钮/可点击元素 ===")
    topbar_btns = page.evaluate('''() => {
        // 找顶栏区域 (一般 topbar 在 fixed/absolute 顶部 或 在 header 标签里)
        const candidates = [];
        // 1. 顶栏 header / nav / [class*="topbar"] / [class*="header"]
        const containers = [
            document.querySelector('header'),
            document.querySelector('nav'),
            ...document.querySelectorAll('[class*="topbar" i], [class*="header" i], [class*="toolbar" i]')
        ].filter(Boolean);
        // 去重
        const uniq = [...new Set(containers)];
        for (const c of uniq) {
            const rect = c.getBoundingClientRect();
            // 只看顶部 200px 内的容器
            if (rect.top < 250) {
                const items = c.querySelectorAll('button, [role="button"], a, [class*="btn" i]');
                items.forEach(it => {
                    const r = it.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        candidates.push({
                            tag: it.tagName,
                            text: (it.innerText||'').trim().slice(0,30),
                            aria: it.getAttribute('aria-label')||'',
                            title: it.getAttribute('title')||'',
                            cls: (it.className||'').toString().slice(0,80),
                            href: it.getAttribute('href')||'',
                            x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width)
                        });
                    }
                });
            }
        }
        // 去重(按 text+aria+title)
        const seen = new Set();
        return candidates.filter(c => {
            const k = c.text + '|' + c.aria + '|' + c.title;
            if (seen.has(k)) return false;
            seen.add(k); return true;
        });
    }''')
    print(f"  顶栏按钮数: {len(topbar_btns)}")
    for b in topbar_btns:
        print(f"    text='{b['text']}' aria='{b['aria']}' title='{b['title']}' cls='{b['cls'][:50]}' @({b['x']},{b['y']})")

    print("\n=== 3. 找'智能导入'入口 ===")
    # 关键词: 智能导入, 图纸导入, 拼图, 识别, 视觉, smartImport, smart-import
    smart_btn = None
    for b in topbar_btns:
        s = b['text'] + b['aria'] + b['title']
        if any(k in s for k in ['智能','图纸','拼图','识别','视觉','smart','Smart','import','Import','导入']):
            # 排除 '导入项目' (这个是 .pbp 导入)
            if '导入项目' in s or '导入作品' in s:
                continue
            smart_btn = b
            break
    if smart_btn:
        print(f"  ✓ 找到智能导入入口: text='{smart_btn['text']}' aria='{smart_btn['aria']}'")
    else:
        print("  没找到明显的智能导入入口, dump 全部按钮再次扫:")
        all_btns = page.evaluate('''() => {
            return [...document.querySelectorAll('button, [role="button"], a')].filter(b => {
                const r = b.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            }).map(b => ({
                text: (b.innerText||'').trim().slice(0,30),
                aria: b.getAttribute('aria-label')||'',
                title: b.getAttribute('title')||'',
            })).filter(x => x.text || x.aria || x.title);
        }''')
        for b in all_btns:
            print(f"    text='{b['text']}' aria='{b['aria']}' title='{b['title']}'")
        # 再扫一次含 '导入' 的所有按钮(可能就在顶栏的'导入项目'旁边有'智能导入')
        for b in all_btns:
            s = b['text']+b['aria']+b['title']
            if '导入' in s or '智能' in s or '识别' in s:
                print(f"    >> 含导入/智能/识别: '{s}'")

    print("\n=== 4. 尝试触发 smartImport modal ===")
    modal_triggered = False
    if smart_btn:
        try:
            # 用 evaluate 直接触发 click, 避开 focus trap
            page.evaluate('''(b) => {
                const all = [...document.querySelectorAll('button, [role="button"], a')];
                const t = all.find(x => (x.innerText||'').trim() === b.text || x.getAttribute('aria-label') === b.aria);
                if (t) t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }''', smart_btn)
            page.wait_for_timeout(2500)
            modal_triggered = True
            print(f"  ✓ 触发了入口 click")
        except Exception as e:
            print(f"  click 失败: {e}")
    
    # 兜底: 找含"智能"/"smart"的按钮直接点
    if not modal_triggered:
        try:
            page.evaluate('''() => {
                const all = [...document.querySelectorAll('button, [role="button"], a, [class*="btn" i]')];
                const t = all.find(x => {
                    const s = (x.innerText||'') + (x.getAttribute('aria-label')||'') + (x.getAttribute('title')||'');
                    return /智能|图纸|拼图|视觉|smart/i.test(s);
                });
                if (t) t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }''')
            page.wait_for_timeout(2500)
            print("  ✓ 兜底点击了含'智能/图纸'关键词的元素")
        except Exception as e:
            print(f"  兜底失败: {e}")
    
    page.screenshot(path='/workspace/si10_after_smart_click.png')

    print("\n=== 5. dump modal 内容 ===")
    modal = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [class*="dialog" i]')];
        if (dlgs.length === 0) return {found: false, body_head: document.body.innerText.slice(0,400)};
        const d = dlgs[dlgs.length-1];
        return {
            found: true,
            text: d.innerText.slice(0,800),
            tag: d.tagName,
            cls: (d.className||'').toString().slice(0,120),
            radios: [...d.querySelectorAll('[role="radio"], [role="option"], button')].map(r => ({
                text: (r.innerText||'').trim().slice(0,50),
                aria: r.getAttribute('aria-label')||'',
                checked: r.getAttribute('aria-checked') === 'true'
            })).filter(x => x.text || x.aria)
        };
    }''')
    print(f"  modal found: {modal.get('found')}")
    if modal.get('found'):
        print(f"  modal text:\n{modal.get('text','')[:600]}")
        print(f"  modal radios/options:")
        for r in modal.get('radios', []):
            print(f"    text='{r['text']}' aria='{r['aria']}' checked={r['checked']}")

    print("\n=== 6. 选 MARD 视觉识别 ===")
    mard_clicked = False
    try:
        page.evaluate('''() => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
            if (dlgs.length === 0) return;
            const d = dlgs[dlgs.length-1];
            const cands = [...d.querySelectorAll('[role="radio"], [role="option"], button, div, label')];
            const m = cands.find(x => /MARD|视觉识别|视觉|图纸/.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
            if (m) {
                m.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                m.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}));
                m.dispatchEvent(new PointerEvent('pointerup', {bubbles: true}));
            }
        }''')
        page.wait_for_timeout(2500)
        mard_clicked = True
        print("  ✓ 选了 MARD")
    except Exception as e:
        print(f"  MARD 选择失败: {e}")
    
    page.screenshot(path='/workspace/si10_after_mard.png')
    modal2 = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
        if (dlgs.length === 0) return {found: false};
        const d = dlgs[dlgs.length-1];
        return {
            found: true,
            text: d.innerText.slice(0,800),
            file_inputs: [...d.querySelectorAll('input[type="file"]')].map(i => ({accept: i.accept||'', visible: i.offsetParent !== null}))
        };
    }''')
    print(f"  选 MARD 后 modal: {json.dumps(modal2, ensure_ascii=False)[:500]}")

    print("\n=== 7. 找'下一步'/'确认'按钮并点 ===")
    for btn_text in ['下一步', '确认', '确定', '继续', 'Next', 'Confirm', 'Continue']:
        ok = page.evaluate('''(t) => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"]')];
            if (dlgs.length === 0) return false;
            const d = dlgs[dlgs.length-1];
            const btn = [...d.querySelectorAll('button')].find(b => (b.innerText||'').trim() === t);
            if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); return true; }
            return false;
        }''', btn_text)
        if ok:
            print(f"  ✓ 点了 '{btn_text}'")
            page.wait_for_timeout(2500)
            break
    page.screenshot(path='/workspace/si10_after_next.png')

    print("\n=== 8. 上传 测试图.jpg ===")
    # 优先 modal 内的 file input, 否则用页面上所有 image file input
    upload_ok = page.evaluate('''(img) => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"]')];
        if (dlgs.length > 0) {
            const d = dlgs[dlgs.length-1];
            const inps = [...d.querySelectorAll('input[type="file"]')];
            if (inps.length > 0) return {where: 'modal', count: inps.length, accepts: inps.map(i=>i.accept||'')};
        }
        const page_inps = [...document.querySelectorAll('input[type="file"]')];
        return {where: 'page', count: page_inps.length, accepts: page_inps.map(i=>i.accept||'')};
    }''', IMG)
    print(f"  file input 位置: {upload_ok}")
    
    # 上传: 优先 modal 内的, 兜底用页面第一个 image input
    uploaded = False
    inp_modal = page.locator('[role="dialog"] input[type="file"], [data-slot="dialog-content"] input[type="file"]').last
    if inp_modal.count() > 0:
        try:
            inp_modal.set_input_files(IMG)
            uploaded = True
            print("  ✓ 上传到 modal 内 input")
        except Exception as e:
            print(f"  modal 上传失败: {e}")
    if not uploaded:
        # 兜底
        inps = page.locator('input[type="file"]')
        n = inps.count()
        print(f"  页面 file input 总数: {n}")
        for i in range(n):
            try:
                inps.nth(i).set_input_files(IMG)
                print(f"  ✓ 上传到第 {i} 个 input")
                uploaded = True
                break
            except Exception as e:
                print(f"  第{i}个失败: {e}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si10_after_upload.png')

    print("\n=== 9. 等识别 (最长 90s) ===")
    recognized = False
    for i in range(45):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,400)''')
        # 进入编辑器 or 出现色号/网格/裁剪 等关键词
        if '/editor' in url or '/workspace' in url and '/create' not in url:
            print(f"  [{i*2}s] URL 变: {url}")
            recognized = True
            page.wait_for_timeout(3000)
            break
        if any(k in body for k in ['色号','网格','创建项目','完成','裁剪','分割','识别成功','导入成功','MARD']):
            print(f"  [{i*2}s] 识别关键词出现")
            recognized = True
            page.wait_for_timeout(3000)
            break
        if i % 5 == 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si10_final.png')
    body_final = page.evaluate('''() => document.body.innerText.slice(0,500)''')
    print(f"  最终 URL: {page.url}")
    print(f"  最终 body:\n{body_final[:400]}")

    print("\n=== 10. console errors ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 11. XHR (识别相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','图纸']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:600]}")

    ctx.close(); browser.close()
print("\nDONE")
