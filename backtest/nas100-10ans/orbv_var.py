import sys; sys.path.insert(0, ".")
import multiprocessing as mp, numpy as np, pandas as pd
import fam, orbv
F = None
def init():
    global F
    fam.prep(); F = pd.read_pickle("orb_features.pkl")
def work(job):
    lab, p = job
    X = orbv.run(F, p)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): orbv.line(lab, X)
    return buf.getvalue().strip()
Ftr = pd.read_pickle("orb_features.pkl"); Ftr = Ftr[Ftr.day < pd.Timestamp("2022-09-01")]
q80 = float(Ftr.or_atr.quantile(0.8)); q20 = float(Ftr.or_atr.quantile(0.2))
JOBS = [
 ("**Base** (+236R)", {}),
 ("*Taille du stop*", None),
 ("Stop à 0,75 × le range (plus serré)", dict(sm=0.75)),
 ("Stop à 1,25 × le range", dict(sm=1.25)),
 ("Stop à 1,5 × le range", dict(sm=1.5)),
 ("Stop à 2 × le range", dict(sm=2.0)),
 ("*Confirmer la cassure*", None),
 ("Entrée 10 % du range au-delà du niveau", dict(buf=0.10)),
 ("Entrée 25 % du range au-delà du niveau", dict(buf=0.25)),
 ("Cassures avant 9:45 seulement", dict(cutoff=585)),
 ("*Stop au point d'entrée / verrouillage*", None),
 ("Stop à l'entrée dès +1R", dict(be=1.0)),
 ("Stop à -0,5R dès +1R", dict(be=1.0, lock=-0.5)),
 ("Stop à l'entrée dès +1,5R", dict(be=1.5)),
 ("Stop à l'entrée dès +2R", dict(be=2.0)),
 ("Stop à +1R dès +3R", dict(be=3.0, lock=1.0)),
 ("Stop à +2R dès +4R", dict(be=4.0, lock=2.0)),
 ("*Prises partielles*", None),
 ("Moitié à +1R, reste à 15:50", dict(pr=1.0, pf=0.5)),
 ("Moitié à +1R puis stop à l'entrée", dict(pr=1.0, pf=0.5, pbe=True)),
 ("Moitié à +2R, reste à 15:50", dict(pr=2.0, pf=0.5)),
 ("Moitié à +3R, reste à 15:50", dict(pr=3.0, pf=0.5)),
 ("*Stop dans le temps*", None),
 ("Sortie si en perte après 30 min", dict(ts=6, tsr=0.0)),
 ("Sortie si en perte après 1 h", dict(ts=12, tsr=0.0)),
 ("Sortie si sous -0,5R après 1 h", dict(ts=12, tsr=-0.5)),
 ("*Objectif*", None),
 ("Objectif 5R", dict(rr=5.0)),
 ("Objectif 10R", dict(rr=10.0)),
 ("*Après un faux départ*", None),
 ("Inversion : après un stop, ordre de l'autre côté", dict(maxT=2)),
 ("*Filtre de range*", None),
 (f"Pas de trade si range > {q80:.2f} ATR jour (20 % les plus grands en 2018-22)", dict(maxor=q80)),
 (f"Pas de trade si range < {q20:.2f} ATR jour (20 % les plus petits)", dict(minor=q20)),
]
if __name__ == "__main__":
    jobs = [j for j in JOBS if j[1] is not None]
    with mp.Pool(4, initializer=init) as p:
        res = dict(zip([j[0] for j in jobs], p.map(work, jobs)))
    print("| Piste | Trades | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
    print("|---|---|---|---|---|---|---|---|")
    for lab, p in JOBS:
        print(f"| {lab} |||||||| " if p is None else res[lab])
