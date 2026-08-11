"""
Démo 5 : Visualisation des attaques
PyCon Togo 2026

Génère un bar chart des IP les plus actives à partir des logs SSH.
"""

import sys
import matplotlib.pyplot as plt
from collections import Counter
from log_analyzer import parse_auth_log


def visualize(filepath: str, top_n: int = 10, output: str | None = None):
    counter = parse_auth_log(filepath)
    top = counter.most_common(top_n)

    if not top:
        print("[i] Aucune donnée à visualiser.")
        return

    ips, counts = zip(*top)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = plt.cm.Reds_r([1 - (i / len(counts)) * 0.7 for i in range(len(counts))])
    bars = ax.bar(range(len(ips)), counts, color=colors, edgecolor="#FF4444", linewidth=0.5)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.02,
            str(count),
            ha="center",
            va="bottom",
            fontsize=9,
            color="#00FF41",
        )

    ax.set_xticks(range(len(ips)))
    ax.set_xticklabels(ips, rotation=45, ha="right", fontsize=9, color="#CCCCCC")
    ax.set_ylabel("Nombre de tentatives échouées", color="#CCCCCC")
    ax.set_title(f"Top {top_n} IP — Tentatives SSH échouées", color="#00FF41", fontsize=14, fontweight="bold")
    ax.set_facecolor("#0D1117")
    fig.patch.set_facecolor("#0D1117")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333333")
    ax.spines["bottom"].set_color("#333333")
    ax.tick_params(colors="#888888")

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150, bbox_inches="tight")
        print(f"[✓] Graphique sauvegardé : {output}")
    else:
        plt.show()


def main():
    filepath = "data/auth.log"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    visualize(filepath, output="data/ssh_attacks.png")


if __name__ == "__main__":
    main()
