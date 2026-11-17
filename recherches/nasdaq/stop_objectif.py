"""Stop au prix d'entrée plus tôt et objectif en R : la v6 contre les réglages essayés sur TradingView (17 novembre 2026).

    python recherches/nasdaq/stop_objectif.py

Même moteur à la minute que gestion.trade2 (bid et ask Dukascopy, glissement 0,1 point, ajout de 2 unités à +2R), avec
en plus un objectif comme dans le script Pine : posé sur toutes les unités (pyramide comprise), actif à partir de la
bougie M5 qui suit l'entrée. Grille : stop à l'entrée à 0,5 / 0,75 / 1 / 1,5R ou jamais, objectif 3 à 8R ou aucun.
Puis 0,5R + 5R contre la v6 : par année, sur les périodes récentes, et sur des fenêtres glissantes de 3, 6 et 12 mois."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import donnees, sim
from sim import G, SLIP

import donnees, sim
from sim import G, SLIP

def trade3(k, d, ent, stop, iend, be=1.5, adds=((2.0, 2.0, 1.0),), tp=None):
    BO, BC, AO, AC = G["BO"], G["BC"], G["AO"], G["AC"]
    fin5, b5 = G["fin5"], G["b5"]
    ADV, FAV, OADV, OFAV = (G["BL"], G["BH"], BO, BO) if d == 1 else (G["AH"], G["AL"], AO, AO)
    risk = abs(ent - stop)
    if not risk > 0: return None
    units = [(ent, 1.0)]; adds = list(adds); be_done = be is None; bar_e = b5[k]
    tpx = None if tp is None else ent + d * tp * risk
    tot = lambda px: sum(s * (px - u) * d for u, s in units) / risk
    if (ADV[k] - stop) * d <= 0:
        return dict(r=tot(stop - d * SLIP), why="stop", pyr=False, be=False)
    m = k
    while True:
        if m > k and (ADV[m] - stop) * d <= 0:
            px = min(stop, OADV[m]) if d == 1 else max(stop, OADV[m])
            return dict(r=tot(px - d * SLIP), why="stop", pyr=len(units) > 1, be=be_done)
        if tpx is not None and b5[m] > bar_e and (FAV[m] - tpx) * d >= 0:
            px = max(tpx, OFAV[m]) if d == 1 else min(tpx, OFAV[m])
            return dict(r=tot(px), why="objectif", pyr=len(units) > 1, be=be_done)
        if fin5[m]:
            c = BC[m] if d == 1 else AC[m]
            cur = (c - ent) * d / risk
            while adds and m + 1 < iend and cur >= adds[0][0] and (tpx is None or (tpx - c) * d > 0):
                trig, sz, gap = adds.pop(0)
                add = (AC[m] + SLIP) if d == 1 else (BC[m] - SLIP)
                units.append((add, sz))
                nv = add - d * gap * risk
                stop = max(stop, nv) if d == 1 else min(stop, nv)
                be_done = True
            if not be_done and b5[m] > bar_e:
                s5 = m
                while s5 > 0 and b5[s5 - 1] == b5[m]: s5 -= 1
                fav = FAV[s5:m + 1].max() if d == 1 else FAV[s5:m + 1].min()
                if (fav - (ent + d * be * risk)) * d >= 0:
                    stop = max(stop, ent) if d == 1 else min(stop, ent)
                    be_done = True
        m += 1
        if m >= iend:
            px = (BO[iend] - SLIP) if d == 1 else (AO[iend] + SLIP)
            return dict(r=tot(px), why="fin", pyr=len(units) > 1, be=be_done)

def jouer(D, **kw):
    out = []
    for r in D.itertuples():
        s = sim.signal(r)
        if not s: continue
        k, d = s
        x = trade3(k, d, sim.entree_px(r, k, d), r.orL if d == 1 else r.orH, r.iend, **kw)
        if x:
            x.update(day=r.day, d=d, per=sim.per(r.day)); out.append(x)
    return pd.DataFrame(out)


if __name__ == "__main__":
    g, D = donnees.preparer(); sim.init(g)
    print(sim.ENTETE)
    V = {}
    for be in (None, 0.5, 0.75, 1.0, 1.5):
        for tp in (None, 3, 4, 5, 6, 8):
            V[(be, tp)] = X = jouer(D, be=be, tp=tp)
            print(sim.ligne(f"stop à l'entrée {be or '-'} / objectif {tp or '-'}", X))
    A, B = V[(1.5, None)], V[(0.5, 5)]
    an = lambda X: X.groupby(pd.DatetimeIndex(X.day).year).r.sum()
    print("\nPar année (R)\n" + pd.DataFrame({"v6": an(A), "0,5R + 5R": an(B)}).round(1).to_string())
    fin = pd.Timestamp("2026-11-14")
    print("\nPériodes qui finissent le 2026-11-13")
    for mois in (1, 3, 6, 12, 24, 36):
        d0 = fin - pd.DateOffset(months=mois); a, b = A[A.day >= d0].r.sum(), B[B.day >= d0].r.sum()
        print(f"{mois:>2} mois : v6 {a:+6.1f}R | 0,5R + 5R {b:+6.1f}R | rapport {b / a:.2f}")
    for mois in (3, 6, 12):
        r = np.array([(A[(A.day >= d0) & (A.day < d0 + pd.DateOffset(months=mois))].r.sum(),
                       B[(B.day >= d0) & (B.day < d0 + pd.DateOffset(months=mois))].r.sum())
                      for d0 in pd.date_range("2018-05-01", fin - pd.DateOffset(months=mois), freq="7D")])
        print(f"fenêtres de {mois} mois ({len(r)}) : 0,5R + 5R meilleur dans {100 * (r[:, 1] > r[:, 0]).mean():.0f} %, "
              f"au moins 2,5 fois la v6 dans {100 * ((r[:, 1] >= 2.5 * r[:, 0]) & (r[:, 0] > 0)).mean():.0f} %")
