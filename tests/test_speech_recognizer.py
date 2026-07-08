import pytest
import numpy as np
from voiceink.speech_recognizer import (
    MODEL_REGISTRY, normalize_asr_output, get_model_info,
    is_model_downloaded, get_model_dir, _get_models_dir,
    SAMPLE_RATE, DEFAULT_MODEL_ID,
)


class TestSampleRate:
    def test_sample_rate_constant(self):
        assert SAMPLE_RATE == 16000


class TestDefaultModel:
    def test_default_model_is_fireredasr2_ctc(self):
        assert DEFAULT_MODEL_ID == "fireredasr2-ctc"
        info = get_model_info(DEFAULT_MODEL_ID)
        assert info is not None
        assert info["name"] == "FireRedASR2"


class TestNormalizeAsrOutput:
    def test_empty_string(self):
        result = normalize_asr_output("")
        assert result == ""

    def test_none_input(self):
        result = normalize_asr_output(None)
        assert result == ""

    def test_no_tags(self):
        text = "这是一段正常的语音识别结果"
        result = normalize_asr_output(text)
        assert result == text

    def test_removes_opening_tag(self):
        text = "<asr_text>识别结果</asr_text>"
        result = normalize_asr_output(text)
        assert "<asr_text>" not in result
        assert "识别结果" in result

    def test_removes_closing_tag(self):
        text = "开头<asr_text>中间</asr_text>结尾"
        result = normalize_asr_output(text)
        assert "<asr_text>" not in result
        assert "</asr_text>" not in result
        assert "开头" in result
        assert "中间" in result
        assert "结尾" in result

    def test_case_insensitive(self):
        text = "<ASR_TEXT>测试</ASR_TEXT>"
        result = normalize_asr_output(text)
        assert result == "测试"

    def test_strips_whitespace(self):
        text = "  <asr_text>内容</asr_text>  "
        result = normalize_asr_output(text)
        assert result == "内容"

    def test_opening_tag_only_before_text(self):
        """Qwen3 may emit ``<asr_text>嗯`` without a closing tag."""
        text = "<asr_text>嗯"
        result = normalize_asr_output(text)
        assert result == "嗯"
        assert "asr_text" not in result

    def test_removes_fireredasr_sil_tokens(self):
        text = "给他购买还出现了个什么标识呢<sil>个没有点伟大<sil><sil><sil>"
        result = normalize_asr_output(text)
        assert "<sil>" not in result
        assert result == "给他购买还出现了个什么标识呢个没有点伟大"

    def test_removes_fireredasr_lang_tags(self):
        text = "<zh>你好<en>hello"
        result = normalize_asr_output(text)
        assert "<" not in result
        assert result == "你好hello"


class TestModelRegistry:
    def test_registry_not_empty(self):
        assert len(MODEL_REGISTRY) >= 7

    def test_all_models_have_required_fields(self):
        required_fields = ["id", "name", "description", "accuracy", "speed", "languages", "size_mb", "loader", "hf_repo", "dir_name", "files"]
        for model in MODEL_REGISTRY:
            for field in required_fields:
                assert field in model, f"Model {model.get('id', 'unknown')} missing field {field}"

    def test_all_models_have_valid_accuracy(self):
        for model in MODEL_REGISTRY:
            accuracy = model["accuracy"]
            assert 1 <= accuracy <= 5

    def test_all_models_have_valid_speed(self):
        for model in MODEL_REGISTRY:
            speed = model["speed"]
            assert 1 <= speed <= 5

    def test_all_models_have_files_list(self):
        for model in MODEL_REGISTRY:
            files = model["files"]
            assert isinstance(files, list)
            assert len(files) > 0


class TestModelRegistryContent:
    def test_sensevoice_model(self):
        model = get_model_info("sensevoice")
        assert model is not None
        assert model["id"] == "sensevoice"
        assert model["loader"] == "sense_voice"

    def test_paraformer_zh_model(self):
        model = get_model_info("paraformer-zh")
        assert model is not None
        assert model["id"] == "paraformer-zh"
        assert model["loader"] == "paraformer"

    def test_fireredasr2_ctc_model(self):
        model = get_model_info("fireredasr2-ctc")
        assert model is not None
        assert model["id"] == "fireredasr2-ctc"
        assert model["loader"] == "fire_red_asr_ctc"

    def test_qwen3_asr_model(self):
        model = get_model_info("qwen3-asr-0.6b")
        assert model is not None
        assert model["id"] == "qwen3-asr-0.6b"
        assert model["loader"] == "qwen3_asr"

    def test_qwen3_asr_1_7b_model(self):
        model = get_model_info("qwen3-asr-1.7b")
        assert model is not None
        assert model["id"] == "qwen3-asr-1.7b"
        assert model["loader"] == "qwen3_asr"
        assert model["size_mb"] == 2400

    def test_unknown_model(self):
        model = get_model_info("nonexistent_model")
        assert model is None


