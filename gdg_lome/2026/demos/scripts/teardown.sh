#!/usr/bin/env bash
# Supprime toute trace du lab après la démo.
#   bash scripts/teardown.sh          conteneurs + réseau + images + secrets locaux
#   bash scripts/teardown.sh --keep-secrets   garde .env, PKI et mots de passe
#   bash scripts/teardown.sh --purge  idem, + supprime aussi les images de base
# Les secrets (CA, clés privées, passwd) sont effacés par défaut : important sur
# une machine prêtée ou partagée.
set -euo pipefail
cd "$(dirname "$0")/.."

STACK=$(grep -E '^STACK_NAME=' .env 2>/dev/null | cut -d= -f2)
STACK=${STACK:-gdg-farm-dev}

echo "== Conteneurs, réseau et images du lab ($STACK-*)"
docker compose --profile attack down --rmi local --remove-orphans 2>/dev/null || true

if [[ ${1:-} != --keep-secrets ]]; then
  echo "== Secrets locaux (PKI, mots de passe, .env)"
  rm -rf mosquitto/tls mosquitto/secrets
  rm -f .env mosquitto/secrets/passwd
  echo "  supprimés : mosquitto/tls/, mosquitto/secrets/, .env"
else
  echo "== Secrets conservés (--keep-secrets)"
fi

if [[ ${1:-} == --purge ]]; then
  echo "== Images de base"
  docker rmi eclipse-mosquitto:2 kalilinux/kali-rolling 2>/dev/null || true
fi

echo "Terminé. Vérifier : docker ps -a | grep $STACK  (doit être vide)"
