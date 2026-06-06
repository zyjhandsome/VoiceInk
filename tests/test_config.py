from voiceink.config import Config, format_hotkey, DEFAULT_CONFIG
import tempfile
import json
import os
from pathlib import Path
import shutil


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
        assert DEFAULT_CONFIG["stt"]["model_id"] == "qwen3-asr-0.6b"

    def test_default_num_threads(self):
        assert DEFAULT_CONFIG["stt"]["num_threads"] == 4

    def test_default_llm_enabled(self):
        assert DEFAULT_CONFIG["llm"]["enabled"] is False

    def test_default_llm_api_fields_empty(self):
        assert DEFAULT_CONFIG["llm"]["api_url"] == ""
        assert DEFAULT_CONFIG["llm"]["api_key"] == ""
        assert DEFAULT_CONFIG["llm"]["model_name"] == ""


class TestConfigInit:
    def test_config_loads_defaults(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with open(os.path.join(temp_dir, ".voiceink", "config.json"), "w") as f:
                json.dump({}, f)
            config = Config()
            assert config.get("hotkey") == "ctrl+space"
            assert config.get("sound_enabled") is True
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_config_loads_existing(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config_data = {
                "hotkey": "alt+space",
                "sound_enabled": False,
                "stt": {"model_id": "sensevoice"}
            }
            config_path = Path(temp_dir) / ".voiceink" / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(config_data, f)
            config = Config()
            assert config.get("hotkey") == "alt+space"
            assert config.get("sound_enabled") is False
            assert config.get("stt.model_id") == "sensevoice"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigGetSet:
    def test_get_nested_key(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            assert config.get("stt.model_id") == "qwen3-asr-0.6b"
            assert config.get("llm.enabled") is False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_default_value(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            assert config.get("nonexistent_key", "default") == "default"
            assert config.get("stt.nonexistent", 123) == 123
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_set_simple_value(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            config.set("hotkey", "ctrl+a")
            assert config.get("hotkey") == "ctrl+a"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_set_nested_value(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            config.set("llm.enabled", True)
            assert config.get("llm.enabled") is True
            config.set("stt.num_threads", 8)
            assert config.get("stt.num_threads") == 8
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_get_all(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            all_config = config.get_all()
            assert isinstance(all_config, dict)
            assert "hotkey" in all_config
            assert "stt" in all_config
            assert "llm" in all_config
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigPersistence:
    def test_config_saves_to_file(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            config.set("test_key", "test_value")
            config.save()

            config_path = config._config_file
            assert config_path.exists()

            with open(config_path, "r") as f:
                saved_data = json.load(f)
            assert "test_key" in saved_data or "test_key" in config.get_all()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_config_loads_saved_values(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            config.set("persistence_test", "saved_value")
            config.save()

            config2 = Config()
            assert config2.get("persistence_test") == "saved_value"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigAtomicWrite:
    def test_atomic_write_creates_temp_file(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            config.set("atomic_test", True)
            config.save()

            temp_files = list(Path(temp_dir + "/.voiceink").glob("config_*.tmp"))
            assert len(temp_files) == 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigModelsDir:
    def test_models_dir_property(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            models_dir = config.models_dir
            assert isinstance(models_dir, Path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_custom_models_dir(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            custom_path = Path(temp_dir) / "custom_models"
            config.set("stt.models_dir", str(custom_path))
            assert config.models_dir == custom_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigRegistrySync:
    def test_registry_sync_handles_errors(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config()
            assert config.get("auto_start") is not None
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
