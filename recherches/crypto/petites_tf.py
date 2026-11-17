"""Étape 8 : achats et ventes sur M5, M15, M30, H1, H4 (et 1d pour comparer), avec et sans la tendance de fond,
avec et sans la DÉRIVE haussière du marché.

Question posée : la crypto monte « presque exponentiellement » ; est-ce cette hausse de fond qui empêche les ventes
de gagner ? Trois mesures pour chaque signal :
 - le gain brut moyen par trade (en points de base, 1 pb = 0,01 %), sans frais ;
 - le même gain une fois la dérive retirée (rendement de chaque bougie moins le rendement moyen de la période) :
   c'est ce qu'aurait gagné le signal sur un marché sans hausse de fond ;
 - le Sharpe net avec des ordres limites (0,02 % par côté, « maker ») et au marché (0,07 %, « taker ») + financement.
Filtre de fond (« tendance journalière ») : score de la confluence journalière (systeme.py), connu à la clôture
de la veille : haussier (>= 0,25), baissier (<= -0,25). Trois versions : sans filtre ; « dans le sens » (achats en
fond haussier, ventes en fond baissier) ; « contre » (ventes en fond haussier, achats en fond baissier).
Sortie : sorties/petites-tf.csv.gz
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

import partage  # noqa: F401,E402  (donnees, indicateurs, btc : dans bitcoin/, partagés avec le bot)
import donnees as DN
import indicateurs as I
import signaux as S
from confluence import votes_a_priori
from moteur import financement_par_bougie

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
TFS = ["5m", "15m", "30m", "1h", "4h", "1d"]
MIN = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
COUPE = pd.Timestamp("2023-01-01", tz="UTC")
DEBUT = pd.Timestamp("2018-01-01", tz="UTC")
COUTS = {"brut": 0.0, "maker": 0.0002, "taker": 0.0007}


def fond(actif, idx):
    """Score de confluence journalier connu au début de chaque bougie (clôture de la veille ou avant)."""
    ctx = S.contexte(actif, "1d")
    sc = votes_a_priori(ctx).mean(axis=1)
    dispo = sc.index + pd.Timedelta("1D")          # connu à la clôture
    pos = np.searchsorted(dispo.values, idx.values, side="right") - 1
    return pd.Series(np.where(pos >= 0, sc.values[np.maximum(pos, 0)], 0.0), index=idx)


def tenir_n(sig, n):
    """Position tenue n bougies après chaque signal (+1/-1), le plus récent l'emporte."""
    s = sig.replace(0, np.nan)
    return s.ffill(limit=n - 1).fillna(0)


