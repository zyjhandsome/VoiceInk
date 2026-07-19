# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** VoiceInk  
**Generated:** 2026-07-18 via ui-ux-pro-max (`--design-system --persist`)  
**Adapted for:** PyQt6 Windows desktop tray utility (light + dark)  
**Style seed:** AI-Native UI / high-end utility (voice transcription)  
**Stack notes:** No web Google Fonts runtime; use system UI fonts. No landing-page hero chrome.

---

## Global Rules

### Theme modes

| Mode | Meaning |
|------|---------|
| `light` | Forced light effective theme |
| `dark` | Forced dark effective theme |
| `system` | Effective theme follows Windows AppsUseLightTheme |

Effective theme is always `light` or `dark`.

### Color Palette — Light

| Role | Hex | Token / CSS Variable |
|------|-----|----------------------|
| Accent / focus | `#2563EB` | `ACCENT` / `--color-accent` |
| Accent text | `#2563EB` | `ACCENT_TEXT` |
| Primary container | `#2563EB` | `PRIMARY_CONTAINER` |
| Accent Hover | `#1D4ED8` | `ACCENT_HV` |
| Accent Soft | `rgba(37, 99, 235, 0.08)` | `ACCENT_SOFT` |
| Background | `#F3F4F6` | `BG` / `--color-background` |
| Surface | `#FFFFFF` | `SURFACE` |
| Surface Muted | `#F9FAFB` | `SURFACE_PEARL` |
| Foreground | `#111827` | `TEXT` / `--color-foreground` |
| Foreground Secondary | `#4B5563` | `TEXT_SEC` |
| Foreground Dim | `#667085` | `TEXT_DIM` |
| Border | `#E5E7EB` | `BORDER` / `--color-border` |
| Control Border | `#D1D5DB` | `CONTROL_BORDER` |
| Destructive / Record | `#C81E1E` / `#DC2626` | `RED` / `STATE_RECORD` |
| Success / toggle on | `#15803D` | `GREEN` / `TOGGLE_ON` |
| Focus Ring | `#2563EB` | `ACCENT_FOCUS` |
| Row Selected | `#EFF6FF` | `ROW_SELECTED` |

**Notes:** Brand interactive axis is blue; recording red is semantic only (not chrome primary). Cool neutrals — no warm pearl wash.

### Color Palette — Dark

| Role | Hex | Token / CSS Variable |
|------|-----|----------------------|
| Accent / focus | `#3B82F6` | `ACCENT` |
| Accent text | `#60A5FA` | `ACCENT_TEXT` |
| Primary container | `#2563EB` | `PRIMARY_CONTAINER` |
| Accent Hover | `#60A5FA` | `ACCENT_HV` |
| Accent Soft | `rgba(59, 130, 246, 0.16)` | `ACCENT_SOFT` |
| Background | `#111827` | `BG` |
| Surface | `#1F2937` | `SURFACE` |
| Surface Muted | `#374151` | `SURFACE_PEARL` |
| Foreground | `#F9FAFB` | `TEXT` |
| Foreground Secondary | `#D1D5DB` | `TEXT_SEC` |
| Foreground Dim | `#9CA3AF` | `TEXT_DIM` |
| Border | `#374151` | `BORDER` |
| Control Border | `#4B5563` | `CONTROL_BORDER` |
| Destructive / Record | `#F87171` | `RED` / `STATE_RECORD` |
| Success | `#22C55E` | `GREEN` |
| Focus Ring | `#3B82F6` | `ACCENT_FOCUS` |
| Row Selected | `rgba(59, 130, 246, 0.20)` | `ROW_SELECTED` |

### Floating overlay (theme-aware)

| Role | Light | Dark |
|------|-------|------|
| Float BG | `rgba(243, 244, 246, 245)` | `rgba(39, 39, 41, 245)` |
| Float Surface | `#FFFFFF` | `#272729` |
| Float Border | `rgba(17, 24, 39, 0.12)` | `rgba(255, 255, 255, 0.10)` |
| Float Text | `#111827` | `#FFFFFF` |
| Float Text Sec | `#4B5563` | `rgba(235, 235, 245, 0.72)` |

### Typography

- **UI Font:** `"Segoe UI Variable", "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif`
- **Mono:** `"Cascadia Mono", "Consolas", "JetBrains Mono", monospace`
- **Mood:** technical, precision, clean, premium desktop utility
- **Do not** ship runtime Google Fonts imports in the desktop app

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `SPACE_XS` / `--space-sm` | `8px` | Tight gaps |
| `SPACE_SM` | `12px` | Inline |
| `SPACE_MD` / `--space-md` | `16px` | Standard padding |
| `SPACE_LG` / `--space-lg` | `24px` | Section padding |
| `SPACE_XL` | `32px` | Large gaps |
| `SIDEBAR_WIDTH` | `248px` | Settings rail |
| `CONTROL_NUMERIC_WIDTH` | `120px` | History spinboxes (flat stepper + suffix) |

### Shape

| Token | Value |
|-------|-------|
| `RADIUS_XS` | `4px` |
| `RADIUS_SM` | `6px` |
| `RADIUS_MD` | `8px` |
| `RADIUS_LG` | `10px` |

### Shadows

| Level | Light | Dark |
|-------|-------|------|
| sm | `0 1px 2px rgba(0,0,0,0.05)` | `0 1px 2px rgba(0,0,0,0.35)` |
| md | `0 4px 6px rgba(0,0,0,0.10)` | `0 4px 8px rgba(0,0,0,0.45)` |

---

## Component Specs (desktop)

### Buttons

- Primary: accent fill, on-accent text, radius MD, visible `:focus` ring 2px accent
- Ghost / danger: semantic colors; danger uses destructive red
- Hover: darken/lighten within theme; no large translate on tray-adjacent chrome

### Cards / settings groups

- Surface fill, 1px border, radius LG
- Selected nav: accent soft wash + 3px accent bar (not saturated full fill)

### Inputs

- Surface / input bg, control border, focus ring accent
- Numeric spinboxes share `CONTROL_NUMERIC_WIDTH` (120px); flat up/down PNG chevrons

### Floating window

- Follows **effective** theme float tokens (not permanently locked to dark)

### Tray menu

- Surface, border, hover row wash from effective theme

---

## UX Guidelines

- Focus rings visible for keyboard users
- No emoji-as-icon; use drawn/SVG icons
- Theme switch applies without restart; preference persisted as `appearance.theme_mode`
- Keep recording red rationed to recording/error semantics
- Avoid excessive decoration and web-landing patterns in settings chrome

---

## Anti-patterns

- Warm cream / terracotta desktop kits
- Purple-glow AI cliché chrome
- Hard-coding a second undocumented brand palette beside this MASTER
- Floating window permanently dark when effective theme is light

---

## Traceability

| Source | Detail |
|--------|--------|
| ui-ux-pro-max query | `desktop utility voice transcription productivity dark mode windows tray` |
| Persist output | `design-system/voiceink/MASTER.md` (raw skill output) |
| This file | Canonical app MASTER with light/dark + desktop adaptations |
