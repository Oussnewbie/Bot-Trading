"""BTC seul, biais corrigés. Le système complet est recalculé à partir des données brutes, pour pouvoir :
 - le juger sur 2012-2017, années JAMAIS utilisées par les recherches précédentes (Bitstamp) ;
 - choisir ses réglages AUTOMATIQUEMENT, chaque année, avec le passé seul (walk-forward) : plus aucun choix humain
   après avoir vu les résultats ;
 - mesurer la probabilité de surajustement (PBO, Bailey-Borwein-López de Prado-Zhu) sur toute la grille ;
 - le comparer à des règles simples (MA200, EMA 50/200) : s'il ne les bat pas, la règle simple gagne ;
 - vérifier qu'il ne regarde jamais le futur (audit par troncature) ;
 - donner des intervalles de confiance (bootstrap par blocs), la sensibilité à la date de départ et aux frais.

Données :
 - prix Bitstamp BTC/USD journalier et 4h (2011-08 -> 2026-11), les mêmes sur toute la période ;
 - volume acheteur agressif Binance (2017-08 ->), ETH/BTC Binance (2017-08 ->), on-chain Coin Metrics (2011 ->),
   financement des perpétuels Binance (2020 ->).
Un vote dont la donnée n'existe pas encore (order flow et ETH/BTC avant 2017) est ABSENT : le score est la moyenne
des votes disponibles.
Coûts : 0,30 % par côté avant 2017 (frais de l'époque 0,25 % + glissement), 0,12 % ensuite. Vente : financement réel
depuis 2020, 10 % par an de coût d'emprunt avant.
"""
import itertools
import os

import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I

