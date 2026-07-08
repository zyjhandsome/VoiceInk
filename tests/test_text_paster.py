import sys

import pytest

import voiceink.text_paster as tp
from voiceink.text_paster import TextPaster, get_foreground_window_info


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

    def test_paste_async_empty_text(self):
        paster = TextPaster()
        results = []
        paster.paste_async("", lambda r: results.append(r))
        assert results == ["error:空文本"]

    def test_restore_clipboard_flag(self):
        paster = TextPaster(restore_clipboard=True)
        assert paster.restore_clipboard is True


class TestPasteShortcut:
    def test_module_imports(self):
        from voiceink import text_paster
        assert hasattr(text_paster, "get_foreground_window_info")
        assert hasattr(text_paster, "_paste_shortcut")


class TestCrossPlatformSupport:
    def test_platform_detection(self):
        assert sys.platform in ["win32", "darwin", "linux"]


@pytest.fixture
def paste_env(monkeypatch):
    """Drive paste_async deterministically without a Qt event loop."""
    state = {
        "copied": [],
        "shortcut_calls": 0,
        "clipboard": "OLD",
        "fg_sequence": None,
    }

    monkeypatch.setattr(tp.QTimer, "singleShot", lambda ms, fn: fn())

    def _copy(text):
        state["copied"].append(text)
        state["clipboard"] = text

    monkeypatch.setattr(tp.pyperclip, "copy", _copy)
    monkeypatch.setattr(tp.pyperclip, "paste", lambda: state["clipboard"])

    def _shortcut():
        state["shortcut_calls"] += 1

    monkeypatch.setattr(tp, "_paste_shortcut", _shortcut)

    def set_foreground(sequence):
        seq = list(sequence)

        def _fg():
            return seq.pop(0) if len(seq) > 1 else seq[0]

        monkeypatch.setattr(tp, "get_foreground_window_info", _fg)

    state["set_foreground"] = set_foreground
    return state


class TestPasteAsyncFlow:
    def test_verified_paste_returns_pasted(self, paste_env):
        # Same foreground window before and after → verified paste.
        paste_env["set_foreground"]([(1234, "Notepad", 4242)])
        paster = TextPaster()
        results = []
        paster.paste_async("你好", results.append)
        assert results == ["pasted"]
        assert paste_env["shortcut_calls"] == 1
        assert "你好" in paste_env["copied"]

    def test_focus_changed_downgrades_to_clipboard(self, paste_env):
        # Foreground changes after paste → cannot confirm → clipboard.
        paste_env["set_foreground"]([(1234, "Editor", 1), (9999, "Other", 2)])
        paster = TextPaster()
        results = []
        paster.paste_async("文本", results.append)
        assert results == ["clipboard"]

    def test_own_window_skips_paste(self, paste_env):
        paste_env["set_foreground"]([(1, "VoiceInk", 1)])
        paster = TextPaster()
        results = []
        paster.paste_async("文本", results.append)
        assert results == ["clipboard"]
        assert paste_env["shortcut_calls"] == 0

    def test_no_target_wayland_hwnd_zero(self, paste_env):
        # hwnd == 0 (e.g. Wayland/no xdotool) → honest clipboard fallback.
        paste_env["set_foreground"]([(0, "", 0)])
        paster = TextPaster()
        results = []
        paster.paste_async("文本", results.append)
        assert results == ["clipboard"]
        assert paste_env["shortcut_calls"] == 0

    def test_shortcut_exception_downgrades_to_clipboard(self, paste_env, monkeypatch):
        paste_env["set_foreground"]([(1234, "Editor", 1)])

        def _boom():
            raise RuntimeError("blocked")

        monkeypatch.setattr(tp, "_paste_shortcut", _boom)
        paster = TextPaster()
        results = []
        paster.paste_async("文本", results.append)
        assert results == ["clipboard"]

    def test_restore_clipboard_after_verified_paste(self, paste_env):
        paste_env["set_foreground"]([(1234, "Editor", 1)])
        paster = TextPaster(restore_clipboard=True)
        results = []
        paster.paste_async("新文本", results.append)
        assert results == ["pasted"]
        # Original clipboard restored after a verified paste.
        assert paste_env["clipboard"] == "OLD"


class TestVerifyPasteTarget:
    def test_hwnd_zero_is_not_verified(self):
        assert tp._verify_paste_target(0) is False
