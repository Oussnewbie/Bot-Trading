"""Backtest indépendant de l'ORB v6 (Nasdaq), écrit à partir des règles du README uniquement.

Modèle d'exécution « EA » (la version de référence selon le README) : les bougies M5 du graphique sont celles du BID
(comme MetaTrader). Un achat stop au high du range est déclenché quand l'ASK atteint ce niveau, une vente stop au low
quand le BID l'atteint ; le stop d'un achat est touché quand le BID descend au stop, celui d'une vente quand l'ASK monte
au stop. Les sorties au marché se font au bid (achat) ou à l'ask (vente). Le spread est donc payé dans les prix.
La simulation descend à la minute (M1 bid et ask Dukascopy) pour savoir quel niveau est touché en premier.

Coûts ajoutés en plus du spread (paramètres) :
 - glis_stop : glissement en points sur chaque exécution d'ordre stop (entrée, stop de protection) ;
 - glis_marche : glissement en points sur chaque ordre au marché (ajout de la pyramide, sortie de 15:50) ;
 - spread_extra : points ajoutés au spread Dukascopy (l'ask est relevé d'autant) ;
 - commission : points par unité et par côté.
Résultat en R : (gain de toutes les unités) ÷ (taille de départ × range), comme le README définit 1R.

Ambiguïtés à la minute (deux niveaux touchés dans la même bougie M1) : mode "proche" = le niveau le plus proche de
l'ouverture de la minute est touché d'abord ; mode "pessimiste" = l'issue la pire pour le trade. Elles sont comptées.
"""
import datetime as dt
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd


# ───────────────────────── calendrier (celui des règles : README, règle 8) ─────────────────────────
def _nth_dow(y, m, dow, n):          # dow : lundi = 0
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(dow - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_dow(y, m, dow):
    d = dt.date(y, m + 1, 1) - dt.timedelta(days=1) if m < 12 else dt.date(y, 12, 31)
    return d - dt.timedelta(days=(d.weekday() - dow) % 7)


def _observed(d):
    return d - dt.timedelta(days=1) if d.weekday() == 5 else d + dt.timedelta(days=1) if d.weekday() == 6 else d


def _paques(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def jour_court(d, juneteenth_depuis=0):
    """Jours où les règles sortent à 12:45 : fériés américains (calculés comme l'EA et le script) et demi-séances.
    juneteenth_depuis : année du premier Juneteenth chômé (0 = toutes les années, comme les règles)."""
    y = d.year
    tg = _nth_dow(y, 11, 3, 4)
    j4 = dt.date(y, 7, 4)
    feries = {_observed(dt.date(y, 1, 1)), _observed(dt.date(y + 1, 1, 1)), _nth_dow(y, 1, 0, 3), _nth_dow(y, 2, 0, 3),
              _paques(y) - dt.timedelta(days=2), _last_dow(y, 5, 0), _observed(j4), _nth_dow(y, 9, 0, 1), tg,
              _observed(dt.date(y, 12, 25))}
    if y >= juneteenth_depuis:
        feries.add(_observed(dt.date(y, 6, 19)))
    courts = {tg + dt.timedelta(days=1), dt.date(y, 12, 24)}
    if j4.weekday() in (1, 2, 3, 4):
        courts.add(j4 - dt.timedelta(days=1))
    elif j4.weekday() == 5:
        courts.add(j4 - dt.timedelta(days=2))
    return d in feries or d in courts


# ───────────────────────── préparation ─────────────────────────
def rsi_wilder(c, n=14):
    d = np.diff(c, prepend=np.nan)
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + up / dn)


def preparer(m1, or_min=5, tf_rsi="5min", rsi_len=14):
    """Découpe les données par jour (heure de New York) et calcule le RSI14 M5 (bid) de chaque bougie M5."""
    b5 = m1[["bc"]].resample(tf_rsi, label="left", closed="left").last().dropna()
    r = pd.Series(rsi_wilder(b5.bc.values, rsi_len), index=b5.index)
    jours = {}
    t = m1.index
    cle = t.normalize()
    m = (t.hour >= 8) & (t.hour < 16)
    sub = m1[m]
    for jour, x in sub.groupby(cle[m]):
        jours[jour] = x
    return jours, r


@dataclass
class Regles:
    rsi: bool = True
    elan: bool = True
    elan_strict: bool = True        # « dépasse » : > (le script Pine utilise >=)
    elan_min_bougies: int = 1       # le script : 1 ; l'EA : 2 (README)
    or_debut: str = "09:30"
    or_min: int = 5                 # durée de la bougie du range
    pre_debut: str = "09:00"
    valides: int = 2                # bougies M5 de validité des ordres (2 = jusqu'à 9:45)
    be: float = 1.5                 # 0 = pas de stop à l'entrée
    pyr: float = 2.0                # 0 = pas de pyramide
    pyr_taille: float = 2.0
    pyr_ecart: float = 1.0
    pyr_bougie_entree: bool = True  # l'ajout peut-il se faire à la clôture de la bougie d'entrée (script : oui)
    sortie: str = "15:50"
    sortie_courte: str = "12:45"
    juneteenth_depuis: int = 0
    rsi_seuil: float = 50.0
    cotes: str = "deux"             # "deux", "achat", "vente"


@dataclass
class Couts:
    glis_stop: float = 0.0
    glis_marche: float = 0.0
    spread_extra: float = 0.0
    commission: float = 0.0
    ambigu: str = "proche"          # "proche" ou "pessimiste"
    prix: str = "ea"                # "ea" (bid/ask) ou "milieu" (un seul prix, comme TradingView ; coût = spread_extra)


def _hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def un_jour(jour, x, rsi_serie, R: Regles, C: Couts):
    """Simule un jour. x : M1 de 9:00 à 15:59 (heure NY). Retourne un dict (trade ou raison de l'absence)."""
    mins = (x.index.hour * 60 + x.index.minute).values
    if C.prix == "milieu":
        mid = lambda a, b: (x[a].values + x[b].values) / 2
        bo, bh, bl, bc = mid("bo", "ao"), mid("bh", "ah"), mid("bl", "al"), mid("bc", "ac")
        ao, ah, al, ac = bo, bh, bl, bc
        cs = C.spread_extra / 2      # demi-spread payé de chaque côté
        bo, bh, bl, bc = bo - cs, bh - cs, bl - cs, bc - cs
        ao, ah, al, ac = ao + 2 * cs, ah + 2 * cs, al + 2 * cs, ac + 2 * cs
        gh, gl, gc = (bh + ah) / 2, (bl + al) / 2, (bc + ac) / 2     # prix du « graphique » = milieu
    else:
        bo, bh, bl, bc = x.bo.values, x.bh.values, x.bl.values, x.bc.values
        e = C.spread_extra
        ao, ah, al, ac = x.ao.values + e, x.ah.values + e, x.al.values + e, x.ac.values + e
        gh, gl, gc = bh, bl, bc                                       # graphique MetaTrader = bid
    t_or, t_pre = _hm(R.or_debut), _hm(R.pre_debut)
    t_fin_or = t_or + R.or_min
    court = jour_court(jour.date(), R.juneteenth_depuis)
    t_sortie = _hm(R.sortie_courte if court else R.sortie)
    res = dict(jour=jour, court=court, dir=0, raison="", R=np.nan, ambigu=0)

    k_or = (mins >= t_or) & (mins < t_fin_or)
    if k_or.sum() == 0:
        res["raison"] = "pas de bougie 9:30"
        return res
    orH, orL = gh[k_or].max(), gl[k_or].min()
    rng = orH - orL
    res.update(orH=orH, orL=orL, range=rng, prix=gc[k_or][-1])
    if rng <= 0:
        res["raison"] = "range nul"
        return res
    # filtres
    t_rsi = pd.Timestamp(jour) + pd.Timedelta(minutes=t_fin_or - 5)     # bougie M5 qui clôture à la fin du range
    rv = rsi_serie.get(t_rsi, np.nan)
    res["rsi"] = rv
    kp = (mins >= t_pre) & (mins < t_or)
    nb_pre = len(np.unique(mins[kp] // 5)) if kp.any() else 0
    pre_ok = nb_pre >= R.elan_min_bougies
    preH = gh[kp].max() if kp.any() else np.nan
    preL = gl[kp].min() if kp.any() else np.nan
    if R.elan_strict:
        eL, eS = pre_ok and orH > preH, pre_ok and orL < preL
    else:
        eL, eS = pre_ok and orH >= preH, pre_ok and orL <= preL
    rL = (rv > R.rsi_seuil) if R.rsi else True
    rS = (rv < R.rsi_seuil) if R.rsi else True
    okL = bool(rL and (eL if R.elan else True)) and R.cotes in ("deux", "achat")
    okS = bool(rS and (eS if R.elan else True)) and R.cotes in ("deux", "vente")
    res.update(okL=okL, okS=okS)
    if not okL and not okS:
        res["raison"] = "filtres"
        return res

    # ordres en attente, de la fin du range à + valides × 5 min
    t_exp = t_fin_or + 5 * R.valides
    idx = np.where((mins >= t_fin_or) & (mins < t_exp))[0]
    entree = None
    for i in idx:
        tL = ah[i] >= orH     # l'achat stop (ou le côté haut bloqué) est touché par l'ask
        tS = bl[i] <= orL     # la vente stop (ou le côté bas bloqué) par le bid
        if not tL and not tS:
            continue
        if tL and tS:
            res["ambigu"] += 1
            if C.ambigu == "pessimiste":
                # deux côtés permis : on suppose l'entrée puis le stop de l'autre côté ; un seul côté : on suppose le
                # côté bloqué d'abord (pas de trade) seulement si cela est pire... on prend le trade puis le stop.
                premier = "L" if okL else "S"
            else:
                premier = "L" if abs(ao[i] - orH) <= abs(bo[i] - orL) else "S"
        else:
            premier = "L" if tL else "S"
        if premier == "L":
            if okL:
                entree = (1, i)
            else:
                res["raison"] = "côté bloqué touché d'abord"
        else:
            if okS:
                entree = (-1, i)
            else:
                res["raison"] = "côté bloqué touché d'abord"
        break
    if entree is None:
        if not res["raison"]:
            res["raison"] = "pas de cassure"
        return res

    d, i0 = entree
    if d == 1:
        px_e = max(orH, ao[i0]) + C.glis_stop
        stop = orL
    else:
        px_e = min(orL, bo[i0]) - C.glis_stop
        stop = orH
    risque = abs(px_e - stop)               # distance réelle (R des seuils, comme le script : |entrée - stop|)
    res.update(dir=d, entree=px_e, t_entree=int(mins[i0]), stop0=stop, glis_entree=abs(px_e - (orH if d == 1 else orL)))
    unites = [(px_e, 1.0)]                  # (prix, taille)
    be_fait = pyr_fait = False
    raison_sortie = "fin de journée"
    px_sortie = None
    m5_entree = mins[i0] // 5
    n = len(mins)
    i = i0
    premiere = True
    while i < n:
        if mins[i] >= t_sortie:
            break
        # stop touché pendant cette minute ? Dans la minute de l'entrée, l'autre côté du range touché lui aussi veut
        # dire que les deux côtés l'ont été (déjà compté comme ambigu) : l'entrée s'est faite d'abord, donc le stop suit.
        if d == 1:
            if bl[i] <= stop:
                px_sortie = (stop if premiere else min(stop, bo[i])) - C.glis_stop
                raison_sortie = "stop"
                break
        else:
            if ah[i] >= stop:
                px_sortie = (stop if premiere else max(stop, ao[i])) + C.glis_stop
                raison_sortie = "stop"
                break
        premiere = False
        # clôture d'une bougie M5 ?
        fin_m5 = (i + 1 >= n) or (mins[i + 1] // 5 != mins[i] // 5)
        if fin_m5:
            m5 = mins[i] // 5
            k = (mins // 5 == m5)
            fav_ext = (bh[k].max() - px_e) if d == 1 else (px_e - al[k].min())   # meilleur prix de la bougie
            fav_clo = (bc[i] - px_e) if d == 1 else (px_e - ac[i])               # clôture de la bougie
            entree_bougie = (m5 == m5_entree)
            pyr_ok = R.pyr > 0 and not pyr_fait and (not entree_bougie or R.pyr_bougie_entree) and \
                mins[i] + 1 < t_sortie and fav_clo >= R.pyr * risque and i + 1 < n
            if pyr_ok:
                j = i + 1                    # ajout au premier prix de la minute suivante
                px_a = (ao[j] + C.glis_marche) if d == 1 else (bo[j] - C.glis_marche)
                unites.append((px_a, R.pyr_taille))
                stop = px_a - d * R.pyr_ecart * risque
                pyr_fait = be_fait = True
            elif R.be > 0 and not be_fait and not entree_bougie and fav_ext >= R.be * risque:
                stop = px_e if (d == 1 and px_e > stop) or (d == -1 and px_e < stop) else stop
                be_fait = True
        i += 1
    if px_sortie is None:
        j = min(i, n) - 1                     # dernière minute avant l'heure de sortie : sortie à sa clôture
        px_sortie = (bc[j] - C.glis_marche) if d == 1 else (ac[j] + C.glis_marche)
    pts = sum(q * d * (px_sortie - p) for p, q in unites)
    tot = sum(q for _, q in unites)
    pts -= C.commission * 2 * tot
    res.update(sortie=px_sortie, raison=raison_sortie, be=be_fait, pyr=pyr_fait, unites=tot,
               R=pts / rng, R_risque=pts / risque, t_sortie=int(mins[i]) if i < n else int(mins[-1]))
    return res


def backtest(jours, rsi, R=None, C=None, debut=None, fin=None):
    R = R or Regles()
    C = C or Couts()
    out = []
    for jour, x in jours.items():
        if (debut and jour < pd.Timestamp(debut)) or (fin and jour >= pd.Timestamp(fin)):
            continue
        if jour.weekday() >= 5:
            continue
        out.append(un_jour(jour, x, rsi, R, C))
    return pd.DataFrame(out)


def resume(df, risque=0.005):
    t = df[df.dir != 0].copy()
    if len(t) == 0:
        return dict(n=0)
    r = t.R.values
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    pertes = 0; pire = 0
    for v in r:
        pertes = pertes + 1 if v < -0.05 else 0
        pire = max(pire, pertes)
    ans = (t.jour.iloc[-1] - t.jour.iloc[0]).days / 365.25
    capital = np.prod(1 + risque * r)
    se = r.std(ddof=1) / np.sqrt(len(r))
    return dict(n=len(t), par_an=round(len(t) / ans, 1), R_moy=round(r.mean(), 3), t_stat=round(r.mean() / se, 2),
                R_total=round(r.sum(), 1), gagnants=round((r > 0.05).mean(), 3), dd_R=round(dd, 1), serie_pertes=pire,
                pyr=round(t.pyr.mean(), 3), be=round(t.be.mean(), 3), stop=round((t.raison == "stop").mean(), 3),
                cagr_05=round(capital ** (1 / ans) - 1, 4), ambigus=int((t.ambigu > 0).sum()))
