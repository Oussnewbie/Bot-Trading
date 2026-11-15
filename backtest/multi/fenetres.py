"""Analyse brute, comme celle qui a fait sortir la fenêtre de 9:30 sur le Nasdaq : pour CHAQUE heure de la journée,
que se passe-t-il quand le prix casse le range qui vient de se former ?

Pour chaque instrument, une fenêtre tous les quarts d'heure (96 par jour), quatre longueurs de range (5, 15, 30 et
60 minutes), la cassure brute sans filtre et avec les deux filtres de la v5, gérée comme la v5 sans pyramide (stop de
l'autre côté du range, stop au prix d'entrée à +1,5R) et avec la pyramide. Sortie 6 h 20 après la fin du range (la durée
9:35 -> 15:50 de la v5), ou à 16:55 New York si la coupure de 17:00 arrive avant. Pas de fenêtre entre 16:00 et 18:00.

Deuxième mesure, sans aucune règle de trading : le lien entre le mouvement d'une demi-heure et celui des deux heures qui
suivent, à chaque heure. Positif = le mouvement se prolonge (terrain de cassure) ; négatif = il se retourne.

Le juge reste le même : une fenêtre trouvée sur la période de recherche doit tenir sur la période de vérification, et
ses voisines (un quart d'heure avant, un quart d'heure après) doivent aller dans le même sens.

    python backtest/multi/fenetres.py [instrument…]      écrit sorties/fenetres.csv et sorties/prolongement.csv
"""
import itertools
import multiprocessing
import os
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import banc as B  # noqa: E402
import familles as F  # noqa: E402

SORTIES = os.path.join(ICI, "sorties")
DUREE_TRADE = 380            # minutes entre la fin du range et la sortie : 9:35 -> 15:50, comme la v5
COUPURE = 1015               # 16:55 New York : rien ne passe la coupure quotidienne de 17:00
GESTIONS = {"sans pyramide": dict(be=1.5), "pyramide": dict(be=1.5, pyr=(2.0, 1.0))}


def heure(m):
    m %= 1440
    return f"{m // 60}:{m % 60:02d}"


def prolongement(g, c):
    """Corrélation entre le mouvement de [h, h+30 min) et celui de [h+30 min, h+2 h 30), à chaque demi-heure, sur la
    période de recherche et sur la vérification. Prix bid, aucune règle, aucun coût."""
    per = pd.Series(B.periodes(g["nom"], pd.Series(c.dates).dt.tz_localize(B.NY)))
    lignes = []
    for m in range(0, 1440, 30):
        if 930 <= m < 1080:
            continue
        a, b, e = c.idx(m), c.idx(m + 30), c.apres(m + 150)
        ok = (a >= 0) & (b > a) & (e > b) & (g["tms"][np.maximum(e, 0)] - g["tms"][np.maximum(b, 0)] <= 3 * 3_600_000)
        r1 = np.where(ok, g["BO"][np.maximum(b, 0)] / g["BO"][np.maximum(a, 0)] - 1, np.nan)
        r2 = np.where(ok, g["BO"][np.maximum(e, 0)] / g["BO"][np.maximum(b, 0)] - 1, np.nan)
        ligne = dict(instrument=g["nom"], heure=heure(m), minute=m)
        for p in ("train", "A"):
            s = ok & (per.values == p)
            n = int(s.sum())
            rho = float(np.corrcoef(r1[s], r2[s])[0, 1]) if n > 30 else np.nan
            ligne.update({f"n_{p}": n, f"corr_{p}": round(rho, 3), f"t_{p}": round(rho * np.sqrt((n - 2) / max(1e-9, 1 - rho * rho)), 2) if n > 30 else np.nan,
                          f"mouvement_{p}": round(100 * float(np.nanmean(np.abs(r1[s]))), 4) if n else np.nan})
        lignes.append(ligne)
    return lignes


def un_instrument(nom):
    debut = time.time()
    g = B.charger(nom)
    c = F.Contexte(g)
    lignes = []
    for m, duree, filtre in itertools.product(range(0, 1440, 15), (5, 15, 30, 60), ("aucun", "v4")):
        fin = m + duree
        if 960 <= m < 1080 or (m < 960 and fin > 960):
            continue
        sortie = fin + DUREE_TRADE
        if fin < COUPURE < sortie:
            sortie = COUPURE
        ordres = F.cassure(c, m, fin, max(10, duree), sortie, filtre)
        spread = np.nan
        if ordres:
            k = np.array([o[0] for o in ordres])
            risque = np.array([abs(o[2] - o[3]) for o in ordres])
            spread = float(np.median((g["AO"][k] - g["BO"][k]) / risque))
        for gestion, options in GESTIONS.items():
            x = B.derouler(g, ordres, **options)
            ligne = dict(instrument=nom, heure=heure(m), minute=m, duree=duree, filtre=filtre, gestion=gestion, spread_sur_risque=round(spread, 3))
            for p in ("train", "A"):
                s = B.stats(x, p)
                ligne.update({f"n_{p}": s["n"], f"moy_{p}": round(s["mean"], 4), f"t_{p}": round(s["t"], 2), f"tot_{p}": round(s["tot"], 1), f"baisse_{p}": round(s["dd"], 1)})
            lignes.append(ligne)
    pro = prolongement(g, c)
    print(f"{nom} : {len(lignes)} fenêtres en {time.time() - debut:.0f} s", flush=True)
    return lignes, pro


if __name__ == "__main__":
    noms = sys.argv[1:] or ["nas100", "dow", "or", "eurusd", "bitcoin"]
    with multiprocessing.Pool(min(4, len(noms))) as pool:
        resultats = pool.map(un_instrument, noms)
    os.makedirs(SORTIES, exist_ok=True)
    for fichier, table in (("fenetres.csv", pd.DataFrame([l for r in resultats for l in r[0]])), ("prolongement.csv", pd.DataFrame([l for r in resultats for l in r[1]]))):
        chemin = os.path.join(SORTIES, fichier)
        if sys.argv[1:] and os.path.exists(chemin):
            ancien = pd.read_csv(chemin)
            table = pd.concat([ancien[~ancien.instrument.isin(noms)], table], ignore_index=True)
        table.to_csv(chemin, index=False)
        print(f"{len(table)} lignes -> {chemin}")
