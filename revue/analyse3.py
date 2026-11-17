"""Rééchantillonnage, surajustement, marge et limites de perte (ORB v6)."""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import nasdaq_donnees as N, orb
from orb import Regles as Rg, Couts as Ct
jours, rsi = pickle.load(open(os.path.join(N.CACHE,'jours.pkl'),'rb'))
rng = np.random.default_rng(12345)
scen = {"sans glissement": Ct(), "glis 1/0,5": Ct(glis_stop=1, glis_marche=0.5), "glis 2/1": Ct(glis_stop=2, glis_marche=1)}
res = {}
for nom, C in scen.items():
    for regle, R in {"v6": Rg(), "ORB nu": Rg(rsi=False, elan=False, be=0, pyr=0), "v6 sans pyramide": Rg(pyr=0)}.items():
        b = orb.backtest(jours, rsi, R, C); t = b[b.dir != 0]
        r = t.R.values
        # bootstrap iid et par blocs de 20 trades
        bs = np.array([rng.choice(r, len(r)).mean() for _ in range(5000)])
        nb = len(r) // 20; blocs = r[:nb * 20].reshape(nb, 20)
        bb = np.array([blocs[rng.integers(0, nb, nb)].mean() for _ in range(5000)])
        # sans les 10 / 20 meilleurs trades
        s = np.sort(r)
        res[(nom, regle)] = dict(n=len(r), R_moy=r.mean().round(3), IC95_iid=f"[{np.quantile(bs,.025):.3f} ; {np.quantile(bs,.975):.3f}]",
            IC95_blocs=f"[{np.quantile(bb,.025):.3f} ; {np.quantile(bb,.975):.3f}]", P_neg=round((bb <= 0).mean(), 4),
            sans_top10=s[:-10].mean().round(3), sans_top20=s[:-20].mean().round(3), sans_top2pct=s[:-int(len(r)*.02)].mean().round(3))
        if nom == "glis 1/0,5" and regle == "v6":
            t.to_pickle(os.path.join(N.CACHE, 'v6_g1_trades.pkl'))
print(pd.DataFrame(res).T.to_string())

t = pd.read_pickle(os.path.join(N.CACHE, 'v6_g1_trades.pkl')).reset_index(drop=True)
r = t.R.values
print("\nNombre d'essais indépendants N tel que le meilleur de N stratégies sans avantage atteigne le t observé (≈ exp(t²/2)) :")
for k, tv in [("v6 sans glissement", 4.88), ("v6 glis 1/0,5", 3.77), ("v6 glis 2/1", 2.34)]:
    print(f"  {k}: t={tv} -> N ≈ {np.exp(tv**2/2):,.0f}")

print("\n=== Marge : part des trades où 3 unités (départ + ajout) dépassent 90 % de la marge ===")
prix = t.entree.values; rgn = t['range'].values
for risque in [0.005, 0.01, 0.02]:
    notion3 = 3 * risque * prix / rgn          # notionnel des 3 unités ÷ capital
    lig = {f"levier {L}": f"{(notion3 / L > 0.9).mean():.0%}" for L in [5, 10, 20, 30, 50, 100]}
    print(f"risque {risque:.1%} : notionnel 3 unités médian {np.median(notion3):.1f}× le capital, max {notion3.max():.0f}× ; trop gros pour : {lig}")

print("\n=== Comptes financés : limites de perte (règles typiques, à vérifier chez ton courtier) ===")
# On rejoue la suite historique à partir de chaque trade de départ : perte maximale statique 10 % du capital de départ,
# perte journalière 5 %, objectif +8 % (phase 1) ou +5 % (phase 2).
def jeu(r, risque, lim=0.10, cible=0.08, horizon=None):
    sorties = {"objectif": 0, "perte max": 0, "ni l'un ni l'autre": 0}
    durees = []
    for s in range(len(r)):
        e = 1.0
        fin = len(r) if horizon is None else min(len(r), s + horizon)
        issue = "ni l'un ni l'autre"
        for j in range(s, fin):
            e *= 1 + risque * r[j]
            if e <= 1 - lim: issue = "perte max"; break
            if cible and e >= 1 + cible: issue = "objectif"; durees.append(j - s + 1); break
        sorties[issue] += 1
    n = len(r)
    return {k: f"{v/n:.0%}" for k, v in sorties.items()} | {"trades médians jusqu'à l'objectif": int(np.median(durees)) if durees else None}
for risque in [0.0025, 0.005, 0.01]:
    print(f"risque {risque:.2%}, phase 1 (+8 % avant −10 %) :", jeu(r, risque))
for risque in [0.005, 0.01]:
    print(f"risque {risque:.2%}, compte financé, 1 an (157 trades), −10 % :", jeu(r, risque, cible=None, horizon=157))
# pire perte d'un trade et d'une journée
print("Pires trades (R):", np.round(np.sort(r)[:5], 2))
# probabilité d'une année perdante par rééchantillonnage
ann = np.array([rng.choice(r, 157).sum() for _ in range(20000)])
print(f"Année simulée (157 trades tirés au hasard) : R total médian {np.median(ann):.0f}, P(année < 0) = {(ann<0).mean():.1%}, 5e centile {np.quantile(ann,.05):.0f} R")
