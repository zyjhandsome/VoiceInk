import logging
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import threading

log = logging.getLogger("VoiceInk")


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
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._is_recording or self._is_cancelled:
            return

        audio_data = indata[:, 0].copy()
        volume = float(np.sqrt(np.mean(audio_data ** 2)))
        self.volume_changed.emit(volume)

        with self._lock:
            self._audio_chunks.append(audio_data)

    def start(self):
        if self._is_recording:
            return

        self._is_recording = True
        self._is_cancelled = False
        with self._lock:
            self._audio_chunks = []

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="float32",
                blocksize=int(self.SAMPLE_RATE * self.CHUNK_DURATION),
                callback=self._audio_callback
            )
            stream.start()
            self._stream = stream
        except Exception as e:
            self._is_recording = False
            if stream is not None:
                try:
                    stream.close()
                except Exception as close_err:
                    log.warning("关闭音频流失败: %s", close_err)
            # 友好化错误信息
            error_msg = str(e)
            if "Permission denied" in error_msg or "access" in error_msg.lower():
                self.error.emit("无法访问麦克风，请检查系统权限设置")
            elif "No device" in error_msg or "device" in error_msg.lower():
                self.error.emit("未检测到麦克风，请确认设备已连接")
            else:
                self.error.emit(f"麦克风启动失败: {error_msg}")

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

        # 所有操作在锁内完成，避免竞争条件
        with self._lock:
            chunks = self._audio_chunks
            self._audio_chunks = []
            is_cancelled = self._is_cancelled
            self._is_cancelled = False

        # 空音频检查
        if is_cancelled or not chunks:
            return

        full_audio = np.concatenate(chunks)
        self.recording_finished.emit(full_audio)

    def cancel(self):
        self._is_cancelled = True
        self.stop()

    @property
    def is_recording(self) -> bool:
        return self._is_recording
