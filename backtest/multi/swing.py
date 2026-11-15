"""Deuxième étage de la recherche : stratégies tenues plusieurs heures ou plusieurs jours (H1, H4, journalier).

Pourquoi : en M5, sur l'or, l'EUR/USD et le bitcoin, le spread pèse 10 à 30 % du risque de chaque trade ; toutes les
familles intraday y perdent. Avec des stops plus larges, le spread pèse 1 à 3 % du risque. En échange la position passe
la nuit : le courtier facture un financement (« swap ») que les données ne contiennent pas. Il est compté ici avec des
taux PRUDENTS, à vérifier chez ton courtier (FINANCEMENT, en % par an de la valeur de la position, par nuit tenue).

Moteur : une position à la fois, bougie après bougie. Signal à la clôture d'une bougie -> exécution à l'ouverture de la
suivante (achat à l'ask, vente au bid, glissement en plus). Stop vérifié dans la bougie, y compris celle de l'entrée ;
un stop suiveur n'est remonté qu'à la clôture, pour la bougie suivante. R = résultat net (financement compris) ÷ risque
de départ.

    python backtest/multi/swing.py [instrument…]      écrit sorties/variantes-swing.csv
"""
import itertools
import multiprocessing
import os
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import banc as B  # noqa: E402

SORTIES = os.path.join(ICI, "sorties")
# Financement par nuit, en % par an de la valeur de la position : (achat, vente). Hypothèses prudentes : un CFD sur
# indice ou sur l'or coûte le taux à court terme du dollar plus la marge du courtier à l'achat ; le bitcoin en CFD
# coûte très cher des deux côtés.
FINANCEMENT = {"nas100": (6.0, 1.0), "dow": (6.0, 1.0), "or": (6.0, 1.0), "eurusd": (3.0, 1.0), "bitcoin": (20.0, 10.0)}


def barres(g, minutes):
    """Bougies bid et ask de `minutes` minutes à partir du M5."""
    cle = g["tms"] // (minutes * 60_000)
    d = pd.DataFrame({k: g[k] for k in ("BO", "BH", "BL", "BC", "AO", "AH", "AL", "AC")})
    d["k"] = cle
    d["tms"] = g["tms"]
    gr = d.groupby("k", sort=True)
    h = dict(BO=gr.BO.first().values, BH=gr.BH.max().values, BL=gr.BL.min().values, BC=gr.BC.last().values,
             AO=gr.AO.first().values, AH=gr.AH.max().values, AL=gr.AL.min().values, AC=gr.AC.last().values,
             tms=gr.tms.first().values)
    h["t"] = pd.DatetimeIndex(pd.to_datetime(h["tms"], unit="ms", utc=True)).tz_convert(B.NY)
    h["n"] = len(h["BC"])
    h["slip"] = g["slip"]
    h["nom"] = g["nom"]
    c = pd.Series(h["BC"])
    pc = c.shift(1).fillna(c.iloc[0]).values
    tr = np.maximum(h["BH"] - h["BL"], np.maximum(abs(h["BH"] - pc), abs(h["BL"] - pc)))
    h["atr"] = pd.Series(tr).ewm(alpha=1 / 24, adjust=False).mean().values
    h["ma200"] = c.rolling(200).mean().values
    h["rsi14"] = B.rsi(h["BC"], 14)
    h["rsi2"] = B.rsi(h["BC"], 2)
    return h


