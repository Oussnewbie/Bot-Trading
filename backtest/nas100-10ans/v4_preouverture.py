import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import numpy as np, pandas as pd, fam
fam.prep(); G = fam.G
T = pd.read_pickle("sl_table2.pkl")
BH, BL, AO, BO = G["BH"], G["BL"], G["AO"], G["BO"]
tn = G["t"].as_unit("ns").asi8
F = pd.read_pickle("orb_features.pkl").reset_index()
T = T.merge(F[["day", "i"]], on="day")
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
def room(row, h0):
    i, k, d = int(row.i), int(row.k), int(row.d)
    a = np.searchsorted(tn, tn[i] - int(h0 * 3600e9))
    if i - a < 2: return np.nan
    lv = BH[a:i].max() if d == 1 else BL[a:i].min()
    orH, orL = BH[i], BL[i]
    return ((lv - (orH if d == 1 else orL)) * d) / (orH - orL)   # en R, depuis le niveau de l'ordre (>0 : extrême de pré-ouverture encore devant)
def show(lab, K):
    yrs = K.groupby(K.t.dt.year).r.sum().round(0).astype(int).tolist()
    eq = K.r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    print(f"| {lab} | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.t<SPLIT].r.mean():+.3f} / {K[K.t>=SPLIT].r.mean():+.3f} | {K.r.sum():+.0f}R | -{dd:.0f}R | {yrs} |")
print("| Fenêtre de pré-ouverture (extrême dépassé par le range de 9:30) | Trades gardés | Stops | Par trade | 2018-22 / 2022-26 | Total | Pire baisse | R par année 2018…2026 |")
print("|---|---|---|---|---|---|---|---|")
show("aucun filtre", T)
for h0, lab in [(0.25, "9:15-9:30"), (0.5, "9:00-9:30"), (1.0, "8:30-9:30"), (1.5, "8:00-9:30"), (2.5, "7:00-9:30"), (5.5, "4:00-9:30"), (15.5, "18:00-9:30 (nuit)")]:
    T[f"pm{h0}"] = [room(r, h0) for r in T.itertuples()]
    show(f"{lab} : range de 9:30 déjà au-delà", T[T[f"pm{h0}"] <= 0])
    show(f"{lab} : … ou extrême à moins de 0,5R devant", T[T[f"pm{h0}"] <= 0.5])
T.to_pickle("sl_table3.pkl")
c = "pm1.5"
print("\nCorrélations du filtre 8:00-9:30 avec :")
m = T[c] <= 0
for v in ("or_dir", "m5_rsi_dir", "or_cloc_dir", "or_atr", "pm_rng_atr", "gap_dir", "pm_move_dir", "st_D1", "room_sw_H4"):
    print(f"  {v}: gardés {T[m][v].mean():+.2f} / retirés {T[~m][v].mean():+.2f}")
print()
show("RSI dans le sens (option actuelle)", T[T.m5_rsi_dir == 1])
show("pré-ouverture 8:00 dépassée ou < 0,5R + RSI dans le sens", T[(T[c] <= 0.5) & (T.m5_rsi_dir == 1)])
show("pré-ouverture 8:00 dépassée ou < 0,5R, RSI contraire", T[(T[c] <= 0.5) & (T.m5_rsi_dir != 1)])
show("pré-ouverture 8:00 à plus de 0,5R devant, RSI dans le sens", T[(T[c] > 0.5) & (T.m5_rsi_dir == 1)])
show("bougie de 9:30 dans le sens", T[T.or_dir == 1])
show("pré-ouverture 8:00 < 0,5R + bougie de 9:30 dans le sens", T[(T[c] <= 0.5) & (T.or_dir == 1)])
print("\nAprès 'pré-ouverture < 0,5R' : longs / courts")
for d in (1, -1): show("achats" if d == 1 else "ventes", T[(T[c] <= 0.5) & (T.d == d)])
