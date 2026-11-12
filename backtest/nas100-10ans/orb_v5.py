"""ORB v5 = filtres RSI14 M5 + élan 9:00-9:30, et une pyramide : quand une bougie M5 clôture à +2R ou plus,
ajout d'une unité au marché et stop de l'ensemble à 1R sous le prix de l'ajout (donc au moins à +1R). Même logique que pine/ORB-v5.pine et mt5/ORB-v5.mq5.

Réglages choisis sur mai 2018 -> août 2022 seulement (v5_exp1.py à v5_exp6.py), puis vérifiés sur septembre 2022 ->
octobre 2026, puis sur janvier 2015 -> avril 2018, période jamais regardée avant que la v5 soit figée."""
import numpy as np, pandas as pd
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all

V5 = dict(cadd=[(2.0, 1.0, ("rel", 1.0, 1.0))])   # clôture ≥ +2R : +1 unité, stop de l'ensemble à 1R sous le prix de l'ajout
PERS = [("B", "2015-01 → 2018-04 (jamais vue)"), ("train", "2018-05 → 2022-08 (choix)"), ("A", "2022-09 → 2026-10 (vérif.)")]

def capital(X, risk):
    eq = peak = 1.0; mdd = 0
    for r in X.r:
        eq *= 1 + risk / 100 * r; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
    yrs = (X.t.iloc[-1] - X.t.iloc[0]).days / 365.25
    return eq, 100 * (eq ** (1 / yrs) - 1), 100 * mdd, yrs

if __name__ == "__main__":
    L.prep()
    # deux points de comparaison : "v3" = sans filtre ni pyramide, "v4" = les filtres de la v5 sans la pyramide
    R = {"v3": run({}, f_all), "v4": run({}, f_v4), "v5": run(V5, f_v4)}
    print('Légende : v3 = sans filtre ni pyramide ; v4 = filtres RSI + élan, sans pyramide ; v5 = filtres + pyramide')
    for per, lab in PERS + [(["B", "train", "A"], "TOUT : 2015-01 → 2026-10")]:
        print(f"\n### {lab}")
        print("| | Trades | Stops pleins | Gagnants | Par trade | Total | Pire baisse / série | t | Années + |"); print("|---|---|---|---|---|---|---|---|---|")
        for nm, X in R.items():
            s = stats(X, per)
            print(f"| {nm} | {s['n']} | {100*s['stop']:.0f} % | {100*s['win']:.0f} % | {s['mean']:+.3f}R | {s['tot']:+.0f}R | -{s['dd']:.0f}R / {s['streak']} | {s['t']:.2f} | {s['ypos']} |")
    X = R["v5"]
    print("\nv5, R par année :", X.groupby(X.t.dt.year).r.sum().round(0).astype(int).to_dict())
    print("v4, R par année :", R["v4"].groupby(R["v4"].t.dt.year).r.sum().round(0).astype(int).to_dict())
    M = R["v4"].merge(X, on="i", suffixes=("4", "5")); py = M[(M.r4 - M.r5).abs() > 1e-9]
    print(f"v5 : pyramide déclenchée sur {100 * len(py) / len(M):.0f} % des trades ; sur ces trades, {py.r4.mean():+.2f}R en v4 et {py.r5.mean():+.2f}R en v5 ; "
          f"{100 * (py.r5 < py.r4).mean():.0f} % finissent moins bien qu'en v4, {100 * (py.r5 <= 0.05).mean():.0f} % finissent à zéro ou moins")
    for nm in ("v4", "v5"):
        for risk in (0.25, 0.5, 1.0):
            eq, an, mdd, yrs = capital(R[nm], risk)
            print(f"{nm} à {risk} % de risque sur {yrs:.1f} ans : x{eq:.1f}, {an:.0f} % par an, pire baisse {mdd:.0f} %")
    for nm in ("v4", "v5"):
        Y = R[nm][R[nm].per != "B"]
        for risk in (0.5, 1.0):
            eq, an, mdd, yrs = capital(Y, risk)
            print(f"{nm} à {risk} % sur 2018-05 → 2026-10 ({yrs:.1f} ans) : x{eq:.1f}, {an:.0f} % par an, pire baisse {mdd:.0f} %")
    X.to_pickle("v5_trades.pkl")
