"""v5, série 5 (2018-22 seulement) : ajouts décidés à la clôture d'une bougie M5 (aucune hypothèse dans la bougie)."""
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all
L.prep()
def show(lab, P):
    a = stats(run(P, f_v4), "train"); b = stats(run(P, f_all), "train")
    print(f"| {lab} | {a['mean']:+.3f} | {a['tot']:+.0f} | -{a['dd']:.0f} | {a['tot']/a['dd']:.1f} | {a['t']:.2f} || {b['mean']:+.3f} | {b['tot']:+.0f} | -{b['dd']:.0f} | {b['tot']/b['dd']:.1f} | {b['t']:.2f} |", flush=True)
print("| Variante | v4 : R/trade | total | pire baisse | total/baisse | t || v3 : R/trade | total | pire baisse | total/baisse | t |"); print("|---|---|---|---|---|---|---|---|---|---|---|")
show("référence v4", {})
show("pyramide sur ordre stop : +1 à +2R (stop +1R)", dict(pyr=[(2, 1, 1)]))
print("| *pyramide à la clôture* |")
for T in (1.5, 2.0, 2.5, 3.0):
    for lock in (0.0, 0.5, 1.0, 1.5):
        if lock >= T - 0.4: continue
        for s in (1, 2):
            show(f"clôture ≥ +{T}R : +{s}, stop à +{lock}R", dict(cadd=[(T, s, lock)]))
print("| *complément précoce à la clôture* |")
for T in (0.0, 0.25, 0.5, 0.75, 1.0):
    for lock in (-1.0, -0.5, 0.0):
        if lock >= T - 0.2: continue
        for s in (1, 2):
            show(f"clôture ≥ +{T}R : +{s}, stop à {lock:+.1f}R", dict(cadd=[(T, s, lock)]))
