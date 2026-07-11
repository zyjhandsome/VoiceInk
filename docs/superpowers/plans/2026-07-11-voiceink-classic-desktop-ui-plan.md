# VoiceInk Classic Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle VoiceInk’s settings, history, floating HUD, and tray token alignment into a classic desktop-utility look (cool neutrals, rationed blue, de-carded sections, float recording-only accent) without changing product semantics or red-line signals.

**Architecture:** Update `design_tokens.py` first (cold gray axis, desaturated accent, float state colors). Drive QSS/components from tokens. Convert most `settings_group` shells to hairline sections; keep interactive cards (trigger / audio / model). Neutralize float status colors except recording. Align tests that hard-code Stitch hex values.

**Tech Stack:** Python 3.10+, PyQt6, existing `voiceink/ui/*`, pytest

**Spec:** `docs/superpowers/specs/2026-07-11-voiceink-classic-desktop-ui-design.md`

**Commits:** Only when the user explicitly asks. Skip commit steps otherwise.

---

## File map

| File | Responsibility |
|------|----------------|
| `voiceink/ui/design_tokens.py` | Cold gray palette, accent, radii, fonts, float state colors |
| `voiceink/ui/settings_styles.py` | Window / button / input QSS from tokens |
| `voiceink/ui/settings_components.py` | De-carded groups, sidebar, nav, choice cards, remove unused `GeneralPageHeader`, quiet tips |
| `voiceink/ui/settings_window.py` | Page assembly: plain sections, about tip, hotkey/about neutrals |
| `voiceink/ui/model_card.py` | Neutral “当前” badge; accent only on primary action when needed |
| `voiceink/ui/history_window.py` | Less boxing; action button hierarchy |
| `voiceink/ui/floating_window.py` | Neutral states; recording-only red |
| `voiceink/ui/tray_icon.py` | Font / gray token alignment only |
| `voiceink/ui/nav_icons.py` | Follow new accent if painted with ACCENT |
| `tests/test_ui_styles.py` | Token / sidebar / accent contract updates |
| `tests/test_floating_window.py` | Optional color contract for recording vs neutral |
| `tests/test_settings_general.py` | Keep layout/behavior; adjust if object names change |
| `README.md` | Only if user-visible copy changes |

---

### Task 1: Lock new visual contracts in tests (TDD)

**Files:**
- Modify: `tests/test_ui_styles.py`
- Modify: `tests/test_floating_window.py`
- Test: same

- [ ] **Step 1: Update `tests/test_ui_styles.py` for classic tokens**

Replace Stitch-era assertions:

```python
# In test_model_rating_labels_and_download_use_brand_accent:
assert "#2563EB" in card._action_btn.styleSheet()

# In test_nav_bg_matches_cool_app_background:
assert NAV_BG.upper() == BG.upper() == "#F3F4F6"

# In test_page_title_avoids_negative_tracking — also lock quieter title size:
from voiceink.ui.settings_components import PAGE_TITLE, SECTION_LABEL
assert "font-size: 22px" in PAGE_TITLE or "font-size: 20px" in PAGE_TITLE
assert "font-weight: 600" in PAGE_TITLE  # semibold, not 700
assert "letter-spacing: -" not in PAGE_TITLE

# In test_sidebar_brand_and_nav_metrics — status is no longer a bordered white card:
status = next(
    w for w in sidebar.findChildren(QFrame)
    if w.objectName() == "sidebarStatusCard"
)
sheet = status.styleSheet().lower()
assert "border: none" in sheet or "border: 0" in sheet or "1px solid" not in sheet
# Background should not force SURFACE white card look
assert "background: transparent" in sheet or SURFACE.lower() not in sheet

# Nav checked text stays dark (not accent blue as primary text color):
from voiceink.ui.settings_components import NAV_BTN_STYLE
from voiceink.ui.design_tokens import TEXT, ACCENT
checked = NAV_BTN_STYLE.split(":checked")[1].split("QPushButton")[0]
assert TEXT.lower() in checked.lower() or "111827" in checked.lower()
# Accent may appear on border-left only
assert "border-left: 4px solid" in checked
```

Add a small token contract class:

```python
class TestClassicDesktopTokens:
    def test_accent_and_surfaces(self):
        from voiceink.ui import design_tokens as t
        assert t.ACCENT.upper() == "#2563EB"
        assert t.BG.upper() == "#F3F4F6"
        assert "Inter" not in t.FONT
        assert t.RADIUS_MD == 8
        assert t.STATE_RECORD.upper() in {"#DC2626", "#E5484D", "#EF4444"}
        # Non-recording float states are neutral (same family as FLOAT_TEXT)
        assert t.STATE_LISTEN == t.FLOAT_TEXT or t.STATE_LISTEN == t.FLOAT_TEXT_SEC
        assert t.STATE_RECOGNIZE in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
        assert t.STATE_POLISH in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
```

