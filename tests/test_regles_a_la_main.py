"""Scénarios écrits à la main : le résultat attendu est calculé sur le papier à partir des règles du README.
Chaque scénario est joué deux fois : par le simulateur (v5_lab.py) et par la réécriture naïve (regles_readme.py).

Jour type (achat). Bid : 9:00-9:25 monte de 10000 à 10012 ; bougie de 9:30 = range 10010 – 10030 (20 points).
Ask = bid + 1. L'achat stop sur 10030 s'exécute à 10030 + 0,1 de glissement = 10030,1 ; stop 10010 ; risque 20,1.
"""
import pandas as pd
import pytest

import orb_v5
import regles_readme as N
from conftest import JOUR_SCENARIO, marche_scenario

MONTEE = {"09:00": (10000, 10002, 10000, 10002), "09:05": (10002, 10004, 10002, 10004), "09:10": (10004, 10006, 10004, 10006),
          "09:15": (10006, 10008, 10006, 10008), "09:20": (10008, 10010, 10008, 10010), "09:25": (10010, 10012, 10010, 10012),
          "09:30": (10012, 10030, 10010, 10028)}
DESCENTE = {"09:00": (10000, 10000, 9998, 9998), "09:05": (9998, 9998, 9996, 9996), "09:10": (9996, 9996, 9994, 9994),
            "09:15": (9994, 9994, 9992, 9992), "09:20": (9992, 9992, 9990, 9990), "09:25": (9990, 9990, 9988, 9988),
            "09:30": (9988, 9990, 9970, 9972)}
ENTREE_ACHAT = {"09:35": (10028, 10040, 10026, 10038)}     # ask haut 10041 >= 10030 : achat à 10030,1
E, RISQUE = 10030.1, 20.1


def jouer(labo, bougies):
    """Renvoie (trade du simulateur, trade de la réécriture) pour le jour du scénario ; None s'il n'y a pas de trade."""
    bid, ask = marche_scenario(bougies)
    labo.prep(data=(bid, ask))
    X = labo.run(orb_v5.V5, labo.f_v4)
    jour = pd.Timestamp(JOUR_SCENARIO)
    X = X[X.t.dt.tz_localize(None).dt.normalize() == jour] if len(X) else X
    T = N.tous_les_trades(bid, ask)
    T = T[T.jour == jour] if len(T) else T
    assert len(X) <= 1 and len(T) <= 1
    return (X.iloc[0] if len(X) else None), (T.iloc[0] if len(T) else None)


def verifier(labo, bougies, r_attendu, sens=1):
    x, t = jouer(labo, bougies)
    assert x is not None and t is not None, "un trade était attendu"
    assert x.d == sens and t.sens == sens
    assert x.r == pytest.approx(r_attendu, abs=1e-9)
    assert t.r == pytest.approx(r_attendu, abs=1e-9)
    return x, t


def test_stop_plein(labo):
    # 9:40 : le bid descend à 10005, sous le stop 10010 -> sortie à 10010 - 0,1
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10038, 10039, 10005, 10008)}
    x, t = verifier(labo, b, (10009.9 - E) / RISQUE)
    assert x.why == "stop" and t.motif == "stop"
    assert t.entree == pytest.approx(E) and t.stop == 10010


def test_trou_a_l_ouverture_sous_le_stop(labo):
    # 9:40 ouvre à 10000, déjà sous le stop : on sort à l'ouverture, pas au stop (perte de plus de 1R)
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10000, 10001, 9995, 9998)}
    verifier(labo, b, (9999.9 - E) / RISQUE)


def test_entree_avec_trou(labo):
    # l'ask ouvre à 10035, au-dessus du niveau : achat à 10035 + 0,1, le risque devient 25,1 ; puis stop plein
    b = {**MONTEE, "09:35": (10034, 10040, 10032, 10038), "09:40": (10038, 10039, 10005, 10008)}
    x, t = verifier(labo, b, (10009.9 - 10035.1) / 25.1)
    assert t.entree == pytest.approx(10035.1)


def test_stop_d_une_vente_declenche_par_l_ask(labo):
    # vente à 9969,9, stop 9990. À 9:40 le bid monte à 9989,5 (sous le stop) mais l'ask à 9990,5 : stoppé quand même
    b = {**DESCENTE, "09:35": (9972, 9973, 9960, 9965), "09:40": (9965, 9989.5, 9964, 9980)}
    x, t = verifier(labo, b, (9969.9 - 9990.1) / 20.1, sens=-1)
    assert t.motif == "stop" and t.entree == pytest.approx(9969.9)


