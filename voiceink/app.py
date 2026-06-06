import logging
import sys
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox

from voiceink.config import Config, format_hotkey, TRIGGER_MODE_CONTINUOUS, TRIGGER_MODE_HOTKEY
from voiceink.hotkey_manager import HotKeyManager
from voiceink.audio_recorder import AudioRecorder
from voiceink.speech_recognizer import SpeechRecognizer, set_models_dir, normalize_asr_output
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

    # 友好化错误信息映射
    ERROR_HINTS = {
        "麦克风": "无法访问麦克风\n请检查：1) 麦克风是否已连接\n2) 是否被其他应用占用\n3) 系统隐私设置",
        "模型未就绪": "语音模型未就绪\n请右键托盘图标 → 设置 → 模型 → 下载模型",
        "模型未下载": "语音模型未下载\n请右键托盘图标 → 设置 → 模型 → 下载模型",
        "录音过短": "录音过短\n请按住快捷键说话，时长至少 0.1 秒",
        "未识别": "未识别到语音内容\n请确保音频来源与设备正确，并靠近麦克风或播放电脑声音",
        "音频设备": "无法打开音频设备\n请在设置 → 通用 → 声音收录 中刷新并选择设备",
        "系统声音": "无法采集系统声音\nWindows 可启用立体声混音或安装 PyAudioWPatch；混合模式需配置电脑声设备",
        "润色失败": "润色失败，已输出原文\n请检查 API 配置是否正确",
        "输出失败": "输出失败\n请确保目标窗口可接收文本输入",
    }

    def _friendly_error(self, original_msg: str) -> str:
        """将技术性错误信息转换为友好提示"""
        for keyword, hint in self.ERROR_HINTS.items():
            if keyword in original_msg:
                return hint
        return original_msg

    def __init__(self):
        super().__init__()

        self._config = Config()
        self._current_transcription = ""
        self._is_transcribing = False
        self._segment_queue: list[np.ndarray] = []

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
        self._apply_audio_config()
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

    def _is_continuous_mode(self) -> bool:
        return self._config.get("audio.trigger_mode", TRIGGER_MODE_CONTINUOUS) == TRIGGER_MODE_CONTINUOUS

    def _connect_signals(self):
        self._hotkey_mgr.recording_start.connect(self._on_recording_start)
        self._hotkey_mgr.recording_stop.connect(self._on_recording_stop)
        self._hotkey_mgr.recording_cancel.connect(self._on_recording_cancel)

        self._recorder.volume_changed.connect(self._floating.update_volume)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._recorder.segment_ready.connect(self._on_segment_ready)
        self._recorder.error.connect(self._on_recorder_error)
        self._recorder.warning.connect(self._on_recorder_warning)

        self._recognizer.final_result.connect(self._on_final_result)
        self._recognizer.error.connect(self._on_recognizer_error)
        self._recognizer.ready.connect(self._on_stt_ready)

        self._polisher.polish_complete.connect(self._on_polish_complete)
        self._polisher.polish_error.connect(self._on_polish_error)

        self._tray.open_settings.connect(self._show_settings)
        self._tray.quit_app.connect(self._quit)
        self._tray.auto_start_toggled.connect(self._on_auto_start_toggled)
        self._tray.model_switched.connect(self._on_tray_model_switch)

    def _apply_audio_config(self):
        from voiceink.audio_devices import (
            INPUT_SOURCES,
            build_recording_plan,
            plan_includes_system_capture,
            sanitize_system_device_index,
        )

        source = self._config.get("audio.input_source", "microphone")
        if source not in INPUT_SOURCES:
            source = "microphone"
            self._config.set("audio.input_source", source)
        sys_idx = sanitize_system_device_index(
            int(self._config.get("audio.system_device_index", -1))
        )
        if sys_idx != int(self._config.get("audio.system_device_index", -1)):
            self._config.set("audio.system_device_index", sys_idx)
        self._recorder.configure(
            input_source=source,
            mic_device_index=int(self._config.get("audio.mic_device_index", -1)),
            system_device_index=sys_idx,
        )
        try:
            plan = build_recording_plan(
                source,
                int(self._config.get("audio.mic_device_index", -1)),
                sys_idx,
            )
            needs_system = source in ("system", "mixed")
            if needs_system and not plan_includes_system_capture(plan):
                log.warning(
                    "当前来源需要电脑播放声道但未配置成功；看视频/开会远端可能无法转写。"
                )
        except RuntimeError as e:
            log.warning("音频计划不可用: %s", e)

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
        if self._is_continuous_mode():
            log.info("已按下快捷键，但当前为「自动持续转写」模式，按住录音不会启动")
            self._tray.showMessage(
                "VoiceInk",
                "当前是「自动持续转写」，Ctrl+Space 不会开始录音。\n"
                "请在本页选「按住快捷键」后点右下角「保存设置」，或改按 Alt+Space 试输入法冲突。",
                QSystemTrayIcon.MessageIcon.Information,
                7000,
            )
            return
        if not self._recognizer.is_ready:
            self._floating.show_error(self._friendly_error("模型未就绪"))
            return

        if self._is_transcribing:
            log.warning("正在转写中，忽略新的录音请求")
            self._floating.show_busy_transcribing()
            return

        log.info("开始录音（来源: %s）...", self._recorder.input_source_display)
        self._current_transcription = ""
        self._sound.play_start()
        self._tray.set_recording(True)
        self._tray.set_activity_tooltip("recording")
        self._floating.show_recording()
        self._recorder.start(continuous=False)

    def _on_recording_stop(self):
        if self._is_continuous_mode():
            return
        if not self._recorder.is_recording:
            self._reset_recording_ui_after_abort()
            return

        log.info("停止录音，开始识别...")
        self._sound.play_stop()
        self._tray.set_recording(False)
        self._tray.set_activity_tooltip("recognizing")
        self._recorder.stop()

    def _reset_recording_ui_after_abort(self):
        """录音未真正开始或已结束时，收回托盘/浮窗状态（防止短按后浮窗常驻）。"""
        self._tray.set_recording(False)
        self._tray.set_activity_tooltip(None)
        if not self._is_continuous_mode():
            self._floating.dismiss_if_idle()

    def _on_recording_cancel(self):
        if self._is_continuous_mode():
            return
        self._reset_recording_ui_after_abort()
        self._recorder.cancel()
        self._floating.show_cancelled()

    def _on_recorder_error(self, error_msg: str):
        if self._recorder.is_continuous:
            self._stop_continuous_listening()
        self._tray.set_recording(False)
        self._tray.set_activity_tooltip(None)
        self._sound.play_error()
        self._floating.show_error(self._friendly_error(error_msg))

    def _on_recorder_warning(self, warning_msg: str):
        log.warning("%s", warning_msg)
        self._tray.showMessage(
            "VoiceInk",
            warning_msg,
            QSystemTrayIcon.MessageIcon.Warning,
            6000,
        )

    def _start_continuous_listening(self):
        if not self._is_continuous_mode():
            return
        if not self._recognizer.is_ready:
            return
        if self._recorder.is_continuous:
            return
        log.info("开启自动持续转写（来源: %s）", self._recorder.input_source_display)
        self._tray.set_activity_tooltip("listening")
        self._floating.show_listening()

        def _begin():
            self._recorder.start_continuous()
            if (
                self._config.get("audio.input_source") == "system"
                and self._recorder.is_continuous
            ):
                self._tray.showMessage(
                    "VoiceInk",
                    "正在采集系统播放声。请确认视频/会议声音走 Windows 默认扬声器（与环回设备一致）。",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000,
                )

        QTimer.singleShot(300, _begin)

    def _stop_continuous_listening(self):
        if self._recorder.is_continuous or self._recorder.is_recording:
            self._recorder.stop_continuous()
        self._tray.set_activity_tooltip(None)
        self._floating.dismiss_if_idle()

    def _on_segment_ready(self, audio: np.ndarray):
        if audio.size < MIN_AUDIO_SAMPLES:
            return
        if self._is_transcribing:
            self._segment_queue.append(audio)
            log.debug("转写排队，队列长度 %d", len(self._segment_queue))
            return
        self._begin_transcription(audio)

    # ── Recognition ───────────────────────────────────

    def _on_recording_finished(self, full_audio: np.ndarray):
        if full_audio.size < MIN_AUDIO_SAMPLES:
            log.warning("录音过短 (%d 采样点)，忽略", full_audio.size)
            self._reset_recording_ui_after_abort()
            self._floating.show_error(self._friendly_error("录音过短"))
            return
        self._begin_transcription(full_audio)

    def _begin_transcription(self, audio: np.ndarray):
        self._is_transcribing = True
        self._tray.set_activity_tooltip("recognizing")
        self._floating.show_recognizing()
        self._recognizer.transcribe_final(audio)

    def _on_final_result(self, text: str):
        text = normalize_asr_output(text)
        if not text.strip():
            log.warning("未识别到语音内容")
            self._is_transcribing = False
            self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
            if self._is_continuous_mode():
                self._floating.show_listening()
            else:
                self._floating.show_error(self._friendly_error("未识别"))
            self._pump_segment_queue()
            return

        log.debug("识别结果长度: %d 字符", len(text))
        self._current_transcription = text

        llm_enabled = self._config.get("llm.enabled", False)
        api_url = self._config.get("llm.api_url", "")
        api_key = self._config.get("llm.api_key", "")
        model_name = self._config.get("llm.model_name", "")
        prompt = self._config.get("llm.prompt", "")

        if llm_enabled and api_url and api_key and model_name:
            self._tray.set_activity_tooltip("polishing")
            self._floating.show_polishing(text)
            self._polisher.polish(text, api_url, api_key, model_name, prompt)
        else:
            self._output_text(text)

    def _on_recognizer_error(self, error_msg: str):
        self._is_transcribing = False
        self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
        self._sound.play_error()
        self._floating.show_error(self._friendly_error(error_msg))
        self._pump_segment_queue()
        if self._is_continuous_mode() and not self._recorder.is_continuous:
            QTimer.singleShot(1500, self._start_continuous_listening)

    def _pump_segment_queue(self):
        if self._is_transcribing or not self._segment_queue:
            if self._is_continuous_mode() and not self._is_transcribing and self._recorder.is_continuous:
                self._floating.show_listening()
            return
        next_audio = self._segment_queue.pop(0)
        self._begin_transcription(next_audio)

    def _on_stt_ready(self):
        if self._is_continuous_mode():
            self._tray.showMessage(
                "VoiceInk",
                "自动持续转写已就绪（检测到说话后自动出字）",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
            QTimer.singleShot(400, self._start_continuous_listening)
            return
        hotkey = format_hotkey(self._config.get("hotkey", "ctrl+space"))
        log.info("✓ 语音识别模型已就绪，按 %s 开始语音输入", hotkey)
        self._tray.showMessage(
            "VoiceInk",
            f"已就绪，按 {hotkey} 开始语音输入",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    # ── Polishing ─────────────────────────────────────

    def _on_polish_complete(self, polished_text: str):
        self._output_text(polished_text)

    def _on_polish_error(self, error_msg: str):
        log.warning("润色失败: %s", error_msg)
        self._floating.show_error(self._friendly_error("润色失败"))
        QTimer.singleShot(500, lambda: self._output_text(self._current_transcription))

    # ── Output ────────────────────────────────────────

    def _output_text(self, text: str):
        self._is_transcribing = False
        text = normalize_asr_output(text)
        if not text.strip():
            self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
            if self._is_continuous_mode():
                self._floating.show_listening()
            else:
                self._floating.show_error(self._friendly_error("未识别"))
            self._pump_segment_queue()
            return
        result = self._paster.paste(text)
        paste_hint = "可按 Cmd+V 粘贴" if sys.platform == "darwin" else "可按 Ctrl+V 粘贴"

        if result == "pasted":
            log.info("已粘贴到光标位置")
            self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
            if self._is_continuous_mode():
                self._floating.show_success("已输入")
                QTimer.singleShot(1700, self._floating.show_listening)
            else:
                self._floating.dismiss_if_idle()
                self._floating.show_success("已输入")
        elif result == "clipboard":
            log.info("已复制到剪贴板")
            self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
            if self._is_continuous_mode():
                self._floating.show_success("已复制", paste_hint)
                QTimer.singleShot(2200, self._floating.show_listening)
            else:
                self._floating.dismiss_if_idle()
                self._floating.show_success("已复制到剪贴板", paste_hint)
        else:
            error_msg = result.replace("error:", "")
            log.error("输出失败: %s", error_msg)
            self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
            self._floating.show_error(self._friendly_error("输出失败"))

        QTimer.singleShot(300, self._pump_segment_queue)

    # ── Settings ──────────────────────────────────────

    def _show_settings(self):
        if self._settings_win is None:
            self._settings_win = SettingsWindow(self._config)
            self._settings_win.hotkey_updated.connect(self._on_hotkey_updated)
            self._settings_win.settings_changed.connect(self._on_settings_changed)
            self._settings_win.finished.connect(self._on_settings_closed)
            self._settings_win.hotkey_capture_started.connect(self._hotkey_mgr.pause)
            self._settings_win.hotkey_capture_ended.connect(self._hotkey_mgr.resume)

        self._settings_win._load_settings()
        self._settings_win.show()
        self._settings_win.raise_()
        self._settings_win.activateWindow()

    def _on_settings_closed(self):
        if self._settings_win is not None:
            self._settings_win._hotkey_edit.cancel_capture_if_active()
        self._hotkey_mgr.resume()
        self._update_tray_models()

    def _on_hotkey_updated(self, new_hotkey: str):
        self._hotkey_mgr.update_hotkey(new_hotkey)

    def _on_settings_changed(self):
        was_continuous = self._recorder.is_continuous
        if was_continuous:
            self._stop_continuous_listening()

        self._sound.enabled = self._config.get("sound_enabled", True)
        self._tray.set_auto_start(self._config.get("auto_start", False))
        self._apply_audio_config()
        set_models_dir(self._config.models_dir)
        self._configure_stt()
        self._update_tray_models()
        self._segment_queue.clear()

        if self._is_continuous_mode() and self._recognizer.is_ready:
            QTimer.singleShot(400, self._start_continuous_listening)

    def _on_tray_model_switch(self, model_id: str):
        current = self._config.get("stt.model_id", "")
        if model_id == current:
            return
        if self._recorder.is_continuous:
            self._stop_continuous_listening()
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
        self._stop_continuous_listening()
        self._hotkey_mgr.stop()
        if self._recorder.is_recording:
            self._recorder.cancel()

        if self._settings_win is not None:
            self._settings_win.cancel_all_downloads()
            self._settings_win.close()

        self._recognizer.shutdown()
        self._polisher.cancel()
        self._tray.hide()
        self._config.save_immediate()
        QApplication.quit()

    def start(self):
        self._hotkey_mgr.start()
        if not self._config.get("first_run_welcome_seen", True):
            QTimer.singleShot(600, self._show_first_run_welcome)

    def _show_first_run_welcome(self):
        if self._is_continuous_mode():
            mode_tip = "当前为「自动持续转写」：检测到说话后会自动识别并粘贴。"
        else:
            hk = format_hotkey(self._config.get("hotkey", "ctrl+space"))
            mode_tip = f"当前为「按住快捷键」：按住 {hk} 说话，松开后识别并粘贴。"
        text = (
            "VoiceInk 在本地完成语音识别（可选通过网络调用大模型润色）。\n\n"
            f"{mode_tip}\n\n"
            "请在设置 → 通用 中选择音频来源：\n"
            "· 仅麦克风：你的说话\n"
            "· 仅电脑播放：视频/会议远端声音\n"
            "· 混合：开会时远端 + 自己都要\n\n"
            "请先在设置 → 模型 中下载至少一个语音模型。"
        )
        QMessageBox.information(None, "欢迎使用 VoiceInk", text)
        self._config.set("first_run_welcome_seen", True)
