// 复刻 i2tools 前端 pbp 解密逻辑 (chunk 3514, module 72592)
// 算法: PBKDF2(password="perler-beads-project-v1", salt="perler-salt", iter=100000, SHA-256)
//       -> AES-GCM-256, IV=前12字节, 密文=剩余字节
const fs = require('fs');
const crypto = require('crypto');

async function deriveKey() {
  // webcrypto 等价实现
  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey(
    'raw',
    enc.encode('perler-beads-project-v1'),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: enc.encode('perler-salt'), iterations: 100000, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt']
  );
}

(async () => {
  const file = process.argv[2] || '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp';
  const raw = fs.readFileSync(file, 'utf8');
  const parsed = JSON.parse(raw);
  console.log('=== .pbp 外层 ===');
  console.log('version :', parsed.version);
  console.log('format  :', parsed.format);
  console.log('data len:', parsed.data.length, 'chars');

  const bin = Buffer.from(parsed.data, 'base64');
  console.log('base64 decoded bytes :', bin.length);
  const iv = bin.slice(0, 12);
  const ct = bin.slice(12);
  console.log('IV (12 bytes, hex)   :', iv.toString('hex'));
  console.log('ciphertext bytes      :', ct.length);

  const key = await deriveKey();
  const exported = await crypto.subtle.exportKey('raw', key);
  console.log('derived AES key (hex) :', Buffer.from(exported).toString('hex'));

  let pt;
  try {
    pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  } catch (e) {
    console.error('DECRYPT FAILED:', e.message);
    process.exit(2);
  }
  const txt = Buffer.from(pt).toString('utf8');
  console.log('plaintext length      :', txt.length, 'chars');
  // 写出明文用于结构分析
  const out = file.replace(/\.pbp$/i, '.pbp.plain.json');
  fs.writeFileSync(out, txt);
  console.log('plain written to      :', out);

  const obj = JSON.parse(txt);
  console.log('=== 解密后顶层结构 ===');
  console.log('top keys              :', Object.keys(obj));
  if (obj.pbpVersion !== undefined) console.log('pbpVersion           :', obj.pbpVersion);
  if (obj.project) {
    console.log('project keys          :', Object.keys(obj.project));
    if (obj.project.dataVersion !== undefined) console.log('  dataVersion       :', obj.project.dataVersion);
    if (obj.project.gridDimensions) console.log('  gridDimensions    :', obj.project.gridDimensions);
    if (obj.project.totalBeadCount !== undefined) console.log('  totalBeadCount    :', obj.project.totalBeadCount);
    if (obj.project.layers) console.log('  layers count      :', obj.project.layers.length, 'types:', [...new Set(obj.project.layers.map(l=>l.type))]);
    if (obj.project.settings) console.log('  settings keys     :', Object.keys(obj.project.settings));
    if (obj.project.colorCounts) console.log('  colorCounts len   :', Object.keys(obj.project.colorCounts).length);
    if (obj.project.paletteSelections) console.log('  paletteSelections :', Object.keys(obj.project.paletteSelections));
    if (obj.project.recentColors) console.log('  recentColors len  :', obj.project.recentColors.length);
  }
  if (obj.assets) {
    console.log('assets count          :', obj.assets.length);
    if (obj.assets[0]) console.log('asset[0] keys         :', Object.keys(obj.assets[0]), 'mimeType:', obj.assets[0].mimeType, 'data type:', typeof obj.assets[0].data, 'data len:', (obj.assets[0].data||'').length);
  }
})().catch(e => { console.error('ERR', e); process.exit(1); });
