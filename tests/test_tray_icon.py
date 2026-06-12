"""Tray icon activation behavior tests."""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from voiceink.ui.tray_icon import TrayIcon


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def tray(qapp):
    icon = TrayIcon()
    yield icon


class TestTrayActivation:
    def test_windows_ignores_single_trigger(self, tray, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        emitted: list[object] = []
        tray.open_settings.connect(lambda: emitted.append(True))

        tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
        tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

        assert len(emitted) == 1

    def test_non_windows_uses_single_trigger(self, tray, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        emitted: list[object] = []
        tray.open_settings.connect(lambda: emitted.append(True))

        tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)

        assert len(emitted) == 1
