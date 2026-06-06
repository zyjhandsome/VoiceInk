import pytest
from voiceink.text_paster import TextPaster, get_foreground_window_info
import sys


class TestTextPasterInit:
    def test_init(self):
        paster = TextPaster()
        assert paster is not None

    def test_own_titles_defined(self):
        paster = TextPaster()
        assert hasattr(paster, "OWN_TITLES")
        assert isinstance(paster.OWN_TITLES, set)
        assert "VoiceInk 设置" in paster.OWN_TITLES
        assert "VoiceInk" in paster.OWN_TITLES


class TestGetForegroundWindowInfo:
    def test_returns_tuple(self):
        info = get_foreground_window_info()
        assert isinstance(info, tuple)
        assert len(info) >= 2


class TestTextPasterIsOwnWindow:
    def test_windows_with_pid(self):
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")
        paster = TextPaster()
        import os
        info = (0, "Test", os.getpid())
        assert paster._is_own_window(info) is True

    def test_different_pid(self):
        paster = TextPaster()
        import os
        info = (0, "Test", os.getpid() + 9999)
        assert paster._is_own_window(info) is False

    def test_own_title(self):
        paster = TextPaster()
        info = (123, "VoiceInk", 9999)
        assert paster._is_own_window(info) is True

    def test_own_settings_title(self):
        paster = TextPaster()
        info = (123, "VoiceInk 设置", 9999)
        assert paster._is_own_window(info) is True

    def test_other_title(self):
        paster = TextPaster()
        info = (123, "Notepad", 9999)
        assert paster._is_own_window(info) is False


class TestTextPasterPaste:
    def test_empty_text_returns_error(self):
        paster = TextPaster()
        result = paster.paste("")
        assert result.startswith("error:")

    def test_paste_returns_status(self):
        paster = TextPaster()
        result = paster.paste("测试文本")
        assert result in ["pasted", "clipboard", "error:"]


class TestPasteShortcut:
    def test_module_imports(self):
        from voiceink import text_paster
        assert hasattr(text_paster, "get_foreground_window_info")
        assert hasattr(text_paster, "_paste_shortcut")


class TestCrossPlatformSupport:
    def test_platform_detection(self):
        assert sys.platform in ["win32", "darwin", "linux"]
