"""Données du dépôt : M1 bid et ask Dukascopy, un zip par année dans donnees/<instrument>/ (UTC, début de bougie),
du 2018-01-01 au 2026-11-13. Instruments : « nas100 » (usatechidxusd) et « or » (xauusd).

- lire_m1(nom)  : le M1 bid et ask d'un instrument, sur les minutes présentes des deux côtés.
- load10()      : le M5 bid et ask du Nasdaq CFD pour le simulateur v5_lab, indexé en heure de New York.
  Le M5 est reconstruit à partir du M1 et gardé dans donnees/cache/ ; il est refait si un zip change.
"""
import glob
import os
import zipfile

import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DONNEES = os.environ.get("ORB_DONNEES", os.path.join(RACINE, "donnees"))
INSTRUMENTS = {"nas100": "usatechidxusd", "or": "xauusd"}
DIR = os.environ.get("NAS100_DIR", os.path.join(DONNEES, "cache")) + os.sep     # dossier du M5 reconstruit
ANNEE_DEBUT = 2018      # décision du 2026-11-14 : rien avant 2018 n'est lu, même si un zip plus ancien traîne dans le dossier


def zips(nom):
    tous = sorted(glob.glob(os.path.join(DONNEES, nom, f"{INSTRUMENTS[nom]}-m1-*.zip")))
    return [z for z in tous if int(os.path.basename(z)[:-4].rsplit("-", 1)[1]) >= ANNEE_DEBUT]


def lire_m1(nom):
    """(bid, ask) en M1, indexés par l'horodatage UTC en millisecondes, colonnes open, high, low, close, volume.
    Seules les minutes présentes des deux côtés sont gardées : bid et ask ont le même index."""
    morceaux = {"bid": [], "ask": []}
    fichiers = zips(nom)
    if not fichiers:
        raise FileNotFoundError(f"aucun zip M1 pour « {nom} » dans {os.path.join(DONNEES, nom)}")
    for z in fichiers:
        with zipfile.ZipFile(z) as f:
            for cote in morceaux:
                membre = [n for n in f.namelist() if f"-m1-{cote}-" in n and n.endswith(".csv")]
                if len(membre) != 1:
                    raise ValueError(f"{z} : un seul fichier {cote} attendu, trouvé {membre}")
                with f.open(membre[0]) as h:
                    morceaux[cote].append(pd.read_csv(h))
    b, a = (pd.concat(morceaux[c], ignore_index=True).drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
            for c in ("bid", "ask"))
    commun = b.index.intersection(a.index)
    return b.loc[commun], a.loc[commun]


def agreger(d, minutes):
    """M1 -> bougies de `minutes` minutes alignées sur l'heure ronde (UTC)."""
    pas = minutes * 60_000
    g = d.groupby(d.index.values // pas * pas, sort=True)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(), "volume": g.volume.sum()})
    out.index.name = "timestamp"
    return out


def csv_path(side):
    """Fichier M5 d'un côté. Dans le dossier par défaut, il est reconstruit s'il manque ou si un zip est plus récent."""
    p = DIR + f"usatechidxusd-m5-{side}.csv"
    z = zips("nas100")
    if not os.path.exists(p) or (z and os.path.getmtime(p) < max(os.path.getmtime(x) for x in z)):
        b, a = lire_m1("nas100")
        os.makedirs(DIR, exist_ok=True)
        for cote, d in (("bid", b), ("ask", a)):
            agreger(d, 5).to_csv(DIR + f"usatechidxusd-m5-{cote}.csv")
    return p


def load_side(side):
    d = pd.read_csv(csv_path(side))
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
    x = b[b.index.year == 2025]
    wk = x[x.index.day_of_week < 4]
    print("nb de bougies par heure NY (lun-jeu 2025) :", wk.groupby(wk.index.hour).size().to_dict())
    print("bougies plates (h==l) :", (b.h == b.l).mean().round(3))