H = os.path.join(DN.D, "historique")
DEBUT = pd.Timestamp("2012-07-01", tz="UTC")       # après 200 jours de chauffe
NOUVEAU = (DEBUT, pd.Timestamp("2018-01-01", tz="UTC"))
ANCIEN = (pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2026-11-17", tz="UTC"))


# ───────────────────────── données brutes ─────────────────────────
def _bitstamp(nom):
    d = pd.read_csv(os.path.join(H, f"bitstamp-btcusd-{nom}.csv"))
    d.index = pd.to_datetime(d.timestamp, unit="s", utc=True)
    return d[["open", "high", "low", "close", "volume"]].astype(float).sort_index()


def brutes():
    d1, d4 = _bitstamp("1d"), _bitstamp("4h")
    oc = pd.read_csv(os.path.join(H, "coinmetrics-btc-2010.csv"))
    oc.index = pd.to_datetime(oc.time, utc=True)
    oc = oc[["FlowInExNtv", "FlowOutExNtv"]].apply(pd.to_numeric, errors="coerce")
    bn = DN.bougies("BTCUSDT", "spot", "1d")
    of = pd.DataFrame({"delta": bn.delta, "volume": bn.volume})
    eb = DN.bougies("ETHBTC", "spot", "1d").close
    fund = DN.financement("BTCUSDT")
    return dict(d1=d1, d4=d4, oc=oc, of=of, eb=eb, fund=fund)


def tronquer(B, t):
    """Les données telles qu'on les avait à l'instant t (pour l'audit anti-futur)."""
    return dict(d1=B["d1"][B["d1"].index + pd.Timedelta("1D") <= t], d4=B["d4"][B["d4"].index + pd.Timedelta("4h") <= t],
                oc=B["oc"][B["oc"].index + pd.Timedelta("2D") <= t], of=B["of"][B["of"].index + pd.Timedelta("1D") <= t],
                eb=B["eb"][B["eb"].index + pd.Timedelta("1D") <= t], fund=B["fund"][B["fund"].index <= t])


# ───────────────────────── le système ─────────────────────────
def votes(B):
    d = B["d1"]; c = d.close; idx = d.index
    ich = I.ichimoku(d, 9, 26, 52)
    haut, bas = np.maximum(ich["spanA"], ich["spanB"]), np.minimum(ich["spanA"], ich["spanB"])
    m, s, _ = I.macd(c)
    hh, ll = d.high.rolling(90).max(), d.low.rolling(90).min()
    sgn = lambda x: np.sign(x).where(x.notna())
    etat = lambda a, b: pd.Series(np.where(a, 1.0, np.where(b, -1.0, 0.0)), index=idx)
    v = pd.DataFrame(index=idx)
    v["ma200"] = sgn(c - I.sma(c, 200))
    v["ichimoku"] = etat(c > haut, c < bas).where(haut.notna())
    v["macd"] = sgn(m - s)
    v["rsi"] = sgn(I.rsi(c, 14) - 50)
    v["vwap"] = sgn(c - I.vwap_ancre(d, "M"))
    v["fibonacci"] = etat(c > ll + 0.618 * (hh - ll), c < ll + 0.382 * (hh - ll)).where(hh.notna())
    of = B["of"].reindex(idx)
    v["orderflow"] = sgn(of.delta.rolling(7).sum() / of.volume.rolling(7).sum())
    oc = B["oc"].copy(); oc.index = oc.index + pd.Timedelta("2D")
    net = (oc.FlowInExNtv - oc.FlowOutExNtv).rolling(30).mean()
    pos = np.searchsorted(net.index.values, (idx + pd.Timedelta("1D")).values, side="right") - 1
    netv = pd.Series(np.where(pos >= 0, net.values[np.maximum(pos, 0)], np.nan), index=idx)
    v["onchain"] = -sgn(netv)
    eb = B["eb"].reindex(idx)
    v["ethbtc"] = sgn(eb - I.sma(eb, 50))
    return v


def caler(serie_j, idx):
    dispo = serie_j.index + pd.Timedelta("1D")
    pos = np.searchsorted(dispo.values, idx.values, side="right") - 1
    return pd.Series(np.where(pos >= 0, serie_j.values[np.maximum(pos, 0)], np.nan), index=idx)


def elements(B):
    """Tout ce qui ne dépend pas des réglages : score journalier, volatilité, tendances 4h."""
    v = votes(B)
    score = v.mean(axis=1, skipna=True)
    r = B["d1"].close.pct_change()
    vol = r.rolling(30).std() * np.sqrt(365)
    d4 = B["d4"]; c4 = d4.close
    e20, e50, e200 = I.ema(c4, 20), I.ema(c4, 50), I.ema(c4, 200)
    conf = {"aucune": (pd.Series(True, index=d4.index), pd.Series(True, index=d4.index)),
            "ema50/200": ((e50 > e200) & (c4 > e200), (e50 < e200) & (c4 < e200)),
            "ema20/50": ((e20 > e50) & (c4 > e50), (e20 < e50) & (c4 < e50))}
    return dict(votes=v, score4=caler(score, d4.index), vol4=caler(vol, d4.index), conf=conf, c4=c4,
                score=score)


def position(E, seuil=0.25, confirmation="ema50/200", vente=0.25, vol_cible=0.4):
    sc, dose = E["score4"], (vol_cible / E["vol4"]).clip(upper=1)
    ch, cb = E["conf"][confirmation]
    achat = ((sc >= seuil) & ch).astype(float) * dose
    vend = ((sc <= -seuil) & cb).astype(float) * dose * vente
    return (achat - vend).fillna(0)


REGLAGES = [dict(seuil=s, confirmation=cf, vente=k, vol_cible=vc)
            for s, cf, k, vc in itertools.product((0.0, 0.15, 0.25, 0.35, 0.5), ("aucune", "ema50/200", "ema20/50"),
                                                  (0.0, 0.25, 0.5), (0.3, 0.4, 0.5))]
FINAL = dict(seuil=0.25, confirmation="ema50/200", vente=0.25, vol_cible=0.4)


# ───────────────────────── rendements ─────────────────────────
class Banc4h:
    def __init__(self, B, c4, frais=1.0):
        self.c = c4
        self.r = c4.pct_change().fillna(0).values
        idx = c4.index
        self.cout = np.where(idx < pd.Timestamp("2017-01-01", tz="UTC"), 0.0030, 0.0012) * frais
        f = B["fund"]
        g = np.searchsorted(idx.values, f.index.values, side="right") - 1
        fb = pd.Series(f.values).groupby(g).sum()
        fund = np.zeros(len(idx))
        ok = fb.index[fb.index >= 0]
        fund[ok] = fb.loc[ok].values
        avant = idx < pd.Timestamp("2020-01-01", tz="UTC")
        fund[avant] = -0.10 / 365 / 6          # avant 2020 : un vendeur paie ~10 %/an pour emprunter (signe : voir net)
        self.fund = fund
        self.jour = idx.floor("D")

    def journalier(self, pos):
        p = np.asarray(pos, dtype=float)
        t = np.r_[0.0, p[:-1]]
        chg = np.abs(np.diff(np.r_[0.0, t]))
        net = t * self.r - chg * self.cout
        # financement : acheteur en perp n'est pas compté (achat au comptant) ; vendeur reçoit le financement positif
        net = net + np.where(t < 0, -t * self.fund, 0.0)
        return pd.Series(net, index=self.jour).groupby(level=0).apply(lambda x: (1 + x).prod() - 1)


def stats(y):
    y = y.dropna()
    if len(y) < 30 or y.std() == 0:
        return dict(sharpe=np.nan, cagr=np.nan, mdd=np.nan)
    eq = (1 + y).cumprod()
    return dict(sharpe=y.mean() / y.std() * np.sqrt(365), cagr=eq.iloc[-1] ** (365 / len(y)) - 1,
                mdd=(eq / eq.cummax() - 1).min())


def periode(y, a, b):
    return y[(y.index >= a) & (y.index < b)]
