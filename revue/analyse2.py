"""Sensibilité de l'ORB v6 : coûts, réglages voisins, période, date de départ."""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import nasdaq_donnees as N, orb
from orb import Regles as Rg, Couts as Ct
jours, rsi = pickle.load(open(os.path.join(N.CACHE,'jours.pkl'),'rb'))
def run(R=Rg(), C=Ct(), r=None): return orb.backtest(jours, rsi if r is None else r, R, C)
cols=['n','R_moy','t_stat','R_total','gagnants','dd_R','serie_pertes','pyr','cagr_05']
out={}
print("=== COÛTS (règles v6) ===")
rows={}
for gs in [0,0.5,1,2,3,5]:
    for gm in [0, 1]:
        rows[f"glis stop {gs} / marché {gm}"]=orb.resume(run(C=Ct(glis_stop=gs, glis_marche=gm)))
for e in [1,2,4]:
    rows[f"spread +{e} pt"]=orb.resume(run(C=Ct(spread_extra=e)))
rows["glis 2/1 + spread +1 + comm 0,5"]=orb.resume(run(C=Ct(glis_stop=2, glis_marche=1, spread_extra=1, commission=0.5)))
rows["ambiguïtés pessimistes"]=orb.resume(run(C=Ct(ambigu="pessimiste")))
rows["prix milieu (TradingView) + 1,3 pt"]=orb.resume(run(C=Ct(prix="milieu", spread_extra=1.3)))
c=pd.DataFrame(rows).T[cols]; print(c.to_string()); out['couts']=c
# coût en % du range : glissement proportionnel
print("\n=== VOISINS (glissement 1 pt stop, 0,5 marché) ===")
Cb=Ct(glis_stop=1, glis_marche=0.5)
rows={}
for k,R in {
 "v6": Rg(),
 "BE 1,0": Rg(be=1.0), "BE 1,25": Rg(be=1.25), "BE 1,75": Rg(be=1.75), "BE 2,0": Rg(be=2.0), "sans BE": Rg(be=0),
 "pyr 1,5R": Rg(pyr=1.5, pyr_ecart=1.0), "pyr 1,75R": Rg(pyr=1.75), "pyr 2,5R": Rg(pyr=2.5), "pyr 3R": Rg(pyr=3.0), "sans pyr": Rg(pyr=0),
 "ajout ×1": Rg(pyr_taille=1), "ajout ×1,5": Rg(pyr_taille=1.5), "ajout ×3 (pire −2R)": Rg(pyr_taille=3),
 "écart 0,75R": Rg(pyr_ecart=0.75), "écart 1,25R": Rg(pyr_ecart=1.25), "écart 1,5R": Rg(pyr_ecart=1.5),
 "valides 1": Rg(valides=1), "valides 3": Rg(valides=3), "valides 4": Rg(valides=4), "valides 6": Rg(valides=6),

 "élan dès 9:15": Rg(pre_debut="09:15"), "élan dès 8:30": Rg(pre_debut="08:30"), "élan dès 9:25": Rg(pre_debut="09:25"),
 "sortie 15:00": Rg(sortie="15:00"), "sortie 15:30": Rg(sortie="15:30"), "sortie 15:55": Rg(sortie="15:55"), "sortie 12:00": Rg(sortie="12:00"),
 "range 10 min": Rg(or_min=10), "range 15 min": Rg(or_min=15),
 "achats seuls": Rg(cotes="achat"), "ventes seules": Rg(cotes="vente"),
}.items():
    rows[k]=orb.resume(run(R, Cb))
for L in [7, 10, 21, 28]:
    _, r2 = orb.preparer(pd.read_pickle(os.path.join(N.CACHE,'nas100_m1.pkl')), rsi_len=L)
    rows[f"RSI {L}"]=orb.resume(run(Rg(), Cb, r2))
for th in [45, 55]:
    rows[f"RSI seuil {th} (asymétrique)"]=orb.resume(run(Rg(rsi_seuil=th), Cb))
v=pd.DataFrame(rows).T[cols]; print(v.to_string()); out['voisins']=v
# RSI à 45/55 : zone neutre
print("\n=== PAR ANNÉE ET SOUS-PÉRIODES (glissement 1/0,5) ===")
b=run(C=Cb); b.to_pickle(os.path.join(N.CACHE,'v6_g1.pkl'))
t=b[b.dir!=0].copy()
y=t.groupby(t.jour.dt.year).R.agg(['count','mean','sum']); y['t']=t.groupby(t.jour.dt.year).R.apply(lambda r: r.mean()/r.std()*np.sqrt(len(r)))
print(y.round(2).to_string()); out['annees']=y
nu=run(Rg(rsi=False, elan=False, be=0, pyr=0), Cb); tn=nu[nu.dir!=0]
print("ORB nu par année:", tn.groupby(tn.jour.dt.year).R.mean().round(3).to_dict())
# date de départ : résultat sur 12 et 24 mois glissants
t=t.set_index('jour')
m=t.R.resample('ME').sum()
for w in [6,12,24]:
    r=m.rolling(w).sum().dropna()
    print(f"Somme de R sur {w} mois glissants : min {r.min():.1f}, 5e centile {r.quantile(.05):.1f}, médiane {r.median():.1f}, part < 0 : {(r<0).mean():.0%}")
pickle.dump(out, open(os.path.join(N.CACHE,'analyse2.pkl'),'wb'))
