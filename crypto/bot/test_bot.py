"""Tests du bot : python -m pytest crypto/bot -q  (≈ 2 min ; les tests « historiques » ont besoin des données locales)."""
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.dirname(ICI))
import btc  # noqa: E402
from bot import Bot, DEFAUT  # noqa: E402
from courtier import Action, CourtierPapier, Etat, plan  # noqa: E402
from strategie import PROFILS, decider  # noqa: E402

T = lambda s: pd.Timestamp(s, tz="UTC")
DONNEES = os.path.exists(os.path.join(btc.H, "coinmetrics-btc-2010.csv"))
historique = pytest.mark.skipif(not DONNEES, reason="données locales absentes")


# ───────────────────────── plan d'ordres ─────────────────────────
def test_plan_ouvre_un_achat():
    p = plan(Etat(50_000, 10_000, 0, 0, 0), 0.5)
    assert [a.type for a in p.actions] == ["acheter_spot"]
    assert p.actions[0].quantite == pytest.approx(0.1)


def test_plan_ne_bouge_pas_dans_la_bande():
    e = Etat(50_000, 5_200, 0.096, 0, 0)            # exposition 48 %
    assert plan(e, 0.50, bande=0.05).actions == []
    assert plan(e, 0.60, bande=0.05).actions[0].type == "acheter_spot"


def test_plan_passe_de_l_achat_a_la_vente_dans_le_bon_ordre():
    e = Etat(50_000, 0, 0.2, 0, 0)                  # 10 000 $ tout en BTC
    types = [a.type for a in plan(e, -0.25).actions]
    assert types == ["vendre_spot", "vers_futures", "perp"]
    a = plan(e, -0.25).actions
    assert a[1].quantite == pytest.approx(2_500)    # marge = taille de la vente (levier 1)
    assert a[2].quantite == pytest.approx(-0.05)


def test_plan_ferme_la_vente_et_rapatrie_la_marge():
    e = Etat(40_000, 7_500, 0, 2_500, -0.0625)
    types = [a.type for a in plan(e, 0.0).actions]
    assert types == ["perp", "vers_spot"]
    assert plan(e, 0.0).actions[0].quantite == pytest.approx(0.0625)


def test_plan_ferme_toujours_meme_petit():
    e = Etat(50_000, 9_700, 0.006, 0, 0)            # 3 % d'exposition, sous la bande
    assert [a.type for a in plan(e, 0.0).actions] == ["vendre_spot"]


# ───────────────────────── compte papier ─────────────────────────
def test_papier_achat_vente_frais():
    c = CourtierPapier(capital=10_000); c.fixer_prix(50_000)
    c.executer(Action("acheter_spot", 0.1))
    c.fixer_prix(55_000)
    c.executer(Action("vendre_spot", c.btc_spot))
    gain_brut = 0.1 * 5_000
    assert 10_000 + gain_brut - 25 < c.etat().capital < 10_000 + gain_brut


def test_papier_vente_gagne_quand_le_prix_baisse():
    c = CourtierPapier(capital=10_000); c.fixer_prix(50_000)
    c.executer(Action("vers_futures", 2_500)); c.executer(Action("perp", -0.05))
    c.fixer_prix(45_000)
    assert c.etat().capital == pytest.approx(10_000 + 0.05 * 5_000, abs=5)     # gain latent
    c.executer(Action("perp", 0.05, "fermer la vente")); c.executer(Action("vers_spot", 1e9))
    assert c.perp_btc == 0 and c.usdt_futures == pytest.approx(0)
    assert c.etat().capital == pytest.approx(10_000 + 250, abs=5)


def test_papier_vente_perd_quand_le_prix_monte():
    c = CourtierPapier(capital=10_000); c.fixer_prix(50_000)
    c.executer(Action("vers_futures", 2_500)); c.executer(Action("perp", -0.05))
    c.fixer_prix(60_000)
    c.executer(Action("perp", 0.05, "fermer la vente"))
    assert c.etat().capital == pytest.approx(10_000 - 500, abs=5)


