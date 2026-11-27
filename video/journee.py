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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "etrave"))
import export  # noqa: E402  (lecture des journaux, la même que l'export trimestriel)
import pont    # noqa: E402

# Correctif VID-02 (audit du 25/11/2026) : le Python de Windows n'a pas de base de fuseaux horaires ; sans le paquet tzdata, l'outil
# s'arrêtait dès son import sur une erreur incompréhensible.
try:
    NEW_YORK, PARIS = ZoneInfo("America/New_York"), ZoneInfo("Europe/Paris")
except ZoneInfoNotFoundError:
    raise SystemExit("Fuseaux horaires introuvables. Sous Windows, installe-les une fois : py -m pip install tzdata")
# Les deux marchés trades_j, dans l'ordre du récap, et les mots de la voix (« S et P » se lit mieux que « S&P »)
MARCHES = {
    "nasdaq": {"nom": "Nasdaq 100", "voix": "Nasdaq", "ordre": 0},
    "sp500": {"nom": "S&P 500", "voix": "S et P cinq cents", "ordre": 1},
}


class JourneeIncomplete(Exception):
    """La journée ne peut pas être racontée telle quelle (séance pas finie, bougies absentes…) : le message dit quoi faire."""


# V-23 (audit du 27/11/2026) : la règle était recopiée ici et avait divergé de celle d'Étrave (un S&P « ES1… » était « autre »).
# C'est celle d'Étrave (pont.instrument_de), la même que InstrumentOf() de l'EA.
instrument = pont.instrument_de


def vers_paris_ny(jour, hhmm):
    """« 09:35 » à New York, le jour donné → datetime à Paris. V-02 : une heure abîmée (« 15h50 ») lève ValueError, que charger()
    transforme en JourneeIncomplete (la séance est signalée, les autres jours continuent)."""
    h, m = (int(x) for x in hhmm.split(":")[:2])
    return datetime.datetime(jour.year, jour.month, jour.day, h, m, tzinfo=NEW_YORK).astimezone(PARIS)


def vers_paris_ms(ms):
    """Millisecondes UTC (colonnes entree_utc_ms / sortie_utc_ms) → datetime à Paris ; None si vide. V-02 : une valeur absurde
    (hors des dates possibles) lève ValueError, jamais OverflowError ni OSError."""
    v = export.nombre(ms)
    if not v:
        return None
    try:
        return datetime.datetime.fromtimestamp(v / 1000, tz=datetime.timezone.utc).astimezone(PARIS)
    except (OverflowError, OSError, ValueError):
        raise ValueError(f"heure en millisecondes impossible : {ms}")


# V-11 (audit du 27/11/2026) : `recap --testeur` racontait le Dow (DJI30, hors périmètre, fichiers d'un passage précédent du
# testeur : l'EA n'efface que les fichiers de son propre symbole) comme un troisième marché, compté dans le bilan. Seuls le Nasdaq et
# le S&P 500 sont lus.
MARCHES_LUS = ("nasdaq", "sp500")
_CACHE = {}


