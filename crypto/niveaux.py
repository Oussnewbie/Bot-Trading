"""Supports et résistances : détection (plusieurs méthodes) et TEST statistique.

Chaque méthode donne, à la clôture de chaque jour (00:00 UTC), une liste de niveaux de prix calculés uniquement avec le
passé. Ces niveaux sont utilisés le jour suivant, sur les bougies 1h :
 - un niveau est « touché » quand une bougie 1h l'atteint en venant d'au-dessus (support) ou d'en dessous (résistance) ;
 - « rebond » si le prix repart ensuite de k × ATR journalier dans le sens du rejet AVANT de clôturer à k × ATR de
   l'autre côté (« cassure »), dans les 5 jours ; sinon « rien ».
Témoin : les mêmes niveaux décalés de ±1,5 ATR (deux témoins), passés dans le même test. Un niveau « marche » si son
taux de rebond dépasse nettement celui des témoins : sinon le prix « rebondit » autant n'importe où.
"""
import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I

ARRONDIS = {"BTC": (1000, 5000, 10000), "ETH": (100, 500, 1000)}


def journalier(actif):
    h = DN.bougies(actif + "USDT", "spot", "1h")
    d = DN.regrouper(h, "1d")
    d["atr"] = I.atr(d, 14)
    return h, d


# ───────────────────────── méthodes ─────────────────────────
def pivots(d, n):
    """Points pivots (fractales) : plus haut entouré de n bougies plus basses de chaque côté. Confirmé n jours après :
    on renvoie la date de CONFIRMATION, seule utilisable."""
    h, l = d.high.values, d.low.values
    ph, pl = [], []
    for i in range(n, len(d) - n):
        if h[i] == h[i - n:i + n + 1].max():
            ph.append((i + n, h[i]))
        if l[i] == l[i - n:i + n + 1].min():
            pl.append((i + n, l[i]))
    return ph, pl


def regrouper_niveaux(prix, tol):
    """Regroupe des prix à moins de `tol` les uns des autres : (niveau moyen, nombre de touches)."""
    if len(prix) == 0:
        return np.array([]), np.array([])
    p = np.sort(np.asarray(prix))
    groupes = [[p[0]]]
    for x in p[1:]:
        if x - groupes[-1][-1] <= tol:
            groupes[-1].append(x)
        else:
            groupes.append([x])
    return np.array([np.mean(g) for g in groupes]), np.array([len(g) for g in groupes])


def m_pivots(d, n=5, fenetre=365, min_touches=1):
    ph, pl = pivots(d, n)
    pts = sorted(ph + pl)
    idx = np.array([i for i, _ in pts]); val = np.array([v for _, v in pts])
    out = {}
    for i in range(len(d)):
        m = (idx <= i) & (idx > i - fenetre)
        if m.sum() == 0:
            continue
        niv, cnt = regrouper_niveaux(val[m], 0.5 * d.atr.iloc[i])
        out[i] = niv[cnt >= min_touches]
    return out


def m_kde(d, n=5, fenetre=365):
    """Pics de la densité (noyau gaussien de largeur 1 ATR) des pivots des `fenetre` derniers jours."""
    ph, pl = pivots(d, n)
    pts = sorted(ph + pl)
    idx = np.array([i for i, _ in pts]); val = np.array([v for _, v in pts])
    out = {}
    for i in range(len(d)):
        m = (idx <= i) & (idx > i - fenetre)
        if m.sum() < 3 or np.isnan(d.atr.iloc[i]):
            continue
        v = val[m]; bw = d.atr.iloc[i]
        grille = np.linspace(v.min(), v.max(), 400)
        dens = np.exp(-0.5 * ((grille[:, None] - v[None, :]) / bw) ** 2).sum(1)
        pic = (dens[1:-1] > dens[:-2]) & (dens[1:-1] > dens[2:]) & (dens[1:-1] >= 2)
        out[i] = grille[1:-1][pic]
    return out


