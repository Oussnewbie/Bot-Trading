import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import v4_sim as slsim
from v4_sim import G, F, path, line, S
BO, BH, BL, BC, AO, AH, AL, AC, mins, t = (G[k] for k in ("BO","BH","BL","BC","AO","AH","AL","AC","mins","t"))
import orbx
tn = t.as_unit("ns").asi8
def ext(i, h0):
    a = np.searchsorted(tn, tn[i] - int(h0 * 3600e9))
    return (BH[a:i].max(), BL[a:i].min()) if i - a >= 2 else (np.nan, np.nan)
for h0 in (0.5, 1.0, 1.5):
    e = np.array([ext(i, h0) for i in F.index]); F[f"pH{h0}"] = e[:, 0]; F[f"pL{h0}"] = e[:, 1]
def run_allow(allow, p={}):
    """Comme le script Pine : seuls les côtés autorisés ont un ordre ; si l'autre côté est touché d'abord, plus de trade."""
    lb = orbx.last_before(950); out = []
    for i, row in F.iterrows():
        last_i = lb[i]
        if last_i <= i: continue
        orH, orL = row.orH, row.orL; sides = allow(row)
        if not sides: continue
        k = i + 1
        while k <= last_i and mins[k] < p.get("cutoff", 585):
            up = AH[k] >= orH; dn = BL[k] <= orL
            if up or dn:
                hit = [d for d, h in ((1, up), (-1, dn)) if h and d in sides]
                if not hit: break                      # le côté interdit est touché d'abord : ordre annulé
                res = []
                for d in hit:
                    ent = (max(orH, AO[k]) + S) if d == 1 else (min(orL, BO[k]) - S)
                    res.append((path(k, d, ent, orL if d == 1 else orH, last_i, orH, orL, p), d))
                (r, ex), d = min(res, key=lambda x: x[0][0])
                out.append(dict(t=t[k], i=i, r=r, d=d)); break
            k += 1
    return pd.DataFrame(out)
rsi = lambda r: {1} if r.m5_rsi > 0 else {-1} if r.m5_rsi < 0 else set()
def beyond(h0, tol=0.0):
    def f(r):
        w = r.orH - r.orL; s = set()
        if r.orH >= r[f"pH{h0}"] - tol * w: s.add(1)
        if r.orL <= r[f"pL{h0}"] + tol * w: s.add(-1)
        return s
    return f
both = lambda r: {1, -1}
if __name__ == "__main__":
    print("| Variante (simulée comme le script : un seul côté si filtre) | Trades | Stops pleins | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
    print("|---|---|---|---|---|---|---|---|---|")
    line("v3", run_allow(both))
    line("v3 + RSI (option actuelle)", run_allow(rsi))
    for h0, lab in ((0.5, "9:00"), (1.0, "8:30"), (1.5, "8:00")):
        line(f"v3 + range de 9:30 qui dépasse l'extrême {lab}-9:30 du même côté", run_allow(beyond(h0)))
        line(f"v3 + … ou s'en approche à 0,5 range", run_allow(beyond(h0, 0.5)))
    for h0, lab in ((0.5, "9:00"), (1.5, "8:00")):
        line(f"RSI + extrême {lab}-9:30 dépassé", run_allow(lambda r, f=beyond(h0): rsi(r) & f(r)))
        line(f"RSI + extrême {lab}-9:30 dépassé ou à 0,5 range", run_allow(lambda r, f=beyond(h0, 0.5): rsi(r) & f(r)))
