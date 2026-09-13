"""精确切片提取：3D 引擎特征 + IndexedDB schema。"""
import os

BASE = '/workspace/i2tools/i2tools.com/_next/static/chunks/'

def slice_file(fname, keys, ctx_before=120, ctx_after=300, max_hits=3):
    path = BASE + fname
    print(f"\n{'='*70}\n# {fname}\n{'='*70}")
    if not os.path.exists(path):
        print(f"  ✗ 文件不存在")
        return
    with open(path, encoding='utf-8', errors='replace') as f:
        content = f.read()
    print(f"  文件大小: {len(content)} chars")
    for k in keys:
        positions = []
        start = 0
        while True:
            idx = content.find(k, start)
            if idx == -1: break
            positions.append(idx)
            start = idx + len(k)
            if len(positions) >= 8: break
        if not positions:
            continue
        print(f"\n  ## '{k}' @{len(positions)} 次 (前{max_hits}):")
        for i, pos in enumerate(positions[:max_hits]):
            s = max(0, pos - ctx_before)
            e = min(len(content), pos + len(k) + ctx_after)
            snip = content[s:e].replace('\n', '\\n')
            print(f"    [{i}] @{pos}: ...{snip}...")

# 1) 3D 引擎特征
slice_file('9872-c5b827a0694e9972.js', [
    'Application', 'WebGLRenderer', 'three.module', 'THREE.',
    'Renderer3D', 'Mesh', 'Camera', 'Scene', 'Geometry',
    'bead', 'cylinder', 'Pegboard', '拼豆板', '烫豆', '毛巾',
    'roundPixels', 'modelViewProjectionMatrix', 'instanced',
    'shadow', 'ambient', 'rotateY',
])

# 2) IndexedDB schema - 在所有命中文件搜
print("\n\n" + "="*70)
print("# IndexedDB schema 搜索（多文件）")
print("="*70)
for fname in ['4907-8c12cfdbedfc227c.js', '757-8eb555c67879de3b.js',
              '7808-a7ed9686b058a80c.js', '7824-a12ba49ff917cbc3.js',
              '8323-91d16d9a3585ddd3.js']:
    slice_file(fname, [
        'indexedDB', 'objectStore', 'openDatabase', 'IDBDatabase',
        'magic-perler', 'project-storage', 'createObjectStore',
        'magicNumber', 'signatureBytes', '.pbp',
        'pixelGrid', 'colorSystem', 'autosaveRevision',
        'cloudBackup', 'cloud-backup',
    ], ctx_before=80, ctx_after=200, max_hits=2)
