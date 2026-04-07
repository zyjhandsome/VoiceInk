import sys
import os
import atexit
import logging
import threading

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_lock_file_path: str | None = None


def check_single_instance() -> bool:
    """Ensure only one instance of VoiceInk runs at a time using a lock file."""
    global _lock_file_path
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "voiceink.lock")
    _lock_file_path = lock_file

    try:
        if os.path.exists(lock_file):
            with open(lock_file, "r") as f:
                old_pid_str = f.read().strip()
            if old_pid_str.isdigit():
                old_pid = int(old_pid_str)
                try:
                    os.kill(old_pid, 0)
                    if sys.platform == "win32":
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        handle = kernel32.OpenProcess(0x0400, False, old_pid)
                        if handle:
                            kernel32.CloseHandle(handle)
                            return False
                    else:
                        return False
                except (OSError, ProcessLookupError):
                    pass

        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


def cleanup_lock():
    if _lock_file_path:
        try:
            os.remove(_lock_file_path)
        except OSError:
            pass


def _install_exception_hooks(log: logging.Logger):
    """Install global exception handlers so crashes are logged, not silently lost."""

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))

    def _threading_excepthook(args):
        if args.exc_type is SystemExit:
            return
        log.critical(
            "线程 %s 未捕获异常", args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _excepthook
    threading.excepthook = _threading_excepthook


def main():
    if not check_single_instance():
        print("VoiceInk 已在运行中。")
        sys.exit(0)

    atexit.register(cleanup_lock)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("VoiceInk")
    _install_exception_hooks(log)
    log.info("VoiceInk 启动中...")

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("VoiceInk")
    app.setStyle("Fusion")

    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC",
                         "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 16px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
    """)

    from voiceink.app import App
    voice_ink = App()
    voice_ink.start()

    exit_code = app.exec()
    cleanup_lock()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
