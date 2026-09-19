"""Spatial Island surface: morph modes, chrome, and HUD actions."""

from __future__ import annotations

import sys

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from voiceink.ui.floating_window import COMPACT_HEIGHT, FloatingWindow
from voiceink.ui.island_chrome import ISLAND_SHEET_WIDTH, position_island


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def win(qapp):
    w = FloatingWindow()
    yield w
    w.close()


class TestIslandMorph:
    def test_listening_uses_compact_capsule(self, win):
        win.show_listening()
        assert win.island_mode() == "compact"
        assert win.height() <= COMPACT_HEIGHT + 8
        assert "正在听" in win._status_label.text()

    def test_expand_live_shows_actions(self, win):
        win.show_listening()
        win.expand_live("下一步把这份纪要贴到会议群里。")
        assert win.island_mode() == "expanded"
        assert "纪要" in win._text_label.text()
        assert win._history_btn.isVisible()
        assert win._settings_btn.isVisible()
        assert win._end_btn.isVisible()

    def test_settings_button_emits(self, win):
        hits = []
        win.settings_requested.connect(lambda: hits.append(True))
        win.show_listening()
        win.expand_live("hello")
        win._settings_btn.click()
        assert hits == [True]

    def test_history_button_emits(self, win):
        hits = []
        win.history_requested.connect(lambda: hits.append(True))
        win.show_listening()
        win.expand_live("hello")
        win._history_btn.click()
        assert hits == [True]

    def test_end_button_stops_continuous(self, win):
        stops = []
        win.continuous_stop_requested.connect(lambda: stops.append(True))
        win.show_listening()
        win.expand_live("hello")
        win._end_btn.click()
        assert stops == [True]

    def test_success_auto_collapses_to_compact(self, win):
        win.expand_live("done")
        win.show_success("已输入")
        assert win.island_mode() == "compact"

    def test_container_uses_island_object_name(self, win):
        assert win._container.objectName() == "islandContainer"

    def test_expanded_end_is_only_primary(self, win):
        from voiceink.ui import design_tokens as tok

        win.show_listening()
        win.expand_live("hello")
        assert tok.ACCENT.lower() in win._end_btn.styleSheet().lower()
        assert tok.ACCENT.lower() not in win._history_btn.styleSheet().lower()
        assert tok.ACCENT.lower() not in win._settings_btn.styleSheet().lower()

    def test_source_chips_are_not_buttons(self, win):
        from PyQt6.QtWidgets import QLabel, QPushButton

        win.set_input_source("mixed")
        win.expand_live("hello")
        assert isinstance(win._mic_chip, QLabel)
        assert isinstance(win._sys_chip, QLabel)
        assert not isinstance(win._mic_chip, QPushButton)
        assert win._mic_chip.property("islandOn") is True

    def test_on_chip_text_contrasts_with_mint(self, win):
        from voiceink.ui import design_tokens as tok

        win.set_input_source("mixed")
        win.expand_live("hello")
        mic_css = win._mic_chip.styleSheet().lower()
        assert tok.ISLAND_MINT.lower() in mic_css
        if tok.ISLAND_MINT.lower() == "#0f7a4a":
            assert "#0a0a0c" not in mic_css
            assert tok.ACCENT_ON_DARK.lower() in mic_css

    def test_header_click_collapses_expanded_listen(self, win):
        win.show_listening()
        win.expand_live("hello")
        assert win.island_mode() == "expanded"
        win.collapse_live()
        assert win.island_mode() == "compact"
        assert win._listening_active is True


class TestIslandChrome:
    def test_hud_is_frameless_tool(self, win):
        flags = win.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint
        assert flags & Qt.WindowType.WindowStaysOnTopHint
        assert flags & Qt.WindowType.Tool

    def test_position_island_centers_near_top(self, qapp, win):
        win.resize(320, 56)
        position_island(win, width=320)
        screen = qapp.primaryScreen().availableGeometry()
        assert win.x() >= screen.x()
        assert win.y() <= screen.y() + 140

    def test_expand_shows_source_chips(self, win):
        win.set_input_source("mixed")
        win.show_listening()
        win.expand_live("hello")
        assert win._mic_chip.isVisible()
        assert win._sys_chip.isVisible()
        assert win._mic_chip.property("islandOn") is True
        assert win._sys_chip.property("islandOn") is True

    def test_microphone_source_marks_only_mic_chip(self, win):
        win.set_input_source("microphone")
        win.expand_live("hello")
        assert win._mic_chip.property("islandOn") is True
        assert win._sys_chip.property("islandOn") is False


class TestIslandSheetConstants:
    def test_sheet_width_constant(self):
        from voiceink.ui.island_chrome import ISLAND_SETTINGS_WIDTH

        assert ISLAND_SHEET_WIDTH >= 440
        assert ISLAND_SHEET_WIDTH <= 560
        assert ISLAND_SETTINGS_WIDTH >= ISLAND_SHEET_WIDTH
        assert ISLAND_SETTINGS_WIDTH <= 760
