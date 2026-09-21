# tests/test_main_window.py
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(sys.argv)


def _make_main_window(tmp_path, monkeypatch):
    from voiceink.config import Config
    from voiceink.history_store import HistoryStore
    from voiceink.ui.main_window import MainWindow
    from voiceink.ui.settings_window import SettingsWindow
    monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
    monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
    monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)
    store = HistoryStore(tmp_path / "h.db")
    win = MainWindow(Config(config_dir=tmp_path), store)
    return win, store

def test_chrome_size_and_nav(qapp, tmp_path, monkeypatch):
    from voiceink.ui.main_window import NAV_LABELS
    from voiceink.ui import design_tokens as tok
    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        assert win.width() == 960
        assert win.height() == 640
        assert [b.text() for b in win._nav_buttons] == list(NAV_LABELS)
        assert win._sidebar.width() == tok.SIDEBAR_WIDTH
        assert win.windowFlags() & Qt.WindowType.FramelessWindowHint
        assert win.current_page() == "general"
        win.show_page("history")
        assert win.current_page() == "history"
    finally:
        win.close()
        store.close()


def test_outer_border_uses_explicit_window_frame(qapp, tmp_path, monkeypatch):
    from voiceink.ui import design_tokens as tok

    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        css = win.styleSheet()
        margins = win.layout().contentsMargins()
        assert win.objectName() == "mainWindow"
        assert "QWidget#mainWindow" in css
        assert f"border: 1px solid {tok.TEXT_DIM}" in css
        assert f"border-radius: {tok.WINDOW_RADIUS}px" in css
        assert not win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert f"background: {tok.BG}" in css
        assert f"background: {tok.BG}" in win._stack.styleSheet()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (
            1,
            1,
            1,
            1,
        )
        assert "border: 1px solid" not in win._sidebar.styleSheet()
    finally:
        win.close()
        store.close()


def test_caption_chrome_is_distinct_from_content(qapp, tmp_path, monkeypatch):
    from voiceink.ui import design_tokens as tok

    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        css = win._caption.styleSheet()
        assert win._caption.objectName() == "mainCaption"
        assert f"background: {tok.BG}" in css
        assert f"border-bottom: 1px solid {tok.CONTROL_BORDER}" in css
        assert win._caption.height() == 42
    finally:
        win.close()
        store.close()


def test_caption_drag_moves_window(qapp, tmp_path, monkeypatch):
    from PyQt6.QtCore import QEvent, QPoint, QPointF
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication

    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        win.show()
        win.move(200, 160)
        QApplication.processEvents()
        origin = QPoint(win.pos())
        local = QPoint(40, 18)
        press_global = win._caption.mapToGlobal(local)
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(local),
            QPointF(press_global),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(win._caption, press)
        delta = QPoint(80, 40)
        moved_local = local + delta
        move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(moved_local),
            QPointF(press_global + delta),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(win._caption, move)
        QApplication.processEvents()
        assert win.pos() == origin + delta
    finally:
        win.close()
        store.close()


def test_close_hides_does_not_quit(qapp, tmp_path, monkeypatch):
    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        win.show()
        win.close()
        assert win.isHidden()
        win.deleteLater()
    finally:
        store.close()


def test_show_page_embeds_hosts(qapp, tmp_path, monkeypatch):
    from voiceink.config import Config
    from voiceink.history_store import HistoryStore
    from voiceink.ui.main_window import MainWindow
    from voiceink.ui.settings_window import SettingsWindow
    monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
    monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
    monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)
    store = HistoryStore(tmp_path / "h.db")
    win = MainWindow(Config(config_dir=tmp_path), store)
    try:
        assert not hasattr(win._settings, "_island_nav")
        win.show_page("engine")
        assert win._settings._pages.currentIndex() == 1
        win.show_page("history")
        assert win._stack.currentWidget() is win._history
        assert win._history._title_label.text() == "历史"
        assert not hasattr(win._history, "_close_btn")
    finally:
        win.close()
        store.close()


def test_show_page_history_refreshes_list(qapp, tmp_path, monkeypatch):
    win, store = _make_main_window(tmp_path, monkeypatch)
    try:
        refreshes: list[int] = []
        original = win._history.refresh

        def spy():
            refreshes.append(1)
            original()

        win._history.refresh = spy
        win.show_page("general")
        win.show_page("history")
        assert refreshes
    finally:
        win.close()
        store.close()
