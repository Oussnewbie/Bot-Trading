"""Fabrique le fichier de travail du moteur à partir des CSV Dukascopy M1 (bid et ask).

Mêmes étapes que 01_charger_donnees.py de l'archive (Nasdaq) et 74_marches.py (autres marchés) :
- doublons d'horodatage retirés, puis seules les minutes présentes à la fois en bid et en ask sont gardées ;
- heure de New York (ou de la place du marché) : date, minute du jour, année, jour de la semaine ;
- pour un marché qui n'ouvre pas à 9:30, l'horloge est décalée pour que SON ouverture tombe à « 9:30 » (74_marches.py) ;
- aucune donnée n'est inventée : une minute absente reste absente.
Format de sortie : timestamp, date, minute, annee, dow, bo, bh, bl, bc, bv, ao, ah, al, ac, av (b = bid, a = ask).
"""
import glob
import os
import time

import pandas as pd

import sim_chemins as SC

COLONNES_CSV = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
COLONNES = ['timestamp', 'date', 'minute', 'annee', 'dow', 'bo', 'bh', 'bl', 'bc', 'bv', 'ao', 'ah', 'al', 'ac', 'av']


def fusionner_bid_ask(b, a, fuseau='America/New_York', ouverture=570):
    """b, a : tableaux Dukascopy M1 (timestamp en ms UTC, open, high, low, close, volume).
    ouverture : minute locale de l'ouverture de la séance (570 = 9:30) ; l'horloge est décalée de 570 - ouverture minutes."""
    b = b[COLONNES_CSV].drop_duplicates('timestamp').set_index('timestamp')
    a = a[COLONNES_CSV].drop_duplicates('timestamp').set_index('timestamp')
    m = b.join(a, how='inner', suffixes=('_b', '_a'))
    m.columns = ['bo', 'bh', 'bl', 'bc', 'bv', 'ao', 'ah', 'al', 'ac', 'av']
    m = m.reset_index()
    if not m.timestamp.is_monotonic_increasing:          # les CSV Dukascopy sont déjà dans l'ordre ; garde-fou seulement
        m = m.sort_values('timestamp', kind='stable').reset_index(drop=True)
    loc = pd.to_datetime(m.timestamp, unit='ms', utc=True).dt.tz_convert(fuseau)
    if ouverture != 570:
        loc = loc + pd.Timedelta(minutes=570 - ouverture)
    m['date'] = loc.dt.strftime('%Y-%m-%d')
    m['minute'] = (loc.dt.hour * 60 + loc.dt.minute).astype('int16')
    m['annee'] = loc.dt.year.astype('int16')
    m['dow'] = loc.dt.day_of_week.astype('int8')
    return m[COLONNES]


def csv_nasdaq(dossier=None):
    """Les deux CSV (bid, ask) du dossier brut ; il doit y en avoir exactement un de chaque."""
    dossier = dossier or SC.DOSSIER_BRUT
    fb = sorted(glob.glob(os.path.join(dossier, '*-bid-*.csv')))
    fa = sorted(glob.glob(os.path.join(dossier, '*-ask-*.csv')))
    if len(fb) != 1 or len(fa) != 1:
        raise FileNotFoundError(f"il faut exactement un CSV « -bid- » et un CSV « -ask- » dans {dossier} "
                                f"(trouvé : {len(fb)} bid, {len(fa)} ask). Réglage : BOT_TRADING_BRUT ou sim_chemins.py.")
    return fb[0], fa[0]


def lire_csv_nasdaq(dossier=None, nrows=None):
    """Lit les CSV bruts du Nasdaq (nrows : seulement les premières lignes, pour les tests) et les fusionne."""
    fb, fa = csv_nasdaq(dossier)
    return fusionner_bid_ask(pd.read_csv(fb, nrows=nrows), pd.read_csv(fa, nrows=nrows))


def construire_m1_nasdaq(dossier=None, sortie=None, bavard=True):
    """CSV bruts -> parquet de travail (écrit d'abord sous un nom temporaire, puis renommé)."""
    sortie = sortie or SC.M1_NASDAQ
    t0 = time.time()
    m = lire_csv_nasdaq(dossier)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    tmp = sortie + '.tmp'
    m.to_parquet(tmp, index=False)
    os.replace(tmp, sortie)
    if bavard:
        print(f'données : {len(m)} minutes bid + ask, du {m.date.iloc[0]} au {m.date.iloc[-1]} -> {sortie} ({time.time() - t0:.0f} s)')
    return sortie


def chemin_m1_nasdaq(construire=True):
    """Chemin du parquet de travail du Nasdaq ; le fabrique s'il manque (si construire=True)."""
    if not os.path.exists(SC.M1_NASDAQ):
        if not construire:
            raise FileNotFoundError(SC.M1_NASDAQ)
        construire_m1_nasdaq()
    return SC.M1_NASDAQ
