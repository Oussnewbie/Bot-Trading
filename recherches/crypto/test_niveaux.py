"""Lance le test des supports et résistances (niveaux.py) : chaque méthode contre ses deux témoins décalés de ±1,5 ATR,
pour un mouvement de k = 0,5 et 1 ATR, BTC et ETH, recherche (2018-2022) et vérification (2023-2026).
Sortie : sorties/niveaux.csv"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

import niveaux as N

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
COUPE = np.datetime64("2023-01-01")
_cache = {}


SUPPLEMENTAIRES = {"fvg60j": lambda h, d: N.m_fvg(d), "order-blocks60j": lambda h, d: N.m_order_blocks(d),
                   "pivots-classiques-jour": lambda h, d: N.m_pivots_classiques(d, "D"),
                   "pivots-classiques-semaine": lambda h, d: N.m_pivots_classiques(d, "W-SUN"),
                   "pivots-classiques-mois": lambda h, d: N.m_pivots_classiques(d, "M")}


def donnees(actif, noms=None):
    if actif not in _cache:
        h, d = N.journalier(actif)
        ms = {k: f(h, d) for k, f in SUPPLEMENTAIRES.items()} if noms == "supp" else N.methodes(actif, h, d)
        _cache[actif] = (h, d, ms)
    return _cache[actif]


def un(args):
    actif, nom = args
    h, d, ms = donnees(actif, "supp" if nom in SUPPLEMENTAIRES else None)
    lignes = []
    for k in (0.5, 1.0):
        res = {}
        for dec in (0.0, 1.5, -1.5):
            t = N.tester(h, d, ms[nom], k=k, decalage=dec)
            t["per"] = np.where(t.t.values < COUPE, "R", "V")
            res[dec] = t
        for per in ("R", "V"):
            for sens in ("S", "R", "tous"):
                def taux(t):
                    x = t[(t.per == per) & ((t.sens == sens) | (sens == "tous"))].dropna(subset=["issue"])
                    return x.issue.mean(), len(x)
                p, n = taux(res[0.0])
                pc = [taux(res[dc]) for dc in (1.5, -1.5)]
                q = np.nansum([a * b for a, b in pc]) / max(1, sum(b for _, b in pc))
                m = sum(b for _, b in pc)
                se = np.sqrt(q * (1 - q) * (1 / max(n, 1) + 1 / max(m, 1)))
                lignes.append(dict(actif=actif, methode=nom, k=k, periode=per, sens=sens, n=n, rebond=p,
                                   n_temoin=m, rebond_temoin=q, ecart=p - q, z=(p - q) / se if se > 0 else np.nan))
    print(actif, nom, "ok", flush=True)
    return lignes


if __name__ == "__main__":
    taches = []
    supp = "--supp" in sys.argv
    for a in ("BTC", "ETH"):
        if supp:
            taches += [(a, n) for n in SUPPLEMENTAIRES]
            continue
        taches += [(a, n) for n in ["pivots3", "pivots5", "pivots10", "pivots5-2touches", "pivots5-3touches",
                                    "kde-pivots5", "veille-haut-bas", "semaine-haut-bas", "mois-haut-bas",
                                    "profil-poc30j", "profil-zone30j", "profil-hvn30j", "profil-lvn30j",
                                    "profil-poc90j", "profil-hvn90j", "vwap-pivots10", "moyennes20-200",
                                    "ichimoku-kijun-nuage", "fibonacci90j"] + [f"arrondi{p}" for p in N.ARRONDIS[a]]]
    with Pool(4) as pool:
        res = pool.map(un, taches, chunksize=1)
    df = pd.DataFrame([l for r in res for l in r])
    df.to_csv(os.path.join(OUT, "niveaux-supp.csv" if supp else "niveaux.csv"), index=False, float_format="%.4f")
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    x = df[(df.sens == "tous")].pivot_table(index=["actif", "methode"], columns=["k", "periode"], values=["ecart", "z"])
    print(x.round(3).to_string())
