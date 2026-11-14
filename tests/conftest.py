"""Outils communs des tests : chemins, données réelles (dézippées au besoin) et marchés fabriqués à la main."""
import os
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMU = os.path.join(RACINE, "backtest", "nas100-10ans")
DONNEES = os.path.join(RACINE, "donnees")
ZIP = os.path.join(DONNEES, "NAS100-M5-bid-ask-2015-2026.zip")
CSV_DIR = os.path.join(DONNEES, "Data Bid and Ask 10y")
NY = "America/New_York"

for p in (SIMU, os.path.dirname(os.path.abspath(__file__))):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(scope="session")
def donnees_reelles():
    """Les bougies NAS100 du dépôt (bid, ask). Dézippe l'archive si besoin ; saute le test si elle manque."""
    import load10
    if not os.path.exists(load10.csv_path("bid")):
        if not os.path.exists(ZIP):
            pytest.skip("données absentes : donnees/NAS100-M5-bid-ask-2015-2026.zip")
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(DONNEES, [n for n in z.namelist() if n.endswith(".csv") and not n.startswith("__MACOSX")])
    return load10.load10()


@pytest.fixture()
def labo(tmp_path, monkeypatch):
    """Le simulateur v5_lab, avec son cache redirigé vers un dossier temporaire (les tests ne touchent pas au vrai)."""
    import v5_lab
    monkeypatch.setattr(v5_lab, "CACHE_DIR", str(tmp_path))
    return v5_lab


def index_jour(date, debut="08:00", fin="15:55"):
    return pd.date_range(f"{date} {debut}", f"{date} {fin}", freq="5min", tz=NY)


def jours_ouvres(premier, n):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(premier, periods=n)]


def avec_ask(bid, spread=1.0):
    ask = bid.copy()
    ask[["o", "h", "l", "c"]] = bid[["o", "h", "l", "c"]] + spread
    return bid, ask


def marche_aleatoire(n_jours=60, premier="2024-01-02", base=10000.0, bruit=4.0, spread=1.0, graine=1):
    """Marche aléatoire M5, de 8:00 à 15:55 New York, pour les tests qui n'ont pas besoin de vraies données."""
    rng = np.random.default_rng(graine)
    morceaux, px = [], base
    for d in jours_ouvres(premier, n_jours):
        idx = index_jour(d)
        n = len(idx)
        c = px + np.cumsum(rng.normal(0, bruit, n))
        o = np.concatenate([[px], c[:-1]])
        h = np.maximum(o, c) + rng.uniform(0, bruit, n)
        l = np.minimum(o, c) - rng.uniform(0, bruit, n)
        morceaux.append(pd.DataFrame(dict(o=o, h=h, l=l, c=c, v=1.0), index=idx))
        px = c[-1]
    return avec_ask(pd.concat(morceaux), spread)


def jours_calmes(n=20, premier="2024-01-02", base=10000.0):
    """n jours presque plats (le prix oscille de 0,5 point) : ils servent d'historique avant le jour du scénario."""
    morceaux = []
    for d in jours_ouvres(premier, n):
        idx = index_jour(d)
        c = base + 0.5 * (np.arange(len(idx)) % 2)
        o = np.concatenate([[base], c[:-1]])
        morceaux.append(pd.DataFrame(dict(o=o, h=np.maximum(o, c), l=np.minimum(o, c), c=c, v=1.0), index=idx))
    return pd.concat(morceaux)


def jour_scenario(date, bougies, base=10000.0):
    """Un jour écrit à la main. bougies : {"HH:MM": (o, h, l, c)} en prix bid.
    Avant la première bougie décrite : plat à « base ». Après la dernière : plat à sa clôture."""
    idx = index_jour(date)
    lignes, dernier = [], base
    for t in idx:
        cle = t.strftime("%H:%M")
        if cle in bougies:
            o, h, l, c = bougies[cle]
        else:
            o = h = l = c = dernier
        lignes.append((o, h, l, c, 1.0))
        dernier = c
    return pd.DataFrame(lignes, columns=["o", "h", "l", "c", "v"], index=idx)


JOUR_SCENARIO = "2024-01-30"   # le 21e jour ouvré après les 20 jours calmes


def marche_scenario(bougies, spread=1.0):
    return avec_ask(pd.concat([jours_calmes(), jour_scenario(JOUR_SCENARIO, bougies)]), spread)
