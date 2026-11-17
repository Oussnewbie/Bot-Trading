"""Rejoue la v6 minute par minute et refait etrave/reference.json (les trades que la page Risque d'Étrave rejoue).

    python recherches/nasdaq/reference.py

Règles : celles de l'EA ORB-v6 (ajout de 2 unités à +2R, stop de l'ensemble 1R sous l'ajout, stop à l'entrée à +1,5R,
sortie 15:50, 12:45 les jours fériés et demi-séances). Coûts : spread réel de Dukascopy, glissement 0,1 point."""
import json, os, sys
import pandas as pd
ICI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ICI)
import donnees, sim, gestion

AJOUT = ((2.0, 2.0, 1.0),)      # (seuil en R à la clôture M5, taille de l'ajout, stop commun en R sous l'ajout)

if __name__ == "__main__":
    g, D = donnees.preparer(); sim.init(g)
    X = gestion.jouer(D, adds=AJOUT).sort_values("day").reset_index(drop=True)
    print(sim.ENTETE); print(sim.ligne("v6, ajout de 2", X))
    print(sim.ligne("v5, ajout de 1", gestion.jouer(D, adds=((2.0, 1.0, 1.0),))))
    print(sim.ligne("sans pyramide", gestion.jouer(D, adds=())))
    ref = dict(source="ORB v6 (ajout de 2 unités à +2R) rejouée le 2026-11-17 à la minute sur NAS100 CFD Dukascopy (M1 bid et ask), glissement 0,1 point",
               debut=str(X.day.iloc[0].date()), fin="2026-11-13", colonnes=["date", "r", "range_sur_prix", "pyramide"],
               trades=[[str(r.day.date()), round(float(r.r), 4), round(float(r.rng / r.prix), 6), int(bool(r.pyr))] for r in X.itertuples()])
    sortie = os.path.join(os.path.dirname(os.path.dirname(ICI)), "etrave", "reference.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, separators=(",", ":"))
    print(len(ref["trades"]), "trades écrits dans", sortie)