def m_precedents(d, quoi):
    """Plus haut et plus bas de la veille, de la semaine ou du mois précédents (calendrier UTC)."""
    per = {"jour": "D", "semaine": "W-SUN", "mois": "M"}[quoi]
    cle = d.index.tz_localize(None).to_period(per)
    g = pd.DataFrame({"h": d.high, "l": d.low, "k": cle}).groupby("k").agg(h=("h", "max"), l=("l", "min"))
    prec = g.shift(1)
    out = {}
    for i, k in enumerate(cle):
        if quoi == "jour":
            hh, ll = d.high.iloc[i], d.low.iloc[i]          # le jour qui vient de clôturer = la veille du jour testé
        else:
            # période en cours non terminée : on prend la période précédente complète
            if i + 1 < len(cle) and cle[i + 1] != k:          # dernier jour de la période : elle est complète
                hh, ll = g.loc[k, "h"], g.loc[k, "l"]
            else:
                hh, ll = prec.loc[k, "h"], prec.loc[k, "l"]
        if not np.isnan(hh):
            out[i] = np.array([hh, ll])
    return out


def m_arrondis(d, pas):
    out = {}
    for i, c in enumerate(d.close.values):
        b = np.floor(c / pas) * pas
        out[i] = np.array([b - pas, b, b + pas, b + 2 * pas])
    return out


def m_profil_volume(h, d, jours=30, quoi="poc"):
    """Profil de volume des `jours` derniers jours en 1h (le volume de chaque bougie réparti sur son prix typique, en
    cases de 0,5 % du prix) : POC (case la plus traitée), bords de la zone de valeur (70 %), ou pics (HVN)."""
    tp = ((h.high + h.low + h.close) / 3).values
    vol = h.volume.values
    fin_jour = np.searchsorted(h.index.values, (d.index + pd.Timedelta("1D")).values)
    out = {}
    for i in range(jours, len(d)):
        a, b = fin_jour[i - jours], fin_jour[i]
        p, v = tp[a:b], vol[a:b]
        if len(p) < 24:
            continue
        pas = d.close.iloc[i] * 0.005
        cases = np.floor(p / pas).astype(int)
        k0 = cases.min()
        prof = np.bincount(cases - k0, weights=v)
        centres = (np.arange(len(prof)) + k0 + 0.5) * pas
        poc = np.argmax(prof)
        if quoi == "poc":
            out[i] = np.array([centres[poc]])
        elif quoi == "zone":
            ordre = np.argsort(prof)[::-1]
            cum = np.cumsum(prof[ordre]) / prof.sum()
            garde = ordre[: np.searchsorted(cum, 0.7) + 1]
            out[i] = np.array([centres[garde.min()], centres[garde.max()]])
        elif quoi == "hvn":
            lis = np.convolve(prof, np.ones(3) / 3, mode="same")
            pic = np.flatnonzero((lis[1:-1] > lis[:-2]) & (lis[1:-1] > lis[2:])) + 1
            pic = pic[lis[pic] > np.median(lis)]
            out[i] = centres[pic]
        elif quoi == "lvn":
            lis = np.convolve(prof, np.ones(3) / 3, mode="same")
            creux = np.flatnonzero((lis[1:-1] < lis[:-2]) & (lis[1:-1] < lis[2:])) + 1
            out[i] = centres[creux]
    return out


def m_vwap_pivots(d, n=10, combien=3):
    """VWAP ancrés aux `combien` derniers grands pivots (hauts et bas)."""
    ph, pl = pivots(d, n)
    tp = (d.high + d.low + d.close) / 3
    pv, v = (tp * d.volume).cumsum().values, d.volume.cumsum().values
    out = {}
    for i in range(len(d)):
        ancres = sorted([j - n for j, _ in ph + pl if j <= i])[-combien:]
        if ancres:
            out[i] = np.array([(pv[i] - (pv[a - 1] if a else 0)) / (v[i] - (v[a - 1] if a else 0)) for a in ancres])
    return out


