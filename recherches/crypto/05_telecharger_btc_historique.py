"""Historique long du bitcoin, pour juger le système sur des années JAMAIS utilisées par la recherche (2012-2017) :
- Bitstamp BTC/USD, bougies journalières et 4h, 2011-08 -> aujourd'hui (API publique, sans clé) ;
- Coin Metrics, on-chain journalier du BTC depuis 2010.
Sortie : donnees/crypto/historique/ (hors git). `--maj` retélécharge tout jusqu'à aujourd'hui (pour btc_jour.py).
"""
import json
import os
import sys
import time
import urllib.request

import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
X = os.path.join(ICI, "..", "..", "donnees", "crypto", "historique")
os.makedirs(X, exist_ok=True)


def get(url):
    for i in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-script"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


FIN = pd.Timestamp.now(tz="UTC").floor("D") + pd.Timedelta("1D")


def bitstamp(step, nom):
    out = os.path.join(X, f"bitstamp-btcusd-{nom}.csv")
    if os.path.exists(out) and "--maj" not in sys.argv:
        return
    debut = int(pd.Timestamp("2011-08-18", tz="UTC").timestamp())
    fin = int(FIN.timestamp())
    rows = []
    t = debut
    while t < fin:
        j = json.loads(get(f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit=1000&start={t}"))
        lot = j["data"]["ohlc"]
        if not lot:
            t += step * 1000
            continue
        rows += lot
        dernier = int(lot[-1]["timestamp"])
        t = dernier + step
        time.sleep(0.2)
    d = pd.DataFrame(rows).drop_duplicates("timestamp")
    d.to_csv(out, index=False)
    print(nom, len(d), pd.to_datetime(int(d.timestamp.iloc[0]), unit="s"), pd.to_datetime(int(d.timestamp.iloc[-1]), unit="s"))


def coinmetrics():
    out = os.path.join(X, "coinmetrics-btc-2010.csv")
    if os.path.exists(out) and "--maj" not in sys.argv:
        return
    url = ("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD,FlowInExNtv,"
           "FlowOutExNtv,CapMVRVCur,AdrActCnt&frequency=1d&start_time=2010-07-01&page_size=10000&format=csv")
    with open(out, "wb") as f:
        f.write(get(url))


if __name__ == "__main__":
    bitstamp(86400, "1d")
    bitstamp(14400, "4h")
    coinmetrics()
