"""
Démo 7 : Analyse NLP des CVE (Common Vulnerabilities and Exposures)
PyCon Togo 2026

Utilise un modèle HuggingFace pour classifier la sévérité des CVE
à partir de leur description textuelle.

Note : Le modèle sera téléchargé au premier lancement (~500 Mo).
"""

import json
import requests
import sys

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


SAMPLE_CVES = [
    {
        "id": "CVE-2024-3094",
        "description": (
            "A backdoor was found in the xz-utils package. Malicious code was "
            "injected into the upstream tarballs, allowing remote code execution "
            "without authentication on affected systems."
        ),
        "cvss": 10.0,
        "severity": "CRITICAL",
    },
    {
        "id": "CVE-2023-44487",
        "description": (
            "The HTTP/2 protocol allows a denial of service because request "
            "cancellation can reset many streams quickly, leading to excessive "
            "server resource consumption."
        ),
        "cvss": 7.5,
        "severity": "HIGH",
    },
    {
        "id": "CVE-2023-32784",
        "description": (
            "KeePass before version 2.54 allows extraction of the master password "
            "from memory dumps due to how the password entry box processes keystrokes."
        ),
        "cvss": 5.5,
        "severity": "MEDIUM",
    },
    {
        "id": "CVE-2022-12345",
        "description": (
            "A minor information disclosure vulnerability in a web interface allows "
            "authenticated users to view non-sensitive configuration data."
        ),
        "cvss": 3.1,
        "severity": "LOW",
    },
    {
        "id": "CVE-2021-44228",
        "description": (
            "Apache Log4j2 JNDI features do not protect against attacker-controlled "
            "LDAP and other JNDI related endpoints, allowing remote code execution "
            "by logging a specially crafted message."
        ),
        "cvss": 10.0,
        "severity": "CRITICAL",
    },
]


def analyze_cve_zero_shot(descriptions: list[str]):
    if not HAS_TRANSFORMERS:
        print("[!] transformers non installé. pip install transformers torch")
        return

    print("[*] Chargement du modèle de zero-shot classification...")
    classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=-1,
    )

    candidate_labels = ["critical", "high", "medium", "low"]

    for i, desc in enumerate(descriptions):
        result = classifier(desc, candidate_labels)
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        print(f"\n  CVE #{i+1}")
        print(f"  Description : {desc[:100]}...")
        print(f"  Sévérité prédite : {top_label.upper()} ({top_score:.1%})")
        print(f"  Scores détaillés : {dict(zip(result['labels'], [f'{s:.1%}' for s in result['scores']]))}")


def main():
    print(f"\n{'='*60}")
    print(f"📝 Analyse NLP des CVE")
    print(f"{'='*60}")

    print(f"\nÉchantillon : {len(SAMPLE_CVES)} CVE\n")
    print(f"{'ID':20s} {'CVSS':>6s}  {'Sévérité':>10s}  Description")
    print("-" * 80)
    for cve in SAMPLE_CVES:
        desc = cve["description"][:80]
        print(f"{cve['id']:20s} {cve['cvss']:>5.1f}  {cve['severity']:>10s}  {desc}...")

    print("\n" + "=" * 60)
    print("🧠 Zero-shot classification avec HuggingFace")
    print("=" * 60)

    descriptions = [cve["description"] for cve in SAMPLE_CVES]
    analyze_cve_zero_shot(descriptions)


if __name__ == "__main__":
    main()
