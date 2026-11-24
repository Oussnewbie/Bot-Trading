"""Session 5 : la V10 Confort avec les quatre règles écrites à l'avance (recherche/notes/idees-strategies.md, « SESSION 5 »).

strategie_s5() est une copie de v10lib.strategie() (profil Confort : mémoire « propre », continuations « range_intact »), à laquelle
s'ajoutent les réglages des règles. Avec les réglages neutres, elle redonne exactement v10lib.strategie() : test_regles_s5.py le
vérifie sur les 3 612 trades du Nasdaq. v10lib.py n'est pas modifié.

  H1 plancher de bruit : mult = multiple_plancher(J)    (multiple du stop par jour, au lieu de k = 3)
  H2 achats seuls      : sens_permis=(1,)
  H3 R1 (VIX)          : jours_ok = jours_vix(J, vix)
  H4 G1 (gamma)        : jours_ok = jours_gex(J, gex)
  coûts S&P 500        : J.set_cout('prop', slip_pb=0.6) ; marge_B = marge_pb(J, 0.5)
"""
import numpy as np
import pandas as pd

import moteur as M
import v9lib as L
from sim_jit import njit


@njit
def repli_vwap_marge(minute, bo, bh, bl, bc, ref, dep, d1, sens, niv_inval, fin_min, tol, complet, marge):
    """v9lib.repli_vwap, avec la marge du stop de B en paramètre (1 point fixe dans l'archive)."""
    cur = minute[dep] // 5; o5 = bo[dep]; h5 = bh[dep]; l5 = bl[dep]; ph = np.nan; pl = np.nan; nb = 0
    for i in range(dep + 1, d1 - 1):
        q = minute[i] // 5
        if q != cur:
            c5 = bc[i - 1]; r = ref[i - 1]; nb += 1
            if (sens == 1 and c5 < niv_inval) or (sens == -1 and c5 > niv_inval): return -1, np.nan, 1
            if minute[i] >= fin_min: return -1, np.nan, 0
            if nb >= 2 and not np.isnan(r):
                if sens == 1 and l5 <= r + tol and c5 > r and c5 > o5:
                    return i, min(l5, pl if not np.isnan(pl) else l5) - marge, 0
                if sens == -1 and h5 >= r - tol and c5 < r and c5 < o5:
                    return i, max(h5, ph if not np.isnan(ph) else h5) + marge, 0
            ph = h5; pl = l5; cur = q; o5 = bo[i]; h5 = bh[i]; l5 = bl[i]
        else:
            if bh[i] > h5: h5 = bh[i]
            if bl[i] < l5: l5 = bl[i]
    return -1, np.nan, 0


# ───────────────────────── réglages des règles ─────────────────────────
def ranges_930(J):
    """Range de la bougie M5 de 9:30 de chaque jour (NaN si le jour n'en a pas)."""
    rng = np.full(J.nj, np.nan)
    R = J.Rp
    ok = R.orh.notna() & R.orl.notna()
    rng[R.index[ok].values] = (R.orh[ok] - R.orl[ok]).values
    rng[rng <= 0] = np.nan
    return rng


def multiple_plancher(J, k=3.0, c=2.5, n=20):
    """H1 : multiple du stop du jour j = max(k ; c × R20 / range du jour), R20 = moyenne des ranges de 9:30 des n séances
    précédentes qui en ont un (jour j exclu). Tant que R20 n'existe pas (n premières séances), le multiple reste k."""
    rng = ranges_930(J)
    s = pd.Series(rng).dropna()
    r20 = pd.Series(np.nan, index=range(J.nj))
    r20[s.index] = s.shift(1).rolling(n, min_periods=n).mean().values
    f = np.full(J.nj, float(k))
    ok = r20.notna().values & ~np.isnan(rng)
    f[ok] = np.maximum(k, c * r20.values[ok] / rng[ok])
    return f


def marge_pb(J, pb):
    """Marge du stop de B en points, par jour : pb points de base du prix de référence du jour (J.px)."""
    return J.px * pb * 1e-4


def _veille(J, serie):
    """Pour chaque jour j : la dernière valeur de la série (indexée par date « AAAA-MM-JJ ») datée AVANT le jour j."""
    s = serie.sort_index()
    dates = pd.Index(s.index)
    pos = dates.searchsorted(pd.Index(J.D.dates), side='left') - 1      # dernière date strictement avant
    vals = np.full(J.nj, np.nan)
    ok = pos >= 0
    vals[ok] = s.values[pos[ok]]
    return vals


def jours_vix(J, vix_close, n=252):
    """H3 (R1) : on trade le jour j si la clôture du VIX de la dernière séance avant j est >= la médiane des n dernières clôtures
    (celle-ci comprise). vix_close : Series indexée par date « AAAA-MM-JJ »."""
    s = vix_close.sort_index().astype(float)
    med = s.rolling(n, min_periods=n).median()
    v = _veille(J, s); m = _veille(J, med)
    return ~np.isnan(m) & (v >= m)


def jours_gex(J, gex, n=252):
    """H4 (G1) : on trade le jour j si le GEX de la dernière ligne datée avant j est < la médiane des n dernières lignes (celle-ci
    comprise). gex : Series indexée par date « AAAA-MM-JJ »."""
    s = gex.sort_index().astype(float)
    med = s.rolling(n, min_periods=n).median()
    v = _veille(J, s); m = _veille(J, med)
    return ~np.isnan(m) & (v < m)


