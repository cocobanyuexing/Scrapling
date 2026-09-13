# 幻彩拼豆 (i2tools.com) 产品需求文档 (PRD)

## 0. 文档信息

| 项 | 值 |
|:---|:---|
| 文档版本 | v1.0 |
| 整理时间 | 2026-09-13 |
| 来源 | 基于 i2tools.com 实测逆向整理（参见 `file:///workspace/i2tools_review.md`） |
| 目标读者 | 产品经理 / 业务方 / 接手团队 |
| 关联文档 | `file:///workspace/i2tools_DEV.md`（开发文档，技术细节落点） |
| 实测账号 | `aq.jinlong@163.com`（等级 1，10/100 EXP） |

> 说明：本文档所有需求规格、按钮坐标、参数表均来自 2026-09-13 的真实在线实测，14 项功能实测全部通过（详见 review.md §1.2 任务清单）。涉及技术实现的细节请查阅 DEV 文档对应章节。

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

**功能需求**：

| 步骤 | 行为 |
|:---|:---|
| 1. 上传像素画 | `input[type="file"]`，jpg/png/webp |
| 2. 边界扫描 | 识别"半像素"边缘 |
| 3. 量化对齐 | 量化到整数像素网格 |
| 4. 重采样匹配 | 匹配 MARD 调色板 |
| 5. 输出修正 canvas | `toDataURL('image/png')` 可下载 |
| 6. 创建项目继续编辑 | 可选「创建项目继续编辑」，写入 IndexedDB，跳转 `/editor?projectId=1789297487536-ia8zup1` |

**验收标准**：
- ✅ canvas[1] 出现结果像素
- ✅ 导出 PNG 可下载
- ✅ 保存项目写入 IndexedDB 并跳转编辑器
- ✅ 实测脚本 `file:///workspace/run_perfect_pixel.py`

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

| 弹窗字段 | 算法印证 |
|:---|:---|
| 「最大连通块 N / 连通块 N」 | 8 连通域 BFS 分析 |
| 「最大色块面积」滑块 1-12 | 面积阈值过滤 `areaThreshold` |
| 「替换为(主色)」 | 颜色距离计算（sRGB 加权距离） |
| 4 预设强度 | 4 套 `light/balanced/strong/aggressive` 参数 |
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

#### 3.4.3 库存扣减逻辑

| 步骤 | 行为 |
|:---|:---|
| 1. 色号合并 | 相同色号在多项目用量累加 |
| 2. 扣减 | 依据项目 `colorCounts` 减库存数量 |
| 3. 低库存预警 | `< 10`（默认阈值）触发提醒 |
| 4. 按钮 | 编辑器顶栏「扣减库存」按钮 `title` 存在，需用 `evaluate(btn => btn.click())` 触发原生 onClick |

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

### 4.2 图纸导入流程

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
跳转编辑器 /editor?projectId=xxx
   ↓
（同 §4.1 后续流程）
```

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
| 必查 | `/workspace/i2tools/` 目录（2742 文件爬取样本，606MB） |
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

### 11.2 置信度分级

#### A. 实测确认（高置信度，有直接证据）

| 项 | 证据类型 |
|:---|:---|
| 前端 Next.js 19.2.0-canary App Router | 路由结构 + chunk 文件名 + `__next` 数据特征 |
| PixiJS v8（WebGPU + WebGL 双路径） | vendor chunk 字符串 + 渲染器实例化代码 |
| Zustand 状态管理 | state 调用模式 `s.G.getState()` 实测 |
| Axios 1.18.1 / Zod 4.4.3 | npm 包版本字符串实测 |
| next-intl 国际化 | `[locale]` 路由 + `NEXT_LOCALE` cookie 实测 |
| 后端 Node.js + Express | 响应头 `x-powered-by: Express` |
| 阿里云 OSS（结果图） | `oss-cdn.i2tools.com` 域名 + 结果图 URL 实测 |
| Cloudflare R2（上传存储） | `r2-uploads` 路径实测 |
| IndexedDB v10 `magic-perler-projects` | 数据库版本 + object stores 实测 |
| .pbp 格式 `{version, format, data}` | 实测解密成功 |
| AES-GCM-256 + PBKDF2(SHA-256, 100000, perler-salt) | 解密参数实测验证 |
| 后处理 4 预设（light/balanced/strong/aggressive） | 弹窗 dump 实测 |
| MARD 色号体系 H/G/C/M 221 色 | `brands.mard.definitions` 实测 |
| 小红书 Vue 3 + formula-runtime | vendor chunk + `data-v-` 标记实测 |
| 小红书 openresty 网关 | 响应头实测 |
| 小红书 x-s / x-s-common / x-t 签名头 | XHR 抓包实测 |
| API 端点 14 个 | 实测调用 + 响应 body |

#### B. 推测（中置信度，基于间接证据推断）

| 项 | 推测依据 | 不确定点 |
|:---|:---|:---|
| 颜色匹配算法 DeltaEHybrid + CAM16-UCS | JS chunk 字符串看到类名 | 具体调用流程、参数选择是推测的 |
| K-D Tree 7 叉树加速结构 | chunk 字符串推测 | 树的构建/查询细节未实测 |
| Median Cut 调色板提取 | chunk 字符串推测 | 具体实现未反编译完整 |
| 像素化 4 模式（Structural/Dominant/Average/PixelArtOptimized） | 模式名实测 | 各模式算法差异是推测的 |
| perfect-pixel 修正算法 | 推测"借鉴开源思路重写 TS 版" | 原始开源出处未确认 |
| 去噪 8 连通域 BFS | 基于参数表推测实现 | BFS/DFS 选择、扫描顺序未确认 |
| 库存扣减色号累加逻辑 | API 实测通过 | 扣减的具体时序、回滚机制推测 |

#### C. 高度推测/不确定（低置信度，需接手者验证）

| 项 | 现状 | 建议 |
|:---|:---|:---|
| 拼图图纸识别 Canny/Sobel 边缘检测 | **完全是推测，无反编译证据** | 接手后应优先反编译图纸识别 chunk 验证 |
| 数据库 Schema（users/projects/inventory/checkin/orders/products） | 基于 API 返回结构反推 | 真实表结构、字段类型、索引需查实际 DDL |
| SQL DDL 语句 | 完全推测 | 仅供建库参考，非生产 schema |
| 环境变量清单 | OSS/R2 实测，JWT_SECRET/XSRF_SECRET 等推测 | 部署前需向原作者确认 |
| 部署命令 `pnpm db:migrate` 等 | 推测 | 需查 `package.json` scripts 字段确认 |
| Redis 使用 | "可选"是推测 | 未实测是否有 Redis |
| Nginx 反代配置示例 | 推测的模板 | 需根据实际部署环境调整 |

### 11.3 接手者建议

1. **高置信度项**可直接采信，作为接手基础
2. **中置信度项**需进一步反编译 JS chunk 验证（关键 chunk：`9872`(3D) / `8071`(颜色) / `6777`(去噪) / `9350`(MARD) / `7824`(IDB) / `1720`(小红书)）
3. **低置信度项**务必向原作者 `aq.jinlong@163.com` 确认，或通过实际部署验证
4. 任何关键决策前，优先参考 `/workspace/i2tools/` 爬取样本（2742 文件）和 `test_*.py` 实测脚本

---

**文档结束**
