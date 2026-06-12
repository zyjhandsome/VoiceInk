"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from voiceink.audio_devices import AudioDeviceInfo, RecordingPlan, StreamEndpoint
from voiceink.audio_recorder import AudioRecorder
from voiceink.config import Config


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
