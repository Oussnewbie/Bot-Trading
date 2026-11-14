"""Outils communs de l'étude des stops : chemins, heure de New York, reconstruction des horizons, verrou des périodes.

Conventions :
- Les fichiers Dukascopy sont en UTC ; l'horodatage d'une bougie est son DÉBUT.
- Heure de New York par la base de fuseaux (America/New_York) : l'heure d'été américaine est gérée, comme InpSrvDST.
- M3 à H1 : bougies alignées sur l'heure ronde (identiques à celles de Dukascopy et de MT5).
- H4 et D1 : alignées sur 17:00 New York, c'est-à-dire minuit du serveur MT5 de l'EA (GMT+2 l'hiver, heure d'été
  américaine). La bougie D1 va de 17:00 à 17:00 NY ; les H4 commencent à 17:00, 21:00, 1:00, 5:00, 9:00 et 13:00 NY.
- Les minutes sans cotation n'existent pas dans les fichiers (pas de bougies plates ajoutées).
- Les données sont les zips M1 de donnees/ (lus par backtest/nas100-10ans/load10.py). Les bougies reconstruites vont dans
  donnees/cache/bougies/, hors git.
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIES = os.path.join(ICI, "sorties")
RACINE = os.path.dirname(os.path.dirname(ICI))
SIMU = os.path.join(RACINE, "backtest", "nas100-10ans")
if SIMU not in sys.path:
    sys.path.insert(0, SIMU)
import load10  # noqa: E402

DONNEES = load10.DONNEES
BOUGIES = os.path.join(DONNEES, "cache", "bougies")

NY = "America/New_York"
INSTRUMENTS = load10.INSTRUMENTS
HORIZONS = {"M1": 1, "M3": 3, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
COLONNES = ["bo", "bh", "bl", "bc", "bv", "ao", "ah", "al", "ac", "av"]

# Décision du 2026-11-14 : l'étude et les données du dépôt vont du 2018-01-01 au 2026-11-13. Rien avant : les moyennes
# longues (MA200 en D1) n'existent donc qu'à partir de l'automne 2018.
DEBUT_ETUDE = pd.Timestamp("2018-01-01", tz=NY)

# Découpage anti-bruit (dates en heure de New York, borne de fin exclue). La période finale est celle de la demande.
# La coupe entre recherche et vérification (2021-01-01) est une PROPOSITION, à confirmer avant l'étape 2.
COUPE_VERIFICATION = "2021-01-01"
PERIODES = {
    "recherche": ("2018-01-01", COUPE_VERIFICATION),
    "verification": (COUPE_VERIFICATION, "2023-01-01"),
    "finale": ("2023-01-01", None),
}
DEBUT_FINALE = pd.Timestamp(PERIODES["finale"][0], tz=NY)
VERROU_ENV = "ETUDE_SL_FINALE"            # doit valoir « ouverte » pour lire la période finale dans une étude
MOTIFS_SANS_VERROU = ("qualite des donnees", "reference v5 non modifiee")


class PeriodeVerrouillee(RuntimeError):
    pass


def heure_ny(t_ms):
    """Horodatages UTC en millisecondes -> DatetimeIndex en heure de New York."""
    return pd.DatetimeIndex(pd.to_datetime(np.asarray(t_ms, dtype="int64"), unit="ms", utc=True)).tz_convert(NY)


def debuts_de_bougie(t_ms, horizon):
    """Début (UTC, ms) de la bougie `horizon` qui contient chaque minute de t_ms."""
    t_ms = np.asarray(t_ms, dtype="int64")
    n = HORIZONS[horizon]
    if n < 240:
        pas = n * 60_000
        return t_ms // pas * pas
    local = heure_ny(t_ms).tz_localize(None)                       # heure murale de New York
    debut = (local + pd.Timedelta(hours=7)).floor("4h" if horizon == "H4" else "1D") - pd.Timedelta(hours=7)
    utc = debut.tz_localize(NY, ambiguous=True, nonexistent="shift_forward").tz_convert("UTC")
    return utc.as_unit("ms").asi8


def agreger(m1, horizon):
    """m1 : tableau indexé par l'horodatage UTC en ms, colonnes COLONNES. Renvoie les bougies de l'horizon demandé."""
    if horizon == "M1":
        return m1
    cle = debuts_de_bougie(m1.index.values, horizon)
    g = m1.groupby(cle, sort=True)
    out = pd.DataFrame({
        "bo": g.bo.first(), "bh": g.bh.max(), "bl": g.bl.min(), "bc": g.bc.last(), "bv": g.bv.sum(),
        "ao": g.ao.first(), "ah": g.ah.max(), "al": g.al.min(), "ac": g.ac.last(), "av": g.av.sum(),
    })
    out.index.name = "t"
    return out


def chemin_bougies(instrument, horizon):
    return os.path.join(BOUGIES, f"{instrument}-{horizon}.npz")


def enregistrer(df, instrument, horizon):
    os.makedirs(BOUGIES, exist_ok=True)
    np.savez_compressed(chemin_bougies(instrument, horizon), t=df.index.values.astype("int64"), **{c: df[c].values for c in COLONNES})


def decouper(df, finale=False, motif=None):
    """Applique le verrou : sans autorisation, tout ce qui commence le 2023-01-01 (New York) ou après est retiré.
    finale=True n'est accepté que pour la qualité des données, la référence v5 non modifiée, ou si la variable
    d'environnement ETUDE_SL_FINALE vaut « ouverte » (test final, une seule fois)."""
    if not finale:
        return df[df.index < DEBUT_FINALE]
    if motif in MOTIFS_SANS_VERROU or os.environ.get(VERROU_ENV) == "ouverte":
        return df
    raise PeriodeVerrouillee(
        f"La période finale (2023 -> 2026) est verrouillée. Motifs permis : {MOTIFS_SANS_VERROU}, ou {VERROU_ENV}=ouverte.")


