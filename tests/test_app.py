import pytest
import numpy as np

from voiceink.app import App, MIN_AUDIO_SAMPLES
from tests.helpers.app_harness import app_harness


class TestAppConstants:
    def test_min_audio_samples(self):
        assert MIN_AUDIO_SAMPLES == 1600


class TestAppErrorHints:
    def test_error_hints_defined(self):
        assert isinstance(App.ERROR_HINTS, dict)

    @pytest.mark.parametrize(
        "keyword",
        [
            "麦克风",
            "模型未就绪",
            "模型未下载",
            "录音过短",
            "未识别",
            "润色失败",
            "输出失败",
        ],
    )
    def test_error_hints_cover_common_cases(self, keyword):
        assert keyword in App.ERROR_HINTS


class TestAppFriendlyError:
    def test_friendly_error_with_keyword(self):
        app = App.__new__(App)
        app.ERROR_HINTS = App.ERROR_HINTS
        result = app._friendly_error("无法访问麦克风")
        assert "麦克风" in result or "检查" in result

    def test_friendly_error_without_keyword(self):
        app = App.__new__(App)
        app.ERROR_HINTS = App.ERROR_HINTS
        result = app._friendly_error("未知错误")
        assert result == "未知错误"

    def test_friendly_error_returns_hint(self):
        app = App.__new__(App)
        app.ERROR_HINTS = App.ERROR_HINTS
        result = app._friendly_error("模型加载失败，模型未就绪")
        assert "模型未就绪" in result


class TestAppInit:
    def test_init_creates_modules(self):
        with app_harness() as h:
            app = h["app"]
            assert hasattr(app, "_config")
            assert hasattr(app, "_hotkey_mgr")
            assert hasattr(app, "_recorder")
            assert hasattr(app, "_recognizer")
            assert hasattr(app, "_polisher")
            assert hasattr(app, "_paster")
            assert hasattr(app, "_sound")

    def test_init_creates_ui(self):
        with app_harness() as h:
            app = h["app"]
            assert hasattr(app, "_floating")
            assert hasattr(app, "_tray")
            assert hasattr(app, "_settings_win")


class TestAppSignals:
    def test_signals_connected(self):
        with app_harness() as h:
            assert hasattr(h["app"], "_connect_signals")


class TestAppState:
    def test_initial_transcription_empty(self):
        with app_harness() as h:
            app = h["app"]
            assert app._current_transcription == ""
            assert app._is_transcribing is False


class TestAppMethods:
    def test_has_show_settings(self):
        with app_harness() as h:
            app = h["app"]
            assert hasattr(app, "_show_settings")
            assert callable(app._show_settings)

    def test_has_quit(self):
        with app_harness() as h:
            app = h["app"]
            assert hasattr(app, "_quit")
            assert callable(app._quit)

    def test_has_start(self):
        with app_harness() as h:
            app = h["app"]
            assert hasattr(app, "start")
            assert callable(app.start)


class TestCoreSignalIntegrity:
    """NFR-REL-03: the four core signals must be wired in _connect_signals."""

    def test_core_signals_connected(self):
        with app_harness() as h:
            h["hotkey"].esc_pressed.connect.assert_called()
            h["recognizer"].ready.connect.assert_called()
            h["recognizer"].model_load_progress.connect.assert_called()
            h["recorder"].segment_ready.connect.assert_called()

    def test_recognizer_final_and_error_connected(self):
        with app_harness() as h:
            h["recognizer"].final_result.connect.assert_called()
            h["recognizer"].error.connect.assert_called()


class TestHandlePasteResult:
    def test_pasted_non_continuous_shows_success(self):
        with app_harness() as h:
            app = h["app"]
            app._handle_paste_result("pasted")
            h["floating"].show_success.assert_any_call("已输入")

    def test_clipboard_shows_copied_hint(self):
        with app_harness() as h:
            app = h["app"]
            app._handle_paste_result("clipboard")
            assert h["floating"].show_success.called
            args = h["floating"].show_success.call_args[0]
            assert "已复制" in args[0]

    def test_error_shows_friendly_error(self):
        with app_harness() as h:
            app = h["app"]
            app._handle_paste_result("error:目标不可写")
            assert h["floating"].show_error.called

    def test_degraded_from_polish_shows_info(self):
        with app_harness() as h:
            app = h["app"]
            app._handle_paste_result("pasted", degraded_from_polish=True)
            h["floating"].show_info.assert_any_call("已输入（原文）")


