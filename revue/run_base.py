import sys, time, pickle, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import nasdaq_donnees as N, orb
t=time.time()
m1=N.m1()
jours, rsi = orb.preparer(m1)
pickle.dump((jours, rsi), open(os.path.join(N.CACHE,'jours.pkl'),'wb'))
print('prep', round(time.time()-t,1), len(jours))
t=time.time()
df=orb.backtest(jours, rsi)
print('bt', round(time.time()-t,1))
df.to_pickle(os.path.join(N.CACHE,'base.pkl'))
print(orb.resume(df))
print(df.raison.value_counts())
