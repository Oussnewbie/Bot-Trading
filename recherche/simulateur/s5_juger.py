"""Session 5, étape 4 : LA lecture unique du S&P 500 (règles et critère : recherche/notes/idees-strategies.md, « SESSION 5 »).

    .venv/bin/python recherche/simulateur/s5_juger.py

Prérequis : s5_qualite.py lancé et relu ; donnees/externes/VIX_History.csv (Cboe) et donnees/externes/DIX.csv (SqueezeMetrics).
Écrit recherche/resultats/s5_sp500_jugement.md et refuse de se relancer ensuite : le S&P 500 ne juge qu'une fois. Seule exception,
une erreur de code prouvée : --corriger "raison" relance et ajoute la raison au rapport.
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import sim_chemins as SC  # noqa: E402

M1 = os.path.join(SC.DOSSIER_DONNEES, "sp500_m1.parquet")
EXT = os.path.join(SC.DOSSIER_DONNEES, "externes")
SORTIE = os.path.join(SC.DEPOT, "recherche", "resultats", "s5_sp500_jugement.md")
COUT, RESIST = 0.6, (1.2, 1.8)        # glissement en points de base du prix, par exécution
MARGE_B_PB = 0.5
TIRAGES, GRAINE = 10_000, 20261124
HOLM = [0.05 / 4, 0.05 / 3, 0.05 / 2, 0.05]
GAIN_MIN = 0.75


def gagnant(r):
    return r > 0.05


def mesures(X, nj_ref=None):
    if len(X) == 0:
        return dict(trades=0, reussite=np.nan, jours=0, jours_perdants=np.nan, total=0.0, pire_baisse=0.0, stops=np.nan)
    j = X.groupby("j").r.sum()
    courbe = j.cumsum()
    return dict(trades=len(X), reussite=gagnant(X.r).mean(), jours=len(j), jours_perdants=(j < -0.05).mean(),
                total=X.r.sum(), pire_baisse=(courbe.cummax() - courbe).max(), stops=(X.r_propre <= -0.9).mean())


def p_bootstrap(X0, X1, rng):
    """P(différence de taux de trades gagnants <= 0) par tirage de jours avec remise, sur l'union des jours tradés."""
    jours = np.union1d(X0.j.unique(), X1.j.unique())
    g0 = X0.assign(w=gagnant(X0.r)).groupby("j").w.agg(["sum", "size"]).reindex(jours, fill_value=0)
    g1 = X1.assign(w=gagnant(X1.r)).groupby("j").w.agg(["sum", "size"]).reindex(jours, fill_value=0)
    s0, n0, s1, n1 = (a.to_numpy(float) for a in (g0["sum"], g0["size"], g1["sum"], g1["size"]))
    obs = s1.sum() / n1.sum() - s0.sum() / n0.sum()
    k = len(jours)
    diffs = np.empty(TIRAGES)
    for t in range(TIRAGES):
        idx = rng.integers(0, k, k)
        a, b = n1[idx].sum(), n0[idx].sum()
        diffs[t] = (s1[idx].sum() / a if a else np.nan) - (s0[idx].sum() / b if b else np.nan)
    return obs, float(np.nanmean(diffs <= 0))


