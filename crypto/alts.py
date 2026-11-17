"""Étape 13 : élargir l'univers à ~55 cryptos (Binance spot, journalier), y compris des mortes ou radiées (LUNA, FTT,
WAVES, EOS, XMR...) pour limiter le biais du survivant.

Univers chaque jour : les 20 cryptos au plus gros volume en dollars sur les 30 derniers jours, cotées depuis au moins
120 jours. Une cotation interrompue plus de 3 jours (radiation, migration) coupe la série : la position est perdue
au dernier prix.
Coûts : 0,15 % par côté (frais 0,10 % + glissement 0,05 %, plus large que sur BTC).

A1 Tendance sur chaque crypto : prix > MA200 ET MACD > signal ET RSI14 > 50 (version « prix seul » de la confluence),
   taille 40 % ÷ volatilité, divisée par le nombre de cryptos de l'univers.
A2 Momentum en coupe transversale (Liu-Tsyvinski-Wu) : chaque lundi, achat des k cryptos aux meilleurs rendements sur
   L jours (k = 3, 5, 10 ; L = 7, 14, 28, 56), à poids égaux dosés par la volatilité ; avec ou sans le filtre
   « BTC en tendance haussière » (confluence BTC >= 0,25).
A3 Portefeuille : le système BTC/ETH (multi-unités) + une poche A2.
Choix sur 2018-2022, vérification 2023-2026. Sortie : sorties/alts.txt
"""
import glob
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I
import moteur as M
import signaux as S
from confluence import votes_a_priori
from multi_tf import caler
from recherche import PERIODES, OUT

COUT = 0.0015


def panneau():
    def f():
        closes, vols = {}, {}
        for dossier in sorted(glob.glob(f"{DN.D}/binance/spot/monthly/klines/*USDT/1d")):
            sym = os.path.basename(os.path.dirname(dossier))
            fs = sorted(glob.glob(f"{dossier}/*.csv")) + sorted(glob.glob(f"{DN.D}/binance/spot/daily/klines/{sym}/1d/*.csv"))
            d = DN._lire_klines(fs)
            d.index = d.index.normalize()
            d = d[~d.index.duplicated()]
            # coupe à la première interruption de plus de 3 jours
            trou = d.index.to_series().diff() > pd.Timedelta("3D")
            if trou.any():
                d = d[d.index < trou[trou].index[0]]
            closes[sym[:-4]] = d.close
            vols[sym[:-4]] = d.quote_volume
        return pd.concat({"c": pd.DataFrame(closes), "v": pd.DataFrame(vols)}, axis=1).sort_index()
    x = DN._cache("panneau-alts-1d", f)
    return x["c"], x["v"]


def univers(c, v, n=20):
    age = c.notna().cumsum()
    vm = v.rolling(30, min_periods=20).mean().where(age >= 120)
    rang = vm.rank(axis=1, ascending=False)
    return (rang <= n) & c.notna()


def evaluer_poids(w, c, nom, bh):
    """w : poids décidés à la clôture du jour t, tenus le jour t+1. Rendement net, statistiques par période."""
    r = c.pct_change(fill_method=None).fillna(0)
    # une crypto qui disparaît : sa dernière variation est 0, et elle sort du portefeuille
    w = w.fillna(0)
    tenu = w.shift(1).fillna(0)
    net = (tenu * r).sum(axis=1) - (w.diff().abs().sum(axis=1).shift(1).fillna(0)) * COUT
    out = []
    for k, (a, b) in PERIODES.items():
        m = (net.index >= a) & (net.index < b)
        y = net[m]
        eq = (1 + y).cumprod()
        out.append(f"{k}: Sh {y.mean() / y.std() * np.sqrt(365):.2f} cagr {eq.iloc[-1] ** (365 / len(y)) - 1:+.0%} "
                   f"dd {(eq / eq.cummax() - 1).min():.0%} expo {tenu[m].abs().sum(axis=1).mean():.0%}")
    print(f"  {nom:<58}", "  ".join(out))
    return net


def main():
    c, v = panneau()
    c = c[c.index >= "2017-09-01"]; v = v.reindex(c.index)
    U = univers(c, v)
    r = c.pct_change(fill_method=None)
    vol = r.rolling(30, min_periods=20).std() * np.sqrt(365)
    dose = (0.4 / vol).clip(upper=1)
    print(f"{c.shape[1]} cryptos ; taille moyenne de l'univers {U.sum(axis=1)[U.sum(axis=1) > 0].mean():.0f}")
    ctx = S.contexte("BTC", "1d")
    sc_btc = votes_a_priori(ctx).mean(axis=1)
    btc_ok = (sc_btc.reindex(c.index).ffill() >= 0.25)
    bh = r["BTC"].fillna(0)

    print("\n== Références ==")
    evaluer_poids(pd.DataFrame({"BTC": 1.0}, index=c.index).reindex(columns=c.columns).fillna(0), c, "BTC acheté et gardé", bh)
    ew = U.astype(float).div(U.sum(axis=1), axis=0)
    evaluer_poids(ew, c, "les 20 plus grosses cryptos à poids égaux, gardées", bh)

    print("\n== A1 tendance sur chaque crypto (prix > MA200, MACD > signal, RSI > 50) ==")
    m, s, _ = I.macd(c)
    rsi = c.apply(lambda x: I.rsi(x.dropna(), 14).reindex(x.index))
    tend = (c > c.rolling(200, min_periods=200).mean()) & (m > s) & (rsi > 50)
    for filtre in (False, True):
        sig = tend & U & (btc_ok.values[:, None] if filtre else True)
        w = (sig * dose).div(U.sum(axis=1).clip(lower=1), axis=0) * 4      # 4 × part égale, plafonné à 1 au total
        w = w.div(w.sum(axis=1).clip(lower=1), axis=0)
        evaluer_poids(w, c, "A1 tendance" + (" + BTC haussier" if filtre else ""), bh)

    print("\n== A2 momentum en coupe transversale (rebalancement le lundi) ==")
    lundi = c.index.dayofweek == 0
    for L in (7, 14, 28, 56):
        perf = c / c.shift(L) - 1
        for k in (3, 5, 10):
            for filtre in (False, True):
                rg = perf.where(U).rank(axis=1, ascending=False)
                choix = (rg <= k)
                w = (choix * dose).div(k)
                w = w.where(pd.Series(lundi, index=c.index), np.nan).ffill().fillna(0)
                w = w.where(U, 0)
                if filtre:
                    w = w.mul(btc_ok.astype(float), axis=0)
                evaluer_poids(w, c, f"A2 L={L} j, top {k}" + (" + BTC haussier" if filtre else ""), bh)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "alts.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
