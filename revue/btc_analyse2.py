import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bitcoin"))
import pandas as pd, numpy as np
import btc_backtest as BT
import btc, donnees as DN
B = BT.charger(); E = btc.elements(B); idx = E["c4"].index
A, Z = "2018-01-01", "2026-11-14"
def sh(p, **kw):
    return BT.mesures(BT.simuler(p, B, debut=A, fin=Z, **kw)["eq"])
# 1. grille de réglages du code (REGLAGES, 135 combinaisons)
rows = []
for g in btc.REGLAGES:
    m = sh(btc.position(E, **g)); rows.append(dict(g, **m))
G = pd.DataFrame(rows)
fin = G[(G.seuil == .25) & (G.confirmation == "ema50/200") & (G.vente == .25) & (G.vol_cible == .4)].iloc[0]
print(f"Grille REGLAGES 2018-2026 (135) : Sharpe médian {G.sharpe.median():.2f}, 10e-90e centile {G.sharpe.quantile(.1):.2f}-{G.sharpe.quantile(.9):.2f}, max {G.sharpe.max():.2f}")
print(f"Réglage final : Sharpe {fin.sharpe:.2f}, rang {int((G.sharpe > fin.sharpe).sum()) + 1}/135")
print(G.groupby("confirmation").sharpe.median().round(2).to_dict(), G.groupby("seuil").sharpe.median().round(2).to_dict(), G.groupby("vente").sharpe.median().round(2).to_dict())
# 2. retrait d'un vote
V = E["votes"]
print("\nRetrait d'un vote (Sharpe 2018-2026, réglage final) :")
for k in V.columns:
    E2 = dict(E); sc = V.drop(columns=k).mean(axis=1, skipna=True); E2["score4"] = btc.caler(sc, E["c4"].index)
    m = sh(btc.position(E2, **btc.FINAL)); print(f"  sans {k:10s}: Sharpe {m['sharpe']:.2f}  CAGR {m['cagr']:+.0%}  dd {m['mdd']:.0%}")
for kk in [["ma200"], ["ma200", "ichimoku", "macd", "rsi"]]:
    E2 = dict(E); E2["score4"] = btc.caler(V[kk].mean(axis=1), E["c4"].index)
    m = sh(btc.position(E2, **btc.FINAL)); print(f"  votes {kk} seulement: Sharpe {m['sharpe']:.2f} CAGR {m['cagr']:+.0%} dd {m['mdd']:.0%}")
# 3. décisions sur prix Binance (comme le bot réel) contre Bitstamp
h = DN.bougies("BTCUSDT", "spot", "1h")
agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "taker_buy_base": "sum"}
d1 = h.resample("24h", origin="epoch").agg(agg).dropna(subset=["close"]); d4 = h.resample("4h", origin="epoch").agg(agg).dropna(subset=["close"])
d1 = d1[d1.index + pd.Timedelta("1D") <= BT.FIN_DONNEES]
Bb = dict(B); Bb.update(d1=d1[["open", "high", "low", "close", "volume"]], d4=d4[["open", "high", "low", "close", "volume"]])
Eb = btc.elements(Bb); pb = btc.position(Eb, **btc.FINAL); pa = btc.position(E, **btc.FINAL)
com = pa.index.intersection(pb.index); com = com[com >= pd.Timestamp("2018-06-01", tz="UTC")]
sa, sb = np.sign(pa[com].round(6)), np.sign(pb[com].round(6))
print(f"\nBinance vs Bitstamp (bougies 4h depuis 2018-06) : même sens {(sa == sb).mean():.1%}, écart moyen d'exposition {(pa[com] - pb[com]).abs().mean():.3f}")
for nom, p, BB in [("décisions Bitstamp, prix Bitstamp", pa, B), ("décisions Binance, prix Binance", pb, Bb)]:
    m = BT.mesures(BT.simuler(p, BB, debut="2018-06-01", fin=Z)["eq"]); print(f"  {nom}: CAGR {m['cagr']:+.0%} Sharpe {m['sharpe']:.2f} dd {m['mdd']:.0%}")
# 4. date de départ : rendement sur 12 mois à partir de chaque mois, bot vs MA200 dosée
r_bot = BT.simuler(pa, B, debut=A, fin=Z)["eq"].resample("1D").last()
r_ma = BT.simuler(BT.ma200_vol(B, E, idx), B, debut=A, fin=Z, coupe=0)["eq"].resample("1D").last()
r_bh = BT.simuler(BT.achat_garde(idx), B, debut=A, fin=Z, coupe=0)["eq"].resample("1D").last()
f12 = lambda s: (s.shift(-365) / s - 1).dropna()
a, b, c = f12(r_bot), f12(r_ma), f12(r_bh)
print(f"\n12 mois à partir de chaque jour (2018-2025) : bot < 0 dans {(a < 0).mean():.0%} des départs (pire {a.min():+.0%}, médiane {a.median():+.0%}) ; MA200 dosée < 0 : {(b < 0).mean():.0%} ; achat-garde < 0 : {(c < 0).mean():.0%} ; bot > MA200 dosée : {(a > b.reindex(a.index)).mean():.0%}")
print("Par année civile (bot / MA200 dosée / achat-garde) :")
for y in range(2018, 2027):
    s = lambda e: e[str(y)].iloc[-1] / e[str(y)].iloc[0] - 1
    print(f"  {y}: {s(r_bot):+.0%} / {s(r_ma):+.0%} / {s(r_bh):+.0%}")
# 5. rééchantillonnage par blocs (60 jours) de la différence de Sharpe bot - MA200 dosée, et bot - EMA 4h seule
ema = (E["conf"]["ema50/200"][0].astype(float) * (0.4 / E["vol4"]).clip(upper=1)).fillna(0)
r_ema = BT.simuler(ema, B, debut=A, fin=Z, coupe=0)["eq"].resample("1D").last()
R = pd.concat([r_bot.pct_change(), r_ma.pct_change(), r_ema.pct_change(), r_bh.pct_change()], axis=1).dropna().values
rng = np.random.default_rng(7); n = len(R); L = 60; nb = n // L
shp = lambda x: x.mean(0) / x.std(0) * np.sqrt(365)
D = []
for _ in range(3000):
    st = rng.integers(0, n - L, nb); x = np.concatenate([R[s:s + L] for s in st]); D.append(shp(x))
D = np.array(D)
print(f"\nBlocs de 60 jours, Sharpe bot : IC95 [{np.quantile(D[:,0],.025):.2f} ; {np.quantile(D[:,0],.975):.2f}]")
for j, nom in [(1, "MA200 dosée"), (2, "EMA50/200 4h dosée"), (3, "achat-garde")]:
    d = D[:, 0] - D[:, j]; print(f"  bot − {nom} : Sharpe +{np.median(d):.2f}, IC95 [{np.quantile(d,.025):+.2f} ; {np.quantile(d,.975):+.2f}], P(≤0) = {(d <= 0).mean():.1%}")
pickle.dump(G, open("donnees/revue/btc_grille.pkl", "wb"))
