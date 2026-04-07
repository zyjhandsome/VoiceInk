from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard
import threading


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
    """Parse a hotkey string like 'alt+space' into a set of pynput keys."""
    keys = set()
    for part in hotkey_str.lower().split("+"):
        part = part.strip()
        if part in KEY_MAP:
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

    def __init__(self, hotkey_str: str = "ctrl+space", parent=None):
        super().__init__(parent)
        self._hotkey_keys = parse_hotkey(hotkey_str)
        self._hotkey_str = hotkey_str
        self._pressed_keys = set()
        self._is_recording = False
        self._paused = False
        self._listener = None
        self._lock = threading.Lock()

    def start(self):
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
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
        with self._lock:
            self._paused = True
            self._pressed_keys.clear()

    def resume(self):
        with self._lock:
            self._paused = False
            self._pressed_keys.clear()

    def update_hotkey(self, hotkey_str: str):
        with self._lock:
            self._hotkey_str = hotkey_str
            self._hotkey_keys = parse_hotkey(hotkey_str)
            self._pressed_keys.clear()

    def _normalize_key(self, key):
        """Normalize key variants (left/right alt, ctrl, shift) to canonical form."""
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            if keyboard.Key.alt_l in self._hotkey_keys or keyboard.Key.alt_r in self._hotkey_keys:
                return key
            return keyboard.Key.alt_l
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            if keyboard.Key.ctrl_l in self._hotkey_keys or keyboard.Key.ctrl_r in self._hotkey_keys:
                return key
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

            if key == keyboard.Key.esc and self._is_recording:
                self._is_recording = False
                self.recording_cancel.emit()
                return

            if not self._is_recording and self._hotkey_keys and self._hotkey_keys.issubset(self._pressed_keys):
                self._is_recording = True
                self.recording_start.emit()

    def _on_release(self, key):
        normalized = self._normalize_key(key)

        with self._lock:
            if self._paused:
                return
            self._pressed_keys.discard(normalized)
            # Also discard the original key in case normalization differs
            self._pressed_keys.discard(key)

            if self._is_recording and normalized in self._hotkey_keys:
                self._is_recording = False
                self.recording_stop.emit()

    @property
    def hotkey_str(self) -> str:
        return self._hotkey_str
