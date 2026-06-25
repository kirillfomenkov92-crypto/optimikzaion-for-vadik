"""Тесты типа OperationResult.

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_operation_result.py

OperationResult различает три исхода, которые раньше сливались в bool:
успех, пропуск-ради-защиты (skipped) и ошибку (error).
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

from app.core.result import OperationResult  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# 1) Успех.
ok = OperationResult(success=True, message="готово")
check(ok.is_ok() is True, "успех: is_ok() True")
check(ok.skipped is False, "успех: не skipped")

# 2) Пропуск ради защиты — это НЕ ошибка, но и не «применено».
skip = OperationResult(success=True, skipped=True, message="защищено")
check(skip.is_ok() is True, "skip: is_ok() True (не ошибка)")
check(skip.skipped is True, "skip: skipped True")

# 3) Ошибка.
err = OperationResult(success=False, error=RuntimeError("boom"), message="сбой")
check(err.is_ok() is False, "ошибка: is_ok() False")
check(err.error is not None, "ошибка: error задан")

# 4) Различимость skip и error (главная цель типа).
check(skip.skipped and not skip.error, "skip отличается от error")
check(err.error and not err.skipped, "error отличается от skip")

# 5) undo по умолчанию — пустой список (изоляция экземпляров).
a = OperationResult(success=True)
b = OperationResult(success=True)
a.undo.append("x")
check(b.undo == [], "undo не должен шериться между экземплярами (default_factory)")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: OperationResult корректно различает успех/пропуск/ошибку.")
