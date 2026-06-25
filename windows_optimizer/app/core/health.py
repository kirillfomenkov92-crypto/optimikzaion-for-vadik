"""Оценка состояния системы и текст динамики «было → стало».

Чистая логика без Qt — чтобы покрыть тестом. Оценка честная и простая: доля
применённых безопасных улучшений, смещённая в дружелюбный диапазон 55..100
(чтобы не пугать пользователя нулём на свежей системе).
"""
from __future__ import annotations

from typing import List, Dict


def score_from_rows(rows: List[Dict]) -> int:
    """0..100 по доле применённых твиков реестра."""
    if not rows:
        return 80
    applied = sum(1 for r in rows if r.get("status") == "applied")
    return int(round(55 + (applied / len(rows)) * 45))


def grade(score: int) -> str:
    if score >= 85:
        return "Отлично"
    if score >= 70:
        return "Хорошо"
    if score >= 55:
        return "Можно лучше"
    return "Требует внимания"


def delta_text(before: int, after: int) -> str:
    """Подпись динамики после оптимизации."""
    if after > before:
        return f"Состояние: было {before} → стало {after} (+{after - before})"
    if after == before:
        return f"Состояние: {after} (уже оптимально)"
    return f"Состояние: {after}"
