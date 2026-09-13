"""小红书运行时 response body 抓取
目标: 抓 /api/sns/web/v2/comment/page 和 /api/sns/web/v2/user/me 的响应 body
看真实数据结构, 也看反爬 API 的响应
"""
from patchright.sync_api import sync_playwright
import json, os

URL = 'https://www.xiaohongshu.com/explore/6a7551fe00000000250036eb?xsec_token=ABVGopREJSL_vb3wmW5E1-KDFe1rKvJ_pcu9QLr86qrtY=&xsec_source=pc_search&source=web_explore_feed'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    page = ctx.new_page()

    # 抓 response body
    api_responses = []
    KEY_API = ['/api/sns/web/v2/comment/page', '/api/sns/web/v2/user/me', '/api/sns/web/v1/config',
               '/api/sns/web/v2/widgets', '/api/sns/web/v1/system/config', '/api/sns/web/v1/login/activate',
               '/api/sec/v1/scripting', '/api/sec/v1/sbtsource', '/api/sec/v1/shield/webprofile',
               '/api/redcaptcha/v2/getconfig']
    def on_response(resp):
        u = resp.url
        if not any(k in u for k in KEY_API): return
        try:
            body = resp.text()
        except: body = '<err>'
        api_responses.append({
            'url': u[:200], 'status': resp.status, 'ct': resp.headers.get('content-type',''),
            'body_head': body[:2500]
        })
    page.on('response', on_response)

    print("=== 1. 加载页面 ===")
    page.goto(URL, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(6000)  # 等 XHR 完成

    print(f"\n=== 2. 抓到 {len(api_responses)} 个关键 API response ===")
    for r in api_responses:
        print(f"\n  --- [{r['status']}] {r['url'][:160]} ---")
        print(f"  Content-Type: {r['ct']}")
        print(f"  body 前 2500 字符:")
        print('    ' + r['body_head'].replace('\n', '\n    ')[:2500])

    print(f"\n=== 3. __INITIAL_STATE__ 顶层结构 ===")
    state_keys = page.evaluate('''() => {
        try { return Object.keys(window.__INITIAL_STATE__ || {}); }
        catch(e) { return ['err:'+e.message]; }
    }''')
    print(f"  顶层 keys: {state_keys}")
    # 找 note keys
    note_keys = [k for k in state_keys if 'note' in k.lower() or 'feed' in k.lower() or 'item' in k.lower()]
    print(f"  note/feed keys: {note_keys}")
    if note_keys:
        for nk in note_keys:
            data = page.evaluate(f'''() => {{
                try {{
                    const d = window.__INITIAL_STATE__['{nk}'];
                    return JSON.stringify(d).slice(0,3000);
                }} catch(e) {{ return 'err:'+e.message; }}
            }}''')
            print(f"\n  {nk} 前 3000 字符:")
            print('    ' + data[:3000])

    ctx.close(); browser.close()
print("\nDONE")
