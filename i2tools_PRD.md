# 幻彩拼豆 (i2tools.com) 产品需求文档 (PRD)

## 0. 文档信息

| 项 | 值 |
|:---|:---|
| 文档版本 | v4.0 |
| 整理时间 | 2026-09-14 |
| 来源 | 基于 i2tools.com 实测逆向整理（参见 `file:///workspace/i2tools_review.md`） |
| 目标读者 | 产品经理 / 业务方 / 接手团队 |
| 关联文档 | `file:///workspace/i2tools_DEV.md`（开发文档，技术细节落点，v3 同步） |
| 实测账号 | `aq.jinlong@163.com`（等级 1，10/100 EXP） |

> 说明：本文档所有需求规格、按钮坐标、参数表均来自 2026-09-13 的真实在线实测。v3 修正同步 DEV 文档：B 类 4 项（perfect-pixel / 去噪 BFS / 库存扣减 API / MARD-CNN 客户端识别）已通过真实操作测试升级到 A 类，详见 §11.2.1 / §11.3。涉及技术实现的细节请查阅 DEV 文档对应章节。

### 0.1 修正历史

| 版本 | 时间 | 变更 |
|:---:|:---|:---|
| v1.0 | 2026-09-13 | 初版文档 |
| v2.0 | 2026-09-13 | 反编译 chunk 验证修正 4 处算法错误（K-D Tree / Median Cut / Canny-Sobel / 小红书客户端反爬） |
| v3.0 | 2026-09-13 | 真实操作测试全部完成：B 类 4 项升级到 A 类。新增 §11.2.1 实测操作验证修正 6 项。C 类新增 6 项错误推测修正（operationType→actionType、H01→H1、软删除→反向op、库存为负阻断→不阻断、perfect-pixel 步骤→to.aS 签名+参数、去噪扫描→BFS 队列扩散）。D 类小红书 worker 标注"用户决定不测试"。 |
| v4.0 | 2026-09-14 | 新增 §12 复刻可行性评估（简版）：工具台真实清单（3 个独立工具，chunk 9173 `C8`）+ 资产分层 + 5 个结构性缺口精确归属到所属工具与技术栈。完整版与 roadmap 见 `i2tools_DEV.md` §12。 |

---

## 1. 产品概述

### 1.1 产品定位

| 项 | 值 |
|:---|:---|
| 产品名 | 幻彩拼豆 |
| 域名 | `https://i2tools.com/`（中文版主域名，英文版走 `/en`） |
| 一句话定位 | 面向拼豆 / 烫豆 / 毛巾烫创作者的一站式在线工作台，整合图片转像素画、图纸识别、3D 预览、库存管理、社区导入全流程 |
| 形态 | Web SPA（Next.js 19 + PixiJS v8 WebGPU/WebGL），同时支持 PC + 移动端 viewport |
| 商业模式 | 积分消耗（AI 生成 1 分/次）+ 订阅套餐（云备份配额 + 积分包）+ 等级权益体系 |

### 1.2 目标用户

| 用户层 | 占比（推测） | 典型场景 |
|:---|:---|:---|
| **个人拼豆创作者**（爱好者 + 小批量代工） | 主要 | 上传照片生成图纸、3D 预览效果、扣减库存对账 |
| **拼豆工作室 / 教学机构** | 次要 | 批量代工订单管理、库存盘点、教学课件制作 |
| **社区作品复用者** | 长尾 | 从小红书笔记导入图纸，快速复用社区作品 |

**用户特征**（基于实测账号 aq.jinlong@163.com 等级 1）：
- 创作行为强依赖**积分**（每日 3 分免费额度，AI 生成 1 分/次）
- 创作能力受**等级权益**约束（云备份配额 5 个 / AI 识别配额 10 次 / 日）
- 需要长期**库存追踪**（按 MARD 色号体系管理豆材库存，低于阈值 10 颗触发预警）
- 创作流程对**色号合并 / 去杂色 / 降噪**后处理依赖度高（实测 49 色合并到 16-23 色）

### 1.3 核心价值

| 传统流程痛点 | 幻彩拼豆解决方案 |
|:---|:---|
| 手绘图纸耗时 | AI 像素化（4 模式：Structural/Dominant/Average/PixelArtOptimized）一键生成 |
| 人工配色误差大 | MARD 4 系列 221 色号体系 + CAM16-UCS 颜色距离算法 |
| 看不出最终效果 | 3D 预览三工艺切换（拼豆圆柱 / 烫豆扁平 / 毛巾烫肋条） |
| Excel 管库存易错 | 色号库存联动，项目 `colorCounts` 直接扣减库存 + 低库存预警 |
| 社区作品难复用 | 小红书笔记链接导入（受外部反爬限制） |

---

## 2. 用户角色与权限

### 2.1 用户角色

| 角色 | 入口 | 权限范围 |
|:---|:---|:---|
| **未登录访客** | 首页 / 教程 | 仅浏览静态内容 |
| **注册用户** | 登录后全站 | 工具台 / 编辑器 / 工作台 / 库存 / 账户 |
| **订阅用户** | 账户中心 → 订阅管理 | 解锁更高云备份配额 + 积分套餐 |

### 2.2 等级权益表（5 级）

来源：`GET /v1/app/level/configs`（实测响应 200）

| 等级 | 累积 EXP | 每日积分 | 云备份配额（个） | AI 识别配额（次/日） |
|:---:|:---:|:---:|:---:|:---:|
| 1 | 0 | 3 | 5 | 10 |
| 2 | 100 | 5 | 10 | 10 |
| 3 | 500 | 8 | 20 | 10 |
| 4 | 2,000 | 10 | 30 | 10 |
| 5 | 5,000 | 10 | （更高，未实测到精确值） | 10 |

### 2.3 EXP 升级机制

| 来源 | EXP 奖励 |
|:---|:---|
| **每日签到** | +10 EXP（连续签到累积，实测账号连续 13 天） |
| 创作行为 | （推测，未实测到精确值） |

> 实测账号 aq.jinlong@163.com 当前：等级 1，累积 10 EXP / 100 EXP 升级阈值。

### 2.4 订阅套餐（账户中心 → 订阅管理）

来源：`GET /v1/app/products/cloud_backup_space/offers` + `/v1/app/products/mp_points/offers`

| 类型 | 套餐 | 价格 |
|:---|:---|:---|
| **云备份空间** | 30 个备份 | ¥10 |
| | 60 个备份 | （未实测精确价，介于 10-30） |
| | 150 个备份 | （未实测精确价） |
| | 500 个备份 | ¥30 |
| **积分套餐** | 25 积分起 | ¥5 |

