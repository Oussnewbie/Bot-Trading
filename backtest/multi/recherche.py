"""Recherche de stratégies par instrument : toutes les variantes de familles.py, sur chaque instrument, jugées par une
règle écrite AVANT de lancer quoi que ce soit.

    python backtest/multi/recherche.py                    tous les instruments (4 processus)
    python backtest/multi/recherche.py or eurusd          seulement ceux-là

LA RÈGLE (anti-surapprentissage) :
 1. Une variante n'est « candidate » que sur la période de recherche (train, 2018-05 -> 2022-08) :
    au moins 100 trades, et un t de Student d'au moins 3 (une chance sur 750 d'arriver par hasard pour une variante,
    donc environ 2 fausses candidates attendues sur 1 500 variantes essayées).
 2. Une candidate n'est « confirmée » que si la période de vérification (A, 2022-09 -> 2026-11), qu'elle n'a pas servi à
    choisir, est positive avec un t d'au moins 2.
 3. Tout le reste est rejeté, même si le total sur 9 ans est joli : sur 1 500 variantes, les jolis totaux par hasard
    sont nombreux.
Le fichier sorties/variantes.csv garde TOUTES les variantes, les perdantes aussi.
"""
import itertools
import multiprocessing
import os
import sys
import time

import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import banc as B  # noqa: E402
import familles as F  # noqa: E402

SORTIES = os.path.join(ICI, "sorties")
T_CANDIDATE, N_CANDIDATE, T_CONFIRME = 3.0, 100, 2.0

# Séances par instrument (minutes, heure de New York). ouvertures : débuts de range d'ouverture testés ;
# plages : ranges de séance (début, fin, validité de la cassure) ; seance : fenêtre des signaux des autres familles.
SEANCES = {
    # plages : avant-marché, nuit, 24 heures précédentes (supports et résistances de la veille), séance de Londres
    "nas100":  dict(ouvertures=[570], sortie=950, plages=[(240, 570, 120), (-360, 570, 120), (-870, 570, 240)], seance=(575, 900), ancre=570),
    "dow":     dict(ouvertures=[570], sortie=950, plages=[(240, 570, 120), (-360, 570, 120), (-870, 570, 240)], seance=(575, 900), ancre=570),
    "or":      dict(ouvertures=[180, 500, 570], sortie=950, plages=[(-360, 180, 240), (-360, 500, 180), (-870, 570, 240), (180, 480, 240)], seance=(185, 900), ancre=180),
    "eurusd":  dict(ouvertures=[120, 180, 480, 570], sortie=960, plages=[(-420, 120, 240), (-420, 180, 240), (-870, 570, 240), (180, 480, 240)], seance=(185, 900), ancre=180),
    "bitcoin": dict(ouvertures=[180, 570], sortie=950, plages=[(-360, 180, 240), (0, 570, 120), (-870, 570, 240)], seance=(185, 900), ancre=180),
}
GESTIONS_CASSURE = {"stop a l'entree +1,5R": dict(be=1.5), "v5 : +1,5R et pyramide": dict(be=1.5, pyr=(2.0, 1.0)), "objectif 2R": dict(tp=2.0)}
GESTIONS_TENDANCE = {"sortie fin de seance": dict(), "objectif 2R": dict(tp=2.0), "v5 : +1,5R et pyramide": dict(be=1.5, pyr=(2.0, 1.0))}
GESTIONS_RETOUR = {"objectif 1R (la moyenne)": dict(tp=1.0)}