class TestGetModelInfo:
    def test_returns_model_dict(self):
        model = get_model_info("sensevoice")
        assert isinstance(model, dict)

    def test_model_has_files(self):
        model = get_model_info("sensevoice")
        assert "files" in model
        assert isinstance(model["files"], list)


class TestIsModelDownloaded:
    def test_unknown_model_not_downloaded(self):
        result = is_model_downloaded("nonexistent_model_12345")
        assert result is False

    def test_valid_model_check(self):
        result = is_model_downloaded("sensevoice")
        assert isinstance(result, bool)


class TestGetModelsDir:
    def test_returns_path(self):
        result = _get_models_dir()
        from pathlib import Path
        assert isinstance(result, Path)


class TestGetModelDir:
    def test_unknown_model_raises(self):
        with pytest.raises(ValueError):
            get_model_dir("nonexistent_model_xyz")

    def test_valid_model_returns_path(self):
        result = get_model_dir("sensevoice")
        from pathlib import Path
        assert isinstance(result, Path)


class TestModelAccuracySpeed:
    def test_qwen3_high_accuracy(self):
        model = get_model_info("qwen3-asr-0.6b")
        assert model["accuracy"] == 5

    def test_qwen3_1_7b_slowest_speed(self):
        model = get_model_info("qwen3-asr-1.7b")
        assert model["accuracy"] == 5
        assert model["speed"] == 1

    def test_sensevoice_fast_speed(self):
        model = get_model_info("sensevoice")
        assert model["speed"] == 5

    def test_fireredasr2_aed_highest_accuracy(self):
        model = get_model_info("fireredasr2-aed")
        assert model["accuracy"] == 5
        assert model["speed"] == 2


class TestModelLanguages:
    def test_sensevoice_multilingual(self):
        model = get_model_info("sensevoice")
        assert "中" in model["languages"]
        assert "英" in model["languages"]

    def test_zipformer_chinese_only(self):
        model = get_model_info("zipformer-ctc-zh")
        assert model["languages"] == "中"


class TestResolveStartupModelId:
    def test_uses_configured_when_downloaded(self, monkeypatch):
        from voiceink.speech_recognizer import resolve_startup_model_id

        monkeypatch.setattr(
            "voiceink.speech_recognizer.is_model_downloaded",
            lambda mid: mid == "sensevoice",
        )
        monkeypatch.setattr(
            "voiceink.speech_recognizer.get_downloaded_models",
            lambda: ["sensevoice"],
        )
        assert resolve_startup_model_id("sensevoice") == "sensevoice"

    def test_prefers_default_when_configured_missing(self, monkeypatch):
        from voiceink.speech_recognizer import (
            DEFAULT_MODEL_ID,
            resolve_startup_model_id,
        )

        monkeypatch.setattr(
            "voiceink.speech_recognizer.is_model_downloaded",
            lambda mid: mid == DEFAULT_MODEL_ID,
        )
        monkeypatch.setattr(
            "voiceink.speech_recognizer.get_downloaded_models",
            lambda: [DEFAULT_MODEL_ID],
        )
        assert resolve_startup_model_id("qwen3-asr-0.6b") == DEFAULT_MODEL_ID

    def test_falls_back_to_any_downloaded(self, monkeypatch):
        from voiceink.speech_recognizer import resolve_startup_model_id

        monkeypatch.setattr(
            "voiceink.speech_recognizer.is_model_downloaded",
            lambda mid: mid == "qwen3-asr-0.6b",
        )
        monkeypatch.setattr(
            "voiceink.speech_recognizer.get_downloaded_models",
            lambda: ["qwen3-asr-0.6b"],
        )
        assert resolve_startup_model_id("fireredasr2-ctc") == "qwen3-asr-0.6b"

    def test_returns_configured_when_nothing_downloaded(self, monkeypatch):
        from voiceink.speech_recognizer import resolve_startup_model_id

        monkeypatch.setattr(
            "voiceink.speech_recognizer.is_model_downloaded", lambda mid: False
        )
        monkeypatch.setattr(
            "voiceink.speech_recognizer.get_downloaded_models", lambda: []
        )
        assert resolve_startup_model_id("sensevoice") == "sensevoice"

    def test_blank_configured_falls_back_to_default(self, monkeypatch):
        from voiceink.speech_recognizer import (
            DEFAULT_MODEL_ID,
            resolve_startup_model_id,
        )

        monkeypatch.setattr(
            "voiceink.speech_recognizer.is_model_downloaded",
            lambda mid: mid == DEFAULT_MODEL_ID,
        )
        monkeypatch.setattr(
            "voiceink.speech_recognizer.get_downloaded_models",
            lambda: [DEFAULT_MODEL_ID],
        )
        assert resolve_startup_model_id("") == DEFAULT_MODEL_ID


