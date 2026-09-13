"""切片提取 minified JS 关键上下文。"""
import re

KEYS = {
    '9872-c5b827a0694e9972.js': [
        'three', 'THREE.', 'WebGLRenderer', 'pixi', 'Application', 'Renderer3D',
        'createShader', 'fragmentShader', 'vertexShader', 'gl_Position', 'gl_FragColor',
        'roundPixels', 'modelViewProjectionMatrix', 'instanced', 'bead', 'cylinder',
        '拼豆', '烫豆', '毛巾', '3D', 'pegboard', 'shadow', 'ambient', 'rotate',
    ],
    '3107-465456a81e8a9713.js': [
        '.pbp', 'magic', 'version', 'importPbpProjectFile', 'serialize', 'deserialize',
        'FileReader', 'readAsArrayBuffer', 'readAsText', 'TextDecoder',
        'pixelGrid', 'palette', 'colorSystem', 'mard', 'projectName',
        'invalidFormat', 'versionMismatch', 'incompleteData', 'parseFailed',
        'indexedDB', 'objectStore', 'cloud-backup', 'cloudBackup',
    ],
    '6777-710cc5ad9e725047.js': [
        'mard', 'MARD', 'colorSystem', 'colorCounts', 'totalBeadCount', 'rebuildComposite',
        'areaThreshold', 'passes', 'highContrastThreshold', 'maxColorDistance',
        'minContactRatioPercent', 'light', 'balanced', 'strong', 'aggressive',
        'connectedComponent', '8-connected', '4-connected', 'neighbor',
        'denoise', 'removeNoise', 'merge', 'colorDistance',
    ],
    '9350-9895fcf460f5295c.js': [
        'mard', 'MARD', 'brands.mard', 'definitions', 'H2', 'H7', 'H16', 'H19',
        'G3', 'G17', 'C18', 'M1', 'M15', 'colorSystem', 'colors', 'palette',
    ],
    '8323-91d16d9a3585ddd3.js': [
        '.pbp', 'magic', 'version', 'serialize', 'deserialize',
        'smartImport', 'blueprint', 'recognize', 'createSmartImportProjectRecord',
        '/v1/app/', 'inventory', 'stock', 'deduct', 'merge', 'denoise',
    ],
    '1720-fa8a8467cef59a57.js': [
        'smartImport', 'blueprint', 'recognize', 'createSmartImportProjectRecord',
        '/v1/app/', '.pbp', 'inventory', 'xhs', '小红书',
    ],
}

BASE = '/workspace/i2tools/i2tools.com/_next/static/chunks/'

for fname, keys in KEYS.items():
    path = BASE + fname
    print(f"\n{'='*70}\n# {fname}\n{'='*70}")
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.read()
        print(f"  文件大小: {len(content)} chars")
    except FileNotFoundError:
        print(f"  ✗ 文件不存在")
        continue

    for k in keys:
        # 找所有出现位置
        positions = []
        start = 0
        while True:
            idx = content.find(k, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + len(k)
            if len(positions) >= 5:
                break
        if not positions:
            continue
        print(f"\n  ## '{k}' 出现 {len(positions)} 次（前5个）:")
        for i, pos in enumerate(positions[:3]):
            ctx_start = max(0, pos - 100)
            ctx_end = min(len(content), pos + len(k) + 200)
            snippet = content[ctx_start:ctx_end]
            # 清洗换行
            snippet = snippet.replace('\n', '\\n')
            print(f"    [{i}] @{pos}: ...{snippet}...")
