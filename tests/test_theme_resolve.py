"""Theme mode resolution, defaults, and config persistence."""

from __future__ import annotations

from pathlib import Path


class TestResolveEffectiveTheme:
    def test_explicit_light(self):
        from voiceink.ui.theme import resolve_effective_theme

        assert resolve_effective_theme("light") == "light"

    def test_explicit_dark(self):
        from voiceink.ui.theme import resolve_effective_theme

        assert resolve_effective_theme("dark") == "dark"

    def test_system_follows_probe(self):
        from voiceink.ui.theme import resolve_effective_theme

        assert resolve_effective_theme("system", system_is_light=True) == "light"
        assert resolve_effective_theme("system", system_is_light=False) == "dark"

    def test_unknown_mode_falls_back_to_system(self):
        from voiceink.ui.theme import resolve_effective_theme

        assert resolve_effective_theme("neon", system_is_light=False) == "dark"
        assert resolve_effective_theme("", system_is_light=True) == "light"


class TestThemeConfigDefault:
    def test_default_theme_mode_is_system(self, tmp_path: Path):
        from voiceink.config import Config

        cfg = Config(config_dir=tmp_path)
        assert cfg.get("appearance.theme_mode") == "system"

    def test_theme_mode_persists_across_reload(self, tmp_path: Path):
        from voiceink.config import Config

        cfg = Config(config_dir=tmp_path)
        cfg.set("appearance.theme_mode", "dark")
        cfg.save_immediate()

        cfg2 = Config(config_dir=tmp_path)
        assert cfg2.get("appearance.theme_mode") == "dark"


class TestTokensFor:
    def test_light_and_dark_differ_on_background(self):
        from voiceink.ui.design_tokens import tokens_for

        light = tokens_for("light")
        dark = tokens_for("dark")
        assert light["BG"] != dark["BG"]
        assert light["TEXT"] != dark["TEXT"]
        assert dark["BG"].startswith("#") or dark["BG"].startswith("rgb")

    def test_activate_updates_module_level_bg(self):
        from voiceink.ui import design_tokens as dt

        dt.activate("dark")
        assert dt.BG == dt.tokens_for("dark")["BG"]
        dt.activate("light")
        assert dt.BG == dt.tokens_for("light")["BG"]


class TestSettingsAppearanceEntry:
    def test_appearance_combo_exists_and_persists(self, tmp_path: Path, monkeypatch):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.config import Config
        from voiceink.ui.settings_window import SettingsWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)

        cfg = Config(config_dir=tmp_path)
        win = SettingsWindow(cfg)

        assert win._theme_combo.findData("system") >= 0
        assert win._theme_combo.findData("light") >= 0
        assert win._theme_combo.findData("dark") >= 0

        dark_index = win._theme_combo.findData("dark")
        win._theme_combo.setCurrentIndex(dark_index)
        assert cfg.get("appearance.theme_mode") == "dark"

        apply_theme(mode="dark", surfaces=(win,))
        assert "#111827" in win.styleSheet()

    def test_general_labels_follow_dark_text_tokens(self, tmp_path: Path, monkeypatch):
        """Regression: inline styles must not stay locked to light TEXT on dark BG."""
        import sys

        from PyQt6.QtWidgets import QApplication, QLabel

        from voiceink.config import Config
        from voiceink.ui import design_tokens as tok
        from voiceink.ui.settings_components import CompactPickCard, ToggleOptionRow
        from voiceink.ui.settings_window import SettingsWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)

        win = SettingsWindow(Config(config_dir=tmp_path))
        try:
            apply_theme(mode="dark", surfaces=(win,))
            assert tok.TEXT.upper() == "#F9FAFB"

            title = win._general_hero._title.styleSheet().upper()
            assert "#F9FAFB" in title

            row = win._auto_start_row
            assert isinstance(row, ToggleOptionRow)
            row_title = next(
                lb for lb in row.findChildren(QLabel) if lb.property("viRole") == "rowTitle"
            )
            assert tok.TEXT.upper() in row_title.styleSheet().upper()
            assert "#111827" not in row_title.styleSheet().upper()

            picks = win.findChildren(CompactPickCard)
            assert picks
            pick_title = next(
                lb for lb in picks[0].findChildren(QLabel)
                if lb.property("viRole") == "pickTitle"
            )
            assert tok.TEXT.upper() in pick_title.styleSheet().upper()

            assert tok.TEXT_DIM.upper() in win._theme_desc_label.styleSheet().upper()
        finally:
            win.close()
            apply_theme(mode="light")


