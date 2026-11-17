"""Backtest indépendant du bot BTC. Les DÉCISIONS viennent du code du bot (btc.elements + btc.position, ce que
strategie.decider applique) ; les RENDEMENTS sont recalculés ici, par une comptabilité de compte :

 - la cible (fraction signée du capital) est décidée à la clôture de chaque bougie 4h et exécutée à ce prix de clôture
   (Bitstamp ; en réel : Binance, 90 s plus tard), plus un glissement ;
 - bande : un ajustement de moins de 5 % du capital est ignoré, sauf ouvrir, fermer ou changer de sens (LISEZMOI) ;
 - l'exposition dérive avec le prix entre deux ajustements (quantité de BTC fixe) ;
 - frais par côté : comptant (achat) et perpétuel (vente, ou tout en levier > 1), réglables ;
 - financement : payé ou reçu à 00:00, 08:00 et 16:00 UTC par la position détenue à cet instant (taux réels Binance
   depuis 2020 ; avant, hypothèse réglable) ; un achat au comptant n'en paie pas ;
 - coupe-circuit : capital < 60 % de son plus haut -> tout est fermé, plus rien ensuite ;
 - levier L > 1 : cible × L en perpétuel, marge croisée ; stop de protection à mi-chemin de la liquidation, vérifié sur
   le plus haut / plus bas de la bougie 4h ; liquidation (capital à 0) si le prix touche le niveau de liquidation.
"""
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(ICI), "bitcoin"))
import btc  # noqa: E402

FIN_DONNEES = pd.Timestamp("2026-11-17 00:00", tz="UTC")   # dernière clôture journalière complète au moment de la revue


@dataclass
class Frais:
    comptant: float = 0.0010     # frais Binance comptant (maker = taker = 0,10 % au niveau VIP 0, sans BNB)
    perp: float = 0.0004         # moyenne maker 0,02 % / taker 0,05 %
    glis: float = 0.0003         # glissement / écart achat-vente par côté
    avant2017: float = 0.0035    # Bitstamp 2012-2016 : 0,25 % de frais + glissement
    fund_avant2020: float = 0.0  # taux de financement annuel supposé avant 2020 (positif : la vente reçoit)
    mult: float = 1.0            # multiplicateur de tous les coûts de transaction


def charger():
    B = btc.brutes()
    # seules les bougies clôturées au moment de la revue
    B["d1"] = B["d1"][B["d1"].index + pd.Timedelta("1D") <= FIN_DONNEES]
    B["d4"] = B["d4"][B["d4"].index + pd.Timedelta("4h") <= pd.Timestamp("2026-11-17 16:00", tz="UTC")]
    return B


def financement_par_bougie(B, idx, F: Frais):
    """Taux de financement payé à la FIN de chaque bougie 4h (00:00, 08:00, 16:00 UTC), signe Binance : >0 = l'acheteur paie."""
    f = B["fund"]
    fin = idx + pd.Timedelta("4h")
    s = pd.Series(0.0, index=idx)
    reel = f.reindex(fin).fillna(0.0).values
    s[:] = reel
    paie = np.isin(fin.hour, [0, 8, 16])
    avant = fin < pd.Timestamp("2020-01-01", tz="UTC")
    s[avant & paie] = F.fund_avant2020 / (365 * 3)
    return s.values


