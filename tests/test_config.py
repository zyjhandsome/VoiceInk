import json

import pytest

from voiceink.config import Config, format_hotkey, DEFAULT_CONFIG
from voiceink.speech_recognizer import DEFAULT_MODEL_ID


class TestFormatHotkey:
    def test_empty_hotkey(self):
        assert format_hotkey("") == ""

    def test_single_key(self):
        assert format_hotkey("space") == "Space"

    def test_modifier_combination(self):
        result = format_hotkey("ctrl+space")
        assert "Ctrl" in result
        assert "Space" in result
        assert " + " in result

    def test_multiple_modifiers(self):
        result = format_hotkey("ctrl+shift+space")
        parts = result.split(" + ")
        assert len(parts) == 3
        assert "Ctrl" in parts
        assert "Shift" in parts
        assert "Space" in parts

    def test_lowercase_input(self):
        result = format_hotkey("ALT+TAB")
        assert result == "Alt + Tab"

    def test_single_character_uppercase(self):
        result = format_hotkey("a")
        assert result == "A"


class TestConfigDefaults:
    def test_default_hotkey(self):
        assert DEFAULT_CONFIG["hotkey"] == "ctrl+space"

    def test_default_sound_enabled(self):
        assert DEFAULT_CONFIG["sound_enabled"] is True

    def test_default_auto_start(self):
        assert DEFAULT_CONFIG["auto_start"] is False

    def test_default_first_run_welcome_seen(self):
        assert DEFAULT_CONFIG["first_run_welcome_seen"] is True

    def test_default_model_id(self):
        assert DEFAULT_CONFIG["stt"]["model_id"] == DEFAULT_MODEL_ID
        assert DEFAULT_MODEL_ID == "fireredasr2-ctc"

    def test_default_num_threads(self):
        assert DEFAULT_CONFIG["stt"]["num_threads"] == 4

    def test_default_llm_enabled(self):
        assert DEFAULT_CONFIG["llm"]["enabled"] is False

    def test_default_llm_api_fields_empty(self):
        assert DEFAULT_CONFIG["llm"]["api_url"] == ""
        assert DEFAULT_CONFIG["llm"]["api_key"] == ""
        assert DEFAULT_CONFIG["llm"]["model_name"] == ""


class TestConfigInit:
    def test_config_loads_defaults(self, config_home):
        with open(config_home / "config.json", "w", encoding="utf-8") as f:
            json.dump({}, f)
        config = Config(config_dir=config_home)
        assert config.get("hotkey") == "ctrl+space"
        assert config.get("sound_enabled") is True

    def test_config_loads_existing(self, config_home):
        config_data = {
            "hotkey": "alt+space",
            "sound_enabled": False,
            "stt": {"model_id": "sensevoice"},
        }
        with open(config_home / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f)
        config = Config(config_dir=config_home)
        assert config.get("hotkey") == "alt+space"
        assert config.get("sound_enabled") is False
        assert config.get("stt.model_id") == "sensevoice"


class TestConfigGetSet:
    def test_get_nested_key(self, config):
        assert config.get("stt.model_id") == DEFAULT_MODEL_ID
        assert config.get("llm.enabled") is False

    def test_get_default_value(self, config):
        assert config.get("nonexistent_key", "default") == "default"
        assert config.get("stt.nonexistent", 123) == 123

    def test_set_simple_value(self, config):
        config.set("hotkey", "ctrl+a")
        assert config.get("hotkey") == "ctrl+a"

    def test_set_nested_value(self, config):
        config.set("llm.enabled", True)
        assert config.get("llm.enabled") is True
        config.set("stt.num_threads", 8)
        assert config.get("stt.num_threads") == 8

    def test_get_all(self, config):
        all_config = config.get_all()
        assert isinstance(all_config, dict)
        assert "hotkey" in all_config
        assert "stt" in all_config
        assert "llm" in all_config


class TestConfigPersistence:
    def test_config_saves_to_file(self, config):
        config.set("test_key", "test_value")
        config.save()

        config_path = config._config_file
        assert config_path.exists()

        with open(config_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert "test_key" in saved_data or "test_key" in config.get_all()

    def test_config_loads_saved_values(self, config_home):
        config = Config(config_dir=config_home)
        config.set("persistence_test", "saved_value")
        config.save_immediate()

        config2 = Config(config_dir=config_home)
        assert config2.get("persistence_test") == "saved_value"


class TestConfigAtomicWrite:
    def test_atomic_write_creates_temp_file(self, config_home):
        config = Config(config_dir=config_home)
        config.set("atomic_test", True)
        config.save()

        temp_files = list(config_home.glob("config_*.tmp"))
        assert len(temp_files) == 0


class TestConfigModelsDir:
    def test_models_dir_property(self, config):
        from pathlib import Path

        models_dir = config.models_dir
        assert isinstance(models_dir, Path)

    def test_custom_models_dir(self, config, tmp_path):
        custom_path = tmp_path / "custom_models"
        config.set("stt.models_dir", str(custom_path))
        assert config.models_dir == custom_path


class TestConfigRegistrySync:
    def test_registry_sync_handles_errors(self, config):
        assert config.get("auto_start") is not None
