"""Setups précis (achat et VENTE) simulés trade par trade sur les bougies 1h : stop et objectif touchés dans la bougie,
le stop gagne quand les deux sont possibles dans la même heure.

Décision à la clôture journalière (00:00 UTC), entrée à l'ouverture de la bougie 1h suivante (au marché).
Coûts : perpétuel Binance 0,05 % + 0,02 % de glissement à l'entrée et à la sortie, financement réel heure par heure
(un vendeur le reçoit quand il est positif). Stop au-delà de la mèche du jour du signal + 0,25 ATR, au moins 0,5 ATR.

Régimes (journaliers) : baisse = clôture < SMA200 et SMA200 en baisse sur 20 jours ; nuage = sous le nuage Ichimoku ;
confluence = score des 9 votes <= -0,25 ; aucun. Miroir pour les achats.

Déclencheurs (pour une vente ; miroir pour un achat) :
 rejet-kijun / rejet-nuage / rejet-sma20 / rejet-sma50 / rejet-vwap-sommet : le plus haut du jour touche le niveau,
   la clôture finit dessous ;
 retest-cassure : le plus bas de 30 jours a été cassé dans les 10 derniers jours, le prix revient le toucher et clôture
   dessous ;
 cassure20 : clôture sous le plus bas des 20 jours ;
 chasse-veille : le plus haut dépasse celui de la veille mais la clôture revient sous (prise de liquidité ratée) ;
 chasse-semaine : idem avec le plus haut de la semaine précédente ;
 rsi-retour : RSI 14 repasse sous 55 après être monté au-dessus de 60 ;
 prime-pic : prime du perpétuel dans les 10 % les plus hauts de l'année ;
 fng-cupidite : Fear & Greed > 60 ;
 cb-negative : la prime Coinbase sur 7 jours passe sous zéro.
Sorties : objectif 1,5R / 2R / 3R, sortie au temps 5 ou 20 jours, ou suivi (clôture de l'autre côté de la SMA20).
Sortie : sorties/evenements.csv
"""
import itertools
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

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
COUT = 0.0005 + 0.0002
COUPE = pd.Timestamp("2023-01-01", tz="UTC")


def preparer(actif):
    ctx = S.contexte(actif, "1d")
    d = ctx["d"].copy()
    c = d.close
    d["atr"] = I.atr(d, 14)
    m200 = I.sma(c, 200)
    ich = I.ichimoku(d, 9, 26, 52)
    haut = np.maximum(ich["spanA"], ich["spanB"]); bas = np.minimum(ich["spanA"], ich["spanB"])
    score = votes_a_priori(ctx).mean(axis=1)
    reg = {
        "aucun": (pd.Series(True, index=d.index), pd.Series(True, index=d.index)),
        "sma200": ((c > m200) & (m200 > m200.shift(20)), (c < m200) & (m200 < m200.shift(20))),
        "nuage": (c > haut, c < bas),
        "confluence": (score >= 0.25, score <= -0.25),
    }
    # niveaux : pour une vente on regarde le niveau AU-DESSUS (résistance), pour un achat en dessous
    ph, pl = [], []
    n = 10
    for i in range(n, len(d) - n):
        if d.high.iloc[i] == d.high.iloc[i - n:i + n + 1].max():
            ph.append(i)
        if d.low.iloc[i] == d.low.iloc[i - n:i + n + 1].min():
            pl.append(i)
    tp = (d.high + d.low + d.close) / 3
    pv, vv = (tp * d.volume).cumsum().values, d.volume.cumsum().values

    def avwap_dernier(pivs):
        out = np.full(len(d), np.nan)
        conf = np.array(pivs) + n
        for i in range(len(d)):
            k = np.searchsorted(conf, i, side="right") - 1
            if k >= 0:
                a = pivs[k]
                out[i] = (pv[i] - (pv[a - 1] if a else 0)) / (vv[i] - (vv[a - 1] if a else 0))
        return pd.Series(out, index=d.index)
    niveaux = {"kijun": (ich["kijun"], ich["kijun"]), "nuage": (haut, bas),
               "sma20": (I.sma(c, 20),) * 2, "sma50": (I.sma(c, 50),) * 2,
               "vwap-sommet": (avwap_dernier(pl), avwap_dernier(ph))}   # (support pour achat, résistance pour vente)
    trig = {}
    for nom, (sup, res) in niveaux.items():
        trig[f"rejet-{nom}"] = ((d.low <= sup) & (c > sup), (d.high >= res) & (c < res))
    lo30, hi30 = d.low.rolling(30).min().shift(), d.high.rolling(30).max().shift()
    casse_bas = (c < lo30); casse_haut = (c > hi30)
    niv_bas = lo30.where(casse_bas).ffill(limit=10); niv_haut = hi30.where(casse_haut).ffill(limit=10)
    recent_b = casse_bas.rolling(10).max().astype(bool); recent_h = casse_haut.rolling(10).max().astype(bool)
    trig["retest-cassure"] = (recent_h & (d.low <= niv_haut) & (c > niv_haut) & ~casse_haut,
                              recent_b & (d.high >= niv_bas) & (c < niv_bas) & ~casse_bas)
    trig["cassure20"] = (c > d.high.rolling(20).max().shift(), c < d.low.rolling(20).min().shift())
    trig["chasse-veille"] = ((d.low < d.low.shift()) & (c > d.low.shift()), (d.high > d.high.shift()) & (c < d.high.shift()))
    sem = d.index.tz_localize(None).to_period("W-SUN")
    g = pd.DataFrame({"h": d.high, "l": d.low, "k": sem}).groupby("k").agg(h=("h", "max"), l=("l", "min")).shift()
    hs, ls = pd.Series(g.h.reindex(sem).values, index=d.index), pd.Series(g.l.reindex(sem).values, index=d.index)
    trig["chasse-semaine"] = ((d.low < ls) & (c > ls), (d.high > hs) & (c < hs))
    r = I.rsi(c, 14)
    trig["rsi-retour"] = ((r > 45) & (r.rolling(5).min() < 40), (r < 55) & (r.rolling(5).max() > 60))
    rg = I.rang_glissant(ctx["prime"].rolling(7, min_periods=1).mean(), 365)
    trig["prime-pic"] = (rg < 0.1, rg > 0.9)
    trig["fng-cupidite"] = (ctx["fng"] < 25, ctx["fng"] > 60)
    cb = ctx["prime_cb"].rolling(7, min_periods=1).mean()
    trig["cb-negative"] = ((cb > 0) & (cb.shift() <= 0), (cb < 0) & (cb.shift() >= 0))
    h = DN.bougies(actif + "USDT", "spot", "1h")
    f = DN.financement(actif + "USDT")
    fh = f.reindex(h.index).fillna(0).values
    return dict(d=d, reg=reg, trig=trig, h=h, fh=fh, sma20=I.sma(c, 20), minuit=(h.index.hour == 23))


