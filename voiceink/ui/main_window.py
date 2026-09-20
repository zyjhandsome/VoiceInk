"""Frameless VoiceInk main-window chrome (sidebar + stack)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from voiceink.ui import design_tokens as tok

NAV_LABELS = ("历史", "通用", "引擎", "润色", "关于")
PAGE_KEYS = ("history", "general", "engine", "polish", "about")
PAGE_OBJECT_NAMES = (
    "pageHistory",
    "pageGeneral",
    "pageEngine",
    "pagePolish",
    "pageAbout",
)

_CAPTION_H = 36
_NAV_BTN_H = 29
_NAV_FONT_PX = 12
_INK_DOT_PX = 8
_WINDOW_W = 960
_WINDOW_H = 640


class MainWindow(QWidget):
    def __init__(self, config, history_store, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._history_store = history_store
        self._page = "general"
        self._setup_window()
        self._setup_ui()
        self.reapply_theme()
        self.show_page("general")

    def _setup_window(self) -> None:
        self.setWindowTitle("VoiceInk")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(_WINDOW_W, _WINDOW_H)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._caption = QWidget()
        self._caption.setFixedHeight(_CAPTION_H)
        cap = QHBoxLayout(self._caption)
        cap.setContentsMargins(12, 0, 8, 0)
        cap.setSpacing(8)

        self._ink_dot = QLabel()
        self._ink_dot.setFixedSize(_INK_DOT_PX, _INK_DOT_PX)
        self._title = QLabel("VoiceInk")

        self._min_btn = QPushButton("–")
        self._max_btn = QPushButton("□")
        self._close_btn = QPushButton("×")
        for btn in (self._min_btn, self._max_btn, self._close_btn):
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._min_btn.clicked.connect(self.showMinimized)
        self._max_btn.clicked.connect(self._toggle_maximized)
        self._close_btn.clicked.connect(self.hide)

        cap.addWidget(self._ink_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        cap.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)
        cap.addStretch(1)
        cap.addWidget(self._min_btn)
        cap.addWidget(self._max_btn)
        cap.addWidget(self._close_btn)
        root.addWidget(self._caption)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = QWidget()
        self._sidebar.setObjectName("mainSidebar")
        self._sidebar.setFixedWidth(tok.SIDEBAR_WIDTH)
        side = QVBoxLayout(self._sidebar)
        side.setContentsMargins(8, 8, 8, 8)
        side.setSpacing(4)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: list[QPushButton] = []
        for index, label in enumerate(NAV_LABELS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(_NAV_BTN_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            key = PAGE_KEYS[index]
            btn.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
            self._nav_group.addButton(btn, index)
            self._nav_buttons.append(btn)
            side.addWidget(btn)
        side.addStretch(1)
        body.addWidget(self._sidebar)

        from voiceink.ui.history_window import HistoryWindow
        from voiceink.ui.settings_window import SettingsWindow

        self._stack = QStackedWidget()
        self._history = HistoryWindow(self._history_store, self)
        self._history.setObjectName(PAGE_OBJECT_NAMES[0])
        self._settings = SettingsWindow(self._config, self)
        self._settings.setObjectName(PAGE_OBJECT_NAMES[1])
        self._stack.addWidget(self._history)
        self._stack.addWidget(self._settings)
        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        self.resize(_WINDOW_W, _WINDOW_H)
        root.activate()

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def show_page(self, key: str) -> None:
        if key not in PAGE_KEYS:
            return
        self._page = key
        settings_index = {
            "general": 0,
            "engine": 1,
            "polish": 2,
            "about": 3,
        }
        if key == "history":
            self._stack.setCurrentIndex(0)
        else:
            self._stack.setCurrentIndex(1)
            self._settings.show_page(settings_index[key])
        nav_index = PAGE_KEYS.index(key)
        btn = self._nav_buttons[nav_index]
        btn.blockSignals(True)
        btn.setChecked(True)
        btn.blockSignals(False)

    def current_page(self) -> str:
        return self._page

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

    def reapply_theme(self) -> None:
        from voiceink.ui import design_tokens as live

        self.setStyleSheet(f"background: {live.BG};")
        self._caption.setStyleSheet(f"background: {live.BG};")
        self._title.setStyleSheet(
            f"color: {live.TEXT}; font-size: {live.TYPE_BODY_SM}px;"
            f" font-weight: 600; background: transparent;"
        )
        self._ink_dot.setStyleSheet(
            f"background: {live.TEXT}; border-radius: {_INK_DOT_PX // 2}px;"
        )
        cap_btn = (
            f"QPushButton {{ background: transparent; color: {live.TEXT_SEC};"
            f" border: none; font-size: {_NAV_FONT_PX}px; }}"
            f"QPushButton:hover {{ color: {live.TEXT};"
            f" background: {live.NAV_SELECTED_BG}; }}"
        )
        for btn in (self._min_btn, self._max_btn, self._close_btn):
            btn.setStyleSheet(cap_btn)
        self._sidebar.setStyleSheet(
            f"QWidget#mainSidebar {{ background: {live.BG};"
            f" border-right: 1px solid {live.HAIRLINE}; }}"
        )
        nav_css = (
            f"QPushButton {{ background: transparent; color: {live.TEXT_SEC};"
            f" border: none; border-radius: {live.RADIUS_MD}px;"
            f" font-size: {_NAV_FONT_PX}px; text-align: left; padding: 0 10px; }}"
            f"QPushButton:checked {{ background: {live.NAV_SELECTED_BG};"
            f" color: {live.TEXT}; }}"
        )
        for btn in self._nav_buttons:
            btn.setStyleSheet(nav_css)
