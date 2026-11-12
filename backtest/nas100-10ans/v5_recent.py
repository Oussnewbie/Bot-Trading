"""Rejoue la v5 sur les dernières semaines, jour par jour, avec la raison de chaque trade.
Données : contrat à terme Nasdaq (NQ) en M5 chez Yahoo Finance (60 jours au plus), un seul prix : l'ask est
simulé avec un spread fixe. Les prix diffèrent un peu d'un CFD, les ranges presque pas.
    pip install yfinance ; python v5_recent.py [spread en points, 1.2 par défaut]"""
import sys
import numpy as np, pandas as pd
import v5_lab as L, orb_v5

def yahoo(spread):
    import yfinance as yf
    d = yf.download("NQ=F", period="60d", interval="5m", prepost=True, progress=False, auto_adjust=False)
    d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
    d = d.tz_convert("America/New_York")[["Open", "High", "Low", "Close", "Volume"]].dropna()
    d.columns = ["o", "h", "l", "c", "v"]
    a = d.copy(); a[["o", "h", "l", "c"]] += spread
    return d, a

def journal(X, D, G):
    X = X.copy(); X["day"] = X.t.dt.tz_localize(None).dt.normalize()
    for r in D.itertuples():
        okL = r.rsi > 50 and r.orH >= r.preH; okS = r.rsi < 50 and r.orL <= r.preL
        whyL = "" if okL else ("RSI" if r.rsi <= 50 else "élan")
        whyS = "" if okS else ("RSI" if r.rsi >= 50 else "élan")
        x = X[X.day == r.day]
        if len(x):
            x = x.iloc[0]
            res = f"{'ACHAT' if x.d == 1 else 'VENTE'} à {x.t.strftime('%H:%M')} → {x.r:+.2f}R ({x.why}, meilleur moment {x.mfe:+.1f}R, sortie {G['t'][x.ex].strftime('%H:%M')})"
        else:
            res = "pas de trade" + ("" if (okL or okS) else " (les deux côtés bloqués)")
        print(f"{r.day.date()} | range {r.orL:.1f}–{r.orH:.1f} ({r.orw:.0f} pts) | 9:00-9:30 {r.preL:.1f}–{r.preH:.1f} | RSI {r.rsi:.0f} | "
              f"achat {'oui' if okL else 'non (' + whyL + ')'} · vente {'oui' if okS else 'non (' + whyS + ')'} | {res}")

if __name__ == "__main__":
    spread = float(sys.argv[1]) if len(sys.argv) > 1 else 1.2
    D = L.prep(yahoo(spread))
    X = L.run(orb_v5.V5, L.f_v4)
    journal(X, D, L.G)
    s = L.stats(X)
    print(f"\n{s['n']} trades · {100 * s['win']:.0f} % gagnants · {s['tot']:+.1f}R · par trade {s['mean']:+.2f}R · pire baisse -{s['dd']:.1f}R · {s['streak']} pertes de suite")
