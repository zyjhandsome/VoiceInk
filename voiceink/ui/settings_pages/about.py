"""About settings page."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from voiceink.config import VERSION
from voiceink.ui import design_tokens as tok
from voiceink.ui.settings_components import (
    SettingsPage,
    page_header,
    footnote,
    settings_group,
    settings_section,
)


def build_about_page(win) -> QWidget:
    page = SettingsPage()
    page.add(page_header("关于", "VoiceInk · 让语音成为文字"))
    win._about_info_group = settings_group()
    win._about_info_lay = QVBoxLayout(win._about_info_group)
    win._about_info_lay.setContentsMargins(0, 0, 0, 0)
    win._about_info_lay.setSpacing(0)

    brand_row = QWidget()
    brand_lay = QHBoxLayout(brand_row)
    brand_lay.setContentsMargins(16, 8, 16, 8)
    brand_lay.setSpacing(12)
    brand_name = QLabel("VoiceInk")
    brand_name.setProperty("viRole", "kvKey")
    brand_name.setStyleSheet(
        f"color: {tok.TEXT}; font-size: {tok.TYPE_BODY_SM}px; font-weight: 700;"
        f" background: transparent;"
    )
    brand_lay.addWidget(brand_name)
    brand_lay.addStretch(1)
    win._about_version_label = QLabel(f"版本 {VERSION}")
    win._about_version_label.setStyleSheet(
        f"color: {tok.TEXT_SEC}; font-size: {tok.TYPE_CAPTION}px; font-weight: 700;"
        f" background: {tok.SURFACE_PEARL}; border: 1px solid {tok.HAIRLINE};"
        f" border-radius: {tok.RADIUS_PILL}px; padding: 3px 10px;"
    )
    brand_lay.addWidget(win._about_version_label)
    win._about_info_lay.addWidget(brand_row)

    win._about_runtime_wrap = QWidget()
    win._about_runtime_lay = QVBoxLayout(win._about_runtime_wrap)
    win._about_runtime_lay.setContentsMargins(0, 0, 0, 0)
    win._about_runtime_lay.setSpacing(0)
    win._about_info_lay.addWidget(win._about_runtime_wrap)

    win._about_paths_toggle = QPushButton("文件位置")
    win._about_paths_toggle.setObjectName("aboutPathsToggle")
    win._about_paths_toggle.setCheckable(True)
    win._about_paths_toggle.setChecked(False)
    win._about_paths_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
    win._about_paths_toggle.setStyleSheet(
        f"QPushButton#aboutPathsToggle {{"
        f" color: {tok.TEXT_SEC}; background: transparent; border: none;"
        f" font-size: {tok.TYPE_BODY_SM}px; font-weight: 400;"
        f" text-align: left; padding: 10px 16px;"
        f"}}"
        f"QPushButton#aboutPathsToggle:hover {{ color: {tok.TEXT}; }}"
    )
    win._about_paths_wrap = QWidget()
    win._about_paths_wrap.setObjectName("aboutPaths")
    win._about_paths_lay = QVBoxLayout(win._about_paths_wrap)
    win._about_paths_lay.setContentsMargins(0, 0, 0, 0)
    win._about_paths_lay.setSpacing(0)
    win._about_paths_wrap.setVisible(False)
    win._about_paths_toggle.toggled.connect(win._about_paths_wrap.setVisible)
    win._about_info_lay.addWidget(win._about_paths_toggle)
    win._about_info_lay.addWidget(win._about_paths_wrap)

    page.add(settings_section("", win._about_info_group))

    win._about_usage_tip = settings_group()
    win._about_usage_tip.setObjectName("settingsGroup")
    tip_layout = QVBoxLayout(win._about_usage_tip)
    tip_layout.setContentsMargins(16, 12, 16, 12)
    tip_layout.addWidget(footnote(""))
    page.add(win._about_usage_tip)
    page.set_compact()
    page.set_spacing(12)
    return page
