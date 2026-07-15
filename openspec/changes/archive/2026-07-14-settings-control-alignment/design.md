## Context

设置页已有 `design_tokens`、`settings_styles.WINDOW_CSS` 与 `labeled_row` / `ToggleOptionRow` 组件体系。历史区两个 `QSpinBox` 未设固定宽度、未写 QSS，Qt 按内容自适应导致宽度不一致；`SettingsPage` 使用 `ScrollBarAlwaysOn` 常占右缘。

## Goals / Non-Goals

**Goals:**

- 历史「保留天数」「最大会话数」两框等宽、等高，视觉纳入输入控件体系
- 右侧控件（开关与数值框）右缘对齐
- 设置页垂直滚动条按需出现

**Non-Goals:**

- 不改导航、主题色、触发方式/音频来源卡片布局
- 不缩短页脚脚注、不做折叠分组
- 不引入新依赖或改配置语义

## Decisions

1. **固定宽度 token，而非随最大值动态算宽**  
   - 选用：在 `design_tokens` 增加 `CONTROL_NUMERIC_WIDTH`（约 120px），两 spin `setFixedWidth`。  
   - 备选：按 `sizeHint` 取较大者 — 更复杂且字体变化时仍可能漂移。  
   - 理由：两处最大值已知（3650 / 100000），固定宽足够且稳定。

2. **QSpinBox 样式放进 `WINDOW_CSS`**  
   - 与 `QLineEdit`/`QComboBox` 同边框、圆角、focus 环；上下按钮保持紧凑。  
   - 不单独做自定义 paint 控件。

3. **右缘对齐靠统一右边距**  
   - `labeled_row` 右边距与 `ToggleOptionRow` 一致（16px）；spin 固定宽后右缘自然重合。  
   - 不引入额外「控件槽」widget，除非实测仍错位。

4. **滚动条 `ScrollBarAsNeeded`**  
   - 仅改 `SettingsPage` 垂直策略；水平仍关闭。

## Risks / Trade-offs

- [大数字 + 后缀在窄框被裁切] → Mitigation：宽度按 `99999 场` 预留；必要时微调 token 到 128px  
- [QSS 在 Windows 原生 spin 按钮上细节偏差] → Mitigation：保持简单边框样式，不强制重绘箭头  
- [仅设置页改滚动条，历史窗仍 Always 行为] → 可接受；历史窗列表本身需要滚动

## Migration Plan

纯 UI；无数据迁移。回滚即还原上述文件。

## Open Questions

无。
