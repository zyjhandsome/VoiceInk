from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
import math


class _DotIndicator(QWidget):
    """Small animated dot that pulses to indicate active state."""

    def __init__(self, color: str = "#FF6B6B", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(12, 12)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def start_pulse(self):
        self._pulse = 0.0
        self._timer.start(50)

    def stop_pulse(self):
        self._timer.stop()
        self._pulse = 0.0
        self.update()

    def _tick(self):
        self._pulse += 0.15
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        alpha = int(80 + 60 * abs(math.sin(self._pulse))) if self._timer.isActive() else 160
        outer = QColor(self._color)
        outer.setAlpha(alpha)
        p.setBrush(outer)
        p.drawEllipse(0, 0, 12, 12)

        p.setBrush(self._color)
        p.drawEllipse(3, 3, 6, 6)
        p.end()


class WaveformWidget(QWidget):

    NUM_BARS = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 0.0
        self._bar_heights = [0.0] * self.NUM_BARS
        self._phase = 0.0
        self.setFixedHeight(30)
        self.setMinimumWidth(200)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        self._phase = 0.0
        self._timer.start(50)

    def stop(self):
        self._timer.stop()
        self._bar_heights = [0.0] * self.NUM_BARS
        self.update()

    def set_volume(self, volume: float):
        self._volume = min(volume * 8, 1.0)

    def _animate(self):
        self._phase += 0.3
        for i in range(self.NUM_BARS):
            wave = math.sin(self._phase + i * 0.5) * 0.5 + 0.5
            target = wave * self._volume
            self._bar_heights[i] += (target - self._bar_heights[i]) * 0.4
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_width = max(3, (w - (self.NUM_BARS - 1) * 3) // self.NUM_BARS)
        total_width = self.NUM_BARS * bar_width + (self.NUM_BARS - 1) * 3
        x_offset = (w - total_width) // 2

        for i in range(self.NUM_BARS):
            bar_h = max(3, int(self._bar_heights[i] * (h - 4)))
            x = x_offset + i * (bar_width + 3)
            y = (h - bar_h) // 2

            green_val = int(180 + self._bar_heights[i] * 75)
            painter.setBrush(QColor(100, green_val, 255, 220))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_h, 2, 2)

        painter.end()


class FloatingWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_window()
        self._setup_ui()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(360, 120)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget()
        self._container.setObjectName("container")
        self._container.setStyleSheet("""
            #container {
                background-color: rgba(36, 36, 44, 238);
                border-radius: 16px;
                border: none;
            }
        """)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(20, 14, 20, 14)
        container_layout.setSpacing(6)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addStretch()

        self._dot = _DotIndicator()
        status_row.addWidget(self._dot)

        self._status_label = QLabel("准备中...")
        self._status_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self._status_label.setStyleSheet("color: white; background: transparent;")
        status_row.addWidget(self._status_label)

        status_row.addStretch()
        container_layout.addLayout(status_row)

        self._waveform = WaveformWidget()
        container_layout.addWidget(self._waveform)

        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Microsoft YaHei", 9))
        self._text_label.setStyleSheet("color: rgba(220, 220, 230, 200); background: transparent;")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setWordWrap(True)
        self._text_label.setMaximumHeight(36)
        container_layout.addWidget(self._text_label)

        layout.addWidget(self._container)

    def _position_on_screen(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + geo.height() - self.height() - 80
            self.move(x, y)

    def _set_state(self, text: str, color: str, pulse: bool = False):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; background: transparent;")
        self._dot.set_color(color)
        if pulse:
            self._dot.start_pulse()
        else:
            self._dot.stop_pulse()

    def show_recording(self):
        self._hide_timer.stop()
        self._set_state("录音中", "#FF6B6B", pulse=True)
        self._text_label.setText("")
        self._waveform.show()
        self._waveform.start()
        self._position_on_screen()
        self.show()

    def show_recognizing(self, partial_text: str = ""):
        self._hide_timer.stop()
        self._set_state("识别中", "#FFD93D", pulse=True)
        self._waveform.stop()
        self._waveform.hide()
        if partial_text:
            display = partial_text if len(partial_text) <= 50 else "..." + partial_text[-47:]
            self._text_label.setText(display)
        self.show()

    def show_polishing(self, text: str = ""):
        self._hide_timer.stop()
        self._set_state("润色中", "#6BCB77", pulse=True)
        self._waveform.stop()
        self._waveform.hide()
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)
        self.show()

    def show_success(self, message: str = "已输入"):
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#6BCB77")
        self._text_label.setText("")
        self._hide_timer.start(1500)

    def show_cancelled(self):
        self._waveform.stop()
        self._waveform.hide()
        self._set_state("已取消", "#999999")
        self._text_label.setText("")
        self._hide_timer.start(1000)

    def show_error(self, message: str):
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#FF6B6B")
        self._text_label.setText("")
        self._position_on_screen()
        self.show()
        self._hide_timer.start(2000)

    def update_volume(self, volume: float):
        self._waveform.set_volume(volume)

    def update_partial_text(self, text: str):
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)

    def show_model_loading(self):
        self._hide_timer.stop()
        self._set_state("模型加载中", "#FFD93D", pulse=True)
        self._waveform.hide()
        self._text_label.setText("首次使用需下载模型，请稍候...")
        self._position_on_screen()
        self.show()
