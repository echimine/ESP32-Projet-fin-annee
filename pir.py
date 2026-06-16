from sensor import Sensor, SensorState
from machine import Pin
import time

class PIRState(SensorState):
    def __init__(self, detected):
        self.detected = detected

    def __str__(self):
        return "PIR: mouvement détecté" if self.detected else "PIR: calme"

    def to_json(self):
        import json
        return json.dumps({"detected": self.detected})

class PIRSensor(Sensor):
    def __init__(self, pin_num, on_motion=None, retrigger_ms=2000):
        self._pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
        self._on_motion = on_motion
        self._retrigger_ms = retrigger_ms
        self._last_trigger = 0
        self.state = PIRState(False)

    def read(self):
        val = self._pin.value()
        now = time.ticks_ms()
        if val == 1:
            self.state = PIRState(True)
            if time.ticks_diff(now, self._last_trigger) >= self._retrigger_ms:
                self._last_trigger = now
                print("[PIR] Mouvement détecté")
                if self._on_motion:
                    self._on_motion()
        else:
            self.state = PIRState(False)
        return self.state