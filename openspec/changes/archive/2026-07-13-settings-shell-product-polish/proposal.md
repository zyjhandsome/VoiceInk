## Why

设置窗口在落地「经典桌面工具」气质后显得平、空、控件廉价，用户观感偏 Low。需要在**不推翻经典冷灰中性轴**的前提下抬升工艺，并为设置壳增加可感知的「产品感」表面层次，先改善每日最高频的设置界面。

## What Changes

- 抬升设置壳视觉工艺：侧栏、页头、分区节奏、分组容器、触发方式卡、快捷键区、底栏的层级与间距。
- 允许设置壳使用更明确的产品感表面（白底分组容器、清晰选中态、受控的浅层深度/分隔），但仍遵循蓝限用（主 CTA + 选中强调）。
- 同步必要的 `design_tokens` / QSS / 组件样式与相关 UI 契约测试。
- **不**改设置项语义、配置读写、信息架构（四页仍为：通用 / 模型 / 润色 / 关于）。
- **不**在本变更内重做浮窗、历史窗、托盘菜单气质（共享 token 变更须保持这些表面不回归、不明显跑偏）。

## Capabilities

### New Capabilities

- `settings-shell-visual-polish`: 设置窗口外壳与通用页关键容器的可观察视觉/交互质感（选中态、分区层次、焦点可读性），不含配置行为变更。

### Modified Capabilities

- （无）`openspec/specs/` 当前无既有能力规格可改。

## Impact

- 代码：`voiceink/ui/design_tokens.py`、`settings_styles.py`、`settings_components.py`、`settings_window.py`；必要时极小触达 `nav_icons.py` / `app_styles.py`。
- 测试：`tests/test_ui_styles.py`、`tests/test_settings_general.py`（及因样式契约变动的相关断言）。
- 行为契约：设置仍即时生效；快捷键/触发/音频等功能文案与配置键不变。
- 工作区注意：已有未提交的设置 UI 微调与大量无关文档删除；本变更只吸收对齐目标的 UI 改动，**不得**把无关删除纳入本变更范围。
