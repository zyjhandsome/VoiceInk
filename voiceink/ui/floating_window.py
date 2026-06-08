from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QCursor
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

    continuous_stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listening_active = False
        self._model_loading_active = False
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
        container_layout.setContentsMargins(20, 10, 12, 14)
        container_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addStretch()
        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.setToolTip("关闭浮窗")
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(200, 200, 210, 190);
                border: none;
                font-size: 17px;
                font-weight: bold;
                border-radius: 12px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 28);
                color: white;
            }
        """)
        self._close_btn.clicked.connect(self._on_close_clicked)
        header_row.addWidget(self._close_btn)
        container_layout.addLayout(header_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.setContentsMargins(0, 0, 8, 0)
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

    def _update_close_button(self) -> None:
        self._close_btn.setVisible(True)
        self._close_btn.setToolTip(
            "结束整场自动监听" if self._listening_active else "关闭浮窗"
        )

    def _on_close_clicked(self) -> None:
        if self._listening_active:
            self.continuous_stop_requested.emit()
        else:
            self.dismiss_if_idle()

    def _position_on_screen(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + geo.height() - self.height() - 80
            self.move(x, y)

    def _present(self) -> None:
        """Show floating window with close button visible in all states."""
        self._hide_timer.stop()
        self._update_close_button()
        self._position_on_screen()
        self.show()

    def _set_state(self, text: str, color: str, pulse: bool = False):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; background: transparent;")
        self._dot.set_color(color)
        if pulse:
            self._dot.start_pulse()
        else:
            self._dot.stop_pulse()

    def show_listening(self):
        self._model_loading_active = False
        self._listening_active = True
        self._set_state("自动监听中", "#4A90D9", pulse=True)
        self._text_label.setText("说完停顿后自动出字 · 点 × 结束整场监听")
        self.unsetCursor()
        self._waveform.show()
        self._waveform.start()
        self._present()

    def show_continuous_idle(self, hotkey: str):
        """Continuous mode: model ready but user has not started listening yet."""
        self._model_loading_active = False
        self._listening_active = False
        self._set_state("待开始", "#888888", pulse=False)
        self._text_label.setText(f"按住 {hotkey} 开始持续监听")
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._present()

    def show_continuous_stopped(self):
        self._listening_active = False
        self._set_state("已停止监听", "#999999", pulse=False)
        self._text_label.setText("")
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._present()

    def show_recording(self):
        self._listening_active = False
        self._set_state("录音中", "#FF6B6B", pulse=True)
        self._text_label.setText("松开结束 · Esc 取消")
        self._waveform.show()
        self._waveform.start()
        self._present()

    def dismiss_if_idle(self):
        """Hide floating window when recording never started or UI was left visible."""
        self._listening_active = False
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._dot.stop_pulse()
        self._hide_timer.stop()
        self.hide()

    def show_recognizing(self, partial_text: str = ""):
        self._set_state("识别中", "#FFD93D", pulse=True)
        self._waveform.stop()
        self._waveform.hide()
        if partial_text:
            display = partial_text if len(partial_text) <= 50 else "..." + partial_text[-47:]
            self._text_label.setText(display)
        self._present()

    def show_polishing(self, text: str = ""):
        self._set_state("润色中", "#6BCB77", pulse=True)
        self._waveform.stop()
        self._waveform.hide()
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)
        self._present()

    def show_success(self, message: str = "已输入", subtitle: str = ""):
        self._model_loading_active = False
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#6BCB77")
        self._text_label.setText(subtitle)
        self._present()
        dur = 2200 if subtitle else 1500
        self._hide_timer.start(dur)

    def show_info(self, message: str, subtitle: str = ""):
        """Non-error informational state (e.g. polish fallback, soft warnings)."""
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#FFD93D", pulse=False)
        self._text_label.setText(subtitle)
        self._present()
        dur = 2200 if subtitle else 1800
        self._hide_timer.start(dur)

    def show_warning(self, message: str, subtitle: str = ""):
        if self._model_loading_active:
            return
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#FFA94D", pulse=False)
        self._text_label.setText(subtitle)
        self._present()
        self._hide_timer.start(5000)

    def show_cancelled(self):
        self._waveform.stop()
        self._waveform.hide()
        self._set_state("已取消", "#999999")
        self._text_label.setText("")
        self._present()
        self._hide_timer.start(1000)

    def show_error(self, message: str):
        if self._model_loading_active:
            return
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, "#FF6B6B")
        self._text_label.setText("")
        duration = min(8, max(3, len(message) // 10 + 2))
        self._present()
        self._hide_timer.start(duration * 1000)

    def update_volume(self, volume: float):
        self._waveform.set_volume(volume)

    def show_busy_transcribing(self):
        """User tried to record while inference is running."""
        self._set_state("请稍候", "#FFD93D", pulse=False)
        self._text_label.setText("正在识别上一轮语音，稍后重试")
        self._waveform.stop()
        self._waveform.hide()
        self._present()
        self._hide_timer.start(2200)

    def update_partial_text(self, text: str):
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)

    def show_model_loading(self, detail: str = ""):
        self._listening_active = False
        self._model_loading_active = True
        self._set_state("模型加载中", "#FFD93D", pulse=True)
        self._waveform.hide()
        self._text_label.setText(
            detail or "模型文件已下载，正在载入内存（FireRedASR2 约需 10–40 秒）…"
        )
        self._present()

    def clear_model_loading_lock(self) -> None:
        self._model_loading_active = False
