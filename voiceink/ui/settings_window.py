import math
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QFormLayout, QMessageBox, QFrame, QScrollArea,
    QProgressBar, QListWidget, QListWidgetItem, QStackedWidget,
    QFileDialog,     QGraphicsDropShadowEffect, QTextEdit,
    QSizePolicy, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt6.QtGui import QFont, QPainter, QColor, QIcon, QPixmap, QPen

from voiceink.config import (
    Config,
    VERSION,
    format_hotkey,
    TRIGGER_MODE_CONTINUOUS,
    TRIGGER_MODE_HOTKEY,
)
from voiceink.audio_recorder import AudioRecorder
from voiceink.audio_devices import (
    INPUT_SOURCE_MICROPHONE,
    INPUT_SOURCE_MIXED,
    INPUT_SOURCE_SYSTEM,
    list_microphone_devices,
    list_system_capture_devices_for_settings,
    platform_audio_hint,
    sanitize_system_device_index,
)

# ── Design Tokens (Light) ────────────────────────────────────────

_BG        = "#FAFAFA"
_NAV_BG    = "#F0F0F2"
_SURFACE   = "#FFFFFF"
_BORDER    = "#D5D5DA"
_INPUT_BG  = "#F3F3F6"
_TEXT      = "#1D1D1F"
_TEXT_SEC  = "#6E6E73"
_TEXT_DIM  = "#AEAEB2"
_ACCENT    = "#007AFF"
_ACCENT_HV = "#0062CC"
_ACCENT_BG = "#EBF3FF"
_GREEN     = "#34C759"
_GREEN_BG  = "#E4F8EB"
_RED       = "#FF3B30"
_RED_BG    = "#FFEBE9"
_BAR_ON    = "#007AFF"
_BAR_OFF   = "#E5E5EA"
_FONT      = '"Microsoft YaHei", "Segoe UI", sans-serif'

