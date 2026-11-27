# GDG Lome 2026 — Serre sous attaque

Talk de 30 minutes + démo live, en français, pour la communauté GDG (développeurs).

## Thème

**Serre sous attaque : pentest d'une ferme connectée, du capteur au cloud**

## Description

Une ferme connectée empile des capteurs, des automates, un broker MQTT et des modèles
d'IA qui décident à notre place de l'irrigation, du climat et des rendements. Cette
surface d'attaque est encore très peu auditée, et une simple télémétrie falsifiée peut
se transformer en perte physique réelle.

Pendant ce talk, nous attaquons une serre **simulée** (100 % Docker, zéro matériel) :
découverte du réseau, lecture d'un broker MQTT anonyme, injection de mesures
trompeuses, détournement d'une vanne d'irrigation, puis empoisonnement du modèle de
rendement. Nous reconstruisons ensuite les défenses : segmentation, authentification
MQTT, validation des données, contrôle des actionneurs et détection d'anomalies.

Tout est local, reproducible et sans danger : aucune cible réelle, aucun matériel,
aucune émission radio.

## Speaker

**Boaz Kodjo BoazAK** — nom conservé sans changement.

Application Security Specialist, DevSecOps and Penetration Tester |
Mandela Washington Fellowship Alumnus

Réseaux (même identifiant sur tous) : Twitter, TikTok, LinkedIn, Instagram, Facebook —
`Boaz Kodjo BoazAK`

Hashtags : `#KodjoDoDjango` `#InfoSecKodjo`

## Contenu du dossier

```
gdg_lome/2026/
├── README.md              ← ce fichier
├── abstract.md            ← résumé CFP + bio + réseaux
├── slides.md              ← source Marp (slides en français)
├── build_deck.js          ← génère « Presentation 2026.pptx » depuis le même contenu
├── Presentation 2026.pptx ← deck PowerPoint généré
├── demos/                 ← lab Docker complet + script de démo
│   ├── README.md
│   ├── compose.yaml
│   ├── .env.example
│   ├── mosquitto/         ← insecure/secure/hardened.conf + acl
│   ├── simulator/
│   ├── dashboard/
│   ├── attacker/
│   └── scripts/           ← setup.sh, mode.sh, demo.sh
└── docs/
    ├── fiche_setup_demo.md ← fiche speaker : set-up, minutage, commandes
    └── guide_participant.md
```

## Démarrage rapide

```bash
cd demos
bash scripts/setup.sh            # .env, secrets, PKI, comptes MQTT, images
bash scripts/mode.sh insecure
bash scripts/demo.sh all         # 4 actes, pause entre chaque commande
```

Ouvrir `http://127.0.0.1:8080`. Fiche speaker : `docs/fiche_setup_demo.md`.

## Les 4 actes

1. **Ferme ouverte** (`insecure`) : nmap, écoute du bus MQTT.
2. **Mentir et agir** : fausse humidité, vanne ouverte par `curl`, impact en FCFA.
3. **Défense naïve contournée** (`secure`) : token volé sur le bus puis rejoué,
   faux état `CLOSED` retenu, empoisonnement plausible.
4. **Défense en profondeur** (`hardened`) : TLS, comptes, ACL, commandes HMAC
   avec nonce, détection de saut et de cohérence ; puis la dérive lente comme limite.

## Répétition (check-list)

- [ ] `bash scripts/setup.sh` sans erreur
- [ ] `NO_PAUSE=1 bash scripts/demo.sh all` : actes 1 à 4 conformes à la fiche
- [ ] `node build_deck.js` régénère le PPTX, slides Marp relues
- [ ] Vidéo et captures du Plan B prêtes (cf. `docs/fiche_setup_demo.md`)

## Corrections appliquées au profil

- `Pentration Tester` → `Penetration Tester`
- `Alumni Mandela Washington Fellowship` → `Mandela Washington Fellowship Alumnus`
- Accents français ajoutés dans les intitulés (`présentation`, `démo`, `réseaux`).
