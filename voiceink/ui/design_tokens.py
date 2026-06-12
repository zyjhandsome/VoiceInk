"""Apple-inspired VoiceInk design tokens (aligned with awesome-design-md/apple)."""

# Brand & accent — Action Blue family
ACCENT = "#0066CC"
ACCENT_HV = "#005BB5"
ACCENT_FOCUS = "#0071E3"
ACCENT_ON_DARK = "#2997FF"
ACCENT_BG = "#E8F4FF"
ACCENT_SOFT = "rgba(0, 102, 204, 0.10)"

# Surfaces
BG = "#EDF0F5"
NAV_BG = "#E6EAF0"
SURFACE = "#FFFFFF"
SURFACE_PEARL = "#F4F6F9"
BORDER = "#D8DEE6"
HAIRLINE = "#D0D7E2"
DIVIDER_SOFT = "#E4E9F0"
ROW_SELECTED = "#DCEAFA"
INPUT_BG = "#FFFFFF"
BAR_OFF = "#F0F0F0"

# Typography
TEXT = "#1D1D1F"
TEXT_SEC = "#86868B"
TEXT_DIM = "#7A7A7A"
TEXT_MUTED_DARK = "#CCCCCC"
FONT = (
    '"SF Pro Text", "Segoe UI Variable", "Microsoft YaHei UI", '
    '"Segoe UI", system-ui, -apple-system, sans-serif'
)
FONT_DISPLAY = (
    '"SF Pro Display", "Segoe UI Variable Display", "Segoe UI", '
    '"Microsoft YaHei UI", system-ui, -apple-system, sans-serif'
)

# Semantic colors
GREEN = "#34C759"
GREEN_BG = "#E8F8ED"
RED = "#FF3B30"
RED_BG = "#FFEBE9"
AMBER = "#FFCC00"
AMBER_TEXT = "#996F00"
AMBER_SOFT = "#FFFAEB"

# Shape — Apple rounded scale
RADIUS_XS = 5
RADIUS_SM = 8
RADIUS_MD = 11
RADIUS_LG = 18
RADIUS_PILL = 999

# Spacing scale (8px base)
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 16
SPACE_LG = 12
SPACE_XL = 24
PAGE_MARGIN_H = 20
PAGE_MARGIN_V = 14
CONTENT_MAX_WIDTH = 9999

# Interactive controls
CONTROL_BORDER = "#C7C7CC"
CONTROL_BORDER_HOVER = "#AEAEB2"
TOGGLE_OFF = "#E5E5EA"
TOGGLE_OFF_HOVER = "#D1D1D6"
TOGGLE_OFF_TRACK = (60, 60, 67, 48)
TOGGLE_OFF_TRACK_HOVER = (60, 60, 67, 72)
ROW_HOVER = "rgba(0, 0, 0, 0.03)"
FOCUS_RING = f"2px solid {ACCENT_FOCUS}"

# Dark overlay — surface-tile palette
FLOAT_BG = "rgba(39, 39, 41, 245)"
FLOAT_TILE = "#272729"
FLOAT_BORDER = "rgba(255, 255, 255, 0.10)"
FLOAT_BORDER_INNER = "rgba(210, 210, 215, 0.24)"
CHIP_BG = "rgba(210, 210, 215, 0.64)"
FLOAT_TEXT = "#FFFFFF"
FLOAT_TEXT_SEC = "rgba(235, 235, 245, 0.72)"
FLOAT_SHADOW = "rgba(0, 0, 0, 0.38)"

# State colors (floating window)
STATE_RECORD = "#FF6961"
STATE_LISTEN = ACCENT_ON_DARK
STATE_RECOGNIZE = AMBER
STATE_POLISH = GREEN
STATE_SUCCESS = GREEN
STATE_WARN = "#FF9F0A"
STATE_MUTED = "#98989D"
STATE_ERROR = "#FF6961"
