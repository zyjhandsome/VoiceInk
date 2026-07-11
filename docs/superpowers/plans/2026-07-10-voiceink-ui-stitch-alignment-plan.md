# VoiceInk UI Stitch Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align VoiceInk PyQt6 UI (settings, history, tray; float tokens only) to Stitch Desktop Pro visual language without changing product semantics or red-line signals.

**Architecture:** Update `design_tokens.py` to Stitch palette first; restyle QSS and shared components; then restructure settings pages, history dual-pane, and tray menu. No ASR/paste/`App._connect_signals` changes.

**Tech Stack:** Python 3.10+, PyQt6, existing `voiceink/ui/*`, pytest

**Spec:** `docs/superpowers/specs/2026-07-10-voiceink-ui-stitch-alignment-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `voiceink/ui/design_tokens.py` | Stitch colors, radii, fonts, spacing |
| `voiceink/ui/settings_styles.py` | Window/button/input QSS from tokens |
| `voiceink/ui/settings_components.py` | Sidebar, heroes, cards, trigger picker, polish preview |
| `voiceink/ui/settings_window.py` | Four pages layout wiring |
| `voiceink/ui/history_window.py` | Dual-pane visual layout |
| `voiceink/ui/tray_icon.py` | Tray menu stylesheet |
| `voiceink/ui/floating_window.py` | Shared radius/font only |
| `voiceink/ui/nav_icons.py` / `model_card.py` | Follow new accent tokens |
| `tests/test_readme_features.py` (+ UI/history tests) | Regression |

---

### Task 1: Design tokens → Stitch palette

**Files:**
- Modify: `voiceink/ui/design_tokens.py`
- Test: existing imports still resolve; `pytest tests/ -q -k "settings or history or tray or ui" --maxfail=5` (or full suite if narrow filter empty)

- [ ] **Step 1: Replace light-theme tokens**

Set (keep `FLOAT_*` dark overlay family; only align `RADIUS_*` if needed):

```python
ACCENT = "#0050CB"
ACCENT_HV = "#003FA4"
ACCENT_FOCUS = "#0066FF"
ACCENT_ON_DARK = "#B3C5FF"
ACCENT_BG = "#DAE1FF"
ACCENT_SOFT = "rgba(0, 80, 203, 0.10)"

BG = "#F5F7FA"
NAV_BG = "#FCF8F9"
SURFACE = "#FFFFFF"
SURFACE_PEARL = "#F6F3F4"
BORDER = "#E1E4E8"
HAIRLINE = "#C2C6D8"
DIVIDER_SOFT = "#E5E2E3"
ROW_SELECTED = "#DCE3F0"
INPUT_BG = "#FFFFFF"

TEXT = "#1B1B1C"
TEXT_SEC = "#424656"
TEXT_DIM = "#727687"

FONT = (
    '"Inter", "Segoe UI Variable", "Microsoft YaHei UI", '
    '"Segoe UI", system-ui, sans-serif'
)
FONT_DISPLAY = FONT
FONT_MONO = (
    '"JetBrains Mono", "Cascadia Mono", "Consolas", monospace'
)

RADIUS_XS = 6
RADIUS_SM = 8
RADIUS_MD = 12
RADIUS_LG = 16
RADIUS_PILL = 999

# Optional aliases used by sidebar/nav
SECONDARY_CONTAINER = "#DCE3F0"
OUTLINE_VARIANT = "#C2C6D8"
PRIMARY_CONTAINER = "#0066FF"
```

Keep semantic greens/reds/ambers; keep `FLOAT_*` colors unchanged.

- [ ] **Step 2: Smoke-import**

Run: `python -c "from voiceink.ui.design_tokens import ACCENT, RADIUS_MD; assert ACCENT.upper()=='#0050CB'; assert RADIUS_MD==12"`

Expected: exit 0

- [ ] **Step 3: Commit** (only if user asked for commits)

---

### Task 2: Settings QSS + shared components shell

**Files:**
- Modify: `voiceink/ui/settings_styles.py`
- Modify: `voiceink/ui/settings_components.py` (`SettingsSidebar`, `PageHero`, `settings_section`/`settings_group`, nav styles)
- Modify: `voiceink/ui/nav_icons.py` (use new `ACCENT`)

- [ ] **Step 1: Update `WINDOW_CSS` / buttons** to use new tokens; primary button solid `#0050CB`, radius 12px; inputs soft gray focus blue.

- [ ] **Step 2: Rebuild `SettingsSidebar`**
  - Brand row: circular primary-container mic + blue “VoiceInk”
  - Status card: two lines (ready·model / polish on|off)
  - Nav: active = left 4px bar + `SECONDARY_CONTAINER` bg
  - Footer: Status line
  - Width ~248–260px

- [ ] **Step 3: PageHero** — display title + optional subtitle; polish page can show status on the right via existing or small API extension.

- [ ] **Step 4: Run** `pytest tests/test_readme_features.py -q`

---

### Task 3: Settings pages structure

**Files:**
- Modify: `voiceink/ui/settings_window.py`
- Modify: `voiceink/ui/settings_components.py` (`TriggerModePicker`, `polish_preview_content`, about helpers)
- Modify: `voiceink/ui/model_card.py` (border/radius/accent only)

- [ ] **Step 1: General** — large trigger cards; keep section order per spec §5.2
- [ ] **Step 2: Model** — hero + current engine + list + storage cards
- [ ] **Step 3: Polish** — header status; toggle → preview (gray / light-blue) → API/prompt below
- [ ] **Step 4: About** — brand + version pill; tip bar; KV table with mono paths
- [ ] **Step 5:** `pytest tests/test_readme_features.py -q`

---

### Task 4: History window dual-pane

**Files:**
- Modify: `voiceink/ui/history_window.py`

- [ ] **Step 1:** Left column: title + search + list (selected: `ROW_SELECTED` + left accent bar)
- [ ] **Step 2:** Right: detail card + export/delete actions; keep store/export APIs
- [ ] **Step 3:** `pytest tests/ -q -k history`

---

### Task 5: Tray menu + floating token tweak

**Files:**
- Modify: `voiceink/ui/tray_icon.py` (`_menu_stylesheet`)
- Modify: `voiceink/ui/floating_window.py` (radius/font only)

- [ ] **Step 1:** Tray: white surface, 12px radius, stronger shadow feel via border; checked = blue dot; separators
- [ ] **Step 2:** Float: use `RADIUS_MD`/`RADIUS_LG` and shared `FONT` where hardcoded
- [ ] **Step 3:** `pytest tests/test_readme_features.py -q`

---

### Task 6: README / final verification

**Files:**
- Modify: `README.md` only if user-visible labels changed
- Run: `pytest tests/test_readme_features.py -q` and broader UI-related tests

- [ ] **Step 1:** Diff user-facing strings; update README checklist if needed
- [ ] **Step 2:** Full relevant pytest pass
- [ ] **Step 3:** Manual note: compare to Stitch screenshots for sidebar/trigger/polish/about/tray/history

---

## Spec coverage checklist

| Spec § | Task |
|--------|------|
| §3 Tokens | T1 |
| §5.1 Shell | T2 |
| §5.2–5.5 Pages | T3 |
| §5.6 History | T4 |
| §5.7–5.8 Tray/Float | T5 |
| §7 Tests | T2–T6 |
