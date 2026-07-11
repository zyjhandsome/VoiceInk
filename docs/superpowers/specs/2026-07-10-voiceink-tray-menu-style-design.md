# VoiceInk 托盘右键菜单 · 参考图风格优化 — 设计文档

> 日期: 2026-07-10  
> 状态: 已确认  
> 关联: [UI Stitch 对齐设计](2026-07-10-voiceink-ui-stitch-alignment-design.md) §5.7（本文件覆盖其中托盘菜单视觉结论）  
> 参考: 用户提供的桌面工具右键菜单截图（通栏分隔、左侧 ✓、右侧 ›、浅灰悬停）

## 1. 目标与非目标

### 目标

将托盘图标右键菜单的**视觉与分组节奏**对齐参考图风格：白底、小圆角、通栏细分隔、浅灰悬停、左侧勾选、右侧子菜单箭头；在不大改交互的前提下让菜单更像原生桌面工具。

### 非目标

- 不自绘自定义弹出面板（不用替代 `QMenu`）。
- 不增减菜单项、不改文案、不改信号语义。
- 不改设置页 / 历史窗 / 浮窗。
- 不追求与参考图像素级一致（Windows `QMenu` + QSS 有系统限制）。

## 2. 已确认决策

| 决策点 | 结论 |
|--------|------|
| 范围 | 视觉样式 + 分组微调（方案 B） |
| 视觉方向 | 参考图风格（方案 A）：小圆角、✓、浅灰悬停、通栏分隔 |
| 实现路径 | 纯 QSS 重绘现有 `QMenu`（方案 1） |
| 与 Stitch §5.7 | **覆盖**：不再使用 12px 大圆角、浅蓝悬停、蓝色圆点勾选 |

## 3. 菜单结构

自上而下，组间通栏细分隔线：

1. **状态**（禁用、灰色）— 如「就绪 · FireRedASR2」；由 `set_status_summary` 更新  
2. **打开设置** / **历史**  
3. **切换模型** ›（子菜单：已下载模型单选；空态「暂无已下载模型」）  
4. **开机自启**（可勾选；勾选时左侧 ✓）  
5. **退出**

信号保持不变：`open_settings` / `history_requested` / `model_switched` / `auto_start_toggled` / `quit_app`。

## 4. 视觉规格

| 属性 | 值 |
|------|-----|
| 背景 | `#FFFFFF` |
| 边框 | `1px solid #E0E0E0` |
| 圆角 | `4px`（菜单容器；项本身无大圆角块） |
| 阴影 | 轻阴影（QSS/`setWindowFlags` 能力范围内尽力；不强求与参考图一致） |
| 字号 | `13px`；字体沿用 `FONT` token 回退链 |
| 项内边距 | 约 `8px 18px`（垂直宽松） |
| 悬停 | 背景 `#F5F5F5`，文字保持深色（不用品牌蓝底/蓝字） |
| 禁用（状态行） | 文字 `#888888` |
| 分隔线 | `1px`、`#EEEEEE`，左右 margin 尽量小或 0，呈通栏感 |
| 勾选 | 左侧深灰 ✓（`QMenu::indicator:checked`） |
| 子菜单箭头 | 右侧 › / 系统 right-arrow，中性灰 |

可在 `design_tokens.py` 增加托盘菜单专用常量（如 `TRAY_MENU_RADIUS`、`TRAY_MENU_HOVER`、`TRAY_MENU_SEPARATOR`），由 `_menu_stylesheet()` 引用，避免魔法数散落。

## 5. 改动面

```
voiceink/ui/design_tokens.py   ← 可选：托盘菜单 token
voiceink/ui/tray_icon.py       ← _menu_stylesheet()；确认 _setup_menu() 分组
tests/test_tray_icon.py        ← 现有契约保留；必要时补分组/可勾选断言
```

**数据流 / 信号：** 无变更。

## 6. 错误处理与降级

- QSS 在部分 Windows 主题下圆角/阴影可能被忽略：菜单仍须可读、可点，功能不受影响。
- 字体缺失时回退到 Segoe UI / 微软雅黑，与全局 token 一致。

## 7. 测试与验收

- 跑 `pytest tests/test_tray_icon.py` 及相关 UI 用例；不得破坏状态项禁用、Windows 双击打开设置等契约。
- 人工验收：右键托盘对照参考图节奏（分组、通栏分隔、浅灰悬停、✓ / ›）。
- README：菜单文案无变化则不必改；若有可见文案变化则按变更审查清单更新。
- 红线：不改 `ready` / `model_load_progress` / `segment_ready` / `esc_pressed` 语义。

## 8. 实现顺序

1. （可选）补充托盘菜单 token。  
2. 重写 `_menu_stylesheet()`，子菜单共用同一套样式。  
3. 核对 `_setup_menu()` 分隔与分组。  
4. 更新/补充 `test_tray_icon`。  
5. 目视验收 + pytest。
