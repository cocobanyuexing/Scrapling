"""小红书链接实测 - 浏览器运行时分析
目标: 用真实 xsec_token 链接加载页面, 抓取运行时网络请求
看: 1) 真实 API endpoint 2) 签名请求头 x-s/x-t/x-m-common 3) 是否有登录拦截 4) 反爬触发条件
"""
from patchright.sync_api import sync_playwright
import json, os, time

URL = 'https://www.xiaohongshu.com/explore/6a7551fe00000000250036eb?xsec_token=ABVGopREJSL_vb3wmW5E1-KDFe1rKvJ_pcu9QLr86qrtY=&xsec_source=pc_search&source=web_explore_feed'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    page = ctx.new_page()

    # 详细记录所有请求,重点 XHR/fetch
    xhr_log = []
    all_reqs = []
    def on_request(req):
        all_reqs.append({
            'm': req.method, 'url': req.url, 'rt': req.resource_type,
            'hdrs': dict(req.headers)
        })
        if req.resource_type in ('xhr', 'fetch'):
            hdrs = dict(req.headers)
            # 找签名头
            sign_hdrs = {k:v for k,v in hdrs.items() if k.lower().startswith('x-') or 'token' in k.lower() or 'sign' in k.lower()}
            xhr_log.append({
                'm': req.method, 'url': req.url,
                'sign_hdrs': sign_hdrs,
                'all_hdrs': hdrs
            })
    page.on('request', on_request)
    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text[:300]}'))

    print("=== 1. 加载页面 ===")
    resp = page.goto(URL, wait_until='networkidle', timeout=60000)
    print(f"  HTTP: {resp.status if resp else 'None'}")
    print(f"  最终 URL: {page.url}")
    page.wait_for_timeout(5000)

    print("\n=== 2. 页面标题/正文头部 ===")
    title = page.title()
    print(f"  title: {title}")
    body_head = page.evaluate('''() => document.body.innerText.slice(0,800)''')
    print(f"  body 前 800 字符:\n{body_head[:800]}")

    print("\n=== 3. 截图当前页 ===")
    page.screenshot(path='/workspace/xhs_1_landed.png')

    print("\n=== 4. 所有 XHR/fetch 请求 (签名头分析) ===")
    print(f"  总请求数: {len(all_reqs)}, XHR 数: {len(xhr_log)}")
    for x in xhr_log:
        u = x['url']
        # 过滤掉图片/静态资源
        if any(u.endswith(s) for s in ['.png','.jpg','.webp','.css','.js','.ico','.svg','.gif']): continue
        print(f"\n  [{x['m']}] {u[:150]}")
        if x.get('sign_hdrs'):
            print(f"    签名头:")
            for k,v in x['sign_hdrs'].items():
                print(f"      {k}: {v[:100]}")

    print("\n=== 5. API endpoint 汇总(去重) ===")
    api_endpoints = set()
    for r in all_reqs:
        u = r['url']
        # 抓 /api/ /sns/ /edith/ /solar/ 路径
        import re
        m = re.search(r'(https?://[^/]+)?(/(api|sns|edith|solar|fe_api|web_api)/[a-zA-Z0-9/_-]*)', u)
        if m:
            api_endpoints.add(m.group(2))
    for ep in sorted(api_endpoints):
        print(f"  {ep}")

    print("\n=== 6. 找笔记内容数据(是否拿到 SSR 之外的真实内容) ===")
    note_data = page.evaluate('''() => {
        const state = window.__INITIAL_STATE__;
        if (!state) return {has_state: false};
        // 找 note 相关数据
        const keys = Object.keys(state);
        const note_keys = keys.filter(k => /note|feed|item|detail|post/i.test(k));
        return {
            has_state: true,
            top_keys: keys.slice(0,30),
            note_keys: note_keys,
            note_data_sample: JSON.stringify(state[note_keys[0]] || {}).slice(0,1500) if note_keys else ''
        };
    }''')
    print(f"  __INITIAL_STATE__ 顶层 keys: {note_data.get('top_keys')}")
    print(f"  note 相关 keys: {note_data.get('note_keys')}")

    print("\n=== 7. 是否有登录弹窗/拦截 ===")
    login_modal = page.evaluate('''() => {
        const dlgs = [...document.querySelectorAll('[role="dialog"], [class*="login" i], [class*="modal" i]')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 100 && r.height > 100;
        });
        if (dlgs.length === 0) return {found: false};
        return {found: true, text: dlgs[0].innerText.slice(0,300)};
    }''')
    print(f"  登录弹窗: {login_modal}")

    print("\n=== 8. console 错误 ===")
    for m in console_msgs[-15:]:
        print(f"  {m}")

    print("\n=== 9. 反爬触发迹象(看 422/403/461 等) ===")
    bad_status = [r for r in all_reqs if hasattr(r, 'status') and r.get('status') and r['status'] >= 400]
    # Playwright 请求对象不直接给 status, 跳过
    print(f"  (本脚本未捕获 response status, 看下面 xhr_log)")
    
    # 改用 response 监听
    print("\n=== 10. 监听 response (找异常状态码) ===")
    # 再发一次刷新, 抓 response
    bad_responses = []
    def on_response(resp):
        if resp.status >= 400:
            bad_responses.append({'st': resp.status, 'url': resp.url[:120]})
    page.on('response', on_response)
    page.reload(wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)
    for br in bad_responses[:20]:
        print(f"  {br['st']} {br['url']}")

    ctx.close(); browser.close()
print("\nDONE")