def simuler(h, entree, dist, sortie_l=None, sortie_s=None, suiveur=None, tp=None, max_bougies=None):
    """entree[i] = +1 / -1 / 0 à la clôture de la bougie i ; dist[i] = distance du stop de départ ;
    sortie_l / sortie_s = sortie demandée à la clôture ; suiveur = stop suiveur à tant d'ATR du meilleur prix ;
    tp = objectif en R ; max_bougies = durée maximale. Retourne la table des trades."""
    BO, BH, BL, AO, AH, AL, atr, slip, n = h["BO"], h["BH"], h["BL"], h["AO"], h["AH"], h["AL"], h["atr"], h["slip"], h["n"]
    achat, vente = FINANCEMENT[h["nom"]]
    jour = (h["tms"] // 86_400_000)
    trades = []
    pos = 0
    ent = stop = risque = lvl = meilleur = 0.0
    i_ent = 0
    sortir = False

    def fermer(i, px):
        nuits = int(jour[i] - jour[i_ent])
        cout = ent * (achat if pos == 1 else vente) / 100.0 / 365.0 * nuits
        trades.append((h["t"][i_ent], ((px - ent) * pos - cout) / risque, pos, nuits))

    for i in range(1, n):
        # 1. à l'ouverture : sortie puis entrée décidées à la clôture précédente
        if pos != 0 and sortir:
            fermer(i, BO[i] - slip if pos == 1 else AO[i] + slip)
            pos = 0
        sortir = False
        s = entree[i - 1]
        if pos == 0 and s != 0 and dist[i - 1] > 0:
            pos = int(s)
            ent = AO[i] + slip if pos == 1 else BO[i] - slip
            risque = dist[i - 1]
            stop = ent - pos * risque
            lvl = ent + pos * tp * risque if tp else 0.0
            meilleur = ent
            i_ent = i
        if pos == 0:
            continue
        # 2. dans la bougie : le stop d'abord, puis l'objectif (jamais sur la bougie d'entrée)
        if pos == 1 and BL[i] <= stop:
            fermer(i, min(stop, BO[i]) - slip); pos = 0; continue
        if pos == -1 and AH[i] >= stop:
            fermer(i, max(stop, AO[i]) + slip); pos = 0; continue
        if tp and i > i_ent and ((pos == 1 and BH[i] >= lvl) or (pos == -1 and AL[i] <= lvl)):
            fermer(i, lvl); pos = 0; continue
        # 3. à la clôture : stop suiveur, sortie demandée, durée maximale
        if suiveur:
            if pos == 1:
                meilleur = max(meilleur, BH[i]); stop = max(stop, meilleur - suiveur * atr[i])
            else:
                meilleur = min(meilleur, AL[i]); stop = min(stop, meilleur + suiveur * atr[i])
        if (pos == 1 and sortie_l is not None and sortie_l[i]) or (pos == -1 and sortie_s is not None and sortie_s[i]):
            sortir = True
        if max_bougies and i - i_ent + 1 >= max_bougies:
            sortir = True
    x = pd.DataFrame(trades, columns=["t", "r", "d", "nuits"])
    x["per"] = B.periodes(h["nom"], x.t) if len(x) else []
    return x


# ───────────────────────── familles ─────────────────────────
def _biais(h, actif):
    if not actif:
        return np.ones(h["n"]), np.ones(h["n"])
    haut = (h["BC"] > h["ma200"]).astype(float)
    bas = (h["BC"] < h["ma200"]).astype(float)
    return haut, bas


def donchian(h, n, biais):
    """Cassure du plus haut / plus bas des n bougies précédentes (clôture), dans le sens de la MA200 si demandé."""
    hh = pd.Series(h["BH"]).rolling(n).max().shift(1).values
    ll = pd.Series(h["BL"]).rolling(n).min().shift(1).values
    up, dn = _biais(h, biais)
    return np.where((h["BC"] > hh) & (up > 0), 1, np.where((h["BC"] < ll) & (dn > 0), -1, 0))


def repli(h, seuil):
    """Repli dans la tendance : prix au-dessus de la MA200 et RSI14 qui passe sous `seuil` -> achat (et l'inverse)."""
    r = h["rsi14"]
    rp = np.roll(r, 1); rp[0] = r[0]
    return np.where((h["BC"] > h["ma200"]) & (r < seuil) & (rp >= seuil), 1,
                    np.where((h["BC"] < h["ma200"]) & (r > 100 - seuil) & (rp <= 100 - seuil), -1, 0))


def macd(h, biais, rapide=12, lent=26, signal=9):
    c = pd.Series(h["BC"])
    ligne = c.ewm(span=rapide, adjust=False).mean() - c.ewm(span=lent, adjust=False).mean()
    hist = (ligne - ligne.ewm(span=signal, adjust=False).mean()).values
    hp = np.roll(hist, 1); hp[0] = 0
    up, dn = _biais(h, biais)
    croise = np.where((hist > 0) & (hp <= 0), 1, np.where((hist < 0) & (hp >= 0), -1, 0))
    return np.where((croise == 1) & (up > 0), 1, np.where((croise == -1) & (dn > 0), -1, 0)), croise


def rsi2(h, seuil, tendance, deux_sens):
    """Retour à la moyenne journalier (Connors) : RSI2 sous `seuil` -> achat, sortie quand la clôture repasse au-dessus
    de sa moyenne 5 jours. Avec `tendance`, seulement au-dessus de la MA200 journalière."""
    r, c = h["rsi2"], h["BC"]
    ok_l = (c > h["ma200"]) if tendance else np.ones(h["n"], dtype=bool)
    ok_s = (c < h["ma200"]) if tendance else np.ones(h["n"], dtype=bool)
    ent = np.where((r < seuil) & ok_l, 1, np.where(deux_sens & (r > 100 - seuil) & ok_s, -1, 0))
    ma5 = pd.Series(c).rolling(5).mean().values
    return ent, c > ma5, c < ma5


def variantes(g):
    """(famille, description, fonction -> table des trades)."""
    H = {"H1": barres(g, 60), "H4": barres(g, 240), "J": barres(g, 1440)}
    v = []
    for (tf, n), suiv, biais in itertools.product((("H1", 24), ("H1", 72), ("H1", 120), ("H4", 30), ("H4", 60)), (3.0, 5.0), (False, True)):
        h = H[tf]
        v.append(("cassure Donchian", f"{tf}, plus haut/bas de {n} bougies, stop suiveur {suiv:g} ATR, biais MA200 {'oui' if biais else 'non'}",
                  lambda h=h, n=n, suiv=suiv, biais=biais: simuler(h, donchian(h, n, biais), suiv * h["atr"], suiveur=suiv)))
    for tf, seuil, mode in itertools.product(("H1", "H4"), (35, 30), ("objectif 2R", "stop suiveur 3 ATR")):
        h = H[tf]
        v.append(("repli RSI dans la tendance", f"{tf}, RSI14 < {seuil} au-dessus de la MA200, stop 3 ATR, {mode}",
                  lambda h=h, seuil=seuil, mode=mode: simuler(h, repli(h, seuil), 3.0 * h["atr"], tp=2.0 if mode == "objectif 2R" else None,
                                                             suiveur=None if mode == "objectif 2R" else 3.0)))
    for tf, stop, biais in itertools.product(("H1", "H4"), (3.0, 5.0), (True, False)):
        h = H[tf]

        def f(h=h, stop=stop, biais=biais):
            ent, croise = macd(h, biais)
            return simuler(h, ent, stop * h["atr"], sortie_l=croise == -1, sortie_s=croise == 1)
        v.append(("croisement MACD", f"{tf}, stop {stop:g} ATR, sortie au croisement inverse, biais MA200 {'oui' if biais else 'non'}", f))
    for seuil, tendance, deux in itertools.product((10, 15), (True, False), (False, True)):
        h = H["J"]

        def f(h=h, seuil=seuil, tendance=tendance, deux=deux):
            ent, sl, ss = rsi2(h, seuil, tendance, deux)
            return simuler(h, ent, 3.0 * h["atr"], sortie_l=sl, sortie_s=ss, max_bougies=10)
        v.append(("RSI2 journalier (retour a la moyenne)", f"RSI2 < {seuil}, {'au-dessus de la MA200' if tendance else 'sans filtre'}, {'achat et vente' if deux else 'achat seul'}, stop 3 ATR", f))
    return v


def un_instrument(nom):
    debut = time.time()
    g = B.charger(nom)
    lignes = []
    for famille, description, jouer in variantes(g):
        x = jouer()
        ligne = dict(instrument=nom, famille=famille, variante=description, gestion="")
        for per in ("train", "A"):
            s = B.stats(x, per)
            ligne.update({f"n_{per}": s["n"], f"moy_{per}": round(s["mean"], 4), f"t_{per}": round(s["t"], 2),
                          f"tot_{per}": round(s["tot"], 1), f"baisse_{per}": round(s["dd"], 1)})
        x = x[x.per != "B"]                                     # les totaux ne comptent que recherche + vérification
        tout = B.stats(x)
        ligne.update(n=tout["n"], tot=round(tout["tot"], 1), baisse=round(tout["dd"], 1), annees_pos=tout["ypos"], gagnants=round(tout["win"], 3),
                     tot_achats=round(float(x.r[x.d == 1].sum()), 1) if len(x) else 0.0, tot_ventes=round(float(x.r[x.d == -1].sum()), 1) if len(x) else 0.0,
                     nuits_moy=round(float(x.nuits.mean()), 1) if len(x) else 0.0)
        lignes.append(ligne)
    print(f"{nom} : {len(lignes)} variantes en {time.time() - debut:.0f} s", flush=True)
    return lignes


if __name__ == "__main__":
    noms = sys.argv[1:] or list(FINANCEMENT)
    with multiprocessing.Pool(min(4, len(noms))) as pool:
        resultats = pool.map(un_instrument, noms)
    table = pd.DataFrame([ligne for lignes in resultats for ligne in lignes])
    os.makedirs(SORTIES, exist_ok=True)
    chemin = os.path.join(SORTIES, "variantes-swing.csv")
    if sys.argv[1:] and os.path.exists(chemin):
        ancien = pd.read_csv(chemin)
        table = pd.concat([ancien[~ancien.instrument.isin(noms)], table], ignore_index=True)
    table.to_csv(chemin, index=False)
    print(f"{len(table)} variantes -> {chemin}")
