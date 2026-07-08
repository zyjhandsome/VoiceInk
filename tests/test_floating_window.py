"""Tests for the floating status HUD (voiceink/ui/floating_window.py)."""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication

from voiceink.ui.floating_window import (
    FloatingWindow,
    WaveformWidget,
    _DotIndicator,
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def win(qapp):
    w = FloatingWindow()
    yield w
    w.close()


class TestFloatingWindowStates:
    def test_initial_flags(self, win):
        assert win._listening_active is False
        assert win._model_loading_active is False

    def test_show_listening_sets_flags(self, win):
        win.show_listening()
        assert win._listening_active is True
        assert win._model_loading_active is False
        assert "自动监听" in win._status_label.text()

    def test_show_continuous_idle_sets_hint(self, win):
        win.show_continuous_idle("Alt+Space")
        assert win._listening_active is False
        assert "Alt+Space" in win._text_label.text()

    def test_show_continuous_stopped(self, win):
        win.show_listening()
        win.show_continuous_stopped()
        assert win._listening_active is False
        assert "已停止" in win._status_label.text()

    def test_show_recording(self, win):
        win.show_recording()
        assert win._listening_active is False
        assert "录音中" in win._status_label.text()

    def test_show_recognizing_truncates_long_text(self, win):
        long_text = "字" * 80
        win.show_recognizing(long_text)
        assert win._status_label.text() == "识别中"
        assert win._text_label.text().startswith("...")

    def test_show_polishing(self, win):
        win.show_polishing("润色文本")
        assert win._status_label.text() == "润色中"

    def test_show_success_with_subtitle(self, win):
        win.show_success("已输入", "可按 Ctrl+V")
        assert win._status_label.text() == "已输入"
        assert win._text_label.text() == "可按 Ctrl+V"

    def test_show_info(self, win):
        win.show_info("已输入（原文）")
        assert win._status_label.text() == "已输入（原文）"

    def test_show_cancelled(self, win):
        win.show_cancelled()
        assert win._status_label.text() == "已取消"

    def test_show_busy_transcribing(self, win):
        win.show_busy_transcribing()
        assert "请稍候" in win._status_label.text()

    def test_update_partial_text(self, win):
        win.update_partial_text("部分文本")
        assert win._text_label.text() == "部分文本"

    def test_update_volume_forwards_to_waveform(self, win):
        win.update_volume(0.5)
        assert win._waveform._volume == pytest.approx(min(0.5 * 8, 1.0))


class TestModelLoadingGuard:
    """FR-UI-04 / P0: model-loading state must not be overwritten by errors/warnings."""

    def test_error_suppressed_during_model_loading(self, win):
        win.show_model_loading("载入中")
        assert win._model_loading_active is True
        win.show_error("识别失败")
        # Still showing model-loading state, error was ignored.
        assert win._status_label.text() == "模型加载中"

    def test_warning_suppressed_during_model_loading(self, win):
        win.show_model_loading()
        win.show_warning("音频受限")
        assert win._status_label.text() == "模型加载中"

    def test_clear_lock_allows_errors_again(self, win):
        win.show_model_loading()
        win.clear_model_loading_lock()
        assert win._model_loading_active is False
        win.show_error("识别失败")
        assert win._status_label.text() == "识别失败"

    def test_success_clears_loading_flag(self, win):
        win.show_model_loading()
        win.show_success("已就绪")
        assert win._model_loading_active is False


class TestCloseButton:
    def test_close_emits_stop_when_listening(self, win):
        stops = []
        win.continuous_stop_requested.connect(lambda: stops.append(True))
        win.show_listening()
        win._on_close_clicked()
        assert stops == [True]

    def test_close_dismisses_when_idle(self, win):
        win.show_continuous_idle("Alt+Space")
        win._on_close_clicked()
        assert win.isVisible() is False

    def test_update_close_button_tooltip(self, win):
        win.show_listening()
        win._update_close_button()
        assert "结束" in win._close_btn.toolTip()


class TestSubWidgets:
    def test_dot_indicator_pulse_lifecycle(self, qapp):
        dot = _DotIndicator()
        dot.start_pulse()
        assert dot._timer.isActive()
        dot.stop_pulse()
        assert not dot._timer.isActive()

    def test_waveform_start_stop(self, qapp):
        wf = WaveformWidget()
        wf.start()
        assert wf._timer.isActive()
        wf.set_volume(1.0)
        wf._animate()
        wf.stop()
        assert not wf._timer.isActive()
        assert all(h == 0.0 for h in wf._bar_heights)
