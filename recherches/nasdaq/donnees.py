"""M1 bid/ask du Nasdaq (Dukascopy) -> tableaux numpy en heure de New York + table des jours (ce qui est connu à 9:35).

Les zips M1 ne sont plus dans le dépôt. Pour les récupérer (un zip par année, 2018 -> 2026-11-13) :
    git archive afb79de donnees/nas100 | tar -x
ou indiquer un autre dossier qui contient nas100/ avec la variable ORB_DONNEES."""
import os, glob, zipfile
import numpy as np, pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(ICI))
SRC = os.path.join(os.environ.get("ORB_DONNEES", os.path.join(RACINE, "donnees")), "nas100")
CACHE = os.path.join(ICI, "cache.npz")      # ignoré par git ; à effacer si les zips changent
NY = "America/New_York"


def lire():
    if not glob.glob(os.path.join(SRC, "*.zip")):
        raise FileNotFoundError(f"aucun zip M1 dans {SRC} : voir l'en-tête de ce fichier")
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    parts = {"bid": [], "ask": []}
    for zp in sorted(glob.glob(os.path.join(SRC, "*.zip"))):
        with zipfile.ZipFile(zp) as f:
            for c in parts:
                m = [n for n in f.namelist() if f"-m1-{c}-" in n][0]
                with f.open(m) as h:
                    parts[c].append(pd.read_csv(h))
    b, a = (pd.concat(parts[c]).drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp") for c in ("bid", "ask"))
    com = b.index.intersection(a.index)
    b, a = b.loc[com], a.loc[com]
    g = dict(ts=com.values.astype("int64"))
    for s, d in (("B", b), ("A", a)):
        for L, col in (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close")):
            g[s + L] = d[col].values.astype("float64")
    np.savez(CACHE, **g)
    return g


def m5(g):
    """M5 bid (et ask close) reconstruit du M1, pour RSI et filtres."""
    k = g["ts"] // 300_000
    df = pd.DataFrame({"k": k, "o": g["BO"], "h": g["BH"], "l": g["BL"], "c": g["BC"], "ac": g["AC"]})
    gr = df.groupby("k", sort=True)
    out = pd.DataFrame({"o": gr.o.first(), "h": gr.h.max(), "l": gr.l.min(), "c": gr.c.last(), "ac": gr.ac.last()})
    out["ts"] = out.index.values * 300_000
    return out


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values


# ── calendrier NYSE (mêmes règles que le script Pine / l'EA) ──
def _nth(y, m, wd, n):
    d = pd.Timestamp(y, m, 1)
    return d + pd.Timedelta(days=(wd - d.weekday()) % 7 + 7 * (n - 1))


def _obs(d):
    return d - pd.Timedelta(days=1) if d.weekday() == 5 else d + pd.Timedelta(days=1) if d.weekday() == 6 else d


def _paques(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; mo = (h + l - 7 * m + 114) // 31; da = (h + l - 7 * m + 114) % 31 + 1
    return pd.Timestamp(y, mo, da)


def jours_courts(annees):
    s = set()
    for y in annees:
        tg = _nth(y, 11, 3, 4)
        j4 = pd.Timestamp(y, 7, 4)
        lm = pd.Timestamp(y, 6, 1) - pd.Timedelta(days=1)
        lm = lm - pd.Timedelta(days=(lm.weekday()) % 7)
        L = [_obs(pd.Timestamp(y, 1, 1)), _obs(pd.Timestamp(y + 1, 1, 1)), _nth(y, 1, 0, 3), _nth(y, 2, 0, 3),
             _paques(y) - pd.Timedelta(days=2), lm, _obs(pd.Timestamp(y, 6, 19)), _obs(j4), _nth(y, 9, 0, 1), tg,
             _obs(pd.Timestamp(y, 12, 25)), tg + pd.Timedelta(days=1), pd.Timestamp(y, 12, 24)]
        if 1 <= j4.weekday() <= 4:
            L.append(j4 - pd.Timedelta(days=1))
        elif j4.weekday() == 5:
            L.append(j4 - pd.Timedelta(days=2))
        s.update(x.normalize() for x in L)
    return s


def preparer():
    g = lire()
    t = pd.DatetimeIndex(pd.to_datetime(g["ts"], unit="ms", utc=True)).tz_convert(NY)
    g["mins"] = (t.hour * 60 + t.minute).values.astype(np.int32)
    g["jour"] = t.tz_localize(None).normalize().values
    M = m5(g)
    M["rsi"] = rsi(M.c.values)
    tm = pd.DatetimeIndex(pd.to_datetime(M.ts.values, unit="ms", utc=True)).tz_convert(NY)
    M["mins"] = (tm.hour * 60 + tm.minute).values
    M["jour"] = tm.tz_localize(None).normalize().values
    courts = jours_courts(range(2017, 2028))
    rows = []
    # repères M1 par jour
    jour1 = g["jour"]
    debut = np.r_[0, np.flatnonzero(jour1[1:] != jour1[:-1]) + 1]
    fin = np.r_[debut[1:], len(jour1)]
    pos_jour = {pd.Timestamp(jour1[d]): (d, f) for d, f in zip(debut, fin)}
    Mg = M.groupby("jour")
    for day, x in Mg:
        day = pd.Timestamp(day)
        o = x[x.mins == 570]
        if len(o) != 1 or day.weekday() >= 5:
            continue
        pre = x[(x.mins >= 540) & (x.mins < 570)]
        if len(pre) < 2:
            continue
        d0, d1 = pos_jour[day]
        mm = g["mins"][d0:d1]
        i35 = d0 + int(np.searchsorted(mm, 575))
        if i35 >= d1 or g["mins"][i35] >= 600:
            continue
        court = day in courts
        flat = 765 if court else 950                     # 12:45 ou 15:50
        iend = d0 + int(np.searchsorted(mm, flat))       # première minute à/après la sortie
        if iend >= d1:
            iend = d1 - 1
        o = o.iloc[0]
        rows.append(dict(day=day, orH=o.h, orL=o.l, orO=o.o, orC=o.c, orw=o.h - o.l, rsi=o.rsi,
                         preH=pre.h.max(), preL=pre.l.min(), i35=i35, iend=iend, court=court))
    D = pd.DataFrame(rows)
    return g, D
