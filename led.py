# led.py
import time
from machine import Pin
import neopixel

class LedController:
    def __init__(self, pin_num, n=116, brightness=1):
        self.n = n
        self.brightness = brightness
        self.np = neopixel.NeoPixel(Pin(pin_num), n)

        # --- jauge ---
        self._level = 0                # 0..100 (cible)
        self._level_smooth = 0.0       # lissé
        self._last_gauge_ms = 0

        # --- animations wave ---
        self._anim_active = False
        self._anim_t0 = 0
        self._anim_duration = 0
        self._anim_speed = 0
        self._anim_phase = 0
        self._anim_last_frame = -1

        # --- state display ---
        self._state_active = False
        self._state = "CENTER"
        self._state_inner = 10
        self._state_outer = 20
        self._state_color = (255, 255, 255)

        self.clear()

    def _scale(self, r, g, b):
        br = self.brightness
        return (int(r * br), int(g * br), int(b * br))

    def clear(self):
        for i in range(self.n):
            self.np[i] = (0, 0, 0)
        self.np.write()

    # ---------- helpers ----------
    def _wheel(self, pos):
        pos &= 255
        if pos < 85:
            return (255 - pos * 3, pos * 3, 0)
        if pos < 170:
            pos -= 85
            return (0, 255 - pos * 3, pos * 3)
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)

    def _smoothstep(self, x):
        # x in [0..1]
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        return x * x * (3.0 - 2.0 * x)

    def _gamma(self, v):
        # v in [0..1]
        if v <= 0:
            return 0.0
        if v >= 1:
            return 1.0
        return v ** 2.2

    # ---------- animations send/recv ----------
    def _start_wave(self, duration_ms, speed_ms, phase_offset):
        self._anim_active = True
        self._anim_t0 = time.ticks_ms()
        self._anim_duration = duration_ms
        self._anim_speed = speed_ms
        self._anim_phase = phase_offset
        self._anim_last_frame = -1

    def on_send(self):
        # vague courte & nerveuse
        self._start_wave(duration_ms=450, speed_ms=25, phase_offset=0)

    def on_recv(self):
        # vague un peu plus longue
        self._start_wave(duration_ms=650, speed_ms=30, phase_offset=90)

    # ---------- jauge ----------
    def set_level(self, percent):
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        self._level = percent

    def set_state(self, state, inner_count=10, outer_count=20, color=(255, 255, 255)):
        self._state_active = True
        self._state = str(state).upper()
        self._state_inner = max(1, int(inner_count))
        self._state_outer = max(self._state_inner, int(outer_count))
        self._state_color = color

    def clear_state(self):
        self._state_active = False

    def bar_from_axis(self, axis_value, color=(255, 255, 0)):
        # Compat API: map axis in [-1..1] to gauge level (0..100).
        # color is ignored to keep the existing gauge style.
        if axis_value < -1.0:
            axis_value = -1.0
        elif axis_value > 1.0:
            axis_value = 1.0
        percent = int((axis_value + 1.0) * 50)
        self.set_level(percent)

    def _color_gauge(self, i):
        # dégradé rouge -> vert
        if self.n <= 1:
            return (0, 255, 0)
        t = i / (self.n - 1)   # 0..1
        r = int(255 * (1.0 - t))
        g = int(255 * t)
        b = 0
        return (r, g, b)

    def _render_gauge(self, percent_float):
        filled = (percent_float / 100.0) * self.n  # 0..n

        for i in range(self.n):
            d = filled - i

            if d >= 1:
                intensity = 1.0
            elif d <= 0:
                intensity = 0.0
            else:
                intensity = self._smoothstep(d)

            # petite traîne (halo) derrière le front
            trail = 0.0
            if d < 0:
                # proche du front => un petit glow
                trail = max(0.0, 0.18 + d)  # d=-0.1 => 0.08, d=-0.2 => 0
                trail = self._smoothstep(trail) * 0.25

            level = max(intensity, trail)
            level = self._gamma(level)

            r, g, b = self._color_gauge(i)
            self.np[i] = self._scale(int(r * level), int(g * level), int(b * level))

        self.np.write()

    def _render_state(self):
        state = self._state
        inner = self._state_inner
        outer = self._state_outer

        if inner > self.n:
            inner = self.n
        if outer > self.n:
            outer = self.n

        for i in range(self.n):
            self.np[i] = (0, 0, 0)

        r, g, b = self._scale(*self._state_color)

        if state in ("1", "LEFT"):
            start, end = 0, inner
        elif state in ("3", "RIGHT"):
            start, end = self.n - inner, self.n
        else:
            start = (self.n - inner) // 2
            end = start + inner

        for i in range(start, end):
            if 0 <= i < self.n:
                self.np[i] = (r, g, b)

        self.np.write()

    # ---------- update global ----------
    def update(self):
        now = time.ticks_ms()

        # 1) PRIORITÉ: animation wave (send/recv)
        if self._anim_active:
            elapsed = time.ticks_diff(now, self._anim_t0)

            if elapsed >= self._anim_duration:
                self._anim_active = False
                # retour automatique à la jauge dès la prochaine frame
            else:
                frame = elapsed // self._anim_speed
                if frame != self._anim_last_frame:
                    self._anim_last_frame = frame

                    base = (frame * 10 + self._anim_phase) & 255
                    spacing = 256 // self.n

                    for i in range(self.n):
                        color = self._wheel((base + i * spacing) & 255)
                        self.np[i] = self._scale(*color)

                    self.np.write()
                return  # pendant l'anim, on n'affiche pas la jauge

        # 2) Mode état
        if self._state_active:
            self._render_state()
            return

        # 3) Mode normal: jauge fluide (20ms)
        if time.ticks_diff(now, self._last_gauge_ms) < 20:
            return
        self._last_gauge_ms = now

        # lissage doux (plus bas = plus fluide)
        alpha = 0.12
        self._level_smooth = (1 - alpha) * self._level_smooth + alpha * self._level

        self._render_gauge(self._level_smooth)
