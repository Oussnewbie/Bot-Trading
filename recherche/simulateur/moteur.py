"""Moteur de simulation a la minute (M1, bid et ask) pour le Nasdaq CFD.
- Les bougies M5 (ou M3, M1) sont reconstruites a partir du M1 bid, comme dans MetaTrader.
- Achat : declenche et paye a l'ASK, stop touche par le BID. Vente : l'inverse.
- Les decisions de gestion (stop a l'entree, pyramide) se prennent a la cloture des bougies de gestion, comme dans l'EA.
- Dans une minute ou l'ordre des evenements est inconnu, on suit le chemin probable de la bougie
  (bougie haussiere : bas d'abord puis haut ; baissiere : haut d'abord puis bas), ou le pire cas si pess=True.
Aucune donnee n'est inventee : une minute absente reste absente."""
import numpy as np, pandas as pd
from sim_jit import njit          # numba, ou rien si numba manque (archive : from numba import njit)
import sim_chemins as SC
import datetime as dt

# ------------------------------------------------------------------ calendrier (memes regles que l'EA)
def _nth_dow(y, m, dow, n):   # dow : lundi = 0
    d = dt.date(y, m, 1)
    return d + dt.timedelta(days=(dow - d.weekday()) % 7 + 7 * (n - 1))
def _last_monday_may(y):
    d = dt.date(y, 5, 31)
    return d - dt.timedelta(days=d.weekday())
def _observed(d):
    return d - dt.timedelta(days=1) if d.weekday() == 5 else d + dt.timedelta(days=1) if d.weekday() == 6 else d
def _easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)
def short_day(d):
    """Jour ferie americain ou demi-seance (sortie a 12:45), calcule comme dans l'EA."""
    y = d.year
    tg = _nth_dow(y, 11, 3, 4)
    j4 = dt.date(y, 7, 4); w4 = j4.weekday()
    pre4 = j4 - dt.timedelta(days=1) if 1 <= w4 <= 4 else j4 - dt.timedelta(days=2) if w4 == 5 else None
    feries = {_observed(dt.date(y, 1, 1)), _observed(dt.date(y + 1, 1, 1)), _nth_dow(y, 1, 0, 3), _nth_dow(y, 2, 0, 3),
              _easter(y) - dt.timedelta(days=2), _last_monday_may(y), _observed(dt.date(y, 6, 19)), _observed(j4),
              _nth_dow(y, 9, 0, 1), tg, _observed(dt.date(y, 12, 25))}
    return d in feries or d == tg + dt.timedelta(days=1) or d == dt.date(y, 12, 24) or (pre4 is not None and d == pre4)

