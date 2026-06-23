"""Модуль сети: твики TCP/IP, профили DNS и базовая диагностика."""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import log_change
from app.core.optimizer import OptimizerModule
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"

_TCPIP = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"

# (имя, путь, тип, оптимизированное, дефолт, описание)
TCP_TWEAKS = [
    ("TcpAckFrequency", _TCPIP, "REG_DWORD", 1, 2, "Убрать задержку подтверждений TCP"),
    ("TCPNoDelay", _TCPIP, "REG_DWORD", 1, 0, "Отключить алгоритм Nagle"),
    ("Tcp1323Opts", _TCPIP, "REG_DWORD", 3, 0, "TCP timestamps + Window Scaling"),
    ("MaxUserPort", _TCPIP, "REG_DWORD", 65534, 5000, "Больше доступных портов"),
    ("TcpTimedWaitDelay", _TCPIP, "REG_DWORD", 30, 240, "Быстрее освобождать порты"),
    ("DefaultTTL", _TCPIP, "REG_DWORD", 64, 128, "Стандартный TTL"),
]

DNS_PROFILES = {
    "Cloudflare": ("1.1.1.1", "1.0.0.1"),
    "Google": ("8.8.8.8", "8.8.4.4"),
    "Quad9": ("9.9.9.9", "149.112.112.112"),
}


class NetworkModule(OptimizerModule):
    key = "network"
    title = "Сеть"

    def scan(self) -> List[Dict]:
        rows: List[Dict] = []
        for name, path, rtype, opt, default, desc in TCP_TWEAKS:
            status = "unknown"
            if IS_WINDOWS:
                try:
                    cur, _ = reg.read_value("HKLM", path, name)
                    status = ("applied" if cur == opt else
                              "default" if (cur is None or cur == default) else "modified")
                except Exception:
                    status = "unknown"
            rows.append({"name": name, "description": desc, "optimized": opt,
                         "default": default, "status": status})
        return rows

    def apply_tcp_tweaks(self) -> Dict[str, bool]:
        result: Dict[str, bool] = {}
        for name, path, rtype, opt, _default, _desc in TCP_TWEAKS:
            try:
                old, _ = reg.read_value("HKLM", path, name)
                reg.write_value("HKLM", path, name, opt, rtype)
                log_change("network", f"{name}", old=old, new=opt)
                result[name] = True
            except Exception as e:  # pragma: no cover
                log_change("network", f"{name}", status=f"ERROR:{e}")
                result[name] = False
        return result

    def set_dns(self, interface: str, profile: str) -> bool:
        """Назначить DNS из профиля для сетевого интерфейса (netsh)."""
        if not IS_WINDOWS or profile not in DNS_PROFILES:
            return False
        primary, secondary = DNS_PROFILES[profile]
        try:
            subprocess.run(["netsh", "interface", "ip", "set", "dns",
                            f"name={interface}", "static", primary], capture_output=True, text=True)
            subprocess.run(["netsh", "interface", "ip", "add", "dns",
                            f"name={interface}", secondary, "index=2"], capture_output=True, text=True)
            log_change("network", f"DNS {interface} -> {profile}", new=f"{primary},{secondary}")
            return True
        except Exception as e:  # pragma: no cover
            log_change("network", f"DNS {interface}", status=f"ERROR:{e}")
            return False

    def flush_dns(self) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
            return True
        except Exception:
            return False

    def ping(self, host: str = "1.1.1.1", count: int = 4) -> str:
        """Простой ping для диагностики (возвращает текстовый вывод)."""
        flag = "-n" if IS_WINDOWS else "-c"
        try:
            cp = subprocess.run(["ping", flag, str(count), host], capture_output=True, text=True)
            return cp.stdout or cp.stderr
        except Exception as e:  # pragma: no cover
            return f"ошибка ping: {e}"
