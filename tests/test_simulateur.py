"""Tests du simulateur : pas d'information du futur, fuseau horaire, cache, et accord avec la réécriture des règles."""
import os

import numpy as np
import pandas as pd
import pytest

import orb_v5
import regles_readme as N
from conftest import NY, marche_aleatoire

# colonnes de la table des jours qui doivent être connues à 9:35 (« spread » lit l'ouverture de la bougie de 9:35 et
# « last » est l'indice de la dernière bougie du jour : elles ne servent à aucune décision d'entrée)
CONNUES_A_9H35 = ["orH", "orL", "orO", "orC", "orw", "preH", "preL", "pmH", "pmL", "rsi", "atr5", "atrd", "pdh", "pdl",
                  "pdc", "pdo", "prng", "nr", "rnk7", "gap", "or_atr", "or_med", "dow"]


def jour_de(X):
    return X.t.dt.tz_localize(None).dt.normalize()


# ───────────────────────── information du futur ─────────────────────────
def test_aucune_information_du_futur(labo):
    """On remplace toutes les bougies qui suivent la bougie de 9:30 d'un jour J par d'autres prix.
    Ce que le simulateur savait à 9:35 le jour J, et tous les trades des jours précédents, ne doivent pas bouger."""
    bid, ask = marche_aleatoire(n_jours=60, graine=7)
    bid2, ask2 = marche_aleatoire(n_jours=60, graine=8)
    jours = sorted(set(bid.index.tz_localize(None).normalize()))
    J = jours[40]
    coupe = pd.Timestamp(J.strftime("%Y-%m-%d") + " 09:30", tz=NY)
    apres = bid.index > coupe
    bid_m, ask_m = bid.copy(), ask.copy()
    bid_m[apres], ask_m[apres] = bid2[apres].values, ask2[apres].values

    D1 = labo.prep(data=(bid, ask)).copy()
    X1 = labo.run(orb_v5.V5, labo.f_v4)
    D2 = labo.prep(data=(bid_m, ask_m)).copy()
    X2 = labo.run(orb_v5.V5, labo.f_v4)

    a = D1[D1.day <= J].reset_index(drop=True)
    b = D2[D2.day <= J].reset_index(drop=True)
    assert len(a) == len(b) == 41
    pd.testing.assert_frame_equal(a[CONNUES_A_9H35], b[CONNUES_A_9H35])
    # même côté permis le jour J, avec ou sans le futur
    assert labo.f_v4(a.iloc[-1]) == labo.f_v4(b.iloc[-1])
    avant1 = X1[jour_de(X1) < J].reset_index(drop=True)
    avant2 = X2[jour_de(X2) < J].reset_index(drop=True)
    assert len(avant1) > 5
    pd.testing.assert_frame_equal(avant1, avant2)
    # contrôle du test lui-même : le futur a bien été changé
    assert not X1[jour_de(X1) > J].r.round(6).equals(X2[jour_de(X2) > J].r.round(6))


def test_simulateur_egal_aux_regles_du_readme_sur_un_marche_fabrique(labo):
    for graine in (1, 2, 3):
        bid, ask = marche_aleatoire(n_jours=120, graine=graine)
        labo.prep(data=(bid, ask))
        X = labo.run(orb_v5.V5, labo.f_v4)
        T = N.tous_les_trades(bid, ask)
        assert len(X) == len(T) and len(X) > 15
        assert list(jour_de(X)) == list(T.jour)
        assert list(X.d) == list(T.sens)
        np.testing.assert_allclose(X.r.values, T.r.values, atol=1e-9)


# ───────────────────────── fuseau horaire et heure d'été ─────────────────────────
def test_la_bougie_de_9h30_suit_l_heure_d_ete(tmp_path, monkeypatch):
    """Les fichiers sont en UTC. 9:30 à New York = 14:30 UTC en hiver et 13:30 UTC en été."""
    import load10
    utc = pd.DatetimeIndex(["2024-03-08 14:30", "2024-03-08 14:35",      # vendredi avant le passage à l'heure d'été
                            "2024-03-11 13:30", "2024-03-11 13:35",      # lundi après
                            "2024-11-01 13:30", "2024-11-04 14:30"], tz="UTC")   # avant et après le retour à l'heure d'hiver
    df = pd.DataFrame(dict(timestamp=utc.as_unit("ms").asi8, open=1.0, high=2.0, low=0.5, close=1.5, volume=1.0))
    for cote in ("bid", "ask"):
        df.to_csv(tmp_path / f"usatechidxusd-m5-{cote}.csv", index=False)
    monkeypatch.setattr(load10, "DIR", str(tmp_path) + os.sep)
    b, a = load10.load10()
    assert [str(t.time()) for t in b.index] == ["09:30:00", "09:35:00", "09:30:00", "09:35:00", "09:30:00", "09:30:00"]
    assert str(b.index.tz) == NY and list(b.columns) == ["o", "h", "l", "c", "v"]


# ───────────────────────── cache ─────────────────────────
def ecrire_csv(dossier, bid, ask):
    for cote, d in (("bid", bid), ("ask", ask)):
        out = pd.DataFrame(dict(timestamp=d.index.tz_convert("UTC").as_unit("ms").asi8, open=d.o.values, high=d.h.values,
                                low=d.l.values, close=d.c.values, volume=d.v.values))
        out.to_csv(os.path.join(dossier, f"usatechidxusd-m5-{cote}.csv"), index=False)


