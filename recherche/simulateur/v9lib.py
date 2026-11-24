"""Bibliotheque de la session 3 : rejoue v6 / v7 / V8 et les variantes sur n'importe quel jeu de donnees (Dukascopy bid+ask, ou
HistData bid seul avec spread suppose), avec un cout par jour (glissement fixe en points ou proportionnel au prix), et un
simulateur generalise (pyramide a plusieurs etages, ajout sur ordre stop ou a la cloture d'une bougie).
Le moteur d'origine (moteur.py) n'est pas modifie : sim_gen reproduit sim_trade a l'identique avec ses reglages par defaut (verifie)."""
# (archive : ajout du dossier des scripts du bac a sable dans sys.path)
import numpy as np, pandas as pd, datetime as dt
from sim_jit import njit
import moteur as M, commun as C, sim_chemins as SC, sim_donnees as SD

FOMC_AVANT_2018 = ['2010-12-14',
    '2011-01-26','2011-03-15','2011-04-27','2011-06-22','2011-08-09','2011-09-21','2011-11-02','2011-12-13',
    '2012-01-25','2012-03-13','2012-04-25','2012-06-20','2012-08-01','2012-09-13','2012-10-24','2012-12-12',
    '2013-01-30','2013-03-20','2013-05-01','2013-06-19','2013-07-31','2013-09-18','2013-10-30','2013-12-18',
    '2014-01-29','2014-03-19','2014-04-30','2014-06-18','2014-07-30','2014-09-17','2014-10-29','2014-12-17',
    '2015-01-28','2015-03-18','2015-04-29','2015-06-17','2015-07-29','2015-09-17','2015-10-28','2015-12-16',
    '2016-01-27','2016-03-16','2016-04-27','2016-06-15','2016-07-27','2016-09-21','2016-11-02','2016-12-14',
    '2017-02-01','2017-03-15','2017-05-03','2017-06-14','2017-07-26','2017-09-20','2017-11-01','2017-12-13']
FOMC_TOUT = set(C.FOMC) | set(FOMC_AVANT_2018)

class Jeu:
    """Un jeu de donnees pret a etre rejoue. cout : 'fixe' (glissement = slip points) ou 'prop' (glissement = slip_pb points de base du prix)."""
    def __init__(self, source='duka', debut=None, fin=None, cout='fixe', slip=1.0, slip_pb=1.43, spread_pb=1.5, spread_fixe=None, us=True):
        tableau = isinstance(source, pd.DataFrame)   # ajout : un tableau deja au format du moteur (tests, marche prepare en memoire)
        self.source = 'tableau' if tableau else source
        if tableau:
            D = M.Donnees(source)
        elif source == 'duka':
            D = M.Donnees(SD.chemin_m1_nasdaq())   # archive : m1.parquet du bac a sable
        elif source.endswith('.parquet'):
            D = M.Donnees(source)                 # session 4 : fichier prepare par 74_marches.py (bid + ask Dukascopy, horloge ramenee a « ouverture = 9:30 »)
        else:
            D = M.Donnees(preparer_hd(source, spread_pb, spread_fixe))
        self.D = D; self.nj = D.nj
        self.FOMC = np.array([d in FOMC_TOUT for d in D.dates])
        if not us:                                # seance hors New York : ni jours FOMC ni jours feries americains
            self.FOMC[:] = False; D.court = np.zeros(D.nj, bool)
        self.ok = np.ones(D.nj, bool)
        if debut is not None: self.ok &= (D.dates >= debut)
        if fin is not None: self.ok &= (D.dates <= fin)
        # prix de reference du jour : premiere cotation du jour
        px = D.bo[D.d0]
        self.px = px
        self.set_cout(cout, slip, slip_pb)
        # prix moyen de seance (VWAP) ancre a 9:30 ; sans volume si le volume est absent
        N = len(D.bc); vw = np.full(N, np.nan); vwu = np.full(N, np.nan); tp = (D.bh + D.bl + D.bc) / 3
        sans_vol = (D.bv.sum() == 0) or not (tableau or source == 'duka' or source.endswith('.parquet'))
        for j in range(D.nj):
            s_ = D.idx_minute(j, 570); e_ = D.d1[j]
            if e_ > s_:
                vwu[s_:e_] = np.cumsum(tp[s_:e_]) / np.arange(1, e_ - s_ + 1)
                if not sans_vol:
                    cv = np.cumsum(D.bv[s_:e_]); cv[cv == 0] = np.nan
                    vw[s_:e_] = np.cumsum(tp[s_:e_] * D.bv[s_:e_]) / cv
        self.vwap = vwu if sans_vol else vw; self.vwap_sans_volume = vwu
        self.a = (D.minute, D.bo, D.bh, D.bl, D.bc, D.ao, D.ah, D.al, D.ac)
        self.Rp = M.prepare_orb(D).set_index('j')
    def set_cout(self, cout='fixe', slip=1.0, slip_pb=1.43):
        self.cout = cout
        self.slip_j = np.full(self.nj, float(slip)) if cout == 'fixe' else self.px * slip_pb * 1e-4
        return self

