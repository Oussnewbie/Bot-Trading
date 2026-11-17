"""Étape 9 : comment détecter un retournement de tendance ? Test de chaque détecteur sur M5, M15, M30, H1, H4, 1d.

Vérité terrain (« triple barrière », López de Prado) : à la clôture de chaque bougie, on regarde la suite. Le prix
touche-t-il d'abord +b % (hausse) ou -b % (baisse), dans les 100 bougies suivantes ? b est mis à l'échelle de l'unité
de temps : 15 % × racine(durée de la bougie / 1 jour), soit 15 % en 1d, 6,1 % en 4h, 3,1 % en 1h, 2,2 % en 30m,
1,5 % en 15m, 0,9 % en 5m.

Un détecteur de retournement baissier « marche » si, après son signal, la baisse arrive d'abord PLUS SOUVENT qu'en
moyenne (taux de base) : lift = précision ÷ taux de base > 1. Pour gagner en tradant avec un stop à +b et un objectif
à -b, il faut une précision supérieure à 50 % + coût ÷ (2b) parmi les trades qui touchent une barrière.

Détecteurs testés (et leur miroir haussier) : RSI > 70, divergence RSI, divergence MACD, divergence CVD (order flow),
chasse de liquidité au-dessus du plus haut de 20 bougies, climax de volume avec mèche, englobante au sommet, CHoCH
(cassure de structure), divergence + CHoCH, croisement EMA 9/21, clôture sous EMA50, sous la kijun, sortie du nuage,
retour dans les bandes de Bollinger, usure de la tendance (première clôture sous l'EMA20 après 20 bougies dessus).
Chacun sans filtre, dans le sens de la tendance de fond journalière, et contre elle.
Sortie : sorties/retournements.csv
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as sw

import donnees as DN
import indicateurs as I
import signaux as S
from petites_tf import fond, _structure, MIN, COUPE, DEBUT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
H = 100


def barriere(tf):
    return 0.15 * np.sqrt(MIN[tf] / 1440)


def etiquettes(d, b):
    """+1 si +b est touché d'abord, -1 si -b d'abord, 0 si aucun en H bougies ou les deux dans la même bougie."""
    c, hi, lo = d.close.values, d.high.values, d.low.values
    n = len(c)
    hp = np.r_[hi[1:], np.full(H, np.nan)]; lp = np.r_[lo[1:], np.full(H, np.nan)]
    out = np.zeros(n, dtype=np.int8)
    for s in range(0, n, 20000):
        e = min(n, s + 20000)
        wh = sw(hp, H)[s:e]; wl = sw(lp, H)[s:e]
        up = (wh >= (c[s:e] * (1 + b))[:, None]); dn = (wl <= (c[s:e] * (1 - b))[:, None])
        fu = np.where(up.any(1), up.argmax(1), H + 1); fd = np.where(dn.any(1), dn.argmax(1), H + 1)
        out[s:e] = np.where(fu < fd, 1, np.where(fd < fu, -1, 0))
    return pd.Series(out, index=d.index)


def detecteurs(d):
    c, h, l, v = d.close, d.high, d.low, d.volume
    n = 20
    r14 = I.rsi(c, 14)
    m, sg, hist = I.macd(c)
    haut20, bas20 = c >= c.rolling(n).max(), c <= c.rolling(n).min()
    cvd = d.delta.cumsum()
    hp, lp = h.rolling(n).max().shift(), l.rolling(n).min().shift()
    rng = (h - l).replace(0, np.nan)
    e9, e21, e50, e20 = I.ema(c, 9), I.ema(c, 21), I.ema(c, 50), I.ema(c, 20)
    ich = I.ichimoku(d, 9, 26, 52)
    haut, bas = np.maximum(ich["spanA"], ich["spanB"]), np.minimum(ich["spanA"], ich["spanB"])
    mb, hb, bb = I.bollinger(c, 20, 2)
    st = _structure(d, 3)
    croise_bas = lambda x, y: (x < y) & (x.shift() >= y.shift())
    recent = lambda x: x.rolling(10).max().fillna(0).astype(bool)
    div_rsi = (bas20 & (r14 > r14.rolling(n).min() + 5), haut20 & (r14 < r14.rolling(n).max() - 5))
    div_cvd = (bas20 & (cvd - cvd.shift(n) > 0), haut20 & (cvd - cvd.shift(n) < 0))
    choch = ((st == 1) & (st.shift() == -1), (st == -1) & (st.shift() == 1))
    return {   # nom : (signal de retournement haussier, signal de retournement baissier)
        "rsi-extreme": ((r14 < 30) & (r14.shift() >= 30), (r14 > 70) & (r14.shift() <= 70)),
        "div-rsi": div_rsi,
        "div-macd": (bas20 & (hist > hist.rolling(n).min() * 0.5) & (hist.rolling(n).min() < 0),
                     haut20 & (hist < hist.rolling(n).max() * 0.5) & (hist.rolling(n).max() > 0)),
        "div-cvd": div_cvd,
        "chasse-liquidite": ((l < lp) & (c > lp), (h > hp) & (c < hp)),
        "climax-volume": ((v > 3 * v.rolling(50).mean()) & ((np.minimum(c, d.open) - l) / rng > 0.5),
                          (v > 3 * v.rolling(50).mean()) & ((h - np.maximum(c, d.open)) / rng > 0.5)),
        "englobante-extreme": ((c > d.open) & (c.shift() < d.open.shift()) & (c > d.open.shift()) & bas20.shift(1, fill_value=False),
                               (c < d.open) & (c.shift() > d.open.shift()) & (c < d.open.shift()) & haut20.shift(1, fill_value=False)),
        "choch": choch,
        "div-rsi+choch": (recent(div_rsi[0]) & choch[0], recent(div_rsi[1]) & choch[1]),
        "div-cvd+choch": (recent(div_cvd[0]) & choch[0], recent(div_cvd[1]) & choch[1]),
        "croisement-ema9-21": (croise_bas(e21, e9), croise_bas(e9, e21)),
        "cloture-ema50": (croise_bas(e50, c), croise_bas(c, e50)),
        "cloture-kijun": (croise_bas(ich["kijun"], c), croise_bas(c, ich["kijun"])),
        "sortie-nuage": (croise_bas(haut, c), croise_bas(c, bas)),
        "retour-bollinger": ((c > bb) & (c.shift() <= bb.shift()), (c < hb) & (c.shift() >= hb.shift())),
        "usure-ema20": ((c > e20) & ((c.shift() < e20.shift()).rolling(20).sum() == 20),
                        (c < e20) & ((c.shift() > e20.shift()).rolling(20).sum() == 20)),
    }


def un(args):
    actif, tf = args
    d = DN.bougies_m5(actif + "USDT", tf)
    d = d[d.index >= DEBUT - pd.Timedelta("60D")]
    b = barriere(tf)
    lab = etiquettes(d, b)
    sc = fond(actif, d.index)
    per = {"R": (d.index >= DEBUT) & (d.index < COUPE), "V": d.index >= COUPE}
    filtres = {"sans": (True, True), "dans-le-sens": (sc >= 0.25, sc <= -0.25), "contre": (sc <= -0.25, sc >= 0.25)}
    lignes = []
    for pk, pm in per.items():
        L = lab[pm]
        lignes.append(dict(actif=actif, tf=tf, detecteur="_base", filtre="", sens="", periode=pk, barriere=b,
                           n=len(L), p_hausse=(L == 1).mean(), p_baisse=(L == -1).mean()))
        for fn, (ok_l, ok_s) in filtres.items():
            for sens, ok, cible in (("haussier", ok_l, 1), ("baissier", ok_s, -1)):
                okm = (ok if isinstance(ok, bool) else ok.values)
                Lb = lab[pm & okm] if not isinstance(ok, bool) else L
                lignes.append(dict(actif=actif, tf=tf, detecteur="_base", filtre=fn, sens=sens, periode=pk, barriere=b,
                                   n=len(Lb), precision=(Lb == cible).mean(), contraire=(Lb == -cible).mean()))
    for nom, (sl, ss) in detecteurs(d).items():
        for fn, (ok_l, ok_s) in filtres.items():
            for sens, sig, ok, cible in (("haussier", sl, ok_l, 1), ("baissier", ss, ok_s, -1)):
                s = sig.fillna(False).astype(bool)
                if not isinstance(ok, bool):
                    s = s & ok
                for pk, pm in per.items():
                    x = lab[s & pm]
                    if len(x) < 20:
                        continue
                    lignes.append(dict(actif=actif, tf=tf, detecteur=nom, filtre=fn, sens=sens, periode=pk, barriere=b,
                                       n=len(x), precision=(x == cible).mean(), contraire=(x == -cible).mean()))
    print(actif, tf, flush=True)
    return lignes


if __name__ == "__main__":
    taches = [(a, tf) for a in ("BTC", "ETH") for tf in ("5m", "15m", "30m", "1h", "4h", "1d")]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 3) as pool:
        res = pool.map(un, taches, chunksize=1)
    df = pd.DataFrame([l for r in res for l in r])
    df.to_csv(os.path.join(OUT, "retournements.csv"), index=False, float_format="%.4f")
    print(len(df))