def main():
    corriger = None
    if "--corriger" in sys.argv:
        corriger = sys.argv[sys.argv.index("--corriger") + 1]
    if os.path.exists(SORTIE) and not corriger:
        sys.exit(f"{SORTIE} existe déjà : le S&P 500 a été lu. Relance seulement pour une erreur de code prouvée : --corriger \"raison\".")
    for f in (M1, os.path.join(EXT, "VIX_History.csv"), os.path.join(EXT, "DIX.csv")):
        if not os.path.exists(f):
            sys.exit(f"manquant : {f} (lancer d'abord s5_qualite.py et télécharger le VIX et le GEX)")

    import v9lib as L
    import regles_s5 as S

    vix = pd.read_csv(os.path.join(EXT, "VIX_History.csv"))
    vix = pd.Series(vix.CLOSE.values, index=pd.to_datetime(vix.DATE, format="%m/%d/%Y").dt.strftime("%Y-%m-%d"))
    gex = pd.read_csv(os.path.join(EXT, "DIX.csv"))
    gex = pd.Series(gex.gex.values, index=gex.date.astype(str))

    resultats = {}
    for cout in (COUT,) + RESIST:
        J = L.Jeu(M1, cout="prop", slip_pb=cout)
        T = L.orb_v6(J)
        mb = S.marge_pb(J, MARGE_B_PB)
        regles = {
            "R0 V10 inchangée": dict(),
            "H1 plancher de bruit": dict(mult=S.multiple_plancher(J)),
            "H2 achats seuls": dict(sens_permis=(1,)),
            "H3 VIX >= médiane": dict(jours_ok=S.jours_vix(J, vix)),
            "H4 GEX < médiane": dict(jours_ok=S.jours_gex(J, gex)),
        }
        resultats[cout] = {nom: S.strategie_s5(J, T=T, marge_B=mb, **kw) for nom, kw in regles.items()}

    X = resultats[COUT]
    m0 = mesures(X["R0 V10 inchangée"])
    rng = np.random.default_rng(GRAINE)
    lignes = ["# S&P 500 Dukascopy : lecture unique des quatre règles de la session 5", ""]
    if corriger:
        lignes += [f"**Relance pour erreur de code : {corriger}**", ""]
    lignes += [f"Coût principal : spread réel + {COUT} pb par exécution ; marge du stop de B {MARGE_B_PB} pb. Critère A (idees-strategies.md, session 5).", "",
               "| Règle | Trades | Trades gagnants | Jours | Jours perdants | Stops pleins | Total | Pire baisse |",
               "|---|---|---|---|---|---|---|---|"]
    for nom, Xr in X.items():
        m = mesures(Xr)
        lignes.append(f"| {nom} | {m['trades']} | {100 * m['reussite']:.1f} % | {m['jours']} | {100 * m['jours_perdants']:.1f} % | "
                      f"{100 * m['stops']:.1f} % | {m['total']:+.0f} R | {m['pire_baisse']:.0f} R |")

    # critère A
    tests = []
    for nom in list(X)[1:]:
        obs, p = p_bootstrap(X["R0 V10 inchangée"], X[nom], rng)
        m = mesures(X[nom])
        tests.append(dict(nom=nom, diff=obs, p=p, gain_ok=(m0["total"] > 0 and m["total"] >= GAIN_MIN * m0["total"]),
                          jours_ok=m["jours_perdants"] <= m0["jours_perdants"],
                          resist_ok=mesures(resultats[RESIST[0]][nom])["reussite"] > mesures(resultats[RESIST[0]]["R0 V10 inchangée"])["reussite"]))
    ordre = sorted(tests, key=lambda t: t["p"])
    holm_ok = {}
    encore = True
    for rang, t in enumerate(ordre):
        seuil = HOLM[rang]
        holm_ok[t["nom"]] = encore and t["diff"] > 0 and t["p"] < seuil
        if not holm_ok[t["nom"]]:
            encore = False
    lignes += ["", "## Critère A", ""]
    if m0["total"] <= 0:
        lignes += [f"**R0 ne gagne rien au coût principal ({m0['total']:+.0f} R) : aucune règle n'est retenue sur ces données** (règle écrite à l'avance).", ""]
    lignes += ["| Règle | Écart de taux de gagnants | p (tirages) | 1. Holm | 2. Gain >= 75 % | 3. Jours perdants | 4. Résiste à 1,2 pb | Retenue |",
               "|---|---|---|---|---|---|---|---|"]
    for t in tests:
        ok = m0["total"] > 0 and holm_ok[t["nom"]] and t["gain_ok"] and t["jours_ok"] and t["resist_ok"]
        o = lambda v: "oui" if v else "non"  # noqa: E731
        lignes.append(f"| {t['nom']} | {100 * t['diff']:+.1f} pts | {t['p']:.4f} | {o(holm_ok[t['nom']])} | {o(t['gain_ok'])} | "
                      f"{o(t['jours_ok'])} | {o(t['resist_ok'])} | **{o(ok)}** |")

    # coûts de résistance
    lignes += ["", "## Tests de résistance (total, taux de trades gagnants)", "", "| Règle | " + " | ".join(f"{c} pb" for c in (COUT,) + RESIST) + " |",
               "|---|" + "---|" * (1 + len(RESIST))]
    for nom in X:
        cases = []
        for c in (COUT,) + RESIST:
            m = mesures(resultats[c][nom])
            cases.append(f"{m['total']:+.0f} R, {100 * m['reussite']:.1f} %")
        lignes.append(f"| {nom} | " + " | ".join(cases) + " |")

    # descriptif, non jugé
    R0 = X["R0 V10 inchangée"].copy()
    lignes += ["", "## Descriptif (non jugé)", "", "R0 par sens et par entrée :", "", "| Entrée | Sens | Trades | Gagnants | Moyenne | Total |", "|---|---|---|---|---|---|"]
    R0["entree"] = R0.comp.str[0]
    for (e, s), g in R0.groupby(["entree", "sens"]):
        lignes.append(f"| {e} | {'achat' if s == 1 else 'vente'} | {len(g)} | {100 * gagnant(g.r).mean():.1f} % | {g.r.mean():+.3f} R | {g.r.sum():+.0f} R |")
    lignes += ["", "Par année (total en R) :", "", "| Règle | " + " | ".join(str(a) for a in sorted(R0.annee.unique())) + " |",
               "|---|" + "---|" * R0.annee.nunique()]
    for nom, Xr in X.items():
        ya = Xr.groupby("annee").r.sum().reindex(sorted(R0.annee.unique()), fill_value=0)
        lignes.append(f"| {nom} | " + " | ".join(f"{v:+.0f}" for v in ya) + " |")
    g4 = X["H4 GEX < médiane"]
    for nom_p, cond in (("2018 à nov. 2020 (GEX reconstruit)", g4.date < "2020-12-01"), ("déc. 2020 à 2026", g4.date >= "2020-12-01")):
        m = mesures(g4[cond])
        lignes.append(f"\nH4 sur {nom_p} : {m['trades']} trades, {100 * m['reussite']:.1f} % gagnants, {m['total']:+.0f} R.")

    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    for nom, Xr in X.items():
        Xr.to_csv(os.path.join(SC.DOSSIER_DONNEES, f"s5_trades_{nom.split()[0]}.csv"), index=False)
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