def lire(dossier, base):
    """Les lignes d'un journal de l'EA (`<base>-*.csv`), seulement pour le Nasdaq et le S&P 500. V-22 : gardées en mémoire tant que
    les fichiers ne changent pas (un récap du mois relisait tous les journaux pour chacune de ses séances)."""
    import glob
    fichiers = sorted(glob.glob(os.path.join(dossier, f"{base}-*.csv")))
    empreinte = []
    for f in fichiers:
        try:
            st = os.stat(f)
            empreinte.append((f, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    cle = (os.path.abspath(dossier), base)
    if cle not in _CACHE or _CACHE[cle][0] != empreinte:
        lignes, _ = export.lire_journal(dossier, base)
        _CACHE[cle] = (empreinte, [x for x in lignes if instrument(x.get("symbole", "")) in MARCHES_LUS])
    return _CACHE[cle][1]


def jours_finis(dossier):
    """Les jours (dates de New York) dont la séance est finie (ligne « fin »), du plus ancien au plus récent."""
    return sorted({export.jour_de(s["jour_ny"]) for s in lire(dossier, "seances") if s.get("moment") == "fin" and export.jour_de(s["jour_ny"])})


def premier_jour(dossier):
    """Le premier jour (New York) qui a une ligne dans le journal des séances (« decision » ou « fin »), ou None. V-12 : pas de récap
    d'une semaine ou d'un mois commencés avant."""
    jours = [export.jour_de(s["jour_ny"]) for s in lire(dossier, "seances")]
    jours = [j for j in jours if j]
    return min(jours) if jours else None


def seances_manquantes(dossier, debut, fin, decisions=None, avec_calendrier=True):
    """Les séances qui manquent aux journaux entre `debut` et `fin` (dates de New York, séances déjà dues) : [(jour, symbole ou
    None, cause)]. Un jour acquitté (`decisions` : « accepter » ou « ignorer ») n'est pas compté.

    V-03 (audit du 27/11/2026) : un marché qui a une ligne « decision » ou des positions dans le journal d'exécution ce jour-là,
    mais pas de ligne « fin » (MetaTrader arrêté avant 15:52 New York, plantage) : la perte du jour disparaissait de la semaine.
    V-01, avec le calendrier de l'EA (calendrier.py) : un jour de séance sans aucune ligne « fin » (MetaTrader fermé, EA arrêté,
    « JOUR MANQUÉ » de l'EA, qui n'écrit alors aucune ligne), et un marché qui tournait la séance d'avant mais n'a rien écrit ce
    jour-là (un seul graphique arrêté)."""
    import calendrier
    decisions = decisions or {}
    seances, executions = lire(dossier, "seances"), lire(dossier, "execution")
    fins, vus, trades_j = {}, {}, {}
    for s in seances:
        j = export.jour_de(s.get("jour_ny"))
        if j:
            vus.setdefault(j, set()).add(s["symbole"])
            if s.get("moment") == "fin":
                fins.setdefault(j, set()).add(s["symbole"])
    for e in executions:
        j = export.jour_de(e.get("jour_ny"))
        if j:
            trades_j.setdefault(j, {}).setdefault(e["symbole"], 0)
            trades_j[j][e["symbole"]] += 1
    res = []
    jours = sorted(set(list(vus) + list(trades_j)) | (set(calendrier.jours_de_seance(debut, fin)) if avec_calendrier else set()))
    precedent = set()            # les marchés de la séance précédente (ligne « fin »)
    for j in sorted(d for d in fins if d < debut)[-1:]:
        precedent = fins[j]
    for j in jours:
        if not debut <= j <= fin:
            continue
        if decisions.get(j.isoformat()) in ("accepter", "ignorer"):
            precedent = fins.get(j, precedent)
            continue
        finis_j = fins.get(j, set())
        manque = False
        for symbole in sorted((vus.get(j, set()) | set(trades_j.get(j, {}))) - finis_j):
            n = trades_j.get(j, {}).get(symbole, 0)
            res.append((j, symbole, f"{symbole} : pas de ligne « fin » dans le journal des séances"
                        + (f", alors que le journal d'exécution a {n} position(s)" if n else "")
                        + " (MetaTrader arrêté avant 15:52 New York ?)"))
            manque = True
        if avec_calendrier and calendrier.jour_de_seance(j):
            if not finis_j and not manque:
                res.append((j, None, "aucune séance dans les journaux (MetaTrader fermé, EA arrêté ou « JOUR MANQUÉ » de l'EA)"))
            elif finis_j:
                for symbole in sorted(precedent - finis_j - vus.get(j, set())):
                    res.append((j, symbole, f"{symbole} : aucune ligne ce jour-là, alors qu'il tournait la séance d'avant (graphique "
                                            "fermé, EA retiré ou « JOUR MANQUÉ » ?)"))
        if finis_j:
            precedent = finis_j
    return res


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
        # le chemin du prix pendant la position (ticks et M1 lus par l'EA) : le plus loin en notre faveur (mfe), contre nous (mae),
        # et la distance du stop ; en points du symbole, vides si l'EA n'a pas pu les mesurer
        "mfe": export.nombre(e.get("mfe_prix")), "mae": export.nombre(e.get("mae_prix")), "risque": export.nombre(e.get("risque_prix")),
    }


def charger(dossier, jour=None, bougies_requises=True, accepter=False):
    """La journée `jour` (date de New York ; par défaut la dernière séance finie) : un dictionnaire prêt à raconter.

    marches : un par symbole qui a une ligne « fin » ce jour-là, Nasdaq puis S&P 500 ; chacun avec sa zone, ses bougies (heure de
    Paris), ses positions (dans l'ordre d'entrée) et ses totaux (points, R, argent, % du solde si le journal des trades est là).
    bougies_requises=False : pour les récaps de la semaine et du mois, qui n'ont besoin que des résultats.
    accepter (V-09, `outil.py accepter --jour`) : la séance est prise telle que les journaux la donnent, le journal d'exécution
    faisant foi (positions sans ligne « fin », écart avec le journal des trades du compte).
    avertissements : ce que le journal du mode automatique doit dire (versions de journal différentes, V-11).
    """
    if not os.path.isdir(dossier):
        raise JourneeIncomplete(f"Dossier des journaux introuvable : {dossier}")
    try:
        return _charger(dossier, jour, bougies_requises, accepter)
    except (ValueError, TypeError, KeyError) as err:
        # V-02 (audit du 27/11/2026) : une ligne abîmée au bon nombre de colonnes (heure « 15h50 », milliseconde absurde) levait
        # ValueError hors du mode automatique : plus aucune vidéo, même pour les jours sains, sans notification.
        raise JourneeIncomplete(f"journal abîmé pour la séance du {jour.isoformat() if jour else '?'} ({type(err).__name__} : {err}) : "
                                "corrige ou retire la ligne, ou `outil.py ignorer --jour` pour passer ce jour")


def _charger(dossier, jour, bougies_requises, accepter):
    seances = lire(dossier, "seances")
    finis = jours_finis(dossier)
    executions = lire(dossier, "execution")
    if jour and accepter and jour not in finis and any(e.get("jour_ny") == jour.isoformat() for e in executions):
        finis = sorted(finis + [jour])         # V-09 : séance acceptée telle quelle, positions sans ligne « fin »
    if not finis:
        raise JourneeIncomplete("Aucune séance finie dans ce dossier : l'EA écrit la ligne « fin » quelques minutes après la sortie "
                                "de fin de journée (vers 21:52 à Paris).")
    jour = jour or finis[-1]
    if jour not in finis:
        derniers = ", ".join(j.isoformat() for j in finis[-5:])
        raise JourneeIncomplete(f"La séance du {jour.isoformat()} n'est pas finie dans les journaux (pas de ligne « fin »). "
                                f"Dernières séances finies : {derniers}.")
    cle = jour.isoformat()
    # V-03 : un marché avec une ligne « decision » ou des positions ce jour-là, mais sans ligne « fin » (MetaTrader arrêté avant
    # 15:52 New York) : la journée racontée sans lui serait fausse (sa perte disparaîtrait).
    avec_fin = {x["symbole"] for x in seances if x["jour_ny"] == cle and x.get("moment") == "fin"}
    sans_fin = ({x["symbole"] for x in seances if x["jour_ny"] == cle} | {e["symbole"] for e in executions if e.get("jour_ny") == cle}) - avec_fin
    if sans_fin and not accepter:
        raise JourneeIncomplete(f"{', '.join(sorted(sans_fin))} le {cle} : pas de ligne « fin » dans le journal des séances (MetaTrader "
                                "arrêté avant 15:52 New York ?) : la journée racontée sans ce marché serait fausse. `outil.py accepter "
                                "--jour` la prend telle quelle (journal d'exécution), `outil.py ignorer --jour` la passe.")
    bougies = lire(dossier, "bougies")
    trades = pont.lire_trades(dossier)
    marches, sources, versions = [], set(), set()
    for s in sorted(avec_fin | (sans_fin if accepter else set())):
        lignes = [x for x in seances if x["jour_ny"] == cle and x["symbole"] == s]
        fins = [x for x in lignes if x["moment"] == "fin"]
        fin = fins[-1] if fins else {}
        sources.update(x.get("source", "") for x in lignes)
        # V-19 (audit du 27/11/2026) : BougiesRow écrit deux fois le même jour (ligne « fin » réécrite après un redémarrage) donnait
        # 166 bougies au lieu de 83, la journée dessinée deux fois. Une bougie par heure (la dernière écrite), dans l'ordre.
        par_heure = {}
        for x in bougies:
            if x["jour_ny"] == cle and x["symbole"] == s:
                par_heure[x["heure_ny"]] = x
        b = [par_heure[h] for h in sorted(par_heure)]
        versions.update(x.get("version", "") for x in lignes + b)
        versions.update(e.get("version", "") for e in executions if e.get("jour_ny") == cle and e.get("symbole") == s)
        if not b and bougies_requises:
            raise JourneeIncomplete(f"Pas de bougies pour {s} le {cle} : l'EA qui tournait ce jour-là n'écrivait pas encore le journal "
                                    "des bougies (bougies-<symbole>.csv). Installe l'EA de cette version, le récap marchera dès la séance suivante.")
        bas, haut = export.nombre(fin.get("range_bas")), export.nombre(fin.get("range_haut"))
        positions = sorted((_position(e) for e in executions if e.get("jour_ny") == cle and e.get("symbole") == s),
                           key=lambda p: p["entree"] or datetime.datetime.max.replace(tzinfo=PARIS))
        du_jour = [t for t in trades if t["date"].replace(".", "-") == cle and t["symbole"] == s]
        net_trades, net_exec = sum(t["net"] for t in du_jour), sum(p["net"] or 0.0 for p in positions)
        # la règle de l'export trimestriel : le journal d'exécution doit retrouver le journal des trades (à 0,05 près) ; une séance
        # acceptée telle quelle (V-09) garde le journal d'exécution
        if du_jour and abs(net_trades - net_exec) > 0.05 and not accepter:
            raise JourneeIncomplete(f"{s} le {cle} : le journal d'exécution ne retrouve pas le journal des trades "
                                    f"({len(positions)} position(s) pour {net_exec:.2f}, contre {len(du_jour)} trade(s) pour {net_trades:.2f}). "
                                    "MetaTrader s'est peut-être arrêté avant d'écrire l'exécution : la vidéo raconterait une autre séance.")
        if not positions and "terminé" in fin.get("etat", ""):
            raise JourneeIncomplete(f"{s} le {cle} : la séance dit qu'un trade a eu lieu, mais le journal d'exécution n'a aucune position "
                                    "(MetaTrader arrêté avant de l'écrire ?). Pas de vidéo « pas de trade » pour une séance tradée.")
        pct = [t["pct"] for t in du_jour if t["pct"] is not None]
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
    avertissements = []
    if len(versions - {""}) > 1:
        avertissements.append(f"versions de journal différentes le {cle} ({', '.join(sorted(versions - {''}))}) : un fichier vient peut-être "
                              "d'un autre EA ou d'un passage plus ancien du testeur")
    nets = [m["net"] for m in marches if m["positions"]]
    net = sum(nets) if nets and all(n is not None for n in nets) else None
    return {
        "jour": jour, "source": "testeur" if "testeur" in sources else ("reel" if "reel" in sources else (sorted(sources - {""}) or [""])[0]),
        "marches": marches, "net": net,
        # la photo de l'onglet Historique de MetaTrader prise le soir même (historique.py), s'il y en a une
        "historique": next((c for c in [os.path.join(dossier, "captures", f"historique-{cle}.png")] if os.path.exists(c)), None),
        "verdict": None if net is None else ("positive" if net > 0 else "négative" if net < 0 else "neutre"),
        "trades": sum(len(m["positions"]) for m in marches),
        "avertissements": avertissements,
    }
