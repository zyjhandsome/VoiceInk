"""Simple RMS-based speech segmentation for continuous listening mode."""

from __future__ import annotations

import numpy as np

from voiceink.audio_utils import TARGET_SAMPLE_RATE, rms_volume
from voiceink.speaker_session import dominant_route

SPEECH_RMS_THRESHOLD = 0.002
SILENCE_HOLD_SEC = 0.85
MIN_SPEECH_SEC = 0.25
# Stay inside the Fun-ASR-Nano / Qwen3-ASR context window so a long
# monologue emits a slice while the user is still talking.
MAX_SPEECH_SEC = 15.0


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
        self._energy: list[tuple[int, float, float]] = []
        self._total_samples = 0
        self._silence_run = 0
        self._in_speech = False
        self._last_route = ""

    @property
    def last_route(self) -> str:
        """mic, system, or empty for the segment most recently emitted."""
        return self._last_route

    def feed(
        self,
        mono_block: np.ndarray,
        *,
        mic_energy: float = 0.0,
        system_energy: float = 0.0,
    ) -> np.ndarray | None:
        block = np.asarray(mono_block, dtype=np.float32).reshape(-1)
        if block.size == 0:
            return None

        loud = rms_volume(block) >= self._speech_threshold
        if loud:
            self._in_speech = True
            self._silence_run = 0
            self._remember_block(block, mic_energy, system_energy)
            if self._total_samples >= self._max_samples:
                return self._take_segment(limit=self._max_samples)
            return None

        if not self._in_speech:
            return None

        self._remember_block(block, mic_energy, system_energy)
        self._silence_run += block.size
        if self._total_samples >= self._max_samples:
            return self._take_segment(limit=self._max_samples)
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
        mic, system, _tail = self._split_energy(out.size)
        self.reset()
        self._last_route = dominant_route(mic, system)
        return out

    def _remember_block(self, block: np.ndarray, mic_energy: float, system_energy: float) -> None:
        self._buffer.append(block)
        self._energy.append((int(block.size), float(mic_energy), float(system_energy)))
        self._total_samples += int(block.size)

    def _split_energy(self, sample_count: int) -> tuple[float, float, list[tuple[int, float, float]]]:
        mic = 0.0
        system = 0.0
        remaining = int(sample_count)
        tail: list[tuple[int, float, float]] = []
        for count, mic_part, system_part in self._energy:
            count = int(count)
            if count <= 0:
                continue
            if remaining <= 0:
                tail.append((count, mic_part, system_part))
                continue
            if count <= remaining:
                mic += mic_part
                system += system_part
                remaining -= count
                continue
            fraction = remaining / count
            mic += mic_part * fraction
            system += system_part * fraction
            tail.append((count - remaining, mic_part * (1.0 - fraction), system_part * (1.0 - fraction)))
            remaining = 0
        return mic, system, tail

    def _take_segment(self, limit: int | None = None) -> np.ndarray | None:
        if self._total_samples < self._min_samples:
            self.reset()
            return None
        if not self._buffer:
            self.reset()
            return None
        audio = np.concatenate(self._buffer).astype(np.float32, copy=False)
        take = audio.size if limit is None else min(int(limit), int(audio.size))
        mic, system, tail_energy = self._split_energy(take)
        tail = audio[take:] if take < audio.size else None
        self.reset()
        self._last_route = dominant_route(mic, system)
        if tail is not None and tail.size:
            self._in_speech = True
            self._buffer = [tail]
            self._total_samples = int(tail.size)
            self._energy = tail_energy
        return audio[:take]
