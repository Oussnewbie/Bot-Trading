"""Les familles de stratégies testées sur chaque instrument. Chaque fonction rend une liste d'ordres
(bougie d'entrée, sens, prix d'entrée glissement compris, stop, bougie de sortie au plus tard) : un trade par jour au
plus, tout est fermé en fin de séance. La gestion (stop à l'entrée, objectif, pyramide) est appliquée par banc.jouer.

Heures : minutes depuis minuit, heure de New York (570 = 9:30 ; négatif = la veille au soir).
"""
import numpy as np

import banc as B


class Contexte:
    """Un instrument, ses jours et ses indicateurs, calculés une seule fois."""

    def __init__(self, g):
        self.g = g
        self.dates = B.jours(g)
        self.rsi = B.rsi(g["BC"])
        self.atr = B.atr(g)
        self.biais = B.biais_ma200_h1(g)
        self.macd, self.macd_hist = B.macd_m15(g)
        self.cog, self.cog_sd, rang15 = B.centre_de_gravite(g)
        self.neuf15 = np.zeros(g["n"], dtype=bool)
        self.neuf15[1:] = rang15[1:] != rang15[:-1]            # première bougie M5 après la clôture d'une M15
        self.c15 = B.sur_m5(B.horizon(g, 15)[0].c.values, rang15)
        self._idx, self._apres, self._vwap = {}, {}, {}

    def idx(self, minute):
        if minute not in self._idx:
            self._idx[minute] = B.indice(self.g, self.dates, minute)
        return self._idx[minute]

    def apres(self, minute):
        if minute not in self._apres:
            self._apres[minute] = B.premier_apres(self.g, self.dates, minute)
        return self._apres[minute]

    def vwap(self, ancre):
        if ancre not in self._vwap:
            self._vwap[ancre] = B.vwap_depuis(self.g, self.idx(ancre))
        return self._vwap[ancre]


def cotes(c, filtre, a, k0, hi, lo, pre=30):
    """Les côtés permis à la bougie k0, pour un range [a, k0) de bornes hi et lo."""
    g = c.g
    permis = {1, -1}
    if "rsi" in filtre or "v4" in filtre:
        r = c.rsi[k0 - 1]
        permis &= {1} if r > 50 else {-1} if r < 50 else set()
    if "ext" in filtre or "v4" in filtre:
        n = pre // 5
        d0 = a - n
        if d0 < 0 or g["tms"][a] - g["tms"][d0] != pre * 60_000:      # la fenêtre d'avant doit être complète
            return set()
        e = set()
        if hi >= g["BH"][d0:a].max():
            e.add(1)
        if lo <= g["BL"][d0:a].min():
            e.add(-1)
        permis &= e
    if "ma200" in filtre:
        b = c.biais[k0]
        permis &= {1} if b > 0 else {-1} if b < 0 else set()
    return permis


