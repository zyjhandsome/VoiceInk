import sys

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QBrush, QPen,
    QRadialGradient, QPainterPath, QActionGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QRectF, QPointF

def _menu_stylesheet() -> str:
    from voiceink.ui import design_tokens as tok

    # Right padding leaves room for submenu chevron / check indicator.
    pad_right = tok.TRAY_MENU_PAD_H + 22
    return f"""
    QMenu {{
        background-color: {tok.SURFACE};
        color: {tok.TEXT};
        border: 1px solid {tok.TRAY_MENU_BORDER};
        border-radius: {tok.TRAY_MENU_RADIUS}px;
        padding: 4px 0px;
        font-family: {tok.FONT};
        font-size: {tok.TYPE_BODY_SM}px;
    }}
    QMenu::item {{
        padding: {tok.TRAY_MENU_PAD_V}px {pad_right}px {tok.TRAY_MENU_PAD_V}px {tok.TRAY_MENU_PAD_H}px;
        margin: 0px;
        border-radius: 0px;
        background: transparent;
    }}
    QMenu::item:selected {{
        background-color: {tok.TRAY_MENU_HOVER};
        color: {tok.TEXT};
    }}
    QMenu::item:disabled {{
        color: {tok.TRAY_MENU_DISABLED};
        background: transparent;
    }}
    QMenu::separator {{
        height: 1px;
        background: {tok.TRAY_MENU_SEPARATOR};
        margin: 2px 0px;
    }}
    QMenu::indicator {{
        width: 14px;
        height: 14px;
        margin-left: 4px;
    }}
    QMenu::right-arrow {{
        width: 10px;
        height: 10px;
        margin-right: 10px;
    }}
    """