class TestModelsDirGlobal:
    def test_set_models_dir_used_by_get_model_dir(self, tmp_path, monkeypatch):
        from voiceink import speech_recognizer as sr

        monkeypatch.setattr(sr, "_get_portable_model_dir", lambda mid: None)
        try:
            sr.set_models_dir(tmp_path)
            d = sr.get_model_dir("fireredasr2-ctc")
            assert str(d).startswith(str(tmp_path))
        finally:
            sr.set_models_dir(None)

    def test_get_model_dir_unknown_raises(self):
        from voiceink.speech_recognizer import get_model_dir

        with pytest.raises(ValueError):
            get_model_dir("no-such-model")

    def test_delete_unknown_model_returns_false(self):
        from voiceink.speech_recognizer import delete_model

        assert delete_model("no-such-model") is False

    def test_delete_missing_dir_returns_false(self, tmp_path, monkeypatch):
        from voiceink import speech_recognizer as sr

        monkeypatch.setattr(sr, "_get_portable_model_dir", lambda mid: None)
        try:
            sr.set_models_dir(tmp_path)
            assert sr.delete_model("fireredasr2-ctc") is False
        finally:
            sr.set_models_dir(None)


class _FakeStream:
    def __init__(self, text):
        self.result = type("R", (), {"text": text})()

    def accept_waveform(self, sr, audio):
        self._audio = audio


class _FakeRecognizer:
    def __init__(self, text="识别文本"):
        self._text = text

    def create_stream(self):
        return _FakeStream(self._text)

    def decode_stream(self, stream):
        pass


class TestTranscribeWorkerRun:
    def _run(self, worker):
        from unittest.mock import MagicMock

        results, errors = [], []
        worker.result_ready.connect(results.append)
        worker.error.connect(errors.append)
        worker.run()
        return results, errors

    def test_run_emits_normalized_result(self):
        from voiceink.speech_recognizer import TranscribeWorker

        rec = _FakeRecognizer("<asr_text>你好</asr_text>")
        worker = TranscribeWorker(rec, np.ones(16000, dtype=np.float32))
        results, errors = self._run(worker)
        assert results == ["你好"]
        assert errors == []

    def test_run_empty_audio_emits_error(self):
        from voiceink.speech_recognizer import TranscribeWorker

        worker = TranscribeWorker(_FakeRecognizer(), np.array([], dtype=np.float32))
        results, errors = self._run(worker)
        assert results == []
        assert errors and "音频数据无效" in errors[0]

    def test_run_nan_audio_emits_error(self):
        from voiceink.speech_recognizer import TranscribeWorker

        bad = np.array([np.nan, np.nan], dtype=np.float32)
        worker = TranscribeWorker(_FakeRecognizer(), bad)
        results, errors = self._run(worker)
        assert errors and "音频数据无效" in errors[0]

    def test_run_cancelled_does_nothing(self):
        from voiceink.speech_recognizer import TranscribeWorker

        worker = TranscribeWorker(_FakeRecognizer(), np.ones(16000, dtype=np.float32))
        worker.cancel()
        results, errors = self._run(worker)
        assert results == [] and errors == []

    def test_run_recognizer_exception_emits_error(self):
        from voiceink.speech_recognizer import TranscribeWorker

        rec = _FakeRecognizer()
        rec.decode_stream = lambda s: (_ for _ in ()).throw(RuntimeError("boom"))
        worker = TranscribeWorker(rec, np.ones(16000, dtype=np.float32))
        results, errors = self._run(worker)
        assert results == []
        assert errors and "识别失败" in errors[0]


