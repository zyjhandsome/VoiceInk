import pytest
from voiceink.hotkey_manager import parse_hotkey, HotKeyManager, KEY_MAP
from pynput import keyboard
import threading


class TestParseHotkey:
    def test_parse_ctrl_space(self):
        result = parse_hotkey("ctrl+space")
        assert keyboard.Key.ctrl_l in result
        assert keyboard.Key.space in result
        assert keyboard.Key.ctrl_r not in result

    def test_parse_ctrl_space_matches_single_physical_ctrl(self):
        """Hotkey set must not require both left and right modifier keys."""
        hotkey = parse_hotkey("ctrl+space")
        assert hotkey.issubset({keyboard.Key.ctrl_l, keyboard.Key.space})
        assert len(hotkey) == 2

    def test_parse_single_key(self):
        result = parse_hotkey("space")
        assert keyboard.Key.space in result

    def test_parse_with_uppercase(self):
        result = parse_hotkey("CTRL+SPACE")
        assert keyboard.Key.ctrl_l in result
        assert keyboard.Key.space in result

    def test_parse_with_spaces(self):
        result = parse_hotkey(" ctrl + space ")
        assert keyboard.Key.ctrl_l in result
        assert keyboard.Key.space in result

    def test_parse_alt_key(self):
        result = parse_hotkey("alt+space")
        assert keyboard.Key.alt_l in result

    def test_parse_shift_key(self):
        result = parse_hotkey("shift+space")
        assert keyboard.Key.shift_l in result

    def test_parse_three_keys(self):
        result = parse_hotkey("ctrl+shift+space")
        assert keyboard.Key.ctrl_l in result
        assert keyboard.Key.shift_l in result
        assert keyboard.Key.space in result

    def test_parse_character_key(self):
        result = parse_hotkey("a")
        char_key = keyboard.KeyCode.from_char("a")
        assert char_key in result

    def test_parse_mixed_modifier_and_char(self):
        result = parse_hotkey("ctrl+a")
        assert keyboard.Key.ctrl_l in result
        char_key = keyboard.KeyCode.from_char("a")
        assert char_key in result

    def test_parse_invalid_key_ignored(self):
        result = parse_hotkey("ctrl+invalidkey123")
        assert keyboard.Key.ctrl_l in result
        assert len(result) == 1


class TestHotKeyManagerInit:
    def test_default_hotkey(self):
        mgr = HotKeyManager()
        assert mgr._hotkey_str == "ctrl+space"
        assert mgr._hotkey_keys is not None

    def test_custom_hotkey(self):
        mgr = HotKeyManager("alt+space")
        assert mgr._hotkey_str == "alt+space"

    def test_initial_state(self):
        mgr = HotKeyManager()
        assert mgr._is_recording is False
        assert mgr._paused is False
        assert mgr._pressed_keys == set()

    def test_hotkey_str_property(self):
        mgr = HotKeyManager("ctrl+b")
        assert mgr.hotkey_str == "ctrl+b"


class TestHotKeyManagerStartStop:
    def test_start_creates_listener(self):
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance() or QApplication(sys.argv)
        mgr = HotKeyManager(parent=app)
        mgr.start()
        assert mgr._listener is not None
        mgr.stop()

    def test_double_start_ignored(self):
        from PyQt6.QtWidgets import QApplication
        import sys

        app = QApplication.instance() or QApplication(sys.argv)
        mgr = HotKeyManager(parent=app)
        mgr.start()
        first_listener = mgr._listener
        mgr.start()
        assert mgr._listener is first_listener
        mgr.stop()

    def test_stop_clears_keys(self):
        mgr = HotKeyManager()
        mgr.start()
        mgr._pressed_keys.add(keyboard.Key.ctrl_l)
        mgr.stop()
        assert len(mgr._pressed_keys) == 0


class TestHotKeyManagerPauseResume:
    def test_pause_sets_flag(self):
        mgr = HotKeyManager()
        mgr.pause()
        assert mgr._paused is True

    def test_pause_clears_keys(self):
        mgr = HotKeyManager()
        mgr._pressed_keys.add(keyboard.Key.ctrl_l)
        mgr.pause()
        assert len(mgr._pressed_keys) == 0

    def test_resume_clears_flag(self):
        mgr = HotKeyManager()
        mgr.pause()
        mgr.resume()
        assert mgr._paused is False

    def test_resume_clears_keys(self):
        mgr = HotKeyManager()
        mgr.resume()
        assert len(mgr._pressed_keys) == 0


class TestHotKeyManagerUpdate:
    def test_update_hotkey(self):
        mgr = HotKeyManager("ctrl+space")
        mgr.update_hotkey("alt+space")
        assert mgr._hotkey_str == "alt+space"
        assert keyboard.Key.alt_l in mgr._hotkey_keys

    def test_update_clears_pressed_keys(self):
        mgr = HotKeyManager("ctrl+space")
        mgr._pressed_keys.add(keyboard.Key.ctrl_l)
        mgr.update_hotkey("alt+space")
        assert len(mgr._pressed_keys) == 0


class TestHotKeyManagerRelease:
    def test_release_while_recording_emits_stop(self):
        mgr = HotKeyManager("ctrl+space")
        stops = []
        mgr.recording_stop.connect(lambda: stops.append(True))

        with mgr._lock:
            mgr._is_recording = True
            mgr._pressed_keys.update({keyboard.Key.ctrl_l, keyboard.Key.space})

        mgr._on_release(keyboard.Key.space)
        assert stops, "releasing any combo key should stop recording"

    def test_release_does_not_deadlock(self):
        """Regression: _on_release must not re-enter _lock via _hotkey_still_held()."""
        mgr = HotKeyManager("ctrl+space")
        done = threading.Event()

        def _release_worker():
            mgr._on_release(keyboard.Key.space)
            mgr._on_release(keyboard.Key.ctrl_l)
            done.set()

        with mgr._lock:
            mgr._is_recording = True
            mgr._pressed_keys.update({keyboard.Key.ctrl_l, keyboard.Key.space})

        t = threading.Thread(target=_release_worker)
        t.start()
        t.join(timeout=1.0)
        assert done.is_set(), "release handler deadlocked"


class TestHotKeyManagerSignals:
    def test_signals_defined(self):
        mgr = HotKeyManager()
        assert hasattr(mgr, "recording_start")
        assert hasattr(mgr, "recording_stop")
        assert hasattr(mgr, "recording_cancel")


class TestKeyMapCompleteness:
    def test_key_map_has_basic_modifiers(self):
        assert "ctrl" in KEY_MAP
        assert "alt" in KEY_MAP
        assert "shift" in KEY_MAP
        assert "space" in KEY_MAP

    def test_key_map_has_letter_modifiers(self):
        assert "ctrl_l" in KEY_MAP
        assert "ctrl_r" in KEY_MAP
        assert "alt_l" in KEY_MAP
        assert "alt_r" in KEY_MAP
        assert "shift_l" in KEY_MAP
        assert "shift_r" in KEY_MAP

    def test_key_map_has_special_keys(self):
        assert "tab" in KEY_MAP
        assert "enter" in KEY_MAP
        assert "esc" in KEY_MAP
        assert "win" in KEY_MAP
        assert "cmd" in KEY_MAP
