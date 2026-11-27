#!/bin/sh
set -e
# PIN faible aléatoire pour alice (4 chiffres), PIN fort pour admin, flag unique.
export ALICE_PIN="$(python3 -c 'import secrets;print("%04d"%secrets.randbelow(10000))')"
export ADMIN_PIN="$(python3 -c 'import secrets;print(secrets.token_hex(12))')"
FLAG="${FLAG:-NCTF{agorh_$(python3 -c 'import secrets;print(secrets.token_hex(5))')}}"
printf '%s\n' "$FLAG" > /flag
chmod 644 /flag
echo "[+] AgoRH prêt (alice PIN tiré au hasard, flag écrit dans /flag)"
exec python3 /app/server.py
