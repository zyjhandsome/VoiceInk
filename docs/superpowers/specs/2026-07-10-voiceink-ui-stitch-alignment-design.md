# VoiceInk UI · Stitch Desktop Pro 对齐 — 设计文档

> 日期: 2026-07-10  
> 状态: 已确认；实现进行中（`feature/ui-stitch-alignment`）  
> 参考: `stitch_voicescribe_desktop_pro/`（含 `voiceink_design_system/DESIGN.md` 与各屏 `code.html` / `screen.png`）

## 1. 目标与非目标

### 目标

将现有 PyQt6 UI 对齐 Stitch「VoiceInk Desktop Pro」的 **Modern / Corporate** 视觉语言，并在设置页、历史窗、托盘菜单上做**结构级**重组，使界面更清晰、更接近设计稿，同时不改变产品功能语义。

### 非目标

- 不像素级还原 HTML/Tailwind 稿（PyQt 无法也不必 1:1）。
- 不改 ASR / 润色 / 粘贴主链路，不改 `App._connect_signals` 四条红线信号语义。
- 不把浮窗改成浅色；不改浮窗交互与状态机。
- 不新增设置侧栏「历史」页；历史保持独立窗口。
- 不改历史存储、搜索、导出、清理等业务逻辑。

## 2. 已确认决策

| 决策点 | 结论 |
|--------|------|
| 范围 | 设置（通用/模型/润色/关于）+ 托盘菜单 + 历史窗口；浮窗仅统一部分 token |
| 对齐深度 | **结构也对齐**（方案 B）：侧栏状态卡、分区卡片、润色预览、关于 KV 表等按稿重组 |
| 实现路径 | **Token 先行 + 按页结构对齐**（方案 1） |
| 历史 | 独立窗口保留，用同一套侧栏/卡片语言重排双栏布局 |
| 浮窗 | 深色外观与逻辑保留；只共用圆角/字号等 token |

## 3. 设计 Token

以 `stitch_voicescribe_desktop_pro/.../voiceink_design_system/DESIGN.md` 为权威，落到 `voiceink/ui/design_tokens.py`（并驱动 `settings_styles.py` / 组件 QSS）。

| 角色 | 值 |
|------|-----|
| Primary | `#0050cb` |
| Primary container | `#0066ff` |
| App background | `#F5F7FA`（稿中 cool soft gray；与 surface `#fcf8f9` 同族） |
| Card / surface | `#FFFFFF` |
| Sidebar / surface-low | `#f6f3f4` / `#fcf8f9` |
| Text | `#1b1b1c` |
| Text secondary | `#424656` |
| Outline | `#727687` / variant `#c2c6d8` / card border `#E1E4E8` |
| Secondary container（导航激活底） | `#dce3f0` |
| Card radius | **12px** |
| Card shadow | `0 4px 12px rgba(0,0,0,0.05)` |
| Popover shadow | `0 8px 24px rgba(0,0,0,0.12)` |
| Sidebar width | 240–260px |
| Font UI | `Inter` → `Segoe UI` → `Microsoft YaHei UI` → system |
| Font mono | `JetBrains Mono` / `Cascadia Mono` / `Consolas`（快捷键、路径） |

语义色（成功绿 / 警告琥珀 / 错误红）仅用于状态与危险操作，不改品牌主色。

浮窗继续使用现有深色 overlay token（`FLOAT_*`）；仅将圆角、字号等与浅色体系对齐的数值统一，不强制换色。

## 4. 架构与改动面

```
design_tokens.py          ← Stitch 色板 / 圆角 / 间距 / 字体
settings_styles.py        ← WINDOW_CSS、按钮、输入、菜单 QSS
settings_components.py    ← Sidebar、PageHero、卡片、触发方式、润色预览等
settings_window.py        ← 四页信息架构微调（不改配置读写语义）
history_window.py         ← 双栏视觉重排
tray_icon.py              ← 菜单样式（蓝点勾选、分隔、间距）
floating_window.py        ← 仅 token 数值；深色与交互不动
nav_icons.py / model_card ← 颜色跟随新 token
```

