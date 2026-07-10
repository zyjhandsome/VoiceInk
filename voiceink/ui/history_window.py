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
from voiceink.ui.design_tokens import BG, TEXT, TEXT_DIM
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
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("历史")
        title.setStyleSheet(
            "font-size: 22px; font-weight: 650; background: transparent;"
            f" color: {TEXT};"
        )
        root.addWidget(title)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索历史内容")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_edit.textChanged.connect(lambda: self._search_timer.start())
        self._search_timer.timeout.connect(self._perform_search)
        root.addWidget(self._search_edit)

        body = QHBoxLayout()
        body.setSpacing(12)

        self._session_list = QListWidget()
        self._session_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._session_list.itemDoubleClicked.connect(self._expand_session)
        self._session_list.currentItemChanged.connect(
            lambda current, _prev: self._expand_session(current) if current else None
        )
        self._session_list.setStyleSheet(
            f"QListWidget {{ background: white; color: {TEXT}; border: 1px solid #D0D7E2;"
            " border-radius: 11px; padding: 8px; }}"
            "QListWidget::item { padding: 10px; border-radius: 8px; }"
            "QListWidget::item:selected { background: #DCEAFA; }"
        )
        body.addWidget(self._session_list, 2)

        self._details = QTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText("双击左侧会话查看分段内容")
        body.addWidget(self._details, 3)
        root.addLayout(body, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._copy_raw_btn = QPushButton("复制原文")
        self._copy_raw_btn.setStyleSheet(BTN_GHOST_SM)
        self._copy_raw_btn.clicked.connect(self._copy_selected_raw)
        actions.addWidget(self._copy_raw_btn)

        self._copy_polished_btn = QPushButton("复制润色")
        self._copy_polished_btn.setStyleSheet(BTN_GHOST_SM)
        self._copy_polished_btn.clicked.connect(self._copy_selected_polished)
        actions.addWidget(self._copy_polished_btn)

        self._export_btn = QPushButton("导出")
        self._export_btn.setStyleSheet(BTN_GHOST_SM)
        self._export_btn.clicked.connect(self._export_selected)
        actions.addWidget(self._export_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setStyleSheet(BTN_DANGER_SM)
        self._delete_btn.clicked.connect(self._delete_selected_sessions)
        actions.addWidget(self._delete_btn)

        actions.addStretch()

        self._clear_all_btn = QPushButton("清空全部历史")
        self._clear_all_btn.setStyleSheet(BTN_DANGER_SM)
        self._clear_all_btn.clicked.connect(self._clear_all_history)
        actions.addWidget(self._clear_all_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.setStyleSheet(BTN_PRIMARY)
        self._close_btn.clicked.connect(self.close)
        actions.addWidget(self._close_btn)
        root.addLayout(actions)

        self.setStyleSheet(self.styleSheet() + f"QDialog {{ background: {BG}; }}")

    def refresh(self) -> None:
        self._load_sessions(self._store.list_sessions())

    def _load_sessions(self, sessions: list[SessionSummary]) -> None:
        self._session_list.clear()
        self._sessions_by_id = {s.session_id: s for s in sessions}
        for session in sessions:
            item = QListWidgetItem(self._session_item_text(session))
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)
            self._session_list.addItem(item)
        if sessions:
            self._session_list.setCurrentRow(0)
        else:
            self._details.clear()

    def _session_item_text(self, session: SessionSummary) -> str:
        target = session.target_app or "未知应用"
        source = session.source or "未知来源"
        preview = session.preview or "(无内容)"
        return (
            f"{_format_dt(session.created_at)} · {source} → {target}\n"
            f"{preview}\n"
            f"{session.segment_count} 段"
        )

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
        lines = []
        for segment in _segments_in_order(segments):
            text = _effective_text(segment).strip()
            if text:
                lines.append(text)
        self._details.setPlainText("\n\n".join(lines))

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
        if ids:
            return ids[0]
        item = self._session_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _copy_selected_raw(self) -> None:
        session_id = self._active_session_id()
        if not session_id:
            return
        segments = self._store.get_session_segments(session_id)
        text = "\n\n".join(s.raw_text.strip() for s in _segments_in_order(segments) if s.raw_text.strip())
        QApplication.clipboard().setText(text)

    def _copy_selected_polished(self) -> None:
        session_id = self._active_session_id()
        if not session_id:
            return
        segments = self._store.get_session_segments(session_id)
        QApplication.clipboard().setText(_session_body(segments))

    def _delete_selected_sessions(self) -> None:
        ids = self._selected_session_ids()
        if not ids:
            return
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
        Path(path).write_text(build_single_session_markdown(session, segments), encoding="utf-8")

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
        Path(path).write_text(
            build_batch_export_markdown(sessions, segments_by_session),
            encoding="utf-8",
        )
