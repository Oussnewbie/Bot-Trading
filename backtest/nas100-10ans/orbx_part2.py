import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import fam, orbx
fam.prep()
F = pd.read_pickle("orb_features.pkl")
split = pd.Timestamp("2022-09-01", tz="America/New_York")
def table(rr):
    base = orbx.orb(F, rr=rr)
    T = pd.DataFrame(base, columns=["t", "r", "d"])
    T["day"] = T.t.dt.tz_localize(None).dt.normalize()
    return T.merge(F.reset_index(), on="day", how="left")
T = table(5.0)
whip = T.d == 0
print(f"jours où les deux niveaux sont touchés dans la même bougie : {whip.sum()} ({100*whip.mean():.1f} %), comptés -1R dans chaque groupe")
def show(lab, m, X=None):
    X = T if X is None else X
    x = X[m | (X.d == 0)]
    tr, te = x[x.t < split].r, x[x.t >= split].r
    yrs = x.groupby(x.t.dt.year).r.sum()
    eq = x.r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    st = w = 0
    for v in x.r:
        st = st + 1 if v < 0 else 0; w = max(w, st)
    print(f"| {lab} | {len(x)} | {100*(x.r>0).mean():.0f} % | {x.r.mean():+.3f}R | {tr.mean():+.3f} / {te.mean():+.3f} | {x.r.sum():+.0f}R | -{dd:.0f}R / {w} | {(yrs>0).sum()}/{len(yrs)} |")
    return x
print("| Première cassure gardée si… (objectif 5R) | Trades | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |")
print("|---|---|---|---|---|---|---|---|")
show("**toutes (base)**", T.d != 0)
cols = [("MA200 journalière", "d_sma200"), ("MA50 journalière", "d_sma50"), ("EMA200 H1", "h_ema200"), ("EMA50 H1", "h_ema50"),
        ("EMA200 M5", "m5_ema200"), ("RSI14 H1 (50)", "h_rsi"), ("RSI14 M5 (50)", "m5_rsi"), ("MACD H1", "h_macd"),
        ("Ichimoku H1 nuage", "ichi"), ("Ichimoku H1 Tenkan/Kijun", "h_tk"), ("Bollinger H1 moyenne", "h_pb"),
        ("Gap d'ouverture", "gap"), ("Midnight open (ICT)", "mid_open"), ("Bougie de la veille", "prevdir")]
for lab, col in cols:
    s = np.sign(T[col])
    show(lab + " — dans le sens", (s == T.d) & (T.d != 0))
pos = (T.c - T.pdl) / (T.pdh - T.pdl)
show("Fibo veille : achat au-dessus de 50 %, vente en dessous", ((T.d == 1) & (pos >= 0.5)) | ((T.d == -1) & (pos <= 0.5)))
show("Ouverture hors du range de la veille", ((pos > 1) | (pos < 0)) & (T.d != 0))
show("RSI M5 en excès dans le sens (> 70 achat, < 30 vente)", ((T.d == 1) & (T.m5_rsi >= 20)) | ((T.d == -1) & (T.m5_rsi <= -20)))
print("| *Score : nombre d'indicateurs d'accord parmi EMA50 H1, RSI H1, Ichimoku TK, gap, midnight open, RSI M5, EMA200 M5* ||||||||")
sc = sum((np.sign(T[c]) == T.d).astype(int) for c in ["h_ema50", "h_rsi", "h_tk", "gap", "mid_open", "m5_rsi", "m5_ema200"])
T["score"] = sc
for k in range(3, 8):
    show(f"score ≥ {k} sur 7", (T.score >= k) & (T.d != 0))
print("| *Avec objectif 8R et sortie 15:50* ||||||||")
T8 = table(8.0); T8["score"] = sum((np.sign(T8[c]) == T8.d).astype(int) for c in ["h_ema50", "h_rsi", "h_tk", "gap", "mid_open", "m5_rsi", "m5_ema200"])
for k in (4, 5, 6):
    show(f"score ≥ {k}, objectif 8R", (T8.score >= k) & (T8.d != 0), T8)
TE = table(None); TE["score"] = sum((np.sign(TE[c]) == TE.d).astype(int) for c in ["h_ema50", "h_rsi", "h_tk", "gap", "mid_open", "m5_rsi", "m5_ema200"])
for k in (4, 5, 6):
    show(f"score ≥ {k}, sans objectif (15:50)", (TE.score >= k) & (TE.d != 0), TE)
T.to_pickle("orb_trades5R.pkl")
