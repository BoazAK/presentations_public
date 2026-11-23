# Guide participant — Serre sous attaque

Atelier de 2 à 3 heures, en français. Objectif : rejouer l'attaque, puis la bloquer.

## Avant de commencer

- Docker + Docker Compose installés.
- Un navigateur pour ouvrir <http://127.0.0.1:8080>.
- Pas besoin de savoir cultiver : une humidité « normale » est autour de 65 %.

## Installation

```bash
cd gdg_lome/2026/demos
bash scripts/setup.sh
bash scripts/mode.sh insecure
run() { docker compose --progress quiet run --rm -T attacker python attack.py "$@"; }
```

Vérifier que la page affiche une humidité entre 62 et 68 % et un score proche de 100 %.

## Exercice 1 — Écouter la ferme

```bash
run sniff --seconds 8
```

Questions :
1. Quels topics voyez-vous ?
2. Un inconnu sur le réseau peut-il lire ces données ? Pourquoi ?

## Exercice 2 — Mentir au capteur

```bash
run flood --value 0
curl http://127.0.0.1:8080/api/model/score
```

Questions :
1. Que s'est-il passé sur le score ?
2. Le dashboard vérifiait-il la valeur avant de la stocker ?

## Exercice 3 — Ouvrir la vanne

```bash
curl -X POST http://127.0.0.1:8080/api/valve/open
```

Questions :
1. Quelle est la différence entre « lire une donnée » et « agir sur le monde » ?
2. Quel contrôle manquait sur cet endpoint ?

## Exercice 4 — Passer en défense naïve

```bash
bash scripts/mode.sh secure
run flood --value 0
run valve
run valve --secure
```

Questions :
1. Pourquoi la première requête `valve` échoue-t-elle ?
2. Pourquoi la deuxième réussit-elle ?

## Exercice 5 — Contourner la défense naïve

```bash
run replay --simulate-operator --close-first
run spoof-state --state CLOSED
run flood --value 25 --count 30
run state
```

Questions :
1. Où le token circule-t-il en clair ?
2. Pourquoi le dashboard affiche-t-il `CLOSED` alors que le débitmètre indique 33 L/min ?
3. Pourquoi la valeur 25 passe-t-elle le filtre ?

## Exercice 6 — Défense en profondeur

```bash
bash scripts/mode.sh hardened
run anon
run sniff --as viewer
run spoof-state --as sensor-02
run replay --as maintenance --simulate-operator --close-first
run forge --as maintenance
run state
```

Lire `mosquitto/hardened.conf`, `mosquitto/acl` et la fonction `verify` de
`simulator/simulator.py`.

Questions :
1. Quel contrôle bloque chaque commande ?
2. Le compte `maintenance` peut publier sur la vanne : pourquoi son rejeu échoue-t-il ?

## Exercice 7 (bonus) — Battre le détecteur

```bash
run flood --as sensor-02 --value 25 --count 10
run drift --as sensor-02
run state
```

Questions :
1. Pourquoi `flood` est détecté et pas `drift` ?
2. Pourquoi le vrai capteur est-il rejeté à la fin ?
3. Proposez un contrôle qui aurait détecté la dérive (indice : le débitmètre, un
   second capteur, un modèle physique).

## Corrigé express

| Exercice | Point clé |
|---|---|
| 1 | Le topic `farm/#` donne une vue complète de la serre |
| 2 | Aucune validation de plage : 0 est accepté comme 65 |
| 3 | Endpoint d'action sans authentification ni journal |
| 4 | Validation des valeurs + token sur l'API |
| 5 | Le bus reste ouvert : token en clair rejouable, état falsifiable, valeur plausible |
| 6 | TLS + identité + ACL au broker, HMAC + nonce + horodatage sur la commande |
| 7 | Un seuil se contourne lentement : croiser des sources indépendantes |

## Nettoyage

```bash
cd demos && docker compose down
```

## Speaker

**Boaz Kodjo BoazAK** — Application Security Specialist, DevSecOps and Penetration
Tester | Mandela Washington Fellowship Alumnus

Twitter · TikTok · LinkedIn · Instagram · Facebook : `Boaz Kodjo BoazAK`

`#KodjoDoDjango` `#InfoSecKodjo`
