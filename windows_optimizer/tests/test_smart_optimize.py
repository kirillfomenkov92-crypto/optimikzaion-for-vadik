"""Тесты ядра быстрой оптимизации и оценки состояния.

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_smart_optimize.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import smart_optimize as so  # noqa: E402
from app.core import health  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# --- план: только safe + видимые в простом режиме + не применённые ---
rows = [
    {"id": "a", "risk_level": "safe", "simple_mode_visible": True, "status": "default"},
    {"id": "b", "risk_level": "safe", "simple_mode_visible": True, "status": "applied"},   # уже применён
    {"id": "c", "risk_level": "advanced", "simple_mode_visible": True, "status": "default"},  # рискованный
    {"id": "d", "risk_level": "safe", "simple_mode_visible": False, "status": "default"},   # скрыт в простом
    {"id": "e", "risk_level": "safe", "simple_mode_visible": True, "status": "modified"},
]
ids = so.pending_safe_tweak_ids(rows)
check(ids == ["a", "e"], f"в план должны войти только a,e — получено {ids}")

# --- предпросмотр: считает твики и размер только безопасных temp-папок ---
disk = [
    {"label": "Временные файлы пользователя", "exists": True, "size_bytes": 50 * 1024 * 1024},
    {"label": "Temp в LocalAppData", "exists": True, "size_bytes": 10 * 1024 * 1024},
    {"label": "Кэш обновлений Windows", "exists": True, "size_bytes": 999 * 1024 * 1024},  # warn — не считаем
    {"label": "Системный Temp", "exists": False, "size_bytes": 0},
]
p = so.preview(rows, disk)
check(p["tweaks"] == 2, f"твиков в превью: {p['tweaks']}")
check(p["temp_mb"] == 60.0, f"temp_mb должно быть 60.0 (50+10), получено {p['temp_mb']}")
check("999" not in str(p["temp_mb"]), "warn-папка не должна попадать в превью")

# --- текст превью ---
txt = so.preview_text(p)
check("безопасных улучшений: 2" in txt and "~60.0 МБ" in txt, f"текст превью: {txt!r}")
# пустой план
empty = so.preview([], [])
check("нечего" in so.preview_text(empty), "пустой план — 'применять нечего'")

# --- оценка состояния ---
check(health.score_from_rows([]) == 80, "пустой реестр -> 80")
all_applied = [{"status": "applied"}] * 4
check(health.score_from_rows(all_applied) == 100, f"все применены -> 100, получено {health.score_from_rows(all_applied)}")
none_applied = [{"status": "default"}] * 4
check(health.score_from_rows(none_applied) == 55, f"ничего не применено -> 55, получено {health.score_from_rows(none_applied)}")

# --- дельта ---
check("было 60 → стало 80 (+20)" in health.delta_text(60, 80), "дельта роста")
check("уже оптимально" in health.delta_text(90, 90), "дельта без изменений")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: ядро быстрой оптимизации и оценки состояния корректно.")
