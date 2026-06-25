"""Единый применятель твиков реестра с верификацией.

Раньше каждый модуль (network, gaming, …) повторял один шаблон:
прочитать старое значение → записать → залогировать → вернуть bool, причём
часть модулей не проверяла, что значение действительно применилось. Этот
помощник централизует шаблон и добавляет обязательную верификацию read-back.

Твик задаётся кортежем ``(hive, path, name, rtype, value)``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.core.logger import get_logger, log_change
from app.utils import registry_helper as reg

_log = get_logger()

# (hive, path, name, rtype, value)
Tweak = Tuple[str, str, str, str, Any]


class RegistryTweakApplier:
    """Применяет твики реестра единообразно, с проверкой результата."""

    @staticmethod
    def apply_one(hive: str, path: str, name: str, rtype: str, value: Any) -> bool:
        """Записать значение и проверить read-back. True — применено и подтверждено."""
        full = f"{hive}\\{path}\\{name}"
        try:
            old, _ = reg.read_value(hive, path, name)
            reg.write_value(hive, path, name, value, rtype)
            cur, _ = reg.read_value(hive, path, name)
            verified = (cur == value)
            log_change("registry", full, old=old, new=value,
                       status="SUCCESS" if verified else "WARN: значение не подтвердилось")
            if not verified:
                _log.warning("Твик %s записан, но read-back вернул %r (ожидалось %r)", full, cur, value)
            return verified
        except Exception as e:  # pragma: no cover - покрыто тестом через фейк
            log_change("registry", full, status=f"ERROR:{e}")
            _log.warning("Не удалось применить твик %s: %s", full, e)
            return False

    @staticmethod
    def apply_many(tweaks: List[Tweak]) -> Dict[str, bool]:
        """Применить список твиков. Возвращает {name: успех}."""
        result: Dict[str, bool] = {}
        for hive, path, name, rtype, value in tweaks:
            result[name] = RegistryTweakApplier.apply_one(hive, path, name, rtype, value)
        return result
