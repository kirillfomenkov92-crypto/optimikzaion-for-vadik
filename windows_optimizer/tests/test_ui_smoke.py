"""Смоук-тест отрисовки UI (offscreen).

Запуск (из корня репозитория, нужен PyQt6):
    QT_QPA_PLATFORM=offscreen python windows_optimizer/tests/test_ui_smoke.py

Импорт-проверки CI не ловят падения при СОЗДАНии и ОТРИСОВКЕ виджетов
(ошибки в __init__/paintEvent/scan). Здесь мы реально инстанцируем главное
окно и ключевые панели и вызываем grab() — любой краш проваливает тест.
Если PyQt6 не установлен (локальная dev-среда), тест корректно пропускается.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]  # windows_optimizer/
sys.path.insert(0, str(ROOT))

try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    print("SKIP: PyQt6 не установлен — смоук-рендер пропущен.")
    sys.exit(0)


def main() -> int:
    app = QApplication(sys.argv)
    from app.ui.styles.design_tokens import build_qss, Colors
    app.setStyleSheet(build_qss(Colors))

    failures: list[str] = []

    def render(make, name: str) -> None:
        try:
            w = make()
            w.resize(1100, 720)
            w.show()
            for _ in range(5):
                app.processEvents()
            pm = w.grab()
            if pm.isNull():
                failures.append(f"{name}: grab() вернул пустое изображение")
        except Exception as e:  # noqa: BLE001
            import traceback
            failures.append(f"{name}: {e}\n{traceback.format_exc()}")

    from app.ui.main_window import MainWindow
    from app.ui.dashboard import Dashboard
    from app.ui.debloat_panel import DebloatPanel
    from app.ui.scan_page import ScanPage
    from app.ui.widgets.tweak_panel import TweakPanel
    from app.modules.registry import RegistryModule

    render(MainWindow, "MainWindow")
    render(Dashboard, "Dashboard")
    render(DebloatPanel, "DebloatPanel")
    render(ScanPage, "ScanPage")
    render(lambda: TweakPanel(RegistryModule(), "Реестр — твики"), "TweakPanel")

    if failures:
        print(f"ПРОВАЛ: {len(failures)} экранов с ошибкой")
        for f in failures:
            print("  -", f)
        return 1
    print("OK: все экраны создаются и отрисовываются без ошибок.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
