import sys, time
sys.path.insert(0, ".")
import numpy as np, pandas as pd
import sim
from sim import run, summary
from load10 import load10
sim.SLIP = 0.1
b, a = load10()
START = "2018-05-01"
b = b[b.index >= START]; a = a[a.index >= START]
F = dict(conf="choch", confMax=10, disp=0.0, consume=False, entry="mid", pd=True, bias="none",
         pools=("asia", "pd", "lon", "ny"), maxTrades=2, maxLoss=3, minStop=1.0, rr=2.0, ny=True, pm=True, tgt="liq")
def rep(label, cfg, detail=False):
    t0 = time.time()
    tr, st, nd = run(b, cfg, ask=a)
    s = summary(tr, nd)
    r = pd.Series([t["rr"] for t in tr], index=[t["tsig"] for t in tr])
    yrs = r.groupby(r.index.year).sum()
    pos_y = (yrs > 0).sum()
    line = (f"| {label} | {s['n']} | {s['perDay']:.2f} | {s['win']:.0f} % | {s['exp']:+.2f}R | {s['total']:+.0f}R | "
            f"{s['pf']:.2f} | -{s['dd']:.0f}R / {s['worst']} | {pos_y}/{len(yrs)} |")
    print(line, flush=True)
    if detail:
        print("   par année :", {int(k): round(v, 1) for k, v in yrs.items()})
        print("   par année (trades) :", r.groupby(r.index.year).size().to_dict())
        for key, names in [("sess", ["Londres", "NY matin", "NY aprem"]), ("kind", ["Asie", "Veille", "Londres", "NY matin"])]:
            g = collections.defaultdict(list)
            for t in tr:
                g[t[key]].append(t["rr"])
            print("  ", key, {names[k]: (len(v), round(sum(v), 1), round(np.mean(v), 2)) for k, v in sorted(g.items())})
        print("   longs", round(sum(t["rr"] for t in tr if t["dir"] == 1), 1), "shorts", round(sum(t["rr"] for t in tr if t["dir"] == -1), 1))
        print("   sorties", collections.Counter(t["why"] for t in tr))
        print("   stop moyen en points", round(np.mean([t["risk"] for t in tr]), 1), "par année", {int(k): round(v, 1) for k, v in pd.Series([t["risk"] for t in tr], index=r.index).groupby(r.index.year).mean().items()})
    return tr
import collections
if __name__ == "__main__":
    print("| Variante | Trades | /jour | Gagnants | Espérance | Total | PF | DD / pire série | Années + |")
    print("|---|---|---|---|---|---|---|---|---|")
    rep("v2 actuelle", F, detail=True)
    rep("v1 (tes anciens réglages)", dict(maxTrades=2, maxLoss=3))
