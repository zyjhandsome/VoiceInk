"""Stitch Desktop Pro building blocks for VoiceInk settings UI."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QSize, QPointF, QRectF, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QRadioButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from voiceink.ui.design_tokens import (
    ACCENT,
    ACCENT_FOCUS,
    ACCENT_SOFT,
    AMBER_SOFT,
    AMBER_TEXT,
    CONTROL_BORDER,
    CONTROL_BORDER_HOVER,
    DIVIDER_SOFT,
    FONT_DISPLAY,
    HAIRLINE,
    NAV_BG,
    PAGE_MARGIN_H,
    PAGE_MARGIN_V,
    RADIUS_MD,
    RADIUS_PILL,
    RADIUS_SM,
    ROW_HOVER,
    SECONDARY_CONTAINER,
    SIDEBAR_WIDTH,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SURFACE,
    SURFACE_PEARL,
    TEXT,
    TEXT_DIM,
    TEXT_SEC,
    TOGGLE_OFF_TRACK,
    TOGGLE_OFF_TRACK_HOVER,
)

# ── Style fragments ──────────────────────────────────────────────

SECTION_LABEL = (
    f"color: {TEXT_SEC}; font-size: 13px; font-weight: 600;"
    f" padding: 12px {SPACE_MD}px 8px {SPACE_MD}px; letter-spacing: 0;"
    f" background: transparent;"
)

PAGE_TITLE = (
    f"color: {TEXT}; font-family: {FONT_DISPLAY}; font-size: 22px;"
    f" font-weight: 600; letter-spacing: 0;"
)

PAGE_SUBTITLE = (
    f"color: {TEXT_SEC}; font-size: 14px; padding: 0;"
    f" line-height: 1.4; letter-spacing: 0;"
)

FOOTNOTE = (
    f"color: {TEXT_DIM}; font-size: 11px; line-height: 1.45;"
    f" padding: 4px 4px 0 4px; letter-spacing: 0;"
)

GROUP_STYLE = f"""
    QFrame#settingsGroup {{
        background: transparent;
        border: none;
        border-radius: 0;
    }}
"""

HERO_CARD_STYLE = GROUP_STYLE.replace("settingsGroup", "settingsHeroCard")

ROW_RADIO_STYLE = f"""
    QRadioButton {{
        color: {TEXT};
        spacing: 12px;
        font-size: 14px;
        padding: 10px 14px;
        background: transparent;
        border: none;
    }}
    QRadioButton::indicator {{
        width: 20px;
        height: 20px;
        subcontrol-position: right center;
        subcontrol-origin: padding;
        margin-right: 4px;
        border-radius: 10px;
        border: 2px solid {CONTROL_BORDER_HOVER};
        background: {SURFACE};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {ACCENT};
        background: qradialgradient(
            cx:0.5, cy:0.5, radius:0.45, fx:0.5, fy:0.5,
            stop:0 {ACCENT}, stop:0.52 {ACCENT},
            stop:0.53 {SURFACE}, stop:1 {SURFACE}
        );
    }}
    QRadioButton::indicator:unchecked:hover {{
        border-color: {ACCENT_FOCUS};
    }}
    QRadioButton:focus {{
        border: 2px solid {ACCENT_FOCUS};
        border-radius: {RADIUS_SM}px;
        padding: 8px 12px;
    }}
"""

NAV_BTN_STYLE = f"""
    QPushButton#settingsNavBtn {{
        text-align: left;
        padding: 0 14px 0 12px;
        border: none;
        border-left: 4px solid transparent;
        border-radius: {RADIUS_SM}px;
        color: {TEXT_SEC};
        font-size: 14px;
        font-weight: 500;
        background: transparent;
    }}
    QPushButton#settingsNavBtn:checked {{
        background: {SECONDARY_CONTAINER};
        border-left: 4px solid {ACCENT};
        color: {TEXT};
        font-weight: 600;
    }}
    QPushButton#settingsNavBtn:hover:!checked {{
        background: {ROW_HOVER};
        color: {TEXT};
    }}
    QPushButton#settingsNavBtn:focus {{
        border: 2px solid {ACCENT_FOCUS};
        border-left: 4px solid {ACCENT_FOCUS};
    }}
"""

LINK_BTN_STYLE = f"""
    QPushButton {{
        color: {TEXT_SEC}; background: transparent; border: none;
        font-size: 12px; text-align: left; padding: 4px 0;
    }}
    QPushButton:hover {{ color: {TEXT}; }}
    QPushButton:focus {{
        outline: none;
        border-bottom: 1px solid {CONTROL_BORDER_HOVER};
    }}
