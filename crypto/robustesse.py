"""Étape 3 : la confluence « a priori » (9 votes, seuil 0,25, dosage à 40 % de volatilité) sous tous les angles.

1. Retirer un outil à la fois (lequel compte ?) et version « prix seul » (sans order flow, on-chain ni ETH/BTC :
   ce qu'on peut coder dans TradingView ou MetaTrader sans données externes).
2. Seuils voisins, dosage voisin, 1d contre 4h.
3. Exécution retardée d'une bougie (si le signal de minuit UTC est exécuté le lendemain).
4. Année par année, BTC et ETH.
5. Coûts d'un CFD MetaTrader : spread réel Dukascopy à 00:00 UTC + swap d'achat de 20 % par an (hypothèse à vérifier).
Sortie : sorties/robustesse.txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import donnees as DN
import moteur as M
import signaux as S
from confluence import votes_a_priori, dosage_vol
from recherche import PERIODES, OUT

SEUIL, VOL = 0.25, 0.4
PRIX_SEUL = ["ma200", "ichimoku", "macd", "rsi", "vwap", "fibonacci"]


def position(votes, ctx, seuil=SEUIL, vol=VOL, cols=None):
    v = votes if cols is None else votes[cols]
    sc = v.mean(axis=1)
    p = S.etat(sc >= seuil, sc <= -seuil)
    return p * dosage_vol(ctx, vol) if vol else p


def ligne(banc, p, mode="spot"):
    r = banc.evaluer(p.values, mode)
    return {f"{k}_{m}": round(float(v), 2) for k, x in r.items() if x for m, v in x.items()
            if m in ("sharpe", "cagr", "mdd", "t_alpha", "expo", "trades")}


def cfd(ctx, p, code, swap_an=0.20):
    """Rendement journalier d'un CFD : achat à l'ask, vente au bid (spread Dukascopy de l'heure de la décision),
    swap payé sur la position tenue."""
    dk = DN.dukascopy(code)
    sp = ((dk.ask.close - dk.bid.close) / dk.bid.close)
    idx = ctx["d"].index
    demi = sp.reindex(idx + pd.Timedelta(hours=S.TF_H[ctx["tf"]] - 1)).values / 2      # dernière heure de la bougie
    demi = pd.Series(demi, index=idx).ffill().fillna(0.002)
    c = ctx["d"].close
    tenue = p.shift(1).fillna(0).clip(lower=0)
    chg = (p.clip(lower=0) - p.clip(lower=0).shift(1).fillna(0)).abs().shift(1).fillna(0)
    net = tenue * c.pct_change().fillna(0) - chg * (demi.shift(1).fillna(0.002) + 0.0002) \
        - tenue * swap_an / 365 * S.TF_H[ctx["tf"]] / 24
    return M.journalier(net)


def resume_j(nj, a, b):
    y = nj[(nj.index >= a) & (nj.index < b)]
    eq = (1 + y).cumprod()
    return dict(sharpe=round(y.mean() / y.std() * np.sqrt(365), 2), cagr=round(eq.iloc[-1] ** (365 / len(y)) - 1, 2),
                mdd=round((eq / eq.cummax() - 1).min(), 2))


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    ctxs = {(a, tf): S.contexte(a, tf) for a in ("BTC", "ETH") for tf in ("1d", "4h")}
    votes = {k: votes_a_priori(c) for k, c in ctxs.items()}
    bancs = {k: M.Banc(c["d"].close, c["funding_bougie"], PERIODES) for k, c in ctxs.items()}

    print("== Référence : achat-conservation ==")
    for a in ("BTC", "ETH"):
        print(a, bancs[(a, "1d")].achat_conservation())

    print("\n== 1. Retirer un outil (1d, spot) ==")
    rows = []
    for a in ("BTC", "ETH"):
        k = (a, "1d")
        allc = list(votes[k].columns)
        rows.append(dict(actif=a, version="les 9", **ligne(bancs[k], position(votes[k], ctxs[k]))))
        for out in allc:
            rows.append(dict(actif=a, version=f"sans {out}",
                             **ligne(bancs[k], position(votes[k], ctxs[k], cols=[c for c in allc if c != out]))))
        rows.append(dict(actif=a, version="prix seul (6)", **ligne(bancs[k], position(votes[k], ctxs[k], cols=PRIX_SEUL))))
        rows.append(dict(actif=a, version="prix seul + orderflow",
                         **ligne(bancs[k], position(votes[k], ctxs[k], cols=PRIX_SEUL + ["orderflow"]))))
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n== 2. Voisinage : seuil × dosage × unité de temps (spot) ==")
    rows = []
    for (a, tf), v in votes.items():
        for s in (0.01, 0.15, 0.25, 0.35, 0.5):
            for vol in (None, 0.3, 0.4, 0.5):
                rows.append(dict(actif=a, tf=tf, seuil=s, vol=vol or "-",
                                 **ligne(bancs[(a, tf)], position(v, ctxs[(a, tf)], s, vol))))
    t = pd.DataFrame(rows)
    print(t[["actif", "tf", "seuil", "vol", "R_sharpe", "R_t_alpha", "V_sharpe", "V_t_alpha", "T_sharpe", "T_cagr",
             "T_mdd", "T_t_alpha", "T_trades"]].to_string(index=False))

    print("\n== 3. Exécution retardée d'une bougie (1d, spot) ==")
    for a in ("BTC", "ETH"):
        k = (a, "1d")
        p = position(votes[k], ctxs[k])
        print(a, "normal  ", ligne(bancs[k], p))
        print(a, "retard 1", ligne(bancs[k], p.shift(1).fillna(0)))

    print("\n== 4. Année par année (1d, spot, rendement de l'année) ==")
    for a in ("BTC", "ETH"):
        k = (a, "1d"); c = ctxs[k]
        net, _ = M.rendements(position(votes[k], c), c["d"].close, "spot")
        nj = M.journalier(net); bh = M.journalier(c["d"].close.pct_change().fillna(0))
        an = pd.DataFrame({"strategie": (1 + nj).groupby(nj.index.year).prod() - 1,
                           "achat-conservation": (1 + bh).groupby(bh.index.year).prod() - 1})
        dd = pd.Series({y: ((1 + g).cumprod() / (1 + g).cumprod().cummax() - 1).min() for y, g in nj.groupby(nj.index.year)})
        an["pire baisse strat."] = dd
        print(a); print(an.loc[2018:].round(2).to_string())

    print("\n== 5. CFD MetaTrader (spread Dukascopy + swap 20 %/an), long seulement, 1d ==")
    for a, code in (("BTC", "btcusd"), ("ETH", "ethusd")):
        k = (a, "1d")
        nj = cfd(ctxs[k], position(votes[k], ctxs[k]), code)
        for nom, (d0, d1) in (("2022-2026", (pd.Timestamp("2022-01-01", tz="UTC"), M.VALIDATION[1])),
                              ("validation 2023-2026", M.VALIDATION)):
            print(a, nom, "CFD", resume_j(nj, d0, d1))
        net, _ = M.rendements(position(votes[k], ctxs[k]), ctxs[k]["d"].close, "spot")
        print(a, "2022-2026 spot Binance", resume_j(M.journalier(net), pd.Timestamp("2022-01-01", tz="UTC"), M.VALIDATION[1]))
        for swap in (0.0, 0.10, 0.30):
            print(a, f"  swap {swap:.0%}", resume_j(cfd(ctxs[k], position(votes[k], ctxs[k]), code, swap), *M.VALIDATION))


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "robustesse.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
