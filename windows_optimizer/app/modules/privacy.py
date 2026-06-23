"""Модуль приватности и bloatware.

Состоит из двух частей:
  1) твики приватности (телеметрия, рекламный ID и т.п.) — переиспользуют
     реестровый движок из RegistryModule (категория 'privacy');
  2) удаление предустановленных UWP-приложений (bloatware) через PowerShell
     Get-AppxPackage | Remove-AppxPackage. Системные пакеты в список не входят.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import get_logger, log_change
from app.core.optimizer import OptimizerModule
from app.modules.registry import RegistryModule

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

# Кандидаты на удаление: (паттерн пакета, человекочитаемое имя, безопасно?).
BLOATWARE = [
    ("Microsoft.XboxGamingOverlay", "Xbox Game Bar", True),
    ("Microsoft.XboxGameOverlay", "Xbox Game Overlay", True),
    ("Microsoft.XboxApp", "Xbox App", True),
    ("Microsoft.GamingApp", "Xbox (Gaming App)", True),
    ("Microsoft.MicrosoftSolitaireCollection", "Solitaire Collection", True),
    ("Microsoft.People", "People", True),
    ("Microsoft.BingNews", "News", True),
    ("Microsoft.BingWeather", "Weather", True),
    ("Microsoft.WindowsMaps", "Maps", True),
    ("Microsoft.GetHelp", "Get Help", True),
    ("Microsoft.Getstarted", "Tips", True),
    ("Microsoft.Todos", "To Do", True),
    ("microsoft.windowscommunicationsapps", "Mail and Calendar", False),
    ("MicrosoftTeams", "Teams (Personal)", True),
    ("SpotifyAB.SpotifyMusic", "Spotify (trial)", True),
    ("Clipchamp.Clipchamp", "Clipchamp", True),
]

# Системные пакеты, которые НИКОГДА не предлагать к удалению.
PROTECTED_APPX = {
    "Microsoft.WindowsStore", "Microsoft.SecHealthUI", "Microsoft.WindowsTerminal",
    "Microsoft.DesktopAppInstaller", "Microsoft.UI.Xaml", "Microsoft.VCLibs",
}


class PrivacyModule(OptimizerModule):
    key = "privacy"
    title = "Приватность"

    def __init__(self) -> None:
        self._registry = RegistryModule()

    def privacy_tweaks(self) -> List[Dict]:
        """Твики категории privacy из реестрового модуля."""
        return [t for t in self._registry.scan() if t["category"] == "privacy"]

    def apply_privacy(self, ids: List[str]) -> Dict[str, bool]:
        return self._registry.apply_many(ids)

    def installed_bloatware(self) -> Dict[str, bool]:
        """Какие из кандидатов реально установлены (через PowerShell)."""
        installed: Dict[str, bool] = {}
        if not IS_WINDOWS:
            return installed
        try:
            ps = "Get-AppxPackage | Select-Object -ExpandProperty Name"
            cp = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True)
            names = set(cp.stdout.split())
            for pattern, _, _ in BLOATWARE:
                installed[pattern] = any(pattern.lower() in n.lower() for n in names)
        except Exception as e:  # pragma: no cover
            _log.warning("Проверка Appx не удалась: %s", e)
        return installed

    def scan(self) -> List[Dict]:
        installed = self.installed_bloatware()
        rows: List[Dict] = []
        for t in self.privacy_tweaks():
            rows.append({"kind": "tweak", "id": t["id"], "name": t["name"],
                         "status": t["status"], "risk": t["risk"]})
        for pattern, label, safe in BLOATWARE:
            rows.append({"kind": "appx", "id": pattern, "name": label,
                         "safe": safe, "installed": installed.get(pattern)})
        return rows

    def remove_appx(self, pattern: str) -> bool:
        """Удалить UWP-приложение по паттерну имени (для текущего пользователя)."""
        if pattern in PROTECTED_APPX:
            log_change("privacy", f"ЗАЩИТА: пропуск системного пакета {pattern}", status="SKIPPED")
            return False
        if not IS_WINDOWS:
            return False
        try:
            ps = f"Get-AppxPackage *{pattern}* | Remove-AppxPackage"
            cp = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True)
            ok = cp.returncode == 0
            log_change("privacy", f"remove appx {pattern}",
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("privacy", f"remove appx {pattern}", status=f"ERROR:{e}")
            return False
