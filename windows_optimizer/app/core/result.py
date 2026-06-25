"""Единый результат операции изменения системы.

Раньше методы возвращали голый ``bool``, из-за чего нельзя было отличить
«пропущено ради защиты» от «реальная ошибка» (см. services.set_start_type,
который в обоих случаях возвращал False). OperationResult делает исход явным.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OperationResult:
    success: bool
    message: str = ""
    skipped: bool = False               # пропущено осознанно (защита/условие), не ошибка
    detail: Optional[Dict[str, Any]] = None
    error: Optional[BaseException] = None
    undo: List[str] = field(default_factory=list)

    def is_ok(self) -> bool:
        """Операция не привела к ошибке (успех или осознанный пропуск)."""
        return self.success and self.error is None

    def as_dict(self) -> Dict[str, Any]:
        """Стабильное представление для UI/логов (без объекта исключения)."""
        return {
            "success": self.success,
            "skipped": self.skipped,
            "message": self.message,
            "error": str(self.error) if self.error else None,
        }
