import pytest
from voiceink.text_polisher import TextPolisher, PolishWorker, POLISH_PROMPT


class TestPolishPrompt:
    def test_prompt_exists(self):
        assert POLISH_PROMPT is not None
        assert len(POLISH_PROMPT) > 0

    def test_prompt_contains_rules(self):
        assert "润色" in POLISH_PROMPT
        assert "规则" in POLISH_PROMPT or "严格规则" in POLISH_PROMPT

    def test_prompt_mentions_no_response(self):
        assert "不要回答" in POLISH_PROMPT or "不要" in POLISH_PROMPT

    def test_prompt_has_examples(self):
        assert "示例" in POLISH_PROMPT
        assert "输入" in POLISH_PROMPT
        assert "输出" in POLISH_PROMPT


class TestPolishWorkerInit:
    def test_init_requires_api_params(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="test_key",
            model_name="test_model",
            text="测试文本"
        )
        assert worker._api_url == "https://api.example.com"
        assert worker._api_key == "test_key"
        assert worker._model_name == "test_model"
        assert worker._text == "测试文本"
        assert worker._cancelled is False

    def test_init_strips_trailing_slash(self):
        worker = PolishWorker(
            api_url="https://api.example.com/",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._api_url == "https://api.example.com"

    def test_init_custom_prompt(self):
        custom_prompt = "自定义提示词"
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text",
            prompt=custom_prompt
        )
        assert worker._prompt == custom_prompt

    def test_init_default_prompt(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._prompt == POLISH_PROMPT


class TestPolishWorkerCancel:
    def test_cancel_flag_initially_false(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._cancelled is False

    def test_cancel_sets_flag(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text"
        )
        worker.cancel()
        assert worker._cancelled is True

    def test_double_cancel(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text"
        )
        worker.cancel()
        worker.cancel()
        assert worker._cancelled is True


class TestPolishWorkerSignals:
    def test_signals_defined(self):
        worker = PolishWorker(
            api_url="https://api.example.com",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert hasattr(worker, "result_ready")
        assert hasattr(worker, "error")


class TestTextPolisherInit:
    def test_init_no_worker(self):
        polisher = TextPolisher()
        assert polisher._worker is None


class TestTextPolisherPolish:
    def test_polish_empty_text(self):
        polisher = TextPolisher()
        emitted_values = []
        polisher.polish_complete.connect(lambda x: emitted_values.append(x))
        polisher.polish("", "https://api.example.com", "key", "model")
        assert len(emitted_values) == 1
        assert emitted_values[0] == ""


class TestTextPolisherCancel:
    def test_cancel_no_worker(self):
        polisher = TextPolisher()
        polisher.cancel()
        assert polisher._worker is None


class TestTestConnection:
    def test_https_required(self):
        success, message = TextPolisher.test_connection(
            "http://api.example.com",
            "key",
            "model"
        )
        assert success is False
        assert "HTTPS" in message or "安全" in message

    def test_https_rejected(self):
        success, message = TextPolisher.test_connection(
            "http://insecure-api.com/chat/completions",
            "key",
            "model"
        )
        assert success is False


class TestApiUrlConstruction:
    def test_url_with_chat_completions(self):
        worker = PolishWorker(
            api_url="https://api.example.com/chat/completions",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._api_url == "https://api.example.com"

    def test_url_without_chat_completions(self):
        worker = PolishWorker(
            api_url="https://api.example.com/v1",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._api_url == "https://api.example.com"


class TestTextPolisherSignals:
    def test_signals_defined(self):
        polisher = TextPolisher()
        assert hasattr(polisher, "polish_complete")
        assert hasattr(polisher, "polish_error")
