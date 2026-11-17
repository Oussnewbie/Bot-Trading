"""ORB v5 rejoué à la minute (M1 bid/ask). Les décisions de la v5 restent prises à la clôture des bougies M5
(stop à l'entrée à +1,5R, pyramide à +2R), mais l'entrée et le stop sont vus minute par minute.

Conventions (prudentes, comme l'ancien simulateur) :
 - achat déclenché quand l'ASK touche le niveau, exécuté à max(niveau, ouverture ask) + glissement ;
   vente quand le BID touche le niveau, min(niveau, ouverture bid) - glissement ;
 - stop d'un achat touché par le BID bas, d'une vente par l'ASK haut ; exécuté au pire de (stop, ouverture) ± glissement ;
 - dans la minute d'entrée, si le stop est aussi touché, on compte le stop (ordre inconnu dans la minute) ;
 - un stop déplacé ne vaut qu'à partir de la minute qui suit la clôture M5 qui l'a décidé.
"""
import numpy as np, pandas as pd

SLIP = 0.1
T0, T1 = pd.Timestamp("2018-05-01"), pd.Timestamp("2022-09-01")
G = {}


def init(g):
    G.clear(); G.update(g)
    b5 = g["ts"] // 300_000
    fin5 = np.ones(len(b5), bool); fin5[:-1] = b5[1:] != b5[:-1]
    G["b5"] = b5; G["fin5"] = fin5


