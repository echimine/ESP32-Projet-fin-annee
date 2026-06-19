from sensor import Sensor, SensorState
from machine import Pin
import time
import json


class ButtonState(SensorState):
    def __init__(self, pressed=False):
        self.pressed = pressed

    def __str__(self):
        return "Button: appuyé" if self.pressed else "Button: relâché"

    def to_json(self):
        return json.dumps({"pressed": self.pressed})


class ButtonSensor(Sensor):
    def __init__(self, pin_num, on_press=None, on_release=None, debounce_ms=300):
        self._pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self._on_press = on_press
        self._on_release = on_release
        self._debounce_ms = debounce_ms
        self._last_value = 1
        self._last_press_time = 0
        self.state = ButtonState(False)

    def read(self):
        value = self._pin.value()
        now = time.ticks_ms()

        # Front descendant 1→0 : appui
        if value == 0 and self._last_value == 1:
            if time.ticks_diff(now, self._last_press_time) > self._debounce_ms:
                self._last_press_time = now
                self.state = ButtonState(True)
                if self._on_press:
                    self._on_press()

        # Front montant 0→1 : relâche
        elif value == 1 and self._last_value == 0:
            self.state = ButtonState(False)
            if self._on_release:
                self._on_release()

        self._last_value = value
        return self.state
