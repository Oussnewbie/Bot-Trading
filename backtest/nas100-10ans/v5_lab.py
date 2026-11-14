"""Laboratoire de la v5 : simulateur souple de l'ORB de New York sur NAS100 M5 (bid et ask, spread réel).

Trois périodes :
  B     : avant mai 2018               (dans le dépôt : janvier -> avril 2018 ; 2015-2017 ont été retirées le 2026-11-14)
  train : mai 2018 -> août 2022        (toute l'exploration s'est faite ici)
  A     : septembre 2022 -> novembre 2026 (vérification)
Conventions prudentes : sur la bougie d'entrée seul le stop peut être touché ; quand un stop et un gain sont dans la
même bougie, le stop gagne ; un stop déplacé ne vaut qu'à partir de la bougie suivante.
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import numpy as np, pandas as pd
from load10 import load10

SLIP = 0.1
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))   # dossier des fichiers de cache v5_days.pkl et v5_bars.npz
T0, T1 = pd.Timestamp("2018-05-01"), pd.Timestamp("2022-09-01")
G = {}
D = None


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values


def _heures(tn):
    return pd.DatetimeIndex(pd.to_datetime(tn, utc=True)).tz_convert("America/New_York")


def _empreinte():
    """Empreinte des deux fichiers de données et du code qui construit le cache (taille et date de modification).
    Si l'un d'eux change, le cache est reconstruit : il ne peut plus rendre un ancien résultat sans prévenir."""
    import load10 as LD
    parts = []
    for p in (LD.csv_path("bid"), LD.csv_path("ask"), os.path.abspath(__file__), os.path.abspath(LD.__file__)):
        st = os.stat(p)
        parts.append(f"{os.path.basename(p)}:{st.st_size}:{st.st_mtime_ns}")
    return "|".join(parts)


def prep(data=None):
    """Charge les données et construit la table des jours (tout ce qui est connu à 9:35).
    data = (bid, ask) : deux tableaux o, h, l, c indexés en heure de New York, pour rejouer d'autres données."""
    global D
    cache = data is None
    f_days, f_bars = os.path.join(CACHE_DIR, "v5_days.pkl"), os.path.join(CACHE_DIR, "v5_bars.npz")
    sig = _empreinte() if cache else None
    if cache and os.path.exists(f_days) and os.path.exists(f_bars):
        z = np.load(f_bars, allow_pickle=True)
        if "sig" in z.files and str(z["sig"]) == sig:            # cache valable seulement pour ces données et ce code
            G.clear(); G.update({k: z[k] for k in z.files if k != "sig"}); G["t"] = _heures(G["tn"])
            D = pd.read_pickle(f_days); return D
    b, a = load10() if cache else data
    t = b.index
    g = dict(BO=b.o.values, BH=b.h.values, BL=b.l.values, BC=b.c.values, AO=a.o.values, AH=a.h.values, AL=a.l.values, AC=a.c.values)
    mins = (t.hour * 60 + t.minute).values
    cal = t.tz_localize(None).normalize()
    g["mins"] = mins; g["tn"] = t.as_unit("ns").asi8
    g["r5"] = rsi(g["BC"])
    pc = np.roll(g["BC"], 1); pc[0] = g["BC"][0]
    tr5 = np.maximum(g["BH"] - g["BL"], np.maximum(abs(g["BH"] - pc), abs(g["BL"] - pc)))
    g["atr5"] = pd.Series(tr5).ewm(alpha=1 / 14, adjust=False).mean().values
    BO, BH, BL, BC = g["BO"], g["BH"], g["BL"], g["BC"]
    df = pd.DataFrame({"o": BO, "h": BH, "l": BL, "c": BC}, index=t)
    rth = df[(mins >= 570) & (mins < 960)]
    DD = rth.groupby(rth.index.tz_localize(None).normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    trd = np.maximum(DD.h - DD.l, np.maximum((DD.h - DD.c.shift()).abs(), (DD.l - DD.c.shift()).abs()))
    DD["atr"] = trd.rolling(14).mean(); DD["rng"] = DD.h - DD.l
    DD["nr"] = DD.rng / DD.rng.rolling(7).max()          # 1 = plus grand range des 7 derniers jours
    DD["rnk7"] = DD.rng.rolling(7).apply(lambda x: (x[-1] <= x).mean(), raw=True)  # 1 = plus petit range des 7 jours
    Dp = DD.shift(1)
    idx = np.arange(len(t))
    s = pd.Series(np.where(mins < 950, idx, -1), index=cal)
    last = s.groupby(level=0).transform("max").values
    rows = []
    calv = cal.values
    for i in np.flatnonzero(mins == 570):
        day = cal[i]
        # l'ATR journalier (14 jours) ne sert qu'à des variantes de recherche : un jour sans ATR reste un jour de la v5
        if last[i] <= i or day not in Dp.index: continue
        dp = Dp.loc[day]
        j = i - 1; pre = []
        while j >= 0 and calv[j] == calv[i] and mins[j] >= 540: pre.append(j); j -= 1
        j8 = i - 1; pm = []
        while j8 >= 0 and calv[j8] == calv[i] and mins[j8] >= 480: pm.append(j8); j8 -= 1
        if len(pre) < 2: continue
        orw = BH[i] - BL[i]
        rows.append(dict(i=i, day=day, last=last[i], orH=BH[i], orL=BL[i], orO=BO[i], orC=BC[i], orw=orw,
                         preH=BH[pre].max(), preL=BL[pre].min(), pmH=BH[pm].max(), pmL=BL[pm].min(),
                         rsi=g["r5"][i], atr5=g["atr5"][i - 1], atrd=dp.atr, pdh=dp.h, pdl=dp.l, pdc=dp.c, pdo=dp.o,
                         prng=dp.rng / dp.atr, nr=dp.nr, rnk7=dp.rnk7, gap=(BO[i] - dp.c) / dp.atr, spread=a.o.values[i + 1] - BO[i + 1]))
    D = pd.DataFrame(rows)
    D["or_atr"] = D.orw / D.atrd
    D["or_med"] = D.orw / D.orw.rolling(20, min_periods=10).median().shift(1)   # range de 9:30 vs médiane des 20 jours précédents
    D["per"] = np.where(D.day < T0, "B", np.where(D.day < T1, "train", "A"))
    D["dow"] = pd.DatetimeIndex(D.day).day_of_week
    if cache:
        D.to_pickle(f_days)
        np.savez(f_bars, sig=np.array(sig), **g)
    G.clear(); G.update(g); G["t"] = _heures(g["tn"])
    return D


# ───────────────────────── filtres : côtés permis ─────────────────────────
def f_rsi(r): return {1} if r.rsi > 50 else {-1} if r.rsi < 50 else set()
def f_ext(r):
    s = set()
    if r.orH >= r.preH: s.add(1)
    if r.orL <= r.preL: s.add(-1)
    return s
def f_v4(r): return f_rsi(r) & f_ext(r)
def f_all(r): return {1, -1}


# ───────────────────────── gestion d'un trade ─────────────────────────
def path(k, d, ent, sl, last_i, P, fill="stop"):
    """Renvoie (R total en unités du risque initial, indice de sortie, MFE, détails)."""
    BO, BH, BL, BC, AO, AH, AL, AC, mins = (G[x] for x in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC", "mins"))
    risk = abs(ent - sl)
    if not risk > 0: return None                       # stop au mauvais endroit, ou sans valeur (ATR pas encore disponible)
    if fill != "close" and ((d == 1 and BL[k] <= sl) or (d == -1 and AH[k] >= sl)):
        return (sl - d * SLIP - ent) * d / risk, k, 0.0, "stop"
    locks = sorted(P.get("locks", [(1.5, 0.0)]))       # (seuil en R, stop placé à tant de R)
    tp = P.get("tp"); pyr = list(P.get("pyr", []))     # pyramides sur ordre stop : (seuil R, taille, stop commun en R)
    cadd = list(P.get("cadd", []))                     # ajouts décidés à la clôture d'une bougie : (seuil R, taille, stop commun en R)
    adds = []                                          # (prix, taille)
    tex = P.get("tex")                                 # sortie anticipée (minutes)
    trail = P.get("trail")                             # (début en R, nb de bougies) : stop sous le plus bas des n dernières bougies
    stop, mfe, why = sl, 0.0, "fin"
    real = [0.0]                                       # R déjà encaissés (ajout stoppé dans sa bougie)
    def total(px):
        r = real[0] + (px - ent) * d / risk
        for apx, sz in adds: r += sz * (px - apx) * d / risk
        return r
    def close_adds(j, stop):
        # ajout au marché à la clôture de la bougie j si elle clôture au-delà du seuil (aucune hypothèse dans la bougie)
        cur = ((BC[j] - ent) if d == 1 else (ent - AC[j])) / risk
        while cadd and cur >= cadd[0][0]:
            trig, sz, lock = cadd.pop(0)
            if isinstance(lock, tuple) and lock[0] == "max" and cur > lock[1]: continue     # ("max", m, stop) : pas d'ajout si la clôture dépasse m R
            apx = (AC[j] + SLIP) if d == 1 else (BC[j] - SLIP)
            adds.append((apx, sz))
            if isinstance(lock, tuple):
                if lock[0] == "rel": lock = max(lock[2], (apx - ent) * d / risk - lock[1])  # ("rel", x, plancher) : stop à x R sous le prix de l'ajout
                else: lock = lock[2]
            lv = ent + d * lock * risk
            stop = max(stop, lv) if d == 1 else min(stop, lv)
        return stop
    if fill != "close": stop = close_adds(k, stop)
    for j in range(k + 1, last_i + 1):
        hi = BH[j] if d == 1 else AH[j]; lo = BL[j] if d == 1 else AL[j]
        if (lo <= stop) if d == 1 else (hi >= stop):
            px = (min(stop, BO[j]) - SLIP) if d == 1 else (max(stop, AO[j]) + SLIP)
            return total(px), j, mfe, ("stop" if stop == sl else "stop remonté")
        fav = ((hi - ent) if d == 1 else (ent - lo)) / risk
        if tp is not None and fav >= tp:
            return total(ent + d * tp * risk), j, max(mfe, fav), "objectif"
        mfe = max(mfe, fav)
        for trig, lock in locks:
            if mfe >= trig:
                lv = ent + d * lock * risk
                stop = max(stop, lv) if d == 1 else min(stop, lv)
        while pyr and mfe >= pyr[0][0]:
            trig, sz, lock = pyr.pop(0)
            apx = ent + d * trig * risk + d * SLIP
            lv = ent + d * lock * risk
            # L'ajout a son propre stop dès son exécution. Prudence : s'il a pu être touché dans la même bougie
            # (clôture revenue derrière le stop, ou bougie ouverte devant le stop et descendue dessous), il l'est.
            if d == 1: hit = BC[j] <= lv or (BO[j] > lv and BL[j] <= lv)
            else:      hit = AC[j] >= lv or (AO[j] < lv and AH[j] >= lv)
            if hit: real[0] += sz * ((lv - d * SLIP) - apx) * d / risk
            else: adds.append((apx, sz))
            stop = max(stop, lv) if d == 1 else min(stop, lv)
        if j < last_i: stop = close_adds(j, stop)
        if trail and mfe >= trail[0]:
            n = trail[1]
            lv = (BL[max(k, j - n + 1):j + 1].min()) if d == 1 else (AH[max(k, j - n + 1):j + 1].max())
            stop = max(stop, lv) if d == 1 else min(stop, lv)
        if tex is not None and mins[j] >= tex - 5:
            px = BC[j] - SLIP if d == 1 else AC[j] + SLIP
            return total(px), j, mfe, "heure"
    px = BC[last_i] - SLIP if d == 1 else AC[last_i] + SLIP
    return total(px), last_i, mfe, why


def sl_price(r, d, ent, P):
    m = P.get("sl", "range")
    lvl_far = r.orL if d == 1 else r.orH
    if m == "range": return lvl_far
    if m[0] == "frac": return ent - d * m[1] * r.orw                      # fraction du range depuis l'entrée
    if m[0] == "atr": return ent - d * m[1] * r.atrd                      # fraction de l'ATR jour
    if m[0] == "clamp":                                                   # range borné entre lo et hi ATR jour
        dist = min(max(r.orw, m[1] * r.atrd), m[2] * r.atrd); return ent - d * dist
    if m[0] == "atr5": return ent - d * m[1] * r.atr5
    raise ValueError(m)


def run(P=None, filt=f_v4, days=None):
    """Simule tous les jours. Un seul ordre du côté permis, annulé si l'autre côté est touché d'abord (comme le script)."""
    P = P or {}
    BO, BH, BL, BC, AO, AH, AL, AC, mins, t = (G[x] for x in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC", "mins", "t"))
    cutoff = P.get("cutoff", 585); buf = P.get("buf", 0.0); entry = P.get("entry", "stop"); out = []
    for r in (D if days is None else days).itertuples():
        sides = filt(r)
        if not sides: continue
        i, last_i = r.i, r.last
        lvH, lvL = r.orH + buf * r.orw, r.orL - buf * r.orw
        k = i + 1; n = 0; done = False
        while k <= last_i and mins[k] < cutoff and not done:
            if entry == "stop":
                up = AH[k] >= lvH; dn = BL[k] <= lvL
                if up or dn:
                    hit = [d for d, h in ((1, up), (-1, dn)) if h and d in sides]
                    if not hit: break
                    res = []
                    for d in hit:
                        ent = (max(lvH, AO[k]) + SLIP) if d == 1 else (min(lvL, BO[k]) - SLIP)
                        res.append((path(k, d, ent, sl_price(r, d, ent, P), last_i, P), d, ent))
                    res = [x for x in res if x[0]]
                    if not res: break
                    (rr, ex, mfe, why), d, ent = min(res, key=lambda x: x[0][0])
                    out.append(dict(t=t[k], i=i, per=r.per, r=rr, d=d, k=k, ex=ex, mfe=mfe, why=why, n=n))
                    n += 1
                    # ré-entrée du même côté après un stop : nouvel ordre stop au même niveau, jusqu'à re_until
                    re = P.get("re")
                    if re and why == "stop" and n <= re.get("max", 1):
                        k2 = ex + 1
                        # il faut d'abord que le prix soit revenu sous le niveau (ordre replacé), puis le recasse
                        while k2 <= last_i and mins[k2] < re.get("until", 660):
                            trig = (AH[k2] >= lvH) if d == 1 else (BL[k2] <= lvL)
                            if trig:
                                ent2 = (max(lvH, AO[k2]) + SLIP) if d == 1 else (min(lvL, BO[k2]) - SLIP)
                                p2 = path(k2, d, ent2, sl_price(r, d, ent2, P), last_i, P)
                                if p2: out.append(dict(t=t[k2], i=i, per=r.per, r=p2[0], d=d, k=k2, ex=p2[1], mfe=p2[2], why=p2[3], n=n))
                                break
                            k2 += 1
                    done = True
            elif entry == "close":
                up = BC[k] > r.orH; dn = BC[k] < r.orL
                if up or dn:
                    d = 1 if up else -1
                    if d not in sides: break
                    ent = (AC[k] + SLIP) if d == 1 else (BC[k] - SLIP)
                    p = path(k, d, ent, sl_price(r, d, ent, P), last_i, P, fill="close")
                    if p: out.append(dict(t=t[k], i=i, per=r.per, r=p[0], d=d, k=k, ex=p[1], mfe=p[2], why=p[3], n=0))
                    done = True
            elif entry == "retest":
                # signal : clôture hors du range ; puis achat limite au niveau (+ off × range), valable rt bougies
                up = BC[k] > r.orH; dn = BC[k] < r.orL
                if up or dn:
                    d = 1 if up else -1
                    if d not in sides: break
                    lim = (r.orH if d == 1 else r.orL) + d * P.get("off", 0.0) * r.orw
                    for k2 in range(k + 1, min(last_i, k + P.get("rt", 6)) + 1):
                        if (AL[k2] <= lim) if d == 1 else (BH[k2] >= lim):
                            ent = lim
                            p = path(k2, d, ent, sl_price(r, d, ent, P), last_i, P)
                            if p: out.append(dict(t=t[k2], i=i, per=r.per, r=p[0], d=d, k=k2, ex=p[1], mfe=p[2], why=p[3], n=0))
                            break
                    done = True
            k += 1
    return pd.DataFrame(out)


# ───────────────────────── statistiques ─────────────────────────
def stats(X, per=None):
    if per is not None: X = X[X.per.isin([per] if isinstance(per, str) else per)]
    if len(X) == 0: return dict(n=0, mean=np.nan, tot=0, dd=0, streak=0, stop=np.nan, win=np.nan, t=np.nan, ypos="0/0", yrs=0)
    r = X.r.values; eq = np.cumsum(r); dd = (np.maximum.accumulate(np.maximum(eq, 0)) - eq).max()
    s = w = 0
    for v in r:
        s = s + 1 if v < -0.05 else 0; w = max(w, s)
    y = X.groupby(X.t.dt.year).r.sum()
    yrs = (X.t.iloc[-1] - X.t.iloc[0]).days / 365.25
    return dict(n=len(X), mean=r.mean(), tot=r.sum(), dd=dd, streak=w, stop=(r <= -0.9).mean(), win=(r > 0.05).mean(),
                t=r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else np.nan, ypos=f"{(y > 0).sum()}/{len(y)}", yrs=yrs)


def line(lab, X, pers=("train",)):
    """Par défaut seule la période d'exploration est affichée."""
    cells = []
    for p in pers:
        s = stats(X, p)
        cells.append(f"{s['n']:4d} | {100*s['stop']:.0f} % | {s['mean']:+.3f} | {s['tot']:+5.0f}R | -{s['dd']:.0f}R / {s['streak']} | t={s['t']:.1f} | {s['ypos']}")
    print(f"| {lab} | " + " || ".join(cells) + " |", flush=True)


def head(pers=("train",)):
    print("| Variante | " + " || ".join(f"{p}: trades | stops | R/trade | total | pire baisse / série | t | années +" for p in pers) + " |")
    print("|---|" + "---|" * (7 * len(pers) + len(pers) - 1))


if __name__ == "__main__":
    prep()
    print(D.per.value_counts().to_dict())
    # contrôle : sans pyramide, à partir de mai 2018, sans filtre (v3) puis avec les filtres (v4)
    for lab, f in (("v3", f_all), ("v4", f_v4)):
        X = run({}, f); X = X[X.per != "B"]
        print(lab, len(X), round(X.r.mean(), 3), round(X.r.sum()))
