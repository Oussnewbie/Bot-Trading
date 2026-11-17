"""Étape 11 : comment doser la VENTE du système multi-unités (RAPPORT-3) ?

Partie achat fixe : fond journalier haussier (score >= 0,25) ET tendance 4h haussière, taille 40 % ÷ vol 30 j.
Partie vente de base : fond journalier baissier (score <= -0,25) ET tendance 4h baissière (EMA50 < EMA200, clôture
< EMA200), même taille. Variantes de la vente, écrites AVANT de lancer :
 taille       : 0 (achat seul), 0,25, 0,5, 0,75, 1 × la taille de l'achat
 vol-cible    : la vente dosée à 20 % ou 30 % de volatilité au lieu de 40 %
 proportionnel: taille × |score| (plus les votes sont baissiers, plus on vend)
 seuil        : vendre seulement si score <= -0,5 ou <= -0,75
 peur         : pas de vente si Fear & Greed < 20 (capitulation : rebonds violents)
 encombre     : pas de vente si financement moyen 3 j < -0,01 % par 8 h (vendeurs déjà trop nombreux)
 sortie-ema20 : sortie plus rapide, dès une clôture 4h au-dessus de l'EMA20 (retour quand elle repasse dessous)
 duree30      : 30 jours au plus par épisode de vente
 frein-dd     : la vente passe à mi-taille quand sa propre courbe est à plus de 15 % sous son sommet
 + quelques combinaisons.
Règle de choix (écrite avant) : meilleur Sharpe du système complet sur BTC 2018-2022 ; on regarde ensuite BTC
2023-2026, l'ETH, et un portefeuille 50/50 BTC-ETH. Sortie : sorties/dosage-vente.csv et .txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I
import moteur as M
import signaux as S
from confluence import votes_a_priori, dosage_vol
from moteur import financement_par_bougie
from multi_tf import caler
from recherche import PERIODES, OUT


def preparer(actif):
    d = DN.bougies_m5(actif + "USDT", "4h")
    d = d[d.index >= pd.Timestamp("2017-10-01", tz="UTC")]
    c = d.close
    fb = financement_par_bougie(DN.financement(actif + "USDT"), d.index)
    ctxj = S.contexte(actif, "1d")
    score = caler(votes_a_priori(ctxj).mean(axis=1), d.index)
    dose = {v: caler(dosage_vol(ctxj, v), d.index) for v in (0.2, 0.3, 0.4)}
    fng = caler(ctxj["fng"], d.index)
    f = DN.financement(actif + "USDT")
    f3 = f.rolling(9, min_periods=1).mean()            # 9 financements = 3 jours
    f3 = f3.reindex(f3.index.union(d.index)).ffill().reindex(d.index + pd.Timedelta("4h") - pd.Timedelta("1s")).set_axis(d.index)
    e20, e50, e200 = I.ema(c, 20), I.ema(c, 50), I.ema(c, 200)
    return dict(d=d, c=c, fb=fb, score=score, dose=dose, fng=fng, f3=f3, e20=e20,
                t_h=(e50 > e200) & (c > e200), t_b=(e50 < e200) & (c < e200))


def vente(P, taille=1.0, vol=0.4, proportionnel=False, seuil=-0.25, peur=False, encombre=False, sortie_ema20=False,
          duree=None, frein_dd=False):
    c, sc = P["c"], P["score"]
    ok = (sc <= seuil) & P["t_b"]
    if peur:
        ok &= ~(P["fng"] < 20)
    if encombre:
        ok &= ~(P["f3"] < -0.0001)
    if sortie_ema20:
        ok &= c < P["e20"]
    s = ok.astype(float)
    if duree:
        grp = (s.diff() != 0).cumsum()
        age = s.groupby(grp).cumcount()
        s = s.where(age < duree * 6, 0)
    s = s * P["dose"][vol] * taille
    if proportionnel:
        s = s * sc.abs().clip(upper=1)
    if frein_dd:
        r = c.pct_change().fillna(0).values
        sv = s.values.copy(); eq = 1.0; pic = 1.0; out = np.zeros(len(sv))
        for i in range(1, len(sv)):
            eq *= 1 - out[i - 1] * r[i]
            pic = max(pic, eq)
            out[i] = sv[i] * (0.5 if eq / pic < 0.85 else 1.0)
        s = pd.Series(out, index=s.index)
    return -s


VARIANTES = {
    "achat seul": dict(taille=0.0),
    "vente 0,25": dict(taille=0.25), "vente 0,5": dict(taille=0.5), "vente 0,75": dict(taille=0.75), "vente 1": dict(taille=1.0),
    "vol-cible 20 %": dict(vol=0.2), "vol-cible 30 %": dict(vol=0.3),
    "proportionnel": dict(proportionnel=True),
    "seuil -0,5": dict(seuil=-0.5), "seuil -0,75": dict(seuil=-0.75),
    "peur (pas si F&G < 20)": dict(peur=True), "encombre (pas si funding < 0)": dict(encombre=True),
    "sortie-ema20": dict(sortie_ema20=True), "duree30": dict(duree=30), "frein-dd": dict(frein_dd=True),
    "0,5 + proportionnel": dict(taille=0.5, proportionnel=True),
    "0,5 + seuil -0,5": dict(taille=0.5, seuil=-0.5),
    "0,5 + peur + encombre": dict(taille=0.5, peur=True, encombre=True),
    "proportionnel + peur + encombre": dict(proportionnel=True, peur=True, encombre=True),
    "0,5 + sortie-ema20": dict(taille=0.5, sortie_ema20=True),
}


def stats_j(nj, bh, a, b):
    m = (nj.index >= a) & (nj.index < b)
    y = nj[m]; x = bh[m]
    eq = (1 + y).cumprod()
    (al, be), (ta, tb) = M.nw_t(y.values, x.values)
    return dict(sharpe=y.mean() / y.std() * np.sqrt(365), cagr=eq.iloc[-1] ** (365 / len(y)) - 1,
                mdd=(eq / eq.cummax() - 1).min(), t_alpha=ta)


def main():
    P = {a: preparer(a) for a in ("BTC", "ETH")}
    lignes = []
    nets = {}
    for nom, kw in VARIANTES.items():
        for a, p in P.items():
            achat = S.etat(p["score"] >= 0.25) * p["t_h"].astype(float) * p["dose"][0.4]
            v = vente(p, **kw)
            pos = (achat + v).fillna(0)
            net, tenue = M.rendements(pos, p["c"], "perp", p["fb"])
            nv, _ = M.rendements(v.fillna(0), p["c"], "perp", p["fb"])
            nj, njv = M.journalier(net), M.journalier(nv)
            bh = M.journalier(p["c"].pct_change().fillna(0))
            nets[(nom, a)] = nj
            for per, (d0, d1) in PERIODES.items():
                s = stats_j(nj, bh, d0, d1); sv = stats_j(njv, bh, d0, d1)
                lignes.append(dict(variante=nom, actif=a, periode=per, **s, vente_sharpe=sv["sharpe"], vente_mdd=sv["mdd"],
                                   expo_vente=float((v[(v.index >= d0) & (v.index < d1)] != 0).mean())))
        # portefeuille 50/50
        nj = (nets[(nom, "BTC")] + nets[(nom, "ETH")].reindex(nets[(nom, "BTC")].index).fillna(0)) / 2
        bh = M.journalier(P["BTC"]["c"].pct_change().fillna(0))
        for per, (d0, d1) in PERIODES.items():
            lignes.append(dict(variante=nom, actif="50/50", periode=per, **stats_j(nj, bh, d0, d1)))
    df = pd.DataFrame(lignes)
    df.to_csv(os.path.join(OUT, "dosage-vente.csv"), index=False, float_format="%.4f")
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    w = df.pivot_table(index="variante", columns=["actif", "periode"], values="sharpe").round(2)
    w = w.reindex(list(VARIANTES))
    print("== Sharpe du système complet (R = 2018-2022, V = 2023-2026, T = 2018-2026) ==")
    print(w.to_string())
    print("\n== Pire baisse du système complet ==")
    print(df.pivot_table(index="variante", columns=["actif", "periode"], values="mdd").reindex(list(VARIANTES)).round(2).to_string())
    print("\n== Gain par an du système complet ==")
    print(df.pivot_table(index="variante", columns=["actif", "periode"], values="cagr").reindex(list(VARIANTES)).round(2).to_string())
    print("\n== La vente seule : Sharpe propre et pire baisse ==")
    x = df[df.actif != "50/50"]
    print(x.pivot_table(index="variante", columns=["actif", "periode"], values=["vente_sharpe", "vente_mdd"]).reindex(list(VARIANTES)).round(2).to_string())
    r = df[(df.actif == "BTC") & (df.periode == "R")].sort_values("sharpe", ascending=False)
    print("\nRègle de choix — meilleur Sharpe BTC 2018-2022 :", r.iloc[0].variante)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "dosage-vente.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
