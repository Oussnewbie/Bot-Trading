"""Other setup families on NAS100 CFD M5 (bid chart, ask/bid execution), New York time.

ORB: New York opening range breakout. CONT: continuation after a liquidity pool breaks (close beyond the level)
inside a kill zone. Conservative fills: on the bar where an order fills, only the stop can be hit; if stop and
target are inside the same later bar, the stop wins.
"""
import sys
sys.path.insert(0, ".")
import numpy as np, pandas as pd
from load10 import load10
from sim import pivots

SLIP = 0.1
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
G = {}


def prep(start="2018-05-01"):
    b, a = load10()
    b = b[b.index >= start]; a = a[a.index >= start]
    t = b.index
    g = dict(t=t, BO=b.o.values, BH=b.h.values, BL=b.l.values, BC=b.c.values,
             AO=a.o.values, AH=a.h.values, AL=a.l.values, AC=a.c.values)
    mins = (t.hour * 60 + t.minute).values
    g["mins"] = mins
    pc = np.roll(g["BC"], 1); pc[0] = g["BC"][0]
    tr = np.maximum(g["BH"] - g["BL"], np.maximum(abs(g["BH"] - pc), abs(g["BL"] - pc)))
    g["ATR"] = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().values
    ph, pl = pivots(g["BH"], g["BL"], 2)
    g["swH"] = pd.Series(ph).ffill().values
    g["swL"] = pd.Series(pl).ffill().values
    cal = t.tz_localize(None).normalize()
    g["cal"] = cal
    # last bar before 15:50 on the same calendar day, for every bar
    idx = np.arange(len(t))
    before = mins < 15 * 60 + 50
    s = pd.Series(np.where(before, idx, -1), index=cal)
    last = s.groupby(level=0).transform("max").values
    g["flat"] = np.where(before, last, -1)
    # trading day for pools: starts at 19:00 NY
    g["tday"] = (t + pd.Timedelta(hours=5)).tz_localize(None).normalize()
    G.update(g)
    return g


