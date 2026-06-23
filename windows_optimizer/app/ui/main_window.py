"""Главное окно: левая навигация + правая рабочая область (QStackedWidget)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QStatusBar,
    QVBoxLayout, QWidget, QMainWindow, QScrollArea,
)

from app.ui.dashboard import Dashboard
from app.ui.scan_page import ScanPage
from app.ui.backups_page import BackupsPage
from app.ui.about_page import AboutPage
from app.ui.settings_page import SettingsPage
from app.ui.widgets.tweak_panel import TweakPanel
from app.ui.widgets.disk_panel import DiskPanel
from app.ui.widgets.services_panel import ServicesPanel
from app.ui.widgets.action_panel import ActionPanel
from app.modules.registry import RegistryModule
from app.modules.startup import StartupModule
from app.modules.services import ServicesModule
from app.modules.disk import DiskModule
from app.modules.privacy import PrivacyModule
from app.modules.network import NetworkModule
from app.modules.power import PowerModule
from app.modules.memory import MemoryModule
from app.modules.gaming import GamingModule
from app.modules.gpu import GpuModule
from app.modules.cpu import CpuModule
from app.modules.security import SecurityModule

_STYLES_DIR = Path(__file__).resolve().parent / "styles"
_STYLE = _STYLES_DIR / "dark_theme.qss"
_ICON = Path(__file__).resolve().parents[2] / "resources" / "icons" / "app.ico"


class _ModulePlaceholder(QWidget):
    """Простая панель модуля на этапе фундамента: показывает результат scan()."""

    def __init__(self, title: str, rows: List[str]) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        layout.addWidget(head)
        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        inner_l = QVBoxLayout(inner)
        if not rows:
            inner_l.addWidget(QLabel("Нет данных (доступно на Windows)."))
        for r in rows:
            lbl = QLabel("• " + r)
            lbl.setWordWrap(True)
            inner_l.addWidget(lbl)
        inner_l.addStretch(1)
        area.setWidget(inner)
        layout.addWidget(area)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Windows Optimizer Pro")
        self.setMinimumSize(1100, 700)
        if _ICON.exists():
            self.setWindowIcon(QIcon(str(_ICON)))

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(self.sidebar)
        side_l.setContentsMargins(12, 16, 12, 16)
        side_l.setSpacing(6)

        self.stack = QStackedWidget()
        self.stack.setObjectName("WorkArea")

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for title, widget in self._pages():
            self._add_page(side_l, title, widget)
        side_l.addStretch(1)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов")

        if self._btn_group.buttons():
            self._btn_group.buttons()[0].setChecked(True)
            self.stack.setCurrentIndex(0)

        self._apply_style()

    def _pages(self) -> List[Tuple[str, QWidget]]:
        reg = RegistryModule()
        startup = StartupModule()
        privacy = PrivacyModule()
        network = NetworkModule()
        power = PowerModule()
        memory = MemoryModule()

        startup_rows = [f"{r['name']} — {r.get('source','')}" for r in startup.scan()]
        gaming = GamingModule()
        gpu = GpuModule()
        cpu = CpuModule()
        security = SecurityModule()
        gpu_rows = [f"{r['item']}: {r['value']}" for r in gpu.scan()]
        security_rows = [f"{r['item']}: {r['value']}" for r in security.scan()]

        # Обёртки «применить рекомендованное» для панелей действий.
        apply_memory = lambda: {"LargeSystemCache": memory.set_large_system_cache(0)}
        apply_cpu = lambda: {"Win32PrioritySeparation (передний план)": cpu.set_priority_separation(0x2A)}
        apply_privacy = lambda: privacy.apply_privacy([t["id"] for t in privacy.privacy_tweaks()])

        return [
            ("🏠 Дашборд", Dashboard()),
            ("🔍 Сканирование", ScanPage()),
            ("🚀 Автозагрузка", _ModulePlaceholder("Автозагрузка", startup_rows)),
            ("⚙️ Службы", ServicesPanel()),
            ("💾 Очистка диска", DiskPanel()),
            ("🌐 Сеть", ActionPanel("Сеть (TCP/IP)", network.scan, network.apply_tcp_tweaks,
                                     "Применить TCP-твики",
                                     hint="DNS-профили и ping доступны в модуле network.")),
            ("⚡ Питание", ActionPanel("Питание", power.scan, power.enable_high_performance,
                                       "Включить «Высокая производительность»",
                                       backup_before=False)),
            ("🧠 Память", ActionPanel("Память", memory.scan, apply_memory,
                                       "Применить (LargeSystemCache=приложения)")),
            ("🎮 Игры", ActionPanel("Игровая оптимизация", gaming.scan, gaming.apply_all,
                                     "Применить игровые твики")),
            ("🖥️ GPU", _ModulePlaceholder("GPU", gpu_rows)),
            ("🖧 CPU", ActionPanel("CPU", cpu.scan, apply_cpu,
                                    "Приоритет переднему плану")),
            ("🔒 Безопасность", _ModulePlaceholder("Безопасность", security_rows)),
            ("🕵️ Приватность", ActionPanel("Приватность", privacy.scan, apply_privacy,
                                            "Применить твики приватности")),
            ("📝 Реестр", TweakPanel(reg, "Реестр — твики")),
            ("🗄️ Бэкапы", BackupsPage()),
            ("⚙️ Настройки", SettingsPage(self.set_theme, getattr(self, "_theme", "dark"))),
            ("❓ О программе", AboutPage()),
        ]

    def _add_page(self, side_layout: QVBoxLayout, title: str, widget: QWidget) -> None:
        idx = self.stack.addWidget(widget)
        btn = QPushButton(title)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _=False, i=idx: self.stack.setCurrentIndex(i))
        self._btn_group.addButton(btn)
        side_layout.addWidget(btn)

    def _apply_style(self) -> None:
        self.set_theme(getattr(self, "_theme", "dark"))

    def set_theme(self, name: str) -> None:
        """Переключить тему ('dark'|'light') без перезапуска."""
        self._theme = name if name in ("dark", "light") else "dark"
        qss = _STYLES_DIR / f"{self._theme}_theme.qss"
        try:
            if qss.exists():
                self.setStyleSheet(qss.read_text(encoding="utf-8"))
        except Exception:
            pass
