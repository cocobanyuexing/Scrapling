"""实测 3 v2: 找正确的库存扣减 API + 用浏览器内 fetch (自动带 cookie)"""
from patchright.sync_api import sync_playwright
import json, os, time, re

EMAIL = 'aq.jinlong@163.com'
PWD = 'abc123456'

# 先反编译所有 chunk 找库存扣减 API
import glob
CHUNKS_DIR = '/workspace/i2tools/i2tools.com/_next/static/chunks'
files = sorted(glob.glob(f'{CHUNKS_DIR}/*.js'))

print("=" * 60)
print("【全 chunk 扫描】库存扣减相关 API 路径")
print("=" * 60)

KW_PATTERNS = [
    '/v1/app/inventory',
    '/v1/app/stock',
    '/v1/app/bead',
    '/v1/app/inventory/deduct',
    '/v1/app/inventory/consume',
    '/v1/app/inventory/use',
    'inventory/deduct',
    'inventory/consume',
    'stock/deduct',
    'deductInventory',
    'consumeInventory',
    'useInventory',
    'subtractStock',
]

chunks = {}
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            chunks[os.path.basename(f)] = fp.read()
    except: pass

for kw in KW_PATTERNS:
    hits = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0: hits.append((name, n))
    if hits:
        print(f"\n[{kw}]")
        for n, c in sorted(hits, key=lambda x: -x[1])[:5]:
            print(f"  {n}: {c}")

# 找所有 /v1/app/* 库存相关
print("\n" + "=" * 60)
print("【全 chunk 扫描】所有 inventory/stock 路径")
print("=" * 60)
all_inv_paths = set()
for name, content in chunks.items():
    for m in re.finditer(r'/v1/app/(inventory|stock|bead)[\w/\-{}:]*', content):
        all_inv_paths.add(m.group())
print(f"路径总数: {len(all_inv_paths)}")
for p in sorted(all_inv_paths)[:30]:
    print(f"  {p}")

# 找扣减函数名
print("\n" + "=" * 60)
print("【扣减函数名】")
print("=" * 60)
for kw in ['deduct', 'consume', 'subtract', 'decrement']:
    hits = []
    for name, content in chunks.items():
        ms = list(re.finditer(rf'\w*{kw}\w*', content, re.IGNORECASE))
        if ms:
            unique_words = set(m.group() for m in ms)
            if unique_words:
                hits.append((name, list(unique_words)[:5]))
    if hits:
        print(f"\n[{kw}]")
        for n, ws in sorted(hits, key=lambda x: -len(x[1]))[:3]:
            print(f"  {n}: {ws}")

# 真测试浏览器内 fetch 调用
print("\n" + "=" * 60)
print("【浏览器内 fetch 实测】")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--proxy-server=http://127.0.0.1:18080']
    )
    ctx = browser.new_context(viewport={'width': 1440, 'height': 950}, locale='zh-CN')
    page = ctx.new_page()

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

    # 进库存页让 cookie 重新激活
    page.goto('https://i2tools.com/workspace/inventory', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(3000)

    cookies = ctx.cookies()
    print(f"\n所有 cookie:")
    for c in cookies:
        if any(k in c['name'].lower() for k in ['token', 'session', 'xsrf', 'csrf', 'auth']):
            print(f"  {c['name']}: {c['value'][:60]}...")

    # 试 fetch with credentials
    print("\n--- 浏览器内 fetch GET /v1/app/inventory/summary ---")
    result = page.evaluate('''async () => {
        try {
            const r = await fetch('/v1/app/inventory/summary', {
                credentials: 'include'
            });
            const text = await r.text();
            return {st: r.status, body: text.slice(0, 1500)};
        } catch(e) { return {err: String(e)}; }
    }''')
    print(f"  status: {result.get('st')}")
    print(f"  body: {result.get('body', '')[:1200]}")

    # 试 POST 扣减
    print("\n--- 浏览器内 fetch POST 尝试扣减 ---")
    # 取一个色号测试扣减
    test_payload = {
        "items": [{"colorCode": "H2", "count": 1}],
        "operation": "deduct"
    }
    result = page.evaluate('''async (payload) => {
        try {
            const r = await fetch('/v1/app/inventory/deduct', {
                method: 'POST',
                credentials: 'include',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const text = await r.text();
            return {st: r.status, body: text.slice(0, 1000)};
        } catch(e) { return {err: String(e)}; }
    }''', test_payload)
    print(f"  POST /deduct status: {result.get('st')}")
    print(f"  body: {result.get('body', '')[:600]}")

    # 也试 consume
    result = page.evaluate('''async (payload) => {
        try {
            const r = await fetch('/v1/app/inventory/consume', {
                method: 'POST',
                credentials: 'include',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const text = await r.text();
            return {st: r.status, body: text.slice(0, 1000)};
        } catch(e) { return {err: String(e)}; }
    }''', test_payload)
    print(f"\n  POST /consume status: {result.get('st')}")
    print(f"  body: {result.get('body', '')[:600]}")

    ctx.close(); browser.close()
print("\nDONE")
