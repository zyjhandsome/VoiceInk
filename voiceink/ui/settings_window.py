import logging
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QMessageBox, QFrame, QScrollArea,
    QStackedWidget,
    QFileDialog, QTextEdit,
    QSizePolicy, QRadioButton, QButtonGroup, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer

log = logging.getLogger("VoiceInk")

from voiceink.config import (
    Config,
    VERSION,
    format_hotkey,
    TRIGGER_MODE_CONTINUOUS,
    TRIGGER_MODE_HOTKEY,
)
from voiceink.audio_recorder import AudioRecorder
from voiceink.audio_devices import (
    INPUT_SOURCE_MICROPHONE,
    INPUT_SOURCE_MIXED,
    INPUT_SOURCE_SYSTEM,
    list_microphone_devices,
    list_system_capture_devices_for_settings,
    platform_audio_hint,
    sanitize_system_device_index,
)

from voiceink.ui.settings_components import (
    AudioSourcePicker,
    PAGE_SUBTITLE,
    PageHero,
    SettingsPage,
    SettingsSidebar,
    ToggleOptionRow,
    TriggerModePicker,
    WideTestButton,
    device_selection_link,
    elide_middle,
    empty_state,
    footnote,
    group_divider,
    info_callout,
    inline_action_row,
    kv_row,
    kv_row_elided,
    labeled_row,
    polish_preview_content,
    settings_group,
    settings_section,
    stacked_field_row,
    usage_tip_bar,
)
from voiceink.ui.hotkey_edit import HotkeyEdit
from voiceink.ui.model_card import ModelCard
from voiceink.ui.nav_icons import nav_icon
from voiceink.ui.settings_styles import (
    BTN_GHOST as _BTN_GHOST,
    BTN_GHOST_SM as _BTN_GHOST_SM,
    BTN_PRIMARY as _BTN_PRIMARY,
    WINDOW_CSS,
)
from voiceink.ui.design_tokens import (
    ACCENT as _ACCENT,
    ACCENT_FOCUS as _ACCENT_FOCUS,
    BAR_OFF as _BAR_OFF,
    BG as _BG,
    DIVIDER_SOFT as _DIVIDER_SOFT,
    FONT as _FONT,
    FONT_DISPLAY as _FONT_DISPLAY,
    HAIRLINE as _HAIRLINE,
    INPUT_BG as _INPUT_BG,
    RADIUS_MD as _RADIUS_MD,
    TEXT as _TEXT,
    TEXT_DIM as _TEXT_DIM,
    TEXT_SEC as _TEXT_SEC,
)

# ── Settings Window ──────────────────────────────────────────────


