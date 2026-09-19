"""About settings page."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from voiceink.config import VERSION
from voiceink.ui import design_tokens as tok
from voiceink.ui.settings_components import (
    SettingsPage,
    info_callout,
    settings_group,
    settings_section,
)


def build_about_page(win) -> QWidget:
    page = SettingsPage()
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
        f"color: {tok.TEXT}; font-size: {tok.TYPE_BODY_SM}px; font-weight: 550;"
        f" background: transparent;"
    )
    brand_lay.addWidget(brand_name)
    brand_lay.addStretch(1)
    win._about_version_label = QLabel(f"版本 {VERSION}")
    win._about_version_label.setStyleSheet(
        f"color: {tok.TEXT_SEC}; font-size: {tok.TYPE_CAPTION}px; font-weight: 600;"
        f" background: {tok.SURFACE_PEARL}; border: 1px solid {tok.HAIRLINE};"
        f" border-radius: {tok.RADIUS_PILL}px; padding: 3px 10px;"
    )
    brand_lay.addWidget(win._about_version_label)
    win._about_info_lay.addWidget(brand_row)
    page.add(settings_section("", win._about_info_group))

    win._about_usage_tip = info_callout("", "aboutUsageCallout")
    page.add(win._about_usage_tip)
    page.set_compact()
    page.set_spacing(12)
    return page
