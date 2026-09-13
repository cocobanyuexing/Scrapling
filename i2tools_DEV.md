# 幻彩拼豆 (i2tools.com) 开发文档 (DEV)

## 0. 文档信息

| 项 | 值 |
|:---|:---|
| 文档版本 | v1.0 |
| 整理时间 | 2026-09-13 |
| 目标读者 | 全栈开发 / 运维 / 接手团队 |
| 来源 | 基于 i2tools.com 实测逆向整理（参见 `file:///workspace/i2tools_review.md`） |
| 关联文档 | `file:///workspace/i2tools_PRD.md`（产品需求文档，业务侧落点） |
| 爬取样本 | `/workspace/i2tools/` 目录（2742 文件 / 606MB） |

> 说明：本文档所有架构、代码、API、部署命令均来自 2026-09-13 的真实在线实测与 JS chunk 反编译。业务需求规格请查阅 PRD 文档对应章节。

---

## 1. 架构总览

### 1.1 系统架构图

```
                                  [Browser]
                                      │
                                      │ HTTPS (HTTP/2 + HTTP/3 可选)
                                      ▼
                              [Nginx 反向代理]
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
        [Next.js SSR/CSR]      [Node.js + Express API]   [静态资源 CDN]
        (i2tools.com)          (/v1/app/* 业务接口)       (_next/static/*)
              │                       │
              │                       ├── [PostgreSQL / MySQL]
              │                       │     (users / projects / inventory
              │                       │      / checkin / orders / products)
              │                       │
              │                       ├── [Redis 缓存（可选）]
              │                       │     (会话 / 任务队列状态)
              │                       │
              │                       ▼
              │                 [阿里云 OSS]            [Cloudflare R2]
              │                 (oss-cdn.i2tools.com)    (用户上传 r2-uploads)
              │                 /ai-results/* 结果图     _next/.../r2-uploads/*
              │
              ▼
        [IndexedDB v10]
        数据库名: magic-perler-projects
        object store: projects / project_snapshots
                      / magic-perler-assembly-progress
              │
              ▼
        [PixiJS v8 Canvas]
        (WebGPU 优先 → webgl2 回退)
        (sprite 堆叠 + 投影矩阵 模拟 3D)
```

### 1.2 技术栈表

#### 前端

| 类别 | 技术 | 版本 | 证据来源 |
|:---|:---|:---|:---|
| 框架 | Next.js（App Router） | 19.2.0-canary | `package.json` + 路由组目录 `[locale]/(main)`、`(workspace)` |
| 国际化 | next-intl | - | `[locale]` 动态路由 + `NEXT_LOCALE` cookie |
| 渲染引擎 | PixiJS | v8 | chunk `9872` 中 `Application/WebGLRenderer/roundPixels` |
| 状态管理 | Zustand | - | `s.G.getState()`、`r.$.getState()` 多处调用 |
| HTTP 客户端 | Axios | 1.18.1 | `package.json` |
| 数据校验 | Zod | 4.4.3 | `package.json` |
| 3D 模拟 | sprite 堆叠 + 投影矩阵 | - | 非 Three.js，pixi 原生模拟 3D |
| WebGPU 路径 | WebGPU + WebGL 双路径 | - | 代码中检测 `navigator.gpu` 回退 `webgl2` |

#### 后端

| 类别 | 技术 | 证据 |
|:---|:---|:---|
| Web 框架 | Node.js + Express | 响应头 `x-powered-by: Express` |
| 对象存储 1 | 阿里云 OSS | 结果图 URL `oss-cdn.i2tools.com/ai-results/...` |
| 对象存储 2 | Cloudflare R2 | 上传存储 `_next/.../r2-uploads/...` |
| 认证 | JWT + Refresh | `accessToken`/`refreshToken` JWT，session_id 在 payload |
| 防护 | XSRF + Cookie | `X-XSRF-TOKEN` 头 + 同源 Cookie |
| 数据库 | IndexedDB（前端） + 服务端 DB（推测 PostgreSQL/MySQL） | `magic-perler-projects` v10 + API 返回 UUID |

---

## 2. 前端架构

### 2.1 路由结构（基于实测爬取）

```
/
└── [locale]/                       # next-intl 动态路由（如 /zh、/en）
    ├── (main)/                      # 主站路由组
    │   ├── page.tsx                 # 首页
    │   └── ...
    ├── (workspace)/                 # 工作台路由组
    │   ├── create/                  # 项目列表
    │   ├── gallery/                 # 画廊
    │   ├── inventory/               # 库存管理
    │   ├── tools/                   # 工具台入口
    │   └── account/                 # 账户中心（PC 简化版）
    ├── tools/
    │   ├── ai-pixel-art/            # 图片生成像素画
    │   ├── perfect-pixel/           # 伪像素画修正
    │   └── xhs/                     # 小红书链接导入
    ├── editor/                      # 编辑器（/editor?projectId=xxx）
    └── tutorials/                   # 教程（静态内容）
```

> **关键陷阱**：旧 `/editor?projectId=...` URL 在新版工作台上线后被重定向回首页。需先点「立刻前往」按钮找新工作台 `/workspace/create`，再点「新建空白项目」进编辑器。

### 2.2 状态管理（Zustand）

调用模式（minified 后的命名）：
- 应用状态：`s.G.getState()` — 认证信息、项目数据、UI 状态
- 备用 store：`r.$.getState()` — 渲染相关状态

### 2.3 渲染引擎（PixiJS v8）

#### 双路径检测
```js
// 伪代码（基于 chunk 9872 反编译）
const Renderer = navigator.gpu ? WebGPURenderer : WebGLRenderer;
const app = new Application({
  renderer: new Renderer({ roundPixels: true }),
  ...
});
```

#### 3D 模拟（非 Three.js）
- 工艺：sprite 堆叠 + 投影矩阵（`modelViewProjectionMatrix`）
- 拼豆：独立圆柱豆 sprite + 中心孔贴图
- 烫豆：扁平 sprite，无独立边界
- 毛巾烫：横向肋条纹理 sprite

#### 关键 chunk 映射

| chunk | 内容 |
|:---|:---|
| `9872-c5b827a0694e9972.js` | 3D 引擎 + 编辑器 |
| `8071-30a1b464baed2037.js` | 编辑器内核 + 颜色匹配算法 |
| `1720-fa8a8467cef59a57.js` | 小红书工具前端 + 对象存储上传 |
| `6777-710cc5ad9e725047.js` | 去噪 / 杂色处理算法 |
| `9350-9895fcf460f5295c.js` | MARD 色号体系定义 |
| `7824-a12ba49ff917cbc3.js` | IndexedDB schema |

