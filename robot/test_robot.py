"""Contrôles statiques de l'EA Strategy V10 : `python -m pytest robot`.

Ce ne sont pas des tests de compilation (impossible sans MetaEditor) : ils vérifient, dans le texte du code, que les
correctifs d'exécution sont en place et que les calculs recopiés ici donnent le bon résultat.
"""
import math
import os
import re

ICI = os.path.dirname(os.path.abspath(__file__))
EA = open(os.path.join(ICI, "Strategy-V10.mq5"), encoding="utf-8-sig").read()


def vol_digits(step):
    """Copie en Python de VolDigits() de l'EA."""
    d = 0
    while d < 8 and abs(step * 10 ** d - round(step * 10 ** d)) > 1e-6:
        d += 1
    return d


def normaliser(lots, digits):
    """NormalizeDouble de MQL5 : arrondi au plus proche, la moitié s'éloignant de zéro."""
    facteur = 10 ** digits
    return math.floor(lots * facteur + 0.5) / facteur


def test_decimales_du_pas_de_volume():
    attendu = {1.0: 0, 0.1: 1, 0.5: 1, 0.01: 2, 0.05: 2, 0.25: 2, 0.001: 3, 2.0: 0}
    for pas, decimales in attendu.items():
        assert vol_digits(pas) == decimales, pas


def test_le_lot_arrondi_ne_depasse_jamais_le_lot_calcule():
    """EA-04 : avec un pas de 0,5, l'ancien calcul arrondissait 0,5 lot à 1 lot (le double du risque)."""
    for pas in (1.0, 0.5, 0.25, 0.1, 0.05, 0.01):
        for brut in (0.37, 0.5, 0.74, 1.26, 2.9, 7.77):
            lots = math.floor(brut / pas) * pas
            assert normaliser(lots, vol_digits(pas)) <= brut + 1e-9, (pas, brut)
    ancien = int(max(0, round(-math.log10(0.5))))
    assert normaliser(0.5, ancien) == 1.0          # le défaut corrigé, reproduit


def test_l_ea_utilise_volDigits_partout():
    assert "MathLog10(step)" not in EA
    assert re.search(r"^int VolDigits\(double step\)", EA, re.M)
    assert EA.count("VolDigits(step)") == 4        # cassure, pyramide de la cassure, jambes B/C/D, pyramide des jambes


def corps(fonction):
    return re.search(rf"^bool {fonction}\(\).*?\n  }}\n", EA, re.S | re.M).group(0)


def test_pas_d_ordre_si_l_heure_du_serveur_est_fausse():
    """EA-01 : un mauvais réglage d'heure d'été n'était que signalé ; l'EA tradait la mauvaise bougie."""
    setup = corps("Setup")
    garde = setup.index("if(!gClockOk)")
    assert "CheckClock();" in setup[:garde]
    assert setup.index("if(!gActive)") < garde < setup.index("gObserve   = true;")   # avant tout ordre et avant la mémoire
    assert "!MQLInfoInteger(MQL_TESTER)" in setup[:garde]                            # pas dans le testeur (heure simulée)


def test_le_rsi_est_lu_une_fois_l_indicateur_a_jour():
    """EA-04 (RSI) : au premier tick de 9:35, le RSI pouvait être celui de 9:25."""
    setup = corps("Setup")
    attente = setup.index("BarsCalculated(hRSI) < Bars(_Symbol, PERIOD_M5)")
    assert attente < setup.index("CopyBuffer(hRSI, 0, 1, 1, rsi)")
    assert setup[attente:attente + 120].count("return false;") == 1                  # réessayé au tick suivant


def test_les_ordres_stop_ne_survivent_pas_a_l_ea():
    """Revue du 17/11/2026 : ordres GTC préférés aux ordres DAY, et jamais supprimés quand l'EA s'arrête."""
    choix = re.search(r"ENUM_ORDER_TYPE_TIME tt = (.*?);", EA, re.S).group(1)
    assert choix.index("ORDER_TIME_SPECIFIED") < choix.index("ORDER_TIME_DAY") < choix.index("ORDER_TIME_GTC")
    fin = re.search(r"void OnDeinit\(const int reason\)(.*?)\n  }\n", EA, re.S).group(1)
    assert "DeletePendings()" in fin
    for raison in ("REASON_REMOVE", "REASON_CHARTCLOSE", "REASON_CLOSE"):
        assert raison in fin
    for raison in ("REASON_PARAMETERS", "REASON_RECOMPILE", "REASON_CHARTCHANGE"):   # l'EA repart aussitôt : on garde
        assert raison not in fin


def test_entree_au_marche_bornee_a_1_25_R():
    """EA-06 : entrée au marché « quelle que soit la distance » quand l'EA démarre en retard."""
    entrees = re.search(r"void CheckEntries\(\)(.*?)\n  }\n", EA, re.S).group(1)
    garde = entrees.index("riskN > 1.25 * riskP")
    assert entrees.index("if(gObserve)") < garde < entrees.index("trade.Buy(gLots")    # après la règle mémoire, avant l'ordre
    assert "CancelDay(" in entrees[garde:garde + 200]
