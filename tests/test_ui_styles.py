"""Smoke tests for static UI style modules."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel


class TestAppStyles:
    def test_global_stylesheet_is_nonempty_string(self):
        from voiceink.ui.app_styles import GLOBAL_APP_STYLESHEET

        assert isinstance(GLOBAL_APP_STYLESHEET, str)
        assert len(GLOBAL_APP_STYLESHEET.strip()) > 0


class TestSettingsStyles:
    def test_window_css_available(self):
        import voiceink.ui.settings_styles as st

        assert hasattr(st, "WINDOW_CSS")
        assert isinstance(st.WINDOW_CSS, str)

    def test_interactive_styles_provide_visible_focus_rings(self):
        import voiceink.ui.settings_styles as st
        from voiceink.ui.settings_components import NAV_BTN_STYLE, ROW_RADIO_STYLE

        for style in (
            st.BTN_PRIMARY,
            st.BTN_GHOST_SM,
            st.BTN_DANGER_SM,
            NAV_BTN_STYLE,
            ROW_RADIO_STYLE,
        ):
            assert ":focus" in style
            assert "2px solid" in style

    def test_model_rating_labels_and_download_use_brand_accent(self):
        from voiceink.ui.model_card import ModelCard, format_model_ratings

        card = ModelCard(
            {
                "id": "demo",
                "name": "示例模型",
                "size_mb": 12,
                "description": "测试",
                "languages": "中文",
                "accuracy": 5,
                "speed": 4,
            },
            is_downloaded=False,
            is_active=False,
        )

        assert format_model_ratings(5, 4) == "高精度 · 较快"
        assert any("高精度" in label.text() for label in card.findChildren(QLabel))
        assert "#2563EB" in card._action_btn.styleSheet()

    def test_active_model_card_uses_subtle_current_state(self):
        from voiceink.ui.design_tokens import ACCENT, ACCENT_SOFT, SURFACE_PEARL, TEXT_SEC
        from voiceink.ui.model_card import ModelCard

        card = ModelCard(
            {
                "id": "demo",
                "name": "示例模型",
                "size_mb": 12,
                "description": "测试",
                "languages": "中文",
                "accuracy": 5,
                "speed": 4,
            },
            is_downloaded=True,
            is_active=True,
        )
        try:
            sheet = card.styleSheet()
            assert f"border: 1px solid {ACCENT}" in sheet
            assert f"border: 2px solid {ACCENT}" not in sheet

            current_badge = next(label for label in card.findChildren(QLabel) if label.text() == "当前")
            badge_sheet = current_badge.styleSheet()
            assert f"background: {SURFACE_PEARL}" in badge_sheet
            assert f"color: {TEXT_SEC}" in badge_sheet
            assert ACCENT_SOFT not in badge_sheet
        finally:
            card.close()


class TestSidebarVisualContracts:
    """Sidebar spacing / type / surface polish (Stitch alignment follow-up)."""

    def test_nav_bg_matches_cool_app_background(self):
        from voiceink.ui.design_tokens import BG, NAV_BG

        assert NAV_BG.upper() == BG.upper() == "#F3F4F6"

    def test_nav_btn_style_uses_single_left_bar_and_soft_wash(self):
        from voiceink.ui.design_tokens import ACCENT, NAV_SELECTED_BG, TEXT
        from voiceink.ui.settings_components import NAV_BTN_STYLE

        assert "font-size: 14px" in NAV_BTN_STYLE
        # One strong blue device (left bar) + soft wash; label stays dark.
        checked_block = NAV_BTN_STYLE.split(":checked")[1].split("}")[0]
        assert f"background: {NAV_SELECTED_BG}" in checked_block
        assert f"color: {TEXT}" in checked_block
        assert f"border-left: 3px solid {ACCENT}" in checked_block
        assert "border: 1px solid" not in checked_block
        assert "border: 2px solid" not in checked_block

    def test_page_title_avoids_negative_tracking(self):
        from voiceink.ui.design_tokens import TEXT_SEC
        from voiceink.ui.settings_components import PAGE_TITLE, SECTION_LABEL

        assert "font-size: 22px" in PAGE_TITLE or "font-size: 20px" in PAGE_TITLE
        assert "font-weight: 600" in PAGE_TITLE
        assert "letter-spacing: -" not in PAGE_TITLE
        assert "letter-spacing: 0" in PAGE_TITLE
        assert TEXT_SEC.lower() in SECTION_LABEL.lower()

    def test_group_and_hero_surfaces_are_soft_containers(self):
        from voiceink.ui.design_tokens import RADIUS_MD, SURFACE
        from voiceink.ui.settings_components import GROUP_STYLE, HERO_CARD_STYLE

        for style in (GROUP_STYLE, HERO_CARD_STYLE):
            assert f"background: {SURFACE}" in style
            assert f"border-radius: {RADIUS_MD}px" in style
            assert "border: none" in style or "border: 0" in style
            assert "1px solid" not in style
        assert HERO_CARD_STYLE == GROUP_STYLE.replace("settingsGroup", "settingsHeroCard")

    def test_usage_tip_bar_is_neutral(self):
        from voiceink.ui.design_tokens import HAIRLINE, SURFACE_PEARL, TEXT_SEC
        from voiceink.ui.settings_components import usage_tip_bar

        tip = usage_tip_bar("提示")
        try:
            assert f"background: {SURFACE_PEARL}" in tip.styleSheet()
            assert f"border: 1px solid {HAIRLINE}" in tip.styleSheet()
            label = next(child for child in tip.findChildren(QLabel) if child.text() == "提示")
            assert f"color: {TEXT_SEC}" in label.styleSheet()
        finally:
            tip.close()

    def test_vertical_choice_selected_uses_single_emphasis(self):
        from PyQt6.QtWidgets import QRadioButton

        from voiceink.ui.design_tokens import ACCENT, ACCENT_SOFT, HAIRLINE, NAV_SELECTED_BAR_PX, TEXT
        from voiceink.ui.settings_components import ChoiceCard, VerticalChoiceCard

        radio = QRadioButton()
        radio.setChecked(True)
        card = VerticalChoiceCard("仅麦克风", "收录你的说话声", "mic", radio)
        try:
            sheet = card.styleSheet()
            assert f"background: {ACCENT_SOFT}" in sheet
            assert f"border: 1px solid {HAIRLINE}" in sheet
            assert f"border-left: {NAV_SELECTED_BAR_PX}px solid {ACCENT}" in sheet
            title = next(label for label in card.findChildren(QLabel) if label.text() == "仅麦克风")
            assert f"color: {TEXT}" in title.styleSheet()
            assert f"color: {ACCENT}" not in title.styleSheet()
        finally:
            card.close()
            radio.close()

        radio2 = QRadioButton()
        radio2.setChecked(True)
        grid = ChoiceCard("仅麦克风", "收录你的说话声", "mic", radio2)
        try:
            sheet = grid.styleSheet()
            assert f"background: {ACCENT_SOFT}" in sheet
            assert f"border-left: {NAV_SELECTED_BAR_PX}px solid {ACCENT}" in sheet
            assert f"border: 2px solid {ACCENT}" not in sheet
            title = next(label for label in grid.findChildren(QLabel) if label.text() == "仅麦克风")
            assert f"color: {TEXT}" in title.styleSheet()
            assert f"color: {ACCENT}" not in title.styleSheet()
        finally:
            grid.close()
            radio2.close()

    def test_general_page_header_class_removed(self):
        import voiceink.ui.settings_components as components

        assert not hasattr(components, "GeneralPageHeader")

    def test_sidebar_brand_and_nav_metrics(self):
        import sys

        from PyQt6.QtWidgets import QApplication, QFrame, QPushButton

        from voiceink.ui.design_tokens import SURFACE, TEXT
        from voiceink.ui.nav_icons import nav_icon
        from voiceink.ui.settings_components import SettingsSidebar

        QApplication.instance() or QApplication(sys.argv)
        sidebar = SettingsSidebar(nav_icon)
        try:
            brand = next(
                lbl for lbl in sidebar.findChildren(QLabel) if lbl.text() == "VoiceInk"
            )
            assert TEXT.lower() in brand.styleSheet().lower()
            assert "letter-spacing: -" not in brand.styleSheet()

            status = next(
                w for w in sidebar.findChildren(QFrame)
                if w.objectName() == "sidebarStatusCard"
            )
            sheet = status.styleSheet().lower()
            assert "border: none" in sheet or "border: 0" in sheet or "1px solid" not in sheet
            assert "background: transparent" in sheet or SURFACE.lower() not in sheet

            from voiceink.ui.design_tokens import SETTINGS_SIDEBAR_BG
            from voiceink.ui.settings_components import NAV_BTN_STYLE

            checked = NAV_BTN_STYLE.split(":checked")[1].split("QPushButton")[0]
            assert TEXT.lower() in checked.lower() or "111827" in checked.lower()
            assert "border-left: 3px solid" in checked

            nav_btns = [
                b for b in sidebar.findChildren(QPushButton)
                if b.objectName() == "settingsNavBtn"
            ]
            assert len(nav_btns) == 4
            assert all(b.height() >= 40 for b in nav_btns)
            assert all(not b.text().startswith("  ") for b in nav_btns)
            assert "border-right" in sidebar.styleSheet()
            assert SETTINGS_SIDEBAR_BG.lower() in sidebar.styleSheet().lower()
        finally:
            sidebar.close()


class TestClassicDesktopTokens:
    def test_accent_and_surfaces(self):
        from voiceink.ui import design_tokens as t

        assert t.ACCENT.upper() == "#2563EB"
        assert t.BG.upper() == "#F3F4F6"
        assert "Inter" not in t.FONT
        assert t.RADIUS_MD == 8
        assert t.STATE_RECORD.upper() in {"#DC2626", "#E5484D", "#EF4444"}
        assert t.STATE_LISTEN == t.FLOAT_TEXT or t.STATE_LISTEN == t.FLOAT_TEXT_SEC
        assert t.STATE_RECOGNIZE in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
        assert t.STATE_POLISH in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
        assert t.SETTINGS_SIDEBAR_BG.upper() == t.SURFACE.upper()
        assert t.NAV_SELECTED_BG == t.ACCENT_SOFT
        assert "#" not in t.NAV_SELECTED_BG.lower() or t.NAV_SELECTED_BG.startswith("rgba")

    def test_toggle_on_uses_semantic_green(self):
        from voiceink.ui import design_tokens as t

        assert t.TOGGLE_ON.upper() == t.GREEN.upper()
        assert t.TOGGLE_ON_HOVER.upper() != t.TOGGLE_ON.upper()
        assert t.TOGGLE_ON_HOVER.upper().startswith("#")


class TestCursorInspiredSettingsPolish:
    def test_switch_on_track_uses_toggle_green(self):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.design_tokens import TOGGLE_ON, TOGGLE_ON_HOVER
        from voiceink.ui.settings_components import SwitchControl

        QApplication.instance() or QApplication(sys.argv)
        sw = SwitchControl()
        try:
            sw.setChecked(True, animate=False)
            color = sw._track_color()
            assert color.name().upper() == TOGGLE_ON.upper()
            sw.set_hovered(True)
            hover = sw._track_color()
            assert hover.name().upper() == TOGGLE_ON_HOVER.upper()
        finally:
            sw.close()

    def test_labeled_row_puts_control_on_the_right(self):
        import sys

        from PyQt6.QtWidgets import QApplication, QComboBox, QLabel

        from voiceink.ui.settings_components import labeled_row

        QApplication.instance() or QApplication(sys.argv)
        combo = QComboBox()
        row = labeled_row("麦克风", combo, "自动选择可用设备")
        try:
            labels = [lbl.text() for lbl in row.findChildren(QLabel)]
            assert "麦克风" in labels
            assert "自动选择可用设备" in labels
            lay = row.layout()
            assert lay.count() >= 2
            assert lay.itemAt(lay.count() - 1).widget() is combo
        finally:
            row.close()
            combo.close()

    def test_nav_icon_active_stays_neutral_not_accent(self):
        from pathlib import Path

        from voiceink.ui import nav_icons as mod
        from voiceink.ui.nav_icons import nav_icon

        idle = nav_icon("general", active=False)
        active = nav_icon("general", active=True)
        assert not idle.isNull() and not active.isNull()

        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "TEXT if active else TEXT_SEC" in src
        assert "ACCENT if active" not in src


class TestSettingsControlAlignment:
    """History numeric spins + scrollbar policy (settings-control-alignment)."""

    def test_window_css_styles_spinbox_like_inputs(self):
        import voiceink.ui.settings_styles as st
        from voiceink.ui.design_tokens import ACCENT_FOCUS, HAIRLINE, RADIUS_MD

        assert "QSpinBox {" in st.WINDOW_CSS or "QSpinBox {{" in st.WINDOW_CSS
        assert f"border: 1px solid {HAIRLINE}" in st.WINDOW_CSS
        assert f"border-radius: {RADIUS_MD}px" in st.WINDOW_CSS
        assert "QSpinBox:focus" in st.WINDOW_CSS
        assert f"2px solid {ACCENT_FOCUS}" in st.WINDOW_CSS
        # Styling ::up/down-button without arrows clears native steppers on Windows.
        assert "QSpinBox::up-button" not in st.WINDOW_CSS
        assert "QSpinBox::down-button" not in st.WINDOW_CSS
        # Same pitfall for combos: ::drop-down without ::down-arrow hides the chevron.
        assert "QComboBox::drop-down" not in st.WINDOW_CSS
        assert "QComboBox {" in st.WINDOW_CSS

    def test_numeric_control_width_token(self):
        from voiceink.ui.design_tokens import CONTROL_NUMERIC_WIDTH

        assert CONTROL_NUMERIC_WIDTH == 120

    def test_device_combo_width_token(self):
        from voiceink.ui.design_tokens import CONTROL_DEVICE_COMBO_WIDTH

        assert CONTROL_DEVICE_COMBO_WIDTH == 320

    def test_history_spins_share_fixed_width(self, config, monkeypatch):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.design_tokens import CONTROL_NUMERIC_WIDTH
        from voiceink.ui.settings_window import SettingsWindow

        QApplication.instance() or QApplication(sys.argv)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)

        win = SettingsWindow(config)
        try:
            assert win._history_retention_days_spin.minimumWidth() == CONTROL_NUMERIC_WIDTH
            assert win._history_max_entries_spin.minimumWidth() == CONTROL_NUMERIC_WIDTH
            assert win._history_retention_days_spin.maximumWidth() == CONTROL_NUMERIC_WIDTH
            assert win._history_max_entries_spin.maximumWidth() == CONTROL_NUMERIC_WIDTH
        finally:
            win.close()

    def test_device_combos_share_fixed_width(self, config, monkeypatch):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.design_tokens import CONTROL_DEVICE_COMBO_WIDTH
        from voiceink.ui.settings_window import SettingsWindow

        QApplication.instance() or QApplication(sys.argv)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)

        win = SettingsWindow(config)
        try:
            assert win._mic_device_combo.minimumWidth() == CONTROL_DEVICE_COMBO_WIDTH
            assert win._system_device_combo.minimumWidth() == CONTROL_DEVICE_COMBO_WIDTH
            assert win._mic_device_combo.maximumWidth() == CONTROL_DEVICE_COMBO_WIDTH
            assert win._system_device_combo.maximumWidth() == CONTROL_DEVICE_COMBO_WIDTH
        finally:
            win.close()

    def test_settings_page_scrollbar_as_needed(self):
        import sys

        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.settings_components import SettingsPage

        QApplication.instance() or QApplication(sys.argv)
        page = SettingsPage()
        try:
            assert (
                page.verticalScrollBarPolicy()
                == Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        finally:
            page.close()
