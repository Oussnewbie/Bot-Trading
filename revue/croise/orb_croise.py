"""Backtest indépendant d'ORB v6 (Nasdaq), modèle de l'EA, écrit à partir des seules règles du README.

Usage : python orb_croise.py [dossier_donnees] [fichier_sortie.csv]
"""
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).resolve().parent
DONNEES = Path(sys.argv[1]) if len(sys.argv) > 1 else ICI.parents[1] / "donnees" / "nas100"
SORTIE = Path(sys.argv[2]) if len(sys.argv) > 2 else ICI / "trades_croise.csv"
TZ = "America/New_York"


# --------------------------------------------------------------------------- données
def charger():
    morceaux = []
    for zp in sorted(DONNEES.glob("usatechidxusd-m1-*.zip")):
        an = zp.stem.split("-")[-1]
        with zipfile.ZipFile(zp) as z:
            b = pd.read_csv(z.open(f"usatechidxusd-m1-bid-{an}.csv"))
            a = pd.read_csv(z.open(f"usatechidxusd-m1-ask-{an}.csv"))
        b = b.drop(columns="volume").rename(columns=lambda c: c if c == "timestamp" else "b" + c)
        a = a.drop(columns="volume").rename(columns=lambda c: c if c == "timestamp" else "a" + c)
        morceaux.append(b.merge(a, on="timestamp", how="outer"))
    df = pd.concat(morceaux).drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    utc = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["utc"] = utc
    df["ny"] = utc.dt.tz_convert(TZ).dt.tz_localize(None)
    return df


def rsi_wilder(close, n=14):
    close = np.asarray(close, float)
    d = np.diff(close)
    g = np.where(d > 0, d, 0.0)
    l = np.where(d < 0, -d, 0.0)
    out = np.full(len(close), np.nan)
    if len(d) < n:
        return out
    ag, al = g[:n].mean(), l[:n].mean()
    def val(ag, al):
        return 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    out[n] = val(ag, al)
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + g[i]) / n
        al = (al * (n - 1) + l[i]) / n
        out[i + 1] = val(ag, al)
    return out


def rsi_m5(df):
    """RSI14 de Wilder sur les clôtures M5 bid, série continue (toutes les bougies)."""
    bid = df.dropna(subset=["bclose"])
    seau = bid["utc"].dt.floor("5min")  # décalage NY entier en heures : même découpage qu'en heure locale
    m5 = bid.groupby(seau)["bclose"].last()
    rsi = pd.Series(rsi_wilder(m5.values), index=m5.index.tz_convert(TZ).tz_localize(None))
    return rsi