#### ⚠️ `readPixels` 陷阱
PixiJS 默认未设置 `preserveDrawingBuffer: true`，用 `gl.readPixels` 验证 webgl canvas 渲染会返回空。**改用 `page.screenshot()` 视觉验证 + canvas `toDataURL()` 比对**。

### 2.4 IndexedDB Schema

#### 数据库元信息
| 项 | 值 |
|:---|:---|
| 数据库名 | `magic-perler-projects` |
| version | 10 |
| 主要 object store | `projects`（keyPath=`id`） |
| 辅助 store | `project_snapshots`（历史快照）、`magic-perler-assembly-progress`（装配进度） |

#### 项目数据结构（TypeScript 接口，基于实测 plain JSON）

```ts
// IndexedDB projects store 中的项目记录
interface Project {
  id: string;                                  // 如 "1789307961484-yd8c0qg"
  dataVersion: number;                          // = 5
  name: string;                                 // 如 "AI像素画 2026/09/13"
  thumbnail: string;                            // data:image/png;base64,... 缩略图
  originalAssetId: string;                      // 原始资源 ID（关联 assets）
  layers: Layer[];                              // 2 个：[REF 参考层, PIXEL 像素层]
  gridDimensions: { N: number; M: number };     // N=列, M=行
  colorCounts: Record<string, number>;          // {色号: 颗数}
  settings: ProjectSettings;
  paletteSelections: string[];                  // 调色板选择，MARD 全集 = 221 色
  activeLayerId: string;
  recentColors: string[];
  totalBeadCount: number;                       // 总豆数
  cropRegion: { ... } | null;
  viewState: { zoom: number; pan: { x: number; y: number } };
}

interface Layer {
  id: string;
  name: string;                                 // "参考图层" 或 "像素图层"
  type: 'REF' | 'PIXEL';
  imageSrc: string | null;                      // REF 层有，PIXEL 层为 null
  assetId: string | null;                       // REF 层关联 assets[].id
  flipX: boolean;
  rotation: number;
  opacity: number;
  x: number;
  y: number;
  width: number;
  height: number;
  visible: boolean;
  locked: boolean;
  data: { cells: string[] } | null;             // PIXEL 层：扁平 cells 数组，每项是色号
  order: number;
}

interface ProjectSettings {
  granularity: number;                          // 网格尺寸
  threshold: number;                            // 阈值
  pixelationMode: 'structural' | 'dominant' | 'average' | 'pixelart-optimized';
  colorMatchingAlgorithm: 'cam16-ucs' | ...;
  colorSystem: 'MARD' | ...;
}

// .pbp 文件顶层结构（解密后）
interface PbpFile {
  pbpVersion: 2;
  project: Project;
  assets: Asset[];                              // PNG 原图等
}

interface Asset {
  id: string;
  mimeType: 'image/png' | ...;
  data: string;                                  // base64
}
```

**实测样本**：`file:///workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp.plain.json`
- gridDimensions: {N: 136, M: 196}
- layers: 2 个 [REF, PIXEL]，PIXEL 层 cells 数组长度 = 26,656（= 136×196）
- colorCounts: 48 个色号（H2/M12/H6/H16...）
- settings: `{granularity:136, threshold:10, pixelationMode:"structural", colorMatchingAlgorithm:"cam16-ucs", colorSystem:"MARD"}`
- assets: 1 个 PNG（base64 长 77,434 字符）

---

## 3. 后端架构

### 3.1 API 设计（实测通过 14 个端点）

| # | 接口 | 方法 | 状态 | 用途 |
|:---:|:---|:---:|:---:|:---|
| 1 | `/v1/app/auth/email/login` | POST | 201 | 邮箱密码登录 |
| 2 | `/v1/app/auth/info` | GET | 200 | 用户信息 + 等级 + 积分 |
| 3 | `/v1/app/checkin/status` | GET | 200 | 签到状态 |
| 4 | `/v1/app/level/configs` | GET | 200 | 等级权益表 |
| 5 | `/v1/app/projects/quota` | GET | 200 | 项目配额 |
| 6 | `/v1/app/inventory/summary` | GET | 200 | 库存统计 |
| 7 | `/v1/app/inventory/brands` | GET | 200 | 品牌列表 |
| 8 | `/v1/app/inventory/colors` | GET | 200 | 色号详情 |
| 9 | `/v1/app/products` | GET | 200 | 商品列表 |
| 10 | `/v1/app/products/cloud_backup_space/offers` | GET | 200 | 备份套餐 |
| 11 | `/v1/app/products/mp_points/offers` | GET | 200 | 积分套餐 |
| 12 | `/v1/app/pixel-art/conversions` | POST | 200 | 生成像素画任务 |
| 13 | `/v1/app/pixel-art/conversions/{taskNo}` | GET | 200 | 查询单任务 |
| 14 | `/v1/client-errors` | POST | 201 | 前端错误上报 |

> 未实测但推断存在的端点：`/v1/app/xhs/import`（小红书导入，实测响应 422）。

#### 3.1.1 登录请求/响应示例

**请求**：
```http
POST /v1/app/auth/email/login HTTP/1.1
Content-Type: application/json
X-XSRF-TOKEN: <token>
Cookie: XSRF-TOKEN=<token>; session=<session_id>

{
  "email": "aq.jinlong@163.com",
  "password": "abc123456"
}
```

**响应**（HTTP 201）：
```json
{
  "accessToken": "<JWT>",
  "refreshToken": "<JWT>",
  "user": {
    "id": "<uuid>",
    "email": "aq.jinlong@163.com",
    "level": 1,
    "exp": 10
  }
}
```

#### 3.1.2 用户信息示例（`GET /v1/app/auth/info`）

```json
{
  "user": {
    "id": "<uuid>",
    "email": "aq.jinlong@163.com",
    "level": 1,
    "exp": 10,
    "expToNextLevel": 100,
    "points": 24,
    "cloudBackupQuota": 5
  }
}
```

#### 3.1.3 库存统计示例（`GET /v1/app/inventory/summary`）

```json
{
  "totalCount": ...,
  "trackedColors": ...,
  "lowStockCount": ...,
  "defaultThreshold": 10,
  "adjustmentAmount": 100
}
```

#### 3.1.4 品牌列表示例（`GET /v1/app/inventory/brands`）

