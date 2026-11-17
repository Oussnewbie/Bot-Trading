"""Tests du bot : python -m pytest bitcoin -q  (≈ 2 min ; les tests « historiques » ont besoin des données locales)."""
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import btc  # noqa: E402
from bot import Bot, DEFAUT, secrets  # noqa: E402
from courtier import Action, CourtierPapier, Etat, plan, prix_stop  # noqa: E402
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
    marge de la vente) et compare au calcul direct sur les mêmes prix : les deux doivent rester proches."""
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


# ───────────────────────── levier (montage perpétuel), stop, ordres limites ─────────────────────────
def test_plan_perpetuel_ouvre_en_perp_et_deplace_tout_le_capital():
    p = plan(Etat(50_000, 10_000, 0, 0, 0), 2.0, montage="perpetuel")
    assert [a.type for a in p.actions] == ["vers_futures", "perp"]
    assert p.actions[0].quantite == pytest.approx(10_000) and p.actions[1].quantite == pytest.approx(0.4)


def test_plan_perpetuel_retourne_la_position():
    e = Etat(50_000, 0, 0, 10_000, 0.4)
    a = plan(e, -0.5, montage="perpetuel").actions
    assert [x.type for x in a] == ["perp", "perp"]
    assert a[0].quantite == pytest.approx(-0.4) and "fermer" in a[0].motif
    assert a[1].quantite == pytest.approx(-0.1)


def test_plan_perpetuel_vend_le_btc_au_comptant_laisse_par_le_montage_x1():
    e = Etat(50_000, 0, 0.2, 0, 0)
    assert [x.type for x in plan(e, 2.0, montage="perpetuel").actions] == ["vendre_spot", "vers_futures", "perp"]


def test_stop_a_mi_chemin_de_la_liquidation():
    assert prix_stop(0.5, 60_000, "comptant") is None
    assert prix_stop(2.0, 60_000, "perpetuel") == pytest.approx(45_000)       # 25 % sous le prix à ×2
    assert prix_stop(-1.0, 60_000, "perpetuel") == pytest.approx(90_000)      # 50 % au-dessus pour une vente ×1


def test_papier_stop_touche_ferme_la_position():
    c = CourtierPapier(capital=10_000); c.fixer_prix(50_000)
    c.executer(Action("vers_futures", 10_000)); c.executer(Action("perp", 0.4))     # ×2
    c.poser_stop(prix_stop(2.0, 50_000, "perpetuel"))
    assert c.verifier_stop(51_000, 40_000) is None
    s = c.verifier_stop(51_000, 37_000)
    assert s and c.perp_btc == 0
    assert c.etat().capital == pytest.approx(10_000 - 0.4 * (50_000 - 37_500 * (1 - 0.005)), rel=0.01)


def test_ordres_limites_coutent_moins_en_perpetuel():
    m, l = CourtierPapier(capital=10_000, ordres="marche"), CourtierPapier(capital=10_000, ordres="limite")
    for c in (m, l):
        c.fixer_prix(50_000); c.executer(Action("vers_futures", 10_000)); c.executer(Action("perp", 0.2)); c.executer(Action("perp", -0.2, "fermer"))
    assert l.etat().capital > m.etat().capital


def test_le_levier_multiplie_la_cible(tmp_path):
    b1 = bot_test(tmp_path / "a")
    b3 = Bot(dict(DEFAUT, dossier=str(tmp_path / "b"), levier=3), source=SourceFixe(), courtier=CourtierPapier(capital=10_000))
    t = T("2026-02-20 04:01")
    d1, d3 = b1.cycle(t)["decision"], b3.cycle(t)["decision"]
    assert d3["cible"] == pytest.approx(3 * d1["cible"])
    assert b3.montage == "perpetuel" and b3.etat["stop"] is not None and b3.courtier.perp_btc > 0 and b3.courtier.btc_spot == 0


def test_maintenant_force_un_nouveau_cycle(tmp_path):
    b = bot_test(tmp_path)
    t = T("2026-02-20 04:01")
    b.cycle(t)
    assert b.cycle(t)["statut"] == "déjà traité"
    assert b.cycle(t, force=True)["statut"] == "ok"


def test_secrets_du_fichier_d_etrave(tmp_path, monkeypatch):
    monkeypatch.delenv("BINANCE_API_KEY", raising=False); monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    f = tmp_path / "s.json"
    f.write_text('{"binance_cle": "abc", "binance_secret": "def", "telegram_jeton": "1:x"}')
    s = secrets(dict(fichier_secrets=str(f)))
    assert s["cle"] == "abc" and s["secret"] == "def" and s["telegram_jeton"] == "1:x"
    monkeypatch.setenv("BINANCE_API_KEY", "env")
    assert secrets(dict(fichier_secrets=str(f)))["cle"] == "env"


class FauxExchange:
    """Imite ccxt : le 1er ordre limite est rempli à moitié, le 2e est refusé (il aurait été preneur), le 3e reste vide ;
    au bout des essais, le reste part au marché."""

    def __init__(self):
        self.ordres, self.n = {}, 0

    def amount_to_precision(self, sym, q):
        return f"{math.floor(q * 1000) / 1000:.3f}"

    def fetch_order_book(self, sym, n):
        return {"bids": [[49_990.0, 1]], "asks": [[50_010.0, 1]]}

    def create_order(self, sym, type_, cote, q, prix=None, params=None):
        self.n += 1
        if type_ == "limit":
            assert params.get("postOnly") is True
            if self.n == 2:
                raise RuntimeError("post-only refusé")
            rempli = q / 2 if self.n == 1 else 0.0
        else:
            rempli = q
        o = dict(id=str(self.n), type=type_, status="closed" if rempli == q else "open", filled=rempli, amount=q)
        self.ordres[o["id"]] = o
        return o

    def fetch_order(self, i, sym):
        return self.ordres[i]

    def cancel_order(self, i, sym):
        self.ordres[i]["status"] = "canceled"


def test_ordre_limite_puis_marche_pour_le_reste(monkeypatch):
    import courtier as C
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    cb = object.__new__(C.CourtierBinance)
    cb.ordres, cb.ESSAIS_LIMITE, cb.ATTENTE_S = "limite", 4, 0
    ex = FauxExchange()
    r = cb._ordre(ex, "BTC/USDT", "buy", 0.1)
    types = [o["type"] for o in ex.ordres.values()]
    assert types[0] == "limit" and types[-1] == "market"
    assert r["quantite"] == pytest.approx(0.1, abs=1e-3)
