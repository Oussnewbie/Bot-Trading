"""Chiffres de recherche/critique-v10.md, recalculés à partir des trades simulés de la V10 (profil Confort).

    .venv/bin/python recherche/scripts/critique_v10.py

Ce sont des DESCRIPTIONS de données déjà vues (Nasdaq 2010-2026) : elles servent à choisir des pistes, pas à les prouver.
"""
import os

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(ICI), "resultats")
PERIODES = [("2018-2026", "trades_V10_confort_2018_2026_1pt.csv"),
            ("2010-2017", "trades_V10_confort_2010_2017_couts_aujourdhui.csv")]
pd.set_option("display.width", 200)


def gagnants(s):
    return (s > 0.05).mean()


def resume(t, nom):
    j = t.groupby("date").r.sum()
    courbe = j.cumsum()
    baisse = (courbe.cummax() - courbe).max()
    return (f"{nom:<20} trades {len(t):5d} · gagnants {gagnants(t.r):.1%} · jours gagnants {gagnants(j):.1%} · "
            f"total {t.r.sum():5.0f} R · pire baisse {baisse:3.0f} R")


for periode, fichier in PERIODES:
    t = pd.read_csv(os.path.join(RES, fichier), parse_dates=["date"])
    t["entree"] = t.comp.str[0]
    print(f"\n================ {periode}")

    # 1. achats contre ventes
    print(resume(t, "V10 telle quelle"))
    print(resume(t[t.sens == 1], "achats seulement"))
    print(resume(t[t.sens == -1], "ventes seulement"))
    print(t.groupby(["entree", "sens"]).r.agg(n="size", gagnants=gagnants, moyenne="mean", total="sum").round(3))

    # 2. achats et ventes selon la tendance de fond (prix d'entrée de A contre sa moyenne des 50 jours de trade précédents)
    a = t[t.comp == "A"].set_index("date").sort_index()
    ma = a.E.rolling(50, min_periods=30).mean().shift(1)
    tend = (a.E > ma).where(ma.notna()).rename("haussier")
    u = t.merge(tend, left_on="date", right_index=True).dropna(subset=["haussier"])
    u["tendance"] = np.where(u.haussier.astype(bool), "au-dessus MA50", "sous MA50")
    print(u.groupby(["tendance", "sens"]).r.agg(n="size", gagnants=gagnants, moyenne="mean").round(3))

    # 3. taille du range de 9:30 par rapport aux 20 derniers jours de trade
    rg = (a.E - a.stop).abs() / 3
    d = pd.DataFrame({"rel": rg / rg.rolling(20, min_periods=10).mean().shift(1), "A_stop": a.sortie == "stop",
                      "r_jour": t.groupby("date").r.sum()}).dropna()
    d["quintile"] = pd.qcut(d.rel, 5, labels=["Q1 petit", "Q2", "Q3", "Q4", "Q5 grand"])
    print(d.groupby("quintile", observed=True).agg(jours=("r_jour", "size"), range_relatif=("rel", "mean"),
                                                   A_au_stop=("A_stop", "mean"), jours_gagnants=("r_jour", gagnants),
                                                   r_par_jour=("r_jour", "mean")).round(3))

    # 4. de quoi sont faits les jours et les trades perdants
    j = t.groupby("date").agg(r=("r", "sum"), tous_stop=("sortie", lambda s: (s == "stop").all()))
    print(f"jours : {len(j)} · gagnants {gagnants(j.r):.1%} · perdants {(j.r < -0.05).mean():.1%} · "
          f"tous les trades au stop plein {j.tous_stop.mean():.1%} (en moyenne {j[j.tous_stop].r.mean():.2f} R)")
    p = t[t.r <= 0.05]
    print(f"trades non gagnants : {len(p) / len(t):.1%} · dont stop plein {(p.sortie == 'stop').mean():.1%} · "
          f"dont sortie de fin de journée {(p.sortie == 'fin de journee').mean():.1%} "
          f"(en moyenne {p[p.sortie == 'fin de journee'].r.mean():.2f} R)")
    issue_a = a.sortie.rename("issue_A")
    k = t.groupby("date").agg(r=("r", "sum"), n=("r", "size")).join(issue_a)
    print(k.groupby("issue_A").agg(jours=("r", "size"), r_jour=("r", "mean"), trades_par_jour=("n", "mean")).round(2))
