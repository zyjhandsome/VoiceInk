import logging
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from pynput import keyboard

log = logging.getLogger("VoiceInk")

# 短按防误触（毫秒）；计时器必须在 Qt 主线程启动，否则 Windows 上可能永不触发
MIN_HOLD_MS = 120
# 松开早于该时长视为输入法/系统误触（如 Ctrl+Space 切换输入法），不提示用户
MIN_SHORT_TAP_MS = 50

KEY_MAP = {
    "alt": keyboard.Key.alt_l,
    "alt_l": keyboard.Key.alt_l,
    "alt_r": keyboard.Key.alt_r,
    "ctrl": keyboard.Key.ctrl_l,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "shift": keyboard.Key.shift_l,
    "shift_l": keyboard.Key.shift_l,
    "shift_r": keyboard.Key.shift_r,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
    "esc": keyboard.Key.esc,
    "win": keyboard.Key.cmd,
    "cmd": keyboard.Key.cmd,
}


def parse_hotkey(hotkey_str: str) -> set:
    """Parse a hotkey string like 'alt+space' into a set of pynput keys.

    Modifiers map to a single canonical key (left variant); _normalize_key
    maps left/right to the same key so either physical key satisfies the combo.
    """
    keys = set()
    for part in hotkey_str.lower().split("+"):
        part = part.strip()
        if part == "ctrl":
            keys.add(KEY_MAP["ctrl_l"])
        elif part == "alt":
            keys.add(KEY_MAP["alt_l"])
        elif part == "shift":
            keys.add(KEY_MAP["shift_l"])
        elif part in KEY_MAP:
            keys.add(KEY_MAP[part])
        elif len(part) == 1:
            try:
                keys.add(keyboard.KeyCode.from_char(part))
            except Exception:
                pass
    return keys


