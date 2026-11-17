"""Étape 6 : les hypothèses tirées de la littérature (voir RAPPORT-2.md, section « ce que dit la recherche »).

H1 « carry crash » (BRI, Schmeling-Schrimpf-Todorov) : financement moyen 7 j dans les 10 % les plus hauts de l'année
   ET clôture < EMA20 -> le risque de krach augmente. Test : probabilité d'une baisse de 15 % dans les 30 jours ;
   puis utilisé pour couper les achats de la confluence, ou pour vendre 10 jours.
H2 Vente de tendance en régime baissier (clôture < SMA200, SMA200 en baisse sur 20 j, rendement 90 j < 0) : vente
   sous le plus bas de 20 jours, rachat au-dessus du plus haut de 10 jours ou de la SMA50 ; pas de vente si le
   financement 3 j < -0,01 % (ventes déjà encombrées). Variantes : + prime Coinbase 7 j < 0 ; + Fear & Greed
   remonté >= 45 dans les 5 derniers jours (vendre les rebonds de soulagement).
H4 Franchissement d'un chiffre rond (Osler) : première clôture au-delà d'un multiple de 5 000 / 10 000 $ (BTC),
   500 / 1 000 $ (ETH) après 10 jours de l'autre côté : le mouvement continue-t-il sur 1, 3, 5 jours ? Témoins :
   mêmes règles avec les niveaux décalés d'une fraction aléatoire du pas.
H7 Ensemble de canaux de Donchian (Zarattini-Pagani-Barbon) : moyenne des états de cassure 10/20/40/80/160 jours,
   taille × 40 % ÷ volatilité 30 j ; vente seulement si la moyenne < -0,6.
H8 Exécution : la même confluence avec des bougies journalières clôturées à 22:00 UTC au lieu de 00:00.
Sortie : sorties/hypotheses.txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import indicateurs as I
import moteur as M
import signaux as S
from confluence import votes_a_priori, dosage_vol
from recherche import PERIODES, OUT

CHIFFRES = {"BTC": (5000, 10000), "ETH": (500, 1000)}


def montrer(banc, nom, p, mode):
    r = banc.evaluer(p.fillna(0).values, mode)
    print(f"  {nom:<52} {mode:<5}", "  ".join(
        f"{k}: Sh {x['sharpe']:.2f} t {x['t_alpha']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%} n {x['trades']}"
        for k, x in r.items() if x))


def h1(ctx, banc, longp):
    d = ctx["d"]; c = d.close
    f7 = ctx["funding"].rolling(7, min_periods=1).mean()
    rg = I.rang_glissant(f7, 365)
    cond = (rg > 0.9) & (c < I.ema(c, 20))
    futur_min = d.low[::-1].rolling(30, min_periods=1).min()[::-1].shift(-1)
    krach = (futur_min / c - 1) <= -0.15
    ok = f7.notna() & futur_min.notna()
    for per, (a, b) in PERIODES.items():
        m = ok & (d.index >= a) & (d.index < b)
        print(f"  H1 {per}: P(krach 15 % en 30 j) si condition = {krach[m & cond].mean():.0%} (n={int((m & cond).sum())} jours)"
              f" ; sinon {krach[m & ~cond].mean():.0%}")
    montrer(banc, "H1 confluence, achats coupés si condition", longp.where(~cond, 0), "spot")
    vente = -(cond.astype(float).rolling(10, min_periods=1).max())       # vendu 10 jours après chaque jour de condition
    montrer(banc, "H1 vente 10 jours sur condition", vente, "court")


def h2(ctx, banc):
    d = ctx["d"]; c = d.close
    m200 = I.sma(c, 200)
    regime = (c < m200) & (m200 < m200.shift(20)) & (c / c.shift(90) - 1 < 0)
    f3 = ctx["funding"].rolling(3, min_periods=1).mean()
    base = regime & (c < d.low.rolling(20).min().shift()) & ~(f3 < -0.0001)
    sortie = (c > d.high.rolling(10).max().shift()) | (c > I.sma(c, 50))
    cb = ctx["prime_cb"].rolling(7, min_periods=1).mean()
    fg = ctx["fng"].rolling(5, min_periods=1).max()
    dose = dosage_vol(ctx, 0.4)
    for nom, e in (("H2 vente de tendance baissière", base),
                   ("H2 + prime Coinbase 7 j < 0", base & (cb < 0)),
                   ("H2 + Fear&Greed remonté >= 45 en 5 j", regime & (fg >= 45) & (c < I.ema(c, 10)) & ~(f3 < -0.0001))):
        p = -S.tenir(e, sortie)
        montrer(banc, nom, p * dose, "court")


def h4(ctx, rng):
    d = ctx["d"]; c = d.close.values
    lignes = []
    for pas in CHIFFRES[ctx["actif"]]:
        for temoin in range(0, 21):
            dec = 0 if temoin == 0 else rng.uniform(0.2, 0.8) * pas
            niveau_bas = np.floor((c - dec) / pas) * pas + dec          # niveau sous la clôture
            res = []
            for i in range(11, len(c) - 5):
                for L in (niveau_bas[i], niveau_bas[i] + pas):
                    if c[i] > L and (c[i - 10:i] < L).all():
                        sens = 1
                    elif c[i] < L and (c[i - 10:i] > L).all():
                        sens = -1
                    else:
                        continue
                    res.append((d.index[i], sens * (c[i + 1] / c[i] - 1), sens * (c[i + 3] / c[i] - 1), sens * (c[i + 5] / c[i] - 1)))
            r = pd.DataFrame(res, columns=["t", "r1", "r3", "r5"])
            lignes.append(dict(pas=pas, temoin=temoin, n=len(r), **{k: r[k].mean() * 100 for k in ("r1", "r3", "r5")}))
    t = pd.DataFrame(lignes)
    for pas, g in t.groupby("pas"):
        vrai = g[g.temoin == 0].iloc[0]; tem = g[g.temoin > 0]
        print(f"  H4 pas {pas}: {int(vrai.n)} franchissements, suite moyenne en % 1j/3j/5j = "
              f"{vrai.r1:+.2f}/{vrai.r3:+.2f}/{vrai.r5:+.2f} ; témoins (médiane de 20) "
              f"{tem.r1.median():+.2f}/{tem.r3.median():+.2f}/{tem.r5.median():+.2f} ; rang du vrai parmi 21 (5 j) : "
              f"{int((tem.r5 < vrai.r5).sum()) + 1}")


def h7(ctx, banc):
    d = ctx["d"]; c = d.close
    etats = []
    for n in (10, 20, 40, 80, 160):
        hh, ll = d.high.rolling(n).max().shift(), d.low.rolling(n).min().shift()
        etats.append(S.tenir(c > hh, c < ll, c < ll, c > hh))
    moy = pd.concat(etats, axis=1).mean(axis=1)
    dose = dosage_vol(ctx, 0.4)
    montrer(banc, "H7 Donchian ensemble, achat (moyenne > 0)", moy.clip(lower=0) * dose, "spot")
    montrer(banc, "H7 Donchian ensemble, achat seuil 0", S.etat(moy > 0) * dose, "spot")
    montrer(banc, "H7 Donchian ensemble, ventes si < -0,6", -S.etat(moy < -0.6) * dose, "court")
    montrer(banc, "H7 Donchian ensemble, achat + ventes", (moy.clip(lower=0) - S.etat(moy < -0.6)) * dose, "perp")
    return moy


def main():
    rng = np.random.default_rng(0)
    for actif in ("BTC", "ETH"):
        print(f"\n######## {actif} ########")
        ctx = S.contexte(actif, "1d")
        banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
        conf = votes_a_priori(ctx).mean(axis=1)
        dose = dosage_vol(ctx, 0.4)
        longp = S.etat(conf >= 0.25) * dose
        montrer(banc, "référence : confluence achat", longp, "spot")
        h1(ctx, banc, longp)
        h2(ctx, banc)
        h4(ctx, rng)
        moy = h7(ctx, banc)
        montrer(banc, "confluence + ensemble Donchian (moyenne des deux)", ((S.etat(conf >= 0.25) + S.etat(moy > 0)) / 2) * dose, "spot")
        for dec in (20, 21, 22, 23):
            c2 = S.contexte(actif, "1d", dec)
            b2 = M.Banc(c2["d"].close, c2["funding_bougie"], PERIODES)
            p2 = S.etat(votes_a_priori(c2).mean(axis=1) >= 0.25) * dosage_vol(c2, 0.4)
            montrer(b2, f"H8 confluence, clôture journalière à {dec}:00 UTC", p2, "spot")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "hypotheses.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
