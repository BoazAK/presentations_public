# GDG Lomé 2026 — Serre sous attaque

> **Pentest d'une ferme connectée, du capteur au cloud**
>
> Talk + démo live — GDG Lomé 2026

On attaque une serre connectée **simulée** (capteurs, broker MQTT, dashboard,
modèle de rendement, vanne d'irrigation), puis on reconstruit ses défenses. Tout
tourne dans Docker : **aucun capteur réel, aucun signal radio, aucune cible
externe**. Le lab reste sur `127.0.0.1` par défaut.

> ✅ **Validé** : les 4 actes ont été rejoués de bout en bout dans les 3 modes
> (attaque réussie en `insecure`, défense naïve contournée en `secure`, attaques
> bloquées en `hardened`, et la dérive lente comme limite du détecteur).

---

## 📋 Contenu du dossier

```
gdg_lome/2026/
├── demos/                      ← lab Docker complet
│   ├── mosquitto/                 ← 3 configs broker (insecure/secure/hardened) + ACL
│   ├── simulator/                 ← capteurs + contrôleur de vanne
│   ├── dashboard/                 ← tableau de bord, modèle, impact en FCFA, journal
│   ├── attacker/                  ← attack.py, nmap, mosquitto-clients
│   ├── scripts/                   ← setup.sh, mode.sh, demo.sh, teardown.sh
│   ├── compose.yaml
│   ├── .env.example
│   └── README.md                  ← guide complet du lab (install → nettoyage)
└── docs/
    └── guide_participant.md    ← atelier pas à pas (7 exercices + corrigé)
```

---

## 🚀 Installation

Prérequis : Docker + Docker Compose (v2).

```bash
cd gdg_lome/2026/demos
docker pull eclipse-mosquitto:2 python:3.12-slim
bash scripts/setup.sh            # .env, secrets, PKI locale, comptes MQTT, images
bash scripts/mode.sh insecure
```

Ouvrir <http://127.0.0.1:8080>.

## ▶️ Jouer la démo

```bash
bash scripts/demo.sh all         # 4 actes, pause entre chaque commande
```

| Acte | Mode | Ce qu'on montre |
|---|---|---|
| 1 | `insecure` | Reconnaissance, lecture de tout le bus MQTT anonyme |
| 2 | `insecure` | Fausse télémétrie, vanne ouverte par `curl`, impact en litres et FCFA |
| 3 | `secure` | La défense naïve contournée : token volé sur le bus et rejoué, faux état de vanne, empoisonnement plausible |
| 4 | `hardened` | TLS + ACL + commandes signées HMAC bloquent tout ; puis la dérive lente, limite du détecteur |

Changer de mode : `bash scripts/mode.sh insecure|secure|hardened`.
Atelier détaillé : [`docs/guide_participant.md`](docs/guide_participant.md).

## 🧹 Nettoyage

```bash
docker compose down              # conteneurs + réseau
bash scripts/teardown.sh         # + images et secrets locaux (PKI, mots de passe, .env)
```

Lancer `teardown.sh` après une démo sur une machine prêtée ou partagée : il efface
la CA, les clés privées et les mots de passe générés localement.

---

## ⚠️ Cadre

Lab strictement pédagogique et local. Ne jamais l'exposer sur Internet. Les
identifiants et tokens fournis sont des valeurs de démo publiques, à usage de lab
uniquement.

## 📧 Contact

**Boaz Kodjo BoazAK** — Application Security Specialist, DevSecOps & Penetration Tester

Twitter · TikTok · LinkedIn · Instagram · Facebook : `Boaz Kodjo BoazAK`
`#KodjoDoDjango` · `#InfoSecKodjo`
