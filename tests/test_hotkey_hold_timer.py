"""Verify hold timer is armed on the Qt main thread (regression for Ctrl+Space)."""

import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from pynput import keyboard

from voiceink.hotkey_manager import HotKeyManager, MIN_HOLD_MS


def _arm_and_wait(app, mgr, on_start):
    mgr.recording_start.connect(on_start)
    QTimer.singleShot(MIN_HOLD_MS + 250, app.quit)
    app.exec()


def test_hold_timer_fires_on_main_thread():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space", parent=app)
    started = []

    def on_start():
        started.append(True)
        app.quit()

    mgr._on_press(keyboard.Key.ctrl_l)
    mgr._on_press(keyboard.Key.space)
    mgr._start_hold_timer_on_main_thread()
    _arm_and_wait(app, mgr, on_start)

    assert started, "recording_start should emit after hold threshold"


def test_hold_timer_fires_with_right_ctrl():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space", parent=app)
    started = []

    def on_start():
        started.append(True)
        app.quit()

    mgr._on_press(keyboard.Key.ctrl_r)
    mgr._on_press(keyboard.Key.space)
    mgr._start_hold_timer_on_main_thread()
    _arm_and_wait(app, mgr, on_start)

    assert started, "recording_start should emit when using right Ctrl"


def test_short_tap_does_not_start():
    from unittest.mock import patch

    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space", parent=app)
    started = []
    short_taps = []
    mgr.recording_start.connect(lambda: started.append(True))
    mgr.hotkey_tap_too_short.connect(lambda: short_taps.append(True))

    t0 = 1000.0
    with patch("voiceink.hotkey_manager.time.monotonic", side_effect=[t0, t0 + 0.08, t0 + 0.08]):
        mgr._on_press(keyboard.Key.ctrl_l)
        mgr._on_press(keyboard.Key.space)
        mgr._on_release(keyboard.Key.space)
        mgr._on_release(keyboard.Key.ctrl_l)

    assert not started
    assert short_taps, "deliberate short tap should notify"


def test_ime_flicker_does_not_emit_short_tap():
    """Sub-50ms combo (typical IME Ctrl+Space) should not spam the user."""
    from unittest.mock import patch

    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space", parent=app)
    short_taps = []
    mgr.hotkey_tap_too_short.connect(lambda: short_taps.append(True))

    t0 = 1000.0
    with patch("voiceink.hotkey_manager.time.monotonic", side_effect=[t0, t0 + 0.02, t0 + 0.02]):
        mgr._on_press(keyboard.Key.ctrl_l)
        mgr._on_press(keyboard.Key.space)
        mgr._on_release(keyboard.Key.space)
        mgr._on_release(keyboard.Key.ctrl_l)

    assert not short_taps


def test_continuous_mode_emits_listen_start_not_recording():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space", parent=app)
    mgr.set_continuous_trigger_mode(True)
    started = []
    recording = []

    mgr.continuous_listen_start.connect(lambda: started.append(True))
    mgr.recording_start.connect(lambda: recording.append(True))

    mgr._on_press(keyboard.Key.ctrl_l)
    mgr._on_press(keyboard.Key.space)
    assert mgr._hold_pending
    mgr._on_hold_timeout()

    assert started, "continuous_listen_start should emit in continuous trigger mode"
    assert not recording
    assert not mgr._is_recording, "continuous mode must not latch hotkey recording state"
