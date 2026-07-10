import logging
import os
import sys
import subprocess
from typing import Callable

import pyperclip
import pyautogui
from PyQt6.QtCore import QTimer

log = logging.getLogger("VoiceInk")

PASTE_DELAY_MS = 150
VERIFY_AFTER_PASTE_MS = 120


def _get_foreground_window_win32():
    """Windows: get foreground window info via win32gui. Returns (hwnd, title, pid)."""
    try:
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return hwnd, title, pid
    except Exception:
        return 0, "", 0


def _get_foreground_window_macos():
    """macOS: get frontmost application name via osascript."""
    try:
        out = subprocess.check_output(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process whose frontmost is true'],
            timeout=2, text=True,
        ).strip()
        return 1, out
    except Exception:
        return 0, ""


def _get_foreground_window_linux():
    """Linux/X11: get active window title via xdotool."""
    try:
        wid = subprocess.check_output(
            ["xdotool", "getactivewindow"], timeout=2, text=True,
        ).strip()
        title = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowname"], timeout=2, text=True,
        ).strip()
        return int(wid), title
    except Exception:
        return 0, ""


def get_foreground_window_info():
    """Returns (handle, title) of the foreground window, cross-platform.
    On Windows, also provides PID as 3rd element."""
    if sys.platform == "win32":
        return _get_foreground_window_win32()
    elif sys.platform == "darwin":
        return _get_foreground_window_macos()
    else:
        return _get_foreground_window_linux()


def get_foreground_process_name() -> str:
    """Return foreground process basename only (D4 privacy: no window title).

    Windows: resolve PID via win32api/win32process. Elsewhere: best-effort "" .
    """
    try:
        info = get_foreground_window_info()
        if sys.platform != "win32":
            return ""
        if len(info) < 3:
            return ""
        pid = info[2]
        if not pid:
            return ""
        import win32api
        import win32con
        import win32process

        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )
        try:
            path = win32process.GetModuleFileNameEx(handle, 0)
        finally:
            try:
                win32api.CloseHandle(handle)
            except Exception:
                pass
        return os.path.basename(path) if path else ""
    except Exception:
        return ""


def _paste_shortcut():
    """Trigger the system paste shortcut, platform-aware."""
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")


def _verify_paste_target(hwnd_before: int) -> bool:
    """Best-effort check that focus did not move away before paste completed."""
    if hwnd_before == 0:
        return False
    info_after = get_foreground_window_info()
    return info_after[0] == hwnd_before


class TextPaster:
    OWN_TITLES = {"VoiceInk 设置", "VoiceInk"}

    def __init__(self, restore_clipboard: bool = False):
        self.restore_clipboard = restore_clipboard

    def _is_own_window(self, info: tuple) -> bool:
        """Check if the foreground window belongs to this process."""
        if sys.platform == "win32" and len(info) >= 3:
            _, title, pid = info
            if pid == os.getpid():
                return True
        else:
            _, title = info[:2]
        return title in self.OWN_TITLES

    def paste(self, text: str) -> str:
        """
        Synchronous paste (no verification). Prefer paste_async in the UI thread.
        Returns: 'pasted', 'clipboard', or 'error:<msg>'.
        """
        if not text:
            return "error:空文本"

        info = get_foreground_window_info()
        hwnd = info[0]
        has_target = hwnd != 0 and not self._is_own_window(info)

        pyperclip.copy(text)

        if has_target:
            _paste_shortcut()
            return "pasted"
        return "clipboard"

    def paste_async(self, text: str, callback: Callable[[str], None]) -> None:
        """
        Copy text and attempt paste after a short delay, then verify focus
        stayed on the target window. Invokes callback with result status.
        """
        if not text:
            callback("error:空文本")
            return

        info = get_foreground_window_info()
        hwnd = info[0]
        has_target = hwnd != 0 and not self._is_own_window(info)

        old_clipboard = None
        if self.restore_clipboard:
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass

        try:
            pyperclip.copy(text)
        except Exception as e:
            log.error("写入剪贴板失败: %s", e)
            callback(f"error:{e}")
            return

        if not has_target:
            callback("clipboard")
            return

        def _do_paste():
            try:
                _paste_shortcut()
            except Exception as e:
                log.warning("模拟粘贴失败: %s", e)
                callback("clipboard")
                return
            QTimer.singleShot(VERIFY_AFTER_PASTE_MS, _verify)

        def _verify():
            if _verify_paste_target(hwnd):
                if self.restore_clipboard and old_clipboard is not None:
                    try:
                        pyperclip.copy(old_clipboard)
                    except Exception:
                        pass
                callback("pasted")
            else:
                log.info("粘贴校验未通过（焦点已切换或目标不可粘贴），保留剪贴板内容")
                try:
                    pyperclip.copy(text)
                except Exception:
                    pass
                callback("clipboard")

        QTimer.singleShot(PASTE_DELAY_MS, _do_paste)
