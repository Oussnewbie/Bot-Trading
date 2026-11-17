"""Chargement des données Dukascopy NAS100 (USATECHIDXUSD), M1 bid et ask, en heure de New York.

Source : donnees/nas100/usatechidxusd-m1-AAAA.zip (extrait de afb79de). Horodatage = ouverture de la bougie, en ms UTC.
Sortie : un DataFrame M1 indexé en heure de New York (naïve), colonnes bo bh bl bc (bid) ao ah al ac (ask).
Cache : donnees/revue/nas100_m1.pkl (hors git).
"""
import glob
import os
import zipfile

import numpy as np
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RACINE, "donnees", "nas100")
CACHE = os.path.join(RACINE, "donnees", "revue")


def _lire(motif):
    parts = {"bid": [], "ask": []}
    for z in sorted(glob.glob(os.path.join(SRC, motif))):
        with zipfile.ZipFile(z) as fz:
            for n in fz.namelist():
                cote = "bid" if "-bid-" in n else "ask"
                with fz.open(n) as h:
                    parts[cote].append(pd.read_csv(h))
    out = {}
    for cote, p in parts.items():
        d = pd.concat(p).drop_duplicates("timestamp").sort_values("timestamp")
        d.index = pd.to_datetime(d.timestamp, unit="ms", utc=True)
        out[cote] = d[["open", "high", "low", "close", "volume"]].astype(float)
    return out


def m1(motif="usatechidxusd-m1-*.zip", cache=True):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "nas100_m1.pkl")
    if cache and motif == "usatechidxusd-m1-*.zip" and os.path.exists(p):
        return pd.read_pickle(p)
    o = _lire(motif)
    b, a = o["bid"], o["ask"]
    idx = b.index.intersection(a.index)
    b, a = b.loc[idx], a.loc[idx]
    d = pd.DataFrame({"bo": b.open, "bh": b.high, "bl": b.low, "bc": b.close, "bv": b.volume,
                      "ao": a.open, "ah": a.high, "al": a.low, "ac": a.close}, index=idx)
    d["utc"] = d.index
    d.index = d.index.tz_convert("America/New_York").tz_localize(None)
    if cache and motif == "usatechidxusd-m1-*.zip":
        d.to_pickle(p)
    return d


if __name__ == "__main__":
    d = m1()
    print(d.shape, d.index[0], d.index[-1])
    print(d.head())
    sp = d.ac - d.bc
    print("spread (ask-bid close) quantiles:", sp.quantile([0, .1, .5, .9, .99, 1]).round(3).to_dict())