def simuler(pos, B, F=Frais(), bande=0.05, levier=1, coupe=0.40, stop_protection=True, debut=None, fin=None):
    d4 = B["d4"].reindex(pos.index)
    idx = pos.index
    c, h, l = d4.close.values, d4.high.values, d4.low.values
    cible = np.clip(pos.values * levier, -levier, levier)
    fund = financement_par_bougie(B, idx, F)
    perp_tout = levier > 1
    avant17 = idx < pd.Timestamp("2017-01-01", tz="UTC")
    m = np.ones(len(idx), bool)
    if debut is not None:
        m &= idx >= pd.Timestamp(debut, tz="UTC")
    if fin is not None:
        m &= idx < pd.Timestamp(fin, tz="UTC")
    ii = np.where(m)[0]
    E = 1.0; q = 0.0; pic = 1.0; arrete = False
    eq = np.full(len(idx), np.nan); expo = np.zeros(len(idx))
    couts = 0.0; volume = 0.0; n_ordres = 0; n_stop = n_liq = 0; fund_tot = 0.0
    for k, i in enumerate(ii):
        px = c[i]
        if k > 0:
            # la bougie i s'est déroulée avec la quantité q décidée à la clôture précédente
            prec = c[ii[k - 1]]
            if q != 0 and perp_tout:
                notion = abs(q) * prec
                liq_dist = max(E / notion - 0.005, 0.0)       # mouvement contraire qui efface le capital (croisée, marge de maintien 0,5 %)
                adverse = (prec - l[i]) / prec if q > 0 else (h[i] - prec) / prec
                if stop_protection and adverse >= liq_dist / 2:
                    sortie = prec * (1 - np.sign(q) * liq_dist / 2) * (1 - np.sign(q) * 0.005)
                    E += q * (sortie - prec)
                    E -= abs(q) * sortie * (F.perp + F.glis) * F.mult
                    q = 0.0; n_stop += 1
                    px_ref = None
                elif adverse >= liq_dist:
                    E = 0.0; q = 0.0; n_liq += 1
                else:
                    E += q * (px - prec)
            else:
                E += q * (px - prec)
            # financement payé à la fin de la bougie par la position détenue (perpétuel seulement)
            if q < 0 or (perp_tout and q != 0):
                ff = -q * px * fund[i]
                E += ff; fund_tot += ff
        if E <= 0:
            E = 0.0; q = 0.0; eq[i] = 0.0; arrete = True
            continue
        pic = max(pic, E)
        if not arrete and coupe and E < (1 - coupe) * pic:
            arrete = True
        T = 0.0 if arrete else cible[i]
        x = q * px / E
        change = (np.sign(T) != np.sign(x)) or (abs(T - x) >= bande)
        if change:
            dq = T * E / px - q
            # coût : comptant pour la partie achat en montage ×1, perpétuel sinon
            if perp_tout:
                taux = F.perp + F.glis
            else:
                # en ×1 : un achat au comptant, une vente en perpétuel ; un changement de sens touche les deux
                part_c = abs(max(T, 0) - max(x, 0)); part_p = abs(min(T, 0) - min(x, 0))
                tot = part_c + part_p if part_c + part_p > 0 else 1
                taux = (part_c * (F.comptant + F.glis) + part_p * (F.perp + F.glis)) / tot
            if avant17[i]:
                taux = F.avant2017
            cout = abs(dq) * px * taux * F.mult
            E -= cout; couts += cout; volume += abs(dq) * px / E; n_ordres += 1
            q = T * E / px if E > 0 else 0.0
        eq[i] = E
        expo[i] = q * px / E if E > 0 else 0.0
    s = pd.Series(eq, index=idx).dropna()
    ans = (s.index[-1] - s.index[0]).days / 365.25 if len(s) > 1 else 1
    return dict(eq=s, expo=pd.Series(expo, index=idx)[m], couts=couts, rotation_an=volume / ans, ordres_an=n_ordres / ans,
                stops=n_stop, liquidations=n_liq, fund=fund_tot, arrete=arrete)


def mesures(eq):
    j = eq.resample("1D").last().dropna()
    r = j.pct_change().dropna()
    if len(r) < 30:
        return dict(cagr=np.nan, vol=np.nan, sharpe=np.nan, mdd=np.nan, fin=np.nan)
    ans = (j.index[-1] - j.index[0]).days / 365.25
    if j.iloc[-1] <= 0:
        return dict(cagr=-1.0, vol=np.nan, sharpe=np.nan, mdd=-1.0, fin=0.0)
    return dict(cagr=(j.iloc[-1] / j.iloc[0]) ** (1 / ans) - 1, vol=r.std() * np.sqrt(365),
                sharpe=r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan,
                mdd=(j / j.cummax() - 1).min(), fin=j.iloc[-1] / j.iloc[0])


# ───────────────────────── règles de comparaison ─────────────────────────
def achat_garde(idx):
    return pd.Series(1.0, index=idx)


def ma200(B, idx):
    """Achat au comptant quand la clôture journalière est au-dessus de sa moyenne de 200 jours, sinon liquidités.
    Connue à la clôture du jour (index + 1 jour), appliquée aux bougies 4h suivantes."""
    c = B["d1"].close
    sig = (c > c.rolling(200).mean()).astype(float).where(c.rolling(200).mean().notna(), 0.0)
    return btc.caler(sig, idx).fillna(0.0)


def ma200_vol(B, E, idx, vol_cible=0.4):
    return ma200(B, idx) * (vol_cible / E["vol4"]).clip(upper=1).fillna(0)
