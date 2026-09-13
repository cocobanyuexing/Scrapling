"""反编译关键 chunk, 提取算法实现的真实代码段
验证: 1)颜色匹配 2)K-D Tree 3)Median Cut 4)去噪8连通域 5)拼图图纸识别
"""
import re, os

CHUNKS = {
    'color_8071': '/workspace/i2tools/i2tools.com/_next/static/chunks/8071-30a1b464baed2037.js',
    'denoise_6777': '/workspace/i2tools/i2tools.com/_next/static/chunks/6777-710cc5ad9e725047.js',
    '3d_9872': '/workspace/i2tools/i2tools.com/_next/static/chunks/9872-c5b827a0694e9972.js',
    'mard_9350': '/workspace/i2tools/i2tools.com/_next/static/chunks/9350-9895fcf460f5295c.js',
    'idb_7824': '/workspace/i2tools/i2tools.com/_next/static/chunks/7824-a12ba49ff917cbc3.js',
    'xhs_1720': '/workspace/i2tools/i2tools.com/_next/static/chunks/1720-fa8a8467cef59a57.js',
}

def extract_context(text, keyword, before=200, after=400):
    """提取关键字周围的代码上下文"""
    out = []
    for m in re.finditer(re.escape(keyword), text, re.IGNORECASE):
        s = max(0, m.start()-before)
        e = min(len(text), m.end()+after)
        ctx = text[s:e]
        out.append((m.start(), ctx))
    return out

print("=" * 80)
print("【验证1】chunk 8071 - 颜色匹配算法")
print("=" * 80)
with open(CHUNKS['color_8071'], encoding='utf-8') as f:
    c8071 = f.read()
print(f"  文件大小: {len(c8071)} 字符")

# 验证 DeltaE / CAM16
for kw in ['deltaE', 'DeltaE', 'CAM16', 'cam16', 'cieLab', 'CIEDE2000', 'lab2', 'srgb', 'XYZ']:
    ctxs = extract_context(c8071, kw, 150, 300)
    if ctxs:
        print(f"\n  [{kw}] 命中 {len(ctxs)} 处:")
        for i, (pos, ctx) in enumerate(ctxs[:2]):
            print(f"    位置 {pos}: ...{ctx[:400]}...")
            print()

# 验证 K-D Tree / Median Cut
print("\n  --- K-D Tree / Median Cut 验证 ---")
for kw in ['kdTree', 'kdtree', 'nearest', 'closest', 'median', 'split', 'bucket', 'quantiz', 'palette']:
    ctxs = extract_context(c8071, kw, 100, 250)
    if ctxs:
        print(f"\n  [{kw}] 命中 {len(ctxs)} 处:")
        for pos, ctx in ctxs[:1]:
            print(f"    ...{ctx[:350]}...")

print("\n" + "=" * 80)
print("【验证2】chunk 6777 - 去噪/连通域算法")
print("=" * 80)
with open(CHUNKS['denoise_6777'], encoding='utf-8') as f:
    c6777 = f.read()
print(f"  文件大小: {len(c6777)} 字符")

# 实际去噪算法实现
for kw in ['connectedComponent', 'floodFill', 'BFS', 'DFS', 'island', 'stray', 'smallArea', 'removeSmall', '8connected', 'neighbor', 'adjacent', 'component']:
    ctxs = extract_context(c6777, kw, 150, 350)
    if ctxs:
        print(f"\n  [{kw}] 命中 {len(ctxs)} 处:")
        for pos, ctx in ctxs[:2]:
            print(f"    位置 {pos}: ...{ctx[:500]}...")

print("\n" + "=" * 80)
print("【验证3】chunk 9872 - 3D 渲染 + canny/sobel 真实上下文")
print("=" * 80)
with open(CHUNKS['3d_9872'], encoding='utf-8') as f:
    c9872 = f.read()
print(f"  文件大小: {len(c9872)} 字符")

# canny/sobel 在 chunk 9872 里的真实用途
for kw in ['canny', 'sobel', 'edgeDetection', 'gradient', 'hough', 'contour', 'scharr', 'prewitt', 'laplacian']:
    ctxs = extract_context(c9872, kw, 200, 500)
    if ctxs:
        print(f"\n  [{kw}] 命中 {len(ctxs)} 处:")
        for pos, ctx in ctxs[:3]:
            print(f"    位置 {pos}: ...{ctx[:600]}...")

print("\n" + "=" * 80)
print("【验证4】chunk 9350 - MARD 色号体系")
print("=" * 80)
with open(CHUNKS['mard_9350'], encoding='utf-8') as f:
    c9350 = f.read()
print(f"  文件大小: {len(c9350)} 字符")

for kw in ['mard', 'MARD', 'H2', 'G5', 'C12', 'M8', 'brands', 'definitions']:
    ctxs = extract_context(c9350, kw, 100, 300)
    if ctxs:
        print(f"\n  [{kw}] 命中 {len(ctxs)} 处:")
        for pos, ctx in ctxs[:1]:
            print(f"    ...{ctx[:400]}...")

print("\nDONE")
