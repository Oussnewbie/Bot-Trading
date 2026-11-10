import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbv
fam.prep(); F = pd.read_pickle("orb_features.pkl")
Ftr = F[F.day < pd.Timestamp("2022-09-01")]; q80 = float(Ftr.or_atr.quantile(0.8))
FR = F[np.isfinite(F.m5_rsi)]
print("| Combinaison | Trades | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
print("|---|---|---|---|---|---|---|---|")
C = dict(cutoff=585, be=1.5)
for lab, p, FF in [("Base", {}, F),
                   ("Cassure avant 9:45 + stop à l'entrée dès +1,5R", C, F),
                   ("+ sortie si en perte après 1 h", {**C, "ts": 12, "tsr": 0.0}, F),
                   ("+ pas de trade si grand range", {**C, "maxor": q80}, F)]:
    orbv.line(lab, orbv.run(FF, p))
# RSI M5 filter on the first break (conservative: whipsaw days kept)
X = orbv.run(F, C)
X["day"] = X.t.dt.tz_localize(None).dt.normalize()
X = X.merge(F[["day", "m5_rsi"]], on="day", how="left")
keep = (np.sign(X.m5_rsi) == X.d) | X.both
orbv.line("Cassure avant 9:45 + stop à l'entrée dès +1,5R + RSI14 M5 dans le sens", X[keep])
B = orbv.run(F, C)
for risk in (0.5, 1.0):
    eq = 1.0; peak = 1.0; mdd = 0
    for r in B.r:
        eq *= 1 + risk / 100 * r; peak = max(peak, eq); mdd = max(mdd, 1 - eq / peak)
    yrs = (B.t.iloc[-1] - B.t.iloc[0]).days / 365.25
    print(f"Capital avec {risk} % de risque par trade (cassure avant 9:45 + stop à l'entrée dès +1,5R) : x{eq:.2f} en {yrs:.1f} ans, soit {100*(eq**(1/yrs)-1):.0f} % par an, pire baisse {100*mdd:.0f} %")
