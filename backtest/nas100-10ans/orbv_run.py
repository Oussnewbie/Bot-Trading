import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbv
fam.prep()
F = pd.read_pickle("orb_features.pkl")
B = orbv.run(F, {})
B.to_pickle("orb_base_trades.pkl")
L, W = B[B.r < -0.05], B[B.r > 0.05]
print(f"BASE : {len(B)} trades, {len(W)} gagnants, {len(L)} perdants, {len(B)-len(W)-len(L)} à ~0 ; total {B.r.sum():+.0f}R")
print("\n--- Anatomie des perdants ---")
print(f"stoppés sur la bougie d'entrée : {100*(L.bars==0).mean():.0f} %, en 15 min : {100*(L.bars<=3).mean():.0f} %, en 1 h : {100*(L.bars<=12).mean():.0f} %, après 1 h : {100*(L.bars>12).mean():.0f} %")
print(f"faux départs des deux côtés dans la même bougie : {L.both.sum()} perdants ({100*L.both.mean():.0f} %)")
print("gain maximal atteint avant le stop (MFE) — part des perdants qui ont d'abord atteint : " +
      ", ".join(f"+{x}R {100*(L.mfe>=x).mean():.0f} %" for x in (0.25, 0.5, 1, 1.5, 2)))
print("perdants non stoppés mais sortis à 15:50 en perte :", int((L.bars > 0).sum() - (L.r <= -0.95).sum()), "dont perte moyenne", round(L[L.r > -0.95].r.mean(), 2), "R")
print("\n--- Anatomie des gagnants ---")
print("recul maximal avant de gagner (MAE) — part des gagnants descendus jusqu'à : " +
      ", ".join(f"-{x}R {100*(W.mae>=x).mean():.0f} %" for x in (0.25, 0.5, 0.75, 0.9)))
print("gagnants : part sortie à 15:50 :", f"{100*(W.bars>0).mean():.0f} %", "; gain médian", round(W.r.median(), 2), "R ; part > 3R :", f"{100*(W.r>3).mean():.0f} %", "; somme des gagnants > 3R :", round(W[W.r>3].r.sum()), "R")
print("\n--- Résultat selon la taille du range d'ouverture (en ATR jour) ---")
q = pd.qcut(B.or_atr, 5)
print(B.groupby(q, observed=True).r.agg(["count", "mean", "sum"]).round(2))
print("\n--- Résultat selon l'heure de la cassure ---")
hh = B.t.dt.hour * 60 + B.t.dt.minute
print(B.groupby(pd.cut(hh, [0, 580, 600, 630, 660, 720]), observed=True).r.agg(["count", "mean", "sum"]).round(2))