class HotKeyManager(QObject):
    recording_start = pyqtSignal()
    recording_stop = pyqtSignal()
    recording_cancel = pyqtSignal()
    continuous_listen_start = pyqtSignal()
    esc_pressed = pyqtSignal()
    hotkey_tap_too_short = pyqtSignal()
    listener_status = pyqtSignal(bool, str)
    # 从 pynput 线程投递到 Qt 主线程，再启动 QTimer
    _arm_hold_on_main = pyqtSignal()

    def __init__(self, hotkey_str: str = "alt+space", parent=None):
        super().__init__(parent)
        self._hotkey_keys = parse_hotkey(hotkey_str)
        self._hotkey_str = hotkey_str
        self._pressed_keys = set()
        self._is_recording = False
        self._continuous_trigger_mode = False
        self._paused = False
        self._listener = None
        self._lock = threading.Lock()
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold_timeout)
        self._hold_pending = False
        self._hold_activated = False
        self._hold_started_at = 0.0
        self._arm_hold_on_main.connect(self._start_hold_timer_on_main_thread)

    def start(self):
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        try:
            self._listener.start()
        except Exception as e:
            log.error("全局快捷键监听启动失败: %s", e)
            self._listener = None
            self.listener_status.emit(False, f"快捷键监听启动失败: {e}")
            return
        if self._listener.is_alive():
            log.info("全局快捷键监听已启动: %s", self._hotkey_str)
            self.listener_status.emit(True, "")
        else:
            log.error("全局快捷键监听未运行: %s", self._hotkey_str)
            self._listener = None
            self.listener_status.emit(
                False,
                "快捷键监听未能启动，请在设置中更换快捷键后重试",
            )

    def stop(self):
        self._cancel_hold_pending()
        if self._listener:
            self._listener.stop()
            try:
                self._listener.join(timeout=2.0)
            except Exception:
                pass
            self._listener = None
        with self._lock:
            self._pressed_keys.clear()

    def pause(self):
        self._cancel_hold_pending()
        with self._lock:
            self._paused = True
            self._pressed_keys.clear()

    def resume(self):
        self._cancel_hold_pending()
        with self._lock:
            self._paused = False
            self._pressed_keys.clear()

    def update_hotkey(self, hotkey_str: str):
        self._cancel_hold_pending()
        with self._lock:
            self._hotkey_str = hotkey_str
            self._hotkey_keys = parse_hotkey(hotkey_str)
            self._pressed_keys.clear()
        log.info("快捷键已更新: %s", hotkey_str)

    def set_continuous_trigger_mode(self, enabled: bool) -> None:
        """When True, hold hotkey starts continuous listening (release does not stop)."""
        self._cancel_hold_pending()
        with self._lock:
            self._continuous_trigger_mode = enabled
            self._pressed_keys.clear()
            self._is_recording = False

    def _cancel_hold_pending(self):
        self._hold_timer.stop()
        self._hold_pending = False

    def _hotkey_still_held(self) -> bool:
        with self._lock:
            return self._hotkey_still_held_locked()

    def _hotkey_still_held_locked(self) -> bool:
        """Caller must hold ``self._lock``."""
        return bool(
            self._hotkey_keys
            and self._hotkey_keys.issubset(self._pressed_keys)
        )

    def _on_hold_timeout(self):
        if not self._hold_pending or self._paused:
            self._hold_pending = False
            return
        if not self._hotkey_still_held():
            self._hold_pending = False
            return

        if self._continuous_trigger_mode:
            self._hold_pending = False
            self._hold_activated = True
            log.debug("快捷键按住达标，请求开启持续监听")
            self.continuous_listen_start.emit()
            return

        with self._lock:
            if self._is_recording:
                self._hold_pending = False
                return
            self._is_recording = True
        self._hold_pending = False
        self._hold_activated = True
        log.debug("快捷键按住达标，开始录音")
        self.recording_start.emit()

    def _normalize_key(self, key):
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            if keyboard.Key.alt_l in self._hotkey_keys or keyboard.Key.alt_r in self._hotkey_keys:
                return key
            return keyboard.Key.alt_l
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            if keyboard.Key.ctrl_l in self._hotkey_keys or keyboard.Key.ctrl_r in self._hotkey_keys:
                return keyboard.Key.ctrl_l
            return keyboard.Key.ctrl_l
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            if keyboard.Key.shift_l in self._hotkey_keys or keyboard.Key.shift_r in self._hotkey_keys:
                return key
            return keyboard.Key.shift_l
        return key

    def _on_press(self, key):
        normalized = self._normalize_key(key)

        with self._lock:
            if self._paused:
                return
            self._pressed_keys.add(normalized)

            if key == keyboard.Key.esc:
                self.esc_pressed.emit()
                if self._is_recording:
                    self._is_recording = False
                    self.recording_cancel.emit()
                return

            if (
                not self._is_recording
                and not self._hold_pending
                and self._hotkey_keys
                and self._hotkey_keys.issubset(self._pressed_keys)
            ):
                self._hold_pending = True
                self._hold_activated = False
                self._hold_started_at = time.monotonic()
        if self._hold_pending:
            self._arm_hold_on_main.emit()

    def _on_release(self, key):
        normalized = self._normalize_key(key)
        emit_stop = False
        sync_hold_timer = False
        emit_short_tap = False

        with self._lock:
            if self._paused:
                return
            self._pressed_keys.discard(normalized)
            self._pressed_keys.discard(key)

            if self._hold_pending:
                self._hold_pending = False
                sync_hold_timer = True
                if not self._hold_activated:
                    held_ms = (time.monotonic() - self._hold_started_at) * 1000
                    if held_ms >= MIN_SHORT_TAP_MS:
                        emit_short_tap = True
                    else:
                        log.debug(
                            "忽略极短快捷键组合 (%.0f ms)，可能为输入法占用",
                            held_ms,
                        )

            if self._is_recording and not self._hotkey_still_held_locked():
                self._is_recording = False
                emit_stop = True

        if emit_short_tap:
            self.hotkey_tap_too_short.emit()
        if sync_hold_timer:
            self._arm_hold_on_main.emit()
        if emit_stop:
            log.debug("快捷键松开，停止录音")
            self.recording_stop.emit()

    def _start_hold_timer_on_main_thread(self):
        """QTimer 只能在 Qt 主线程 start/stop。"""
        if self._hold_pending:
            self._hold_timer.start(MIN_HOLD_MS)
        else:
            self._hold_timer.stop()

    @property
    def hotkey_str(self) -> str:
        return self._hotkey_str
