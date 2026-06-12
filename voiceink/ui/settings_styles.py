"""QSS style fragments for the settings window."""

from voiceink.ui.design_tokens import (
    ACCENT,
    ACCENT_BG,
    ACCENT_FOCUS,
    ACCENT_HV,
    BAR_OFF,
    BG,
    FONT,
    GREEN,
    GREEN_BG,
    HAIRLINE,
    INPUT_BG,
    RADIUS_MD,
    RADIUS_PILL,
    RADIUS_SM,
    RED,
    RED_BG,
    SURFACE,
    SURFACE_PEARL,
    TEXT,
    TEXT_DIM,
    TEXT_SEC,
)
from voiceink.ui.settings_components import NAV_BTN_STYLE, ROW_RADIO_STYLE

WINDOW_CSS = f"""
    QDialog {{
        background: {BG};
        color: {TEXT};
        font-family: {FONT};
        font-size: 14px;
    }}
    QLabel {{
        color: {TEXT};
        background: transparent;
    }}
    QLineEdit {{
        background: {INPUT_BG};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_MD}px;
        padding: 10px 14px;
        font-size: 14px;
        selection-background-color: {ACCENT};
        selection-color: white;
    }}
    QLineEdit:focus {{
        border: 2px solid {ACCENT_FOCUS};
        padding: 9px 13px;
    }}
    {ROW_RADIO_STYLE}
    {NAV_BTN_STYLE}
    HotkeyEdit {{
        background: {SURFACE_PEARL};
        color: {ACCENT};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_MD}px;
        padding: 12px 16px;
        font-size: 16px;
        font-weight: 600;
        font-family: "Cascadia Mono", "Consolas", "SF Mono", monospace;
        min-height: 24px;
    }}
    HotkeyEdit:focus {{
        border: 2px solid {ACCENT_FOCUS};
        padding: 11px 15px;
        background: {SURFACE};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QComboBox {{
        background: {INPUT_BG};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_MD}px;
        padding: 8px 12px;
        font-size: 14px;
        min-height: 32px;
    }}
    QComboBox:focus {{
        border: 2px solid {ACCENT_FOCUS};
        padding: 7px 11px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background: {SURFACE};
        color: {TEXT};
        border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_MD}px;
        padding: 6px;
        selection-background-color: {ACCENT_BG};
        selection-color: {ACCENT};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 32px;
        padding: 6px 10px;
        border-radius: {RADIUS_SM}px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {SURFACE_PEARL};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar:vertical:disabled {{
        background: transparent;
    }}
    QScrollBar::handle:vertical:disabled {{
        background: transparent;
    }}
    QScrollBar::handle:vertical {{
        background: {HAIRLINE};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""

BTN_PRIMARY = f"""
    QPushButton {{
        background: {ACCENT}; color: white; border: none;
        border-radius: {RADIUS_PILL}px; padding: 11px 22px; font-size: 14px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {ACCENT_FOCUS}; }}
    QPushButton:pressed {{ background: {ACCENT_HV}; }}
    QPushButton:disabled {{ background: {BAR_OFF}; color: {TEXT_DIM}; }}
    QPushButton:focus {{ outline: none; }}
"""

BTN_GHOST = f"""
    QPushButton {{
        background: {SURFACE_PEARL}; color: {TEXT}; border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_PILL}px; padding: 11px 22px; font-size: 14px;
    }}
    QPushButton:hover {{ background: {SURFACE}; color: {TEXT}; border-color: {TEXT_DIM}; }}
    QPushButton:focus {{ outline: none; border: 2px solid {ACCENT_FOCUS}; }}
"""

BTN_GHOST_SM = f"""
    QPushButton {{
        background: {SURFACE_PEARL}; color: {TEXT_SEC}; border: 1px solid {HAIRLINE};
        border-radius: {RADIUS_SM}px; padding: 8px 15px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {SURFACE}; color: {TEXT}; }}
"""

BTN_DANGER_SM = f"""
    QPushButton {{
        background: transparent; color: {RED}; border: 1px solid {RED_BG};
        border-radius: {RADIUS_SM}px; padding: 8px 15px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {RED_BG}; color: {RED}; }}
"""

BTN_GREEN_SM = f"""
    QPushButton {{
        background: {GREEN_BG}; color: {GREEN}; border: none;
        border-radius: {RADIUS_PILL}px; padding: 8px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background: #D4F5DE; }}
    QPushButton:disabled {{ background: {BAR_OFF}; color: {TEXT_DIM}; }}
"""

BTN_ACCENT_SM = f"""
    QPushButton {{
        background: {ACCENT}; color: white; border: none;
        border-radius: {RADIUS_PILL}px; padding: 8px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {ACCENT_FOCUS}; }}
"""