# --------------------------------------------------------------------------- calendrier
def nieme_jour(an, mois, jour_sem, n):
    d = date(an, mois, 1)
    d += timedelta(days=(jour_sem - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def dernier_jour(an, mois, jour_sem):
    d = date(an, mois + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - jour_sem) % 7)


def paques(an):
    a, b, c = an % 19, an // 100, an % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois = (h + l - 7 * m + 114) // 31
    jour = (h + l - 7 * m + 114) % 31 + 1
    return date(an, mois, jour)


def observe(d):
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def jours_courts(an):
    """Jours fériés (observés) et demi-séances de l'année `an` : sortie à 12:45."""
    j = set()
    j.add(observe(date(an, 1, 1)))
    if date(an + 1, 1, 1).weekday() == 5:          # 1er janvier suivant un samedi -> 31 décembre
        j.add(date(an, 12, 31))
    j.add(nieme_jour(an, 1, 0, 3))                 # MLK
    j.add(nieme_jour(an, 2, 0, 3))                 # Presidents' Day
    j.add(paques(an) - timedelta(days=2))          # vendredi saint
    j.add(dernier_jour(an, 5, 0))                  # Memorial Day
    j.add(observe(date(an, 6, 19)))                # Juneteenth, toutes les années
    j.add(observe(date(an, 7, 4)))
    j.add(nieme_jour(an, 9, 0, 1))                 # Labor Day
    tg = nieme_jour(an, 11, 3, 4)                  # Thanksgiving
    j.add(tg)
    j.add(observe(date(an, 12, 25)))
    # demi-séances
    j.add(tg + timedelta(days=1))
    j.add(date(an, 12, 24))
    wd4 = date(an, 7, 4).weekday()
    if 1 <= wd4 <= 4:
        j.add(date(an, 7, 3))
    if wd4 == 5:
        j.add(date(an, 7, 2))
    return j


# --------------------------------------------------------------------------- simulation
def minute(t):
    return t.hour * 60 + t.minute


def simuler_jour(jour, mins, bo, bh, bl, bc, ao, ah, al, ac, rsi, fin, stats):
    """mins : minute du jour (NY) de chaque ligne, triées, de 9:00 à fin-1."""
    i930 = np.searchsorted(mins, 570)
    if i930 >= len(mins) or mins[i930] != 570:
        return None
    rng_idx = np.where((mins >= 570) & (mins < 575))[0]
    hi = np.nanmax(bh[rng_idx])
    lo = np.nanmin(bl[rng_idx])
    rng = hi - lo
    if not rng > 0:
        stats["range_nul"] += 1
        return None
    pre = np.where((mins >= 540) & (mins < 570))[0]
    nb_m5_pre = len(set(mins[pre] // 5))
    if nb_m5_pre < 2:
        stats["elan_moins_de_2_bougies"] += 1
        return None
    pre_hi = np.nanmax(bh[pre])
    pre_lo = np.nanmin(bl[pre])
    achat_ok = rsi > 50 and hi > pre_hi
    vente_ok = rsi < 50 and lo < pre_lo
    if not (achat_ok or vente_ok):
        return None

    # --- ordres 9:35:00 - 9:44:59
    sens = 0
    e = None
    for i in np.where((mins >= 575) & (mins < 585))[0]:
        t_achat = ah[i] >= hi
        t_vente = bl[i] <= lo
        if not (t_achat or t_vente):
            continue
        if t_achat and t_vente:
            d_achat = hi - ao[i]
            d_vente = bo[i] - lo
            premier = 1 if d_achat <= d_vente else -1   # égalité : achat d'abord
            stats["deux_cotes_meme_minute"] += 1
        else:
            premier = 1 if t_achat else -1
        if (premier == 1 and achat_ok) or (premier == -1 and vente_ok):
            sens, e = premier, i
        else:
            stats["cote_bloque_touche"] += 1
        break
    if sens == 0:
        return None

    if sens == 1:
        entree = max(hi, ao[e])
        stop0 = lo
    else:
        entree = min(lo, bo[e])
        stop0 = hi
    R = abs(entree - stop0)
    unites = [(entree, 1.0)]
    stop = stop0
    be = pyr = False
    sortie = None
    raison = "fin de journée"
    seau_entree = mins[e] // 5
    n = len(mins)

    i = e
    while i < n:
        # 1) stop dans la minute
        if sens == 1:
            if bl[i] <= stop:
                sortie = stop if i == e else min(stop, bo[i])
        else:
            if ah[i] >= stop:
                sortie = stop if i == e else max(stop, ao[i])
        if sortie is not None:
            raison = "stop"
            break
        # 2) fin de journée
        if i == n - 1:
            sortie = bc[i] if sens == 1 else ac[i]
            break
        # 3) clôture d'une bougie M5
        seau = mins[i] // 5
        if mins[i + 1] // 5 != seau:
            nouveau_stop = None
            if not pyr:
                cl = bc[i] if sens == 1 else ac[i]
                if (cl - entree) * sens >= 2 * R:
                    # ajout au prix d'ouverture de la minute suivante (< heure de sortie par construction)
                    j = i + 1
                    p_ajout = ao[j] if sens == 1 else bo[j]
                    unites.append((p_ajout, 2.0))
                    pyr = True
                    nouveau_stop = p_ajout - sens * R
                    if (nouveau_stop - stop) * sens < 0:
                        stats["pyramide_baisse_stop"] += 1
            if nouveau_stop is None and not be and seau > seau_entree:
                idx = np.where(mins[: i + 1] // 5 == seau)[0]
                meilleur = np.nanmax(bh[idx]) if sens == 1 else np.nanmin(al[idx])
                if (meilleur - entree) * sens >= 1.5 * R and (entree - stop) * sens > 0:
                    nouveau_stop = entree
                    be = True
            if nouveau_stop is not None:
                stop = nouveau_stop
        i += 1

    res = sum((sortie - p) * sens * q for p, q in unites) / rng
    return dict(jour=jour.isoformat(), sens=sens, entree=round(entree, 3), stop0=round(stop0, 3),
                range=round(rng, 3), R=round(res, 4), be=int(be), pyramide=int(pyr),
                raison_sortie=raison)


def main():
    df = charger()
    rsi = rsi_m5(df)
    df = df.dropna(subset=["bopen", "aopen"]).reset_index(drop=True)
    ny = df["ny"]
    df["jour"] = ny.dt.date
    df["min"] = ny.dt.hour * 60 + ny.dt.minute
    courts = set()
    for an in range(2017, 2028):
        courts |= jours_courts(an)
    stats = dict(range_nul=0, elan_moins_de_2_bougies=0, deux_cotes_meme_minute=0,
                 cote_bloque_touche=0, pyramide_baisse_stop=0, jours_sautes=0, jours_courts_trades=0)
    trades = []
    seance = df[(df["min"] >= 540) & (df["min"] < 950)]
    for jour, g in seance.groupby("jour"):
        if jour.weekday() >= 5:
            continue
        fin = 765 if jour in courts else 950
        g = g[g["min"] < fin]
        mins = g["min"].to_numpy()
        if 570 not in mins:
            stats["jours_sautes"] += 1
            continue
        r = rsi.get(pd.Timestamp(jour) + pd.Timedelta(minutes=570), np.nan)
        a = [g[c].to_numpy(float) for c in ("bopen", "bhigh", "blow", "bclose", "aopen", "ahigh", "alow", "aclose")]
        t = simuler_jour(jour, mins, *a, r, fin, stats)
        if t:
            trades.append(t)
            if jour in courts:
                stats["jours_courts_trades"] += 1
    out = pd.DataFrame(trades)
    out.to_csv(SORTIE, index=False)

    R = out["R"]
    print(f"trades {len(out)}  R moyen {R.mean():.4f}  R total {R.sum():.2f}  "
          f"gagnants {(R > 0.05).mean():.1%}  pyramides {out.pyramide.sum()}  stops à l'entrée {out.be.sum()}")
    print("sorties :", out.raison_sortie.value_counts().to_dict(), " sens :", out.sens.value_counts().to_dict())
    print("R par année :", out.groupby(out.jour.str[:4])["R"].agg(["count", "sum", "mean"]).round(2).to_string())
    print("stats :", stats)


if __name__ == "__main__":
    main()
