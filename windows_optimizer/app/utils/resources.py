"""Пути к ресурсам, работающие и в dev, и в собранном .exe (PyInstaller).

В onefile-сборке PyInstaller распаковывает данные во временную папку
``sys._MEIPASS``. Эта функция возвращает корректный путь в обоих случаях.
"""
from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parents[2]
    return root.joinpath(*parts)
