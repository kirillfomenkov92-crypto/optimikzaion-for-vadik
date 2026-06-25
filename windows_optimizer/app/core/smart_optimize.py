"""Логика быстрой оптимизации в один клик (план + предпросмотр).

Чистая, тестируемая часть: какие безопасные действия войдут в «Ускорить» и
их сводка для предпросмотра (dry-run) — БЕЗ изменений системы. Само применение
выполняет Дашборд через существующие модули и StepWorker с бэкапом.

Принцип: в one-click входят ТОЛЬКО 🟢-безопасные, видимые в простом режиме и
ещё не применённые твики реестра + очистка заведомо безопасных временных папок.
Деблоат (необратимое удаление приложений) сюда НЕ входит.
"""
from __future__ import annotations

from typing import Dict, List

# Заведомо безопасные для очистки временные папки (подмножество DiskModule).
SAFE_TEMP_LABELS = ("Временные файлы пользователя", "Temp в LocalAppData")


def pending_safe_tweak_ids(registry_rows: List[Dict]) -> List[str]:
    """id безопасных, видимых в простом режиме, ещё не применённых твиков."""
    return [
        r["id"] for r in registry_rows
        if r.get("risk_level") == "safe"
        and r.get("simple_mode_visible", True)
        and r.get("status") != "applied"
    ]


def preview(registry_rows: List[Dict], disk_rows: List[Dict]) -> Dict:
    """Сводка плана для предпросмотра (ничего не меняет).

    Возвращает: количество твиков, их id и оценку освобождаемого места (МБ).
    """
    ids = pending_safe_tweak_ids(registry_rows)
    temp_bytes = sum(
        int(d.get("size_bytes", 0)) for d in disk_rows
        if d.get("label") in SAFE_TEMP_LABELS and d.get("exists")
    )
    return {
        "tweaks": len(ids),
        "tweak_ids": ids,
        "temp_mb": round(temp_bytes / (1024 * 1024), 1),
    }


def preview_text(p: Dict) -> str:
    """Человеко-понятная строка для диалога подтверждения."""
    parts = []
    if p["tweaks"]:
        parts.append(f"безопасных улучшений: {p['tweaks']}")
    if p["temp_mb"] > 0:
        parts.append(f"очистка временных файлов: ~{p['temp_mb']} МБ")
    if not parts:
        return "Система уже оптимизирована — применять нечего."
    return "Будет сделано:\n• " + "\n• ".join(parts)
