"""
analyse_rh.py
-------------
Analyse et visualise la repartition des salaries selon :
  - leur pratique sportive personnelle
  - leur moyen de deplacement pour venir au travail

Usage :
  python analyse_rh.py

Prerequis :
  - pip install pandas openpyxl matplotlib
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

import matplotlib
matplotlib.use("Agg")  # rendu sans fenetre graphique

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from utils.config import get_rh_file, get_sport_file, BASE_DIR
from utils.helpers import is_sport_valide
from utils.logging_utils import setup_logging


setup_logging("analyse_rh.log", BASE_DIR)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chargement et preparation des donnees
# ---------------------------------------------------------------------------
def load_and_merge() -> pd.DataFrame:
    df_rh    = pd.read_excel(get_rh_file(), dtype=str)
    df_sport = pd.read_excel(get_sport_file(), dtype=str)

    df_rh.columns    = df_rh.columns.str.strip()
    df_sport.columns = df_sport.columns.str.strip()

    df_rh    = df_rh.rename(columns={
        df_rh.columns[0]:  "id_salarie",
        df_rh.columns[10]: "moyen_deplacement",
    })
    df_sport = df_sport.rename(columns={
        df_sport.columns[0]: "id_salarie",
        df_sport.columns[1]: "pratique_sport",
    })

    df_rh["id_salarie"]        = df_rh["id_salarie"].str.strip()
    df_sport["id_salarie"]     = df_sport["id_salarie"].str.strip()
    df_sport["pratique_sport"] = df_sport["pratique_sport"].str.strip()

    df = df_rh[["id_salarie", "moyen_deplacement"]].merge(
        df_sport[["id_salarie", "pratique_sport"]],
        on="id_salarie", how="left"
    )

    sportif_deplacement = ["Marche/running", "Vélo/Trottinette/Autres"]
    df["vient_sportivement"] = df["moyen_deplacement"].isin(sportif_deplacement)
    df["pratique_sport"] = is_sport_valide(df["pratique_sport"])
    return df


def categorise(df: pd.DataFrame) -> dict:
    return {
        "Sport + Deplacement sportif":       df[ df["pratique_sport"] &  df["vient_sportivement"]].shape[0],
        "Sport + Voiture/TC":                df[ df["pratique_sport"] & ~df["vient_sportivement"]].shape[0],
        "Pas de sport + Deplacement sportif": df[~df["pratique_sport"] &  df["vient_sportivement"]].shape[0],
        "Pas de sport + Voiture/TC":         df[~df["pratique_sport"] & ~df["vient_sportivement"]].shape[0],
    }


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------
COLORS = ["#2ecc71", "#e74c3c", "#3498db", "#95a5a6"]


def build_figure(categories: dict, total: int) -> plt.Figure:
    labels = list(categories.keys())
    values = list(categories.values())

    fig, (ax_pie, ax_bar) = plt.subplots(
        1, 2,
        figsize=(14, 6),
        facecolor="#1a1a2e",
    )
    fig.suptitle(
        "Repartition des salaries — Pratique sportive & Deplacement",
        fontsize=14, fontweight="bold", color="white", y=1.01,
    )

    # --- Camembert ---
    wedges, texts, autotexts = ax_pie.pie(
        values,
        colors=COLORS,
        autopct=lambda p: f"{p:.1f}%\n({int(round(p * total / 100))})",
        startangle=90,
        pctdistance=0.75,
        wedgeprops={"linewidth": 2, "edgecolor": "#1a1a2e"},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontsize(9)

    ax_pie.set_facecolor("#1a1a2e")
    ax_pie.set_title("Repartition en %", color="white", fontsize=11, pad=12)

    legend_patches = [
        mpatches.Patch(color=COLORS[i], label=f"{labels[i]} ({values[i]})")
        for i in range(len(labels))
    ]
    ax_pie.legend(
        handles=legend_patches,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
        fontsize=8,
        framealpha=0,
        labelcolor="white",
    )

    # --- Tableau ---
    ax_bar.set_facecolor("#1a1a2e")
    ax_bar.set_title("Tableau recapitulatif", color="white", fontsize=11, pad=12)
    ax_bar.axis("off")

    col_labels = ["Categorie", "Nombre", "% du total"]
    table_data = [
        [label, str(val), f"{val/total*100:.1f}%"]
        for label, val in categories.items()
    ]
    table_data.append(["TOTAL", str(total), "100.0%"])

    table = ax_bar.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        bbox=[0, 0.1, 1, 0.8],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    # Style header
    for j in range(len(col_labels)):
        table[(0, j)].set_facecolor("#16213e")
        table[(0, j)].set_text_props(color="white", fontweight="bold")

    # Style lignes de donnees
    for i in range(1, len(table_data) + 1):
        for j in range(len(col_labels)):
            if i <= len(COLORS):
                table[(i, j)].set_facecolor(COLORS[i - 1] + "33")  # transparence
            else:
                table[(i, j)].set_facecolor("#16213e")
            table[(i, j)].set_text_props(color="white")

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=== Demarrage de l'analyse RH ===")
    logger.info("Chargement des donnees...")
    df         = load_and_merge()
    categories = categorise(df)
    total      = sum(categories.values())

    logger.info("Total salaries : %d", total)
    for label, val in categories.items():
        logger.info("  %-45s : %3d  (%.1f%%)", label, val, val / total * 100)

    logger.info("Generation du graphique...")
    fig      = build_figure(categories, total)
    out_path = os.path.join(BASE_DIR, "logs", "analyse_rh.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    logger.info("Graphique sauvegarde : %s", out_path)
    logger.info("=== Analyse terminee avec succes ===")


if __name__ == "__main__":
    main()