def trade(k, d, ent, stop, iend, be=1.5, pyr=(2.0, 1.0), close_stop=None, risk=None, tp=None, be_lock=0.0):
    """Un trade entré dans la minute k. Retourne dict(r, ex, why, mfe, mae) ; R = résultat ÷ risque de départ.
    close_stop : None = stop classique ; sinon (niveau jugé à la clôture M5, stop de secours touché en séance).
    risk : risque de départ (par défaut |ent - stop|)."""
    BO, BH, BL, BC, AO, AH, AL, AC = (G[x] for x in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC"))
    fin5, b5 = G["fin5"], G["b5"]
    if close_stop is not None:
        cl_lvl, stop = close_stop
    risk = risk if risk else abs(ent - stop)
    if not risk > 0:
        return None
    units = [ent]
    be_done = be is None
    pyr_done = pyr is None
    mfe = mae = 0.0
    bar_e = b5[k]
    if d == 1:
        ADV, FAV, OADV = BL, BH, BO
    else:
        ADV, FAV, OADV = AH, AL, AO

    def tot(px):
        return sum((px - u) * d for u in units) / risk

    # minute d'entrée : seul le stop compte (prudence)
    if (ADV[k] - stop) * d <= 0:
        return dict(r=tot(stop - d * SLIP), ex=k, why="stop", mfe=0.0, mae=-1.0)
    m = k
    while True:
        if m > k:
            if (ADV[m] - stop) * d <= 0:
                px = min(stop, OADV[m]) if d == 1 else max(stop, OADV[m])
                return dict(r=tot(px - d * SLIP), ex=m, why="stop" if len(units) == 1 and not (be_done and be is not None) else "stop remonté",
                            mfe=mfe, mae=min(mae, (stop - ent) * d / risk))
            if tp is not None and (FAV[m] - (ent + d * tp * risk)) * d >= 0:
                return dict(r=tot(ent + d * tp * risk), ex=m, why="objectif", mfe=max(mfe, tp), mae=mae)
        mfe = max(mfe, (FAV[m] - ent) * d / risk)
        mae = min(mae, (ADV[m] - ent) * d / risk)
        if fin5[m]:
            # clôture d'une bougie M5
            if close_stop is not None:
                c = BC[m] if d == 1 else AC[m]
                if (c - cl_lvl) * d < 0:                 # clôture au-delà du niveau : sortie au marché
                    px = (BC[m] if d == 1 else AC[m]) - d * SLIP
                    return dict(r=tot(px), ex=m, why="stop clôture", mfe=mfe, mae=mae)
            if not pyr_done and m + 1 < iend:
                cur = ((BC[m] - ent) if d == 1 else (ent - AC[m])) / risk
                if cur >= pyr[0]:
                    add = (AC[m] + SLIP) if d == 1 else (BC[m] - SLIP)
                    units.append(add)
                    nv = add - d * pyr[1] * risk
                    stop = max(stop, nv) if d == 1 else min(stop, nv)
                    if close_stop is not None:
                        close_stop = None
                    pyr_done = be_done = True
            if not be_done and b5[m] > bar_e:
                # bougie M5 après celle de l'entrée : son extrême favorable (toute la bougie)
                s5 = m
                while s5 > 0 and b5[s5 - 1] == b5[m]:
                    s5 -= 1
                fav = FAV[s5:m + 1].max() if d == 1 else FAV[s5:m + 1].min()
                if (fav - (ent + d * be * risk)) * d >= 0:
                    lv = ent + d * be_lock * risk
                    stop = max(stop, lv) if d == 1 else min(stop, lv)
                    if close_stop is not None:
                        close_stop = None
                    be_done = True
        m += 1
        if m >= iend:
            px = (BO[iend] - SLIP) if d == 1 else (AO[iend] + SLIP)
            return dict(r=tot(px), ex=iend, why="fin", mfe=mfe, mae=mae)


def cotes(r, filt=True):
    if not filt:
        return {1, -1}
    s = set()
    if r.rsi > 50 and r.orH >= r.preH: s.add(1)
    if r.rsi < 50 and r.orL <= r.preL: s.add(-1)
    return s


def per(day):
    return "B" if day < T0 else "train" if day < T1 else "A"


def signal(r, cutoff=585, filt=True):
    """Premier franchissement du range entre 9:35 et cutoff (minutes NY). Retourne (k, d) ou None."""
    sides = cotes(r, filt)
    if not sides:
        return None
    BH_, BL_, AH_, mins = G["BH"], G["BL"], G["AH"], G["mins"]
    k = r.i35
    while k < r.iend and mins[k] < cutoff:
        up = AH_[k] >= r.orH; dn = BL_[k] <= r.orL
        if up or dn:
            hit = [d for d, h in ((1, up), (-1, dn)) if h and d in sides]
            if not hit or len(hit) == 2 and False:
                return None
            if up and dn:                       # les deux dans la même minute : rare ; on prend le côté permis s'il est seul
                if len(hit) != 1:
                    return None
            return k, hit[0]
        k += 1
    return None


def entree_px(r, k, d):
    return (max(r.orH, G["AO"][k]) + SLIP) if d == 1 else (min(r.orL, G["BO"][k]) - SLIP)


def base(D, **kw):
    out = []
    for r in D.itertuples():
        s = signal(r)
        if not s:
            continue
        k, d = s
        ent = entree_px(r, k, d)
        st = r.orL if d == 1 else r.orH
        x = trade(k, d, ent, st, r.iend, **kw)
        if x:
            x.update(day=r.day, d=d, k=k, ent=ent, stop=st, per=per(r.day))
            out.append(x)
    return pd.DataFrame(out)


def stats(X, p=None):
    if p is not None:
        X = X[X.per.isin([p] if isinstance(p, str) else p)]
    if len(X) < 2:
        return dict(n=len(X), mean=0, tot=0, dd=0, t=0, stop=0, streak=0, ypos="-")
    r = X.r.values
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.maximum(eq, 0)) - eq).max()
    s = w = 0
    for v in r:
        s = s + 1 if v < -0.05 else 0; w = max(w, s)
    y = X.groupby(pd.DatetimeIndex(X.day).year).r.sum()
    return dict(n=len(X), mean=r.mean(), tot=r.sum(), dd=dd, t=r.mean() / r.std() * np.sqrt(len(r)), stop=(r <= -0.9).mean(),
                streak=w, ypos=f"{(y > 0).sum()}/{len(y)}")


def ligne(lab, X):
    c = []
    for p in ("train", "A", ["B", "train", "A"]):
        s = stats(X, p)
        c.append(f"{s['n']} | {s['mean']:+.3f} | {s['tot']:+.0f}R | t={s['t']:.1f}")
    s = stats(X, ["B", "train", "A"])
    return f"| {lab} | " + " | ".join(c) + f" | -{s['dd']:.0f}R | {s['streak']} | {100*s['stop']:.0f} % | {s['ypos']} |"


ENTETE = ("| Variante | Recherche 2018-05→2022-08 : n | R/trade | total | t | Vérif. 2022-09→2026-11 : n | R/trade | total | t "
          "| Tout : n | R/trade | total | t | pire baisse | série | stops pleins | années + |\n|---" + "|---" * 17 + "|")
