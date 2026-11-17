"""Chargement des données de la recherche crypto (voir 00_telecharger.sh). Tout est en UTC, début de bougie.

- bougies(sym, marche, tf) : OHLCV Binance + volume acheteur agressif (taker buy) ; marche = "spot" ou "perp".
  tf = "1h", "4h", "1d"... (reconstruit à partir du 1h).
- financement(sym)         : taux de financement des perpétuels (toutes les 8 h).
- metriques(sym)           : open interest et ratios long/short (Binance, toutes les 5 min, 2021-12 ->), ramenés à l'heure.
- onchain(actif)           : Coin Metrics journalier ("btc" ou "eth").
- dukascopy(code, tf)      : bid et ask Dukascopy (btcusd, ethusd) pour mesurer le coût d'un CFD.
Cache parquet dans donnees/cache/.
"""
import glob
import os
import zipfile

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ICI, "donnees")
CACHE = os.path.join(D, "cache")
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count",
        "taker_buy_base", "taker_buy_quote", "ignore"]


def _cache(nom, fabrique):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, nom + ".pkl")
    if os.path.exists(p):
        return pd.read_pickle(p)
    df = fabrique()
    df.to_pickle(p)
    return df


def _lire_klines(fichiers):
    parts = []
    for f in fichiers:
        d = pd.read_csv(f, header=None, names=COLS, low_memory=False)
        if not str(d.iloc[0, 0]).isdigit():          # les fichiers récents ont un en-tête
            d = d.iloc[1:]
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    t = d.open_time.astype("int64")
    t = np.where(t > 10**14, t // 1000, t)          # spot : microsecondes depuis 2025
    d.index = pd.to_datetime(t, unit="ms", utc=True)
    d = d[["open", "high", "low", "close", "volume", "quote_volume", "count", "taker_buy_base"]].astype(float)
    d = d[~d.index.duplicated()].sort_index()
    return d


def _h1(sym, marche):
    racine = os.path.join(D, "binance", "spot" if marche == "spot" else "futures/um")
    fs = sorted(glob.glob(f"{racine}/monthly/klines/{sym}/1h/*.csv")) + sorted(glob.glob(f"{racine}/daily/klines/{sym}/1h/*.csv"))
    if not fs:
        raise FileNotFoundError(f"{sym} {marche}")
    return _cache(f"{sym}-{marche}-1h", lambda: _lire_klines(fs))


def regrouper(d, tf):
    if tf == "1h":
        return d
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "quote_volume": "sum",
           "count": "sum", "taker_buy_base": "sum"}
    r = d.resample(tf.replace("h", "h").replace("d", "D").replace("w", "W-MON"), label="left", closed="left").agg(agg)
    return r.dropna(subset=["close"])


def bougies(sym, marche="spot", tf="1h"):
    d = regrouper(_h1(sym, marche), tf)
    d["delta"] = 2 * d.taker_buy_base - d.volume       # achats agressifs - ventes agressives (en unités de l'actif)
    return d


def financement(sym):
    def f():
        fs = sorted(glob.glob(f"{D}/binance/futures/um/monthly/fundingRate/{sym}/*.csv"))
        d = pd.concat([pd.read_csv(x) for x in fs], ignore_index=True)
        d.index = pd.to_datetime(d.calc_time, unit="ms", utc=True).dt.floor("h")
        return d.last_funding_rate.astype(float).groupby(level=0).last().sort_index()
    return _cache(f"{sym}-funding", f)


def metriques(sym):
    def f():
        fs = sorted(glob.glob(f"{D}/binance/futures/um/daily/metrics/{sym}/*.csv"))
        d = pd.concat([pd.read_csv(x) for x in fs], ignore_index=True)
        d.index = pd.to_datetime(d.create_time, utc=True)
        d = d.drop(columns=["create_time", "symbol"]).astype(float)
        return d.resample("1h", label="left", closed="left").last()
    return _cache(f"{sym}-metrics", f)


def onchain(actif):
    def f():
        d = pd.read_csv(f"{D}/coinmetrics/{actif}.csv")
        d.index = pd.to_datetime(d.time, utc=True).dt.normalize()
        keep = [c for c in d.columns if c not in ("asset", "time") and "status" not in c]
        return d[keep].apply(pd.to_numeric, errors="coerce")
    return _cache(f"onchain-{actif}", f)


def dukascopy(code, tf="1h"):
    def f():
        out = {}
        for cote in ("bid", "ask"):
            parts = []
            for z in sorted(glob.glob(f"{D}/dukascopy/{code}/{code}-m1-*.zip")):
                with zipfile.ZipFile(z) as fz:
                    m = [n for n in fz.namelist() if f"-{cote}-" in n]
                    with fz.open(m[0]) as h:
                        parts.append(pd.read_csv(h))
            x = pd.concat(parts).drop_duplicates("timestamp").sort_values("timestamp")
            x.index = pd.to_datetime(x.timestamp, unit="ms", utc=True)
            x = x.resample("1h", label="left", closed="left").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
            out[cote] = x
        b, a = out["bid"], out["ask"]
        idx = b.index.intersection(a.index)
        return pd.concat({"bid": b.loc[idx], "ask": a.loc[idx]}, axis=1)
    d = _cache(f"duka-{code}-1h", f)
    return d
