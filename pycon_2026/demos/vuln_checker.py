"""
Démo 2 : Détection automatisée de vulnérabilités Web
PyCon Togo 2026

Vérifie la présence des headers de sécurité essentiels sur un site donné.
"""

import requests
import sys
from urllib.parse import urlparse


SECURITY_HEADERS = {
    "X-Frame-Options": {
        "risque": "Clickjacking",
        "remediation": "DENY ou SAMEORIGIN",
    },
    "Content-Security-Policy": {
        "risque": "XSS / Injection de contenu",
        "remediation": "Définir une politique CSP stricte",
    },
    "Strict-Transport-Security": {
        "risque": "Man-in-the-Middle (MITM)",
        "remediation": "max-age=31536000; includeSubDomains",
    },
    "X-Content-Type-Options": {
        "risque": "MIME sniffing",
        "remediation": "nosniff",
    },
    "X-Permitted-Cross-Domain-Policies": {
        "risque": "Cross-domain data leakage",
        "remediation": "none",
    },
    "Referrer-Policy": {
        "risque": "Fuites d'informations via Referer",
        "remediation": "strict-origin-when-cross-origin",
    },
    "Permissions-Policy": {
        "risque": "Accès aux API navigateur non contrôlé",
        "remediation": "Restreindre les permissions inutiles",
    },
}

DANGEROUS_HEADERS = {
    "Server": "Divulgue la version du serveur web",
    "X-Powered-By": "Divulgue la stack technique",
    "X-AspNet-Version": "Divulgue la version ASP.NET",
}


def check_url(target_url: str) -> dict:
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    print(f"\n{'='*60}")
    print(f"🔍 Analyse de sécurité : {target_url}")
    print(f"{'='*60}\n")

    try:
        resp = requests.get(target_url, timeout=10, allow_redirects=True)
    except requests.exceptions.RequestException as e:
        print(f"[✗] Erreur de connexion : {e}")
        return {}

    print(f"[i] Code HTTP : {resp.status_code}")
    print(f"[i] URL finale : {resp.url}\n")

    missing = 0
    present = 0

    print("─" * 60)
    print("HEADERS DE SÉCURITÉ")
    print("─" * 60)

    for header, info in SECURITY_HEADERS.items():
        if header in resp.headers:
            print(f"[✓] {header}")
            print(f"    Valeur : {resp.headers[header]}")
            present += 1
        else:
            print(f"[✗] {header} — ABSENT")
            print(f"    ⚠️  Risque : {info['risque']}")
            print(f"    💡 Correction : {info['remediation']}")
            missing += 1

    print("\n" + "─" * 60)
    print("HEADERS POTENTIELLEMENT DANGEREUX")
    print("─" * 60)

    for header, risque in DANGEROUS_HEADERS.items():
        if header in resp.headers:
            print(f"[!] {header} : {resp.headers[header]}")
            print(f"    ⚠️  {risque}")

    print(f"\n{'='*60}")
    print(f"RÉSUMÉ : {present} headers présents, {missing} absents")
    print(f"{'='*60}")

    return {
        "url": target_url,
        "status_code": resp.status_code,
        "headers_present": present,
        "headers_missing": missing,
    }


def main():
    url = "https://example.com"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    check_url(url)


if __name__ == "__main__":
    main()
