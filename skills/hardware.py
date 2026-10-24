from core import hardware
from core.hardware import HardwareError, SENSORS

USAGE = (
    "usage:\n"
    "  hw status          - mode and connection check\n"
    "  hw read <temp|hum|light>\n"
    "  hw led <on|off>\n"
    "  hw reconnect       - reopen the device after changing env vars"
)


def register(app):
    app._register("hw", hw, "Hardware: hw status | hw read <sensor> | hw led on|off")


def hw(rest: str) -> str:
    parts = rest.strip().lower().split()
    if not parts:
        return USAGE
    action = parts[0]
    try:
        if action == "reconnect":
            hardware.reset_device()
            return "device reset. " + _status()
        if action == "status":
            return _status()
        if action == "read" and len(parts) == 2:
            sensor = parts[1]
            if sensor not in SENSORS:
                return "unknown sensor. choose: " + ", ".join(SENSORS)
            value = hardware.get_device().read(sensor)
            return f"{sensor}: {value} {SENSORS[sensor][1]}"
        if action == "led" and len(parts) == 2 and parts[1] in ("on", "off"):
            hardware.get_device().set_led(parts[1] == "on")
            return f"led {parts[1]}"
    except HardwareError as e:
        return f"hw error: {e}"
    return USAGE


def _status() -> str:
    dev = hardware.get_device()
    ok = "connected" if dev.ping() else "not responding"
    return f"hardware mode: {dev.mode} ({ok})"
