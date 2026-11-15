"""Troisième étage : les effets d'horaire documentés dans la littérature, testés tels quels (aucun réglage cherché).

 - indices : la dérive de nuit (achat à la clôture de New York, vente à l'ouverture suivante) ; l'élan de fin de séance
   (la dernière demi-heure dans le sens de la journée, ou dans le sens de la première demi-heure) ;
 - or : la hausse des heures d'Asie (achat le soir, vente au matin de Londres ou avant New York) ;
 - EUR/USD : une devise baisse pendant ses propres heures de bureau (vente pendant l'Europe, achat pendant l'Amérique) ;
 - bitcoin : la nuit américaine, et l'élan de fin de séance.

Un trade par jour, entrée et sortie à heure fixe, stop large (15 ATR M5) qui ne sert que de garde-fou et d'unité de
risque. Les achats du soir se font à 20:00 et non à la réouverture de 17:00-18:00 : le spread y est plusieurs fois plus
large (un premier essai à 18:05 perdait 0,07R par trade sur ce seul coût). Le financement d'une nuit est compté (taux de swing.FINANCEMENT) pour les trades qui passent 17:00 New York.

    python backtest/multi/horaires.py      écrit sorties/variantes-horaires.csv
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import banc as B  # noqa: E402
from swing import FINANCEMENT  # noqa: E402

STOP_ATR = 15.0
# (description, entrée, sortie, sens) ; sens : +1, -1, "jour" (sens de la séance jusqu'à l'entrée, depuis 9:30),
# "debut" (sens de la première demi-heure 9:30-10:00). Minutes de New York ; une sortie > 1440 est le lendemain.
INDICES = [("nuit : achat 15:55, vente 9:35 le lendemain", 955, 1440 + 575, 1), ("fin de seance dans le sens de la journee (15:30 -> 15:55)", 930, 955, "jour"),
           ("fin de seance dans le sens de la premiere demi-heure (15:30 -> 15:55)", 930, 955, "debut"), ("seance : achat 9:35, vente 15:55", 575, 955, 1)]
TESTS = {
    "nas100": INDICES, "dow": INDICES,
    "or": [("Asie : achat 20:00, vente 3:00", 1200, 1440 + 180, 1), ("Asie + Londres : achat 20:00, vente 8:20", 1200, 1440 + 500, 1),
           ("New York : vente 9:35, rachat 15:55", 575, 955, -1), ("fin de seance dans le sens de la journee (15:30 -> 15:55)", 930, 955, "jour")],
    "eurusd": [("heures d'Europe : vente 3:00, rachat 11:00", 180, 660, -1), ("heures d'Amerique : achat 11:00, vente 16:55", 660, 1015, 1),
               ("Asie : achat 20:00, vente 3:00", 1200, 1440 + 180, 1)],
    "bitcoin": [("nuit americaine : achat 16:00, vente 9:30", 960, 1440 + 570, 1), ("seance americaine : achat 9:35, vente 15:55", 575, 955, 1),
                ("fin de seance dans le sens de la journee (15:30 -> 15:55)", 930, 955, "jour")],
}


def jouer_fenetre(g, entree, sortie, sens):
    dates = B.jours(g)
    atr = B.atr(g)
    i_ent, i_sor = B.indice(g, dates, entree), B.premier_apres(g, dates, sortie)
    i_930, i_1000 = B.indice(g, dates, 570), B.indice(g, dates, 600)
    achat, vente = FINANCEMENT[g["nom"]]
    lignes = []
    for j in range(len(dates)):
        k, e = i_ent[j], i_sor[j]
        if k < 1 or e <= k or g["tms"][e] - g["tms"][k] > 4 * 86_400_000:      # entrée absente, ou sortie plus de 4 jours après
            continue
        if sens in ("jour", "debut"):
            a = i_930[j]
            b = k if sens == "jour" else i_1000[j]
            if a < 0 or b <= a:
                continue
            d = int(np.sign(g["BO"][b] - g["BO"][a]))
            if d == 0:
                continue
        else:
            d = sens
        ent = g["AO"][k] + g["slip"] if d == 1 else g["BO"][k] - g["slip"]
        risque = STOP_ATR * atr[k - 1]
        res = B.jouer(g, int(k), d, float(ent), float(ent - d * risque), int(e))
        if res is None:
            continue
        nuits = 1 if sortie > 1440 and entree < 1020 else 0       # passe 17:00 New York (une entrée à 20:00 ne paie pas la nuit qui vient de tourner)
        cout = ent * (achat if d == 1 else vente) / 100.0 / 365.0 * nuits
        lignes.append((g["t"][int(k)], res[0] - cout / risque, d))
    x = pd.DataFrame(lignes, columns=["t", "r", "d"])
    x["per"] = B.periodes(g["nom"], x.t)
    return x


if __name__ == "__main__":
    lignes = []
    for nom, tests in TESTS.items():
        try:
            g = B.charger(nom)
        except FileNotFoundError:
            continue
        for description, entree, sortie, sens in tests:
            x = jouer_fenetre(g, entree, sortie, sens)
            ligne = dict(instrument=nom, famille="effet d'horaire", variante=description, gestion="")
            for per in ("train", "A"):
                s = B.stats(x, per)
                ligne.update({f"n_{per}": s["n"], f"moy_{per}": round(s["mean"], 4), f"t_{per}": round(s["t"], 2),
                              f"tot_{per}": round(s["tot"], 1), f"baisse_{per}": round(s["dd"], 1)})
            tout = B.stats(x, ["train", "A"])
            ligne.update(n=tout["n"], tot=round(tout["tot"], 1), baisse=round(tout["dd"], 1), annees_pos=tout["ypos"], gagnants=round(tout["win"], 3))
            lignes.append(ligne)
    table = pd.DataFrame(lignes)
    os.makedirs(os.path.join(ICI, "sorties"), exist_ok=True)
    table.to_csv(os.path.join(ICI, "sorties", "variantes-horaires.csv"), index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 75)
    print(table[["instrument", "variante", "n_train", "moy_train", "t_train", "tot_train", "n_A", "moy_A", "t_A", "tot_A", "annees_pos"]].to_string(index=False))