def cassure(c, debut, fin, valable, sortie, filtre="aucun", exact=True):
    """Cassure d'un range : plus haut et plus bas des bougies de [debut, fin) ; ordre stop d'achat sur le haut et de vente
    sur le bas pendant `valable` minutes après `fin`, stop de l'autre côté du range. ORB (range court à l'ouverture) ou
    range de séance (nuit, Asie, avant-marché). Un côté bloqué par le filtre et touché d'abord annule la journée."""
    g = c.g
    BH, BL, AH, AO, BO, slip = g["BH"], g["BL"], g["AH"], g["AO"], g["BO"], g["slip"]
    i0 = c.idx(debut) if exact else c.apres(debut)
    i1, ifin = c.idx(fin), c.apres(sortie)
    nb = (fin - debut) // 5
    ordres = []
    for j in range(len(c.dates)):
        a, k0, e = i0[j], i1[j], ifin[j]
        if a < 0 or k0 < 0 or e <= k0 or k0 <= a or (exact and k0 - a != nb) or (not exact and k0 - a < nb // 2):
            continue
        hi, lo = BH[a:k0].max(), BL[a:k0].min()
        if not hi > lo:
            continue
        permis = cotes(c, filtre, a, k0, hi, lo)
        if not permis:
            continue
        for k in range(k0, min(k0 + valable // 5, e)):
            haut, bas = AH[k] >= hi, BL[k] <= lo
            if haut and 1 in permis and not (bas and -1 in permis and abs(BO[k] - lo) < abs(AO[k] - hi)):
                ordres.append((k, 1, max(hi, AO[k]) + slip, lo, e)); break
            if bas and -1 in permis:
                ordres.append((k, -1, min(lo, BO[k]) - slip, hi, e)); break
            if haut or bas:                                      # le côté bloqué a été touché d'abord
                break
    return ordres


def balayage(c, debut, fin, valable, sortie, biais=False):
    """« Prise de liquidité » (ICT / SMC) : le prix dépasse le plus haut du range [debut, fin) puis la bougie M5 clôture
    de nouveau dessous -> vente à l'ouverture suivante, stop au-dessus de la mèche. Symétrique sous le plus bas."""
    g = c.g
    BH, BL, BC, AH, AO, BO, slip = g["BH"], g["BL"], g["BC"], g["AH"], g["AO"], g["BO"], g["slip"]
    i0, i1, ifin = c.apres(debut), c.idx(fin), c.apres(sortie)
    ordres = []
    for j in range(len(c.dates)):
        a, k0, e = i0[j], i1[j], ifin[j]
        if k0 < 0 or k0 - a < 6 or e <= k0 + 1:
            continue
        hi, lo = BH[a:k0].max(), BL[a:k0].min()
        for k in range(k0, min(k0 + valable // 5, e - 1)):
            b = c.biais[k + 1]
            if BH[k] > hi and BC[k] < hi and (not biais or b < 0):
                ordres.append((k + 1, -1, BO[k + 1] - slip, AH[k], e)); break
            if BL[k] < lo and BC[k] > lo and (not biais or b > 0):
                ordres.append((k + 1, 1, AO[k + 1] + slip, BL[k], e)); break
    return ordres


def repli_rsi(c, debut, jusqu, sortie, seuil=30, stop_atr=3.0, biais=True):
    """Repli dans la tendance : biais MA200 H1 haussier et RSI14 M5 qui passe sous `seuil` -> achat à l'ouverture
    suivante, stop à `stop_atr` ATR M5. Symétrique à la vente (RSI au-dessus de 100 - seuil, biais baissier)."""
    g = c.g
    AO, BO, slip = g["AO"], g["BO"], g["slip"]
    i0, i1, ifin = c.idx(debut), c.apres(jusqu), c.apres(sortie)
    r = c.rsi
    bas = np.zeros(g["n"], dtype=bool); haut = np.zeros(g["n"], dtype=bool)
    bas[1:] = (r[1:] < seuil) & (r[:-1] >= seuil)
    haut[1:] = (r[1:] > 100 - seuil) & (r[:-1] <= 100 - seuil)
    ordres = []
    for j in range(len(c.dates)):
        a, u, e = i0[j], i1[j], ifin[j]
        if a < 0 or u <= a + 1 or e <= a + 2:
            continue
        for k in np.flatnonzero(bas[a:u - 1] | haut[a:u - 1]) + a + 1:      # signal à la clôture de k-1, entrée à k
            if k >= e:
                break
            d = 1 if bas[k - 1] else -1
            if biais and c.biais[k] * d <= 0:
                continue
            ent = AO[k] + slip if d == 1 else BO[k] - slip
            ordres.append((k, d, ent, ent - d * stop_atr * c.atr[k - 1], e)); break
    return ordres


def repli_vwap(c, ancre, debut, jusqu, sortie, biais=True):
    """Repli sur le VWAP de la séance : la bougie touche le VWAP et clôture du bon côté (au-dessus, la précédente aussi)
    -> achat à l'ouverture suivante, stop sous le plus bas de la bougie. Sens donné par le biais MA200 H1, sinon par
    la position du prix par rapport au VWAP."""
    g = c.g
    BH, BL, BC, AH, AO, BO, slip = g["BH"], g["BL"], g["BC"], g["AH"], g["AO"], g["BO"], g["slip"]
    vw, _ = c.vwap(ancre)
    i0, i1, ifin = c.idx(debut), c.apres(jusqu), c.apres(sortie)
    ordres = []
    for j in range(len(c.dates)):
        a, u, e = i0[j], i1[j], ifin[j]
        if a < 1 or u <= a + 1 or e <= a + 2:
            continue
        for k in range(a + 1, min(u, e)):
            p = k - 1
            if not vw[p] == vw[p] or not vw[p - 1] == vw[p - 1]:
                continue
            if BL[p] <= vw[p] < BC[p] and BC[p - 1] > vw[p - 1] and (not biais or c.biais[k] > 0):
                ordres.append((k, 1, AO[k] + slip, BL[p] - 0.25 * c.atr[p], e)); break
            if AH[p] >= vw[p] > BC[p] and BC[p - 1] < vw[p - 1] and (not biais or c.biais[k] < 0):
                ordres.append((k, -1, BO[k] - slip, AH[p] + 0.25 * c.atr[p], e)); break
    return ordres


def retour_vwap(c, ancre, debut, jusqu, sortie, bandes=2.0, biais=False):
    """Retour à la moyenne : clôture au-delà de `bandes` écarts-types du VWAP -> trade vers le VWAP, stop à la même
    distance de l'autre côté (l'objectif de 1R est appliqué par la gestion)."""
    g = c.g
    BC, AO, BO, slip = g["BC"], g["AO"], g["BO"], g["slip"]
    vw, sd = c.vwap(ancre)
    i0, i1, ifin = c.idx(debut), c.apres(jusqu), c.apres(sortie)
    ordres = []
    for j in range(len(c.dates)):
        a, u, e = i0[j], i1[j], ifin[j]
        if a < 1 or u <= a + 1 or e <= a + 2:
            continue
        for k in range(a + 1, min(u, e)):
            p = k - 1
            if not sd[p] > 0:
                continue
            d = 1 if BC[p] < vw[p] - bandes * sd[p] else -1 if BC[p] > vw[p] + bandes * sd[p] else 0
            if d == 0 or (biais and c.biais[k] * d <= 0):
                continue
            ent = AO[k] + slip if d == 1 else BO[k] - slip
            dist = (vw[p] - ent) * d
            if dist > 0:
                ordres.append((k, d, ent, ent - d * dist, e)); break
    return ordres


def croisement_macd(c, debut, jusqu, sortie, stop_atr=3.0, biais=True):
    """MACD (12, 26, 9) en M15 : croisement du signal à la clôture d'une M15 -> entrée à l'ouverture M5 suivante, dans
    le sens du biais MA200 H1 si demandé. Stop à `stop_atr` ATR M5."""
    g = c.g
    AO, BO, slip = g["AO"], g["BO"], g["slip"]
    i0, i1, ifin = c.idx(debut), c.apres(jusqu), c.apres(sortie)
    ordres = []
    for j in range(len(c.dates)):
        a, u, e = i0[j], i1[j], ifin[j]
        if a < 1 or u <= a or e <= a + 1:
            continue
        for k in np.flatnonzero(c.macd[a:u]) + a:
            if k >= e:
                break
            d = int(c.macd[k])
            if biais and c.biais[k] * d <= 0:
                continue
            ent = AO[k] + slip if d == 1 else BO[k] - slip
            ordres.append((k, d, ent, ent - d * stop_atr * c.atr[k - 1], e)); break
    return ordres


def retour_cog(c, debut, jusqu, sortie, bandes=2.0, biais=False):
    """Centre de gravité Belkhayate (régression polynomiale M15) : clôture M15 au-delà de `bandes` écarts-types ->
    trade vers le centre, stop à la même distance de l'autre côté."""
    g = c.g
    AO, BO, slip = g["AO"], g["BO"], g["slip"]
    i0, i1, ifin = c.idx(debut), c.apres(jusqu), c.apres(sortie)
    ecart = (c.c15 - c.cog) / np.where(c.cog_sd > 0, c.cog_sd, np.nan)
    signal = np.where(c.neuf15 & (ecart < -bandes), 1, np.where(c.neuf15 & (ecart > bandes), -1, 0))
    ordres = []
    for j in range(len(c.dates)):
        a, u, e = i0[j], i1[j], ifin[j]
        if a < 1 or u <= a or e <= a + 1:
            continue
        for k in np.flatnonzero(signal[a:u]) + a:
            if k >= e:
                break
            d = int(signal[k])
            if biais and c.biais[k] * d <= 0:
                continue
            ent = AO[k] + slip if d == 1 else BO[k] - slip
            dist = (c.cog[k] - ent) * d
            if dist > 0:
                ordres.append((k, d, ent, ent - d * dist, e)); break
    return ordres
