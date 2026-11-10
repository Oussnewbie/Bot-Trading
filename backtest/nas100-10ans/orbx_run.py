import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd, time
import fam, orbx
fam.prep()
t0 = time.time(); F = orbx.features(); print("features", F.shape, f"{time.time()-t0:.0f}s", flush=True)
F.to_pickle("orb_features.pkl")
def line(lab, out):
    s = fam.stats(out)
    print(f"| {lab} | {s['n']} | {s['win']:.0f} % | {s['exp']:+.3f}R | {s['etr']:+.3f} / {s['ete']:+.3f} | {s['total']:+.0f}R | -{s['dd']:.0f}R | {s['pf']:.2f} | {s['ypos']}/{s['ny']} |", flush=True)
    return s
print("| Variante | Trades | Gagnants | Par trade | 2018-22 / 2022-26 | Total | Pire baisse | PF | Années + |")
print("|---|---|---|---|---|---|---|---|---|")
line("**ORB de base** (sortie 15:50)", orbx.orb(F))
def with_(col):  return lambda r: ({1} if r[col] > 0 else {-1} if r[col] < 0 else set()) if np.isfinite(r[col]) else set()
def against(col): return lambda r: ({-1} if r[col] > 0 else {1} if r[col] < 0 else set()) if np.isfinite(r[col]) else set()
print("| *Filtres de tendance (dans le sens / contre)* |||||||||")
for lab, col in [("MA200 journalière", "d_sma200"), ("MA50 journalière", "d_sma50"), ("EMA200 H1", "h_ema200"), ("EMA50 H1", "h_ema50"),
                 ("EMA200 M5", "m5_ema200"), ("RSI14 H1 > ou < 50", "h_rsi"), ("RSI14 M5 > ou < 50", "m5_rsi"), ("MACD H1 (histogramme)", "h_macd"),
                 ("Ichimoku H1 : au-dessus / sous le nuage", "ichi"), ("Ichimoku H1 : Tenkan / Kijun", "h_tk"), ("Bollinger H1 : au-dessus / sous la moyenne", "h_pb"),
                 ("Gap d'ouverture", "gap"), ("Midnight open (ICT)", "mid_open"), ("Bougie de la veille", "prevdir")]:
    line(lab + " — dans le sens", orbx.orb(F, with_(col)))
    line(lab + " — contre", orbx.orb(F, against(col)))
print("| *Filtres de journée* |||||||||")
med = F[F.day < pd.Timestamp("2022-09-01")].or_atr.median()
line(f"Range d'ouverture petit (< médiane {med:.2f} ATR jour)", orbx.orb(F, lambda r: {1, -1} if r.or_atr < med else set()))
line("Range d'ouverture grand (> médiane)", orbx.orb(F, lambda r: {1, -1} if r.or_atr >= med else set()))
line("Volatilité H1 basse (Bollinger étroit, < 50 %)", orbx.orb(F, lambda r: {1, -1} if r.bbw_rank < 0.5 else set()))
line("Volatilité H1 haute (Bollinger large, > 50 %)", orbx.orb(F, lambda r: {1, -1} if r.bbw_rank >= 0.5 else set()))
for wd, nm in enumerate(["lundi", "mardi", "mercredi", "jeudi", "vendredi"]):
    line(f"Sans le {nm}", orbx.orb(F, lambda r, wd=wd: set() if r.day.dayofweek == wd else {1, -1}))
print("| *Sorties* |||||||||")
for lab, kw in [("Objectif 2R", dict(rr=2.0)), ("Objectif 3R", dict(rr=3.0)), ("Objectif 5R", dict(rr=5.0)), ("Objectif 8R", dict(rr=8.0)),
                ("Objectif = high / low de la veille", dict(tgt="pd")),
                ("Stop à l'entrée dès +1R", dict(be=1.0)), ("Stop à l'entrée dès +2R", dict(be=2.0)),
                ("Stop suiveur 2 ATR M5 après +1R", dict(trail=2.0)), ("Stop suiveur 4 ATR M5 après +1R", dict(trail=4.0)), ("Stop suiveur 8 ATR M5 après +1R", dict(trail=8.0)),
                ("Sortie à 11:00", dict(tex=660)), ("Sortie à 12:00", dict(tex=720)), ("Sortie à 14:00", dict(tex=840))]:
    line(lab, orbx.orb(F, **kw))
