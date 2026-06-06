import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_recording_hardware(monkeypatch):
    """Avoid opening real microphones / WASAPI loopback during unit tests."""
    from voiceink.audio_devices import (
        INPUT_SOURCE_MICROPHONE,
        AudioDeviceInfo,
        RecordingPlan,
        StreamEndpoint,
    )
    from voiceink.audio_recorder import AudioRecorder

    mic = AudioDeviceInfo(0, "Test Mic", "WASAPI", 16000, 1, False, False)
    plan = RecordingPlan(
        INPUT_SOURCE_MICROPHONE,
        [StreamEndpoint("microphone", mic, False)],
    )

    monkeypatch.setattr(
        "voiceink.audio_devices.build_recording_plan",
        lambda *args, **kwargs: plan,
    )

    def _fake_open_lane(self, lane):
        lane.sample_rate = lane.endpoint.device.sample_rate

    monkeypatch.setattr(AudioRecorder, "_open_lane_stream", _fake_open_lane)
    monkeypatch.setattr(
        AudioRecorder,
        "_open_system_lane_with_fallback",
        lambda self, primary: None,
    )