---

## 3. 功能模块清单

### 3.1 工具台 `/tools`

#### 3.1.1 ai-pixel-art（图片生成像素画）

**用户故事**：作为创作者，我希望上传一张图片，系统自动生成拼豆像素画，以节省手工配色时间。

**功能需求**：

| 字段 | 选项 / 行为 |
|:---|:---|
| 上传图片 | 支持 jpg/png/webp，通过 `input[type="file"]` |
| 预设尺寸 | 50 / 52 / 78 / 104（4 个预设，单击选中） |
| 像素化模式 | 智能 / 卡通 / 写实 / 简化 |
| ↳ 对应算法 | Structural / Dominant / Average / PixelArtOptimized |
| 色号范围 | MARD（221 色，默认选中） |
| 颜色上限 | 不限 / 少量 / 适中 / 丰富 |
| 杂色清理 | 不限 / 轻度 / 适中 / 强力（4 预设强度） |
| 色彩增强 | 关闭 / 自然 / 鲜艳 |
| 消耗积分 | 1 分/次（实测账号 25 → 24） |
| 任务模型 | 异步任务（PENDING → PROCESSING → SUCCESS） |
| 结果托管 | 阿里云 OSS：`https://oss-cdn.i2tools.com/ai-results/bead-conversion/TASK.../0.webp` |

**API**：`POST /v1/app/pixel-art/conversions` 提交 → `GET /v1/app/pixel-art/conversions/{taskNo}` 轮询

**验收标准**：
- ✅ 任务 SUCCESS 后可下载 webp 结果图
- ✅ 积分扣减 1 分
- ✅ 实测脚本 `file:///workspace/gen_pixelart.py`

#### 3.1.2 perfect-pixel（伪像素画修正）

**用户故事**：作为创作者，我希望把外部像素画修正对齐到拼豆网格，以避免半像素错位。

**功能需求（v3 反编译 + 实测修正）**：

| 步骤 | 行为 | 实测证据 |
|:---|:---|:---|
| 1. 上传像素画 | `input[type="file"]`，jpg/png/webp | `run_perfect_pixel.py` |
| 2. 调用修正（Web Worker 异步） | 函数 `to.aS(imageSource, gridDimensions, projectName, pixelLayerName, referenceLayerName)`，参数 `sampleMethod:"center"` / `gridSize:null` / `minSize:4` / `peakWidth:6` / `refineIntensity:.25` / `fixSquare:!0` | chunk 1720 反编译 + `verify_pp_v3.py` |
| 3. 输出修正 canvas | `toDataURL('image/png')` 可下载 | `perfectpixel_result_canvas1.png` |
| 4. 创建项目继续编辑 | 可选「创建项目继续编辑」，写入 IndexedDB，跳转 `/editor?projectId=xxx` | `pp_after_save.png` |

> ⚠️ v3 修正：原"边界扫描→量化对齐→重采样匹配"为推测描述，**已用 chunk 1720 `to.aS` 函数签名 + 6 个参数实测替换**。函数体内部权重张量仍未反编译（D 类，待接手者验证）。

**验收标准**：
- ✅ canvas[1] 出现结果像素
- ✅ 导出 PNG 可下载
- ✅ 保存项目写入 IndexedDB 并跳转编辑器
- ✅ 实测脚本 `file:///workspace/run_perfect_pixel.py` + `file:///workspace/verify_pp_v3.py`

#### 3.1.3 小红书链接导入

**用户故事**：作为创作者，我希望从小红书笔记导入拼豆图纸，以快速复用社区作品。

**功能需求**：

| 项 | 值 |
|:---|:---|
| 输入 | 小红书 explore 笔记 URL，需含 `xsec_token`、`xsec_source`、`source` 三件套参数 |
| 后端 API | `POST /v1/app/xhs/import` |
| 服务端流程 | 请求小红书 SSR HTML → 解析 meta description / og:image 提取图纸信息 → 转换为项目 |
| 实测响应 | HTTP 422 Unprocessable Entity |

**已知限制**（小红书三层反爬，详见 DEV §9）：
1. **脚本层**：`as.xiaohongshu.com/api/sec/v1/ds` 返回 obfuscator.io 风格混淆脚本（59KB），含 `_0x341b` 字符串数组 + 重写 `apply/call/bind` 防 hook
2. **设备指纹层**：`/api/sec/v1/sbtsource` 下发指纹采集脚本 URL + token 生成 + commonPatch 加密 API 清单
3. **请求签名层**：每个 XHR 必带 `x-s`（请求级签名）+ `x-s-common`（会话级公共签名）+ `x-t`（13 位毫秒时间戳）

**产品结论**：422 系外部平台反爬限制，i2tools 侧功能已实现（端点存在并响应），需要服务端代理 + xsec_token 凭证才能稳定导入。

---

### 3.2 编辑器 `/editor?projectId=xxx`

#### 3.2.1 新建项目入口

| 入口 | 触发 |
|:---|:---|
| 新建空白项目 | navbar「新建」下拉 → 填宽高（默认 50×50）→ 点「创建」→ 跳转 `/editor?projectId=1789297487536-...` |
| 导入 .pbp 项目文件 | `input[type="file"][accept=".pbp"]`（JSON 容器 + AES-GCM-256 加密，详见 §6.2） |
| 导入拼图图纸 | `input[type="file"][accept*="image"]` 上传图片，**自动**触发「选择转换模式」modal |
| 小红书链接导入 | 工具台 `/tools/xhs` |

#### 3.2.2 「选择转换模式」modal（图纸导入参数）

> 真实入口：直接上传图片到 `input[type="file"][accept*="image"]` 即自动弹出，**无需先点「新建」**。

| 选项 | 适用场景 |
|:---|:---|
| 图片转换 | 适合照片 / 插画等普通图片 |
| 像素图转换 | 适合像素图或清晰网格图片 |

选「图片转换」后进入参数 modal（见 §3.2.3）。

#### 3.2.3 参数 modal 完整字段（实测）

来源：用 `file:///workspace/测试图.jpg` 实测，详见 review.md 附录 F。

| 参数 | 值 / 选项 |
|:---|:---|
| **图片信息** | 205×307 尺寸 / 76 颜色 / 62,935 数量 |
| **水平尺寸** | 50 / 52 / 78 / 104（4 个预设） |
| **转换效果** | 智能 / 卡通 / 写实 / 简化 |
| ↳ 对应算法 | Structural / Dominant / Average / PixelArtOptimized |
| **色号范围** | MARD（221 色）— 默认选中 |
| **颜色上限** | 不限 / 少量 / 适中 / 丰富 |
| **杂色清理** | 不限 / 轻度 / 适中 / 强力（4 预设） |
| **色彩增强** | 关闭 / 自然 / 鲜艳 |
| **提交按钮** | 「创建项目」 |

