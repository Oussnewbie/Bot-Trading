import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import v4_filtres as slallow
from v4_filtres import F, run_allow, G
from v4_sim import SPLIT
mins, BH, BL, cal = G["mins"], G["BH"], G["BL"], G["cal"]
atr = F.atrd.values
r830 = []
for n, i in enumerate(F.index):
    j = i - 12  # bougie de 8:30 (12 bougies avant 9:30)
    r830.append((BH[j] - BL[j]) / F.atrd.iloc[n] if mins[j] == 510 and cal[j] == cal[i] else np.nan)
F["r830"] = r830
tr_days = F.day < pd.Timestamp("2022-09-01")
med830 = F.loc[tr_days, "r830"].median()
FILT = {
 "RSI": lambda r: {1} if r.m5_rsi > 0 else {-1} if r.m5_rsi < 0 else set(),
 "Ext9h": slallow.beyond(0.5),
 "Gap": lambda r: {1} if r.gap > 0 else {-1} if r.gap < 0 else set(),
 "PasMercredi": lambda r: set() if pd.Timestamp(r.day).dayofweek == 2 else {1, -1},
 "8h30calme": lambda r: {1, -1} if (np.isfinite(r.r830) and r.r830 <= med830) else set(),
}
names = list(FILT)
rows = []
ndays_tr = tr_days.sum(); ndays_te = (~tr_days).sum()
for nb in range(0, len(names) + 1):
    for combo in itertools.combinations(names, nb):
        for only935 in (False, True):
            def allow(r, c=combo):
                s = {1, -1}
                for nm in c: s = s & FILT[nm](r)
                return s
            X = run_allow(allow, {"cutoff": 580} if only935 else {})
            if only935: pass
            a, b = X[X.t < SPLIT], X[X.t >= SPLIT]
            rows.append(dict(combo="+".join(combo) + (" +9h35" if only935 else "") or "v3", n_tr=len(a), n_te=len(b),
                             freq=len(X) / len(F), rA=a.r.mean(), rB=b.r.mean(), totA=a.r.sum(), totB=b.r.sum()))
R = pd.DataFrame(rows)
R.loc[R.combo == "", "combo"] = "v3"
R.to_pickle("v4_combos.pkl")
pd.set_option("display.width", 250)
print("combinaisons testées :", len(R))
ok = R[R.freq >= 0.5]
print("dont au moins 1 trade tous les 2 jours :", len(ok))
print("\nCorrélation (rang) entre le R/trade 2018-22 et le R/trade 2022-26 des combinaisons :", round(ok.rA.rank().corr(ok.rB.rank()), 2))
print("\n=== Top 10 choisies sur 2018-22 seulement, et ce qu'elles ont fait ensuite ===")
print(ok.sort_values("rA", ascending=False).head(10).round(3).to_string(index=False))
print("\n=== Références ===")
print(R[R.combo.isin(["v3", "RSI", "Ext9h", "RSI+Ext9h"])].round(3).to_string(index=False))
print("\n=== Effet moyen de chaque filtre (ajouté à n'importe quelle combinaison) ===")
for nm in names + ["9h35"]:
    w = ok[ok.combo.str.contains(nm)]; wo = ok[~ok.combo.str.contains(nm)]
    print(f"{nm:12s} 2018-22 {w.rA.mean()-wo.rA.mean():+.3f}R   2022-26 {w.rB.mean()-wo.rB.mean():+.3f}R")
