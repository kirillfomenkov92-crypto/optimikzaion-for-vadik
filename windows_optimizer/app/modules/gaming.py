"""Модуль игровой оптимизации: Game Bar/DVR, fullscreen, GPU-приоритет, BCD."""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import log_change
from app.core.optimizer import OptimizerModule
from app.core.tweak_applier import RegistryTweakApplier
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"

_GAMES_TASK = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"

# (hive, path, name, type, optimized, default, описание)
# ВНИМАНИЕ: GameDVR_Enabled (HKCU\System\GameConfigStore) сюда НЕ добавлять —
# этим твиком владеет БД (tweaks_database.json, id=disable_gamebar_dvr), чтобы
# не было двух источников правды и расхождения статуса/применения.
GAME_TWEAKS = [
    ("HKCU", r"SOFTWARE\Microsoft\GameBar", "AutoGameModeEnabled", "REG_DWORD", 1, 1, "Game Mode включён"),
    ("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", "REG_DWORD", 2, 0, "Отключить fullscreen optimization"),
    ("HKLM", _GAMES_TASK, "GPU Priority", "REG_DWORD", 8, 8, "GPU-приоритет для игр"),
    ("HKLM", _GAMES_TASK, "Priority", "REG_DWORD", 6, 2, "Приоритет планировщика для игр"),
]


class GamingModule(OptimizerModule):
    key = "gaming"
    title = "Игры"

    def scan(self) -> List[Dict]:
        rows: List[Dict] = []
        for hive, path, name, _t, opt, default, desc in GAME_TWEAKS:
            status = "unknown"
            if IS_WINDOWS:
                try:
                    cur, _ = reg.read_value(hive, path, name)
                    status = ("applied" if cur == opt else
                              "default" if (cur is None or cur == default) else "modified")
                except Exception:
                    status = "unknown"
            rows.append({"name": name, "description": desc, "status": status})
        return rows

    def apply_all(self) -> Dict[str, bool]:
        # Единый применятель с верификацией read-back (см. app/core/tweak_applier).
        tweaks = [(hive, path, name, rtype, opt)
                  for hive, path, name, rtype, opt, _d, _desc in GAME_TWEAKS]
        return RegistryTweakApplier.apply_many(tweaks, module="gaming")

    def set_hpet(self, enabled: bool) -> bool:
        """Управление HPET через bcdedit. ВНИМАНИЕ: эффект индивидуален — тестировать."""
        if not IS_WINDOWS:
            return False
        try:
            arg = "useplatformclock" if enabled else "deletevalue"
            cmd = ["bcdedit", "/set", "useplatformclock", "true"] if enabled else \
                  ["bcdedit", "/deletevalue", "useplatformclock"]
            cp = subprocess.run(cmd, capture_output=True, text=True)
            ok = cp.returncode == 0
            log_change("gaming", f"HPET {'on' if enabled else 'off'}",
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("gaming", "HPET", status=f"ERROR:{e}")
            return False
