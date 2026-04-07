import os
import sys
import time
import subprocess

import pyperclip
import pyautogui


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


def _paste_shortcut():
    """Trigger the system paste shortcut, platform-aware."""
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.hotkey("ctrl", "v")


class TextPaster:
    OWN_TITLES = {"VoiceInk 设置", "VoiceInk"}

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
        Paste text to the cursor position.
        Returns a status string: 'pasted', 'clipboard', or 'error:<msg>'.
        """
        if not text:
            return "error:空文本"

        info = get_foreground_window_info()
        hwnd = info[0]
        has_target = hwnd != 0 and not self._is_own_window(info)

        try:
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(text)

            if has_target:
                time.sleep(0.15)
                _paste_shortcut()
                time.sleep(0.1)

                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass

                return "pasted"
            else:
                return "clipboard"

        except Exception as e:
            return f"error:{str(e)}"
