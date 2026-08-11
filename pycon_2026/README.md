# PyCon Togo 2026 — Workshop

> **Exploring and Innovating with Python: Security, Open Source, and Emerging Technologies**
>
> Workshop technique interactif — 50 minutes — Live Coding

---

## 📋 Contenu du dossier

```
pycon_2026/
├── demos/                     ← Scripts Python des 10 démos live
│   ├── port_scanner.py        ← Scanner de ports asynchrone (asyncio)
│   ├── vuln_checker.py        ← Détection automatisée de vulnérabilités Web
│   ├── malware_hash.py        ← Analyse de malware par hash (VirusTotal)
│   ├── sast_analyzer.py       ← SAST — Analyse statique avec AST (*custom tool*)
│   ├── supply_chain_audit.py  ← Audit de dépendances (PyPI/supply chain)
│   ├── log_analyzer.py        ← Analyse de logs SSH (auth.log)
│   ├── visualize_logs.py      ← Visualisation des attaques (matplotlib)
│   ├── phishing_detector.py   ← Détection de phishing par ML (scikit-learn)
│   ├── cve_nlp.py             ← Analyse NLP des CVE (HuggingFace)
│   └── report_generator.py    ← Génération de rapport automatique (Jinja2)
├── data/                      ← Données factices pour les démos
│   ├── auth.log               ← Logs SSH simulés (~90 entrées)
│   └── urls.csv               ← Dataset URLs légitimes vs phishing (60 URLs)
├── requirements.txt           ← Dépendances Python
└── README.md                  ← Ce fichier
```

---

## 🚀 Démarrage rapide

### Option 1 : Environnement local

```bash
cd pycon_2026
python demos/port_scanner.py
```

### Option 2 : Installation manuelle

```bash
git clone https://github.com/BoazAK/presentations_public.git
cd presentations_public/pycon_2026
pip install -r requirements.txt
python demos/port_scanner.py
```

---

## 📚 Ressources recommandées

| Type | Référence |
|------|-----------|
| Livre | *Black Hat Python* (2e éd.) — Justin Seitz |
| Livre | *Violent Python* — TJ O'Connor |
| Livre | *Python for Data Analysis* — Wes McKinney |
| Lab | TryHackMe, HackTheBox, Root-Me |
| Lab | PortSwigger Web Security Academy |
| Outil | OWASP ZAP, mitmproxy, sqlmap |
| Communauté | Python Togo, PyCon Africa, OWASP |

---

## 📧 Contact

- GitHub : [BoazAK](https://github.com/BoazAK)
- Twitter/X : [@BoazakK](https://twitter.com/BoazakK)
- LinkedIn : [boazak](https://www.linkedin.com/in/boazak)
