"""查询 ai-pixel-art 任务状态 + 下载结果图（用 page.evaluate fetch 复用登录态）。"""
from patchright.sync_api import sync_playwright
import json

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'
TASK_NO = 'TASK20260913185502422649'

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='zh-CN')
    page = ctx.new_page()

    print("=== 0. 登录 ===")
    page.goto('https://i2tools.com/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2000)
    page.keyboard.press('Escape')
    page.wait_for_timeout(1500)
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
    except Exception as e:
        print(f"  checkbox: {e}")
    for txt in ['开始游戏', '開始遊戲', '登录', '登入']:
        loc = page.locator(f'[data-slot="dialog-content"] button:has-text("{txt}")').first
        if loc.count() > 0:
            loc.click(timeout=5000)
            break
    page.wait_for_timeout(5000)
    print("  登录完成")

    # 用 page.evaluate fetch 复用 cookie + localStorage 注入 Authorization
    # 前端 axios 实例会自动注入 token，但 page.evaluate 的 fetch 不会走 axios 拦截器
    # 所以我们手动从 localStorage 拿 token 注入
    print("\n=== 1. 查询任务状态（轮询）===")
    result = page.evaluate('''async (taskNo) => {
        const auth = JSON.parse(localStorage.getItem('auth-storage') || '{}');
        const token = auth.state?.accessToken;
        if (!token) return {error: 'no token in localStorage'};

        // 试单任务接口
        let last = null;
        for (let i = 0; i < 24; i++) {
            // 试 /{taskNo} 单任务接口
            let r = await fetch(`/v1/app/pixel-art/conversions/${taskNo}`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            let j = await r.json();
            last = j;
            // 也查列表
            let r2 = await fetch(`/v1/app/pixel-art/conversions?pageIndex=1&pageSize=10&statuses=SUCCESS&statuses=FAILED&statuses=CANCELED&statuses=PENDING&statuses=PROCESSING`, {
                headers: {'Authorization': 'Bearer ' + token}
            });
            let j2 = await r2.json();
            const item = (j2.data?.items || []).find(x => x.taskNo === taskNo) || (j.data && j.data.taskNo === taskNo ? j.data : null);
            const status = item?.status || j.data?.status || 'UNKNOWN';
            await new Promise(r => setTimeout(r, 3000));
            if (status === 'SUCCESS' || status === 'FAILED' || status === 'CANCELED') {
                return {finalStatus: status, item, singleTask: j.data, pollIters: i+1};
            }
        }
        return {finalStatus: 'TIMEOUT', last, pollIters: 24};
    }''', TASK_NO)

    print(f"  轮询结果: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

    # 如果有结果图，下载
    item = result.get('item') or result.get('singleTask')
    if item:
        print(f"\n=== 2. 任务详情 ===")
        print(json.dumps(item, ensure_ascii=False, indent=2))
        # 找结果图 URL
        result_url = item.get('resultUrl') or item.get('resultImage') or item.get('outputUrl')
        if not result_url:
            # 在嵌套字段里找
            def find_url(obj, depth=0):
                if depth > 5: return None
                if isinstance(obj, str) and ('r2.cloudflarestorage' in obj or 'oss' in obj or 'i2tools' in obj) and ('.png' in obj or '.webp' in obj or '.jpg' in obj or 'pixel' in obj or 'result' in obj or 'output' in obj):
                    return obj
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        r = find_url(v, depth+1)
                        if r: return r
                elif isinstance(obj, list):
                    for v in obj:
                        r = find_url(v, depth+1)
                        if r: return r
                return None
            result_url = find_url(item)
        print(f"  结果图 URL: {result_url}")

        if result_url:
            # 下载（通过 page.evaluate fetch 转 base64，避开跨域）
            print("\n=== 3. 下载结果图 ===")
            b64 = page.evaluate('''async (url) => {
                const r = await fetch(url);
                const blob = await r.blob();
                const reader = new FileReader();
                return new Promise(res => {
                    reader.onload = () => res({ok: true, b64: reader.result, type: blob.type, size: blob.size});
                    reader.onerror = () => res({ok: false, err: 'reader error'});
                    reader.readAsDataURL(blob);
                });
            }''', result_url)
            print(f"  下载结果: ok={b64.get('ok')} type={b64.get('type')} size={b64.get('size')}")
            if b64.get('ok') and b64.get('b64'):
                import base64
                data = b64['b64'].split(',', 1)[1]
                ext = b64.get('type', 'image/png').split('/')[-1].split(';')[0]
                out = f'/workspace/pixelart_result_{TASK_NO}.{ext}'
                with open(out, 'wb') as f:
                    f.write(base64.b64decode(data))
                print(f"  ✓ 已保存到 {out}")

    # 查积分最终状态
    print("\n=== 4. 积分最终状态 ===")
    pts = page.evaluate('''async () => {
        const auth = JSON.parse(localStorage.getItem('auth-storage') || '{}');
        const token = auth.state?.accessToken;
        const r = await fetch('/v1/app/points/summary', {headers: {'Authorization': 'Bearer ' + token}});
        return await r.json();
    }''')
    print(f"  {json.dumps(pts, ensure_ascii=False)[:300]}")

    browser.close()