class SettingsWindow(QDialog):
    hotkey_updated = pyqtSignal(str)
    settings_changed = pyqtSignal()
    auto_start_changed = pyqtSignal(bool)
    sound_enabled_changed = pyqtSignal(bool)
    models_changed = pyqtSignal()
    hotkey_capture_started = pyqtSignal()
    hotkey_capture_ended = pyqtSignal()

    def __init__(self, config: Config, parent=None, pending_segment_count=None):
        super().__init__(parent)
        self._config = config
        self._pending_segment_count = pending_segment_count
        self._model_cards: dict[str, ModelCard] = {}
        self._dl_workers: dict[str, object] = {}
        self._mic_test_recorder = AudioRecorder(self)
        self._mic_probe_active = False
        self._mic_probe_max = 0.0
        self._loading = False
        self._runtime_status_hint = "就绪"
        self._setup_window()
        self._setup_ui()
        self._load_settings()

    def _setup_window(self):
        self.setWindowTitle("设置")
        self.setMinimumSize(720, 560)
        self.resize(860, 620)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setStyleSheet(WINDOW_CSS)

    def _on_nav_changed(self, row: int):
        self._pages.setCurrentIndex(row)

    def _open_about_from_general(self) -> None:
        self._sidebar.set_active(3)
        self._pages.setCurrentIndex(3)

    # ── Layout ─────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = SettingsSidebar(nav_icon)
        self._sidebar.page_changed.connect(self._on_nav_changed)
        body.addWidget(self._sidebar)

        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet(f"background: {_HAIRLINE};")
        body.addWidget(div)

        content_wrap = QWidget()
        content_wrap.setStyleSheet(f"background: {_BG};")
        content_lay = QHBoxLayout(content_wrap)
        content_lay.setContentsMargins(16, 0, 16, 0)
        content_lay.setSpacing(0)

        self._pages = QStackedWidget()
        self._pages.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        self._pages.setStyleSheet(f"background: {_BG};")
        self._pages.addWidget(self._create_general_page())
        self._pages.addWidget(self._create_model_page())
        self._pages.addWidget(self._create_polish_page())
        self._pages.addWidget(self._create_about_page())
        content_lay.addWidget(self._pages, 1)
        body.addWidget(content_wrap, 1)

        root.addLayout(body, 1)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_DIVIDER_SOFT};")
        root.addWidget(sep)

        footer = QWidget()
        footer.setObjectName("settingsFooter")
        footer.setStyleSheet(f"""
            QWidget#settingsFooter {{
                background: {_BG};
                border-top: 1px solid {_HAIRLINE};
            }}
        """)
        btn_bar = QHBoxLayout(footer)
        btn_bar.setContentsMargins(16, 12, 16, 12)
        btn_bar.setSpacing(12)

        self._footer_hint = QLabel("更改会即时生效")
        self._footer_hint.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 12px; background: transparent;"
            f" padding-left: 4px;"
        )
        btn_bar.addWidget(self._footer_hint, 1)

        done_btn = QPushButton("完成")
        done_btn.setFixedHeight(38)
        done_btn.setMinimumWidth(96)
        done_btn.setStyleSheet(_BTN_PRIMARY)
        done_btn.setDefault(True)
        done_btn.setAutoDefault(True)
        done_btn.setAccessibleName("完成并关闭设置")
        done_btn.clicked.connect(self._on_done)
        btn_bar.addWidget(done_btn)

        root.addWidget(footer)

    # ── Page: General ──────────────────────────────────

    def set_runtime_status(self, hint: str) -> None:
        self._runtime_status_hint = hint.strip() or "就绪"
        self._refresh_sidebar_status()

    def _create_general_page(self) -> QWidget:
        page = SettingsPage()
        self._general_hero = PageHero(
            "通用设置",
            subtitle="快捷键、触发方式与音频输入",
        )
        page.add(self._general_hero)

        trig_group = settings_group()
        trig_lay = QVBoxLayout(trig_group)
        trig_lay.setContentsMargins(0, 0, 0, 0)
        trig_lay.setSpacing(0)
        self._trigger_group = QButtonGroup(self)
        self._trigger_continuous_rb = QRadioButton()
        self._trigger_hotkey_rb = QRadioButton()
        for rb in (self._trigger_continuous_rb, self._trigger_hotkey_rb):
            self._trigger_group.addButton(rb)
        trig_lay.addWidget(TriggerModePicker(
            self._trigger_continuous_rb,
            self._trigger_hotkey_rb,
        ))
        page.add(settings_section("触发方式", trig_group))

        hk_group = settings_group()
        hk_lay = QVBoxLayout(hk_group)
        hk_lay.setContentsMargins(0, 0, 0, 0)
        hk_lay.setSpacing(0)
        self._hotkey_edit = HotkeyEdit()
        self._hotkey_edit.setObjectName("HotkeyEdit")
        self._hotkey_edit.setMinimumHeight(48)
        self._hotkey_edit.capture_started.connect(self.hotkey_capture_started.emit)
        self._hotkey_edit.capture_ended.connect(self.hotkey_capture_ended.emit)
        self._hotkey_edit.hotkey_changed.connect(self._apply_hotkey_setting)
        hk_lay.addWidget(stacked_field_row(
            "录音快捷键", self._hotkey_edit,
            "点击输入框后按下组合键绑定；按住该键开始录音，松开结束",
        ))
        page.add(settings_section("快捷键", hk_group))

        pref_group = settings_group()
        pref_lay = QVBoxLayout(pref_group)
        pref_lay.setContentsMargins(0, 0, 0, 0)
        pref_lay.setSpacing(0)
        self._auto_start_row = ToggleOptionRow(
            "开机时自动启动", "登录 Windows 后自动在托盘运行",
        )
        self._sound_row = ToggleOptionRow(
            "录音提示音", "开始和结束录音时播放短促提示音",
        )
        self._auto_start_row.toggled.connect(self._on_auto_start_toggled)
        self._sound_row.toggled.connect(self._on_sound_toggled)
        pref_lay.addWidget(self._auto_start_row)
        pref_lay.addWidget(group_divider())
        pref_lay.addWidget(self._sound_row)
        page.add(settings_section("开机与提示音", pref_group))

        history_group = settings_group()
        history_lay = QVBoxLayout(history_group)
        history_lay.setContentsMargins(0, 0, 0, 0)
        history_lay.setSpacing(0)
        self._history_enabled_row = ToggleOptionRow(
            "保存语音历史",
            "记录未来识别结果；关闭后不会删除已有历史",
        )
        self._history_retention_days_spin = QSpinBox()
        self._history_retention_days_spin.setRange(1, 3650)
        self._history_retention_days_spin.setSuffix(" 天")
        self._history_retention_days_spin.setAccessibleName("历史保留天数")
        self._history_max_entries_spin = QSpinBox()
        self._history_max_entries_spin.setRange(1, 100000)
        self._history_max_entries_spin.setSingleStep(100)
        self._history_max_entries_spin.setSuffix(" 场")
        self._history_max_entries_spin.setAccessibleName("最多保留会话数")
        self._history_enabled_row.toggled.connect(self._on_history_enabled_toggled)
        self._history_retention_days_spin.valueChanged.connect(self._on_history_limits_changed)
        self._history_max_entries_spin.valueChanged.connect(self._on_history_limits_changed)
        history_lay.addWidget(self._history_enabled_row)
        history_lay.addWidget(group_divider())
        history_lay.addWidget(labeled_row(
            "保留天数",
            self._history_retention_days_spin,
            "超过天数的旧会话会在清理时删除，当前会话不会被半删。",
        ))
        history_lay.addWidget(group_divider())
        history_lay.addWidget(labeled_row(
            "最大会话数",
            self._history_max_entries_spin,
            "按整场会话计数，超出后优先清理最旧会话。",
        ))
        page.add(settings_section("历史", history_group))

        src_group = settings_group()
        src_lay = QVBoxLayout(src_group)
        src_lay.setContentsMargins(0, 0, 0, 0)
        src_lay.setSpacing(0)
        self._source_group = QButtonGroup(self)
        self._src_mic_rb = QRadioButton()
        self._src_sys_rb = QRadioButton()
        self._src_mixed_rb = QRadioButton()
        for rb in (self._src_mic_rb, self._src_sys_rb, self._src_mixed_rb):
            self._source_group.addButton(rb)
        src_lay.addWidget(AudioSourcePicker(
            self._src_mic_rb, self._src_sys_rb, self._src_mixed_rb,
        ))
        self._mixed_audio_callout = info_callout(
            "混合模式会同时收录麦克风与电脑播放声。若背景有视频、音乐或会议远端声音，"
            "识别结果可能混杂中英或乱码。日常口述建议选「仅麦克风」。"
        )
        self._mixed_audio_callout.setVisible(False)
        callout_wrap = QWidget()
        callout_lay = QHBoxLayout(callout_wrap)
        callout_lay.setContentsMargins(16, 0, 16, 12)
        callout_lay.addWidget(self._mixed_audio_callout)
        src_lay.addWidget(callout_wrap)
        self._src_mic_rb.toggled.connect(self._sync_source_device_widgets)
        self._src_sys_rb.toggled.connect(self._sync_source_device_widgets)
        self._src_mixed_rb.toggled.connect(self._sync_source_device_widgets)
        page.add(settings_section("音频来源", src_group))

        test_group = settings_group()
        test_lay = QVBoxLayout(test_group)
        test_lay.setContentsMargins(0, 0, 0, 0)
        test_lay.setSpacing(0)
        self._mic_test_btn = WideTestButton("测试声音（约 2 秒）")
        self._mic_test_btn.clicked.connect(self._run_mic_probe)
        test_lay.addWidget(self._mic_test_btn)
        self._mic_test_status = QLabel("")
        self._mic_test_status.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 12px; background: transparent;"
            f" padding: 0 16px 10px 16px;"
        )
        self._mic_test_status.setWordWrap(True)
        test_lay.addWidget(self._mic_test_status)
        page.add(settings_section("检测音频", test_group))

        adv_toggle_row = QHBoxLayout()
        adv_toggle_row.setContentsMargins(16, 0, 16, 0)
        self._advanced_audio_btn = device_selection_link("手动选择音频设备")
        self._advanced_audio_btn.toggled.connect(self._toggle_advanced_audio)
        adv_toggle_row.addWidget(self._advanced_audio_btn)
        adv_toggle_row.addStretch()
        page.add_layout(adv_toggle_row)

        self._advanced_audio_panel = settings_group()
        self._advanced_audio_panel.setVisible(False)
        self._advanced_audio_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        adv_lay = QVBoxLayout(self._advanced_audio_panel)
        adv_lay.setContentsMargins(0, 0, 0, 0)
        adv_lay.setSpacing(0)
        self._mic_device_combo = QComboBox()
        self._system_device_combo = QComboBox()
        adv_lay.addWidget(labeled_row("麦克风", self._mic_device_combo))
        adv_lay.addWidget(group_divider())
        adv_lay.addWidget(labeled_row("电脑声", self._system_device_combo))

        dev_btn_row = QHBoxLayout()
        dev_btn_row.setContentsMargins(16, 8, 16, 12)
        dev_btn_row.setSpacing(8)
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setStyleSheet(_BTN_GHOST_SM)
        refresh_btn.clicked.connect(self._refresh_audio_device_lists)
        reset_btn = QPushButton("恢复自动选择")
        reset_btn.setStyleSheet(_BTN_GHOST_SM)
        reset_btn.setToolTip("让程序自动挑选设备，避免选到打不开的声卡")
        reset_btn.clicked.connect(self._reset_audio_devices_to_auto)
        dev_btn_row.addWidget(refresh_btn)
        dev_btn_row.addWidget(reset_btn)
        dev_btn_row.addStretch()
        adv_lay.addLayout(dev_btn_row)
        page.add(settings_section("", self._advanced_audio_panel))

        for rb in (self._src_mic_rb, self._src_sys_rb, self._src_mixed_rb):
            rb.toggled.connect(self._on_input_source_radio_toggled)
        self._trigger_continuous_rb.toggled.connect(self._on_trigger_mode_radio_toggled)
        self._trigger_hotkey_rb.toggled.connect(self._on_trigger_mode_radio_toggled)
        self._mic_device_combo.currentIndexChanged.connect(self._on_audio_device_changed)
        self._system_device_combo.currentIndexChanged.connect(self._on_audio_device_changed)

        page.add(footnote(
            f"{platform_audio_hint()}\n"
            "若 Ctrl+Space 无反应，可改为 Alt+Space。"
        ))
        page.set_compact()
        return page

    # ── Page: Model ────────────────────────────────────

    def _create_model_page(self) -> QWidget:
        page = SettingsPage()
        self._model_hero = PageHero("语音识别")
        page.add(self._model_hero)

        self._model_hero_host = settings_group()
        self._model_hero_layout = QVBoxLayout(self._model_hero_host)
        self._model_hero_layout.setContentsMargins(0, 0, 0, 0)
        self._model_hero_layout.setSpacing(0)
        page.add(settings_section("当前引擎", self._model_hero_host))

        storage_group = settings_group()
        storage_lay = QHBoxLayout(storage_group)
        storage_lay.setContentsMargins(16, 12, 12, 12)
        storage_lay.setSpacing(10)
        self._storage_summary_label = QLabel()
        self._storage_summary_label.setStyleSheet(
            f"color: {_TEXT_SEC}; font-size: 13px; background: transparent;"
        )
        self._storage_summary_label.setWordWrap(True)
        storage_lay.addWidget(self._storage_summary_label, 1)
        chg = QPushButton("更改存储…")
        chg.setFixedHeight(32)
        chg.setStyleSheet(_BTN_GHOST_SM)
        chg.clicked.connect(self._change_model_dir)
        storage_lay.addWidget(chg)
        page.add(settings_section("存储", storage_group))

        self._dir_path_label = QLabel()
        self._dir_path_label.setVisible(False)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(24)
        page.add(self._cards_container)
        page.set_compact()
        return page

    def _refresh_dir_label(self):
        p = str(self._config.models_dir)
        self._dir_path_label.setText(p)
        self._dir_path_label.setToolTip(p)
        self._refresh_storage_summary()

    def _change_model_dir(self):
        cur = str(self._config.models_dir)
        d = QFileDialog.getExistingDirectory(self, "选择模型存储目录", cur)
        if not d:
            return
        new_p = Path(d)
        old_p = self._config.models_dir
        if new_p == old_p:
            return
        new_p.mkdir(parents=True, exist_ok=True)
        moved = 0
        failed: list[str] = []
        if old_p.exists():
            for item in old_p.iterdir():
                if item.is_dir():
                    target = new_p / item.name
                    if not target.exists():
                        try:
                            shutil.move(str(item), str(target))
                            moved += 1
                        except OSError as e:
                            log.warning("模型目录迁移失败 %s: %s", item.name, e)
                            failed.append(item.name)
        self._config.set("stt.models_dir", str(new_p))
        from voiceink.speech_recognizer import set_models_dir
        set_models_dir(new_p)
        self._refresh_dir_label()
        self._rebuild_model_cards()
        if moved > 0:
            QMessageBox.information(self, "完成", f"已将 {moved} 个模型迁移到新目录。")
        if failed:
            QMessageBox.warning(
                self,
                "部分迁移失败",
                "以下模型未能迁移，请手动复制后重试：\n" + "\n".join(failed),
            )

    def _refresh_storage_summary(self) -> None:
        if not hasattr(self, "_storage_summary_label"):
            return
        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded

        downloaded = [m for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]
        total_mb = sum(m["size_mb"] for m in downloaded)
        path = elide_middle(str(self._config.models_dir), 36)
        count = len(downloaded)
        self._storage_summary_label.setText(
            f"已下载 {count} 个 · 约 {total_mb} MB · {path}"
        )
        self._storage_summary_label.setToolTip(str(self._config.models_dir))

    def _refresh_active_model_hero(self) -> None:
        if not hasattr(self, "_model_hero_layout"):
            return
        while self._model_hero_layout.count():
            item = self._model_hero_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from voiceink.speech_recognizer import DEFAULT_MODEL_ID, get_model_info, is_model_downloaded

        active_id = self._config.get("stt.model_id", DEFAULT_MODEL_ID)
        info = get_model_info(active_id) if active_id else None
        if not info or not is_model_downloaded(active_id):
            empty_wrap = QWidget()
            empty_lay = QVBoxLayout(empty_wrap)
            empty_lay.setContentsMargins(0, 8, 0, 8)
            empty_lay.addWidget(empty_state("尚未选择已下载的模型，请从下方下载并启用。"))
            self._model_hero_layout.addWidget(empty_wrap)
            return

        card = QWidget()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel(info["name"])
        title.setStyleSheet(
            f"color: {_TEXT}; font-family: {_FONT_DISPLAY}; font-size: 18px;"
            f" font-weight: 600; background: transparent;"
        )
        head.addWidget(title)
        badge = QLabel("当前引擎")
        badge.setStyleSheet(
            f"background: {_ACCENT}; color: white; border-radius: 10px;"
            f" padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )
        head.addWidget(badge)
        head.addStretch()
        size = QLabel(f"{info['size_mb']} MB")
        size.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 12px; background: transparent;")
        head.addWidget(size)
        lay.addLayout(head)

        desc = QLabel(info["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_TEXT_SEC}; font-size: 13px; background: transparent;")
        lay.addWidget(desc)

        meta = QLabel(f"{info['languages']} · 准确率 {info['accuracy']}/5 · 速度 {info['speed']}/5")
        meta.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 12px; background: transparent;")
        lay.addWidget(meta)

        self._model_hero_layout.addWidget(card)

    def _rebuild_model_cards(self):
        from voiceink.speech_recognizer import MODEL_REGISTRY, DEFAULT_MODEL_ID, is_model_downloaded
        self._refresh_active_model_hero()
        self._refresh_storage_summary()

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._model_cards.clear()
        active_id = self._config.get("stt.model_id", DEFAULT_MODEL_ID)

        def _add_section(title: str, models: list, downloaded: bool) -> None:
            section = QWidget()
            section_lay = QVBoxLayout(section)
            section_lay.setContentsMargins(0, 0, 0, 0)
            section_lay.setSpacing(10)

            if title:
                hdr = QLabel(title)
                hdr.setStyleSheet(
                    f"color: {_TEXT_SEC}; font-size: 12px; font-weight: 600;"
                    f" padding: 0 4px; background: transparent;"
                    f" letter-spacing: 0.02em;"
                )
                section_lay.addWidget(hdr)

            if not models:
                msg = "暂无其他已下载模型" if downloaded else "所有模型均已下载"
                empty_group = settings_group()
                empty_lay = QVBoxLayout(empty_group)
                empty_lay.setContentsMargins(0, 0, 0, 0)
                empty_lay.addWidget(empty_state(msg))
                section_lay.addWidget(empty_group)
            else:
                list_host = QWidget()
                list_lay = QVBoxLayout(list_host)
                list_lay.setContentsMargins(0, 0, 0, 0)
                list_lay.setSpacing(12)
                for m_info in models:
                    card = ModelCard(
                        m_info, downloaded, downloaded and m_info["id"] == active_id,
                    )
                    card.action_clicked.connect(self._on_card_action)
                    self._model_cards[m_info["id"]] = card
                    list_lay.addWidget(card)
                section_lay.addWidget(list_host)

            self._cards_layout.addWidget(section)

        downloaded_models = [
            m for m in MODEL_REGISTRY
            if is_model_downloaded(m["id"]) and m["id"] != active_id
        ]
        available_models = [m for m in MODEL_REGISTRY if not is_model_downloaded(m["id"])]
        if downloaded_models:
            _add_section("其他已下载", downloaded_models, True)
        _add_section("可下载", available_models, False)
        self._refresh_model_hero_status()

    def _on_card_action(self, model_id: str, action: str):
        if action == "select":
            self._config.set("stt.model_id", model_id)
            self._rebuild_model_cards()
            self.models_changed.emit()
        elif action == "download":
            self._start_download(model_id)
        elif action == "delete":
            self._delete_model(model_id)

    def _start_download(self, model_id: str):
        from voiceink.speech_recognizer import ModelDownloadWorker
        worker = ModelDownloadWorker(model_id)
        self._dl_workers[model_id] = worker
        card = self._model_cards.get(model_id)
        worker.progress.connect(lambda pct, c=card: c.set_download_progress(pct) if c else None)
        worker.finished_ok.connect(lambda mid: self._on_dl_done(mid))
        worker.error.connect(lambda msg, c=card: self._on_dl_error(msg, c))
        worker.start()

    def _on_dl_done(self, model_id: str):
        self._dl_workers.pop(model_id, None)
        from voiceink.speech_recognizer import get_downloaded_models
        downloaded = get_downloaded_models()
        if len(downloaded) == 1 and downloaded[0] == model_id:
            self._config.set("stt.model_id", model_id)
        self._rebuild_model_cards()
        self.models_changed.emit()
        from voiceink.speech_recognizer import get_model_info
        info = get_model_info(model_id)
        name = info["name"] if info else model_id
        QMessageBox.information(self, "完成", f"{name} 已下载，可以开始使用。")

    def _on_dl_error(self, msg: str, card):
        if card:
            card.set_download_error(msg)
        QMessageBox.warning(self, "下载失败", msg)

    def _delete_model(self, model_id: str):
        from voiceink.speech_recognizer import get_model_info, delete_model
        info = get_model_info(model_id)
        name = info["name"] if info else model_id
        reply = QMessageBox.question(
            self, "删除模型",
            f'确定删除 "{name}" 吗？删除后需重新下载。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        active_id = self._config.get("stt.model_id", "")
        delete_model(model_id)
        if active_id == model_id:
            from voiceink.speech_recognizer import get_downloaded_models
            remaining = get_downloaded_models()
            self._config.set("stt.model_id", remaining[0] if remaining else "")
        self._rebuild_model_cards()
        self.models_changed.emit()

    # ── Page: Polish (LLM) ─────────────────────────────

    def _create_polish_page(self) -> QWidget:
        page = SettingsPage()
        self._polish_hero = PageHero("文字润色")
        page.add(self._polish_hero)

        polish_card = settings_group()
        polish_card_lay = QVBoxLayout(polish_card)
        polish_card_lay.setContentsMargins(0, 0, 0, 0)
        polish_card_lay.setSpacing(0)
        self._llm_enable_row = ToggleOptionRow(
            "启用文字润色", "关闭时直接输出语音转写原文",
        )
        self._llm_enable_row.toggled.connect(self._on_llm_enable_toggled)
        polish_card_lay.addWidget(self._llm_enable_row)
        self._llm_preview_divider = group_divider()
        polish_card_lay.addWidget(self._llm_preview_divider)
        self._llm_preview_card = polish_preview_content()
        polish_card_lay.addWidget(self._llm_preview_card)
        page.add(settings_section("", polish_card))

        self._llm_container = QWidget()
        c_lay = QVBoxLayout(self._llm_container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(16)

        conn_group = settings_group()
        conn_lay = QVBoxLayout(conn_group)
        conn_lay.setContentsMargins(0, 0, 0, 0)
        conn_lay.setSpacing(0)
        self._llm_url_edit = QLineEdit()
        self._llm_url_edit.setPlaceholderText("https://api.deepseek.com/v1")
        conn_lay.addWidget(stacked_field_row("接口地址", self._llm_url_edit))

        key_wrap = QWidget()
        key_row = QHBoxLayout(key_wrap)
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(8)
        self._llm_key_edit = QLineEdit()
        self._llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_key_edit.setPlaceholderText("sk-...")
        self._llm_key_toggle = QPushButton("显示")
        self._llm_key_toggle.setFixedWidth(52)
        self._llm_key_toggle.setCheckable(True)
        self._llm_key_toggle.setStyleSheet(_BTN_GHOST_SM)
        self._llm_key_toggle.toggled.connect(
            lambda on: self._llm_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self._llm_key_edit, 1)
        key_row.addWidget(self._llm_key_toggle)
        conn_lay.addWidget(group_divider())
        conn_lay.addWidget(stacked_field_row("API 密钥", key_wrap))
        self._llm_model_edit = QLineEdit()
        self._llm_model_edit.setPlaceholderText("deepseek-chat")
        conn_lay.addWidget(group_divider())
        conn_lay.addWidget(stacked_field_row("模型名称", self._llm_model_edit))

        test_inner = QWidget()
        test_row = QHBoxLayout(test_inner)
        test_row.setContentsMargins(0, 0, 0, 0)
        test_row.addStretch()
        self._llm_test_btn = QPushButton("测试连接")
        self._llm_test_btn.setStyleSheet(_BTN_GHOST_SM)
        self._llm_test_btn.setFixedHeight(32)
        self._llm_test_btn.clicked.connect(self._test_llm)
        test_row.addWidget(self._llm_test_btn)
        conn_lay.addWidget(group_divider())
        conn_lay.addWidget(inline_action_row(test_inner, margins=(16, 8, 16, 12)))
        c_lay.addWidget(settings_section("接口配置", conn_group))

        prompt_group = settings_group()
        prompt_lay = QVBoxLayout(prompt_group)
        prompt_lay.setContentsMargins(16, 12, 16, 12)
        prompt_lay.setSpacing(8)
        ph = QHBoxLayout()
        ph.setContentsMargins(0, 0, 0, 0)
        ph.addStretch()
        self._prompt_reset_btn = QPushButton("恢复默认")
        self._prompt_reset_btn.setStyleSheet(_BTN_GHOST_SM)
        self._prompt_reset_btn.setFixedHeight(28)
        self._prompt_reset_btn.clicked.connect(self._reset_prompt)
        ph.addWidget(self._prompt_reset_btn)
        prompt_lay.addLayout(ph)
        self._llm_prompt_edit = QTextEdit()
        self._llm_prompt_edit.setFixedHeight(128)
        self._llm_prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_INPUT_BG}; color: {_TEXT};
                border: 1px solid {_HAIRLINE}; border-radius: {_RADIUS_MD}px;
                padding: 10px 12px; font-size: 13px; font-family: {_FONT};
            }}
            QTextEdit:focus {{
                border: 2px solid {_ACCENT_FOCUS};
                padding: 9px 11px;
            }}
        """)
        self._llm_prompt_edit.setPlaceholderText("留空则使用内置默认提示词")
        prompt_lay.addWidget(self._llm_prompt_edit)
        c_lay.addWidget(settings_section("提示词", prompt_group))
        c_lay.addWidget(footnote(
            "支持 OpenAI、DeepSeek、通义千问、Ollama 等 OpenAI 兼容接口。"
        ))
        page.add(self._llm_container)

        self._llm_url_edit.editingFinished.connect(self._flush_llm_fields)
        self._llm_key_edit.editingFinished.connect(self._flush_llm_fields)
        self._llm_model_edit.editingFinished.connect(self._flush_llm_fields)
        self._llm_prompt_timer = QTimer(self)
        self._llm_prompt_timer.setSingleShot(True)
        self._llm_prompt_timer.timeout.connect(self._flush_llm_fields)
        self._llm_prompt_edit.textChanged.connect(
            lambda: self._llm_prompt_timer.start(600)
        )

        page.set_compact()
        page.set_spacing(10)
        return page

    def _on_llm_enable_toggled(self, enabled: bool):
        self._llm_container.setVisible(enabled)
        self._llm_preview_card.setVisible(not enabled)
        if hasattr(self, "_llm_preview_divider"):
            self._llm_preview_divider.setVisible(not enabled)
        self._refresh_polish_hero_status()
        if self._loading:
            return
        self._config.set("llm.enabled", enabled)
        self._flush_llm_fields()

    def _reset_prompt(self):
        from voiceink.text_polisher import POLISH_PROMPT
        self._llm_prompt_edit.setPlainText(POLISH_PROMPT)

    # ── Page: About ────────────────────────────────────

    def _create_about_page(self) -> QWidget:
        page = SettingsPage()
        self._about_hero = PageHero("关于 VoiceInk")
        page.add(self._about_hero)

        brand_group = settings_group()
        brand_lay = QHBoxLayout(brand_group)
        brand_lay.setContentsMargins(18, 16, 18, 16)
        brand_lay.setSpacing(14)
        from voiceink.ui.tray_icon import create_microphone_icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            create_microphone_icon(recording=False, size=96).pixmap(48, 48)
        )
        icon_lbl.setStyleSheet("background: transparent;")
        brand_lay.addWidget(icon_lbl)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(4)
        t = QLabel("VoiceInk")
        t.setStyleSheet(
            f"color: {_TEXT}; font-family: {_FONT_DISPLAY}; font-size: 20px;"
            f" font-weight: 600; letter-spacing: -0.3px; background: transparent;"
        )
        brand_text.addWidget(t)
        self._about_version_label = QLabel(f"版本 {VERSION}")
        self._about_version_label.setStyleSheet(PAGE_SUBTITLE)
        brand_text.addWidget(self._about_version_label)
        brand_lay.addLayout(brand_text)
        brand_lay.addStretch()
        page.add(settings_section("", brand_group))

        self._about_usage_tip = usage_tip_bar("")
        page.add(self._about_usage_tip)

        self._about_info_group = settings_group()
        self._about_info_lay = QVBoxLayout(self._about_info_group)
        self._about_info_lay.setContentsMargins(0, 0, 0, 0)
        self._about_info_lay.setSpacing(0)
        page.add(settings_section("运行信息", self._about_info_group))
        page.set_compact()
        return page

    def _refresh_about_info(self):
        while self._about_info_lay.count():
            item = self._about_info_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded, get_model_info

        active_id = self._config.get("stt.model_id", "")
        ai = get_model_info(active_id)
        active_name = ai["name"] if ai else "未选择"

        downloaded = [m for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]
        total_mb = sum(m["size_mb"] for m in downloaded)

        items = [
            ("当前模型", active_name),
            ("已下载", f"{len(downloaded)} 个 · 约 {total_mb} MB"),
            ("模型目录", str(self._config.models_dir)),
            ("配置文件", str(self._config.config_dir / "config.json")),
            ("快捷键", format_hotkey(self._config.get("hotkey", "alt+space"))),
        ]

        for i, (key, val) in enumerate(items):
            if i > 0:
                self._about_info_lay.addWidget(group_divider())
            if key in ("模型目录", "配置文件"):
                self._about_info_lay.addWidget(kv_row_elided(key, val))
            else:
                self._about_info_lay.addWidget(kv_row(key, val))

        self._refresh_about_hero_status()

    def _config_source_label(self, source: str | None = None) -> str:
        src = source or self._config.get("audio.input_source", INPUT_SOURCE_MICROPHONE)
        return {
            INPUT_SOURCE_MICROPHONE: "仅麦克风",
            INPUT_SOURCE_SYSTEM: "仅电脑播放",
            INPUT_SOURCE_MIXED: "混合音频",
        }.get(src, "仅麦克风")

    def _config_trigger_label(self, mode: str | None = None) -> str:
        m = mode or self._config.get("audio.trigger_mode", TRIGGER_MODE_CONTINUOUS)
        return "持续转写" if m == TRIGGER_MODE_CONTINUOUS else "按住录音"

    def _active_model_name(self) -> str:
        from voiceink.speech_recognizer import get_model_info
        active_id = self._config.get("stt.model_id", "")
        info = get_model_info(active_id) if active_id else None
        return info["name"] if info else "未选择"

    def _refresh_general_hero_status(self) -> None:
        if not hasattr(self, "_general_header"):
            return
        # General page uses a static reference header; status lives in sidebar.

    def _refresh_model_hero_status(self) -> None:
        if not hasattr(self, "_model_hero"):
            return
        from voiceink.speech_recognizer import get_model_info, is_model_downloaded

        active_id = self._config.get("stt.model_id", "")
        info = get_model_info(active_id) if active_id else None
        if info and is_model_downloaded(active_id):
            self._model_hero.set_subtitle(
                f"{info['name']} · {info['size_mb']} MB · {info['languages']}"
            )
            self._model_hero.set_tags([])
        else:
            self._model_hero.set_subtitle("尚未下载或未启用模型")
            self._model_hero.set_tags([])

    def _refresh_polish_hero_status(self) -> None:
        if not hasattr(self, "_polish_hero"):
            return
        enabled = self._config.get("llm.enabled", False)
        if hasattr(self, "_llm_enable_row"):
            enabled = self._llm_enable_row.isChecked()
        if enabled:
            model = self._config.get("llm.model_name", "") or "未配置"
            self._polish_hero.set_inline_status(f"已开启 · {model}")
            self._polish_hero.set_subtitle("")
        else:
            self._polish_hero.set_inline_status("已关闭")
            self._polish_hero.set_subtitle("")

    def _refresh_about_hero_status(self) -> None:
        if not hasattr(self, "_about_hero"):
            return
        self._about_hero.set_tags([])
        self._about_hero.set_subtitle("")
        if hasattr(self, "_about_usage_tip"):
            hotkey = format_hotkey(self._config.get("hotkey", "alt+space"))
            if self._config.get("audio.trigger_mode") == TRIGGER_MODE_CONTINUOUS:
                tip = (
                    f"持续转写：按住 {hotkey} 开始监听，停顿后自动出字；"
                    f"Esc 或浮窗 × 结束"
                )
            else:
                tip = f"按住 {hotkey} 说话，松开后识别并粘贴"
            labels = self._about_usage_tip.findChildren(QLabel)
            if labels:
                labels[0].setText(tip)

    def _refresh_sidebar_status(self) -> None:
        if not hasattr(self, "_sidebar"):
            return
        llm_on = self._config.get("llm.enabled", False)
        if hasattr(self, "_llm_enable_row"):
            llm_on = self._llm_enable_row.isChecked()
        llm = "润色已开启" if llm_on else "润色已关闭"
        model = elide_middle(self._active_model_name(), 20)
        self._sidebar.set_status_line(
            f"{self._runtime_status_hint} · {model}",
            llm,
        )

    def _refresh_all_heroes(self) -> None:
        self._refresh_general_hero_status()
        self._refresh_model_hero_status()
        self._refresh_polish_hero_status()
        self._refresh_about_hero_status()
        self._refresh_sidebar_status()

    # ── Shared ─────────────────────────────────────────

    @staticmethod
    def _add_sep(layout: QVBoxLayout):
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background: {_BAR_OFF};")
        layout.addWidget(s)

    # ── Load / Save ────────────────────────────────────

    def _selected_input_source(self) -> str:
        if self._src_sys_rb.isChecked():
            return INPUT_SOURCE_SYSTEM
        if self._src_mixed_rb.isChecked():
            return INPUT_SOURCE_MIXED
        return INPUT_SOURCE_MICROPHONE

    def _selected_trigger_mode(self) -> str:
        if self._trigger_hotkey_rb.isChecked():
            return TRIGGER_MODE_HOTKEY
        return TRIGGER_MODE_CONTINUOUS

    def _sync_source_device_widgets(self):
        src = self._selected_input_source()
        mic_on = src in (INPUT_SOURCE_MICROPHONE, INPUT_SOURCE_MIXED)
        sys_on = src in (INPUT_SOURCE_SYSTEM, INPUT_SOURCE_MIXED)
        self._mic_device_combo.setEnabled(mic_on)
        self._system_device_combo.setEnabled(sys_on)
        if hasattr(self, "_mixed_audio_callout"):
            self._mixed_audio_callout.setVisible(src == INPUT_SOURCE_MIXED)

    def _apply_input_source_radios(self, source: str):
        if source == INPUT_SOURCE_SYSTEM:
            self._src_sys_rb.setChecked(True)
        elif source == INPUT_SOURCE_MIXED:
            self._src_mixed_rb.setChecked(True)
        else:
            self._src_mic_rb.setChecked(True)
        self._sync_source_device_widgets()

    def _apply_trigger_mode_radios(self, mode: str):
        if mode == TRIGGER_MODE_HOTKEY:
            self._trigger_hotkey_rb.setChecked(True)
        else:
            self._trigger_continuous_rb.setChecked(True)

    def _load_settings(self):
        self._loading = True
        self._hotkey_edit.set_value(self._config.get("hotkey", "alt+space"))
        self._auto_start_row.setChecked(self._config.get("auto_start", False))
        self._sound_row.setChecked(self._config.get("sound_enabled", True))
        self._history_enabled_row.setChecked(self._config.get("history.enabled", True))
        self._history_retention_days_spin.setValue(
            int(self._config.get("history.retention_days", 90))
        )
        self._history_max_entries_spin.setValue(
            int(self._config.get("history.max_entries", 5000))
        )

        self._apply_input_source_radios(
            self._config.get("audio.input_source", INPUT_SOURCE_MICROPHONE)
        )
        self._apply_trigger_mode_radios(
            self._config.get("audio.trigger_mode", TRIGGER_MODE_CONTINUOUS)
        )

        self._refresh_audio_device_lists()
        mic_ok = self._set_combo_by_data(
            self._mic_device_combo, int(self._config.get("audio.mic_device_index", -1))
        )
        sys_ok = self._set_combo_by_data(
            self._system_device_combo, int(self._config.get("audio.system_device_index", -1))
        )
        if not mic_ok or not sys_ok:
            self._reset_audio_devices_to_auto()

        self._refresh_dir_label()
        self._rebuild_model_cards()

        llm_on = self._config.get("llm.enabled", False)
        self._llm_enable_row.setChecked(llm_on)
        self._llm_container.setVisible(llm_on)
        self._llm_preview_card.setVisible(not llm_on)
        if hasattr(self, "_llm_preview_divider"):
            self._llm_preview_divider.setVisible(not llm_on)
        self._llm_url_edit.setText(self._config.get("llm.api_url", ""))
        self._llm_key_edit.setText(self._config.get("llm.api_key", ""))
        self._llm_model_edit.setText(self._config.get("llm.model_name", ""))
        self._llm_prompt_edit.setPlainText(self._config.get("llm.prompt", ""))

        self._refresh_about_info()
        self._refresh_all_heroes()
        self._loading = False

    def _set_combo_by_data(self, combo: QComboBox, value: int) -> bool:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return True
        if combo.count() > 0:
            combo.setCurrentIndex(0)
        return False

    def _reset_audio_devices_to_auto(self):
        self._set_combo_by_data(self._mic_device_combo, -1)
        self._set_combo_by_data(self._system_device_combo, -1)
        self._mic_test_status.setText("已恢复为「自动选择」，请再点「测试声音」。")

    def _refresh_audio_device_lists(self):
        mic_sel = self._mic_device_combo.currentData() if self._mic_device_combo.count() else -1
        sys_sel = self._system_device_combo.currentData() if self._system_device_combo.count() else -1

        self._mic_device_combo.clear()
        self._mic_device_combo.addItem("自动选择", -1)
        try:
            for dev in list_microphone_devices():
                self._mic_device_combo.addItem(dev.label, dev.index)
        except Exception as e:
            self._mic_device_combo.addItem(f"枚举失败: {e}", -1)

        self._system_device_combo.clear()
        self._system_device_combo.addItem("自动选择", -1)
        try:
            for dev in list_system_capture_devices_for_settings():
                self._system_device_combo.addItem(dev.label, dev.index)
        except Exception as e:
            self._system_device_combo.addItem(f"枚举失败: {e}", -1)

        if mic_sel is not None:
            self._set_combo_by_data(self._mic_device_combo, int(mic_sel))
        if sys_sel is not None:
            self._set_combo_by_data(self._system_device_combo, int(sys_sel))

    def _toggle_advanced_audio(self, visible: bool):
        self._advanced_audio_panel.setVisible(visible)
        self._advanced_audio_btn.setText(
            "收起设备选择  ›" if visible else "手动选择音频设备  ›"
        )
        self._advanced_audio_btn.setChecked(visible)
        if visible and self._mic_device_combo.count() <= 1:
            self._refresh_audio_device_lists()

    def _current_audio_probe_config(self) -> tuple[str, int, int]:
        return (
            self._selected_input_source(),
            int(self._mic_device_combo.currentData() if self._mic_device_combo.currentData() is not None else -1),
            int(self._system_device_combo.currentData() if self._system_device_combo.currentData() is not None else -1),
        )

    def _disconnect_mic_probe_signals(self):
        try:
            self._mic_test_recorder.volume_changed.disconnect(self._on_mic_probe_volume)
        except TypeError:
            pass
        try:
            self._mic_test_recorder.error.disconnect(self._on_mic_probe_error)
        except TypeError:
            pass
        try:
            self._mic_test_recorder.warning.disconnect(self._on_mic_probe_warning)
        except TypeError:
            pass

    def _run_mic_probe(self):
        if self._mic_probe_active or self._mic_test_recorder.is_recording:
            return
        if self._mic_device_combo.count() <= 1 or self._system_device_combo.count() <= 1:
            self._refresh_audio_device_lists()
        src, mic_idx, sys_idx = self._current_audio_probe_config()
        if mic_idx >= 0 and self._mic_device_combo.findData(mic_idx) < 0:
            mic_idx = -1
        if sys_idx >= 0 and self._system_device_combo.findData(sys_idx) < 0:
            sys_idx = -1
        sys_idx = sanitize_system_device_index(sys_idx)
        if sys_idx < 0:
            self._set_combo_by_data(self._system_device_combo, -1)
        self._mic_test_recorder.configure(
            input_source=src,
            mic_device_index=mic_idx,
            system_device_index=sys_idx,
        )
        self._mic_probe_active = True
        self._mic_probe_max = 0.0
        self._mic_test_btn.setEnabled(False)
        self._mic_test_status.setText("监听中…请说话并播放一段电脑声音")
        self._mic_test_recorder.volume_changed.connect(self._on_mic_probe_volume)
        self._mic_test_recorder.error.connect(self._on_mic_probe_error)
        self._mic_test_recorder.warning.connect(self._on_mic_probe_warning)
        self._mic_test_recorder.start()
        QTimer.singleShot(2000, self._finish_mic_probe)

    def _on_mic_probe_volume(self, volume: float):
        self._mic_probe_max = max(self._mic_probe_max, float(volume))

    def _on_mic_probe_error(self, msg: str):
        if not self._mic_probe_active:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.cancel()
        self._mic_test_btn.setEnabled(True)
        self._mic_test_status.setText("")
        QMessageBox.warning(self, "音频设备", msg)

    def _on_mic_probe_warning(self, msg: str):
        if not self._mic_probe_active:
            return
        self._mic_test_status.setText(msg)

    def _finish_mic_probe(self):
        if not self._mic_probe_active:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.stop()
        self._mic_test_btn.setEnabled(True)
        threshold = 0.0015
        peak = self._mic_probe_max
        warn = self._mic_test_recorder.last_start_warning
        if peak >= threshold:
            base = f"已检测到声音（峰值约 {peak:.4f}），可以正常使用。"
            self._mic_test_status.setText(f"{base} {warn}".strip() if warn else base)
        else:
            self._mic_test_status.setText(
                f"几乎无输入（峰值约 {peak:.4f}）。请点「恢复自动选择」后再测；仍失败再展开下方改设备。"
            )

    def _cancel_mic_probe_if_active(self):
        if not self._mic_probe_active and not self._mic_test_recorder.is_recording:
            return
        self._mic_probe_active = False
        self._disconnect_mic_probe_signals()
        if self._mic_test_recorder.is_recording:
            self._mic_test_recorder.cancel()
        self._mic_test_btn.setEnabled(True)

    # ── Instant apply ──────────────────────────────────

    def _confirm_discard_pending(self) -> bool:
        if self._pending_segment_count is None:
            return True
        pending = int(self._pending_segment_count())
        if pending <= 0:
            return True
        reply = QMessageBox.question(
            self,
            "待识别语音",
            f"仍有 {pending} 段语音等待识别，应用此更改将丢弃这些片段。\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _revert_input_source_radios(self):
        self._loading = True
        self._apply_input_source_radios(
            self._config.get("audio.input_source", INPUT_SOURCE_MICROPHONE)
        )
        self._loading = False

    def _revert_trigger_mode_radios(self):
        self._loading = True
        self._apply_trigger_mode_radios(
            self._config.get("audio.trigger_mode", TRIGGER_MODE_CONTINUOUS)
        )
        self._loading = False

    def _persist_runtime_settings(self):
        self._config.set("audio.input_source", self._selected_input_source())
        self._config.set("audio.trigger_mode", self._selected_trigger_mode())
        self._config.set(
            "audio.mic_device_index",
            int(self._mic_device_combo.currentData() or -1),
        )
        sys_idx = sanitize_system_device_index(
            int(self._system_device_combo.currentData() or -1)
        )
        self._config.set("audio.system_device_index", sys_idx)
        if sys_idx < 0:
            self._set_combo_by_data(self._system_device_combo, -1)
        self._config.save_immediate()
        self.settings_changed.emit()
        self._refresh_about_info()
        self._refresh_all_heroes()

    def _on_auto_start_toggled(self, checked: bool):
        if self._loading:
            return
        self._config.set("auto_start", checked)
        self.auto_start_changed.emit(checked)

    def _on_sound_toggled(self, checked: bool):
        if self._loading:
            return
        self._config.set("sound_enabled", checked)
        self.sound_enabled_changed.emit(checked)

    def _on_history_enabled_toggled(self, checked: bool):
        if self._loading:
            return
        self._config.set("history.enabled", checked)

    def _on_history_limits_changed(self, _value: int):
        if self._loading:
            return
        self._config.set("history.retention_days", self._history_retention_days_spin.value())
        self._config.set("history.max_entries", self._history_max_entries_spin.value())

    def _apply_hotkey_setting(self, hotkey: str):
        if self._loading or not hotkey:
            return
        parts = hotkey.lower().split("+")
        has_modifier = any(
            p.strip() in ("ctrl", "alt", "shift", "win", "cmd") for p in parts
        )
        if not has_modifier:
            QMessageBox.warning(self, "提示", "快捷键必须包含至少一个修饰键（Ctrl/Alt/Shift）。")
            self._loading = True
            self._hotkey_edit.set_value(self._config.get("hotkey", "alt+space"))
            self._loading = False
            return
        old = self._config.get("hotkey")
        self._config.set("hotkey", hotkey)
        if hotkey != old:
            self.hotkey_updated.emit(hotkey)
        self._refresh_about_info()
        self._refresh_all_heroes()

    def _on_input_source_radio_toggled(self, checked: bool):
        if not checked or self._loading:
            return
        if not self._confirm_discard_pending():
            self._revert_input_source_radios()
            return
        self._persist_runtime_settings()

    def _on_trigger_mode_radio_toggled(self, checked: bool):
        if not checked or self._loading:
            return
        if not self._confirm_discard_pending():
            self._revert_trigger_mode_radios()
            return
        self._persist_runtime_settings()

    def _on_audio_device_changed(self, _index: int):
        if self._loading:
            return
        if not self._confirm_discard_pending():
            self._loading = True
            self._set_combo_by_data(
                self._mic_device_combo,
                int(self._config.get("audio.mic_device_index", -1)),
            )
            self._set_combo_by_data(
                self._system_device_combo,
                int(self._config.get("audio.system_device_index", -1)),
            )
            self._loading = False
            return
        self._persist_runtime_settings()

    def _flush_llm_fields(self):
        if self._loading:
            return
        llm_enabled = self._llm_enable_row.isChecked()
        llm_url = self._llm_url_edit.text().strip()
        if llm_enabled and llm_url and not llm_url.startswith("https://"):
            QMessageBox.warning(self, "提示", "LLM 接口地址必须使用 HTTPS。")
            self._loading = True
            self._llm_url_edit.setText(self._config.get("llm.api_url", ""))
            self._loading = False
            return
        self._config.set("llm.enabled", llm_enabled)
        self._config.set("llm.api_url", llm_url)
        self._config.set("llm.api_key", self._llm_key_edit.text().strip())
        self._config.set("llm.model_name", self._llm_model_edit.text().strip())
        self._config.set("llm.prompt", self._llm_prompt_edit.toPlainText().strip())

    def _on_done(self):
        self._cancel_mic_probe_if_active()
        self._flush_llm_fields()
        self.close()

    # ── LLM Test ───────────────────────────────────────

    def _test_llm(self):
        url = self._llm_url_edit.text().strip()
        key = self._llm_key_edit.text().strip()
        model = self._llm_model_edit.text().strip()
        if not all([url, key, model]):
            QMessageBox.warning(self, "提示", "请填写完整的接口信息。")
            return

        class _W(QThread):
            def __init__(self, u, k, m):
                super().__init__()
                self.u, self.k, self.m = u, k, m
                self.ok, self.msg = False, ""

            def run(self):
                from voiceink.text_polisher import TextPolisher
                self.ok, self.msg = TextPolisher.test_connection(self.u, self.k, self.m)

        self._llm_test_worker = _W(url, key, model)
        self._llm_test_worker.finished.connect(
            lambda: self._on_test_done(self._llm_test_worker, self._llm_test_btn)
        )
        self._llm_test_btn.setEnabled(False)
        self._llm_test_btn.setText("测试中...")
        self._llm_test_worker.start()

    def _on_test_done(self, w, btn):
        btn.setEnabled(True)
        btn.setText("测试连接")
        if w.ok:
            QMessageBox.information(self, "成功", "连接正常，可以使用。")
        else:
            QMessageBox.warning(self, "失败", w.msg)

    # ── Cleanup ────────────────────────────────────────

    def reload_settings(self) -> None:
        """Reload form fields from the current config."""
        self._load_settings()

    def cancel_hotkey_capture(self) -> None:
        """Stop in-progress shortcut capture and resume global hotkey listening."""
        self._hotkey_edit.cancel_capture_if_active()

    def cancel_all_downloads(self):
        """Wait for any in-progress download workers to finish."""
        for model_id, worker in list(self._dl_workers.items()):
            if hasattr(worker, 'isRunning') and worker.isRunning():
                worker.wait(3000)
        self._dl_workers.clear()

    def closeEvent(self, event):
        self._cancel_mic_probe_if_active()
        self.cancel_hotkey_capture()
        self._flush_llm_fields()
        self.cancel_all_downloads()
        super().closeEvent(event)