def create_microphone_icon(color: str | None = None, recording: bool = False, size: int = 64) -> QIcon:
    from voiceink.ui import design_tokens as tok

    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    cx = s / 2

    if recording:
        record = QColor(tok.STATE_RECORD)
        darker = QColor(record)
        darker = darker.darker(120)
        bg_grad = QRadialGradient(QPointF(cx, cx), s * 0.45)
        bg_grad.setColorAt(0, record)
        bg_grad.setColorAt(1, darker)
    else:
        top = QColor(color or tok.ACCENT_FOCUS)
        bottom = QColor(color or tok.ACCENT)
        bg_grad = QRadialGradient(QPointF(cx, cx), s * 0.45)
        bg_grad.setColorAt(0, top)
        bg_grad.setColorAt(1, bottom)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(bg_grad))
    margin = s * 0.06
    painter.drawRoundedRect(
        QRectF(margin, margin, s - 2 * margin, s - 2 * margin),
        s * 0.22, s * 0.22
    )

    mic_w = s * 0.22
    mic_h = s * 0.32
    mic_x = cx - mic_w / 2
    mic_y = s * 0.16

    mic_path = QPainterPath()
    mic_path.addRoundedRect(QRectF(mic_x, mic_y, mic_w, mic_h), mic_w / 2, mic_w / 2)
    painter.setBrush(QBrush(QColor(255, 255, 255, 245)))
    painter.drawPath(mic_path)

    painter.setPen(QPen(QColor(255, 255, 255, 80), 1))
    grille_top = mic_y + mic_h * 0.3
    grille_bottom = mic_y + mic_h * 0.7
    for i in range(3):
        y = grille_top + (grille_bottom - grille_top) * i / 2
        painter.drawLine(QPointF(mic_x + mic_w * 0.25, y), QPointF(mic_x + mic_w * 0.75, y))

    arc_pen = QPen(QColor(255, 255, 255, 220), s * 0.035)
    arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(arc_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    arc_w = s * 0.38
    arc_h = s * 0.28
    arc_rect = QRectF(cx - arc_w / 2, s * 0.26, arc_w, arc_h)
    painter.drawArc(arc_rect, 0, -180 * 16)

    stem_top = s * 0.26 + arc_h / 2
    stem_bottom = s * 0.68
    painter.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bottom))

    base_w = s * 0.22
    painter.drawLine(QPointF(cx - base_w / 2, stem_bottom), QPointF(cx + base_w / 2, stem_bottom))

    if recording:
        wave_pen = QPen(QColor(255, 255, 255, 140), s * 0.02)
        wave_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(wave_pen)
        for i, offset in enumerate([s * 0.06, s * 0.12]):
            alpha = 140 - i * 50
            wave_pen.setColor(QColor(255, 255, 255, alpha))
            painter.setPen(wave_pen)
            painter.drawArc(
                QRectF(cx - mic_w / 2 - offset - s * 0.04, s * 0.22, s * 0.08, s * 0.2),
                45 * 16, 90 * 16
            )
            painter.drawArc(
                QRectF(cx + mic_w / 2 + offset - s * 0.04, s * 0.22, s * 0.08, s * 0.2),
                135 * 16, -90 * 16
            )

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    open_settings = pyqtSignal()
    history_requested = pyqtSignal()
    quit_app = pyqtSignal()
    auto_start_toggled = pyqtSignal(bool)
    model_switched = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._icon_kind = "normal"
        self._rebuild_icons()
        self.setIcon(self._normal_icon)
        self._idle_tooltip = "VoiceInk - 就绪"
        self._status_summary = "就绪"
        self.setToolTip(self._idle_tooltip)
        self._flash_timer = None
        self._flash_restore_recording = False

        self._model_menu = None
        self._model_group = None
        self._menu = None
        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _rebuild_icons(self) -> None:
        from voiceink.ui import design_tokens as tok

        self._normal_icon = create_microphone_icon(recording=False)
        self._recording_icon = create_microphone_icon(recording=True)
        self._attention_icon = create_microphone_icon(color=tok.ATTENTION, recording=False)

    def _apply_icon_kind(self, kind: str) -> None:
        self._icon_kind = kind
        if kind == "recording":
            self.setIcon(self._recording_icon)
        elif kind == "attention":
            self.setIcon(self._attention_icon)
        else:
            self.setIcon(self._normal_icon)

    def reapply_theme(self) -> None:
        css = _menu_stylesheet()
        if self._menu is not None:
            self._menu.setStyleSheet(css)
        if self._model_menu is not None:
            self._model_menu.setStyleSheet(css)
        kind = getattr(self, "_icon_kind", "normal")
        self._rebuild_icons()
        self._apply_icon_kind(kind)

    def _setup_menu(self):
        menu_css = _menu_stylesheet()
        menu = QMenu()
        self._menu = menu
        menu.setStyleSheet(menu_css)

        self._status_action = menu.addAction(self._status_summary)
        self._status_action.setEnabled(False)
        menu.addSeparator()

        settings_action = menu.addAction("打开设置")
        settings_action.triggered.connect(self.open_settings.emit)

        history_action = menu.addAction("历史")
        history_action.triggered.connect(self.history_requested.emit)

        menu.addSeparator()

        self._model_menu = menu.addMenu("切换模型")
        self._model_menu.setStyleSheet(menu_css)
        empty = self._model_menu.addAction("加载中...")
        empty.setEnabled(False)

        menu.addSeparator()

        self._auto_start_action = menu.addAction("开机自启")
        self._auto_start_action.setCheckable(True)
        self._auto_start_action.toggled.connect(self.auto_start_toggled.emit)

        menu.addSeparator()

        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.quit_app.emit)

        self.setContextMenu(menu)

    def update_models(self, downloaded_models: list[dict], active_id: str):
        if self._model_group is not None:
            try:
                self._model_group.triggered.disconnect()
            except (TypeError, RuntimeError):
                pass

        self._model_menu.clear()

        if not downloaded_models:
            empty = self._model_menu.addAction("暂无已下载模型")
            empty.setEnabled(False)
            self._model_group = None
            return

        self._model_group = QActionGroup(self._model_menu)
        self._model_group.setExclusive(True)

        for m in downloaded_models:
            action = self._model_menu.addAction(m["name"])
            action.setCheckable(True)
            action.setChecked(m["id"] == active_id)
            action.setData(m["id"])
            self._model_group.addAction(action)

        self._model_group.triggered.connect(
            lambda a: self.model_switched.emit(a.data())
        )

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_activated(self, reason):
        # Windows emits Trigger on the first click of a double-click, then DoubleClick.
        # Handling both opens settings twice; on Windows only respond to double-click.
        if sys.platform == "win32":
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                self.open_settings.emit()
            return
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_settings.emit()

    def set_recording(self, is_recording: bool):
        self._apply_icon_kind("recording" if is_recording else "normal")

    def flash_attention(self, duration_ms: int = 450) -> None:
        """Brief tray icon flash for soft feedback (e.g. short-tap during cooldown)."""
        from PyQt6.QtCore import QTimer

        if self._flash_timer is not None:
            self._flash_timer.stop()
            self._flash_timer.deleteLater()
        self._flash_restore_recording = self._icon_kind == "recording"
        self._apply_icon_kind("attention")
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)

        def _restore():
            self._apply_icon_kind(
                "recording" if self._flash_restore_recording else "normal"
            )
            self._flash_timer = None

        self._flash_timer.timeout.connect(_restore)
        self._flash_timer.start(max(120, int(duration_ms)))

    def set_status_summary(self, text: str) -> None:
        self._status_summary = (text or "就绪").strip()
        self._status_action.setText(self._status_summary)
        self._idle_tooltip = f"VoiceInk - {self._status_summary}"
        self.setToolTip(self._idle_tooltip)

    def set_activity_tooltip(self, state: str | None):
        """Brief tray hint for background work. None = idle."""
        if state is None:
            self.setToolTip(self._idle_tooltip)
            return
        lines = {
            "recording": "录音中",
            "recognizing": "识别中",
            "polishing": "润色中",
            "listening": "监听中",
            "loading": "模型加载中",
        }
        label = lines.get(state, "")
        if label:
            self.setToolTip(f"VoiceInk - {label}")
        else:
            self.setToolTip(self._idle_tooltip)

    def set_auto_start(self, enabled: bool):
        self._auto_start_action.blockSignals(True)
        self._auto_start_action.setChecked(enabled)
        self._auto_start_action.blockSignals(False)