# ------------------------------------------------------------------ donnees
class Donnees:
    def __init__(self, chemin=SC.M1_NASDAQ):
        # chemin : un parquet au format du moteur, ou directement le tableau (ajout pour les tests)
        m = chemin if isinstance(chemin, pd.DataFrame) else pd.read_parquet(chemin)
        m = m[m.dow < 5].reset_index(drop=True)
        self.m = m
        self.ts = m.timestamp.values.astype(np.int64)
        self.minute = m.minute.values.astype(np.int32)
        for c in ['bo','bh','bl','bc','ao','ah','al','ac','bv']:
            setattr(self, c, m[c].values.astype(np.float64))
        # index des jours (jour de New York)
        codes, uniq = pd.factorize(m.date)
        self.jour_id = codes.astype(np.int32)
        self.dates = np.array(uniq)
        chg = np.flatnonzero(np.diff(codes)) + 1
        self.d0 = np.concatenate([[0], chg]).astype(np.int64)
        self.d1 = np.concatenate([chg, [len(m)]]).astype(np.int64)
        self.nj = len(self.dates)
        self.pydates = [dt.date.fromisoformat(x) for x in self.dates]
        self.court = np.array([short_day(d) for d in self.pydates])
        self.dow = np.array([d.weekday() for d in self.pydates])
        self.annee = np.array([d.year for d in self.pydates])

    def idx_minute(self, j, minute):
        """Premiere ligne du jour j dont la minute de New York est >= minute (ou d1 s'il n'y en a pas)."""
        a, b = self.d0[j], self.d1[j]
        return a + int(np.searchsorted(self.minute[a:b], minute, side='left'))

    def barres(self, tf):
        """Bougies bid de tf minutes sur toute l'histoire (seance et hors seance), alignees sur l'horloge."""
        k = self.ts // (tf * 60000)
        chg = np.flatnonzero(np.diff(k)) + 1
        s = np.concatenate([[0], chg]); e = np.concatenate([chg, [len(k)]])
        o = self.bo[s]; c = self.bc[e - 1]
        h = np.maximum.reduceat(self.bh, s); l = np.minimum.reduceat(self.bl, s)
        v = np.add.reduceat(self.bv, s)
        return pd.DataFrame({'ts': k[s] * tf * 60000, 'o': o, 'h': h, 'l': l, 'c': c, 'v': v,
                             'jour_id': self.jour_id[s], 'minute': (self.minute[s] // tf) * tf, 'i0': s, 'i1': e})

def rsi_wilder(c, n=14):
    """RSI de Wilder (celui de MetaTrader et de TradingView)."""
    d = np.diff(c, prepend=c[0])
    g = np.where(d > 0, d, 0.0); p = np.where(d < 0, -d, 0.0)
    ag = np.empty(len(c)); ap = np.empty(len(c)); ag[:] = np.nan; ap[:] = np.nan
    if len(c) <= n: return ag
    ag[n] = g[1:n + 1].mean(); ap[n] = p[1:n + 1].mean()
    return _rsi_loop(g, p, ag, ap, n)
@njit(cache=True)
def _rsi_loop(g, p, ag, ap, n):
    out = np.empty(len(g)); out[:] = np.nan
    for i in range(n + 1, len(g)):
        ag[i] = (ag[i - 1] * (n - 1) + g[i]) / n
        ap[i] = (ap[i - 1] * (n - 1) + p[i]) / n
    for i in range(n, len(g)):
        out[i] = 100.0 if ap[i] == 0 else 100.0 - 100.0 / (1.0 + ag[i] / ap[i])
    return out

# ------------------------------------------------------------------ simulation d'un trade
# codes de sortie
S_AUCUN, S_STOP, S_BE, S_LOCK, S_FIN, S_TP, S_BLOQUE, S_PAS_CASSURE, S_TRAIL, S_BE_MARCHE = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

@njit(cache=True)
def sim_trade(minute, bo, bh, bl, bc, ao, ah, al, ac, i0, d1, fin_entree, flat_min, sens, niv_in, niv_sl, rng,
              tf, be_R, pyr_R, pyr_size, pyr_gap, tgt_R, slip, pess, annule_si_bloque, trail_R, entree_marche, prix_force=0.0):
    """Simule un trade du jour. prix_force > 0 : ordre limite execute a ce prix dans la minute i0 (sans glissement). sens = +1 achat, -1 vente. niv_in = niveau de l'ordre stop d'entree, niv_sl = stop initial.
    rng = valeur de 1R en points (denominateur du resultat). tf = duree des bougies de gestion (minutes).
    be_R : stop a l'entree des que +be_R atteint (0 = non). pyr_* : pyramide (0 = non). tgt_R : objectif (0 = non).
    trail_R : stop suiveur a trail_R sous le plus haut des bougies closes (0 = non). entree_marche : entrer tout de suite a i0.
    Retourne (code, R, i_entree, i_sortie, prix_entree, prix_sortie, mfe_R, mae_R, pyramide, be)."""
    # ---------------- entree
    ie = -1; E = 0.0
    i = i0
    stop_meme_minute = False
    while i < d1 and minute[i] < fin_entree and minute[i] < flat_min:
        if prix_force > 0.0:
            ie = i; E = prix_force
            stop_meme_minute = (bl[i] <= niv_sl) if sens == 1 else (ah[i] >= niv_sl)
            break
        if entree_marche:
            ie = i; E = (ao[i] + slip) if sens == 1 else (bo[i] - slip)
            break
        if sens == 1:
            ouv_au_dela = ao[i] >= niv_in
            trig = ah[i] >= niv_in
            blk = bl[i] <= niv_sl
            haussiere = bc[i] >= bo[i]
        else:
            ouv_au_dela = bo[i] <= niv_in
            trig = bl[i] <= niv_in
            blk = ah[i] >= niv_sl
            haussiere = bc[i] >= bo[i]
        if ouv_au_dela:
            ie = i; E = (ao[i] + slip) if sens == 1 else (bo[i] - slip)
            stop_meme_minute = blk
            break
        if blk and not trig:
            if annule_si_bloque:
                return S_BLOQUE, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0
            i += 1; continue
        if trig and not blk:
            ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip)
            break
        if trig and blk:
            # ordre inconnu dans la minute : chemin probable (ou pire cas)
            entree_dabord = pess or (sens == 1 and not haussiere) or (sens == -1 and haussiere)
            if entree_dabord:
                ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip)
                stop_meme_minute = True
                break
            else:
                if annule_si_bloque:
                    return S_BLOQUE, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0
                # ordres des deux cotes sans annulation : le bas a ete touche d'abord puis le haut -> entree sans stop sur cette minute
                ie = i; E = (niv_in + slip) if sens == 1 else (niv_in - slip)
                break
        i += 1
    if ie < 0:
        return S_PAS_CASSURE, 0.0, -1, i, 0.0, 0.0, 0.0, 0.0, 0, 0
    risk = abs(E - niv_sl)
    if risk <= 0: risk = rng
    stop = niv_sl
    if stop_meme_minute:
        px = (stop - slip) if sens == 1 else (stop + slip)
        r = sens * (px - E) / rng
        return S_STOP, r, ie, ie, E, px, 0.0, r, 0, 0
    be = False; pyr = False; add_px = 0.0; n_add = 0.0
    seau = minute[ie] // tf; seau_entree = seau
    if sens == 1:
        fav = bh[ie]; clo = bc[ie]
    else:
        fav = al[ie]; clo = ac[ie]
    mfe = 0.0; mae = 0.0
    meilleur = E   # plus haut (achat) / plus bas (vente) des bougies closes, pour le stop suiveur
    code = S_AUCUN; px = 0.0; isor = ie
    i = ie + 1
    while i < d1:
        if minute[i] >= flat_min:
            px = (bo[i] - slip) if sens == 1 else (ao[i] + slip)
            code = S_FIN; isor = i
            break
        s = minute[i] // tf
        if s != seau:
            # ---- cloture d'une bougie de gestion
            if pyr_R > 0 and not pyr:
                curR = sens * (clo - E) / risk
                if curR >= pyr_R:
                    mkt = ao[i] if sens == 1 else bo[i]
                    lock = mkt - sens * pyr_gap * risk
                    add_px = mkt + sens * slip
                    n_add = pyr_size; pyr = True; be = True
                    stop = lock
            if be_R > 0 and not be and seau > seau_entree:
                if (sens == 1 and fav >= E + be_R * risk) or (sens == -1 and fav <= E - be_R * risk):
                    be = True
                    if (sens == 1 and bo[i] <= E) or (sens == -1 and ao[i] >= E):
                        px = (bo[i] - slip) if sens == 1 else (ao[i] + slip)
                        code = S_BE_MARCHE; isor = i
                        break
                    stop = E
            if trail_R > 0:
                if sens == 1:
                    if fav > meilleur: meilleur = fav
                    ns = meilleur - trail_R * risk
                    if ns > stop and ns < bo[i]: stop = ns
                else:
                    if fav < meilleur: meilleur = fav
                    ns = meilleur + trail_R * risk
                    if ns < stop and ns > ao[i]: stop = ns
            seau = s
            if sens == 1:
                fav = bh[i]
            else:
                fav = al[i]
        # ---- stop et objectif dans la minute (pire cas : le stop d'abord)
        if sens == 1:
            if bl[i] <= stop:
                px = min(stop, bo[i]) - slip
                isor = i
                code = S_LOCK if pyr else (S_TRAIL if (trail_R > 0 and stop > niv_sl and stop != E) else (S_BE if be else S_STOP))
                break
            if tgt_R > 0 and bh[i] >= E + tgt_R * risk:
                px = E + tgt_R * risk; isor = i; code = S_TP
                break
            if bh[i] > fav: fav = bh[i]
            clo = bc[i]
            v = (bh[i] - E) / rng
            if v > mfe: mfe = v
            v = (bl[i] - E) / rng
            if v < mae: mae = v
        else:
            if ah[i] >= stop:
                px = max(stop, ao[i]) + slip
                isor = i
                code = S_LOCK if pyr else (S_TRAIL if (trail_R > 0 and stop < niv_sl and stop != E) else (S_BE if be else S_STOP))
                break
            if tgt_R > 0 and al[i] <= E - tgt_R * risk:
                px = E - tgt_R * risk; isor = i; code = S_TP
                break
            if al[i] < fav: fav = al[i]
            clo = ac[i]
            v = (E - al[i]) / rng
            if v > mfe: mfe = v
            v = (E - ah[i]) / rng
            if v < mae: mae = v
        i += 1
    if code == S_AUCUN:
        # les cotations s'arretent avant l'heure de sortie : sortie a la derniere cloture connue
        j = d1 - 1
        px = (bc[j] - slip) if sens == 1 else (ac[j] + slip)
        code = S_FIN; isor = j
    pnl = sens * (px - E) + n_add * sens * (px - add_px)
    return code, pnl / rng, ie, isor, E, px, mfe, mae, 1 if pyr else 0, 1 if be else 0

NOMS_SORTIE = {S_STOP: 'stop', S_BE: 'stop a l entree', S_LOCK: 'stop remonte (pyramide)', S_FIN: 'fin de journee', S_TP: 'objectif',
               S_BLOQUE: 'cote bloque touche', S_PAS_CASSURE: 'pas de cassure', S_TRAIL: 'stop suiveur', S_BE_MARCHE: 'stop a l entree (marche)'}

# ------------------------------------------------------------------ ORB generique
def prepare_orb(D, or_min=5, pre_debut=540, or_debut=570, rsi_tf=5, rsi_len=14, pre_min_barres=2):
    """Pour chaque jour : range d'ouverture, fenetre de l'elan, RSI. Retourne un DataFrame (un jour par ligne)."""
    cle = (or_min, pre_debut, or_debut, rsi_tf, rsi_len, pre_min_barres)
    cache = getattr(D, '_prep', {})
    if cle in cache: return cache[cle]
    B = D.barres(rsi_tf)
    B['rsi'] = rsi_wilder(B.c.values, rsi_len)
    # RSI a la cloture de la derniere bougie rsi_tf contenue dans le range d'ouverture
    fin_or = or_debut + or_min
    last = B[(B.minute >= or_debut) & (B.minute < fin_or)].groupby('jour_id').tail(1).set_index('jour_id')
    rows = []
    for j in range(D.nj):
        a = D.idx_minute(j, or_debut); b = D.idx_minute(j, fin_or)
        p0 = D.idx_minute(j, pre_debut)
        if b <= a or b >= D.d1[j]:
            rows.append((j, np.nan, np.nan, np.nan, np.nan, 0, np.nan, b, 0)); continue
        orh = D.bh[a:b].max(); orl = D.bl[a:b].min()
        npre = len(np.unique(D.minute[p0:a] // 5)) if a > p0 else 0
        ph = D.bh[p0:a].max() if a > p0 else np.nan; pl = D.bl[p0:a].min() if a > p0 else np.nan
        rsi = last.rsi.get(j, np.nan)
        rows.append((j, orh, orl, ph, pl, npre, rsi, b, b - a))
    R = pd.DataFrame(rows, columns=['j', 'orh', 'orl', 'ph', 'pl', 'npre', 'rsi', 'i0', 'n_or'])
    R['date'] = D.dates; R['court'] = D.court
    cache[cle] = R; D._prep = cache
    return R

def run_orb(D, or_min=5, valid_min=10, flat=950, flat_court=765, use_rsi=True, rsi_seuil_haut=50.0, rsi_seuil_bas=50.0, use_ext=True,
            tf=5, be_R=1.5, pyr_R=2.0, pyr_size=2.0, pyr_gap=1.0, tgt_R=0.0, slip=1.0, pess=False, trail_R=0.0,
            rsi_tf=5, rsi_len=14, pre_min_barres=2, masque=None, stop_frac=1.0, garder_non_trades=False):
    """ORB : ordre stop sur le bord du range d'ouverture (duree or_min), valable valid_min minutes.
    Regles v6 par defaut. stop_frac : part du range utilisee pour le stop (1 = l'autre bord). masque : jours autorises (bool)."""
    R = prepare_orb(D, or_min=or_min, rsi_tf=rsi_tf, rsi_len=rsi_len, pre_min_barres=pre_min_barres)
    fin_or = 570 + or_min
    out = []
    for r in R.itertuples(index=False):
        j = r.j
        if np.isnan(r.orh) or (masque is not None and not masque[j]): continue
        rng = r.orh - r.orl
        if rng <= 0: continue
        pre_ok = r.npre >= pre_min_barres
        okL = ((not use_rsi) or r.rsi > rsi_seuil_haut) and ((not use_ext) or (pre_ok and r.orh >= r.ph))
        okS = ((not use_rsi) or r.rsi < rsi_seuil_bas) and ((not use_ext) or (pre_ok and r.orl <= r.pl))
        if okL == okS:
            if not okL:
                if garder_non_trades: out.append((j, 0, 'filtres', np.nan, rng, r.rsi, -1, -1, np.nan, np.nan, np.nan, np.nan, 0, 0))
                continue
            # les deux cotes permis (seulement si le filtre RSI est coupe) : le premier touche est pris
            sens = 0
        else:
            sens = 1 if okL else -1
        fm = flat_court if r.court else flat
        d1 = D.d1[j]
        if sens == 0:
            # on simule les deux cotes sans annulation et on garde le premier declenche
            best = None
            for s in (1, -1):
                niv_in = r.orh if s == 1 else r.orl
                niv_sl = (niv_in - stop_frac * rng) if s == 1 else (niv_in + stop_frac * rng)
                res = sim_trade(D.minute, D.bo, D.bh, D.bl, D.bc, D.ao, D.ah, D.al, D.ac, r.i0, d1, fin_or + valid_min, fm, s, niv_in, niv_sl, rng,
                                tf, be_R, pyr_R, pyr_size, pyr_gap, tgt_R, slip, pess, False, trail_R, False)
                if res[2] >= 0 and (best is None or res[2] < best[1][2]): best = (s, res)
            if best is None:
                if garder_non_trades: out.append((j, 0, 'pas de cassure', np.nan, rng, r.rsi, -1, -1, np.nan, np.nan, np.nan, np.nan, 0, 0))
                continue
            sens, res = best
        else:
            niv_in = r.orh if sens == 1 else r.orl
            niv_sl = (niv_in - stop_frac * rng) if sens == 1 else (niv_in + stop_frac * rng)
            res = sim_trade(D.minute, D.bo, D.bh, D.bl, D.bc, D.ao, D.ah, D.al, D.ac, r.i0, d1, fin_or + valid_min, fm, sens, niv_in, niv_sl, rng,
                            tf, be_R, pyr_R, pyr_size, pyr_gap, tgt_R, slip, pess, stop_frac >= 1.0, trail_R, False)
        code, rr, ie, isor, E, px, mfe, mae, pyr, be = res
        if ie < 0:
            if garder_non_trades: out.append((j, sens, NOMS_SORTIE[code], np.nan, rng, r.rsi, -1, -1, np.nan, np.nan, np.nan, np.nan, 0, 0))
            continue
        out.append((j, sens, NOMS_SORTIE[code], rr, rng, r.rsi, ie, isor, E, px, mfe, mae, pyr, be))
    T = pd.DataFrame(out, columns=['j', 'sens', 'sortie', 'r', 'range', 'rsi', 'ie', 'isor', 'entree', 'prix_sortie', 'mfe', 'mae', 'pyramide', 'be'])
    T['date'] = D.dates[T.j.values]; T['annee'] = D.annee[T.j.values]
    return T

# ------------------------------------------------------------------ mesures
def mesures(r, par_an=None):
    r = np.asarray(r, dtype=float); n = len(r)
    if n == 0: return dict(n=0)
    eq = np.cumsum(r); pic = np.maximum.accumulate(np.maximum(eq, 0)); dd = float((pic - eq).max())
    s = 0; pire = 0
    for v in r:
        s = s + 1 if v < -0.05 else 0
        if s > pire: pire = s
    g = r[r > 0].sum(); p = -r[r < 0].sum()
    return dict(n=n, esp=float(r.mean()), total=float(r.sum()), gagnants=float(100 * (r > 0.05).mean()), stops=float(100 * (r <= -0.9).mean()),
                pf=float(g / p) if p > 0 else np.nan, dd=dd, serie=int(pire), ecart=float(r.std(ddof=1)) if n > 1 else np.nan,
                t=float(r.mean() / r.std(ddof=1) * np.sqrt(n)) if n > 1 and r.std(ddof=1) > 0 else np.nan)
