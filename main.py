from wsclient import WSClient
from message import Message, MessageType, ENVOI_TYPE, SensorId
from orchestrator import Orchestrator
from pir import PIRSensor
from ld2410c import LD2410CSensor
from machine import Pin
import time
import neopixel

# === CONFIG ===
USERNAME    = "ESP32-MOTION"
WS_URL      = "ws://192.168.1.10:8765"

PIR_PIN     = 14
RADAR_PIN   = 27

LED_PIN     = 5
NUM_LEDS    = 30

ACTIVE_MS   = 1000   # temps pendant lequel les LEDs restent allumées
COOLDOWN_MS = 500    # temps avant une nouvelle détection

# === INIT LEDs ===
np = neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS)

for i in range(NUM_LEDS):
    np[i] = (0, 0, 0)

np.write()

# === ÉTAT ===
_motion_active = False
_cooldown_active = False

_motion_t0 = 0
_cooldown_t0 = 0

_last_radar_state = 0

# === LEDS ===
def leds_on_red():
    for i in range(NUM_LEDS):
        np[i] = (255, 255, 255)
    np.write()
    print("[LED] LEDs allumées")


def leds_off():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()
    print("[LED] LEDs éteintes")


# === WEBSOCKET ===
def send_motion_message(sensor_name):
    global ws

    if ws.open:
        msg = Message(
            message_type=ENVOI_TYPE.SENSOR,
            emitter=USERNAME,
            receiver="ESP32-CAM",
            sensor_id=sensor_name,
            value='{"detected": true}'
        )
        ws.send(msg.to_json())
        print("[WS] Ordre photo envoyé à ESP32-CAM via", sensor_name)
    else:
        print("[WS] WebSocket non connecté, message non envoyé")


# === DÉTECTION ===
def trigger_motion(sensor_name):
    global _motion_active, _cooldown_active, _motion_t0

    if _motion_active:
        return

    if _cooldown_active:
        return

    _motion_active = True
    _motion_t0 = time.ticks_ms()

    send_motion_message(sensor_name)
    leds_on_red()


# === CALLBACKS WS ===
def on_connect(ws):
    print("[WS] Connecté")

    msg = Message(
        message_type=MessageType.DECLARATION,
        emitter=USERNAME,
        receiver="SERVER",
        value="hello je suis connecté"
    )

    ws.send(msg.to_json())


def on_message(raw):
    received = Message.from_json(raw)

    mtype   = received.message_type
    value   = received.value
    emitter = received.emitter

    if mtype == "SYS_MESSAGE":
        print("[SYS]", value)
        return

    if mtype == "DECLARATION":
        print("[DECLARATION]", emitter, "connecté")
        return

    print("[MSG]", mtype, ":", value)


def on_close():
    print("[WS] Déconnecté")
    leds_off()



# === INIT ===
ws = WSClient(
    WS_URL,
    on_message=on_message,
    on_connect=on_connect,
    on_close=on_close
)

radar = LD2410CSensor(
    RADAR_PIN,
    on_presence=lambda: trigger_motion("LD2410C"),
    retrigger_ms=5000
)

o = Orchestrator(verbose=False) \
    .add_sensor(radar)

print("[SYSTEM] Programme démarré")
print("[RADAR] Lecture sur GPIO", RADAR_PIN)


# === BOUCLE PRINCIPALE ===
while True:
    # Poll WebSocket
    ws.poll()

    # Lecture des capteurs via orchestrator
    o.update()

    now = time.ticks_ms()

    # Fin de la détection active après ACTIVE_MS
    if _motion_active:
        if time.ticks_diff(now, _motion_t0) >= ACTIVE_MS:
            _motion_active = False
            _cooldown_active = True
            _cooldown_t0 = now
            leds_off()

    # Fin du cooldown
    if _cooldown_active:
        if time.ticks_diff(now, _cooldown_t0) >= COOLDOWN_MS:
            _cooldown_active = False
            print("[SYSTEM] Prêt à détecter")

    time.sleep(0.01)