class TestModelLoadWorkerRun:
    def test_run_success_emits_loaded(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        sentinel = object()
        monkeypatch.setattr(sr, "_create_recognizer", lambda mid, n: sentinel)
        worker = sr.ModelLoadWorker("fireredasr2-ctc", 4)
        loaded, errors = [], []
        worker.loaded.connect(loaded.append)
        worker.error.connect(errors.append)
        worker.run()
        assert loaded == [sentinel]
        assert errors == []

    def test_run_failure_emits_error(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        def _boom(mid, n):
            raise RuntimeError("load failed")

        monkeypatch.setattr(sr, "_create_recognizer", _boom)
        worker = sr.ModelLoadWorker("fireredasr2-ctc", 4)
        loaded, errors = [], []
        worker.loaded.connect(loaded.append)
        worker.error.connect(errors.append)
        worker.run()
        assert loaded == []
        assert errors and "模型加载失败" in errors[0]


class TestSpeechRecognizerBehavior:
    def test_transcribe_final_not_ready_emits_error(self):
        from voiceink.speech_recognizer import SpeechRecognizer

        rec = SpeechRecognizer()
        errors = []
        rec.error.connect(errors.append)
        rec.transcribe_final(np.ones(1600, dtype=np.float32))
        assert errors and "未就绪" in errors[0]

    def test_stale_result_is_ignored(self):
        from voiceink.speech_recognizer import SpeechRecognizer

        rec = SpeechRecognizer()
        finals = []
        rec.final_result.connect(finals.append)
        rec._active_seq = 5
        rec._on_final_result("新结果", 5)
        rec._on_final_result("过时结果", 4)
        assert finals == ["新结果"]

    def test_stale_error_is_ignored(self):
        from voiceink.speech_recognizer import SpeechRecognizer

        rec = SpeechRecognizer()
        errors = []
        rec.error.connect(errors.append)
        rec._active_seq = 2
        rec._on_worker_error("当前错误", 2)
        rec._on_worker_error("过时错误", 1)
        assert errors == ["当前错误"]

    def test_transcribe_final_no_terminate_and_supersedes(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        # Do not run real threads; capture worker lifecycle instead.
        monkeypatch.setattr(sr.TranscribeWorker, "start", lambda self: None)
        monkeypatch.setattr(sr.TranscribeWorker, "isRunning", lambda self: True)

        rec = sr.SpeechRecognizer()
        rec._is_ready = True
        rec._recognizer = _FakeRecognizer()

        rec.transcribe_final(np.ones(1600, dtype=np.float32))
        first = rec._current_worker
        assert rec._active_seq == 1

        rec.transcribe_final(np.ones(1600, dtype=np.float32))
        assert rec._active_seq == 2
        assert first._cancelled is True  # old worker cancelled, not terminated

    def test_configure_skips_when_model_not_downloaded(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        monkeypatch.setattr(sr, "is_model_downloaded", lambda mid: False)
        loads = []
        monkeypatch.setattr(
            sr.SpeechRecognizer, "_load_model", lambda self: loads.append(True)
        )
        rec = sr.SpeechRecognizer()
        rec.configure("fireredasr2-ctc", 4)
        assert loads == []

    def test_configure_triggers_load_when_downloaded(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        monkeypatch.setattr(sr, "is_model_downloaded", lambda mid: True)
        loads = []
        monkeypatch.setattr(
            sr.SpeechRecognizer, "_load_model", lambda self: loads.append(True)
        )
        rec = sr.SpeechRecognizer()
        rec.configure("fireredasr2-ctc", 4)
        assert loads == [True]

    def test_configure_skips_reload_when_ready(self, monkeypatch):
        from voiceink import speech_recognizer as sr

        monkeypatch.setattr(sr, "is_model_downloaded", lambda mid: True)
        loads = []
        monkeypatch.setattr(
            sr.SpeechRecognizer, "_load_model", lambda self: loads.append(True)
        )
        rec = sr.SpeechRecognizer()
        rec._model_id = "fireredasr2-ctc"
        rec._num_threads = 4
        rec._is_ready = True
        rec._recognizer = _FakeRecognizer()
        rec.configure("fireredasr2-ctc", 4)
        assert loads == []  # already resident, no reload

    def test_is_ready_and_current_model_properties(self):
        from voiceink.speech_recognizer import SpeechRecognizer

        rec = SpeechRecognizer()
        assert rec.is_ready is False
        assert rec.is_loading is False
        assert rec.current_model_id == ""
