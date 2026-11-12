"""v5, série 2 (2018-22 seulement) : grille de pyramides, simulation sévère (l'ajout peut être stoppé dans sa bougie)."""
import v5_lab as L
from v5_lab import run, line, head, f_v4, f_all, stats
L.prep()
print("### Une pyramide : seuil × stop commun × taille — FILTRES v4 / SANS FILTRE (2018-22)")
print("| seuil | stop | taille | v4 : R/trade | total | pire baisse | t || v3 : R/trade | total | pire baisse | t |"); print("|---|---|---|---|---|---|---|---|---|---|---|")
a = stats(run({}, f_v4), "train"); b = stats(run({}, f_all), "train")
print(f"| sans | | | {a['mean']:+.3f} | {a['tot']:+.0f} | -{a['dd']:.0f} | {a['t']:.1f} || {b['mean']:+.3f} | {b['tot']:+.0f} | -{b['dd']:.0f} | {b['t']:.1f} |")
for trig in (1.5, 2.0, 2.5, 3.0, 4.0):
    for lock in (0.0, 0.5, 1.0, 1.5, 2.0):
        if lock >= trig: continue
        for sz in (0.5, 1.0, 2.0):
            P = dict(pyr=[(trig, sz, lock)])
            a = stats(run(P, f_v4), "train"); b = stats(run(P, f_all), "train")
            print(f"| +{trig}R | +{lock}R | {sz} | {a['mean']:+.3f} | {a['tot']:+.0f} | -{a['dd']:.0f} | {a['t']:.1f} || {b['mean']:+.3f} | {b['tot']:+.0f} | -{b['dd']:.0f} | {b['t']:.1f} |", flush=True)
print("\n### Deux pyramides (2018-22)"); head()
for lab, pyr in [("+1 à +2R (stop +1R), +1 à +4R (stop +2R)", [(2, 1, 1), (4, 1, 2)]),
                 ("+1 à +2R (stop +1R), +1 à +4R (stop +2,5R)", [(2, 1, 1), (4, 1, 2.5)]),
                 ("+1 à +2R (stop +1R), +1 à +5R (stop +3R)", [(2, 1, 1), (5, 1, 3)]),
                 ("+1 à +2R (stop +1R), +1 à +6R (stop +3R)", [(2, 1, 1), (6, 1, 3)]),
                 ("+1 à +2R (stop +1R), +1 à +3R (stop +1,5R)", [(2, 1, 1), (3, 1, 1.5)]),
                 ("+1 à +2R (stop +1R), +2 à +4R (stop +2,5R)", [(2, 1, 1), (4, 2, 2.5)]),
                 ("+1 à +2R, +1 à +4R, +1 à +6R (stops +1, +2,5, +4,5)", [(2, 1, 1), (4, 1, 2.5), (6, 1, 4.5)])]:
    line("v4 · " + lab, run(dict(pyr=pyr), f_v4)); line("v3 · " + lab, run(dict(pyr=pyr), f_all))
