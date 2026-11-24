"""Rejoue la Strategy V10, profil Confort, sur le Nasdaq 2018-2026 (spread réel + 1 point de glissement par exécution)
et compare trade par trade avec la référence recherche/resultats/trades_V10_confort_2018_2026_1pt.csv.

    .venv/bin/python recherche/simulateur/reproduire_v10.py

- Fabrique donnees/nasdaq_m1.parquet à partir des CSV Dukascopy s'il manque (voir sim_chemins.py pour les dossiers).
- Mêmes appels que 80_confort_final.py de l'archive : Jeu('duka'), orb_v6, puis strategie(k=3, mem_seuil=1, d_cond='range_intact').
- Écrit les trades dans donnees/trades_V10_confort_2018_2026_1pt.csv (jamais dans recherche/resultats/).
- Code de sortie 0 si tout concorde (mêmes trades, mêmes sens, sorties et pyramides, écarts <= 1e-4), 1 sinon.
"""
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)

import sim_chemins as SC  # noqa: E402
import sim_donnees as SD  # noqa: E402
import sim_jit  # noqa: E402

CONFORT = dict(k=3.0, mem_seuil=1.0, d_cond='range_intact')          # profil Confort tel que codé dans la V10
COLONNES = ['date', 'comp', 'sens', 'E', 'stop', 'px', 'r', 'r_propre', 'lots', 'risque', 'sortie', 'pyramide']
NUMERIQUES = ['E', 'stop', 'px', 'r', 'r_propre', 'lots', 'risque']
EXACTES = ['sens', 'sortie', 'pyramide']
TOLERANCE = 1e-4                    # la référence est arrondie à 4 décimales : un écart de 5e-5 au plus est attendu
MINUTES_ATTENDUES = 3_002_322       # resultats/01_qualite_donnees.md de l'archive
CONTROLES = {'v6': 475.96, 'v7': 591.33, 'V8': 986.17}                          # 43_controle_v9lib.py, 1 point
PAR_ENTREE = {'A': 1138, 'B': 854, 'D1': 601, 'D2': 529, 'D3': 490}            # 80_confort_final.md


def comparer(X, ref, tol=TOLERANCE):
    """Compare deux listes de trades (colonnes de COLONNES), appariées sur (date, comp). Retourne un dict de mesures."""
    a = X[COLONNES].copy()
    b = ref[COLONNES].copy()
    a['date'] = a.date.astype(str)
    b['date'] = b.date.astype(str)
    M = a.merge(b, on=['date', 'comp'], how='outer', suffixes=('', '_ref'), indicator=True)
    both = M[M._merge == 'both']
    res = dict(trades=len(a), trades_ref=len(b), apparies=len(both),
               manquants=M[M._merge == 'right_only'][['date', 'comp']], en_trop=M[M._merge == 'left_only'][['date', 'comp']],
               total=float(a.r.sum()), total_ref=float(b.r.sum()))
    for c in NUMERIQUES:
        res[f'ecart_max_{c}'] = float((both[c] - both[f'{c}_ref']).abs().max()) if len(both) else 0.0
    for c in EXACTES:
        res[f'differents_{c}'] = int((both[c].astype(str) != both[f'{c}_ref'].astype(str)).sum())
    ecart = np.zeros(len(both), bool)
    for c in NUMERIQUES:
        ecart |= ~((both[c] - both[f'{c}_ref']).abs().values <= tol)      # un NaN compte comme un écart
    for c in EXACTES:
        ecart |= (both[c].astype(str) != both[f'{c}_ref'].astype(str)).values
    res['lignes_differentes'] = both[ecart]
    res['identique'] = (len(res['manquants']) == 0 and len(res['en_trop']) == 0 and not ecart.any())
    return res


def afficher(res):
    print(f"trades : simulés {res['trades']}, référence {res['trades_ref']}, appariés sur (date, entrée) {res['apparies']}")
    print(f"manquants (dans la référence seulement) : {len(res['manquants'])} ; en trop (simulés seulement) : {len(res['en_trop'])}")
    print(f"total : simulé {res['total']:+.4f} R, référence {res['total_ref']:+.4f} R (écart {res['total'] - res['total_ref']:+.4f} R)")
    print('écart maximal par trade : ' + ', '.join(f"{c} {res[f'ecart_max_{c}']:.2e}" for c in NUMERIQUES))
    print('valeurs différentes : ' + ', '.join(f"{c} {res[f'differents_{c}']}" for c in EXACTES))
    for nom in ('manquants', 'en_trop', 'lignes_differentes'):
        if len(res[nom]):
            print(f'\n{nom} (10 premiers) :')
            print(res[nom].head(10).to_string(index=False))


