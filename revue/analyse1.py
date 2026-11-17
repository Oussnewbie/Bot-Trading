import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import nasdaq_donnees as N, orb
jours, rsi = pickle.load(open(os.path.join(N.CACHE,'jours.pkl'),'rb'))
from orb import Regles as Rg, Couts as Ct
def run(R=Rg(), C=Ct()): return orb.backtest(jours, rsi, R, C)
base = run()
print(base[base.dir!=0].nsmallest(5,"R")[["jour","dir","entree","stop0","range","R","pyr","raison","unites","sortie"]].to_string())
t = base[base.dir!=0].copy(); t["pyr"]=t.pyr.astype(bool); t["be"]=t.be.astype(bool)
print("Distribution du R (base) :", t.R.describe(percentiles=[.05,.25,.5,.75,.95,.99]).round(2).to_dict())
print("Somme des R par type : pyramide", round(t[t.pyr].R.sum(),1), "n", t.pyr.sum(), "| sans pyramide", round(t[~t.pyr].R.sum(),1))
print("Top 10 trades = ", round(t.R.nlargest(10).sum(),1), "R ; top 20 =", round(t.R.nlargest(20).sum(),1), "R ; total", round(t.R.sum(),1))
print("\nPar année (base):")
print(t.groupby(t.jour.dt.year).R.agg(['count','mean','sum']).round(2))
print("\nPar sens:", t.groupby('dir').R.agg(['count','mean','sum']).round(2).to_dict())
print("glissement d'entrée (gap au-delà du niveau), points:", t.glis_entree.describe().round(2).to_dict())
print("range points médian par année:", t.groupby(t.jour.dt.year)['range'].median().round(1).to_dict())
configs = {
 "ORB nu (sans filtre, sans BE, sans pyramide)": Rg(rsi=False, elan=False, be=0, pyr=0),
 "ORB nu + BE 1,5R": Rg(rsi=False, elan=False, pyr=0),
 "ORB nu + pyramide": Rg(rsi=False, elan=False),
 "Filtres seuls (sans BE ni pyramide)": Rg(be=0, pyr=0),
 "Filtres + BE (sans pyramide)": Rg(pyr=0),
 "Filtres + pyramide (sans BE)": Rg(be=0),
 "v6 complet": Rg(),
 "v6, RSI seul": Rg(elan=False),
 "v6, élan seul": Rg(rsi=False),
 "v6, élan >= et 2 bougies (EA)": Rg(elan_strict=False, elan_min_bougies=2),
 "v6, pas d'ajout sur la bougie d'entrée": Rg(pyr_bougie_entree=False),
}
rows={}
for k,R in configs.items():
    rows[k]=orb.resume(run(R))
print(pd.DataFrame(rows).T[['n','R_moy','t_stat','R_total','gagnants','dd_R','serie_pertes','pyr','cagr_05']].to_string())
