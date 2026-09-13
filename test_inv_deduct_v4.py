"""实测 3 v4: 挖 chunk 6567 真实扣减 API + 走 UI 真正执行扣减流程"""
import re

CHUNKS = {
    '6567': '/workspace/i2tools/i2tools.com/_next/static/chunks/6567-de9b1e7224a4224d.js',
    '1386': '/workspace/i2tools/i2tools.com/_next/static/chunks/1386-a92cea6265f3ca30.js',
    '2298': '/workspace/i2tools/i2tools.com/_next/static/chunks/2298-44d97b4fb3a2cf27.js',
}

for name, path in CHUNKS.items():
    print(f"\n{'='*60}")
    print(f"chunk {name}")
    print(f"{'='*60}")
    with open(path, encoding='utf-8') as f:
        c = f.read()
    print(f"  大小: {len(c)}")

    # 找所有 /v1/app/* 路径
    paths = set()
    for m in re.finditer(r'["\'`](/v1/app/[\w/\-{}:]+)["\'`]', c):
        paths.add(m.group(1))
    print(f"  /v1/app/* 路径: {len(paths)}")
    for p in sorted(paths):
        print(f"    {p}")

    # 扣减相关上下文
    for kw in ['subtract', 'deduct', 'consume', 'consumeQuantity', 'remarkSubtract', 'projectInventoryConsumeDialog']:
        ms = list(re.finditer(rf'\b{re.escape(kw)}\b', c))
        if ms:
            print(f"\n  [{kw}] 命中 {len(ms)} 处, 第一处上下文:")
            m = ms[0]
            s = max(0, m.start() - 200)
            e = min(len(c), m.end() + 600)
            print(f"    {c[s:e]}")

# 也看 inventory 周边的 API
print(f"\n{'='*60}")
print("所有 chunk 中的 /inventory 相关 URL")
print(f"{'='*60}")
import glob
files = sorted(glob.glob('/workspace/i2tools/i2tools.com/_next/static/chunks/*.js'))
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            c = fp.read()
        ms = list(re.finditer(r'/[\w/\-{}:]*(inventory|stock|consume|subtract|deduct)[\w/\-{}:]*', c, re.IGNORECASE))
        if ms:
            paths = set(m.group() for m in ms)
            name = f.split('/')[-1]
            for p in sorted(paths):
                if '/' in p and len(p) < 80 and ('v1' in p or 'api' in p):
                    print(f"  {name}: {p}")
    except: pass

print("\nDONE")