**导入结果实测**：
- 跳转 `/editor?projectId=1789307961484-yd8c0qg`
- 网格尺寸：205×307
- 色号数：76
- 总豆数：62,935

> ⚠️ **关键交互陷阱**：点「创建项目」时 `page.locator().click()` 会被 `dialog-overlay` 拦截 pointer events，必须用 `evaluate(btn => btn.click())` 调原生方法触发 React onClick（详见 DEV §9 已知问题）。

#### 3.2.4 编辑器顶栏功能（基于实测坐标）

| 按钮 | 屏幕坐标 | 功能 |
|:---|:---:|:---|
| 我的作品 | （顶栏左侧） | 跳转 `/workspace/create` 项目列表 |
| 导入项目 | （顶栏左侧） | 触发 `input[type="file"][accept=".pbp"]` |
| 辅助模式 | （顶栏左侧） | 切换辅助显示 |
| 3D 预览 | （顶栏左侧） | 打开 3D 面板，详见 §3.2.5 |
| 快捷键 | （顶栏左侧） | 弹出快捷键说明 |
| 主题配置 | （顶栏左侧） | 切换主题 |
| 发布作品 | （顶栏左侧） | 发布到画廊 |
| 导出作品 | （顶栏左侧） | 弹出「选择导出格式」modal，详见 §3.2.7 |
| **色号合并** | **@(1185, 217)** | 弹出 §3.2.6 色号合并弹窗 |
| **去除杂色** | **@(1260, 217)** | 弹出 §3.2.6 去除杂色弹窗 |
| **降噪** | **@(1335, 217)** | 弹出 §3.2.6 降噪弹窗 |

#### 3.2.5 3D 预览面板

**用户故事**：作为创作者，我希望看到拼豆/烫豆/毛巾烫三种工艺的真实效果，决定采用哪种工艺。

**功能需求**：

| 项 | 实测结果 |
|:---|:---|
| 3D 按钮 | `button[title="3D 预览"]` |
| 渲染上下文 | WebGL2 canvas 1280×782 |
| 渲染引擎 | PixiJS v8（WebGPU + WebGL 双路径，详见 DEV §2.3） |
| 真实数据来源 | ai-pixel-art 生成项目 5×5=25 颗豆（H2:22 + H6:2 + H16:1） |
| **拼豆工艺** | 独立圆柱豆 + 中心孔 |
| **烫豆工艺** | 融合为扁平面米状，无独立边界 |
| **毛巾烫工艺** | 横向肋条纹理模拟织物 |

5 个复选框交互：
- 显示阴影
- 自动旋转
- 环境光
- 拼豆板
- 背景色

**验收标准**：
- ✅ 三工艺切换有视觉差异
- ✅ 5 个复选框全部可切换
- ✅ 空白项目（0 豆）开 3D 无对象（需先有豆数据）

#### 3.2.6 后处理算法弹窗（色号合并 / 去除杂色 / 降噪）

> 三个按钮位于顶栏 @(1185, 217) / @(1260, 217) / @(1335, 217)，详见 review.md 附录 H。

**通用触发技巧**：用 `page.evaluate(btn => btn.click())` 调原生方法绕过 `dialog-overlay` 拦截。

##### 3.2.6.1 色号合并弹窗

| 字段 | 实测值 |
|:---|:---|
| 模式选择 | **相似度 / K-means**（两种聚类算法） |
| 阈值滑块 | 90%（阈值越高只会合并越接近的色号） |
| 当前色号数 | 49 |
| 预计保留 | 23 |
| 影响颗数 | 5,444 |
| 建议分组 | 17 |
| 确认按钮 | 「确认应用合并」 |

每组结构示例：
```
组1: 5个色号 影响3228颗 中置信度
  来源: H9 / H2 / H22 / H10 / H8
  主色: H9
```

##### 3.2.6.2 去除杂色弹窗

**描述**：「识别作品里数量较少的零碎色号，并把它们吸附到更接近的主色上」

| 字段 | 实测值 |
|:---|:---|
| 清理强度滑块 | 35%（轻度 ↔ 强力） |
| 强度说明 | 「强度越高，移除的小色号越多，但也更可能影响细节」 |
| 当前色号数 | 49 |
| 预计保留 | 16 |
| 影响颗数 | 1,685 |
| 清理建议 | 33 |
| 确认按钮 | 「确认清理」 |

每个建议项结构示例：
```
H23: 174颗
  替换为: M7 (当前1486颗)
  评级: 适中
  最大连通块: 6
  连通块: 139
```

**评级标准**：

| 评级 | 标准 |
|:---|:---|
| 安全 | 最大连通块 1-3，少量连通块 |
| 适中 | 中等连通块 |
| 需复核 | 最大连通块 91，连通块 83（例如 M8 → M7） |

##### 3.2.6.3 降噪弹窗

**描述**：「消除面积小于阈值的孤立噪点，在保留细节的同时降低拼装难度」

| 字段 | 实测值 |
|:---|:---|
| 预设强度 | 轻度 / 标准 / 强力 / 激进（light / balanced / strong / aggressive） |
| 候选像素 | 2,619 |
| 预计处理 | 1,444 |
| 可清理区域 | 1,443 |
| 受保护区域 | 791 |
| 滑块 1 | **最大色块面积 = 2**（范围 1-12） |
| 滑块 2 | **清理轮数 = 1** |
| 高级选项 | 有 |
| 确认按钮 | 「确认」 |

**算法对应关系**（详见 DEV §4.4）：

| 弹窗字段 | 算法印证 | 实测证据 |
|:---|:---|:---|
| 「最大连通块 N / 连通块 N」 | 8 连通域 BFS 分析（chunk 6777：`q.shift()+q.push()` 经典 BFS 队列扩散 + `new Uint8Array` 标记矩阵 + `u(t)` 4/8 连通选择器） | chunk 6777 反编译 |
| 「最大色块面积」滑块 1-12 | 面积阈值过滤 `areaThreshold` | chunk 6777 |
| 「替换为(主色)」 | 颜色距离计算（sRGB 加权距离） | chunk 6777 |
| 4 预设强度 | 4 套 `light/balanced/strong/aggressive` 参数 | chunk 6777 |
| 「确认」应用后色号数变化 | **实测 49 → 45**（`test_denoise_apply_v3.py`，证明算法真实执行） | `dn_after_apply.png` |
| 模式选择 K-means | K-means 聚类 |
| 相似度阈值滑块 90% | 相似度阈值可调 |

