import logging
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QMessageBox, QFrame,
    QStackedWidget,
    QFileDialog,
    QSizePolicy, QSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer

log = logging.getLogger("VoiceInk")

from voiceink.config import (
    Config,
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
    sanitize_system_device_index,
)

from voiceink.ui.settings_components import (
    SettingsPage,
    elide_middle,
    empty_state,
    group_divider,
    kv_row,
    kv_row_elided,
    settings_group,
)
from voiceink.ui.settings_pages import (
    build_about_page,
    build_general_page,
    build_model_page,
    build_polish_page,
)
from voiceink.ui.model_card import ModelCard, RATING_TOOLTIP, format_model_ratings
from voiceink.ui import design_tokens as _tok
from voiceink.ui import settings_styles as _settings_styles
from voiceink.ui.theme import normalize_theme_mode

# Non-color layout constants (theme-independent).
_CONTROL_NUMERIC_WIDTH = _tok.CONTROL_NUMERIC_WIDTH
# Shared width so 显示 / 测试连接 / 恢复默认 share one right-edge column.
_LLM_ACTION_BTN_WIDTH = 88

# ── Settings Window ──────────────────────────────────────────────


class SettingsWindow(QWidget):
    hotkey_updated = pyqtSignal(str)
    settings_changed = pyqtSignal()
    auto_start_changed = pyqtSignal(bool)
    sound_enabled_changed = pyqtSignal(bool)
    models_changed = pyqtSignal()
    theme_changed = pyqtSignal(str)
    hotkey_capture_started = pyqtSignal()
    hotkey_capture_ended = pyqtSignal()
    closed = pyqtSignal()
    finished = pyqtSignal(int)

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
        # Paint from the active axis (construct-time helpers may use cached fragments).
        self.reapply_theme()

    def _setup_window(self):
        self.setWindowTitle("设置")
        self.setStyleSheet(_settings_styles.WINDOW_CSS)

    def reapply_theme(self) -> None:
        """Refresh dialog chrome after design tokens were activated."""
        from voiceink.ui import design_tokens as tok
        from voiceink.ui.settings_components import (
            paint_device_selection_link,
            reapply_subtree,
        )

        from voiceink.ui.island_chrome import island_container_css

        self.setStyleSheet(_settings_styles.WINDOW_CSS)
        if hasattr(self, "_sheet"):
            self._sheet.setStyleSheet(island_container_css())
        if hasattr(self, "_island_nav"):
            for btn in self._island_nav:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; color: {tok.TEXT_SEC};"
                    f" border: none; border-radius: 14px; padding: 0 12px; }}"
                    f"QPushButton:checked {{ background: {tok.CHIP_BG}; color: {tok.TEXT}; }}"
                )
        if hasattr(self, "_island_title"):
            self._island_title.setStyleSheet(
                f"color: {tok.TEXT}; font-size: {_tok.TYPE_TITLE}px; font-weight: 600;"
                f" background: transparent;"
            )
        if hasattr(self, "_close_btn"):
            self._close_btn.setStyleSheet(
                f"QPushButton {{ background: {tok.CHIP_BG}; color: {tok.TEXT};"
                f" border: none; border-radius: 14px; font-size: {tok.TYPE_BODY_SM}px; }}"
                f"QPushButton:hover {{ background: {tok.CHIP_BG_HOVER}; }}"
            )
        if hasattr(self, "_content_wrap"):
            self._content_wrap.setStyleSheet("background: transparent;")
        if hasattr(self, "_pages_host"):
            self._pages_host.setStyleSheet("background: transparent;")
        if hasattr(self, "_pages"):
            self._pages.setStyleSheet("background: transparent;")
        if hasattr(self, "_hotkey_hint"):
            self._hotkey_hint.setStyleSheet(
                f"color: {tok.TEXT_DIM}; font-size: {_tok.TYPE_FOOTNOTE}px; line-height: 1.4;"
                f" background: transparent; padding: 0 16px 12px 16px;"
            )
        if hasattr(self, "_advanced_audio_btn"):
            paint_device_selection_link(self._advanced_audio_btn)
        if hasattr(self, "_storage_summary_label"):
            self._storage_summary_label.setStyleSheet(
                f"color: {tok.TEXT_SEC}; font-size: {_tok.TYPE_BODY_SM}px; background: transparent;"
            )

        reapply_subtree(self)
        if hasattr(self, "_model_hero_layout"):
            self._refresh_active_model_hero()
        if hasattr(self, "_llm_prompt_edit"):
            self._paint_llm_prompt_edit()
        if hasattr(self, "_about_version_label"):
            self._about_version_label.setStyleSheet(
                f"color: {tok.TEXT_SEC}; font-size: {_tok.TYPE_CAPTION}px; font-weight: 600;"
                f" background: {tok.SURFACE_PEARL}; border: 1px solid {tok.HAIRLINE};"
                f" border-radius: {tok.RADIUS_PILL}px; padding: 3px 10px;"
            )
        if hasattr(self, "_llm_test_status"):
            self._llm_test_status.setStyleSheet(
                f"color: {tok.TEXT_SEC}; font-size: {tok.TYPE_FOOTNOTE}px;"
                f" background: transparent; padding: 0 16px 12px 16px;"
            )
        if hasattr(self, "_about_paths_toggle"):
            self._about_paths_toggle.setStyleSheet(
                f"QPushButton#aboutPathsToggle {{"
                f" color: {tok.TEXT_SEC}; background: transparent; border: none;"
                f" font-size: {tok.TYPE_BODY_SM}px; font-weight: 500;"
                f" text-align: left; padding: 10px 16px;"
                f"}}"
                f"QPushButton#aboutPathsToggle:hover {{ color: {tok.TEXT}; }}"
            )

    def show_page(self, index: int) -> None:
        self._pages.setCurrentIndex(index)

    def _on_nav_changed(self, row: int):
        self.show_page(row)

    def _open_about_from_general(self) -> None:
        self.show_page(3)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.parent() is None:
            self.closed.emit()
            self.finished.emit(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # The content column starts directly with the active page. Settings are
        # auto-saved, so persistent action chrome would only consume space.
        content_wrap = QWidget()
        self._content_wrap = content_wrap
        content_wrap.setStyleSheet("background: transparent;")
        content_lay = QVBoxLayout(content_wrap)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        pages_host = QWidget()
        self._pages_host = pages_host
        pages_host.setStyleSheet("background: transparent;")
        pages_lay = QHBoxLayout(pages_host)
        # Top/bottom inset so section titles (e.g. 偏好) are not flush-clipped
        # against the content column edge when scrolled.
        pages_lay.setContentsMargins(12, 4, 12, 12)
        pages_lay.setSpacing(0)

        self._pages = QStackedWidget()
        self._pages.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        self._pages.setStyleSheet("background: transparent;")
        self._pages.addWidget(build_general_page(self))
        self._pages.addWidget(build_model_page(self))
        self._pages.addWidget(build_polish_page(self))
        self._pages.addWidget(build_about_page(self))
        for i in range(self._pages.count()):
            page = self._pages.widget(i)
            if isinstance(page, SettingsPage):
                page.set_compact(True)
                page.set_spacing(16)
        pages_lay.addWidget(self._pages, 1)
        content_lay.addWidget(pages_host, 1)
        root.addWidget(content_wrap, 1)

    # ── Page: General ──────────────────────────────────

    def set_runtime_status(self, hint: str) -> None:
        self._runtime_status_hint = hint.strip() or "就绪"

    def _configure_numeric_spin(self, spin: QSpinBox) -> None:
        """Shared metrics for flat themed QSpinBox steppers."""
        spin.setFixedWidth(_CONTROL_NUMERIC_WIDTH)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

    def _set_mic_test_status(self, text: str) -> None:
        if hasattr(self, "_mic_test_status"):
            self._mic_test_status.setText(text)

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
        title.setProperty("viRole", "engineHeroTitle")
        title.setStyleSheet(
            f"color: {_tok.TEXT}; font-family: {_tok.FONT_DISPLAY}; font-size: {_tok.TYPE_HERO}px;"
            f" font-weight: 600; background: transparent;"
        )
        head.addWidget(title)
        badge = QLabel("当前")
        badge.setProperty("viRole", "engineHeroBadge")
        badge.setStyleSheet(
            f"background: {_tok.SURFACE_PEARL}; color: {_tok.TEXT_SEC};"
            f" border-radius: {_tok.RADIUS_PILL}px; padding: 3px 10px;"
            f" font-size: {_tok.TYPE_CAPTION}px; font-weight: 600;"
        )
        head.addWidget(badge)
        head.addStretch()
        size = QLabel(f"{info['size_mb']} MB")
        size.setProperty("viRole", "engineHeroSize")
        size.setStyleSheet(
            f"color: {_tok.TEXT_DIM}; font-size: {_tok.TYPE_FOOTNOTE}px; background: transparent;"
        )
        head.addWidget(size)
        lay.addLayout(head)

        desc = QLabel(info["description"])
        desc.setProperty("viRole", "engineHeroDesc")
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {_tok.TEXT_SEC}; font-size: {_tok.TYPE_BODY_SM}px; background: transparent;"
        )
        lay.addWidget(desc)

        meta = QLabel(
            f"{info['languages']} · "
            f"{format_model_ratings(info['accuracy'], info['speed'])}"
        )
        meta.setProperty("viRole", "engineHeroMeta")
        meta.setStyleSheet(
            f"color: {_tok.TEXT_DIM}; font-size: {_tok.TYPE_FOOTNOTE}px; background: transparent;"
        )
        meta.setToolTip(RATING_TOOLTIP)
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
                    f"color: {_tok.TEXT_SEC}; font-size: {_tok.TYPE_FOOTNOTE}px; font-weight: 600;"
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
        QMessageBox.information(
            self,
            "完成",
            f"{name} 已下载，正在载入内存（约需数十秒）。载入完成前请勿开始录音。",
        )

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

    def _on_llm_enable_toggled(self, enabled: bool):
        # Keep the enable row visually stable while the tall config block
        # mounts/unmounts (avoids scroll jumping the switch under the cursor).
        page = self._polish_scroll_page()
        anchor_y = 0
        scroll_before = 0
        if page is not None and page.widget() is not None:
            anchor_y = self._llm_enable_row.mapTo(page.widget(), self._llm_enable_row.rect().topLeft()).y()
            scroll_before = page.verticalScrollBar().value()

        self._llm_container.setVisible(enabled)
        self._llm_preview_card.setVisible(True)
        if hasattr(self, "_llm_preview_divider"):
            self._llm_preview_divider.setVisible(True)

        if page is not None and page.widget() is not None:
            def _restore() -> None:
                if page.widget() is None:
                    return
                new_y = self._llm_enable_row.mapTo(
                    page.widget(), self._llm_enable_row.rect().topLeft()
                ).y()
                page.verticalScrollBar().setValue(
                    max(0, scroll_before + (new_y - anchor_y))
                )
                page._sync_scroll_gutter(
                    page.verticalScrollBar().minimum(),
                    page.verticalScrollBar().maximum(),
                )

            QTimer.singleShot(0, _restore)

        if self._loading:
            return
        self._config.set("llm.enabled", enabled)
        self._flush_llm_fields()

    def _polish_scroll_page(self):
        w = self._llm_enable_row.parentWidget()
        while w is not None:
            if isinstance(w, SettingsPage):
                return w
            w = w.parentWidget()
        return None

    def _toggle_llm_key_visibility(self, visible: bool) -> None:
        self._llm_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self._llm_key_toggle.setText("隐藏" if visible else "显示")

    def _style_llm_action_btn(self, btn: QPushButton) -> None:
        """Shared metrics so polish actions share one right-edge column."""
        btn.setProperty("viBtn", "ghostSm")
        btn.setFixedWidth(_LLM_ACTION_BTN_WIDTH)
        btn.setMinimumHeight(32)
        btn.setStyleSheet(_settings_styles.BTN_GHOST_SM)

    def _paint_llm_prompt_edit(self) -> None:
        self._llm_prompt_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_tok.INPUT_BG}; color: {_tok.TEXT};
                border: 1px solid {_tok.HAIRLINE}; border-radius: {_tok.RADIUS_MD}px;
                padding: 10px 12px; font-size: {_tok.TYPE_BODY_SM}px; font-family: {_tok.FONT};
            }}
            QTextEdit:focus {{
                border: 2px solid {_tok.ACCENT_FOCUS};
                padding: 9px 11px;
            }}
        """)

    def _reset_prompt(self):
        from voiceink.text_polisher import POLISH_PROMPT
        self._llm_prompt_edit.setPlainText(POLISH_PROMPT)
        self._flush_llm_fields()

    # ── Page: About ────────────────────────────────────

    def _refresh_about_info(self):
        if not hasattr(self, "_about_runtime_lay"):
            return

        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded, get_model_info

        active_id = self._config.get("stt.model_id", "")
        ai = get_model_info(active_id)
        active_name = ai["name"] if ai else "未选择"

        downloaded = [m for m in MODEL_REGISTRY if is_model_downloaded(m["id"])]
        total_mb = sum(m["size_mb"] for m in downloaded)

        while self._about_runtime_lay.count():
            item = self._about_runtime_lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        runtime_items = [
            ("当前模型", active_name),
            ("快捷键", format_hotkey(self._config.get("hotkey", "ctrl+space"))),
            (
                "润色",
                "已开启"
                if self._config.get("llm.enabled", False)
                else "已关闭",
            ),
        ]
        for key, val in runtime_items:
            self._about_runtime_lay.addWidget(group_divider())
            self._about_runtime_lay.addWidget(kv_row(key, val))

        while self._about_paths_lay.count():
            item = self._about_paths_lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        path_items = [
            ("已下载", f"{len(downloaded)} 个 · 约 {total_mb} MB"),
            ("模型目录", str(self._config.models_dir)),
            ("配置文件", str(self._config.config_dir / "config.json")),
        ]
        for key, val in path_items:
            self._about_paths_lay.addWidget(group_divider())
            if key in ("模型目录", "配置文件"):
                self._about_paths_lay.addWidget(kv_row_elided(key, val, max_len=42))
            else:
                self._about_paths_lay.addWidget(kv_row(key, val))

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

    def _refresh_about_hero_status(self) -> None:
        if not hasattr(self, "_about_usage_tip"):
            return
        hotkey = format_hotkey(self._config.get("hotkey", "ctrl+space"))
        if self._config.get("audio.trigger_mode") == TRIGGER_MODE_CONTINUOUS:
            tip = (
                f"持续转写：按住 {hotkey} 开始监听，停顿后自动出字；"
                f"Esc 或听写条「结束」结束"
            )
        else:
            tip = f"按住 {hotkey} 说话，松开后识别并粘贴"
        labels = self._about_usage_tip.findChildren(QLabel)
        if labels:
            labels[0].setText(tip)

    # ── Shared ─────────────────────────────────────────

    @staticmethod
    def _add_sep(layout: QVBoxLayout):
        s = QFrame()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background: {_tok.BAR_OFF};")
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
        mixed = self._src_mixed_rb.isChecked()
        self._mixed_audio_callout.setVisible(mixed)
        if hasattr(self, "_mixed_audio_callout_wrap"):
            self._mixed_audio_callout_wrap.setVisible(mixed)

    def _set_history_limit_rows_visible(self, visible: bool) -> None:
        self._history_retention_row.setVisible(visible)
        self._history_max_entries_row.setVisible(visible)

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
        self._hotkey_edit.set_value(self._config.get("hotkey", "ctrl+space"))
        self._auto_start_row.setChecked(self._config.get("auto_start", False))
        self._sound_row.setChecked(self._config.get("sound_enabled", True))
        self._restore_clipboard_row.setChecked(
            self._config.get("output.restore_clipboard", False)
        )
        self._refresh_hotkey_hint()
        self._history_enabled_row.setChecked(self._config.get("history.enabled", True))
        self._history_retention_days_spin.setValue(
            int(self._config.get("history.retention_days", 90))
        )
        self._history_max_entries_spin.setValue(
            int(self._config.get("history.max_entries", 5000))
        )
        self._set_history_limit_rows_visible(self._history_enabled_row.isChecked())

        theme_mode = normalize_theme_mode(
            self._config.get("appearance.theme_mode", "system")
        )
        idx = self._theme_combo.findData(theme_mode)
        if idx < 0:
            idx = self._theme_combo.findData("system")
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(max(0, idx))
        self._theme_combo.blockSignals(False)

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
        self._llm_preview_card.setVisible(True)
        if hasattr(self, "_llm_preview_divider"):
            self._llm_preview_divider.setVisible(True)
        self._llm_url_edit.setText(self._config.get("llm.api_url", ""))
        self._llm_key_edit.setText(self._config.get("llm.api_key", ""))
        self._llm_model_edit.setText(self._config.get("llm.model_name", ""))
        self._llm_prompt_edit.setPlainText(self._config.get("llm.prompt", ""))
        self._llm_prompt_edit.setEnabled(True)

        self._refresh_about_info()
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
        self._set_mic_test_status("已恢复为「自动选择」，请再点「测试声音」。")

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
            "收起手动设备" if visible else "手动选择音频设备"
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
        self._set_mic_test_status("监听中…请说话并播放一段电脑声音")
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
        self._set_mic_test_status("")
        QMessageBox.warning(self, "音频设备", msg)

    def _on_mic_probe_warning(self, msg: str):
        if not self._mic_probe_active:
            return
        self._set_mic_test_status(msg)

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
            base = "已检测到声音，可以正常使用。"
            self._set_mic_test_status(f"{base} {warn}".strip() if warn else base)
        else:
            self._set_mic_test_status(
                "几乎无输入。请点「恢复自动选择」后再测；仍失败再展开下方改设备。"
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
        self._refresh_hotkey_hint()
        self._refresh_about_info()

    def _refresh_hotkey_hint(self) -> None:
        if not hasattr(self, "_hotkey_hint"):
            return
        self._hotkey_hint.setText(
            "持续模式按住约 0.30 秒开始，松开不结束；Esc 或结束可结束整场。"
        )

    def _on_theme_mode_changed(self, _index: int = 0):
        if self._loading:
            return
        mode = normalize_theme_mode(self._theme_combo.currentData())
        self._config.set("appearance.theme_mode", mode)
        self._config.save_immediate()
        self.theme_changed.emit(mode)

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

    def _on_restore_clipboard_toggled(self, checked: bool):
        if self._loading:
            return
        self._config.set("output.restore_clipboard", checked)

    def _on_history_enabled_toggled(self, checked: bool):
        self._set_history_limit_rows_visible(checked)
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
            self._hotkey_edit.set_value(self._config.get("hotkey", "ctrl+space"))
            self._loading = False
            return
        old = self._config.get("hotkey")
        self._config.set("hotkey", hotkey)
        if hotkey != old:
            self.hotkey_updated.emit(hotkey)
        self._refresh_about_info()

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
        from voiceink.text_polisher import is_secure_or_local_url

        llm_enabled = self._llm_enable_row.isChecked()
        llm_url = self._llm_url_edit.text().strip()
        if llm_enabled and llm_url and not is_secure_or_local_url(llm_url):
            QMessageBox.warning(
                self,
                "提示",
                "远程 API 须使用 HTTPS；本地 localhost / 127.0.0.1 可用 HTTP。",
            )
            self._loading = True
            self._llm_url_edit.setText(self._config.get("llm.api_url", ""))
            self._loading = False
            return
        self._config.set("llm.enabled", llm_enabled)
        self._config.set("llm.api_url", llm_url)
        self._config.set("llm.api_key", self._llm_key_edit.text().strip())
        self._config.set("llm.model_name", self._llm_model_edit.text().strip())
        self._config.set("llm.prompt", self._llm_prompt_edit.toPlainText().strip())
        self._config.set("llm.mode", "polish")

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
            self._llm_test_status.setText("请填写完整的接口信息。")
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
            self._llm_test_status.setText("连接正常，可以使用。")
        else:
            self._llm_test_status.setText(w.msg)

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
