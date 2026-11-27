#!/usr/bin/env bash
# Prépare l'environnement de démo : cible (AgoRH) + machine d'attaque, sur un réseau dédié.
# Idempotent : relançable pour repartir d'un état propre.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CHALL_DIR="$(cd "$HERE/../challenge" && pwd)"
STACK=rtm1-demo
NET="$STACK-net"
ATTACKER="$STACK-attacker"

echo "[*] Déploiement de la cible (AgoRH)…"
( cd "$CHALL_DIR" && docker compose up -d --build )   # compose lit .env s'il existe, sinon ses défauts

echo "[*] (Re)création de la machine d'attaque…"
docker rm -f "$ATTACKER" >/dev/null 2>&1 || true
docker run -d --name "$ATTACKER" --network "$NET" --ip 172.30.40.50 \
  python:3.12-slim sleep infinity >/dev/null
docker exec "$ATTACKER" sh -c \
  'apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq curl jq >/dev/null 2>&1'

echo
echo "[+] Prêt."
echo "    Cible     : 172.30.40.10:8080   (hôte: http://localhost:30300)"
echo "    Attaquant : docker exec -it $ATTACKER bash"
echo "    Astuce    : depuis l'attaquant,  T=http://172.30.40.10:8080"