def m_moyennes(d, ns=(20, 50, 100, 200)):
    ms = [I.sma(d.close, n).values for n in ns]
    return {i: np.array([m[i] for m in ms if not np.isnan(m[i])]) for i in range(len(d))}


def m_ichimoku(d):
    ich = I.ichimoku(d, 9, 26, 52)
    k, a, b = ich["kijun"].values, ich["spanA"].values, ich["spanB"].values
    return {i: np.array([x for x in (k[i], a[i], b[i]) if not np.isnan(x)]) for i in range(len(d))}


def m_fibo(d, jours=90, niveaux=(0.382, 0.5, 0.618)):
    hh, ll = d.high.rolling(jours).max().values, d.low.rolling(jours).min().values
    return {i: np.array([ll[i] + f * (hh[i] - ll[i]) for f in niveaux]) for i in range(len(d)) if not np.isnan(hh[i])}


def methodes(actif, h, d):
    m = {
        "pivots3": m_pivots(d, 3), "pivots5": m_pivots(d, 5), "pivots10": m_pivots(d, 10),
        "pivots5-2touches": m_pivots(d, 5, min_touches=2), "pivots5-3touches": m_pivots(d, 5, min_touches=3),
        "kde-pivots5": m_kde(d, 5),
        "veille-haut-bas": m_precedents(d, "jour"), "semaine-haut-bas": m_precedents(d, "semaine"),
        "mois-haut-bas": m_precedents(d, "mois"),
        "profil-poc30j": m_profil_volume(h, d, 30, "poc"), "profil-zone30j": m_profil_volume(h, d, 30, "zone"),
        "profil-hvn30j": m_profil_volume(h, d, 30, "hvn"), "profil-lvn30j": m_profil_volume(h, d, 30, "lvn"),
        "profil-poc90j": m_profil_volume(h, d, 90, "poc"), "profil-hvn90j": m_profil_volume(h, d, 90, "hvn"),
        "vwap-pivots10": m_vwap_pivots(d), "moyennes20-200": m_moyennes(d),
        "ichimoku-kijun-nuage": m_ichimoku(d), "fibonacci90j": m_fibo(d),
    }
    for p in ARRONDIS[actif]:
        m[f"arrondi{p}"] = m_arrondis(d, p)
    return m


# ───────────────────────── test ─────────────────────────
def tester(h, d, niv_par_jour, k=0.5, horizon_h=120, decalage=0.0):
    """Toutes les touches des niveaux (décalés de `decalage` ATR) et leur issue. Un niveau ne compte qu'une fois par
    jour et par sens. Renvoie un DataFrame : temps, sens (S support / R résistance), issue (1 rebond, 0 cassure,
    nan ni l'un ni l'autre)."""
    H, L, C = h.high.values, h.low.values, h.close.values
    t_h = h.index.values
    debut_jour = np.searchsorted(t_h, (d.index + pd.Timedelta("1D")).values)   # 1re bougie 1h du jour suivant
    atr = d.atr.values
    lignes = []
    for i, niv in niv_par_jour.items():
        if i + 1 >= len(d) or np.isnan(atr[i]) or len(niv) == 0:
            continue
        a = debut_jour[i]; b = debut_jour[i + 1] if i + 1 < len(debut_jour) else len(C)
        if a < 1 or a >= len(C):
            continue
        dist = k * atr[i]
        for lv in np.unique(np.round(niv + decalage * atr[i], 8)):
            for sens in ("S", "R"):
                for j in range(a, b):
                    pc = C[j - 1]
                    if sens == "S" and pc > lv and L[j] <= lv:
                        break
                    if sens == "R" and pc < lv and H[j] >= lv:
                        break
                else:
                    continue
                issue = np.nan
                for m in range(j, min(j + horizon_h, len(C))):
                    if sens == "S":
                        if C[m] < lv - dist:
                            issue = 0; break
                        if H[m] >= lv + dist and m > j:
                            issue = 1; break
                    else:
                        if C[m] > lv + dist:
                            issue = 0; break
                        if L[m] <= lv - dist and m > j:
                            issue = 1; break
                lignes.append((t_h[j], sens, issue))
    return pd.DataFrame(lignes, columns=["t", "sens", "issue"])


