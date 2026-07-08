"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from voiceink.audio_devices import AudioDeviceInfo, RecordingPlan, StreamEndpoint
from voiceink.audio_recorder import AudioRecorder
from voiceink.config import Config


@pytest.fixture(scope="session", autouse=True)
def _qapp_session():
    """Keep a single QApplication alive for the whole test session.

    Prevents ``wrapped C/C++ object ... has been deleted`` flakiness when Qt
    objects (HotKeyManager, SettingsWindow, ...) are created across modules
    without a persistent application instance.
    """
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _isolate_registry_auto_start(monkeypatch):
    """Stop tests from reading the real machine's Windows ``Run`` key.

    Without this, a developer machine that has VoiceInk registered for
    auto-start would leak ``auto_start=True`` into every isolated Config,
    making toggle/signal assertions non-deterministic. We simulate an empty
    ``Run`` key so the real sync code path still runs (and stays covered).
    """
    if sys.platform == "win32":
        import winreg

        def _no_entry(*_args, **_kwargs):
            raise FileNotFoundError

        monkeypatch.setattr(winreg, "QueryValueEx", _no_entry)


@pytest.fixture
def config_home(tmp_path):
    """Isolated ~/.voiceink directory for config tests."""
    home = tmp_path / ".voiceink"
    home.mkdir(parents=True)
    return home


@pytest.fixture
def config(config_home):
    """Config instance backed by a temporary directory."""
    return Config(config_dir=config_home)


@pytest.fixture
def mock_recording_hardware(monkeypatch):
    """Avoid opening real microphones during AudioRecorder.start() tests."""
    device = AudioDeviceInfo(0, "Mock Mic", "mock", 16000, 1, False, False)
    endpoint = StreamEndpoint("microphone", device, False)
    plan = RecordingPlan(input_source="microphone", endpoints=(endpoint,))

    def fake_build_recording_plan(*_args, **_kwargs):
        return plan

    def fake_open_lane_stream(self, lane):
        lane.stream = MagicMock()
        lane.stream.close = MagicMock()
        lane.sample_rate = 16000

    monkeypatch.setattr(
        "voiceink.audio_recorder.build_recording_plan",
        fake_build_recording_plan,
    )
    monkeypatch.setattr(AudioRecorder, "_open_lane_stream", fake_open_lane_stream)
