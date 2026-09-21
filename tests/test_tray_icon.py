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
        tray.wake_island.connect(lambda: emitted.append(True))

        tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
        tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

        assert len(emitted) == 1

    def test_non_windows_uses_single_trigger(self, tray, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        emitted: list[object] = []
        tray.wake_island.connect(lambda: emitted.append(True))

        tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)

        assert len(emitted) == 1

    def test_status_summary_is_disabled_first_menu_action_and_updates_tooltip(self, tray):
        tray.set_status_summary("就绪 · FireRedASR2")

        action = tray.contextMenu().actions()[0]
        assert action.text() == "就绪 · FireRedASR2"
        assert not action.isEnabled()
        assert "FireRedASR2" in tray.toolTip()

    def test_activity_tooltip_uses_capsule_words(self, tray):
        tray.set_status_summary("就绪")
        tray.set_activity_tooltip("listening")
        assert tray.toolTip() == "VoiceInk - 正在听"
        tray.set_activity_tooltip("recognizing")
        assert tray.toolTip() == "VoiceInk - 正在识别"
        tray.set_activity_tooltip("loading")
        assert tray.toolTip() == "VoiceInk - 模型载入中"
        tray.set_activity_tooltip(None)
        assert tray.toolTip() == "VoiceInk - 就绪"


class TestTrayMenuStyleAndGrouping:
    def test_menu_stylesheet_uses_reference_style_tokens(self, tray):
        from voiceink.ui import design_tokens as t

        css = tray.contextMenu().styleSheet()
        assert t.TRAY_MENU_RADIUS == 8
        assert f"border-radius: {t.TRAY_MENU_RADIUS}px" in css
        assert "border-radius: 4px" not in css
        assert "border-radius: 12px" not in css
        assert t.TRAY_MENU_HOVER in css
        assert t.TRAY_MENU_SEPARATOR in css
        assert t.TRAY_MENU_BORDER in css
        assert f"font-size: {t.TYPE_BODY_SM}px" in css
        # No Stitch tray look leftovers
        assert "rgba(0, 80, 203" not in css

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
        assert labels[2] == "打开 VoiceInk"
        assert labels[3] == "历史"
        assert labels[4] == "---"
        assert labels[5] == "切换模型"
        assert labels[6] == "---"
        assert labels[7] == "开机自启"
        assert actions[7].isCheckable()
        assert labels[8] == "---"
        assert labels[9] == "退出"


def test_idle_mic_uses_text_token():
    from voiceink.ui import design_tokens as tok
    from voiceink.ui.tray_icon import create_microphone_icon
    import inspect
    assert "TEXT" in inspect.getsource(create_microphone_icon)
    assert tok.ACCENT not in inspect.getsource(create_microphone_icon).split("recording")[0]