def variantes(nom):
    """Toutes les variantes d'un instrument : (famille, description, fonction qui rend les ordres, gestions)."""
    s = SEANCES[nom]
    sortie, (deb, fin), ancre = s["sortie"], s["seance"], s["ancre"]
    v = []
    for o, duree, valable, filtre in itertools.product(s["ouvertures"], (5, 15, 30, 60), (10, 60), ("aucun", "v4", "ma200", "v4+ma200")):
        v.append(("cassure d'ouverture (ORB)", f"range {o // 60}:{o % 60:02d} +{duree} min, valable {valable} min, filtre {filtre}",
                  lambda c, o=o, duree=duree, valable=valable, filtre=filtre: F.cassure(c, o, o + duree, valable, sortie, filtre), GESTIONS_CASSURE))
    for (a, b, valable), filtre in itertools.product(s["plages"], ("aucun", "ma200")):
        v.append(("cassure d'un range de seance", f"range {a} -> {b} min, valable {valable} min, filtre {filtre}",
                  lambda c, a=a, b=b, valable=valable, filtre=filtre: F.cassure(c, a, b, valable, sortie, filtre, exact=False), GESTIONS_CASSURE))
    for (a, b, valable), biais in itertools.product(s["plages"], (False, True)):
        v.append(("prise de liquidite (ICT/SMC)", f"range {a} -> {b} min, {valable} min, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, a=a, b=b, valable=valable, biais=biais: F.balayage(c, a, b, valable, sortie, biais), GESTIONS_TENDANCE))
    for seuil, stop, biais in itertools.product((30, 25), (2.0, 4.0), (True, False)):
        v.append(("repli RSI", f"RSI14 M5 < {seuil}, stop {stop:g} ATR, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, seuil=seuil, stop=stop, biais=biais: F.repli_rsi(c, deb, fin, sortie, seuil, stop, biais), GESTIONS_TENDANCE))
    for biais in (True, False):
        v.append(("repli sur le VWAP", f"VWAP ancre {ancre} min, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, biais=biais: F.repli_vwap(c, ancre, deb + 25, fin, sortie, biais), GESTIONS_TENDANCE))
    for bandes, biais in itertools.product((2.0, 2.5), (False, True)):
        v.append(("retour au VWAP", f"VWAP ancre {ancre} min, {bandes:g} ecarts-types, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, bandes=bandes, biais=biais: F.retour_vwap(c, ancre, deb + 25, fin, sortie, bandes, biais), GESTIONS_RETOUR))
    for stop, biais in itertools.product((2.0, 4.0), (True, False)):
        v.append(("croisement MACD M15", f"stop {stop:g} ATR, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, stop=stop, biais=biais: F.croisement_macd(c, deb, fin, sortie, stop, biais), GESTIONS_TENDANCE))
    for bandes, biais in itertools.product((2.0, 2.5), (False, True)):
        v.append(("centre de gravite Belkhayate", f"{bandes:g} ecarts-types, biais MA200 {'oui' if biais else 'non'}",
                  lambda c, bandes=bandes, biais=biais: F.retour_cog(c, deb, fin, sortie, bandes, biais), GESTIONS_RETOUR))
    return v


def un_instrument(nom):
    debut = time.time()
    g = B.charger(nom)
    c = F.Contexte(g)
    lignes = []
    for famille, description, ordres_de, gestions in variantes(nom):
        ordres = ordres_de(c)
        for gestion, options in gestions.items():
            x = B.derouler(g, ordres, **options)
            ligne = dict(instrument=nom, famille=famille, variante=description, gestion=gestion)
            for per in ("train", "A"):
                s = B.stats(x, per)
                ligne.update({f"n_{per}": s["n"], f"moy_{per}": round(s["mean"], 4), f"t_{per}": round(s["t"], 2),
                              f"tot_{per}": round(s["tot"], 1), f"baisse_{per}": round(s["dd"], 1)})
            tout = B.stats(x, ["train", "A"])
            ligne.update(n=tout["n"], tot=round(tout["tot"], 1), baisse=round(tout["dd"], 1), annees_pos=tout["ypos"], gagnants=round(tout["win"], 3))
            lignes.append(ligne)
    print(f"{nom} : {len(lignes)} variantes en {time.time() - debut:.0f} s", flush=True)
    return lignes


if __name__ == "__main__":
    noms = sys.argv[1:] or list(SEANCES)
    with multiprocessing.Pool(min(4, len(noms))) as pool:
        resultats = pool.map(un_instrument, noms)
    table = pd.DataFrame([ligne for lignes in resultats for ligne in lignes])
    os.makedirs(SORTIES, exist_ok=True)
    chemin = os.path.join(SORTIES, "variantes.csv")
    if sys.argv[1:] and os.path.exists(chemin):                  # relance partielle : on garde les autres instruments
        ancien = pd.read_csv(chemin)
        table = pd.concat([ancien[~ancien.instrument.isin(noms)], table], ignore_index=True)
    table.to_csv(chemin, index=False)
    print(f"{len(table)} variantes -> {chemin}")
