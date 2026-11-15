"""Banc de test commun à plusieurs instruments (Nasdaq, Dow Jones, or, EUR/USD, bitcoin) : données, indicateurs, moteur.

Mêmes conventions prudentes que backtest/nas100-10ans/v5_lab.py :
 - bougies M5 bid ET ask reconstruites du M1 Dukascopy : le spread réel est payé à l'entrée et à la sortie ;
 - un achat entre à l'ask et sort au bid, une vente entre au bid et sort à l'ask, plus un glissement par exécution ;
 - quand un stop et un gain sont possibles dans la même bougie, le stop gagne ; un stop déplacé ne vaut qu'à partir de
   la bougie suivante ; sur la bougie d'entrée seul le stop peut être touché ;
 - tout indicateur n'utilise que des bougies CLÔTURÉES (H1 et M15 : la dernière bougie terminée) ;
 - R = résultat de tout le trade (ajout compris) ÷ risque de départ (distance entrée-stop).

Périodes, comme pour la v5 : « train » = 2018-05 -> 2022-08 (toute recherche se fait là), « A » = 2022-09 -> 2026-11
(vérification, regardée une seule fois), « B » = 2018-01 -> 2018-04.
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), "nas100-10ans"))
import load10 as LD  # noqa: E402

NY = "America/New_York"
CACHE = os.path.join(LD.DONNEES, "cache", "multi")
T0, T1 = pd.Timestamp("2018-05-01"), pd.Timestamp("2022-09-01")
# Bitcoin : chez Dukascopy son spread vaut 1 à 1,8 % du prix en 2018-2020 et 0,05 à 0,35 % depuis 2022. Les années
# d'avant 2022 ne disent rien d'un courtier d'aujourd'hui : recherche sur 2022-01 -> 2024-06, vérification ensuite.
COUPES = {"bitcoin": (pd.Timestamp("2022-01-01"), pd.Timestamp("2024-07-01"))}


def periodes(nom, t):
    """« B » (avant la recherche, ignorée), « train » (recherche) ou « A » (vérification) pour chaque date d'entrée."""
    t0, t1 = COUPES.get(nom, (T0, T1))
    jour = t.dt.tz_localize(None)
    return np.where(jour < t0, "B", np.where(jour < t1, "train", "A"))
# Glissement par exécution, en unités de prix : environ 8 % du spread habituel en séance (0,1 point sur le Nasdaq,
# la valeur du simulateur de la v5).
GLISSEMENT = {"nas100": 0.1, "dow": 0.25, "or": 0.03, "eurusd": 0.00001, "bitcoin": 2.0}


