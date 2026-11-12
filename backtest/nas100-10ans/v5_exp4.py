"""v5, série 4 (2018-22 seulement) : entrée en deux temps (complément quand le trade a commencé à avoir raison),
seule puis avec la pyramide à +2R. Comparaison par le t (indépendant de la taille) et le total / pire baisse."""
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all
L.prep()
def show(lab, P):
    a = stats(run(P, f_v4), "train"); b = stats(run(P, f_all), "train")
    print(f"| {lab} | {a['mean']:+.3f} | {a['tot']:+.0f} | -{a['dd']:.0f} | {a['tot']/a['dd']:.1f} | {a['t']:.2f} || {b['mean']:+.3f} | {b['tot']:+.0f} | -{b['dd']:.0f} | {b['tot']/b['dd']:.1f} | {b['t']:.2f} |", flush=True)
print("| Variante | v4 : R/trade | total | pire baisse | total/baisse | t || v3 : R/trade | total | pire baisse | total/baisse | t |"); print("|---|---|---|---|---|---|---|---|---|---|---|")
show("référence", {})
show("pyramide +1 à +2R (stop +1R)", dict(pyr=[(2, 1, 1)]))
for T in (0.25, 0.5, 0.75, 1.0):
    for s in (1, 2):
        for lock in (-1.0, -0.5, 0.0):
            if lock >= T: continue
            show(f"complément ×{s} à +{T}R, stop à {lock:+.1f}R", dict(pyr=[(T, s, lock)]))
print("| *combinaisons* |")
for T, s, lock in ((0.5, 1, -1.0), (0.5, 2, -1.0), (1.0, 1, -1.0), (1.0, 1, 0.0), (1.0, 2, -1.0), (0.5, 1, -0.5)):
    show(f"complément ×{s} à +{T}R (stop {lock:+.1f}R) + pyramide ×1 à +2R (stop +1R)", dict(pyr=[(T, s, lock), (2, 1, 1)]))
    show(f"complément ×{s} à +{T}R (stop {lock:+.1f}R) + pyramide ×{1+s} à +2R (stop +1R)", dict(pyr=[(T, s, lock), (2, 1 + s, 1)]))
