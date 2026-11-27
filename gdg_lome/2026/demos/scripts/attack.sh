#!/usr/bin/env bash
# Démarre l'attaquant (une seule fois) et s'y connecte.
# L'attaquant est un conteneur persistant (sleep infinity) : on lance ce script
# au début du talk, puis on tape les commandes dans le shell obtenu, sans préfixe docker.
#
# Usage :
#   bash scripts/attack.sh                        # ouvre un shell interactif dans l'attaquant
#   bash scripts/attack.sh python attack.py state # exécute une commande unique puis rend la main
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --profile attack up -d attacker >/dev/null
if [[ $# -eq 0 ]]; then
  exec docker compose exec attacker bash
else
  exec docker compose exec attacker "$@"
fi
