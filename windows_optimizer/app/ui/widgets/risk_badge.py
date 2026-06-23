"""Бейдж уровня риска: 🟢 Безопасно / 🟡 Осторожно / 🔴 Для опытных."""
from __future__ import annotations

from typing import Tuple

from PyQt6.QtWidgets import QLabel


class RiskLevel:
    SAFE = ("safe", "🟢 Безопасно", "#4ecca3", "Можно включать не задумываясь")
    CAUTION = ("caution", "🟡 Осторожно", "#ffd460", "Прочитайте описание перед включением")
    ADVANCED = ("advanced", "🔴 Для опытных", "#e94560", "Только если понимаете, что делаете")

    # Сопоставление со старыми уровнями риска из БД (low/medium/high).
    _MAP = {
        "low": SAFE, "safe": SAFE,
        "medium": CAUTION, "caution": CAUTION,
        "high": ADVANCED, "advanced": ADVANCED,
    }

    @classmethod
    def from_str(cls, value: str) -> Tuple[str, str, str, str]:
        return cls._MAP.get((value or "low").lower(), cls.SAFE)


class RiskBadge(QLabel):
    def __init__(self, level: Tuple[str, str, str, str], parent=None) -> None:
        super().__init__(parent)
        _, text, color, tooltip = level
        self.setText(text)
        self.setToolTip(tooltip)
        self.setStyleSheet(
            "QLabel { color: %s; font-size: 11px; padding: 2px 6px; "
            "border: 1px solid %s; border-radius: 8px; }" % (color, color)
        )