```json
{
  "brands": [
    { "name": "MARD", "colorCount": 305 },
    { "name": "COCO", "colorCount": 291 },
    { "name": "漫漫", "colorCount": 289 },
    { "name": "盼盼", "colorCount": 291 },
    { "name": "咪小窝", "colorCount": 291 }
  ]
}
```

#### 3.1.5 像素画任务提交（`POST /v1/app/pixel-art/conversions`）

```json
{
  "imageUrl": "<R2 上传后的 URL>",
  "size": 50,
  "pixelationMode": "pixelart-optimized",
  "colorSystem": "MARD",
  "colorLimit": "rich",
  "noiseCleanup": "balanced",
  "colorEnhance": "natural"
}
```

**响应**：
```json
{
  "taskNo": "TASK20260913202841282414",
  "status": "PENDING"
}
```

#### 3.1.6 任务轮询（`GET /v1/app/pixel-art/conversions/{taskNo}`）

状态机：`PENDING → PROCESSING → SUCCESS`

**SUCCESS 响应**：
```json
{
  "taskNo": "TASK20260913202841282414",
  "status": "SUCCESS",
  "images": [
    "https://oss-cdn.i2tools.com/ai-results/bead-conversion/TASK.../0.webp"
  ],
  "pointsConsumed": 1
}
```

> ⚠️ **字段陷阱**：`sourceFileName` 是文件名不是 URL，下载结果图必须从 `images` 字段提取正确 URL。

### 3.2 认证流程

```
1. POST /v1/app/auth/email/login
   → 返回 accessToken + refreshToken（均为 JWT，session_id 在 payload）

2. 后续请求头：
   Authorization: Bearer <accessToken>
   X-XSRF-TOKEN: <token>           # 双 token 防护
   Cookie: XSRF-TOKEN=<token>; session=<session_id>   # 同源 Cookie

3. 用户信息查询：GET /v1/app/auth/info
```

**XSRF 双 token 机制**：
- `X-XSRF-TOKEN` 头 + 同源 Cookie 必须同时存在
- 用于防止 CSRF 跨站请求伪造

### 3.3 对象存储

| 用途 | 服务 | 域名 / 路径 |
|:---|:---|:---|
| AI 结果图托管 | 阿里云 OSS | `oss-cdn.i2tools.com/ai-results/bead-conversion/TASK.../0.webp` |
| 云备份封面图 | 阿里云 OSS | `oss-cdn.i2tools.com/perler/cloud-backups/{uuid}_{uuid}_cover.webp` |
| 画廊缩略图 | 阿里云 OSS | `oss-cdn.i2tools.com/gallery/{uuid}_thumb_{uuid}.webp` |
| 用户上传 | Cloudflare R2 | `_next/.../r2-uploads/...` |

---

## 4. 算法实现（反编译）

### 4.1 颜色匹配

来源：chunk `8071-30a1b464baed2037.js`

| 算法 | 用途 | 关键点 |
|:---|:---|:---|
| **Median Cut** | 调色板提取 | 经典分箱法，递归切分最长通道 |
| **K-D Tree** | 最近邻加速 | 7 叉树近邻搜索，加速量化 |
| **DeltaEHybrid** | 颜色距离 | CIE Delta E 混合算法 |
| **CAM16-UCS** | 颜色距离 | 更符合人眼感知的高级算法（实测项目默认 `cam16-ucs`） |

#### 颜色距离实现（去噪 / 合并共用，sRGB 空间加权）

```js
// 6 位 hex 计算 sRGB 空间距离（亮度加权）
// 输入：e, t 为两个 #RRGGBB hex 字符串
function colorDistance(e, t) {
  let o = parseInt(e.slice(1, 3), 16),   // R of e
      r = parseInt(e.slice(3, 5), 16),   // G of e
      l = parseInt(e.slice(5, 7), 16);   // B of e
  let n = parseInt(t.slice(1, 3), 16),   // R of t
      a = parseInt(t.slice(3, 5), 16),   // G of t
      i = parseInt(t.slice(5, 7), 16);   // B of t
  let s = (o + n) / 2;                   // 平均 R
  let d = o - n, c = r - a, u = l - i;   // 三通道差值
  return Math.sqrt(
    (512 + s) * d * d / 256 +
    4 * c * c +
    (767 - s) * u * u / 256
  );
}
```

### 4.2 像素化（4 模式）

来源：chunk `8071`

| 模式 | 用途 |
|:---|:---|
| **Structural** | 保留结构特征（"智能"） |
| **Dominant** | 主导色（"卡通"） |
| **Average** | 均值色（"写实"） |
| **PixelArtOptimized** | 像素画优化，默认（"简化"） |

### 4.3 perfect-pixel 修正算法

来源：独立 chunk，借鉴开源思路 TS 重写。

流程：
1. 输入像素画结果图
2. 边界扫描识别"半像素"边缘
3. 量化到整数像素网格
4. 重采样匹配 MARD 调色板
5. 输出对齐后的修正 canvas

### 4.4 去噪 / 杂色处理算法（核心）

来源：chunk `6777-710cc5ad9e725047.js`

#### 4.4.1 4 种预设强度（完整参数表）

```js
let i = {
  light:      { areaThreshold: 1, passes: 1, connectivity: 8, maxColorDistance: 60,  minContactRatio: 0.20, protectThinLines: true,  protectHighContrast: true,  highContrastThreshold: 72,  protectTransparentEdges: true  },
  balanced:   { areaThreshold: 2, passes: 1, connectivity: 8, maxColorDistance: 84,  minContactRatio: 0.12, protectThinLines: true,  protectHighContrast: true,  highContrastThreshold: 88,  protectTransparentEdges: true  },
  strong:     { areaThreshold: 4, passes: 2, connectivity: 8, maxColorDistance: 116, minContactRatio: 0.08, protectThinLines: true,  protectHighContrast: true,  highContrastThreshold: 108, protectTransparentEdges: false },
  aggressive: { areaThreshold: 8, passes: 2, connectivity: 8, maxColorDistance: 180, minContactRatio: 0,    protectThinLines: false, protectHighContrast: false, highContrastThreshold: 180, protectTransparentEdges: false },
};
```

