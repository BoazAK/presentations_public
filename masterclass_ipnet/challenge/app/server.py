#!/usr/bin/env python3
# Portail RH interne — cible volontairement vulnérable (Module 1 Red Team, démo).
# Chaîne en 4 maillons :
#   1. Recon / fuite d'info   : /robots.txt + /backup/notes.txt révèlent un compte + PIN 4 chiffres.
#   2. Login (politique faible): PIN à 4 chiffres, aucune limitation -> brute-force.
#   3. Cookie faible          : session = base64(json) NON signée -> on forge role=admin.
#   4. Injection de commande  : /admin/diag?host= passe l'entrée au shell -> cat /flag.
#
# NE PAS déployer hors d'un lab : toutes les failles sont intentionnelles.
import os, json, base64, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", "8080"))

# Comptes. alice = compte de test à PIN faible (4 chiffres). admin = PIN fort.
USERS = {
    "alice": {"pin": os.environ.get("ALICE_PIN", "4071"), "role": "user"},
    "admin": {"pin": os.environ.get("ADMIN_PIN", "home-run-7788-aegis"), "role": "admin"},
}

PAGE = """<!doctype html><html lang=fr><head><meta charset=utf-8>
<title>Portail RH — AgoRH</title><style>
body{font-family:system-ui,sans-serif;background:#0f1622;color:#e6edf5;max-width:640px;margin:3rem auto;padding:0 1rem}
a{color:#46c7f5} .card{background:#17202e;border:1px solid #273349;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0}
code{background:#0b1220;padding:.1rem .3rem;border-radius:4px}</style></head><body>
<h1>AgoRH — Portail RH interne</h1>
<p class=card>Espace réservé au personnel. Connexion : <a href=/login>/login</a></p>
<!-- TODO(ops): retirer /backup avant la mise en production - cf. memo RH -->
<footer><small>AgoRH Systems — interne</small></footer></body></html>"""

LOGIN = """<!doctype html><html lang=fr><head><meta charset=utf-8><title>Connexion — AgoRH</title>
<style>body{font-family:system-ui,sans-serif;background:#0f1622;color:#e6edf5;max-width:420px;margin:3rem auto}
input{display:block;width:100%;padding:.5rem;margin:.4rem 0;background:#0b1220;border:1px solid #273349;color:#e6edf5;border-radius:6px}
button{padding:.5rem 1rem;background:#46c7f5;border:0;border-radius:6px;font-weight:600}</style></head><body>
<h2>Connexion</h2><form method=POST action=/login>
<label>Identifiant</label><input name=user>
<label>Code PIN</label><input name=pin type=password>
<button>Se connecter</button></form></body></html>"""


def b64u_json(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


def read_cookie(headers):
    raw = headers.get("Cookie", "")
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            if k == "session":
                try:
                    return json.loads(base64.urlsafe_b64decode(v + "=" * (-len(v) % 4)))
                except Exception:
                    return None
    return None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="text/html; charset=utf-8", cookie=None):
        b = body if isinstance(body, (bytes, bytearray)) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            self.send(200, PAGE)
        elif u.path == "/login":
            self.send(200, LOGIN)
        elif u.path == "/robots.txt":
            # Volontairement discret : on ne révèle PAS /backup (il faudra le brute-forcer).
            self.send(200, "User-agent: *\nDisallow: /admin/\n", "text/plain")
        elif u.path == "/backup/notes.txt":
            # Maillon 1 : fuite d'info (compte de test + politique de PIN faible).
            self.send(200,
                      "MEMO RH — reinitialisation des acces\n"
                      "- Les PIN temporaires sont a 4 chiffres (0000-9999).\n"
                      "- Compte de test encore actif : alice\n"
                      "- Outil admin de diagnostic reseau : /admin/diag?host=<hote>\n"
                      "- TODO: renforcer la politique de mot de passe avant la prod.\n",
                      "text/plain")
        elif u.path == "/me":
            sess = read_cookie(self.headers)
            self.send(200, json.dumps(sess or {"error": "no session"}), "application/json")
        elif u.path == "/admin":
            sess = read_cookie(self.headers)
            if not sess or sess.get("role") != "admin":
                self.send(403, json.dumps({"error": "admin role required"}), "application/json")
                return
            self.send(200, "<h2>Diagnostic reseau</h2>"
                           "<p>Usage : <code>/admin/diag?host=192.168.1.1</code></p>")
        elif u.path == "/admin/diag":
            # Maillon 3 (gate) : exige role=admin dans le cookie (forgeable, maillon faible).
            sess = read_cookie(self.headers)
            if not sess or sess.get("role") != "admin":
                self.send(403, json.dumps({"error": "admin role required"}), "application/json")
                return
            host = q.get("host", [""])[0]
            if not host:
                self.send(400, json.dumps({"error": "host requis"}), "application/json")
                return
            # Maillon 4 : injection de commande (shell=True, entree non filtree).
            try:
                out = subprocess.run("ping -c 1 -W 1 " + host, shell=True,
                                     capture_output=True, text=True, timeout=8)
                body = (out.stdout or "") + (out.stderr or "")
            except Exception as e:
                body = "erreur: " + str(e)
            self.send(200, body, "text/plain")
        else:
            self.send(404, json.dumps({"error": "not found"}), "application/json")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/login":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode(errors="replace")
            form = parse_qs(body)
            user = form.get("user", [""])[0]
            pin = form.get("pin", [""])[0]
            rec = USERS.get(user)
            # Maillon 2 : aucune limitation de tentatives, PIN a 4 chiffres -> brute-force.
            if rec and pin == rec["pin"]:
                cookie = "session=%s; Path=/" % b64u_json({"user": user, "role": rec["role"]})
                self.send(200, json.dumps({"ok": True, "user": user, "role": rec["role"]}),
                          "application/json", cookie=cookie)
            else:
                self.send(401, json.dumps({"ok": False, "error": "identifiants invalides"}),
                          "application/json")
        else:
            self.send(404, json.dumps({"error": "not found"}), "application/json")


if __name__ == "__main__":
    print("AgoRH portail RH sur", PORT, flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
