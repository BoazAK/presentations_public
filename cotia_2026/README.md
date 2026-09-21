# IndabaX Togo 2026 — Talk

> **Sécuriser les LLM : le pentest des applications basées sur l'IA**
>
> Talk 30 min — 24 au 26 septembre 2026 — Unipod, Université de Lomé
>
> Thème de la conférence : « Écosystème IA : Recherche, Innovation et Coopération »

Méthodologie : prompt injection, fuite du system prompt, jailbreak, excessive agency — 5 phases (OWASP Top 10 LLM) — scripts d'entraînement **100 % locaux** (Ollama, modèle `llama3.1`), aucune cible externe.

> ✅ **Validé** : les 4 scripts ont été testés de bout en bout (injection détectée, fuite du prompt 4/6 probes, 2 bypass jailbreak sur 5, agent exécute 3/3 sans validation).

---

## 📋 Contenu du dossier

```
cotia_2026/
├── demos/                      ← 4 scripts de pentest LLM, 100 % locaux (Ollama)
│   ├── prompt_injection.py        ← Injection indirecte via un document
│   ├── extract_system_prompt.py   ← Fuite du system prompt (6 probes)
│   ├── jailbreak.py               ← Contournement des garde-fous (5 techniques)
│   └── excessive_agency.py        ← Abus des permissions d'un agent
├── requirements.txt           ← Dépendances Python (ollama)
└── README.md                  ← Ce fichier (guide complet, install → nettoyage)
```

---

## 🚀 Installation

### 1. Uniquement si absent : Python 3.10+

`python3 --version` — sinon installer depuis https://python.org.

### 2. Installer Ollama

**macOS / Linux :**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

macOS via Homebrew : `brew install ollama`. **Windows** : installeur sur https://ollama.com/download.

### 3. Lancer le serveur et vérifier

```bash
ollama --version      # doit afficher un numéro de version
ollama serve          # démarre le serveur (normalement auto après install)
```

Dans un second terminal : `curl http://localhost:11434/api/tags` → doit répondre `{"models":[...]}`.

> Lien : `http://localhost:11434` — c'est l'API utilisée par les scripts.

### 4. Télécharger le modèle local

```bash
ollama pull llama3.1
```

> `llama3.1` (≈ 4,7 Go) suffit pour toutes les démos. Plus léger : `ollama pull llama3.2` ou `mistral`.

### 5. Créer l'environnement virtuel Python

```bash
cd cotia_2026

python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux — Windows : .venv\Scripts\activate
python3 -m pip install -r requirements.txt
```

> **À chaque session de travail/répétition** : réactiver le venv (`source .venv/bin/activate`) avant de lancer les démos (prompt préfixé par `(.venv)`).

---

## 🎬 Lancer les démos

Le venv doit être activé :

```bash
python3 demos/prompt_injection.py      # 1. injection indirecte (document malveillant)
python3 demos/extract_system_prompt.py # 2. fuite du system prompt
python3 demos/jailbreak.py             # 3. contournement des garde-fous
python3 demos/excessive_agency.py      # 4. abus des permissions d'un agent
```

Sortir du venv quand on a fini : `deactivate`

### Résultats attendus (modèle `llama3.1`)

| Script | Verdict |
|--------|---------|
| `prompt_injection.py` | Doc innocent → résumé fidèle · Doc malveillant → **résumé détourné ⚠️** |
| `extract_system_prompt.py` | **4 probes sur 6** révèlent le prompt + le secret DB ⚠️ |
| `jailbreak.py` | directe/DAN/hypothétique/completion **REFUSÉ** · phrasebook/tableau **BYPASS ⚠️** |
| `excessive_agency.py` | 3 requêtes exécutées **sans validation humaine ⚠️** |

> Les sorties varient légèrement selon la version du modèle. C'est un résultat en soi : certaines techniques passent, d'autres non.

### 🛡️ Framework éthique

- 100 % local (Ollama), aucune cible externe, aucune donnée réelle de l'Université de Lomé.
- Les exfils et actions sensibles sont simulées et masquées à l'écran.
- Plan B hors-ligne : chaque script affiche aussi la sortie attendue en commentaires.

---

## 🧪 Dépannage

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError: No module named 'ollama'` | Venv pas activé → `source .venv/bin/activate` puis `pip install -r requirements.txt` |
| `"ollama" has no attribute (...)` / erreur d'import strange | Réinstaller dans le venv : `pip install --upgrade ollama` |
| `ConnectionError: ... localhost:11434` | Ollama n'est pas lancé → `ollama serve` |
| `model 'llama3.1' not found` | `ollama pull llama3.1` |
| Le modèle répond lentement | Premier téléchargement + CPU → patienter, ou `ollama pull mistral` (plus léger et rapide) |
| `command not found: ollama` | Ouvrir un nouveau terminal ou `export PATH=$PATH:/usr/local/bin` |
| Pas d'accès à internet le jour J | Prépull le modèle **avant** la conférence, ajouter `OLLAMA_MODELS` si besoin |

---

## 🧹 Tout supprimer après la démo

Nettoyage complet de la machine après la conférence (venv + modèles + Ollama). À exécuter dans l'ordre.

```bash
deactivate                          # sortir du venv (si activé)
rm -rf .venv                        # supprimer le venv (dépendances + paquet ollama)
ollama list                         # voir les modèles présents
ollama rm llama3.1                  # supprimer le modèle du talk
ollama rm llama3.2 mistral          # supprimer aussi les modèles de secours éventuels
rm -rf ~/.ollama                    # ⚠️ irréversible : TOUS les modèles + config
```

**Désinstallation d'Ollama** : macOS/Linux (install.sh) `rm /usr/local/bin/ollama` (supra `rm -rf ~/.ollama` déjà fait) · macOS (Homebrew) `brew uninstall ollama && brew cleanup ollama` · Windows via *Paramètres → Applications*, puis supprimer `%USERPROFILE%\.ollama`.

**Vérifier que tout est bien parti :**

```bash
which ollama        # ne doit plus rien afficher
ollama list         # command not found (ou pas de modèles)
ls cotia_2026/.venv # ne doit plus exister
```

> Les fichiers du talk (scripts, captures) sont conservés — c'est le repo 👍.

---

## ✅ Checklist jour J

- [ ] `source .venv/bin/activate` (prompt `(.venv)`)
- [ ] `ollama serve` lancé
- [ ] `ollama list` → `llama3.1` présent
- [ ] `python3 demos/prompt_injection.py` testé une fois dans le venv
- [ ] Modèle préchargé (5 min d'échauffement avant le talk pour accélérer la 1re réponse)
- [ ] Projecteur testé, fonts monospace installées si besoin

---

## 📚 Ressources recommandées

| Type | Référence |
|------|-----------|
| Standard | OWASP Top 10 for LLM Applications |
| Lab | PortSwigger LLM AI Security Academy |
| Lab | prompt-injection.org (attacks & mitigations) |
| Outil | Ollama, Giskard, Lakera Guard |
| Communauté | IndabaX Togo, Neuractif |

---

## 📧 Contact

- Twitter/X : [@BoazakK](https://twitter.com/BoazakK)
- LinkedIn : [boazak](https://www.linkedin.com/in/boazak)
