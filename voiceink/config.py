import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from PyQt6.QtCore import QTimer

log = logging.getLogger("VoiceInk")

VERSION = "1.1.0"


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
        "model_id": "sensevoice",
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
        self._models_dir = self._config_dir / "models"
        self._config: dict = {}
        self._extra_keys: dict = {}
        # 延迟保存机制：避免频繁写入文件
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)
        self._ensure_dirs()
        self._load()

    def _ensure_dirs(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._models_dir.mkdir(parents=True, exist_ok=True)

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
