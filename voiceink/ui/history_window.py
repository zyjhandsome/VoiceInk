"""History browser window and Markdown export helpers."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
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
from voiceink.ui.design_tokens import (
    ACCENT,
    BG,
    BORDER,
    FONT_DISPLAY,
    HAIRLINE,
    RADIUS_MD,
    RADIUS_SM,
    ROW_SELECTED,
    SURFACE,
    SURFACE_PEARL,
    TEXT,
)
from voiceink.ui.settings_styles import (
    BTN_DANGER_SM,
    BTN_GHOST_SM,
    BTN_PRIMARY,
    WINDOW_CSS,
)


def _format_dt(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


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
        self._setup_window()
        self._setup_ui()
        self.refresh()

    def _setup_window(self) -> None:
        self.setWindowTitle("历史")
        self.setMinimumSize(760, 520)
        self.resize(900, 640)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setStyleSheet(WINDOW_CSS)

    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left = QWidget()
        left.setObjectName("historyLeftPane")
        left.setStyleSheet(f"""
            QWidget#historyLeftPane {{
                background: {SURFACE};
                border-right: 1px solid {BORDER};
            }}
        """)
        left.setFixedWidth(340)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 16, 16, 16)
        left_lay.setSpacing(12)

        title = QLabel("历史")
        title.setStyleSheet(
            f"font-family: {FONT_DISPLAY}; font-size: 22px; font-weight: 700;"
            f" background: transparent; color: {TEXT}; letter-spacing: -0.02em;"
        )
        left_lay.addWidget(title)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索会话…")
        self._search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {SURFACE_PEARL};
                color: {TEXT};
                border: 1px solid {HAIRLINE};
                border-radius: {RADIUS_MD}px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {ACCENT};
                padding: 9px 13px;
            }}
        """)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_edit.textChanged.connect(lambda: self._search_timer.start())
        self._search_timer.timeout.connect(self._perform_search)
        left_lay.addWidget(self._search_edit)

        self._session_list = QListWidget()
        self._session_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._session_list.itemDoubleClicked.connect(self._expand_session)
        self._session_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._session_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                color: {TEXT};
                border: none;
                padding: 0;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: {RADIUS_SM}px;
                margin: 2px 0;
            }}
            QListWidget::item:selected {{
                background: {ROW_SELECTED};
                border-left: 3px solid {ACCENT};
                color: {TEXT};
            }}
            QListWidget::item:hover:!selected {{
                background: {SURFACE_PEARL};
            }}
        """)
        left_lay.addWidget(self._session_list, 1)
        root.addWidget(left)

        right = QWidget()
        right.setStyleSheet(f"background: {BG};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(20, 16, 20, 16)
        right_lay.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._detail_title = QLabel("会话详情")
        self._detail_title.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {TEXT}; background: transparent;"
        )
        header.addWidget(self._detail_title, 1)

        self._copy_raw_btn = QPushButton("复制原文")
        self._copy_raw_btn.setStyleSheet(BTN_GHOST_SM)
        self._copy_raw_btn.clicked.connect(self._copy_selected_raw)
        header.addWidget(self._copy_raw_btn)

        self._copy_polished_btn = QPushButton("复制润色")
        self._copy_polished_btn.setStyleSheet(BTN_GHOST_SM)
        self._copy_polished_btn.clicked.connect(self._copy_selected_polished)
        header.addWidget(self._copy_polished_btn)

        self._export_btn = QPushButton("导出")
        self._export_btn.setStyleSheet(BTN_PRIMARY)
        self._export_btn.clicked.connect(self._export_selected)
        header.addWidget(self._export_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet(BTN_DANGER_SM)
        self._delete_btn.clicked.connect(self._delete_selected_sessions)
        header.addWidget(self._delete_btn)
        right_lay.addLayout(header)

        self._feedback_label = QLabel("")
        self._feedback_label.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; background: transparent;"
        )
        self._feedback_label.setVisible(False)
        right_lay.addWidget(self._feedback_label)
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(lambda: self._feedback_label.setVisible(False))

        detail_card = QFrame()
        detail_card.setObjectName("historyDetailCard")
        detail_card.setStyleSheet("""
            QFrame#historyDetailCard {
                background: transparent;
                border: none;
            }
        """)
        detail_lay = QVBoxLayout(detail_card)
        detail_lay.setContentsMargins(0, 0, 0, 0)

        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText("选择左侧会话查看分段内容")
        self._details.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                color: {TEXT};
                border: none;
                padding: 12px 0;
                font-size: 14px;
            }}
        """)
        detail_lay.addWidget(self._details)
        right_lay.addWidget(detail_card, 1)

        self._undo_bar = QFrame()
        self._undo_bar.setVisible(False)
        self._undo_bar.setStyleSheet(f"""
            QFrame {{
                background: {SURFACE_PEARL};
                border: 1px solid {BORDER};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        undo_lay = QHBoxLayout(self._undo_bar)
        undo_lay.setContentsMargins(12, 8, 8, 8)
        self._undo_label = QLabel("")
        undo_lay.addWidget(self._undo_label, 1)
        self._undo_btn = QPushButton("撤销")
        self._undo_btn.setStyleSheet(BTN_GHOST_SM)
        self._undo_btn.clicked.connect(self._undo_pending_delete)
        undo_lay.addWidget(self._undo_btn)
        right_lay.addWidget(self._undo_bar)
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.setInterval(8000)
        self._undo_timer.timeout.connect(self._commit_pending_delete)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._clear_all_btn = QPushButton("清空全部历史")
        self._clear_all_btn.setStyleSheet(BTN_DANGER_SM)
        self._clear_all_btn.clicked.connect(self._clear_all_history)
        actions.addWidget(self._clear_all_btn)
        actions.addStretch()
        self._close_btn = QPushButton("关闭")
        self._close_btn.setStyleSheet(BTN_PRIMARY)
        self._close_btn.clicked.connect(self.close)
        actions.addWidget(self._close_btn)
        right_lay.addLayout(actions)

        root.addWidget(right, 1)

    def refresh(self) -> None:
        self._load_sessions(self._store.list_sessions())

    def _load_sessions(self, sessions: list[SessionSummary]) -> None:
        self._session_list.clear()
        self._sessions_by_id = {s.session_id: s for s in sessions}
        for session in sessions:
            item = QListWidgetItem(self._session_item_text(session))
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)
            item.setToolTip(
                f"来源：{session.source or '未知来源'} · "
                f"应用：{session.target_app or '未知应用'}"
            )
            self._session_list.addItem(item)
        if sessions:
            self._session_list.setCurrentRow(0)
        else:
            self._detail_title.setText("暂无历史")
            self._details.setPlainText("暂无历史记录。完成一次语音转写后，会话会显示在这里。")
        self._on_selection_changed()

    def _session_item_text(self, session: SessionSummary) -> str:
        preview = session.preview or "(无内容)"
        return f"{preview}\n{_format_dt(session.created_at)} · {session.segment_count} 段"

    def _perform_search(self) -> None:
        q = self._search_edit.text().strip()
        if q:
            self._load_sessions(self._store.search_sessions(q))
        else:
            self.refresh()

    def _expand_session(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        segments = self._store.get_session_segments(session_id)
        summary = self._sessions_by_id.get(session_id)
        meta_bits = []
        if summary is not None:
            if summary.source:
                meta_bits.append(f"来源：{summary.source}")
            if summary.target_app:
                meta_bits.append(f"应用：{summary.target_app}")
        if segments:
            first = _segments_in_order(segments)[0]
            mode = (first.trigger_mode or "").strip()
            if mode == "continuous":
                meta_bits.append("触发：持续转写")
            elif mode == "hotkey":
                meta_bits.append("触发：按住录音")
            elif mode:
                meta_bits.append(f"触发：{mode}")
            if first.model:
                meta_bits.append(f"模型：{first.model}")
        lines = []
        if meta_bits:
            lines.append(" · ".join(meta_bits))
            lines.append("")
        for segment in _segments_in_order(segments):
            text = _effective_text(segment).strip()
            if text:
                lines.append(text)
        self._details.setPlainText("\n\n".join(lines) if lines else "")

    def _on_selection_changed(self) -> None:
        selected = self._selected_session_ids()
        count = len(selected)
        self._copy_raw_btn.setEnabled(count == 1)
        self._copy_polished_btn.setEnabled(count == 1)
        self._export_btn.setEnabled(count > 0)
        self._delete_btn.setEnabled(count > 0)
        if count == 1:
            self._detail_title.setText("会话详情")
            item = self._session_list.selectedItems()[0]
            self._expand_session(item)
        elif count > 1:
            self._detail_title.setText(f"已选 {count} 项")
            self._details.setPlainText(f"已选 {count} 项，可批量导出或删除。")
        elif self._session_list.count():
            self._detail_title.setText("会话详情")
            self._details.setPlainText("选择左侧会话查看分段内容")

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