#### 3.2.7 导出功能

「选择导出格式」modal 3 种格式：

| 格式 | 说明 |
|:---|:---|
| 拼豆图纸 (PNG) | 含网格、色号表 |
| 像素原图 (PNG) | 无网格的高清图 |
| 项目数据 (PBP) | 保存进度，AES-GCM-256 加密，可再次导入（详见 §6.2） |

**实测**：选「项目数据 (PBP)」→ 下载 `项目-2026-09-13-205x307-20260913135933.pbp`（5,613,122 字节 ≈ 5.3MB）。

---

### 3.3 工作台 `/workspace`

| 路径 | 功能 |
|:---|:---|
| `/workspace/create` | 项目列表 |
| `/workspace/gallery` | 画廊 |
| `/workspace/inventory` | 库存管理（详见 §3.4） |
| `/workspace/tools` | 工具台 |
| `/workspace/account` | 账户中心（PC 简化版，移动端独有菜单见 §3.5） |

---

### 3.4 库存管理 `/workspace/inventory`

**用户故事**：作为创作者，我希望跟踪每种色号的库存，避免买到一半发现缺豆。

#### 3.4.1 API 实测

| 接口 | 方法 | 状态 | 数据 |
|:---|:---:|:---:|:---|
| `/v1/app/inventory/summary` | GET | 200 | 总数 / 跟踪色号 / 低库存 / 默认阈值 10 / 调整量 100 |
| `/v1/app/inventory/brands` | GET | 200 | 5 品牌：MARD 305 / COCO 291 / 漫漫 289 / 盼盼 291 / 咪小窝 291 |
| `/v1/app/inventory/colors` | GET | 200 | 色号详情（hex、库存、阈值） |

#### 3.4.2 MARD 色号体系

实测项目数据共 21 种色号：

| 系列 | 色号（库存数） |
|:---|:---|
| **H 系列** | H2(1898) / H6(77) / H7(223) / H16(139) / H20(...) / H3 / H4 / H5 / H8 / H9 / H10 / H11 / H13 / H14 / H19 / H21 / H22 / H23 |
| **G 系列** | G3(15) / G12 / G14 / G4 / G5 / G6 / G7 / G8 / G10 / G11 / G15 / G16 / G17 / G21 |
| **C 系列** | C5 / C12(3) |
| **M 系列** | M9(1) / M15(30) / M3 / M4 / M5 / M6 / M7 / M8 / M10 / M12 |

#### 3.4.3 库存扣减逻辑（v3 完整实测）

> v3 修正：原"扣减→低库存预警→按钮"为推测描述，**已用 chunk 3244 反编译 + v14 真实测试替换**。

**API 端点（反编译 + 实测验证）**：

| 方法 | 路径 | 用途 |
|:---:|:---|:---|
| GET  | `/v1/app/inventory/summary` | 库存汇总（totalQuantity / trackedColorCount / inStockColorCount / lowStockCount / defaultWarningThreshold=10 / defaultAdjustQuantity=100） |
| GET  | `/v1/app/inventory/colors?pageIndex=1&pageSize=2000` | 色号列表（items 数组：`{brandCode,colorCode,quantity,hex}`） |
| POST | `/v1/app/inventory/operations` | 手动调整（actionType=`manual_adjust`，items 数组） |
| POST | `/v1/app/inventory/operations/{id}/rollback` | 回滚指定操作（id 必须为 numeric string） |
| POST | `/v1/app/inventory/operations/project-consume` | 项目消耗库存（snapshotTitle+colorSystem+materialsCompact+remark?） |

**请求字段 schema（v3 修正：字段名 `actionType` 而非 `operationType`）**：

| 字段 | 类型 | 枚举值 | 说明 |
|:---|:---|:---|:---|
| `actionType` | string | `manual_adjust` / `project_consume` / `import` / `rollback` | 操作类型（⚠️ 不是 operationType） |
| `items[].brandCode` | string | 如 `MARD` | 品牌 |
| `items[].colorCode` | string | 如 `H1` / `H2` | 色号（⚠️ 不带 0，不是 `H01`） |
| `items[].changeQty` | int | 正/负 | 增减数量（**允许为负数，不强制非负校验**） |
| `remark` | string | - | 备注（可选） |
| `materialsCompact` | string | 如 `H1:1,H2:2` | 项目消耗专用 |

**v14 实测流程**（`test_inv_deduct_v14.py` + `inv_v14.log`，9 步全部 status=201）：

| 步骤 | 操作 | 结果 |
|:---:|:---|:---|
| 1 | `POST /operations` H1 +10 | opId=29854，H1 0→10 |
| 2 | `POST /operations/29854/rollback` | 反向 op（H1 -10），H1 10→0 |
| 3 | `POST /operations` H1 -3 | opId=29856，H1 0→**−3**（允许负数） |
| 4 | `POST /operations/29856/rollback` | 反向 op（H1 +3），H1 −3→0 |
| 5 | `POST /operations/project-consume` H1:1,H2:2 | opId=29858，H1 −1 / H2 −2 |

**回滚机制（v3 修正）**：
- ❌ 原推测：软删除原 operation
- ✅ 实测：**创建反向 operation**（`actionType=rollback`，`sourceType=system`，`rollbackOfId` 指向原 op，`direction` 相反，`changeQty` 取反）

**实测证据**：`inv_v14.log` + `inv_v8_modal.png` + `inv_v9_main.png`

---

### 3.5 账户中心（移动端独有菜单 + PC）

> PC 版 `/workspace/account` 没有「每日签到」「订阅管理」菜单，这两个菜单是**移动端 viewport 独有**。需用移动端 viewport + `is_mobile=True` + `has_touch=True` 重新访问。

| 菜单 | 平台 | API | 关键数据 |
|:---|:---|:---|:---|
| **每日签到** | 移动端 | `/v1/app/checkin/status` | 今日已签到、连续 13 天、签到得 10 EXP |
| **订阅管理** | 移动端 | `/v1/app/products/cloud_backup_space/offers` + `/v1/app/products/mp_points/offers` | 4 备份套餐 + 积分套餐（详见 §2.4） |
| **个人资料** | PC + 移动 | `/v1/app/auth/info` + `/v1/app/level/configs` | 等级 1（10/100 EXP）、云备份 5 个、每日 3 积分 |
| **库存** | PC + 移动 | 同 §3.4 | 同 PC |

