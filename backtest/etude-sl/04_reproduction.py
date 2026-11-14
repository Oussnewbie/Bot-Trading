"""Étape 1.4b — La v5 du dépôt redonne-t-elle les chiffres du README ? Et sur le M5 reconstruit depuis le M1 ?

Le simulateur backtest/nas100-10ans/v5_lab.py est importé tel quel (avec les réglages de orb_v5.py). Son cache est
redirigé vers un dossier temporaire : aucun fichier existant n'est touché. Écrit sorties/etape1_reproduction.md.

La v5 n'est pas modifiée ici : lire toute la période, 2023-2026 comprise, ne consomme pas la période finale.
"""
import os
import sys
import tempfile

import numpy as np
import pandas as pd

import commun as C

sys.path.insert(0, C.SIMU)
import v5_lab as L          # noqa: E402  (change le dossier courant : tous les chemins de ce script sont absolus)
import orb_v5               # noqa: E402

MOTIF = "reference v5 non modifiee"
# README de main (2c0c65c), tableau « ce que le test dit vraiment » : (trades, total R, pire baisse R)
README = {
    "v5": {"B": (555, -31, 74), "train": (724, 249, 22), "A": (646, 155, 25), "tout": (1925, 372, 74)},
    "sans pyramide": {"B": (555, -52, 78), "train": (724, 152, 23), "A": (646, 111, 27), "tout": (1925, 211, 78)},
}
ANCIEN = (1915, 373, 69)    # en-tête de mt5/ORB-v5.mq5 et texte de la demande
NOMS = {"B": "2015-01 → 2018-04", "train": "2018-05 → 2022-08", "A": "2022-09 → 2026-10", "tout": "Tout : 2015 → 2026"}


def mesure(X, per):
    s = L.stats(X, None if per == "tout" else per)
    return s["n"], s["tot"], s["dd"], s["mean"], s["streak"]


def tableau(out, R):
    ok_tout = True
    out.append("| Période | | Trades | R par trade | Total | Pire baisse | Pire série | README | Verdict |\n|---|---|---|---|---|---|---|---|---|")
    for per in ("B", "train", "A", "tout"):
        for nom in ("sans pyramide", "v5"):
            n, tot, dd, moy, serie = mesure(R[nom], per)
            rn, rt, rd = README[nom][per]
            ok = n == rn and round(tot) == rt and round(dd) == rd
            ok_tout &= ok
            out.append(f"| {NOMS[per]} | {nom} | {n} | {moy:+.3f}R | {tot:+.1f}R | -{dd:.1f}R | {serie} | {rn} trades, {rt:+d}R, -{rd}R | {'identique' if ok else 'ÉCART'} |")
    return ok_tout


