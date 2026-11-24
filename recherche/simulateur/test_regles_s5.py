"""Contrôles de regles_s5.py (session 5) : `.venv/bin/python -m pytest recherche/simulateur -q`."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import regles_s5 as S  # noqa: E402
import sim_chemins as SC  # noqa: E402


class FauxJeu:
    """Le strict nécessaire de v9lib.Jeu pour les réglages par jour."""
    def __init__(self, dates, orh, orl, px=None):
        self.nj = len(dates)
        self.D = type("D", (), {"dates": np.array(dates)})()
        self.Rp = pd.DataFrame({"orh": orh, "orl": orl}, index=pd.Index(range(self.nj), name="j"))
        self.px = np.array(px if px is not None else [5000.0] * self.nj)


def test_plancher_de_bruit():
    """f = max(3 ; 2,5 × moyenne des ranges des 20 séances précédentes / range du jour) ; 3 tant que la moyenne n'existe pas."""
    n = 25
    rng = [10.0] * 24 + [4.0]                       # le 25e jour a un range 2,5 fois plus petit que la moyenne
    J = FauxJeu([f"2026-01-{i + 1:02d}" for i in range(n)], [100 + r for r in rng], [100.0] * n)
    f = S.multiple_plancher(J)
    assert np.all(f[:20] == 3.0)                    # moins de 20 séances avant : pas de moyenne
    assert f[20] == 3.0                             # 2,5 × 10 / 10 = 2,5 < 3
    assert f[24] == pytest.approx(2.5 * 10 / 4)     # 6,25 : le stop s'élargit les jours calmes


def test_vix_et_gex_ne_regardent_que_la_veille():
    dates = [f"2026-03-{i + 1:02d}" for i in range(10)]
    J = FauxJeu(dates, [101.0] * 10, [100.0] * 10)
    serie = pd.Series(np.arange(10.0), index=dates)
    v = S._veille(J, serie)
    assert np.isnan(v[0]) and v[1] == 0.0 and v[9] == 8.0     # le jour j voit la valeur de j-1, jamais celle de j
    # médiane sur 3 lignes, pour le test : jour j tradé si valeur(j-1) >= médiane(j-3..j-1)
    ok = S.jours_vix(J, serie, n=3)
    assert not ok[:3].any() and ok[3:].all()                  # série croissante : toujours au-dessus de sa médiane
    assert not S.jours_gex(J, serie, n=3)[3:].any()           # et jamais en dessous


def test_marge_en_points_de_base():
    J = FauxJeu(["2026-01-02"], [101.0], [100.0], px=[6000.0])
    assert S.marge_pb(J, 0.5)[0] == pytest.approx(0.3)


@pytest.mark.skipif(not os.path.isdir(SC.DOSSIER_BRUT), reason="données Nasdaq absentes")
def test_reglages_neutres_redonnent_la_v10():
    import v9lib as L
    import v10lib as V
    J = L.Jeu("duka")
    T = L.orb_v6(J)
    ref = V.strategie(J, T=T, k=3.0, mem_seuil=1.0, d_cond="range_intact")
    neu = S.strategie_s5(J, T=T, mult=np.full(J.nj, 3.0), marge_B=np.full(J.nj, 1.0), jours_ok=np.ones(J.nj, bool))
    cols = ["j", "comp", "sens", "ie", "ix", "E", "px", "stop", "r", "r_propre", "risque", "lots", "sortie", "pyramide"]
    assert len(ref) == 3612 and ref[cols].equals(neu[cols])
    assert (S.strategie_s5(J, T=T, sens_permis=(1,)).sens == 1).all()