def main():
    warnings.filterwarnings('ignore')
    pd.set_option('display.width', 220)
    t0 = time.time()
    if os.path.exists(SC.M1_NASDAQ):
        print(f'données : {SC.M1_NASDAQ} (déjà fabriqué)')
    else:
        print(f'données : fabrication de {SC.M1_NASDAQ} à partir de {SC.DOSSIER_BRUT} ...')
        SD.construire_m1_nasdaq()
    t_donnees = time.time() - t0

    import v9lib as L      # importés ici : moteur.py et v9lib.py compilent leurs fonctions numba au premier appel
    import v10lib as V
    t1 = time.time()
    J = L.Jeu('duka')
    D = J.D
    n_min = len(D.m)
    print(f"jeu : {n_min} minutes en semaine, {D.nj} jours, du {D.dates[0]} au {D.dates[-1]} ; numba : {'oui' if sim_jit.AVEC_NUMBA else 'non (Python pur)'}")
    m_brut = len(pd.read_parquet(SC.M1_NASDAQ, columns=['timestamp']))
    print(f'  minutes communes bid + ask : {m_brut} (archive : {MINUTES_ATTENDUES})')

    # ---- points de contrôle de l'archive (pour chercher un écart s'il y en a un)
    T = L.orb_v6(J)
    G = L.filtre_v7(J, T)
    X8 = L.v8(J, T=T)
    obtenus = {'v6': T.r.sum(), 'v7': G[G.pris].r.sum(), 'V8': X8.r.sum()}
    print('contrôles (43_controle_v9lib.py) : ' + ', '.join(f'{k} {v:+.2f} R (archive {CONTROLES[k]:+.2f})' for k, v in obtenus.items()))

    # ---- la V10 Confort, comme 80_confort_final.py
    X = V.strategie(J, T=T, **CONFORT)
    t_sim = time.time() - t1
    os.makedirs(SC.DOSSIER_DONNEES, exist_ok=True)
    sortie = os.path.join(SC.DOSSIER_DONNEES, 'trades_V10_confort_2018_2026_1pt.csv')
    X[COLONNES].round(4).to_csv(sortie, index=False)
    print(f'\ntrades V10 Confort écrits : {sortie}')
    n = X.comp.value_counts()
    print('trades par entrée : ' + ', '.join(f'{c} {int(n.get(c, 0))} (archive {v})' for c, v in PAR_ENTREE.items()))
    b = V.bilan(X)
    print(f"bilan : {b['trades']} trades, réussite {b['reussite_pct']} %, stops pleins {b['stops_pleins_pct']} %, total {b['total']:+.0f} R, "
          f"pire baisse {b['pire_baisse']:.0f} R, t = {b['t']}, années positives {b['annees_pos']} "
          f"(archive : 3612, 46.7 %, 29.5 %, +477 R, 32 R, t = 4.18, 8/9)")

    # ---- comparaison trade par trade
    print(f'\n== comparaison avec {os.path.relpath(SC.REFERENCE_V10, SC.DEPOT)}')
    ref = pd.read_csv(SC.REFERENCE_V10)
    res = comparer(X, ref)
    afficher(res)
    ok_controles = all(abs(obtenus[k] - CONTROLES[k]) < 0.006 for k in CONTROLES)
    print(f"\nrésultat : {'IDENTIQUE' if res['identique'] else 'DIFFÉRENT'} à la référence (tolérance {TOLERANCE:g})"
          f"{'' if ok_controles else ' ; ATTENTION : contrôles v6 / v7 / V8 différents de l archive'}")
    print(f'durée : données {t_donnees:.0f} s, simulation (compilation numba comprise) {t_sim:.0f} s, total {time.time() - t0:.0f} s')
    return 0 if res['identique'] and ok_controles else 1


if __name__ == '__main__':
    sys.exit(main())
