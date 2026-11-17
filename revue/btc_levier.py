import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import btc_backtest as BT
from btc_backtest import Frais
import btc
B = BT.charger(); E = btc.elements(B)
pos = btc.position(E, **btc.FINAL)
print("Levier (montage perpétuel dès ×2 ; avant 2020, les achats en perpétuel paient 10 %/an de financement, hypothèse)")
for L in range(1, 11):
    out = []
    for (a, b), stop in [(("2012-07-01", "2026-11-14"), True), (("2018-01-01", "2026-11-14"), True), (("2022-01-01", "2026-11-14"), True), (("2018-01-01", "2026-11-14"), False)]:
        r = BT.simuler(pos, B, levier=L, debut=a, fin=b, stop_protection=stop, F=Frais(fund_avant2020=0.10 if L > 1 else 0.0))
        m = BT.mesures(r["eq"])
        txt = "RUINE" if m["fin"] == 0 or r["liquidations"] else f"{m['cagr']:+.0%} Sh {m['sharpe']:.2f} dd {m['mdd']:.0%}"
        txt += f" st{r['stops']}" + (" COUPÉ" if r["arrete"] else "")
        out.append(txt)
    print(f"×{L:<2} 2012-26: {out[0]:34s} | 2018-26: {out[1]:34s} | 2022-26: {out[2]:34s} | 2018-26 sans stop: {out[3]}")

print("\nSans coupe-circuit (comme profils.py), achats en perpétuel payant 10 %/an avant 2020 :")
for L in [1, 2, 3, 4, 5, 7, 10]:
    o = []
    for a in ["2012-07-01", "2018-01-01", "2022-01-01"]:
        r = BT.simuler(pos, B, levier=L, debut=a, fin="2026-11-14", coupe=0, F=Frais(fund_avant2020=0.10 if L > 1 else 0))
        m = BT.mesures(r["eq"])
        o.append(("RUINE" if r["liquidations"] or m["fin"] == 0 else f"{m['cagr']:+.0%} Sh {m['sharpe']:.2f} dd {m['mdd']:.0%}") + f" st{r['stops']}")
    rc = BT.simuler(pos, B, levier=L, debut="2018-01-01", fin="2026-11-14", F=Frais(fund_avant2020=0.10 if L > 1 else 0))
    eq = rc["eq"]; arr = eq.index[eq.diff().fillna(1).ne(0)][-1].date() if rc["arrete"] else "jamais"
    print(f"×{L:<2} 2012-26: {o[0]:30s} | 2018-26: {o[1]:30s} | 2022-26: {o[2]:30s} | arrêt par le coupe-circuit (départ 2018) : {arr}")
