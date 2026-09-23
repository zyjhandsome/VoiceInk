"""The setup wizard must ship in Simplified Chinese only."""

from pathlib import Path

_ISS = Path(__file__).resolve().parents[1] / "installer" / "VoiceInk-Setup.iss"


def test_setup_wizard_uses_simplified_chinese_only():
    text = _ISS.read_text(encoding="utf-8")
    assert 'MessagesFile: "compiler:Languages\\ChineseSimplified.isl"' in text
    assert "Default.isl" not in text
    assert "ShowLanguageDialog=no" in text
    assert "VoiceInk Setup" not in text
