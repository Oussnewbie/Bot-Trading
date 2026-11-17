"""Étape 1 : toutes les variantes, seules et filtrées, sur BTC et ETH, en 1d, 4h et 1h, en spot et en perpétuel.

RÈGLE ÉCRITE AVANT DE LANCER (17 novembre 2026) — choix sur le BITCOIN seulement :
 - période de recherche 2018-01 -> 2022-12, période de vérification 2023-01 -> 2026-11 ;
 - « candidate » : sur la recherche, t de l'alpha >= 3 (Newey-West, rendements journaliers après coûts),
   Sharpe au-dessus de l'achat-conservation, au moins 15 trades ;
 - « confirmée » : sur la vérification BTC, alpha > 0 avec t >= 1,5, ET sur l'Ethereum (mêmes réglages, jamais servi
   à choisir), alpha > 0 avec t >= 1,5 sur 2018-2026 entier.
L'alpha est mesuré contre l'achat-conservation du même actif : il dit si le signal fait mieux que la même exposition
prise au hasard. Un signal qui « gagne » seulement parce que le bitcoin a monté a un alpha nul.
Sortie : sorties/variantes.csv (toutes les variantes, les perdantes aussi).
"""
import os
import sys
import time
from multiprocessing import Pool

import pandas as pd

import moteur as M
import signaux as S

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, "sorties")
PERIODES = {"R": M.RECHERCHE, "V": M.VALIDATION,
            "T": (pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2026-11-17", tz="UTC"))}


def un(args):
    actif, tf = args
    t0 = time.time()
    ctx = S.contexte(actif, tf)
    banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
    base = S.tous(ctx)
    fil = S.filtres(ctx)
    lignes = []
    for nom, pos in base.items():
        for fn, f in [("", None)] + list(fil.items()):
            p = pos if f is None else S.filtrer(pos, f)
            for mode in ("spot", "perp"):
                res = banc.evaluer(p.values, mode)
                ligne = dict(actif=actif, tf=tf, mode=mode, famille=nom.split("/")[0], variante=nom, filtre=fn)
                for per, r in res.items():
                    if r:
                        for k, v in r.items():
                            ligne[f"{per}_{k}"] = float(v)
                lignes.append(ligne)
    bh = banc.achat_conservation()
    print(f"{actif} {tf}: {len(lignes)} évaluations en {time.time() - t0:.0f} s", flush=True)
    return lignes, {(actif, tf, per): v for per, v in bh.items()}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    taches = [(a, tf) for a in ("BTC", "ETH") for tf in ("1d", "4h", "1h")]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 3) as pool:
        res = pool.map(un, taches)
    df = pd.DataFrame([l for r, _ in res for l in r])
    df.to_csv(os.path.join(OUT, "variantes.csv.gz"), index=False, float_format="%.4f")
    bh = pd.DataFrame({k: v for _, b in res for k, v in b.items()}).T
    bh.index.names = ["actif", "tf", "periode"]
    bh.to_csv(os.path.join(OUT, "achat-conservation.csv"), float_format="%.4f")
    print(len(df), "lignes")