class TestHotkeyTapTooShortHint:
    def test_hint_uses_derived_hold_duration(self):
        # SD-07 regression: user-facing hint must match MIN_HOLD_MS (0.12s).
        with app_harness() as h:
            app = h["app"]
            h["recorder"].is_continuous = False
            app._on_hotkey_tap_too_short()
            assert h["tray"].showMessage.called
            hint = h["tray"].showMessage.call_args[0][1]
            assert "0.12" in hint


class TestSettingsChangedQueue:
    def test_pending_queue_cleared_on_settings_change(self):
        with app_harness() as h:
            app = h["app"]
            app._segment_queue = [np.zeros(1600, dtype=np.float32)] * 3
            h["recorder"].is_continuous = False
            app._on_settings_changed()
            assert app._segment_queue == []

    def test_pending_segment_count_counts_queue_and_active(self):
        with app_harness() as h:
            app = h["app"]
            app._segment_queue = [np.zeros(1600, dtype=np.float32)] * 2
            app._is_transcribing = True
            assert app._pending_segment_count() == 3


class TestSegmentReadyQueueing:
    def test_short_segment_ignored(self):
        with app_harness() as h:
            app = h["app"]
            app._on_segment_ready(np.zeros(10, dtype=np.float32))
            assert app._segment_queue == []

    def test_segment_queued_when_transcribing(self):
        with app_harness() as h:
            app = h["app"]
            h["recognizer"].is_ready = True
            app._is_transcribing = True
            app._on_segment_ready(np.zeros(1600, dtype=np.float32))
            assert len(app._segment_queue) == 1

    def test_segment_queued_while_model_loading(self):
        with app_harness() as h:
            app = h["app"]
            h["recognizer"].is_ready = False
            h["recognizer"].is_loading = True
            app._on_segment_ready(np.zeros(1600, dtype=np.float32))
            assert len(app._segment_queue) == 1


class TestFinalResultFlow:
    def test_empty_result_non_continuous_shows_error(self):
        with app_harness(config_overrides={"audio.trigger_mode": "hotkey"}) as h:
            app = h["app"]
            h["recognizer"].is_ready = True
            h["recognizer"].is_loading = False
            app._is_transcribing = True
            app._on_final_result("   ")
            assert h["floating"].show_error.called
            assert app._is_transcribing is False

    def test_result_outputs_directly_when_llm_disabled(self):
        with app_harness() as h:
            app = h["app"]
            h["recognizer"].is_ready = True
            app._on_final_result("你好世界")
            h["paster"].paste_async.assert_called()

    def test_result_triggers_polish_when_enabled(self):
        overrides = {
            "llm.enabled": True,
            "llm.api_url": "https://api.example.com/v1",
            "llm.api_key": "k",
            "llm.model_name": "m",
        }
        with app_harness(config_overrides=overrides) as h:
            app = h["app"]
            h["recognizer"].is_ready = True
            app._on_final_result("你好世界")
            h["polisher"].polish.assert_called()
            h["paster"].paste_async.assert_not_called()


class TestBeginTranscription:
    def test_begin_transcription_calls_recognizer(self):
        with app_harness() as h:
            app = h["app"]
            h["recognizer"].is_ready = True
            audio = np.ones(1600, dtype=np.float32)
            app._begin_transcription(audio)
            assert app._is_transcribing is True
            h["recognizer"].transcribe_final.assert_called_once()

    def test_begin_transcription_requeues_when_loading(self):
        with app_harness() as h:
            app = h["app"]
            h["recognizer"].is_ready = False
            h["recognizer"].is_loading = True
            audio = np.ones(1600, dtype=np.float32)
            app._begin_transcription(audio)
            assert app._is_transcribing is False
            assert len(app._segment_queue) == 1