def test_stop_au_prix_d_entree_apres_1_5R(labo):
    # 9:40 : +1,5R atteint (10061 >= 10030,1 + 1,5 x 20,1 = 10060,25), clôture sous +2R. 9:45 : retour à 10029 -> sortie à l'entrée
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10038, 10061, 10036, 10050), "09:45": (10050, 10051, 10029, 10031)}
    x, t = verifier(labo, b, (E - 0.1 - E) / RISQUE)
    assert x.why == "stop remonté" and t.motif == "stop remonté"


def test_stop_deplace_seulement_a_la_bougie_suivante(labo):
    # 9:40 : +1,5R atteint PUIS retour sous l'entrée dans la même bougie : le stop déplacé ne vaut pas encore.
    # Le reste de la journée est plat à 10035 : sortie de fin de journée à 10035 - 0,1.
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10038, 10061, 10029, 10035)}
    x, t = verifier(labo, b, (10034.9 - E) / RISQUE)
    assert t.motif == "fin" and str(t.heure_sortie.time()) == "15:45:00"


def test_pyramide_puis_stop_remonte(labo):
    # 9:40 clôture à 10072 = +2,08R -> ajout à l'ask 10073 + 0,1 ; stop de l'ensemble 1R dessous = 10053.
    # 9:45 : le bid descend à 10050 -> tout sort à 10053 - 0,1. Unité de départ +22,8 ; ajout -20,2 ; total +2,6 points.
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10038, 10075, 10037, 10072), "09:45": (10072, 10073, 10050, 10052)}
    x, t = verifier(labo, b, ((10052.9 - E) + (10052.9 - 10073.1)) / RISQUE)
    assert bool(t.pyramide) and t.r > 0     # après l'ajout, le pire cas reste au-dessus de zéro


def test_pyramide_puis_fin_de_journee(labo):
    b = {**MONTEE, **ENTREE_ACHAT, "09:40": (10038, 10075, 10037, 10072)}
    verifier(labo, b, ((10071.9 - E) + (10071.9 - 10073.1)) / RISQUE)


def test_les_deux_cotes_dans_la_bougie_d_entree(labo):
    # 9:35 touche le haut (entrée) et le bas (stop) : on ne sait pas l'ordre, le test compte un stop plein
    b = {**MONTEE, "09:35": (10028, 10040, 10005, 10020)}
    verifier(labo, b, (10009.9 - E) / RISQUE)


def test_cote_bloque_touche_d_abord(labo):
    # jour d'achat seulement ; 9:35 touche le bas du range sans toucher le haut -> ordre annulé, même si 9:40 casse le haut
    b = {**MONTEE, "09:35": (10028, 10028.5, 10009, 10015), "09:40": (10015, 10045, 10014, 10040)}
    x, t = jouer(labo, b)
    assert x is None and t is None


def test_pas_de_cassure_avant_9h45(labo):
    # les bougies de 9:35 et 9:40 restent dans le range ; la cassure de 9:45 arrive trop tard
    b = {**MONTEE, "09:35": (10028, 10028.5, 10020, 10025), "09:40": (10025, 10028.5, 10020, 10026), "09:45": (10026, 10060, 10025, 10055)}
    x, t = jouer(labo, b)
    assert x is None and t is None


def test_filtre_elan(labo):
    # le range de 9:30 ne dépasse pas le plus haut de 9:00-9:30 (10040 à 9:10) : achat interdit malgré un RSI > 50
    b = {**MONTEE, "09:10": (10004, 10040, 10004, 10006), "09:35": (10028, 10045, 10026, 10040)}
    x, t = jouer(labo, b)
    assert x is None and t is None


def test_r_mesure_sur_le_range(labo):
    # règle 4 du README : 1R = taille x range. Avec un trou à l'entrée, la perte réelle dépasse 1R.
    b = {**MONTEE, "09:35": (10034, 10040, 10032, 10038), "09:40": (10038, 10039, 10005, 10008)}
    bid, ask = marche_scenario(b)
    t = N.tous_les_trades(bid, ask, r_sur="range").iloc[-1]
    assert t.r == pytest.approx((10009.9 - 10035.1) / 20.0)   # -1,26R sur l'argent risqué, contre -1,004R sur entrée-stop
