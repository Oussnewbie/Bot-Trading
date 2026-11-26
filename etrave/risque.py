"""Un risque par trade et un levier rejoués sur les trades de référence : gain par an, pire baisse, jours où la marge manque.

Les trades viennent de etrave/reference.json : la V11 rejouée sur le Nasdaq 100 et le S&P 500 (données M1 du courtier, 2019-03 ->
2026-11, spread réel + glissement), une ligne par marché et par jour de trade : sa date, le marché, le résultat de toutes
les entrées du jour (A, B, D1 à D3 et leurs pyramides) en R (1 R = le risque réglé) et la largeur du range rapportée au prix.
Jusqu'au 26/11/2026, ce fichier contenait l'ancienne ORB v6 (une seule position par jour, Nasdaq seul) : la page sous-estimait la
pire journée. Les deux marchés tradent le même jour sur le même solde : le capital est composé jour après jour (somme des
deux marchés), avec en plus la marge :

    taille de la position = solde × risque ÷ (3 × range)  (stop à 3 ranges, lots divisés par 3)
    marge demandée        = valeur de la position ÷ levier
    donc risque possible  = levier × (range ÷ prix) × 3 × part de la marge utilisable ÷ nombre d'unités

Le nombre d'unités est celui que l'EA réserve sur un compte hedging (Setup) : la marge de la cassure est prévue pour
toutes les entrées du jour, pyramides comprises, même si elles ne viennent pas toutes.

Quand le risque demandé dépasse ce plafond, l'EA réduit la taille (il ne peut pas ouvrir plus que la marge ne permet) :
le trade est gardé, avec un risque plus petit. Le calcul fait de même, jour par jour.
"""
import datetime
import json
import os

REFERENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.json")
# Valeurs de l'EA : MARGIN_USE, puis les unités de marge de Setup (revue cloud du 25/11/2026 : on en comptait 3, l'EA en
# réserve 15). Chaque entrée compte 1 unité, plus InpPyrSize unités pour sa pyramide : la cassure A, l'entrée B, et les
# InpDCount entrées D (pyramide InpDPyr). L'entrée C est coupée.
PART_MARGE = 0.90
PYRAMIDE = 2.0          # InpPyrSize
STOP_RANGES = 3.0       # InpStopMult : stop à 3 ranges, la position est 3 fois plus petite qu'avec un stop à 1 range
ENTREES_D = 3           # InpDCount
UNITES = (1 + PYRAMIDE) + (1 + PYRAMIDE) + ENTREES_D * (1 + PYRAMIDE)

_cache = {}


def charger(chemin=REFERENCE):
    if chemin not in _cache:
        with open(chemin, "r", encoding="utf-8") as f:
            _cache[chemin] = json.load(f)
    return _cache[chemin]


def risque_possible(levier, range_sur_prix, part_marge=PART_MARGE, unites=UNITES, stop=STOP_RANGES):
    """Le plus grand risque (fraction du solde) que la marge permet ce jour-là."""
    return levier * range_sur_prix * stop * part_marge / unites


def simuler(risque_pct, levier=None, reference=None):
    """Le test rejoué à ce risque (en % du solde) et ce levier (None = marge jamais limitante)."""
    ref = charger() if reference is None else reference
    trades = ref["trades"]
    voulu = risque_pct / 100.0
    capital = sommet = 1.0
    pire = 0.0
    reduits = 0
    somme_risque = 0.0
    jours = {}                                                   # date -> rendement du jour (les deux marchés)
    for date, _marche, r, range_sur_prix in trades:
        f = voulu
        if levier:
            plafond = risque_possible(levier, range_sur_prix)
            if plafond < f:
                f = plafond
                reduits += 1
        somme_risque += f
        jours[date] = jours.get(date, 0.0) + f * r
    serie = serie_pire = 0
    cout_serie = cout_pire = 1.0
    pire_jour = 0.0
    for date in sorted(jours):
        rendement = jours[date]
        capital *= max(0.0, 1.0 + rendement)
        sommet = max(sommet, capital)
        pire = max(pire, 1.0 - capital / sommet)
        pire_jour = min(pire_jour, rendement)
        if rendement < 0:                                        # la plus longue série de jours perdants, et ce qu'elle a coûté
            serie, cout_serie = serie + 1, cout_serie * max(0.0, 1.0 + rendement)
            if serie > serie_pire or (serie == serie_pire and cout_serie < cout_pire):
                serie_pire, cout_pire = serie, cout_serie
        else:
            serie, cout_serie = 0, 1.0
    annees = (datetime.date.fromisoformat(ref["fin"]) - datetime.date.fromisoformat(ref["debut"])).days / 365.25
    return {
        "risquePct": risque_pct,
        "levier": levier,
        "trades": len(trades),
        "jours": len(jours),
        "annees": round(annees, 1),
        "debut": ref["debut"], "fin": ref["fin"],
        "multiple": capital,
        "parAnPct": 100.0 * (capital ** (1.0 / annees) - 1.0) if capital > 0 else -100.0,
        "pireBaissePct": 100.0 * pire,
        # part des trades dont la taille aurait été réduite faute de marge, et risque réellement pris en moyenne
        "reduitsPct": 100.0 * reduits / len(trades),
        "risqueMoyenPct": 100.0 * somme_risque / len(trades),
        # repères : la plus longue série de jours perdants du test et la pire journée (toutes les entrées, deux marchés), à ce risque
        "serie": serie_pire,
        "seriePct": 100.0 * (1.0 - cout_pire),
        "pireJourPct": -100.0 * pire_jour,
        "pireJourR": -pire_jour / voulu if voulu else 0.0,
        # levier qu'il faut pour que la moitié des jours passent sans réduction à ce risque
        "rangeMedianPct": 100.0 * sorted(t[2] for t in trades)[len(trades) // 2],
        # unités que l'EA réserve (toutes les entrées et leurs pyramides) : ce que la marge doit pouvoir porter
        "unites": UNITES,
        "stopRanges": STOP_RANGES,
    }
