"""v5, série 9 : idée venue des trades d'octobre-novembre 2026 (les perdants avaient un RSI proche de 50).
Un RSI plus marqué à 9:30 (au moins 50 ± x) améliore-t-il la v5 ? Test sur les trois périodes."""
import numpy as np, pandas as pd
import v5_lab as L, orb_v5
from v5_lab import run, stats, f_ext
D = L.prep()
def f_rsi_x(x):
    def f(r):
        s = {1} if r.rsi > 50 + x else {-1} if r.rsi < 50 - x else set()
        return s & f_ext(r)
    return f
PERS = ("B", "train", "A")
print("| RSI à au moins | 2015-18 : trades | R/trade | total | 2018-22 : trades | R/trade | total | 2022-26 : trades | R/trade | total | TOUT : trades | R/trade | total | pire baisse | t |"); print("|" + "---|" * 15)
for x in (0, 3, 5, 8, 10, 12, 15, 20):
    X = run(orb_v5.V5, f_rsi_x(x)); cells = []
    for p in PERS:
        s = stats(X, p); cells.append(f"{s['n']} | {s['mean']:+.3f} | {s['tot']:+.0f}R")
    s = stats(X, list(PERS)); print(f"| 50 ± {x} | " + " | ".join(cells) + f" | {s['n']} | {s['mean']:+.3f} | {s['tot']:+.0f}R | -{s['dd']:.0f}R | {s['t']:.2f} |", flush=True)
# par tranche de force du RSI, v5, trois périodes
X = run(orb_v5.V5, L.f_v4).merge(D[["i", "rsi"]], on="i"); X["f"] = (X.rsi - 50).abs()
X["b"] = pd.cut(X.f, [0, 5, 10, 15, 20, 30, 50])
print("\nv5 par tranche d'écart du RSI à 50 (trades, R par trade) :")
print(X.groupby(["b", "per"], observed=True).r.agg(["size", "mean"]).unstack("per").round(3).to_string())
# pyramide stoppée : combien perd-on vraiment après l'ajout ?
P = run(orb_v5.V5, L.f_v4); Q = run({}, L.f_v4).merge(P, on="i", suffixes=("4", "5"))
py = Q[(Q.r4 - Q.r5).abs() > 1e-9]; st = py[py.why5 == "stop remonté"]
print(f"\nTrades pyramidés : {len(py)} ; stoppés au stop remonté : {len(st)} ; résultat de ceux-là : médiane {st.r5.median():+.2f}R, moyenne {st.r5.mean():+.2f}R, "
      f"pire {st.r5.min():+.2f}R, 10 % les pires sous {st.r5.quantile(0.1):+.2f}R")
