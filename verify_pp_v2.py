"""更宽泛搜索 perfect-pixel 主算法实现"""
import re

CHUNK = '/workspace/i2tools/i2tools.com/_next/static/chunks/1720-fa8a8467cef59a57.js'

with open(CHUNK, encoding='utf-8') as f:
    c = f.read()

# 用关键特征找主算法
# perfect-pixel 应该有: alignPixel, snap, boundary, quantize, subpixel, halfPixel 等
KEY_FEATURES = [
    'subpixel', 'sub-pixel', 'subPixel',
    'halfPixel', 'half-pixel', 'halfPixel',
    'quantize', 'snapToGrid', 'snap_to_grid',
    'boundaryScan', 'boundary_scan',
    'resample', 're-sample',
    'nearestNeighbor', 'nearest_neighbor',
    'pixelPerfect', 'pixel_perfect',
    'fixHalfPixel',
    'referenceLayer', 'pixelLayer',
    'gridDimensions',
]

print("=" * 60)
print("用关键特征搜索 perfect-pixel 主算法")
print("=" * 60)

for kw in KEY_FEATURES:
    matches = list(re.finditer(re.escape(kw), c, re.IGNORECASE))
    if matches:
        print(f"\n[{kw}] 命中 {len(matches)} 处:")
        for m in matches[:2]:
            s = max(0, m.start() - 200)
            e = min(len(c), m.end() + 500)
            ctx = c[s:e]
            print(f"  位置 {m.start()}: ...{ctx}...")
            print()

# 也看 perfectPixel 周围更宽的上下文
print("\n" + "=" * 60)
print("perfectPixel 关键字周围 3000 字符")
print("=" * 60)
for m in re.finditer('perfectPixel', c, re.IGNORECASE):
    s = max(0, m.start() - 300)
    e = min(len(c), m.end() + 3000)
    ctx = c[s:e]
    print(f"\n位置 {m.start()}:")
    print(ctx[:3000])
    print("---")

# 看 chunk 1720 整体导出符号
print("\n" + "=" * 60)
print("chunk 1720 所有 export 符号")
print("=" * 60)
exports = re.findall(r'(\w+)\.(\w+)\s*=\s*function', c)
exports_set = set()
for o, p in exports:
    exports_set.add(f"{o}.{p}")
print(f"  函数定义总数: {len(exports_set)}")
# 找 aS 周围符号
for sym in sorted(exports_set):
    if 'aS' in sym or 'perfer' in sym.lower() or 'fix' in sym.lower() or 'align' in sym.lower() or 'snap' in sym.lower() or 'quant' in sym.lower():
        print(f"  - {sym}")

# 直接查 to 这个对象的导出
print("\n--- to.* 函数清单 ---")
to_funcs = [m.group(1) for m in re.finditer(r'to\.(\w+)\s*=', c)]
print(f"  to.* 总数: {len(to_funcs)}")
for fn in sorted(set(to_funcs))[:30]:
    print(f"  - to.{fn}")