def resume(t):
    x = t.dropna(subset=["issue"])
    return len(t), x.issue.mean() if len(x) else np.nan, len(x)


# ───────────────────────── méthodes ICT / SMC et points pivots classiques ─────────────────────────
def m_fvg(d, jours=60):
    """Fair value gaps (déséquilibres) non comblés des `jours` derniers jours : bougie i-2 et bougie i ne se
    recouvrent pas (haussier : bas[i] > haut[i-2]). Niveaux = les deux bords du trou, tant qu'il n'est pas comblé."""
    h, l, c = d.high.values, d.low.values, d.close.values
    trous = []          # (indice, bas du trou, haut du trou)
    out = {}
    for i in range(2, len(d)):
        if l[i] > h[i - 2]:
            trous.append([i, h[i - 2], l[i]])
        elif h[i] < l[i - 2]:
            trous.append([i, h[i], l[i - 2]])
        trous = [t for t in trous if i - t[0] <= jours and not (l[i] <= t[1] and t[0] < i and h[i] >= t[2])]
        out[i] = np.array([x for t in trous for x in t[1:]])
    return out


def m_order_blocks(d, jours=60, impulsion=1.5):
    """Order blocks : dernière bougie de sens contraire avant une impulsion (déplacement > `impulsion` ATR sur 3 bougies).
    Niveaux = haut et bas de cette bougie, tant que le prix n'a pas clôturé au-delà."""
    o, h, l, c, a = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    blocs = []
    out = {}
    for i in range(4, len(d)):
        if not np.isnan(a[i]):
            if c[i] - c[i - 3] > impulsion * a[i]:
                for j in range(i - 3, max(i - 8, 0), -1):
                    if c[j] < o[j]:
                        blocs.append([i, l[j], h[j], 1]); break
            elif c[i - 3] - c[i] > impulsion * a[i]:
                for j in range(i - 3, max(i - 8, 0), -1):
                    if c[j] > o[j]:
                        blocs.append([i, l[j], h[j], -1]); break
        blocs = [b for b in blocs if i - b[0] <= jours and not ((b[3] == 1 and c[i] < b[1]) or (b[3] == -1 and c[i] > b[2]))]
        out[i] = np.array([x for b in blocs for x in b[1:3]])
    return out


def m_pivots_classiques(d, per="D"):
    """Points pivots « floor » : P = (H+B+C)/3 de la période précédente, R1 = 2P-B, S1 = 2P-H, R2 = P+(H-B), S2 = P-(H-B)."""
    if per == "D":
        H, B, C = d.high.values, d.low.values, d.close.values
        idx = range(len(d))
        f = lambda i: (H[i], B[i], C[i])
    else:
        cle = d.index.tz_localize(None).to_period(per)
        g = pd.DataFrame({"h": d.high, "l": d.low, "c": d.close, "k": cle}).groupby("k").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
        prec = g.shift(1)
        dernier = pd.Series(cle).shift(-1).values != cle
        f = lambda i: tuple(g.loc[cle[i]] if dernier[i] else prec.loc[cle[i]])
        idx = range(len(d))
    out = {}
    for i in idx:
        hh, ll, cc = f(i)
        if np.isnan(hh):
            continue
        p = (hh + ll + cc) / 3
        out[i] = np.array([p, 2 * p - ll, 2 * p - hh, p + (hh - ll), p - (hh - ll)])
    return out
