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
import math
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


def mediane_range(trades, marche=None):
    """La médiane de la largeur du range rapportée au prix (colonne range_sur_prix), pour un marché ou pour tous."""
    largeurs = sorted(t[3] for t in trades if marche is None or t[1] == marche)
    return largeurs[len(largeurs) // 2] if largeurs else None


def risque_possible(levier, range_sur_prix, part_marge=PART_MARGE, unites=UNITES, stop=STOP_RANGES):
    """Le plus grand risque (fraction du solde) que la marge permet ce jour-là."""
    return levier * range_sur_prix * stop * part_marge / unites


def estimer_taille(solde, risque_pct, prix, valeur_point_lot, lot_pas, lot_min, marche, reference=None):
    """AUD-24 (audit du 26/11/2026) : la taille d'une cassure A sur ce marché, avec le lot minimum et le pas de volume du
    courtier (l'onglet Risque les ignorait). Estimation, avec le range médian du test au lieu du range du jour :

        risque en argent = solde × risque %
        stop             ≈ STOP_RANGES × médiane de range_sur_prix du marché (reference.json) × prix
        argent par lot   = stop × valeur_point_lot (argent par point de prix et par lot, donné par l'EA)
        lots             = arrondi vers le bas au pas de volume, comme l'EA ; sous le lot minimum, l'EA ne prend pas le trade

    None si une valeur manque, n'est pas un nombre fini ou n'a pas de sens (0, négatif), ou si le marché est inconnu."""
    valeurs = (solde, risque_pct, prix, valeur_point_lot, lot_pas, lot_min)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in valeurs):
        return None
    if min(solde, risque_pct, prix, valeur_point_lot, lot_pas) <= 0 or lot_min < 0:
        return None
    mediane = mediane_range((charger() if reference is None else reference)["trades"], marche)
    if not mediane:
        return None
    risque_argent = solde * risque_pct / 100.0
    stop_prix = STOP_RANGES * mediane * prix
    argent_par_lot = stop_prix * valeur_point_lot
    bruts = risque_argent / argent_par_lot
    lots = round(math.floor(bruts / lot_pas + 1e-9) * lot_pas, 8)      # 1e-9 : 0.3 / 0.1 vaut 2.9999999999999996
    sous_minimum = lots <= 0 or lots < lot_min - 1e-9
    risque_reel = 0.0 if sous_minimum else lots * argent_par_lot
    reduction = 100.0 * (1.0 - risque_reel / risque_argent)
    return {
        "marche": marche, "lots": 0.0 if sous_minimum else lots, "lotsBruts": bruts, "lotMin": lot_min, "lotPas": lot_pas,
        "stopPrix": stop_prix, "argentParLot": argent_par_lot, "risqueArgent": risque_argent, "risqueReelArgent": risque_reel,
        "reductionPct": reduction, "sousMinimum": sous_minimum,
        # l'arrondi au pas fait perdre plus de 30 % du risque voulu
        "arrondiTropFort": not sous_minimum and reduction > 30.0,
    }


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
        # levier qu'il faut pour que la moitié des jours passent sans réduction à ce risque. AUD-15 (audit du 26/11/2026) : la
        # médiane prenait t[2] (le R du jour, médiane négative) au lieu de t[3] (le range rapporté au prix) : « environ 1:0 »
        "rangeMedianPct": 100.0 * mediane_range(trades),
        # unités que l'EA réserve (toutes les entrées et leurs pyramides) : ce que la marge doit pouvoir porter
        "unites": UNITES,
        "stopRanges": STOP_RANGES,
    }
