"""Données du bot, récupérées à chaque cycle, sans clé d'API :
 - bougies Binance spot BTCUSDT (journalières et 4h, avec le volume acheteur agressif) et ETHBTC journalières, par le
   miroir public de données de marché de Binance (data-api.binance.vision : accessible même là où l'API de trading
   ne l'est pas) ;
 - flux des exchanges (on-chain) de Coin Metrics (API communautaire).
Elles sont mises dans le même format que les données historiques (`btc.brutes()`), puis coupées à l'instant présent : seules
les bougies CLÔTURÉES comptent (`btc.tronquer`).

`SourceHistorique` rejoue le passé avec les fichiers locaux, pour tester le bot de bout en bout sans réseau.
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # btc.py est dans ce dossier
import btc  # noqa: E402

KLINES = "https://data-api.binance.vision/api/v3/klines"
COINMETRICS = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def _get(url, essais=4):
    err = None
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "etrave-btc-bot"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(2 * (i + 1))
    raise ConnectionError(f"{url} : {err}")


def klines(symbole, intervalle, nombre):
    """Les `nombre` dernières bougies (la bougie en cours comprise ; elle est retirée plus tard)."""
    lignes = []
    fin = None
    while len(lignes) < nombre:
        lim = min(1000, nombre - len(lignes))
        url = f"{KLINES}?symbol={symbole}&interval={intervalle}&limit={lim}" + (f"&endTime={fin}" if fin else "")
        lot = _get(url)
        if not lot:
            break
        lignes = lot + lignes
        fin = lot[0][0] - 1
        if len(lot) < lim:
            break
    d = pd.DataFrame(lignes, columns=["t", "open", "high", "low", "close", "volume", "tf", "qv", "n", "taker", "tq", "x"])
    d.index = pd.to_datetime(d.t.astype("int64"), unit="ms", utc=True)
    d = d[["open", "high", "low", "close", "volume", "taker"]].astype(float)
    return d[~d.index.duplicated()].sort_index()


def onchain(jours=150):
    debut = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=jours)).strftime("%Y-%m-%d")
    j = _get(f"{COINMETRICS}?assets=btc&metrics=FlowInExNtv,FlowOutExNtv&frequency=1d&start_time={debut}&page_size=1000")
    d = pd.DataFrame(j["data"])
    d.index = pd.to_datetime(d.time, utc=True)
    return d[["FlowInExNtv", "FlowOutExNtv"]].apply(pd.to_numeric, errors="coerce")


class SourceLive:
    """Les données réelles, maintenant."""

    def charger(self, maintenant=None):
        maintenant = maintenant or pd.Timestamp.now(tz="UTC")
        d1 = klines("BTCUSDT", "1d", 1000)
        d4 = klines("BTCUSDT", "4h", 1500)        # assez pour que l'EMA200 4h soit identique au calcul complet
        eb = klines("ETHBTC", "1d", 200).close
        B = dict(d1=d1[["open", "high", "low", "close", "volume"]], d4=d4[["open", "high", "low", "close", "volume"]],
                 of=pd.DataFrame({"delta": 2 * d1.taker - d1.volume, "volume": d1.volume}),
                 eb=eb, oc=onchain(), fund=pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC")))
        return btc.tronquer(B, maintenant)


class SourceHistorique:
    """Le passé, avec les fichiers locaux de donnees/crypto/ (Binance pour les prix, comme en réel), coupé à l'instant
    demandé. Sert aux tests et au rejeu."""

    def __init__(self):
        import donnees as DN
        h = DN.bougies("BTCUSDT", "spot", "1h")
        agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "taker_buy_base": "sum"}
        d1 = h.resample("24h", origin="epoch").agg(agg).dropna(subset=["close"])
        d4 = h.resample("4h", origin="epoch").agg(agg).dropna(subset=["close"])
        oc = pd.read_csv(os.path.join(btc.H, "coinmetrics-btc-2010.csv"))
        oc.index = pd.to_datetime(oc.time, utc=True)
        self.B = dict(d1=d1[["open", "high", "low", "close", "volume"]], d4=d4[["open", "high", "low", "close", "volume"]],
                      of=pd.DataFrame({"delta": 2 * d1.taker_buy_base - d1.volume, "volume": d1.volume}),
                      eb=DN.bougies("ETHBTC", "spot", "1d").close,
                      oc=oc[["FlowInExNtv", "FlowOutExNtv"]].apply(pd.to_numeric, errors="coerce"),
                      fund=pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC")))

    def charger(self, maintenant):
        return btc.tronquer(self.B, maintenant)
