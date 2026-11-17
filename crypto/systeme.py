"""Le système final et l'OUTIL d'analyse journalière.

Système (décidé à la clôture journalière 00:00 UTC, exécuté juste après) :
 1. ACHAT — confluence des 9 votes (score >= 0,25), taille = min(1 ; 40 % ÷ volatilité 30 j).
 2. VENTE (option, perpétuel) — « vendre les rebonds de soulagement en tendance baissière » :
    régime baissier (clôture < SMA200, SMA200 en baisse sur 20 j, rendement 90 j < 0, ET score <= -0,25),
    Fear & Greed remonté à 45 ou plus dans les 5 derniers jours, clôture repassée sous l'EMA10,
    pas de vente si le financement 3 j < -0,01 %. Rachat au-dessus du plus haut de 10 jours ou de la SMA50.
    Même taille.
 3. ALERTE de risque (pas un signal) — « carry crash » : financement 7 j dans les 10 % les plus hauts de l'année ET
    clôture < EMA20 (BTC : 42 % de risque d'une chute de 15 % en 30 jours, contre 27 % sinon).

`python systeme.py` : évaluation complète (achat seul, vente seule, les deux), Sharpe « dégonflé » (Bailey et López de
Prado) pour 1 à 70 000 essais, puis le TABLEAU DU JOUR pour BTC et ETH.
"""
import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

import donnees as DN
import indicateurs as I
import moteur as M
import niveaux as N
import signaux as S
from confluence import votes_a_priori, dosage_vol
from recherche import PERIODES, OUT

SEUIL, VOL = 0.25, 0.4


def positions(ctx):
    d = ctx["d"]; c = d.close
    votes = votes_a_priori(ctx)
    score = votes.mean(axis=1)
    dose = dosage_vol(ctx, VOL)
    achat = S.etat(score >= SEUIL) * dose
    m200 = I.sma(c, 200)
    regime = (c < m200) & (m200 < m200.shift(20)) & (c / c.shift(90) - 1 < 0) & (score <= -SEUIL)
    f3 = ctx["funding"].rolling(3, min_periods=1).mean()
    fg = ctx["fng"].rolling(5, min_periods=1).max()
    entree = regime & (fg >= 45) & (c < I.ema(c, 10)) & ~(f3 < -0.0001)
    sortie = (c > d.high.rolling(10).max().shift()) | (c > I.sma(c, 50))
    vente = -S.tenir(entree, sortie) * dose
    f7 = ctx["funding"].rolling(7, min_periods=1).mean()
    alerte = (I.rang_glissant(f7, 365) > 0.9) & (c < I.ema(c, 20))
    return dict(votes=votes, score=score, dose=dose, achat=achat, vente=vente, alerte=alerte, regime=regime,
                fg=ctx["fng"], f7=f7)


