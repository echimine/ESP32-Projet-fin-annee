from sensor import Sensor, SensorState
from machine import Pin
import time
import json


class LD2410CState(SensorState):
    def __init__(self, detected):
        self.detected = detected

    def __str__(self):
        return "LD2410C: présence détectée" if self.detected else "LD2410C: aucune présence"

    def to_json(self):
        return json.dumps({"detected": self.detected})


class LD2410CSensor(Sensor):
    def __init__(self, pin_num, on_presence=None, retrigger_ms=5000):
        self._pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        self._on_presence = on_presence
        self._retrigger_ms = retrigger_ms
        self._last_trigger = 0
        self.state = LD2410CState(False)

    def read(self):
        val = self._pin.value()
        now = time.ticks_ms()

        if val == 1:
            self.state = LD2410CState(True)
            if time.ticks_diff(now, self._last_trigger) >= self._retrigger_ms:
                self._last_trigger = now
                if self._on_presence:
                    self._on_presence()
        else:
            self.state = LD2410CState(False)

        return self.state
