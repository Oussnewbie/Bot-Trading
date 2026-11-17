"""Gestion du trade généralisée (même moteur à la minute que sim.trade) : plusieurs ajouts de taille libre,
stop à l'entrée réglable, heure de sortie réglable, stop suiveur après la pyramide."""
import numpy as np, pandas as pd
import sim
from sim import G, SLIP


def trade2(k, d, ent, stop, iend, be=1.5, be_lock=0.0, adds=((2.0, 1.0, 1.0),), suiveur=None):
    """adds : liste de (seuil en R à la clôture M5, taille, distance du stop commun sous le prix de l'ajout en R).
    suiveur : après le dernier ajout, stop commun à `suiveur` R sous la meilleure clôture M5 (None = rien)."""
    BO, BC, AO, AC = G["BO"], G["BC"], G["AO"], G["AC"]
    fin5, b5 = G["fin5"], G["b5"]
    ADV, FAV, OADV = (G["BL"], G["BH"], BO) if d == 1 else (G["AH"], G["AL"], AO)
    risk = abs(ent - stop)
    if not risk > 0: return None
    units = [(ent, 1.0)]
    adds = list(adds); be_done = be is None; bar_e = b5[k]; best_c = None

    def tot(px):
        return sum(s * (px - u) * d for u, s in units) / risk

    if (ADV[k] - stop) * d <= 0:
        return dict(r=tot(stop - d * SLIP), ex=k, why="stop", pyr=False)
    m = k
    while True:
        if m > k and (ADV[m] - stop) * d <= 0:
            px = min(stop, OADV[m]) if d == 1 else max(stop, OADV[m])
            return dict(r=tot(px - d * SLIP), ex=m, why="stop", pyr=len(units) > 1)
        if fin5[m]:
            c = BC[m] if d == 1 else AC[m]
            cur = (c - ent) * d / risk
            while adds and m + 1 < iend and cur >= adds[0][0]:
                trig, sz, gap = adds.pop(0)
                add = (AC[m] + SLIP) if d == 1 else (BC[m] - SLIP)
                units.append((add, sz))
                nv = add - d * gap * risk
                stop = max(stop, nv) if d == 1 else min(stop, nv)
                be_done = True
            if suiveur is not None and len(units) > 1 and not adds:
                best_c = c if best_c is None else (max(best_c, c) if d == 1 else min(best_c, c))
                nv = best_c - d * suiveur * risk
                stop = max(stop, nv) if d == 1 else min(stop, nv)
            if not be_done and b5[m] > bar_e:
                s5 = m
                while s5 > 0 and b5[s5 - 1] == b5[m]: s5 -= 1
                fav = FAV[s5:m + 1].max() if d == 1 else FAV[s5:m + 1].min()
                if (fav - (ent + d * be * risk)) * d >= 0:
                    lv = ent + d * be_lock * risk
                    stop = max(stop, lv) if d == 1 else min(stop, lv)
                    be_done = True
        m += 1
        if m >= iend:
            px = (BO[iend] - SLIP) if d == 1 else (AO[iend] + SLIP)
            return dict(r=tot(px), ex=iend, why="fin", pyr=len(units) > 1)


def jouer(D, sortie=None, **kw):
    """sortie : minute NY de sortie forcée (ex. 720 = 12:00), sinon 15:50 / 12:45 comme la v5."""
    out = []
    mins = G["mins"]
    for r in D.itertuples():
        s = sim.signal(r)
        if not s: continue
        k, d = s
        ent = sim.entree_px(r, k, d); st = r.orL if d == 1 else r.orH
        iend = r.iend
        if sortie is not None:
            j = k
            while j < iend and mins[j] < sortie: j += 1
            iend = j
            if iend <= k: continue
        x = trade2(k, d, ent, st, iend, **kw)
        if x:
            x.update(day=r.day, d=d, per=sim.per(r.day), rng=r.orw, prix=r.orH)
            out.append(x)
    return pd.DataFrame(out)
