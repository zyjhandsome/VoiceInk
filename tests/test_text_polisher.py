import sys
from unittest.mock import MagicMock, patch

import pytest

from voiceink.text_polisher import (
    INSECURE_URL_ERROR,
    POLISH_PROMPT,
    PolishWorker,
    TextPolisher,
    is_secure_or_local_url,
)


class TestSecureOrLocalUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://api.deepseek.com/v1",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "http://localhost:11434/v1",
            "http://127.0.0.1:11434/v1",
            "http://[::1]:11434/v1",
            "http://localhost/chat/completions",
        ],
    )
    def test_allowed_urls(self, url):
        assert is_secure_or_local_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "http://api.example.com/v1",
            "http://8.8.8.8/v1",测试文本测试文本
            "http://insecure-remote.com/chat/completions",
            "ftp://localhost/x",
            "",
            "   ",
        ],
    )
    def test_rejected_urls(self, url):
        assert is_secure_or_local_url(url) is False

    def test_ollama_default_endpoint_allowed(self):
        # Regression for SD-03: Ollama's default HTTP endpoint must be usable.
        assert is_secure_or_local_url("http://localhost:11434/v1") is True


def _fake_httpx_module(response=None, raise_exc=None):
    """Build a fake ``httpx`` module usable as ``import httpx`` inside run()."""
    fake = MagicMock()

    class _Timeout(Exception):
        pass

    class _HTTPStatusError(Exception):
        def __init__(self, resp):
            self.response = resp

    fake.TimeoutException = _Timeout
    fake.HTTPStatusError = _HTTPStatusError

    client = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = client
    ctx.__exit__.return_value = False
    fake.Client.return_value = ctx
    if raise_exc is not None:
        client.post.side_effect = raise_exc
    else:
        client.post.return_value = response
    return fake, client


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
        assert worker._api_url == "https://api.example.com/chat/completions"

    def test_url_without_chat_completions(self):
        worker = PolishWorker(
            api_url="https://api.example.com/v1",
            api_key="key",
            model_name="model",
            text="text"
        )
        assert worker._api_url == "https://api.example.com/v1"


class TestTextPolisherSignals:
    def test_signals_defined(self):
        polisher = TextPolisher()
        assert hasattr(polisher, "polish_complete")
        assert hasattr(polisher, "polish_error")


def _make_response(payload, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = payload
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = RuntimeError("HTTP 500")
    return resp


class TestPolishWorkerRun:
    def _run_worker(self, worker, fake_httpx):
        results, errors = [], []
        worker.result_ready.connect(results.append)
        worker.error.connect(errors.append)
        with patch.dict(sys.modules, {"httpx": fake_httpx}):
            worker.run()
        return results, errors

    def test_run_success_emits_polished_text(self):
        payload = {"choices": [{"message": {"content": " 润色后的文本 "}}]}
        fake, client = _fake_httpx_module(_make_response(payload))
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "原始文本")
        results, errors = self._run_worker(worker, fake)
        assert results == ["润色后的文本"]
        assert errors == []
        # URL gets /chat/completions appended
        assert client.post.call_args[0][0].endswith("/chat/completions")

    def test_run_allows_local_http_endpoint(self):
        payload = {"choices": [{"message": {"content": "本地润色"}}]}
        fake, _ = _fake_httpx_module(_make_response(payload))
        worker = PolishWorker("http://localhost:11434/v1", "", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == ["本地润色"]
        assert errors == []

    def test_run_rejects_remote_http(self):
        fake, client = _fake_httpx_module(_make_response({}))
        worker = PolishWorker("http://api.example.com/v1", "k", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == []
        assert errors == [INSECURE_URL_ERROR]
        client.post.assert_not_called()

    def test_run_cancelled_before_start_does_nothing(self):
        fake, client = _fake_httpx_module(_make_response({}))
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "文本")
        worker.cancel()
        results, errors = self._run_worker(worker, fake)
        assert results == [] and errors == []
        client.post.assert_not_called()

    def test_run_timeout_emits_friendly_error(self):
        fake, client = _fake_httpx_module()
        client.post.side_effect = fake.TimeoutException()
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == []
        assert errors and "超时" in errors[0]

    def test_run_empty_choices_emits_error(self):
        fake, _ = _fake_httpx_module(_make_response({"choices": []}))
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == []
        assert errors and "响应格式异常" in errors[0]

    def test_run_empty_content_emits_error(self):
        payload = {"choices": [{"message": {"content": "   "}}]}
        fake, _ = _fake_httpx_module(_make_response(payload))
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == []
        assert errors and "空内容" in errors[0]

    def test_run_generic_exception_emits_error(self):
        fake, client = _fake_httpx_module()
        client.post.side_effect = ValueError("boom")
        worker = PolishWorker("https://api.example.com/v1", "k", "m", "文本")
        results, errors = self._run_worker(worker, fake)
        assert results == []
        assert errors and "润色失败" in errors[0]


class TestTestConnectionRun:
    def test_local_http_accepted(self):
        fake, client = _fake_httpx_module(_make_response({}))
        with patch.dict(sys.modules, {"httpx": fake}):
            ok, msg = TextPolisher.test_connection(
                "http://localhost:11434/v1", "k", "m"
            )
        assert ok is True
        assert "成功" in msg

    def test_remote_http_rejected_without_request(self):
        fake, client = _fake_httpx_module(_make_response({}))
        with patch.dict(sys.modules, {"httpx": fake}):
            ok, msg = TextPolisher.test_connection(
                "http://api.example.com/v1", "k", "m"
            )
        assert ok is False
        client.post.assert_not_called()

    def test_https_success(self):
        fake, _ = _fake_httpx_module(_make_response({}))
        with patch.dict(sys.modules, {"httpx": fake}):
            ok, msg = TextPolisher.test_connection(
                "https://api.example.com/v1", "k", "m"
            )
        assert ok is True
