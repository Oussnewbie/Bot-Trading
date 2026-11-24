"""Contrôles du simulateur V10.

    .venv/bin/python -m pytest recherche/simulateur -q -p no:cacheprovider

- Sans données : des journées synthétiques passent par toute la chaîne (fusion bid / ask, heure de New York, range de 9:30,
  RSI, filtres, entrée A, jambes B et D, mémoire, FOMC) et chaque résultat attendu est calculé à la main dans les commentaires.
- Avec les CSV Dukascopy du Bureau : le début de 2018 et la fin de 2026 sont rejoués et comparés à la référence.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
if ICI not in sys.path:
    sys.path.insert(0, ICI)

import moteur as M  # noqa: E402
import reproduire_v10 as R  # noqa: E402
import sim_chemins as SC  # noqa: E402
import sim_donnees as SD  # noqa: E402
import v9lib as L  # noqa: E402
import v10lib as V  # noqa: E402

SPREAD = 0.5          # ask = bid + 0,5 ; glissement du jeu : 1 point par exécution


# ------------------------------------------------------------------ journées synthétiques
def _jour(b, suite):
    """Minutes bid (minute de New York, o, h, l, c) de 8:00 à 15:59. b = niveau de base du jour.
    8:00-9:29 : montée régulière de b à b+5 (RSI à 100, élan haussier, haut d'avant-ouverture b+5).
    9:30-9:34 : range d'ouverture, bas b, haut b+10 (range = 10 points)."""
    rows = [(480 + t, b + 5 * t / 90, b + 5 * (t + 1) / 90, b + 5 * t / 90, b + 5 * (t + 1) / 90) for t in range(90)]
    rows += [(570, b + 5, b + 6, b, b + 2), (571, b + 2, b + 5, b + 2, b + 5), (572, b + 5, b + 8, b + 5, b + 8),
             (573, b + 8, b + 9, b + 7, b + 9), (574, b + 9, b + 10, b + 9, b + 10)]
    return rows + suite(b)


def _gagnant(b):
    """9:35 ouvre à b+10 (ask b+10,5 au-dessus du niveau b+10 : achat à l'ouverture, b+11,5 avec le glissement) et monte à b+50,
    puis tout reste plat à b+50 jusqu'au soir."""
    return [(575, b + 10, b + 50, b + 10, b + 50)] + [(m, b + 50, b + 50, b + 50, b + 50) for m in range(576, 960)]


def _perdant(b):
    """Même achat à b+11,5 à 9:35, plat à b+10, puis chute à b-30 à 10:00 (sous le stop de A, b-20)."""
    return ([(575, b + 10, b + 11, b + 10, b + 10)] + [(m, b + 10, b + 10, b + 10, b + 10) for m in range(576, 600)]
            + [(600, b + 10, b + 10, b - 30, b - 30)] + [(m, b - 30, b - 30, b - 30, b - 30) for m in range(601, 960)])


def _tableau(jours):
    """jours : liste de (date, lignes). Construit bid et ask au format Dukascopy (ms UTC) puis les fusionne comme les vrais CSV."""
    rec = []
    for date, rows in jours:
        for minute, o, h, l, c in rows:
            ny = pd.Timestamp(f'{date} {minute // 60:02d}:{minute % 60:02d}').tz_localize('America/New_York')
            rec.append((ny.tz_convert('UTC').value // 10**6, o, h, l, c))
    bid = pd.DataFrame(rec, columns=['timestamp', 'open', 'high', 'low', 'close'])
    bid['volume'] = 1.0
    ask = bid.copy()
    for c in ('open', 'high', 'low', 'close'):
        ask[c] = ask[c] + SPREAD
    return SD.fusionner_bid_ask(bid, ask)


def _trois_jours(dates):
    # le niveau de base de chaque jour = la clôture de la veille (le RSI court sur tout l'historique)
    return _tableau([(dates[0], _jour(100, _gagnant)), (dates[1], _jour(150, _gagnant)), (dates[2], _jour(200, _perdant))])


def _v10(m, **kw):
    J = L.Jeu(m)
    T = L.orb_v6(J)
    X = V.strategie(J, T=T, **{**R.CONFORT, **kw})
    return J, T, X


# ------------------------------------------------------------------ tests sans données
def test_fusion_bid_ask_heure_de_new_york():
    m = _tableau([('2024-01-09', [(570, 1, 2, 0.5, 1.5)]), ('2024-07-09', [(570, 1, 2, 0.5, 1.5)])])
    assert list(m.columns) == SD.COLONNES
    assert list(m.minute) == [570, 570]                    # 9:30 New York, en hiver (UTC-5) comme en été (UTC-4)
    assert list(m.date) == ['2024-01-09', '2024-07-09']
    assert list(m.dow) == [1, 1]
    assert (m.ao - m.bo).tolist() == [SPREAD, SPREAD]


def test_calendrier_feries_et_fomc():
    import datetime as dt
    courts = ['2024-01-01', '2024-01-15', '2024-02-19', '2024-03-29', '2024-05-27', '2024-06-19', '2024-07-03', '2024-07-04',
              '2024-09-02', '2024-11-28', '2024-11-29', '2024-12-24', '2024-12-25']
    for d in courts:
        assert M.short_day(dt.date.fromisoformat(d)), d
    for d in ('2024-04-09', '2024-04-10', '2024-04-11', '2024-07-05', '2024-12-26'):
        assert not M.short_day(dt.date.fromisoformat(d)), d
    assert '2024-05-01' in L.FOMC_TOUT and '2026-12-09' in L.FOMC_TOUT and '2024-04-10' not in L.FOMC_TOUT


def test_journees_synthetiques_resultats_calcules_a_la_main():
    _, T, X = _v10(_trois_jours(['2024-04-09', '2024-04-10', '2024-04-11']))
    # la cassure v6 voit un signal d'achat les 3 jours (RSI 100 > 50, haut du range b+10 >= haut d'avant-ouverture b+5)
    assert list(T.date) == ['2024-04-09', '2024-04-10', '2024-04-11'] and list(T.sens) == [1, 1, 1]
    # le 10/04 est sauté par la mémoire (A du 09/04 a fini à +1,25 R > +1 R) ; aucune jambe B (aucune bougie M5 haussière
    # sur le VWAP), D2 et D3 absentes (bougies plates), D1 du 11/04 annulée (le bas de sa bougie est touché avant l'entrée)
    assert list(zip(X.date, X.comp)) == [('2024-04-09', 'A'), ('2024-04-09', 'D1'), ('2024-04-11', 'A')]
    a1, d1, a3 = (X.iloc[i] for i in range(3))
    # A du 09/04 : achat 100+10,5+1 = 111,5 ; stop = niveau 110 - 3 x range 10 = 80 ; 1R = 30 points.
    # Risque réel 31,5 : +1,5R (158,75) jamais atteint, cloture M5 a +1,22R < +2R : ni stop a l'entree ni pyramide.
    # Sortie 15:50 au bid 150 - 1 = 149 : (149 - 111,5) / 30 = +1,25 R
    assert (a1.sens, a1.E, a1.stop, a1.px, a1.sortie, a1.pyramide) == (1, 111.5, 80.0, 149.0, 'fin de journee', 0)
    assert a1.r == pytest.approx(1.25) and a1.lots == pytest.approx(1 / 3) and a1.risque == 1.0
    # D1 du 09/04 : bougie 9:35-9:39 de 110 a 150 (range 40) ; 9:40 ouvre a l'ask 150,5 au-dessus de 150 : achat 151,5.
    # Stop 150 - 3 x 40 = 30, 1R propre = 120 ; sortie 149 : -2,5 / 120. Risque plafonne a 1 R de A, lots 10 / 120.
    assert (d1.sens, d1.E, d1.stop, d1.px, d1.sortie, d1.pyramide) == (1, 151.5, 30.0, 149.0, 'fin de journee', 0)
    assert d1.r_propre == pytest.approx(-2.5 / 120) and d1.r == pytest.approx(-2.5 / 120)
    assert d1.risque == 1.0 and d1.lots == pytest.approx(10 / 120)
    # A du 11/04 : achat 211,5, stop 180 ; a 10:00 le bid tombe a 170 : sortie au stop 180 - 1 = 179 : -32,5 / 30
    assert (a3.sens, a3.E, a3.stop, a3.px, a3.sortie, a3.pyramide) == (1, 211.5, 180.0, 179.0, 'stop', 0)
    assert a3.r == pytest.approx(-32.5 / 30)


def test_memoire_seuil():
    # avec un seuil de mémoire de 1,3 R, le +1,25 R du 09/04 ne fait plus sauter le 10/04 (même journée, mêmes trades)
    _, _, X = _v10(_trois_jours(['2024-04-09', '2024-04-10', '2024-04-11']), mem_seuil=1.3)
    assert list(zip(X.date, X.comp)) == [('2024-04-09', 'A'), ('2024-04-09', 'D1'), ('2024-04-10', 'A'),
                                         ('2024-04-10', 'D1'), ('2024-04-11', 'A')]
    assert X.r.iloc[2] == pytest.approx(1.25) and X.r.iloc[4] == pytest.approx(-32.5 / 30)


def test_jour_fomc_retire_avant_la_memoire():
    # le 01/05/2024 est un jour FOMC : retiré avant la règle de mémoire, il ne « consomme » pas le saut.
    # Le saut dû au +1,25 R du 30/04 tombe donc sur le 02/05.
    _, T, X = _v10(_trois_jours(['2024-04-30', '2024-05-01', '2024-05-02']))
    assert len(T) == 3
    assert list(zip(X.date, X.comp)) == [('2024-04-30', 'A'), ('2024-04-30', 'D1')]


def test_comparaison_voit_les_ecarts():
    ref = pd.DataFrame({'date': ['2024-04-09', '2024-04-09'], 'comp': ['A', 'D1'], 'sens': [1, 1], 'E': [111.5, 151.5],
                        'stop': [80.0, 30.0], 'px': [149.0, 149.0], 'r': [1.25, -0.0208], 'r_propre': [1.25, -0.0208],
                        'lots': [0.3333, 0.0833], 'risque': [1.0, 1.0], 'sortie': ['fin de journee'] * 2, 'pyramide': [0, 0]})
    assert R.comparer(ref, ref)['identique']
    x = ref.copy()
    x.loc[1, 'r'] += 0.01
    assert not R.comparer(x, ref)['identique']
    x = ref.copy()
    x.loc[0, 'px'] = float('nan')
    assert not R.comparer(x, ref)['identique']
    x = ref.copy()
    x.loc[0, 'sortie'] = 'stop'
    assert R.comparer(x, ref)['differents_sortie'] == 1
    res = R.comparer(ref.iloc[:1], ref)
    assert not res['identique'] and len(res['manquants']) == 1


# ------------------------------------------------------------------ tests avec les vraies données (sautés si elles sont absentes)
CSV_PRESENTS = bool(glob.glob(os.path.join(SC.DOSSIER_BRUT, '*-bid-*.csv'))) and bool(glob.glob(os.path.join(SC.DOSSIER_BRUT, '*-ask-*.csv')))
sans_donnees = pytest.mark.skipif(not CSV_PRESENTS, reason=f'CSV Dukascopy absents de {SC.DOSSIER_BRUT}')


def _comparer_a_la_reference(X, debut, fin):
    ref = pd.read_csv(SC.REFERENCE_V10)
    ref = ref[(ref.date >= debut) & (ref.date <= fin)]
    res = R.comparer(X, ref)
    assert res['identique'], (res['manquants'], res['en_trop'], res['lignes_differentes'])
    return res


@sans_donnees
def test_debut_2018_identique_a_la_reference():
    # les 40 000 premières minutes des CSV : même départ que la simulation complète (RSI, mémoire), donc mêmes trades exactement
    m = SD.lire_csv_nasdaq(nrows=40_000)
    m = m[m.date < m.date.iloc[-1]].reset_index(drop=True)        # dernier jour incomplet retiré
    _, _, X = _v10(m)
    res = _comparer_a_la_reference(X, m.date.iloc[0], m.date.iloc[-1])
    assert res['apparies'] >= 30 and set(X.comp) == {'A', 'B', 'D1', 'D2', 'D3'}


@sans_donnees
def test_fin_2026_identique_a_la_reference():
    # Fenêtre qui commence le lendemain d'un trade A de la référence fini à +1 R ou moins : la mémoire n'y saute rien au départ.
    # 10 jours de cotations avant la fenêtre suffisent au RSI (lissage de Wilder : l'écart de départ est divisé par 1e60).
    ref = pd.read_csv(SC.REFERENCE_V10)
    a = ref[(ref.comp == 'A') & (ref.date < '2026-10-01') & (ref.r <= 1.0)]
    debut = (pd.Timestamp(a.date.iloc[-1]) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    chauffe = (pd.Timestamp(debut) - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
    m = pd.read_parquet(SD.chemin_m1_nasdaq(), filters=[('date', '>=', chauffe)])
    J = L.Jeu(m, debut=debut)
    X = V.strategie(J, T=L.orb_v6(J), **R.CONFORT)
    res = _comparer_a_la_reference(X, debut, '2026-12-31')
    assert res['apparies'] >= 50 and np.isclose(res['total'], res['total_ref'], atol=0.01)
