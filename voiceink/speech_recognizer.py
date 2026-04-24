import logging
import re
import shutil
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread

log = logging.getLogger("VoiceInk")

SAMPLE_RATE = 16000

# Qwen3-ASR (sherpa-onnx) may emit XML-style delimiters in decoded text.
_ASR_TEXT_TAG_RE = re.compile(r"</?asr_text\s*>", re.IGNORECASE)


def normalize_asr_output(text: str) -> str:
    """Remove ASR model wrapper tags (e.g. <asr_text>...</asr_text>) from recognition text."""
    if not text:
        return text
    cleaned = _ASR_TEXT_TAG_RE.sub("", text)
    return cleaned.strip()

HF_URL = "https://huggingface.co"

# ── Model Registry ────────────────────────────────────────────────

MODEL_REGISTRY = [
    {
        "id": "sensevoice",
        "name": "SenseVoice",
        "description": "极速推理，多语种支持",
        "accuracy": 3,
        "speed": 5,
        "languages": "中/英/日/韩/粤",
        "size_mb": 230,
        "loader": "sense_voice",
        "hf_repo": "csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "dir_name": "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
        "files": ["model.int8.onnx", "tokens.txt"],
    },
    {
        "id": "paraformer-zh",
        "name": "Paraformer 中文",
        "description": "高精度中英文识别",
        "accuracy": 4,
        "speed": 4,
        "languages": "中/英",
        "size_mb": 240,
        "loader": "paraformer",
        "hf_repo": "csukuangfj/sherpa-onnx-paraformer-zh-2024-03-09",
        "dir_name": "sherpa-onnx-paraformer-zh-2024-03-09",
        "files": ["model.int8.onnx", "tokens.txt"],
    },
    {
        "id": "fireredasr2-ctc",
        "name": "FireRedASR2",
        "description": "中文准确率最高，含方言",
        "accuracy": 5,
        "speed": 3,
        "languages": "中/英/方言",
        "size_mb": 740,
        "loader": "fire_red_asr_ctc",
        "hf_repo": "csukuangfj2/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25",
        "dir_name": "sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25",
        "files": ["model.int8.onnx", "tokens.txt"],
    },
    {
        "id": "paraformer-trilingual",
        "name": "Paraformer 三语",
        "description": "中英粤三语支持",
        "accuracy": 4,
        "speed": 4,
        "languages": "中/英/粤",
        "size_mb": 240,
        "loader": "paraformer",
        "hf_repo": "csukuangfj/sherpa-onnx-paraformer-trilingual-zh-cantonese-en",
        "dir_name": "sherpa-onnx-paraformer-trilingual-zh-cantonese-en",
        "files": ["model.int8.onnx", "tokens.txt"],
    },
    {
        "id": "fireredasr2-aed",
        "name": "FireRedASR2 AED",
        "description": "最高准确率，含方言（较慢）",
        "accuracy": 5,
        "speed": 2,
        "languages": "中/英/方言",
        "size_mb": 1234,
        "loader": "fire_red_asr",
        "hf_repo": "csukuangfj2/sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26",
        "dir_name": "sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26",
        "files": ["encoder.int8.onnx", "decoder.int8.onnx", "tokens.txt"],
    },
    {
        "id": "zipformer-ctc-zh",
        "name": "Zipformer CTC",
        "description": "轻量快速，纯中文识别",
        "accuracy": 3,
        "speed": 5,
        "languages": "中",
        "size_mb": 367,
        "loader": "zipformer_ctc",
        "hf_repo": "csukuangfj/sherpa-onnx-zipformer-ctc-zh-int8-2025-07-03",
        "dir_name": "sherpa-onnx-zipformer-ctc-zh-int8-2025-07-03",
        "files": ["model.int8.onnx", "tokens.txt"],
    },
    {
        "id": "qwen3-asr-0.6b",
        "name": "Qwen3-ASR 0.6B",
        "description": "阿里最新大模型ASR，高精度",
        "accuracy": 5,
        "speed": 2,
        "languages": "中/英",
        "size_mb": 983,
        "loader": "qwen3_asr",
        "hf_repo": "csukuangfj2/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25",
        "dir_name": "sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25",
        "files": [
            "conv_frontend.onnx",
            "encoder.int8.onnx",
            "decoder.int8.onnx",
            "tokenizer/vocab.json",
            "tokenizer/merges.txt",
            "tokenizer/tokenizer_config.json",
        ],
    },
]