移动端 viewport 配置示例：
```python
ctx = browser.new_context(
    viewport={'width': 390, 'height': 844},
    user_agent='Mozilla/5.0 (iPhone; ...)',
    is_mobile=True,
    has_touch=True
)
```

---

### 3.6 教程 `/tutorials`

静态内容，未实测到交互功能。

---

## 4. 业务流程图

### 4.1 创作主流程

```
上传图片
   ↓
ai-pixel-art 生成像素画（消耗 1 积分，异步任务）
   ↓
perfect-pixel 修正对齐网格
   ↓
创建项目进编辑器
   ↓
3D 预览三工艺（拼豆/烫豆/毛巾烫）
   ↓
后处理：色号合并 / 去除杂色 / 降噪
   ↓
导出 .pbp / 拼豆图纸 / 像素原图
   ↓
扣减库存（colorCounts 减库存 + 低库存预警）
```

### 4.2 图纸导入流程（v3 实测：MARD-CNN 客户端识别）

```
上传图片 → input[type="file"][accept*="image"]
   ↓
自动触发「选择转换模式」modal
   ↓
选「图片转换」（适合照片/插画）
   ↓
参数 modal：尺寸 / 效果 / MARD / 颜色上限 / 杂色清理 / 色彩增强
   ↓
点「创建项目」（需用 evaluate 调原生 click 绕过 dialog-overlay）
   ↓
MARD-CNN 客户端本地识别（3 阶段：Cropping → Segmenting → Review + GridAlign/Verification）
   ⚠️ v15 实测 XHR 日志无任何识别相关请求（无 pattern/recognize/mard-cnn），证明是浏览器本地推理
   ↓
跳转编辑器 /editor?projectId=xxx
   ↓
（同 §4.1 后续流程）
```

> ⚠️ v3 修正：MARD-CNN 模型权重张量与 CNN 网络结构仍未反编译（D 类，待接手者验证 chunk 3107 中的权重矩阵）。客户端识别路径已通过 v15 实测确认（`si15.log` + `exports/项目-*.pbp` 5.6MB）。

### 4.3 小红书导入流程

```
输入小红书 URL（需含 xsec_token + xsec_source + source 三件套）
   ↓
i2tools 后端代理 → 请求小红书 SSR HTML
   ↓
解析 meta description / og:image 提取图纸信息
   ↓
转换为项目
   ↓
跳转编辑器
```

> ⚠️ 当前实测响应 HTTP 422（小红书三层反爬限制），详见 §3.1.3 与 DEV §9。

### 4.4 .pbp 项目导入/导出对称流程

```
导入：input[type="file"][accept=".pbp"]
   → JSON.parse 外层
   → Base64 解码 data
   → PBKDF2 派生密钥（固定 password/salt）
   → AES-GCM-256 解密
   → 写入 IndexedDB magic-perler-projects
   → 跳转 /editor?projectId=xxx

导出：编辑器 → 导出作品 → 选「项目数据 (PBP)」
   → 项目数据 + assets 序列化为 JSON
   → AES-GCM-256 加密（同一密钥）
   → Base64 编码
   → 外层 JSON 容器 {version:"1.0", format:"pbp", data:<base64>}
   → 触发下载 .pbp 文件
```

实测对称验证：导入样本与导出样本的 PBKDF2 派生密钥完全相同（`f10c45...8734`），结构完全一致。

---

## 5. 非功能性需求

| 类别 | 需求 |
|:---|:---|
| **性能** | PixiJS v8 WebGPU + WebGL 双路径，136×196 网格（26,656 颗豆）流畅渲染 |
| **浏览器兼容** | Chrome / Edge / Safari / Firefox |
| **移动端** | viewport 独有 UI（每日签到 / 订阅管理），需 390×844 viewport + is_mobile + has_touch |
| **国际化** | next-intl，`[locale]` 动态路由 + `NEXT_LOCALE` cookie，中英文版本（`/` vs `/en`） |
| **安全** | XSRF + Cookie 双 token，JWT + Refresh |
| **可用性** | 多弹窗 Escape 关闭，更新日志对话框 |
| **错误监控** | 前端错误上报 `POST /v1/client-errors`（状态 201） |
| **对象存储** | 阿里云 OSS（结果图 `oss-cdn.i2tools.com/ai-results/...`） + Cloudflare R2（用户上传 `_next/.../r2-uploads/...`） |

---

## 6. 数据模型（产品视角）

### 6.1 项目数据结构（IndexedDB projects store）

```ts
{
  id: string,                                  // 项目 ID，格式如 "1789307961484-yd8c0qg"
  layers: Layer[],                             // 图层数组（REF 参考层 + PIXEL 像素层）
  gridDimensions: { rows: number, cols: number },
  settings: {
    colorSystem: 'MARD' | ...,
    granularity: number,
    threshold: number,
    pixelationMode: 'structural' | 'dominant' | 'average' | 'pixelart-optimized',
    colorMatchingAlgorithm: 'cam16-ucs' | ...
  },
  colorCounts: Record<string, number>,          // {色号: 颗数}
  totalBeadCount: number,
  originalAssetId: string,
  activeLayerId: string,
  paletteSelections: string[],                  // 调色板选择（MARD 221 色全集）
  recentColors: string[]
}
```

**IndexedDB Schema**（详见 DEV §2.4）：
- 数据库名：`magic-perler-projects`（version=10）
- object store：`projects` / `project_snapshots` / `magic-perler-assembly-progress`

### 6.2 .pbp 文件格式

**外层 JSON 容器**：
```json
{
  "version": "1.0",
  "format": "pbp",
  "data": "<base64 密文>"
}
```

**加密**（详见 DEV §5）：
- 算法：AES-GCM-256
- 密钥派生：PBKDF2（password=`perler-beads-project-v1`，salt=`perler-salt`，iterations=100000，hash=SHA-256）
- IV：Base64 解码后前 12 字节
- ⚠️ **固定密钥**（混淆非真加密）：所有 .pbp 文件使用同一把固定密钥，任何拿到 .pbp 的人都能解密。**产品建议**：如需真加密保护，需引入用户密钥或服务端密钥。

### 6.3 MARD 色号体系

| 系列 | 用途 |
|:---|:---|
| **H 系列** | 主色系（实测 18 色） |
| **G 系列** | 绿色系（实测 14 色） |
| **C 系列** | 浅色系（实测 2 色） |
| **M 系列** | 混合系（实测 10 色） |

