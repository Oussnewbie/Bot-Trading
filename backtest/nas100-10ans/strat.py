"""Classic indicator strategies on NAS100 CFD (H1 and daily bars built from M5 bid/ask), measured in R.
Entries at bar close (buy at ask, sell at bid); stop and target checked on the following bars, stop first."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from load10 import load10
from orbx import ema, rsi
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
SL = 0.1

def bars(rule, start="2018-05-01"):
    b, a = load10(); b = b[b.index >= start]; a = a[a.index >= start]
    agg = {"o": "first", "h": "max", "l": "min", "c": "last"}
    if rule == "D":
        m = b.index.hour * 60 + b.index.minute
        keep = (m >= 570) & (m < 960)
        b, a = b[keep], a[keep]
        key = b.index.tz_localize(None).normalize()
        B = b.groupby(key).agg(agg); A = a.groupby(key).agg(agg)
        B.index = B.index.tz_localize("America/New_York"); A.index = B.index
    else:
        B = b.resample(rule, label="left", closed="left").agg(agg).dropna()
        A = a.resample(rule, label="left", closed="left").agg(agg).reindex(B.index)
    return B, A

def atr(B, n=14):
    pc = B.c.shift()
    tr = np.maximum(B.h - B.l, np.maximum((B.h - pc).abs(), (B.l - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean().values

def backtest(B, A, signal, stop_fn, exit_fn=None, rr=None, max_bars=None):
    """signal(i) -> +1/-1/0 at close of bar i; stop_fn(i, d, entry) -> stop price; exit_fn(i, d) -> True to exit at close."""
    bo, bh, bl, bc = B.o.values, B.h.values, B.l.values, B.c.values
    ao, ah, al, ac = A.o.values, A.h.values, A.l.values, A.c.values
    out = []; i = 1; n = len(B)
    while i < n - 1:
        d = signal(i)
        if not d:
            i += 1; continue
        ent = (ac[i] if d == 1 else bc[i]) + d * SL
        sl = stop_fn(i, d, ent)
        if not np.isfinite(sl) or (ent - sl) * d <= 0:
            i += 1; continue
        risk = abs(ent - sl); tp = None if rr is None else ent + d * rr * risk
        r = None
        for k in range(i + 1, n):
            if d == 1:
                if bl[k] <= sl: r = (min(sl, bo[k]) - SL - ent) / risk; break
                if tp is not None and bh[k] >= tp: r = (tp - ent) / risk; break
            else:
                if ah[k] >= sl: r = (ent - max(sl, ao[k]) - SL) / risk; break
                if tp is not None and al[k] <= tp: r = (ent - tp) / risk; break
            if (exit_fn is not None and exit_fn(k, d)) or (max_bars and k - i >= max_bars):
                px = bc[k] if d == 1 else ac[k]; r = (px - ent) * d / risk; break
        if r is None: break
        out.append((B.index[i], r, d)); i = k + 1
    return out

def report(lab, out):
    if not out:
        print(f"| {lab} | 0 |"); return
    r = pd.Series([x[1] for x in out], index=pd.DatetimeIndex([x[0] for x in out]))
    tr, te = r[r.index < SPLIT], r[r.index >= SPLIT]
    yrs = r.groupby(r.index.year).sum(); eq = r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    print(f"| {lab} | {len(r)} | {100*(r>0).mean():.0f} % | {r.mean():+.3f}R | {tr.mean():+.3f} / {te.mean():+.3f} | {r.sum():+.0f}R | -{dd:.0f}R | {(yrs>0).sum()}/{len(yrs)} |", flush=True)

if __name__ == "__main__":
    print("| Stratégie | Trades | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse | Années + |")
    print("|---|---|---|---|---|---|---|---|")
    # ---- daily
    B, A = bars("D")
    c = B.c.values; sma200 = B.c.rolling(200).mean().values; sma5 = B.c.rolling(5).mean().values
    r2 = rsi(c, 2); at = atr(B)
    report("RSI(2) de Connors (jour) : achat RSI2 < 10 au-dessus de la MA200, sortie au-dessus de la MA5, stop 2,5 ATR",
           backtest(B, A, lambda i: 1 if c[i] > sma200[i] and r2[i] < 10 else 0, lambda i, d, e: e - 2.5 * at[i],
                    lambda k, d: c[k] > sma5[k]))
    report("RSI(2) de Connors, achats et ventes",
           backtest(B, A, lambda i: 1 if c[i] > sma200[i] and r2[i] < 10 else -1 if c[i] < sma200[i] and r2[i] > 90 else 0,
                    lambda i, d, e: e - d * 2.5 * at[i], lambda k, d: (c[k] > sma5[k]) if d == 1 else (c[k] < sma5[k])))
    hi20, lo20 = B.h.rolling(20).max().shift().values, B.l.rolling(20).min().shift().values
    report("Cassure de Donchian 20 jours (tendance), stop 2 ATR, sortie sur le canal 10 jours",
           backtest(B, A, lambda i: 1 if c[i] > hi20[i] else -1 if c[i] < lo20[i] else 0, lambda i, d, e: e - d * 2 * at[i],
                    lambda k, d: (c[k] < B.l.rolling(10).min().shift().values[k]) if d == 1 else (c[k] > B.h.rolling(10).max().shift().values[k])))
    # ---- H1
    B, A = bars("1h")
    c = B.c.values; h = B.h.values; l = B.l.values; at = atr(B)
    e200 = ema(c, 200); m = ema(c, 12) - ema(c, 26); sig = ema(m, 9); hist = m - sig
    mid = B.c.rolling(20).mean().values; sd = B.c.rolling(20).std().values
    up, dn = mid + 2 * sd, mid - 2 * sd
    r14 = rsi(c, 14)
    tenkan = (B.h.rolling(9).max() + B.l.rolling(9).min()).values / 2
    kijun = (B.h.rolling(26).max() + B.l.rolling(26).min()).values / 2
    sa = pd.Series((tenkan + kijun) / 2).shift(26).values
    sb = pd.Series((B.h.rolling(52).max() + B.l.rolling(52).min()).values / 2).shift(26).values
    hours = B.index.hour.values
    rth = (hours >= 9) & (hours < 16)
    def cross_up(x, y, i): return x[i] > y[i] and x[i - 1] <= y[i - 1]
    report("MACD H1 qui croise dans le sens de l'EMA200, stop 2 ATR, objectif 2R",
           backtest(B, A, lambda i: 1 if cross_up(m, sig, i) and c[i] > e200[i] else -1 if cross_up(sig, m, i) and c[i] < e200[i] else 0,
                    lambda i, d, e: e - d * 2 * at[i], rr=2.0))
    report("MACD H1 + EMA200, sortie au croisement inverse",
           backtest(B, A, lambda i: 1 if cross_up(m, sig, i) and c[i] > e200[i] else -1 if cross_up(sig, m, i) and c[i] < e200[i] else 0,
                    lambda i, d, e: e - d * 2 * at[i], lambda k, d: (m[k] < sig[k]) if d == 1 else (m[k] > sig[k])))
    report("Ichimoku H1 : croisement Tenkan/Kijun au-dessus / sous le nuage, stop 2 ATR, sortie au croisement inverse",
           backtest(B, A, lambda i: 1 if cross_up(tenkan, kijun, i) and c[i] > np.nanmax([sa[i], sb[i]]) else
                    -1 if cross_up(kijun, tenkan, i) and c[i] < np.nanmin([sa[i], sb[i]]) else 0,
                    lambda i, d, e: e - d * 2 * at[i], lambda k, d: (tenkan[k] < kijun[k]) if d == 1 else (tenkan[k] > kijun[k])))
    report("Bollinger H1 retour à la moyenne : clôture hors bande (20, 2), objectif la moyenne, stop 1,5 ATR, séance US",
           backtest(B, A, lambda i: (1 if c[i] < dn[i] else -1 if c[i] > up[i] else 0) if rth[i] else 0,
                    lambda i, d, e: e - d * 1.5 * at[i], lambda k, d: (c[k] >= mid[k]) if d == 1 else (c[k] <= mid[k]), max_bars=24))
    report("Bollinger H1 retour à la moyenne, achats seulement au-dessus de l'EMA200",
           backtest(B, A, lambda i: 1 if rth[i] and c[i] < dn[i] and c[i] > e200[i] else 0,
                    lambda i, d, e: e - 1.5 * at[i], lambda k, d: c[k] >= mid[k], max_bars=24))
    report("RSI14 H1 survendu (< 30) au-dessus de l'EMA200 : achat, sortie RSI > 50, stop 2 ATR",
           backtest(B, A, lambda i: 1 if r14[i] < 30 and c[i] > e200[i] else 0, lambda i, d, e: e - 2 * at[i], lambda k, d: r14[k] > 50))
    # Fibonacci pullback: uptrend above EMA200, swing = last 50 bars; buy limit at 61.8 % approximated by close crossing below it
    hh, ll = B.h.rolling(50).max().values, B.l.rolling(50).min().values
    fib618 = hh - 0.618 * (hh - ll)
    report("Pullback Fibonacci 61,8 % (H1, tendance EMA200), stop sous le bas du swing, objectif le haut du swing",
           backtest(B, A, lambda i: 1 if c[i] > e200[i] and l[i] <= fib618[i] < c[i] and hh[i] > hh[i - 10] else 0,
                    lambda i, d, e: ll[i] - 0.5 * at[i], lambda k, d: False, rr=None, max_bars=48))
