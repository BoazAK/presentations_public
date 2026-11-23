"""Serre simulée : capteurs (humidité, température, débit) et contrôleur de vanne.

Modes (FARM_MODE) :
- insecure : toute commande OPEN/CLOSE est exécutée ;
- secure   : la commande doit porter le token statique (défense naïve, rejouable) ;
- hardened : la commande doit être signée HMAC-SHA256, récente (<= 10 s) et jamais vue.
"""

import hashlib
import hmac
import json
import os
import random
import time
from collections import deque

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "mosquitto")
MODE = os.getenv("FARM_MODE", "insecure")
TOKEN = os.getenv("DEMO_TOKEN", "gdg-demo-token")
CMD_KEY = os.getenv("CMD_HMAC_KEY", "")
MQTT_USER = os.getenv("MQTT_USER", "simulator")
MQTT_PASS = os.getenv("MQTT_PASS", "")
CA_FILE = "/certs/ca.crt"

STATE_TOPIC = "farm/actuator/valve/state"
ALERT_TOPIC = "farm/alert"
MAX_AGE_S = 10
FLOW_OPEN_L_MIN = 33.0  # hypothèse : goutte-à-goutte 2 m³/h pour 500 m²

valve = "CLOSED"
seen_nonces = deque(maxlen=1000)


def alert(client, text):
    print(f"ALERT {text}", flush=True)
    client.publish(ALERT_TOPIC, f"simulator: {text}")


def verify(payload):
    """Retourne None si la commande est acceptée, sinon la raison du refus."""
    if MODE == "insecure":
        return None
    if MODE == "secure":
        return None if payload.get("token") == TOKEN else "token invalide"

    sig = str(payload.get("sig", ""))
    nonce = str(payload.get("nonce", ""))
    try:
        ts = int(payload.get("ts", 0))
    except (TypeError, ValueError):
        return "horodatage invalide"
    message = f"{payload.get('command')}|{ts}|{nonce}".encode()
    expected = hmac.new(CMD_KEY.encode(), message, hashlib.sha256).hexdigest()
    if not CMD_KEY or not hmac.compare_digest(sig, expected):
        return "signature HMAC invalide"
    if abs(time.time() - ts) > MAX_AGE_S:
        return f"commande expirée ({int(time.time() - ts)} s)"
    if nonce in seen_nonces:
        return "rejeu détecté (nonce déjà utilisé)"
    seen_nonces.append(nonce)
    return None


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"simulator: connexion refusée ({reason_code})", flush=True)
        return
    client.subscribe("farm/actuator/valve")
    client.publish(STATE_TOPIC, valve, retain=True)
    print(f"simulator connecté à {HOST}, mode={MODE}", flush=True)


def on_message(client, userdata, msg):
    global valve
    try:
        payload = json.loads(msg.payload.decode())
        if not isinstance(payload, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        payload = {"command": msg.payload.decode(errors="replace")}

    command = str(payload.get("command", "")).upper()
    if command not in ("OPEN", "CLOSE"):
        return

    reason = verify(payload)
    if reason:
        alert(client, f"commande {command} REJETÉE : {reason}")
        return

    valve = "OPEN" if command == "OPEN" else "CLOSED"
    client.publish(STATE_TOPIC, valve, retain=True)
    print(f"valve -> {valve}", flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="farm-simulator")
client.on_connect = on_connect
client.on_message = on_message
port = 1883
if MODE == "hardened":
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(ca_certs=CA_FILE)
    port = 8883
client.connect_async(HOST, port, 60)
client.loop_start()

while True:
    humidity = round(random.uniform(62, 68), 1)
    temperature = round(random.uniform(23, 26), 1)
    flow = round(FLOW_OPEN_L_MIN + random.uniform(-1.5, 1.5), 1) if valve == "OPEN" else 0.0
    client.publish("farm/sensor/humidity", str(humidity))
    client.publish("farm/sensor/temperature", str(temperature))
    client.publish("farm/sensor/flow", str(flow))
    time.sleep(2)