- [ ] **Step 2: Add float color contract in `tests/test_floating_window.py`**

```python
class TestFloatingWindowClassicColors:
    def test_recording_uses_record_accent_others_neutral(self, win):
        from voiceink.ui.design_tokens import FLOAT_TEXT, STATE_RECORD

        win.show_listening()
        listen_ss = win._status_label.styleSheet().lower()
        assert STATE_RECORD.lower() not in listen_ss
        assert FLOAT_TEXT.lower() in listen_ss or "ffffff" in listen_ss or "235, 235, 245" in listen_ss

        win.show_recording()
        rec_ss = win._status_label.styleSheet().lower()
        assert STATE_RECORD.lower() in rec_ss

        win.show_recognizing("hi")
        assert STATE_RECORD.lower() not in win._status_label.styleSheet().lower()
```

- [ ] **Step 3: Run tests — expect FAIL on old tokens**

Run:

```bash
python -m pytest tests/test_ui_styles.py tests/test_floating_window.py::TestFloatingWindowClassicColors -v --maxfail=20
```

Expected: FAIL (old `#0050CB` / `#F5F7FA` / rainbow STATE_* / bordered status card).

---

### Task 2: `design_tokens.py` → classic palette

**Files:**
- Modify: `voiceink/ui/design_tokens.py`
- Test: `tests/test_ui_styles.py`

- [ ] **Step 1: Replace light-theme + float state tokens**

Keep tray `TRAY_MENU_*` block. Set:

```python
"""VoiceInk design tokens — classic desktop utility."""

# Brand & accent (rationed)
ACCENT = "#2563EB"
ACCENT_HV = "#1D4ED8"
ACCENT_FOCUS = "#2563EB"
ACCENT_ON_DARK = "#FFFFFF"  # float default emphasis = neutral white
ACCENT_BG = "#DBEAFE"
ACCENT_SOFT = "rgba(37, 99, 235, 0.08)"
PRIMARY_CONTAINER = "#2563EB"
SECONDARY_CONTAINER = "#E5E7EB"  # nav selected wash (neutral)

# Surfaces — single cool axis
BG = "#F3F4F6"
NAV_BG = "#F3F4F6"
SURFACE = "#FFFFFF"
SURFACE_PEARL = "#F9FAFB"  # cool muted fill (no warm pearl)
BORDER = "#E5E7EB"
HAIRLINE = "#E5E7EB"
OUTLINE_VARIANT = "#D1D5DB"
DIVIDER_SOFT = "#E5E7EB"
ROW_SELECTED = "#EFF6FF"  # very light blue wash for list selection only
INPUT_BG = "#FFFFFF"
BAR_OFF = "#E5E7EB"

# Typography
TEXT = "#111827"
TEXT_SEC = "#4B5563"
TEXT_DIM = "#9CA3AF"
TEXT_MUTED_DARK = "#CCCCCC"
FONT = (
    '"Segoe UI Variable", "Microsoft YaHei UI", '
    '"Segoe UI", system-ui, sans-serif'
)
FONT_DISPLAY = FONT
FONT_MONO = (
    '"Cascadia Mono", "Consolas", "JetBrains Mono", monospace'
)

# Semantic (settings actions only — not float state rainbow)
GREEN = "#16A34A"
GREEN_BG = "#DCFCE7"
RED = "#DC2626"
RED_BG = "#FEE2E2"
AMBER = "#D97706"
AMBER_TEXT = "#92400E"
AMBER_SOFT = "#FFFBEB"

# Shape
RADIUS_XS = 4
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 10
RADIUS_PILL = 999

# Keep existing SPACE_* / PAGE_MARGIN_* / SIDEBAR_WIDTH / TOGGLE_* / ROW_HOVER
# Update CONTROL_BORDER to cool grays:
CONTROL_BORDER = "#D1D5DB"
CONTROL_BORDER_HOVER = "#9CA3AF"

# Dark overlay — floating window (structure unchanged)
FLOAT_BG = "rgba(39, 39, 41, 245)"
FLOAT_TILE = "#272729"
FLOAT_BORDER = "rgba(255, 255, 255, 0.10)"
FLOAT_BORDER_INNER = "rgba(210, 210, 215, 0.24)"
CHIP_BG = "rgba(210, 210, 215, 0.40)"
FLOAT_TEXT = "#FFFFFF"
FLOAT_TEXT_SEC = "rgba(235, 235, 245, 0.72)"
FLOAT_SHADOW = "rgba(0, 0, 0, 0.38)"

# Float state colors — classic: neutral + recording only
STATE_RECORD = "#DC2626"
STATE_LISTEN = FLOAT_TEXT
STATE_RECOGNIZE = FLOAT_TEXT
STATE_POLISH = FLOAT_TEXT
STATE_SUCCESS = FLOAT_TEXT
STATE_WARN = FLOAT_TEXT_SEC
STATE_MUTED = FLOAT_TEXT_SEC
STATE_ERROR = STATE_RECORD
```

