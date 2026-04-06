import json
import os
from pathlib import Path
from typing import Any


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
        "model_name": ""
    }
}


class Config:
    def __init__(self):
        self._config_dir = Path.home() / ".voiceink"
        self._config_file = self._config_dir / "config.json"
        self._models_dir = self._config_dir / "models"
        self._config = {}
        self._ensure_dirs()
        self._load()

    def _ensure_dirs(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._config = {}
        self._config = self._merge_defaults(DEFAULT_CONFIG, self._config)

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

    def save(self):
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

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
        self.save()

    def get_all(self) -> dict:
        return self._config.copy()

    @property
    def models_dir(self) -> Path:
        custom = self.get("stt.models_dir", "")
        if custom:
            p = Path(custom)
            p.mkdir(parents=True, exist_ok=True)
            return p
        return self._models_dir

    @property
    def config_dir(self) -> Path:
        return self._config_dir
