# Lab — Serre sous attaque (100 % Docker)

Ferme simulée pour le talk GDG Lomé 2026. Aucun capteur réel, aucun signal radio,
aucune cible externe. Le lab reste sur `127.0.0.1` par défaut.

## Architecture

```
  simulator ──capteurs──▶ mosquitto ──▶ dashboard (Flask, modèle, impact FCFA)
  (humidité, température,     ▲                │ POST /api/valve/{open,close}
   débit, vanne)              │                ▼
       ▲                      └──── commande MQTT (token ou HMAC) ────┘
       └───────────────── attacker (profil « attack »)
```

| Service | Rôle | Port hôte |
|---|---|---|
| `mosquitto` | Broker MQTT (config selon le mode) | `1883` (clair), `8883` (TLS) |
| `simulator` | Capteurs + contrôleur de vanne | — |
| `dashboard` | Tableau de bord, modèle de rendement, journal, impact | `8080` |
| `attacker` | `attack.py`, `nmap`, `mosquitto_pub/sub` (`profiles: [attack]`) | — |

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
docker pull eclipse-mosquitto:2 python:3.12-slim
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

## Déroulé scripté

```bash
bash scripts/demo.sh all          # ou acte1 | acte2 | acte3 | acte4
NO_PAUSE=1 bash scripts/demo.sh all   # sans pause (répétition rapide, ~2 min)
```

Le script démarre l'attaquant une fois (`docker compose exec`) et réutilise ce même
conteneur persistant pour toutes les étapes, au lieu d'en recréer un par commande.

## Commandes d'attaque

L'attaquant est un **conteneur persistant** : on le démarre **une fois**, puis on s'y
connecte et on tape les commandes dedans, sans préfixe `docker` à chaque étape.

```bash
bash scripts/attack.sh            # démarre l'attaquant (si besoin) et ouvre un shell dedans
# équivaut à :
docker compose --profile attack up -d attacker
docker compose exec attacker bash
```

Dans ce shell (outils déjà présents : `attack.py`, `nmap`, `mosquitto_pub`/`mosquitto_sub`),
les commandes du tableau ci-dessous se tapent **nues** : `python attack.py <cmd>` pour les
sous-commandes `attack.py`, et directement `nmap …` / `mosquitto_sub …` pour les autres.
L'attaquant reste vivant quand on change de mode. Pour une commande unique sans ouvrir de
shell : `bash scripts/attack.sh python attack.py state`.

| Commande | Effet |
|---|---|
| `python attack.py recon` | ports 1883, 8883, 8080 |
| `nmap -sV -p 1883,8883,8080 mosquitto dashboard` | versions des services |
| `python attack.py anon` | tentatives anonymes en clair et en TLS |
| `python attack.py sniff [--topic T] [--as U]` | écoute du bus |
| `python attack.py flood --value V [--count N] [--as U]` | fausses mesures d'humidité |
| `python attack.py drift [--as U]` | dérive lente sous le seuil du détecteur |
| `python attack.py valve [--secure] [--close]` | API vanne, sans ou avec le token opérateur |
| `python attack.py replay [--simulate-operator] [--close-first] [--as U]` | capture puis rejeu d'une commande |
| `python attack.py forge [--as U]` | commande forgée sans clé HMAC |
| `python attack.py spoof-state [--state CLOSED] [--as U]` | faux état de vanne retenu |
| `python attack.py state` / `python attack.py score` | état, impact et journal / score du modèle |
| `python attack.py reset` | remise à zéro (commande de lab, hors scénario) |

`--as viewer|maintenance|sensor-02` utilise des identifiants « fuités » à faibles droits
(TLS 8883). `--tls` tente une connexion TLS anonyme.

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
bash scripts/teardown.sh --purge # idem + images de base (mosquitto, python)
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
