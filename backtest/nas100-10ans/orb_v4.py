"""ORB v4 : v3 + filtre RSI14 M5 + filtre d'élan (la bougie de 9:30 dépasse l'extrême de 9:00-9:30 du même côté).
Même logique que pine/ORB-v4.pine : un ordre seulement du côté autorisé, annulé si l'autre côté du range est
touché d'abord ; ordres valables jusqu'à 9:45 ; stop au prix d'entrée dès +1,5R ; sortie à 15:50."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from v4_filtres import run_allow, rsi, beyond, both, F
from v4_sim import line, SPLIT

V4 = lambda r: rsi(r) & beyond(0.5)(r)

if __name__ == "__main__":
    print("| Version | Trades | Stops pleins | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
    print("|---|---|---|---|---|---|---|---|---|")
    line("v3", run_allow(both))
    line("v3 + RSI seul", run_allow(rsi))
    line("v3 + élan 9:00-9:30 seul", run_allow(beyond(0.5)))
    X = line("**v4** (RSI + élan)", run_allow(V4))
    yrs = (X.t.iloc[-1] - X.t.iloc[0]).days / 365.25
    print(f"\nv4 : {len(X) / yrs:.0f} trades par an, {len(X) / len(F):.2f} par jour de bourse")
    print("R par année :", X.groupby(X.t.dt.year).r.sum().round(0).astype(int).to_dict())
    for risk in (0.5, 1.0):
        eq = peak = 1.0; mdd = 0
        for r in X.r:
            eq *= 1 + risk / 100 * r; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
        print(f"capital à {risk} % de risque : x{eq:.2f} en {yrs:.1f} ans, {100*(eq**(1/yrs)-1):.0f} % par an, pire baisse {100*mdd:.0f} %")
