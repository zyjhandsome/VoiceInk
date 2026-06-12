"""Model selection card for the settings model page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from voiceink.ui.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    BAR_OFF,
    GREEN,
    HAIRLINE,
    RADIUS_MD,
    RADIUS_PILL,
    SURFACE,
    TEXT,
    TEXT_DIM,
    TEXT_SEC,
)
from voiceink.ui.settings_styles import (
    BTN_ACCENT_SM,
    BTN_DANGER_SM,
    BTN_GREEN_SM,
)


class ModelCard(QFrame):
    action_clicked = pyqtSignal(str, str)

    def __init__(
        self,
        model_info: dict,
        is_downloaded: bool,
        is_active: bool,
        parent=None,
    ):
        super().__init__(parent)
        self._model_id = model_info["id"]
        self._info = model_info
        self._is_downloaded = is_downloaded
        self._is_active = is_active
        self._progress_bar = None
        self._action_btn = None
        self._setup_ui()

    def _setup_ui(self):
        ring = f"2px solid {ACCENT}" if self._is_active else f"1px solid {HAIRLINE}"
        self.setStyleSheet(
            f"ModelCard {{ background: {SURFACE}; border: {ring};"
            f" border-radius: {RADIUS_MD}px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(10)
        name_lbl = QLabel(self._info["name"])
        name_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 15px; font-weight: 600; background: transparent;"
        )
        head.addWidget(name_lbl)
        if self._is_active:
            badge = QLabel("当前")
            badge.setStyleSheet(
                f"background: {ACCENT_SOFT}; color: {ACCENT}; border-radius: {RADIUS_PILL}px;"
                "padding: 3px 9px; font-size: 11px; font-weight: 600;"
            )
            head.addWidget(badge)
        head.addStretch()
        size_lbl = QLabel(f"{self._info['size_mb']} MB")
        size_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        head.addWidget(size_lbl)
        layout.addLayout(head)

        layout.addSpacing(8)

        desc = QLabel(self._info["description"])
        desc.setStyleSheet(
            f"color: {TEXT_SEC}; font-size: 13px; line-height: 1.45;"
            f" background: transparent;"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(6)

        meta = QLabel(
            f"{self._info['languages']} · 准确率 {self._info['accuracy']}/5"
            f" · 速度 {self._info['speed']}/5"
        )
        meta.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 12px; background: transparent;"
        )
        meta.setWordWrap(True)
        layout.addWidget(meta)

        layout.addSpacing(12)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: {BAR_OFF}; border-radius: 2px; border: none; }}
            QProgressBar::chunk {{ background: {GREEN}; border-radius: 2px; }}
        """)
        layout.addWidget(self._progress_bar)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        if self._is_downloaded:
            if not self._is_active:
                sel_btn = QPushButton("使用此模型")
                sel_btn.setFixedHeight(32)
                sel_btn.setStyleSheet(BTN_ACCENT_SM)
                sel_btn.clicked.connect(
                    lambda: self.action_clicked.emit(self._model_id, "select")
                )
                actions.addWidget(sel_btn)
            del_btn = QPushButton("删除")
            del_btn.setFixedHeight(32)
            del_btn.setStyleSheet(BTN_DANGER_SM)
            del_btn.clicked.connect(
                lambda: self.action_clicked.emit(self._model_id, "delete")
            )
            actions.addWidget(del_btn)
        else:
            self._action_btn = QPushButton("下载")
            self._action_btn.setFixedHeight(32)
            self._action_btn.setMinimumWidth(96)
            self._action_btn.setStyleSheet(BTN_GREEN_SM)
            self._action_btn.clicked.connect(
                lambda: self.action_clicked.emit(self._model_id, "download")
            )
            actions.addWidget(self._action_btn)
        actions.addStretch()
        layout.addLayout(actions)

    def set_download_progress(self, pct: int):
        if self._progress_bar:
            self._progress_bar.setVisible(True)
            self._progress_bar.setValue(pct)
        if self._action_btn:
            self._action_btn.setEnabled(False)
            self._action_btn.setText(f"{pct}%")

    def set_download_error(self, msg: str):
        if self._progress_bar:
            self._progress_bar.setVisible(False)
        if self._action_btn:
            self._action_btn.setEnabled(True)
            self._action_btn.setText("重试")