if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    L.CACHE_DIR = tempfile.mkdtemp(prefix="etude-sl-cache-")
    out = ["# Étape 1 — reproduction de la v5\n",
           "Simulateur : `backtest/nas100-10ans/v5_lab.py`, réglages de `orb_v5.py`, sans aucune modification. Glissement 0,1 point (celui du code).\n"]

    # 1. données du dépôt
    L.prep()
    R = {"sans pyramide": L.run({}, L.f_v4), "v5": L.run(orb_v5.V5, L.f_v4)}
    X = R["v5"]
    out.append("## 1. Sur les données du dépôt (`donnees/`, M5)\n")
    ok1 = tableau(out, R)
    out.append(f"\n**{'Les 8 lignes du README sont retrouvées.' if ok1 else 'Au moins une ligne ne colle pas avec le README.'}**\n")

    # 2. l'ancien chiffre : 1 915 trades, +373R, -69R
    anciens_jours = L.D[L.D.atrd.notna()]
    Xa = L.run(orb_v5.V5, L.f_v4, days=anciens_jours)
    n, tot, dd, moy, serie = mesure(Xa, "tout")
    ok2 = (n, round(tot), round(dd)) == ANCIEN
    perdus = X[~X.i.isin(Xa.i)]
    out.append("## 2. D'où viennent « 1 915 trades, +373R »\n")
    out.append("Avant l'audit du 14 novembre 2026 (commit `d2cf90e`), le simulateur écartait les jours sans ATR journalier sur 14 jours, "
               "c'est-à-dire les premières semaines de 2015. La v5 n'utilise pas cet ATR. En rejouant la v5 sans ces jours :\n")
    out.append(C.ENTETE_R)
    out.append(C.ligne_r("v5 sans les jours écartés par l'ancien code", Xa.r.values))
    out.append(C.ligne_r("v5 du code actuel", X.r.values))
    out.append(f"\nAncien chiffre attendu : {ANCIEN[0]} trades, +{ANCIEN[1]}R, pire baisse -{ANCIEN[2]}R → **{'retrouvé' if ok2 else 'NON retrouvé'}**.")
    out.append(f"Les {len(perdus)} trades de différence vont du {perdus.t.min():%Y-%m-%d} au {perdus.t.max():%Y-%m-%d} et totalisent {perdus.r.sum():+.2f}R : "
               + ", ".join(f"{t:%m-%d} {r:+.2f}R" for t, r in zip(perdus.t, perdus.r)) + ".\n")

    # 3. M5 reconstruit depuis le M1, mêmes dates
    m5 = C.charger("nas100", "M5", finale=True, motif=MOTIF)
    ref_t0, ref_t1 = L.G["t"][0], L.G["t"][-1]
    b, a = C.cotes(m5[(m5.index >= ref_t0) & (m5.index <= ref_t1)])
    L.prep(data=(b, a))
    R2 = {"sans pyramide": L.run({}, L.f_v4), "v5": L.run(orb_v5.V5, L.f_v4)}
    X2 = R2["v5"]
    out.append("## 3. Sur le M5 reconstruit à partir du M1 téléchargé, mêmes dates\n")
    ok3 = tableau(out, R2)
    M = X.merge(X2, on="t", how="outer", suffixes=("_depot", "_m1"), indicator=True)
    communs = M[M._merge == "both"]
    ecart = (communs.r_depot - communs.r_m1).abs()
    ok3 &= len(communs) == len(X) == len(X2) and ecart.max() < 1e-9
    out.append(f"\nTrade par trade : {len(X)} trades dans le dépôt, {len(X2)} dans le reconstruit, {len(communs)} à la même minute ; "
               f"écart maximal de R sur ces trades : {ecart.max():.2e} ; trades dont le R diffère de plus de 0,000001 : {int((ecart > 1e-6).sum())}.")
    out.append(f"\n**{'Mêmes trades, mêmes R.' if ok3 else 'Les trades diffèrent : voir ci-dessus.'}**\n")

    # 4. tout l'historique M1 (référence pour la suite), découpage de l'étude
    b, a = C.cotes(m5)
    L.prep(data=(b, a))
    X3 = L.run(orb_v5.V5, L.f_v4)
    X3["an"] = X3.t.dt.year
    out.append("## 4. La v5 non modifiée sur tout l'historique téléchargé (M5 reconstruit), découpage de l'étude\n")
    out.append(f"Du {m5.index[0]:%Y-%m-%d} au {m5.index[-1]:%Y-%m-%d}. Jours où le simulateur a un range de 9:30 et une fenêtre 9:00-9:30 : {len(L.D)}.\n")
    out.append(C.ENTETE_R)
    t = X3.t.dt.tz_localize(None)
    for nom, d0, d1 in (("Avant 2015 (jamais simulé jusqu'ici)", "2000-01-01", "2015-01-01"), ("2015 → 2017", "2015-01-01", "2018-01-01"),
                        ("**Recherche : début → 2017**", "2000-01-01", "2018-01-01"), ("**Vérification : 2018 → 2022**", "2018-01-01", "2023-01-01"),
                        ("**Finale : 2023 → 2026-11**", "2023-01-01", "2100-01-01"), ("Tout", "2000-01-01", "2100-01-01")):
        out.append(C.ligne_r(nom, X3.r[(t >= d0) & (t < d1)].values))
    out.append("\nPar année :\n\n| Année | Jours simulables | Trades | R par trade | Total |\n|---|---|---|---|---|")
    jours_an = pd.DatetimeIndex(L.D.day).year
    for an, g in X3.groupby("an"):
        out.append(f"| {an} | {(jours_an == an).sum()} | {len(g)} | {g.r.mean():+.3f}R | {g.r.sum():+.1f}R |")
    out.append(f"\n**Verdict de l'étape : {'reproduction réussie' if ok1 and ok2 and ok3 else 'ÉCART À EXPLIQUER'}.**")
    with open(os.path.join(C.SORTIES, "etape1_reproduction.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    sys.exit(0 if ok1 and ok2 and ok3 else 1)
