from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFontMetrics, QPainter, QColor, QFont, QCursor
import math

from voiceink.ui.design_tokens import (
    FLOAT_TEXT,
    FONT,
    FONT_DISPLAY,
    STATE_ERROR,
    STATE_LISTEN,
    STATE_MUTED,
    STATE_POLISH,
    STATE_RECOGNIZE,
    STATE_RECORD,
    STATE_SUCCESS,
    STATE_WARN,
)
from voiceink.ui.island_chrome import island_container_css, island_window_flags, position_island

COMPACT_HEIGHT = 64
EXPANDED_MIN_HEIGHT = 168


class _DotIndicator(QWidget):
    """Listening ring that pulses while a session is active."""

    def __init__(self, color: str = STATE_RECORD, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(16, 16)

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

        if self._timer.isActive():
            alpha = int(40 + 40 * abs(math.sin(self._pulse)))
            outer = QColor(self._color)
            outer.setAlpha(alpha)
            p.setBrush(outer)
            p.drawEllipse(0, 0, 16, 16)

        pen = self._color
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        from PyQt6.QtGui import QPen
        ring = QPen(self._color)
        ring.setWidth(2)
        p.setPen(ring)
        p.drawEllipse(2, 2, 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(6, 6, 4, 4)
        p.end()


class WaveformWidget(QWidget):

    NUM_BARS = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = 0.0
        self._bar_heights = [0.0] * self.NUM_BARS
        self._phase = 0.0
        self._accent = QColor(FLOAT_TEXT)
        self.setFixedHeight(18)
        self.setFixedWidth(72)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def set_accent(self, color: str):
        self._accent = QColor(color)

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
        gap = 2
        bar_width = max(2, (w - (self.NUM_BARS - 1) * gap) // self.NUM_BARS)
        total_width = self.NUM_BARS * bar_width + (self.NUM_BARS - 1) * gap
        x_offset = (w - total_width) // 2

        for i in range(self.NUM_BARS):
            bar_h = max(3, int(self._bar_heights[i] * (h - 2)))
            x = x_offset + i * (bar_width + gap)
            y = (h - bar_h) // 2

            fill = QColor(self._accent)
            fill.setAlpha(int(100 + self._bar_heights[i] * 155))
            painter.setBrush(fill)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_width, bar_h, 1, 1)

        painter.end()


class FloatingWindow(QWidget):

    continuous_stop_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    history_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listening_active = False
        self._model_loading_active = False
        self._current_accent = FLOAT_TEXT
        self._mode = "compact"
        self._setup_window()
        self._setup_ui()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def island_mode(self) -> str:
        return self._mode

    def set_input_source(self, source: str) -> None:
        self._source = source or "microphone"
        mic = self._source in ("microphone", "mixed", "mic")
        system = self._source in ("system", "mixed")
        self._mic_chip.setProperty("islandOn", mic)
        self._sys_chip.setProperty("islandOn", system)
        self._paint_source_chips()

    def _paint_source_chips(self) -> None:
        from voiceink.ui import design_tokens as tok

        def css(on: bool) -> str:
            if on:
                return (
                    f"QLabel {{ background: {tok.ISLAND_MINT}; color: #0A0A0C;"
                    f" border: none; border-radius: 11px; padding: 0 8px;"
                    f" font-size: {tok.TYPE_CAPTION}px; }}"
                )
            return (
                f"QLabel {{ background: transparent; color: {tok.FLOAT_TEXT_SEC};"
                f" border: 1px solid {tok.FLOAT_BORDER}; border-radius: 11px; padding: 0 8px;"
                f" font-size: {tok.TYPE_CAPTION}px; }}"
            )

        self._mic_chip.setStyleSheet(css(bool(self._mic_chip.property("islandOn"))))
        self._sys_chip.setStyleSheet(css(bool(self._sys_chip.property("islandOn"))))

    def reapply_theme(self) -> None:
        from voiceink.ui import design_tokens as tok

        self._container.setStyleSheet(island_container_css())
        self._status_label.setFont(
            QFont(tok.UI_FONT_FAMILY, tok.TYPE_BODY_SM, QFont.Weight.DemiBold)
        )
        self._status_label.setStyleSheet(
            f"color: {tok.FLOAT_TEXT}; background: transparent;"
            f" font-family: {tok.FONT_DISPLAY}; letter-spacing: -0.2px;"
        )
        ghost = f"""
            QPushButton {{
                background: {tok.CHIP_BG};
                color: {tok.FLOAT_TEXT};
                border: none;
                font-size: {tok.TYPE_CAPTION}px;
                font-weight: 500;
                border-radius: 14px;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background: {tok.CHIP_BG_HOVER};
                color: {tok.FLOAT_TEXT};
            }}
            QPushButton:pressed {{
                background: {tok.CHIP_BG_PRESS};
            }}
        """
        self._close_btn.setStyleSheet(ghost)
        self._end_btn.setStyleSheet(f"""
            QPushButton {{
                background: {tok.ACCENT};
                color: {tok.ACCENT_ON_DARK};
                border: none;
                font-size: {tok.TYPE_CAPTION}px;
                font-weight: 500;
                border-radius: 14px;
                padding: 0px 10px;
            }}
            QPushButton:hover {{
                background: {tok.ACCENT_HV};
                color: {tok.ACCENT_ON_DARK};
            }}
        """)
        for btn in (self._history_btn, self._settings_btn):
            btn.setStyleSheet(ghost)
        self._paint_source_chips()
        self._text_label.setFont(QFont(tok.UI_FONT_FAMILY, tok.TYPE_BODY))
        self._text_label.setStyleSheet(
            f"color: {tok.FLOAT_TEXT}; background: transparent;"
            f" font-family: {tok.FONT}; letter-spacing: -0.2px;"
        )
        self._current_accent = tok.FLOAT_TEXT

    def _setup_window(self):
        self.setWindowFlags(island_window_flags() | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumSize(300, COMPACT_HEIGHT)
        self.resize(320, COMPACT_HEIGHT)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._container = QWidget()
        self._container.setObjectName("islandContainer")

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(14, 10, 10, 10)
        container_layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.setContentsMargins(0, 0, 0, 0)

        self._dot = _DotIndicator()
        header_row.addWidget(self._dot)

        self._waveform = WaveformWidget()
        header_row.addWidget(self._waveform)

        from voiceink.ui import design_tokens as tok

        self._status_label = QLabel("准备中...")
        self._status_label.setFont(
            QFont(tok.UI_FONT_FAMILY, tok.TYPE_BODY_SM, QFont.Weight.DemiBold)
        )
        header_row.addWidget(self._status_label)
        self._mic_chip = QLabel("麦克风")
        self._sys_chip = QLabel("电脑播放")
        for chip in (self._mic_chip, self._sys_chip):
            chip.setFixedHeight(22)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            header_row.addWidget(chip)
        self._source = "microphone"
        header_row.addStretch()

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.setToolTip("关闭浮窗")
        self._close_btn.setAccessibleName("关闭浮窗")
        self._close_btn.clicked.connect(self._on_close_clicked)
        header_row.addWidget(self._close_btn)
        container_layout.addLayout(header_row)

        self._text_label = QLabel("")
        self._text_label.setFont(QFont(tok.UI_FONT_FAMILY, tok.TYPE_BODY))
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._text_label.setWordWrap(True)
        self._text_label.setMaximumHeight(36)
        container_layout.addWidget(self._text_label)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._end_btn = QPushButton("结束")
        self._history_btn = QPushButton("历史")
        self._settings_btn = QPushButton("设置")
        for btn in (self._end_btn, self._history_btn, self._settings_btn):
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(28)
            actions.addWidget(btn)
        self._end_btn.clicked.connect(self._on_end_clicked)
        self._history_btn.clicked.connect(self.history_requested.emit)
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        self._actions_host = QWidget()
        self._actions_host.setLayout(actions)
        container_layout.addWidget(self._actions_host)

        layout.addWidget(self._container)
        self.reapply_theme()
        self.set_input_source("microphone")
        self._set_mode("compact")

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        expanded = mode == "expanded"
        self._actions_host.setVisible(expanded)
        self._mic_chip.setVisible(expanded)
        self._sys_chip.setVisible(expanded)
        if expanded:
            self._text_label.setMaximumHeight(96)
            self.setMinimumWidth(400)
            self.setFixedHeight(max(EXPANDED_MIN_HEIGHT, self.sizeHint().height()))
            self.resize(420, self.height())
        else:
            self._text_label.setMaximumHeight(36)
            self.setMinimumWidth(300)
            self.setFixedHeight(COMPACT_HEIGHT)
            self.resize(320, COMPACT_HEIGHT)

    def expand_live(self, text: str = "") -> None:
        self._hide_timer.stop()
        if text:
            self._text_label.setText(text)
        self._text_label.show()
        self._set_mode("expanded")
        self._present()

    def collapse_live(self) -> None:
        if not self._listening_active:
            return
        self._text_label.hide()
        self._set_mode("compact")
        self._present()

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

    def _on_end_clicked(self) -> None:
        self.continuous_stop_requested.emit()

    def _position_on_screen(self):
        position_island(self, width=self.width())

    def _present(self) -> None:
        self._hide_timer.stop()
        self._update_close_button()
        self._position_on_screen()
        self.show()

    def _set_state(self, text: str, color: str, pulse: bool = False):
        self._current_accent = color
        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            f"color: {color}; background: transparent;"
            f" font-family: {FONT_DISPLAY}; letter-spacing: -0.2px;"
        )
        self._dot.set_color(color)
        self._waveform.set_accent(color)
        if pulse:
            self._dot.start_pulse()
        else:
            self._dot.stop_pulse()

    def _restore_compact_height(self) -> None:
        self._text_label.setMaximumHeight(36)
        self._text_label.setToolTip("")
        self._text_label.show()
        self._set_mode("compact")

    def show_listening(self):
        self._restore_compact_height()
        self._model_loading_active = False
        self._listening_active = True
        self._set_state("正在听", STATE_LISTEN, pulse=False)
        self._text_label.setText("")
        self._text_label.hide()
        self.unsetCursor()
        self._waveform.show()
        self._waveform.start()
        self._present()

    def show_continuous_idle(self, hotkey: str):
        self._model_loading_active = False
        self._restore_compact_height()
        self._listening_active = False
        self._set_state("待开始", STATE_MUTED, pulse=False)
        self._text_label.setText(f"按住 {hotkey} 开始持续监听")
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._present()

    def show_continuous_stopped(self):
        self._restore_compact_height()
        self._listening_active = False
        self._set_state("已停止监听", STATE_MUTED, pulse=False)
        self._text_label.setText("")
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._present()

    def show_recording(self):
        self._restore_compact_height()
        self._listening_active = False
        self._set_state("录音中", STATE_RECORD, pulse=True)
        self._text_label.setText("松开结束，Esc 取消")
        self._waveform.show()
        self._waveform.start()
        self._present()

    def dismiss_if_idle(self):
        self._model_loading_active = False
        self._listening_active = False
        self._set_mode("compact")
        self.unsetCursor()
        self._waveform.stop()
        self._waveform.hide()
        self._dot.stop_pulse()
        self._hide_timer.stop()
        self.hide()

    def show_recognizing(self, partial_text: str = ""):
        self._restore_compact_height()
        self._set_state("正在识别", STATE_RECOGNIZE, pulse=False)
        self._waveform.stop()
        self._waveform.hide()
        if partial_text:
            display = partial_text if len(partial_text) <= 50 else "..." + partial_text[-47:]
            self._text_label.setText(display)
        self._present()

    def show_polishing(self, text: str = ""):
        self._restore_compact_height()
        self._set_state("润色中", STATE_POLISH, pulse=False)
        self._waveform.stop()
        self._waveform.hide()
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)
        self._present()

    def show_success(self, message: str = "已输入", subtitle: str = ""):
        self._restore_compact_height()
        self._model_loading_active = False
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, STATE_SUCCESS)
        self._text_label.setText(subtitle)
        self._present()
        dur = 2200 if subtitle else 1500
        self._hide_timer.start(dur)

    def show_info(self, message: str, subtitle: str = ""):
        self._restore_compact_height()
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, STATE_RECOGNIZE, pulse=False)
        self._text_label.setText(subtitle)
        self._present()
        dur = 2200 if subtitle else 1800
        self._hide_timer.start(dur)

    def show_warning(self, message: str, subtitle: str = ""):
        if self._model_loading_active:
            return
        self._restore_compact_height()
        self._waveform.stop()
        self._waveform.hide()
        self._set_state(message, STATE_WARN, pulse=False)
        self._text_label.setText(subtitle)
        self._present()
        self._hide_timer.start(5000)

    def show_cancelled(self):
        self._restore_compact_height()
        self._waveform.stop()
        self._waveform.hide()
        self._set_state("已取消", STATE_MUTED)
        self._text_label.setText("")
        self._present()
        self._hide_timer.start(1000)

    def show_error(self, message: str, *, auto_dismiss_ms: int = 5000):
        if self._model_loading_active:
            return
        self._set_mode("compact")
        self._waveform.stop()
        self._waveform.hide()
        if "：" in message:
            status, remainder = message.split("：", 1)
            status = status.split("\n", 1)[0]
        else:
            status = message[:12]
            remainder = message[12:]
        self._set_state(status, STATE_ERROR)
        self.setToolTip(message)
        remainder = remainder.strip()
        if remainder:
            metrics = QFontMetrics(self._text_label.font())
            avail = max(80, self.width() - 48)
            self._text_label.setText(
                metrics.elidedText(remainder, Qt.TextElideMode.ElideRight, avail)
            )
            self._text_label.setToolTip(message)
            self._text_label.show()
            self.setFixedHeight(COMPACT_HEIGHT + 24)
        else:
            self._text_label.setText("")
            self._text_label.setToolTip("")
            self._text_label.hide()
            self.setFixedHeight(COMPACT_HEIGHT)
        self._present()
        if auto_dismiss_ms and auto_dismiss_ms > 0:
            self._hide_timer.start(auto_dismiss_ms)
        else:
            self._hide_timer.stop()

    def update_volume(self, volume: float):
        self._waveform.set_volume(volume)

    def show_busy_transcribing(self):
        self._restore_compact_height()
        self._set_state("请稍候", STATE_RECOGNIZE, pulse=False)
        self._text_label.setText("正在识别上一轮语音，稍后重试")
        self._waveform.stop()
        self._waveform.hide()
        self._present()
        self._hide_timer.start(2200)

    def update_partial_text(self, text: str):
        if text:
            display = text if len(text) <= 50 else "..." + text[-47:]
            self._text_label.setText(display)
            if self._listening_active:
                self.expand_live(display)

    def show_model_loading(self, detail: str = ""):
        self._listening_active = False
        self._restore_compact_height()
        self._model_loading_active = True
        self._set_state("模型载入中", STATE_RECOGNIZE, pulse=False)
        self._waveform.hide()
        self._text_label.setText(
            detail or "模型文件已下载，正在载入内存（FireRedASR2 约需 10-40 秒）…"
        )
        self._present()

    def clear_model_loading_lock(self) -> None:
        self._model_loading_active = False

    def mousePressEvent(self, event):
        if self._listening_active and self._mode == "expanded":
            widget = self.childAt(event.pos())
            while widget is not None and widget is not self:
                if widget in (self._status_label, self._dot, self._waveform):
                    self.collapse_live()
                    super().mousePressEvent(event)
                    return
                widget = widget.parentWidget()
        elif self._listening_active and self._mode == "compact":
            self.expand_live(self._text_label.text())
        super().mousePressEvent(event)
