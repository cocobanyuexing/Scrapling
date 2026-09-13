"""找登录 API URL"""
import re, glob, os

CHUNKS_DIR = '/workspace/i2tools/i2tools.com/_next/static/chunks'
files = sorted(glob.glob(f'{CHUNKS_DIR}/*.js'))

# 找所有含 login/sign-in 的 chunk + 上下文
print("="*60)
print("所有含 login/sign-in 的 chunk + 上下文")
print("="*60)

KW = ['login', 'signin', 'sign-in', 'auth/sign', 'loginBy', 'authenticate', 'auth/login']
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            c = fp.read()
        # 找 API URL 模式: 'url-path' 或 "url-path"
        path_ms = list(re.finditer(r'["\'`](/v1/app/[\w/\-{}:]*?(?:login|sign|auth|session)[\w/\-{}:]*)["\'`]', c, re.IGNORECASE))
        if path_ms:
            name = os.path.basename(f)
            print(f"\n  {name}:")
            for m in path_ms[:5]:
                s = max(0, m.start()-100)
                e = min(len(c), m.end()+200)
                print(f"    位置 {m.start()}: {c[s:e][:300]}")
    except: pass

# 找登录 service 函数
print("\n" + "="*60)
print("登录 service 函数")
print("="*60)
for f in files:
    try:
        with open(f, encoding='utf-8') as fp:
            c = fp.read()
        # 找 o.L.post('/auth/...') 等
        ms = list(re.finditer(r'\w+\.post\([\'"`][^\'"`]*(?:login|sign|auth|session)[^\'"`]*[\'"`]', c, re.IGNORECASE))
        if ms:
            name = os.path.basename(f)
            print(f"\n  {name}:")
            for m in ms[:5]:
                s = max(0, m.start()-100)
                e = min(len(c), m.end()+200)
                print(f"    {c[s:e][:400]}")
    except: pass

# 看 chunk 356 (含 login)
print("\n" + "="*60)
print("chunk 356 详细")
print("="*60)
with open(f'{CHUNKS_DIR}/356-c0386ce8d90ed827.js', encoding='utf-8') as f:
    c356 = f.read()
print(f"  大小: {len(c356)}")
# 找 login 上下文
for m in re.finditer(r'login', c356, re.IGNORECASE):
    s = max(0, m.start()-150)
    e = min(len(c356), m.end()+300)
    ctx = c356[s:e]
    if 'post' in ctx.lower() or 'api' in ctx.lower() or '/v1' in ctx.lower():
        print(f"\n  位置 {m.start()}:")
        print(f"    {ctx[:500]}")
        break