def preparer_hd(pair='NSXUSD', spread_pb=1.5, spread_fixe=None):
    """HistData (bid seul) -> meme format que m1.parquet, ask = bid + spread (proportionnel au prix du jour, ou fixe)."""
    f = f'{SC.DOSSIER_DONNEES}/hd_{pair}_{"fixe%g" % spread_fixe if spread_fixe is not None else "pb%g" % spread_pb}.parquet'
    import os
    if os.path.exists(f): return f
    X = pd.read_parquet(f'{SC.DOSSIER_DONNEES}/hd_{pair}.parquet')
    p0 = X.groupby('date').o.transform('first')
    sp = (spread_fixe if spread_fixe is not None else p0 * spread_pb * 1e-4)
    Y = pd.DataFrame({'timestamp': X.timestamp, 'date': X.date, 'minute': X.minute, 'annee': X.annee, 'dow': X.dow,
                      'bo': X.o, 'bh': X.h, 'bl': X.l, 'bc': X.c, 'bv': 1.0, 'ao': X.o + sp, 'ah': X.h + sp, 'al': X.l + sp, 'ac': X.c + sp, 'av': 1.0})
    Y.to_parquet(f, index=False); return f

# ------------------------------------------------------------------ simulateur generalise
@njit(cache=True)
def sim_gen(minute, bo, bh, bl, bc, ao, ah, al, ac, i0, d1, fin_entree, flat_min, sens, niv_in, niv_sl, rng,
            tf, be_R, ptrig, psize, pgap, pmode, slip, annule_si_bloque, entree_marche, pess_add, max_add_min):
    """Comme moteur.sim_trade, avec une pyramide a plusieurs etages.
    ptrig[k], psize[k], pgap[k] : l'etage k s'ajoute quand le trade atteint +ptrig[k] R (cloture d'une bougie de gestion si pmode = 0,
    ordre stop touche dans la minute si pmode = 1) ; psize[k] unites ; le stop de l'ensemble passe a pgap[k] R sous le prix d'ajout.
    Ajout sur ordre stop : si, dans la meme minute, le prix touche aussi le nouveau stop, on suit le chemin probable de la bougie
    (bougie contraire au trade = l'ajout d'abord puis le stop -> sortie ; bougie dans le sens = pas de sortie), ou le pire cas si pess_add.
    Retourne (code, R total, i_entree, i_sortie, E, prix_sortie, mfe, mae, nb_etages, be, R de l'unite de depart)."""
    ie = -1; E = 0.0; i = i0; stop_meme_minute = False
    while i < d1 and minute[i] < fin_entree and minute[i] < flat_min:
        if entree_marche:
            ie = i; E = (ao[i] + slip) if sens == 1 else (bo[i] - slip)
            break
        if sens == 1:
            ouv_au_dela = ao[i] >= niv_in; trig = ah[i] >= niv_in; blk = bl[i] <= niv_sl
        else:
            ouv_au_dela = bo[i] <= niv_in; trig = bl[i] <= niv_in; blk = ah[i] >= niv_sl
        haussiere = bc[i] >= bo[i]
        if ouv_au_dela:
            ie = i; E = (ao[i] + slip) if sens == 1 else (bo[i] - slip); stop_meme_minute = blk
            break
        if blk and not trig:
            if annule_si_bloque: return 6, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0
            i += 1; continue
        if trig and not blk:
            ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip)
            break
        if trig and blk:
            entree_dabord = pess_add or (sens == 1 and not haussiere) or (sens == -1 and haussiere)
            if entree_dabord:
                ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip); stop_meme_minute = True
                break
            else:
                if annule_si_bloque: return 6, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0
                ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip)
                break
        i += 1
    if ie < 0: return 7, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0
    risk = abs(E - niv_sl)
    if risk <= 0: risk = rng
    stop = niv_sl
    if stop_meme_minute:
        px = (stop - slip) if sens == 1 else (stop + slip); r = sens * (px - E) / rng
        return 1, r, ie, ie, E, px, 0.0, r, 0, 0, r
    be = False; npyr = len(ptrig); k = 0; pnl_add_units = 0.0; sum_add = 0.0; sum_add_px = 0.0
    seau = minute[ie] // tf; seau_entree = seau
    if sens == 1: fav = bh[ie]; clo = bc[ie]
    else: fav = al[ie]; clo = ac[ie]
    mfe = 0.0; mae = 0.0; code = 0; px = 0.0; isor = ie
    i = ie + 1
    while i < d1:
        if minute[i] >= flat_min:
            px = (bo[i] - slip) if sens == 1 else (ao[i] + slip); code = 4; isor = i
            break
        s = minute[i] // tf
        if s != seau:
            if pmode == 0 and k < npyr and minute[i] < max_add_min:
                curR = sens * (clo - E) / risk
                if curR >= ptrig[k]:
                    mkt = ao[i] if sens == 1 else bo[i]
                    stop_n = mkt - sens * pgap[k] * risk
                    if (sens == 1 and stop_n > stop) or (sens == -1 and stop_n < stop): stop = stop_n
                    apx = mkt + sens * slip
                    sum_add += psize[k]; sum_add_px += psize[k] * apx; k += 1; be = True
            if be_R > 0 and not be and seau > seau_entree:
                if (sens == 1 and fav >= E + be_R * risk) or (sens == -1 and fav <= E - be_R * risk):
                    be = True
                    if (sens == 1 and bo[i] <= E) or (sens == -1 and ao[i] >= E):
                        px = (bo[i] - slip) if sens == 1 else (ao[i] + slip); code = 9; isor = i
                        break
                    stop = E
            seau = s
            if sens == 1: fav = bh[i]
            else: fav = al[i]
        if sens == 1:
            if bl[i] <= stop:
                px = min(stop, bo[i]) - slip; isor = i
                code = 3 if k > 0 else (2 if be else 1)
                break
            # ajout sur ordre stop dans la minute (pmode = 1) : le stop d'abord (pire cas), puis l'ajout
            ajoute = False
            while pmode == 1 and k < npyr and minute[i] < max_add_min and ah[i] >= E + ptrig[k] * risk:
                lvl = E + ptrig[k] * risk; apx = max(lvl, ao[i]) + slip
                stop_n = apx - slip - pgap[k] * risk
                if stop_n > stop: stop = stop_n
                sum_add += psize[k]; sum_add_px += psize[k] * apx; k += 1; be = True; ajoute = True
            if ajoute and bl[i] <= stop and (pess_add or bc[i] < bo[i]):
                px = stop - slip; isor = i; code = 3
                break
            if bh[i] > fav: fav = bh[i]
            clo = bc[i]
            v = (bh[i] - E) / rng
            if v > mfe: mfe = v
            v = (bl[i] - E) / rng
            if v < mae: mae = v
        else:
            if ah[i] >= stop:
                px = max(stop, ao[i]) + slip; isor = i
                code = 3 if k > 0 else (2 if be else 1)
                break
            ajoute = False
            while pmode == 1 and k < npyr and minute[i] < max_add_min and bl[i] <= E - ptrig[k] * risk:
                lvl = E - ptrig[k] * risk; apx = min(lvl, bo[i]) - slip
                stop_n = apx + slip + pgap[k] * risk
                if stop_n < stop: stop = stop_n
                sum_add += psize[k]; sum_add_px += psize[k] * apx; k += 1; be = True; ajoute = True
            if ajoute and ah[i] >= stop and (pess_add or ac[i] > ao[i]):
                px = stop + slip; isor = i; code = 3
                break
            if al[i] < fav: fav = al[i]
            clo = ac[i]
            v = (E - al[i]) / rng
            if v > mfe: mfe = v
            v = (E - ah[i]) / rng
            if v < mae: mae = v
        i += 1
    if code == 0:
        j = d1 - 1
        px = (bc[j] - slip) if sens == 1 else (ac[j] + slip); code = 4; isor = j
    base = sens * (px - E)
    pnl = base + sens * (sum_add * px - sum_add_px)
    return code, pnl / rng, ie, isor, E, px, mfe, mae, k, 1 if be else 0, base / rng

