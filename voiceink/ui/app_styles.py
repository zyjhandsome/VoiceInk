"""Global application QSS built from design tokens."""

from __future__ import annotations

from voiceink.ui.design_tokens import FONT


def build_global_stylesheet(effective: str = "light") -> str:
    """Return the theme-independent application typography baseline.

    Theme colors belong to QApplication's palette and surface-local QSS. Keeping
    this stylesheet static avoids an expensive full widget-tree repolish on
    every light/dark switch.
    """
    del effective
    return f"""
    QWidget {{
        font-family: {FONT};
        font-size: 14px;
    }}
"""


# Backward-compatible name: light axis at import; prefer build_global_stylesheet.
GLOBAL_APP_STYLESHEET = build_global_stylesheet("light")
