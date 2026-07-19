"""History window UI and Markdown export behavior."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from voiceink.history_store import SegmentRecord, SessionSummary
from voiceink.app import App
from voiceink.ui.history_window import (
    HistoryWindow,
    build_batch_export_markdown,
    build_single_session_markdown,
    suggest_batch_export_filename,
    suggest_single_export_filename,
)
from voiceink.ui.tray_icon import TrayIcon


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication(sys.argv)


class FakeHistoryStore:
    def __init__(self) -> None:
        self.sessions = [
            SessionSummary(
                session_id="newer",
                created_at=1_700_000_300_000,
                segment_count=2,
                source="mixed",
                target_app="Code.exe",
                preview="newer preview",
            ),
            SessionSummary(
                session_id="older",
                created_at=1_700_000_000_000,
                segment_count=1,
                source="mic",
                target_app="Notepad.exe",
                preview="older preview",
            ),
        ]
        self.segments = {
            "newer": [
                SegmentRecord("newer", 1, 1_700_000_301_000, "raw second", "", "mixed", 900, "Code.exe", "continuous", "fire-red"),
                SegmentRecord("newer", 0, 1_700_000_300_000, "raw first", "polished first", "mixed", 1100, "Code.exe", "continuous", "fire-red"),
            ],
            "older": [
                SegmentRecord("older", 0, 1_700_000_000_000, "older raw", "", "mic", 500, "Notepad.exe", "hotkey", "tiny"),
            ],
        }
        self.search_terms: list[str] = []
        self.deleted_sessions: list[list[str]] = []
        self.deleted_all = False

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionSummary]:
        return self.sessions[offset : offset + limit]

    def search_sessions(self, q: str) -> list[SessionSummary]:
        self.search_terms.append(q)
        return [self.sessions[1]]

    def get_session_segments(self, session_id: str) -> list[SegmentRecord]:
        return self.segments[session_id]

    def enqueue_delete_sessions(self, session_ids: list[str]) -> None:
        self.deleted_sessions.append(session_ids)

    def enqueue_delete_all(self) -> None:
        self.deleted_all = True


def test_renders_sessions_as_reverse_order_group_rows(qapp):
    store = FakeHistoryStore()
    window = HistoryWindow(store)

    assert not hasattr(window, "_history_web")
    assert window._session_list.count() == 2
    first = window._session_list.item(0)
    second = window._session_list.item(1)

    assert first.data(Qt.ItemDataRole.UserRole) == "newer"
    assert "newer preview" in first.text()
    assert "2 段" in first.text()
    assert "mixed" not in first.text()
    assert "Code.exe" not in first.text()
    assert "mixed" in first.toolTip()
    assert "Code.exe" in first.toolTip()
    assert second.data(Qt.ItemDataRole.UserRole) == "older"


def test_double_click_expands_session_segments(qapp):
    store = FakeHistoryStore()
    window = HistoryWindow(store)

    window._expand_session(window._session_list.item(0))

    detail = window._details.toPlainText()
    assert "polished first" in detail
    assert "raw second" in detail
    assert "来源：" in detail or "触发：" in detail or "模型：" in detail


def test_legacy_file_import_history_labels_are_preserved(qapp):
    """Withdrawn file-transcription capability still shows legacy history metadata."""
    store = FakeHistoryStore()
    store.sessions.insert(
        0,
        SessionSummary(
            session_id="file1",
            created_at=1_700_000_400_000,
            segment_count=1,
            source="file",
            target_app="",
            preview="from media file",
        ),
    )
    store.segments["file1"] = [
        SegmentRecord(
            "file1",
            0,
            1_700_000_400_000,
            "file raw text",
            "",
            "file",
            1200,
            "",
            "file_import",
            "fire-red",
        ),
    ]
    window = HistoryWindow(store)
    window._expand_session(window._session_list.item(0))
    detail = window._details.toPlainText()
    assert "来源：文件转写" in detail
    assert "触发：导入文件" in detail
    assert "file raw text" in detail


def test_search_debounces_into_like_search(qapp):
    store = FakeHistoryStore()
    window = HistoryWindow(store)

    window._search_edit.setText("older")
    window._search_timer.stop()
    window._perform_search()

    assert store.search_terms == ["older"]
    assert window._session_list.count() == 1
    assert window._session_list.item(0).data(Qt.ItemDataRole.UserRole) == "older"


def test_delete_selected_sessions_commits_after_undo_timeout(qapp, monkeypatch):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    window._session_list.item(0).setSelected(True)
    window._session_list.item(1).setSelected(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window._delete_selected_sessions()
    assert store.deleted_sessions == []
    assert window._session_list.count() == 0

    window._commit_pending_delete()
    assert store.deleted_sessions == [["newer", "older"]]


def test_delete_selected_sessions_cancel_keeps_sessions(qapp, monkeypatch):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    window._delete_selected_sessions()

    assert store.deleted_sessions == []
    assert window._session_list.count() == 2


def test_undo_pending_delete_restores_sessions_without_store_delete(qapp, monkeypatch):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    window._session_list.item(0).setSelected(True)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window._delete_selected_sessions()
    window._undo_pending_delete()

    assert store.deleted_sessions == []
    assert window._session_list.count() == 2


def test_selection_summary_disables_copy_for_multiple_items(qapp):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    window._session_list.item(0).setSelected(True)
    window._session_list.item(1).setSelected(True)
    window._on_selection_changed()

    assert "已选 2 项" in window._details.toPlainText()
    assert "已选 2 项" in window._detail_title.text()
    assert not window._copy_raw_btn.isEnabled()
    assert not window._copy_polished_btn.isEnabled()
    assert window._export_btn.isEnabled()
    assert window._delete_btn.isEnabled()


def test_empty_history_shows_helpful_placeholder_and_disables_actions(qapp):
    store = FakeHistoryStore()
    store.sessions = []
    window = HistoryWindow(store)

    assert "暂无历史" in window._details.toPlainText()
    assert not window._copy_raw_btn.isEnabled()
    assert not window._copy_polished_btn.isEnabled()
    assert not window._export_btn.isEnabled()
    assert not window._delete_btn.isEnabled()


def test_copy_feedback_is_shown_for_single_selection(qapp):
    store = FakeHistoryStore()
    window = HistoryWindow(store)

    window._copy_selected_raw()

    assert "已复制" in window._feedback_label.text()


def test_export_failure_shows_error_message(qapp, monkeypatch, tmp_path):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    errors = []
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "history.md"), "Markdown (*.md)"),
    )
    monkeypatch.setattr(
        Path,
        "write_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args, **kwargs: errors.append(args[2]),
    )

    window._export_selected()

    assert errors and "disk full" in errors[0]


def test_clear_all_history_uses_store_enqueue_after_confirmation(qapp, monkeypatch):
    store = FakeHistoryStore()
    window = HistoryWindow(store)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    window._clear_all_history()

    assert store.deleted_all is True


def test_single_export_markdown_frontmatter_and_effective_text_by_seq():
    session = SessionSummary("newer", 1_700_000_300_000, 2, "mixed", "Code.exe", "preview")
    segments = [
        SegmentRecord("newer", 2, 1_700_000_302_000, "third raw", "third polished", "mixed", 700, "Code.exe", "continuous", "fire-red"),
        SegmentRecord("newer", 0, 1_700_000_300_000, "first raw", "", "mixed", 1100, "Code.exe", "continuous", "fire-red"),
        SegmentRecord("newer", 1, 1_700_000_301_000, "second raw", "second polished", "mixed", 900, "Code.exe", "continuous", "fire-red"),
    ]

    markdown = build_single_session_markdown(session, segments)

    assert markdown.startswith("---\n")
    assert "source: mixed" in markdown
    assert "target_app: Code.exe" in markdown
    assert "duration_ms: 2700" in markdown
    assert "model: fire-red" in markdown
    assert "segment_count: 2" in markdown
    assert markdown.index("first raw") < markdown.index("second polished") < markdown.index("third polished")
    assert "second raw" not in markdown


def test_batch_export_markdown_uses_one_section_per_session():
    newer = SessionSummary("newer", 1_700_000_300_000, 2, "mixed", "Code.exe", "newer preview")
    older = SessionSummary("older", 1_700_000_000_000, 1, "mic", "Notepad.exe", "older preview")
    segments_by_session = {
        "newer": [SegmentRecord("newer", 0, 1_700_000_300_000, "new raw", "", "mixed", 100, "Code.exe", "continuous", "fire-red")],
        "older": [SegmentRecord("older", 0, 1_700_000_000_000, "old raw", "", "mic", 100, "Notepad.exe", "hotkey", "tiny")],
    }

    markdown = build_batch_export_markdown([newer, older], segments_by_session)

    assert markdown.count("\n## ") == 2
    assert "## " in markdown
    assert "old raw" in markdown
    assert "new raw" in markdown
    assert markdown.index("older preview") < markdown.index("newer preview")


def test_export_filenames_follow_adr_patterns():
    session = SessionSummary("newer", 1_700_000_300_000, 2, "mixed", "Code.exe", "preview")

    assert suggest_single_export_filename(session).startswith("voiceink-")
    assert suggest_single_export_filename(session).endswith(".md")
    assert suggest_batch_export_filename(now_ms=1_700_000_300_000).startswith("voiceink-export-")
    assert suggest_batch_export_filename(now_ms=1_700_000_300_000).endswith(".md")


def test_tray_menu_has_history_entry_signal(qapp):
    tray = TrayIcon()
    emitted: list[bool] = []
    tray.history_requested.connect(lambda: emitted.append(True))

    history_action = next(
        action for action in tray.contextMenu().actions() if action.text() == "历史"
    )
    history_action.trigger()

    assert emitted == [True]
    tray.hide()


def test_app_show_history_window_reuses_single_window(qapp, monkeypatch):
    created: list[object] = []

    class FakeHistoryWindow:
        def __init__(self, store):
            self.store = store
            self.shown = 0
            self.raised = 0
            self.activated = 0
            created.append(self)

        def isVisible(self):
            return self.shown > 0

        def refresh(self):
            pass

        def show(self):
            self.shown += 1

        def raise_(self):
            self.raised += 1

        def activateWindow(self):
            self.activated += 1

    monkeypatch.setattr("voiceink.app.HistoryWindow", FakeHistoryWindow)
    app = App.__new__(App)
    app._history = object()
    app._history_win = None

    app._show_history_window()
    app._show_history_window()

    assert len(created) == 1
    assert created[0].store is app._history
    assert created[0].shown == 1
    assert created[0].raised == 2
    assert created[0].activated == 2
