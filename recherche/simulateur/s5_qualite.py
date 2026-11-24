"""Session 5, étape 3 : contrôle de qualité du S&P 500 Dukascopy AVANT toute stratégie (aucun trade n'est calculé ici).

    .venv/bin/python recherche/simulateur/s5_qualite.py

Fabrique donnees/sp500_m1.parquet à partir des CSV de donnees/brut/sp500/ (telecharger_sp500.sh) et écrit
recherche/resultats/s5_sp500_qualite.md : couverture, jours avec une bougie de 9:30, spread en séance par année, minutes à spread
nul, trous. Une période inutilisable doit être exclue par une règle écrite à ce moment-là, avant s5_juger.py.
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import sim_chemins as SC  # noqa: E402
import sim_donnees as SD  # noqa: E402

BRUT = os.path.join(SC.DOSSIER_DONNEES, "brut", "sp500")
M1 = os.path.join(SC.DOSSIER_DONNEES, "sp500_m1.parquet")
SORTIE = os.path.join(SC.DEPOT, "recherche", "resultats", "s5_sp500_qualite.md")


def main():
    if not os.path.exists(M1):
        SD.construire_m1_nasdaq(dossier=BRUT, sortie=M1)          # fonction générique : CSV bid + ask -> parquet au format du moteur
    m = pd.read_parquet(M1)
    seance = m[(m.minute >= 570) & (m.minute < 960)].copy()
    seance["spread"] = seance.ao - seance.bo
    ouv = m[(m.minute >= 570) & (m.minute < 575)].copy()
    ouv["spread"] = ouv.ao - ouv.bo
    jours = seance.groupby("date").size()
    j930 = set(m.loc[m.minute == 570, "date"])
    lignes = [
        "# S&P 500 Dukascopy (usa500idxusd) : contrôle de qualité avant toute stratégie (session 5)",
        "",
        f"- Minutes bid + ask communes : {len(m)} ; du {m.date.iloc[0]} au {m.date.iloc[-1]}.",
        f"- Jours avec au moins une minute de séance (9:30-16:00 NY) : {len(jours)} ; avec une minute à 9:30 : {len(j930)}.",
        f"- Minutes de séance par jour : médiane {int(jours.median())}, 5e centile {int(jours.quantile(0.05))}, minimum {int(jours.min())}.",
        "",
        "## Par année",
        "",
        "| Année | Jours | Spread médian en séance | Spread médian 9:30-9:35 | Minutes de séance à spread nul ou négatif | Prix médian | Range médian de 9:30 |",
        "|---|---|---|---|---|---|---|",
    ]
    rng = m[m.minute.between(570, 574)].groupby("date").agg(h=("bh", "max"), l=("bl", "min"))
    rng["r"] = rng.h - rng.l
    rng["annee"] = pd.to_datetime(rng.index).year
    for an, g in seance.groupby("annee"):
        o = ouv[ouv.annee == an]
        lignes.append(f"| {an} | {g.date.nunique()} | {g.spread.median():.2f} | {o.spread.median():.2f} | {100 * (g.spread <= 0).mean():.2f} % | "
                      f"{g.bc.median():.0f} | {rng[rng.annee == an].r.median():.2f} |")
    # trous : jours ouvrés sans minute de séance, et jours à séance très incomplète
    tous = pd.bdate_range(m.date.iloc[0], m.date.iloc[-1]).strftime("%Y-%m-%d")
    manquants = sorted(set(tous) - set(jours.index))
    courts = jours[jours < 300]
    lignes += ["", "## Trous",
               f"- Jours ouvrés sans aucune minute de séance : {len(manquants)} (fériés de la Bourse compris) : "
               + ", ".join(manquants[:40]) + (" …" if len(manquants) > 40 else ""),
               f"- Jours avec moins de 300 minutes de séance : {len(courts)} : " + ", ".join(courts.index[:40]) + (" …" if len(courts) > 40 else ""),
               "", "Aucune stratégie n'a été calculée pour écrire ce fichier."]
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
