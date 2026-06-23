"""Страница настроек: тема (тёмная/светлая) и сведения о профиле."""
from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class SettingsPage(QWidget):
    def __init__(self, set_theme: Callable[[str], None], current_theme: str = "dark") -> None:
        super().__init__()
        self._set_theme = set_theme

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("Настройки")
        head.setObjectName("Title")
        root.addWidget(head)

        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(["Тёмная", "Светлая"])
        self.theme.setCurrentIndex(0 if current_theme == "dark" else 1)
        form.addRow("Тема:", self.theme)
        root.addLayout(form)

        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self._apply)
        root.addWidget(apply_btn)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)
        root.addStretch(1)

    def _apply(self) -> None:
        name = "dark" if self.theme.currentIndex() == 0 else "light"
        self._set_theme(name)
        self.status.setText("Тема применена.")