def execute(i0, d, kind, entry, sl, tp, exp_i, last_i, fill_px=None):
    """kind: market (fill at close of i0), limit (from i0+1 until exp_i), atbar (filled at fill_px on bar i0)."""
    BO, BH, BL, BC, AO, AH, AL, AC = (G[k] for k in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC"))
    filled = False
    if kind == "market":
        entry = (AC[i0] if d == 1 else BC[i0]) + d * SLIP
        filled = True
        i = i0 + 1
    elif kind == "atbar":
        entry = fill_px
        filled = True
        if (d == 1 and BL[i0] <= sl) or (d == -1 and AH[i0] >= sl):
            return (sl - d * SLIP - entry) * d / abs(entry - sl), i0, i0
        i = i0 + 1
    else:
        i = i0 + 1
    if filled and (entry - sl) * d <= 0:
        return None
    fi = i0 if filled else None
    while i <= last_i:
        if not filled:
            if i > exp_i:
                return None
            if d == 1:
                hit, px = AL[i] <= entry, min(entry, AO[i])
            else:
                hit, px = BH[i] >= entry, max(entry, BO[i])
            if hit:
                entry, filled, fi = px, True, i
                if (entry - sl) * d <= 0:
                    return None
                if (d == 1 and BL[i] <= sl) or (d == -1 and AH[i] >= sl):
                    return (sl - d * SLIP - entry) * d / abs(entry - sl), i, fi
            elif tp is not None and ((d == 1 and BH[i] >= tp) or (d == -1 and BL[i] <= tp)):
                return None
            i += 1
            continue
        risk = abs(entry - sl)
        if d == 1:
            if BL[i] <= sl:
                return (min(sl, BO[i]) - SLIP - entry) / risk, i, fi
            if tp is not None and BH[i] >= tp:
                return (tp - entry) / risk, i, fi
        else:
            if AH[i] >= sl:
                return (entry - max(sl, AO[i]) - SLIP) / risk, i, fi
            if tp is not None and AL[i] <= tp:
                return (entry - tp) / risk, i, fi
        i += 1
    if not filled:
        return None
    px = BC[last_i] if d == 1 else AC[last_i]
    return (px - entry) * d / abs(entry - sl), last_i, fi


def target(entry, sl, d, rr):
    return None if rr is None else entry + d * rr * abs(entry - sl)


def orb(p):
    """p: orMin, entry ('close'|'stop'), stop ('range'|'mid'), rr (None = end of day), maxT, cutoff (minutes)."""
    t, mins, BH, BL, BC, AH = G["t"], G["mins"], G["BH"], G["BL"], G["BC"], G["AH"]
    out = []
    cal = G["cal"]
    starts = np.flatnonzero((mins == 570))
    for s0 in starts:
        last_i = G["flat"][s0]
        if last_i < 0:
            continue
        e0 = s0
        while e0 + 1 <= last_i and mins[e0 + 1] < 570 + p["orMin"] and cal[e0 + 1] == cal[s0]:
            e0 += 1
        orH, orL = BH[s0:e0 + 1].max(), BL[s0:e0 + 1].min()
        if orH <= orL:
            continue
        mid = (orH + orL) / 2
        i, n, used = e0 + 1, 0, set()
        while i <= last_i and mins[i] < p["cutoff"] and n < p["maxT"]:
            d = 0
            if p["entry"] == "close":
                if BC[i] > orH and 1 not in used:
                    d = 1
                elif BC[i] < orL and -1 not in used:
                    d = -1
                if d:
                    sl = (orL if d == 1 else orH) if p["stop"] == "range" else mid
                    ent = AC_close = None
                    r = execute(i, d, "market", None, sl, None, i, last_i)
                    if r is not None:
                        ent = (G["AC"][i] if d == 1 else BC[i]) + d * SLIP
                        tp = target(ent, sl, d, p["rr"])
                        r = execute(i, d, "market", None, sl, tp, i, last_i)
            else:
                up = G["AH"][i] >= orH and 1 not in used
                dn = BL[i] <= orL and -1 not in used
                if up and dn:
                    out.append((t[i], -1.0, 0)); n += 1; used |= {1, -1}; break
                if up or dn:
                    d = 1 if up else -1
                    lvl = orH if d == 1 else orL
                    px = (max(lvl, G["AO"][i]) + SLIP) if d == 1 else (min(lvl, G["BO"][i]) - SLIP)
                    sl = (orL if d == 1 else orH) if p["stop"] == "range" else mid
                    tp = target(px, sl, d, p["rr"])
                    r = execute(i, d, "atbar", None, sl, tp, i, last_i, fill_px=px)
            if d:
                used.add(d)
                if r is not None:
                    out.append((t[i], r[0], d)); n += 1
                    i = r[1] + 1
                    continue
            i += 1
    return out


def cont(p):
    """Continuation after a pool break. p: pools (set of 'asia','pd','lon'), sess (set of 0 London, 1 NY),
    disp (body in ATR), entry ('close'|'retest'|'mid'), stop ('candle'|'swing'), rr (None = end of day), maxT."""
    t, mins, BO, BH, BL, BC = G["t"], G["mins"], G["BO"], G["BH"], G["BL"], G["BC"]
    A, tday = G["ATR"], G["tday"]
    out = []
    bounds = np.flatnonzero(np.r_[True, tday[1:] != tday[:-1]])
    bounds = np.r_[bounds, len(t)]
    prevH = prevL = None
    for k in range(len(bounds) - 1):
        lo, hi = bounds[k], bounds[k + 1]
        if hi - lo < 100:
            prevH = prevL = None
            continue
        pools = []  # [level, dir, active_from_minute_rule, used]
        if "pd" in p["pools"] and prevH is not None:
            pools += [[prevH, 1, "day", False], [prevL, -1, "day", False]]
        dm = mins[lo:hi]
        asia = (dm >= 19 * 60) | (dm < 120)
        lon = (dm >= 120) & (dm < 300)
        if "asia" in p["pools"] and asia.any():
            ii = lo + np.flatnonzero(asia)
            pools += [[BH[ii].max(), 1, "asia", False], [BL[ii].min(), -1, "asia", False]]
        if "lon" in p["pools"] and lon.any():
            ii = lo + np.flatnonzero(lon)
            pools += [[BH[ii].max(), 1, "lon", False], [BL[ii].min(), -1, "lon", False]]
        prevH, prevL = BH[lo:hi].max(), BL[lo:hi].min()
        n, busy = 0, -1
        for i in range(lo, hi):
            m = mins[i]
            if m >= 19 * 60:
                continue  # Asia session: the pools are not known yet
            kzs = 0 if 120 <= m < 300 else 1 if 510 <= m < 660 else -1
            for pl in pools:
                if pl[3]:
                    continue
                lvl, d, src = pl[0], pl[1], pl[2]
                if src == "asia" and m < 120:
                    continue
                if src == "lon" and m < 300:
                    continue
                beyond_wick = BH[i] > lvl if d == 1 else BL[i] < lvl
                if not beyond_wick:
                    continue
                if kzs < 0 or kzs not in p["sess"]:
                    pl[3] = True  # taken outside the traded windows: consumed
                    continue
                closed = BC[i] > lvl if d == 1 else BC[i] < lvl
                body = (BC[i] - BO[i]) * d
                if not closed:
                    continue
                pl[3] = True
                if body < p["disp"] * A[i] or i <= busy or n >= p["maxT"]:
                    continue
                last_i = G["flat"][i]
                if last_i < 0 or last_i <= i:
                    continue
                if p["stop"] == "candle":
                    sl = (BL[i] if d == 1 else BH[i]) - d * 0.1 * A[i]
                else:
                    sl = (G["swL"][i] if d == 1 else G["swH"][i]) - d * 0.1 * A[i]
                if p["entry"] == "close":
                    ent0 = G["AC"][i] if d == 1 else BC[i]
                elif p["entry"] == "retest":
                    ent0 = lvl
                else:
                    ent0 = (BO[i] + BC[i]) / 2
                if not np.isfinite(sl) or (ent0 - sl) * d < A[i]:
                    sl = ent0 - d * A[i]
                tp = target(ent0, sl, d, p["rr"])
                kind = "market" if p["entry"] == "close" else "limit"
                r = execute(i, d, kind, ent0, sl, tp, i + 12, last_i)
                if r is None:
                    busy = min(i + 12, last_i)
                    continue
                out.append((t[i], r[0], d)); n += 1
                busy = r[1]
    return out


def stats(out):
    if not out:
        return dict(n=0)
    r = pd.Series([x[1] for x in out], index=pd.DatetimeIndex([x[0] for x in out]))
    eq = r.cumsum()
    dd = (eq.cummax().clip(lower=0) - eq).max()
    tr, te = r[r.index < SPLIT], r[r.index >= SPLIT]
    yrs = r.groupby(r.index.year).sum()
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), exp=r.mean(), total=r.sum(), pf=wins / losses if losses else np.inf, dd=dd,
                win=(r > 0).mean() * 100, ntr=len(tr), etr=tr.mean() if len(tr) else np.nan,
                nte=len(te), ete=te.mean() if len(te) else np.nan, ttr=tr.sum(), tte=te.sum(),
                ypos=int((yrs > 0).sum()), ny=len(yrs), yrs={int(k): round(v, 1) for k, v in yrs.items()})