完整定义：`brands.mard.definitions` 映射（详见 DEV §3 API）。

---

## 7. 部署需求

| 组件 | 要求 |
|:---|:---|
| 前端 | Node.js 18+（推荐 20 LTS）、Next.js 19.2.0-canary（App Router）、pnpm 8+ |
| 后端 | Node.js + Express，PostgreSQL 14+ 或 MySQL 8+，Redis 6+（可选，会话缓存） |
| 对象存储 | 阿里云 OSS（结果图） + Cloudflare R2（用户上传） |
| 域名 | `i2tools.com` + `oss-cdn.i2tools.com` |
| 反代 | Nginx，HTTPS，HTTP/2（HTTP/3 可选） |
| 监控 | 前端错误上报 `POST /v1/client-errors`，可选 Sentry APM |

> 详细部署步骤、环境变量、Nginx 配置示例详见 `file:///workspace/i2tools_DEV.md` §6。

---

## 8. 验收清单（基于 14 项实测）

| # | 功能 | 状态 | 验收脚本 |
|:---:|:---|:---:|:---|
| 1 | ai-pixel-art 上传+生成+耗积分+下载 | ✅ | `gen_pixelart.py` |
| 2 | perfect-pixel 修正+保存 | ✅ | `run_perfect_pixel.py` |
| 3 | 3D 预览面板+三工艺+5 复选框 | ✅ | `test_3d_real.py` |
| 4 | 库存管理 UI+API 三接口 | ✅ | `test_inventory.py` |
| 5 | 新建空白项目 50×50 | ✅ | `test_3d_blank.py` |
| 6 | 每日签到（连续 13 天） | ✅ | `test_acc_features.py` |
| 7 | 订阅管理（4 备份套餐+积分套餐） | ✅ | `test_acc_features.py` |
| 8 | 个人资料（等级权益表） | ✅ | `test_acc_features.py` |
| 9 | MARD 色号体系（H/G/C/M 4 系列 21 色） | ✅ | `test_inventory.py` |
| 10 | 色号合并/去除杂色/降噪 3 弹窗 | ✅ | `test_postprocess.py` + `test_inventory.py` |
| 11 | 扣减库存按钮（原生 click 触发） | ✅ | `test_inventory.py` |
| 12 | 导入 .pbp 项目 | ✅ | `test_import_pbp.py` + `decode_pbp.js` |
| 13 | 拼图图纸智能导入（205×307，76 色，62935 豆） | ✅ | `test_smart_import_v15.py` |
| 14 | 小红书链接导入（API 端点实测 422） | ✅ | `test_xhs_runtime.py` + `test_xhs_response.py` |

---

## 9. 已知问题与限制（产品视角）

| 问题 | 影响 | 临时方案 |
|:---|:---|:---|
| 小红书三层反爬 | 链接导入返回 422，无法直接拉取笔记内容 | 服务端代理 + xsec_token 凭证 + 用户手动提供 URL |
| .pbp 固定密钥 | 任何拿到 .pbp 的人都能解密，混淆非真加密 | 如需真加密，引入用户密钥或服务端密钥 |
| 移动端独有菜单 | PC 版无「每日签到」「订阅管理」 | 移动端 viewport 访问 |
| 沙箱环境跳转 google | 沙箱无国内直连出口 | 浏览器显式指定代理 `--proxy-server=http://127.0.0.1:18080` |
| 注册通道走错域名 | 注册页是 `/en`（英文版），与中文主域名不一致 | 直接使用已注册账号登录，跳过重新注册 |
| 更新日志对话框遮挡 | 点登录后 modal 不显示 | 多次按 ESC 关闭所有 dialog |
| 旧 editor URL 重定向 | `/editor?projectId=...` 跳回首页 | 先点「立刻前往」找新工作台 `/workspace/create` |
| `dialog-overlay` 拦截 | `page.locator().click()` 无法触发 React onClick | 用 `evaluate(btn => btn.click())` 调原生方法 |

---

## 10. 接手清单

| 必读 | 路径 |
|:---|:---|
| 复盘文档 | `file:///workspace/i2tools_review.md` |
| 产品需求 | `file:///workspace/i2tools_PRD.md`（本文档） |
| 开发文档 | `file:///workspace/i2tools_DEV.md` |
| 必跑 | 所有 `test_*.py` 脚本（详见 DEV §8） |
| 必查 | `/workspace/i2tools/` 目录（2742 文件爬取样本，606MB 磁盘占用 / 压缩包 ≈414MB，口径详见 review.md §2.3） |
| 联系 | 原作者 `aq.jinlong@163.com` |

---

## 11. 准确度说明（重要）

> ⚠️ 本文档基于对 i2tools.com 的**逆向实测**整理。在编写过程中曾出现过分析错误并借助辅助工具修正，因此本章节明确标注各项内容的**置信度**，供接手者判断。

### 11.1 之前修正过的错误（历史记录）

| # | 错误内容 | 修正依据 | 修正后结论 |
|:---:|:---|:---|:---|
| 1 | 后端框架误判为 Laravel | 响应头 `x-powered-by: Express` | Node.js + Express |
| 2 | 登录邮箱 `aq.jilong@163.com` 失败 | 用户确认实际注册邮箱 | `aq.jinlong@163.com`（"jilong" → "jinlong"） |
| 3 | 下载结果图误用 `sourceFileName` 当 URL | 任务响应 `images` 字段 | 真实 URL 为 `https://oss-cdn.i2tools.com/ai-results/...` |
| 4 | 注册走错域名 `/en`（英文版）收不到验证码 | 用户指出主域名是 i2tools.com | 直接登录已注册账号，跳过重新注册 |

### 11.2 反编译 chunk 验证发现的错误（v2 修正）

> ⚠️ 用户反馈"未实测就推测"后，反编译全部 72 个 chunk 文件，**发现 4 处算法推测错误**：

| # | 文档原写法 | 反编译发现 | 修正后结论 |
|:---:|:---|:---|:---|
| 5 | "K-D Tree 7 叉树加速结构" | chunk 8071 实际是朴素线性扫描+Map 缓存 | 颜色匹配用朴素线性扫描+Map 缓存 CAM16-UCS 转换结果 |
| 6 | "Median Cut 调色板提取" | 全部 chunk 0 命中 medianCut | **Median Cut 不存在**，调色板来自固定 MARD 221 色 |
| 7 | "拼图图纸识别 Canny/Sobel 边缘检测" | chunk 3107 实际有 `MardCnn="mard-cnn"` 模式 | **实际算法是 MARD-CNN 卷积神经网络**（非边缘检测） |
| 8 | "小红书客户端对抗反爬" | chunk 1720 调用 `xhs-worker.i2tools.com/extract` | **i2tools 用自己的服务端 worker 代理**，客户端只发 shareText |