NOMS = {1: 'stop', 2: 'stop a l entree', 3: 'stop remonte (pyramide)', 4: 'fin de journee', 6: 'cote bloque touche', 7: 'pas de cassure', 9: 'stop a l entree (marche)'}
PYR_V6 = (np.array([2.0]), np.array([2.0]), np.array([1.0]))
SANS_PYR = (np.zeros(0), np.zeros(0), np.zeros(0))

def orb_v6(J, pyr=PYR_V6, pmode=0, be_R=1.5, tf=5, valid_min=10, or_min=5, flat=950, flat_court=765, masque=None, use_rsi=True, use_ext=True, max_add_min=10**6, pess_add=False):
    """Tous les trades de la cassure v6 (avant memoire et exclusions), avec le cout du jeu J (par jour)."""
    D = J.D; R = M.prepare_orb(D, or_min=or_min); fin_or = 570 + or_min; out = []
    for r in R.itertuples(index=False):
        j = r.j
        if not J.ok[j] or np.isnan(r.orh) or (masque is not None and not masque[j]): continue
        rng = r.orh - r.orl
        if rng <= 0: continue
        pre_ok = r.npre >= 2
        okL = ((not use_rsi) or r.rsi > 50.0) and ((not use_ext) or (pre_ok and r.orh >= r.ph))
        okS = ((not use_rsi) or r.rsi < 50.0) and ((not use_ext) or (pre_ok and r.orl <= r.pl))
        if okL == okS: continue
        sens = 1 if okL else -1
        fm = flat_court if r.court else flat
        niv_in = r.orh if sens == 1 else r.orl; niv_sl = r.orl if sens == 1 else r.orh
        res = sim_gen(*J.a, r.i0, D.d1[j], fin_or + valid_min, fm, sens, niv_in, niv_sl, rng, tf, be_R, pyr[0], pyr[1], pyr[2], pmode, J.slip_j[j], True, False, pess_add, max_add_min)
        if res[2] < 0: continue
        out.append((j, sens, NOMS[res[0]], res[1], rng, r.rsi, res[2], res[3], res[4], res[5], res[6], res[7], res[8], res[9], res[10], r.orh, r.orl))
    T = pd.DataFrame(out, columns=['j', 'sens', 'sortie', 'r', 'range', 'rsi', 'ie', 'isor', 'entree', 'prix_sortie', 'mfe', 'mae', 'pyramide', 'be', 'r_base', 'orh', 'orl'])
    T['date'] = D.dates[T.j.values]; T['annee'] = D.annee[T.j.values]
    return T