"""


def section_header(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(SECTION_LABEL)
    return lbl


def page_header(title: str, subtitle: str = "") -> QWidget:
    wrap = QWidget()
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 4)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setStyleSheet(PAGE_TITLE)
    lay.addWidget(t)
    if subtitle:
        lay.addWidget(page_intro(subtitle))
    return wrap


def page_intro(text: str) -> QLabel:
    """Subtitle-only intro — sidebar already shows the page title."""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(PAGE_SUBTITLE)
    return lbl


def elide_middle(text: str, max_len: int = 44) -> str:
    if len(text) <= max_len:
        return text
    head = max_len // 2 - 2
    tail = max_len - head - 1
    return f"{text[:head]}…{text[-tail:]}"


class PageHero(QWidget):
    """Page title with optional inline status and subtitle."""

    def __init__(self, title: str, tags: list[str] | None = None, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 2)
        self._root.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._title = QLabel(title)
        self._title.setStyleSheet(PAGE_TITLE)
        top.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)

        self._inline_status = QLabel("")
        self._inline_status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._inline_status.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; font-weight: 500;"
            f" background: transparent;"
        )
        self._inline_status.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        self._inline_status.setVisible(False)
        top.addWidget(self._inline_status, 0, Qt.AlignmentFlag.AlignVCenter)
        self._root.addLayout(top)

        self._subtitle = QLabel(subtitle)
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet(PAGE_SUBTITLE)
        self._subtitle.setVisible(bool(subtitle))
        self._root.addWidget(self._subtitle)

        if tags:
            self.set_tags(tags)

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

    def set_inline_status(self, text: str) -> None:
        cleaned = text.strip()
        self._inline_status.setText(cleaned)
        self._inline_status.setVisible(bool(cleaned))

    def set_tags(self, tags: list[str]) -> None:
        parts = [t.strip() for t in tags if t and t.strip()]
        self.set_subtitle(" · ".join(parts))

    def set_status(self, text: str) -> None:
        self.set_inline_status(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)
        visible = bool(text)
        self._subtitle.setVisible(visible)
        self._root.setContentsMargins(0, 0, 0, 6 if visible else 2)


def hero_card() -> QFrame:
    frame = QFrame()
    frame.setObjectName("settingsHeroCard")
    frame.setStyleSheet(HERO_CARD_STYLE)
    return frame


def usage_tip_bar(text: str) -> QFrame:
    """Inline hint strip below hero (shortcut / how-to)."""
    frame = QFrame()
    frame.setObjectName("usageTipBar")
    frame.setStyleSheet(f"""
        QFrame#usageTipBar {{
            background: {SURFACE_PEARL};
            border: 1px solid {HAIRLINE};
            border-radius: {RADIUS_MD}px;
        }}
    """)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(16, 12, 16, 12)
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {TEXT_SEC}; font-size: 13px; line-height: 1.45; background: transparent;"
    )
    lay.addWidget(lbl)
    return frame


def polish_preview_content() -> QWidget:
    """Before/after sample body — embed inside parent card, no extra box."""
    frame = QWidget()
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(SPACE_MD, 4, SPACE_MD, SPACE_MD)
    lay.setSpacing(12)

    head = QLabel("效果预览")
    head.setStyleSheet(
        f"color: {TEXT}; font-size: 16px; font-weight: 600; background: transparent;"
    )
    lay.addWidget(head)

    def _sample(label: str, body: str, *, polished: bool) -> None:
        box = QWidget()
        bl = QVBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        tag = QLabel(label)
        tag.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; font-weight: 500;"
            f" background: transparent;"
        )
        bl.addWidget(tag)
        txt = QLabel(body)
        txt.setWordWrap(True)
        if polished:
            color = TEXT
            bg = SURFACE
            border = f"1px solid {HAIRLINE}"
        else:
            color = TEXT_SEC
            bg = SURFACE_PEARL
            border = f"1px solid {HAIRLINE}"
        txt.setStyleSheet(
            f"color: {color}; font-size: 14px; line-height: 1.5;"
            f" background: {bg}; border: {border};"
            f" border-radius: {RADIUS_SM}px; padding: 12px 14px;"
        )
        bl.addWidget(txt)
        lay.addWidget(box)

    _sample(
        "转写原文",
        "那个我今天嗯想去趟超市然后买点东西。",
        polished=False,
    )
    _sample(
        "润色后",
        "我今天想去趟超市买点东西。",
        polished=True,
    )
    hint = QLabel("ℹ  开启上方开关并配置 API 后，识别结果会自动润色。")
    hint.setWordWrap(True)
    hint.setStyleSheet(
        f"color: {TEXT_SEC}; font-size: 12px; background: transparent;"
    )
    lay.addWidget(hint)
    return frame


def kv_row_elided(key: str, value: str, *, max_len: int = 44) -> QWidget:
    display = elide_middle(value, max_len)
    row = kv_row(key, display, mono=True)
    if display != value:
        for child in row.findChildren(QLabel):
            if child.text() == display:
                child.setToolTip(value)
                break
    return row


def footnote(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(FOOTNOTE)
    return lbl


def info_callout(text: str, object_name: str = "infoCallout") -> QFrame:
    """Subtle inline notice — not a heavy alert banner."""
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setStyleSheet(f"""
        QFrame#{object_name} {{
            background: {AMBER_SOFT};
            border: 1px solid #F5E6B8;
            border-radius: {RADIUS_SM}px;
        }}
    """)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(8)
    icon = QLabel("⚠")
    icon.setStyleSheet(
        f"color: {AMBER_TEXT}; font-size: 14px; background: transparent;"
    )
    icon.setAlignment(Qt.AlignmentFlag.AlignTop)
    lay.addWidget(icon)
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {AMBER_TEXT}; font-size: 12px; line-height: 1.45; background: transparent;"
    )
    lay.addWidget(lbl, 1)
    return frame


def empty_state(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"color: {TEXT_DIM}; font-size: 13px; padding: 20px 12px;"
        f" background: transparent;"
    )
    return lbl


def group_divider() -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(SPACE_MD, 0, SPACE_MD, 0)
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {DIVIDER_SOFT};")
    lay.addWidget(line)
    return wrap


def settings_group() -> QFrame:
    frame = QFrame()
    frame.setObjectName("settingsGroup")
    frame.setStyleSheet(GROUP_STYLE)
    return frame


def settings_section(title: str, group: QFrame) -> QWidget:
    """Section title above a white card."""
    wrap = QWidget()
    wrap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6 if title else 0)
    if title:
        hdr = QLabel(title)
        hdr.setObjectName("settingsGroupTitle")
        hdr.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; font-weight: 600;"
            f" padding: 0 4px; background: transparent;"
            f" letter-spacing: 0.02em;"
        )
        lay.addWidget(hdr)
    lay.addWidget(group)
    return wrap


def option_row(title: str, subtitle: str = "") -> QWidget:
    col = QWidget()
    lay = QVBoxLayout(col)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setStyleSheet(
        f"color: {TEXT}; font-size: 14px; font-weight: 500; background: transparent;"
    )
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        lay.addWidget(s)
    return col


def labeled_row(label: str, widget: QWidget, hint: str = "") -> QWidget:
    row = QWidget()
    outer = QVBoxLayout(row)
    outer.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
    outer.setSpacing(6)

    top = QHBoxLayout()
    top.setSpacing(SPACE_SM)
    lbl = QLabel(label)
    lbl.setStyleSheet(
        f"color: {TEXT_SEC}; font-size: 13px; min-width: 72px; background: transparent;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    lbl.setBuddy(widget)
    top.addWidget(lbl)
    top.addWidget(widget, 1)
    outer.addLayout(top)

    if hint:
        h = QLabel(hint)
        h.setWordWrap(True)
        h.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; padding-left: 84px; background: transparent;"
        )
        outer.addWidget(h)
    return row


def stacked_field_row(label: str, widget: QWidget, hint: str = "") -> QWidget:
    """Vertical field — label, control, optional hint (settings-row pattern)."""
    row = QWidget()
    outer = QVBoxLayout(row)
    outer.setContentsMargins(SPACE_MD, 10, SPACE_MD, 10)
    outer.setSpacing(6)

    lbl = QLabel(label)
    lbl.setStyleSheet(
        f"color: {TEXT}; font-size: 14px; font-weight: 500; background: transparent;"
    )
    lbl.setBuddy(widget)
    outer.addWidget(lbl)
    outer.addWidget(widget)

    if hint:
        h = QLabel(hint)
        h.setWordWrap(True)
        h.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; line-height: 1.4; background: transparent;"
        )
        outer.addWidget(h)
    return row


def inline_action_row(widget: QWidget, *, margins: tuple[int, int, int, int] | None = None) -> QWidget:
    """Padded row for buttons or status inside a settings group."""
    row = QWidget()
    m = margins or (SPACE_MD, SPACE_SM, SPACE_MD, SPACE_MD)
    lay = QVBoxLayout(row)
    lay.setContentsMargins(*m)
    lay.setSpacing(8)
    lay.addWidget(widget)
    return row


def kv_row(key: str, value: str, *, mono: bool = False) -> QWidget:
    from voiceink.ui.design_tokens import FONT_MONO

    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(SPACE_MD, 11, SPACE_MD, 11)
    lay.setSpacing(SPACE_MD)
    k = QLabel(key)
    k.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px; min-width: 80px;")
    k.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    v = QLabel(value)
    v.setWordWrap(True)
    v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if mono:
        v.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-family: {FONT_MONO};"
        )
    else:
        v.setStyleSheet(f"color: {TEXT}; font-size: 13px;")
    lay.addWidget(k)
    lay.addWidget(v, 1)
    return row


class _SourceIcon(QWidget):
    """Simple painted icon for audio source choice cards."""

    def __init__(self, kind: str, active: bool = False, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._active = active
        self.setFixedSize(32, 32)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(ACCENT if self._active else TEXT_SEC)
        pen = QPen(color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._kind == "mic":
            p.drawRoundedRect(11, 4, 10, 16, 5, 5)
            p.drawLine(16, 20, 16, 24)
            p.drawLine(12, 24, 20, 24)
            p.drawLine(16, 4, 16, 2)
        elif self._kind == "sys":
            p.drawRoundedRect(6, 10, 8, 12, 2, 2)
            p.drawLine(10, 22, 10, 26)
            p.drawLine(6, 26, 14, 26)
            p.drawLine(18, 12, 24, 8)
            p.drawLine(24, 8, 24, 20)
            p.drawLine(18, 20, 24, 20)
        elif self._kind == "continuous":
            p.setBrush(color)
            for x, h in ((8, 10), (14, 18), (20, 12), (26, 16)):
                y = 24 - h
                p.drawRoundedRect(x, y, 4, h, 2, 2)
            p.setBrush(Qt.BrushStyle.NoBrush)
        elif self._kind == "hotkey":
            p.drawRoundedRect(7, 9, 18, 14, 4, 4)
            p.drawLine(11, 14, 21, 14)
            p.drawLine(11, 18, 17, 18)
        else:
            p.drawRoundedRect(4, 8, 8, 12, 3, 3)
            p.drawLine(8, 20, 8, 23)
            p.drawRoundedRect(18, 6, 10, 14, 4, 4)
            p.drawLine(23, 20, 23, 24)
            p.drawLine(20, 24, 26, 24)
        p.end()


class ChoiceCard(QFrame):
    """Clickable option card — vertical icon layout (legacy horizontal picker)."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_kind: str,
        radio: QRadioButton,
        parent=None,
    ):
        super().__init__(parent)
        self._radio = radio
        self._icon_kind = icon_kind
        self._subtitle = subtitle
        self.setObjectName("ChoiceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(title)
        if subtitle:
            self.setAccessibleDescription(subtitle)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._icon = _SourceIcon(icon_kind)
        lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignHCenter)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        t.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        lay.addWidget(t)

        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        s.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 11px; line-height: 1.35; background: transparent;"
        )
        lay.addWidget(s)

        radio.toggled.connect(self._sync_style)
        self._sync_style(radio.isChecked())

    def _sync_style(self, checked: bool) -> None:
        self.setProperty("accessibleChecked", checked)
        self.setAccessibleDescription(
            f"{self._subtitle}，{'已选中' if checked else '未选中'}".strip("，")
        )
        self._icon.set_active(checked)
        if checked:
            self.setStyleSheet(f"""
                ChoiceCard {{
                    background: {SURFACE};
                    border: 2px solid {ACCENT};
                    border-radius: {RADIUS_MD}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ChoiceCard {{
                    background: {SURFACE};
                    border: 1px solid {HAIRLINE};
                    border-radius: {RADIUS_MD}px;
                }}
                ChoiceCard:hover {{
                    border-color: {ACCENT_FOCUS};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._radio.setChecked(True)
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._radio.setChecked(True)
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class VerticalChoiceCard(QFrame):
    """Full-width selectable row — reference general-settings audio cards."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_kind: str,
        radio: QRadioButton,
        parent=None,
    ):
        super().__init__(parent)
        self._radio = radio
        self._subtitle = subtitle
        self.setObjectName("VerticalChoiceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(title)
        if subtitle:
            self.setAccessibleDescription(subtitle)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        self._icon = _SourceIcon(icon_kind)
        lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(
            f"color: {TEXT}; font-size: 14px; font-weight: 600; background: transparent;"
        )
        text_col.addWidget(t)
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; line-height: 1.35; background: transparent;"
        )
        text_col.addWidget(s)
        lay.addLayout(text_col, 1)

        radio.setVisible(False)
        radio.toggled.connect(self._sync_style)
        self._sync_style(radio.isChecked())

    def _sync_style(self, checked: bool) -> None:
        self.setProperty("accessibleChecked", checked)
        self.setAccessibleDescription(
            f"{self._subtitle}，{'已选中' if checked else '未选中'}".strip("，")
        )
        self._icon.set_active(checked)
        if checked:
            self.setStyleSheet(f"""
                VerticalChoiceCard {{
                    background: {ACCENT_SOFT};
                    border: 1px solid {HAIRLINE};
                    border-left: 3px solid {ACCENT};
                    border-radius: {RADIUS_MD}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                VerticalChoiceCard {{
                    background: {SURFACE};
                    border: 1px solid {HAIRLINE};
                    border-radius: {RADIUS_MD}px;
                }}
                VerticalChoiceCard:hover {{
                    border-color: {ACCENT_FOCUS};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._radio.setChecked(True)
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._radio.setChecked(True)
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class AudioSourcePicker(QWidget):
    """Vertically stacked audio source cards (reference layout)."""

    def __init__(
        self,
        mic_radio: QRadioButton,
        sys_radio: QRadioButton,
        mixed_radio: QRadioButton,
        parent=None,
    ):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        lay.setSpacing(8)

        specs = [
            (mic_radio, "仅麦克风", "收录你的说话声", "mic"),
            (sys_radio, "仅电脑播放", "视频、会议声音", "sys"),
            (mixed_radio, "麦克风+电脑", "开会同时收录", "mixed"),
        ]
        for rb, title, sub, kind in specs:
            lay.addWidget(VerticalChoiceCard(title, sub, kind, rb))


class TriggerModePicker(QWidget):
    """Mutually exclusive trigger mode cards — side-by-side Stitch layout."""

    def __init__(
        self,
        continuous_radio: QRadioButton,
        hotkey_radio: QRadioButton,
        parent=None,
    ):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        lay.setSpacing(12)

        specs = [
            (
                continuous_radio,
                "自动持续转写",
                "按住约 0.30 秒开始，浮窗 × 结束整场监听",
                "continuous",
            ),
            (
                hotkey_radio,
                "按住快捷键录音",
                "按住约 0.18 秒录音，松开后结束并识别",
                "hotkey",
            ),
        ]
        for rb, title, sub, kind in specs:
            card = VerticalChoiceCard(title, sub, kind, rb)
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            lay.addWidget(card, 1)


class _PlayCircle(QWidget):
    """Neutral circular play affordance for audio test row."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = min(self.width(), self.height())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TEXT_SEC))
        p.drawEllipse(0, 0, d, d)
        tri = QPolygonF([
            QPointF(d * 0.38, d * 0.28),
            QPointF(d * 0.38, d * 0.72),
            QPointF(d * 0.72, d * 0.50),
        ])
        p.setBrush(QColor("#FFFFFF"))
        p.drawPolygon(tri)
        p.end()


class _WaveformBadge(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(TEXT_DIM)
        c.setAlpha(120)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        w, h = self.width(), self.height()
        bars = [0.35, 0.7, 0.5, 0.9, 0.45, 0.75, 0.55]
        gap = 3
        bar_w = max(2, (w - gap * (len(bars) - 1)) // len(bars))
        for i, ratio in enumerate(bars):
            bh = max(4, int(h * ratio))
            x = i * (bar_w + gap)
            y = (h - bh) // 2
            p.drawRoundedRect(x, y, bar_w, bh, 2, 2)
        p.end()


class WideTestButton(QWidget):
    """Reference-style test row: play · label · waveform."""

    clicked = pyqtSignal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("WideTestButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(52)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(text)
        self._enabled = True
        self._sync_style()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        self._play = _PlayCircle()
        self._play.setFixedSize(32, 32)
        lay.addWidget(self._play, 0, Qt.AlignmentFlag.AlignVCenter)

        self._label = QLabel(text)
        self._label.setStyleSheet(
            f"color: {TEXT}; font-size: 14px; font-weight: 500; background: transparent;"
        )
        lay.addWidget(self._label, 1, Qt.AlignmentFlag.AlignVCenter)

        wave = _WaveformBadge()
        wave.setFixedSize(64, 26)
        lay.addWidget(wave, 0, Qt.AlignmentFlag.AlignVCenter)

    def _sync_style(self) -> None:
        if self._enabled:
            self.setStyleSheet(f"""
                WideTestButton {{
                    background: {SURFACE};
                    border: none;
                    border-radius: {RADIUS_MD}px;
                }}
                WideTestButton:hover {{
                    background: {SURFACE_PEARL};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                WideTestButton {{
                    background: {SURFACE};
                    border: none;
                    border-radius: {RADIUS_MD}px;
                    opacity: 0.55;
                }}
            """)

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self._sync_style()
        super().setEnabled(enabled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.isEnabled():
                self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


def device_selection_link(text: str = "手动选择音频设备") -> QPushButton:
    """Text link with chevron — toggles advanced device panel."""
    btn = QPushButton(f"{text}  ›")
    btn.setCheckable(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setAccessibleName(text)
    btn.setStyleSheet(LINK_BTN_STYLE)
    return btn


def collapsible_toggle_btn(text: str) -> QPushButton:
    btn = QPushButton(f"▸  {text}")
    btn.setCheckable(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(f"""
        QPushButton {{
            color: {TEXT_SEC};
            background: transparent;
            border: none;
            font-size: 13px;
            font-weight: 500;
            text-align: left;
            padding: 6px 4px;
        }}
        QPushButton:hover {{
            color: {TEXT};
        }}
    """)

    def _sync(expanded: bool) -> None:
        mark = "▾" if expanded else "▸"
        btn.setText(f"{mark}  {text}")

    btn.toggled.connect(_sync)
    return btn


class SettingsSidebar(QWidget):
    """Stitch-style settings sidebar with brand, status card, and nav."""

    page_changed = pyqtSignal(int)

    _SHAPES = ["general", "model", "polish", "about"]
    _LABELS = ["通用", "模型", "润色", "关于"]

    def __init__(self, nav_icon_fn, version: str = "", parent=None):
        super().__init__(parent)
        self._nav_icon_fn = nav_icon_fn
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(
            f"background: {NAV_BG}; border-right: 1px solid {HAIRLINE};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE_MD, SPACE_LG, SPACE_MD, SPACE_MD)
        root.setSpacing(0)

        from voiceink.ui.tray_icon import create_microphone_icon

        brand = QHBoxLayout()
        brand.setContentsMargins(4, 0, 4, 0)
        brand.setSpacing(10)

        icon = QLabel()
        icon.setFixedSize(32, 32)
        icon.setPixmap(create_microphone_icon(recording=False, size=64).pixmap(32, 32))
        icon.setStyleSheet("background: transparent;")
        icon.setAccessibleName("VoiceInk 图标")
        brand.addWidget(icon)
        name = QLabel("VoiceInk")
        name.setStyleSheet(
            f"color: {TEXT}; font-family: {FONT_DISPLAY}; font-size: 18px;"
            f" font-weight: 600; letter-spacing: 0; background: transparent;"
        )
        brand.addWidget(name, 1)
        root.addLayout(brand)

        root.addSpacing(SPACE_MD)

        status_card = QFrame()
        status_card.setObjectName("sidebarStatusCard")
        status_card.setStyleSheet(f"""
            QFrame#sidebarStatusCard {{
                background: transparent;
                border: none;
            }}
        """)
        status_lay = QVBoxLayout(status_card)
        status_lay.setContentsMargins(12, 10, 12, 10)
        status_lay.setSpacing(4)

        self._status_primary = QLabel("")
        self._status_primary.setWordWrap(True)
        self._status_primary.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 500;"
            f" background: transparent;"
        )
        status_lay.addWidget(self._status_primary)

        self._status_secondary = QLabel("")
        self._status_secondary.setWordWrap(False)
        self._status_secondary.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; background: transparent;"
        )
        status_lay.addWidget(self._status_secondary)

        self._status_wrap = status_card
        self._status_wrap.setVisible(False)
        root.addWidget(self._status_wrap)

        root.addSpacing(SPACE_MD)

        self._buttons: list[QPushButton] = []
        nav_col = QVBoxLayout()
        nav_col.setContentsMargins(0, 0, 0, 0)
        nav_col.setSpacing(6)
        for shape, label in zip(self._SHAPES, self._LABELS):
            btn = QPushButton(label)
            btn.setObjectName("settingsNavBtn")
            btn.setCheckable(True)
            btn.setIcon(nav_icon_fn(shape))
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(42)
            btn.setToolTip(label)
            btn.setAccessibleName(f"设置：{label}")
            btn.clicked.connect(lambda checked, i=len(self._buttons): self._select(i))
            self._buttons.append(btn)
            nav_col.addWidget(btn)
        root.addLayout(nav_col)

        root.addStretch(1)

        footer = QHBoxLayout()
        footer.setContentsMargins(4, SPACE_SM, 4, 0)
        self._footer_status = QLabel(version)
        self._footer_status.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 12px; font-weight: 500; background: transparent;"
        )
        footer.addWidget(self._footer_status, 1)
        root.addLayout(footer)

        self.set_active(0)

    def _select(self, index: int) -> None:
        self.set_active(index)
        self.page_changed.emit(index)

    def set_active(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            active = i == index
            btn.setChecked(active)
            btn.setIcon(self._nav_icon_fn(self._SHAPES[i], active=active))

    def set_status_line(self, primary: str, secondary: str = "") -> None:
        primary = primary.strip()
        secondary = secondary.strip()
        self._status_primary.setText(primary)
        self._status_secondary.setText(secondary)
        self._status_secondary.setVisible(bool(secondary))
        self._status_wrap.setVisible(bool(primary or secondary))

    def set_footer_status(self, text: str) -> None:
        self.set_status_line((text or "就绪").strip(), self._status_secondary.text())


def _option_text_column(title: str, subtitle: str) -> QWidget:
    wrap = QWidget()
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(SPACE_MD, 10, SPACE_SM, 10)
    lay.setSpacing(0)
    lay.addWidget(option_row(title, subtitle), 1)
    return wrap


class RadioOptionRow(QWidget):
    """Full-width selectable row; click anywhere or press Space to select."""

    def __init__(self, title: str, subtitle: str, radio_button, parent=None):
        super().__init__(parent)
        self._radio = radio_button
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(title)
        if subtitle:
            self.setAccessibleDescription(subtitle)
        radio_button.setAccessibleName(title)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_option_text_column(title, subtitle), 1)
        radio_button.setText("")
        radio_button.setCursor(Qt.CursorShape.PointingHandCursor)
        lay.addWidget(radio_button)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._radio.setChecked(True)
            self.setFocus()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._radio.setChecked(True)
            event.accept()
            return
        super().keyPressEvent(event)


class SwitchControl(QCheckBox):
    """iOS/Huawei-style pill switch (reference general-settings toggles)."""

    toggled = pyqtSignal(bool)

    _TRACK_W = 44
    _TRACK_H = 24
    _KNOB_MARGIN = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SwitchControl")
        self._checked = False
        self._knob_pos = 0.0
        self._hover = False
        self._anim: QPropertyAnimation | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setProperty("accessibleRole", "CheckBox")
        self.setProperty("accessibleChecked", False)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "SwitchControl { background: transparent; border: none; }"
            "SwitchControl::indicator { width: 0; height: 0; border: none; }"
        )
        self.setFixedSize(self._TRACK_W, self._TRACK_H)

    def _track_color(self) -> QColor:
        if self._checked or self._knob_pos > 0.5:
            return QColor(ACCENT_FOCUS if self._hover else ACCENT)
        rgb = TOGGLE_OFF_TRACK_HOVER if self._hover else TOGGLE_OFF_TRACK
        return QColor(rgb[0], rgb[1], rgb[2], rgb[3])

    def _get_knob_pos(self) -> float:
        return self._knob_pos

    def _set_knob_pos(self, value: float) -> None:
        self._knob_pos = value
        self.update()

    knob_pos = pyqtProperty(float, _get_knob_pos, _set_knob_pos)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, *, animate: bool = True) -> None:
        checked = bool(checked)
        if self._checked == checked and (
            (checked and self._knob_pos >= 0.99) or (not checked and self._knob_pos <= 0.01)
        ):
            return
        self._checked = checked
        super().setChecked(checked)
        self.setProperty("accessibleChecked", checked)
        target = 1.0 if checked else 0.0
        if animate and self.isVisible():
            if self._anim is not None:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"knob_pos", self)
            self._anim.setDuration(220)
            self._anim.setStartValue(self._knob_pos)
            self._anim.setEndValue(target)
            self._anim.setEasingCurve(QEasingCurve.Type.OutQuart)
            self._anim.start()
        else:
            self._knob_pos = target
            self.update()
        if not self.signalsBlocked():
            self.toggled.emit(checked)

    def blockSignals(self, block: bool) -> bool:
        return super().blockSignals(block)

    def set_hovered(self, hovered: bool) -> None:
        hovered = bool(hovered)
        if self._hover == hovered:
            return
        self._hover = hovered
        self.update()

    def enterEvent(self, event):
        self.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_hovered(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.setFocus()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self._TRACK_W, self._TRACK_H
        radius = h / 2.0
        if self.hasFocus():
            focus_pen = QPen(QColor(ACCENT_FOCUS), 2)
            focus_pen.setCosmetic(True)
            p.setPen(focus_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), radius - 1, radius - 1)
        on = self._checked or self._knob_pos > 0.5

        # Same outer track geometry in both states — avoid 1px pen shrinking OFF state.
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._track_color())
        p.drawRoundedRect(0, 0, w, h, radius, radius)

        if not on:
            border = QColor(CONTROL_BORDER)
            border.setAlpha(90)
            pen = QPen(border, 1)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(
                QRectF(0.5, 0.5, w - 1, h - 1), radius - 0.5, radius - 0.5,
            )

        knob_d = h - self._KNOB_MARGIN * 2
        travel = w - knob_d - self._KNOB_MARGIN * 2
        knob_x = self._KNOB_MARGIN + int(travel * self._knob_pos)
        knob_y = self._KNOB_MARGIN

        shadow = QColor(0, 0, 0, 36 if on else 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(knob_x, knob_y + 1, knob_d, knob_d)

        p.setBrush(QColor(SURFACE))
        p.drawEllipse(knob_x, knob_y, knob_d, knob_d)
        p.end()

    def sizeHint(self):
        return QSize(self._TRACK_W, self._TRACK_H)

    def minimumSizeHint(self):
        return QSize(self._TRACK_W, self._TRACK_H)


class ToggleOptionRow(QWidget):
    """Full-width toggle row with explicit title/subtitle.

    Must be a QWidget (not QCheckBox): QAbstractButton sizeHint ignores child
    layouts and uses Fixed vertical policy, which collapses the row to 0 height.
    """

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("ToggleOptionRow")
        self._hover = False
        self._switch = SwitchControl()
        self._switch.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._switch.setAccessibleName(title)
        if subtitle:
            self._switch.setAccessibleDescription(subtitle)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setProperty("accessibleRole", "CheckBox")
        self.setProperty("accessibleChecked", False)
        self._switch.toggled.connect(
            lambda checked: self.setProperty("accessibleChecked", checked)
        )
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAccessibleName(title)
        if subtitle:
            self.setAccessibleDescription(subtitle)
        self._sync_row_style()

        text_col = _option_text_column(title, subtitle)
        _set_click_through(text_col)

        switch_slot = QWidget()
        switch_slot.setFixedSize(SwitchControl._TRACK_W, SwitchControl._TRACK_H)
        switch_slot.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        slot_lay = QHBoxLayout(switch_slot)
        slot_lay.setContentsMargins(0, 0, 0, 0)
        slot_lay.addWidget(self._switch)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 16, 0)
        lay.setSpacing(12)
        lay.addWidget(text_col, 1)
        lay.addWidget(switch_slot, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

    def _toggle(self) -> None:
        self._switch.setChecked(not self._switch.isChecked())
        self.setFocus()

    def _sync_row_style(self) -> None:
        hover_bg = ROW_HOVER if self._hover else "transparent"
        self.setStyleSheet(f"""
            ToggleOptionRow {{
                background: {hover_bg};
                border-radius: {RADIUS_SM}px;
            }}
            ToggleOptionRow:focus {{
                border: 2px solid {ACCENT_FOCUS};
            }}
        """)

    def enterEvent(self, event):
        self._hover = True
        self._switch.set_hovered(True)
        self._sync_row_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._switch.set_hovered(False)
        self._sync_row_style()
        super().leaveEvent(event)

    @property
    def toggled(self):
        return self._switch.toggled

    def isChecked(self) -> bool:
        return self._switch.isChecked()

    def setChecked(self, checked: bool) -> None:
        self._switch.setChecked(checked, animate=False)
        self.setProperty("accessibleChecked", bool(checked))

    def blockSignals(self, block: bool) -> bool:
        return self._switch.blockSignals(block)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._toggle()
            event.accept()
            return
        super().keyPressEvent(event)


def _set_click_through(widget: QWidget) -> None:
    """Let parent rows receive clicks across labels and padding."""
    widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    for child in widget.findChildren(QWidget):
        child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class SettingsPage(QScrollArea):
    """Scrollable content shell with consistent margins."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        body = QWidget()
        body.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        self._layout = QVBoxLayout(body)
        self._layout.setContentsMargins(PAGE_MARGIN_H, PAGE_MARGIN_V, PAGE_MARGIN_H, PAGE_MARGIN_V)
        self._layout.setSpacing(SPACE_XL)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(body)

    def set_compact(self, compact: bool = True) -> None:
        m = (18, 12, 18, 14) if compact else (PAGE_MARGIN_H, PAGE_MARGIN_V, PAGE_MARGIN_H, PAGE_MARGIN_V)
        self._layout.setContentsMargins(*m)

    def set_spacing(self, px: int) -> None:
        self._layout.setSpacing(px)

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)

    def add_stretch(self) -> None:
        self._layout.addStretch(1)
