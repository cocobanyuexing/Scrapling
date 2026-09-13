"""追查真实算法实现 v4
1) chunk 1386 - 去噪算法实际代码(stray/noise 命中)
2) chunk 2298 - 拼图图纸识别真实算法(图纸/识别 命中)
3) chunk 3107 - smartImport 真实流程
4) 看 xhs-worker 服务端 worker 真实接口
"""
import re, os, glob

CHUNKS_DIR = '/workspace/i2tools/i2tools.com/_next/static/chunks'
files = sorted(glob.glob(f'{CHUNKS_DIR}/*.js'))
chunks = {}
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            chunks[os.path.basename(f)] = fp.read()
    except: pass

def ctx(text, kw, before=200, after=600, max_hits=3):
    out = []
    for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
        s = max(0, m.start()-before)
        e = min(len(text), m.end()+after)
        out.append((m.start(), text[s:e]))
        if len(out) >= max_hits: break
    return out

# 1) chunk 1386 - 去噪算法实际代码
print("=" * 80)
print("【任务1】chunk 1386 - 去噪算法实际代码")
print("=" * 80)
c1386 = chunks.get('1386-a92cea6265f3ca30.js', '')
print(f"  文件大小: {len(c1386)} 字符")
for kw in ['stray', 'noise', 'denoise', 'removeStray', 'island',
           'connectivity', 'component', 'floodFill', 'flood',
           'queue', 'stack', 'visited', 'mark', 'neighbor',
           'passes', 'areaThreshold', 'contactRatio', 'maxColorDistance']:
    hits = ctx(c1386, kw, 200, 500, 2)
    if hits:
        print(f"\n  [{kw}] 命中 {len(hits)} 处:")
        for pos, c in hits:
            print(f"    位置 {pos}: ...{c[:600]}...")
            print()

# chunk 1386 前 1500 字符了解概况
print("\n  --- chunk 1386 前 1500 字符 ---")
print(c1386[:1500])

# 2) chunk 2298 - 拼图图纸识别真实算法
print("\n" + "=" * 80)
print("【任务2】chunk 2298 - 拼图图纸识别真实算法")
print("=" * 80)
c2298 = chunks.get('2298-44d97b4fb3a2cf27.js', '')
print(f"  文件大小: {len(c2298)} 字符")
# 查"图纸"/"识别"上下文
for kw in ['图纸', '识别', '智能', '转换', 'sampleImage', 'MARD', 'colorSystem',
           'pixelsPerCell', 'cellSize', 'gridSize', 'imageToGrid']:
    hits = ctx(c2298, kw, 200, 500, 2)
    if hits:
        print(f"\n  [{kw}] 命中 {len(hits)} 处:")
        for pos, c in hits:
            print(f"    位置 {pos}: ...{c[:600]}...")
            print()

# 3) chunk 3107 - smartImport 流程
print("\n" + "=" * 80)
print("【任务3】chunk 3107 - smartImport 流程")
print("=" * 80)
c3107 = chunks.get('3107-465456a81e8a9713.js', '')
print(f"  文件大小: {len(c3107)} 字符")
for kw in ['smartImport', 'imageConvert', 'MARD', 'patternMatch', 'pattern_match',
           'visualMatch', 'visual_match', 'extractColor', 'extract_color',
           'sampleRegion', 'sample_region', 'processImage', 'process_image']:
    hits = ctx(c3107, kw, 200, 500, 2)
    if hits:
        print(f"\n  [{kw}] 命中 {len(hits)} 处:")
        for pos, c in hits:
            print(f"    位置 {pos}: ...{c[:700]}...")
            print()

# 4) xhs-worker 服务端 worker 真实接口
print("\n" + "=" * 80)
print("【任务4】xhs-worker 服务端 worker 真实接口")
print("=" * 80)
c1720 = chunks['1720-fa8a8467cef59a57.js']
for kw in ['xhs-worker', '/extract', '/proxy', 'shareText', 'worker', 'XhsMedia']:
    hits = ctx(c1720, kw, 200, 500, 3)
    if hits:
        print(f"\n  [{kw}] 命中:")
        for pos, c in hits:
            print(f"    位置 {pos}: ...{c[:700]}...")
            print()

print("\nDONE")
