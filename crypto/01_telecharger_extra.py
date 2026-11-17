"""Données supplémentaires (hors git, crypto/donnees/extra/) :
- Binance : indice de prime des perpétuels (premiumIndexKlines 1h) BTC et ETH, 2020-01 ->
- Coinbase : bougies 1h BTC-USD et ETH-USD (prime Coinbase = Coinbase / Binance - 1 : demande américaine)
- alternative.me : indice Fear & Greed journalier (2018-02 ->)
- Deribit : indice de volatilité implicite DVOL journalier BTC et ETH (2021-03 ->)
- DefiLlama : capitalisation totale des stablecoins, journalière
Aucune clé d'API.
"""
import io
import json
import os
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
X = os.path.join(ICI, "donnees", "extra")
os.makedirs(X, exist_ok=True)


def get(url, essais=5):
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-script"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == essais - 1:
                raise
            time.sleep(2 * (i + 1))


def premium(sym):
    out = os.path.join(X, f"{sym}-premium-1h.csv")
    if os.path.exists(out):
        return
    mois = [p.strftime("%Y-%m") for p in pd.period_range("2020-01", "2026-10", freq="M")]

    def un(m):
        try:
            z = get(f"https://data.binance.vision/data/futures/um/monthly/premiumIndexKlines/{sym}/1h/{sym}-1h-{m}.zip")
        except Exception:  # noqa: BLE001
            return None
        with zipfile.ZipFile(io.BytesIO(z)) as f:
            d = pd.read_csv(f.open(f.namelist()[0]), header=None)
        if not str(d.iloc[0, 0]).isdigit():
            d = d.iloc[1:]
        return d.iloc[:, :5]
    with ThreadPoolExecutor(8) as ex:
        parts = [p for p in ex.map(un, mois) if p is not None]
    jours = pd.date_range("2026-11-01", "2026-11-16").strftime("%Y-%m-%d")

    def unj(j):
        try:
            z = get(f"https://data.binance.vision/data/futures/um/daily/premiumIndexKlines/{sym}/1h/{sym}-1h-{j}.zip")
        except Exception:  # noqa: BLE001
            return None
        with zipfile.ZipFile(io.BytesIO(z)) as f:
            d = pd.read_csv(f.open(f.namelist()[0]), header=None)
        if not str(d.iloc[0, 0]).isdigit():
            d = d.iloc[1:]
        return d.iloc[:, :5]
    with ThreadPoolExecutor(8) as ex:
        parts += [p for p in ex.map(unj, jours) if p is not None]
    d = pd.concat(parts)
    d.columns = ["t", "open", "high", "low", "close"]
    d.astype(float).drop_duplicates("t").sort_values("t").to_csv(out, index=False)


def coinbase(prod):
    out = os.path.join(X, f"coinbase-{prod}-1h.csv")
    if os.path.exists(out):
        return
    debut, fin = pd.Timestamp("2017-08-01", tz="UTC"), pd.Timestamp("2026-11-17", tz="UTC")
    bornes = pd.date_range(debut, fin, freq="300h")

    def un(a):
        b = min(a + pd.Timedelta(hours=300), fin)
        u = (f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=3600"
             f"&start={a.isoformat()}&end={b.isoformat()}")
        for i in range(6):
            try:
                return json.loads(get(u))
            except Exception:  # noqa: BLE001
                time.sleep(3 * (i + 1))
        return []
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(un, bornes))
    rows = [r for x in res for r in x]
    d = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"]).drop_duplicates("t").sort_values("t")
    d.to_csv(out, index=False)


def fng():
    out = os.path.join(X, "fear-greed.csv")
    if not os.path.exists(out):
        j = json.loads(get("https://api.alternative.me/fng/?limit=0&format=json"))
        d = pd.DataFrame(j["data"])[["timestamp", "value"]]
        d.to_csv(out, index=False)


def dvol(cur):
    out = os.path.join(X, f"dvol-{cur}.csv")
    if os.path.exists(out):
        return
    rows = []
    fin = int(pd.Timestamp("2026-11-17", tz="UTC").timestamp() * 1000)
    a = int(pd.Timestamp("2021-01-01", tz="UTC").timestamp() * 1000)
    while a < fin:
        b = min(a + 900 * 86400_000, fin)
        j = json.loads(get(f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={cur}"
                           f"&start_timestamp={a}&end_timestamp={b}&resolution=86400"))
        rows += j["result"]["data"]
        a = b
    pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"]).drop_duplicates("t").to_csv(out, index=False)


def stablecoins():
    out = os.path.join(X, "stablecoins.csv")
    if not os.path.exists(out):
        j = json.loads(get("https://stablecoins.llama.fi/stablecoincharts/all"))
        d = pd.DataFrame([{"t": int(x["date"]), "usd": x.get("totalCirculatingUSD", {}).get("peggedUSD")} for x in j])
        d.to_csv(out, index=False)


if __name__ == "__main__":
    for f, a in [(fng, ()), (stablecoins, ()), (dvol, ("BTC",)), (dvol, ("ETH",)), (premium, ("BTCUSDT",)),
                 (premium, ("ETHUSDT",)), (coinbase, ("BTC-USD",)), (coinbase, ("ETH-USD",))]:
        t = time.time()
        f(*a)
        print(f.__name__, a, f"{time.time() - t:.0f} s", flush=True)
