"""Reconstruit interface/reference.json : la liste des trades de la v5 sur les données du dépôt (2018 -> 2026-11).

L'interface s'en sert pour dire ce que le test donne à un risque et un levier choisis (gain par an, pire baisse,
jours où la marge manque). À relancer quand les données ou le simulateur changent :

    python interface/construire_reference.py

Pour chaque trade : la date (New York), le résultat en R, la largeur du range rapportée au prix (elle fixe la taille de
la position, donc la marge), et si la pyramide s'est déclenchée.
"""
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "reference.json")
sys.path.insert(0, os.path.join(os.path.dirname(ICI), "backtest", "nas100-10ans"))


def construire():
    import v5_lab as L
    from orb_v5 import V5

    jours = L.prep()
    sans, avec = L.run({}, L.f_v4), L.run(V5, L.f_v4)
    x = avec.merge(jours[["i", "orH", "orL", "orw"]], on="i").merge(sans[["i", "r"]].rename(columns={"r": "r_sans"}), on="i")
    trades = [[t.strftime("%Y-%m-%d"), round(float(r), 4), round(float(w / ((h + l) / 2)), 6), int(abs(r - r0) > 1e-9)]
              for t, r, w, h, l, r0 in zip(x.t, x.r, x.orw, x.orH, x.orL, x.r_sans)]
    return {
        "source": "backtest/nas100-10ans/orb_v5.py, NAS100 CFD Dukascopy M5, glissement 0,1 point",
        "debut": trades[0][0], "fin": trades[-1][0],
        "colonnes": ["date", "r", "range_sur_prix", "pyramide"],
        "trades": trades,
    }


if __name__ == "__main__":
    ref = construire()
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False, separators=(",", ":"))
    n = len(ref["trades"])
    print(f"{SORTIE} : {n} trades, {sum(t[1] for t in ref['trades']):+.0f}R, pyramide sur {100 * sum(t[3] for t in ref['trades']) / n:.0f} % des trades")
