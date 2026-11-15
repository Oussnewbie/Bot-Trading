"""La v5 du Nasdaq appliquée telle quelle à l'or (XAUUSD), sans rien régler : une expérience, pas une stratégie.

    python backtest/or/v5_sur_or.py

Résultat du 15 novembre 2026 (M1 Dukascopy bid et ask, 2018-01 -> 2026-11, M5 reconstruit) : la v5 PERD sur l'or.
    glissement 0,02 $ : 773 trades, -0,18R par trade, -137R, pire baisse -157R, 7 années sur 9 dans le rouge
    glissement 0,10 $ : 773 trades, -0,23R par trade, -174R
Le spread coûte environ 12 % du range de 9:30 (1 à 3 % sur le Nasdaq depuis 2020). Sans filtre ni pyramide : -238R.
C'est pourquoi la case « Or » de l'interface Étrave est décochée par défaut.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nas100-10ans"))
import load10 as LD  # noqa: E402
import v5_lab as L  # noqa: E402
from orb_v5 import V5  # noqa: E402


def m5(d):
    x = LD.agreger(d, 5)
    x.index = pd.to_datetime(x.index, unit="ms", utc=True).tz_convert("America/New_York")
    x = x[["open", "high", "low", "close", "volume"]]
    x.columns = ["o", "h", "l", "c", "v"]
    return x


if __name__ == "__main__":
    bid, ask = (m5(d) for d in LD.lire_m1("or"))
    for glissement in (0.02, 0.1):
        L.SLIP = glissement
        jours = L.prep(data=(bid, ask))      # données passées à la main : le cache du Nasdaq n'est ni lu ni écrit
        print(f"\n### Or, glissement {glissement} $ par exécution (spread médian = {100 * float((jours.spread / jours.orw).median()):.0f} % du range de 9:30)")
        print("| | Trades | Par trade | Total | Pire baisse / série | t |"); print("|---|---|---|---|---|---|")
        for nom, regles, filtre in (("sans filtre ni pyramide", {}, L.f_all), ("filtres, sans pyramide", {}, L.f_v4), ("v5", V5, L.f_v4)):
            x = L.run(regles, filtre)
            s = L.stats(x, ["B", "train", "A"])
            print(f"| {nom} | {s['n']} | {s['mean']:+.3f}R | {s['tot']:+.0f}R | -{s['dd']:.0f}R / {s['streak']} | {s['t']:.2f} |")
            if nom == "v5":
                par_an = x.groupby(x.t.dt.year).r.sum().round(0).astype(int).to_dict()
        print("v5, R par année :", par_an)
