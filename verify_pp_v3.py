"""精准定位 xhs-worker 和 perfect-pixel 真实 API"""
import re

CHUNK = '/workspace/i2tools/i2tools.com/_next/static/chunks/1720-fa8a8467cef59a57.js'

with open(CHUNK, encoding='utf-8') as f:
    c = f.read()

# 1) xhs-worker 上下文
print("=" * 60)
print("【1】xhs-worker 上下文")
print("=" * 60)
for m in re.finditer(r'xhs-worker', c):
    s = max(0, m.start() - 400)
    e = min(len(c), m.end() + 400)
    print(f"位置 {m.start()}: {c[s:e]}")
    print()

# 2) /extract /proxy 上下文
print("\n" + "=" * 60)
print("【2】/extract /proxy 上下文")
print("=" * 60)
for kw in ['/extract', '/proxy', 'shareText', 'XhsMediaExtractor', 'worker']:
    for m in re.finditer(re.escape(kw), c):
        s = max(0, m.start() - 200)
        e = min(len(c), m.end() + 400)
        print(f"\n[{kw}] 位置 {m.start()}:")
        print(c[s:e])
        break  # 只看第一处

# 3) perfect-pixel 处理流程
print("\n" + "=" * 60)
print("【3】perfect-pixel 处理流程")
print("=" * 60)
# perfect-pixel 的 API 调用模式
for kw in ['refineImage', 'refine_image', 'perfectPixelRefine', 'refine', 'perfect-pixel', '/refine', '/v1/app/perfect']:
    for m in re.finditer(re.escape(kw), c, re.IGNORECASE):
        s = max(0, m.start() - 200)
        e = min(len(c), m.end() + 500)
        print(f"\n[{kw}] 位置 {m.start()}:")
        print(c[s:e])
        break  # 只看第一处

# 4) 看 perfect-pixel 工具页面的 state 调用 (找处理入口)
print("\n" + "=" * 60)
print("【4】perfect-pixel 入口 - state 调用")
print("=" * 60)
# 找 onRefine / onProcess / handleProcess 等
for kw in ['onRefine', 'onProcess', 'handleProcess', 'handleRefine', 'processImage', 'startRefine', 'triggerRefine']:
    for m in re.finditer(re.escape(kw), c):
        s = max(0, m.start() - 200)
        e = min(len(c), m.end() + 500)
        print(f"\n[{kw}] 位置 {m.start()}:")
        print(c[s:e])
        break

# 5) 直接看 perfect-pixel page 路由
print("\n" + "=" * 60)
print("【5】查找 perfect-pixel 路由 page 文件")
print("=" * 60)
import glob, os
files = sorted(glob.glob('/workspace/i2tools/i2tools.com/_next/static/chunks/app/**/*.js', recursive=True))
print(f"app/ 下 chunk 总数: {len(files)}")
# 含 perfect 的
for f in files:
    name = os.path.basename(f)
    # 试读前 500 字符看是否是 perfect-pixel 页面
    try:
        with open(f, encoding='utf-8') as fp:
            head = fp.read(2000)
        if 'perfect' in head.lower() or 'refine' in head.lower():
            print(f"\n  命中文件: {name}")
            print(f"  前 500 字符: {head[:500]}")
    except: pass
