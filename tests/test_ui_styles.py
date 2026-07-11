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

    def test_nav_btn_style_is_readable_with_left_bar_only(self):
        from voiceink.ui.design_tokens import ACCENT, TEXT
        from voiceink.ui.settings_components import NAV_BTN_STYLE

        assert "font-size: 14px" in NAV_BTN_STYLE
        assert "border-left: 4px solid" in NAV_BTN_STYLE
        # Selected state must not become a full blue card outline.
        checked_block = NAV_BTN_STYLE.split(":checked")[1].split("}")[0]
        assert "border-left: 4px solid" in checked_block
        assert f"border-left: 4px solid {ACCENT}" in checked_block
        assert f"color: {TEXT}" in checked_block
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

    def test_group_and_hero_surfaces_are_decarded(self):
        from voiceink.ui.settings_components import GROUP_STYLE, HERO_CARD_STYLE

        for style in (GROUP_STYLE, HERO_CARD_STYLE):
            assert "background: transparent" in style
            assert "border: none" in style
            assert "border-radius: 0" in style
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

        from voiceink.ui.design_tokens import ACCENT, ACCENT_SOFT, HAIRLINE, TEXT
        from voiceink.ui.settings_components import VerticalChoiceCard

        radio = QRadioButton()
        radio.setChecked(True)
        card = VerticalChoiceCard("仅麦克风", "收录你的说话声", "mic", radio)
        try:
            sheet = card.styleSheet()
            assert f"background: {ACCENT_SOFT}" in sheet
            assert f"border: 1px solid {HAIRLINE}" in sheet
            assert f"border-left: 3px solid {ACCENT}" in sheet
            title = next(label for label in card.findChildren(QLabel) if label.text() == "仅麦克风")
            assert f"color: {TEXT}" in title.styleSheet()
            assert f"color: {ACCENT}" not in title.styleSheet()
        finally:
            card.close()
            radio.close()

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

            from voiceink.ui.settings_components import NAV_BTN_STYLE

            checked = NAV_BTN_STYLE.split(":checked")[1].split("QPushButton")[0]
            assert TEXT.lower() in checked.lower() or "111827" in checked.lower()
            assert "border-left: 4px solid" in checked

            nav_btns = [
                b for b in sidebar.findChildren(QPushButton)
                if b.objectName() == "settingsNavBtn"
            ]
            assert len(nav_btns) == 4
            assert all(b.height() >= 40 for b in nav_btns)
            assert all(not b.text().startswith("  ") for b in nav_btns)
            assert "border-right" in sidebar.styleSheet()
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
