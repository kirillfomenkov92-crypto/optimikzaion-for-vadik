"""Тесты единого применятеля твиков реестра (RegistryTweakApplier).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_tweak_applier.py

Проверяет: запись + верификация read-back, корректный возврат при
несовпадении и при исключении, батч apply_many. Реестр не трогается —
registry_helper подменяется на словарь в памяти.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]  # windows_optimizer/
sys.path.insert(0, str(ROOT))

from app.core import tweak_applier as ta  # noqa: E402
from app.utils import registry_helper as reg  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# --- Фейковый реестр в памяти, подменяет registry_helper ---
class FakeRegistry:
    def __init__(self) -> None:
        self.store: dict = {}
        self.fail_write_on: set = set()  # ключи, на которых write бросает
        self.silent_drop: set = set()    # ключи, где write «успешен», но значение не меняется

    def read_value(self, hive, path, name):
        return self.store.get((hive, path, name), (None, None))

    def write_value(self, hive, path, name, value, regtype="REG_DWORD"):
        if (hive, path, name) in self.fail_write_on:
            raise OSError("отказ записи (тест)")
        if (hive, path, name) in self.silent_drop:
            return  # имитируем запись, которая не применилась
        self.store[(hive, path, name)] = (value, regtype)


def with_fake(fake: FakeRegistry):
    """Подменить функции registry_helper на методы fake (вернуть восстановитель)."""
    orig = (reg.read_value, reg.write_value)
    reg.read_value = fake.read_value           # type: ignore[assignment]
    reg.write_value = fake.write_value         # type: ignore[assignment]
    # applier мог импортировать reg как модуль — патчим там же.
    ta.reg.read_value = fake.read_value        # type: ignore[attr-defined]
    ta.reg.write_value = fake.write_value      # type: ignore[attr-defined]

    def restore():
        reg.read_value, reg.write_value = orig
        ta.reg.read_value, ta.reg.write_value = orig
    return restore


# 1) Успешная запись с верификацией read-back => True, значение в store.
fake = FakeRegistry()
restore = with_fake(fake)
try:
    ok = ta.RegistryTweakApplier.apply_one("HKLM", r"SYS\Test", "Val", "REG_DWORD", 1)
    check(ok is True, "apply_one должен вернуть True при успешной записи")
    check(fake.store.get(("HKLM", r"SYS\Test", "Val")) == (1, "REG_DWORD"),
          "значение должно быть записано в реестр")
finally:
    restore()

# 2) Запись «успешна», но read-back не совпал => False (верификация ловит).
fake = FakeRegistry()
fake.silent_drop.add(("HKLM", r"SYS\Test", "Val"))
restore = with_fake(fake)
try:
    ok = ta.RegistryTweakApplier.apply_one("HKLM", r"SYS\Test", "Val", "REG_DWORD", 1)
    check(ok is False, "apply_one должен вернуть False при несовпадении read-back")
finally:
    restore()

# 3) Исключение при записи => False, не пробрасывается.
fake = FakeRegistry()
fake.fail_write_on.add(("HKLM", r"SYS\Test", "Val"))
restore = with_fake(fake)
try:
    ok = ta.RegistryTweakApplier.apply_one("HKLM", r"SYS\Test", "Val", "REG_DWORD", 1)
    check(ok is False, "apply_one должен вернуть False при исключении записи")
finally:
    restore()

# 4) apply_many возвращает {name: bool} для смешанного набора.
fake = FakeRegistry()
fake.fail_write_on.add(("HKCU", r"A", "Bad"))
restore = with_fake(fake)
try:
    res = ta.RegistryTweakApplier.apply_many([
        ("HKLM", r"A", "Good", "REG_DWORD", 5),
        ("HKCU", r"A", "Bad", "REG_DWORD", 9),
    ])
    check(res == {"Good": True, "Bad": False},
          f"apply_many вернул неожиданно: {res}")
finally:
    restore()


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: RegistryTweakApplier корректен (запись, верификация, ошибки, батч).")