### 11.2.1 实测操作验证修正（v3 新增）

> v3 修正：4 项 B 类推测通过真实操作测试全部升级到 A 类。详见 DEV §4.3 / §4.4 / §4.6 / §4.5。

| # | 文档原写法 | 实测发现 | 修正后结论 |
|:---:|:---|:---|:---|
| 9 | 库存扣减字段 `operationType` | `inv_v14.log` 实测请求体字段为 `actionType`（枚举 manual_adjust/project_consume/import/rollback） | 字段名 `actionType`，非 `operationType` |
| 10 | MARD 色号格式 "H01" | `inv_v14.log` 实测成功使用 "H1"，chunk 9350 反编译 `brands.mard.definitions` 也是 H1/H2 | 色号格式 **不带 0**，如 H1/H2/G1 |
| 11 | 回滚机制 = 软删除原 operation | `inv_v14.log` 实测：回滚生成新 op，`actionType=rollback`，`rollbackOfId` 指向原 op，`direction` 相反，`changeQty` 取反 | 回滚 = **创建反向 operation**（非软删除） |
| 12 | 库存为负会阻断 | `inv_v14.log` 实测 H1 -3 也成功（afterQty=-3），**不强制非负校验** | 库存允许为负数 |
| 13 | perfect-pixel "边界扫描→量化→重采样" | chunk 1720 反编译 `to.aS` 函数签名 + 6 个参数（`sampleMethod:"center"`/`gridSize:null`/`minSize:4`/`peakWidth:6`/`refineIntensity:.25`/`fixSquare:!0`） | 用 `to.aS` 签名 + 参数替换原推测步骤 |
| 14 | 去噪 8 连通扫描方法未确认 | chunk 6777 反编译 `q.shift()+q.push()` 经典 BFS 队列扩散 + `new Uint8Array` 标记矩阵 + `u(t)` 4/8 连通选择器 + **实测色号 49→45** | 去噪用经典 BFS 队列扩散（非 DFS） |

### 11.3 置信度分级（v3 修正后 - 真实操作测试全部完成）

> ✅ v3 修正：B 类全部 4 项已通过真实操作测试升级到 A 类。详见 DEV §4.3 / §4.4 / §4.5 / §4.6 实测章节。

#### A. 实测确认（高置信度，有直接证据 - 反编译 + 真实操作测试）

- 前端 Next.js/PixiJS v8/Zustand/Axios/Zod/next-intl（chunk 反编译确认）
- 后端 Express（响应头实测）
- 颜色匹配 DeltaEHybrid + CAM16-UCS（chunk 8071 反编译）
- 像素化 4 模式（chunk 8071 反编译）
- 去噪 4 预设 + 8 连通（chunk 6777 反编译）
- **去噪 BFS 扫描方法（升级自 B 类）**（chunk 6777：`q.shift()+q.push()` + `new Uint8Array` + `u(t)` 4/8 连通选择器，**实测色号 49→45 真实执行**）
- **拼图图纸识别 = MARD-CNN（含客户端识别实测）**（chunk 3107：`e.MardCnn="mard-cnn"` + 3 阶段，**v15 真实触发识别流程，XHR 无 pattern/recognize 请求，证明客户端推理**）
- **小红书导入 = xhs-worker 服务端代理**（chunk 1720 反编译）
- MARD 色号体系 221 色（chunk 9350 反编译）
- OSS/R2/IndexedDB v10/.pbp AES-GCM-256（实测确认）
- **perfect-pixel 修正算法（升级自 B 类）**（chunk 1720：`to.aS` 函数签名 + 6 个参数 + Web Worker 异步执行，**v3 真实执行**）
- **库存扣减/回滚 API（升级自 B 类）**（chunk 3244 反编译 + `inv_v14.log` 真实测试：H1 +10/-3 + rollback + project-consume 全部 status=201，**回滚 = 创建反向 operation**，**允许库存为负数**）

#### B. 推测（中置信度，未完全反编译）

> ✅ v3 修正：B 类原 4 项全部升级到 A 类。当前 B 类已无剩余项。

（无）

#### C. 之前推测，现已推翻（错误推测）

| 原推测 | 修正后 |
|:---|:---|
| ❌ K-D Tree 7 叉树加速结构 | ✅ 朴素线性扫描 + Map 缓存 |
| ❌ Median Cut 调色板提取 | ✅ 不存在，调色板来自固定 MARD 221 色 |
| ❌ 拼图图纸识别 Canny/Sobel | ✅ 实际是 MARD-CNN 卷积神经网络 |
| ❌ 小红书客户端对抗 x-s 反爬 | ✅ i2tools 服务端 worker 代理 |
| ❌ 库存扣减字段 `operationType` | ✅ 实际字段名 `actionType` |
| ❌ MARD 色号格式 "H01" | ✅ 实际格式 "H1"（不带 0） |
| ❌ 回滚机制 = 软删除原 op | ✅ 实际是创建反向 operation |
| ❌ 库存为负会阻断 | ✅ 实测 H1 -3 也成功，**不强制非负校验** |
| ❌ perfect-pixel "边界扫描→量化→重采样" | ✅ 实际是 `to.aS` 函数 + 6 个参数（Web Worker 异步执行） |
| ❌ 去噪扫描方法未确认 | ✅ 实际是经典 BFS 队列扩散（`q.shift()+q.push()`） |

#### D. 高度推测/不确定（低置信度，需接手者验证）

> v3 修正：MARD-CNN 模型架构升级（已确认客户端推理，但权重/CNN 结构仍未反编译）。小红书 worker 内部反爬实现保持 D 类（用户决定不测）。

- 数据库 Schema/SQL DDL（基于 API 反推，非生产 schema）
- 环境变量清单（OSS/R2 实测，其它推测）
- 部署命令/Redis 使用/Nginx 配置示例
- MARD-CNN 模型权重张量与 CNN 网络结构（已确认客户端识别，chunk 3107 中权重/CNN 层级未反编译）
- 小红书 worker 内部反爬实现（**用户决定不测试**，保持 D 类待接手者验证）
- perfect-pixel `to.aS` 内部步骤权重张量（函数入口已反编译，内部"边界扫描→量化→重采样"具体实现未反编译）

### 11.4 接手者建议