def charger(nom):
    """Les bougies M5 d'un instrument : dict de tableaux (BO, BH, BL, BC, AO, AH, AL, AC, V) et le temps.
    Gardé dans donnees/cache/multi/ ; refait si un zip change."""
    fichiers = LD.zips(nom)
    if not fichiers:
        raise FileNotFoundError(f"aucune donnée pour « {nom} »")
    sig = "|".join(f"{os.path.basename(z)}:{os.path.getsize(z)}" for z in fichiers)
    chemin = os.path.join(CACHE, f"{nom}-m5.npz")
    if os.path.exists(chemin):
        z = np.load(chemin, allow_pickle=False)
        if str(z["sig"]) == sig:
            return _habiller(nom, {k: z[k] for k in z.files if k != "sig"})
    b, a = LD.lire_m1(nom)
    b5, a5 = LD.agreger(b, 5), LD.agreger(a, 5)
    g = dict(tms=b5.index.values.astype("int64"), V=b5.volume.values.astype("float64"))
    for cote, d in (("B", b5), ("A", a5)):
        for lettre, col in (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close")):
            g[cote + lettre] = d[col].values.astype("float64")
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(chemin, sig=np.array(sig), **g)
    return _habiller(nom, g)


def _habiller(nom, g):
    t = pd.DatetimeIndex(pd.to_datetime(g["tms"], unit="ms", utc=True)).tz_convert(NY)
    g["nom"] = nom
    g["t"] = t
    g["mins"] = (t.hour * 60 + t.minute).values
    g["jour"] = t.tz_localize(None).normalize().values          # date de New York de chaque bougie
    g["slip"] = GLISSEMENT[nom]
    g["n"] = len(t)
    return g


# ───────────────────────── repères de temps ─────────────────────────
def jours(g):
    """Les dates (New York) présentes dans les données."""
    return pd.DatetimeIndex(np.unique(g["jour"]))


def indice(g, dates, minute):
    """Pour chaque date, l'indice de la bougie qui commence à cette heure de New York (minutes depuis minuit ; négatif =
    la veille au soir), ou -1 si elle manque. L'heure est une heure d'horloge : l'heure d'été est respectée."""
    murale = dates + pd.Timedelta(minutes=int(minute))
    locale = murale.tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    ms = np.where(locale.isna(), -1, (locale.tz_convert("UTC").tz_localize(None).values.astype("datetime64[ms]").astype("int64")))
    pos = np.searchsorted(g["tms"], ms)
    pos = np.minimum(pos, g["n"] - 1)
    return np.where(g["tms"][pos] == ms, pos, -1)


def premier_apres(g, dates, minute):
    """Comme `indice`, mais la première bougie à cette heure OU après (pour une sortie : le marché peut être fermé)."""
    murale = dates + pd.Timedelta(minutes=int(minute))
    locale = murale.tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    ms = np.where(locale.isna(), -1, (locale.tz_convert("UTC").tz_localize(None).values.astype("datetime64[ms]").astype("int64")))
    return np.minimum(np.searchsorted(g["tms"], ms), g["n"] - 1)


# ───────────────────────── indicateurs (bougies clôturées uniquement) ─────────────────────────
def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values


def atr(g, n=14):
    pc = np.roll(g["BC"], 1); pc[0] = g["BC"][0]
    tr = np.maximum(g["BH"] - g["BL"], np.maximum(abs(g["BH"] - pc), abs(g["BL"] - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values


def horizon(g, minutes):
    """Bougies de `minutes` minutes (bid) et, pour chaque bougie M5, le rang de la dernière grande bougie TERMINÉE."""
    pas = minutes * 60_000
    cle = g["tms"] // pas
    s = pd.DataFrame({"k": cle, "o": g["BO"], "h": g["BH"], "l": g["BL"], "c": g["BC"]})
    gr = s.groupby("k", sort=True)
    grand = pd.DataFrame({"o": gr.o.first(), "h": gr.h.max(), "l": gr.l.min(), "c": gr.c.last()})
    rang = np.searchsorted(grand.index.values, cle) - 1        # la bougie en cours n'est pas terminée : on prend la précédente
    return grand, rang


def sur_m5(valeurs, rang):
    """Valeur d'un indicateur de grand horizon vue depuis chaque bougie M5 (dernière grande bougie terminée)."""
    v = np.asarray(valeurs, dtype="float64")
    return np.where(rang >= 0, v[np.maximum(rang, 0)], np.nan)


def biais_ma200_h1(g):
    """+1 si la dernière bougie H1 terminée clôture au-dessus de sa moyenne mobile 200, -1 en dessous, 0 sinon."""
    h1, rang = horizon(g, 60)
    ma = h1.c.rolling(200).mean()
    b = np.sign(h1.c - ma).fillna(0).values
    return sur_m5(b, rang)


def macd_m15(g, rapide=12, lent=26, signal=9):
    """Sur les bougies M15 terminées : +1 à la bougie où le MACD passe au-dessus de son signal, -1 en dessous."""
    m15, rang = horizon(g, 15)
    ligne = m15.c.ewm(span=rapide, adjust=False).mean() - m15.c.ewm(span=lent, adjust=False).mean()
    hist = (ligne - ligne.ewm(span=signal, adjust=False).mean()).values
    croise = np.zeros(len(hist))
    croise[1:] = np.where((hist[1:] > 0) & (hist[:-1] <= 0), 1, np.where((hist[1:] < 0) & (hist[:-1] >= 0), -1, 0))
    nouveau = np.zeros(g["n"], dtype=bool)
    nouveau[1:] = rang[1:] != rang[:-1]                          # première bougie M5 après la clôture d'une M15
    return np.where(nouveau, sur_m5(croise, rang), 0), sur_m5(hist, rang)


def centre_de_gravite(g, minutes=15, fenetre=120, degre=3):
    """Centre de gravité « Belkhayate » : valeur, à la dernière bougie, d'une régression polynomiale sur `fenetre`
    bougies, et écart-type des écarts au centre. Calculé bougie après bougie (pas de repeinte), puis vu depuis le M5."""
    grand, rang = horizon(g, minutes)
    x = np.arange(fenetre)
    A = np.vander(x, degre + 1)
    poids = (np.vander([fenetre - 1], degre + 1) @ np.linalg.pinv(A)).ravel()     # valeur ajustée au dernier point
    c = grand.c.values
    centre = np.full(len(c), np.nan)
    if len(c) >= fenetre:
        centre[fenetre - 1:] = np.convolve(c, poids[::-1], mode="valid")
    ecart = pd.Series(c - centre).rolling(fenetre).std().values
    return sur_m5(centre, rang), sur_m5(ecart, rang), rang


def vwap_depuis(g, debut):
    """VWAP ancré : depuis l'indice `debut[i]` de chaque jour (-1 = pas de séance), prix typique pondéré par le volume
    coté de Dukascopy (ce n'est pas un volume de marché). Retourne le VWAP et son écart-type pondéré, par bougie."""
    typ = (g["BH"] + g["BL"] + g["BC"]) / 3
    vol = np.maximum(g["V"], 1e-9)
    ancre = np.zeros(g["n"], dtype=bool)
    ancre[debut[debut >= 0]] = True
    groupe = np.cumsum(ancre)
    pv, v, pv2 = (pd.Series(x).groupby(groupe).cumsum().values for x in (typ * vol, vol, typ * typ * vol))
    vw = pv / v
    sd = np.sqrt(np.maximum(pv2 / v - vw * vw, 0))
    avant = groupe == 0
    vw[avant] = np.nan; sd[avant] = np.nan
    return vw, sd


# ───────────────────────── moteur : un trade ─────────────────────────
def _premier(masque):
    i = int(np.argmax(masque))
    return i if masque[i] else -1


def jouer(g, k, d, entree, stop, fin, be=None, tp=None, pyr=None):
    """Déroule un trade entré à la bougie k (prix `entree`, glissement déjà compté), stop à `stop`, sorti au plus tard à
    l'ouverture de la bougie `fin`. be = seuil en R du stop au prix d'entrée ; tp = objectif en R ;
    pyr = (seuil en R à la clôture, distance en R du stop commun sous le prix de l'ajout). Retourne (R, bougie de sortie)."""
    slip = g["slip"]
    if d == 1:
        O, ADV, FAV, C, CA = g["BO"], g["BL"], g["BH"], g["BC"], g["AC"]
    else:
        O, ADV, FAV, C, CA = g["AO"], g["AH"], g["AL"], g["AC"], g["BC"]
    risque = abs(entree - stop)
    if not risque > 0 or fin <= k:
        return None
    unites = [(entree, 1.0)]
    pos = k
    be_fait = be is None
    pyr_fait = pyr is None
    lvl_tp = entree + d * tp * risque if tp else None

    def total(px):
        return sum(t * (px - e) * d for e, t in unites) / risque

    while True:
        adv = ADV[pos:fin]
        s = _premier((adv - stop) * d <= 0)
        b = p = t = -1
        if not be_fait:
            a0 = max(pos, k + 1)
            if a0 < fin:
                x = _premier((FAV[a0:fin] - (entree + d * be * risque)) * d >= 0)
                b = x + a0 - pos if x >= 0 else -1
        if not pyr_fait and fin - 1 > pos:
            x = _premier((C[pos:fin - 1] - (entree + d * pyr[0] * risque)) * d >= 0)
            p = x
        if lvl_tp is not None:
            a0 = max(pos, k + 1)
            if a0 < fin:
                x = _premier((FAV[a0:fin] - lvl_tp) * d >= 0)
                t = x + a0 - pos if x >= 0 else -1
        suivants = [x for x in (s, b, p, t) if x >= 0]
        if not suivants:
            j = min(fin, g["n"] - 1)
            return total(O[j] - d * slip), j
        premier = min(suivants)
        j = pos + premier
        if s == premier:                                        # le stop d'abord, toujours
            px = min(stop, O[j]) if d == 1 else max(stop, O[j])
            return total(px - d * slip), j
        if t == premier:
            return total(lvl_tp), j
        if p == premier:                                        # ajout au marché à la clôture de la bougie j
            prix_ajout = CA[j] + d * slip
            unites.append((prix_ajout, 1.0))
            nouveau = prix_ajout - d * pyr[1] * risque
            stop = max(stop, nouveau) if d == 1 else min(stop, nouveau)
            pyr_fait = be_fait = True
        else:                                                   # +be R atteint : stop au prix d'entrée dès la bougie suivante
            stop = max(stop, entree) if d == 1 else min(stop, entree)
            be_fait = True
        pos = j + 1
        if pos >= fin:
            j = min(fin, g["n"] - 1)
            return total(O[j] - d * slip), j


def derouler(g, ordres, **gestion):
    """ordres : liste de (k, d, entree, stop, fin). Retourne la table des trades : t, r, d, per."""
    lignes = []
    for k, d, entree, stop, fin in ordres:
        res = jouer(g, int(k), int(d), float(entree), float(stop), int(fin), **gestion)
        if res is not None:
            lignes.append((g["t"][int(k)], res[0], int(d)))
    x = pd.DataFrame(lignes, columns=["t", "r", "d"])
    x["per"] = periodes(g["nom"], x.t) if len(x) else []
    return x


def stats(x, per=None):
    """Nombre de trades, R moyen, total, t de Student, pire baisse en R, années positives."""
    if per is not None:
        x = x[x.per.isin([per] if isinstance(per, str) else per)]
    n = len(x)
    if n < 2:
        return dict(n=n, mean=0.0, tot=0.0, t=0.0, dd=0.0, ypos="0/0", win=0.0)
    r = x.r.values
    cum = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(np.maximum(cum, 0)) - cum))
    an = x.groupby(x.t.dt.year).r.sum()
    sd = r.std(ddof=1)
    return dict(n=n, mean=float(r.mean()), tot=float(r.sum()), t=float(r.mean() / sd * np.sqrt(n)) if sd > 0 else 0.0, dd=dd,
                ypos=f"{int((an > 0).sum())}/{len(an)}", win=float((r > 0.05).mean()))
