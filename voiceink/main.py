import sys
import os
import atexit
import logging
import threading
import ctypes

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_lock_file_path: str | None = None
_win_mutex = None

# 在 main() 配置日志前，使用临时 logger
_log = logging.getLogger("VoiceInk")


def check_single_instance() -> bool:
    """Ensure only one instance of VoiceInk runs at a time."""
    if sys.platform == "win32":
        # 使用 ctypes 创建 Windows 互斥锁（更可靠，不需要 pywin32）
        try:
            mutex_name = "Local\\VoiceInk_Single_Instance_Mutex"
            # CreateMutex 参数: lpMutexAttributes=NULL, bInitialOwner=False, lpName
            kernel32 = ctypes.windll.kernel32
            ERROR_ALREADY_EXISTS = 183  # Windows 错误代码

            mutex = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = kernel32.GetLastError()

            if last_error == ERROR_ALREADY_EXISTS:
                # 互斥锁已存在，说明已有实例运行
                if mutex:
                    kernel32.CloseHandle(mutex)
                return False

            global _win_mutex
            _win_mutex = mutex
            return True
        except Exception as e:
            _log.warning("互斥锁创建失败，使用文件锁: %s", e)

    # 非 Windows 或互斥锁失败时，使用文件锁
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
                    # 进程存在，说明已有实例
                    return False
                except (OSError, ProcessLookupError):
                    # 进程不存在，可以启动
                    pass

        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        return True
    except OSError as e:
        _log.warning("文件锁创建失败: %s", e)
        return True


def cleanup_lock():
    """清理单实例锁"""
    global _win_mutex

    # Windows: 关闭互斥锁句柄
    if _win_mutex:
        try:
            ctypes.windll.kernel32.CloseHandle(_win_mutex)
            _win_mutex = None
        except Exception:
            pass

    # 文件锁: 删除锁文件
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
    from PyQt6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("VoiceInk")
    app.setStyle("Fusion")

    # 设置应用图标，让 Windows 任务栏显示正确的图标
    from voiceink.ui.tray_icon import create_microphone_icon
    app_icon = create_microphone_icon(recording=False, size=64)
    app.setWindowIcon(app_icon)

    # Windows: 设置 AppUserModelID 让任务栏显示正确的图标
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VoiceInk.VoiceInkApp")
        except Exception:
            pass

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