def test_le_cache_est_refait_quand_les_donnees_changent(labo, tmp_path, monkeypatch):
    import load10
    dossier = tmp_path / "csv"
    dossier.mkdir()
    monkeypatch.setattr(load10, "DIR", str(dossier) + os.sep)
    bid, ask = marche_aleatoire(n_jours=40, graine=3)
    ecrire_csv(dossier, bid, ask)
    D1 = labo.prep()
    assert len(D1) == 40
    assert os.path.exists(os.path.join(labo.CACHE_DIR, "v5_days.pkl"))
    assert len(labo.prep()) == 40                       # deuxième appel : relu depuis le cache
    bid, ask = marche_aleatoire(n_jours=25, graine=4)   # d'autres données, mêmes noms de fichiers
    ecrire_csv(dossier, bid, ask)
    D2 = labo.prep()
    assert len(D2) == 25, "le simulateur a rendu l'ancien résultat : cache périmé"
    assert len(labo.G["BC"]) == len(bid)


def test_le_cache_rend_le_meme_resultat_que_le_calcul(labo, tmp_path, monkeypatch):
    import load10
    dossier = tmp_path / "csv"
    dossier.mkdir()
    monkeypatch.setattr(load10, "DIR", str(dossier) + os.sep)
    bid, ask = marche_aleatoire(n_jours=40, graine=5)
    ecrire_csv(dossier, bid, ask)
    labo.prep()
    X1 = labo.run(orb_v5.V5, labo.f_v4)
    labo.G.clear()
    labo.prep()                                          # depuis le cache
    X2 = labo.run(orb_v5.V5, labo.f_v4)
    pd.testing.assert_frame_equal(X1, X2)


# ───────────────────────── premiers jours et stops impossibles ─────────────────────────
def test_les_premiers_jours_ne_sont_pas_ecartes(labo):
    """Les règles de la v5 n'ont pas besoin de l'ATR journalier : un jour sans 14 jours d'historique se trade aussi."""
    bid, ask = marche_aleatoire(n_jours=10, graine=11)
    D = labo.prep(data=(bid, ask))
    assert len(D) == 10 and D.atrd.isna().all()
    X = labo.run(orb_v5.V5, labo.f_v4)
    T = N.tous_les_trades(bid, ask)
    assert len(T) > 0 and len(X) == len(T)
    np.testing.assert_allclose(X.r.values, T.r.values, atol=1e-9)


def test_un_stop_sans_valeur_ne_donne_pas_de_trade(labo):
    """Variante de recherche « stop en ATR jour » un jour où l'ATR n'existe pas encore : pas de trade, pas de R « NaN »."""
    bid, ask = marche_aleatoire(n_jours=10, graine=11)
    labo.prep(data=(bid, ask))
    X = labo.run(dict(sl=("atr", 0.2)), labo.f_v4)
    assert len(X) == 0 or X.r.notna().all()


# ───────────────────────── données réelles du dépôt ─────────────────────────
def test_donnees_reelles_saines(donnees_reelles):
    b, a = donnees_reelles
    assert b.index.equals(a.index) and b.index.is_monotonic_increasing and not b.index.has_duplicates
    assert str(b.index[0].date()) == "2018-01-02" and str(b.index[-1].date()) == "2026-11-13"
    assert not b.isna().any().any() and not a.isna().any().any()
    for col in "ohlc":
        assert (a[col] >= b[col]).all(), "ask sous le bid"
    for d in (b, a):
        assert (d.h >= d[["o", "c"]].max(axis=1)).all() and (d.l <= d[["o", "c"]].min(axis=1)).all()
    # le fuseau est bon si la pause quotidienne tombe entre 17:00 et 18:00 à New York, toute l'année
    assert (b.index.hour != 17).all()


def test_reference_v5_sur_les_donnees_reelles(donnees_reelles, labo):
    """Le simulateur et la réécriture des règles donnent les mêmes trades sur 2018 → 2026-11 : chiffres de référence du README."""
    bid, ask = donnees_reelles
    labo.prep(data=(bid, ask))
    X = labo.run(orb_v5.V5, labo.f_v4)
    T = N.tous_les_trades(bid, ask)
    assert len(X) == len(T) == 1427
    assert list(jour_de(X)) == list(T.jour) and list(X.d) == list(T.sens)
    np.testing.assert_allclose(X.r.values, T.r.values, atol=1e-9)
    s = labo.stats(X)
    assert s["tot"] == pytest.approx(437.98, abs=0.01)
    assert s["dd"] == pytest.approx(24.65, abs=0.01)
    assert s["streak"] == 13
    par_periode = X.groupby("per").r.agg(["size", "sum"])
    assert par_periode.loc["B", "size"] == 50 and par_periode.loc["train", "size"] == 724 and par_periode.loc["A", "size"] == 653
    assert par_periode.loc["B", "sum"] == pytest.approx(23.14, abs=0.01)
    assert par_periode.loc["train", "sum"] == pytest.approx(248.81, abs=0.01)
    assert par_periode.loc["A", "sum"] == pytest.approx(166.03, abs=0.01)


def test_rien_avant_2018_n_est_lu(tmp_path, monkeypatch):
    """Un zip d'une année antérieure à 2018 déposé dans le dossier des données est ignoré."""
    import load10
    (tmp_path / "nas100").mkdir()
    for an in (2016, 2017, 2018, 2019):
        (tmp_path / "nas100" / f"usatechidxusd-m1-{an}.zip").write_bytes(b"")
    monkeypatch.setattr(load10, "DONNEES", str(tmp_path))
    assert [os.path.basename(z) for z in load10.zips("nas100")] == ["usatechidxusd-m1-2018.zip", "usatechidxusd-m1-2019.zip"]
