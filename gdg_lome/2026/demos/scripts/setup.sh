#!/usr/bin/env bash
# Prépare le lab : .env, secrets, PKI de démo (CA + certificat broker),
# fichier de mots de passe Mosquitto, images Docker. Idempotent.
# Usage : bash scripts/setup.sh [--force]   (--force régénère PKI et mots de passe)
set -euo pipefail
cd "$(dirname "$0")/.."

FORCE=${1:-}
[[ -f .env ]] || cp .env.example .env

# Remplit une variable vide de .env avec un secret aléatoire.
fill_secret() {
  local key=$1 value
  if grep -qE "^${key}=$" .env || [[ $FORCE == --force ]]; then
    value=$(openssl rand -hex 24)
    sed -i.bak "s|^${key}=.*|${key}=${value}|" .env && rm -f .env.bak
    echo "  secret généré : ${key}"
  fi
}
echo "== Secrets"
fill_secret CMD_HMAC_KEY
fill_secret MQTT_PASS_SIMULATOR
fill_secret MQTT_PASS_DASHBOARD
set -a; source .env; set +a

echo "== PKI de démo (CA locale, 365 jours)"
mkdir -p mosquitto/tls/ca mosquitto/tls/server mosquitto/tls/public mosquitto/secrets
if [[ ! -f mosquitto/tls/server/server.crt || $FORCE == --force ]]; then
  tmp=$(mktemp -d)
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 -sha256 \
    -subj "/CN=GDG Lome Farm Lab CA" \
    -keyout mosquitto/tls/ca/ca.key -out mosquitto/tls/ca/ca.crt 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -sha256 -subj "/CN=mosquitto" \
    -keyout mosquitto/tls/server/server.key -out "$tmp/server.csr" 2>/dev/null
  printf "subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n" > "$tmp/ext.cnf"
  openssl x509 -req -in "$tmp/server.csr" -days 365 -sha256 \
    -CA mosquitto/tls/ca/ca.crt -CAkey mosquitto/tls/ca/ca.key -CAcreateserial \
    -extfile "$tmp/ext.cnf" -out mosquitto/tls/server/server.crt 2>/dev/null
  cp mosquitto/tls/ca/ca.crt mosquitto/tls/server/ca.crt
  cp mosquitto/tls/ca/ca.crt mosquitto/tls/public/ca.crt
  # Lisible par l'utilisateur mosquitto du conteneur (lab uniquement).
  chmod 644 mosquitto/tls/server/server.key
  rm -rf "$tmp" mosquitto/tls/ca/ca.srl
  echo "  CA et certificat broker (SAN mosquitto, localhost, 127.0.0.1) générés"
else
  echo "  déjà présente (--force pour régénérer)"
fi

echo "== Comptes MQTT du mode hardened"
docker run --rm -v "$PWD/mosquitto/secrets:/work" eclipse-mosquitto:2 sh -c "
  rm -f /work/passwd && touch /work/passwd &&
  mosquitto_passwd -b /work/passwd simulator   '$MQTT_PASS_SIMULATOR' &&
  mosquitto_passwd -b /work/passwd dashboard   '$MQTT_PASS_DASHBOARD' &&
  mosquitto_passwd -b /work/passwd viewer      '$LEAK_VIEWER_PASS' &&
  mosquitto_passwd -b /work/passwd maintenance '$LEAK_MAINTENANCE_PASS' &&
  mosquitto_passwd -b /work/passwd sensor-02   '$LEAK_SENSOR02_PASS' &&
  chmod 644 /work/passwd" 2>/dev/null
echo "  5 comptes : simulator, dashboard, viewer, maintenance, sensor-02"

echo "== Images Docker"
docker compose --profile attack build --quiet
echo "Prêt. Démarrer : bash scripts/mode.sh insecure"
