import sys
from sim import *
nq = load("data/NQ.csv"); es = load("data/ES.csv")
V2 = dict(pools=("asia","pd","lon"), conf="choch", confMax=10, disp=0.5, entry="fvg", pd=True,
          bias="d1", use="with", neutral="both", maxTrades=3, maxLoss=2, consume=True, minStop=1.0, rr=2.0)
variants = [
 ("v1 tes réglages", {}),
 ("v1 réglages d'origine (Londres seul, marge 20)", dict(confMax=3, minStop=0.5, limitBars=12, pad=20.0, ny=False, maxLoss=2)),
 ("v1 + biais H1 contre", dict(bias="h1", use="against")),
 ("v1 + biais journalier", dict(bias="d1")),
 ("v2 défaut", V2),
 ("v2 sans biais", {**V2, "bias":"none"}),
 ("v2 biais contre", {**V2, "use":"against"}),
 ("v2 biais H4", {**V2, "bias":"h4"}),
 ("v2 biais D1+H4", {**V2, "bias":"both"}),
 ("v2 biais H1", {**V2, "bias":"h1"}),
 ("v2 neutre = pas de trade", {**V2, "neutral":"skip"}),
 ("v2 reclôture au lieu de CHoCH", {**V2, "conf":"reclose", "confMax":6}),
 ("v2 sans déplacement", {**V2, "disp":0.0}),
 ("v2 entrée milieu bougie", {**V2, "entry":"mid"}),
 ("v2 entrée clôture", {**V2, "entry":"close"}),
 ("v2 sans premium/discount", {**V2, "pd":False}),
 ("v2 objectif liquidité", {**V2, "tgt":"liq"}),
 ("v2 BE à 1R", {**V2, "be":1.0}),
 ("v2 objectif 3R", {**V2, "rr":3.0}),
 ("v2 objectif 1.5R", {**V2, "rr":1.5}),
 ("v2 + après-midi", {**V2, "pm":True, "pools":("asia","pd","lon","ny")}),
 ("v2 Londres seul", {**V2, "ny":False}),
 ("v2 poches Asie seules", {**V2, "pools":("asia",)}),
 ("v2 Asie + veille", {**V2, "pools":("asia","pd")}),
 ("v2 swings 3", {**V2, "swLen":3}),
 ("v2 + SMT (ES)", {**V2, "smt":True}),
 ("v2 4 trades/jour", {**V2, "maxTrades":4}),
]
print("| Variante | Trades | /jour | Gagnants | Espérance | Total | PF | DD / pire série |")
print("|---|---|---|---|---|---|---|---|")
for name, cfg in variants:
    tr, stt, nd = run(nq, cfg, peer=es if cfg.get("smt") else None)
    print(fmt_row(name, summary(tr, nd)))
