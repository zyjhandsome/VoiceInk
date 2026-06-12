"""Global application QSS built from design tokens."""

from voiceink.ui.design_tokens import FONT, HAIRLINE, RADIUS_LG, SURFACE, TEXT

GLOBAL_APP_STYLESHEET = f"""
    QWidget {{
        font-family: {FONT};
        font-size: 14px;
        color: {TEXT};
    }}
    QGroupBox {{
        font-weight: 600;
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_LG}px;
        margin-top: 16px;
        padding-top: 20px;
        background: {SURFACE};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
        color: {TEXT};
        letter-spacing: -0.2px;
    }}
"""
