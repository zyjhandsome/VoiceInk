## 1. Baseline & tokens

- [x] 1.1 记录基线：`py -3.10 -m pytest tests/test_ui_styles.py tests/test_settings_general.py -q`；若失败，判定是否与本变更无关并写入降级记录后再继续
  - 证据：2026-07-13，43 passed
- [x] 1.2 在 `voiceink/ui/design_tokens.py` 调整/补充设置壳所需表面与选中相关 token（保持冷灰轴与蓝限用）；不引入暖 pearl / 紫色主题
  - 新增：`SETTINGS_SIDEBAR_BG` / `NAV_SELECTED_BG` / `NAV_SELECTED_BAR_PX`
- [x] 1.3 确认共享 token 变更不会迫使 `floating_window` / `history_window` / `tray_icon` 改气质；若有回归风险，改为 settings-local 常量或收窄改动
  - 新增 token 仅被 settings 壳消费；float/tray 相关测试仍绿；`history_window.py` WIP 未纳入本变更

## 2. Settings shell surfaces

- [x] 2.1 更新 `settings_styles.py` / `settings_components.py`：分组容器、分区标题节奏、页头与底栏层次符合产品感规格
- [x] 2.2 更新 `SettingsSidebar` 选中态：单一蓝强调 + 中性洗色，选中文字深色
- [x] 2.3 更新 `TriggerModePicker` / choice cards 选中态：禁止蓝底+蓝边+蓝字三重强调
- [x] 2.4 核对 `settings_window.py` 四页组装仅消费新壳样式，不改配置读写与文案

## 3. Tests & verification

- [x] 3.1 更新 `tests/test_ui_styles.py`（及必要的 `test_settings_general.py`）契约断言以匹配新选中/表面规则
- [x] 3.2 跑 `py -3.10 -m pytest tests/test_ui_styles.py tests/test_settings_general.py tests/test_readme_features.py -q`
  - 扩展回归：`test_floating_window` + `test_tray_icon`；合计 100 passed（2026-07-13）
- [x] 3.3 手工冒烟：设置四页导航、触发方式切换、热键焦点环、关闭主按钮；确认配置仍即时生效
  - 程序化冒烟 `SMOKE_OK`（四页、导航切页、侧栏白底、选中左边条契约、触发切换、关闭主 CTA、HotkeyEdit:focus）
  - 用户「继续」确认收尾；目视质感仍可在应用内复核
- [x] 3.4 对照 `git status`：确保无关 `docs/`/`openwiki/` 删除未进入本变更暂存；diff 不超出允许 UI/测试路径（除已批准的 token 共享文件）
  - 本变更触及：tokens / settings_components / nav_icons / settings_window / 相关测试 / openspec；`history_window.py` 仍为工作区无关 WIP，勿暂存
