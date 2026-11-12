"""Autopsie des stops ORB v3 : une ligne par trade, tout ce qui est connu avant ou à l'entrée."""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam
from fam import pivots
fam.prep(); G = fam.G
t, mins, cal = G["t"], G["mins"], G["cal"]
BO, BH, BL, BC, AO, AH, AL, AC = (G[k] for k in ("BO","BH","BL","BC","AO","AH","AL","AC"))
X = pd.read_pickle("prevday_trades.pkl")
F = pd.read_pickle("orb_features.pkl").reset_index()
X = X.merge(F[["day", "i", "orH", "orL", "c", "h_ema50", "h_rsi", "h_tk", "ichi", "d_sma200", "d_sma50", "bbw_rank", "mid_open", "m5_ema200"]], on="day", how="left")
tn = t.as_unit("ns").asi8
df = pd.DataFrame({"o": BO, "h": BH, "l": BL, "c": BC}, index=t)

# --- structure de marché par unité de temps (pivots confirmés, sans regard vers le futur) ---
def structure(rule, n=2, origin="start_day"):
    R = df.resample(rule, label="left", closed="left", origin=origin).agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
    ph, pl = pivots(R.h.values, R.l.values, n)
    sh = pd.Series(ph); sl = pd.Series(pl)
    sh1 = sh.ffill(); sl1 = sl.ffill()
    # précédent pivot (avant le dernier)
    shp = sh.where(sh.notna()).shift(1); shp = pd.Series(np.where(sh.notna(), sh.ffill().shift(1).values, np.nan)).ffill()
    # plus simple : liste des pivots puis valeurs avant-dernières
    def prev_last(s):
        v = s.dropna(); prev = v.shift(1)
        return pd.Series(prev, index=v.index).reindex(range(len(s))).ffill().values
    shp = prev_last(sh); slp = prev_last(sl)
    st = np.where((sh1 > shp) & (sl1 > slp), 1, np.where((sh1 < shp) & (sl1 < slp), -1, 0))
    end = (R.index + pd.Timedelta(rule)).as_unit("ns").asi8
    return pd.DataFrame({"end": end, "st": st, "sh": sh1.values, "sl": sl1.values, "c": R.c.values})
TF = {"M15": structure("15min"), "H1": structure("1h"), "H4": structure("4h")}
# D1 = séances 9:30-16:00
rth = df[(mins >= 570) & (mins < 960)]
D = rth.groupby(rth.index.tz_localize(None).normalize()).agg(o=("o","first"), h=("h","max"), l=("l","min"), c=("c","last"))
ph, pl = pivots(D.h.values, D.l.values, 2)
Ds = pd.DataFrame({"sh": pd.Series(ph).ffill().values, "sl": pd.Series(pl).ffill().values}, index=D.index)
def prev_last(a):
    s = pd.Series(a); v = s.dropna(); return pd.Series(v.shift(1)).reindex(range(len(s))).ffill().values
Ds["shp"] = prev_last(ph); Ds["slp"] = prev_last(pl)
Ds["st"] = np.where((Ds.sh > Ds.shp) & (Ds.sl > Ds.slp), 1, np.where((Ds.sh < Ds.shp) & (Ds.sl < Ds.slp), -1, 0))
Ds = Ds.shift(1)  # état connu avant la séance
W = D.copy(); W["wk"] = W.index.to_period("W")
WK = W.groupby("wk").agg(h=("h","max"), l=("l","min")); WKp = WK.shift(1)

