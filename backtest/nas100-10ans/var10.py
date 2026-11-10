import sys
sys.path.insert(0, ".")
import multiprocessing as mp, numpy as np, pandas as pd
import sim
from sim import run, summary
from load10 import load10
from run10 import F
G = {}
def init():
    sim.SLIP = 0.1
    b, a = load10()
    G["b"] = b[b.index >= "2018-05-01"]; G["a"] = a[a.index >= "2018-05-01"]
def work(job):
    label, cfg, spread = job
    tr, st, nd = run(G["b"], cfg, ask=G["a"] if spread else None)
    s = summary(tr, nd)
    r = pd.Series([t["rr"] for t in tr], index=[t["tsig"] for t in tr])
    tr1 = r[r.index < "2022-09-01"]; tr2 = r[r.index >= "2022-09-01"]
    yrs = r.groupby(r.index.year).sum()
    return (f"| {label} | {s['n']} | {s['win']:.0f} % | {s['exp']:+.2f}R | {s['total']:+.0f}R | {s['pf']:.2f} | "
            f"-{s['dd']:.0f}R / {s['worst']} | {tr1.mean():+.2f} / {tr2.mean():+.2f} | {(yrs > 0).sum()}/{len(yrs)} |")
JOBS = [
 ("v2 sans spread (bid seul)", F, False),
 ("v2 avec spread", F, True),
 ("reclôture au lieu de CHoCH", {**F, "conf": "reclose", "confMax": 6}, True),
 ("CHoCH 6 bougies", {**F, "confMax": 6}, True),
 ("CHoCH 20 bougies", {**F, "confMax": 20}, True),
 ("déplacement 0,5 ATR", {**F, "disp": 0.5}, True),
 ("entrée FVG", {**F, "entry": "fvg"}, True),
 ("entrée clôture (au marché)", {**F, "entry": "close"}, True),
 ("sans premium/discount", {**F, "pd": False}, True),
 ("objectif 2R fixe", {**F, "tgt": "R"}, True),
 ("objectif 3R fixe", {**F, "tgt": "R", "rr": 3.0}, True),
 ("objectif 1R fixe", {**F, "tgt": "R", "rr": 1.0}, True),
 ("Londres seul", {**F, "ny": False, "pm": False}, True),
 ("NY matin seul", {**F, "lonOff": True}, True),
 ("poches Asie seules", {**F, "pools": ("asia",)}, True),
 ("biais journalier, dans le sens", {**F, "bias": "d1"}, True),
 ("biais journalier, contre", {**F, "bias": "d1", "use": "against"}, True),
 ("biais H4, dans le sens", {**F, "bias": "h4"}, True),
 ("biais H4, contre", {**F, "bias": "h4", "use": "against"}, True),
 ("biais H1, dans le sens", {**F, "bias": "h1"}, True),
 ("biais H1, contre", {**F, "bias": "h1", "use": "against"}, True),
 ("Asie large seulement", {**F, "asiaMin": 1.0}, True),
 ("midnight open", {**F, "mo": True}, True),
 ("stop min 2 ATR", {**F, "minStop": 2.0}, True),
 ("swings M5 de 3", {**F, "swLen": 3}, True),
 ("poche consommée hors KZ", {**F, "consume": True}, True),
]
if __name__ == "__main__":
    with mp.Pool(4, initializer=init) as p:
        out = p.map(work, JOBS, chunksize=1)
    print("| Variante | Trades | Gagnants | Espérance | Total | PF | DD / série | 2018-22 / 2022-26 | Années + |")
    print("|---|---|---|---|---|---|---|---|---|")
    print("\n".join(out))
