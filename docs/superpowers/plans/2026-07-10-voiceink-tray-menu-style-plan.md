# Tray Menu Reference Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the VoiceInk tray context menu to match the reference desktop-utility look (small radius, full-bleed separators, light-gray hover, left ✓) while keeping menu items and signals unchanged.

**Architecture:** Keep `QSystemTrayIcon` + `QMenu`. Add tray-specific tokens in `design_tokens.py`, rewrite `_menu_stylesheet()` in `tray_icon.py`, and lock the look + grouping with stylesheet/structure tests. No custom popup widget.

**Tech Stack:** Python 3.10+, PyQt6, pytest

**Spec:** `docs/superpowers/specs/2026-07-10-voiceink-tray-menu-style-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `voiceink/ui/design_tokens.py` | Tray menu tokens (`TRAY_MENU_*`) |
| `voiceink/ui/tray_icon.py` | `_menu_stylesheet()` + menu grouping |
| `tests/test_tray_icon.py` | Structure + stylesheet contract tests |

---

### Task 1: Failing tests for tray menu style + grouping

**Files:**
- Modify: `tests/test_tray_icon.py`
- Test: `tests/test_tray_icon.py`

- [x] **Step 1: Write the failing tests**

Append to `tests/test_tray_icon.py`:

```python
class TestTrayMenuStyleAndGrouping:
    def test_menu_stylesheet_uses_reference_style_tokens(self, tray):
        from voiceink.ui import design_tokens as t

        css = tray.contextMenu().styleSheet()
        assert t.TRAY_MENU_RADIUS == 4
        assert f"border-radius: {t.TRAY_MENU_RADIUS}px" in css
        assert t.TRAY_MENU_HOVER in css
        assert t.TRAY_MENU_SEPARATOR in css
        assert t.TRAY_MENU_BORDER in css
        assert "font-size: 13px" in css
        # No Stitch tray look leftovers
        assert "rgba(0, 80, 203" not in css
        assert "border-radius: 12px" not in css
        assert "border-radius: 8px" not in css

    def test_menu_groups_match_spec_order(self, tray):
        actions = tray.contextMenu().actions()
        # QMenu separators are actions with isSeparator()
        labels = []
        for a in actions:
            if a.isSeparator():
                labels.append("---")
            else:
                labels.append(a.text())

        assert labels[0]  # status (dynamic)
        assert not actions[0].isEnabled()
        assert labels[1] == "---"
        assert labels[2] == "打开设置"
        assert labels[3] == "历史"
        assert labels[4] == "---"
        assert labels[5] == "切换模型"
        assert labels[6] == "---"
        assert labels[7] == "开机自启"
        assert actions[7].isCheckable()
        assert labels[8] == "---"
        assert labels[9] == "退出"
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tray_icon.py::TestTrayMenuStyleAndGrouping -v`

Expected: FAIL (missing `TRAY_MENU_*` tokens and/or old stylesheet still has 12px / accent soft)

- [ ] **Step 3: Commit** (only if user requested commits; otherwise skip)

---

### Task 2: Tray menu tokens + stylesheet

**Files:**
- Modify: `voiceink/ui/design_tokens.py`
- Modify: `voiceink/ui/tray_icon.py`
- Test: `tests/test_tray_icon.py`

- [x] **Step 1: Add tokens at end of `design_tokens.py` (before or after float tokens block is fine; append after shape section or at file end)**

```python
# Tray context menu — reference desktop-utility style
TRAY_MENU_RADIUS = 4
TRAY_MENU_BORDER = "#E0E0E0"
TRAY_MENU_SEPARATOR = "#EEEEEE"
TRAY_MENU_HOVER = "#F5F5F5"
TRAY_MENU_DISABLED = "#888888"
TRAY_MENU_CHECK = "#333333"
TRAY_MENU_ARROW = "#999999"
TRAY_MENU_PAD_V = 8
TRAY_MENU_PAD_H = 18
```

- [x] **Step 2: Rewrite `_menu_stylesheet()` and update imports in `tray_icon.py`**

Replace the token imports and `_menu_stylesheet` with:

```python
from voiceink.ui.design_tokens import (
    ACCENT,
    ACCENT_FOCUS,
    FONT,
    SURFACE,
    TEXT,
    TRAY_MENU_ARROW,
    TRAY_MENU_BORDER,
    TRAY_MENU_CHECK,
    TRAY_MENU_DISABLED,
    TRAY_MENU_HOVER,
    TRAY_MENU_PAD_H,
    TRAY_MENU_PAD_V,
    TRAY_MENU_RADIUS,
    TRAY_MENU_SEPARATOR,
)


def _menu_stylesheet() -> str:
    return f"""
    QMenu {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {TRAY_MENU_BORDER};
        border-radius: {TRAY_MENU_RADIUS}px;
        padding: 4px 0px;
        font-family: {FONT};
        font-size: 13px;
    }}
    QMenu::item {{
        padding: {TRAY_MENU_PAD_V}px {TRAY_MENU_PAD_H}px {TRAY_MENU_PAD_V}px {TRAY_MENU_PAD_H}px;
        margin: 0px;
        border-radius: 0px;
        background: transparent;
    }}
    QMenu::item:selected {{
        background-color: {TRAY_MENU_HOVER};
        color: {TEXT};
    }}
    QMenu::item:disabled {{
        color: {TRAY_MENU_DISABLED};
        background: transparent;
    }}
    QMenu::separator {{
        height: 1px;
        background: {TRAY_MENU_SEPARATOR};
        margin: 2px 0px;
    }}
    QMenu::indicator {{
        width: 14px;
        height: 14px;
        margin-left: 4px;
    }}
    QMenu::indicator:non-exclusive:checked,
    QMenu::indicator:exclusive:checked {{
        /* Qt draws check; color hint via image optional — keep space for ✓ */
    }}
    QMenu::right-arrow {{
        width: 10px;
        height: 10px;
        margin-right: 10px;
    }}
    """
```

Note: Keep `ACCENT` / `ACCENT_FOCUS` imports if still used by `create_microphone_icon`. Remove unused `ACCENT_SOFT`, `HAIRLINE`, `RADIUS_MD`, `TEXT_DIM` if no longer referenced.

Confirm `_setup_menu()` already matches the five-group structure in the spec (status | settings+history | model | auto-start | quit). Do not change action texts or signals.

- [x] **Step 3: Run tests**

Run: `python -m pytest tests/test_tray_icon.py -v`

Expected: PASS (all tray tests including new style/grouping)

- [ ] **Step 4: Commit** (only if user requested commits; otherwise skip)

---

### Task 3: Verification

- [x] **Step 1: Run related UI tests**

Run: `python -m pytest tests/test_tray_icon.py tests/test_history_window.py::test_tray_menu_has_history_entry_signal tests/test_ui_styles.py -q`

Expected: all pass

- [ ] **Step 2: Manual note for human**

Right-click tray icon: white menu, ~4px radius, full-bleed separators, gray hover, checkmark on 开机自启, chevron on 切换模型; actions still work.

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Reference visual (4px, gray hover, separators) | Task 2 |
| Grouping 5 sections | Task 1 test + existing `_setup_menu` |
| Signals/copy unchanged | Task 2 (no signal edits) |
| Tokens optional but preferred | Task 2 Step 1 |
| pytest tray contracts | Task 1 + 3 |
| No custom QMenu replacement | Entire plan uses QSS only |