rows = []
for _, x in X.iterrows():
    i, k, d = int(x.i), int(x.k), int(x.d)
    t0 = tn[i]
    orH, orL = x.orH, x.orL; orw = orH - orL; atr = x.atrd
    ent = (max(orH, AO[k]) + fam.SLIP) if d == 1 else (min(orL, BO[k]) - fam.SLIP)
    risk = abs(ent - (orL if d == 1 else orH))
    lvl = orH if d == 1 else orL
    # nuit : 18:00 veille -> 9:30 ; pré-ouverture 8:00 -> 9:30 ; 9:00 -> 9:30
    a = np.searchsorted(tn, t0 - int(15.5*3600e9)); a8 = np.searchsorted(tn, t0 - int(1.5*3600e9)); a9 = np.searchsorted(tn, t0 - int(0.5*3600e9))
    if i - a8 < 6 or i - a < 60: continue  # trou de données avant l'ouverture
    onH, onL = BH[a:i].max(), BL[a:i].min()
    pmH, pmL = BH[a8:i].max(), BL[a8:i].min()
    b830 = np.flatnonzero((cal[a8:i] == cal[i]) & (mins[a8:i] == 510))
    r830 = (BH[a8 + b830[0]] - BL[a8 + b830[0]]) / atr if len(b830) else np.nan
    pm_move = (BC[i-1] - BO[a8]) / atr
    on_move = (BC[i-1] - BO[a]) / atr
    pc = x.pc; pdh, pdl = x.pdh, x.pdl
    # niveaux dans le sens du trade : distance en R depuis l'entrée vers le prochain niveau
    cands = {"ON": onH if d == 1 else onL, "PD": pdh if d == 1 else pdl, "PM": pmH if d == 1 else pmL, "PC": pc}
    wk = pd.Timestamp(x.day).to_period("W")
    if wk in WKp.index and np.isfinite(WKp.loc[wk].h): cands["PW"] = WKp.loc[wk].h if d == 1 else WKp.loc[wk].l
    row = dict(idx=_, r=x.r, d=d, t=x.t, day=x.day, k=k, ex=x.ex, stop=x.r <= -0.9, risk_pts=risk, orw=orw, or_atr=orw/atr,
               spread_R=(AC[i] - BC[i]) / risk)
    room = []
    for nm, v in cands.items():
        dist = (v - ent) * d / risk  # >0 : niveau encore devant
        row[f"room_{nm}"] = dist
        if dist > 0: room.append(dist)
    row["room_min"] = min(room) if room else 99.0
    # la cassure a-t-elle déjà dépassé le niveau de la nuit / de la veille (prise de liquidité) ?
    row["or_swept_ON"] = int((orH > onH) if d == 1 else (orL < onL))
    row["or_swept_ONopp"] = int((orL < onL) if d == 1 else (orH > onH))
    row["inside_PD"] = int(pdl < x.c < pdh)
    row["c_vs_PD"] = (x.c - pdl) / (pdh - pdl)  # 0 = PDL, 1 = PDH
    row["c_vs_ON"] = (x.c - onL) / (onH - onL)
    row["on_rng_atr"] = (onH - onL) / atr
    row["pm_rng_atr"] = (pmH - pmL) / atr
    row["r830_atr"] = r830
    row["pm_move_dir"] = pm_move * d
    row["on_move_dir"] = on_move * d
    row["gap_dir"] = x.gap / atr * d
    row["gap_abs"] = abs(x.gap) / atr
    # bougie de 9:30
    rngb = BH[i] - BL[i]
    row["or_cloc_dir"] = ((BC[i] - BL[i]) / rngb if d == 1 else (BH[i] - BC[i]) / rngb) if rngb > 0 else 0.5
    row["or_body"] = abs(BC[i] - BO[i]) / rngb if rngb > 0 else 0
    row["or_dir"] = np.sign(BC[i] - BO[i]) * d
    row["or_vs_prevbar"] = min(rngb / max(BH[i-1] - BL[i-1], 1e-9), 20)
    # bougie d'exécution : connue à sa clôture
    row["fill_close_inside"] = int((BC[k] < orH) if d == 1 else (BC[k] > orL))
    row["fill_close_R"] = ((BC[k] - ent) if d == 1 else (ent - AC[k])) / risk
    row["fill_bar"] = mins[k]
    row["both"] = int(x.both)
    # structure par unité de temps (dernière bougie close avant 9:30)
    for nm, T in TF.items():
        j = np.searchsorted(T.end.values, t0, side="right") - 1
        row[f"st_{nm}"] = T.st.values[j] * d
        row[f"room_sw_{nm}"] = ((T.sh.values[j] if d == 1 else T.sl.values[j]) - ent) * d / risk
        row[f"stop_vs_sw_{nm}"] = ((T.sl.values[j] if d == 1 else T.sh.values[j]) - (orL if d == 1 else orH)) * d / risk  # >0 : pivot opposé entre stop et entrée
    if x.day in Ds.index:
        ds = Ds.loc[x.day]
        row["st_D1"] = ds.st * d
        row["room_sw_D1"] = ((ds.sh if d == 1 else ds.sl) - ent) * d / risk
    row["align_n"] = sum(row.get(f"st_{n}", 0) == 1 for n in ("M15", "H1", "H4", "D1"))
    row["contra_n"] = sum(row.get(f"st_{n}", 0) == -1 for n in ("M15", "H1", "H4", "D1"))
    # tendance / indicateurs déjà existants, orientés dans le sens du trade
    for c in ("h_ema50", "h_rsi", "h_tk", "d_sma200", "d_sma50", "mid_open", "m5_ema200", "m5_rsi"):
        row[c + "_dir"] = np.sign(x[c]) * d if np.isfinite(x[c]) else 0
    row["prev_body_dir"] = x.body * d
    row["prev_cloc_dir"] = x.cloc if d == 1 else 1 - x.cloc
    row["bbw_rank"] = x.bbw_rank
    dt = pd.Timestamp(x.day)
    row["dow"] = dt.dayofweek
    row["first_fri"] = int(dt.dayofweek == 4 and dt.day <= 7)
    row["opex"] = int(dt.dayofweek == 4 and 15 <= dt.day <= 21)
    row["month_edge"] = int(dt.day <= 3 or dt.day >= 28)
    row["atr_rank"] = np.nan
    rows.append(row)
T = pd.DataFrame(rows)
# volatilité relative : ATR du jour vs ses 250 derniers jours
A = X.drop_duplicates("day").set_index("day").atrd
T["atr_rank"] = T.day.map(A.rolling(250, min_periods=60).rank(pct=True))
# ex post (diagnostic, pas un filtre) : bougie de 10:00 anormale = news de 10:00
r10 = {}
for dday in T.day.unique():
    pass
T.to_pickle("sl_table.pkl")
print(T.shape); print(T.describe().T[["mean", "50%"]].round(2).to_string())