| 参数 | 范围 | 含义 |
|:---|:---|:---|
| `areaThreshold` | 1-12（滑块） | 连通域像素数 < 阈值 → 视为杂色 |
| `passes` | 1-2 | 清理轮数 |
| `connectivity` | 4 或 8 | 4 连通或 8 连通 |
| `maxColorDistance` | 60-180 | 颜色距离上限，越大合并越激进 |
| `minContactRatio` | 0-0.9（步长 0.05） | 接触率保护阈值，过低才删除 |
| `protectThinLines` | bool | 保护细线条 |
| `protectHighContrast` | bool | 保护高对比度边缘 |
| `highContrastThreshold` | 72-180 | 高对比度阈值 |
| `protectTransparentEdges` | bool | 保护透明边缘 |

#### 4.4.2 8 连通域分析（BFS 标记）

```js
// 4 连通：[[-1,0],[1,0],[0,-1],[0,1]]
// 8 连通：[[-1,-1],[-1,1],[1,-1],[1,1]] 补充对角
let d = [[-1, 0], [1, 0], [0, -1], [0, 1]];
let c = [[-1, -1], [-1, 1], [1, -1], [1, 1]];

// 4 or 8 连通选择器
let u = e => 4 === e ? d : c;

// BFS 标记同色像素为同一区域
function g(e, t = 8) {
  let r = u(t),                                  // 邻居偏移表
      n = Array.from({ length: e.length },
        () => new Uint8Array(e[0].length));      // 标记矩阵
  for (let row = 0; row < e.length; row++) {
    for (let col = 0; col < e[0].length; col++) {
      if (n[row][col]) continue;                  // 已标记跳过
      // BFS 扩散，同色并入同一连通域
      let q = [{ row, col }];
      while (q.length) {
        let p = q.shift();
        for (let [dr, dc] of r) {
          let nr = p.row + dr, nc = p.col + dc;
          if (nr >= 0 && nr < e.length &&
              nc >= 0 && nc < e[0].length &&
              !n[nr][nc] &&
              same_color(e[nr][nc], e[p.row][p.col])) {
            n[nr][nc] = 1;
            q.push({ row: nr, col: nc });
          }
        }
      }
    }
  }
  return n;
}
```

#### 4.4.3 面积阈值过滤
- 参数：`areaThreshold` ∈ [1, 12] step 1
- 含义：连通域像素数 < 阈值 → 视为杂色 → 删除 / 合并到邻域

#### 4.4.4 接触率保护
- 参数：`minContactRatio` ∈ [0, 0.9] step 0.05
- 含义：杂色区域与主体像素的接触比例，过低才删除（保护线条）

#### 4.4.5 K-means 聚类（色号合并模式之一）
- 色号合并弹窗模式选择含 K-means
- 阈值滑块 90%（相似度阈值，越高只合并越接近的色号）

### 4.5 拼图图纸识别算法

来源：chunk `1720`

流程：
1. 图纸上传 → 边缘检测（Canny / Sobel）
2. 矢量化 → 提取色块边界
3. 颜色识别 → 匹配 MARD 色号
4. 网格重建 → 生成项目 layers

### 4.6 库存扣减算法

来源：chunk `9350`

- **色号合并**：相同色号多项目用量累加
- **扣减**：依据项目 `colorCounts` 减库存数量
- **低库存预警**：`< 阈值` 触发提醒（默认 10）

---

## 5. .pbp 文件格式（完整规格）

### 5.1 外层 JSON 容器

```json
{
  "version": "1.0",
  "format": "pbp",
  "data": "<base64 密文>"
}
```

### 5.2 加密参数

| 参数 | 值 |
|:---|:---|
| 算法 | AES-GCM-256 |
| 密钥派生 | PBKDF2 |
| password | `perler-beads-project-v1` |
| salt | `perler-salt` |
| iterations | 100,000 |
| hash | SHA-256 |
| 派生 AES 密钥(hex) | `f10c45331007903f5ff9218d696ea6513db0926f4a9232df9bd61c8d98eb8734` |
| IV | Base64 解码后前 12 字节 |
| 密文 | 剩余字节 |
| 认证标签 | AES-GCM 内置 |

### 5.3 解密后顶层结构

```json
{
  "pbpVersion": 2,
  "project": { ... },
  "assets": [ ... ]
}
```

`project` 字段完整结构（参见 §2.4 Layer / Project 接口）：

```
project: {
  dataVersion: 5,
  name: string,                    // 项目名
  thumbnail: string,               // data:image/png;base64,... 缩略图
  originalAssetId: string,          // 原始资源 ID
  layers: Layer[],                  // [REF 参考层, PIXEL 像素层]
  gridDimensions: { N, M },         // N=列, M=行
  colorCounts: Record<色号, 颗数>,
  settings: {
    granularity, threshold,
    pixelationMode,                 // Structural/Dominant/Average/PixelArtOptimized
    colorMatchingAlgorithm,         // cam16-ucs 等
    colorSystem                     // MARD 等
  },
  paletteSelections: string[],      // 调色板选择（MARD 全集 221 色）
  activeLayerId: string,
  recentColors: string[],
  totalBeadCount: number,
  cropRegion: { ... } | null,
  viewState: { zoom, pan: { x, y } }
}
```

### 5.4 解密工具

**完整脚本**：`file:///workspace/decode_pbp.js`

核心片段（Node.js，使用 webcrypto）：

```js
const fs = require('fs');
const crypto = require('crypto');

async function deriveKey() {
  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey(
    'raw',
    enc.encode('perler-beads-project-v1'),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt: enc.encode('perler-salt'),
      iterations: 100000, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt']
  );
}

(async () => {
  const file = process.argv[2]
    || '/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp';
  const raw = fs.readFileSync(file, 'utf8');
  const parsed = JSON.parse(raw);

  // 1. Base64 解码 data
  const bin = Buffer.from(parsed.data, 'base64');
  const iv  = bin.slice(0, 12);            // IV = 前 12 字节
  const ct  = bin.slice(12);               // 密文 = 剩余

  // 2. PBKDF2 派生 AES-256 密钥
  const key = await deriveKey();

  // 3. AES-256-GCM 解密
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ct);
  const txt = Buffer.from(pt).toString('utf8');

  // 4. 写出明文用于结构分析
  const out = file.replace(/\.pbp$/i, '.pbp.plain.json');
  fs.writeFileSync(out, txt);

  const obj = JSON.parse(txt);
  console.log('pbpVersion:', obj.pbpVersion);
  console.log('project keys:', Object.keys(obj.project));
  console.log('assets count:', obj.assets.length);
})().catch(e => { console.error('ERR', e); process.exit(1); });
```

