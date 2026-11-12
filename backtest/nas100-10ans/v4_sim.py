"""Variantes de la v3 : sortie si la bougie clôture de nouveau dans le range, entrée sur clôture, filtres de structure."""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbx
fam.prep(); G = fam.G
if not os.path.exists("orb_features.pkl"):  # indicateurs à 9:35, calculés une fois (comme orbx_run.py)
    orbx.features().to_pickle("orb_features.pkl")
F = pd.read_pickle("orb_features.pkl")
BO, BH, BL, BC, AO, AH, AL, AC, mins, t = (G[k] for k in ("BO","BH","BL","BC","AO","AH","AL","AC","mins","t"))
S = fam.SLIP
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")

def path(k, d, ent, sl, last_i, orH, orL, p, start=None):
    """start = k (stop orders: only the stop can be hit on the fill bar) ; ci = window (bars, fill bar = 0) for close-inside exit."""
    risk = abs(ent - sl); be = p.get("be", 1.5); ci = p.get("ci"); cim = p.get("cim", 0.0)
    j0 = k
    if start != "close":
        if (d == 1 and BL[k] <= sl) or (d == -1 and AH[k] >= sl):
            return (sl - d * S - ent) * d / risk, k
        if ci is not None and ci >= 0:
            inside = (BC[k] < orH - cim * (orH - orL)) if d == 1 else (BC[k] > orL + cim * (orH - orL))
            if inside: return (((BC[k] - S) - ent) if d == 1 else (ent - (AC[k] + S))) / risk, k
    stop, mfe = sl, 0.0
    for j in range(k + 1, last_i + 1):
        hi = BH[j] if d == 1 else AH[j]; lo = BL[j] if d == 1 else AL[j]
        if (lo <= stop) if d == 1 else (hi >= stop):
            px = (min(stop, BO[j]) - S) if d == 1 else (max(stop, AO[j]) + S)
            return (px - ent) * d / risk, j
        fav = ((hi - ent) if d == 1 else (ent - lo)) / risk
        mfe = max(mfe, fav)
        if be and mfe >= be: stop = max(stop, ent) if d == 1 else min(stop, ent)
        if ci is not None and j - k <= ci:
            inside = (BC[j] < orH - cim * (orH - orL)) if d == 1 else (BC[j] > orL + cim * (orH - orL))
            if inside: return (((BC[j] - S) - ent) if d == 1 else (ent - (AC[j] + S))) / risk, j
    px = BC[last_i] - S if d == 1 else AC[last_i] + S
    return (px - ent) * d / risk, last_i

def run(p, keep=None):
    lb = orbx.last_before(950); out = []
    cutoff = p.get("cutoff", 585)
    for i, row in F.iterrows():
        last_i = lb[i]
        if last_i <= i: continue
        orH, orL = row.orH, row.orL
        if p.get("entry") == "close":
            # entrée à la clôture de la première bougie qui clôture hors du range (avant cutoff)
            for k in range(i + 1, last_i):
                if mins[k] >= cutoff: break
                up = BC[k] > orH; dn = BC[k] < orL
                if up or dn:
                    d = 1 if up else -1
                    ent = (AC[k] + S) if d == 1 else (BC[k] - S)
                    sl = orL if d == 1 else orH
                    if p.get("slmode") == "bar": sl = BL[k] if d == 1 else AH[k]
                    if (ent - sl) * d <= 0: break
                    r, ex = path(k, d, ent, sl, last_i, orH, orL, p, start="close")
                    out.append(dict(t=t[k], i=i, r=r, d=d)); break
                # le stop opposé déjà touché ne compte pas ici : on attend une clôture
            continue
        k = i + 1; sides = {1, -1}
        while k <= last_i and mins[k] < cutoff:
            up = AH[k] >= orH; dn = BL[k] <= orL
            if up or dn:
                res = []
                for d in [x for x, h in ((1, up), (-1, dn)) if h]:
                    ent = (max(orH, AO[k]) + S) if d == 1 else (min(orL, BO[k]) - S)
                    res.append((path(k, d, ent, orL if d == 1 else orH, last_i, orH, orL, p), d))
                (r, ex), d = min(res, key=lambda x: x[0][0])
                out.append(dict(t=t[k], i=i, r=r, d=d, both=len(res) == 2)); break
            k += 1
    X = pd.DataFrame(out)
    if keep is not None: X = X[[keep(F.loc[i], d) for i, d in zip(X.i, X.d)]]
    return X

def line(lab, X):
    r = X.r; tr, te = X[X.t < SPLIT].r, X[X.t >= SPLIT].r
    eq = r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    st = w = 0
    for v in r: st = st + 1 if v < -0.05 else 0; w = max(w, st)
    yrs = X.groupby(X.t.dt.year).r.sum()
    print(f"| {lab} | {len(X)} | {100*(r<=-0.9).mean():.0f} % | {100*(r>0.05).mean():.0f} % | {r.mean():+.3f}R | {tr.mean():+.3f} / {te.mean():+.3f} | {r.sum():+.0f}R | -{dd:.0f}R / {w} | {(yrs>0).sum()}/{len(yrs)} |", flush=True)
    return X

if __name__ == "__main__":
    print("| Variante | Trades | Stops pleins | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
    print("|---|---|---|---|---|---|---|---|---|")
    line("v3 (référence)", run({}))
    for ci in (0, 1, 2, 3, 6):
        line(f"Sortie si clôture de nouveau dans le range, {ci+1} bougie(s) après l'entrée", run(dict(ci=ci)))
    line("Sortie si clôture à plus de 25 % dans le range, bougie d'entrée", run(dict(ci=0, cim=0.25)))
    line("Sortie si clôture à plus de 50 % dans le range, bougie d'entrée", run(dict(ci=0, cim=0.5)))
    line("Entrée à la clôture hors du range (avant 9:45), stop de l'autre côté", run(dict(entry="close")))
    line("Entrée à la clôture hors du range (avant 9:50)", run(dict(entry="close", cutoff=590)))
    line("Entrée à la clôture hors du range (avant 10:00)", run(dict(entry="close", cutoff=600)))
    line("Entrée à la clôture + sortie si reclôture dans le range (3 bougies)", run(dict(entry="close", ci=2)))