def get_model_info(model_id: str) -> dict | None:
    for m in MODEL_REGISTRY:
        if m["id"] == model_id:
            return m
    return None


_custom_models_dir: Path | None = None


def set_models_dir(path: Path | None):
    global _custom_models_dir
    _custom_models_dir = path
    if path:
        path.mkdir(parents=True, exist_ok=True)


def _get_models_dir() -> Path:
    """Return models directory. Packaged exe uses install dir, dev uses user dir."""
    import sys

    if _custom_models_dir:
        return _custom_models_dir

    # Packaged exe: try install directory first
    if hasattr(sys, '_MEIPASS'):
        install_models = Path(sys._MEIPASS).parent / "models"
        if install_models.exists():
            return install_models
        # Install dir not writable? Fall back to user dir
        try:
            install_models.mkdir(parents=True, exist_ok=True)
            return install_models
        except OSError:
            pass  # Permission denied, use user dir

    # Development or fallback: user directory
    return Path.home() / ".voiceink" / "models"


def _get_portable_model_dir(model_id: str) -> Path | None:
    """Look for models in portable locations: next to exe or project root."""
    import sys
    info = get_model_info(model_id)
    if not info:
        return None

    candidates = []
    if hasattr(sys, '_MEIPASS'):
        candidates.append(Path(sys._MEIPASS).parent / "models" / info["dir_name"])
    candidates.append(Path(__file__).parent.parent / "models" / info["dir_name"])

    for d in candidates:
        if d.exists() and all((d / f).exists() for f in info["files"]):
            return d
    return None


def get_model_dir(model_id: str) -> Path:
    portable = _get_portable_model_dir(model_id)
    if portable:
        return portable
    info = get_model_info(model_id)
    if not info:
        raise ValueError(f"未知模型: {model_id}")
    return _get_models_dir() / info["dir_name"]


def is_model_downloaded(model_id: str) -> bool:
    if _get_portable_model_dir(model_id):
        return True
    info = get_model_info(model_id)
    if not info:
        return False
    d = _get_models_dir() / info["dir_name"]
    return all((d / f).exists() for f in info["files"])


def get_downloaded_models() -> list[str]:
    return [m["id"] for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]


def delete_model(model_id: str) -> bool:
    if _get_portable_model_dir(model_id):
        return False
    info = get_model_info(model_id)
    if not info:
        return False
    d = _get_models_dir() / info["dir_name"]
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


# ── Workers ───────────────────────────────────────────────────────

class ModelDownloadWorker(QThread):
    """Downloads model files from HuggingFace."""
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)  # model_id
    error = pyqtSignal(str)

    def __init__(self, model_id: str):
        super().__init__()
        self._model_id = model_id
        self._cancelled = False

    def cancel(self):
        """Set cancellation flag to stop download."""
        self._cancelled = True

    def run(self):
        try:
            import httpx

            info = get_model_info(self._model_id)
            if not info:
                self.error.emit(f"未知模型: {self._model_id}")
                return

            model_dir = _get_models_dir() / info["dir_name"]
            model_dir.mkdir(parents=True, exist_ok=True)
            hf_url = f"{HF_URL}/{info['hf_repo']}/resolve/main/"

            files = info["files"]
            total_files = len(files)

            last_emit_pct = -1

            for i, filename in enumerate(files):
                if self._cancelled:
                    log.info("模型下载已取消")
                    self.error.emit("下载已取消")
                    return

                target = model_dir / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    current_pct = int((i + 1) / total_files * 100)
                    if current_pct > last_emit_pct:
                        last_emit_pct = current_pct
                        self.progress.emit(current_pct)
                    continue

                url = hf_url + filename
                log.info("下载: %s", url)

                tmp_path = target.with_suffix(".tmp")
                try:
                    # 缩短超时时间，添加取消检查
                    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as resp:
                        resp.raise_for_status()
                        total = int(resp.headers.get("content-length", 0))
                        downloaded = 0

                        with open(tmp_path, "wb") as f:
                            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                                if self._cancelled:
                                    resp.close()
                                    tmp_path.unlink()
                                    log.info("模型下载已取消")
                                    self.error.emit("下载已取消")
                                    return
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    file_pct = downloaded / total
                                    overall_pct = int((i + file_pct) / total_files * 100)
                                    if overall_pct > last_emit_pct:
                                        last_emit_pct = overall_pct
                                        self.progress.emit(overall_pct)

                    tmp_path.rename(target)
                except Exception:
                    if tmp_path.exists():
                        tmp_path.unlink()
                    raise

            if self._cancelled:
                return

            if is_model_downloaded(self._model_id):
                log.info("模型下载完成: %s", info["name"])
                self.finished_ok.emit(self._model_id)
            else:
                self.error.emit("模型文件不完整，请重试")

        except Exception as e:
            log.error("模型下载失败: %s", e)
            self.error.emit(f"下载失败: {e}")


