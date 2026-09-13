"""反编译 perfect-pixel to.aS 函数体"""
import re

CHUNK = '/workspace/i2tools/i2tools.com/_next/static/chunks/1720-fa8a8467cef59a57.js'

with open(CHUNK, encoding='utf-8') as f:
    c = f.read()

print(f"chunk 大小: {len(c)} 字符")

# 找 perfect-pixel 函数定义
# 通常是 to.aS = function(... 或 function aS(
patterns = [
    r'to\.aS\s*=\s*function[^{]*\{[\s\S]{0,3000}?\}',
    r'\.aS\s*=\s*function[^{]*\{[\s\S]{0,3000}?\}',
    r'function\s+aS[\s\S]{0,300}?\{[\s\S]{0,3000}?\}',
]

for i, pat in enumerate(patterns):
    matches = re.findall(pat, c)
    if matches:
        print(f"\n--- 模式 {i}: 命中 {len(matches)} 处 ---")
        for j, m in enumerate(matches[:2]):
            print(f"  match {j}: {m[:1500]}")
            print()

# 如果上面没找到, 直接找 perfectPixel 函数
print("\n--- 找 perfectPixel 函数 ---")
m = re.search(r'perfectPixel[^{]{0,200}\{', c)
if m:
    s = m.start()
    # 找匹配的右大括号
    depth = 0
    for k in range(s, min(s+8000, len(c))):
        if c[k] == '{': depth += 1
        elif c[k] == '}':
            depth -= 1
            if depth == 0:
                func_body = c[s:k+1]
                print(f"  perfectPixel 函数 (位置 {s}-{k}, 长度 {len(func_body)}):")
                print(func_body[:3000])
                break

# 找 to.aS 函数定义位置
print("\n--- 找 to.aS = ... ---")
m = re.search(r'to\.aS\s*=', c)
if m:
    s = m.start()
    e = min(s + 5000, len(c))
    snippet = c[s:e]
    print(f"  位置 {s}: {snippet[:3000]}")