Keep existing `TRAY_MENU_*` constants. Optional: align `TRAY_MENU_BORDER` to `#E5E7EB` only if tray tests still pass.

- [ ] **Step 2: Re-run token tests**

```bash
python -m pytest tests/test_ui_styles.py::TestClassicDesktopTokens -v
```

Expected: PASS for token asserts; other UI style tests may still fail until components update.

---

### Task 3: Global QSS + quiet chrome (`settings_styles`)

**Files:**
- Modify: `voiceink/ui/settings_styles.py`
- Modify: `voiceink/ui/app_styles.py` (if it hard-codes radii/colors)

- [ ] **Step 1: Hotkey / inputs / buttons follow neutrals**

In `WINDOW_CSS` / `HotkeyEdit`:

- HotkeyEdit: `background: {SURFACE_PEARL}`; `color: {TEXT}` (not ACCENT); border `HAIRLINE`
- Focus: prefer stable padding (avoid 1px↔2px padding swap). If QSS cannot outline cleanly, use 2px focus **without** reducing padding.
- `BTN_PRIMARY`: ACCENT fill (allowed)
- `BTN_GHOST*`: pearl/neutral; no accent text
- Prefer `RADIUS_SM` over pill for small action buttons unless badge-like

- [ ] **Step 2: Smoke**

```bash
python -m pytest tests/test_ui_styles.py::TestSettingsStyles -v
```

---

### Task 4: Components — de-card, sidebar, nav, tips

**Files:**
- Modify: `voiceink/ui/settings_components.py`
- Test: `tests/test_ui_styles.py`, `tests/test_settings_general.py`

- [ ] **Step 1: Quiet `PAGE_TITLE`**

```python
PAGE_TITLE = (
    f"color: {TEXT}; font-family: {FONT_DISPLAY}; font-size: 22px;"
    f" font-weight: 600; letter-spacing: 0;"
)
```

- [ ] **Step 2: De-card `GROUP_STYLE` / hero card**

```python
GROUP_STYLE = f"""
    QFrame#settingsGroup {{
        background: transparent;
        border: none;
        border-radius: 0;
    }}
"""
HERO_CARD_STYLE = GROUP_STYLE.replace("settingsGroup", "settingsHeroCard")
```

Keep `settingsGroupTitle` object names so `test_general_sections_follow_task_order` still works. Add hairline dividers between dense row clusters only if the page looks too flat after de-carding.

- [ ] **Step 3: Sidebar status — no white card**

```python
QFrame#sidebarStatusCard {{
    background: transparent;
    border: none;
}}
```

Brand title: `font-size: 18px; font-weight: 600`.

- [ ] **Step 4: Nav selected — left bar + wash, dark text**

```python
QPushButton#settingsNavBtn:checked {{
    background: {SECONDARY_CONTAINER};
    border-left: 4px solid {ACCENT};
    color: {TEXT};
    font-weight: 600;
}}
```

- [ ] **Step 5: Choice cards — single emphasis**

Selected `VerticalChoiceCard`: `border: 1px solid {HAIRLINE}` + `border-left: 3px solid {ACCENT}` + `background: {ACCENT_SOFT}`; title `{TEXT}` (not ACCENT).

- [ ] **Step 6: `usage_tip_bar` → neutral tip**

Background `SURFACE_PEARL`; border `HAIRLINE`; label `TEXT_SEC`. No accent wash / accent text.

- [ ] **Step 7: Delete unused `GeneralPageHeader` class**

Grep confirms it is unused outside its definition. Remove the class.

- [ ] **Step 8: Run**

```bash
python -m pytest tests/test_ui_styles.py tests/test_settings_general.py -v --maxfail=15
```

---

### Task 5: Settings pages + model card

**Files:**
- Modify: `voiceink/ui/settings_window.py`
- Modify: `voiceink/ui/model_card.py`
- Test: `tests/test_settings_general.py`, `tests/test_ui_styles.py`