def _create_recognizer(model_id: str, num_threads: int):
    """Create a sherpa_onnx.OfflineRecognizer for the given model."""
    import sherpa_onnx

    info = get_model_info(model_id)
    if not info:
        raise ValueError(f"未知模型: {model_id}")

    model_dir = get_model_dir(model_id)
    loader = info["loader"]

    if loader == "sense_voice":
        return sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model_dir / "model.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=num_threads,
            use_itn=True,
            debug=False,
        )
    elif loader == "paraformer":
        return sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=str(model_dir / "model.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=num_threads,
            debug=False,
        )
    elif loader == "fire_red_asr_ctc":
        return sherpa_onnx.OfflineRecognizer.from_fire_red_asr_ctc(
            model=str(model_dir / "model.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=num_threads,
            debug=False,
        )
    elif loader == "fire_red_asr":
        return sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
            encoder=str(model_dir / "encoder.int8.onnx"),
            decoder=str(model_dir / "decoder.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=num_threads,
            debug=False,
        )
    elif loader == "zipformer_ctc":
        return sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
            model=str(model_dir / "model.int8.onnx"),
            tokens=str(model_dir / "tokens.txt"),
            num_threads=num_threads,
            debug=False,
        )
    elif loader == "qwen3_asr":
        # Workaround: sherpa-onnx 1.12.35 from_qwen3_asr() passes unsupported
        # 'hotwords' kwarg to C++ OfflineQwen3ASRModelConfig, causing a crash.
        # Build the config objects manually to bypass the bug.
        from sherpa_onnx import (
            OfflineQwen3ASRModelConfig,
            OfflineModelConfig,
            OfflineRecognizerConfig,
            FeatureExtractorConfig,
        )

        qwen3_cfg = OfflineQwen3ASRModelConfig(
            conv_frontend=str(model_dir / "conv_frontend.onnx"),
            encoder=str(model_dir / "encoder.int8.onnx"),
            decoder=str(model_dir / "decoder.int8.onnx"),
            tokenizer=str(model_dir / "tokenizer"),
        )
        model_cfg = OfflineModelConfig(
            qwen3_asr=qwen3_cfg,
            num_threads=num_threads,
            debug=False,
            provider="cpu",
        )
        feat_cfg = FeatureExtractorConfig(sampling_rate=16000, feature_dim=128)
        rec_cfg = OfflineRecognizerConfig(
            feat_config=feat_cfg,
            model_config=model_cfg,
            decoding_method="greedy_search",
        )
        rec = sherpa_onnx.OfflineRecognizer.__new__(sherpa_onnx.OfflineRecognizer)
        rec.recognizer = sherpa_onnx.lib._sherpa_onnx.OfflineRecognizer(rec_cfg)
        rec.config = rec_cfg
        return rec
    else:
        raise ValueError(f"不支持的 loader: {loader}")


class ModelLoadWorker(QThread):
    """Loads an ASR model in a background thread."""
    loaded = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, model_id: str, num_threads: int = 4):
        super().__init__()
        self._model_id = model_id
        self._num_threads = num_threads

    def run(self):
        try:
            info = get_model_info(self._model_id)
            name = info["name"] if info else self._model_id
            log.info("正在加载语音识别模型 (%s)...", name)
            recognizer = _create_recognizer(self._model_id, self._num_threads)
            log.info("语音识别模型加载完成: %s", name)
            self.loaded.emit(recognizer)
        except Exception as e:
            log.error("模型加载失败: %s", e)
            self.error.emit(f"模型加载失败: {e}")


