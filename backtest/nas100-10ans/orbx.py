"""ORB 5-minute (New York 9:30) with pre-trade filters and exit variants, NAS100 CFD, bid/ask fills.
Every feature is known at 9:35 NY, before the stop orders are placed."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam
from fam import G

def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().values
def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up = pd.Series(np.maximum(d, 0)).ewm(alpha=1/n, adjust=False).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1/n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values

def features():
    t, mins, BO, BH, BL, BC = G["t"], G["mins"], G["BO"], G["BH"], G["BL"], G["BC"]
    V = fam.load10.__globals__  # noqa
    s0 = np.flatnonzero(mins == 570)
    s0 = s0[G["flat"][s0] > s0]
    cal = G["cal"]
    df = pd.DataFrame({"o": BO, "h": BH, "l": BL, "c": BC}, index=t)
    # RTH daily bars (9:30-16:00)
    rth = df[(mins >= 570) & (mins < 960)]
    D = rth.groupby(rth.index.tz_localize(None).normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    D["sma200"] = D.c.rolling(200).mean(); D["sma50"] = D.c.rolling(50).mean()
    tr = np.maximum(D.h - D.l, np.maximum((D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs()))
    D["atr"] = tr.rolling(14).mean()
    Dp = D.shift(1)  # previous session values only
    # H1 bars, last closed before 9:30 = bar of 8:00
    H = df.resample("1h", label="left", closed="left").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    H["ema200"] = ema(H.c.values, 200); H["ema50"] = ema(H.c.values, 50); H["rsi"] = rsi(H.c.values)
    m = ema(H.c.values, 12) - ema(H.c.values, 26); H["macdh"] = m - ema(m, 9)
    tenkan = (H.h.rolling(9).max() + H.l.rolling(9).min()) / 2; kijun = (H.h.rolling(26).max() + H.l.rolling(26).min()) / 2
    H["spanA"] = ((tenkan + kijun) / 2).shift(26); H["spanB"] = ((H.h.rolling(52).max() + H.l.rolling(52).min()) / 2).shift(26)
    H["tk"] = tenkan - kijun
    mid = H.c.rolling(20).mean(); sd = H.c.rolling(20).std()
    H["pb"] = (H.c - (mid - 2 * sd)) / (4 * sd); H["bbw"] = 4 * sd / mid
    H["bbw_rank"] = H.bbw.rolling(500).rank(pct=True)
    e5 = ema(BC, 200); r5 = rsi(BC)
    rows = []
    vol = None
    for i in s0:
        day = cal[i]
        if day not in Dp.index: continue
        dp = Dp.loc[day]
        hkey = t[i].floor("h") - pd.Timedelta(hours=2)  # 8:00 bar closes at 9:00
        if hkey not in H.index: continue
        hb = H.loc[hkey]
        mo = np.flatnonzero((cal == day) & (mins == 0))
        on = (t > t[i] - pd.Timedelta(hours=15, minutes=30)) & (np.arange(len(t)) < i)
        rows.append(dict(i=i, day=day, c=BC[i], orH=BH[i], orL=BL[i], o930=BO[i],
            d_sma200=dp.c - dp.sma200, d_sma50=dp.c - dp.sma50, prevdir=dp.c - dp.o, gap=BO[i] - dp.c, atrd=dp.atr,
            h_ema200=hb.c - hb.ema200, h_ema50=hb.c - hb.ema50, h_rsi=hb.rsi - 50, h_macd=hb.macdh,
            ichi=(1 if hb.c > max(hb.spanA, hb.spanB) else -1 if hb.c < min(hb.spanA, hb.spanB) else 0) if np.isfinite(hb.spanB) else 0,
            h_tk=hb.tk, h_pb=hb.pb - 0.5, bbw_rank=hb.bbw_rank,
            m5_ema200=BC[i] - e5[i], m5_rsi=r5[i] - 50,
            mid_open=BC[i] - (BO[mo[0]] if len(mo) else np.nan),
            pdh=dp.h, pdl=dp.l))
    F = pd.DataFrame(rows).set_index("i")
    F["orw"] = F.orH - F.orL
    F["or_atr"] = F.orw / F.atrd
    return F

def last_before(tex):
    key = ("lb", tex)
    if key not in G:
        idx = np.arange(len(G["t"])); before = G["mins"] < tex
        s = pd.Series(np.where(before, idx, -1), index=G["cal"])
        G[key] = np.where(before, s.groupby(level=0).transform("max").values, -1)
    return G[key]

def run_trade(i, d, entry, sl, tp, last_i, be=None, trail=None):
    BO, BH, BL, AO, AH, AL, BC, AC, A = (G[k] for k in ("BO", "BH", "BL", "AO", "AH", "AL", "BC", "AC", "ATR"))
    S = fam.SLIP
    risk = abs(entry - sl)
    if (d == 1 and BL[i] <= sl) or (d == -1 and AH[i] >= sl):
        return (sl - d * S - entry) * d / risk
    stop, best = sl, entry
    for k in range(i + 1, last_i + 1):
        if d == 1:
            if BL[k] <= stop: return (min(stop, BO[k]) - S - entry) / risk
            if tp is not None and BH[k] >= tp: return (tp - entry) / risk
            best = max(best, BH[k])
        else:
            if AH[k] >= stop: return (entry - max(stop, AO[k]) - S) / risk
            if tp is not None and AL[k] <= tp: return (entry - tp) / risk
            best = min(best, AL[k])
        gain = (best - entry) * d / risk
        if be is not None and gain >= be:
            stop = max(stop, entry) if d == 1 else min(stop, entry)
        if trail is not None and gain >= 1:
            cand = best - d * trail * A[k]
            stop = max(stop, cand) if d == 1 else min(stop, cand)
    px = BC[last_i] if d == 1 else AC[last_i]
    return (px - entry) * d / risk

def orb(F, allow=None, rr=None, tex=950, be=None, trail=None, cutoff=720, tgt=None):
    """allow(row) -> set of directions allowed that day. tgt='pd': target = previous day high/low if beyond entry."""
    BH, BL, AH, AO, BO, mins = G["BH"], G["BL"], G["AH"], G["AO"], G["BO"], G["mins"]
    lb = last_before(tex)
    out = []
    for i, row in F.iterrows():
        dirs = {1, -1} if allow is None else allow(row)
        if not dirs: continue
        last_i = lb[i]
        if last_i <= i: continue
        orH, orL = row.orH, row.orL
        for k in range(i + 1, last_i + 1):
            if mins[k] >= cutoff: break
            up = 1 in dirs and AH[k] >= orH; dn = -1 in dirs and BL[k] <= orL
            if up and dn:
                out.append((G["t"][k], -1.0, 0)); break
            if up or dn:
                d = 1 if up else -1
                lvl, sl = (orH, orL) if d == 1 else (orL, orH)
                px = (max(lvl, AO[k]) + fam.SLIP) if d == 1 else (min(lvl, BO[k]) - fam.SLIP)
                tp = None if rr is None else px + d * rr * abs(px - sl)
                if tgt == "pd":
                    lv = row.pdh if d == 1 else row.pdl
                    if (lv - px) * d > abs(px - sl): tp = lv
                out.append((G["t"][k], run_trade(k, d, px, sl, tp, last_i, be, trail), d))
                break
    return out
