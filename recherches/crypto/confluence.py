"""Étape 2 : assembler les outils en UNE stratégie de confluence.

Chaque outil donne un vote (+1 haussier, -1 baissier, 0 neutre) à la clôture de chaque bougie. Le score est la moyenne
des votes (-1 à +1). On teste deux façons de l'utiliser :
 - seuil : position +1 si score >= s, -1 si score <= -s (perp) ou 0 ;
 - proportionnelle : position = score (on achète plus quand plus d'outils sont d'accord).
Et, en option, un dosage par la volatilité : position × min(1, volatilité cible ÷ volatilité des 30 derniers jours).

Deux jeux de votes :
 - « a priori » : un réglage standard par outil demandé, fixé AVANT de voir les résultats (MA200, Ichimoku 9-26-52,
   MACD 12-26-9, RSI 14 > 50, VWAP ancré au mois, Fibonacci = prix au-dessus du 0,618 de la jambe de 90 jours,
   order flow spot 7 jours, flux on-chain 30 jours, ETH/BTC au-dessus de sa MA50) ;
 - « choisis » : pour chaque famille, la variante au meilleur t d'alpha sur la RECHERCHE BTC (fichier variantes).
Comme toujours : choix sur BTC 2018-2022, vérification sur BTC 2023-2026 et sur l'ETH.
"""
import os
import sys

import numpy as np
import pandas as pd

import partage  # noqa: F401,E402  (donnees, indicateurs, btc : dans bitcoin/, partagés avec le bot)
import indicateurs as I
import moteur as M
import signaux as S
from recherche import PERIODES, OUT


def votes_a_priori(ctx):
    d = ctx["d"]; c = d.close
    ich = I.ichimoku(d, 9, 26, 52)
    haut = np.maximum(ich["spanA"], ich["spanB"]); bas = np.minimum(ich["spanA"], ich["spanB"])
    m, s, _ = I.macd(c, 12, 26, 9)
    va = I.vwap_ancre(d, "M")
    n90 = S.barres(ctx, 90)
    hh, ll = d.high.rolling(n90).max(), d.low.rolling(n90).min()
    n7 = S.barres(ctx, 7)
    of = d.delta.rolling(n7).sum() / d.volume.rolling(n7).sum()
    oc = ctx["onchain"]
    net = (oc.FlowInExNtv - oc.FlowOutExNtv).rolling(S.barres(ctx, 30)).mean()
    eb = ctx["ethbtc"]
    v = {
        "ma200": np.sign(c - I.sma(c, 200)),
        "ichimoku": S.etat(c > haut, c < bas),
        "macd": np.sign(m - s),
        "rsi": np.sign(I.rsi(c, 14) - 50),
        "vwap": np.sign(c - va),
        "fibonacci": S.etat(c > ll + 0.618 * (hh - ll), c < ll + 0.382 * (hh - ll)),
        "orderflow": np.sign(of),
        "onchain": S.etat(net < 0, net > 0),
        "ethbtc": np.sign(eb - I.sma(eb, 50)) * (1 if ctx["actif"] == "ETH" else 1),
    }
    return pd.DataFrame({k: x.fillna(0) for k, x in v.items()})


def votes_choisis(ctx, choix):
    base = S.tous(ctx)
    fil = S.filtres(ctx)
    out = {}
    for fam, (nom, fn) in choix.items():
        p = base[nom]
        out[fam] = p if not fn else S.filtrer(p, fil[fn])
    return pd.DataFrame(out).fillna(0)


def choisir(df, tf, mode, exclure=("calendrier",)):
    """Meilleure variante SANS filtre par famille sur la recherche BTC (t d'alpha), quelle que soit sa vérification."""
    x = df[(df.actif == "BTC") & (df.tf == tf) & (df["mode"] == mode) & (df.filtre.isna() | (df.filtre == ""))]
    x = x[~x.famille.isin(exclure) & (x.R_trades >= 10)]
    best = x.sort_values("R_t_alpha", ascending=False).groupby("famille").head(1)
    return {r.famille: (r.variante, "") for r in best.itertuples()}, best[["famille", "variante", "R_t_alpha", "V_t_alpha"]]


def dosage_vol(ctx, cible):
    r = ctx["d"].close.pct_change()
    vol = r.rolling(S.barres(ctx, 30)).std() * np.sqrt(ctx["n_an"])
    return (cible / vol).clip(upper=1).fillna(0)


def positions(score, regle):
    if regle == "proportionnelle":
        return score
    s = float(regle)
    return S.etat(score >= s, score <= -s)


REGLES = ["proportionnelle", "0.01", "0.25", "0.5", "0.75"]


def evaluer_tout(votes_par_actif, ctxs, mode, nom_jeu):
    lignes = []
    for actif, votes in votes_par_actif.items():
        ctx = ctxs[actif]
        banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
        score = votes.mean(axis=1)
        for regle in REGLES:
            for vc in (None, 0.4, 0.6):
                p = positions(score, regle)
                if vc:
                    p = p * dosage_vol(ctx, vc)
                res = banc.evaluer(p.values, mode)
                l = dict(jeu=nom_jeu, actif=actif, mode=mode, regle=regle, vol_cible=vc or "")
                for per, r in res.items():
                    for k, v in (r or {}).items():
                        l[f"{per}_{k}"] = float(v)
                lignes.append(l)
    return lignes


if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "1d"
    df = pd.read_csv(os.path.join(OUT, "variantes.csv.gz"))
    ctxs = {a: S.contexte(a, tf) for a in ("BTC", "ETH")}
    lignes = []
    for mode in ("spot", "perp"):
        lignes += evaluer_tout({a: votes_a_priori(c) for a, c in ctxs.items()}, ctxs, mode, "a-priori")
        choix, tab = choisir(df, tf, mode)
        print(mode, "variantes choisies :\n", tab.to_string(index=False))
        lignes += evaluer_tout({a: votes_choisis(c, choix) for a, c in ctxs.items()}, ctxs, mode, "choisis")
    res = pd.DataFrame(lignes)
    res.to_csv(os.path.join(OUT, f"confluence-{tf}.csv"), index=False, float_format="%.4f")
    cols = ["jeu", "actif", "mode", "regle", "vol_cible", "R_sharpe", "R_t_alpha", "V_sharpe", "V_t_alpha", "V_mdd",
            "T_sharpe", "T_cagr", "T_mdd", "T_t_alpha"]
    pd.set_option("display.width", 250)
    print(res[cols].round(2).to_string(index=False))
