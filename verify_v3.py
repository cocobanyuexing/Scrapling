"""追查真实算法实现 v3
1) perfect-pixel 在 chunk 1720 的真实算法
2) 拼图图纸识别真实算法
3) 去噪算法的实际实现(BFS 还是别的)
4) 找小红书导入在哪个 chunk
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

# 1) perfect-pixel 真实实现
print("=" * 80)
print("【任务1】chunk 1720 - perfect-pixel 真实算法")
print("=" * 80)
c1720 = chunks['1720-fa8a8467cef59a57.js']
print(f"  文件大小: {len(c1720)} 字符")
# 查 perfect-pixel 函数实现
for kw in ['perfectPixel', 'fixHalfPixel', 'snapToGrid', 'alignPixel',
           'boundaryScan', 'detectBoundary', 'halfPixel',
           'findGrid', 'detectGrid', 'findPixelSize', 'pixelSize']:
    hits = ctx(c1720, kw, 200, 500, 2)
    if hits:
        print(f"\n  [{kw}] 命中 {len(hits)} 处:")
        for pos, c in hits:
            print(f"    位置 {pos}: ...{c[:700]}...")
            print()

# 看 chunk 1720 前 2000 字符了解概况
print("\n  --- chunk 1720 前 2000 字符 ---")
print(c1720[:2000])

# 2) 拼图图纸识别真实算法 - 用更宽泛的关键字
print("\n" + "=" * 80)
print("【任务2】拼图图纸识别真实算法(宽泛搜索)")
print("=" * 80)
# 用业务关键字
PUZZLE_KW = ['smartImport', 'smart_import', 'imageConvert', 'image_convert',
             'pixelConvert', 'pixel_convert', 'recognizeImage', 'recognize_image',
             'detectPattern', 'pattern_detect', '图纸', '识别',
             'sampleImage', 'sample_image', 'gridImage', 'grid_image',
             'imageToGrid', 'image_to_grid', 'fromImage', 'from_image']
for kw in PUZZLE_KW:
    hits_files = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits_files.append((name, n))
    if hits_files:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits_files, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n}")

# 3) 去噪算法实际实现(BFS/DFS/迭代/扫描)
print("\n" + "=" * 80)
print("【任务3】去噪算法实际实现(BFS/DFS/迭代)")
print("=" * 80)
c6777 = chunks['6777-710cc5ad9e725047.js']
# 找连通域算法实现
for kw in ['queue', 'stack', 'iterative', 'recursive', 'scan', 'label',
           'visited', 'mark', 'flood', 'fill', 'traverse', 'walk',
           'forEach', 'for(', 'while(']:
    hits = ctx(c6777, kw, 200, 400, 2)
    if hits:
        print(f"\n  [{kw}] 命中:")
        for pos, c in hits[:1]:
            print(f"    位置 {pos}: ...{c[:500]}...")

# 4) 小红书导入在哪个 chunk
print("\n" + "=" * 80)
print("【任务4】小红书导入在哪个 chunk")
print("=" * 80)
XHS_KW = ['xiaohongshu', 'xhs', 'redNote', 'red_note', '小红书',
          'noteImport', 'note_import', 'xhsImport', 'xhs_import',
          'parseNote', 'parse_note', 'noteUrl', 'note_url']
for kw in XHS_KW:
    hits_files = []
    for name, content in chunks.items():
        n = len(re.findall(re.escape(kw), content, re.IGNORECASE))
        if n > 0:
            hits_files.append((name, n))
    if hits_files:
        print(f"\n  [{kw}]")
        for name, n in sorted(hits_files, key=lambda x: -x[1])[:3]:
            print(f"    {name}: {n}")

# 5) app/pages 路由 chunk - 找工具页
print("\n" + "=" * 80)
print("【任务5】工具页路由 chunk 实际功能")
print("=" * 80)
app_files = [f for f in files if '/app/' in f]
for f in app_files:
    name = os.path.basename(f)
    size = len(chunks.get(name, ''))
    print(f"  {name}: {size} 字符")

# 看 [toolId]/page 的内容(这是工具页路由)
toolId_path = f'{CHUNKS_DIR}/app/[locale]/(workspace)/workspace/tools/[toolId]/page-edb463d4c1f8e95c.js'
if os.path.exists(toolId_path):
    print(f"\n  --- [toolId]/page 前 1500 字符 ---")
    with open(toolId_path, encoding='utf-8') as fp:
        print(fp.read()[:1500])

print("\nDONE")
