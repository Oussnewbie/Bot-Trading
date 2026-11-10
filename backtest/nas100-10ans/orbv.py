"""ORB 5-min variants with full path stats (MFE / MAE) for loss analysis."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbx
from fam import G

def path(k, d, ent, sl, last_i, p):
    """Trade filled at ent on bar k. Returns (r, exit_i, mfe, mae, bars). Conservative: stop first."""
    BO, BH, BL, BC, AO, AH, AL, AC, A = (G[x] for x in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC", "ATR"))
    S = fam.SLIP; risk = abs(ent - sl)
    if risk <= 0: return None
    tp = None if p.get("rr") is None else ent + d * p["rr"] * risk
    # fill bar: adverse first
    adv0 = ((ent - BL[k]) if d == 1 else (AH[k] - ent)) / risk
    if (d == 1 and BL[k] <= sl) or (d == -1 and AH[k] >= sl):
        return ((sl - d * S - ent) * d / risk, k, 0.0, adv0, 0)
    stop, mfe, mae = sl, 0.0, adv0
    part = 0.0; left = 1.0
    for j in range(k + 1, last_i + 1):
        hi = BH[j] if d == 1 else AH[j]; lo = BL[j] if d == 1 else AL[j]
        fav = ((hi - ent) if d == 1 else (ent - lo)) / risk
        adv = ((ent - lo) if d == 1 else (hi - ent)) / risk
        hit_stop = (lo <= stop) if d == 1 else (hi >= stop)
        if hit_stop:
            px = (min(stop, BO[j]) - S) if d == 1 else (max(stop, AO[j]) + S)
            r_rest = (px - ent) * d / risk
            return (part + left * r_rest, j, max(mfe, 0), max(mae, adv), j - k)
        mae = max(mae, adv)
        if tp is not None and fav >= p["rr"]:
            return (part + left * p["rr"], j, max(mfe, fav), mae, j - k)
        mfe = max(mfe, fav)
        if p.get("pr") and left == 1.0 and fav >= p["pr"]:
            part = p["pf"] * p["pr"]; left = 1 - p["pf"]
            if p.get("pbe"): stop = max(stop, ent) if d == 1 else min(stop, ent)
        if p.get("be") is not None and mfe >= p["be"]:
            lock = ent + d * p.get("lock", 0.0) * risk
            stop = max(stop, lock) if d == 1 else min(stop, lock)
        if p.get("ts") and j - k == p["ts"]:
            cur = ((BC[j] - ent) if d == 1 else (ent - AC[j])) / risk
            if cur < p.get("tsr", 0.0):
                return (part + left * cur, j, mfe, mae, j - k)
    px = BC[last_i] if d == 1 else AC[last_i]
    return (part + left * (px - ent) * d / risk, last_i, mfe, mae, last_i - k)

def run(F, p):
    BO, AO, AH, BL, mins, t = G["BO"], G["AO"], G["AH"], G["BL"], G["mins"], G["t"]
    lb = orbx.last_before(p.get("tex", 950))
    out = []
    for i, row in F.iterrows():
        last_i = lb[i]
        if last_i <= i: continue
        orw = row.orH - row.orL
        if p.get("minor") and row.or_atr < p["minor"]: continue
        if p.get("maxor") and row.or_atr > p["maxor"]: continue
        buf = p.get("buf", 0.0) * orw
        lv = {1: row.orH + buf, -1: row.orL - buf}
        m = p.get("sm", 1.0)
        sls = {1: lv[1] - m * (orw + 2 * buf), -1: lv[-1] + m * (orw + 2 * buf)}
        if p.get("slpts") is not None:
            sls = {1: row.orL - p["slpts"], -1: row.orH + p["slpts"]}
        sides = {1, -1}; n = 0; k = i + 1
        while k <= last_i and mins[k] < p.get("cutoff", 720) and n < p.get("maxT", 1) and sides:
            up = 1 in sides and AH[k] >= lv[1]; dn = -1 in sides and BL[k] <= lv[-1]
            if up or dn:
                cands = [d for d, h in ((1, up), (-1, dn)) if h]
                res = []
                for d in cands:
                    px = (max(lv[1], AO[k]) + fam.SLIP) if d == 1 else (min(lv[-1], BO[k]) - fam.SLIP)
                    r = path(k, d, px, sls[d], last_i, p)
                    if r: res.append((r, d))
                if not res: k += 1; continue
                (r, d) = min(res, key=lambda x: x[0][0])  # both touched in one bar: assume the worse side
                out.append(dict(t=t[k], r=r[0], d=d, mfe=r[2], mae=r[3], bars=r[4], k=k, ex=r[1], both=len(cands) == 2, or_atr=row.or_atr, orw=orw))
                n += 1
                sides.discard(d)
                if len(cands) == 2: sides.clear()
                k = r[1] + 1
                continue
            k += 1
    return pd.DataFrame(out)

SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
def line(lab, X):
    r = X.r
    tr, te = X[X.t < SPLIT].r, X[X.t >= SPLIT].r
    eq = r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    st = w = 0
    for v in r:
        st = st + 1 if v < -0.05 else 0; w = max(w, st)
    yrs = X.groupby(X.t.dt.year).r.sum()
    print(f"| {lab} | {len(X)} | {100*(r>0.05).mean():.0f} % | {r.mean():+.3f}R | {tr.mean():+.3f} / {te.mean():+.3f} | {r.sum():+.0f}R | -{dd:.0f}R / {w} | {(yrs>0).sum()}/{len(yrs)} |", flush=True)
