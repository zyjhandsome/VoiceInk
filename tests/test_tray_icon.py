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

    def test_status_summary_is_disabled_first_menu_action_and_updates_tooltip(self, tray):
        tray.set_status_summary("就绪 · FireRedASR2")

        action = tray.contextMenu().actions()[0]
        assert action.text() == "就绪 · FireRedASR2"
        assert not action.isEnabled()
        assert "FireRedASR2" in tray.toolTip()


class TestTrayMenuStyleAndGrouping:
    def test_menu_stylesheet_uses_reference_style_tokens(self, tray):
        from voiceink.ui import design_tokens as t

        css = tray.contextMenu().styleSheet()
        assert t.TRAY_MENU_RADIUS == 4
        assert f"border-radius: {t.TRAY_MENU_RADIUS}px" in css
        assert t.TRAY_MENU_HOVER in css
        assert t.TRAY_MENU_SEPARATOR in css
        assert t.TRAY_MENU_BORDER in css
        assert "font-size: 13px" in css
        # No Stitch tray look leftovers
        assert "rgba(0, 80, 203" not in css
        assert "border-radius: 12px" not in css
        assert "border-radius: 8px" not in css

    def test_menu_groups_match_spec_order(self, tray):
        actions = tray.contextMenu().actions()
        labels = []
        for a in actions:
            if a.isSeparator():
                labels.append("---")
            else:
                labels.append(a.text())

        assert labels[0]  # status (dynamic)
        assert not actions[0].isEnabled()
        assert labels[1] == "---"
        assert labels[2] == "打开设置"
        assert labels[3] == "历史"
        assert labels[4] == "---"
        assert labels[5] == "切换模型"
        assert labels[6] == "---"
        assert labels[7] == "开机自启"
        assert actions[7].isCheckable()
        assert labels[8] == "---"
        assert labels[9] == "退出"
