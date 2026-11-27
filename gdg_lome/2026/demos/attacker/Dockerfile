# Attaquant de la demo : Kali Linux (conteneur jetable, lab local uniquement).
# Outils offensifs prets : nmap, mosquitto_pub/sub, curl, python3 (+ paho/requests).
# Conteneur persistant : lance une fois, on ouvre un shell dedans (docker compose exec).
FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nmap \
      libcap2-bin \
      mosquitto-clients \
      curl \
      ca-certificates \
      iproute2 \
      python3 \
      python3-paho-mqtt \
      python3-requests \
 && rm -rf /var/lib/apt/lists/* \
 && setcap -r /usr/lib/nmap/nmap 2>/dev/null || true
# nmap porte des capabilities fichier (cap_net_raw) qui bloquent son exec dans le
# conteneur ; on les retire : l'attaquant tourne en root, le scan fonctionne.

# attack.py reste disponible pour reference, mais la demo utilise des commandes brutes.
COPY attack.py .

# Reste vivant : on « exec » dedans. (compose override aussi avec sleep infinity.)
CMD ["sleep", "infinity"]
