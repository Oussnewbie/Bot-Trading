"""Le levier de ×1 à ×10, calculé sur 2012-2026 (prix Bitstamp, bougies 4h) ; écrit profils.json, que lit Étrave.

Levier ×L = la position du profil prudent multipliée par L (volatilité visée 40 % × L, plafond L).
 - ×1 : achat au comptant (pas de financement), vente en perpétuel couverte : le montage actuel du bot ;
 - ×2 et plus : TOUT en perpétuel USDⓈ-M (marge croisée, tout le capital sur le portefeuille futures). Les achats
   paient le financement (réel depuis 2020, 10 % par an avant) ;
 - stop de protection posé chez Binance à mi-chemin de la liquidation (mouvement de 50 % ÷ exposition contre la
   position), vérifié sur le plus haut / plus bas de chaque bougie 4h, exécuté avec 0,5 % de glissement ;
 - liquidation si le mouvement contraire dans une bougie dépasse 100 % ÷ exposition - 0,5 % (marge de maintien) :
   le capital tombe à zéro. Avec le stop elle n'arrive que si le prix saute par-dessus le stop (non simulé : les
   bougies 4h ne montrent pas les sauts), d'où une ligne SANS stop pour voir le pire ;
 - frais : 0,12 % par côté au comptant, 0,07 % en perpétuel (ordres au marché ; les ordres limites font mieux).
Sortie : bitcoin/profils.json (lu par Étrave) et le tableau à l'écran.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import btc  # noqa: E402

PERIODES = {"2012-2026": (btc.DEBUT, btc.ANCIEN[1]), "2018-2026": btc.ANCIEN, "2022-2026": (pd.Timestamp("2022-01-01", tz="UTC"), btc.ANCIEN[1])}


def simuler(E, B, L, stop=True):
    d4 = B["d4"].reindex(E["c4"].index)
    c, h, l = d4.close.values, d4.high.values, d4.low.values
    idx = E["c4"].index
    pos = (btc.position(E, seuil=0.25, confirmation="ema50/200", vente=0.25, vol_cible=0.4) * L).clip(-L, L).values
    f = B["fund"]
    g = np.searchsorted(idx.values, f.index.values, side="right") - 1
    fb = pd.Series(f.values).groupby(g).sum()
    fund = np.full(len(idx), 0.10 / 365 / 6)
    ok = fb.index[fb.index >= 0]
    tmp = np.zeros(len(idx)); tmp[ok] = fb.loc[ok].values
    m = idx >= pd.Timestamp("2020-01-01", tz="UTC")
    fund[m] = tmp[m]
    perp = L > 1
    cout = np.where(idx < pd.Timestamp("2017-01-01", tz="UTC"), 0.0030, 0.0012 if not perp else 0.0007)
    eq = np.ones(len(idx)); e = 1.0; tenu = 0.0
    n_stop = n_liq = 0
    for i in range(1, len(idx)):
        voulu = pos[i - 1]
        if e <= 0:
            eq[i] = 0; continue
        e -= abs(voulu - tenu) * cout[i] * e
        tenu = voulu
        r = c[i] / c[i - 1] - 1
        if tenu != 0:
            adverse = (l[i] / c[i - 1] - 1) if tenu > 0 else -(h[i] / c[i - 1] - 1)
            liq = 1 / abs(tenu) - 0.005
            s = 0.5 / abs(tenu)
            if stop and abs(tenu) > 1 and adverse <= -s:
                e *= 1 - abs(tenu) * (s + 0.005)
                n_stop += 1
                tenu = 0.0
            elif adverse <= -liq:
                e = 0.0
                n_liq += 1
            else:
                fin = tenu * r
                if perp or tenu < 0:
                    fin -= tenu * fund[i]          # un acheteur en perp paie le financement positif, un vendeur le reçoit
                elif tenu > 1:
                    fin -= (tenu - 1) * fund[i]
                e *= 1 + fin
        eq[i] = max(e, 0.0)
    return pd.Series(eq, index=idx), n_stop, n_liq


def mesures(eq, a, b):
    x = eq[(eq.index >= a) & (eq.index < b)]
    j = x.resample("1D").last().dropna()
    r = j.pct_change().dropna()
    if j.iloc[-1] <= 0 or (j <= 0).any():
        return dict(sharpe=None, cagr=-1.0, mdd=-1.0, ruine=True)
    ans = (j.index[-1] - j.index[0]).days / 365
    return dict(sharpe=round(float(r.mean() / r.std() * np.sqrt(365)), 2), cagr=round(float((j.iloc[-1] / j.iloc[0]) ** (1 / ans) - 1), 3),
                mdd=round(float((j / j.cummax() - 1).min()), 3), ruine=False)


def main():
    B = btc.brutes()
    E = btc.elements(B)
    expo = btc.position(E, seuil=0.25, confirmation="ema50/200", vente=0.25, vol_cible=0.4)
    out = {"genere": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"), "leviers": []}
    for L in range(1, 11):
        eq, ns, nl = simuler(E, B, L, stop=True)
        eq0, _, nl0 = simuler(E, B, L, stop=False)
        lig = dict(levier=L, stops=ns, liquidations=nl, liquidations_sans_stop=nl0,
                   expo_moyenne=round(float(np.abs(expo[expo.index >= btc.DEBUT]).mean() * L), 3),
                   expo_max=round(float(np.abs(expo).max() * L), 2))
        for k, (a, b) in PERIODES.items():
            lig[k] = mesures(eq, a, b)
            lig[k + " sans stop"] = mesures(eq0, a, b)
        out["leviers"].append(lig)
        p = lambda d: ("RUINE" if d["ruine"] else f"Sh {d['sharpe']:.2f} {d['cagr']:+.0%}/an dd {d['mdd']:.0%}")
        print(f"×{L:<2} stops {ns:>3} liq {nl} (sans stop : {nl0}) expo moy {lig['expo_moyenne']:.0%} max {lig['expo_max']:.1f} | "
              + " | ".join(f"{k}: {p(lig[k])}" for k in PERIODES) + f" | sans stop 2012-26: {p(lig['2012-2026 sans stop'])}")
    with open(os.path.join(ICI, "profils.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
