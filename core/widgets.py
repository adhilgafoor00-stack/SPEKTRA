import time, socket
from typing import Dict
try:
    import psutil
except Exception:
    psutil = None

import requests

def net_status(timeout=2.0) -> Dict[str, str]:
    t0 = time.time()
    ok = False; latency_ms = None
    try:
        r = requests.get("https://httpbin.org/get", timeout=timeout)
        ok = r.ok
        latency_ms = int((time.time() - t0) * 1000)
    except Exception:
        ok = False
    ip = "unknown"
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        pass
    return {"online": ok, "latency_ms": latency_ms, "ip": ip}

def sys_stats() -> Dict[str, str]:
    if psutil is None:
        return {"cpu": "n/a", "mem": "n/a", "procs": "n/a"}
    try:
        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory()
        return {
            "cpu": f"{cpu:.1f}%",
            "mem": f"{mem.percent:.1f}%",
            "procs": str(len(psutil.pids()))
        }
    except Exception:
        return {"cpu": "n/a", "mem": "n/a", "procs": "n/a"}

def get_widgets():
    return {
        "clock": int(time.time()),
        "system": sys_stats(),
        "network": net_status(),
    }
