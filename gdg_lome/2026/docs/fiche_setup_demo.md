# Fiche de set-up et de démo — Serre sous attaque (GDG Lomé 2026)

Fiche du speaker, à garder sur un second écran ou imprimée. Talk de 30 minutes,
dont environ 14 minutes de démo. Toutes les commandes se lancent depuis
`gdg_lome/2026/demos` et ont été jouées de bout en bout sur le lab.

---

## 1. J-7 : préparation de la machine (avec Internet)

```bash
docker --version && docker compose version          # Compose v2 requis
cd gdg_lome/2026/demos
docker pull eclipse-mosquitto:2 python:3.12-slim
bash scripts/setup.sh                               # .env, secrets, PKI, comptes MQTT, images
bash scripts/mode.sh insecure                       # affiche : mode=insecure ... score=9x
NO_PAUSE=1 bash scripts/demo.sh all                 # répétition complète, environ 2 min
```

Puis enregistrer le Plan B (section 8).

## 2. J-1 : répétition hors ligne

1. Couper le Wi-Fi.
2. `bash scripts/mode.sh insecure` : le lab démarre et les images se reconstruisent depuis le cache.
3. `bash scripts/demo.sh all` avec les pauses, en chronométrant le talk complet.
4. `node ../build_deck.js` si les slides ont changé.

## 3. H-30 : sur place

```bash
cd gdg_lome/2026/demos
bash scripts/mode.sh insecure
```

- Wi-Fi coupé, notifications désactivées (macOS : Concentration).
- Terminal en police 20 pt minimum, thème clair, prompt court : `PS1='$ '`.
- Chargeur branché, veille désactivée : `caffeinate -d &`.

### Disposition de l'écran

| Zone | Contenu |
|---|---|
| Gauche (60 %) | Navigateur sur `http://127.0.0.1:8080`, zoom 125 % |
| Droite haut | Terminal **ATTAQUANT** |
| Droite bas | Terminal **FERME** : `docker compose logs -f --tail 0 simulator dashboard` |

### Raccourcis du terminal ATTAQUANT

```bash
cd gdg_lome/2026/demos
run()  { docker compose --progress quiet run --rm -T attacker python attack.py "$@"; }
atk()  { docker compose --progress quiet run --rm -T attacker "$@"; }
mode() { bash scripts/mode.sh "$1"; }
```

Alternative sans rien taper : `bash scripts/demo.sh acte1` (puis `acte2`, etc.),
avec une pause (Entrée) entre chaque commande.

---

## 4. Minutage du talk (30 min)

| Temps | Slides | Contenu |
|---|---|---|
| 0:00 | 1-5 | Ouverture, enjeux en FCFA, cible, surface d'attaque |
| 5:00 | 6-8 | Actes 1 et 2 (démo) |
| 10:00 | 8 | « Ce que voit l'exploitant », question au public |
| 11:00 | 9-13 | Défense naïve, puis acte 3 (démo) |
| 16:00 | 14-16 | Défense en profondeur : TLS, ACL, HMAC, détection |
| 20:00 | 17-18 | Acte 4 + la dérive lente (démo) |
| 26:00 | 19-21 | Mini-manuel, à retenir, merci |
| 27:00 | — | Questions |

## 5. Actes 1 et 2 : la ferme est ouverte (mode `insecure`)

| # | Commande | Résultat attendu |
|---|---|---|
| 1 | `atk nmap -sV -p 1883,8883,8080 mosquitto dashboard` | `1883 open mosquitto version 2.1.4`, `8080 open Werkzeug` |
| 2 | `atk mosquitto_sub -h mosquitto -t '#' -v -W 6` | défilement de `farm/sensor/*` et `farm/actuator/valve/state` |
| 3 | `run flood --value 0` | jauge humidité à 0 dans le navigateur |
| 4 | `run valve` | `HTTP 200`, vanne `OPEN`, débit 33 L/min |
| 5 | `run state` | `score=0`, impact d'environ 2 000 000 FCFA, compteur d'eau qui grimpe |

Phrase clé : « 4 octets et un `curl` sans token : la récolte entière est menacée. »

## 6. Acte 3 : la défense naïve contournée (mode `secure`)

```bash
mode secure                                        # mode=secure
run flood --value 0                                # journal : REJETÉE hors plage
run valve                                          # HTTP 403 → vote du public
run replay --simulate-operator --close-first       # token capturé, rejeu accepté
run spoof-state --state CLOSED                     # dashboard : CLOSED, débit : 33 L/min
run flood --value 25 --count 30                    # plausible, passe le filtre
run state
```

Résultat vérifié : `mode=secure vanne=CLOSED débit=33.7 L/min score=21 impact≈1 558 000 FCFA`.
Le journal ne montre que les rejets bruyants, rien sur le rejeu ni sur le faux état.
Montrer au terminal FERME : `valve -> OPEN` juste après la fermeture par l'opérateur.

## 7. Acte 4 : défense en profondeur (mode `hardened`)

```bash
mode hardened                                      # mode=hardened
run anon                                           # 1883 refusé · 8883 Not authorized
run sniff --as viewer --seconds 4 --limit 6        # seuls farm/sensor/* reçus
run flood --as viewer --count 2                    # broker : REFUSÉ (Not authorized)
run spoof-state --as sensor-02                     # broker : REFUSÉ (Not authorized)
run replay --as maintenance --simulate-operator --close-first
run forge --as maintenance
run state                                          # journal : rejeu détecté, HMAC invalide
run flood --as sensor-02 --value 25 --count 10     # REJETÉE : saut anormal
run drift --as sensor-02                           # la limite : passe sous le seuil
run state                                          # score=25, le vrai capteur est rejeté
```

Phrases clés :
- replay : « Il a capturé une commande signée valide. Elle ne vaut plus rien 1 seconde après. »
- drift : « Le détecteur rejette maintenant le capteur honnête. La sécurité OT est une course. »

## 8. Plan B (Docker en panne, projecteur capricieux)

- Enregistrer les 4 actes en vidéo la veille (`Cmd+Shift+5`), 1080p, sans son,
  avec une copie sur clé USB.
- Captures du dashboard : normal, vanne OPEN + FCFA, acte 3 (CLOSED + débit 33),
  acte 4 (journal HMAC).
- Conteneur planté : `docker compose restart <service>` ; tout planté : `mode <mode>` (15 s).

## 9. Remise à zéro et suppression

```bash
mode insecure                      # entre deux répétitions : recrée tout
docker compose down                # après le talk : conteneurs + réseau
bash scripts/teardown.sh           # machine prêtée/partagée : efface aussi PKI, mots de passe, .env
bash scripts/teardown.sh --purge   # + images de base
```

Les secrets (CA, clés privées, `passwd`) restent sur le disque tant que
`teardown.sh` n'est pas lancé. Sur ta propre machine, `docker compose down` suffit.

## 10. Check-list finale

- [ ] `mode insecure` affiche `mode=insecure` et un score proche de 100
- [ ] Raccourcis `run`, `atk` et `mode` définis dans le terminal ATTAQUANT
- [ ] Terminal FERME ouvert sur les logs
- [ ] Navigateur sur `127.0.0.1:8080`, zoom 125 %
- [ ] Wi-Fi coupé, notifications désactivées, `caffeinate` lancé
- [ ] Vidéo du Plan B sur le bureau et sur la clé USB
