"""v5, série 6 (2018-22 seulement) : la pyramide à la clôture avec les autres réglages (stop à l'entrée, sortie, durée)."""
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all
L.prep()
PY = [(2.0, 1.0, 1.0)]
def show(lab, P):
    a = stats(run(P, f_v4), "train"); b = stats(run(P, f_all), "train")
    print(f"| {lab} | {a['n']} | {a['mean']:+.3f} | {a['tot']:+.0f} | -{a['dd']:.0f} / {a['streak']} | {a['t']:.2f} || {b['mean']:+.3f} | {b['tot']:+.0f} | -{b['dd']:.0f} | {b['t']:.2f} |", flush=True)
print("| Variante (avec pyramide : clôture ≥ +2R, +1 unité, stop +1R) | trades | v4 : R/trade | total | pire baisse / série | t || v3 : R/trade | total | pire baisse | t |"); print("|---|---|---|---|---|---|---|---|---|---|")
show("**candidat v5** : stop à l'entrée dès +1,5R", dict(cadd=PY))
show("sans stop à l'entrée avant la pyramide", dict(cadd=PY, locks=[]))
show("stop à l'entrée dès +1R", dict(cadd=PY, locks=[(1.0, 0.0)]))
show("stop à -0,5R dès +1R", dict(cadd=PY, locks=[(1.0, -0.5)]))
show("ordres jusqu'à 9:40", dict(cadd=PY, cutoff=580))
show("ordres jusqu'à 10:00", dict(cadd=PY, cutoff=600))
show("sortie à 14:00", dict(cadd=PY, tex=840))
show("objectif 8R", dict(cadd=PY, tp=8.0))
show("objectif 12R", dict(cadd=PY, tp=12.0))
show("stop suiveur dès +4R (24 bougies)", dict(cadd=PY, trail=(4.0, 24)))
show("stop à +2R dès +4R", dict(cadd=PY, locks=[(1.5, 0.0), (4.0, 2.0)]))
show("stop à +3R dès +6R", dict(cadd=PY, locks=[(1.5, 0.0), (6.0, 3.0)]))
show("2e pyramide : clôture ≥ +4R, +1, stop +2,5R", dict(cadd=PY + [(4.0, 1.0, 2.5)]))
show("2e pyramide : clôture ≥ +5R, +1, stop +3R", dict(cadd=PY + [(5.0, 1.0, 3.0)]))
show("pyramide ×2", dict(cadd=[(2.0, 2.0, 1.0)]))
show("pyramide ×0,5", dict(cadd=[(2.0, 0.5, 1.0)]))