class TestSurfaceThemeReapply:
    def test_system_mode_updates_application_palette_for_both_axes(self):
        import sys

        from PyQt6.QtGui import QColor, QPalette
        from PyQt6.QtWidgets import QApplication

        from voiceink.ui import design_tokens as tok
        from voiceink.ui.theme import apply_theme

        app = QApplication.instance() or QApplication(sys.argv)
        try:
            assert apply_theme(app, mode="system", system_is_light=False) == "dark"
            assert (
                app.palette().color(QPalette.ColorRole.Window).name().upper()
                == QColor(tok.BG).name().upper()
            )

            assert apply_theme(app, mode="system", system_is_light=True) == "light"
            assert (
                app.palette().color(QPalette.ColorRole.Window).name().upper()
                == QColor(tok.BG).name().upper()
            )
        finally:
            apply_theme(app, mode="light")

    def test_float_light_not_locked_to_legacy_dark(self):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.floating_window import FloatingWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        win = FloatingWindow()
        apply_theme(mode="light", surfaces=(win,))
        sheet = win._container.styleSheet()
        assert "243, 244, 246" in sheet or "#F3F4F6" in sheet.upper() or "#FFFFFF" in sheet.upper()
        assert "39, 39, 41" not in sheet

    def test_tray_menu_stylesheet_follows_dark(self):
        from voiceink.ui.theme import apply_theme
        from voiceink.ui.tray_icon import _menu_stylesheet

        apply_theme(mode="dark")
        css = _menu_stylesheet()
        assert "#1F2937" in css.upper() or "#111827" in css.upper()
        assert "#F9FAFB" in css.upper()

    def test_history_spinbox_widths_equal_under_dark(self, tmp_path: Path, monkeypatch):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.config import Config
        from voiceink.ui.settings_window import SettingsWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        monkeypatch.setattr(SettingsWindow, "_rebuild_model_cards", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_about_info", lambda self: None)
        monkeypatch.setattr(SettingsWindow, "_refresh_audio_device_lists", lambda self: None)

        win = SettingsWindow(Config(config_dir=tmp_path))
        apply_theme(mode="dark", surfaces=(win,))
        assert (
            win._history_retention_days_spin.width()
            == win._history_max_entries_spin.width()
        )

    def test_history_reapply_keeps_construct_visual_language(self, tmp_path: Path):
        """Theme reapply must not regress History construct QSS (focus/hover/accent)."""
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.history_store import HistoryStore
        from voiceink.ui.history_window import HistoryWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        store = HistoryStore(tmp_path / "history.db")
        win = HistoryWindow(store)
        apply_theme(mode="dark", surfaces=(win,))

        search = win._search_edit.styleSheet()
        assert "QLineEdit:focus" in search
        assert "#374151" in search.upper()  # dark SURFACE_PEARL

        list_css = win._session_list.styleSheet()
        assert "border-left" in list_css
        assert "item:hover" in list_css
        assert "background: transparent" in list_css

        details = win._details.styleSheet()
        assert "background: transparent" in details
        assert "border: none" in details

        assert hasattr(win, "_title_label")
        title_css = win._title_label.styleSheet().upper()
        assert "#F9FAFB" in title_css  # dark TEXT

        undo_css = win._undo_bar.styleSheet().upper()
        assert "#374151" in undo_css  # dark SURFACE_PEARL

        feedback_css = win._feedback_label.styleSheet().upper()
        assert "#F9FAFB" in feedback_css

        store.close()

    def test_info_callout_uses_token_border_not_emoji(self):
        import sys

        from PyQt6.QtWidgets import QApplication, QLabel

        from voiceink.ui.settings_components import info_callout
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        apply_theme(mode="light")
        frame = info_callout("混合采集提示")
        css = frame.styleSheet().upper()
        assert "#F5E6B8" in css or "CALLOUT" in css
        labels = [c.text() for c in frame.findChildren(QLabel)]
        assert "混合采集提示" in labels
        # Prototype v3 callout is text-only (no leading glyph / emoji).
        assert "!" not in labels
        assert "⚠" not in labels
        assert "ℹ" not in labels

    def test_tray_icons_use_semantic_tokens_and_rebuild_on_reapply(self):
        import inspect
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.theme import apply_theme
        from voiceink.ui import tray_icon as tray_mod
        from voiceink.ui.tray_icon import TrayIcon

        src = inspect.getsource(tray_mod.create_microphone_icon)
        assert "#FF6961" not in src
        assert "#D64545" not in src
        assert "STATE_RECORD" in src

        QApplication.instance() or QApplication(sys.argv)
        tray = TrayIcon()
        before = tray._recording_icon
        apply_theme(mode="light", surfaces=(tray,))
        assert tray._recording_icon is not before
        assert not tray._recording_icon.isNull()
        assert not tray._attention_icon.isNull()

    def test_float_close_hover_is_theme_aware(self):
        import sys

        from PyQt6.QtWidgets import QApplication

        from voiceink.ui.floating_window import FloatingWindow
        from voiceink.ui.theme import apply_theme

        QApplication.instance() or QApplication(sys.argv)
        win = FloatingWindow()
        apply_theme(mode="light", surfaces=(win,))
        sheet = win._close_btn.styleSheet()
        assert "rgba(255, 255, 255" not in sheet
        assert "CHIP_BG" in sheet or "rgba(17, 24, 39" in sheet or "#" in sheet
