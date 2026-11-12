"""v5, série 7 : pourquoi 2015-2017 perd. Coût du spread par rapport au range, volatilité, résultat sans spread."""
import numpy as np, pandas as pd
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all
D = L.prep(); G = L.G
D["yr"] = pd.DatetimeIndex(D.day).year
D["cost"] = D.spread / D.orw
D["px"] = D.orC
D["atr_pct"] = 100 * D.atrd / D.px
D["or_pct"] = 100 * D.orw / D.px
print("Par année (médianes des jours) : range de 9:30 en points, spread à 9:35, coût du spread en part du risque, ATR jour en % du prix")
print(D.groupby("yr").agg(jours=("i", "size"), prix=("px", "median"), range_pts=("orw", "median"), spread=("spread", "median"), cout_R=("cost", "median"),
                          atr_pct=("atr_pct", "median"), range_pct=("or_pct", "median")).round(3).to_string())
# résultat sans spread : on rejoue avec l'ask égal au bid
real = {k: G[k] for k in ("AO", "AH", "AL", "AC")}
X4 = run({}, f_v4); X3 = run({}, f_all)
for a, b in (("AO", "BO"), ("AH", "BH"), ("AL", "BL"), ("AC", "BC")): G[a] = G[b]
s0 = L.SLIP; L.SLIP = 0.0
Y4 = run({}, f_v4); Y3 = run({}, f_all)
G.update(real); L.SLIP = s0
print("\nR par trade, avec spread réel / sans spread ni glissement :")
for nm, X, Y in (("v3", X3, Y3), ("v4", X4, Y4)):
    for per in ("B", "train", "A"):
        a, b = stats(X, per), stats(Y, per)
        print(f"  {nm} {per:5s} : {a['mean']:+.3f} / {b['mean']:+.3f}  (coût {b['mean']-a['mean']:.3f}R par trade, {a['n']} trades)")
# l'avantage dépend-il de la volatilité ? v3 et v4, toutes périodes, par tranche d'ATR jour en % du prix et de coût
for nm, X in (("v3", X3), ("v4", X4)):
    Z = X.merge(D[["i", "atr_pct", "cost", "or_pct", "yr"]], on="i")
    print(f"\n{nm} — par tranche d'ATR jour (% du prix), toutes périodes :")
    Z["b"] = pd.cut(Z.atr_pct, [0, 0.7, 0.9, 1.1, 1.4, 1.8, 2.5, 10])
    g = Z.groupby(["b", "per"], observed=True).r.agg(["size", "mean"]).unstack("per").round(3); print(g.to_string())
    print(f"{nm} — par tranche de coût du spread (part du risque) :")
    Z["c"] = pd.cut(Z.cost, [0, 0.02, 0.03, 0.045, 0.06, 0.08, 0.12, 5])
    g = Z.groupby(["c", "per"], observed=True).r.agg(["size", "mean"]).unstack("per").round(3); print(g.to_string())
    print(f"{nm} — par tranche de range de 9:30 (% du prix) :")
    Z["o"] = pd.cut(Z.or_pct, [0, 0.10, 0.15, 0.20, 0.27, 0.35, 0.5, 5])
    g = Z.groupby(["o", "per"], observed=True).r.agg(["size", "mean"]).unstack("per").round(3); print(g.to_string())
