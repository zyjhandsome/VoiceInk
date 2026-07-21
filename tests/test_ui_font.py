"""UI font family resolution and surface consistency."""

from __future__ import annotations

from pathlib import Path


class TestResolveUiFontFamily:
    def test_prefers_segoe_ui_variable_when_present(self):
        from voiceink.ui.design_tokens import resolve_ui_font_family

        family = resolve_ui_font_family(
            available_families=("Segoe UI", "Segoe UI Variable", "Microsoft YaHei UI")
        )
        assert family == "Segoe UI Variable"

    def test_falls_back_to_yahei_when_segoe_variable_missing(self):
        from voiceink.ui.design_tokens import resolve_ui_font_family

        family = resolve_ui_font_family(
            available_families=("Consolas", "Microsoft YaHei UI", "Arial")
        )
        assert family == "Microsoft YaHei UI"

    def test_falls_back_to_segoe_ui_then_yahei_literal(self):
        from voiceink.ui.design_tokens import resolve_ui_font_family

        family = resolve_ui_font_family(available_families=("Segoe UI",))
        assert family == "Segoe UI"

        family = resolve_ui_font_family(available_families=())
        assert family == "Microsoft YaHei UI"


class TestApplyThemeRefreshesFont:
    def test_apply_theme_sets_module_font_from_resolver(self, monkeypatch):
        from voiceink.ui import design_tokens as dt
        from voiceink.ui.theme import apply_theme

        monkeypatch.setattr(
            dt,
            "resolve_ui_font_family",
            lambda **kwargs: "Mock UI Font",
        )
        apply_theme(mode="light", system_is_light=True)
        assert dt.FONT == '"Mock UI Font"'
        assert dt.FONT_DISPLAY == '"Mock UI Font"'

        from voiceink.ui.app_styles import build_global_stylesheet

        css = build_global_stylesheet("light")
        assert "Mock UI Font" in css


class TestFloatingWindowUsesResolvedFont:
    def test_setup_ui_does_not_hardcode_segoe_variable_literal(self):
        source = Path("voiceink/ui/floating_window.py").read_text(encoding="utf-8")
        assert 'QFont("Segoe UI Variable"' not in source


class TestTypographyScaleTokens:
    def test_type_tokens_match_design_ladder(self):
        from voiceink.ui import design_tokens as dt

        assert dt.TYPE_CAPTION == 11
        assert dt.TYPE_FOOTNOTE == 12
        assert dt.TYPE_BODY_SM == 13
        assert dt.TYPE_BODY == 14
        assert dt.TYPE_TITLE_SM == 15
        assert dt.TYPE_TITLE == 16
        assert dt.TYPE_HERO == 18
        assert dt.TYPE_TITLE_LG == 20
        assert dt.TYPE_DISPLAY == 22
        assert dt.TYPE_ICON_LG == 17

    def test_settings_reload_styles_uses_type_tokens(self):
        from voiceink.ui import design_tokens as dt
        from voiceink.ui import settings_components as sc

        sc.reload_styles()
        assert f"font-size: {dt.TYPE_TITLE_LG}px" in sc.PAGE_TITLE
        assert f"font-size: {dt.TYPE_FOOTNOTE}px" in sc.SECTION_LABEL
        assert f"font-size: {dt.TYPE_BODY_SM}px" in sc.PAGE_SUBTITLE

    def test_global_stylesheet_uses_type_body(self):
        from voiceink.ui import design_tokens as dt
        from voiceink.ui.app_styles import build_global_stylesheet

        assert f"font-size: {dt.TYPE_BODY}px" in build_global_stylesheet("light")


class TestThemeSurfacePolish:
    def test_chip_hover_press_tokens_exist(self):
        from voiceink.ui.design_tokens import tokens_for

        for axis in ("light", "dark"):
            t = tokens_for(axis)
            assert "CHIP_BG_HOVER" in t
            assert "CHIP_BG_PRESS" in t
            assert t["CHIP_BG_HOVER"] != t["CHIP_BG"]
            assert t["CHIP_BG_PRESS"] != t["CHIP_BG"]

    def test_float_reapply_uses_chip_tokens_not_string_replace(self):
        source = Path("voiceink/ui/floating_window.py").read_text(encoding="utf-8")
        assert "CHIP_BG.replace" not in source
        assert "CHIP_BG_HOVER" in source

    def test_usage_tip_bar_follows_dark_axis(self):
        import sys

        from PyQt6.QtWidgets import QApplication, QLabel

        from voiceink.ui import design_tokens as dt
        from voiceink.ui.settings_components import paint_usage_tip_bar, usage_tip_bar
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        tip = usage_tip_bar("提示")
        apply_theme(mode="dark", system_is_light=False)
        paint_usage_tip_bar(tip)
        assert dt.SURFACE_PEARL in tip.styleSheet()
        labels = tip.findChildren(QLabel)
        assert labels
        assert dt.TEXT_SEC in labels[0].styleSheet()


class TestCalloutThemeReapply:
    def test_info_callout_repaints_on_dark_activate(self):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui import design_tokens as dt
        from voiceink.ui.settings_components import info_callout, paint_info_callout
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        frame = info_callout("混合采集提示")
        light_bg = dt.tokens_for("light")["AMBER_SOFT"]
        dark_bg = dt.tokens_for("dark")["AMBER_SOFT"]
        assert light_bg in frame.styleSheet()

        apply_theme(mode="dark", system_is_light=False)
        paint_info_callout(frame)
        assert dark_bg in frame.styleSheet()
        assert light_bg not in frame.styleSheet() or light_bg == dark_bg


class TestMasterTypographyAlignment:
    def test_master_documents_font_strategy_and_type_ladder(self):
        from voiceink.ui import design_tokens as dt

        master = Path("design-system/MASTER.md").read_text(encoding="utf-8")
        assert "Segoe UI Variable" in master
        assert "Microsoft YaHei UI" in master
        assert "resolve_ui_font_family" in master or "FONT_STACK" in master
        assert "#16A34A" in master
        for name, size in (
            ("TYPE_CAPTION", dt.TYPE_CAPTION),
            ("TYPE_FOOTNOTE", dt.TYPE_FOOTNOTE),
            ("TYPE_BODY_SM", dt.TYPE_BODY_SM),
            ("TYPE_BODY", dt.TYPE_BODY),
            ("TYPE_TITLE_SM", dt.TYPE_TITLE_SM),
            ("TYPE_TITLE", dt.TYPE_TITLE),
            ("TYPE_ICON_LG", dt.TYPE_ICON_LG),
            ("TYPE_HERO", dt.TYPE_HERO),
            ("TYPE_TITLE_LG", dt.TYPE_TITLE_LG),
            ("TYPE_DISPLAY", dt.TYPE_DISPLAY),
        ):
            assert name in master
            assert f"{size}px" in master
