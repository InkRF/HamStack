"""USB foot-pedal reader (evdev), adapted from the selfie_station pedal loop."""

from __future__ import annotations

import select
import threading
import time
from typing import Callable

MIN_TRIGGER_INTERVAL_SECONDS = 0.5
REOPEN_DELAY_SECONDS = 3.0


class Pedal:
    """Grabs the pedal input device and calls on_press for each key-down.

    The device is reopened after unplug/replug so a bumped USB cable at the
    booth does not need a service restart.
    """

    def __init__(self, device: str, key_name: str, on_press: Callable[[], None], log):
        self.device_path = device
        self.key_name = key_name
        self.on_press = on_press
        self.log = log
        self._running = False
        self._device = None

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._loop, name="pedal", daemon=True).start()

    def stop(self) -> None:
        self._running = False
        self._close()

    def _close(self) -> None:
        if self._device is None:
            return
        try:
            self._device.ungrab()
        except OSError:
            pass
        try:
            self._device.close()
        except OSError:
            pass
        self._device = None

    def _loop(self) -> None:
        from evdev import InputDevice, ecodes

        key_code = getattr(ecodes, self.key_name)
        last_trigger = 0.0

        while self._running:
            try:
                if self._device is None:
                    self._device = InputDevice(self.device_path)
                    self._device.grab()
                    self.log(f"Pedal opened: {self.device_path}")

                ready, _, _ = select.select([self._device.fd], [], [], 0.5)
                if not ready:
                    continue

                for event in self._device.read():
                    if event.type != ecodes.EV_KEY or event.code != key_code or event.value != 1:
                        continue
                    now = time.monotonic()
                    if now - last_trigger < MIN_TRIGGER_INTERVAL_SECONDS:
                        continue
                    last_trigger = now
                    self.on_press()
            except OSError as exc:
                self.log(f"Pedal unavailable ({exc}); retrying")
                self._close()
                time.sleep(REOPEN_DELAY_SECONDS)