def lire_m1(instrument):
    """Le M1 du dépôt au format de l'étude : index = horodatage UTC en ms, colonnes COLONNES."""
    b, a = load10.lire_m1(instrument)
    m1 = pd.DataFrame({"bo": b.open, "bh": b.high, "bl": b.low, "bc": b.close, "bv": b.volume,
                       "ao": a.open, "ah": a.high, "al": a.low, "ac": a.close, "av": a.volume})
    m1.index.name = "t"
    return m1


def charger(instrument, horizon, finale=False, motif=None):
    """Bougies bid et ask d'un instrument (« nas100 » ou « or »), indexées en heure de New York.
    Par défaut la période finale n'est pas rendue (voir decouper)."""
    z = np.load(chemin_bougies(instrument, horizon))
    df = pd.DataFrame({c: z[c] for c in COLONNES}, index=heure_ny(z["t"]))
    return decouper(df, finale=finale, motif=motif)


def cotes(df):
    """(bid, ask) au format attendu par v5_lab.prep(data=...) : colonnes o, h, l, c, v."""
    b = df[["bo", "bh", "bl", "bc", "bv"]].copy(); b.columns = ["o", "h", "l", "c", "v"]
    a = df[["ao", "ah", "al", "ac", "av"]].copy(); a.columns = ["o", "h", "l", "c", "v"]
    return b, a


def periode_de(t):
    """Nom de la période (recherche, verification, finale) pour des dates en heure de New York."""
    t = pd.DatetimeIndex(t)
    j = t.tz_localize(None) if t.tz is not None else t
    return np.where(j < pd.Timestamp(COUPE_VERIFICATION), "recherche", np.where(j < pd.Timestamp("2023-01-01"), "verification", "finale"))


def resume_r(r, neutres=None):
    """Les cinq chiffres demandés pour une suite de résultats en R, dans l'ordre des trades."""
    r = np.asarray(r, dtype=float)
    if len(r) == 0:
        return dict(n=0, moy=np.nan, total=0.0, baisse=0.0, serie=0)
    eq = np.cumsum(r)
    baisse = (np.maximum.accumulate(np.maximum(eq, 0)) - eq).max()
    s = pire = 0
    for v in r:
        s = s + 1 if v < -0.05 else 0
        pire = max(pire, s)
    return dict(n=len(r), moy=r.mean(), total=r.sum(), baisse=baisse, serie=pire)


def ligne_r(nom, r):
    s = resume_r(r)
    if s["n"] == 0:
        return f"| {nom} | 0 | — | — | — | — |"
    return f"| {nom} | {s['n']} | {s['moy']:+.3f}R | {s['total']:+.1f}R | -{s['baisse']:.1f}R | {s['serie']} |"


ENTETE_R = "| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |\n|---|---|---|---|---|---|"