**数据流 / 信号：** 无变更。设置仍即时写配置并发出现有信号；托盘仍发 `open_settings` / `history_requested` / `auto_start_toggled` / `quit_app` 等。

## 5. 界面规格

### 5.1 设置外壳

- 左：品牌行（蓝圆标 + VoiceInk）→ 状态卡（`就绪 · {模型}` / `润色已开启|已关闭`）→ 导航四项 → 底部 `Status: Idle`（或与运行态一致的简短状态）。
- 导航激活：左侧 4px 主色竖条 + `secondary-container` 底 + 主色文字/图标。
- 右：页标题（display）+ 可选副标题；内容区滚动；底栏「更改会即时生效」+「完成」。

### 5.2 通用

- **触发方式**：两张大选中卡（自动持续 / 按住快捷键），选中态蓝边 + 浅蓝底。
- 其后分区卡片顺序：快捷键 → 开机与提示音 → 历史保留相关 → 音频来源 / 检测 / 高级。
- 现有配置项与行为全部保留，仅容器与层级按稿卡片化。

### 5.3 模型

- 页头「语音识别」。
- 当前引擎高亮卡；模型列表卡（含下载线性进度）；存储路径卡。
- 下载 / 切换 / 删除逻辑不变。

### 5.4 润色

- 标题旁显示「已关闭 / 已开启」。
- 主卡：总开关 → 效果预览（转写原文灰底；润色后浅蓝底）→ 接口配置与提示词在下方分区。
- 开关与 API 配置语义不变。

### 5.5 关于

- 品牌卡 + 版本 pill。
- 快捷键使用提示条（如 Ctrl + Space）。
- 「运行信息」KV 表：当前模型、已下载、模型目录、配置文件、快捷键；路径等宽字体。

### 5.6 历史窗口（独立）

- 左：标题 + 搜索框 + 会话列表（选中：浅蓝底 + 左边条；副信息：时间 · 段数）。
- 右：会话详情白卡片 + 导出 / 删除等操作。
- `HistoryStore` API、搜索 debounce、Markdown 导出格式不变。

### 5.7 托盘菜单

- 白底、12px 圆角、轻边框 + 较高阴影。
- 分组：打开设置 / 历史 ‖ 切换模型 › ‖ 开机自启（勾选蓝点）‖ 退出。
- 菜单项文案与信号不变。

### 5.8 浮窗

- 深色条、波形、状态色逻辑保留。
- 仅统一与设计体系共享的圆角 / 字号等数值。

## 6. 错误处理与降级

- UI 重排不得引入新的阻塞路径；历史查询失败仍按现有空态 / 提示处理。
- 字体缺失时回退到 Segoe UI / 微软雅黑，不因 Inter 未安装而布局崩溃。
- 样式表拼装错误时以可读默认样式兜底（开发期通过目视 + 现有 UI 测试发现）。

## 7. 测试与验收

- 跑现有相关测试：`pytest tests/test_readme_features.py` 及 UI/历史相关用例；不得因纯视觉改动破坏契约。
- 若 README 用户可见描述（设置分区名称、托盘项）有文案级变化，按变更审查清单更新 README。
- 人工验收对照 Stitch 截图：侧栏状态卡、触发大卡、润色预览、关于 KV、托盘分组、历史双栏。
- 红线：不改 `ready` / `model_load_progress` / `segment_ready` / `esc_pressed` 语义。

## 8. 实现顺序（供 plan 拆分）

1. 更新 `design_tokens` + `settings_styles`（全局换肤）。
2. 重做 `SettingsSidebar` + 设置外壳底栏。
3. 按页：通用 → 模型 → 润色 → 关于。
4. 历史窗口双栏视觉。
5. 托盘菜单样式。
6. 浮窗 token 微调。
7. 测试 + README 审查（如有文案变化）。

## 9. 参考资产

- `stitch_voicescribe_desktop_pro/.../voiceink_design_system/DESIGN.md`
- 通用：`_2/`；润色：`_3/`；关于：`voiceink/`；托盘：`_4/`
