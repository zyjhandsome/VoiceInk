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

# Tray context menu — reference desktop-utility style
TRAY_MENU_RADIUS = 4
TRAY_MENU_BORDER = "#E5E7EB"
TRAY_MENU_SEPARATOR = "#EEEEEE"
TRAY_MENU_HOVER = "#F5F5F5"
TRAY_MENU_DISABLED = "#888888"
TRAY_MENU_CHECK = "#333333"
TRAY_MENU_ARROW = "#999999"
TRAY_MENU_PAD_V = 8
TRAY_MENU_PAD_H = 18

# Spacing scale (4px base, comfortable density)
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32
PAGE_MARGIN_H = 20
PAGE_MARGIN_V = 16
CONTENT_MAX_WIDTH = 9999
SIDEBAR_WIDTH = 248

# Interactive controls
CONTROL_BORDER = "#D1D5DB"
CONTROL_BORDER_HOVER = "#9CA3AF"
TOGGLE_OFF = "#E5E2E3"
TOGGLE_OFF_HOVER = "#DCD9DA"
TOGGLE_OFF_TRACK = (60, 60, 67, 48)
TOGGLE_OFF_TRACK_HOVER = (60, 60, 67, 72)
ROW_HOVER = "rgba(0, 0, 0, 0.03)"
FOCUS_RING = f"2px solid {ACCENT_FOCUS}"

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