# ───────────────────────── la stratégie ─────────────────────────
def strategie_s5(J, T=None, k=3.0, mult=None, sens_permis=(1, -1), jours_ok=None, marge_B=None, mem_seuil=1.0,
                 tgt=0.0, be=1.5, pyr=2.0, nD=3, valid=10, flat=950, flat_court=765):
    """V10 Confort (v10lib.strategie avec k=3, mem='propre', mem_seuil=1, d_cond='range_intact') et les réglages des règles :
    mult        : multiple du stop par jour (tableau de J.nj valeurs) ; None = k tous les jours
    sens_permis : sens tradés ; un signal d'un autre sens n'est pas un signal (règle mémoire non touchée)
    jours_ok    : jours tradés (tableau de booléens) ; un jour écarté n'est pas un signal (règle mémoire non touchée, comme FOMC)
    marge_B     : marge du stop de B en points, par jour ; None = 1 point (archive)"""
    D = J.D; a = J.a
    if T is None: T = L.orb_v6(J)
    garde = ~(J.FOMC[T.j.values] | D.court[T.j.values]) & np.isin(T.sens.values, sens_permis)
    if jours_ok is not None: garde &= np.asarray(jours_ok, bool)[T.j.values]
    G = T[garde]
    rec = []; saute = False
    for g in G.itertuples():
        if saute:
            saute = False; continue
        j = int(g.j); s = int(g.sens); ie = int(g.ie); E = g.entree; rng = g.range; d1 = D.d1[j]; slip = J.slip_j[j]
        kj = float(k) if mult is None else float(mult[j])
        mb = 1.0 if marge_B is None else float(marge_B[j])
        niv = g.orh if s == 1 else g.orl; autre = g.orl if s == 1 else g.orh; fm = flat_court if D.court[j] else flat
        # ---- A : même entrée, stop à kj ranges du niveau de cassure
        stop = niv - s * kj * rng
        x = M.sim_trade(*a, ie, d1, 10**9, fm, s, 0.0, stop, kj * rng, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, E)
        rA = x[1]; ixA = int(x[3])
        rec.append(dict(j=j, comp='A', sens=s, ie=ie, ix=ixA, E=E, px=x[5], stop=stop, r=rA, r_propre=rA, risque=1.0, lots=1.0 / kj, sortie=M.NOMS_SORTIE[x[0]], pyramide=int(x[8])))
        saute = rA > mem_seuil
        # ---- B : repli sur le VWAP (signal inchangé), stop kj fois plus loin
        i_e, stp, inval = repli_vwap_marge(D.minute, D.bo, D.bh, D.bl, D.bc, J.vwap, ie, d1, s, autre, 840, 0.1 * rng, False, mb)
        if i_e >= 0:
            Eb = (D.ao[i_e] + slip) if s == 1 else (D.bo[i_e] - slip); d0 = s * (Eb - stp)
            if d0 > 0:
                risque = min(1.0, d0 / rng); stopb = Eb - s * kj * d0
                xb = M.sim_trade(*a, i_e, d1, 10**9, flat, s, 0.0, stopb, kj * d0, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, Eb)
                rec.append(dict(j=j, comp='B', sens=s, ie=int(i_e), ix=int(xb[3]), E=Eb, px=xb[5], stop=stopb, r=xb[1] * risque, r_propre=xb[1], risque=risque, lots=risque * rng / (kj * d0), sortie=M.NOMS_SORTIE[xb[0]], pyramide=int(xb[8])))
        # ---- D : continuations, tant que A est ouvert et que l'autre bord du range est intact
        for n in range(nD):
            t0 = 575 + 5 * n; a0 = D.idx_minute(j, t0); b = D.idx_minute(j, t0 + 5)
            if b <= a0 or b >= d1 - 1 or D.minute[a0] >= t0 + 5 or b - a0 < 3 or ie >= b or ixA < b: continue
            if (s == 1 and D.bl[ie:b].min() <= autre) or (s == -1 and D.ah[ie:b].max() >= autre): continue
            bh = D.bh[a0:b].max(); bl = D.bl[a0:b].min(); br = bh - bl
            if br <= 0: continue
            n_in = bh if s == 1 else bl; n_autre = bl if s == 1 else bh
            y = M.sim_trade(*a, b, d1, t0 + 5 + valid, flat, s, n_in, n_autre, br, 5, 0.0, 0.0, 0.0, 1.0, 0.0, slip, False, True, 0.0, False, 0.0)
            if y[2] < 0: continue
            ied = int(y[2]); Ed = y[4]; stopd = n_in - s * kj * br; risque = min(1.0, br / rng)
            xd = M.sim_trade(*a, ied, d1, 10**9, flat, s, 0.0, stopd, kj * br, 5, be, pyr, 2.0, 1.0, tgt, slip, False, False, 0.0, False, Ed)
            rec.append(dict(j=j, comp=f'D{n + 1}', sens=s, ie=ied, ix=int(xd[3]), E=Ed, px=xd[5], stop=stopd, r=xd[1] * risque, r_propre=xd[1], risque=risque, lots=risque * rng / (kj * br), sortie=M.NOMS_SORTIE[xd[0]], pyramide=int(xd[8])))
    X = pd.DataFrame(rec)
    if len(X): X['date'] = D.dates[X.j.values]; X['annee'] = D.annee[X.j.values]
    return X
