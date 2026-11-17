"""Télécharge les données publiques dont la stratégie BTC a besoin, au format attendu par bitcoin/btc.py (brutes()) :
 - Bitstamp BTC/USD 1d et 4h (API publique v2/ohlc) -> donnees/crypto/historique/bitstamp-btcusd-{1d,4h}.csv
 - Coin Metrics (API communautaire) FlowInExNtv, FlowOutExNtv -> donnees/crypto/historique/coinmetrics-btc-2010.csv
 - Binance (data.binance.vision) klines 1h spot BTCUSDT et ETHBTC, financement BTCUSDT USDⓈ-M
Aucune clé. Rien n'est écrit dans le dépôt suivi par git (donnees/ est ignoré).
"""
import concurrent.futures as cf
import io
import json
import os
import time
import urllib.request
import zipfile

import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(RACINE, "donnees", "crypto")
H = os.path.join(D, "historique")
UA = {"User-Agent": "revue-backtest"}


def get(url, binaire=False, essais=5):
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
                return b if binaire else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(3 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    raise ConnectionError(url)


def bitstamp(step, nom):
    lignes, debut = [], int(pd.Timestamp("2011-08-01", tz="UTC").timestamp())
    fin = int(time.time())
    while debut < fin:
        j = get(f"https://www.bitstamp.net/api/v2/ohlc/btcusd/?step={step}&limit=1000&start={debut}")
        o = j["data"]["ohlc"]
        if not o:
            debut += step * 1000
            continue
        lignes += o
        dernier = int(o[-1]["timestamp"])
        if dernier + step <= debut:
            break
        debut = dernier + step
        time.sleep(0.3)
    d = pd.DataFrame(lignes).astype(float).drop_duplicates("timestamp").sort_values("timestamp")
    d["timestamp"] = d.timestamp.astype("int64")
    d[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(os.path.join(H, f"bitstamp-btcusd-{nom}.csv"), index=False)
    print("bitstamp", nom, len(d), pd.to_datetime(d.timestamp.iloc[0], unit="s"), pd.to_datetime(d.timestamp.iloc[-1], unit="s"))


def coinmetrics():
    url = ("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=FlowInExNtv,FlowOutExNtv"
           "&frequency=1d&start_time=2010-01-01&page_size=10000")
    rows = []
    while url:
        j = get(url)
        rows += j["data"]
        url = j.get("next_page_url")
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(H, "coinmetrics-btc-2010.csv"), index=False)
    print("coinmetrics", len(d), d.time.iloc[0], d.time.iloc[-1])


def mois(debut, fin):
    return [p.strftime("%Y-%m") for p in pd.period_range(debut, fin, freq="M")]


def vision(chemin_rel, nom_fichier, dest):
    os.makedirs(dest, exist_ok=True)
    cible = os.path.join(dest, nom_fichier.replace(".zip", ".csv"))
    if os.path.exists(cible):
        return True
    b = get(f"https://data.binance.vision/{chemin_rel}/{nom_fichier}", binaire=True)
    if b is None:
        return False
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        with z.open(z.namelist()[0]) as h, open(cible, "wb") as f:
            f.write(h.read())
    return True


def binance():
    taches = []
    for sym in ("BTCUSDT", "ETHBTC"):
        base = f"data/spot/monthly/klines/{sym}/1h"
        dest = os.path.join(D, "binance", "spot", "monthly", "klines", sym, "1h")
        for m in mois("2017-08", "2026-10"):
            taches.append((base, f"{sym}-1h-{m}.zip", dest))
        based = f"data/spot/daily/klines/{sym}/1h"
        destd = os.path.join(D, "binance", "spot", "daily", "klines", sym, "1h")
        for j in pd.date_range("2026-11-01", "2026-11-16"):
            taches.append((based, f"{sym}-1h-{j:%Y-%m-%d}.zip", destd))
    base = "data/futures/um/monthly/fundingRate/BTCUSDT"
    dest = os.path.join(D, "binance", "futures", "um", "monthly", "fundingRate", "BTCUSDT")
    for m in mois("2019-09", "2026-10"):
        taches.append((base, f"BTCUSDT-fundingRate-{m}.zip", dest))
    with cf.ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(lambda t: vision(*t), taches))
    manquants = [t[1] for t, o in zip(taches, ok) if not o]
    print("binance", sum(ok), "fichiers ;", len(manquants), "absents :", manquants[:20])


if __name__ == "__main__":
    os.makedirs(H, exist_ok=True)
    binance()
    coinmetrics()
    bitstamp(86400, "1d")
    bitstamp(14400, "4h")
