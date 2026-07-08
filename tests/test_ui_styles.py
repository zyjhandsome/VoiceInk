"""Smoke tests for static UI style modules."""

from __future__ import annotations


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
