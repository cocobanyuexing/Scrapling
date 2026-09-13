"""实测 3 v5: 找 eu() 调用的真实 API + 走 UI 真触发扣减"""
import re

# chunk 6567 的 eu() 是 useMutation hook 包装, 真实 API URL 在 service 层
# 找 r() 引用的 chunk
with open('/workspace/i2tools/i2tools.com/_next/static/chunks/6567-de9b1e7224a4224d.js', encoding='utf-8') as f:
    c6567 = f.read()

# eu 的定义
m = re.search(r'eu\s*=\s*\w+', c6567)
if m:
    print(f"eu 定义位置 {m.start()}: {c6567[m.start():m.start()+200]}")

# 找 eu 周围更多上下文 (上下 3000 字符)
m = re.search(r'function eu\b|let eu\b|const eu\b|var eu\b|eu\s*=', c6567)
if m:
    s = max(0, m.start() - 500)
    e = min(len(c6567), m.end() + 3000)
    print(f"\neu 上下文:")
    print(c6567[s:e])

# 找所有 axios.post/put/patch 调用 + 库存相关
print(f"\n{'='*60}")
print("chunk 6567 所有 mutation 调用")
print(f"{'='*60}")
patterns = [
    r'\w+\.post\([^)]{0,200}',
    r'\w+\.put\([^)]{0,200}',
    r'\w+\.patch\([^)]{0,200}',
    r'mutate\([^)]{0,200}',
    r'mutateAsync\([^)]{0,200}',
]
for pat in patterns:
    ms = list(re.finditer(pat, c6567))
    if ms:
        print(f"\n[{pat}] 命中 {len(ms)}")
        for m in ms[:5]:
            print(f"  {c6567[max(0,m.start()-50):m.end()+50]}")

# 找 inventory store 的引用
print(f"\n{'='*60}")
print("chunk 6567 引用的 r(N) 模块")
print(f"{'='*60}")
# var X=r(N) 然后用 X.post()
ms = re.findall(r'(\w+)\s*=\s*r\((\d+)\)', c6567)
print(f"r() 引用: {len(ms)}")
for var, mod in ms[:10]:
    print(f"  {var} = r({mod})")
    # 看 var 怎么被用
    usage = re.findall(rf'{var}\.\w+\([^)]{{0,200}}', c6567)
    if usage:
        print(f"    使用: {usage[:3]}")

# 在所有 chunk 找含 inventory/stock/consume API 的 chunk
print(f"\n{'='*60}")
print("全 chunk 搜 'inventory' 字串")
print(f"{'='*60}")
import glob, os
files = sorted(glob.glob('/workspace/i2tools/i2tools.com/_next/static/chunks/*.js'))
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            c = fp.read()
        # 找 inventory 字串 + 附近有 fetch/axios/post
        if 'inventory' in c.lower():
            ms = list(re.finditer(r'inventory', c, re.IGNORECASE))
            if ms:
                name = os.path.basename(f)
                # 找带 path 的
                path_ms = list(re.finditer(r'/v1/[\w/\-{}:]*inventory[\w/\-{}:]*|inventory/[\w/\-{}:]+', c))
                if path_ms:
                    print(f"\n  {name}:")
                    for m in path_ms[:5]:
                        s = max(0, m.start() - 100)
                        e = min(len(c), m.end() + 200)
                        print(f"    位置 {m.start()}: {c[s:e][:300]}")
    except: pass

print("\nDONE")