- [ ] **Step 1: Page assembly**

- Keep `PageHero` on general; do not reintroduce mobile header.
- Trigger section keeps interactive cards inside transparent `settings_group`.
- Other sections inherit de-carded `GROUP_STYLE`.
- About version pill: `SURFACE_PEARL` + `TEXT_SEC`.
- Footer hint secondary gray; primary close/done keeps ACCENT.

- [ ] **Step 2: `model_card.py`**

- Active: `1px solid {ACCENT}` or left bar (not heavy 2px ring + blue badge).
- “当前” badge: `background: {SURFACE_PEARL}; color: {TEXT_SEC}`.
- Download CTA may keep accent button (primary action — allowed).

- [ ] **Step 3: Run**

```bash
python -m pytest tests/test_settings_general.py tests/test_ui_styles.py -v --maxfail=15
```

---

### Task 6: History window

**Files:**
- Modify: `voiceink/ui/history_window.py`
- Test: `tests/test_history_window.py`

- [ ] **Step 1: Visual hierarchy**

- Search / selection use cool pearl + `ROW_SELECTED` + left bar; text `{TEXT}`.
- Right detail: avoid nested white card; transparent / no border if framed.
- Buttons: `导出` → `BTN_PRIMARY` (or first ghost); `复制原文` / `复制润色` → `BTN_GHOST_SM`; `删除` → `BTN_DANGER_SM`.

- [ ] **Step 2: Run**

```bash
python -m pytest tests/test_history_window.py -v
```

Expected: PASS (logic unchanged).

---

### Task 7: Floating window classic states

**Files:**
- Modify: `voiceink/ui/floating_window.py`
- Test: `tests/test_floating_window.py`

- [ ] **Step 1: Use tokenized states**

After Task 2, non-recording `STATE_*` equal `FLOAT_TEXT` / `FLOAT_TEXT_SEC`. Ensure `_set_state` sites use tokens (no local rainbow hex).

- Default waveform accent: `FLOAT_TEXT` (not old blue-on-dark).
- `show_recording`: `STATE_RECORD` + pulse on.
- Other states: **pulse only for recording** by default (listening = static white dot). If manual QA finds listening too dead, allow soft pulse with `FLOAT_TEXT` only.
- Close button: thinner `✕` (`U+2715`), `font-weight: 400`.

- [ ] **Step 2: Run**

```bash
python -m pytest tests/test_floating_window.py -v
```

Expected: PASS including `TestFloatingWindowClassicColors`.

---

### Task 8: Tray token alignment

**Files:**
- Modify: `voiceink/ui/tray_icon.py` only if FONT / colors need sync
- Test: `tests/test_tray_icon.py`

- [ ] **Step 1: Confirm stylesheet still uses `TRAY_MENU_*` + `FONT`**

No blue hover. Structure unchanged from tray-menu spec.

- [ ] **Step 2: Run**

```bash
python -m pytest tests/test_tray_icon.py -v
```

Expected: PASS.

---

### Task 9: Full regression + README check

**Files:**
- Possibly: `README.md` (only if visible copy changed)

- [ ] **Step 1: Run suite**

```bash
python -m pytest tests/test_ui_styles.py tests/test_settings_general.py tests/test_history_window.py tests/test_floating_window.py tests/test_tray_icon.py tests/test_readme_features.py -q
```

Expected: all PASS.

- [ ] **Step 2: Manual acceptance (spec §7)**

1. Settings: no mobile header; most sections unboxed; trigger/model cards remain  
2. Blue only on primary buttons + selection indicators  
3. History: left-bar selection; clear action hierarchy  
4. Float: only recording red; other states neutral  
5. Tray: small radius, gray hover  

- [ ] **Step 3: README 变更审查清单**

If no user-visible copy/IA changes → no README edit. If any label changed → update README + `tests/test_readme_features.py`.

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Cold gray tokens / no warm pearl / no Inter priority | 2 |
| Accent rationing rules | 3–5 |
| De-card settings groups; keep interactive cards | 4–5 |
| Remove GeneralPageHeader | 4 |
| Sidebar status unboxed; nav dark text | 4 |
| Quiet about tip / version | 4–5 |
| History hierarchy | 6 |
| Float recording-only accent | 2, 7 |
| Tray keep classic, token align | 8 |
| Tests + red-line / README | 1, 9 |

## Pinned values

- Accent: `#2563EB`
- App BG: `#F3F4F6`
- Recording red: `#DC2626`
- `SURFACE_PEARL` name kept, value remapped to cool `#F9FAFB`
- Listening pulse: off by default in Task 7