def filtre_v7(J, T, memoire=True, seuil=0.05, col='r'):
    """Applique les regles de la v7 a la liste des cassures v6 : hors FOMC et jours courts, puis memoire (apres un trade pris gagnant, le signal suivant est saute)."""
    G = T[~(J.FOMC[T.j.values] | J.D.court[T.j.values])].reset_index(drop=True)
    if not memoire: G['pris'] = True; return G
    pris = np.ones(len(G), bool); saute = False; r = G[col].values
    for i in range(len(G)):
        if saute: pris[i] = False; saute = False
        else: saute = r[i] > seuil
    G['pris'] = pris
    return G

@njit(cache=True)
def repli_vwap(minute, bo, bh, bl, bc, ref, dep, d1, sens, niv_inval, fin_min, tol, complet):
    """Premier repli sur la reference apres la minute dep : bougie M5 qui touche la reference (a tol pres), cloture du bon cote et dans le sens.
    complet = True : le stop utilise les 2 dernieres bougies M5 completes (comme le code MQ5 / Pine)."""
    cur = minute[dep] // 5; o5 = bo[dep]; h5 = bh[dep]; l5 = bl[dep]; ph = np.nan; pl = np.nan; nb = 0
    for i in range(dep + 1, d1 - 1):
        q = minute[i] // 5
        if q != cur:
            c5 = bc[i - 1]; r = ref[i - 1]; nb += 1
            if (sens == 1 and c5 < niv_inval) or (sens == -1 and c5 > niv_inval): return -1, np.nan, 1
            if minute[i] >= fin_min: return -1, np.nan, 0
            if nb >= 2 and not np.isnan(r):
                if sens == 1 and l5 <= r + tol and c5 > r and c5 > o5:
                    return i, min(l5, pl if not np.isnan(pl) else l5) - 1.0, 0
                if sens == -1 and h5 >= r - tol and c5 < r and c5 < o5:
                    return i, max(h5, ph if not np.isnan(ph) else h5) + 1.0, 0
            ph = h5; pl = l5; cur = q; o5 = bo[i]; h5 = bh[i]; l5 = bl[i]
        else:
            if bh[i] > h5: h5 = bh[i]
            if bl[i] < l5: l5 = bl[i]
    return -1, np.nan, 0