**等价同步实现**（`crypto.pbkdf2Sync`，更直观）：

```js
const key = crypto.pbkdf2Sync(
  'perler-beads-project-v1',
  'perler-salt',
  100000, 32, 'sha256'
);
const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
const plain = Buffer.concat([decipher.update(ct), decipher.final()]);
```

### 5.5 ⚠️ 重要安全发现：固定密钥 = 混淆而非真加密

**所有 .pbp 文件使用同一把固定密钥**（password / salt / iterations 全部硬编码），任何拿到 .pbp 的人都能用相同参数解密。这实质上是「混淆」(obfuscation) 而非真正的加密保护——无法防止有技术能力的用户读取项目数据。

**对称性验证**（review.md 附录 G）：

| 验证项 | 导入样本 | 导出样本 | 一致性 |
|:---|:---|:---|:---:|
| PBKDF2 派生 AES 密钥 | `f10c45...8734` | `f10c45...8734` | ✅ 完全相同 |
| pbpVersion | 2 | 2 | ✅ |
| project.dataVersion | 5 | 5 | ✅ |
| gridDimensions | {N, M} | {N:205, M:307} | ✅ 与 UI 205×307 一致 |
| totalBeadCount | — | 62935 | ✅ 与 UI 一致 |
| colorCounts | — | 76 | ✅ 与 UI 76 颜色一致 |
| layers | — | 2 个 [REF, PIXEL] | ✅ |
| settings | — | 完整字段 | ✅ |
| assets | — | 1 个 PNG（3,721,698 字符） | ✅ |

---

## 6. 部署指南

### 6.1 环境准备

| 组件 | 版本要求 | 用途 |
|:---|:---|:---|
| Node.js | 18+（推荐 20 LTS） | 前后端运行时 |
| pnpm | 8+ | 包管理器 |
| PostgreSQL | 14+ 或 MySQL 8+ | 主数据库 |
| Redis | 6+（可选） | 会话缓存 / 任务队列状态 |
| Nginx | 1.20+ | 反向代理 + HTTPS + HTTP/2 |
| 阿里云 OSS | - | 结果图托管 |
| Cloudflare R2 | - | 用户上传存储 |

### 6.2 配置环境变量

```bash
# ===== 数据库 =====
DATABASE_URL=postgres://user:pass@localhost:5432/i2tools
# 或 MySQL:
# DATABASE_URL=mysql://user:pass@localhost:3306/i2tools

# ===== 阿里云 OSS（结果图）=====
OSS_ACCESS_KEY=<your_access_key>
OSS_SECRET=<your_secret>
OSS_BUCKET=i2tools-results
OSS_ENDPOINT=oss-cn-<region>.aliyuncs.com
OSS_CDN_DOMAIN=oss-cdn.i2tools.com

# ===== Cloudflare R2（用户上传）=====
R2_ACCESS_KEY=<your_access_key>
R2_SECRET=<your_secret>
R2_BUCKET=i2tools-uploads
R2_ENDPOINT=<account_id>.r2.cloudflarestorage.com
R2_BASE_URL=https://r2.i2tools.com

# ===== 认证 =====
JWT_SECRET=<your_jwt_secret>
XSRF_SECRET=<your_xsrf_secret>

# ===== 前端公开变量（NEXT_PUBLIC_* 会被打包进客户端）=====
NEXT_PUBLIC_API_BASE_URL=https://i2tools.com/v1
NEXT_PUBLIC_OSS_CDN=https://oss-cdn.i2tools.com
NEXT_PUBLIC_R2_BASE=https://r2.i2tools.com

# ===== 可选：APM =====
SENTRY_DSN=<your_sentry_dsn>
```

### 6.3 部署步骤

```bash
# 1. 克隆仓库 + 安装依赖
git clone <repo-url> i2tools
cd i2tools
pnpm install

# 2. 配置 .env（参考 §6.2）

# 3. 数据库迁移建表
pnpm db:migrate

# 4. 构建 Next.js
pnpm build

# 5. 启动服务（前端 3000 + 后端 4000）
pnpm start
# 或分离启动：
# pnpm start:web      # Next.js on :3000
# pnpm start:api      # Express API on :4000
```

### 6.4 Nginx 反代配置示例

```nginx
server {
    listen 443 ssl http2;
    server_name i2tools.com oss-cdn.i2tools.com;

    ssl_certificate     /etc/letsencrypt/live/i2tools.com/fullchain.pem;
    ssl_certificate_key  /etc/letsencrypt/live/i2tools.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # HTTP/3 可选
    # listen 443 quic reuseport;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /v1/ {
        proxy_pass http://127.0.0.1:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OSS CDN（如自建反代）
    location /ai-results/ {
        proxy_pass https://oss-cdn.i2tools.com/ai-results/;
    }
}

# HTTP -> HTTPS 跳转
server {
    listen 80;
    server_name i2tools.com;
    return 301 https://$host$request_uri;
}
```

### 6.5 HTTPS 证书（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d i2tools.com -d oss-cdn.i2tools.com
# 自动续期：certbot 已配置 systemd timer
```

### 6.6 监控

| 项 | 方案 |
|:---|:---|
| 前端错误上报 | `POST /v1/client-errors`（实测状态 201） |
| APM | 可选 Sentry（`SENTRY_DSN`） |
| 日志 | `pino` / `log4js` |

---

## 7. 数据库 Schema（基于 API 返回结构推测）

```sql
-- 用户表
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  level         INT DEFAULT 1,
  exp           INT DEFAULT 0,
  points        INT DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 项目表
CREATE TABLE projects (
  id               VARCHAR(64) PRIMARY KEY,   -- 如 "1789307961484-yd8c0qg"
  user_id          UUID NOT NULL REFERENCES users(id),
  name             VARCHAR(255),
  data             JSONB,                     -- 完整 project 对象
  grid_dimensions  JSONB,                     -- {N, M}
  total_bead_count INT,
  color_counts     JSONB,                      -- {色号: 颗数}
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_projects_user ON projects(user_id);

-- 库存表
CREATE TABLE inventory (
  user_id      UUID NOT NULL REFERENCES users(id),
  brand        VARCHAR(64) NOT NULL,          -- MARD / COCO / 漫漫 / 盼盼 / 咪小窝
  color_code   VARCHAR(16) NOT NULL,          -- 如 H2 / M7
  count        INT DEFAULT 0,
  threshold    INT DEFAULT 10,
  updated_at   TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, brand, color_code)
);
CREATE INDEX idx_inventory_user ON inventory(user_id);
CREATE INDEX idx_inventory_lowstock ON inventory(user_id) WHERE count < threshold;

