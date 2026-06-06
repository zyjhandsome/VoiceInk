"""Verify hold timer is armed on the Qt main thread (regression for Ctrl+Space)."""

import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from pynput import keyboard

from voiceink.hotkey_manager import HotKeyManager, MIN_HOLD_MS


def test_hold_timer_fires_on_main_thread():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space")
    started = []

    def on_start():
        started.append(True)
        app.quit()

    mgr.recording_start.connect(on_start)
    mgr._on_press(keyboard.Key.ctrl_l)
    mgr._on_press(keyboard.Key.space)

    QTimer.singleShot(MIN_HOLD_MS + 250, app.quit)
    app.exec()

    assert started, "recording_start should emit after hold threshold"


def test_hold_timer_fires_with_right_ctrl():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space")
    started = []

    def on_start():
        started.append(True)
        app.quit()

    mgr.recording_start.connect(on_start)
    mgr._on_press(keyboard.Key.ctrl_r)
    mgr._on_press(keyboard.Key.space)

    QTimer.singleShot(MIN_HOLD_MS + 250, app.quit)
    app.exec()

    assert started, "recording_start should emit when using right Ctrl"


def test_short_tap_does_not_start():
    app = QApplication.instance() or QApplication(sys.argv)
    mgr = HotKeyManager("ctrl+space")
    started = []
    mgr.recording_start.connect(lambda: started.append(True))

    mgr._on_press(keyboard.Key.ctrl_l)
    mgr._on_press(keyboard.Key.space)
    mgr._on_release(keyboard.Key.space)
    mgr._on_release(keyboard.Key.ctrl_l)

    QTimer.singleShot(50, app.quit)
    app.exec()

    assert not started
