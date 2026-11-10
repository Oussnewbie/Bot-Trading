import os
import pandas as pd, numpy as np
# Unzip donnees/NAS100-M5-bid-ask-2015-2026.zip into donnees/ first (Dukascopy NAS100 CFD, M5, bid and ask, UTC).
DIR = os.environ.get("NAS100_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "donnees", "Data Bid and Ask 10y")) + os.sep
def load_side(side):
    d = pd.read_csv(DIR + f"usatechidxusd-m5-{side}-2015-01-01-2026-11-01.csv")
    d.index = pd.to_datetime(d.timestamp, unit="ms", utc=True).dt.tz_convert("America/New_York")
    d = d[["open", "high", "low", "close", "volume"]]
    d.columns = ["o", "h", "l", "c", "v"]
    return d
def load10():
    b = load_side("bid"); a = load_side("ask")
    return b, a
if __name__ == "__main__":
    b, a = load10()
    print("bid", b.shape, b.index[0], b.index[-1], "doublons", b.index.duplicated().sum())
    print("index identiques bid/ask :", b.index.equals(a.index))
    sp = (a.c - b.c)
    print("spread (points) médian par année :"); print(sp.groupby(sp.index.year).median().round(2).to_dict())
    print("spread à 03:00 et 09:45 NY (médiane 2025) :", sp[(sp.index.year == 2025) & (sp.index.hour == 3)].median().round(2), sp[(sp.index.year == 2025) & (sp.index.hour == 9) & (sp.index.minute == 45)].median().round(2))
    # bars par heure NY : la pause doit être 17:00-18:00 NY si le fuseau est bon
    x = b[b.index.year == 2025]
    wk = x[x.index.dayofweek < 4]
    print("nb de bougies par heure NY (lun-jeu 2025) :", wk.groupby(wk.index.hour).size().to_dict())
    print("volume nul :", (b.v == 0).mean().round(3), "bougies plates (h==l) :", (b.h == b.l).mean().round(3))
    gaps = b.index.to_series().diff()
    big = gaps[gaps > pd.Timedelta("3h")]
    print("trous > 3 h hors week-end :", (big.index.dayofweek != 6).sum(), "exemples", list(big[big.index.dayofweek != 6].index[:5]))
    print("premières bougies du dimanche (NY) :", b[b.index.dayofweek == 6].index[:3].tolist())
