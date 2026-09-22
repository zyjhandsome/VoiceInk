"""Colors that are applied after startup must follow the active theme axis."""

from PyQt6.QtWidgets import QWidget

from voiceink.ui.design_tokens import activate
from voiceink.ui.hotkey_edit import HotkeyEdit
from voiceink.ui.settings_components import empty_state, reapply_subtree


def test_hotkey_capture_uses_active_dark_colors():
    activate("dark")
    edit = HotkeyEdit()
    edit._begin_capture()
    sheet = edit.styleSheet().lower()
    assert "#222528" in sheet
    assert "#f9fafb" in sheet
    assert "#f7f7f7" not in sheet
    assert "#111827" not in sheet


def test_empty_state_restyles_when_theme_changes():
    activate("light")
    root = QWidget()
    label = empty_state("尚未选择模型")
    label.setParent(root)
    assert "#667085" in label.styleSheet()

    activate("dark")
    reapply_subtree(root)
    sheet = label.styleSheet()
    assert "#9CA3AF" in sheet
    assert "#667085" not in sheet
