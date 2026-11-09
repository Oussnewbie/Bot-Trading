import itertools, sys, json
import multiprocessing as mp
import sim
from sim import load, run, summary
TICKS = {"NQ": 0.25, "ES": 0.25, "YM": 1.0, "RTY": 0.1, "GC": 0.1, "6E": 0.00005}
D = {}
def init():
    for k in TICKS:
        D[k] = load(f"data/{k}.csv")
BIAS = {"none": dict(bias="none"), "d1": dict(bias="d1", use="with"), "d1x": dict(bias="d1", use="against"),
        "h1x": dict(bias="h1", use="against"), "h1": dict(bias="h1", use="with"), "h4": dict(bias="h4", use="with")}
def grid():
    for conf, cm in [("choch", 10), ("choch", 20), ("reclose", 3), ("reclose", 6)]:
        for disp, consume, entry, b, pd, pools in itertools.product((0.0, 0.3), (True, False), ("fvg", "mid"),
                                                                    BIAS, (True, False), ("asia", "all")):
            yield dict(conf=conf, confMax=cm, disp=disp, consume=consume, entry=entry, biasK=b, pd=pd,
                       poolsK=pools)
def cfg_of(g):
    c = dict(conf=g["conf"], confMax=g["confMax"], disp=g["disp"], consume=g["consume"], entry=g["entry"],
             pd=g["pd"], pools=("asia",) if g["poolsK"] == "asia" else ("asia", "pd", "lon"),
             maxTrades=3, maxLoss=2, minStop=1.0, rr=2.0, ny=True)
    c.update(BIAS[g["biasK"]])
    return c
def work(g):
    out = dict(g)
    c = cfg_of(g)
    for k in TICKS:
        sim.SLIP = 2 * TICKS[k]
        tr, st, nd = run(D[k], c)
        s = summary(tr, nd)
        half = len(D[k]) // 2
        cut = D[k].index[half]
        r1 = [t["rr"] for t in tr if t["tsig"] < cut]
        r2 = [t["rr"] for t in tr if t["tsig"] >= cut]
        out[k] = dict(n=s.get("n", 0), exp=s.get("exp", 0.0), total=s.get("total", 0.0), dd=s.get("dd", 0.0),
                      worst=s.get("worst", 0), pd=s.get("perDay", 0.0), h1=sum(r1), h2=sum(r2))
    return out
if __name__ == "__main__":
    gs = list(grid())
    with mp.Pool(4, initializer=init) as p:
        res = p.map(work, gs, chunksize=8)
    json.dump(res, open("grid.json", "w"))
    print(len(res))
