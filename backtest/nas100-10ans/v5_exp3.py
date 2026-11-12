"""v5, série 3 (2018-22 seulement) : contexte du jour, par tranches, sur la v4 avec et sans pyramide."""
import numpy as np, pandas as pd
import v5_lab as L
from v5_lab import run, f_v4, f_all
D = L.prep(); G = L.G
PYR = dict(pyr=[(2.0, 1.0, 1.0)])
def table(P, filt):
    X = run(P, filt); X = X[X.per == "train"].merge(D, on="i", suffixes=("", "_d"))
    d = X.d
    X["gap_dir"] = X.gap * d
    X["gap_abs"] = X.gap.abs()
    X["rsi_str"] = (X.rsi - 50) * d
    X["ext_str"] = np.where(d == 1, X.orH - X.preH, X.preL - X.orL) / X.orw       # de combien le range dépasse 9:00-9:30
    X["pre_w"] = (X.preH - X.preL) / X.orw                                         # largeur 9:00-9:30 / range
    X["pm_w"] = (X.pmH - X.pmL) / X.orw
    X["or_a5"] = X.orw / X.atr5                                                    # range / ATR14 M5 d'avant l'ouverture
    X["cost"] = X.spread / X.orw                                                   # spread en part du risque
    X["or_cloc"] = np.where(d == 1, (X.orC - X.orL), (X.orH - X.orC)) / X.orw      # clôture de 9:30 vers le côté du trade
    X["or_body"] = (X.orC - X.orO) * d / X.orw
    X["pd_dir"] = (X.pdc - X.pdo) / X.atrd * d
    X["pd_pos"] = np.where(d == 1, (X.orC - X.pdl), (X.pdh - X.orC)) / (X.pdh - X.pdl)   # position dans le range de la veille, côté trade
    X["out_pd"] = np.where(d == 1, X.orH > X.pdh, X.orL < X.pdl).astype(int)
    X["dowf"] = X.dow
    return X
FE = ["gap_dir", "gap_abs", "rsi_str", "ext_str", "pre_w", "pm_w", "or_a5", "or_atr", "or_med", "cost", "or_cloc", "or_body", "pd_dir", "pd_pos", "prng", "nr", "rnk7", "out_pd", "dowf"]
A, B = table(PYR, f_v4), table({}, f_v4)
sd = A.r.std(); rows = []
for c in FE:
    v = A[c]
    if v.nunique() <= 7: b = v
    else: b = pd.qcut(v, 4, duplicates="drop")
    for lev, g in A.groupby(b, observed=True):
        rest = A[~A.index.isin(g.index)]
        z = (g.r.mean() - rest.r.mean()) / (sd * np.sqrt(1 / len(g) + 1 / len(rest)))
        g0 = B[B.index.isin(g.index)]
        rows.append(dict(var=c, tranche=str(lev), n=len(g), stops=round(100 * (g.r <= -0.9).mean()), R_pyr=round(g.r.mean(), 3), tot_pyr=round(g.r.sum()), R_sans=round(g0.r.mean(), 3), z=round(z, 2)))
R = pd.DataFrame(rows)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 300)
print("écart-type d'un trade pyramidé :", round(sd, 2), "R ;", len(A), "trades ;", len(R), "tranches testées (≈", round(len(R) * 0.05), "au-delà de |z|=2 par hasard)")
print(R.to_string(index=False))