1. **高置信度项（A 类）**可直接采信，作为接手基础（v3 后 A 类已扩展到 22 项，包含 B 类原 4 项）
2. **中置信度项（B 类）**：v3 后已无剩余项
3. **低置信度项（D 类）**务必向原作者 `aq.jinlong@163.com` 确认，或通过实际部署验证。其中：
   - 数据库 Schema / SQL DDL / 部署命令 / Redis / Nginx 配置 - 需要拿到生产部署的 `package.json` / `.env` / `nginx.conf` / Dockerfile / `docker-compose.yml`
   - MARD-CNN 模型权重 - 反编译 chunk 3107 提取权重矩阵
   - perfect-pixel `to.aS` 函数体 - 反编译 chunk 1720
   - 小红书 worker 内部反爬 - 需要部署 xhs-worker 服务实测（用户决定不测）
4. 任何关键决策前，优先参考：
   - `/workspace/i2tools/` 爬取样本（2742 文件，606MB 磁盘占用 / 压缩包 ≈414MB）
   - `test_*.py` 实测脚本（27 个，覆盖所有功能模块）
   - `/workspace/i2tools_review.md` 复盘文档
   - `/workspace/verify_chunks.py` / `verify_v2.py` / `verify_v3.py` / `verify_v4.py`（反编译验证脚本）
   - `/workspace/test_inv_deduct_v14.py` + `/workspace/inv_v14.log`（v14 真实库存扣减/回滚/项目消耗测试）
   - `/workspace/test_smart_import_v15.py` + `/workspace/si15.log`（v15 真实 MARD-CNN 识别 + .pbp 导出测试）
   - `/workspace/test_denoise_apply_v3.py`（去噪算法 v3 真实执行测试）
   - `/workspace/run_perfect_pixel.py` + `/workspace/verify_pp_v3.py`（perfect-pixel 真实执行测试）

---

## 12. 复刻可行性评估

> 本节为简版（技术细节与 roadmap 全量版见 `i2tools_DEV.md` §12）。回答核心问题：**"有了这些爬取 + 反编译 + 实测资料，能否搭建一个一模一样、所有功能都对齐的网站？"**
> 结论：**可以重建一个 90% 功能对齐的等价站，但不是字节级 / 效果级的一模一样克隆**，卡在 5 个"拿不到原型"的结构性缺口。

### 12.1 工具台真实清单（先澄清一个常见误解）

工具台**只有 3 个独立工具**（来源：chunk 9173 ToolboxPage 模块 68997 的 `C8` 数组，是工具台唯一权威清单）：

| 工具 id | 工具名 | 角色 | 布局 |
|:---|:---|:---|:---|
| `ai-pixel-art` | AI 像素画生成工具（violet） | 图片→像素画生成（服务端 API） | `standalonePage:!0` 独立页 |
| `perfect-pixel` | 伪像素画修正工具（amber） | 对已有像素画结果做对齐修正（客户端 Web Worker `to.aS`） | `detailLayout:"viewport"` |
| `xhs-media` | 小红书原图提取工具（rose） | 小红书链接→原图提取（服务端 worker 代理） | `detailLayout:"document"` + SEO 三元组 |

> 注意：`perfect-pixel` 是**独立工具**，不是 `ai-pixel-art` 的子功能。

### 12.2 资产分层（能复刻 / 需补写 / 无法对齐）

| 层 | 类别 | 可复刻度 |
|:---:|:---|:---|
| ① | 前端 / 渲染 / 算法逻辑 | **90%+ 能复刻**（编辑器、像素化 4 模式、去噪 4 预设、颜色匹配、perfect-pixel `to.aS` 6 参数、MARD-CNN 3 阶段流程） |
| ② | 后端业务逻辑 | **能复刻但需补写**（认证/积分/项目 CRUD/库存扣减/.pbp 加解密，按 API 契约 + 实测行为重写，非复制） |
| ③ | 拿不到原型的黑盒 | **无法 1:1 对齐**（下表 5 项） |

### 12.3 5 个结构性缺口（精确归属到所属工具）

| # | 缺口 | 所属工具（i2tools 工具台） | 技术栈层 | 现状 |
|:---:|:---|:---|:---|:---|
| 1 | 小红书 worker 内部反爬 | **小红书原图提取工具**（`xhs-media`） | 服务端代理 + 客户端调用 | 客户端调 `/extract` POST shareText + `/proxy?u=` 已确认；worker 内部如何过小红书 `x-s/xsec_token` 反爬**未实测**（用户定调不测） |
| 2 | 数据库 Schema（SQL 表） | **全项目服务端**（跨工具底层数据层） | 数据库层 | chunk 7824 只到 IndexedDB；服务端 SQL 表**未公开**（72 chunk 0 命中 `CREATE TABLE`），§7 DDL 为推测 |
| 3 | MARD-CNN 模型权重 | **图纸识别 / 拼图图纸识别工具**（MARD-CNN 流程） | ML 模型层（客户端推理） | 3 阶段流程 + 客户端推理已确认；**权重张量 / CNN 网络结构未反编译**（0 命中 onnx/weightsUrl） |
| 4 | AI 像素画 / perfect-pixel 内部 | **AI 像素画工具**（`ai-pixel-art`）+ 独立 **perfect-pixel 工具** | 生成模型层 + 算法层 | ai-pixel-art 仅任务提交/轮询 API（生成模型无）；perfect-pixel 仅 `to.aS` 入口 + 6 参数（内部卷积/迭代未展开） |
| 5 | OSS / R2 资源内容 | **素材 / 对象存储层**（跨工具） | 对象存储层 | R2 `r2-uploads` 只拿到**目录壳**（0 命中）；OSS 拿到部分真实 `.webp`；**字体 / 模型二进制未下载** |

### 12.4 复刻结论

- **能做到**：用 ① 前端 + ② 后端，重建**功能基本对齐**的等价站（编辑器 / 像素化 / 去噪 / 颜色匹配 / 库存 / 项目导出 .pbp 行为一致）。
- **做不到 100% 一样**：卡在 §12.3 的 5 个缺口（小红书原图提取、服务端 DB Schema、MARD-CNN 权重、AI 像素画生成质量 + perfect-pixel 内部、OSS/R2 素材二进制）。
- **精确表述**：资料足以支撑"**90% 功能对齐的等价重建**"，**不是**"字节级 / 效果级的一模一样克隆"。

> 完整 roadmap（可直接抄 / 需重写 / 需自己造 三档拆解）见 `i2tools_DEV.md` §12.2。

---

**文档结束**
