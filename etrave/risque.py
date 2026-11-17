"""Ce que le test dit d'un risque par trade et d'un levier : gain par an, pire baisse, jours où la marge manque.

Les trades viennent de etrave/reference.json : les 1 391 trades de la v6 (ajout de 2 unités à +2R) rejouée le
17 novembre 2026 minute par minute sur le Nasdaq CFD de Dukascopy (M1 bid et ask, 2018-01 -> 2026-11, glissement
0,1 point), avec pour chacun sa date, son résultat en R, la largeur du range rapportée au prix et si la pyramide s'est
déclenchée. Le fichier était refait par recherches/nasdaq/reference.py (retiré du dépôt, historique git, commit 39b5b77). Le capital est composé trade après trade, avec en plus la marge :

    taille de la position = solde × risque ÷ range        (règle 4 de la v6)
    marge demandée        = valeur de la position ÷ levier
    donc risque possible  = levier × (range ÷ prix) × part de la marge utilisable ÷ nombre d'unités

Quand le risque demandé dépasse ce plafond, l'EA réduit la taille (il ne peut pas ouvrir plus que la marge ne permet) :
le trade est gardé, avec un risque plus petit. Le calcul fait de même, jour par jour.
"""
import datetime
import json
import os

REFERENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.json")
# Les deux valeurs suivantes sont celles de l'EA (MARGIN_USE, et 1 unité de départ + 2 unités de pyramide).
PART_MARGE = 0.90
UNITES = 3.0
# Repères du README : pire série de pertes du test 2018-2026, pire baisse de l'ancien test 2015-2026 (ajout de 2 unités).
PIRE_SERIE = 15
PIRE_BAISSE_ANCIEN_TEST_R = 76

_cache = {}


def charger(chemin=REFERENCE):
    if chemin not in _cache:
        with open(chemin, "r", encoding="utf-8") as f:
            _cache[chemin] = json.load(f)
    return _cache[chemin]


def risque_possible(levier, range_sur_prix, part_marge=PART_MARGE, unites=UNITES):
    """Le plus grand risque (fraction du solde) que la marge permet ce jour-là."""
    return levier * range_sur_prix * part_marge / unites


def simuler(risque_pct, levier=None, reference=None):
    """Le test rejoué à ce risque (en % du solde) et ce levier (None = marge jamais limitante)."""
    ref = charger() if reference is None else reference
    trades = ref["trades"]
    voulu = risque_pct / 100.0
    capital = sommet = 1.0
    pire = 0.0
    reduits = 0
    somme_risque = 0.0
    for _date, r, range_sur_prix, _pyramide in trades:
        f = voulu
        if levier:
            plafond = risque_possible(levier, range_sur_prix)
            if plafond < f:
                f = plafond
                reduits += 1
        somme_risque += f
        capital *= max(0.0, 1.0 + f * r)
        sommet = max(sommet, capital)
        pire = max(pire, 1.0 - capital / sommet)
    jours = (datetime.date.fromisoformat(ref["fin"]) - datetime.date.fromisoformat(ref["debut"])).days
    annees = jours / 365.25
    return {
        "risquePct": risque_pct,
        "levier": levier,
        "trades": len(trades),
        "annees": round(annees, 1),
        "debut": ref["debut"], "fin": ref["fin"],
        "multiple": capital,
        "parAnPct": 100.0 * (capital ** (1.0 / annees) - 1.0) if capital > 0 else -100.0,
        "pireBaissePct": 100.0 * pire,
        # part des trades dont la taille aurait été réduite faute de marge, et risque réellement pris en moyenne
        "reduitsPct": 100.0 * reduits / len(trades),
        "risqueMoyenPct": 100.0 * somme_risque / len(trades),
        # repères simples : une série de pertes pleines, à ce risque
        "serie": PIRE_SERIE,
        "seriePct": 100.0 * (1.0 - (1.0 - voulu) ** PIRE_SERIE),
        "ancienTestR": PIRE_BAISSE_ANCIEN_TEST_R,
        "ancienTestPct": 100.0 * (1.0 - (1.0 - voulu) ** PIRE_BAISSE_ANCIEN_TEST_R),
        # levier qu'il faut pour que la moitié des jours passent sans réduction à ce risque
        "rangeMedianPct": 100.0 * sorted(t[2] for t in trades)[len(trades) // 2],
        # unités ouvertes au plus (départ + pyramide) : ce que la marge doit pouvoir porter
        "unites": UNITES,
    }
