"""Model settings page: current engine, storage, downloadable cards."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from voiceink.ui import design_tokens as tok
from voiceink.ui import settings_styles
from voiceink.ui.settings_components import (
    PageHero,
    SettingsPage,
    settings_group,
    settings_section,
)


def build_model_page(win) -> QWidget:
    page = SettingsPage()
    win._model_hero = PageHero("语音识别")
    page.add(win._model_hero)

    win._model_hero_host = settings_group()
    win._model_hero_layout = QVBoxLayout(win._model_hero_host)
    win._model_hero_layout.setContentsMargins(0, 0, 0, 0)
    win._model_hero_layout.setSpacing(0)
    page.add(settings_section("当前引擎", win._model_hero_host))

    storage_group = settings_group()
    storage_lay = QHBoxLayout(storage_group)
    storage_lay.setContentsMargins(16, 12, 12, 12)
    storage_lay.setSpacing(10)
    win._storage_summary_label = QLabel()
    win._storage_summary_label.setStyleSheet(
        f"color: {tok.TEXT_SEC}; font-size: {tok.TYPE_BODY_SM}px; background: transparent;"
    )
    win._storage_summary_label.setWordWrap(True)
    storage_lay.addWidget(win._storage_summary_label, 1)
    chg = QPushButton("更改存储…")
    chg.setProperty("viBtn", "ghostSm")
    chg.setMinimumHeight(32)
    chg.setStyleSheet(settings_styles.BTN_GHOST_SM)
    chg.clicked.connect(win._change_model_dir)
    storage_lay.addWidget(chg)
    page.add(settings_section("存储", storage_group))

    win._dir_path_label = QLabel()
    win._dir_path_label.setVisible(False)

    win._cards_container = QWidget()
    win._cards_layout = QVBoxLayout(win._cards_container)
    win._cards_layout.setContentsMargins(0, 0, 0, 0)
    win._cards_layout.setSpacing(24)
    page.add(win._cards_container)
    page.set_compact()
    return page
