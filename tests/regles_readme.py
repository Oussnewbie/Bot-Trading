"""Les règles 1 à 7 du README, réécrites naïvement, jour par jour, sans rien partager avec v5_lab.py.

Ce fichier sert de contrôle : si le simulateur (v5_lab.py) et cette réécriture donnent les mêmes trades, le simulateur
applique bien la doc. Il est volontairement lent et simple : une boucle par jour, une boucle par bougie.

Conventions de prix d'un CFD (les mêmes que le README, « Différences avec TradingView ») :
  - un achat s'exécute sur l'ask, se ferme sur le bid ; une vente s'exécute sur le bid, se ferme sur l'ask ;
  - le stop d'un achat se déclenche quand le bid touche le niveau, le stop d'une vente quand l'ask le touche.
Conventions prudentes du test : sur la bougie d'entrée seul le stop peut être touché ; un stop déplacé ne vaut qu'à
partir de la bougie suivante.
"""
import numpy as np
import pandas as pd

GLISSEMENT = 0.1          # points, à chaque exécution au marché ou sur stop
OUVERTURE = 9 * 60 + 30   # 9:30
ELAN = 9 * 60             # 9:00
FIN_ORDRES = 9 * 60 + 45  # ordres valables sur les bougies de 9:35 et 9:40
SORTIE = 15 * 60 + 50     # sortie à la clôture de la dernière bougie avant 15:50


def rsi_wilder(cloture, n=14):
    """RSI de Wilder, boucle explicite (moyennes lissées de facteur 1/n, parties de zéro)."""
    c = np.asarray(cloture, dtype=float)
    out = np.full(len(c), 50.0)
    gain = perte = 0.0
    for i in range(1, len(c)):
        d = c[i] - c[i - 1]
        gain += (max(d, 0.0) - gain) / n
        perte += (max(-d, 0.0) - perte) / n
        out[i] = 50.0 if perte == 0 else 100.0 - 100.0 / (1.0 + gain / perte)
    return out