WINDOW_CSS = f"""
    QDialog {{
        background: {_BG};
        color: {_TEXT};
        font-family: {_FONT};
        font-size: 13px;
    }}
    QLabel {{
        color: {_TEXT};
        background: transparent;
    }}
    QLineEdit {{
        background: {_INPUT_BG};
        color: {_TEXT};
        border: 1px solid {_BORDER};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {_ACCENT};
    }}
    QLineEdit:focus {{
        border: 2px solid {_ACCENT};
        padding: 7px 11px;
    }}
    QCheckBox {{
        color: {_TEXT};
        spacing: 8px;
        font-size: 13px;
    }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border-radius: 4px;
        border: 1px solid {_BORDER};
        background: {_SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {_ACCENT};
        border: 1px solid {_ACCENT};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QComboBox {{
        background: {_INPUT_BG};
        color: {_TEXT};
        border: 1px solid {_BORDER};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        min-height: 28px;
    }}
    QComboBox:focus {{
        border: 2px solid {_ACCENT};
        padding: 5px 9px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {_BORDER};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""

NAV_CSS = f"""
    QListWidget {{
        background: {_NAV_BG};
        border: none;
        outline: none;
        padding: 8px 8px 0 8px;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}
    QListWidget::item {{
        color: {_TEXT_SEC};
        padding: 10px 12px;
        border: none;
        border-radius: 8px;
        margin-bottom: 2px;
        font-size: 13px;
    }}
    QListWidget::item:selected {{
        color: {_TEXT};
        background: rgba(0, 0, 0, 0.06);
        font-weight: 500;
    }}
    QListWidget::item:hover:!selected {{
        background: rgba(0, 0, 0, 0.03);
    }}
"""

_BTN_PRIMARY = f"""
    QPushButton {{
        background: {_ACCENT}; color: white; border: none;
        border-radius: 8px; padding: 9px 22px; font-size: 13px;
    }}
    QPushButton:hover {{ background: {_ACCENT_HV}; }}
    QPushButton:disabled {{ background: {_BAR_OFF}; color: {_TEXT_DIM}; }}
"""

_BTN_GHOST = f"""
    QPushButton {{
        background: transparent; color: {_TEXT_SEC}; border: 1px solid {_BORDER};
        border-radius: 8px; padding: 9px 22px; font-size: 13px;
    }}
    QPushButton:hover {{ background: {_INPUT_BG}; color: {_TEXT}; }}
"""

_BTN_GHOST_SM = f"""
    QPushButton {{
        background: transparent; color: {_TEXT_SEC}; border: 1px solid {_BORDER};
        border-radius: 8px; padding: 4px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {_INPUT_BG}; color: {_TEXT}; }}
"""

_BTN_DANGER_SM = f"""
    QPushButton {{
        background: transparent; color: {_RED}; border: 1px solid {_RED_BG};
        border-radius: 8px; padding: 4px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {_RED_BG}; color: {_RED}; }}
"""

_BTN_GREEN_SM = f"""
    QPushButton {{
        background: {_GREEN_BG}; color: {_GREEN}; border: none;
        border-radius: 8px; padding: 4px 14px; font-size: 12px; font-weight: 500;
    }}
    QPushButton:hover {{ background: #D0F4DC; }}
    QPushButton:disabled {{ background: {_BAR_OFF}; color: {_TEXT_DIM}; }}
"""

_BTN_ACCENT_SM = f"""
    QPushButton {{
        background: {_ACCENT}; color: white; border: none;
        border-radius: 8px; padding: 4px 14px; font-size: 12px;
    }}
    QPushButton:hover {{ background: {_ACCENT_HV}; }}
"""

_SECTION = f"color: {_TEXT_SEC}; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;"


# ── Nav Icons ────────────────────────────────────────────────────


def _nav_icon(shape: str) -> QIcon:
    sz = 18
    pm = QPixmap(sz, sz)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(_TEXT_SEC)
    pen = QPen(c, 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    if shape == "general":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(3, 3, 12, 12)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(7, 7, 4, 4)
        notch = QPen(c, 2.5)
        notch.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(notch)
        for deg in range(0, 360, 45):
            rad = math.radians(deg)
            p.drawLine(
                int(9 + 5.5 * math.cos(rad)), int(9 + 5.5 * math.sin(rad)),
                int(9 + 7.5 * math.cos(rad)), int(9 + 7.5 * math.sin(rad)),
            )

    elif shape == "model":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        for x, y, w, h in [(2, 10, 3, 6), (6, 4, 3, 12), (10, 7, 3, 9), (14, 5, 3, 11)]:
            p.drawRoundedRect(x, y, w, h, 1, 1)

    elif shape == "polish":
        pen2 = QPen(c, 1.8)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawLine(3, 15, 12, 3)
        p.drawLine(12, 3, 15, 6)
        p.drawLine(15, 6, 6, 15)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(1, 1, 3, 3)
        p.drawEllipse(13, 0, 2, 2)

    elif shape == "about":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(2, 2, 14, 14)
        thick = QPen(c, 2)
        thick.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(thick)
        p.drawLine(9, 8, 9, 13)
        p.drawPoint(9, 5)

    p.end()
    return QIcon(pm)


# ── Helpers ──────────────────────────────────────────────────────


_MODIFIER_KEYS = set()


def _init_modifier_keys():
    global _MODIFIER_KEYS
    _MODIFIER_KEYS = {
        Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
        Qt.Key.Key_AltGr, Qt.Key.Key_Meta,
    }


_format_hotkey = format_hotkey


def _qt_key_to_name(key: int) -> str:
    from PyQt6.QtCore import Qt
    mapping = {
        Qt.Key.Key_Space: "space", Qt.Key.Key_Tab: "tab",
        Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
        Qt.Key.Key_Escape: "esc",
    }
    if key in mapping:
        return mapping[key]
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(key).lower()
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(key)
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return f"f{key - Qt.Key.Key_F1 + 1}"
    return ""


# ── Hotkey Edit ──────────────────────────────────────────────────


class HotkeyEdit(QLineEdit):
    hotkey_changed = pyqtSignal(str)
    capture_started = pyqtSignal()
    capture_ended = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        _init_modifier_keys()
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处，然后按下快捷键...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._capturing = False
        self._value = ""

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, hotkey: str):
        self._value = hotkey
        self.setText(_format_hotkey(hotkey))

    def mousePressEvent(self, event):
        if self._capturing:
            self.capture_ended.emit()
        self._capturing = True
        self.setText("请按下组合键...")
        self.setStyleSheet(f"border: 2px solid {_ACCENT}; background: {_ACCENT_BG};")
        self.capture_started.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if not self._capturing:
            return

        key = event.key()
        modifiers = event.modifiers()

        mod_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mod_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mod_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mod_parts.append("Shift")

        if key in _MODIFIER_KEYS:
            if mod_parts:
                self.setText(" + ".join(mod_parts) + " + ...")
            return

        key_name = _qt_key_to_name(key)
        if not key_name:
            return

        display_key = key_name.capitalize() if len(key_name) > 1 else key_name.upper()
        all_parts = mod_parts + [display_key]

        display = " + ".join(all_parts)
        value = "+".join(p.lower() for p in all_parts)

        self.setText(display)
        self._value = value
        self._capturing = False
        self.setStyleSheet("")
        self.hotkey_changed.emit(value)
        self.capture_ended.emit()

    def focusOutEvent(self, event):
        if self._capturing:
            self._capturing = False
            self.setStyleSheet("")
            self.setText(_format_hotkey(self._value))
            self.capture_ended.emit()
        super().focusOutEvent(event)

    def cancel_capture_if_active(self):
        """If user closes settings while recording a new shortcut, release global hotkey pause."""
        if not self._capturing:
            return
        self._capturing = False
        self.setStyleSheet("")
        self.setText(_format_hotkey(self._value))
        self.capture_ended.emit()


# ── Model Card ───────────────────────────────────────────────────


class _BarWidget(QWidget):
    def __init__(self, level: int, parent=None):
        super().__init__(parent)
        self._level = max(1, min(5, level))
        self.setFixedSize(70, 6)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        seg_w = 12
        gap = 2
        for i in range(5):
            x = i * (seg_w + gap)
            color = QColor(_BAR_ON) if i < self._level else QColor(_BAR_OFF)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, 0, seg_w, 6, 3, 3)
        p.end()


class ModelCard(QFrame):
    action_clicked = pyqtSignal(str, str)

    def __init__(self, model_info: dict, is_downloaded: bool,
                 is_active: bool, parent=None):
        super().__init__(parent)
        self._model_id = model_info["id"]
        self._info = model_info
        self._is_downloaded = is_downloaded
        self._is_active = is_active
        self._progress_bar = None
        self._action_btn = None
        self._setup_ui()

    def _setup_ui(self):
        if self._is_active:
            bg = _ACCENT_BG
        else:
            bg = _SURFACE
        self.setStyleSheet(
            f"ModelCard {{ background: {bg}; border: none; border-radius: 12px; }}"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 30 if not self._is_active else 45))
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)

        name_lbl = QLabel(self._info["name"])
        name_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.DemiBold))
        name_lbl.setStyleSheet(f"color: {_TEXT};")
        top.addWidget(name_lbl)

        if self._is_active:
            badge = QLabel(" 使用中 ")
            badge.setStyleSheet(
                f"background: {_ACCENT}; color: white; border-radius: 8px;"
                "padding: 2px 10px; font-size: 10px;"
            )
            top.addWidget(badge)

        top.addStretch()

        bars = QVBoxLayout()
        bars.setSpacing(3)
        for text, level in [("准确率", self._info["accuracy"]),
                             ("速度", self._info["speed"])]:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(text)
            lbl.setFixedWidth(36)
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px;")
            row.addWidget(lbl)
            row.addWidget(_BarWidget(level))
            bars.addLayout(row)
        top.addLayout(bars)
        layout.addLayout(top)

        meta = QHBoxLayout()
        desc = QLabel(self._info["description"])
        desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        meta.addWidget(desc)
        meta.addStretch()
        lang = QLabel(self._info["languages"])
        lang.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        meta.addWidget(lang)
        layout.addLayout(meta)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedSize(120, 8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: {_BAR_OFF}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background: {_GREEN}; border-radius: 4px; }}
        """)
        actions.addWidget(self._progress_bar)
        actions.addStretch()

        if self._is_downloaded:
            if not self._is_active:
                sel_btn = QPushButton("设为当前")
                sel_btn.setFixedHeight(28)
                sel_btn.setStyleSheet(_BTN_ACCENT_SM)
                sel_btn.clicked.connect(lambda: self.action_clicked.emit(self._model_id, "select"))
                actions.addWidget(sel_btn)

            del_btn = QPushButton("删除")
            del_btn.setFixedHeight(28)
            del_btn.setStyleSheet(_BTN_DANGER_SM)
            del_btn.clicked.connect(lambda: self.action_clicked.emit(self._model_id, "delete"))
            actions.addWidget(del_btn)
        else:
            self._action_btn = QPushButton(f"下载  {self._info['size_mb']} MB")
            self._action_btn.setFixedHeight(28)
            self._action_btn.setStyleSheet(_BTN_GREEN_SM)
            self._action_btn.clicked.connect(lambda: self.action_clicked.emit(self._model_id, "download"))
            actions.addWidget(self._action_btn)

        layout.addLayout(actions)

    def set_download_progress(self, pct: int):
        if self._progress_bar:
            self._progress_bar.setVisible(True)
            self._progress_bar.setValue(pct)
        if self._action_btn:
            self._action_btn.setEnabled(False)
            self._action_btn.setText(f"{pct}%")

    def set_download_error(self, msg: str):
        if self._progress_bar:
            self._progress_bar.setVisible(False)
        if self._action_btn:
            self._action_btn.setEnabled(True)
            self._action_btn.setText("重试")


# ── Settings Window ──────────────────────────────────────────────


class SettingsWindow(QDialog):
    hotkey_updated = pyqtSignal(str)
    settings_changed = pyqtSignal()
    hotkey_capture_started = pyqtSignal()
    hotkey_capture_ended = pyqtSignal()

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self._model_cards: dict[str, ModelCard] = {}
        self._dl_workers: dict[str, object] = {}
        self._mic_test_recorder = AudioRecorder(self)
        self._mic_probe_active = False
        self._mic_probe_max = 0.0
        self._setup_window()
        self._setup_ui()
        self._load_settings()

    def _setup_window(self):
        self.setWindowTitle("VoiceInk")
        self.setMinimumSize(580, 440)
        self.resize(700, 520)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setStyleSheet(WINDOW_CSS)

    # ── Layout ─────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(136)
        self._nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav.setStyleSheet(NAV_CSS)

        for shape, label in [("general", "通用"), ("model", "模型"),
                              ("polish", "润色"), ("about", "关于")]:
            item = QListWidgetItem(_nav_icon(shape), label)
            item.setSizeHint(QSize(136, 42))
            self._nav.addItem(item)

        self._nav.setCurrentRow(0)
        body.addWidget(self._nav)

        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet(f"background: {_BAR_OFF};")
        body.addWidget(div)

        self._pages = QStackedWidget()
        self._pages.setStyleSheet(f"background: {_BG};")
        self._pages.addWidget(self._create_general_page())
        self._pages.addWidget(self._create_model_page())
        self._pages.addWidget(self._create_polish_page())
        self._pages.addWidget(self._create_about_page())
        body.addWidget(self._pages, 1)

        self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)

        root.addLayout(body, 1)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_BAR_OFF};")
        root.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(20, 14, 20, 14)
        btn_bar.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(_BTN_GHOST)
        cancel_btn.clicked.connect(self.close)
        btn_bar.addWidget(cancel_btn)

        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet(_BTN_PRIMARY)
        save_btn.clicked.connect(self._save_settings)
        btn_bar.addWidget(save_btn)

        root.addLayout(btn_bar)

    # ── Page: General ──────────────────────────────────

    def _create_general_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 28, 32, 20)
        lay.setSpacing(16)

        t = QLabel("通用设置")
        t.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.DemiBold))
        lay.addWidget(t)
        lay.addSpacing(4)

        s1 = QLabel("快捷键")
        s1.setStyleSheet(_SECTION)
        lay.addWidget(s1)

        row = QHBoxLayout()
        desc = QLabel("按住快捷键录音，松开结束")
        desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        row.addWidget(desc)
        row.addStretch()
        self._hotkey_edit = HotkeyEdit()
        self._hotkey_edit.setFixedWidth(200)
        self._hotkey_edit.capture_started.connect(self.hotkey_capture_started.emit)
        self._hotkey_edit.capture_ended.connect(self.hotkey_capture_ended.emit)
        row.addWidget(self._hotkey_edit)
        lay.addLayout(row)

        self._add_sep(lay)

        s2 = QLabel("偏好")
        s2.setStyleSheet(_SECTION)
        lay.addWidget(s2)

        self._auto_start_cb = QCheckBox("开机时自动启动 VoiceInk")
        self._sound_cb = QCheckBox("录音开始和结束时播放提示音")
        lay.addWidget(self._auto_start_cb)
        lay.addWidget(self._sound_cb)

        self._add_sep(lay)

        s_audio = QLabel("声音收录")
        s_audio.setStyleSheet(_SECTION)
        lay.addWidget(s_audio)

        src_lbl = QLabel("音频来源")
        src_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        lay.addWidget(src_lbl)

        self._source_group = QButtonGroup(self)
        self._src_mic_rb = QRadioButton("仅麦克风（你的说话）")
        self._src_sys_rb = QRadioButton("仅电脑播放（视频、会议里传来的声音）")
        self._src_mixed_rb = QRadioButton("麦克风 + 电脑播放（开会：远端 + 自己）")
        for rb in (self._src_mic_rb, self._src_sys_rb, self._src_mixed_rb):
            rb.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
            self._source_group.addButton(rb)
            lay.addWidget(rb)
        self._src_mic_rb.toggled.connect(self._sync_source_device_widgets)
        self._src_sys_rb.toggled.connect(self._sync_source_device_widgets)
        self._src_mixed_rb.toggled.connect(self._sync_source_device_widgets)

        trig_lbl = QLabel("触发方式")
        trig_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        lay.addWidget(trig_lbl)

        self._trigger_group = QButtonGroup(self)
        self._trigger_continuous_rb = QRadioButton("自动持续转写（检测到说话后自动出字）")
        self._trigger_hotkey_rb = QRadioButton("按住快捷键录音（松开结束）")
        for rb in (self._trigger_continuous_rb, self._trigger_hotkey_rb):
            rb.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
            self._trigger_group.addButton(rb)
            lay.addWidget(rb)
        self._trigger_save_hint = QLabel(
            "修改触发方式或音频来源后，必须点右下角「保存设置」才会生效。"
        )
        self._trigger_save_hint.setStyleSheet(f"color: {_ACCENT}; font-size: 11px;")
        self._trigger_save_hint.setWordWrap(True)
        lay.addWidget(self._trigger_save_hint)

        self._audio_desc = QLabel(
            "建议先点「测试声音」验证设备。开会请选「麦克风 + 电脑播放」；"
            "自动模式下静音一段时间会输出一段文字。"
        )
        self._audio_desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        self._platform_audio_hint = QLabel(platform_audio_hint())
        self._platform_audio_hint.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        self._platform_audio_hint.setWordWrap(True)
        self._audio_desc.setWordWrap(True)
        lay.addWidget(self._audio_desc)
        lay.addWidget(self._platform_audio_hint)

        hk_hint = QLabel(
            "提示：若 Ctrl+Space 无反应，可能是输入法占用了该组合键，可改为 Alt+Space。"
        )
        hk_hint.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        hk_hint.setWordWrap(True)
        lay.addWidget(hk_hint)

        self._mic_test_btn = QPushButton("测试声音（约 2 秒）")
        self._mic_test_btn.setStyleSheet(_BTN_GHOST)
        self._mic_test_btn.clicked.connect(self._run_mic_probe)
        lay.addWidget(self._mic_test_btn)

        self._advanced_audio_btn = QPushButton("出问题了再改设备 ▼")
        self._advanced_audio_btn.setStyleSheet(_BTN_GHOST_SM)
        self._advanced_audio_btn.setCheckable(True)
        self._advanced_audio_btn.setFixedWidth(120)
        self._advanced_audio_btn.toggled.connect(self._toggle_advanced_audio)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._advanced_audio_btn)
        lay.addLayout(btn_row)

        self._advanced_audio_panel = QFrame()
        self._advanced_audio_panel.setObjectName("advancedAudioPanel")
        self._advanced_audio_panel.setStyleSheet(f"""
            QFrame#advancedAudioPanel {{
                background: {_SURFACE};
                border: 1px solid {_BORDER};
                border-radius: 10px;
            }}
        """)
        self._advanced_audio_panel.setVisible(False)
        self._advanced_audio_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        adv_lay = QVBoxLayout(self._advanced_audio_panel)
        adv_lay.setContentsMargins(14, 12, 14, 12)
        adv_lay.setSpacing(10)

        mic_dev_row = QHBoxLayout()
        mic_dev_lbl = QLabel("麦克风")
        mic_dev_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        mic_dev_lbl.setFixedWidth(52)
        mic_dev_row.addWidget(mic_dev_lbl)
        self._mic_device_combo = QComboBox()
        self._mic_device_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._mic_device_combo.setMinimumWidth(180)
        mic_dev_row.addWidget(self._mic_device_combo, 1)
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(_BTN_GHOST_SM)
        refresh_btn.setFixedHeight(28)
        refresh_btn.clicked.connect(self._refresh_audio_device_lists)
        mic_dev_row.addWidget(refresh_btn)
        reset_btn = QPushButton("恢复自动选择")
        reset_btn.setStyleSheet(_BTN_GHOST_SM)
        reset_btn.setFixedHeight(28)
        reset_btn.setToolTip("推荐：让程序自动挑选麦克风与扬声器，避免选到打不开的设备")
        reset_btn.clicked.connect(self._reset_audio_devices_to_auto)
        mic_dev_row.addWidget(reset_btn)
        adv_lay.addLayout(mic_dev_row)

        sys_dev_row = QHBoxLayout()
        sys_dev_lbl = QLabel("电脑声")
        sys_dev_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        sys_dev_lbl.setFixedWidth(52)
        sys_dev_row.addWidget(sys_dev_lbl)
        self._system_device_combo = QComboBox()
        self._system_device_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._system_device_combo.setMinimumWidth(180)
        sys_dev_row.addWidget(self._system_device_combo, 1)
        adv_lay.addLayout(sys_dev_row)

        adv_hint = QLabel(
            "两项都请保持「自动选择」。只有测试失败时再改：电脑声优先选带 Realtek 的扬声器，"
            "不要选名称含糊的「Audio Device」或网易等虚拟声卡。"
        )
        adv_hint.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        adv_hint.setWordWrap(True)
        adv_lay.addWidget(adv_hint)

        lay.addWidget(self._advanced_audio_panel)

        self._mic_test_status = QLabel("")
        self._mic_test_status.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 11px;")
        self._mic_test_status.setWordWrap(True)
        lay.addWidget(self._mic_test_status)

        lay.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    # ── Page: Model ────────────────────────────────────

    def _create_model_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 20, 0, 0)
        lay.setSpacing(0)

        t = QLabel("语音识别模型")
        t.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.DemiBold))
        t.setContentsMargins(28, 8, 0, 0)
        lay.addWidget(t)

        sub = QLabel("模型越大准确率越高，但需要更多存储空间")
        sub.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        sub.setContentsMargins(28, 2, 0, 0)
        lay.addWidget(sub)

        dir_w = QWidget()
        dl = QHBoxLayout(dir_w)
        dl.setContentsMargins(28, 12, 28, 4)
        dl.setSpacing(8)

        dl_lbl = QLabel("存储位置")
        dl_lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        dl_lbl.setFixedWidth(56)
        dl.addWidget(dl_lbl)

        self._dir_path_label = QLabel()
        self._dir_path_label.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 11px; background: {_INPUT_BG};"
            f"border: none; border-radius: 6px; padding: 5px 10px;"
        )
        self._dir_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dl.addWidget(self._dir_path_label, 1)

        chg = QPushButton("更改")
        chg.setFixedHeight(26)
        chg.setStyleSheet(_BTN_GHOST_SM)
        chg.clicked.connect(self._change_model_dir)
        dl.addWidget(chg)

        lay.addWidget(dir_w)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(28, 12, 28, 28)
        self._cards_layout.setSpacing(12)
        scroll.setWidget(self._cards_container)
        lay.addWidget(scroll, 1)

        return page

    def _refresh_dir_label(self):
        p = str(self._config.models_dir)
        self._dir_path_label.setText(p)
        self._dir_path_label.setToolTip(p)

    def _change_model_dir(self):
        cur = str(self._config.models_dir)
        d = QFileDialog.getExistingDirectory(self, "选择模型存储目录", cur)
        if not d:
            return
        new_p = Path(d)
        old_p = self._config.models_dir
        if new_p == old_p:
            return
        new_p.mkdir(parents=True, exist_ok=True)
        moved = 0
        if old_p.exists():
            for item in old_p.iterdir():
                if item.is_dir():
                    target = new_p / item.name
                    if not target.exists():
                        try:
                            shutil.move(str(item), str(target))
                            moved += 1
                        except Exception:
                            pass
        self._config.set("stt.models_dir", str(new_p))
        from voiceink.speech_recognizer import set_models_dir
        set_models_dir(new_p)
        self._refresh_dir_label()
        self._rebuild_model_cards()
        if moved > 0:
            QMessageBox.information(self, "完成", f"已将 {moved} 个模型迁移到新目录。")

    def _rebuild_model_cards(self):
        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._model_cards.clear()
        active_id = self._config.get("stt.model_id", "sensevoice")

        lbl_dl = QLabel("已下载")
        lbl_dl.setStyleSheet(_SECTION)
        self._cards_layout.addWidget(lbl_dl)

        has_dl = False
        for info in MODEL_REGISTRY:
            if is_model_downloaded(info["id"]):
                has_dl = True
                card = ModelCard(info, True, info["id"] == active_id)
                card.action_clicked.connect(self._on_card_action)
                self._model_cards[info["id"]] = card
                self._cards_layout.addWidget(card)

        if not has_dl:
            e = QLabel("尚未下载任何模型，请从下方选择一个开始")
            e.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 12px; padding: 12px 4px;")
            self._cards_layout.addWidget(e)

        lbl_av = QLabel("可下载")
        lbl_av.setStyleSheet(f"{_SECTION} padding-top: 12px;")
        self._cards_layout.addWidget(lbl_av)

        has_av = False
        for info in MODEL_REGISTRY:
            if not is_model_downloaded(info["id"]):
                has_av = True
                card = ModelCard(info, False, False)
                card.action_clicked.connect(self._on_card_action)
                self._model_cards[info["id"]] = card
                self._cards_layout.addWidget(card)

        if not has_av:
            d = QLabel("所有模型已下载")
            d.setStyleSheet(f"color: {_GREEN}; font-size: 12px; padding: 12px 4px;")
            self._cards_layout.addWidget(d)

        self._cards_layout.addStretch()

    def _on_card_action(self, model_id: str, action: str):
        if action == "select":
            self._config.set("stt.model_id", model_id)
            self._rebuild_model_cards()
        elif action == "download":
            self._start_download(model_id)
        elif action == "delete":
            self._delete_model(model_id)

    def _start_download(self, model_id: str):
        from voiceink.speech_recognizer import ModelDownloadWorker
        worker = ModelDownloadWorker(model_id)
        self._dl_workers[model_id] = worker
        card = self._model_cards.get(model_id)
        worker.progress.connect(lambda pct, c=card: c.set_download_progress(pct) if c else None)
        worker.finished_ok.connect(lambda mid: self._on_dl_done(mid))
        worker.error.connect(lambda msg, c=card: self._on_dl_error(msg, c))
        worker.start()

    def _on_dl_done(self, model_id: str):
        self._dl_workers.pop(model_id, None)
        from voiceink.speech_recognizer import get_downloaded_models
        downloaded = get_downloaded_models()
        if len(downloaded) == 1 and downloaded[0] == model_id:
            self._config.set("stt.model_id", model_id)
        self._rebuild_model_cards()
        from voiceink.speech_recognizer import get_model_info
        info = get_model_info(model_id)
        name = info["name"] if info else model_id
        QMessageBox.information(self, "完成", f"{name} 已下载，可以开始使用。")

    def _on_dl_error(self, msg: str, card):
        if card:
            card.set_download_error(msg)
        QMessageBox.warning(self, "下载失败", msg)

    def _delete_model(self, model_id: str):
        from voiceink.speech_recognizer import get_model_info, delete_model
        info = get_model_info(model_id)
        name = info["name"] if info else model_id
        reply = QMessageBox.question(
            self, "删除模型",
            f'确定删除 "{name}" 吗？删除后需重新下载。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        active_id = self._config.get("stt.model_id", "")
        delete_model(model_id)
        if active_id == model_id:
            from voiceink.speech_recognizer import get_downloaded_models
            remaining = get_downloaded_models()
            self._config.set("stt.model_id", remaining[0] if remaining else "")
        self._rebuild_model_cards()

    # ── Page: Polish (LLM) ─────────────────────────────

    def _create_polish_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_BORDER}; border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(16)

        t = QLabel("文字润色")
        t.setFont(QFont("Microsoft YaHei", 20, QFont.Weight.DemiBold))
        lay.addWidget(t)
        lay.addSpacing(4)

        self._llm_enable_cb = QCheckBox("启用润色（自动去除口语词、添加标点）")
        self._llm_enable_cb.toggled.connect(self._on_llm_toggle)
        lay.addWidget(self._llm_enable_cb)

        self._llm_off_hint = QLabel("启用后可配置 LLM 接口与润色提示词。")
        self._llm_off_hint.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 12px;")
        lay.addWidget(self._llm_off_hint)

        self._llm_container = QWidget()
        c_lay = QVBoxLayout(self._llm_container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(16)

        self._add_sep(c_lay)

        self._llm_form = QWidget()
        form = QFormLayout(self._llm_form)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._llm_url_edit = QLineEdit()
        self._llm_url_edit.setPlaceholderText("https://api.deepseek.com/v1")
        form.addRow("接口地址", self._llm_url_edit)

        kr = QHBoxLayout()
        self._llm_key_edit = QLineEdit()
        self._llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_key_edit.setPlaceholderText("sk-...")
        self._llm_key_toggle = QPushButton("显示")
        self._llm_key_toggle.setFixedWidth(48)
        self._llm_key_toggle.setCheckable(True)
        self._llm_key_toggle.setStyleSheet(f"""
            QPushButton {{ background: {_INPUT_BG}; color: {_TEXT_SEC}; border: 1px solid {_BORDER};
                border-radius: 8px; font-size: 11px; padding: 6px; }}
            QPushButton:checked {{ background: {_ACCENT}; color: white; border: 1px solid {_ACCENT}; }}
        """)
        self._llm_key_toggle.toggled.connect(
            lambda on: self._llm_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        kr.addWidget(self._llm_key_edit)
        kr.addWidget(self._llm_key_toggle)
        form.addRow("密钥", kr)

        self._llm_model_edit = QLineEdit()
        self._llm_model_edit.setPlaceholderText("deepseek-chat")
        form.addRow("模型名称", self._llm_model_edit)

        c_lay.addWidget(self._llm_form)

        tr = QHBoxLayout()
        tr.addStretch()
        self._llm_test_btn = QPushButton("测试连接")
        self._llm_test_btn.setStyleSheet(_BTN_GHOST)
        self._llm_test_btn.clicked.connect(self._test_llm)
        tr.addWidget(self._llm_test_btn)
        c_lay.addLayout(tr)

        self._add_sep(c_lay)

        prompt_header = QHBoxLayout()
        prompt_lbl = QLabel("润色提示词")
        prompt_lbl.setStyleSheet(_SECTION)
        prompt_header.addWidget(prompt_lbl)
        prompt_header.addStretch()
        self._prompt_reset_btn = QPushButton("恢复默认")
        self._prompt_reset_btn.setFixedHeight(24)
        self._prompt_reset_btn.setStyleSheet(_BTN_GHOST_SM)
        self._prompt_reset_btn.clicked.connect(self._reset_prompt)
        prompt_header.addWidget(self._prompt_reset_btn)
        c_lay.addLayout(prompt_header)

        prompt_hint = QLabel("自定义发送给大模型的 System Prompt，留空则使用内置默认提示词")
        prompt_hint.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        c_lay.addWidget(prompt_hint)

        self._llm_prompt_edit = QTextEdit()
        self._llm_prompt_edit.setFixedHeight(120)
        self._llm_prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_INPUT_BG};
                color: {_TEXT};
                border: 1px solid {_BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-family: {_FONT};
            }}
            QTextEdit:focus {{
                border: 2px solid {_ACCENT};
                padding: 7px 11px;
            }}
        """)
        self._llm_prompt_edit.setPlaceholderText(
            "留空使用默认提示词。默认行为：去除口语赘词、补全标点、理顺语序，保持原意不变。"
        )
        c_lay.addWidget(self._llm_prompt_edit)

        hint = QLabel(
            "支持 OpenAI、DeepSeek、通义千问、Ollama 等兼容接口。\n"
            "未启用时将直接输出语音转写的原始文字。"
        )
        hint.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        hint.setWordWrap(True)
        c_lay.addWidget(hint)

        lay.addWidget(self._llm_container)
        lay.addStretch()

        scroll.setWidget(page)
        return scroll

    def _on_llm_toggle(self, enabled: bool):
        self._llm_container.setVisible(enabled)
        self._llm_off_hint.setVisible(not enabled)

    def _reset_prompt(self):
        from voiceink.text_polisher import POLISH_PROMPT
        self._llm_prompt_edit.setPlainText(POLISH_PROMPT)

    # ── Page: About ────────────────────────────────────

    def _create_about_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(8)

        t = QLabel("VoiceInk")
        t.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        lay.addWidget(t)

        ver = QLabel(f"版本 {VERSION}")
        ver.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")
        lay.addWidget(ver)

        lay.addSpacing(8)
        self._add_sep(lay)
        lay.addSpacing(8)

        self._about_form = QFormLayout()
        self._about_form.setSpacing(14)
        self._about_form.setHorizontalSpacing(16)
        self._about_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        lay.addLayout(self._about_form)

        lay.addStretch()

        footer = QLabel("按住快捷键说话，松开即转文字")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")
        lay.addWidget(footer)

        return page

    def _refresh_about_info(self):
        while self._about_form.rowCount() > 0:
            self._about_form.removeRow(0)

        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded, get_model_info

        active_id = self._config.get("stt.model_id", "")
        ai = get_model_info(active_id)
        active_name = ai["name"] if ai else "未选择"

        downloaded = [m for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]
        total_mb = sum(m["size_mb"] for m in downloaded)

        items = [
            ("当前模型", active_name),
            ("已下载", f"{len(downloaded)} 个模型，约 {total_mb} MB"),
            ("模型目录", str(self._config.models_dir)),
            ("配置文件", str(self._config.config_dir / "config.json")),
            ("快捷键", _format_hotkey(self._config.get("hotkey", "ctrl+space"))),
        ]

        for label_text, value_text in items:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 12px;")

            val = QLabel(value_text)
            val.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setWordWrap(True)

            self._about_form.addRow(lbl, val)

    # ── Shared ─────────────────────────────────────────

    @staticmethod
    def _add_sep(layout: QVBoxLayout):
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background: {_BAR_OFF};")
        layout.addWidget(s)

    # ── Load / Save ────────────────────────────────────

    def _selected_input_source(self) -> str:
        if self._src_sys_rb.isChecked():
            return INPUT_SOURCE_SYSTEM
        if self._src_mixed_rb.isChecked():
            return INPUT_SOURCE_MIXED
        return INPUT_SOURCE_MICROPHONE

    def _selected_trigger_mode(self) -> str:
        if self._trigger_hotkey_rb.isChecked():
            return TRIGGER_MODE_HOTKEY
        return TRIGGER_MODE_CONTINUOUS

    def _sync_source_device_widgets(self):
        src = self._selected_input_source()
        mic_on = src in (INPUT_SOURCE_MICROPHONE, INPUT_SOURCE_MIXED)
        sys_on = src in (INPUT_SOURCE_SYSTEM, INPUT_SOURCE_MIXED)
        self._mic_device_combo.setEnabled(mic_on)
        self._system_device_combo.setEnabled(sys_on)

    def _apply_input_source_radios(self, source: str):
        if source == INPUT_SOURCE_SYSTEM:
            self._src_sys_rb.setChecked(True)
        elif source == INPUT_SOURCE_MIXED:
            self._src_mixed_rb.setChecked(True)
        else:
            self._src_mic_rb.setChecked(True)
        self._sync_source_device_widgets()

    def _apply_trigger_mode_radios(self, mode: str):
        if mode == TRIGGER_MODE_HOTKEY:
            self._trigger_hotkey_rb.setChecked(True)
        else:
            self._trigger_continuous_rb.setChecked(True)

    def _load_settings(self):
        self._hotkey_edit.set_value(self._config.get("hotkey", "ctrl+space"))
        self._auto_start_cb.setChecked(self._config.get("auto_start", False))
        self._sound_cb.setChecked(self._config.get("sound_enabled", True))

        self._apply_input_source_radios(
            self._config.get("audio.input_source", INPUT_SOURCE_MICROPHONE)
        )
        self._apply_trigger_mode_radios(
            self._config.get("audio.trigger_mode", TRIGGER_MODE_CONTINUOUS)
        )

        self._refresh_audio_device_lists()
        mic_ok = self._set_combo_by_data(
            self._mic_device_combo, int(self._config.get("audio.mic_device_index", -1))
        )
        sys_ok = self._set_combo_by_data(
            self._system_device_combo, int(self._config.get("audio.system_device_index", -1))
        )
        if not mic_ok or not sys_ok:
            self._reset_audio_devices_to_auto()

        self._refresh_dir_label()
        self._rebuild_model_cards()

        llm_on = self._config.get("llm.enabled", False)
        self._llm_enable_cb.setChecked(llm_on)
        self._llm_container.setVisible(llm_on)
        self._llm_off_hint.setVisible(not llm_on)
        self._llm_url_edit.setText(self._config.get("llm.api_url", ""))
        self._llm_key_edit.setText(self._config.get("llm.api_key", ""))
        self._llm_model_edit.setText(self._config.get("llm.model_name", ""))
        self._llm_prompt_edit.setPlainText(self._config.get("llm.prompt", ""))

        self._refresh_about_info()

    def _set_combo_by_data(self, combo: QComboBox, value: int) -> bool:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return True
        if combo.count() > 0:
            combo.setCurrentIndex(0)
        return False

    def _reset_audio_devices_to_auto(self):
        self._set_combo_by_data(self._mic_device_combo, -1)
        self._set_combo_by_data(self._system_device_combo, -1)
        self._mic_test_status.setText("已恢复为「自动选择」，请再点「测试声音」。")

    def _refresh_audio_device_lists(self):
        mic_sel = self._mic_device_combo.currentData() if self._mic_device_combo.count() else -1
        sys_sel = self._system_device_combo.currentData() if self._system_device_combo.count() else -1

        self._mic_device_combo.clear()
        self._mic_device_combo.addItem("自动选择", -1)
        try:
            for dev in list_microphone_devices():
                self._mic_device_combo.addItem(dev.label, dev.index)
        except Exception as e:
            self._mic_device_combo.addItem(f"枚举失败: {e}", -1)

        self._system_device_combo.clear()
        self._system_device_combo.addItem("自动选择", -1)
        try:
            for dev in list_system_capture_devices_for_settings():
                self._system_device_combo.addItem(dev.label, dev.index)
        except Exception as e:
            self._system_device_combo.addItem(f"枚举失败: {e}", -1)

        if mic_sel is not None:
            self._set_combo_by_data(self._mic_device_combo, int(mic_sel))
        if sys_sel is not None:
            self._set_combo_by_data(self._system_device_combo, int(sys_sel))

    def _toggle_advanced_audio(self, visible: bool):
        self._advanced_audio_panel.setVisible(visible)
        self._advanced_audio_btn.setText(
            "出问题了再改设备 ▲" if visible else "出问题了再改设备 ▼"
        )
        if visible and self._mic_device_combo.count() <= 1:
            self._refresh_audio_device_lists()

    def _current_audio_probe_config(self) -> tuple[str, int, int]:
        return (
            self._selected_input_source(),
            int(self._mic_device_combo.currentData() if self._mic_device_combo.currentData() is not None else -1),
            int(self._system_device_combo.currentData() if self._system_device_combo.currentData() is not None else -1),
        )

    def _disconnect_mic_probe_signals(self):
        try:
            self._mic_test_recorder.volume_changed.disconnect(self._on_mic_probe_volume)
        except TypeError:
            pass
        try:
            self._mic_test_recorder.error.disconnect(self._on_mic_probe_error)
        except TypeError:
            pass
        try:
            self._mic_test_recorder.warning.disconnect(self._on_mic_probe_warning)
        except TypeError:
            pass

    def _run_mic_probe(self):
        if self._mic_probe_active or self._mic_test_recorder.is_recording:
            return
        if self._mic_device_combo.count() <= 1 or self._system_device_combo.count() <= 1:
            self._refresh_audio_device_lists()
        src, mic_idx, sys_idx = self._current_audio_probe_config()
        if mic_idx >= 0 and self._mic_device_combo.findData(mic_idx) < 0:
            mic_idx = -1
        if sys_idx >= 0 and self._system_device_combo.findData(sys_idx) < 0:
            sys_idx = -1
        sys_idx = sanitize_system_device_index(sys_idx)
        if sys_idx < 0:
            self._set_combo_by_data(self._system_device_combo, -1)
        self._mic_test_recorder.configure(
            input_source=src,
            mic_device_index=mic_idx,
            system_device_index=sys_idx,
        )
        self._mic_probe_active = True
        self._mic_probe_max = 0.0
        self._mic_test_btn.setEnabled(False)
        self._mic_test_status.setText("监听中…请说话并播放一段电脑声音")
        self._mic_test_recorder.volume_changed.connect(self._on_mic_probe_volume)
        self._mic_test_recorder.error.connect(self._on_mic_probe_error)
        self._mic_test_recorder.warning.connect(self._on_mic_probe_warning)
        self._mic_test_recorder.start()
        QTimer.singleShot(2000, self._finish_mic_probe)

    def _on_mic_probe_volume(self, volume: float):
        self._mic_probe_max = max(self._mic_probe_max, float(volume))

    def _on_mic_probe_error(self, msg: str):
        if not self._mic_probe_active:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.cancel()
        self._mic_test_btn.setEnabled(True)
        self._mic_test_status.setText("")
        QMessageBox.warning(self, "音频设备", msg)

    def _on_mic_probe_warning(self, msg: str):
        if not self._mic_probe_active:
            return
        self._mic_test_status.setText(msg)

    def _finish_mic_probe(self):
        if not self._mic_probe_active:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.stop()
        self._mic_test_btn.setEnabled(True)
        threshold = 0.0015
        peak = self._mic_probe_max
        warn = self._mic_test_recorder.last_start_warning
        if peak >= threshold:
            base = f"已检测到声音（峰值约 {peak:.4f}），可以正常使用。"
            self._mic_test_status.setText(f"{base} {warn}".strip() if warn else base)
        else:
            self._mic_test_status.setText(
                f"几乎无输入（峰值约 {peak:.4f}）。请点「恢复自动选择」后再测；仍失败再展开下方改设备。"
            )

    def _cancel_mic_probe_if_active(self):
        if not self._mic_probe_active and not self._mic_test_recorder.is_recording:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.cancel()
        self._mic_test_btn.setEnabled(True)

    def _save_settings(self):
        self._cancel_mic_probe_if_active()
        hotkey = self._hotkey_edit.value
        if hotkey:
            parts = hotkey.lower().split("+")
            has_modifier = any(p.strip() in ("ctrl", "alt", "shift", "win", "cmd") for p in parts)
            if not has_modifier:
                QMessageBox.warning(self, "提示", "快捷键必须包含至少一个修饰键（Ctrl/Alt/Shift）。")
                return
            old = self._config.get("hotkey")
            self._config.set("hotkey", hotkey)
            if hotkey != old:
                self.hotkey_updated.emit(hotkey)

        self._config.set("auto_start", self._auto_start_cb.isChecked())
        self._config.set("sound_enabled", self._sound_cb.isChecked())

        self._config.set("audio.input_source", self._selected_input_source())
        self._config.set("audio.trigger_mode", self._selected_trigger_mode())
        self._config.set("audio.mic_device_index", int(self._mic_device_combo.currentData() or -1))
        sys_idx = sanitize_system_device_index(
            int(self._system_device_combo.currentData() or -1)
        )
        self._config.set("audio.system_device_index", sys_idx)
        if sys_idx < 0:
            self._set_combo_by_data(self._system_device_combo, -1)

        self._config.set("llm.enabled", self._llm_enable_cb.isChecked())
        self._config.set("llm.api_url", self._llm_url_edit.text().strip())
        self._config.set("llm.api_key", self._llm_key_edit.text().strip())
        self._config.set("llm.model_name", self._llm_model_edit.text().strip())
        self._config.set("llm.prompt", self._llm_prompt_edit.toPlainText().strip())

        self.settings_changed.emit()
        self.close()

    # ── LLM Test ───────────────────────────────────────

    def _test_llm(self):
        url = self._llm_url_edit.text().strip()
        key = self._llm_key_edit.text().strip()
        model = self._llm_model_edit.text().strip()
        if not all([url, key, model]):
            QMessageBox.warning(self, "提示", "请填写完整的接口信息。")
            return

        class _W(QThread):
            def __init__(self, u, k, m):
                super().__init__()
                self.u, self.k, self.m = u, k, m
                self.ok, self.msg = False, ""

            def run(self):
                from voiceink.text_polisher import TextPolisher
                self.ok, self.msg = TextPolisher.test_connection(self.u, self.k, self.m)

        self._llm_test_worker = _W(url, key, model)
        self._llm_test_worker.finished.connect(
            lambda: self._on_test_done(self._llm_test_worker, self._llm_test_btn)
        )
        self._llm_test_btn.setEnabled(False)
        self._llm_test_btn.setText("测试中...")
        self._llm_test_worker.start()

    def _on_test_done(self, w, btn):
        btn.setEnabled(True)
        btn.setText("测试连接")
        if w.ok:
            QMessageBox.information(self, "成功", "连接正常，可以使用。")
        else:
            QMessageBox.warning(self, "失败", w.msg)

    # ── Cleanup ────────────────────────────────────────

    def cancel_all_downloads(self):
        """Wait for any in-progress download workers to finish."""
        for model_id, worker in list(self._dl_workers.items()):
            if hasattr(worker, 'isRunning') and worker.isRunning():
                worker.wait(3000)
        self._dl_workers.clear()

    def closeEvent(self, event):
        self._cancel_mic_probe_if_active()
        self._hotkey_edit.cancel_capture_if_active()
        self.cancel_all_downloads()
        super().closeEvent(event)
