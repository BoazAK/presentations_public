#!/usr/bin/env bash
# Arrête et nettoie l'environnement de démo (conteneurs, image, réseau).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CHALL_DIR="$(cd "$HERE/../challenge" && pwd)"
STACK=rtm1-demo

docker rm -f "$STACK-attacker" >/dev/null 2>&1 || true
( cd "$CHALL_DIR" && docker compose down --rmi local --remove-orphans ) || true
echo "[+] Environnement démonté."
