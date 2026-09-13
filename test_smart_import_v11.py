"""拼图图纸智能导入 v11 - 正确流程
样本: /workspace/测试图.jpg
流程: 登录 -> /workspace/create 项目列表页 -> 点'新建' -> '选择转换模式' modal
      -> 选'图片转换' -> 下一步 modal(选 MARD 视觉识别) -> 上传 -> 等识别
关键: 用更宽松的 modal 选择器 [class*=modal i],[data-state=open],[role=dialog]
"""
from patchright.sync_api import sync_playwright
import json, os, time

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
IMG = '/workspace/测试图.jpg'

def dump_modal(page, tag='modal'):
    """宽松选择器 dump 当前 modal"""
    return page.evaluate('''(tag) => {
        const dlgs = [...document.querySelectorAll(
            '[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], ' +
            '[class*="modal" i], [class*="dialog" i], [data-state="open"], ' +
            '[class*="sheet" i], [class*="popup" i], [class*="overlay" i]'
        )].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 100 && r.height > 100;  // 过滤隐藏/小元素
        });
        if (dlgs.length === 0) return {found: false, tag};
        // 取最大的(主 modal)
        const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
        return {
            found: true,
            tag,
            cls: (d.className||'').toString().slice(0,200),
            text: d.innerText.slice(0,1200),
            tag_name: d.tagName,
            buttons: [...d.querySelectorAll('button')].map(b => ({
                text: (b.innerText||'').trim().slice(0,40),
                aria: b.getAttribute('aria-label')||''
            })).filter(x => x.text || x.aria),
            radios: [...d.querySelectorAll('[role="radio"], [role="option"], [role="tab"]')].map(r => ({
                label: (r.innerText||'').trim().slice(0,40) || r.getAttribute('aria-label')||'',
                checked: r.getAttribute('aria-checked') === 'true' || r.getAttribute('data-state') === 'active'
            })),
            file_inputs: [...d.querySelectorAll('input[type="file"]')].map(i => ({accept: i.accept||'', multiple: i.multiple})),
            visible_inputs: [...d.querySelectorAll('input:not([type=file])')].map(i => ({type: i.type, placeholder: i.placeholder||'', label: i.getAttribute('aria-label')||''}))
        };
    }''', tag)

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
                if 'json' in ct: body = resp.text()[:5000]
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

    print("\n=== 1. 进 /workspace/create ===")
    page.goto('https://i2tools.com/workspace/create', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(4000)
    for _ in range(2):
        page.keyboard.press('Escape'); page.wait_for_timeout(500)
    print(f"  当前 URL: {page.url}")
    page.screenshot(path='/workspace/si11_init.png')

    print("\n=== 2. 点侧边栏 '新建' 按钮 ===")
    # 找 aria-label='新建' 或 text='新建' 的按钮
    clicked = page.evaluate('''() => {
        const all = [...document.querySelectorAll('button, [role="button"], a')];
        // 优先 aria-label='新建' (侧边栏按钮通常用 aria)
        let t = all.find(x => x.getAttribute('aria-label') === '新建');
        if (!t) t = all.find(x => (x.innerText||'').trim() === '新建');
        if (t) {
            t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            return {ok: true, text: (t.innerText||'').trim() || t.getAttribute('aria-label')};
        }
        return {ok: false};
    }''')
    print(f"  点击结果: {clicked}")
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/si11_after_new.png')

    print("\n=== 3. dump '选择转换模式' modal ===")
    modal1 = dump_modal(page, '选择转换模式')
    print(f"  modal1 found: {modal1.get('found')}")
    if modal1.get('found'):
        print(f"  modal1 cls: {modal1.get('cls','')[:100]}")
        print(f"  modal1 text:\n{modal1.get('text','')[:500]}")
        print(f"  modal1 buttons: {[b['text'] or b['aria'] for b in modal1.get('buttons',[])]}")
        print(f"  modal1 radios: {modal1.get('radios',[])}")

    print("\n=== 4. 选 '图片转换' ===")
    # 在 modal 内找含 '图片转换' 的元素点击
    picked = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [data-state="open"]')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 100 && r.height > 100;
        });
        if (dlgs.length === 0) return {ok: false, reason: 'no_modal'};
        const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
        const cands = [...d.querySelectorAll('button, [role="option"], [role="radio"], div, li, label')];
        // 优先匹配 '图片转换'
        let t = cands.find(x => /图片转换/.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
        if (!t) t = cands.find(x => /图片|photo|image/i.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
        if (t) {
            t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            return {ok: true, text: (t.innerText||'').trim().slice(0,80)};
        }
        return {ok: false, reason: 'no_match'};
    }''')
    print(f"  选'图片转换' 结果: {picked}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si11_after_pick_img.png')

    print("\n=== 5. dump 下一步 modal (找 MARD) ===")
    modal2 = dump_modal(page, 'MARD选择')
    print(f"  modal2 found: {modal2.get('found')}")
    if modal2.get('found'):
        print(f"  modal2 cls: {modal2.get('cls','')[:100]}")
        print(f"  modal2 text:\n{modal2.get('text','')[:800]}")
        print(f"  modal2 buttons: {[b['text'] or b['aria'] for b in modal2.get('buttons',[])]}")
        print(f"  modal2 radios: {modal2.get('radios',[])}")
        print(f"  modal2 file_inputs: {modal2.get('file_inputs',[])}")
        print(f"  modal2 visible_inputs: {modal2.get('visible_inputs',[])}")

    print("\n=== 6. 选 'MARD 视觉识别' ===")
    mard_picked = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [data-state="open"]')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 100 && r.height > 100;
        });
        if (dlgs.length === 0) return {ok: false, reason: 'no_modal'};
        const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
        const cands = [...d.querySelectorAll('[role="radio"], [role="option"], button, div, li, label')];
        // 优先 MARD 视觉识别
        let t = cands.find(x => /MARD.*视觉|视觉识别|MARD/.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
        if (!t) t = cands.find(x => /视觉|recogni|vision|MARD/i.test((x.innerText||'') + (x.getAttribute('aria-label')||'')));
        if (t) {
            // 多事件触发(React 受控组件需要)
            t.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            t.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            return {ok: true, text: (t.innerText||'').trim().slice(0,80)};
        }
        return {ok: false, reason: 'no_mard'};
    }''')
    print(f"  选 MARD 结果: {mard_picked}")
    page.wait_for_timeout(2500)
    page.screenshot(path='/workspace/si11_after_mard.png')
    modal3 = dump_modal(page, '选MARD后')
    print(f"  选MARD后 modal: found={modal3.get('found')}")
    if modal3.get('found'):
        print(f"  modal3 text:\n{modal3.get('text','')[:600]}")
        print(f"  modal3 file_inputs: {modal3.get('file_inputs',[])}")
        print(f"  modal3 buttons: {[b['text'] or b['aria'] for b in modal3.get('buttons',[])]}")

    print("\n=== 7. 找 '下一步/确认' 进入上传步骤 ===")
    for btn_text in ['下一步', '确认', '确定', '继续', 'Next', 'Confirm', 'Continue', '上传', '开始']:
        ok = page.evaluate('''(t) => {
            const dlgs = [...document.querySelectorAll('[role="dialog"], [data-slot="dialog-content"], [aria-modal="true"], [class*="modal" i], [data-state="open"]')].filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 100 && r.height > 100;
            });
            if (dlgs.length === 0) return false;
            const d = dlgs.sort((a,b) => (b.getBoundingClientRect().width*b.getBoundingClientRect().height) - (a.getBoundingClientRect().width*a.getBoundingClientRect().height))[0];
            const btn = [...d.querySelectorAll('button')].find(b => (b.innerText||'').trim() === t);
            if (btn) { btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); return true; }
            return false;
        }''', btn_text)
        if ok:
            print(f"  ✓ 点了 '{btn_text}'")
            page.wait_for_timeout(2500)
            break
    page.screenshot(path='/workspace/si11_after_next.png')
    modal4 = dump_modal(page, '下一步后')
    print(f"  下一步后 modal: found={modal4.get('found')}")
    if modal4.get('found'):
        print(f"  modal4 text:\n{modal4.get('text','')[:400]}")
        print(f"  modal4 file_inputs: {modal4.get('file_inputs',[])}")

    print("\n=== 8. 上传 测试图.jpg ===")
    # 优先 modal 内 file input
    uploaded = False
    inp = page.locator('[role="dialog"] input[type="file"], [data-slot="dialog-content"] input[type="file"], [class*="modal" i] input[type="file"]').first
    if inp.count() > 0:
        try:
            inp.set_input_files(IMG)
            uploaded = True
            print("  ✓ 上传到 modal 内 input")
        except Exception as e:
            print(f"  modal 上传失败: {e}")
    if not uploaded:
        # 兜底: 全页面 image input
        inps = page.locator('input[type="file"]')
        n = inps.count()
        print(f"  页面 file input 总数: {n}")
        for i in range(n):
            try:
                inp_i = inps.nth(i)
                accept = inp_i.evaluate('e => e.accept || ""')
                if 'image' in accept or accept == '':
                    inp_i.set_input_files(IMG)
                    print(f"  ✓ 上传到第 {i} 个 input (accept={accept})")
                    uploaded = True
                    break
            except Exception as e:
                print(f"  第{i}个失败: {e}")
    page.wait_for_timeout(3000)
    page.screenshot(path='/workspace/si11_after_upload.png')

    print("\n=== 9. 等识别 (最长 120s) ===")
    recognized = False
    for i in range(60):
        page.wait_for_timeout(2000)
        url = page.url
        body = page.evaluate('''() => document.body.innerText.slice(0,500)''')
        if '/editor' in url or ('/workspace' in url and '/create' not in url):
            print(f"  [{i*2}s] ✓ 进编辑器! URL={url}")
            recognized = True
            page.wait_for_timeout(4000)
            break
        # 关键词: 识别成功/色号/网格/创建项目/导入成功
        if any(k in body for k in ['识别完成','识别成功','色号','网格','创建项目','导入成功','MARD','分析完成']):
            if '选择转换模式' not in body:  # 排除初始 modal
                print(f"  [{i*2}s] 识别关键词出现")
                recognized = True
                page.wait_for_timeout(3000)
                break
        if i % 5 == 0:
            print(f"  [{i*2}s] 等待中... URL={url[:80]}")
    page.screenshot(path='/workspace/si11_final.png')
    body_final = page.evaluate('''() => document.body.innerText.slice(0,600)''')
    print(f"  最终 URL: {page.url}")
    print(f"  最终 body:\n{body_final[:500]}")

    print("\n=== 10. console errors ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 11. XHR (识别相关) ===")
    for x in xhr_log:
        u = x['url']
        if '/v1/' in u or x['st'] >= 400 or any(k in u.lower() for k in ['smart','pattern','recogn','perler','upload','analyz','detect','convers','scan','segment','mard','puzzle','blueprint','图纸','pixel','image','vision']):
            print(f"  {x['st']} {x['m']} {u[:140]}")
            if x.get('body') and x['st'] < 300 and len(x['body']) > 30:
                print(f"    body: {x['body'][:800]}")

    ctx.close(); browser.close()
print("\nDONE")
