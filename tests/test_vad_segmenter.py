"""Tests for README「自动持续转写」的 VAD 分段逻辑。"""

import numpy as np
import pytest

from voiceink.vad_segmenter import SpeechSegmenter, SPEECH_RMS_THRESHOLD


def _tone(duration_sec: float, amplitude: float = 0.5, rate: int = 16000) -> np.ndarray:
    n = int(rate * duration_sec)
    return np.full(n, amplitude, dtype=np.float32)


def _silence(duration_sec: float, rate: int = 16000) -> np.ndarray:
    return _tone(duration_sec, 0.0, rate)


class TestSpeechSegmenterBasics:
    def test_silence_only_returns_none(self):
        seg = SpeechSegmenter(speech_threshold=0.002)
        assert seg.feed(_silence(0.5)) is None

    def test_speech_then_silence_emits_segment(self):
        seg = SpeechSegmenter(
            speech_threshold=0.002,
            silence_hold_sec=0.2,
            min_speech_sec=0.1,
        )
        assert seg.feed(_tone(0.3)) is None
        out = seg.feed(_silence(0.3))
        assert out is not None
        assert out.size >= int(16000 * 0.1)

    def test_too_short_speech_discarded(self):
        seg = SpeechSegmenter(
            speech_threshold=0.002,
            silence_hold_sec=0.1,
            min_speech_sec=0.5,
        )
        seg.feed(_tone(0.1))
        assert seg.feed(_silence(0.2)) is None

    def test_max_length_forces_cut(self):
        seg = SpeechSegmenter(
            speech_threshold=0.002,
            max_speech_sec=0.3,
            min_speech_sec=0.1,
        )
        out = seg.feed(_tone(0.35))
        assert out is not None
        assert out.size <= int(16000 * 0.35) + 100

    def test_reset_clears_state(self):
        seg = SpeechSegmenter()
        seg.feed(_tone(0.2))
        seg.reset()
        assert seg.feed(_silence(0.5)) is None

    def test_flush_emits_incomplete_speech(self):
        seg = SpeechSegmenter(
            speech_threshold=0.002,
            silence_hold_sec=0.85,
            min_speech_sec=0.1,
        )
        seg.feed(_tone(0.3))
        out = seg.flush()
        assert out is not None
        assert out.size >= int(16000 * 0.1)

    def test_flush_discards_too_short_speech(self):
        seg = SpeechSegmenter(
            speech_threshold=0.002,
            min_speech_sec=0.5,
        )
        seg.feed(_tone(0.1))
        assert seg.flush() is None

    def test_lower_threshold_for_system_audio(self):
        """System loopback is quieter; recorder uses 0.0006 threshold."""
        seg = SpeechSegmenter(speech_threshold=0.0006)
        quiet = np.full(1600, 0.001, dtype=np.float32)
        assert seg.feed(quiet) is None
        louder = np.full(1600, 0.0015, dtype=np.float32)
        assert seg.feed(louder) is None  # still accumulating, not finished
