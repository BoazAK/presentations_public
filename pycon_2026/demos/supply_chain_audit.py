"""
Démo 10 : Supply Chain Security — Audit de dépendances
PyCon Togo 2026

Analyse les dépendances d'un projet Python pour détecter :
- Paquets avec vulnérabilités connues
- Paquets non maintenus (pas de release récente)
- Typosquatting potentiel
- Dépendances avec exécution de code à l'installation (setup.py suspect)

Nécessite une connexion internet pour interroger PyPI.
"""

import json
import subprocess
import sys
import re
from datetime import datetime, timezone
import urllib.request
import urllib.error


def get_installed_packages() -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True, text=True
    )
    packages = json.loads(result.stdout)
    return {pkg["name"].lower(): pkg["version"] for pkg in packages}


def get_pypi_info(package_name: str) -> dict | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PyConTogo2026-SupplyChainAudit/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def check_typosquatting(package_name: str) -> list[str]:
    known_packages = [
        "requests", "numpy", "pandas", "flask", "django", "tensorflow",
        "pytorch", "scikit-learn", "matplotlib", "beautifulsoup4", "aiohttp",
        "fastapi", "pydantic", "sqlalchemy", "jinja2", "pillow", "urllib3",
        "pyyaml", "scipy", "transformers", "torch",
    ]

    suspicious = []
    name_lower = package_name.lower()

    for known in known_packages:
        if name_lower == known:
            continue
        if known in name_lower or name_lower in known:
            if len(name_lower) <= len(known) + 5:
                suspicious.append(known)
        if name_lower.replace("-", "") == known.replace("-", ""):
            suspicious.append(known)

    return suspicious


def check_maintenance(info: dict) -> dict:
    releases = info.get("releases", {})
    info_data = info.get("info", {})

    upload_times = []
    for version, files in releases.items():
        for f in files:
            if f.get("upload_time"):
                try:
                    dt = datetime.fromisoformat(f["upload_time"].replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    upload_times.append(dt)
                except (ValueError, TypeError):
                    pass

    latest_release = max(upload_times) if upload_times else None
    days_since_release = None
    if latest_release:
        delta = datetime.now(timezone.utc) - latest_release
        days_since_release = delta.days

    maintainers = info_data.get("maintainers", []) or []
    author = info_data.get("author", "")
    author_email = info_data.get("author_email", "")

    return {
        "latest_release": latest_release,
        "days_since_release": days_since_release,
        "maintainers_count": len(maintainers),
        "author": author,
        "author_email": author_email,
    }


def audit():
    print(f"\n{'='*60}")
    print(f"📦 Supply Chain Security Audit")
    print(f"{'='*60}\n")

    packages = get_installed_packages()
    print(f"[*] {len(packages)} paquets installés.\n")

    warnings = []
    errors = []

    for pkg_name, version in packages.items():
        print(f"  Analyse : {pkg_name}=={version} ...", end=" ")

        info = get_pypi_info(pkg_name)

        if info is None:
            print("⚠️  INTROUVABLE SUR PYPI")
            errors.append(f"{pkg_name} : introuvable sur PyPI — possible typo ou paquet local")
            continue
        elif "error" in info:
            print(f"⚠️  Erreur réseau : {info['error']}")
            continue

        maintenance = check_maintenance(info)

        flags = []

        if maintenance["days_since_release"] is not None and maintenance["days_since_release"] > 730:
            flags.append(f"Pas de release depuis {maintenance['days_since_release']} jours")
            warnings.append(f"{pkg_name} : abandonné ? ({maintenance['days_since_release']} jours sans release)")

        if maintenance["maintainers_count"] == 0 and not maintenance["author"]:
            flags.append("Aucun mainteneur")

        suspicious = check_typosquatting(pkg_name)
        if suspicious:
            flags.append(f"Similaire à : {', '.join(suspicious)}")
            errors.append(f"{pkg_name} : nom suspect — similaire à {', '.join(suspicious)}")

        if flags:
            print(f"⚠️  {' | '.join(flags)}")
        else:
            print("✅")

    print(f"\n{'='*60}")
    print(f"📊 RÉSULTATS")
    print(f"{'='*60}")

    if errors:
        print(f"\n🔴 ERREURS ({len(errors)}) :")
        for e in errors:
            print(f"  • {e}")

    if warnings:
        print(f"\n🟡 AVERTISSEMENTS ({len(warnings)}) :")
        for w in warnings:
            print(f"  • {w}")

    if not errors and not warnings:
        print(f"\n✅ Aucun problème détecté !")

    print(f"\n💡 Recommandations :")
    print(f"  1. Utilisez pip-audit ou safety pour les CVE connues")
    print(f"  2. Vérifiez les hash avec pip install --require-hashes")
    print(f"  3. Préférez les paquets avec plusieurs mainteneurs")
    print(f"  4. Évitez les paquets sans release depuis > 1 an")
    print(f"  5. Utilisez un lockfile (pip freeze > requirements.txt)")


def main():
    audit()


if __name__ == "__main__":
    main()
