"""Indicateurs, tous causaux : la valeur à la bougie t n'utilise que des bougies clôturées jusqu'à t incluse."""
import numpy as np
import pandas as pd


def sma(x, n):
    return x.rolling(n, min_periods=n).mean()


def ema(x, n):
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def ma(x, n, kind="sma"):
    return sma(x, n) if kind == "sma" else ema(x, n)


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d).clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    sg = m.ewm(span=sig, adjust=False, min_periods=sig).mean()
    return m, sg, m - sg


def atr(d, n=14):
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def ichimoku(d, t=9, k=26, s=52):
    """Tenkan, kijun, nuage (span A et B) TEL QU'IL EST AFFICHÉ à la bougie t (calculé k bougies plus tôt),
    nuage futur (calculé à t), et chikou comparé : clôture t contre clôture t-k."""
    mid = lambda n: (d.high.rolling(n).max() + d.low.rolling(n).min()) / 2
    tenkan, kijun = mid(t), mid(k)
    a_now = (tenkan + kijun) / 2
    b_now = mid(s)
    return dict(tenkan=tenkan, kijun=kijun, spanA=a_now.shift(k), spanB=b_now.shift(k),
                futurA=a_now, futurB=b_now, chikou_ok=d.close - d.close.shift(k))


def vwap_ancre(d, periode):
    """VWAP ancré au début de chaque semaine / mois / trimestre / année (UTC). Prix typique × volume."""
    tp = (d.high + d.low + d.close) / 3
    cle = d.index.tz_localize(None).to_period(periode)
    pv = (tp * d.volume).groupby(cle).cumsum()
    v = d.volume.groupby(cle).cumsum()
    return pv / v


def vwap_glissant(d, n):
    tp = (d.high + d.low + d.close) / 3
    return (tp * d.volume).rolling(n).sum() / d.volume.rolling(n).sum()


def vwap_depuis_plus_bas(d, n):
    """VWAP ancré au plus bas des n dernières bougies (l'ancre se déplace quand un nouveau plus bas apparaît).
    Calcul exact par sommes cumulées."""
    tp = (d.high + d.low + d.close) / 3
    pv = (tp * d.volume).cumsum().values
    v = d.volume.cumsum().values
    low = d.low.values
    out = np.full(len(d), np.nan)
    pos_min = pd.Series(low).rolling(n).apply(np.argmin, raw=True).values
    for i in range(n - 1, len(d)):
        j = i - n + 1 + int(pos_min[i])
        pv0 = pv[j - 1] if j > 0 else 0.0
        v0 = v[j - 1] if j > 0 else 0.0
        if v[i] - v0 > 0:
            out[i] = (pv[i] - pv0) / (v[i] - v0)
    return pd.Series(out, index=d.index)


def rang_glissant(x, n):
    """Rang centile de la dernière valeur dans la fenêtre des n dernières (0 à 1), causal."""
    return x.rolling(n, min_periods=max(20, n // 4)).rank(pct=True)


def zscore(x, n):
    return (x - x.rolling(n).mean()) / x.rolling(n).std()


def bollinger(c, n=20, k=2):
    m = sma(c, n)
    s = c.rolling(n).std()
    return m, m + k * s, m - k * s


def supertrend(d, n=10, mult=3):
    a = atr(d, n).values
    hl2 = ((d.high + d.low) / 2).values
    c = d.close.values
    up, dn = hl2 - mult * a, hl2 + mult * a
    sens = np.zeros(len(d))
    fu, fd = up.copy(), dn.copy()
    for i in range(1, len(d)):
        if np.isnan(a[i]):
            continue
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        if c[i] > fd[i - 1]:
            sens[i] = 1
        elif c[i] < fu[i - 1]:
            sens[i] = -1
        else:
            sens[i] = sens[i - 1]
    return pd.Series(sens, index=d.index)
