"""Smoke tests for static UI style modules."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel


def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def _relative_luminance(hex_color: str) -> float:
    channels = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in _rgb(hex_color)
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def _blend(foreground: str, background: str, alpha: float) -> str:
    front = _rgb(foreground)
    back = _rgb(background)
    channels = [
        round((front[index] * alpha + back[index] * (1 - alpha)) * 255)
        for index in range(3)
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


class TestAppStyles:
    def test_global_stylesheet_is_nonempty_string(self):
        from voiceink.ui.app_styles import GLOBAL_APP_STYLESHEET

        assert isinstance(GLOBAL_APP_STYLESHEET, str)
        assert len(GLOBAL_APP_STYLESHEET.strip()) > 0


class TestColorContrastContracts:
    def test_small_text_and_semantic_text_meet_aa_on_light_surfaces(self):
        from voiceink.ui.design_tokens import tokens_for

        light = tokens_for("light")
        for foreground, background in (
            (light["TEXT_DIM"], light["BG"]),
            (light["ACCENT_TEXT"], light["BG"]),
            (light["RED"], light["BG"]),
            (light["GREEN"], light["BG"]),
            ("#FFFFFF", light["PRIMARY_CONTAINER"]),
        ):
            assert _contrast(foreground, background) >= 4.5

    def test_dark_selected_text_and_primary_buttons_meet_aa(self):
        from voiceink.ui.design_tokens import tokens_for

        dark = tokens_for("dark")
        selected_background = _blend(
            dark["ACCENT"], dark["SETTINGS_SIDEBAR_BG"], 0.16
        )
        assert _contrast(dark["ACCENT_TEXT"], selected_background) >= 4.5
        for background in (
            dark["PRIMARY_CONTAINER"],
            dark["PRIMARY_CONTAINER_HOVER"],
            dark["PRIMARY_CONTAINER_PRESSED"],
        ):
            assert _contrast("#FFFFFF", background) >= 4.5


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

            import voiceink.ui.settings_styles as st

            assert card._delete_btn is not None
            assert card._delete_btn.styleSheet() == st.BTN_GHOST_SM
        finally:
            card.close()


class TestSidebarVisualContracts:
    """Sidebar spacing / type / surface polish (Stitch alignment follow-up)."""

    def test_nav_bg_matches_cool_app_background(self):
        from voiceink.ui import design_tokens as t

        t.activate("light")
        assert t.NAV_BG.upper() == t.BG.upper() == "#F3F4F6"

    def test_nav_btn_style_uses_single_left_bar_and_soft_wash(self):
        from voiceink.ui.design_tokens import ACCENT, NAV_SELECTED_BG
        from voiceink.ui.settings_components import NAV_BTN_STYLE

        assert "font-size: 13px" in NAV_BTN_STYLE
        # Prototype v3: left bar + soft wash + accent label.
        checked_block = NAV_BTN_STYLE.split(":checked")[1].split("}")[0]
        assert f"background: {NAV_SELECTED_BG}" in checked_block
        assert f"color: {ACCENT}" in checked_block
        assert f"border-left: 3px solid {ACCENT}" in checked_block
        assert "border: 1px solid" not in checked_block
        assert "border: 2px solid" not in checked_block

    def test_page_title_avoids_negative_tracking(self):
        from voiceink.ui.design_tokens import TEXT_DIM
        from voiceink.ui.settings_components import PAGE_TITLE, SECTION_LABEL

        assert "font-size: 20px" in PAGE_TITLE
        assert "font-weight: 600" in PAGE_TITLE
        assert "letter-spacing: -" not in PAGE_TITLE
        assert "letter-spacing: 0" in PAGE_TITLE
        assert TEXT_DIM.lower() in SECTION_LABEL.lower()
        assert "font-size: 12px" in SECTION_LABEL

    def test_group_and_hero_surfaces_are_bordered_cards(self):
        from voiceink.ui.design_tokens import BORDER, RADIUS_LG, SURFACE
        from voiceink.ui.settings_components import GROUP_STYLE, HERO_CARD_STYLE

        for style in (GROUP_STYLE, HERO_CARD_STYLE):
            assert f"background: {SURFACE}" in style
            assert f"border-radius: {RADIUS_LG}px" in style
            assert f"border: 1px solid {BORDER}" in style
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

        from voiceink.ui.design_tokens import BORDER, SURFACE_PEARL, TEXT
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
            assert SURFACE_PEARL.lower() in sheet
            assert f"1px solid {BORDER}".lower() in sheet

            from voiceink.ui.design_tokens import SETTINGS_SIDEBAR_BG
            from voiceink.ui.settings_components import NAV_BTN_STYLE

            from voiceink.ui.design_tokens import ACCENT

            checked = NAV_BTN_STYLE.split(":checked")[1].split("QPushButton")[0]
            assert ACCENT.lower() in checked.lower() or "2563eb" in checked.lower()
            assert "border-left: 3px solid" in checked

            nav_btns = [
                b for b in sidebar.findChildren(QPushButton)
                if b.objectName() == "settingsNavBtn"
            ]
            assert len(nav_btns) == 4
            assert all(b.height() >= 34 for b in nav_btns)
            assert all(not b.text().startswith("  ") for b in nav_btns)
            assert "border-right" in sidebar.styleSheet()
            assert SETTINGS_SIDEBAR_BG.lower() in sidebar.styleSheet().lower()
        finally:
            sidebar.close()


class TestClassicDesktopTokens:
    def test_accent_and_surfaces(self):
        from voiceink.ui import design_tokens as t

        t.activate("light")
        light = t.tokens_for("light")
        assert t.ACCENT.upper() == light["ACCENT"].upper() == "#2563EB"
        assert t.BG.upper() == light["BG"].upper() == "#F3F4F6"
        assert "Inter" not in t.FONT
        assert t.RADIUS_MD == 8
        assert t.STATE_RECORD.upper() in {"#DC2626", "#E5484D", "#EF4444", "#F87171"}
        assert t.STATE_LISTEN == t.FLOAT_TEXT or t.STATE_LISTEN == t.FLOAT_TEXT_SEC
        assert t.STATE_RECOGNIZE in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
        assert t.STATE_POLISH in (t.FLOAT_TEXT, t.FLOAT_TEXT_SEC)
        assert t.SETTINGS_SIDEBAR_BG.upper() == t.SURFACE.upper()
        assert t.NAV_SELECTED_BG == t.ACCENT_SOFT
        assert "#" not in t.NAV_SELECTED_BG.lower() or t.NAV_SELECTED_BG.startswith("rgba")

    def test_dark_tokens_differ_from_light(self):
        from voiceink.ui.design_tokens import tokens_for

        assert tokens_for("light")["BG"] != tokens_for("dark")["BG"]
        assert tokens_for("dark")["TEXT"].upper() == "#F9FAFB"

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

    def test_switch_track_is_compact(self):
        from voiceink.ui.settings_components import SwitchControl

        assert SwitchControl._TRACK_W == 36
        assert SwitchControl._TRACK_H == 20

    def test_ghost_sm_button_reserves_cjk_label_space(self):
        import voiceink.ui.settings_styles as st

        assert "min-height: 32px" in st.BTN_GHOST_SM
        assert "font-size: 13px" in st.BTN_GHOST_SM
        assert "QPushButton:checked" in st.BTN_GHOST_SM

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
        from voiceink.ui.design_tokens import ACCENT_FOCUS, CONTROL_BORDER, RADIUS_MD, SURFACE

        assert "QSpinBox {" in st.WINDOW_CSS or "QSpinBox {{" in st.WINDOW_CSS
        assert f"border: 1px solid {CONTROL_BORDER}" in st.WINDOW_CSS
        assert f"background: {SURFACE}" in st.WINDOW_CSS
        assert f"border-radius: {RADIUS_MD}px" in st.WINDOW_CSS
        assert "QSpinBox:focus" in st.WINDOW_CSS
        assert f"2px solid {ACCENT_FOCUS}" in st.WINDOW_CSS
        # Flat steppers: buttons + explicit chevron images (bare buttons hide arrows).
        assert "QSpinBox::up-button" in st.WINDOW_CSS
        assert "QSpinBox::down-button" in st.WINDOW_CSS
        assert "QSpinBox::up-arrow" in st.WINDOW_CSS
        assert "QSpinBox::down-arrow" in st.WINDOW_CSS
        assert "spin_chevron_up.png" in st.WINDOW_CSS
        assert "min-height: 32px" in st.build_spinbox_css()
        from pathlib import Path

        assert Path(st._spin_arrow_urls()[0]).is_file()
        assert Path(st._spin_arrow_urls()[1]).is_file()
        # Same pitfall for combos: ::drop-down without ::down-arrow hides the chevron.
        assert "QComboBox::drop-down" not in st.WINDOW_CSS
        assert "QComboBox {" in st.WINDOW_CSS
        assert f"border: 1px solid {CONTROL_BORDER}" in st.WINDOW_CSS

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
        from PyQt6.QtWidgets import QApplication, QSizePolicy

        from voiceink.ui.settings_components import SettingsPage, footnote

        QApplication.instance() or QApplication(sys.argv)
        page = SettingsPage()
        try:
            assert (
                page.verticalScrollBarPolicy()
                == Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            # No overflow → reserve gutter so later tall content won't widen/narrow.
            page._sync_scroll_gutter(0, 0)
            assert page.viewportMargins().right() > 0
            page._sync_scroll_gutter(0, 100)
            assert page.viewportMargins().right() == 0
            body = page.widget()
            assert body is not None
            assert body.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum
            note = footnote("测试脚注换行高度不应虚高")
            assert note.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum
        finally:
            page.close()
