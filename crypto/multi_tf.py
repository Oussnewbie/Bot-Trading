"""Étape 10 : système multi-unités de temps. La journée donne le SENS (confluence des 9 votes, connue à la clôture de
la veille), le H4 donne l'ENTRÉE, à l'achat comme à la vente.

A  référence : confluence journalière, achat seul, tenue en continu (évaluée sur bougies 4h pour comparer).
B  achat si fond haussier ET tendance 4h haussière (EMA50 > EMA200 et clôture > EMA200) ; vente si fond baissier ET
   tendance 4h baissière.
C  B + déclencheur de vente « chasse de liquidité + delta vendeur » en fond baissier (plus haut des 20 bougies 4h
   dépassé, clôture dessous, ventes agressives majoritaires ; tenue 48 bougies = 8 jours).
D  B, achats seuls.
Taille : min(1 ; 40 % ÷ volatilité journalière 30 j), comme la confluence.
Sortie : sorties/multi-tf.txt
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
from petites_tf import fond, tenir_n
from recherche import PERIODES, OUT


def caler(serie_j, idx):
    """Valeur journalière connue à la clôture (index + 1 jour), recopiée sur des bougies plus fines."""
    dispo = serie_j.index + pd.Timedelta("1D")
    pos = np.searchsorted(dispo.values, idx.values, side="right") - 1
    return pd.Series(np.where(pos >= 0, serie_j.values[np.maximum(pos, 0)], 0.0), index=idx)


def main():
    for actif in ("BTC", "ETH"):
        d = DN.bougies_m5(actif + "USDT", "4h")
        d = d[d.index >= pd.Timestamp("2017-10-01", tz="UTC")]
        c = d.close
        banc = M.Banc(c, financement_par_bougie(DN.financement(actif + "USDT"), d.index), PERIODES)
        ctxj = S.contexte(actif, "1d")
        score = caler(votes_a_priori(ctxj).mean(axis=1), d.index)
        dose = caler(dosage_vol(ctxj, 0.4), d.index)
        e50, e200 = I.ema(c, 50), I.ema(c, 200)
        t_h, t_b = (e50 > e200) & (c > e200), (e50 < e200) & (c < e200)
        haut, bas = score >= 0.25, score <= -0.25
        hp = d.high.rolling(20).max().shift()
        chasse = ((d.high > hp) & (c < hp) & (d.delta < 0) & bas)
        vente_chasse = tenir_n(S.etat(pd.Series(False, index=d.index), chasse), 48)
        A = S.etat(haut) * dose
        B = (S.etat(haut & t_h) - S.etat(bas & t_b)) * dose
        C = (S.etat(haut & t_h) - ((S.etat(bas & t_b) + (-vente_chasse)) > 0).astype(float)) * dose
        D = S.etat(haut & t_h) * dose
        print(f"\n######## {actif} (bougies 4h) ########  achat-conservation :",
              "  ".join(f"{k}: Sh {v['sharpe']:.2f} cagr {v['cagr']:.0%} dd {v['mdd']:.0%}" for k, v in banc.achat_conservation().items()))
        for nom, p, mode in (("A confluence journalière, achat (spot)", A, "spot"),
                             ("D fond haussier + tendance 4h, achat (spot)", D, "spot"),
                             ("B fond + tendance 4h, achat et vente (perp)", B, "perp"),
                             ("B … partie vente seule", B, "court"),
                             ("C B + chasse de liquidité en fond baissier (perp)", C, "perp"),
                             ("C … partie vente seule", C, "court")):
            r = banc.evaluer(p.fillna(0).values, mode)
            print(f"  {nom:<50}", "  ".join(f"{k}: Sh {x['sharpe']:.2f} t {x['t_alpha']:.2f} cagr {x['cagr']:.0%} "
                                            f"dd {x['mdd']:.0%} expo {x['expo']:.0%}" for k, x in r.items() if x))


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "multi-tf.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