def entree_marche(J, j, s_, i_e, stop, rng, be, pyr, comp, pmode=0, flat=950, tf=5, lots_max=1.0, risque_max=1.0, pess_add=False):
    """Entree au marche a l'ouverture de la minute i_e, stop donne ; taille plafonnee : jamais plus de lots_max fois les lots de la cassure,
    jamais plus de risque_max R. Retourne un dict (R exprime en R de la cassure du jour) ou None."""
    D = J.D; slip = J.slip_j[j]
    E = (D.ao[i_e] + slip) if s_ == 1 else (D.bo[i_e] - slip); dist = s_ * (E - stop)
    if dist <= 0: return None
    lots = min(lots_max, risque_max * rng / dist)
    if (s_ == 1 and D.bl[i_e] <= stop) or (s_ == -1 and D.ah[i_e] >= stop):
        r_own = -(dist + slip) / dist; ix = i_e; px = stop - s_ * slip; so = 'stop'; npyr = 0
    else:
        res = sim_gen(*J.a, i_e, D.d1[j], 10**9, flat, s_, 0.0, stop, dist, tf, be, pyr[0], pyr[1], pyr[2], pmode, slip, False, True, pess_add, 10**6)
        r_own = res[1]; ix = int(res[3]); px = res[5]; so = NOMS[res[0]]; npyr = res[8]
    return dict(j=j, comp=comp, sens=s_, ie=int(i_e), ix=ix, E=E, px=px, stop=stop, r=r_own * dist / rng * lots, r_propre=r_own, lots=lots, risque=dist / rng * lots, sortie=so, pyramide=npyr)

def v8(J, avec_B=True, avec_C=True, memoire=True, pyrA=PYR_V6, pyrB=PYR_V6, pyrC=SANS_PYR, T=None, h_C=600, fin_B=840, tol_B=0.1):
    """Strategy V8 : A = cassure v7 ; B = premier repli sur le VWAP ; C = entree a 10:00 si la cassure tient. Retourne la liste des trades."""
    D = J.D
    if T is None: T = orb_v6(J, pyr=pyrA)
    G = filtre_v7(J, T, memoire); G = G[G.pris]
    rec = []
    for g in G.itertuples():
        j = int(g.j); s_ = int(g.sens); rng = g.range; d1 = D.d1[j]; ie = int(g.ie)
        niv_in = g.orh if s_ == 1 else g.orl; niv_sl = g.orl if s_ == 1 else g.orh
        rec.append(dict(j=j, comp='A', sens=s_, ie=ie, ix=int(g.isor), E=g.entree, px=g.prix_sortie, stop=niv_sl, r=g.r, r_propre=g.r, lots=1.0, risque=1.0, sortie=g.sortie, pyramide=g.pyramide))
        if avec_B:
            i_e, stp, inval = repli_vwap(D.minute, D.bo, D.bh, D.bl, D.bc, J.vwap, ie, d1, s_, niv_sl, fin_B, tol_B * rng, False)
            if i_e >= 0:
                d_ = entree_marche(J, j, s_, i_e, stp, rng, 1.5, pyrB, 'B')
                if d_ is not None: rec.append(d_)
        if avec_C:
            i_e = D.idx_minute(j, h_C)
            if i_e < d1 - 1 and D.minute[i_e] <= h_C + 3 and i_e > ie and s_ * (D.bc[i_e - 1] - niv_in) > 0:
                if not ((s_ == 1 and D.bl[ie:i_e].min() <= niv_sl) or (s_ == -1 and D.ah[ie:i_e].max() >= niv_sl)):
                    d_ = entree_marche(J, j, s_, i_e, niv_sl, rng, 1.5, pyrC, 'C')
                    if d_ is not None: rec.append(d_)
    X = pd.DataFrame(rec); X['date'] = D.dates[X.j.values]; X['annee'] = D.annee[X.j.values]
    return X

