"""Dashboard de la serre : télémétrie, modèle de rendement, impact, commandes de vanne.

Contrôles par mode (FARM_MODE) :
- insecure : aucun ;
- secure   : plage [20, 100] sur l'humidité, Bearer token sur l'API vanne,
             commande MQTT portant un token statique (défense naïve) ;
- hardened : secure + MQTT TLS/identité/ACL, commandes signées HMAC avec nonce
             et horodatage, détection de saut brutal, cohérence vanne/débit.
"""

import hashlib
import hmac
import json
import os
import secrets
import statistics
import threading
import time
from collections import deque

import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request

HOST = os.getenv("MQTT_HOST", "mosquitto")
MODE = os.getenv("FARM_MODE", "insecure")
TOKEN = os.getenv("DEMO_TOKEN", "gdg-demo-token")
CMD_KEY = os.getenv("CMD_HMAC_KEY", "")
MQTT_USER = os.getenv("MQTT_USER", "dashboard")
MQTT_PASS = os.getenv("MQTT_PASS", "")
CA_FILE = "/certs/ca.crt"

# Hypothèses d'impact (ordres de grandeur, affichées sur la page).
HYPOTHESES = {
    "serre": "Serre de tomates, 500 m², maraîchage péri-urbain (Lomé)",
    "rendement_kg": 4000,  # 8 kg/m² par cycle
    "prix_fcfa_kg": 500,  # prix bord-champ moyen
    "debit_l_min": 33,  # goutte-à-goutte, 2 m³/h
    "eau_fcfa_m3": 600,  # eau + pompage électrique
    "acceleration": 60,  # 1 s de démo = 1 min réelle
}
RECOLTE_FCFA = HYPOTHESES["rendement_kg"] * HYPOTHESES["prix_fcfa_kg"]

RANGE = (20, 100)
MAX_JUMP = 5.0  # écart maximal toléré par rapport à la médiane récente

app = Flask(__name__)
lock = threading.Lock()
history = deque(maxlen=300)
events = deque(maxlen=40)
latest = {"humidity": None, "temperature": None, "flow": 0.0, "valve": "CLOSED"}
impact = {"liters": 0.0, "last_flow_ts": None, "mismatch": False}


def log_event(level, text):
    print(f"{level.upper()} {text}", flush=True)
    with lock:
        events.appendleft({"t": time.strftime("%H:%M:%S"), "level": level, "text": text})


def check_humidity(number):
    """Retourne None si la mesure est acceptée, sinon la raison du refus."""
    if MODE == "insecure":
        return None
    if not RANGE[0] <= number <= RANGE[1]:
        return f"hors plage {list(RANGE)}"
    if MODE == "hardened" and len(history) >= 5:
        median = statistics.median(list(history)[-10:])
        if abs(number - median) > MAX_JUMP:
            return f"saut anormal ({median:.1f} → {number})"
    return None


def on_flow(value):
    now = time.time()
    last = impact["last_flow_ts"]
    if last is not None and value > 0:
        dt = min(now - last, 5)
        impact["liters"] += value * dt / 60 * HYPOTHESES["acceleration"]
    impact["last_flow_ts"] = now
    latest["flow"] = value

    if MODE == "hardened":
        mismatch = latest["valve"] == "CLOSED" and value > 1
        if mismatch and not impact["mismatch"]:
            log_event("alert", f"incohérence : vanne affichée CLOSED mais débit {value} L/min")
        impact["mismatch"] = mismatch


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"dashboard: connexion MQTT refusée ({reason_code})", flush=True)
        return
    client.subscribe("farm/sensor/#")
    client.subscribe("farm/actuator/valve/state")
    client.subscribe("farm/alert")


def on_message(client, userdata, msg):
    value = msg.payload.decode(errors="replace")
    if msg.topic == "farm/alert":
        log_event("alert", value)
        return
    if msg.topic == "farm/actuator/valve/state":
        latest["valve"] = value
        return
    try:
        number = float(value)
    except ValueError:
        return
    if msg.topic == "farm/sensor/humidity":
        reason = check_humidity(number)
        if reason:
            log_event("alert", f"humidité {number} REJETÉE : {reason}")
            return
        latest["humidity"] = number
        history.append(number)
    elif msg.topic == "farm/sensor/temperature":
        latest["temperature"] = number
    elif msg.topic == "farm/sensor/flow":
        on_flow(number)


def make_client(client_id):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    port = 1883
    if MODE == "hardened":
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.tls_set(ca_certs=CA_FILE)
        port = 8883
    client.connect_async(HOST, port, 60)
    return client


subscriber = make_client("farm-dashboard")
subscriber.on_connect = on_connect
subscriber.on_message = on_message
subscriber.loop_start()
publisher = make_client("farm-dashboard-pub")
publisher.loop_start()


def command_payload(command):
    if MODE == "insecure":
        return {"command": command}
    if MODE == "secure":
        return {"command": command, "token": TOKEN}
    ts = int(time.time())
    nonce = secrets.token_hex(8)
    sig = hmac.new(CMD_KEY.encode(), f"{command}|{ts}|{nonce}".encode(), hashlib.sha256)
    return {"command": command, "ts": ts, "nonce": nonce, "sig": sig.hexdigest()}


def send_command(command):
    publisher.publish("farm/actuator/valve", json.dumps(command_payload(command)))


def score():
    if not history:
        return 100
    sample = list(history)[-20:]
    average = sum(sample) / len(sample)
    return max(0, min(100, round(100 - abs(65 - average) * 2.2)))


def impact_summary():
    current = score()
    water_fcfa = impact["liters"] / 1000 * HYPOTHESES["eau_fcfa_m3"]
    # En dessous de 95 % de score, la perte est proportionnelle à l'écart.
    crop_fcfa = RECOLTE_FCFA * max(0, 95 - current) / 95
    return {
        "liters": round(impact["liters"]),
        "water_fcfa": round(water_fcfa),
        "crop_at_risk_fcfa": round(crop_fcfa),
        "total_fcfa": round(water_fcfa + crop_fcfa),
    }


def authorized():
    return MODE == "insecure" or request.headers.get("Authorization") == f"Bearer {TOKEN}"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    with lock:
        recent = list(events)
    return jsonify(
        {
            **latest,
            "score": score(),
            "samples": len(history),
            "mode": MODE,
            "impact": impact_summary(),
            "events": recent,
            "hypotheses": HYPOTHESES,
        }
    )


@app.get("/api/model/score")
def model_score():
    return jsonify({"score": score(), "samples": len(history)})


def valve_endpoint(command):
    if not authorized():
        if MODE != "insecure":
            log_event("warn", f"API vanne {command} refusée (403) depuis {request.remote_addr}")
        return jsonify({"error": "token requis"}), 403
    send_command(command)
    if MODE != "insecure":
        log_event("info", f"API vanne {command} acceptée depuis {request.remote_addr}")
    return jsonify({"status": "command sent", "command": command, "mode": MODE})


@app.post("/api/valve/open")
def open_valve():
    return valve_endpoint("OPEN")


@app.post("/api/valve/close")
def close_valve():
    return valve_endpoint("CLOSE")


@app.post("/api/reset")
def reset():
    """Commande de lab (hors scénario) : remet la serre dans son état initial."""
    history.clear()
    latest["humidity"] = None
    impact.update(liters=0.0, last_flow_ts=None, mismatch=False)
    with lock:
        events.clear()
    send_command("CLOSE")
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
