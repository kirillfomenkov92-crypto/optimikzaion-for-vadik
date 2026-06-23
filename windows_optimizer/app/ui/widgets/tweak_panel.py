"""Интерактивная панель улучшений: человеческие названия, риск, режимы.

Колонки: [✓] Улучшение · Что даёт · Риск · Статус.
В простом режиме показываются только понятные безопасные/осторожные улучшения;
галочка «Показать всё» открывает пункты «для опытных».
Перед применением создаётся сохранение состояния системы (бэкап реестра).
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core import backup
from app.ui.modes import mode_manager
from app.ui.widgets.risk_badge import RiskLevel
from app.ui.widgets.worker import OperationWorker


class TweakPanel(QWidget):
    def __init__(self, provider, title: str) -> None:
        super().__init__()
        self.provider = provider
        self._worker = None
        self._build(title)
        self.refresh()

    def _build(self, title: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        root.addWidget(head)

        self.show_all = QCheckBox("Показать всё (включая пункты для опытных)")
        self.show_all.stateChanged.connect(lambda _=0: self.refresh())
        root.addWidget(self.show_all)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["✓", "Улучшение", "Что даёт", "Риск", "Состояние"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setWordWrap(True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Проверить состояние")
        self.btn_apply = QPushButton("Включить выбранные улучшения")
        self.btn_apply.setObjectName("Primary")
        self.btn_revert = QPushButton("Отменить выбранные")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_apply.clicked.connect(self._apply_selected)
        self.btn_revert.clicked.connect(self._revert_selected)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_revert)
        btns.addWidget(self.btn_apply)
        root.addLayout(btns)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def _visible_rows(self) -> List[Dict]:
        rows = self.provider.scan()
        simple = mode_manager().is_simple() and not self.show_all.isChecked()
        if simple:
            rows = [r for r in rows
                    if r.get("simple_mode_visible", True) and r.get("risk_level", "safe") != "advanced"]
        return rows

    def refresh(self) -> None:
        rows = self._visible_rows()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, r.get("id"))
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(r.get("friendly_name") or r.get("name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("user_benefit", "")))
            _id, text, color, tip = RiskLevel.from_str(r.get("risk_level") or r.get("risk", "low"))
            risk_item = QTableWidgetItem(text)
            risk_item.setForeground(QColor(color))
            risk_item.setToolTip(tip)
            self.table.setItem(i, 3, risk_item)
            self.table.setItem(i, 4, QTableWidgetItem(_status_ru(r.get("status", ""))))
        self.table.resizeRowsToContents()
        self.status.setText(f"Доступно улучшений: {len(rows)}. Перед применением сохраним состояние системы.")

    def _selected_ids(self) -> List[str]:
        ids: List[str] = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _set_busy(self, busy: bool) -> None:
        for b in (self.btn_refresh, self.btn_apply, self.btn_revert):
            b.setEnabled(not busy)

    def _apply_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            self.status.setText("Отметьте галочками улучшения, которые хотите включить.")
            return
        self.status.setText("Сохраняю состояние системы и включаю улучшения…")
        self._set_busy(True)

        def job():
            backup.create_backup("tweaks", hives=["HKLM", "HKCU"], applied_tweaks=ids)
            return self.provider.apply_many(ids)

        self._run(job, "Включено")

    def _revert_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            self.status.setText("Отметьте галочками то, что хотите отменить.")
            return
        self._set_busy(True)
        self.status.setText("Отменяю выбранные изменения…")
        self._run(lambda: self.provider.revert_many(ids), "Отменено")

    def _run(self, fn, verb: str) -> None:
        self._worker = OperationWorker(fn)
        self._worker.finished_ok.connect(lambda res: self._done(res, verb))
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, result: Dict, verb: str) -> None:
        ok = sum(1 for v in (result or {}).values() if v)
        total = len(result or {})
        self.status.setText(f"{verb}: {ok} из {total}. Изменения можно отменить кнопкой «Отменить выбранные».")
        self._set_busy(False)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Не удалось: {msg}")
        self._set_busy(False)


def _status_ru(status: str) -> str:
    return {"applied": "включено", "default": "выключено",
            "modified": "изменено вручную", "unknown": "—"}.get(status, status)