def simuler(P, sens, regime, declencheur, sortie):
    d, h = P["d"], P["h"]
    H, L, O, C = h.high.values, h.low.values, h.open.values, h.close.values
    th = h.index.values
    ok_l, ok_s = P["reg"][regime]
    tl, ts = P["trig"][declencheur]
    sig = (tl & ok_l) if sens == 1 else (ts & ok_s)
    sig = sig.fillna(False).values
    atr = d.atr.values; hi, lo = d.high.values, d.low.values
    sma20 = P["sma20"].values
    debut = np.searchsorted(th, (d.index + pd.Timedelta("1D")).values)
    trades = []
    libre_a = 0
    for i in np.flatnonzero(sig):
        j = debut[i] if i < len(debut) else len(C)
        if j >= len(C) - 1 or j < libre_a or np.isnan(atr[i]):
            continue
        e = O[j]
        stop = (lo[i] - 0.25 * atr[i]) if sens == 1 else (hi[i] + 0.25 * atr[i])
        risque = max(abs(e - stop), 0.5 * atr[i])
        stop = e - sens * risque
        cible, jours = None, 20
        if sortie.startswith("R"):
            cible = e + sens * float(sortie[1:]) * risque
        elif sortie.startswith("T"):
            jours = int(sortie[1:])
        fin = min(len(C), j + jours * 24)
        sortie_px, k = None, j
        fund = 0.0
        for k in range(j, fin):
            fund += fh_ if (fh_ := P["fh"][k]) else 0.0
            if sens == 1 and L[k] <= stop:
                sortie_px = min(stop, O[k]); break
            if sens == -1 and H[k] >= stop:
                sortie_px = max(stop, O[k]); break
            if cible is not None and ((sens == 1 and H[k] >= cible) or (sens == -1 and L[k] <= cible)):
                sortie_px = cible; break
            if sortie == "suivi" and P["minuit"][k] and k > j:      # clôture journalière
                jj = np.searchsorted(debut, k + 1, side="right") - 1
                if 0 <= jj < len(sma20) and ((sens == 1 and C[k] < sma20[jj]) or (sens == -1 and C[k] > sma20[jj])):
                    sortie_px = C[k]; break
        if sortie_px is None:
            sortie_px = C[k]
        brut = sens * (sortie_px / e - 1)
        net = brut - 2 * COUT - sens * fund
        trades.append((th[j], net, net * e / risque))
        libre_a = k + 1
    return pd.DataFrame(trades, columns=["t", "ret", "R"])


def stats(t):
    if len(t) < 5:
        return dict(n=len(t))
    r = t.ret.values
    return dict(n=len(r), gagnants=(r > 0).mean(), moy_pct=r.mean() * 100, R_moy=t.R.mean(),
                t=r.mean() / r.std() * np.sqrt(len(r)) if r.std() > 0 else 0,
                pf=r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.inf, total_pct=r.sum() * 100)


def un(args):
    actif, = args
    P = preparer(actif)
    lignes = []
    for sens, regime, dec, sortie in itertools.product((1, -1), P["reg"], P["trig"], ("R1.5", "R2", "R3", "T5", "T20", "suivi")):
        t = simuler(P, sens, regime, dec, sortie)
        t["per"] = np.where(pd.to_datetime(t.t).dt.tz_localize("UTC") < COUPE, "R", "V") if len(t) else []
        for per in ("R", "V", "T"):
            x = t if per == "T" else t[t.per == per]
            lignes.append(dict(actif=actif, sens="achat" if sens == 1 else "vente", regime=regime, declencheur=dec,
                               sortie=sortie, periode=per, **stats(x)))
    print(actif, "ok", flush=True)
    return lignes


if __name__ == "__main__":
    with Pool(2) as pool:
        res = pool.map(un, [("BTC",), ("ETH",)])
    df = pd.DataFrame([l for r in res for l in r])
    df.to_csv(os.path.join(OUT, "evenements.csv"), index=False, float_format="%.4f")
    print(len(df))
