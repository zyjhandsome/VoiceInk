# tests/test_main_window.py
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(sys.argv)

def test_chrome_size_and_nav(qapp):
    from voiceink.ui.main_window import NAV_LABELS, MainWindow
    from voiceink.ui import design_tokens as tok
    win = MainWindow()
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

def test_close_hides_does_not_quit(qapp):
    from voiceink.ui.main_window import MainWindow
    win = MainWindow()
    win.show()
    win.close()
    assert win.isHidden()
    win.deleteLater()
