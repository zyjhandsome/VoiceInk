import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import threading


class AudioRecorder(QObject):
    volume_changed = pyqtSignal(float)
    audio_chunk_ready = pyqtSignal(np.ndarray)
    recording_finished = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_DURATION = 0.1  # 100ms per callback for responsive volume display

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._is_cancelled = False
        self._audio_chunks = []
        self._stream = None
        self._chunk_accumulator = []
        self._chunk_sample_count = 0
        self._streaming_interval_samples = int(self.SAMPLE_RATE * 3)  # 3 seconds for STT chunks
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._is_recording or self._is_cancelled:
            return

        audio_data = indata[:, 0].copy()

        with self._lock:
            self._audio_chunks.append(audio_data)
            self._chunk_accumulator.append(audio_data)
            self._chunk_sample_count += len(audio_data)

        volume = float(np.sqrt(np.mean(audio_data ** 2)))
        self.volume_changed.emit(volume)

        if self._chunk_sample_count >= self._streaming_interval_samples:
            with self._lock:
                chunk = np.concatenate(self._chunk_accumulator)
                self._chunk_accumulator = []
                self._chunk_sample_count = 0
            self.audio_chunk_ready.emit(chunk)

    def start(self):
        if self._is_recording:
            return

        self._is_recording = True
        self._is_cancelled = False
        self._audio_chunks = []
        self._chunk_accumulator = []
        self._chunk_sample_count = 0

        try:
            self._stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="float32",
                blocksize=int(self.SAMPLE_RATE * self.CHUNK_DURATION),
                callback=self._audio_callback
            )
            self._stream.start()
        except Exception as e:
            self._is_recording = False
            self.error.emit(f"麦克风启动失败: {str(e)}")

    def stop(self):
        if not self._is_recording:
            return

        self._is_recording = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if not self._is_cancelled and self._audio_chunks:
            with self._lock:
                full_audio = np.concatenate(self._audio_chunks)
            self.recording_finished.emit(full_audio)

        self._audio_chunks = []

    def cancel(self):
        self._is_cancelled = True
        self.stop()

    @property
    def is_recording(self) -> bool:
        return self._is_recording
