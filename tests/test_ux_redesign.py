"""User-facing regressions for navigation, mode feedback and history reflow."""
from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from tests.test_history_window import FakeHistoryStore
from tests.test_main_window import _make_main_window
from voiceink.ui.history_window import HistoryWindow
from voiceink.ui.settings_components import CompactPickCard


@pytest.fixture
def main_window(_qapp_session, tmp_path, monkeypatch):
    win, store = _make_main_window(tmp_path, monkeypatch)
    win.show()
    _qapp_session.processEvents()
    yield win
    win.hide()
    win.deleteLater()
    store.close()


def test_keyboard_can_reach_navigation_and_search(main_window, _qapp_session):
    win = main_window
    win._nav_buttons[2].setFocus()
    QTest.keyClick(win._nav_buttons[2], Qt.Key.Key_Space)
    assert win.current_page() == "engine"
    win._focus_history_search()
    _qapp_session.processEvents()
    assert win.current_page() == "history"
    assert win._history._search_edit.hasFocus()


def test_navigation_shortcuts_pause_during_hotkey_capture(main_window):
    win = main_window
    win._settings.hotkey_capture_started.emit()
    assert all(not key.isEnabled() for key in win._shortcuts)
    win._settings.hotkey_capture_ended.emit()
    assert all(key.isEnabled() for key in win._shortcuts)


def test_runtime_and_trigger_instructions_follow_actual_state(main_window):
    win = main_window
    win._settings.set_runtime_status("模型载入中")
    assert win._runtime_label.text() == "模型载入中"
    win._settings._trigger_hotkey_rb.setChecked(True)
    assert "0.18" in win._settings._hotkey_hint.text()
    assert "松开" in win._settings._hotkey_hint.text()
    assert "按住说话" in win._mode_label.text()
    win._settings._trigger_continuous_rb.setChecked(True)
    hint = win._settings._hotkey_hint.text()
    assert "0.30" in hint
    assert "Esc" in hint
    assert "松开后继续" in hint
    assert "停顿" in hint
    assert "不用" in hint


def test_trigger_choice_uses_same_name_as_runtime_mode(main_window):
    cards = main_window._settings.findChildren(CompactPickCard)
    titles = [card._title_label.text() for card in cards]
    assert "持续转写" in titles
    assert "连续口述" not in titles
    assert "持续转写" in main_window._mode_label.text()


def test_task_choices_have_visible_native_radios(main_window):
    cards = main_window._settings.findChildren(CompactPickCard)
    assert len(cards) == 5
    for card in cards:
        assert not card._radio.isHidden()
        assert card._radio.accessibleName()
        assert card.focusProxy() is card._radio


def test_radio_choices_support_arrow_keys(main_window, _qapp_session):
    settings = main_window._settings
    radio = settings._trigger_continuous_rb
    radio.setChecked(True)
    radio.setFocus()
    _qapp_session.processEvents()
    QTest.keyClick(radio, Qt.Key.Key_Right)
    assert settings._trigger_hotkey_rb.isChecked()


def test_polish_disabled_removes_configuration_and_example(main_window):
    win = main_window._settings
    win._llm_enable_row.setChecked(True)
    assert not win._llm_container.isHidden()
    win._llm_enable_row.setChecked(False)
    assert win._llm_container.isHidden()
    assert win._llm_preview_card.isHidden()


def test_audio_error_remains_inline_with_recovery(main_window, monkeypatch):
    win = main_window._settings
    monkeypatch.setattr("voiceink.ui.settings_window.QMessageBox.warning",
                        lambda *args: pytest.fail("Audio feedback should remain in context"))
    win._mic_probe_active = True
    win._on_mic_probe_error("设备不可用")
    assert "设备不可用" in win._mic_test_status.text()
    assert "手动选择" in win._mic_test_status.text()
    assert win._mic_test_btn.isEnabled()


