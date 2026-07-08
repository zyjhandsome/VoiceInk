import logging
import sys
import time
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox

from voiceink.config import (
    Config,
    format_hotkey,
    TRIGGER_MODE_CONTINUOUS,
    TRIGGER_MODE_HOTKEY,
)
from voiceink.hotkey_manager import HotKeyManager, MIN_HOLD_MS
from voiceink.audio_recorder import AudioRecorder
from voiceink.speech_recognizer import (
    DEFAULT_MODEL_ID,
    SpeechRecognizer,
    set_models_dir,
    normalize_asr_output,
    get_model_info,
)
from voiceink.text_polisher import TextPolisher
from voiceink.text_paster import TextPaster
from voiceink.sound_manager import SoundManager
from voiceink.ui.floating_window import FloatingWindow
from voiceink.ui.tray_icon import TrayIcon
from voiceink.ui.settings_window import SettingsWindow

log = logging.getLogger("VoiceInk")

MIN_AUDIO_SAMPLES = 1600  # 0.1s at 16kHz — ignore recordings shorter than this
SHORT_TAP_TRAY_COOLDOWN_S = 300  # 托盘「按过短」提示最少间隔，避免输入法反复弹窗


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
        self._continuous_user_stopped = False
        self._short_tap_tray_last_at = 0.0
        self._hotkey_conflict_warned = False

        log.info("正在初始化各模块...")
        set_models_dir(self._config.models_dir)
        self._init_modules()
        log.info("正在初始化界面...")
        self._init_ui()
        self._connect_signals()
        self._sync_hotkey_trigger_mode()
        self._configure_stt()
        self._update_tray_models()

    def _init_modules(self):
        self._hotkey_mgr = HotKeyManager(
            self._config.get("hotkey", "alt+space")
        )
        self._recorder = AudioRecorder()
        self._apply_audio_config()
        self._recognizer = SpeechRecognizer()
        self._polisher = TextPolisher()
        self._paster = TextPaster(
            restore_clipboard=self._config.get("output.restore_clipboard", False)
        )
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

    def _continuous_session_active(self) -> bool:
        """True while continuous listen session is running (hotkey started, not yet stopped)."""
        return self._is_continuous_mode() and self._recorder.is_continuous

    def _continuous_hotkey_label(self) -> str:
        return format_hotkey(self._config.get("hotkey", "alt+space"))

    def _refresh_continuous_ui_after_output(self) -> None:
        if self._continuous_session_active():
            self._floating.show_listening()
        elif self._is_continuous_mode() and self._recognizer.is_ready:
            self._floating.show_continuous_idle(self._continuous_hotkey_label())
        else:
            self._floating.dismiss_if_idle()

    def _sync_hotkey_trigger_mode(self) -> None:
        self._hotkey_mgr.set_continuous_trigger_mode(self._is_continuous_mode())

    def _connect_signals(self):
        self._hotkey_mgr.recording_start.connect(self._on_recording_start)
        self._hotkey_mgr.recording_stop.connect(self._on_recording_stop)
        self._hotkey_mgr.recording_cancel.connect(self._on_recording_cancel)
        self._hotkey_mgr.continuous_listen_start.connect(self._on_continuous_hotkey_start)
        self._hotkey_mgr.hotkey_tap_too_short.connect(self._on_hotkey_tap_too_short)
        self._hotkey_mgr.esc_pressed.connect(self._on_esc_pressed)
        self._hotkey_mgr.listener_status.connect(self._on_hotkey_listener_status)

        self._recorder.volume_changed.connect(self._floating.update_volume)
        self._recorder.recording_finished.connect(self._on_recording_finished)
        self._recorder.segment_ready.connect(self._on_segment_ready)
        self._recorder.error.connect(self._on_recorder_error)
        self._recorder.warning.connect(self._on_recorder_warning)
        self._recorder.no_speech_warning.connect(self._on_no_speech_warning)

        self._recognizer.final_result.connect(self._on_final_result)
        self._recognizer.error.connect(self._on_recognizer_error)
        self._recognizer.ready.connect(self._on_stt_ready)
        self._recognizer.model_load_progress.connect(self._on_model_load_progress)

        self._polisher.polish_complete.connect(self._on_polish_complete)
        self._polisher.polish_error.connect(self._on_polish_error)

        self._floating.continuous_stop_requested.connect(self._stop_continuous_user_session)

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
        from voiceink.speech_recognizer import is_model_downloaded, resolve_startup_model_id

        configured = self._config.get("stt.model_id", DEFAULT_MODEL_ID)
        model_id = resolve_startup_model_id(configured)
        num_threads = self._config.get("stt.num_threads", 4)

        if model_id and is_model_downloaded(model_id):
            info = get_model_info(model_id)
            name = info["name"] if info else model_id
            needs_load = not (
                self._recognizer.current_model_id == model_id
                and self._recognizer.is_ready
            )
            if needs_load and not self._recognizer.is_loading:
                self._floating.show_model_loading(
                    f"正在将 {name} 载入内存，请稍候（约 10–40 秒）…"
                )
                self._tray.set_activity_tooltip("loading")
                self._sync_settings_runtime_status()
            self._recognizer.configure(model_id, num_threads)
        else:
            info = get_model_info(model_id) if model_id else None
            name = info["name"] if info else (model_id or DEFAULT_MODEL_ID)
            log.warning("语音模型 %s 未下载，请在设置中下载模型", name)
            hint = f"请下载语音模型「{name}」：右键托盘 → 设置 → 模型"
            self._floating.show_error(hint)
            self._tray.showMessage(
                "VoiceInk",
                hint,
                QSystemTrayIcon.MessageIcon.Warning,
                6000,
            )

    # ── Recording flow ────────────────────────────────

    def _model_not_ready_message(self) -> str:
        if self._recognizer.is_loading:
            return "模型加载中，请稍候"
        return self._friendly_error("模型未就绪")

    def _show_model_not_ready(self) -> None:
        if self._recognizer.is_loading:
            self._floating.show_model_loading("正在加载语音模型，请稍候...")
            self._tray.set_activity_tooltip("loading")
        else:
            self._floating.show_error(self._friendly_error("模型未就绪"))

    def _pending_segment_count(self) -> int:
        return len(self._segment_queue) + (1 if self._is_transcribing else 0)

    def _on_esc_pressed(self):
        if self._continuous_session_active():
            self._stop_continuous_user_session()
            return
        if self._recorder.is_recording and not self._is_continuous_mode():
            self._on_recording_cancel()

    def _on_hotkey_listener_status(self, ok: bool, message: str):
        if ok:
            return
        self._tray.showMessage(
            "VoiceInk",
            message or "快捷键监听未能启动，请在设置中更换快捷键",
            QSystemTrayIcon.MessageIcon.Warning,
            8000,
        )
        self._floating.show_error(message or "快捷键监听未能启动")

    def _on_model_load_progress(self, msg: str):
        if "就绪" in msg:
            self._floating.clear_model_loading_lock()
            self._sync_settings_runtime_status()
            return
        if "失败" in msg:
            self._floating.clear_model_loading_lock()
            self._tray.set_activity_tooltip(None)
            self._floating.show_error(self._friendly_error(msg))
            self._sync_settings_runtime_status()
            return
        if self._recorder.is_continuous:
            log.info("模型重新加载，暂停持续监听")
            self._stop_continuous_listening()
        self._floating.show_model_loading(
            f"{msg}\n模型已下载，正在载入内存，完成前请勿开始录音"
        )
        self._tray.set_activity_tooltip("loading")
        self._sync_settings_runtime_status()

    def _on_no_speech_warning(self):
        log.warning("持续监听长时间未检测到有效语音")
        self._floating.show_warning(
            "似乎没采集到声音",
            "请检查麦克风设备与系统隐私权限",
        )
        self._tray.showMessage(
            "VoiceInk",
            "持续监听中长时间未检测到语音，请检查麦克风与设备设置。",
            QSystemTrayIcon.MessageIcon.Warning,
            6000,
        )

    def _on_recording_start(self):
        if self._is_continuous_mode():
            return
        if not self._recognizer.is_ready:
            self._show_model_not_ready()
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

    def _on_continuous_hotkey_start(self):
        if not self._is_continuous_mode():
            return
        if not self._recognizer.is_ready:
            log.warning("持续转写：模型未就绪，无法开始监听")
            self._show_model_not_ready()
            if not self._recognizer.is_loading:
                self._tray.showMessage(
                    "VoiceInk",
                    "语音模型未就绪。请在设置 → 模型 中下载 FireRedASR2 并等待加载完成。",
                    QSystemTrayIcon.MessageIcon.Warning,
                    6000,
                )
            return
        if self._recorder.is_continuous:
            log.debug("持续转写：已在监听中，忽略重复快捷键")
            return
        log.info("快捷键触发：开始持续转写")
        self._continuous_user_stopped = False
        self._start_continuous_listening()

    def _on_hotkey_tap_too_short(self):
        if self._continuous_session_active():
            log.debug("已在持续监听中，忽略快捷键短按提示")
            return

        hotkey = self._continuous_hotkey_label()
        hint = f"请按住 {hotkey} 约 {MIN_HOLD_MS / 1000:.2f} 秒以上"
        hotkey_raw = self._config.get("hotkey", "").lower()
        if "ctrl+space" in hotkey_raw.replace(" ", ""):
            hint += "。Ctrl+Space 常被输入法占用，请在设置中改为 Alt+Space"
        log.info("快捷键按过短: %s", hint)

        now = time.monotonic()
        cooldown = 0.0 if not self._hotkey_conflict_warned else SHORT_TAP_TRAY_COOLDOWN_S
        if now - self._short_tap_tray_last_at >= cooldown:
            self._hotkey_conflict_warned = True
            self._short_tap_tray_last_at = now
            self._tray.showMessage(
                "VoiceInk", hint, QSystemTrayIcon.MessageIcon.Information, 4000
            )

        if self._is_continuous_mode() and self._recognizer.is_ready:
            self._floating.show_continuous_idle(hotkey)
        elif not self._is_continuous_mode():
            self._floating.show_error("录音过短\n" + hint.split("。")[0])

    def _stop_continuous_user_session(self):
        """End the whole continuous listen session; in-flight transcription still completes."""
        if not self._is_continuous_mode() or not self._recorder.is_continuous:
            return
        self._continuous_user_stopped = True
        log.info("用户停止持续转写会话（进行中的识别会继续完成）")
        if self._recorder.is_continuous or self._recorder.is_recording:
            self._recorder.stop_continuous()
        self._tray.set_activity_tooltip(None)
        self._floating.show_continuous_stopped()
        QTimer.singleShot(1200, self._floating.dismiss_if_idle)

    def _on_recorder_error(self, error_msg: str):
        if self._recorder.is_continuous:
            self._stop_continuous_listening()
        self._tray.set_recording(False)
        self._tray.set_activity_tooltip(None)
        self._sound.play_error()
        self._floating.show_error(self._friendly_error(error_msg))

    def _on_recorder_warning(self, warning_msg: str):
        log.warning("%s", warning_msg)
        self._floating.show_warning("音频采集受限", warning_msg)
        self._tray.showMessage(
            "VoiceInk",
            warning_msg,
            QSystemTrayIcon.MessageIcon.Warning,
            10000,
        )

    def _start_continuous_listening(self):
        if not self._is_continuous_mode():
            return
        if not self._recognizer.is_ready:
            return
        if self._recorder.is_continuous:
            return
        log.info("开启自动持续转写（来源: %s）", self._recorder.input_source_display)
        self._sound.play_start()

        def _begin():
            if not self._recognizer.is_ready or self._recognizer.is_loading:
                log.warning("延迟开启持续监听时模型仍未就绪，已取消")
                self._tray.set_activity_tooltip(None)
                self._show_model_not_ready()
                return
            self._recorder.start_continuous()
            if not self._recorder.is_continuous:
                log.warning("持续监听启动失败")
                self._tray.set_activity_tooltip(None)
                self._floating.show_error("无法开启持续监听\n请检查音频设备设置")
                return
            self._tray.set_activity_tooltip("listening")
            self._floating.show_listening()
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
        if not self._recognizer.is_ready:
            if self._recognizer.is_loading:
                self._segment_queue.append(audio)
                log.debug("模型加载中，语音段已排队（队列 %d）", len(self._segment_queue))
                self._floating.show_model_loading(
                    "模型加载中，已录制的语音将排队等待识别…"
                )
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
        if not self._recognizer.is_ready:
            if self._recognizer.is_loading:
                self._segment_queue.insert(0, audio)
                self._floating.show_model_loading("模型加载中，识别已暂停…")
            return
        self._is_transcribing = True
        self._tray.set_activity_tooltip("recognizing")
        self._floating.show_recognizing()
        self._recognizer.transcribe_final(audio)

    def _on_final_result(self, text: str):
        text = normalize_asr_output(text)
        if not text.strip():
            log.warning("未识别到语音内容")
            self._is_transcribing = False
            if self._recognizer.is_loading:
                self._floating.show_model_loading("模型加载中，请稍候…")
                self._tray.set_activity_tooltip("loading")
                self._pump_segment_queue()
                return
            self._tray.set_activity_tooltip(
                "listening" if self._continuous_session_active() else None
            )
            if self._continuous_session_active():
                self._floating.show_listening()
            elif self._is_continuous_mode():
                self._refresh_continuous_ui_after_output()
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
        self._floating.clear_model_loading_lock()
        self._tray.set_activity_tooltip("listening" if self._is_continuous_mode() else None)
        self._sound.play_error()
        self._floating.show_error(self._friendly_error(error_msg))
        self._pump_segment_queue()
        if self._is_continuous_mode() and not self._recorder.is_continuous and not self._continuous_user_stopped:
            QTimer.singleShot(1500, self._start_continuous_listening)

    def _pump_segment_queue(self):
        if self._is_transcribing or not self._segment_queue:
            if self._continuous_session_active() and not self._is_transcribing:
                self._floating.show_listening()
            return
        next_audio = self._segment_queue.pop(0)
        self._begin_transcription(next_audio)

    def _on_stt_ready(self):
        self._floating.clear_model_loading_lock()
        self._tray.set_activity_tooltip(None)
        self._sync_settings_runtime_status()
        if self._segment_queue and not self._is_transcribing:
            log.info("模型就绪，处理排队语音 %d 段", len(self._segment_queue))
            self._pump_segment_queue()
        hotkey = self._continuous_hotkey_label()
        if self._is_continuous_mode():
            self._floating.show_continuous_idle(hotkey)
            tray_msg = (
                f"持续转写已就绪。按住 {hotkey} 开始监听，说完停顿后自动出字；"
                "按 Esc 或点击浮窗右上角 × 停止。"
            )
        else:
            log.info("✓ 语音识别模型已就绪，按 %s 开始语音输入", hotkey)
            self._floating.show_success("已就绪", f"按 {hotkey} 开始语音输入")
            tray_msg = f"已就绪，按 {hotkey} 开始语音输入"
        self._tray.showMessage(
            "VoiceInk",
            tray_msg,
            QSystemTrayIcon.MessageIcon.Information,
            6000 if self._is_continuous_mode() else 3000,
        )

    # ── Polishing ─────────────────────────────────────

    def _on_polish_complete(self, polished_text: str):
        self._output_text(polished_text)

    def _on_polish_error(self, error_msg: str):
        log.warning("润色失败，降级输出原文: %s", error_msg)
        self._output_text(self._current_transcription, degraded_from_polish=True)

    # ── Output ────────────────────────────────────────

    def _output_text(self, text: str, *, degraded_from_polish: bool = False):
        self._is_transcribing = False
        text = normalize_asr_output(text)
        if not text.strip():
            self._tray.set_activity_tooltip(
                "listening" if self._continuous_session_active() else None
            )
            if self._continuous_session_active():
                self._floating.show_listening()
            elif self._is_continuous_mode():
                self._refresh_continuous_ui_after_output()
            else:
                self._floating.show_error(self._friendly_error("未识别"))
            self._pump_segment_queue()
            return

        self._paster.paste_async(text, lambda result: self._handle_paste_result(
            result, degraded_from_polish=degraded_from_polish
        ))

    def _handle_paste_result(self, result: str, *, degraded_from_polish: bool = False):
        paste_hint = "可按 Cmd+V 粘贴" if sys.platform == "darwin" else "可按 Ctrl+V 粘贴"
        success_msg = "已输入（原文）" if degraded_from_polish else "已输入"

        if result == "pasted":
            log.info("已粘贴到光标位置")
            self._tray.set_activity_tooltip(
                "listening" if self._continuous_session_active() else None
            )
            if self._continuous_session_active():
                if degraded_from_polish:
                    self._floating.show_info(success_msg)
                else:
                    self._floating.show_success("已输入")
                QTimer.singleShot(1700, self._refresh_continuous_ui_after_output)
            else:
                self._floating.dismiss_if_idle()
                if degraded_from_polish:
                    self._floating.show_info(success_msg)
                else:
                    self._floating.show_success("已输入")
        elif result == "clipboard":
            log.info("已复制到剪贴板（粘贴未确认成功）")
            self._tray.set_activity_tooltip(
                "listening" if self._continuous_session_active() else None
            )
            if self._continuous_session_active():
                self._floating.show_success("已复制", paste_hint)
                QTimer.singleShot(2200, self._refresh_continuous_ui_after_output)
            else:
                self._floating.dismiss_if_idle()
                self._floating.show_success("已复制到剪贴板", paste_hint)
        else:
            error_msg = result.replace("error:", "")
            log.error("输出失败: %s", error_msg)
            self._tray.set_activity_tooltip(
                "listening" if self._continuous_session_active() else None
            )
            self._floating.show_error(self._friendly_error("输出失败"))

        QTimer.singleShot(300, self._pump_segment_queue)

    # ── Settings ──────────────────────────────────────

    def _sync_settings_runtime_status(self) -> None:
        if self._settings_win is None:
            return
        if self._recognizer.is_loading:
            status = "模型加载中…"
        elif self._recognizer.is_ready:
            status = "就绪"
        else:
            status = "模型未就绪"
        self._settings_win.set_runtime_status(status)

    def _show_settings(self):
        if self._settings_win is not None and self._settings_win.isVisible():
            self._settings_win.raise_()
            self._settings_win.activateWindow()
            return

        if self._settings_win is None:
            self._settings_win = SettingsWindow(
                self._config,
                pending_segment_count=self._pending_segment_count,
            )
            self._settings_win.hotkey_updated.connect(self._on_hotkey_updated)
            self._settings_win.settings_changed.connect(self._on_settings_changed)
            self._settings_win.auto_start_changed.connect(self._on_auto_start_toggled)
            self._settings_win.sound_enabled_changed.connect(self._on_sound_enabled_changed)
            self._settings_win.models_changed.connect(self._on_models_changed)
            self._settings_win.finished.connect(self._on_settings_closed)
            self._settings_win.hotkey_capture_started.connect(self._hotkey_mgr.pause)
            self._settings_win.hotkey_capture_ended.connect(self._hotkey_mgr.resume)

        self._settings_win.reload_settings()
        self._sync_settings_runtime_status()
        self._settings_win.show()
        self._settings_win.raise_()
        self._settings_win.activateWindow()

    def _on_settings_closed(self):
        if self._settings_win is not None:
            self._settings_win.cancel_hotkey_capture()
        self._hotkey_mgr.resume()
        self._update_tray_models()

    def _on_hotkey_updated(self, new_hotkey: str):
        self._hotkey_mgr.update_hotkey(new_hotkey)
        if self._is_continuous_mode() and not self._recorder.is_continuous:
            self._floating.show_continuous_idle(format_hotkey(new_hotkey))

    def _on_models_changed(self):
        """Reload STT after model download/select without requiring a full settings save."""
        if self._recorder.is_continuous:
            self._stop_continuous_listening()
        self._configure_stt()
        self._update_tray_models()
        if self._recognizer.is_ready and self._is_continuous_mode() and not self._recorder.is_continuous:
            self._floating.show_continuous_idle(self._continuous_hotkey_label())

    def _on_settings_changed(self):
        was_continuous = self._recorder.is_continuous
        if was_continuous:
            self._stop_continuous_listening()

        self._continuous_user_stopped = False
        self._sound.enabled = self._config.get("sound_enabled", True)
        self._tray.set_auto_start(self._config.get("auto_start", False))
        self._apply_audio_config()
        set_models_dir(self._config.models_dir)
        self._configure_stt()
        self._update_tray_models()
        if self._pending_segment_count() > 0:
            log.warning("设置已保存，丢弃 %d 段待识别语音", self._pending_segment_count())
        self._segment_queue.clear()
        self._paster.restore_clipboard = self._config.get(
            "output.restore_clipboard", False
        )
        self._sync_hotkey_trigger_mode()

        if self._is_continuous_mode() and self._recognizer.is_ready and not self._recorder.is_continuous:
            self._floating.show_continuous_idle(self._continuous_hotkey_label())

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
        self._tray.set_auto_start(enabled)
        self._setup_auto_start(enabled)

    def _on_sound_enabled_changed(self, enabled: bool):
        self._config.set("sound_enabled", enabled)
        self._sound.enabled = enabled

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
            # 等模型加载完成后再弹欢迎框，避免挡住「模型加载中」状态
            self._recognizer.ready.connect(self._show_first_run_welcome_once)
            QTimer.singleShot(15000, self._show_first_run_welcome_once)

    def _show_first_run_welcome_once(self):
        if self._config.get("first_run_welcome_seen", True):
            return
        try:
            self._recognizer.ready.disconnect(self._show_first_run_welcome_once)
        except TypeError:
            pass
        QTimer.singleShot(400, self._show_first_run_welcome)

    def _show_first_run_welcome(self):
        if self._is_continuous_mode():
            hotkey = self._continuous_hotkey_label()
            mode_tip = (
                f"当前为「自动持续转写」：按住 {hotkey} 开始监听，"
                "按 Esc 或点击浮窗右上角 × 停止。"
            )
        else:
            hk = format_hotkey(self._config.get("hotkey", "alt+space"))
            mode_tip = f"当前为「按住快捷键」：按住 {hk} 说话，松开后识别并粘贴。"
        text = (
            "VoiceInk 在本地完成语音识别（可选通过网络调用大模型润色）。\n\n"
            f"{mode_tip}\n\n"
            "请在设置 → 通用 中选择音频来源：\n"
            "· 仅麦克风：你的说话\n"
            "· 仅电脑播放：视频/会议远端声音\n"
            "· 混合：开会时远端 + 自己都要\n\n"
            "请先在设置 → 模型 中下载至少一个语音模型。\n\n"
            "提示：中文 Windows 上请勿使用 Ctrl+Space（常被输入法占用），"
            "推荐使用 Alt+Space。"
        )
        QMessageBox.information(None, "欢迎使用 VoiceInk", text)
        self._config.set("first_run_welcome_seen", True)
