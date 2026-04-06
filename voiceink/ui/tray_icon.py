from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QBrush, QPen,
    QRadialGradient, QPainterPath, QActionGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QPointF


_MENU_CSS = """
    QMenu {
        background-color: #FFFFFF;
        color: #1A1A1A;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 6px 0px;
        font-family: "Microsoft YaHei", "Segoe UI";
        font-size: 13px;
    }
    QMenu::item {
        padding: 8px 32px 8px 16px;
        margin: 0px 4px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #F0F0F0;
        color: #1A1A1A;
    }
    QMenu::item:disabled {
        color: #AAAAAA;
    }
    QMenu::separator {
        height: 1px;
        background: #EBEBEB;
        margin: 6px 12px;
    }
    QMenu::indicator {
        width: 14px;
        height: 14px;
        margin-left: 6px;
    }
"""


def create_microphone_icon(color: str = "#888888", recording: bool = False, size: int = 64) -> QIcon:
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    cx = s / 2

    if recording:
        bg_grad = QRadialGradient(QPointF(cx, cx), s * 0.45)
        bg_grad.setColorAt(0, QColor("#FF5252"))
        bg_grad.setColorAt(1, QColor("#D32F2F"))
    else:
        bg_grad = QRadialGradient(QPointF(cx, cx), s * 0.45)
        bg_grad.setColorAt(0, QColor("#5C6BC0"))
        bg_grad.setColorAt(1, QColor("#3949AB"))

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
    painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
    painter.drawPath(mic_path)

    painter.setPen(QPen(QColor(180, 180, 200, 120), 1))
    grille_top = mic_y + mic_h * 0.3
    grille_bottom = mic_y + mic_h * 0.7
    for i in range(3):
        y = grille_top + (grille_bottom - grille_top) * i / 2
        painter.drawLine(QPointF(mic_x + mic_w * 0.25, y), QPointF(mic_x + mic_w * 0.75, y))

    arc_pen = QPen(QColor(255, 255, 255, 200), s * 0.035)
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
    quit_app = pyqtSignal()
    auto_start_toggled = pyqtSignal(bool)
    model_switched = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._normal_icon = create_microphone_icon(recording=False)
        self._recording_icon = create_microphone_icon(recording=True)

        self.setIcon(self._normal_icon)
        self.setToolTip("VoiceInk - 语音转文字")

        self._model_menu = None
        self._model_group = None
        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet(_MENU_CSS)

        settings_action = menu.addAction("打开设置")
        settings_action.triggered.connect(self.open_settings.emit)

        menu.addSeparator()

        self._model_menu = menu.addMenu("切换模型")
        self._model_menu.setStyleSheet(_MENU_CSS)
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
        self._model_menu.clear()

        if not downloaded_models:
            empty = self._model_menu.addAction("暂无已下载模型")
            empty.setEnabled(False)
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

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings.emit()

    def set_recording(self, is_recording: bool):
        self.setIcon(self._recording_icon if is_recording else self._normal_icon)

    def set_auto_start(self, enabled: bool):
        self._auto_start_action.setChecked(enabled)
