"""追查真实算法位置
1) 去噪算法在哪个 chunk
2) 拼图图纸识别在哪个 chunk
3) perfect-pixel 修正算法
4) 重新审视 chunk 6777 实际是什么
"""
import re, os, glob

CHUNKS_DIR = '/workspace/i2tools/i2tools.com/_next/static/chunks'
files = sorted(glob.glob(f'{CHUNKS_DIR}/*.js'))

# 关键搜索: 找去噪算法(用更宽泛的关键字)
DENOISE_KW = ['denoise', 'removeStray', 'stray', 'noise', 'noiseLevel',
              'light', 'balanced', 'strong', 'aggressive',
              'connectedComponent', 'floodFill', 'island', 'component8',
              'eightConnected', 'adjacent8', 'neighbor8',
              'smallArea', 'removeSmall', 'isolatedPixel', 'removeIsolated']

# 拼图图纸识别算法
PUZZLE_KW = ['canny', 'sobel', 'edgeDetection', 'edge_detection',
             'houghTransform', 'hough_transform', 'lineDetection',
             'gridDetection', 'detectGrid', 'findGrid',
             'beadDetection', 'detectBead', 'findCircle',
             'circleDetection', 'houghCircles']

# perfect-pixel 修正
PERFECT_KW = ['perfectPixel', 'perfect_pixel', 'fixHalfPixel',
              'alignPixel', 'quantizePixel', 'snapToGrid',
              'halfPixel', 'half_pixel', 'boundaryScan']

# 颜色量化(替代 Median Cut 的可能算法)
QUANTIZE_KW = ['medianCut', 'median_cut', 'kmeans', 'k-means',
               'octree', 'popularity', 'quantization', 'reduceColors']

print("=" * 80)
print("【扫描全部 chunk】寻找去噪/拼图/perfect-pixel/量化算法")
print("=" * 80)
print(f"扫描 {len(files)} 个 chunk 文件\n")

# 预加载所有 chunk
chunks = {}
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            chunks[os.path.basename(f)] = fp.read()
    except: pass

# 1) 去噪算法
print("\n" + "=" * 60)
print("【任务1】去噪算法在哪个 chunk?")
print("=" * 60)
for kw in DENOISE_KW:
    hits = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits.append((name, n))
    if hits:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n} 命中")

# 2) 拼图图纸识别
print("\n" + "=" * 60)
print("【任务2】拼图图纸识别算法在哪个 chunk?")
print("=" * 60)
for kw in PUZZLE_KW:
    hits = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits.append((name, n))
    if hits:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n} 命中")

# 3) perfect-pixel
print("\n" + "=" * 60)
print("【任务3】perfect-pixel 修正算法在哪个 chunk?")
print("=" * 60)
for kw in PERFECT_KW:
    hits = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits.append((name, n))
    if hits:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n} 命中")

# 4) 颜色量化(替代推测的 Median Cut)
print("\n" + "=" * 60)
print("【任务4】颜色量化算法(替代推测的 Median Cut)")
print("=" * 60)
for kw in QUANTIZE_KW:
    hits = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits.append((name, n))
    if hits:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n} 命中")

# 5) chunk 6777 实际是什么
print("\n" + "=" * 60)
print("【任务5】chunk 6777 实际是什么(前 2000 字符)")
print("=" * 60)
c6777 = chunks.get('6777-710cc5ad9e725047.js', '')
print(f"  大小: {len(c6777)} 字符")
print("  前 2000 字符:")
print(c6777[:2000])
print("\n  关键 export 符号:")
exports = re.findall(r'exports\.([a-zA-Z_$][a-zA-Z0-9_$]*)', c6777)
print(f"  exports 数量: {len(exports)}")
for e in exports[:20]:
    print(f"    exports.{e}")

print("\nDONE")
