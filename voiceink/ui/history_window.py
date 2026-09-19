"""History browser window and Markdown export helpers."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from voiceink.history_store import SegmentRecord, SessionSummary
from voiceink.ui import settings_styles as _settings_styles


def _format_dt(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def _day_label(ms: int) -> str:
    day = datetime.fromtimestamp(ms / 1000).date()
    today = datetime.now().date()
    delta = (today - day).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "昨天"
    return day.strftime("%Y-%m-%d")


def _filename_dt(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y%m%d-%H%M%S")


def _effective_text(segment: SegmentRecord) -> str:
    return segment.polished_text or segment.raw_text


def _yaml_value(value: object) -> str:
    return str(value).replace("\n", " ").strip()


def _segments_in_order(segments: list[SegmentRecord]) -> list[SegmentRecord]:
    return sorted(segments, key=lambda s: s.seq)


def _session_duration_ms(segments: list[SegmentRecord]) -> int:
    return sum(max(0, int(s.duration_ms)) for s in segments)


def _session_model(segments: list[SegmentRecord]) -> str:
    return next((s.model for s in segments if s.model), "")


def _session_body(segments: list[SegmentRecord]) -> str:
    texts = [_effective_text(s).strip() for s in _segments_in_order(segments)]
    return "\n\n".join(t for t in texts if t)


_SOURCE_CHIP = {
    "mic": "麦克风",
    "microphone": "麦克风",
    "system": "电脑播放",
    "mixed": "混合",
    "file": "文件转写",
}

_TRIGGER_CHIP = {
    "continuous": "持续转写",
    "hotkey": "按住录音",
    "file_import": "导入文件",
}


def _source_chip_text(source: str | None) -> str:
    key = (source or "").strip()
    return _SOURCE_CHIP.get(key, key or "未知")


def _trigger_chip_text(mode: str | None) -> str:
    key = (mode or "").strip()
    return _TRIGGER_CHIP.get(key, key)


def _session_has_polished(segments: list[SegmentRecord]) -> bool:
    return any((s.polished_text or "").strip() for s in segments)


def _chip_qss() -> str:
    from voiceink.ui import design_tokens as tok

    return (
        f"color: {tok.TEXT_DIM}; font-size: {tok.TYPE_CAPTION}px;"
        f" background: {tok.SURFACE_PEARL}; border-radius: {tok.RADIUS_PILL}px;"
        f" padding: 2px 8px;"
    )


def suggest_single_export_filename(session: SessionSummary) -> str:
    return f"voiceink-{_filename_dt(session.created_at)}.md"


def suggest_batch_export_filename(*, now_ms: int | None = None) -> str:
    stamp = int(time.time() * 1000) if now_ms is None else now_ms
    return f"voiceink-export-{_filename_dt(stamp)}.md"


def build_single_session_markdown(
    session: SessionSummary,
    segments: list[SegmentRecord],
) -> str:
    frontmatter = [
        "---",
        f"created_at: {_yaml_value(_format_dt(session.created_at))}",
        f"source: {_yaml_value(session.source)}",
        f"target_app: {_yaml_value(session.target_app)}",
        f"duration_ms: {_session_duration_ms(segments)}",
        f"model: {_yaml_value(_session_model(segments))}",
        f"segment_count: {session.segment_count}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + _session_body(segments).rstrip() + "\n"


def build_batch_export_markdown(
    sessions: list[SessionSummary],
    segments_by_session: dict[str, list[SegmentRecord]],
) -> str:
    lines = [
        "---",
        f"exported_at: {_yaml_value(_format_dt(int(time.time() * 1000)))}",
        f"session_count: {len(sessions)}",
        "---",
        "",
    ]
    for session in sorted(sessions, key=lambda s: s.created_at):
        segments = segments_by_session.get(session.session_id, [])
        lines.extend(
            [
                f"## {_format_dt(session.created_at)} · {session.preview}",
                "",
                f"- source: {session.source}",
                f"- target_app: {session.target_app}",
                f"- duration_ms: {_session_duration_ms(segments)}",
                f"- model: {_session_model(segments)}",
                f"- segment_count: {session.segment_count}",
                "",
                _session_body(segments).rstrip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


class HistoryWindow(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self._store = store
        self._sessions_by_id: dict[str, SessionSummary] = {}
        self._pending_delete: list[SessionSummary] = []
        self._search_query = ""
        self._setup_window()
        self._setup_ui()
        self.refresh()
        self.reapply_theme()

    def _setup_window(self) -> None:
        from voiceink.ui.island_chrome import (
            ISLAND_SHEET_HEIGHT,
            ISLAND_SHEET_WIDTH,
            apply_island_sheet_flags,
        )

        self.setWindowTitle("历史")
        apply_island_sheet_flags(self)
        self.setMinimumSize(ISLAND_SHEET_WIDTH, 520)
        self.resize(ISLAND_SHEET_WIDTH, ISLAND_SHEET_HEIGHT)
        self.setStyleSheet(_settings_styles.WINDOW_CSS)

    def showEvent(self, event):
        from voiceink.ui.island_chrome import position_island

        super().showEvent(event)
        position_island(self, width=self.width())

    def reapply_theme(self) -> None:
        from voiceink.ui import settings_styles as ss

        from voiceink.ui.island_chrome import island_container_css

        self.setStyleSheet(ss.WINDOW_CSS)
        if hasattr(self, "_sheet"):
            self._sheet.setStyleSheet(island_container_css())
        self._paint_history_styles()

    def _paint_history_styles(self) -> None:
        """Apply construct-parity styles from the active token axis (also used by reapply)."""
        from voiceink.ui import design_tokens as tok
        from voiceink.ui import settings_styles as ss

        if hasattr(self, "_left_pane"):
            self._left_pane.setStyleSheet(f"""
                QWidget#historyLeftPane {{
                    background: transparent;
                    border: none;
                }}
            """)
        if hasattr(self, "_title_label"):
            self._title_label.setStyleSheet(
                f"font-family: {tok.FONT_DISPLAY}; font-size: {tok.TYPE_TITLE}px; font-weight: 600;"
                f" background: transparent; color: {tok.TEXT};"
            )
        if hasattr(self, "_right_pane"):
            self._right_pane.setStyleSheet(f"background: {tok.BG};")
        if hasattr(self, "_search_edit"):
            self._search_edit.setStyleSheet(f"""
                QLineEdit {{
                    background: {tok.SURFACE_PEARL};
                    color: {tok.TEXT};
                    border: 1px solid {tok.HAIRLINE};
                    border-radius: {tok.RADIUS_MD}px;
                    padding: 10px 14px;
                    font-size: {tok.TYPE_BODY_SM}px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {tok.ACCENT};
                    padding: 9px 13px;
                }}
            """)
        if hasattr(self, "_session_list"):
            self._session_list.setStyleSheet(f"""
                QListWidget {{
                    background: transparent;
                    color: transparent;
                    border: none;
                    padding: 0;
                    outline: none;
                }}
                QListWidget::item {{
                    color: transparent;
                    padding: 0;
                    border-radius: {tok.RADIUS_SM}px;
                    margin: 2px 0;
                }}
                QListWidget::item:selected {{
                    background: {tok.ROW_SELECTED};
                    border-left: 3px solid {tok.ACCENT};
                    color: transparent;
                }}
                QListWidget::item:hover:!selected {{
                    background: {tok.SURFACE_PEARL};
                }}
            """)
            chip_css = _chip_qss()
            preview_css = (
                f"color: {tok.TEXT}; font-size: {tok.TYPE_BODY_SM}px; background: transparent;"
            )
            time_css = (
                f"color: {tok.TEXT_DIM}; font-size: {tok.TYPE_CAPTION}px; background: transparent;"
            )
            day_css = (
                f"color: {tok.TEXT_DIM}; font-size: {tok.TYPE_CAPTION}px;"
                f" letter-spacing: 0.08em; background: transparent;"
            )
            for i in range(self._session_list.count()):
                row = self._session_list.itemWidget(self._session_list.item(i))
                if row is None:
                    continue
                for lab in row.findChildren(QLabel):
                    name = lab.objectName()
                    if name == "streamPreview":
                        lab.setStyleSheet(preview_css)
                    elif name == "streamDay":
                        lab.setStyleSheet(day_css)
                    elif name == "streamChip":
                        lab.setStyleSheet(chip_css)
                    else:
                        lab.setStyleSheet(time_css)
        if hasattr(self, "_detail_title"):
            self._detail_title.setStyleSheet(
                f"font-size: {tok.TYPE_TITLE}px; font-weight: 600; color: {tok.TEXT};"
                f" background: transparent;"
            )
        if hasattr(self, "_feedback_label"):
            self._feedback_label.setStyleSheet(
                f"color: {tok.TEXT}; font-size: {tok.TYPE_FOOTNOTE}px; background: transparent;"
            )
        if hasattr(self, "_details"):
            self._details.setStyleSheet(f"""
                QTextEdit {{
                    background: transparent;
                    color: {tok.TEXT};
                    border: none;
                    padding: 12px 0;
                    font-size: {tok.TYPE_BODY}px;
                }}
            """)
        if hasattr(self, "_undo_bar"):
            self._undo_bar.setStyleSheet(f"""
                QFrame {{
                    background: {tok.SURFACE_PEARL};
                    border: 1px solid {tok.BORDER};
                    border-radius: {tok.RADIUS_SM}px;
                }}
            """)
        if hasattr(self, "_export_btn"):
            self._export_btn.setStyleSheet(ss.BTN_GHOST_SM)
        if hasattr(self, "_detail_chip_labels"):
            chip_css = _chip_qss()
            for lab in self._detail_chip_labels:
                lab.setStyleSheet(chip_css)
        if hasattr(self, "_close_btn"):
            self._close_btn.setStyleSheet(
                f"QPushButton {{ background: {tok.CHIP_BG}; color: {tok.TEXT};"
                f" border: none; border-radius: 14px; font-size: {tok.TYPE_BODY_SM}px; }}"
                f"QPushButton:hover {{ background: {tok.CHIP_BG_HOVER}; }}"
            )
        if hasattr(self, "_delete_btn"):
            self._delete_btn.setStyleSheet(ss.BTN_DANGER_SM)
        if hasattr(self, "_clear_all_btn"):
            self._clear_all_btn.setStyleSheet(ss.BTN_DANGER_SM)
        if hasattr(self, "_copy_raw_btn"):
            self._copy_raw_btn.setStyleSheet(ss.BTN_GHOST_SM)
        if hasattr(self, "_copy_polished_btn"):
            self._copy_polished_btn.setStyleSheet(ss.BTN_GHOST_SM)
        if hasattr(self, "_undo_btn"):
            self._undo_btn.setStyleSheet(ss.BTN_GHOST_SM)

    def _setup_ui(self) -> None:
        from voiceink.ui.island_chrome import island_container_css

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)
        self._sheet = QWidget()
        self._sheet.setObjectName("islandSheet")
        self._sheet.setStyleSheet(island_container_css())
        sheet_lay = QVBoxLayout(self._sheet)
        sheet_lay.setContentsMargins(16, 14, 16, 14)
        sheet_lay.setSpacing(10)

        top = QHBoxLayout()
        self._title_label = QLabel("历史")
        top.addWidget(self._title_label, 1)
        self._export_btn = QPushButton("导出 Markdown")
        self._export_btn.clicked.connect(self._export_selected)
        top.addWidget(self._export_btn)
        close_x = QPushButton("\u2715")
        close_x.setFixedSize(28, 28)
        close_x.clicked.connect(self.close)
        self._close_btn = close_x
        top.addWidget(close_x)
        sheet_lay.addLayout(top)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索转写内容")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_edit.textChanged.connect(lambda: self._search_timer.start())
        self._search_timer.timeout.connect(self._perform_search)
        sheet_lay.addWidget(self._search_edit)

        stream = QWidget()
        self._stream_host = stream
        self._left_pane = stream
        stream.setObjectName("historyLeftPane")
        stream_lay = QVBoxLayout(stream)
        stream_lay.setContentsMargins(0, 0, 0, 0)
        stream_lay.setSpacing(0)
        self._session_list = QListWidget()
        self._session_list.setObjectName("historyTimeStream")
        self._session_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._session_list.itemDoubleClicked.connect(self._expand_session)
        self._session_list.itemSelectionChanged.connect(self._on_selection_changed)
        stream_lay.addWidget(self._session_list, 1)
        sheet_lay.addWidget(stream, 1)

        self._right_pane = QWidget()
        right_lay = QVBoxLayout(self._right_pane)
        right_lay.setContentsMargins(0, 4, 0, 0)
        right_lay.setSpacing(8)
        tools = QHBoxLayout()
        self._detail_title = QLabel("会话详情")
        tools.addWidget(self._detail_title, 1)
        self._copy_raw_btn = QPushButton("复制原文")
        self._copy_raw_btn.clicked.connect(self._copy_selected_raw)
        tools.addWidget(self._copy_raw_btn)
        self._copy_polished_btn = QPushButton("复制润色")
        self._copy_polished_btn.clicked.connect(self._copy_selected_polished)
        tools.addWidget(self._copy_polished_btn)
        self._delete_btn = QPushButton("删除")
        self._delete_btn.clicked.connect(self._delete_selected_sessions)
        tools.addWidget(self._delete_btn)
        right_lay.addLayout(tools)

        self._feedback_label = QLabel("")
        self._feedback_label.setVisible(False)
        right_lay.addWidget(self._feedback_label)
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._feedback_label.setVisible(False))

        self._detail_chip_bar = QWidget()
        self._detail_chips = QHBoxLayout(self._detail_chip_bar)
        self._detail_chips.setContentsMargins(0, 0, 0, 0)
        self._detail_chips.setSpacing(6)
        self._detail_chip_host = self._detail_chips
        self._detail_chip_labels: list[QLabel] = []
        self._detail_chips.addStretch()
        right_lay.addWidget(self._detail_chip_bar)

        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText("选择一条转写查看分段内容")
        right_lay.addWidget(self._details, 1)

        self._undo_bar = QFrame()
        self._undo_bar.setVisible(False)
        undo_lay = QHBoxLayout(self._undo_bar)
        undo_lay.setContentsMargins(12, 8, 8, 8)
        self._undo_label = QLabel("")
        undo_lay.addWidget(self._undo_label, 1)
        self._undo_btn = QPushButton("撤销")
        self._undo_btn.clicked.connect(self._undo_pending_delete)
        undo_lay.addWidget(self._undo_btn)
        right_lay.addWidget(self._undo_bar)
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.setInterval(8000)
        self._undo_timer.timeout.connect(self._commit_pending_delete)

        self._clear_all_btn = QPushButton("清空全部历史")
        self._clear_all_btn.clicked.connect(self._clear_all_history)
        right_lay.addWidget(self._clear_all_btn)
        sheet_lay.addWidget(self._right_pane, 1)
        outer.addWidget(self._sheet, 1)
        self._paint_history_styles()

    def refresh(self) -> None:
        self._load_sessions(self._store.list_sessions())

    def _load_sessions(self, sessions: list[SessionSummary]) -> None:
        self._session_list.clear()
        self._sessions_by_id = {s.session_id: s for s in sessions}
        last_day = None
        for session in sessions:
            item = QListWidgetItem(self._session_item_text(session))
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)
            item.setToolTip(
                f"来源：{session.source or '未知来源'} · "
                f"应用：{session.target_app or '未知应用'}"
            )
            self._session_list.addItem(item)
            day = _day_label(session.created_at)
            show_day = day != last_day
            last_day = day
            widget = self._build_stream_row(session, day if show_day else "")
            item.setForeground(Qt.GlobalColor.transparent)
            item.setSizeHint(QSize(0, 86 if show_day else 68))
            self._session_list.setItemWidget(item, widget)
        if sessions:
            self._session_list.setCurrentRow(0)
        else:
            self._set_detail_chips([])
            if self._search_query:
                empty = "没有匹配的转写。"
            else:
                empty = "还没有会话。完成一次转写后会出现在这里。"
            self._detail_title.setText(empty)
            self._details.setPlainText(empty)
        self._on_selection_changed()

    def _build_stream_row(self, session: SessionSummary, day: str) -> QWidget:
        from voiceink.ui import design_tokens as tok

        row = QWidget()
        lay = QVBoxLayout(row)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(4)
        if day:
            day_lab = QLabel(day)
            day_lab.setObjectName("streamDay")
            day_lab.setStyleSheet(
                f"color: {tok.TEXT_DIM}; font-size: {tok.TYPE_CAPTION}px;"
                f" letter-spacing: 0.08em; background: transparent;"
            )
            lay.addWidget(day_lab)
        line = QHBoxLayout()
        time_lab = QLabel(datetime.fromtimestamp(session.created_at / 1000).strftime("%H:%M"))
        time_lab.setObjectName("streamTime")
        time_lab.setFixedWidth(44)
        time_lab.setStyleSheet(
            f"color: {tok.TEXT_DIM}; font-size: {tok.TYPE_CAPTION}px; background: transparent;"
        )
        line.addWidget(time_lab)
        preview = QLabel(session.preview or "(无内容)")
        preview.setObjectName("streamPreview")
        preview.setWordWrap(True)
        preview.setStyleSheet(
            f"color: {tok.TEXT}; font-size: {tok.TYPE_BODY_SM}px; background: transparent;"
        )
        line.addWidget(preview, 1)
        lay.addLayout(line)
        chips = QHBoxLayout()
        chips.addSpacing(44)
        chip_css = _chip_qss()
        source_chip = QLabel(_source_chip_text(session.source))
        source_chip.setObjectName("streamChip")
        source_chip.setStyleSheet(chip_css)
        chips.addWidget(source_chip)
        if session.target_app:
            app_chip = QLabel(session.target_app)
            app_chip.setObjectName("streamChip")
            app_chip.setStyleSheet(chip_css)
            chips.addWidget(app_chip)
        count = QLabel(f"{session.segment_count} 段")
        count.setObjectName("streamChip")
        count.setStyleSheet(chip_css)
        chips.addWidget(count)
        chips.addStretch()
        lay.addLayout(chips)
        row.setMinimumHeight(76 if day else 60)
        return row


    def _session_item_text(self, session: SessionSummary) -> str:
        preview = session.preview or "(无内容)"
        return f"{preview}\n{_format_dt(session.created_at)} · {session.segment_count} 段"

    def _perform_search(self) -> None:
        q = self._search_edit.text().strip()
        self._search_query = q
        if q:
            self._load_sessions(self._store.search_sessions(q))
        else:
            self.refresh()

    def _set_detail_chips(self, texts: list[str]) -> None:
        while self._detail_chips.count():
            item = self._detail_chips.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._detail_chip_labels = []
        chip_css = _chip_qss()
        for text in texts:
            if not text:
                continue
            lab = QLabel(text)
            lab.setStyleSheet(chip_css)
            self._detail_chip_labels.append(lab)
            self._detail_chips.addWidget(lab)
        self._detail_chips.addStretch()
        self._detail_chip_bar.setVisible(bool(self._detail_chip_labels))

    def _expand_session(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        segments = self._store.get_session_segments(session_id)
        summary = self._sessions_by_id.get(session_id)
        chip_texts: list[str] = []
        if summary is not None and summary.source:
            chip_texts.append(_source_chip_text(summary.source))
        if segments:
            first = _segments_in_order(segments)[0]
            trigger = _trigger_chip_text(first.trigger_mode)
            if trigger:
                chip_texts.append(trigger)
            if first.model:
                chip_texts.append(first.model)
        self._set_detail_chips(chip_texts)
        lines: list[str] = []
        for segment in _segments_in_order(segments):
            raw = (segment.raw_text or "").strip()
            polished = (segment.polished_text or "").strip()
            if polished and raw and polished != raw:
                lines.append(f"原文\n{raw}")
                lines.append(f"润色\n{polished}")
            else:
                text = _effective_text(segment).strip()
                if text:
                    lines.append(text)
        self._details.setPlainText("\n\n".join(lines) if lines else "")

    def _on_selection_changed(self) -> None:
        selected = self._selected_session_ids()
        count = len(selected)
        self._copy_raw_btn.setEnabled(count == 1)
        has_polished = False
        if count == 1:
            has_polished = _session_has_polished(
                self._store.get_session_segments(selected[0])
            )
        self._copy_polished_btn.setEnabled(has_polished)
        self._export_btn.setEnabled(count > 0)
        self._delete_btn.setEnabled(count > 0)
        if count == 1:
            self._detail_title.setText("会话详情")
            item = self._session_list.selectedItems()[0]
            self._expand_session(item)
        elif count > 1:
            self._set_detail_chips([])
            self._detail_title.setText(f"已选 {count} 项")
            self._details.setPlainText(f"已选 {count} 项，可批量导出或删除。")
        elif self._session_list.count():
            self._set_detail_chips([])
            self._detail_title.setText("会话详情")
            self._details.setPlainText("选择一条转写查看分段内容")

    def _selected_session_ids(self) -> list[str]:
        return [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._session_list.selectedItems()
            if item.data(Qt.ItemDataRole.UserRole)
        ]

    def _selected_sessions(self) -> list[SessionSummary]:
        return [
            self._sessions_by_id[sid]
            for sid in self._selected_session_ids()
            if sid in self._sessions_by_id
        ]

    def _active_session_id(self) -> str | None:
        ids = self._selected_session_ids()
        if len(ids) == 1:
            return ids[0]
        return None

    def _copy_selected_raw(self) -> None:
        session_id = self._active_session_id()
        if not session_id:
            return
        segments = self._store.get_session_segments(session_id)
        text = "\n\n".join(s.raw_text.strip() for s in _segments_in_order(segments) if s.raw_text.strip())
        QApplication.clipboard().setText(text)
        self._show_feedback("已复制原文")

    def _copy_selected_polished(self) -> None:
        session_id = self._active_session_id()
        if not session_id:
            return
        segments = self._store.get_session_segments(session_id)
        QApplication.clipboard().setText(_session_body(segments))
        self._show_feedback("已复制润色文本")

    def _show_feedback(self, text: str) -> None:
        self._feedback_label.setText(text)
        self._feedback_label.setVisible(True)
        self._feedback_timer.start(2200)

    def _delete_selected_sessions(self) -> None:
        ids = self._selected_session_ids()
        if not ids:
            return
        reply = QMessageBox.question(
            self,
            "删除历史",
            f"确定删除已选 {len(ids)} 项吗？可在 8 秒内撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._pending_delete = self._selected_sessions()
        self._load_sessions([
            session for session in self._sessions_by_id.values()
            if session.session_id not in ids
        ])
        self._undo_label.setText(f"已移除 {len(ids)} 项")
        self._undo_bar.setVisible(True)
        self._undo_timer.start()

    def _undo_pending_delete(self) -> None:
        if not self._pending_delete:
            return
        self._undo_timer.stop()
        self._pending_delete = []
        self._undo_bar.setVisible(False)
        self.refresh()

    def _commit_pending_delete(self) -> None:
        if not self._pending_delete:
            return
        ids = [session.session_id for session in self._pending_delete]
        self._pending_delete = []
        self._undo_bar.setVisible(False)
        self._store.enqueue_delete_sessions(ids)
        QTimer.singleShot(250, self.refresh)

    def _clear_all_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "清空全部历史",
            "确定清空全部历史吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._store.enqueue_delete_all()
        QTimer.singleShot(250, self.refresh)

    def _export_selected(self) -> None:
        sessions = self._selected_sessions()
        if not sessions:
            return
        if len(sessions) == 1:
            self._export_single(sessions[0])
        else:
            self._export_batch(sessions)

    def _export_single(self, session: SessionSummary) -> None:
        default = suggest_single_export_filename(session)
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出历史",
            default,
            "Markdown (*.md)",
        )
        if not path:
            return
        segments = self._store.get_session_segments(session.session_id)
        try:
            Path(path).write_text(
                build_single_session_markdown(session, segments),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.critical(self, "导出失败", f"无法写入文件：{exc}")
            return
        self._show_feedback("已导出历史")

    def _export_batch(self, sessions: list[SessionSummary]) -> None:
        default = suggest_batch_export_filename()
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "批量导出历史",
            default,
            "Markdown (*.md)",
        )
        if not path:
            return
        segments_by_session = {
            s.session_id: self._store.get_session_segments(s.session_id)
            for s in sessions
        }
        try:
            Path(path).write_text(
                build_batch_export_markdown(sessions, segments_by_session),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.critical(self, "导出失败", f"无法写入文件：{exc}")
            return
        self._show_feedback("已导出历史")
