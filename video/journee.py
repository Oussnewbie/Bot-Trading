"""La journée de trading à raconter, lue dans les journaux que l'EA écrit dans le dossier commun de MetaTrader (`…\\Etrave`).

    seances-<symbole>.csv    la zone de 15:30 (range) et la ligne « fin » écrite après la sortie : sans elle, la séance n'est pas finie
    bougies-<symbole>.csv    les bougies M5 de la séance, pour redessiner le graphique
    execution-<symbole>.csv  une ligne par position fermée : heures, prix d'entrée et de sortie, stop, résultat
    trades-<symbole>.csv     (compte seulement, pas le testeur) le résultat de chaque trade en % du solde

Les lectures sont celles de l'export trimestriel d'Étrave (`export.lire_journal`, `pont.lire_trades`) : une ligne abîmée est ignorée,
jamais devinée. Les heures sont converties de New York vers Paris par les fuseaux horaires (l'écart est de 5 h quelques semaines par an,
pas toujours 6 h). Les raisons des filtres écrites par l'EA ne sortent jamais d'ici : elles font partie de ce qui reste secret.
"""
import datetime
import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etrave"))
import export  # noqa: E402  (lecture des journaux, la même que l'export trimestriel)
import pont    # noqa: E402

NEW_YORK, PARIS = ZoneInfo("America/New_York"), ZoneInfo("Europe/Paris")
# Les deux marchés tradés, dans l'ordre du récap, et les mots de la voix (« S et P » se lit mieux que « S&P »)
MARCHES = {
    "nasdaq": {"nom": "Nasdaq 100", "voix": "Nasdaq", "ordre": 0},
    "sp500": {"nom": "S&P 500", "voix": "S et P cinq cents", "ordre": 1},
}


class JourneeIncomplete(Exception):
    """La journée ne peut pas être racontée telle quelle (séance pas finie, bougies absentes…) : le message dit quoi faire."""


def instrument(symbole):
    """« nasdaq », « sp500 » ou « autre », comme InstrumentOf() dans l'EA."""
    s = symbole.upper()
    if any(m in s for m in ("NAS", "NDX", "NQ", "USTEC", "US100", "USATECH", "TECH100")):
        return "nasdaq"
    if any(m in s for m in ("SPX", "SP500", "US500", "USA500", "S&P", "SPI500")):
        return "sp500"
    return "autre"


def vers_paris_ny(jour, hhmm):
    """« 09:35 » à New York, le jour donné → datetime à Paris."""
    h, m = (int(x) for x in hhmm.split(":")[:2])
    return datetime.datetime(jour.year, jour.month, jour.day, h, m, tzinfo=NEW_YORK).astimezone(PARIS)


def vers_paris_ms(ms):
    """Millisecondes UTC (colonnes entree_utc_ms / sortie_utc_ms) → datetime à Paris ; None si vide."""
    v = export.nombre(ms)
    return datetime.datetime.fromtimestamp(v / 1000, tz=datetime.timezone.utc).astimezone(PARIS) if v else None


def jours_finis(dossier):
    """Les jours (dates de New York) dont la séance est finie (ligne « fin »), du plus ancien au plus récent."""
    seances, _ = export.lire_journal(dossier, "seances")
    return sorted({export.jour_de(s["jour_ny"]) for s in seances if s.get("moment") == "fin" and export.jour_de(s["jour_ny"])})


def _position(e):
    sens = int(export.nombre(e.get("sens")) or 0)
    entree, sortie = export.nombre(e.get("prix_entree")), export.nombre(e.get("prix_sortie"))
    return {
        "type": e.get("entree", ""), "sens": sens,
        "entree": vers_paris_ms(e.get("entree_utc_ms")), "sortie": vers_paris_ms(e.get("sortie_utc_ms")),
        "prix_entree": entree, "prix_sortie": sortie, "stop": export.nombre(e.get("stop_initial")),
        "points": (sortie - entree) * sens if entree is not None and sortie is not None and sens in (1, -1) else None,
        "r": export.nombre(e.get("r")), "net": export.nombre(e.get("resultat_net")), "devise": e.get("devise", ""),
        "raison": e.get("raison", ""),
    }


