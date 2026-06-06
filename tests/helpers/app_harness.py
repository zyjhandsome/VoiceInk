"""Shared mocks for App integration tests (README feature flows)."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import MagicMock, patch

from voiceink.config import DEFAULT_CONFIG


def _config_get(store: dict, key: str, default=None):
    keys = key.split(".")
    value = store
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value


def _config_set(store: dict, key: str, value):
    keys = key.split(".")
    node = store
    for k in keys[:-1]:
        if k not in node or not isinstance(node[k], dict):
            node[k] = {}
        node = node[k]
    node[keys[-1]] = value


@contextmanager
def app_harness(config_overrides: dict | None = None):
    """Build a real App with mocked heavy dependencies and configurable store."""
    store = deepcopy(DEFAULT_CONFIG)
    if config_overrides:
        for key, value in config_overrides.items():
            _config_set(store, key, value)

    config_mock = MagicMock()
    config_mock.get.side_effect = lambda key, default=None: _config_get(store, key, default)
    config_mock.set.side_effect = lambda key, value: _config_set(store, key, value)
    config_mock.get_all.return_value = store
    config_mock.models_dir = store.get("stt", {}).get("models_dir") or None

    patches = [
        patch("voiceink.app.Config", return_value=config_mock),
        patch("voiceink.app.HotKeyManager"),
        patch("voiceink.app.AudioRecorder"),
        patch("voiceink.app.SpeechRecognizer"),
        patch("voiceink.app.TextPolisher"),
        patch("voiceink.app.TextPaster"),
        patch("voiceink.app.SoundManager"),
        patch("voiceink.app.FloatingWindow"),
        patch("voiceink.app.TrayIcon"),
    ]
    started = [p.start() for p in patches]

    from voiceink.app import App

    app = App()
    harness = {
        "app": app,
        "config": config_mock,
        "store": store,
        "hotkey": app._hotkey_mgr,
        "recorder": app._recorder,
        "recognizer": app._recognizer,
        "polisher": app._polisher,
        "paster": app._paster,
        "sound": app._sound,
        "floating": app._floating,
        "tray": app._tray,
    }

    # Sensible defaults for README flows
    harness["recognizer"].is_ready = True
    harness["recorder"].is_recording = False
    harness["recorder"].is_continuous = False
    harness["recorder"].input_source_display = "麦克风"

    try:
        yield harness
    finally:
        for p in reversed(patches):
            p.stop()
