"""Bar-by-bar replica of the AMD+ Pine strategies (v1 and v2) on 5-minute data, times in New York.

Conservative fills: on the bar where a limit order fills, only the stop can be hit; when stop and target
are both inside a later bar, the stop wins. Results are in R, so they do not depend on contract size.
"""
import sys
import numpy as np
import pandas as pd

TICK = 0.25
SLIP = 2 * TICK
_CACHE = {}


def load(path):
    d = pd.read_csv(path, index_col=0)
    d.index = pd.to_datetime(d.index, utc=True).tz_convert("America/New_York")
    d = d[["Open", "High", "Low", "Close"]].dropna()
    d.columns = ["o", "h", "l", "c"]
    return d


def in_sess(mins, a, b):
    # session "HHMM-HHMM" on bar open time, minutes since midnight; wraps over midnight
    return (mins >= a) & (mins < b) if a < b else (mins >= a) | (mins < b)


def m(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def atr(d, n=14):
    pc = d.c.shift(1)
    tr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean().values


def pivots(h, l, n):
    """Pivot value known at bar i (pivot at i-n confirmed with n bars on each side)."""
    N = len(h)
    ph = np.full(N, np.nan)
    pl = np.full(N, np.nan)
    for i in range(2 * n, N):
        j = i - n
        win_h = h[j - n:j + n + 1]
        win_l = l[j - n:j + n + 1]
        if h[j] == win_h.max() and (win_h == h[j]).sum() == 1:
            ph[i] = h[j]
        if l[j] == win_l.min() and (win_l == l[j]).sum() == 1:
            pl[i] = l[j]
    return ph, pl


def htf_trend(d, rule, length=2):
    """Structure trend of a higher timeframe, value of the last closed HTF bar mapped onto M5 bars."""
    g = d.resample(rule, origin=pd.Timestamp("2000-01-01 18:00", tz="America/New_York")).agg(
        {"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    ph, pl = pivots(g.h.values, g.l.values, length)
    sh = sl = np.nan
    shd = sld = False
    tr = 0
    out = []
    for i in range(len(g)):
        if not np.isnan(ph[i]):
            sh, shd = ph[i], False
        if not np.isnan(pl[i]):
            sl, sld = pl[i], False
        if not np.isnan(sh) and not shd and g.c.values[i] > sh:
            shd, tr = True, 1
        if not np.isnan(sl) and not sld and g.c.values[i] < sl:
            sld, tr = True, -1
        out.append(tr)
    s = pd.Series(out, index=g.index).shift(1).fillna(0)  # value of the previous (closed) HTF bar
    return s.reindex(d.index, method="ffill").fillna(0).astype(int).values


V1_USER = dict(name="v1 (tes réglages)", pools=("asia",), conf="reclose", confMax=6, swLen=2, disp=0.0,
               entry="mid", limitBars=20, pd=False, slBuf=0.1, minStop=1.0, pad=0.0, tgt="R", rr=2.0,
               rrMin=1.5, rrMax=4.0, be=0.0, bias="none", use="with", neutral="both", ny=True, pm=False,
               maxTrades=2, maxLoss=3, consume=False, smt=False)


def run(d, cfg, peer=None):
    c = dict(V1_USER)
    c.update(cfg)
    o, h, l, cl = d.o.values, d.h.values, d.l.values, d.c.values
    mins = (d.index.hour * 60 + d.index.minute).values
    key = (id(d), c["swLen"])
    if key not in _CACHE:
        _CACHE[key] = (atr(d), pivots(h, l, c["swLen"]), htf_trend(d, "1h"), htf_trend(d, "4h"))
    A, (pvH, pvL), h1, h4 = _CACHE[key]
    if peer is not None:
        pr = peer.reindex(d.index).ffill()
        pH, pL = pr.h.values, pr.l.values
    else:
        pH = pL = np.full(len(d), np.nan)
    inAsia = in_sess(mins, m("1900"), m("0200"))
    lonRaw = in_sess(mins, m("0200"), m("0500"))
    nyRaw = in_sess(mins, m("0830"), m("1100"))
    pmRaw = in_sess(mins, m("1330"), m("1500"))
    inFlat = in_sess(mins, m("1550"), m("1800"))
    inNY = nyRaw & c["ny"]
    inPM = pmRaw & c["pm"]
    inKZ = lonRaw | inNY | inPM

    trades = []
    day = asia = lon = nyam = None
    yH = yL = yC = ppH = ppL = np.nan
    yPH = yPL = np.nan
    dBias = h4Day = 0
    pools = []
    st = [None, None]
    lastSwH = lastSwL = np.nan
    nToday = lossToday = 0
    nDays = 0
    cur = None  # pending or open trade
    stats = dict(sweep=0, out=0, noconf=0, kzend=0, sig=0, bias=0, pd=0, busy=0, smt=0, order=0, miss=0, exp=0)

    def rng_begin(i):
        return dict(hi=h[i], lo=l[i], phi=pH[i], plo=pL[i])

    def rng_grow(r, i):
        r["hi"] = max(r["hi"], h[i]); r["lo"] = min(r["lo"], l[i])
        if not np.isnan(pH[i]):
            r["phi"] = pH[i] if np.isnan(r["phi"]) else max(r["phi"], pH[i])
            r["plo"] = pL[i] if np.isnan(r["plo"]) else min(r["plo"], pL[i])

    def close_trade(t, px, i, why):
        nonlocal lossToday
        rr = (px - t["entry"]) * t["dir"] / t["risk"]
        t.update(exit=px, rr=rr, why=why, t1=d.index[i])
        trades.append(t)
        if rr < -0.1:
            lossToday += 1

    for i in range(1, len(d)):
        # ---------- broker emulator: orders live from the previous bar ----------
        if cur is not None:
            t = cur
            if not t["filled"]:
                hitE = h[i] >= t["entry"] if t["dir"] == -1 else l[i] <= t["entry"]
                if hitE:
                    fill = max(t["entry"], o[i]) if t["dir"] == -1 else min(t["entry"], o[i])
                    t["filled"] = True
                    t["entry"] = fill
                    t["risk"] = abs(fill - t["sl"])
                    t["t0"] = d.index[i]
                    stopHit = h[i] >= t["sl"] if t["dir"] == -1 else l[i] <= t["sl"]
                    if stopHit:
                        close_trade(t, t["sl"] - t["dir"] * SLIP, i, "SL")
                        cur = None
            else:
                stp = t["entry"] if t["be"] else t["sl"]
                stopHit = h[i] >= stp if t["dir"] == -1 else l[i] <= stp
                tpHit = l[i] <= t["tp"] if t["dir"] == -1 else h[i] >= t["tp"]
                if stopHit:
                    px = (max(stp, o[i]) if t["dir"] == -1 else min(stp, o[i])) - t["dir"] * SLIP
                    close_trade(t, px, i, "BE" if t["be"] else "SL")
                    cur = None
                elif tpHit:
                    close_trade(t, t["tp"], i, "TP")
                    cur = None

        # ---------- script at bar close ----------
        if not np.isnan(pvH[i]):
            lastSwH = pvH[i]
        if not np.isnan(pvL[i]):
            lastSwL = pvL[i]

        newDay = inAsia[i] and not inAsia[i - 1]
        if newDay:
            ppH, ppL = yH, yL
            if day is not None:
                yH, yL, yPH, yPL = day["hi"], day["lo"], day["phi"], day["plo"]
            yC = cl[i - 1]
            if np.isnan(ppH) or np.isnan(yH):
                dBias = 0
            elif yC > ppH:
                dBias = 1
            elif yC < ppL:
                dBias = -1
            elif yH > ppH and yC < ppH:
                dBias = -1
            elif yL < ppL and yC > ppL:
                dBias = 1
            else:
                dBias = 0
            h4Day = h4[i]
            day = rng_begin(i)
            asia = rng_begin(i)
            lon = nyam = None
            pools = []
            st = [None, None]
            nToday = lossToday = 0
            nDays += 1
            if "pd" in c["pools"] and not np.isnan(yH):
                pools.append(dict(name="PDH", kind=1, dir=-1, lvl=yH, plvl=yPH, used=False, ptaken=False))
                pools.append(dict(name="PDL", kind=1, dir=1, lvl=yL, plvl=yPL, used=False, ptaken=False))
        elif day is not None:
            rng_grow(day, i)
            if inAsia[i]:
                rng_grow(asia, i)
        if day is None:
            continue

        b = {"none": 0, "d1": dBias, "h4": h4Day, "both": dBias if dBias == h4Day else 0, "h1": h1[i]}[c["bias"]]

        if not inAsia[i] and inAsia[i - 1] and "asia" in c["pools"]:
            pools.append(dict(name="Asie H", kind=0, dir=-1, lvl=asia["hi"], plvl=asia["phi"], used=False, ptaken=False))
            pools.append(dict(name="Asie L", kind=0, dir=1, lvl=asia["lo"], plvl=asia["plo"], used=False, ptaken=False))
        if lonRaw[i] and not lonRaw[i - 1]:
            lon = rng_begin(i)
        elif lonRaw[i] and lon is not None:
            rng_grow(lon, i)
        if not lonRaw[i] and lonRaw[i - 1] and lon is not None and "lon" in c["pools"] and (c["ny"] or c["pm"]):
            pools.append(dict(name="Londres H", kind=2, dir=-1, lvl=lon["hi"], plvl=lon["phi"], used=False, ptaken=False))
            pools.append(dict(name="Londres L", kind=2, dir=1, lvl=lon["lo"], plvl=lon["plo"], used=False, ptaken=False))
        if nyRaw[i] and not nyRaw[i - 1]:
            nyam = rng_begin(i)
        elif nyRaw[i] and nyam is not None:
            rng_grow(nyam, i)
        if not nyRaw[i] and nyRaw[i - 1] and nyam is not None and "ny" in c["pools"] and c["pm"]:
            pools.append(dict(name="NY matin H", kind=3, dir=-1, lvl=nyam["hi"], plvl=nyam["phi"], used=False, ptaken=False))
            pools.append(dict(name="NY matin L", kind=3, dir=1, lvl=nyam["lo"], plvl=nyam["plo"], used=False, ptaken=False))

        sess = 0 if lonRaw[i] else 1 if inNY[i] else 2

        # trade management at close
        if cur is not None:
            t = cur
            if not t["filled"]:
                if i > t["bar0"]:
                    missed = l[i] <= t["tp"] if t["dir"] == -1 else h[i] >= t["tp"]
                    expired = i - t["bar0"] >= c["limitBars"] or not inKZ[i] or inFlat[i]
                    if missed or expired:
                        stats["miss" if missed else "exp"] += 1
                        cur = None
            else:
                if c["be"] > 0 and not t["be"]:
                    lvl_be = t["entry"] + t["dir"] * c["be"] * t["risk"]
                    if (h[i] >= lvl_be) if t["dir"] == 1 else (l[i] <= lvl_be):
                        t["be"] = True
        if inFlat[i] and cur is not None and cur["filled"]:
            close_trade(cur, cl[i], i, "Fin")
            cur = None

        # pools
        for k, p in enumerate(pools):
            if p["used"]:
                continue
            if not np.isnan(p["plvl"]) and not p["ptaken"]:
                if (pH[i] > p["plvl"]) if p["dir"] == -1 else (pL[i] < p["plvl"]):
                    p["ptaken"] = True
            hit = h[i] > p["lvl"] if p["dir"] == -1 else l[i] < p["lvl"]
            if not hit:
                continue
            s = 0 if p["dir"] == -1 else 1
            if inKZ[i] and not inFlat[i]:
                p["used"] = True
                stats["sweep"] += 1
                if st[s] is None:
                    st[s] = dict(ext=h[i] if s == 0 else l[i], lvl=p["lvl"], bar=i, pool=k, name=p["name"],
                                 choch=lastSwL if s == 0 else lastSwH)
                else:
                    if (p["lvl"] > st[s]["lvl"]) if s == 0 else (p["lvl"] < st[s]["lvl"]):
                        st[s]["lvl"], st[s]["pool"] = p["lvl"], k
                    st[s]["name"] += " + " + p["name"]
            elif c["consume"]:
                p["used"] = True
                stats["out"] += 1

        # confirmation
        sig = None
        for s in (0, 1):
            w = st[s]
            if w is None:
                continue
            dd = -1 if s == 0 else 1
            if not inKZ[i] or inFlat[i]:
                st[s] = None
                stats["kzend"] += 1
                continue
            if i > w["bar"] and ((h[i] > w["ext"]) if dd == -1 else (l[i] < w["ext"])):
                w["ext"] = h[i] if dd == -1 else l[i]
                w["choch"] = lastSwL if dd == -1 else lastSwH
            ch = w["lvl"] if np.isnan(w["choch"]) else w["choch"]
            ref = (min(w["lvl"], ch) if dd == -1 else max(w["lvl"], ch)) if c["conf"] == "choch" else w["lvl"]
            brk = cl[i] < ref if dd == -1 else cl[i] > ref
            disp = c["disp"] <= 0 or (cl[i] - o[i]) * dd >= c["disp"] * A[i]
            if brk and disp and sig is None:
                sig = (dd, w)
                st[s] = None
            elif (i - w["bar"] > c["confMax"]) if c["conf"] == "reclose" and not c["consume"] else (i - w["bar"] >= c["confMax"]):
                st[s] = None
                stats["noconf"] += 1

        if sig is None:
            continue
        dd, w = sig
        stats["sig"] += 1
        sp = pools[w["pool"]]
        if c["smt"] and sp["ptaken"]:
            stats["smt"] += 1
            continue
        if c["bias"] != "none":
            ok = (c["neutral"] == "both") if b == 0 else (b == dd if c["use"] == "with" else b == -dd)
            if not ok:
                stats["bias"] += 1
                continue
        mid = (o[i] + cl[i]) / 2
        fvg = np.nan
        for k in range(3):
            if i - k - 2 < 0:
                break
            if dd == -1 and h[i - k] < l[i - k - 2]:
                fvg = (h[i - k] + l[i - k - 2]) / 2
                break
            if dd == 1 and l[i - k] > h[i - k - 2]:
                fvg = (l[i - k] + h[i - k - 2]) / 2
                break
        ent = cl[i] if c["entry"] == "close" else (fvg if c["entry"] == "fvg" and not np.isnan(fvg) else mid)
        eq = (day["hi"] + day["lo"]) / 2
        if c["pd"] and not ((ent > eq) if dd == -1 else (ent < eq)):
            stats["pd"] += 1
            continue
        if cur is not None or nToday >= c["maxTrades"] or lossToday >= c["maxLoss"]:
            stats["busy"] += 1
            continue
        slp = w["ext"] - dd * c["slBuf"] * A[i]
        dist = abs(ent - slp)
        if dist < c["minStop"] * A[i]:
            slp = ent - dd * c["minStop"] * A[i]
            dist = c["minStop"] * A[i]
        slp -= dd * c["pad"]
        dist += c["pad"]
        tp = ent + dd * c["rr"] * dist
        if c["tgt"] == "liq":
            best = None
            for q in pools:
                if not q["used"] and q["dir"] == -dd:
                    rq = (q["lvl"] - ent) * dd / dist
                    if rq >= c["rrMin"] and (best is None or rq < best):
                        best = rq
            if best is not None:
                tp = ent + dd * min(best, c["rrMax"]) * dist
        stats["order"] += 1
        nToday += 1
        t = dict(dir=dd, entry=ent, sl=slp, tp=tp, risk=dist, bar0=i, sess=sess, kind=sp["kind"], filled=False,
                 be=False, name=w["name"], tsig=d.index[i], bias=b)
        if c["entry"] == "close":
            t["filled"] = True
            t["entry"] = cl[i] + dd * SLIP
            t["risk"] = abs(t["entry"] - slp)
            t["t0"] = d.index[i]
        cur = t

    return trades, stats, nDays


def summary(trades, nDays):
    if not trades:
        return dict(n=0)
    r = np.array([t["rr"] for t in trades])
    eq = np.cumsum(r)
    dd = np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq) if len(r) else 0
    streak = worst = 0
    for x in r:
        streak = streak + 1 if x < -0.1 else 0 if x > 0.1 else streak
        worst = max(worst, streak)
    wins, losses = r[r > 0.1].sum(), -r[r < -0.1].sum()
    return dict(n=len(r), perDay=len(r) / nDays, win=100 * (r > 0.1).mean(), exp=r.mean(), total=r.sum(),
                pf=wins / losses if losses > 0 else np.inf, dd=dd, worst=worst)


def fmt_row(name, s):
    if s.get("n", 0) == 0:
        return f"| {name} | 0 | | | | | | |"
    return (f"| {name} | {s['n']} | {s['perDay']:.2f} | {s['win']:.0f} % | {s['exp']:+.2f}R | "
            f"{s['total']:+.1f}R | {s['pf']:.2f} | -{s['dd']:.1f}R / {s['worst']} |")


if __name__ == "__main__":
    d = load(sys.argv[1])
    tr, stt, nd = run(d, {})
    print(summary(tr, nd), stt)
