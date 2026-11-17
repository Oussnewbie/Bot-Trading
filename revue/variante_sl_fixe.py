"""Variante demandée : mêmes entrées que l'ORB v6 (range de 9:30, filtres RSI et élan, ordres stop jusqu'à 9:45, côté bloqué),
puis stop FIXE à N points de l'entrée et objectif à k × N (RR 1 / 1,5 / 2 / 2,5), sortie à 15:50 (12:45 les jours courts)
si ni l'un ni l'autre n'est touché. Pas de stop à l'entrée ni de pyramide.

Exécution comme orb.py (modèle EA, M1 bid/ask Dukascopy) :
 - achat : stop touché quand le BID <= stop (prix min(stop, bid d'ouverture) - glissement), objectif quand le BID >= objectif
   (ordre limite : pas de glissement) ; vente : symétrique sur l'ASK ;
 - stop et objectif touchés dans la même minute : on suppose le STOP (pessimiste), et on les compte.
Témoins : même gestion avec le sens inversé, et en achetant toujours (toujours à la cassure du high, sans filtre de sens).
R = N points (1R = la distance du stop).
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nasdaq_donnees as N  # noqa: E402
import orb  # noqa: E402
from orb import Couts as Ct, Regles as Rg  # noqa: E402


def gerer(x, jour, d, i0, px_e, sl_pts, rr, glis_stop, glis_marche, court):
    mins = (x.index.hour * 60 + x.index.minute).values
    bo, bh, bl, bc = x.bo.values, x.bh.values, x.bl.values, x.bc.values
    ao, ah, al, ac = x.ao.values, x.ah.values, x.al.values, x.ac.values
    t_sortie = orb._hm("12:45" if court else "15:50")
    stop = px_e - d * sl_pts
    obj = px_e + d * rr * sl_pts if rr else None
    amb = 0
    i = i0
    while i < len(mins) and mins[i] < t_sortie:
        if d == 1:
            s_hit = bl[i] <= stop
            o_hit = obj is not None and bh[i] >= obj
        else:
            s_hit = ah[i] >= stop
            o_hit = obj is not None and al[i] <= obj
        if s_hit and o_hit:
            amb += 1
        if s_hit:
            if d == 1:
                px = (stop if i == i0 else min(stop, bo[i])) - glis_stop
            else:
                px = (stop if i == i0 else max(stop, ao[i])) + glis_stop
            return d * (px - px_e) / sl_pts, "stop", amb
        if o_hit:
            if d == 1:
                px = obj if i == i0 else max(obj, bo[i])
            else:
                px = obj if i == i0 else min(obj, ao[i])
            return d * (px - px_e) / sl_pts, "objectif", amb
        i += 1
    j = i - 1
    px = (bc[j] - glis_marche) if d == 1 else (ac[j] + glis_marche)
    return d * (px - px_e) / sl_pts, "15:50", amb


def entrees(jours, rsi, regles, glis_stop):
    """Les entrées du jour selon les règles v6 (ou une variante), via orb.un_jour sans gestion."""
    out = []
    R = Rg(**{**regles.__dict__, "be": 0, "pyr": 0})
    for jour, x in jours.items():
        if jour.weekday() >= 5:
            continue
        a = orb.un_jour(jour, x, rsi, R, Ct(glis_stop=glis_stop))
        if a["dir"] == 0:
            continue
        mins = (x.index.hour * 60 + x.index.minute).values
        i0 = int(np.where(mins == a["t_entree"])[0][0])
        out.append((jour, x, a["dir"], i0, a["entree"], a["court"], a["prix"]))
    return out


def tester(E, sl, rr, glis_stop, glis_marche, sens=1, prop=None):
    lignes = []
    for jour, x, d, i0, px_e, court, prix in E:
        dd = d * sens
        sl_pts = sl if prop is None else prop * px_e
        r, raison, amb = gerer(x, jour, dd, i0, px_e, sl_pts, rr, glis_stop, glis_marche, court)
        lignes.append(dict(jour=jour, dir=dd, R=r, raison=raison, amb=amb, sl_pct=sl_pts / px_e))
    return pd.DataFrame(lignes)


def resume(t):
    r = t.R.values
    eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    s = 0; pire = 0
    for v in r:
        s = s + 1 if v < -0.05 else 0
        pire = max(pire, s)
    ans = (t.jour.iloc[-1] - t.jour.iloc[0]).days / 365.25
    cap = np.prod(1 + 0.005 * r)
    return dict(n=len(r), R_moy=round(r.mean(), 3), t=round(r.mean() / r.std(ddof=1) * np.sqrt(len(r)), 2),
                R_total=round(r.sum(), 1), stops=f"{(t.raison == 'stop').mean():.0%}", objectifs=f"{(t.raison == 'objectif').mean():.0%}",
                fin_jour=f"{(t.raison == '15:50').mean():.0%}", gagnants=f"{(r > 0.05).mean():.0%}", pire_baisse_R=round(dd, 1),
                serie=pire, capital_an_05=f"{cap ** (1 / ans) - 1:+.1%}", ambigus=int((t.amb > 0).sum()))


if __name__ == "__main__":
    jours, rsi = pickle.load(open(os.path.join(N.CACHE, "jours.pkl"), "rb"))
    pd.set_option("display.width", 250)
    for gs, gm in [(0, 0), (1, 0.5), (2, 1)]:
        print(f"\n===== Glissement {gs} pt par ordre stop, {gm} pt au marché (spread Dukascopy compris) =====")
        E = entrees(jours, rsi, Rg(), gs)
        Eall = entrees(jours, rsi, Rg(rsi=False, elan=False), gs)
        Elong = entrees(jours, rsi, Rg(rsi=False, elan=False, cotes="achat"), gs)
        rows = {}
        for rr in [1, 1.5, 2, 2.5, None]:
            nom = f"RR {rr}" if rr else "sans objectif (15:50)"
            rows[f"v6, SL 200, {nom}"] = resume(tester(E, 200, rr, gs, gm))
        for rr in [1, 2]:
            rows[f"TÉMOIN sens inversé, SL 200, RR {rr}"] = resume(tester(E, 200, rr, gs, gm, sens=-1))
            rows[f"TÉMOIN sans filtre, SL 200, RR {rr}"] = resume(tester(Eall, 200, rr, gs, gm))
            rows[f"TÉMOIN achat seul sans filtre, SL 200, RR {rr}"] = resume(tester(Elong, 200, rr, gs, gm))
        for rr in [1, 1.5, 2, 2.5]:
            rows[f"v6, SL 0,8 % du prix, RR {rr}"] = resume(tester(E, None, rr, gs, gm, prop=0.008))
        print(pd.DataFrame(rows).T.to_string())
        if gs == 1:
            t = tester(E, 200, 2, gs, gm)
            print("\nSL 200 / RR 2, par année (R moyen) :", t.groupby(t.jour.dt.year).R.mean().round(2).to_dict())
            t["pct"] = t.sl_pct * 100
            print("200 points = ce % du prix, par année :", t.groupby(t.jour.dt.year).pct.mean().round(2).to_dict())
            # le « biais » : part des jours où le prix de 15:50 est du bon côté de l'entrée
            for nom, EE, sens in [("v6", E, 1), ("sans filtre", Eall, 1), ("achat seul", Elong, 1)]:
                ok = []
                for jour, x, d, i0, px_e, court, prix in EE:
                    mins = (x.index.hour * 60 + x.index.minute).values
                    j = np.where(mins < orb._hm("12:45" if court else "15:50"))[0][-1]
                    ok.append(np.sign((x.bc.values[j] - px_e) * d) > 0)
                print(f"Bon sens à 15:50 ({nom}) : {np.mean(ok):.1%} des {len(ok)} jours")