# ───────────────────────── garde-fous ─────────────────────────
class SourceFixe:
    """Données figées (300 jours de hausse régulière) pour tester le bot sans réseau."""

    def __init__(self, prix=50_000.0):
        j = pd.date_range("2025-01-01", periods=420, freq="1D", tz="UTC")
        h = pd.date_range("2025-01-01", periods=420 * 6, freq="4h", tz="UTC")
        c1 = pd.Series(np.linspace(20_000, prix, len(j)), index=j)
        c4 = pd.Series(np.linspace(20_000, prix, len(h)), index=h)
        mk = lambda c: pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 100.0})
        self.B = dict(d1=mk(c1), d4=mk(c4), of=pd.DataFrame({"delta": 10.0, "volume": 100.0}, index=j),
                      eb=pd.Series(np.linspace(0.05, 0.06, len(j)), index=j),
                      oc=pd.DataFrame({"FlowInExNtv": 100.0, "FlowOutExNtv": 120.0}, index=j),
                      fund=pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC")))

    def charger(self, t):
        return btc.tronquer(self.B, t)


def bot_test(tmp_path, **cfg):
    c = dict(DEFAUT, dossier=str(tmp_path), **cfg)
    return Bot(c, source=SourceFixe(), courtier=CourtierPapier(capital=10_000))


def test_cycle_achete_en_tendance_haussiere_et_ne_rejoue_pas(tmp_path):
    b = bot_test(tmp_path)
    t = T("2026-02-20 04:01")
    r = b.cycle(t)
    assert r["decision"]["sens"] == "ACHAT" and r["exposition"] > 0.2
    assert b.cycle(t)["statut"] == "déjà traité"
    assert os.path.exists(os.path.join(tmp_path, "journal.csv"))


def test_pause_et_fermer(tmp_path):
    b = bot_test(tmp_path)
    open(os.path.join(tmp_path, "PAUSE"), "w").close()
    r = b.cycle(T("2026-02-20 04:01"))
    assert r["execs"] == [] and r["exposition"] == 0
    os.remove(os.path.join(tmp_path, "PAUSE"))
    b.cycle(T("2026-02-20 08:01"))
    open(os.path.join(tmp_path, "FERMER"), "w").close()
    r = b.cycle(T("2026-02-20 12:01"))
    assert abs(r["exposition"]) < 0.01 and os.path.exists(os.path.join(tmp_path, "PAUSE"))


def test_coupe_circuit(tmp_path):
    b = bot_test(tmp_path, perte_max=0.10)
    b.cycle(T("2026-02-20 04:01"))
    b.etat["pic"] = 20_000                               # le capital a fondu de moitié depuis son plus haut
    r = b.cycle(T("2026-02-20 08:01"))
    assert abs(r["exposition"]) < 0.01 and b.etat.get("arrete")
    assert b.cycle(T("2026-02-20 12:01"))["statut"] == "arrêté"


def test_refuse_des_donnees_en_retard(tmp_path):
    b = bot_test(tmp_path)
    r = b.cycle(T("2026-06-01 04:01"))                 # les données s'arrêtent fin février
    assert r["statut"] == "données invalides"


# ───────────────────────── parité avec le test historique ─────────────────────────
@historique
def test_le_bot_decide_exactement_comme_le_backtest():
    from donnees_live import SourceHistorique
    S = SourceHistorique()
    E = btc.elements(S.B)
    pos = btc.position(E, seuil=0.25, confirmation="ema50/200", **{k: PROFILS["prudent"][k] for k in ("vente", "vol_cible")})
    rng = np.random.default_rng(3)
    idx = E["c4"].index[(E["c4"].index > T("2019-01-01")) & (E["c4"].index < T("2026-11-10"))]
    for t0 in rng.choice(idx, 20, replace=False):
        t0 = pd.Timestamp(t0)
        maintenant = t0 + pd.Timedelta("4h") + pd.Timedelta("90s")
        d = decider(S.charger(maintenant), "prudent", maintenant)
        assert d["bougie_4h"] == t0
        assert d["cible"] == pytest.approx(min(pos.loc[t0], 1.0), abs=1e-12), t0


@historique
def test_rejeu_execution_2018_2026_proche_du_backtest():
    """Rejoue les décisions du système bougie par bougie avec le compte papier (frais, glissement, bande de 5 %,
    marge de la vente) et compare au backtest : l'exécution ne doit pas détruire l'avantage."""
    from donnees_live import SourceHistorique
    S = SourceHistorique()
    E = btc.elements(S.B)
    pos = btc.position(E, seuil=0.25, confirmation="ema50/200", vente=0.25, vol_cible=0.4)
    c4 = E["c4"]
    m = (c4.index >= T("2018-01-01"))
    c = CourtierPapier(capital=10_000)
    eq = []
    for t, px, cible in zip(c4.index[m], c4.values[m], pos.values[m]):
        c.fixer_prix(px, t + pd.Timedelta("4h"))
        for a in plan(c.etat(), float(cible), 0.05).actions:
            c.executer(a)
        eq.append(c.etat().capital)
    eq = pd.Series(eq, index=c4.index[m])
    j = eq.resample("1D").last().pct_change().dropna()
    sh_bot = j.mean() / j.std() * np.sqrt(365)
    cagr_bot = (eq.iloc[-1] / eq.iloc[0]) ** (365 / (eq.index[-1] - eq.index[0]).days) - 1
    # backtest (frais 0,12 %, sans bande) sur les mêmes prix Binance
    r = c4.pct_change().fillna(0).values[m]
    p = np.r_[0.0, pos.values[m][:-1]]
    net = pd.Series(p * r - np.abs(np.diff(np.r_[0.0, p])) * 0.0012, index=c4.index[m])
    jb = (1 + net).resample("1D").prod() - 1
    sh_bt = jb.mean() / jb.std() * np.sqrt(365)
    print(f"\nrejeu 2018-2026 : Sharpe bot {sh_bot:.2f} / backtest {sh_bt:.2f} ; gain par an bot {cagr_bot:.1%} ;"
          f" pire baisse bot {(eq / eq.cummax() - 1).min():.1%}")
    assert sh_bot > 1.0 and abs(sh_bot - sh_bt) < 0.25


@historique
def test_concordance_prix_bitstamp_et_binance():
    """Le test long utilise Bitstamp, le bot Binance : les positions doivent presque toujours concorder."""
    from donnees_live import SourceHistorique
    Eb = btc.elements(SourceHistorique().B)
    Es = btc.elements(btc.brutes())
    pb = btc.position(Eb, **btc.FINAL); ps = btc.position(Es, **btc.FINAL)
    i = pb.index.intersection(ps.index)
    i = i[i >= T("2018-06-01")]
    accord = (np.sign(pb[i]) == np.sign(ps[i])).mean()
    print(f"\nmême sens de position Binance / Bitstamp : {accord:.1%}")
    assert accord > 0.9