def sharpe_degonfle(y, x, essais):
    """Deflated Sharpe Ratio (Bailey et López de Prado 2014) sur l'ALPHA journalier (rendement - bêta × actif) :
    probabilité que l'alpha soit réel après avoir essayé `essais` variantes."""
    b = np.polyfit(x, y, 1)[0]
    e = y - b * x
    sr = e.mean() / e.std()
    T = len(e); g3 = skew(e); g4 = kurtosis(e, fisher=False)
    var_sr = (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (T - 1)
    if essais > 1:
        gam = 0.5772
        sr0 = np.sqrt(var_sr) * ((1 - gam) * norm.ppf(1 - 1 / essais) + gam * norm.ppf(1 - 1 / (essais * np.e)))
    else:
        sr0 = 0.0
    return norm.cdf((sr - sr0) / np.sqrt(var_sr)), sr * np.sqrt(365)


def evaluation():
    for actif in ("BTC", "ETH"):
        ctx = S.contexte(actif, "1d")
        banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
        P = positions(ctx)
        print(f"\n######## {actif} ########  achat-conservation :",
              "  ".join(f"{k}: Sh {v['sharpe']:.2f} cagr {v['cagr']:.0%} dd {v['mdd']:.0%}" for k, v in banc.achat_conservation().items()))
        for nom, p, mode in (("achat seul (spot)", P["achat"], "spot"), ("vente seule (perp)", P["vente"], "court"),
                             ("achat + vente (perp)", P["achat"] + P["vente"], "perp")):
            r = banc.evaluer(p.fillna(0).values, mode)
            print(f"  {nom:<22}", "  ".join(f"{k}: Sh {x['sharpe']:.2f} t {x['t_alpha']:.2f} cagr {x['cagr']:.0%} "
                                            f"dd {x['mdd']:.0%} expo {x['expo']:.0%}" for k, x in r.items() if x))
        net, _ = M.rendements(P["achat"], ctx["d"].close, "spot")
        y = M.journalier(net); x = M.journalier(ctx["d"].close.pct_change().fillna(0))
        m = y.index >= pd.Timestamp("2018-03-01", tz="UTC")
        for n in (1, 15, 1000, 70000):
            p, sra = sharpe_degonfle(y[m].values, x[m].values, n)
            print(f"  Sharpe dégonflé de l'alpha (achat), {n:>6} essais : probabilité que l'avantage soit réel = {p:.0%}"
                  f" (Sharpe de l'alpha {sra:.2f})")


def niveaux_proches(actif, prix):
    """Niveaux d'information (PAS des signaux : aucun ne fait mieux que le hasard dans niveaux.py) : les seuls qui ont
    un comportement mesuré sont le plus haut / plus bas de la veille (souvent cassés) et le nuage Ichimoku (rejette
    le prix qui remonte par-dessous)."""
    h, d = N.journalier(actif)
    i = len(d) - 1
    out = {}
    for nom, f in (("veille", lambda: N.m_precedents(d, "jour")), ("semaine passée", lambda: N.m_precedents(d, "semaine")),
                   ("pivots 5 j (≥ 2 touches)", lambda: N.m_pivots(d, 5, min_touches=2)),
                   ("profil de volume 30 j (POC, zone)", lambda: {i: np.r_[N.m_profil_volume(h, d, 30, "poc")[i],
                                                                          N.m_profil_volume(h, d, 30, "zone")[i]]}),
                   ("Ichimoku kijun / nuage", lambda: N.m_ichimoku(d))):
        niv = np.sort(np.asarray(f().get(i, [])))
        dessous = niv[niv < prix][-2:]; dessus = niv[niv > prix][:2]
        out[nom] = (dessous, dessus)
    return out


def tableau_du_jour():
    for actif in ("BTC", "ETH"):
        ctx = S.contexte(actif, "1d")
        P = positions(ctx)
        d = ctx["d"]; t = d.index[-1]; c = d.close.iloc[-1]
        v = P["votes"].iloc[-1]
        print(f"\n━━━━━━━━ {actif} — bougie du {t:%Y-%m-%d} (clôture {c:,.2f} $) ━━━━━━━━")
        print("  Votes      : " + "  ".join(f"{k} {int(x):+d}" for k, x in v.items()))
        print(f"  Score      : {P['score'].iloc[-1]:+.2f}   (achat si >= {SEUIL}, régime baissier si <= -{SEUIL})")
        pa, pv = P["achat"].iloc[-1], P["vente"].iloc[-1]
        etat = "ACHAT" if pa > 0 else ("VENTE" if pv < 0 else "HORS MARCHÉ")
        print(f"  Décision   : {etat}  — achat {pa:.0%} du capital, vente {-pv:.0%} (dosage volatilité {P['dose'].iloc[-1]:.0%})")
        print(f"  Régime baissier strict : {'oui' if P['regime'].iloc[-1] else 'non'} ; Fear & Greed {P['fg'].iloc[-1]:.0f} "
              f"(max 5 j {P['fg'].rolling(5).max().iloc[-1]:.0f}) ; la vente attend un rebond de soulagement (F&G >= 45)")
        print(f"  Alerte « carry crash » : {'OUI' if P['alerte'].iloc[-1] else 'non'} "
              f"(financement 7 j {P['f7'].iloc[-1] * 3 * 365:+.1%} par an)")
        print(f"  Prime perp {ctx['prime'].iloc[-1]:+.4%} ; prime Coinbase 24 h {ctx['prime_cb'].iloc[-1]:+.3%} ; DVOL "
              f"{ctx['dvol'].iloc[-1]:.0f}")
        d4 = DN.bougies_m5(actif + "USDT", "4h")
        c4 = d4.close; e50, e200 = I.ema(c4, 50), I.ema(c4, 200)
        etat4 = "haussière" if (e50.iloc[-1] > e200.iloc[-1] and c4.iloc[-1] > e200.iloc[-1]) else \
            ("baissière" if (e50.iloc[-1] < e200.iloc[-1] and c4.iloc[-1] < e200.iloc[-1]) else "neutre")
        sc = P["score"].iloc[-1]
        mtf = "ACHAT" if (sc >= SEUIL and etat4 == "haussière") else ("VENTE" if (sc <= -SEUIL and etat4 == "baissière") else "rien")
        print(f"  Multi-unités (RAPPORT-3) : tendance 4h {etat4} (bougie {d4.index[-1]:%d/%m %H:%M} UTC) -> {mtf}")
        for nom, (dessous, dessus) in niveaux_proches(actif, c).items():
            print(f"  {nom:<34} dessous {', '.join(f'{x:,.0f}' for x in dessous) or '-':<22} dessus "
                  f"{', '.join(f'{x:,.0f}' for x in dessus) or '-'}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        if "--jour" not in sys.argv:
            evaluation()
        tableau_du_jour()
    if "--jour" not in sys.argv:
        open(os.path.join(OUT, "systeme.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