def charger(dossier, jour=None):
    """La journée `jour` (date de New York ; par défaut la dernière séance finie) : un dictionnaire prêt à raconter.

    marches : un par symbole qui a une ligne « fin » ce jour-là, Nasdaq puis S&P 500 ; chacun avec sa zone, ses bougies (heure de
    Paris), ses positions (dans l'ordre d'entrée) et ses totaux (points, R, argent, % du solde si le journal des trades est là).
    """
    if not os.path.isdir(dossier):
        raise JourneeIncomplete(f"Dossier des journaux introuvable : {dossier}")
    seances, _ = export.lire_journal(dossier, "seances")
    finis = jours_finis(dossier)
    if not finis:
        raise JourneeIncomplete("Aucune séance finie dans ce dossier : l'EA écrit la ligne « fin » quelques minutes après la sortie "
                                "de fin de journée (vers 21:52 à Paris).")
    jour = jour or finis[-1]
    if jour not in finis:
        derniers = ", ".join(j.isoformat() for j in finis[-5:])
        raise JourneeIncomplete(f"La séance du {jour.isoformat()} n'est pas finie dans les journaux (pas de ligne « fin »). "
                                f"Dernières séances finies : {derniers}.")
    cle = jour.isoformat()
    bougies, _ = export.lire_journal(dossier, "bougies")
    executions, _ = export.lire_journal(dossier, "execution")
    trades = pont.lire_trades(dossier)
    marches, sources = [], set()
    for s in sorted({x["symbole"] for x in seances if x["jour_ny"] == cle and x.get("moment") == "fin"}):
        lignes = [x for x in seances if x["jour_ny"] == cle and x["symbole"] == s]
        fin = [x for x in lignes if x["moment"] == "fin"][-1]
        sources.update(x.get("source", "") for x in lignes)
        b = [x for x in bougies if x["jour_ny"] == cle and x["symbole"] == s]
        if not b:
            raise JourneeIncomplete(f"Pas de bougies pour {s} le {cle} : l'EA qui tournait ce jour-là n'écrivait pas encore le journal "
                                    "des bougies (bougies-<symbole>.csv). Installe l'EA de cette version, le récap marchera dès la séance suivante.")
        bas, haut = export.nombre(fin.get("range_bas")), export.nombre(fin.get("range_haut"))
        positions = sorted((_position(e) for e in executions if e.get("jour_ny") == cle and e.get("symbole") == s),
                           key=lambda p: p["entree"] or datetime.datetime.max.replace(tzinfo=PARIS))
        pct = [t["pct"] for t in trades if t["date"].replace(".", "-") == cle and t["symbole"] == s and t["pct"] is not None]
        sommes = {k: sum(p[k] for p in positions) if positions and all(p[k] is not None for p in positions) else None
                  for k in ("points", "r", "net")}
        nature = instrument(s)
        marches.append({
            "symbole": s, "instrument": nature, **MARCHES.get(nature, {"nom": s, "voix": s, "ordre": 9}),
            "zone": {"bas": bas, "haut": haut} if bas and haut and haut > bas else None,
            "bougies": [{"heure": vers_paris_ny(jour, x["heure_ny"]), "o": export.nombre(x["ouverture"]), "h": export.nombre(x["haut"]),
                         "l": export.nombre(x["bas"]), "c": export.nombre(x["cloture"])} for x in b],
            "positions": positions, "points": sommes["points"], "r": sommes["r"], "net": sommes["net"],
            "pct": sum(pct) if pct and len(pct) >= len(positions) else None,
        })
    marches.sort(key=lambda m: (m["ordre"], m["symbole"]))
    nets = [m["net"] for m in marches if m["positions"]]
    net = sum(nets) if nets and all(n is not None for n in nets) else None
    return {
        "jour": jour, "source": "testeur" if "testeur" in sources else ("reel" if "reel" in sources else (sorted(sources - {""}) or [""])[0]),
        "marches": marches, "net": net,
        "verdict": None if net is None else ("positive" if net > 0 else "négative" if net < 0 else "neutre"),
        "trades": sum(len(m["positions"]) for m in marches),
    }
