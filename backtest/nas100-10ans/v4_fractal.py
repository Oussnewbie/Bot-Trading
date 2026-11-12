import os, sys; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
T = pd.read_pickle("sl_table.pkl")
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York"); T["tr"] = T.t < SPLIT
X0 = pd.read_pickle("prevday_trades.pkl"); T["bars"] = X0.loc[T.idx, "bars"].values
def st(r):
    eq = r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max(); s = w = 0
    for v in r: s = s + 1 if v < -0.05 else 0; w = max(w, s)
    return dd, w
def line(lab, m):
    K = T[m]; O = T[~m]; dd, w = st(K.r); yrs = K.groupby(K.t.dt.year).r.sum()
    print(f"| {lab} | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.tr].r.mean():+.3f} / {K[~K.tr].r.mean():+.3f} | {K.r.sum():+.0f}R | -{dd:.0f}R / {w} | {(yrs>0).sum()}/{len(yrs)} | {len(O)} retirés : {O[O.tr].r.mean():+.2f} / {O[~O.tr].r.mean():+.2f} |")
print("| Filtre (trade gardé si…) | Trades | Stops | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + | Trades retirés : R moyen 2018-22 / 2022-26 |")
print("|---|---|---|---|---|---|---|---|---|")
line("v3 sans filtre", T.r == T.r)
print("| *La cassure sort-elle déjà d'un range plus grand ?* |||||||||")
for nm, lab in [("PM", "range de pré-ouverture 8:00-9:30"), ("ON", "range de la nuit 18:00-9:30"), ("PD", "range de la veille"), ("sw_M15", "dernier pivot M15"), ("sw_H1", "dernier pivot H1"), ("sw_H4", "dernier pivot H4"), ("sw_D1", "dernier pivot D1")]:
    c = f"room_{nm}"
    line(f"entrée au-delà du {lab}", T[c] <= 0)
    line(f"… ou à moins de 0,5R de lui", T[c] <= 0.5)
print("| *Obstacle juste devant (plus proche niveau parmi pré-ouverture, nuit, veille, clôture de la veille, semaine)* |||||||||")
for x in (0.25, 0.5, 1.0, 1.5):
    line(f"pas de niveau à moins de {x}R devant", T.room_min >= x)
lv = T[[c for c in ("room_PM", "room_ON", "room_PD", "room_sw_H1", "room_sw_H4") ]]
T["n_broken"] = (lv <= 0).sum(axis=1)
for n in range(0, 6):
    m = T.n_broken == n
    K = T[m]
    print(f"| {n} des 5 niveaux (pré-ouverture, nuit, veille, pivot H1, pivot H4) déjà dépassés | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.tr].r.mean():+.3f} / {K[~K.tr].r.mean():+.3f} | {K.r.sum():+.0f}R | | | |")
print("| *Structure (plus hauts / plus bas) dans le sens du trade* |||||||||")
for nm in ("M15", "H1", "H4", "D1"):
    for v, lab in ((1, "haussière dans le sens"), (-1, "contraire")):
        K = T[T[f"st_{nm}"] == v]
        print(f"| structure {nm} {lab} | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.tr].r.mean():+.3f} / {K[~K.tr].r.mean():+.3f} | {K.r.sum():+.0f}R | | | |")
for n in range(0, 5):
    K = T[T.align_n == n]
    print(f"| {n} unités de temps sur 4 alignées avec le trade | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.tr].r.mean():+.3f} / {K[~K.tr].r.mean():+.3f} | {K.r.sum():+.0f}R | | | |")
for n in range(0, 5):
    K = T[T.contra_n == n]
    print(f"| {n} unités de temps sur 4 contre le trade | {len(K)} | {100*K.stop.mean():.0f} % | {K.r.mean():+.3f} | {K[K.tr].r.mean():+.3f} / {K[~K.tr].r.mean():+.3f} | {K.r.sum():+.0f}R | | | |")
T.to_pickle("sl_table2.pkl")
