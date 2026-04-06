import sys
import time
import subprocess

import pyperclip
import pyautogui


def _get_foreground_window_win32():
    """Windows: get foreground window info via win32gui."""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return hwnd, title
    except Exception:
        return 0, ""


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
    """Returns (handle, title) of the foreground window, cross-platform."""
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

    def paste(self, text: str) -> str:
        """
        Paste text to the cursor position.
        Returns a status string: 'pasted', 'clipboard', or 'error:<msg>'.
        """
        if not text:
            return "error:空文本"

        hwnd, title = get_foreground_window_info()
        has_target = hwnd != 0 and title not in self.OWN_TITLES

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