def orb_first(p):
    """Trade only in the direction of the first 5-minute candle after 9:30: stop order at its high (green) or low
    (red), stop at the other extreme, exit at p['rr'] R or end of day."""
    t, mins, BO, BH, BL, BC = G["t"], G["mins"], G["BO"], G["BH"], G["BL"], G["BC"]
    out = []
    for s0 in np.flatnonzero(mins == 570):
        last_i = G["flat"][s0]
        if last_i <= s0:
            continue
        d = 1 if BC[s0] > BO[s0] else -1 if BC[s0] < BO[s0] else 0
        if d == 0 or BH[s0] <= BL[s0]:
            continue
        lvl, sl = (BH[s0], BL[s0]) if d == 1 else (BL[s0], BH[s0])
        for i in range(s0 + 1, last_i + 1):
            if mins[i] >= p["cutoff"]:
                break
            if (d == 1 and G["AH"][i] >= lvl) or (d == -1 and BL[i] <= lvl):
                px = (max(lvl, G["AO"][i]) + SLIP) if d == 1 else (min(lvl, BO[i]) - SLIP)
                r = execute(i, d, "atbar", None, sl, target(px, sl, d, p["rr"]), i, last_i, fill_px=px)
                if r is not None:
                    out.append((t[i], r[0], d))
                break
    return out
