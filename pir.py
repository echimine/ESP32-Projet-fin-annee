from sensor import Sensor, SensorState
from machine import Pin

class PIRState(SensorState):
    def __init__(self, detected):
        self.detected = detected

    def __str__(self):
        return "PIR: mouvement détecté" if self.detected else "PIR: calme"

    def to_json(self):
        import json
        return json.dumps({"detected": self.detected})

class PIRSensor(Sensor):
    def __init__(self, pin_num, on_motion=None):
        self._pin = Pin(pin_num, Pin.IN)
        self._on_motion = on_motion
        self._last = 0
        self.state = PIRState(False)

    def read(self):
        val = self._pin.value()
        if val == 1 and self._last == 0:
            self.state = PIRState(True)
            if self._on_motion:
                self._on_motion()
        elif val == 0:
            self.state = PIRState(False)
        self._last = val
        return self.state