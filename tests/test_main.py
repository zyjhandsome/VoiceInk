"""Tests for single-instance locking and crash hooks (voiceink/main.py)."""

from __future__ import annotations

import logging
import tempfile
import types

import pytest

import voiceink.main as main


@pytest.fixture
def temp_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(main, "_lock_file_path", None, raising=False)
    monkeypatch.setattr(main, "_win_mutex", None, raising=False)
    yield tmp_path
    main.cleanup_lock()


class TestFileLockFallback:
    def test_first_instance_acquires_lock(self, monkeypatch, temp_lock):
        monkeypatch.setattr(main.sys, "platform", "linux")
        assert main.check_single_instance() is True
        assert (temp_lock / "voiceink.lock").exists()

    def test_second_instance_blocked_when_pid_alive(self, monkeypatch, temp_lock):
        monkeypatch.setattr(main.sys, "platform", "linux")
        assert main.check_single_instance() is True
        # A living PID (our own) in the lock → second check refuses to start.
        (temp_lock / "voiceink.lock").write_text(str(__import__("os").getpid()))
        assert main.check_single_instance() is False

    def test_stale_pid_allows_start(self, monkeypatch, temp_lock):
        monkeypatch.setattr(main.sys, "platform", "linux")

        def _dead_pid(pid, sig):
            raise OSError("no such process")

        monkeypatch.setattr(main.os, "kill", _dead_pid)
        (temp_lock / "voiceink.lock").write_text("999999")
        assert main.check_single_instance() is True

    def test_cleanup_removes_lock_file(self, monkeypatch, temp_lock):
        monkeypatch.setattr(main.sys, "platform", "linux")
        main.check_single_instance()
        assert (temp_lock / "voiceink.lock").exists()
        main.cleanup_lock()
        assert not (temp_lock / "voiceink.lock").exists()


class TestWindowsMutex:
    def test_mutex_first_instance(self, monkeypatch):
        monkeypatch.setattr(main.sys, "platform", "win32")

        fake_kernel = types.SimpleNamespace(
            CreateMutexW=lambda a, b, name: 111,
            GetLastError=lambda: 0,
            CloseHandle=lambda h: True,
        )
        fake_windll = types.SimpleNamespace(kernel32=fake_kernel)
        monkeypatch.setattr(main.ctypes, "windll", fake_windll, raising=False)
        monkeypatch.setattr(main, "_win_mutex", None, raising=False)

        assert main.check_single_instance() is True
        assert main._win_mutex == 111
        main._win_mutex = None

    def test_mutex_already_exists_blocks(self, monkeypatch):
        monkeypatch.setattr(main.sys, "platform", "win32")

        closed = []
        fake_kernel = types.SimpleNamespace(
            CreateMutexW=lambda a, b, name: 222,
            GetLastError=lambda: 183,  # ERROR_ALREADY_EXISTS
            CloseHandle=lambda h: closed.append(h),
        )
        fake_windll = types.SimpleNamespace(kernel32=fake_kernel)
        monkeypatch.setattr(main.ctypes, "windll", fake_windll, raising=False)
        monkeypatch.setattr(main, "_win_mutex", None, raising=False)

        assert main.check_single_instance() is False
        assert closed == [222]


class TestExceptionHooks:
    def test_hooks_installed(self):
        log = logging.getLogger("VoiceInk-test-hooks")
        main._install_exception_hooks(log)
        import sys as _sys
        import threading as _threading

        assert _sys.excepthook is not None
        assert _threading.excepthook is not None

    def test_excepthook_logs_non_keyboard_interrupt(self, caplog):
        log = logging.getLogger("VoiceInk-test-hooks2")
        main._install_exception_hooks(log)
        import sys as _sys

        with caplog.at_level(logging.CRITICAL):
            try:
                raise ValueError("boom")
            except ValueError:
                _sys.excepthook(*_sys.exc_info())
        assert any("未捕获异常" in r.message for r in caplog.records)

    def test_threading_hook_ignores_system_exit(self):
        log = logging.getLogger("VoiceInk-test-hooks3")
        main._install_exception_hooks(log)
        import threading as _threading

        args = types.SimpleNamespace(
            exc_type=SystemExit,
            exc_value=SystemExit(),
            exc_traceback=None,
            thread=None,
        )
        # Should not raise.
        _threading.excepthook(args)
