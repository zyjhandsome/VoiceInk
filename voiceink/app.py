import logging
import sys
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from voiceink.config import Config, format_hotkey
from voiceink.hotkey_manager import HotKeyManager
from voiceink.audio_recorder import AudioRecorder
from voiceink.speech_recognizer import SpeechRecognizer, set_models_dir
from voiceink.text_polisher import TextPolisher
from voiceink.text_paster import TextPaster
from voiceink.sound_manager import SoundManager
from voiceink.ui.floating_window import FloatingWindow
from voiceink.ui.tray_icon import TrayIcon
from voiceink.ui.settings_window import SettingsWindow

log = logging.getLogger("VoiceInk")

MIN_AUDIO_SAMPLES = 1600  # 0.1s at 16kHz — ignore recordings shorter than this


class App(QObject):
    """Central orchestrator that connects all modules."""

    def __init__(self):
        super().__init__()

        self._config = Config()
        self._current_transcription = ""
        self._is_transcribing = False

        log.info("正在初始化各模块...")
        set_models_dir(self._config.models_dir)
        self._init_modules()
        log.info("正在初始化界面...")
        self._init_ui()
        self._connect_signals()
        self._configure_stt()
        self._update_tray_models()

    def _init_modules(self):
        self._hotkey_mgr = HotKeyManager(
            self._config.get("hotkey", "ctrl+space")
        )
        self._recorder = AudioRecorder()
        self._recognizer = SpeechRecognizer()
        self._polisher = TextPolisher()
        self._paster = TextPaster()
        self._sound = SoundManager(
            enabled=self._config.get("sound_enabled", True)
        )

    def _init_ui(self):
        self._floating = FloatingWindow()
        self._tray = TrayIcon()
        self._settings_win = None

        self._tray.set_auto_start(self._config.get("auto_start", False))
        self._tray.show()

    def _connect_signals(self):
        self._hotkey_mgr.recording_start.connect(self._on_recording_start)
        self._hotkey_mgr.recording_stop.connect(self._on_recording_stop)
        self._hotkey_mgr.recording_cancel.connect(self._on_recording_cancel)

        self._recorder.volume_changed.connect(self._floating.update_volume)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._recorder.error.connect(self._on_recorder_error)

        self._recognizer.final_result.connect(self._on_final_result)
        self._recognizer.error.connect(self._on_recognizer_error)
        self._recognizer.ready.connect(self._on_stt_ready)

        self._polisher.polish_complete.connect(self._on_polish_complete)
        self._polisher.polish_error.connect(self._on_polish_error)

        self._tray.open_settings.connect(self._show_settings)
        self._tray.quit_app.connect(self._quit)
        self._tray.auto_start_toggled.connect(self._on_auto_start_toggled)
        self._tray.model_switched.connect(self._on_tray_model_switch)

    def _configure_stt(self):
        from voiceink.speech_recognizer import is_model_downloaded
        model_id = self._config.get("stt.model_id", "sensevoice")
        num_threads = self._config.get("stt.num_threads", 4)

        if model_id and is_model_downloaded(model_id):
            self._recognizer.configure(model_id, num_threads)
        else:
            log.warning("语音模型未下载，请在设置中下载模型")
            self._tray.showMessage(
                "VoiceInk",
                "语音模型未下载，请右键托盘图标 → 打开设置 → 下载模型",
                QSystemTrayIcon.MessageIcon.Warning,
                5000
            )

    # ── Recording flow ────────────────────────────────

    def _on_recording_start(self):
        if not self._recognizer.is_ready:
            self._floating.show_error("语音模型未就绪，请在设置中下载模型")
            return

        if self._is_transcribing:
            log.warning("正在转写中，忽略新的录音请求")
            return

        log.info("开始录音...")
        self._current_transcription = ""
        self._sound.play_start()
        self._tray.set_recording(True)
        self._floating.show_recording()
        self._recorder.start()

    def _on_recording_stop(self):
        if not self._recorder.is_recording:
            return

        log.info("停止录音，开始识别...")
        self._sound.play_stop()
        self._tray.set_recording(False)
        self._recorder.stop()

    def _on_recording_cancel(self):
        self._tray.set_recording(False)
        self._recorder.cancel()
        self._floating.show_cancelled()

    def _on_recorder_error(self, error_msg: str):
        self._tray.set_recording(False)
        self._sound.play_error()
        self._floating.show_error(error_msg)

    # ── Recognition ───────────────────────────────────

    def _on_recording_finished(self, full_audio: np.ndarray):
        if full_audio.size < MIN_AUDIO_SAMPLES:
            log.warning("录音过短 (%d 采样点)，忽略", full_audio.size)
            self._floating.show_error("录音过短，请按住快捷键说话")
            return

        self._is_transcribing = True
        self._floating.show_recognizing()
        self._recognizer.transcribe_final(full_audio)

    def _on_final_result(self, text: str):
        if not text.strip():
            log.warning("未识别到语音内容")
            self._is_transcribing = False
            self._floating.show_error("未识别到语音内容")
            return

        log.info("识别结果: %s", text[:80])
        self._current_transcription = text

        llm_enabled = self._config.get("llm.enabled", False)
        api_url = self._config.get("llm.api_url", "")
        api_key = self._config.get("llm.api_key", "")
        model_name = self._config.get("llm.model_name", "")
        prompt = self._config.get("llm.prompt", "")

        if llm_enabled and api_url and api_key and model_name:
            self._floating.show_polishing(text)
            self._polisher.polish(text, api_url, api_key, model_name, prompt)
        else:
            self._output_text(text)

    def _on_recognizer_error(self, error_msg: str):
        self._is_transcribing = False
        self._sound.play_error()
        self._floating.show_error(error_msg)

    def _on_stt_ready(self):
        hotkey = format_hotkey(self._config.get("hotkey", "ctrl+space"))
        log.info("✓ 语音识别模型已就绪，按 %s 开始语音输入", hotkey)
        self._tray.showMessage(
            "VoiceInk",
            f"已就绪，按 {hotkey} 开始语音输入",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    # ── Polishing ─────────────────────────────────────

    def _on_polish_complete(self, polished_text: str):
        self._output_text(polished_text)

    def _on_polish_error(self, error_msg: str):
        log.warning("润色失败，输出原文: %s", error_msg)
        self._floating.show_error("润色失败，已输出原文")
        QTimer.singleShot(500, lambda: self._output_text(self._current_transcription))

    # ── Output ────────────────────────────────────────

    def _output_text(self, text: str):
        self._is_transcribing = False
        result = self._paster.paste(text)

        if result == "pasted":
            log.info("✓ 已粘贴到光标位置")
            self._floating.show_success("已输入")
        elif result == "clipboard":
            log.info("✓ 已复制到剪贴板")
            self._floating.show_success("已复制到剪贴板")
        else:
            error_msg = result.replace("error:", "")
            log.error("输出失败: %s", error_msg)
            self._floating.show_error(f"输出失败: {error_msg}")

    # ── Settings ──────────────────────────────────────

    def _show_settings(self):
        self._hotkey_mgr.pause()

        if self._settings_win is None:
            self._settings_win = SettingsWindow(self._config)
            self._settings_win.hotkey_updated.connect(self._on_hotkey_updated)
            self._settings_win.settings_changed.connect(self._on_settings_changed)
            self._settings_win.finished.connect(self._on_settings_closed)

        self._settings_win._load_settings()
        self._settings_win.show()
        self._settings_win.raise_()
        self._settings_win.activateWindow()

    def _on_settings_closed(self):
        self._hotkey_mgr.resume()
        self._update_tray_models()

    def _on_hotkey_updated(self, new_hotkey: str):
        self._hotkey_mgr.update_hotkey(new_hotkey)

    def _on_settings_changed(self):
        self._sound.enabled = self._config.get("sound_enabled", True)
        self._tray.set_auto_start(self._config.get("auto_start", False))
        set_models_dir(self._config.models_dir)
        self._configure_stt()
        self._update_tray_models()

    def _on_tray_model_switch(self, model_id: str):
        current = self._config.get("stt.model_id", "")
        if model_id == current:
            return
        self._config.set("stt.model_id", model_id)
        self._configure_stt()
        self._update_tray_models()

    def _update_tray_models(self):
        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded
        downloaded = [m for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]
        active = self._config.get("stt.model_id", "")
        self._tray.update_models(downloaded, active)

    def _on_auto_start_toggled(self, enabled: bool):
        self._config.set("auto_start", enabled)
        self._setup_auto_start(enabled)

    def _setup_auto_start(self, enabled: bool):
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "VoiceInk"

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    exe_path = sys.executable
                    if hasattr(sys, '_MEIPASS'):
                        exe_path = sys.argv[0]
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            log.warning("设置开机自启失败: %s", e)

    # ── Lifecycle ─────────────────────────────────────

    def _quit(self):
        log.info("VoiceInk 正在退出...")
        self._hotkey_mgr.stop()
        if self._recorder.is_recording:
            self._recorder.cancel()

        if self._settings_win is not None:
            self._settings_win.cancel_all_downloads()
            self._settings_win.close()

        self._recognizer.shutdown()
        self._polisher.cancel()
        self._tray.hide()
        QApplication.quit()

    def start(self):
        self._hotkey_mgr.start()
