from sensor import Sensor, SensorState
from machine import ADC, Pin
import time
import json
import ubinascii


class KY037State(SensorState):
    def __init__(self, recording=False, finished=False, duration_ms=0):
        self.recording = recording
        self.finished = finished
        self.duration_ms = duration_ms

    def __str__(self):
        if self.recording:
            return "KY037: enregistrement en cours"
        if self.finished:
            return "KY037: enregistrement terminé"
        return "KY037: inactif"

    def to_json(self):
        return json.dumps({
            "recording": self.recording,
            "finished": self.finished,
            "duration_ms": self.duration_ms
        })


class KY037RecorderSensor(Sensor):
    def __init__(
        self,
        mic_pin_num,
        button_pin_num,
        on_audio_ready=None,
        on_recording_start=None,
        sample_rate=8000,
        max_seconds=8,
        debounce_ms=300
    ):
        # Micro KY-037 sur AO
        self._adc = ADC(Pin(mic_pin_num))
        self._adc.atten(ADC.ATTN_11DB)
        self._adc.width(ADC.WIDTH_12BIT)

        # Bouton en PULL_UP
        # relâché = 1
        # appuyé = 0
        self._button = Pin(button_pin_num, Pin.IN, Pin.PULL_UP)

        self._on_audio_ready = on_audio_ready
        self._on_recording_start = on_recording_start

        self._sample_rate = sample_rate
        self._sample_period_us = int(1000000 / sample_rate)
        self._max_samples = sample_rate * max_seconds

        self._debounce_ms = debounce_ms
        self._last_button = 1
        self._last_button_time = 0

        self._samples = bytearray()
        self._recording = False
        self._recording_start_ms = 0
        self._next_sample_us = 0

        self.state = KY037State(False, False, 0)

    def read(self):
        self._handle_button()

        if self._recording:
            self._record_samples()

        return self.state

    def _handle_button(self):
        button_value = self._button.value()
        now = time.ticks_ms()

        # Détection appui bouton : passage 1 -> 0
        if button_value == 0 and self._last_button == 1:
            if time.ticks_diff(now, self._last_button_time) > self._debounce_ms:
                self._last_button_time = now

                if not self._recording:
                    self.start()
                else:
                    self.stop()

        self._last_button = button_value

    def start(self):
        self._samples = bytearray()
        self._recording = True
        self._recording_start_ms = time.ticks_ms()
        self._next_sample_us = time.ticks_us()

        self.state = KY037State(
            recording=True,
            finished=False,
            duration_ms=0
        )

        if self._on_recording_start:
            self._on_recording_start()

    def stop(self):
        if not self._recording:
            return

        self._recording = False

        duration_ms = time.ticks_diff(
            time.ticks_ms(),
            self._recording_start_ms
        )

        wav_data = self._to_wav(self._samples, self._sample_rate)
        audio_base64 = ubinascii.b2a_base64(wav_data).decode("utf-8").strip()

        self.state = KY037State(
            recording=False,
            finished=True,
            duration_ms=duration_ms
        )

        if self._on_audio_ready:
            self._on_audio_ready(audio_base64, duration_ms)

    def _record_samples(self):
        now = time.ticks_us()

        while time.ticks_diff(now, self._next_sample_us) >= 0:
            raw = self._adc.read()

            # ESP32 ADC : 0 à 4095
            # Audio WAV 8 bits : 0 à 255
            sample_8bit = raw >> 4

            self._samples.append(sample_8bit)

            self._next_sample_us = time.ticks_add(
                self._next_sample_us,
                self._sample_period_us
            )

            # Sécurité : arrêt automatique si durée max atteinte
            if len(self._samples) >= self._max_samples:
                self.stop()
                break

            now = time.ticks_us()

    def _to_wav(self, pcm_data, sample_rate):
        num_channels = 1
        bits_per_sample = 8
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(pcm_data)
        file_size = 36 + data_size

        header = bytearray()

        header.extend(b"RIFF")
        header.extend(self._int_to_bytes(file_size, 4))
        header.extend(b"WAVE")

        header.extend(b"fmt ")
        header.extend(self._int_to_bytes(16, 4))
        header.extend(self._int_to_bytes(1, 2))
        header.extend(self._int_to_bytes(num_channels, 2))
        header.extend(self._int_to_bytes(sample_rate, 4))
        header.extend(self._int_to_bytes(byte_rate, 4))
        header.extend(self._int_to_bytes(block_align, 2))
        header.extend(self._int_to_bytes(bits_per_sample, 2))

        header.extend(b"data")
        header.extend(self._int_to_bytes(data_size, 4))

        return header + pcm_data

    def _int_to_bytes(self, value, length):
        result = bytearray()

        for i in range(length):
            result.append((value >> (8 * i)) & 0xFF)

        return result