"""QSS style fragments for the settings window (theme-rebuildable)."""

from __future__ import annotations

from voiceink.ui import design_tokens as t
from voiceink.ui import settings_components as sc


def build_window_css() -> str:
    return f"""
    QDialog {{
        background: {t.BG};
        color: {t.TEXT};
        font-family: {t.FONT};
        font-size: 14px;
    }}
    QLabel {{
        color: {t.TEXT};
        background: transparent;
    }}
    QLineEdit {{
        background: {t.INPUT_BG};
        color: {t.TEXT};
        border: 1px solid {t.CONTROL_BORDER};
        border-radius: {t.RADIUS_MD}px;
        padding: 10px 14px;
        font-size: 14px;
        selection-background-color: {t.PRIMARY_CONTAINER};
        selection-color: white;
    }}
    QLineEdit:focus {{
        border: 2px solid {t.ACCENT_FOCUS};
        padding: 10px 14px;
    }}
    {sc.ROW_RADIO_STYLE}
    {sc.NAV_BTN_STYLE}
    HotkeyEdit {{
        background: {t.SURFACE};
        color: {t.TEXT};
        border: 1px solid {t.CONTROL_BORDER};
        border-radius: {t.RADIUS_MD}px;
        padding: 10px 12px;
        font-size: 13px;
        font-weight: 600;
        font-family: {t.FONT_MONO};
        min-height: 24px;
    }}
    HotkeyEdit:focus {{
        border: 2px solid {t.ACCENT_FOCUS};
        padding: 10px 12px;
        background: {t.SURFACE};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QComboBox {{
        background: {t.SURFACE};
        color: {t.TEXT};
        border: 1px solid {t.CONTROL_BORDER};
        border-radius: {t.RADIUS_MD}px;
        padding: 8px 28px 8px 12px;
        font-size: 13px;
        min-height: 32px;
    }}
    QComboBox:focus {{
        border: 2px solid {t.ACCENT_FOCUS};
        padding: 8px 28px 8px 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {t.SURFACE};
        color: {t.TEXT};
        border: 1px solid {t.CONTROL_BORDER};
        border-radius: {t.RADIUS_MD}px;
        padding: 6px;
        selection-background-color: {t.ACCENT_SOFT};
        selection-color: {t.ACCENT_TEXT};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 32px;
        padding: 6px 10px;
        border-radius: {t.RADIUS_SM}px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {t.SURFACE_PEARL};
    }}
    QSpinBox {{
        background: {t.SURFACE};
        color: {t.TEXT};
        border: 1px solid {t.CONTROL_BORDER};
        border-radius: {t.RADIUS_MD}px;
        padding: 8px 28px 8px 12px;
        font-size: 13px;
        min-height: 34px;
    }}
    QSpinBox:focus {{
        border: 2px solid {t.ACCENT_FOCUS};
        padding: 8px 28px 8px 12px;
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
        background: {t.HAIRLINE};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""


def build_btn_primary() -> str:
    return f"""
    QPushButton {{
        background: {t.PRIMARY_CONTAINER}; color: white;
        border: 1px solid {t.PRIMARY_CONTAINER};
        border-radius: {t.RADIUS_MD}px; padding: 9px 14px; font-size: 13px; font-weight: 600;
    }}
    QPushButton:hover {{
        background: {t.PRIMARY_CONTAINER_HOVER};
        border-color: {t.PRIMARY_CONTAINER_HOVER};
    }}
    QPushButton:pressed {{
        background: {t.PRIMARY_CONTAINER_PRESSED};
        border-color: {t.PRIMARY_CONTAINER_PRESSED};
    }}
    QPushButton:disabled {{ background: {t.BAR_OFF}; border-color: {t.BAR_OFF}; color: {t.TEXT_DIM}; }}
    QPushButton:focus {{ border: 2px solid {t.ACCENT_FOCUS}; padding: 9px 14px; }}
"""


def build_btn_ghost() -> str:
    return f"""
    QPushButton {{
        background: {t.SURFACE_PEARL}; color: {t.TEXT}; border: 1px solid {t.HAIRLINE};
        border-radius: {t.RADIUS_MD}px; padding: 10px 22px; font-size: 14px;
    }}
    QPushButton:hover {{ background: {t.SURFACE}; color: {t.TEXT}; border-color: {t.TEXT_DIM}; }}
    QPushButton:focus {{ outline: none; border: 2px solid {t.ACCENT_FOCUS}; }}
"""


def build_btn_ghost_sm() -> str:
    return f"""
    QPushButton {{
        background: {t.SURFACE_PEARL}; color: {t.TEXT_SEC}; border: 1px solid {t.HAIRLINE};
        border-radius: {t.RADIUS_SM}px; padding: 8px 15px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {t.SURFACE}; color: {t.TEXT}; }}
    QPushButton:focus {{ border: 2px solid {t.ACCENT_FOCUS}; padding: 8px 15px; }}
"""


def build_btn_danger_sm() -> str:
    return f"""
    QPushButton {{
        background: transparent; color: {t.RED}; border: 1px solid {t.RED_BG};
        border-radius: {t.RADIUS_SM}px; padding: 8px 15px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {t.RED_BG}; color: {t.RED}; }}
    QPushButton:focus {{ border: 2px solid {t.ACCENT_FOCUS}; padding: 8px 15px; }}
"""


def build_btn_green_sm() -> str:
    return f"""
    QPushButton {{
        background: {t.GREEN_BG}; color: {t.GREEN}; border: none;
        border-radius: {t.RADIUS_SM}px; padding: 8px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {t.GREEN_BG}; }}
    QPushButton:disabled {{ background: {t.BAR_OFF}; color: {t.TEXT_DIM}; }}
"""


def build_btn_accent_sm() -> str:
    return f"""
    QPushButton {{
        background: {t.PRIMARY_CONTAINER}; color: white; border: none;
        border-radius: {t.RADIUS_SM}px; padding: 8px 16px; font-size: 12px; font-weight: 600;
    }}
    QPushButton:hover {{ background: {t.PRIMARY_CONTAINER_HOVER}; }}
    QPushButton:pressed {{ background: {t.PRIMARY_CONTAINER_PRESSED}; }}
"""


def reload_styles() -> None:
    """Rebuild module-level style aliases from the active token axis."""
    global WINDOW_CSS, BTN_PRIMARY, BTN_GHOST, BTN_GHOST_SM
    global BTN_DANGER_SM, BTN_GREEN_SM, BTN_ACCENT_SM
    sc.reload_styles()
    WINDOW_CSS = build_window_css()
    BTN_PRIMARY = build_btn_primary()
    BTN_GHOST = build_btn_ghost()
    BTN_GHOST_SM = build_btn_ghost_sm()
    BTN_DANGER_SM = build_btn_danger_sm()
    BTN_GREEN_SM = build_btn_green_sm()
    BTN_ACCENT_SM = build_btn_accent_sm()


WINDOW_CSS = ""
BTN_PRIMARY = ""
BTN_GHOST = ""
BTN_GHOST_SM = ""
BTN_DANGER_SM = ""
BTN_GREEN_SM = ""
BTN_ACCENT_SM = ""

reload_styles()
