#!/usr/bin/env bash
# Change le mode de la serre et redémarre le lab proprement.
# Usage : bash scripts/mode.sh insecure|secure|hardened
set -euo pipefail
cd "$(dirname "$0")/.."

MODE=${1:?usage: mode.sh insecure|secure|hardened}
case $MODE in insecure|secure|hardened) ;; *) echo "mode inconnu : $MODE" >&2; exit 1 ;; esac
[[ -f .env ]] || { echo "lancer d'abord : bash scripts/setup.sh" >&2; exit 1; }
if [[ $MODE == hardened && ! -s mosquitto/secrets/passwd ]]; then
  echo "PKI ou comptes absents : lancer bash scripts/setup.sh" >&2; exit 1
fi

sed -i.bak "s|^FARM_MODE=.*|FARM_MODE=${MODE}|" .env && rm -f .env.bak
# --force-recreate : vide aussi les messages retenus (faux états de vanne).
docker compose up -d --build --force-recreate --remove-orphans >/dev/null 2>&1
for _ in $(seq 1 20); do
  state=$(curl -s "http://127.0.0.1:8080/api/state" 2>/dev/null || true)
  [[ $state == *"\"humidity\":"[0-9]* ]] && break
  sleep 1
done
echo "$state" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("mode=%s vanne=%s humidité=%s score=%s" % (d["mode"], d["valve"], d["humidity"], d["score"]))'