# ------------------------------------------------------------------ mesures
def dd(x):
    x = np.asarray(x, float)
    if len(x) == 0: return 0.0
    eq = np.cumsum(x); return float((np.maximum.accumulate(np.maximum(eq, 0)) - eq).max())

def bilan(X, nom='', nj_an=None):
    """Mesures au niveau du jour (somme des trades du jour)."""
    if len(X) == 0: return dict(strategie=nom, trades=0)
    jr = X.groupby('j').r.sum(); x = jr.values; ya = X.groupby('annee').r.sum()
    na = X.annee.nunique()
    t = x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan
    return dict(strategie=nom, trades=len(X), jours=len(x), total=round(float(x.sum()), 1), par_trade=round(float(X.r.mean()), 3), reussite=round(float(100 * (X.r > 0.05).mean()), 1),
                pf=round(float(X.r[X.r > 0].sum() / -X.r[X.r < 0].sum()), 2) if (X.r < 0).any() else np.nan, pire_baisse=round(dd(x), 1), gain_sur_baisse=round(float(x.sum() / dd(x)), 1) if dd(x) > 0 else np.nan,
                annees_pos=f"{int((ya > 0).sum())}/{len(ya)}", pire_annee=round(float(ya.min()), 1), pire_jour=round(float(x.min()), 2), t_jour=round(float(t), 2))

def serie_jour(J, X, col='r'):
    v = np.zeros(J.nj)
    if len(X): np.add.at(v, X.j.values.astype(int), X[col].values)
    return v


