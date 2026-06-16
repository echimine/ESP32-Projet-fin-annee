# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()
import network
import time


print("In BOOT")


def wifi_connect(ssid: str, password: str, timeout_s: int = 15):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout_s:
            raise RuntimeError("WiFi: connexion impossible (timeout)")
        time.sleep(0.2)

    return wlan

wlan = wifi_connect("NETGEAR13", "silkyrabbit648")
print("Connecté ! IP =", wlan.ifconfig())