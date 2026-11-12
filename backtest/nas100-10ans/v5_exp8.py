"""v5, série 8 : robustesse hors échantillon. Gain de la pyramide (réglages voisins) et des filtres, période par période."""
import numpy as np, pandas as pd
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all, f_rsi, f_ext
L.prep()
PERS = ("B", "train", "A")
def row(lab, X, base=None):
    cells = []
    for p in PERS:
        s = stats(X, p)
        extra = "" if base is None else f" ({s['tot'] - stats(base, p)['tot']:+.0f})"
        cells.append(f"{s['n']} | {s['mean']:+.3f} | {s['tot']:+.0f}R{extra} | -{s['dd']:.0f}R | {s['t']:.2f}")
    s = stats(X, list(PERS)); print(f"| {lab} | " + " | ".join(cells) + f" | {s['tot']:+.0f}R | -{s['dd']:.0f}R | {s['t']:.2f} |", flush=True)
print("| | 2015-18 : trades | R/trade | total (vs sans pyramide) | pire baisse | t | 2018-22 : trades | R/trade | total | pire baisse | t | 2022-26 : trades | R/trade | total | pire baisse | t | TOUT : total | pire baisse | t |")
print("|" + "---|" * 19)
print("| *Filtres (sans pyramide)* |")
for lab, f in (("v3 : aucun filtre", f_all), ("RSI seul", f_rsi), ("élan seul", f_ext), ("v4 : RSI + élan", f_v4)):
    row(lab, run({}, f))
print("| *Pyramide à la clôture, filtres v4* |")
base = run({}, f_v4)
for T, s, lock in ((2.0, 1, 1.0), (1.5, 1, 1.0), (2.0, 1, 0.5), (2.0, 1, 0.0), (2.5, 1, 1.0), (3.0, 1, 1.0), (2.0, 0.5, 1.0), (2.0, 2, 1.0)):
    row(f"clôture ≥ +{T}R : +{s}, stop +{lock}R", run(dict(cadd=[(T, s, lock)]), f_v4), base)
print("| *Pyramide à la clôture, sans filtre* |")
base3 = run({}, f_all)
for T, s, lock in ((2.0, 1, 1.0), (1.5, 1, 1.0), (2.0, 1, 0.5), (2.5, 1, 1.0), (2.0, 2, 1.0)):
    row(f"clôture ≥ +{T}R : +{s}, stop +{lock}R", run(dict(cadd=[(T, s, lock)]), f_all), base3)
print("| *Pyramide + un seul filtre* |")
for lab, f in (("RSI seul", f_rsi), ("élan seul", f_ext)):
    row(lab + " + pyramide", run(dict(cadd=[(2.0, 1, 1.0)]), f), run({}, f))
