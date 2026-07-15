## 1. Tokens & styles

- [x] 1.1 在 `design_tokens.py` 增加 `CONTROL_NUMERIC_WIDTH`（约 120px）
- [x] 1.2 在 `settings_styles.WINDOW_CSS` 增加 `QSpinBox` 样式（边框、圆角、高度、focus）

## 2. Controls & layout

- [x] 2.1 历史区两个 `QSpinBox` 使用 `CONTROL_NUMERIC_WIDTH` 固定宽度
- [x] 2.2 确认 `labeled_row` 与 `ToggleOptionRow` 右边距一致（必要时微调）
- [x] 2.3 `SettingsPage` 垂直滚动条改为 `ScrollBarAsNeeded`

## 3. Verify

- [x] 3.1 更新或补充 `tests/test_ui_styles.py`（若可断言宽度/滚动策略/QSS 片段）
- [x] 3.2 运行相关 UI 测试并通过
