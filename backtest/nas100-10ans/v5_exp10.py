"""v5, série 10 : la pyramide stoppée finit en moyenne à -0,35R (l'ajout se fait à la clôture, souvent au-dessus de +2R).
Variantes : stop à 1R sous le prix de l'ajout (pire cas vraiment nul), ou pas d'ajout si la clôture est trop loin."""
import v5_lab as L
from v5_lab import run, stats, f_v4, f_all
L.prep()
PERS = ("B", "train", "A")
def row(lab, P, f=f_v4):
    X = run(P, f); cells = []
    for p in PERS:
        s = stats(X, p); cells.append(f"{s['mean']:+.3f} | {s['tot']:+.0f}R | -{s['dd']:.0f}R")
    s = stats(X, list(PERS)); print(f"| {lab} | " + " | ".join(cells) + f" | {s['tot']:+.0f}R | -{s['dd']:.0f}R / {s['streak']} | {s['t']:.2f} |", flush=True)
print("| Pyramide (clôture ≥ +2R, +1 unité) | 2015-18 : R/trade | total | pire baisse | 2018-22 : R/trade | total | pire baisse | 2022-26 : R/trade | total | pire baisse | TOUT : total | pire baisse / série | t |"); print("|" + "---|" * 13)
row("sans pyramide", {})
row("première règle : stop de l'ensemble fixe à +1R", dict(cadd=[(2.0, 1, 1.0)]))
row("**v5 : stop à 1R sous le prix de l'ajout**", dict(cadd=[(2.0, 1, ("rel", 1.0, 1.0))]))
row("stop à 1,5R sous le prix de l'ajout (au moins +1R)", dict(cadd=[(2.0, 1, ("rel", 1.5, 1.0))]))
row("stop à 1R sous le prix de l'ajout (au moins +0,5R)", dict(cadd=[(2.0, 1, ("rel", 1.0, 0.5))]))
row("pas d'ajout si la clôture dépasse +3R", dict(cadd=[(2.0, 1, ("max", 3.0, 1.0))]))
row("pas d'ajout si la clôture dépasse +2,5R", dict(cadd=[(2.0, 1, ("max", 2.5, 1.0))]))
print("| *sans filtre* |")
row("sans pyramide", {}, f_all)
row("stop de l'ensemble à +1R", dict(cadd=[(2.0, 1, 1.0)]), f_all)
row("stop à 1R sous le prix de l'ajout (au moins +1R)", dict(cadd=[(2.0, 1, ("rel", 1.0, 1.0))]), f_all)
row("pas d'ajout si la clôture dépasse +3R", dict(cadd=[(2.0, 1, ("max", 3.0, 1.0))]), f_all)
