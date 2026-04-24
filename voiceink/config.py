import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from PyQt6.QtCore import QTimer

log = logging.getLogger("VoiceInk")

VERSION = "1.1.0"


def _get_default_models_dir() -> Path:
    """Return default models directory. Packaged exe uses install dir."""
    # Packaged exe: try install directory first
    if hasattr(sys, '_MEIPASS'):
        install_models = Path(sys._MEIPASS).parent / "models"
        if install_models.exists():
            return install_models
        try:
            install_models.mkdir(parents=True, exist_ok=True)
            return install_models
        except OSError:
            pass  # Permission denied, use user dir
    # Development or fallback: user directory
    return Path.home() / ".voiceink" / "models"


def format_hotkey(hotkey: str) -> str:
    if not hotkey:
        return ""
    parts = hotkey.split("+")
    out = []
    for p in parts:
        p = p.strip()
        out.append(p.capitalize() if len(p) > 1 else p.upper())
    return " + ".join(out)

DEFAULT_CONFIG = {
    "hotkey": "ctrl+space",
    "auto_start": False,
    "sound_enabled": True,
    "stt": {
        "model_id": "qwen3-asr-0.6b",
        "num_threads": 4,
        "models_dir": "",
    },
    "llm": {
        "enabled": False,
        "api_url": "",
        "api_key": "",
        "model_name": "",
        "prompt": ""
    }
}


class Config:
    def __init__(self):
        self._config_dir = Path.home() / ".voiceink"
        self._config_file = self._config_dir / "config.json"
        self._models_dir = _get_default_models_dir()
        self._config: dict = {}
        self._extra_keys: dict = {}
        # 延迟保存机制：避免频繁写入文件
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)
        self._ensure_dirs()
        self._load()
        self._sync_registry_auto_start()

    def _ensure_dirs(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        # models_dir may be install dir (already exists) or user dir
        try:
            self._models_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Permission denied (install dir), models already there

    def _load(self):
        raw: dict = {}
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                log.warning("配置文件读取失败，使用默认配置: %s", e)
                raw = {}
        self._extra_keys = {k: v for k, v in raw.items() if k not in DEFAULT_CONFIG}
        self._config = self._merge_defaults(DEFAULT_CONFIG, raw)

    def _sync_registry_auto_start(self):
        """Sync auto_start setting with Windows registry (installer may have set it)."""
        if sys.platform != "win32":
            return
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "VoiceInk")
                # Registry entry exists - sync to config
                if not self._config.get("auto_start", False):
                    self._config["auto_start"] = True
                    self.save_immediate()
                    log.info("同步注册表开机自启状态到配置文件")
            except FileNotFoundError:
                # Registry entry doesn't exist - nothing to sync
                pass
            winreg.CloseKey(key)
        except Exception as e:
            log.warning("读取注册表开机自启状态失败: %s", e)

    def _merge_defaults(self, defaults: dict, current: dict) -> dict:
        result = {}
        for key, default_value in defaults.items():
            if key in current:
                if isinstance(default_value, dict) and isinstance(current[key], dict):
                    result[key] = self._merge_defaults(default_value, current[key])
                else:
                    result[key] = current[key]
            else:
                result[key] = default_value
        return result

    def _do_save(self):
        """实际执行保存操作"""
        self.save()

    def save_immediate(self):
        """立即保存配置，用于应用退出前"""
        self._save_timer.stop()
        self.save()

    def save(self):
        """Atomic write: write to temp file then rename to prevent corruption."""
        data = {**self._config, **self._extra_keys}
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._config_dir), suffix=".tmp", prefix="config_"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, str(self._config_file))
        except OSError as e:
            log.error("配置文件保存失败: %s", e)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any):
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        # 延迟保存：500ms 后写入，多次 set 只触发一次写入
        self._save_timer.start(500)

    def get_all(self) -> dict:
        return self._config.copy()

    @property
    def models_dir(self) -> Path:
        custom = self.get("stt.models_dir", "")
        if custom:
            return Path(custom)
        return self._models_dir

    @property
    def config_dir(self) -> Path:
        return self._config_dir