def trade_du_jour(bid, ask, rsi_930, r_sur="entree_stop"):
    """bid, ask : bougies M5 d'un seul jour de New York (colonnes o, h, l, c ; index = heure de New York).
    rsi_930 : RSI14 M5 à la clôture de la bougie de 9:30.
    r_sur : "entree_stop" = R mesuré sur la distance entrée-stop (comme v5_lab.py) ;
            "range"       = R mesuré sur le range (règle 4 du README, comme le script TradingView et l'EA).
    Renvoie None (pas de trade) ou un dictionnaire."""
    minutes = bid.index.hour * 60 + bid.index.minute
    pos = {m: k for k, m in enumerate(minutes)}
    if OUVERTURE not in pos:
        return None
    i = pos[OUVERTURE]
    avant = [k for k, m in enumerate(minutes) if ELAN <= m < OUVERTURE]
    if len(avant) < 2:
        return None
    apres = [k for k, m in enumerate(minutes) if OUVERTURE < m < SORTIE]
    if not apres:
        return None
    derniere = apres[-1]

    # règle 1 : le range
    haut, bas = bid.h.iloc[i], bid.l.iloc[i]
    # règle 2 : les deux filtres
    achat_ok = rsi_930 > 50 and haut >= bid.h.iloc[avant].max()
    vente_ok = rsi_930 < 50 and bas <= bid.l.iloc[avant].min()
    if not (achat_ok or vente_ok):
        return None
    sens = 1 if achat_ok else -1

    # règle 3 : ordres valables sur les bougies qui suivent le range, jusqu'à 9:45
    k_entree = None
    k = i + 1
    while k <= derniere and minutes[k] < FIN_ORDRES:
        casse_haut = ask.h.iloc[k] >= haut       # l'ask atteint le haut : un achat stop s'exécuterait
        casse_bas = bid.l.iloc[k] <= bas         # le bid atteint le bas : une vente stop s'exécuterait
        if (sens == 1 and casse_haut) or (sens == -1 and casse_bas):
            k_entree = k
            break
        if casse_haut or casse_bas:              # le côté bloqué est touché d'abord : ordre annulé
            return None
        k += 1
    if k_entree is None:
        return None
    k = k_entree
    if sens == 1:
        entree = max(haut, ask.o.iloc[k]) + GLISSEMENT
        stop_depart = bas
    else:
        entree = min(bas, bid.o.iloc[k]) - GLISSEMENT
        stop_depart = haut
    risque = abs(entree - stop_depart)
    diviseur = risque if r_sur == "entree_stop" else (haut - bas)
    base = dict(jour=bid.index[i].tz_localize(None).normalize(), heure=bid.index[k], sens=sens, entree=entree,
                stop=stop_depart, haut=haut, bas=bas, rsi=rsi_930, pyramide=False)

    def touche(j, niveau):       # le stop est-il touché pendant la bougie j ?
        return bid.l.iloc[j] <= niveau if sens == 1 else ask.h.iloc[j] >= niveau

    def prix_stop(j, niveau):    # prix de sortie sur stop (un trou à l'ouverture est payé)
        return (min(niveau, bid.o.iloc[j]) - GLISSEMENT) if sens == 1 else (max(niveau, ask.o.iloc[j]) + GLISSEMENT)

    # bougie d'entrée : seul le stop peut être touché (règle 4)
    if touche(k, stop_depart):
        sortie = stop_depart - sens * GLISSEMENT
        return dict(base, sortie=sortie, heure_sortie=bid.index[k], motif="stop", r=(sortie - entree) * sens / diviseur)

    stop = stop_depart
    ajout = None                 # prix de l'ajout de la pyramide
    a_l_entree = False
    meilleur = 0.0               # meilleur gain atteint, en R, bougies après celle de l'entrée

    def pyramide(j, stop):
        # règle 7 : la bougie j clôture à +2R ou plus -> ajout au marché, stop de l'ensemble 1R sous le prix de l'ajout
        cloture_r = ((bid.c.iloc[j] - entree) if sens == 1 else (entree - ask.c.iloc[j])) / risque
        if cloture_r < 2.0:
            return None, stop
        prix = (ask.c.iloc[j] + GLISSEMENT) if sens == 1 else (bid.c.iloc[j] - GLISSEMENT)
        niveau_r = max(1.0, (prix - entree) * sens / risque - 1.0)
        niveau = entree + sens * niveau_r * risque
        return prix, (max(stop, niveau) if sens == 1 else min(stop, niveau))

    if k < derniere:
        ajout, stop = pyramide(k, stop)

    def resultat(prix):
        pts = (prix - entree) * sens
        if ajout is not None:
            pts += (prix - ajout) * sens
        return pts / diviseur

    for j in range(k + 1, derniere + 1):
        if touche(j, stop):
            px = prix_stop(j, stop)
            motif = "stop" if stop == stop_depart else "stop remonté"
            return dict(base, sortie=px, heure_sortie=bid.index[j], motif=motif, r=resultat(px), pyramide=ajout is not None)
        gain = ((bid.h.iloc[j] - entree) if sens == 1 else (entree - ask.l.iloc[j])) / risque
        meilleur = max(meilleur, gain)
        # règle 5 : stop au prix d'entrée dès +1,5R, valable à partir de la bougie suivante
        if not a_l_entree and meilleur >= 1.5:
            a_l_entree = True
            stop = max(stop, entree) if sens == 1 else min(stop, entree)
        if ajout is None and j < derniere:
            ajout, stop = pyramide(j, stop)
    # règle 6 : sortie à la clôture de la dernière bougie avant 15:50
    px = (bid.c.iloc[derniere] - GLISSEMENT) if sens == 1 else (ask.c.iloc[derniere] + GLISSEMENT)
    return dict(base, sortie=px, heure_sortie=bid.index[derniere], motif="fin", r=resultat(px), pyramide=ajout is not None)


def tous_les_trades(bid, ask, r_sur="entree_stop"):
    """bid, ask : toutes les bougies M5 (index en heure de New York). Renvoie un tableau, un trade par ligne."""
    rsi = pd.Series(rsi_wilder(bid.c.values), index=bid.index)
    jours = bid.index.tz_localize(None).normalize()
    lignes = []
    for jour, b in bid.groupby(jours):
        a = ask.loc[b.index]
        m = b.index.hour * 60 + b.index.minute
        if OUVERTURE not in set(m):
            continue
        t = trade_du_jour(b, a, float(rsi.loc[b.index[list(m).index(OUVERTURE)]]), r_sur)
        if t:
            lignes.append(t)
    return pd.DataFrame(lignes)