def test_download_is_disabled_immediately_and_error_can_retry(main_window, monkeypatch):
    from unittest.mock import MagicMock
    from voiceink.ui.model_card import ModelCard
    win = main_window._settings
    info = {"id": "preview", "name": "示例", "size_mb": 10, "description": "示例",
            "languages": "中文", "accuracy": 3, "speed": 3}
    card = ModelCard(info, False, False)
    worker = MagicMock()
    monkeypatch.setattr("voiceink.speech_recognizer.ModelDownloadWorker", lambda _mid: worker)
    monkeypatch.setattr("voiceink.ui.settings_window.QMessageBox.warning",
                        lambda *args: pytest.fail("Download error should stay on the card"))
    win._model_cards["preview"] = card
    try:
        win._start_download("preview")
        win._start_download("preview")
        worker.start.assert_called_once()
        assert not card._action_btn.isEnabled()
        win._on_dl_error("网络不可用", card)
        assert card._action_btn.isEnabled()
        assert card._action_btn.text() == "重试"
        assert "网络不可用" in card._error_label.text()
        assert not card._error_label.isHidden()
    finally:
        card.close()


def test_history_rows_reflow_to_splitter_width(_qapp_session):
    win = HistoryWindow(FakeHistoryStore())
    try:
        win.resize(780, 580)
        win.show()
        _qapp_session.processEvents()
        win._splitter.setSizes([220, 500])
        _qapp_session.processEvents()
        row = win._session_list.itemWidget(win._session_list.item(0))
        assert row.width() <= win._session_list.viewport().width()
    finally:
        win.close()


def test_history_can_load_older_sessions(_qapp_session):
    from dataclasses import replace
    store = FakeHistoryStore()
    original = store.sessions[0]
    store.sessions = [replace(original, session_id=f"session-{i}") for i in range(55)]
    store.segments = {s.session_id: [] for s in store.sessions}
    win = HistoryWindow(store)
    try:
        assert win._session_list.count() == 50
        assert not win._more_btn.isHidden()
        win._load_more()
        assert win._session_list.count() == 55
        assert win._more_btn.isHidden()
    finally:
        win.close()


def test_disabled_empty_history_links_to_preference(main_window):
    history = main_window._history
    history.set_history_enabled(False)
    assert not history._history_preferences_btn.isHidden()
    assert "未开启" in history._details.toPlainText()
    history._history_preferences_btn.click()
    assert main_window.current_page() == "general"


def test_refresh_keeps_search_and_current_selection(_qapp_session):
    store = FakeHistoryStore()
    win = HistoryWindow(store)
    try:
        win._session_list.setCurrentRow(1)
        win.refresh()
        assert win._selected_session_ids() == ["older"]
        win._search_edit.setText("older")
        win._perform_search()
        win.refresh()
        assert store.search_terms[-1] == "older"
        assert win._session_list.count() == 1
    finally:
        win.close()


def test_repeated_delete_and_refresh_preserve_single_undo_batch(_qapp_session, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    store = FakeHistoryStore()
    win = HistoryWindow(store)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    try:
        win._delete_selected_sessions()
        win.refresh()
        assert win._session_list.count() == 1
        assert win._selected_session_ids() == ["older"]
        win._delete_selected_sessions()
        win.refresh()
        assert win._session_list.count() == 0
        assert len(win._pending_delete) == 2
        win._undo_pending_delete()
        assert win._session_list.count() == 2
        assert store.deleted_sessions == []
    finally:
        win.close()


def test_listen_bar_stop_action_matches_session_state(_qapp_session):
    from voiceink.ui.floating_window import FloatingWindow
    bar = FloatingWindow()
    try:
        bar.show_model_loading()
        assert bar._end_btn.isHidden()
        bar.show_listening()
        assert not bar._end_btn.isHidden()
        assert "停顿" in bar._status_label.text()
        from voiceink.ui.theme import apply_theme
        from voiceink.ui import design_tokens as tok
        apply_theme(mode="dark", surfaces=[bar])
        assert tok.STATE_LISTEN in bar._status_label.styleSheet()
        assert bar._dot._color.name().lower() == tok.STATE_LISTEN.lower()
        bar.show_continuous_stopped()
        assert bar._end_btn.isHidden()
        bar.show_recording()
        assert bar._end_btn.isHidden()
    finally:
        bar.dismiss_if_idle()


def test_clear_all_cancels_pending_undo(_qapp_session, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    store = FakeHistoryStore()
    win = HistoryWindow(store)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    try:
        win._delete_selected_sessions()
        win._clear_all_history()
        assert store.deleted_all
        assert win._pending_delete == []
        assert not win._undo_timer.isActive()
        assert win._undo_bar.isHidden()
    finally:
        win.close()
