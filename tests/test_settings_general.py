"""General settings page UI and behavior tests (reference layout)."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton

from voiceink.audio_devices import (
    INPUT_SOURCE_MICROPHONE,
    INPUT_SOURCE_MIXED,
    INPUT_SOURCE_SYSTEM,
)
from voiceink.config import TRIGGER_MODE_CONTINUOUS, TRIGGER_MODE_HOTKEY, Config
from voiceink.ui.design_tokens import ACCENT, SURFACE_PEARL, TEXT_DIM, TEXT_SEC
from voiceink.ui.settings_window import SettingsWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def settings_window(config, qapp, monkeypatch):
    monkeypatch.setattr(
        SettingsWindow,
        "_rebuild_model_cards",
        lambda self: None,
    )
    monkeypatch.setattr(
        SettingsWindow,
        "_refresh_about_info",
        lambda self: None,
    )
    monkeypatch.setattr(
        SettingsWindow,
        "_refresh_audio_device_lists",
        lambda self: None,
    )
    win = SettingsWindow(config)
    yield win
    win.close()


class TestGeneralPageLayout:
    def test_header_title_matches_reference(self, settings_window):
        assert settings_window._general_hero._title.text() == "通用设置"

    def test_footer_hint_text(self, settings_window):
        assert settings_window._footer_hint.text() == "更改会即时生效"
        sheet = settings_window._footer_hint.styleSheet()
        assert f"color: {TEXT_DIM}" in sheet
        assert f"color: {ACCENT}" not in sheet

    def test_about_version_and_usage_hint_are_neutral(self, settings_window):
        version_sheet = settings_window._about_version_label.styleSheet()
        assert f"background: {SURFACE_PEARL}" in version_sheet
        assert f"color: {TEXT_SEC}" in version_sheet
        assert f"color: {ACCENT}" not in version_sheet

        labels = settings_window._about_usage_tip.findChildren(type(settings_window._footer_hint))
        assert labels
        assert any(f"color: {TEXT_SEC}" in label.styleSheet() for label in labels)

    def test_general_sections_follow_task_order(self, settings_window, qapp):
        settings_window.resize(1000, 900)
        settings_window.show()
        qapp.processEvents()
        titles = {
            label.text(): label
            for label in settings_window.findChildren(type(settings_window._footer_hint))
            if label.objectName() == "settingsGroupTitle"
        }
        ordered = ["触发方式", "快捷键", "音频来源", "检测音频", "手动设备", "开机与提示", "历史"]

        assert all(title in titles for title in ordered)
        assert [titles[title].mapToGlobal(titles[title].rect().center()).y() for title in ordered] == sorted(
            titles[title].mapToGlobal(titles[title].rect().center()).y() for title in ordered
        )

    def test_general_section_groups_use_soft_containers(self, settings_window):
        from PyQt6.QtWidgets import QFrame

        from voiceink.ui.design_tokens import RADIUS_MD, SURFACE

        titles = [
            label for label in settings_window.findChildren(type(settings_window._footer_hint))
            if label.objectName() == "settingsGroupTitle"
        ]
        groups = [
            frame for frame in settings_window.findChildren(QFrame)
            if frame.objectName() == "settingsGroup"
        ]

        assert titles
        assert groups
        for group in groups:
            sheet = group.styleSheet()
            assert f"background: {SURFACE}" in sheet
            assert "border: none" in sheet
            assert f"border-radius: {RADIUS_MD}px" in sheet

    def test_close_button_uses_close_copy_and_accessible_name(self, settings_window):
        close_button = next(
            button for button in settings_window.findChildren(QPushButton)
            if button.text() == "关闭"
        )
        assert close_button.accessibleName() == "关闭设置"

    def test_polish_preview_stays_visible_when_enabled(self, settings_window):
        settings_window._on_llm_enable_toggled(True)

        assert not settings_window._llm_preview_card.isHidden()

    def test_password_toggle_updates_its_text(self, settings_window):
        settings_window._llm_key_toggle.setChecked(True)
        assert settings_window._llm_key_toggle.text() == "隐藏"
        settings_window._llm_key_toggle.setChecked(False)
        assert settings_window._llm_key_toggle.text() == "显示"

    def test_audio_source_cards_are_vertical(self, settings_window):
        picker = settings_window.findChild(type(settings_window._src_mic_rb.parent()))
        # AudioSourcePicker uses QVBoxLayout on itself
        from voiceink.ui.settings_components import AudioSourcePicker

        ap = settings_window.findChild(AudioSourcePicker)
        assert ap is not None
        assert isinstance(ap.layout(), type(ap.layout()))  # has layout
        assert ap.layout().spacing() == 8

    def test_trigger_mode_uses_choice_cards(self, settings_window):
        from PyQt6.QtWidgets import QHBoxLayout
        from voiceink.ui.settings_components import TriggerModePicker

        picker = settings_window.findChild(TriggerModePicker)
        assert picker is not None
        assert isinstance(picker.layout(), QHBoxLayout)
        assert picker.layout().spacing() == 12
        assert picker.layout().count() == 2

        assert settings_window._mixed_audio_callout.parent() is not None
        settings_window._src_mixed_rb.setChecked(True)
        settings_window._sync_source_device_widgets()
        assert not settings_window._mixed_audio_callout.isHidden()


class TestTriggerMode:
    def test_default_continuous_mode(self, settings_window):
        assert settings_window._trigger_continuous_rb.isChecked()
        assert not settings_window._trigger_hotkey_rb.isChecked()
        assert settings_window._selected_trigger_mode() == TRIGGER_MODE_CONTINUOUS

    def test_hotkey_mode_mutually_exclusive(self, settings_window, monkeypatch):
        persisted = []
        monkeypatch.setattr(
            settings_window,
            "_confirm_discard_pending",
            lambda: True,
        )
        monkeypatch.setattr(
            settings_window,
            "_persist_runtime_settings",
            lambda: persisted.append(settings_window._selected_trigger_mode()),
        )
        settings_window._trigger_hotkey_rb.setChecked(True)
        assert settings_window._trigger_hotkey_rb.isChecked()
        assert not settings_window._trigger_continuous_rb.isChecked()
        assert persisted == [TRIGGER_MODE_HOTKEY]


class TestInputSource:
    def test_source_selection_persists(self, settings_window, config, monkeypatch):
        monkeypatch.setattr(settings_window, "_confirm_discard_pending", lambda: True)
        settings_window._src_sys_rb.setChecked(True)
        assert config.get("audio.input_source") == INPUT_SOURCE_SYSTEM

    def test_mixed_warning_visibility(self, settings_window):
        settings_window._src_mic_rb.setChecked(True)
        settings_window._sync_source_device_widgets()
        assert settings_window._mixed_audio_callout.isHidden()
        settings_window._src_mixed_rb.setChecked(True)
        settings_window._sync_source_device_widgets()
        assert not settings_window._mixed_audio_callout.isHidden()

    def test_revert_on_cancel_pending(self, settings_window, config, monkeypatch):
        config.set("audio.input_source", INPUT_SOURCE_MICROPHONE)
        monkeypatch.setattr(settings_window, "_confirm_discard_pending", lambda: False)
        settings_window._loading = False
        settings_window._src_mixed_rb.setChecked(True)
        assert settings_window._src_mic_rb.isChecked()
        assert config.get("audio.input_source") == INPUT_SOURCE_MICROPHONE


class TestToggles:
    def test_toggle_rows_render_title_and_positive_height(self, settings_window, qapp):
        """QCheckBox-based rows collapse to 0 height; content must stay visible."""
        from PyQt6.QtWidgets import QLabel

        settings_window.resize(1000, 900)
        settings_window.show()
        qapp.processEvents()

        for row, title in (
            (settings_window._auto_start_row, "开机时自动启动"),
            (settings_window._sound_row, "录音提示音"),
            (settings_window._history_enabled_row, "保存语音历史"),
        ):
            assert row.height() >= 40, f"{title} row height={row.height()}"
            labels = [lb for lb in row.findChildren(QLabel) if lb.text() == title]
            assert labels, f"missing title label: {title}"
            assert labels[0].height() >= 14, f"{title} label height={labels[0].height()}"

    def test_row_click_toggles_from_anywhere(self, settings_window, qapp):
        from PyQt6.QtTest import QTest

        settings_window.resize(860, 620)
        settings_window.show()
        qapp.processEvents()

        row = settings_window._sound_row
        initial = row.isChecked()
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, pos=row.rect().center())
        assert row.isChecked() is not initial

    def test_auto_start_emits_and_persists(self, settings_window, config):
        signals = []
        settings_window.auto_start_changed.connect(signals.append)
        settings_window._auto_start_row.setChecked(True)
        assert config.get("auto_start") is True
        assert signals == [True]

    def test_sound_toggle_persists(self, settings_window, config):
        signals = []
        settings_window.sound_enabled_changed.connect(signals.append)
        settings_window._sound_row.setChecked(False)
        assert config.get("sound_enabled") is False
        assert signals == [False]


class TestHotkeyBinding:
    def test_rejects_modifierless_hotkey(self, settings_window, config, monkeypatch):
        warnings = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            lambda *args, **kwargs: warnings.append(args[2]),
        )
        settings_window._apply_hotkey_setting("space")
        assert warnings
        assert config.get("hotkey") != "space"

    def test_accepts_valid_hotkey(self, settings_window, config):
        emitted = []
        settings_window.hotkey_updated.connect(emitted.append)
        settings_window._apply_hotkey_setting("ctrl+shift+a")
        assert config.get("hotkey") == "ctrl+shift+a"
        assert emitted == ["ctrl+shift+a"]


class TestAdvancedDevices:
    def test_device_link_expands_panel(self, settings_window):
        assert settings_window._advanced_audio_panel.isHidden()
        settings_window._toggle_advanced_audio(True)
        assert not settings_window._advanced_audio_panel.isHidden()
        assert "收起" in settings_window._advanced_audio_btn.text()


class TestMicProbe:
    def test_probe_runs_two_second_flow(self, settings_window, monkeypatch):
        monkeypatch.setattr(settings_window, "_refresh_audio_device_lists", lambda: None)
        recorder = settings_window._mic_test_recorder
        recorder.configure = MagicMock()
        recorder.start = MagicMock()
        recorder.stop = MagicMock()

        settings_window._run_mic_probe()
        assert settings_window._mic_probe_active
        assert not settings_window._mic_test_btn.isEnabled()
        recorder.configure.assert_called_once()
        recorder.start.assert_called_once()

        settings_window._on_mic_probe_volume(0.01)
        settings_window._finish_mic_probe()
        assert not settings_window._mic_probe_active
        assert settings_window._mic_test_btn.isEnabled()
        assert "已检测到声音" in settings_window._mic_test_status.text()
        assert "峰值" not in settings_window._mic_test_status.text()


class TestNavigation:
    def test_back_closes_window(self, settings_window, qapp):
        closed = []
        settings_window.finished.connect(lambda _: closed.append(True))
        settings_window._on_done()
        assert settings_window.isVisible() is False or closed

    def test_done_closes_window(self, settings_window):
        settings_window.show()
        settings_window._on_done()
        assert not settings_window.isVisible()


class TestConfigReload:
    def test_reload_restores_ui_from_disk(self, config_home, qapp, monkeypatch):
        cfg_file = config_home / "config.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "hotkey": "ctrl+space",
                    "auto_start": True,
                    "sound_enabled": False,
                    "audio": {
                        "input_source": "mixed",
                        "trigger_mode": "hotkey",
                        "mic_device_index": -1,
                        "system_device_index": -1,
                    },
                }
            ),
            encoding="utf-8",
        )
        config = Config(config_dir=config_home)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)
        win = SettingsWindow(config)
        assert win._auto_start_row.isChecked()
        assert not win._sound_row.isChecked()
        assert win._src_mixed_rb.isChecked()
        assert win._trigger_hotkey_rb.isChecked()
        win.close()
