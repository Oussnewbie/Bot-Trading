import sim, collections
from sim import load, run, summary, fmt_row
T = {"NQ": 0.25, "ES": 0.25, "YM": 1.0, "RTY": 0.1, "GC": 0.1, "6E": 0.00005}
D = {k: load(f"data/{k}.csv") for k in T}
B = dict(conf="choch", confMax=10, disp=0.0, consume=False, entry="mid", pd=True, bias="none",
         pools=("asia", "pd", "lon"), maxTrades=3, maxLoss=2, minStop=1.0, rr=2.0, ny=True)
def agg(cfg, label, show=False):
    allr = []; nd = 0; per = {}
    bysess = collections.defaultdict(list); bykind = collections.defaultdict(list)
    for k in T:
        sim.SLIP = 2 * T[k]
        tr, st, n = run(D[k], cfg); nd = n
        per[k] = summary(tr, n)
        for t in tr:
            allr.append(t); bysess[t["sess"]].append(t["rr"]); bykind[t["kind"]].append(t["rr"])
    s = summary(sorted(allr, key=lambda t: t["tsig"]), nd)
    print(fmt_row(label, s) + " " + " ".join(f"{k}:{per[k].get('total',0):+.1f}/{per[k].get('n',0)}" for k in T))
    if show:
        for k, v in sorted(bysess.items()):
            print("   séance", ["Londres", "NY matin", "NY aprem"][k], len(v), f"{sum(v):+.1f}R")
        for k, v in sorted(bykind.items()):
            print("   poche", ["Asie", "Veille", "Londres", "NY matin"][k], len(v), f"{sum(v):+.1f}R")
print("| Variante (6 marchés cumulés) | Trades | /jour | Gagnants | Espérance | Total | PF | DD / pire série |")
print("|---|---|---|---|---|---|---|---|")
agg(dict(), "v1 tes réglages")
agg(B, "Meilleure v2", show=True)
for lab, ch in [("objectif 1.5R", dict(rr=1.5)), ("objectif 3R", dict(rr=3.0)), ("BE à 1R", dict(be=1.0)),
                ("objectif liquidité", dict(tgt="liq")), ("confirmation 6 bougies", dict(confMax=6)),
                ("confirmation 15", dict(confMax=15)), ("swings 3", dict(swLen=3)), ("+ après-midi", dict(pm=True, pools=("asia","pd","lon","ny"))),
                ("Londres seul", dict(ny=False)), ("sans NY? poches Asie seules", dict(pools=("asia",))),
                ("Asie + veille", dict(pools=("asia","pd"))), ("biais D1 dans le sens", dict(bias="d1")),
                ("biais D1 contre", dict(bias="d1", use="against")), ("biais H4", dict(bias="h4")),
                ("biais H1 contre", dict(bias="h1", use="against")), ("stop min 0.5 ATR", dict(minStop=0.5)),
                ("stop min 1.5 ATR", dict(minStop=1.5)), ("pertes max 1/jour", dict(maxLoss=1)), ("4 trades/jour", dict(maxTrades=4, maxLoss=3)),
                ("entrée FVG", dict(entry="fvg")), ("entrée clôture", dict(entry="close"))]:
    agg({**B, **ch}, "  " + lab)
