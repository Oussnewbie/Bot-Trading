import os, sys; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
T = pd.read_pickle("sl_table.pkl")
SPLIT = pd.Timestamp("2022-09-01", tz="America/New_York")
T["tr"] = T.t < SPLIT
sd = T.r.std(); print("écart-type d'un trade :", round(sd, 2), "R ; R moyen", round(T.r.mean(), 3), "; stops", round(100 * T.stop.mean()), "%")
skip = {"idx","r","d","t","day","k","ex","stop","tr","fill_bar","both"}
cat = {c for c in T.columns if c not in skip and T[c].nunique() <= 5}
res = []
for c in T.columns:
    if c in skip: continue
    v = T[c].replace([np.inf, -np.inf], np.nan)
    if c in cat:
        b = v.astype("float").round(0)
    else:
        q = v[T.tr].quantile([0.2, 0.4, 0.6, 0.8]).values  # seuils fixés sur 2018-22
        b = pd.Series(np.digitize(v, np.unique(q)), index=T.index).where(v.notna())
    for lev in sorted(b.dropna().unique()):
        m = b == lev
        A, B = T[m & T.tr], T[m & ~T.tr]
        RA, RB = T[~m & T.tr], T[~m & ~T.tr]
        if len(A) < 40 or len(B) < 40: continue
        zA = (A.r.mean() - RA.r.mean()) / (sd * np.sqrt(1/len(A) + 1/len(RA)))
        zB = (B.r.mean() - RB.r.mean()) / (sd * np.sqrt(1/len(B) + 1/len(RB)))
        lo = hi = None
        if c not in cat:
            q = np.r_[-np.inf, np.unique(v[T.tr].quantile([0.2,0.4,0.6,0.8]).values), np.inf]; lo, hi = q[int(lev)], q[int(lev)+1]
        res.append(dict(var=c, seau=lev, de=lo, a=hi, n=int(m.sum()), stop=round(100*T[m].stop.mean()), rA=A.r.mean(), rB=B.r.mean(), zA=zA, zB=zB, tot=T[m].r.sum()))
R = pd.DataFrame(res)
R["zmin"] = np.where(np.sign(R.zA) == np.sign(R.zB), np.sign(R.zA) * np.minimum(R.zA.abs(), R.zB.abs()), 0)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
print("\nnombre de tests :", len(R), "-> environ", round(len(R) * 0.05), "dépasseront |z| 2 sur une moitié par hasard ; les deux moitiés au-delà de 1,5 par hasard : ~", round(len(R) * 0.134**2 / 2 * 2, 1))
print("\n=== Seaux les plus mauvais, cohérents sur les deux moitiés ===")
print(R.sort_values("zmin").head(25).round(3).to_string(index=False))
print("\n=== Seaux les plus bons, cohérents sur les deux moitiés ===")
print(R.sort_values("zmin", ascending=False).head(15).round(3).to_string(index=False))
R.to_pickle("sl_eval.pkl")