# ------------------------------------------------------------------ session 3 : reservoir de « jambes » (entrees) les jours v7 et portefeuilles
def jambes(J, bougies=range(575, 615, 5), pess=False, valid=10, be=1.5, T=None, avec_BC=True, plafond_lots=True, pmode=0, cout_max=None):
    """Pour chaque jour v7 : A, B, C (comme la V8) et les entrees de continuation D (cassure de l'extreme de la bougie M5 k dans le sens de A,
    posee a la cloture de la bougie si A est entre et encore ouvert ; stop = l'autre extreme de la bougie), chacune avec et sans pyramide.
    r = resultat en R de A (R du jour). unites = lots reserves (pyramide comprise) en lots de A."""
    D = J.D
    if T is None: T = orb_v6(J, pess_add=pess, pmode=pmode)
    if cout_max is not None:
        # garde-fou : pas de trade si le cout d'un aller-retour (spread a 9:35 + 2 glissements) depasse cout_max x range. Connu a 9:35.
        i935 = J.Rp.i0.reindex(T.j.values).values.astype(int)
        T = T[((D.ao[i935] - D.bo[i935]) + 2 * J.slip_j[T.j.values]) / T.range.values <= cout_max].reset_index(drop=True)
    G = filtre_v7(J, T); G = G[G.pris]
    rec = []
    for g in G.itertuples():
        j = int(g.j); s = int(g.sens); rngA = g.range; d1 = D.d1[j]; ieA = int(g.ie); ixA = int(g.isor)
        niv_in = g.orh if s == 1 else g.orl; niv_sl = g.orl if s == 1 else g.orh
        rec.append(dict(j=j, comp='A', sens=s, ie=ieA, ix=ixA, E=g.entree, px=g.prix_sortie, stop=niv_sl, r=g.r, r_propre=g.r, lots=1.0, risque=1.0, sortie=g.sortie, unites=3.0, pyramide=g.pyramide, t0=570))
        if avec_BC:
            i_e, stp, inval = repli_vwap(D.minute, D.bo, D.bh, D.bl, D.bc, J.vwap, ieA, d1, s, niv_sl, 840, 0.1 * rngA, False)
            if i_e >= 0:
                d_ = entree_marche(J, j, s, i_e, stp, rngA, 1.5, PYR_V6, 'B', pess_add=pess, pmode=pmode)
                if d_ is not None: d_['unites'] = 3.0 * d_['lots']; d_['t0'] = int(D.minute[i_e]); rec.append(d_)
            i_e = D.idx_minute(j, 600)
            if i_e < d1 - 1 and D.minute[i_e] <= 603 and i_e > ieA and s * (D.bc[i_e - 1] - niv_in) > 0:
                if not ((s == 1 and D.bl[ieA:i_e].min() <= niv_sl) or (s == -1 and D.ah[ieA:i_e].max() >= niv_sl)):
                    d_ = entree_marche(J, j, s, i_e, niv_sl, rngA, 1.5, SANS_PYR, 'C', pess_add=pess)
                    if d_ is not None: d_['unites'] = d_['lots']; d_['t0'] = 600; rec.append(d_)
        for t0 in bougies:
            a = D.idx_minute(j, t0); b = D.idx_minute(j, t0 + 5)
            if b <= a or b >= d1 - 1 or D.minute[a] >= t0 + 5 or b - a < 3: continue
            if ieA >= b or ixA < b: continue                      # A doit etre entre ET encore ouvert a la cloture de la bougie
            bh = D.bh[a:b].max(); bl = D.bl[a:b].min(); rng = bh - bl
            if rng <= 0: continue
            n_in = bh if s == 1 else bl; n_sl = bl if s == 1 else bh
            lots = min(1.0, rngA / rng) if plafond_lots else rngA / rng
            for suff, pyr, u in (('p', PYR_V6, 3.0), ('n', SANS_PYR, 1.0)):
                res = sim_gen(*J.a, b, d1, t0 + 5 + valid, 950, s, n_in, n_sl, rng, 5, be, pyr[0], pyr[1], pyr[2], pmode, J.slip_j[j], True, False, pess, 10**6)
                if res[2] < 0: continue
                rec.append(dict(j=j, comp=f'D{t0}{suff}', sens=s, ie=int(res[2]), ix=int(res[3]), E=res[4], px=res[5], stop=n_sl, r=res[1] * rng / rngA * lots, r_propre=res[1], lots=lots,
                                risque=rng / rngA * lots, sortie=NOMS[res[0]], pyramide=int(res[8]), unites=u * lots, t0=t0))
    X = pd.DataFrame(rec); X['date'] = D.dates[X.j.values]; X['annee'] = D.annee[X.j.values]
    return X

def portefeuille(X, comps, cap=None):
    """Garde les jambes dont le type est dans comps ; si cap est donne, une jambe est refusee quand les unites reservees des jambes
    encore ouvertes + les siennes depassent cap (ordre chronologique des entrees)."""
    Z = X[X.comp.isin(comps)]
    if cap is None: return Z
    Z = Z.sort_values(['j', 'ie', 't0']); keep = np.ones(len(Z), bool)
    jv = Z.j.values; iev = Z.ie.values; ixv = Z.ix.values; uv = Z.unites.values
    ouverts = []; cur = -1
    for k in range(len(Z)):
        if jv[k] != cur: cur = jv[k]; ouverts = []
        ouverts = [(x, u) for (x, u) in ouverts if x > iev[k]]
        if sum(u for _, u in ouverts) + uv[k] > cap + 1e-9: keep[k] = False
        else: ouverts.append((ixv[k], uv[k]))
    return Z[keep]

def mesures_jour(X, nj_total=None):
    jr = X.groupby('j').r.sum(); x = jr.values; ya = X.groupby('annee').r.sum()
    pertes = 0; w = 0
    for v in x:
        pertes = pertes + 1 if v < -0.05 else 0
        w = max(w, pertes)
    d = dd(x)
    return dict(trades=len(X), total=round(float(x.sum()), 1), par_trade=round(float(X.r.mean()), 3), reussite=round(float(100 * (X.r > 0.05).mean()), 1), pire_baisse=round(d, 1), ratio=round(float(x.sum() / d), 1) if d > 0 else np.nan,
                annees_pos=int((ya > 0).sum()), pire_annee=round(float(ya.min()), 1), pire_jour=round(float(x.min()), 2), jours_perdants_suite=w,
                t=round(float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), 2), risque_moyen_jour=round(float(X.groupby('j').risque.sum().mean()), 2))
