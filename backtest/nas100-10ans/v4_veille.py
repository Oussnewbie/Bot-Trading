import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbx, orbv
fam.prep()
if os.path.exists("orb_features.pkl"):
    F = pd.read_pickle("orb_features.pkl")
else:
    F = orbx.features(); F.to_pickle("orb_features.pkl")
C = dict(cutoff=585, be=1.5)
X = orbv.run(F, C)
X["day"] = X.t.dt.tz_localize(None).dt.normalize()
X = X.merge(F[["day", "prevdir", "atrd", "gap", "o930", "pdh", "pdl", "m5_rsi"]], on="day", how="left")
X["pc"] = X.o930 - X.gap
X["body"] = X.prevdir / X.atrd                     # veille : (clôture - ouverture) / ATR jour
X["cloc"] = (X.pc - X.pdl) / (X.pdh - X.pdl)       # clôture de la veille dans son range (0 = plus bas, 1 = plus haut)
X["sens"] = np.where(np.sign(X.prevdir) == X.d, "même sens que la veille", "contre la veille")
X.to_pickle("prevday_trades.pkl")
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
def agg(g):
    tr, te = g[g.t < SPLIT].r, g[g.t >= SPLIT].r
    return pd.Series(dict(trades=len(g), gagnants=f"{100*(g.r>0.05).mean():.0f} %", par_trade=round(g.r.mean(), 3),
                          avant_2022=round(tr.mean(), 3), apres_2022=round(te.mean(), 3), total=round(g.r.sum())))
print("v3 :", len(X), "trades,", round(X.r.mean(), 3), "R/trade")
bins = [-9, -1, -0.5, 0, 0.5, 1, 9]
labs = ["veille baisse > 1 ATR", "baisse 0,5-1 ATR", "baisse < 0,5 ATR", "hausse < 0,5 ATR", "hausse 0,5-1 ATR", "veille hausse > 1 ATR"]
X["veille"] = pd.cut(X.body, bins, labels=labs)
X["cote"] = np.where(X.d == 1, "ACHAT", "VENTE")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
print("\n=== Corps de la veille (séance 9:30-16:00) x sens du trade ===")
print(X.groupby(["veille", "cote"], observed=True).apply(agg, include_groups=False))
print("\n=== Trade dans le sens de la veille ou contre (toutes tailles) ===")
print(X.groupby("sens").apply(agg, include_groups=False))
big = X[X.body.abs() > 1]
print("\n=== Veilles > 1 ATR seulement ===")
print(big.groupby("sens").apply(agg, include_groups=False))
X["cl"] = pd.cut(X.cloc, [-.01, .2, .8, 1.01], labels=["veille clôt près du bas", "milieu", "veille clôt près du haut"])
print("\n=== Clôture de la veille dans son range x sens du trade ===")
print(X.groupby(["cl", "cote"], observed=True).apply(agg, include_groups=False))
print("\nPart des achats après une veille baissière > 1 ATR :", int(((X.body < -1) & (X.d == 1)).sum()), "sur", int((X.body < -1).sum()), "trades")
