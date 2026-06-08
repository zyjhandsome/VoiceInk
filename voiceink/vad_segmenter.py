"""Simple RMS-based speech segmentation for continuous listening mode."""

from __future__ import annotations

import numpy as np

from voiceink.audio_utils import TARGET_SAMPLE_RATE, rms_volume

SPEECH_RMS_THRESHOLD = 0.002
SILENCE_HOLD_SEC = 0.85
MIN_SPEECH_SEC = 0.25
MAX_SPEECH_SEC = 90.0


class SpeechSegmenter:
    """Accumulates 16 kHz mono audio; returns a segment when speech ends."""

    def __init__(
        self,
        sample_rate: int = TARGET_SAMPLE_RATE,
        speech_threshold: float = SPEECH_RMS_THRESHOLD,
        silence_hold_sec: float = SILENCE_HOLD_SEC,
        min_speech_sec: float = MIN_SPEECH_SEC,
        max_speech_sec: float = MAX_SPEECH_SEC,
    ):
        self._rate = sample_rate
        self._speech_threshold = speech_threshold
        self._silence_hold_samples = int(sample_rate * silence_hold_sec)
        self._min_samples = int(sample_rate * min_speech_sec)
        self._max_samples = int(sample_rate * max_speech_sec)
        self.reset()

    @property
    def speech_threshold(self) -> float:
        return self._speech_threshold

    def reset(self) -> None:
        self._buffer: list[np.ndarray] = []
        self._total_samples = 0
        self._silence_run = 0
        self._in_speech = False

    def feed(self, mono_block: np.ndarray) -> np.ndarray | None:
        block = np.asarray(mono_block, dtype=np.float32).reshape(-1)
        if block.size == 0:
            return None

        loud = rms_volume(block) >= self._speech_threshold
        if loud:
            self._in_speech = True
            self._silence_run = 0
            self._buffer.append(block)
            self._total_samples += block.size
            if self._total_samples >= self._max_samples:
                return self._take_segment()
            return None

        if not self._in_speech:
            return None

        self._buffer.append(block)
        self._total_samples += block.size
        self._silence_run += block.size
        if self._silence_run >= self._silence_hold_samples:
            return self._take_segment()
        return None

    def flush(self) -> np.ndarray | None:
        """Emit buffered speech that has not yet reached the silence threshold."""
        if not self._in_speech or self._total_samples < self._min_samples:
            self.reset()
            return None
        if not self._buffer:
            self.reset()
            return None
        out = np.concatenate(self._buffer).astype(np.float32, copy=False)
        self.reset()
        return out

    def _take_segment(self) -> np.ndarray | None:
        if self._total_samples < self._min_samples:
            self.reset()
            return None
        if not self._buffer:
            self.reset()
            return None
        out = np.concatenate(self._buffer).astype(np.float32, copy=False)
        self.reset()
        return out
