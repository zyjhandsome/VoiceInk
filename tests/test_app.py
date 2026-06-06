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
