"""Раздел «История изменений»: что приложение делало с системой.

Читает журнал изменений (записи log_change) и показывает их в обратном
порядке понятным языком. Отмена выполняется через раздел «Бэкапы»
(восстановление сохранённого состояния).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)

_LOG = Path(__file__).resolve().parents[2] / "logs" / "optimizer.log"
_LINE = re.compile(r"\[(?P<ts>[\d\-: ]+)\].*?\[(?P<mod>[a-z]+)\]\s+(?P<action>.+?)\s+\|\s+было=(?P<old>.*?)\s+->\s+стало=(?P<new>.*?)\s+\|\s+(?P<status>\w+)")

_MOD_RU = {
    "registry": "Системные настройки", "services": "Службы", "disk": "Очистка диска",
    "network": "Интернет", "power": "Питание", "memory": "Память", "gaming": "Игры",
    "gpu": "Видеокарта", "cpu": "Процессор", "security": "Безопасность",
    "privacy": "Приватность", "startup": "Автозапуск",
}


def _read_history(limit: int = 200) -> List[str]:
    if not _LOG.exists():
        return []
    items: List[str] = []
    try:
        lines = _LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    for line in reversed(lines):
        m = _LINE.search(line)
        if not m:
            continue
        mod = _MOD_RU.get(m.group("mod"), m.group("mod"))
        ok = m.group("status") == "SUCCESS"
        mark = "✓" if ok else "•"
        items.append(f"{mark}  {m.group('ts')}  —  {mod}: {m.group('action')}")
        if len(items) >= limit:
            break
    return items


class HistoryPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("История изменений")
        head.setObjectName("Title")
        root.addWidget(head)
        info = QLabel("Здесь видно всё, что приложение меняло в системе. "
                      "Отменить изменения можно в разделе «Бэкапы» — восстановив сохранённое состояние.")
        info.setObjectName("Subtitle")
        info.setWordWrap(True)
        root.addWidget(info)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        bar = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        bar.addWidget(self.btn_refresh)
        bar.addStretch(1)
        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        bar.addWidget(self.status)
        root.addLayout(bar)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        items = _read_history()
        for it in items:
            self.list.addItem(it)
        if not items:
            self.list.addItem("Пока ничего не менялось.")
        self.status.setText(f"Записей: {len(items)}")
