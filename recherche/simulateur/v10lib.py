"""Bibliotheque de la session 4 : la strategie rejouee comme le robot la jouerait, avec un STOP ELARGI (k fois la distance normale,
lots divises par k : le risque par trade reste 1R), un objectif eventuel, et plusieurs definitions de la regle memoire.
Avec k = 1 et la memoire « propre » on retrouve exactement la V9 (verifie dans 73_profils.py).
Entrees : A (cassure v6), B (repli VWAP), D1..Dn (continuations). 1R = la somme risquee par A."""
# (archive : ajout du dossier des scripts du bac a sable dans sys.path)
import numpy as np, pandas as pd, moteur as M, v9lib as L

def strategie(J, k=1.0, tgt=0.0, be=1.5, pyr=2.0, mem='propre', mem_seuil=0.05, avec_B=True, nD=3, valid=10, flat=950, flat_court=765, T=None, d_cond='A_ouvert'):
    """d_cond : 'A_ouvert' = les continuations ne sont armees que si A est encore ouvert (V9) ; 'range_intact' = en plus, l'autre bord du
    range ne doit pas avoir ete touche depuis la cassure (c'est le stop de la V9 : avec un stop elargi, A reste ouvert bien plus longtemps)."""
    D = J.D; a = J.a
    if T is None: T = L.orb_v6(J)                       # signaux et entrees de la cassure v6 (les regles d'entree ne changent pas)
    G = T[~(J.FOMC[T.j.values] | D.court[T.j.values])]
    rec = []; saute = False
    for g in G.itertuples():
        if saute:
            saute = False; continue
        j = int(g.j); s = int(g.sens); ie = int(g.ie); E = g.entree; rng = g.range; d1 = D.d1[j]; slip = J.slip_j[j]
        niv = g.orh if s == 1 else g.orl; autre = g.orl if s == 1 else g.orh; fm = flat_court if D.court[j] else flat
        # ---- A : meme entree, stop a k ranges du niveau de cassure
        stop = niv - s * k * rng
        x = M.sim_trade(*a, ie, d1, 10**9, fm, s, 0.0, stop, k * rng, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, E)
        rA = x[1]; ixA = int(x[3])
        rec.append(dict(j=j, comp='A', sens=s, ie=ie, ix=ixA, E=E, px=x[5], stop=stop, r=rA, r_propre=rA, risque=1.0, lots=1.0 / k, sortie=M.NOMS_SORTIE[x[0]], pyramide=int(x[8])))
        saute = (rA > mem_seuil) if mem == 'propre' else (g.r > 0.05) if mem == 'v9' else False
        # ---- B : repli sur le VWAP (signal inchange), stop k fois plus loin
        if avec_B:
            i_e, stp, inval = L.repli_vwap(D.minute, D.bo, D.bh, D.bl, D.bc, J.vwap, ie, d1, s, autre, 840, 0.1 * rng, False)
            if i_e >= 0:
                Eb = (D.ao[i_e] + slip) if s == 1 else (D.bo[i_e] - slip); d0 = s * (Eb - stp)
                if d0 > 0:
                    risque = min(1.0, d0 / rng); stopb = Eb - s * k * d0
                    xb = M.sim_trade(*a, i_e, d1, 10**9, flat, s, 0.0, stopb, k * d0, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, Eb)
                    rec.append(dict(j=j, comp='B', sens=s, ie=int(i_e), ix=int(xb[3]), E=Eb, px=xb[5], stop=stopb, r=xb[1] * risque, r_propre=xb[1], risque=risque, lots=risque * rng / (k * d0), sortie=M.NOMS_SORTIE[xb[0]], pyramide=int(xb[8])))
        # ---- D : continuations, tant que A (avec son stop elargi) est ouvert
        for n in range(nD):
            t0 = 575 + 5 * n; a0 = D.idx_minute(j, t0); b = D.idx_minute(j, t0 + 5)
            if b <= a0 or b >= d1 - 1 or D.minute[a0] >= t0 + 5 or b - a0 < 3 or ie >= b or ixA < b: continue
            if d_cond == 'range_intact' and ((s == 1 and D.bl[ie:b].min() <= autre) or (s == -1 and D.ah[ie:b].max() >= autre)): continue
            bh = D.bh[a0:b].max(); bl = D.bl[a0:b].min(); br = bh - bl
            if br <= 0: continue
            n_in = bh if s == 1 else bl; n_autre = bl if s == 1 else bh
            y = M.sim_trade(*a, b, d1, t0 + 5 + valid, flat, s, n_in, n_autre, br, 5, 0.0, 0.0, 0.0, 1.0, 0.0, slip, False, True, 0.0, False, 0.0)   # sert seulement a trouver l'entree
            if y[2] < 0: continue
            ied = int(y[2]); Ed = y[4]; stopd = n_in - s * k * br; risque = min(1.0, br / rng)
            xd = M.sim_trade(*a, ied, d1, 10**9, flat, s, 0.0, stopd, k * br, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, Ed)
            rec.append(dict(j=j, comp=f'D{n + 1}', sens=s, ie=ied, ix=int(xd[3]), E=Ed, px=xd[5], stop=stopd, r=xd[1] * risque, r_propre=xd[1], risque=risque, lots=risque * rng / (k * br), sortie=M.NOMS_SORTIE[xd[0]], pyramide=int(xd[8])))
    X = pd.DataFrame(rec)
    if len(X): X['date'] = D.dates[X.j.values]; X['annee'] = D.annee[X.j.values]
    return X

def bilan(X, na=None):
    if len(X) == 0: return dict(trades=0)
    jr = X.groupby('j').r.sum().values; ya = X.groupby('annee').r.sum(); d = L.dd(jr)
    pertes = 0; w = 0
    for v in jr:
        pertes = pertes + 1 if v < -0.05 else 0; w = max(w, pertes)
    return dict(trades=len(X), reussite_pct=round(100 * (X.r > 0.05).mean(), 1), stops_pleins_pct=round(100 * (X.r_propre <= -0.9).mean(), 1), gain_moyen=round(X.r.mean(), 3), total=round(X.r.sum(), 0), pire_baisse=round(d, 0),
                gain_sur_baisse=round(X.r.sum() / d, 1) if d > 0 else np.nan, t=round(jr.mean() / jr.std(ddof=1) * np.sqrt(len(jr)), 2) if len(jr) > 2 and jr.std() > 0 else np.nan,
                annees_pos=f"{int((ya > 0).sum())}/{len(ya)}", jours_gagnants_pct=round(100 * (jr > 0.05).mean(), 1), jours_perdants_suite=w, pire_jour=round(jr.min(), 1))
