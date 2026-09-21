"""Frameless VoiceInk main-window chrome (sidebar + stack)."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QEvent, QRectF, Qt
from PyQt6.QtGui import QKeySequence, QPainterPath, QRegion, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from voiceink.config import DEFAULT_HOTKEY, format_hotkey
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

_CAPTION_H = 42
_NAV_BTN_H = 40
_NAV_FONT_PX = 14
_INK_DOT_PX = 8
_WINDOW_W = 960
_WINDOW_H = 640


class MainWindow(QWidget):
    def __init__(self, config, history_store, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._history_store = history_store
        self._page = "general"
        self._drag_offset = None
        self._setup_window()
        self._setup_ui()
        self.reapply_theme()
        self.show_page("general")
        self._nav_buttons[1].setFocus(Qt.FocusReason.OtherFocusReason)

    def _setup_window(self) -> None:
        self.setWindowTitle("VoiceInk")
        self.setObjectName("mainWindow")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.resize(_WINDOW_W, _WINDOW_H)
        self.setMinimumSize(880, 580)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        self._caption = QWidget()
        self._caption.setObjectName("mainCaption")
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
            btn.setFixedSize(36, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        for btn, text in ((self._min_btn, "最小化"), (self._max_btn, "最大化 / 还原"),
                          (self._close_btn, "关闭窗口，保留托盘运行")):
            btn.setAccessibleName(text)
            btn.setToolTip(text)

        self._min_btn.clicked.connect(self.showMinimized)
        self._max_btn.clicked.connect(self._toggle_maximized)
        self._close_btn.clicked.connect(self.hide)

        cap.addWidget(self._ink_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        cap.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)
        cap.addStretch(1)
        cap.addWidget(self._min_btn)
        cap.addWidget(self._max_btn)
        cap.addWidget(self._close_btn)
        for handle in (self._caption, self._title, self._ink_dot):
            handle.installEventFilter(self)
        root.addWidget(self._caption)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = QWidget()
        self._sidebar.setObjectName("mainSidebar")
        self._sidebar.setFixedWidth(tok.SIDEBAR_WIDTH)
        side = QVBoxLayout(self._sidebar)
        side.setContentsMargins(12, 18, 12, 16)
        side.setSpacing(4)

        self._nav_heading = QLabel("工作空间")
        side.addWidget(self._nav_heading)
        side.addSpacing(8)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: list[QPushButton] = []
        for index, label in enumerate(NAV_LABELS):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(_NAV_BTN_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            btn.setAccessibleName(label)
            btn.setToolTip(f"{label}  ·  Ctrl+{index + 1}")
            key = PAGE_KEYS[index]
            btn.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
            self._nav_group.addButton(btn, index)
            self._nav_buttons.append(btn)
            side.addWidget(btn)
        side.addStretch(1)
        self._runtime_label = QLabel("状态待确认")
        self._runtime_label.setWordWrap(True)
        self._runtime_label.setAccessibleName("当前运行状态")
        self._mode_label = QLabel()
        self._mode_label.setWordWrap(True)
        self._shortcut_label = QLabel()
        self._shortcut_label.setWordWrap(True)
        side.addWidget(self._runtime_label)
        side.addSpacing(4)
        side.addWidget(self._mode_label)
        side.addWidget(self._shortcut_label)
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
        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(16, 16)
        self._size_grip.setToolTip("拖动调整窗口大小")
        self._settings.runtime_status_changed.connect(self._runtime_label.setText)
        self._settings.settings_changed.connect(self._refresh_usage_summary)
        self._settings.hotkey_updated.connect(self._refresh_usage_summary)
        self._history.history_preferences_requested.connect(self._open_history_preferences)
        self._settings._history_enabled_row.toggled.connect(self._history.set_history_enabled)
        self._history.set_history_enabled(bool(self._config.get("history.enabled", False)))
        self._refresh_usage_summary()
        self._shortcuts = []
        for index, key in enumerate(PAGE_KEYS):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda k=key: self.show_page(k))
            self._shortcuts.append(shortcut)
        for sequence, callback in (("Ctrl+F", self._focus_history_search), ("Ctrl+W", self.hide)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)
        self._settings.hotkey_capture_started.connect(lambda: self._enable_shortcuts(False))
        self._settings.hotkey_capture_ended.connect(lambda: self._enable_shortcuts(True))

        self.resize(_WINDOW_W, _WINDOW_H)
        root.activate()

    def _enable_shortcuts(self, enabled: bool) -> None:
        for shortcut in self._shortcuts:
            shortcut.setEnabled(enabled)

    def _focus_history_search(self) -> None:
        self.show_page("history")
        self._history._search_edit.setFocus()
        self._history._search_edit.selectAll()

    def _open_history_preferences(self) -> None:
        self.show_page("general")
        row = self._settings._history_enabled_row
        self._settings._pages.widget(0).ensureWidgetVisible(row)
        row.setFocus()

    def _refresh_usage_summary(self, *_args) -> None:
        source = {"microphone": "麦克风", "system": "电脑声", "mixed": "混合音频"}.get(
            self._config.get("audio.input_source", "microphone"), "麦克风")
        continuous = self._config.get("audio.trigger_mode", "continuous") == "continuous"
        self._mode_label.setText(f"{source} · {'持续转写' if continuous else '按住说话'}")
        hotkey = format_hotkey(self._config.get("hotkey", DEFAULT_HOTKEY))
        self._shortcut_label.setText(f"按住 {hotkey}\n" + (
            "停顿出字 · Esc /「结束」停止" if continuous else "松开出字 · Esc 取消"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_size_grip"):
            inset = 6 if self.isMaximized() else 10
            self._size_grip.move(self.width() - 16 - inset, self.height() - 16 - inset)
            self._size_grip.setVisible(not self.isMaximized())
        self._apply_window_shape()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_window_shape()

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.reapply_theme()

    def _chrome_radius(self) -> int:
        return 0 if self.isMaximized() else tok.WINDOW_RADIUS

    def _apply_native_round_corners(self, radius: int) -> None:
        if sys.platform != "win32":
            return
        try:
            from ctypes import byref, c_int, sizeof, windll

            hwnd = int(self.winId())
            if hwnd == 0:
                return
            preference = 1 if radius <= 0 else 2
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, byref(c_int(preference)), sizeof(c_int)
            )
        except Exception:
            pass

    def _apply_window_shape(self) -> None:
        radius = self._chrome_radius()
        self._apply_native_round_corners(radius)
        if radius <= 0:
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), float(radius), float(radius))
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

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

    def _caption_drag_target(self, obj) -> bool:
        return obj in (self._caption, self._title, self._ink_dot)

    def eventFilter(self, obj, event):
        if self._caption_drag_target(obj) and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self._toggle_maximized()
                return True
        if not self._caption_drag_target(obj) or self.isMaximized():
            return super().eventFilter(obj, event)
        etype = event.type()
        if (
            etype == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            return False
        if (
            etype == QEvent.Type.MouseMove
            and self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            return True
        if (
            etype == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_offset = None
        return super().eventFilter(obj, event)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

    def reapply_theme(self) -> None:
        from voiceink.ui import design_tokens as live

        radius = self._chrome_radius()
        self.setStyleSheet(
            f"QWidget#mainWindow {{ background: {live.BG};"
            f" border: 1px solid {live.TEXT_DIM};"
            f" border-radius: {radius}px; }}"
        )
        self._caption.setStyleSheet(
            f"QWidget#mainCaption {{"
            f" background: {live.BG};"
            f" border: none;"
            f" border-bottom: 1px solid {live.CONTROL_BORDER};"
            f" border-top-left-radius: {radius}px;"
            f" border-top-right-radius: {radius}px;"
            f"}}"
        )
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
            f"QPushButton:focus {{ border: 2px solid {live.ACCENT_FOCUS}; }}"
        )
        for btn in (self._min_btn, self._max_btn, self._close_btn):
            btn.setStyleSheet(cap_btn)
        self._sidebar.setStyleSheet(
            f"QWidget#mainSidebar {{ background: {live.NAV_BG};"
            f" border-right: 1px solid {live.HAIRLINE};"
            f" border-bottom-left-radius: {radius}px; }}"
        )
        nav_css = (
            f"QPushButton {{ background: transparent; color: {live.TEXT_SEC};"
            f" border: 2px solid transparent; border-radius: {live.RADIUS_MD}px;"
            f" font-size: {_NAV_FONT_PX}px; text-align: left; padding: 0 10px; }}"
            f"QPushButton:checked {{ background: {live.NAV_SELECTED_BG};"
            f" color: {live.TEXT}; font-weight: 600; }}"
            f"QPushButton:hover:!checked {{ background: {live.ROW_HOVER}; color: {live.TEXT}; }}"
            f"QPushButton:focus {{ border-color: {live.ACCENT_FOCUS}; }}"
        )
        for btn in self._nav_buttons:
            btn.setStyleSheet(nav_css)
        for label in (self._nav_heading, self._mode_label, self._shortcut_label):
            label.setStyleSheet(f"color: {live.TEXT_SEC}; font-size: {live.TYPE_CAPTION}px;"
                               " background: transparent; padding: 4px 8px;")
        self._runtime_label.setStyleSheet(
            f"color: {live.TEXT}; font-size: {live.TYPE_FOOTNOTE}px; font-weight: 600;"
            f" background: {live.NAV_SELECTED_BG}; border-radius: 8px; padding: 10px 8px;")
        self._stack.setStyleSheet(f"background: {live.BG};")
        self._apply_window_shape()