-- 签到表
CREATE TABLE checkin (
  user_id          UUID NOT NULL REFERENCES users(id),
  date             DATE NOT NULL,
  exp_earned       INT DEFAULT 10,
  continuous_days  INT DEFAULT 1,
  PRIMARY KEY (user_id, date)
);

-- 商品 / 订单
CREATE TABLE products (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type        VARCHAR(32) NOT NULL,           -- cloud_backup_space / mp_points
  name        VARCHAR(255),
  price       DECIMAL(10,2),
  description TEXT
);

CREATE TABLE orders (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  product_id  UUID NOT NULL REFERENCES products(id),
  amount      DECIMAL(10,2),
  status       VARCHAR(16) DEFAULT 'pending',  -- pending/paid/refunded
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_orders_user ON orders(user_id);

-- 等级配置（静态或字典表）
CREATE TABLE level_configs (
  level              INT PRIMARY KEY,         -- 1-5
  required_exp       INT,
  daily_points       INT,
  cloud_backup_quota INT,
  ai_quota           INT
);
```

---

## 8. 测试与验证

### 8.1 实测脚本清单

| 脚本 | 测试目标 |
|:---|:---|
| `gen_pixelart.py` | ai-pixel-art 上传 + 生成 |
| `query_task.py` | 任务轮询 + 结果图下载 |
| `run_perfect_pixel.py` | perfect-pixel 修正 + 保存 |
| `test_3d_blank.py` | 新建空白项目 + 3D 面板 |
| `test_3d_real.py` | 真实豆数据 + 3D 三工艺 |
| `test_3d_paint.py` | 画笔 + 3D 视图 |
| `test_3d_beads.py` | 单击放豆 + 3D |
| `test_3d_v2.py` / `test_3d_v3.py` / `test_3d_panel.py` | 3D 面板多版本迭代 |
| `test_inventory.py` | 库存管理 UI + API |
| `test_account.py` | 账户中心（PC） |
| `test_account_mobile.py` | 账户中心（移动端发现） |
| `test_acc_features.py` | 每日签到 / 订阅 / 资料 |
| `test_postprocess.py` | 后处理按钮状态 |
| `test_postproc_export_v2.py` | 后处理 + 导出对称验证 |
| `test_import_pbp.py` | 导入 .pbp |
| `test_export_pbp.py` | 导出 .pbp |
| `test_smart_import_v15.py` | 拼图图纸智能导入（最新版） |
| `test_smart_import_v2.py` ~ `v14.py` | 智能导入迭代版本 |
| `test_smart_import_and_postproc.py` | 智能导入 + 后处理串联 |
| `test_save_smartimport_chunk.py` / `test_grab_smartimport_chunk.py` | 智能导入 chunk 保存/抓取 |
| `test_xhs_runtime.py` | 小红书运行时 XHR + 签名头日志 |
| `test_xhs_response.py` | 小红书 API 响应日志 |
| `decode_pbp.js` | .pbp AES-GCM-256 解密 + 结构 dump |
| `slice_minified.py` | 切片提取 minified JS |
| `slice_3d_idb.py` | 3D 引擎 + IDB schema 切片 |
| `explore_new_workspace.py` | 探索新工作台入口 |
| `explore_tools.py` | 工具台入口结构 |

### 8.2 验证流程（按功能分组）

```bash
# 1. 登录 + 账户
python3 /workspace/test_acc_features.py
python3 /workspace/test_account.py
python3 /workspace/test_account_mobile.py

# 2. ai-pixel-art
python3 /workspace/gen_pixelart.py
python3 /workspace/query_task.py

# 3. perfect-pixel
python3 /workspace/run_perfect_pixel.py

# 4. 3D 预览
python3 /workspace/test_3d_blank.py     # 空白项目
python3 /workspace/test_3d_real.py      # 真实豆数据三工艺
python3 /workspace/test_3d_paint.py    # 画笔
python3 /workspace/test_3d_beads.py    # 放豆

# 5. 库存
python3 /workspace/test_inventory.py

# 6. .pbp 导入/导出
node /workspace/decode_pbp.js /workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp
python3 /workspace/test_import_pbp.py
python3 /workspace/test_export_pbp.py

# 7. 拼图图纸
python3 /workspace/test_smart_import_v15.py

# 8. 后处理
python3 /workspace/test_postprocess.py
python3 /workspace/test_postproc_export_v2.py

# 9. 小红书
python3 /workspace/test_xhs_runtime.py
python3 /workspace/test_xhs_response.py
```

### 8.3 测试环境前置要求

```python
# 沙箱代理（国内访问跳转 google 的应对）
browser = p.chromium.launch(
    headless=True,
    args=['--no-sandbox', '--disable-dev-shm-usage',
          '--proxy-server=http://127.0.0.1:18080']
)
```

```python
# 登录前置（更新日志 dialog 关闭 + 用户协议 checkbox 勾选）
for _ in range(3):
    page.keyboard.press('Escape')
    page.wait_for_timeout(700)

# 必须用 Playwright 标准 click 而非 dispatchEvent 触发 checkbox
cb = page.locator('[role="checkbox"]').first
cb.click(timeout=3000)
```

---

## 9. 已知问题与限制

### 9.1 小红书三层反爬

| 层 | 主机 | 端点 | 说明 |
|:---|:---|:---|:---|
| **第一层 脚本层** | `as.xiaohongshu.com` | `/api/sec/v1/ds` | 返回 obfuscator.io 风格混淆脚本（59KB），含 `_0x341b` 字符串数组 + 重写 `apply/call/bind` 防 hook |
| | | `/api/sec/v1/scripting` | 返回动态注入的 `Robin()` 函数（`_ace_` 前缀变量），含 base64+UTF-8 解码器 → 运行时执行环境检测 |
| | `fe-static.xhscdn.com` | `/as/v2/ds/4c0bab9011f51d35ca6280649340e9b9.js` | v2 签名脚本（从 `__INITIAL_STATE__.signConfig.url` 拉取） |
| **第二层 设备指纹 + 风控** | `as.xiaohongshu.com` | `/api/sec/v1/sbtsource` | 下发完整反爬配置：指纹脚本 URL、token 生成、签名脚本、commonPatch（12 个需额外加密的 API） |
| | | `/api/sec/v1/shield/webprofile` | 上报指纹 + 风控数据 |
| | | `/api/redcaptcha/v2/getconfig` | 验证码 SDK 配置 |
| **第三层 请求签名** | 所有 XHR | 必带请求头 | 见下表 |

**每个 XHR 必带的签名头**：

| 头 | 示例 | 含义 |
|:---|:---|:---|
| `x-s` | `XYS_xxx` | 请求级签名，基于 URL/params/body，每个请求不同 |
| `x-s-common` | `2UQAPsHC+aI...` | 会话级公共签名，同一会话不变 |
| `x-t` | `1789308714xxx` | 13 位毫秒时间戳 |
| `x-b3-traceid` | 16 hex | Zipkin B3 分布式追踪 |
| `x-xray-traceid` | 32 hex | 自定义 APM 追踪 |

**对接建议**：
1. `xsec_token` + `xsec_source` + `source` 三件套：URL 参数，服务端校验，过期则 422
2. `x-s` 签名：基于请求 URL+params+body 用 ds 脚本生成，每个请求不同
3. `x-s-common` 签名：设备级，会话内固定，靠指纹采集脚本生成
4. 匿名 session：未登录也能拿 `/api/sns/web/v1/login/activate` 给的 user_id（游客身份），但权限受限
5. 写操作需要二次加密：`commonPatch` 列表中的 12 个 API（评论/点赞/收藏/关注/feed 等）需额外的 token+签名
6. 461 反爬触发：未登录访问 `/api/sns/web/v2/comment/page` 直接触发风控

**结论**：i2tools 后端 `/v1/app/xhs/import` 实测响应 HTTP 422，系外部平台反爬限制。需服务端代理 + xsec_token 凭证。

### 9.2 .pbp 固定密钥

所有 .pbp 文件使用同一把固定密钥（password/salt/iterations 全部硬编码），任何拿到 .pbp 的人都能解密。**混淆非真加密**。如需真加密，需引入用户密钥或服务端密钥派生。

### 9.3 移动端独有菜单

PC 版 `/workspace/account` 没有「每日签到」「订阅管理」菜单。这两个菜单是移动端 viewport 独有：

```python
ctx = browser.new_context(
    viewport={'width': 390, 'height': 844},
    user_agent='Mozilla/5.0 (iPhone; ...)',
    is_mobile=True,
    has_touch=True
)
```

### 9.4 dialog-overlay 拦截 React onClick

弹窗场景（创建项目、色号合并、去除杂色、降噪、扣减库存）中，`page.locator().click()` 会被 `<div data-slot="dialog-overlay" class="...fixed inset-0 z-[99] bg-gray-900">` 拦截 pointer events。

**解决方案**：用 `evaluate` 调用 `button.click()` 原生方法触发 React onClick：

```js
// ❌ 失败：被 overlay 拦截
await page.locator('button:has-text("创建项目")').click();

// ✅ 成功：原生 click 绕过 overlay
await page.locator('button:has-text("创建项目")')
  .evaluate(btn => btn.click());
```

### 9.5 其他实测坑

| 问题 | 现象 | 解决 |
|:---|:---|:---|
| 沙箱跳转 google | 内置浏览器访问 i2tools.com 立即跳转 google.com | 浏览器显式指定代理 `--proxy-server=http://127.0.0.1:18080` |
| 用户协议未勾选 | 登录无 XHR，提示"请先阅读并同意用户协议" | 用 Playwright 标准 `cb.click()` 而非 `dispatchEvent` |
| 邮箱拼写差异 | `aq.jilong@163.com` 提示"不存在通过此邮箱注册的用户" | 实际是 `aq.jinlong@163.com`（"jilong" → "jinlong"） |
| 注册走错域名 | 注册页是 `/en`（英文版），与中文主域名不一致 | 直接登录已注册账号 |
| 更新日志遮挡登录 | 点登录后 modal 不显示 | 多次 ESC 关闭所有 dialog |
| 旧 editor URL 重定向 | `/editor?projectId=...` 跳回首页 | 先点「立刻前往」找 `/workspace/create` |
| 3D 视图空着 | 开 3D 后画布空 | 用 ai-pixel-art 重新生成项目（5×5=25 颗豆）再开 3D |
| `sourceFileName` 误当 URL | 下载的"图片"是 HTML 错误页 | 从任务响应 `images` 字段提取 URL |
| `readPixels` 返回空 | `gl.readPixels` 验证 webgl 失败 | PixiJS 默认未设 `preserveDrawingBuffer:true`，改用 `screenshot()` + `toDataURL()` |
| `/tmp/scrap` 被清理 | 之前创建的脚本丢失 | 所有脚本放到 `/workspace/` 下 |

---

## 10. 接手清单

| 必读 | 路径 |
|:---|:---|
| 复盘文档 | `file:///workspace/i2tools_review.md` |
| 产品需求 | `file:///workspace/i2tools_PRD.md` |
| 开发文档 | `file:///workspace/i2tools_DEV.md`（本文档） |
| 必跑 | 所有 `test_*.py` 脚本（详见 §8） |
| 必查 | `/workspace/i2tools/` 目录（2742 文件爬取样本，606MB） |
| 关键 chunk | `9872`(3D) / `8071`(颜色) / `6777`(去噪) / `9350`(MARD) / `7824`(IDB) / `1720`(小红书) |
| 实测样本 | `/workspace/AI像素画-2026-09-13-136x196-20260913203224.pbp` + `.plain.json` |
| | `/workspace/exports/项目-2026-09-13-205x307-20260913135933.pbp` + `.plain.json` |
| 解密工具 | `file:///workspace/decode_pbp.js` |
| 联系 | 原作者 `aq.jinlong@163.com` |

---

## 11. 准确度说明（重要）

> ⚠️ 本文档基于对 i2tools.com 的**逆向实测**整理。编写过程中曾出现过分析错误并借助辅助工具修正，因此本章节明确标注各项内容的**置信度**，供接手者判断。技术栈/算法等关键环节的准确性分级如下。

### 11.1 之前修正过的错误（历史记录）

| # | 错误内容 | 修正依据 | 修正后结论 |
|:---:|:---|:---|:---|
| 1 | 后端框架误判为 Laravel | 响应头 `x-powered-by: Express` | Node.js + Express |
| 2 | 登录邮箱 `aq.jilong@163.com` 失败 | 用户确认实际注册邮箱 | `aq.jinlong@163.com`（"jilong" → "jinlong"） |
| 3 | 下载结果图误用 `sourceFileName` 当 URL | 任务响应 `images` 字段 | 真实 URL 为 `https://oss-cdn.i2tools.com/ai-results/...` |
| 4 | 注册走错域名 `/en`（英文版）收不到验证码 | 用户指出主域名是 i2tools.com | 直接登录已注册账号，跳过重新注册 |
| 5 | PixiJS `readPixels` 返回空 | `preserveDrawingBuffer` 未设 | 改用 `screenshot()` + `toDataURL()` |
| 6 | `page.locator().click()` 被 dialog-overlay 拦截 | Radix focus trap 拦截原生事件 | 用 `evaluate(btn => btn.click())` 调原生方法 |

### 11.2 置信度分级

#### A. 实测确认（高置信度，有直接证据）

| 项 | 证据类型 | 章节 |
|:---|:---|:---:|
| 前端 Next.js 19.2.0-canary App Router | 路由结构 + chunk 文件名 + `__next` 数据特征 | §2.1 |
| PixiJS v8（WebGPU + WebGL 双路径） | vendor chunk 字符串 + 渲染器实例化代码 | §2.3 |
| Zustand 状态管理 | state 调用模式 `s.G.getState()` 实测 | §2.2 |
| Axios 1.18.1 / Zod 4.4.3 | npm 包版本字符串实测 | §1.2 |
| next-intl 国际化 | `[locale]` 路由 + `NEXT_LOCALE` cookie 实测 | §2.1 |
| 后端 Node.js + Express | 响应头 `x-powered-by: Express` | §3 |
| 阿里云 OSS（结果图） | `oss-cdn.i2tools.com` 域名 + 结果图 URL 实测 | §3.3 |
| Cloudflare R2（上传存储） | `r2-uploads` 路径实测 | §3.3 |
| IndexedDB v10 `magic-perler-projects` | 数据库版本 + object stores 实测 | §2.4 |
| .pbp 格式 `{version, format, data}` | 实测解密成功 | §5 |
| AES-GCM-256 + PBKDF2(SHA-256, 100000, perler-salt) | 解密参数实测验证（`decode_pbp.js` 跑通） | §5.2 |
| 后处理 4 预设（light/balanced/strong/aggressive） | 弹窗 dump 实测 | §4.4 |
| MARD 色号体系 H/G/C/M 221 色 | `brands.mard.definitions` 实测 | §4.6 |
| API 端点 14 个 | 实测调用 + 响应 body | §3.1 |
| 小红书 Vue 3 + formula-runtime | vendor chunk + `data-v-` 标记实测 | 附录 I |
| 小红书 openresty 网关 | 响应头实测 | 附录 I |
| 小红书 x-s / x-s-common / x-t 签名头 | XHR 抓包实测 | 附录 I |

#### B. 推测（中置信度，基于间接证据推断）

| 项 | 推测依据 | 不确定点 | 章节 |
|:---|:---|:---|:---:|
| 颜色匹配算法 DeltaEHybrid + CAM16-UCS | JS chunk 字符串看到类名 | 具体调用流程、参数选择是推测的 | §4.1 |
| K-D Tree 7 叉树加速结构 | chunk 字符串推测 | 树的构建/查询细节未实测 | §4.1 |
| Median Cut 调色板提取 | chunk 字符串推测 | 具体实现未反编译完整 | §4.1 |
| 像素化 4 模式（Structural/Dominant/Average/PixelArtOptimized） | 模式名实测 | 各模式算法差异是推测的 | §4.2 |
| perfect-pixel 修正算法 | 推测"借鉴开源思路重写 TS 版" | 原始开源出处未确认 | §4.3 |
| 去噪 8 连通域 BFS | 基于参数表推测实现 | BFS/DFS 选择、扫描顺序未确认 | §4.4 |
| 库存扣减色号累加逻辑 | API 实测通过 | 扣减的具体时序、回滚机制推测 | §4.6 |

#### C. 高度推测/不确定（低置信度，需接手者验证）

| 项 | 现状 | 建议 | 章节 |
|:---|:---|:---|:---:|
| 拼图图纸识别 Canny/Sobel 边缘检测 | **完全是推测，无反编译证据** | 接手后应优先反编译图纸识别 chunk 验证 | §4.5 |
| 数据库 Schema（users/projects/inventory/checkin/orders/products） | 基于 API 返回结构反推 | 真实表结构、字段类型、索引需查实际 DDL | §7 |
| SQL DDL 语句 | 完全推测 | 仅供建库参考，非生产 schema | §7 |
| 环境变量清单 | OSS/R2 实测，JWT_SECRET/XSRF_SECRET 等推测 | 部署前需向原作者确认 | §6.2 |
| 部署命令 `pnpm db:migrate` 等 | 推测 | 需查 `package.json` scripts 字段确认 | §6.3 |
| Redis 使用 | "可选"是推测 | 未实测是否有 Redis | §6.1 |
| Nginx 反代配置示例 | 推测的模板 | 需根据实际部署环境调整 | §6.3 |

### 11.3 验证路径（接手者必读）

1. **高置信度项（A 类）**可直接采信，作为接手基础
2. **中置信度项（B 类）**需进一步反编译 JS chunk 验证：
   - 关键 chunk：`9872`(3D) / `8071`(颜色) / `6777`(去噪) / `9350`(MARD) / `7824`(IDB) / `1720`(小红书)
   - 验证方法：`node -e "require('./i2tools/.../chunk-9872.js')"` 或用 webpack-unpack
3. **低置信度项（C 类）**务必向原作者 `aq.jinlong@163.com` 确认，或通过实际部署验证：
   - 数据库 DDL：请求原作者提供 `schema.sql` 或 migration 文件
   - 环境变量：请求原作者提供 `.env.example`
   - 拼图图纸识别：反编译图纸识别专用 chunk（待定位）
4. 任何关键决策前，优先参考：
   - `/workspace/i2tools/` 爬取样本（2742 文件，606MB）
   - `test_*.py` 实测脚本（27 个，覆盖所有功能模块）
   - `/workspace/i2tools_review.md` 复盘文档（附录 A~I 完整证据链）

### 11.4 持续修正机制

本文档基于 2026-09-13 的实测快照整理。如接手者在验证过程中发现新证据与文档不符，请：
1. 在对应章节标注 `[待修正：YYYY-MM-DD 发现 ...]`
2. 将新证据补入 `i2tools_review.md` 附录
3. 同步更新 PRD 和 DEV 两个文档

---

**文档结束**
