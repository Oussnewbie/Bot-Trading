"""Tests des outils communs : reconstruction des horizons, ancrage H4/D1, verrou de la période finale."""
import numpy as np
import pandas as pd
import pytest

import commun as C


def _m1(debut_ny, n):
    """n minutes consécutives à partir d'une heure de New York ; prix = rang de la minute."""
    t = pd.date_range(pd.Timestamp(debut_ny, tz=C.NY), periods=n, freq="1min").tz_convert("UTC")
    x = np.arange(n, dtype=float)
    d = pd.DataFrame({"bo": x, "bh": x + 0.5, "bl": x - 0.5, "bc": x + 0.2, "bv": 1.0,
                      "ao": x + 1, "ah": x + 1.5, "al": x + 0.5, "ac": x + 1.2, "av": 2.0}, index=t.as_unit("ms").asi8)
    return d


def test_m5_open_high_low_close_volume():
    g = C.agreger(_m1("2024-06-03 09:30", 10), "M5")
    assert len(g) == 2
    assert list(g.bo) == [0.0, 5.0] and list(g.bc) == [4.2, 9.2]
    assert list(g.bh) == [4.5, 9.5] and list(g.bl) == [-0.5, 4.5]
    assert list(g.ao) == [1.0, 6.0] and list(g.av) == [10.0, 10.0]
    assert C.heure_ny(g.index.values)[0] == pd.Timestamp("2024-06-03 09:30", tz=C.NY)


def test_m3_commence_a_9h30():
    g = C.agreger(_m1("2024-06-03 09:29", 5), "M3")
    assert [f"{t:%H:%M}" for t in C.heure_ny(g.index.values)] == ["09:27", "09:30", "09:33"]


@pytest.mark.parametrize("jour", ["2024-01-10", "2024-07-10"])        # hiver et été : même heure de New York
def test_h4_et_d1_ancres_sur_17h_new_york(jour):
    m1 = _m1(f"{jour} 16:00", 120)                                     # 16:00 -> 17:59 NY
    d1 = C.agreger(m1, "D1"); h4 = C.agreger(m1, "H4")
    assert [f"{t:%H:%M}" for t in C.heure_ny(d1.index.values)] == ["17:00", "17:00"]
    assert C.heure_ny(d1.index.values)[1] == pd.Timestamp(f"{jour} 17:00", tz=C.NY)
    assert [f"{t:%H:%M}" for t in C.heure_ny(h4.index.values)] == ["13:00", "17:00"]
    assert d1.bc.iloc[0] == 59.2 and d1.bo.iloc[1] == 60.0


def test_la_bougie_h4_de_9h_contient_l_ouverture():
    h4 = C.agreger(_m1("2024-03-11 08:58", 5), "H4")                   # lendemain du passage à l'heure d'été
    assert [f"{t:%H:%M}" for t in C.heure_ny(h4.index.values)] == ["05:00", "09:00"]


def test_la_periode_finale_est_verrouillee(monkeypatch):
    monkeypatch.delenv(C.VERROU_ENV, raising=False)
    idx = pd.DatetimeIndex(["2022-12-30 09:30", "2023-01-03 09:30"]).tz_localize(C.NY)
    df = pd.DataFrame({"bo": [1.0, 2.0]}, index=idx)
    assert len(C.decouper(df)) == 1
    with pytest.raises(C.PeriodeVerrouillee):
        C.decouper(df, finale=True)
    with pytest.raises(C.PeriodeVerrouillee):
        C.decouper(df, finale=True, motif="je veux voir")
    assert len(C.decouper(df, finale=True, motif="qualite des donnees")) == 2
    monkeypatch.setenv(C.VERROU_ENV, "ouverte")
    assert len(C.decouper(df, finale=True)) == 2


def test_periode_de():
    t = pd.DatetimeIndex(["2017-12-29 09:35", "2018-01-02 09:35", "2022-12-30 09:35", "2023-01-03 09:35"]).tz_localize(C.NY)
    assert list(C.periode_de(t)) == ["recherche", "verification", "verification", "finale"]


def test_resume_r():
    s = C.resume_r([1.0, -1.0, -1.0, 0.0, -1.0, 3.0])
    assert s["n"] == 6 and s["total"] == 1.0 and s["baisse"] == 3.0 and s["serie"] == 2
