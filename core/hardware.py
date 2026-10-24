"""Hardware bridge: talk to a microcontroller (Arduino / ESP32 / Pi Pico) or simulate one.

Modes (SPEKTRA_HW):
  sim     (default) fake sensors so everything works with no hardware
  serial  real board over USB serial (needs `pip install pyserial`)

Serial line protocol (115200 baud by default, one command per line, one reply per line):
  PING        -> PONG
  GET TEMP    -> 24.6        (deg C)
  GET HUM     -> 51.2        (% RH)
  GET LIGHT   -> 340         (raw ADC 0-1023)
  LED ON      -> OK
  LED OFF     -> OK
A ready-made Arduino/ESP32 sketch is in docs/firmware/spektra_board.ino.

Env: SPEKTRA_SERIAL_PORT (e.g. /dev/ttyUSB0, COM3), SPEKTRA_SERIAL_BAUD
"""
import os
import random
import threading
from typing import Dict, Optional

SENSORS = {
    "temp": ("GET TEMP", "C"),
    "hum": ("GET HUM", "%"),
    "light": ("GET LIGHT", "raw"),
}


class HardwareError(RuntimeError):
    pass


class SimulatedDevice:
    mode = "sim"

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._values = {"temp": 27.0, "hum": 60.0, "light": 400.0}
        self.led = False

    def _drift(self, key: str, step: float, lo: float, hi: float) -> float:
        v = self._values[key] + self._rng.uniform(-step, step)
        self._values[key] = min(hi, max(lo, v))
        return self._values[key]

    def read(self, sensor: str) -> float:
        if sensor == "temp":
            return round(self._drift("temp", 0.4, 18, 40), 1)
        if sensor == "hum":
            return round(self._drift("hum", 1.0, 20, 95), 1)
        if sensor == "light":
            return round(self._drift("light", 25, 0, 1023))
        raise HardwareError(f"unknown sensor '{sensor}'")

    def set_led(self, on: bool) -> None:
        self.led = on

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass


class SerialDevice:
    mode = "serial"

    def __init__(self, port: str, baud: int = 115200, timeout: float = 2.0):
        try:
            import serial  # pyserial
        except Exception as e:
            raise HardwareError("pyserial not installed: pip install pyserial") from e
        try:
            self._ser = serial.Serial(port, baud, timeout=timeout)
        except Exception as e:
            raise HardwareError(f"cannot open {port}: {e}") from e
        self._lock = threading.Lock()
        self.led = False

    def _ask(self, line: str) -> str:
        with self._lock:
            self._ser.reset_input_buffer()
            self._ser.write((line + "\n").encode("ascii"))
            reply = self._ser.readline().decode("ascii", errors="ignore").strip()
        if not reply:
            raise HardwareError("no reply from board (timeout)")
        return reply

    def read(self, sensor: str) -> float:
        if sensor not in SENSORS:
            raise HardwareError(f"unknown sensor '{sensor}'")
        reply = self._ask(SENSORS[sensor][0])
        try:
            return float(reply)
        except ValueError:
            raise HardwareError(f"bad reply from board: {reply!r}")

    def set_led(self, on: bool) -> None:
        reply = self._ask("LED ON" if on else "LED OFF")
        if reply != "OK":
            raise HardwareError(f"board said: {reply}")
        self.led = on

    def ping(self) -> bool:
        try:
            return self._ask("PING") == "PONG"
        except HardwareError:
            return False

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:
            pass


_device = None
_device_lock = threading.Lock()


def get_device():
    """Lazily create the configured device (shared by commands and widgets)."""
    global _device
    with _device_lock:
        if _device is None:
            mode = os.environ.get("SPEKTRA_HW", "sim").lower()
            if mode == "serial":
                port = os.environ.get("SPEKTRA_SERIAL_PORT")
                if not port:
                    raise HardwareError("set SPEKTRA_SERIAL_PORT (e.g. /dev/ttyUSB0 or COM3)")
                baud = int(os.environ.get("SPEKTRA_SERIAL_BAUD", "115200"))
                _device = SerialDevice(port, baud)
            else:
                _device = SimulatedDevice()
        return _device


def reset_device() -> None:
    global _device
    with _device_lock:
        if _device is not None:
            _device.close()
        _device = None


def snapshot() -> Dict[str, str]:
    """Compact reading for the HUD widget; never raises."""
    try:
        dev = get_device()
        return {
            "mode": dev.mode,
            "temp": f"{dev.read('temp')} C",
            "hum": f"{dev.read('hum')} %",
            "led": "on" if dev.led else "off",
        }
    except Exception as e:
        return {"mode": "error", "temp": "n/a", "hum": "n/a", "led": "n/a", "error": str(e)}