def signaux(d):
    c, h, l, v = d.close, d.high, d.low, d.volume
    out = {}
    # tendance
    for a, b in ((9, 21), (20, 50), (50, 200)):
        ea, eb = I.ema(c, a), I.ema(c, b)
        out[f"tendance/ema{a}-{b}"] = S.etat(ea > eb, ea < eb)
    e200 = I.ema(c, 200)
    out["tendance/prix-ema200"] = S.etat(c > e200, c < e200)
    m, sg, hist = I.macd(c)
    out["tendance/macd"] = S.etat(m > sg, m < sg)
    for n in (20, 55):
        hh, ll = h.rolling(n).max().shift(), l.rolling(n).min().shift()
        hx, lx = h.rolling(n // 2).max().shift(), l.rolling(n // 2).min().shift()
        out[f"tendance/donchian{n}"] = S.tenir(c > hh, c < lx, c < ll, c > hx)
    out["tendance/supertrend10x3"] = I.supertrend(d, 10, 3)
    ich = I.ichimoku(d, 9, 26, 52)
    haut, bas = np.maximum(ich["spanA"], ich["spanB"]), np.minimum(ich["spanA"], ich["spanB"])
    out["tendance/nuage"] = S.etat(c > haut, c < bas)
    # retour à la moyenne
    r14 = I.rsi(c, 14)
    out["retour/rsi70-30"] = S.tenir(r14 < 30, r14 > 50, r14 > 70, r14 < 50)
    r2 = I.rsi(c, 2)
    out["retour/rsi2-95-5"] = S.tenir(r2 < 5, r2 > 50, r2 > 95, r2 < 50)
    mb, hb, bb = I.bollinger(c, 20, 2)
    out["retour/bollinger"] = S.tenir(c < bb, c > mb, c > hb, c < mb)
    vw = I.vwap_ancre(d, "D")
    z = (c - vw) / (c - vw).rolling(100).std()
    out["retour/vwap-jour-z2"] = S.tenir(z < -2, z > 0, z > 2, z < 0)
    # retournements (tenus 12 bougies)
    n = 20
    haut20, bas20 = c >= c.rolling(n).max(), c <= c.rolling(n).min()
    div_rsi_s = haut20 & (r14 < r14.rolling(n).max() - 5)
    div_rsi_l = bas20 & (r14 > r14.rolling(n).min() + 5)
    div_mac_s = haut20 & (hist < hist.rolling(n).max() * 0.5) & (hist.rolling(n).max() > 0)
    div_mac_l = bas20 & (hist > hist.rolling(n).min() * 0.5) & (hist.rolling(n).min() < 0)
    cvd = d.delta.cumsum()
    div_cvd_s = haut20 & (cvd - cvd.shift(n) < 0)
    div_cvd_l = bas20 & (cvd - cvd.shift(n) > 0)
    hp, lp = h.rolling(n).max().shift(), l.rolling(n).min().shift()
    sweep_s, sweep_l = (h > hp) & (c < hp), (l < lp) & (c > lp)
    rng = (h - l).replace(0, np.nan)
    climax_s = (v > 3 * v.rolling(50).mean()) & ((h - np.maximum(c, d.open)) / rng > 0.5)
    climax_l = (v > 3 * v.rolling(50).mean()) & ((np.minimum(c, d.open) - l) / rng > 0.5)
    eng_s = (c < d.open) & (c.shift() > d.open.shift()) & (c < d.open.shift()) & (d.open > c.shift()) & haut20.shift(1, fill_value=False)
    eng_l = (c > d.open) & (c.shift() < d.open.shift()) & (c > d.open.shift()) & (d.open < c.shift()) & bas20.shift(1, fill_value=False)
    e20 = I.ema(c, 20)
    usure_s = (c < e20) & ((c.shift() > e20.shift()).rolling(20).sum() == 20)
    usure_l = (c > e20) & ((c.shift() < e20.shift()).rolling(20).sum() == 20)
    # CHoCH : changement d'état de la structure (pivots de 3 bougies)
    st = _structure(d, 3)
    choch_s, choch_l = (st == -1) & (st.shift() == 1), (st == 1) & (st.shift() == -1)
    recent = lambda x: x.rolling(10).max().fillna(0).astype(bool)
    combos = {
        "retournement/div-rsi": (div_rsi_l, div_rsi_s), "retournement/div-macd": (div_mac_l, div_mac_s),
        "retournement/div-cvd": (div_cvd_l, div_cvd_s), "retournement/chasse-liquidite20": (sweep_l, sweep_s),
        "retournement/climax-volume": (climax_l, climax_s), "retournement/englobante-extreme": (eng_l, eng_s),
        "retournement/usure-ema20": (usure_l, usure_s), "retournement/choch3": (choch_l, choch_s),
        "retournement/div-rsi+choch": (recent(div_rsi_l) & choch_l, recent(div_rsi_s) & choch_s),
        "retournement/div-cvd+choch": (recent(div_cvd_l) & choch_l, recent(div_cvd_s) & choch_s),
        "retournement/chasse+delta": (sweep_l & (d.delta > 0), sweep_s & (d.delta < 0)),
    }
    for nom, (lo, sh) in combos.items():
        sig = S.etat(lo, sh)
        out[nom + "-12b"] = tenir_n(sig, 12)
        out[nom + "-48b"] = tenir_n(sig, 48)
    # order flow
    for k in (12, 48):
        ratio = d.delta.rolling(k).sum() / v.rolling(k).sum()
        out[f"orderflow/ratio{k}b"] = S.etat(ratio > 0, ratio < 0)
    return {k: x.fillna(0) for k, x in out.items()}


def _structure(d, n):
    hi, lo, c = d.high.values, d.low.values, d.close.values
    dh = np.full(len(d), np.nan); dl = np.full(len(d), np.nan)
    from numpy.lib.stride_tricks import sliding_window_view as sw
    if len(d) > 2 * n + 1:
        wh = sw(hi, 2 * n + 1).max(axis=1); wl = sw(lo, 2 * n + 1).min(axis=1)
        k = np.arange(n, len(d) - n)
        ph = hi[k] == wh; pl = lo[k] == wl
        dh[k[ph] + n] = hi[k[ph]]; dl[k[pl] + n] = lo[k[pl]]
    dh = pd.Series(dh, index=d.index).ffill(); dl = pd.Series(dl, index=d.index).ffill()
    cs = pd.Series(c, index=d.index)
    return S.tenir(cs > dh, cs < dl, cs < dl, cs > dh)


def evaluer(pos, r, fb, per, cout, detendre=False):
    """Gain par trade (pb) et Sharpe annualisé (sur rendements journaliers) pour une position sur une période."""
    p = pos.values
    tenue = np.r_[0.0, p[:-1]]
    chg = np.abs(np.diff(np.r_[0.0, tenue]))
    rr = r.values
    out = {}
    for k, m in per.items():
        rm = rr[m]
        if detendre:
            rm = rm - rm.mean()
        t = tenue[m]
        net = t * rm - chg[m] * cout - t * fb[m]
        n_tr = int(((t != 0) & (t != np.r_[0.0, t[:-1]])).sum())
        if n_tr < 20:
            out[k] = None
            continue
        jour = r.index[m].floor("D")
        nj = pd.Series(net, index=jour).groupby(level=0).sum()
        out[k] = dict(n=n_tr, pb=net.sum() / n_tr * 1e4, sharpe=nj.mean() / nj.std() * np.sqrt(365) if nj.std() > 0 else 0,
                      expo=float(np.abs(t).mean()))
    return out


def un(args):
    actif, tf = args
    d = DN.bougies_m5(actif + "USDT", tf)
    d = d[d.index >= DEBUT - pd.Timedelta("60D")]
    r = d.close.pct_change().fillna(0)
    fb = financement_par_bougie(DN.financement(actif + "USDT"), d.index).values
    per = {"R": (d.index >= DEBUT) & (d.index < COUPE), "V": d.index >= COUPE}
    sc = fond(actif, d.index)
    filtres = {"sans": (pd.Series(True, index=d.index), pd.Series(True, index=d.index)),
               "dans-le-sens": (sc >= 0.25, sc <= -0.25), "contre": (sc <= -0.25, sc >= 0.25)}
    lignes = []
    for nom, pos in signaux(d).items():
        for fn, (ok_l, ok_s) in filtres.items():
            for sens, p in (("achat", pos.clip(lower=0).where(ok_l, 0)), ("vente", pos.clip(upper=0).where(ok_s, 0))):
                l = dict(actif=actif, tf=tf, signal=nom, famille=nom.split("/")[0], filtre=fn, sens=sens)
                for cn, cv in COUTS.items():
                    for per_k, x in evaluer(p, r, fb if cn != "brut" else np.zeros(len(r)), per, cv).items():
                        if x:
                            l[f"{per_k}_n"] = x["n"]; l[f"{per_k}_expo"] = x["expo"]
                            l[f"{per_k}_pb_{cn}"] = x["pb"]; l[f"{per_k}_sh_{cn}"] = x["sharpe"]
                for per_k, x in evaluer(p, r, np.zeros(len(r)), per, 0.0, detendre=True).items():
                    if x:
                        l[f"{per_k}_pb_sansderive"] = x["pb"]; l[f"{per_k}_sh_sansderive"] = x["sharpe"]
                lignes.append(l)
    # dérive de la période, par bougie et par jour
    for k, m in per.items():
        lignes.append(dict(actif=actif, tf=tf, signal="_derive", filtre="", sens="", **{f"{k}_pb_brut": r.values[m].mean() * 1e4}))
    print(actif, tf, len(lignes), flush=True)
    return lignes


if __name__ == "__main__":
    taches = [(a, tf) for a in ("BTC", "ETH") for tf in TFS]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 3) as pool:
        res = pool.map(un, taches, chunksize=1)
    df = pd.DataFrame([l for r in res for l in r])
    df.to_csv(os.path.join(OUT, "petites-tf.csv.gz"), index=False, float_format="%.4f")
    print(len(df))
