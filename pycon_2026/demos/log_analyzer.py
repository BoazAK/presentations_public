"""
Démo 4 : Analyse de logs SSH
PyCon Togo 2026

Parse un fichier auth.log pour identifier les IP qui tentent
des connexions SSH échouées (brute-force, scans, etc.).
"""

import sys
from collections import Counter


def parse_auth_log(filepath: str) -> Counter:
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    failed_lines = [line.strip() for line in lines if "Failed password" in line]

    ips = []
    for line in failed_lines:
        parts = line.split()
        for i, part in enumerate(parts):
            if part == "from" and i + 1 < len(parts):
                ips.append(parts[i + 1])
                break

    return Counter(ips)


def main():
    filepath = "data/auth.log"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"📋 Analyse de logs SSH : {filepath}")
    print(f"{'='*60}\n")

    counter = parse_auth_log(filepath)
    top_ips = counter.most_common(15)

    if not top_ips:
        print("[i] Aucune tentative échouée trouvée dans ce fichier.")
        return

    print(f"{'IP':20s} {'Tentatives':>12s}  {'Pourcentage':>12s}")
    print("-" * 50)

    total_attempts = sum(counter.values())

    for ip, count in top_ips:
        pct = (count / total_attempts) * 100
        bar = "█" * int(pct / 2)
        print(f"{ip:20s} {count:>8d}    ({pct:5.1f}%)  {bar}")

    print("-" * 50)
    print(f"\n📊 Total : {total_attempts} tentatives échouées")
    print(f"📊 IP uniques : {len(counter)}")
    print(f"📊 Top 1 : {top_ips[0][0]} ({top_ips[0][1]} tentatives)")


if __name__ == "__main__":
    main()
