"""Étape 1.4 — La v5 non modifiée sur les données du dépôt (2018-01-01 -> 2026-11-13) : la référence de l'étude.

Le simulateur backtest/nas100-10ans/v5_lab.py est importé tel quel, avec les réglages de orb_v5.py. Son cache est
redirigé vers un dossier temporaire. Écrit sorties/etape1_reference.md.

La v5 n'est pas modifiée ici : lire toute la période, 2023-2026 comprise, ne consomme pas la période finale.
La comparaison avec l'ancien fichier M5 2015-2026 (mêmes bougies, mêmes trades) a été faite avant son retrait : elle est
dans sorties/historique-2011-2026/.
"""
import os
import sys
import tempfile

import pandas as pd

import commun as C

import v5_lab as L          # noqa: E402  (change le dossier courant : tous les chemins de ce script sont absolus)
import orb_v5               # noqa: E402

MOTIF = "reference v5 non modifiee"
NOMS = {"B": "2018-01 → 2018-04 (avant la période de choix)", "train": "2018-05 → 2022-08 (période de choix)",
        "A": "2022-09 → 2026-11 (vérification)", "tout": "Tout : 2018 → 2026-11"}


if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    L.CACHE_DIR = tempfile.mkdtemp(prefix="etude-sl-cache-")
    out = ["# Étape 1 — la v5 de référence sur les données du dépôt\n",
           "Simulateur : `backtest/nas100-10ans/v5_lab.py`, réglages de `orb_v5.py`, sans aucune modification. Glissement 0,1 point (celui du code).\n"]

    # 1. par le chargeur du simulateur (load10 : M5 reconstruit depuis les zips M1), périodes du README
    L.prep()
    R = {"sans pyramide": L.run({}, L.f_v4), "v5": L.run(orb_v5.V5, L.f_v4)}
    X = R["v5"]
    out.append("## 1. Périodes du README (choix de la v5, puis vérification)\n")
    out.append("| Période | | Trades | R par trade | Total | Pire baisse | Pire série de pertes |\n|---|---|---|---|---|---|---|")
    for per in ("B", "train", "A", "tout"):
        for nom in ("sans pyramide", "v5"):
            x = R[nom] if per == "tout" else R[nom][R[nom].per == per]
            s = C.resume_r(x.r.values)
            out.append(f"| {NOMS[per]} | {nom} | {s['n']} | {s['moy']:+.3f}R | {s['total']:+.1f}R | -{s['baisse']:.1f}R | {s['serie']} |")

    # 2. les bougies de l'étude (donnees/cache/bougies) donnent-elles les mêmes trades ?
    m5 = C.charger("nas100", "M5", finale=True, motif=MOTIF)
    b, a = C.cotes(m5)
    L.prep(data=(b, a))
    X3 = L.run(orb_v5.V5, L.f_v4)
    M = X.merge(X3, on="t", how="outer", suffixes=("_simu", "_etude"), indicator=True)
    communs = M[M._merge == "both"]
    ecart = (communs.r_simu - communs.r_etude).abs()
    ok = len(communs) == len(X) == len(X3) and ecart.max() < 1e-9
    out.append("\n## 2. Les bougies M5 de l'étude contre celles du simulateur\n")
    out.append(f"{len(X)} trades par le chargeur du simulateur, {len(X3)} par les bougies de l'étude, {len(communs)} à la même minute ; "
               f"écart maximal de R : {ecart.max():.2e}. **{'Mêmes trades, mêmes R.' if ok else 'ÉCART À EXPLIQUER.'}**")

    # 3. découpage de l'étude
    X3 = X3.copy()
    X3["an"] = X3.t.dt.year
    X3["periode"] = C.periode_de(X3.t)
    out.append("\n## 3. Découpage de l'étude\n")
    out.append(f"Du {X3.t.min():%Y-%m-%d} au {m5.index[-1]:%Y-%m-%d}. La coupe recherche / vérification ({C.COUPE_VERIFICATION}) est une proposition.\n")
    out.append(C.ENTETE_R)
    for nom, per in (("**Recherche : 2018 → 2020**", "recherche"), ("**Vérification : 2021 → 2022**", "verification"), ("**Finale : 2023 → 2026-11**", "finale")):
        out.append(C.ligne_r(nom, X3.r[X3.periode == per].values))
    out.append(C.ligne_r("Tout : 2018 → 2026-11", X3.r.values))
    out.append("\nPar année :\n\n| Année | Jours simulables | Trades | R par trade | Total | Pire baisse | Pire série de pertes |\n|---|---|---|---|---|---|---|")
    jours_an = pd.DatetimeIndex(L.D.day).year
    for an, g in X3.groupby("an"):
        r_ = C.resume_r(g.r.values)
        out.append(f"| {an} | {(jours_an == an).sum()} | {len(g)} | {g.r.mean():+.3f}R | {g.r.sum():+.1f}R | -{r_['baisse']:.1f}R | {r_['serie']} |")
    out.append("\nRappel : avant 2018 la v5 perd (2015-2017 : -55R, pire baisse -74R ; 2013-05 → 2014 : -33R, 26 pertes de suite). "
               "Ces années ne sont plus dans le dépôt ; le détail est dans `sorties/historique-2011-2026/`. "
               "La pire baisse lue sur 2018-2026 ne contient pas ce régime.")
    with open(os.path.join(C.SORTIES, "etape1_reference.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    sys.exit(0 if ok else 1)
