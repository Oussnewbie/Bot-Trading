"""Étape 14 : le portefeuille d'ensemble. Trois poches qui gagnent de façon différente :
 P1 système multi-unités BTC + ETH (50/50, vente à 0,25)                         — RAPPORT-3
 P2 tendance sur chacune des 20 plus grosses cryptos, si le BTC est haussier     — alts.py A1
 P3 momentum entre cryptos, top 5 sur 7 jours, si le BTC est haussier            — alts.py A2 (meilleur Sharpe 2018-2022)
Combinaisons à poids fixes, rebalancées chaque jour (le coût du rebalancement entre poches est négligé : il ne touche
que l'écart de quelques % entre poches). Sortie : sorties/portefeuille.txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import indicateurs as I
import moteur as M
import signaux as S
from alts import panneau, univers, COUT
from confluence import votes_a_priori
from dosage_vente import preparer, vente
from recherche import PERIODES, OUT


def poche_systeme():
    nj = {}
    for a in ("BTC", "ETH"):
        p = preparer(a)
        achat = S.etat(p["score"] >= 0.25) * p["t_h"].astype(float) * p["dose"][0.4]
        net, _ = M.rendements((achat + vente(p, taille=0.25)).fillna(0), p["c"], "perp", p["fb"])
        nj[a] = M.journalier(net)
    return (nj["BTC"] + nj["ETH"].reindex(nj["BTC"].index).fillna(0)) / 2


def poches_alts():
    c, v = panneau()
    c = c[c.index >= "2017-09-01"]; v = v.reindex(c.index)
    U = univers(c, v)
    r = c.pct_change(fill_method=None)
    dose = (0.4 / (r.rolling(30, min_periods=20).std() * np.sqrt(365))).clip(upper=1)
    sc = votes_a_priori(S.contexte("BTC", "1d")).mean(axis=1)
    btc_ok = (sc.reindex(c.index).ffill() >= 0.25).astype(float)

    def net(w):
        w = w.fillna(0)
        t = w.shift(1).fillna(0)
        return (t * r.fillna(0)).sum(axis=1) - w.diff().abs().sum(axis=1).shift(1).fillna(0) * COUT
    m, s, _ = I.macd(c)
    rsi = c.apply(lambda x: I.rsi(x.dropna(), 14).reindex(x.index))
    tend = (c > c.rolling(200, min_periods=200).mean()) & (m > s) & (rsi > 50) & U
    w1 = (tend * dose).div(U.sum(axis=1).clip(lower=1), axis=0) * 4
    w1 = w1.div(w1.sum(axis=1).clip(lower=1), axis=0).mul(btc_ok, axis=0)
    perf = c / c.shift(7) - 1
    choix = perf.where(U).rank(axis=1, ascending=False) <= 5
    w2 = (choix * dose) / 5
    w2 = w2.where(pd.Series(c.index.dayofweek == 0, index=c.index), np.nan).ffill().fillna(0).where(U, 0).mul(btc_ok, axis=0)
    return net(w1), net(w2), r["BTC"].fillna(0)


def stats(y):
    eq = (1 + y).cumprod()
    return f"Sh {y.mean() / y.std() * np.sqrt(365):.2f} cagr {eq.iloc[-1] ** (365 / len(y)) - 1:+.0%} dd {(eq / eq.cummax() - 1).min():.0%}"


def main():
    p1 = poche_systeme()
    p2, p3, btc = poches_alts()
    df = pd.concat({"P1": p1, "P2": p2, "P3": p3, "BTC": btc}, axis=1).dropna()
    df = df[df.index >= PERIODES["R"][0]]
    print("Corrélation des rendements journaliers (2018-2026) :")
    print(df.corr().round(2).to_string())
    combos = {"BTC acheté et gardé": {"BTC": 1}, "P1 seul (système BTC+ETH)": {"P1": 1}, "P2 seul": {"P2": 1}, "P3 seul": {"P3": 1},
              "P1 50 % + P2 50 %": {"P1": .5, "P2": .5}, "P1 50 % + P3 50 %": {"P1": .5, "P3": .5},
              "P1 + P2 + P3 (un tiers chacun)": {"P1": 1 / 3, "P2": 1 / 3, "P3": 1 / 3},
              "P1 50 % + P2 25 % + P3 25 %": {"P1": .5, "P2": .25, "P3": .25}}
    print()
    for nom, w in combos.items():
        y = sum(df[k] * v for k, v in w.items())
        print(f"  {nom:<34}", "  ".join(f"{k}: {stats(y[(y.index >= a) & (y.index < b)])}" for k, (a, b) in PERIODES.items()))


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "portefeuille.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