class TranscribeWorker(QThread):
    """Runs transcription in a background thread."""
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, recognizer, audio_data: np.ndarray):
        super().__init__()
        self._recognizer = recognizer
        self._audio_data = audio_data
        self._cancelled = False

    def cancel(self):
        """Set cancellation flag."""
        self._cancelled = True

    def run(self):
        if self._cancelled:
            return

        try:
            audio = self._audio_data.astype(np.float32)
            if audio.ndim > 1:
                audio = audio[:, 0]

            # 验证音频数据有效性
            if audio.size == 0 or np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
                self.error.emit("音频数据无效")
                return

            log.info("开始识别 (%.1f 秒音频)...", len(audio) / SAMPLE_RATE)

            stream = self._recognizer.create_stream()
            stream.accept_waveform(SAMPLE_RATE, audio)
            self._recognizer.decode_stream(stream)

            if self._cancelled:
                return

            text = normalize_asr_output(stream.result.text)
            log.debug("识别结果长度: %d 字符", len(text))
            self.result_ready.emit(text)

        except Exception as e:
            log.error("识别失败: %s", e)
            self.error.emit(f"识别失败: {e}")


# ── Main Recognizer ──────────────────────────────────────────────

class SpeechRecognizer(QObject):
    """Offline speech recognizer supporting multiple sherpa-onnx models."""
    final_result = pyqtSignal(str)
    error = pyqtSignal(str)
    ready = pyqtSignal()
    model_load_progress = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recognizer = None
        self._current_worker = None
        self._load_worker = None
        self._is_ready = False
        self._model_id = ""
        self._num_threads = 4

    def configure(self, model_id: str, num_threads: int = 4):
        self._num_threads = num_threads
        self._model_id = model_id

        if not model_id:
            log.warning("未选择语音模型")
            return

        if is_model_downloaded(model_id):
            self._load_model()
        else:
            log.warning("语音模型 %s 未下载", model_id)

    def _load_model(self):
        if self._load_worker and self._load_worker.isRunning():
            return

        self._is_ready = False
        self.model_load_progress.emit("正在加载模型...")
        worker = ModelLoadWorker(self._model_id, self._num_threads)
        worker.loaded.connect(self._on_model_loaded)
        worker.error.connect(self._on_model_load_error)
        self._load_worker = worker
        worker.start()

    def _on_model_loaded(self, recognizer):
        self._recognizer = recognizer
        self._is_ready = True
        self.model_load_progress.emit("模型已就绪")
        self.ready.emit()

    def _on_model_load_error(self, msg: str):
        self._is_ready = False
        self.model_load_progress.emit(msg)
        self.error.emit(msg)

    def transcribe_final(self, full_audio: np.ndarray):
        if not self._is_ready or self._recognizer is None:
            self.error.emit("语音模型未就绪，请等待模型加载完成")
            return

        # 正确处理正在运行的 Worker，避免线程泄漏
        if self._current_worker and self._current_worker.isRunning():
            log.warning("上一次转写仍在进行中，取消旧任务...")
            self._current_worker.cancel()
            self._current_worker.wait(1000)  # 等待最多1秒
            if self._current_worker.isRunning():
                log.warning("Worker 未响应取消，强制终止")
                self._current_worker.terminate()
                self._current_worker.wait()
            # 断开信号连接
            try:
                self._current_worker.disconnect()
            except TypeError:
                pass
            self._current_worker = None

        worker = TranscribeWorker(self._recognizer, full_audio)
        worker.result_ready.connect(self._on_final_result)
        worker.error.connect(lambda e: self.error.emit(e))
        self._current_worker = worker
        worker.start()

    def _on_final_result(self, text: str):
        self.final_result.emit(text)

    def shutdown(self):
        """Stop all running workers for clean app exit."""
        if self._load_worker and self._load_worker.isRunning():
            try:
                self._load_worker.disconnect()
            except TypeError:
                pass
            self._load_worker.wait(1000)

        if self._current_worker and self._current_worker.isRunning():
            self._current_worker.cancel()
            try:
                self._current_worker.disconnect()
            except TypeError:
                pass
            self._current_worker.wait(1000)

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def current_model_id(self) -> str:
        return self._model_id
