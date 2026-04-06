import sys
import os

# Ensure the project root is on sys.path so `voiceink` package can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def check_single_instance():
    """Ensure only one instance of VoiceInk runs at a time using a lock file."""
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "voiceink.lock")

    try:
        if os.path.exists(lock_file):
            with open(lock_file, "r") as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)
                return False  # Another instance is running
            except (OSError, ProcessLookupError):
                pass  # Old process is gone

        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


def cleanup_lock():
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "voiceink.lock")
    try:
        os.remove(lock_file)
    except Exception:
        pass


def main():
    if not check_single_instance():
        print("VoiceInk 已在运行中。")
        sys.exit(0)

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("VoiceInk")
    log.info("VoiceInk 启动中...")

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("VoiceInk")
    app.setStyle("Fusion")

    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif;
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
