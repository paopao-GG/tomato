"""Fruit-picker trigger.

For now this is a safe stub: triggering just logs and reports status, so the
app runs with no Arduino attached. The real pyserial path is implemented but
gated behind config.SERIAL_ENABLED, ready to switch on once the Arduino Mega
(servo scissor) is wired. Protocol matches the PRD: send b"PICK\\n".
"""
from __future__ import annotations

from typing import Callable, Optional

from . import config


class Picker:
    def __init__(self, status_cb: Optional[Callable[[str], None]] = None,
                 serial_enabled: bool = config.SERIAL_ENABLED,
                 port: str = config.SERIAL_PORT, baud: int = config.SERIAL_BAUD):
        self.status_cb = status_cb
        self.serial_enabled = serial_enabled
        self.port = port
        self.baud = baud
        self._ser = None
        if self.serial_enabled:
            self._open()

    def _open(self):
        try:
            import serial
            self._ser = serial.Serial(self.port, self.baud, timeout=1)
            self._status(f"Serial open on {self.port}")
        except Exception as e:  # noqa: BLE001 - report and degrade to stub
            self._ser = None
            self._status(f"Serial open failed ({e}); using stub")

    def trigger(self, reason: str = "manual"):
        """Trigger one pick. Writes to the Arduino if serial is enabled/open,
        otherwise logs as a stub."""
        if self.serial_enabled and self._ser is not None:
            try:
                self._ser.write(config.SERIAL_PICK_CMD)
                msg = f"PICK -> Arduino ({reason})"
            except Exception as e:  # noqa: BLE001
                msg = f"Serial write failed ({e})"
        else:
            msg = f"[STUB] PICK ({reason})"
        print(msg)
        self._status(msg)

    def _status(self, msg: str):
        if self.status_cb is not None:
            self.status_cb(msg)

    def close(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass
            self._ser = None
