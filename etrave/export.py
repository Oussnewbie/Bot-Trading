"""Export trimestriel : les performances et l'exécution de l'EA, un dossier par trimestre, pour les analyser ensuite.

L'EA écrit, dans le dossier commun de MetaTrader (`…\\Common\\Files\\Etrave`), trois journaux par symbole :
    trades-<symbole>.csv      un trade clôturé par ligne (sans en-tête, colonnes de pont.COLONNES_TRADE)
    execution-<symbole>.csv   une position fermée par ligne : prix visé et obtenu, spread, stop, excursions, frais (en-tête)
    seances-<symbole>.csv     une ligne « decision » à 9:35 et une ligne « fin » après la sortie, trade ou non (en-tête)
Les journaux du testeur de stratégie vont dans le sous-dossier `testeur\\` : ils ne sont jamais exportés ici.

`exporter()` écrit `<dossier_exports>/<trimestre>/`, « Étrave exports » sur le Bureau depuis le 27/11/2026 (2027-T1 = janvier à mars 2027, dates de New York) : les lignes du trimestre, un résumé
lisible (resume.md), le même en données (resume.json) et la description des colonnes (colonnes.md). Le dossier est construit sous un
nom provisoire puis renommé : on ne voit jamais un export à moitié écrit. `exporter_trimestres_finis()` fait l'export de chaque
trimestre terminé qui n'en a pas encore ; Étrave l'appelle au démarrage puis toutes les 6 heures.
"""
import datetime
import glob
import json
import math
import os
import shutil
import statistics
import threading
import time

import pont

SOUS_DOSSIER = "exports"                # ancien emplacement, gardé quand l'ordinateur n'a pas de Bureau
NOM_BUREAU = "Étrave exports"           # demande de l'utilisateur du 27/11/2026 : exports et journaux sur le Bureau
SOUS_DOSSIER_JOURNAUX = "journaux"
JOURNAUX_COPIES = ("trades-*.csv", "execution-*.csv", "seances-*.csv", "alertes-*.csv")   # jamais reglages.txt : il a le jeton
MARGE_JOURS = 3            # un trimestre est terminé 3 jours après sa fin : sa dernière séance a eu le temps d'être écrite
# Interrupteur du robot, jugé marché par marché (ET-16) sur les 60 derniers jours de trade de chaque marché.
JOURS_INTERRUPTEUR = 60
GAGNANT_R = 0.05           # un jour est gagnant au-delà de +0,05 R (comme le résumé)
# AUD-09 (audit du 26/11/2026) : seuils PAR MARCHÉ, recalculés pour la V11. Avant : moins de 28 % de jours gagnants, total pire
# que −40 R, baisse de plus de 66 R, calculés pour la V10 et pour un seul marché.
# Règle, appliquée à etrave/reference.json (la V11 rejouée, une ligne par marché et par jour de trade) : sur toutes les fenêtres
# glissantes de 60 jours de trade du marché, pire total × 1,25, pire baisse × 1,25, pire part de jours gagnants − 5 points
# (seuils_depuis_reference ; etrave/test_export.py les recalcule depuis reference.json).
# Ces seuils viennent de données déjà vues (l'historique qui a servi à mettre la stratégie au point) : des repères, et
# pas une preuve. Un seuil franchi dit « coupe ce marché et fais le point », pas « la stratégie ne marche plus ».
SEUILS_INTERRUPTEUR = {
    "nasdaq": {"jours_gagnants_min_pct": 26.67, "total_min_r": -14.54, "baisse_max_r": 23.88},
    "sp500": {"jours_gagnants_min_pct": 18.33, "total_min_r": -44.83, "baisse_max_r": 48.64},
}

COLONNES_DOC = {
    "execution": [
        ("source", "testeur, demo, reel ou concours"),
        ("id_position", "identifiant de la position chez le courtier"),
        ("jour_ny", "date de la séance, à New York"),
        ("entree", "A (cassure), A+ (ajout de pyramide de A), B, B+, D1 à D3, D1+…, « orpheline » si l'EA l'avait perdue de vue"),
        ("sens", "1 achat, -1 vente"),
        ("entree_utc_ms, sortie_utc_ms", "heures d'entrée et de sortie, en millisecondes UTC (pour rejoindre les prix du courtier)"),
        ("prix_vise", "niveau de la cassure (A), niveau guetté (D), prix du marché à la décision (B et ajouts) ; vide si inconnu"),
        ("glissement_entree", "(prix d'entrée − prix visé) × sens : positif = moins bon que visé"),
        ("spread_entree", "écart ask − bid au premier tick après l'entrée"),
        ("stop_initial, risque_prix", "stop posé à l'entrée et distance entrée-stop (1 R de cette position, en prix)"),
        ("stop_en_place", "stop chez le courtier au moment de la sortie ; stop_virtuel : celui que l'EA surveillait lui-même"),
        ("glissement_sortie", "pour une sortie au stop : (stop − prix de sortie) × sens, positif = moins bon que le stop"),
        ("raison, raison_courtier", "raison de la sortie selon l'EA, et selon le courtier (SL, TP, EA, manuel, stop_out)"),
        ("mfe_prix, mae_prix", "plus grand gain latent et plus grande perte latente avant la sortie, au prix qui fermerait la position"),
        ("mfe_r, mae_r", "les mêmes, en R de cette position (÷ risque_prix)"),
        ("excursion", "ticks (exact), ticks+M1 (bougies d'une minute au milieu ; vente : ask estimé), partiel (une partie manquait)"),
        ("frais, swap, resultat_net", "commission et frais, swap, résultat net en devise du compte"),
        ("r", "résultat net ÷ somme risquée par la cassure du jour (même R que le journal des trades)"),
        ("range_prix, stop_mult", "taille du range de 9:30 et multiple du stop du jour"),
        ("complet", "1 si l'entrée et la sortie sont dans l'historique, 0 sinon"),
    ],
    "seances": [
        ("moment", "decision (range de 9:30 traité, à 9:35) ou fin (après la sortie de fin de journée)"),
        ("range_bas, range_haut, range_prix", "le range de 9:30"),
        ("spread, cout_r", "spread au moment de la ligne, et (spread + 2 glissements supposés) ÷ risque du jour"),
        ("filtres", "filtres de la cassure (RSI, élan)"),
        ("etat", "ce que l'EA a décidé (decision) ou l'état du jour (fin)"),
    ],
}


# ───────────────────────── lecture des journaux ─────────────────────────
def lire_journal(dossier, base):
    """Les lignes des journaux `<base>-*.csv` du dossier (pas du sous-dossier du testeur), en dictionnaires. Une ligne qui n'a pas
    le nombre de colonnes de l'en-tête est ignorée, jamais devinée."""
    lignes, entete = [], None
    for chemin in sorted(glob.glob(os.path.join(dossier, f"{base}-*.csv"))):
        try:
            with open(chemin, "r", encoding="utf-8-sig", errors="replace") as f:
                texte = f.read().splitlines()
        except OSError:
            continue
        if not texte:
            continue
        colonnes = [c.strip() for c in texte[0].split(";")]
        if "version" not in colonnes:
            continue
        entete = entete or colonnes
        for ligne in texte[1:]:
            champs = [c.strip() for c in ligne.split(";")]
            if len(champs) == len(colonnes) and champs[0] != "version":
                lignes.append(dict(zip(colonnes, champs)))
    return lignes, entete


def nombre(valeur):
    """Un nombre fini, ou None (AUD-16 : « nan » ou « inf » d'un journal passaient en NaN dans resume.json)."""
    try:
        resultat = float(valeur) if valeur not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return resultat if resultat is not None and math.isfinite(resultat) else None


def jour_de(texte):
    try:
        return datetime.date.fromisoformat(str(texte)[:10].replace(".", "-"))
    except ValueError:
        return None


def aujourdhui_ny(maintenant=None):
    """La date du jour à New York. Correctif ET-10 (audit du 25/11/2026) : la date de l'ordinateur (Paris, le VPS) passait au
    lendemain six heures avant New York, et « Exporter le trimestre en cours » pouvait viser le trimestre neuf, encore vide.
    Sans zoneinfo (Python de Windows sans le paquet tzdata) : règle américaine de l'heure d'été, comme l'EA (UsDst)."""
    utc = maintenant or datetime.datetime.now(datetime.timezone.utc)
    annee = utc.year
    mars = datetime.datetime(annee, 3, 1, tzinfo=datetime.timezone.utc)
    novembre = datetime.datetime(annee, 11, 1, tzinfo=datetime.timezone.utc)
    # deuxième dimanche de mars et premier dimanche de novembre, à 2:00 heure de New York (7:00 puis 6:00 UTC)
    debut_ete = mars + datetime.timedelta(days=(6 - mars.weekday()) % 7 + 7, hours=7)
    fin_ete = novembre + datetime.timedelta(days=(6 - novembre.weekday()) % 7, hours=6)
    decalage = 4 if debut_ete <= utc < fin_ete else 5
    return (utc - datetime.timedelta(hours=decalage)).date()


# ───────────────────────── trimestres ─────────────────────────
def trimestre_de(jour):
    return f"{jour.year}-T{(jour.month - 1) // 3 + 1}"


def bornes(trimestre):
    annee, t = trimestre.split("-T")
    annee, t = int(annee), int(t)
    if not 1 <= t <= 4:
        raise ValueError(trimestre)
    debut = datetime.date(annee, 3 * t - 2, 1)
    fin = datetime.date(annee + (t == 4), 1 if t == 4 else 3 * t + 1, 1) - datetime.timedelta(days=1)
    return debut, fin


def termine(trimestre, aujourdhui):
    return aujourdhui > bornes(trimestre)[1] + datetime.timedelta(days=MARGE_JOURS)


def dossier_exports(dossier, env=None, existe=os.path.isdir):
    """Où vont les exports. `ETRAVE_EXPORTS` d'abord (essais), puis « Étrave exports » sur le Bureau (demande de l'utilisateur du
    27/11/2026 ; Mac : ~/Desktop, Windows : %USERPROFILE%\\Desktop), sinon l'ancien sous-dossier `exports` du dossier commun de
    MetaTrader (ordinateur sans Bureau)."""
    env = os.environ if env is None else env
    if env.get("ETRAVE_EXPORTS"):
        return env["ETRAVE_EXPORTS"]
    accueil = env.get("USERPROFILE") or env.get("HOME") or os.path.expanduser("~")
    bureau = os.path.join(accueil, "Desktop")
    return os.path.join(bureau, NOM_BUREAU) if existe(bureau) else os.path.join(dossier, SOUS_DOSSIER)


def copier_journaux(dossier, destination=None):
    """Demande de l'utilisateur du 27/11/2026 : une copie des journaux bruts de l'EA (trades, exécution, séances, alertes) dans
    « Étrave exports/journaux/ », refaite dès qu'un journal a changé. Rien ne se perd si MetaTrader est réinstallé. Jamais les
    réglages (ils contiennent le jeton Telegram), ni l'état, ni les journaux du testeur. Chaque fichier est copié sous un nom
    provisoire puis renommé : jamais de copie à moitié écrite. Retourne les noms copiés."""
    destination = destination or os.path.join(dossier_exports(dossier), SOUS_DOSSIER_JOURNAUX)
    copies = []
    for motif in JOURNAUX_COPIES:
        for source in sorted(glob.glob(os.path.join(dossier, motif))):
            nom = os.path.basename(source)
            cible = os.path.join(destination, nom)
            try:
                origine = os.stat(source)
                if os.path.exists(cible):
                    copie = os.stat(cible)
                    if copie.st_size == origine.st_size and copie.st_mtime >= origine.st_mtime:
                        continue
                os.makedirs(destination, exist_ok=True)
                shutil.copy2(source, cible + ".tmp")
                os.replace(cible + ".tmp", cible)
                copies.append(nom)
            except OSError:
                continue                    # fichier verrouillé un instant : recopié au passage suivant
    return copies


def exports_faits(dossier):
    """Les exports déjà écrits, du plus récent au plus ancien."""
    racine = dossier_exports(dossier)
    if not os.path.isdir(racine):
        return []
    faits = []
    for nom in sorted(os.listdir(racine), reverse=True):
        chemin = os.path.join(racine, nom)
        if nom.startswith(".") or not os.path.isfile(os.path.join(chemin, "resume.json")):
            continue
        try:
            with open(os.path.join(chemin, "resume.json"), "r", encoding="utf-8") as f:
                resume = json.load(f)
        except (OSError, ValueError):
            continue
        faits.append({"nom": nom, "chemin": chemin, "genere": resume.get("genere_le"), "en_cours": resume.get("en_cours", False),
                      "trades": resume.get("trades", {}).get("n", 0)})
    return faits


# ───────────────────────── résumé ─────────────────────────
def _baisse(valeurs):
    """Plus forte baisse d'une suite de résultats cumulés, depuis le plus haut précédent (0 au départ)."""
    cumul = sommet = pire = 0.0
    for v in valeurs:
        cumul += v
        sommet = max(sommet, cumul)
        pire = max(pire, sommet - cumul)
    return pire


def _arrondi(v, n=2):
    return None if v is None else round(v, n)


def _stats(valeurs, n=2):
    valeurs = [v for v in valeurs if v is not None]
    if not valeurs:
        return {"n": 0, "moyenne": None, "mediane": None, "pire": None}
    return {"n": len(valeurs), "moyenne": _arrondi(statistics.fmean(valeurs), n), "mediane": _arrondi(statistics.median(valeurs), n),
            "pire": _arrondi(max(valeurs), n)}


def classer_etat(texte):
    """La décision d'une séance, ramenée à une famille stable (les textes de l'EA contiennent des prix et des heures)."""
    t = (texte or "").strip()
    if t.startswith(("Achat stop", "Vente stop")) or (t.startswith("Achat ") and " Vente " in t):
        return "ordres posés"
    if t.startswith("Règle mémoire") or t.startswith("Signal sauté"):
        return "règle mémoire : signal non pris"
    if t.startswith("Pas de signal"):
        return "pas de signal"
    if t.startswith("Pas de trade"):
        raison = t.split(":", 1)[1].strip() if ":" in t else t
        for mot, famille in (("FOMC", "FOMC"), ("férié", "jour férié ou demi-séance"), ("coût", "coût trop lourd (garde-fou)"),
                             ("désactivé", "marché coupé dans Étrave"), ("heure du serveur", "heure du serveur fausse"),
                             ("bloqué", "filtres : aucun côté permis"), ("autre côté", "autre côté du range touché d'abord"),
                             ("pas de cassure", "pas de cassure avant 9:45"), ("trop loin", "prix déjà trop loin du niveau"),
                             ("refusée", "entrée refusée par le courtier"), ("taille", "taille impossible"), ("EA arrêté", "EA arrêté")):
            if mot in raison:
                return "pas de trade : " + famille
        return "pas de trade : " + raison[:60]
    if " terminé" in t or " en cours" in t:
        return "trade pris"
    return t[:60] or "inconnu"


def mesurer(r):
    """Les trois mesures de l'interrupteur sur une suite de résultats journaliers en R : part de jours gagnants (%), total, baisse."""
    return {"jours_gagnants_pct": 100.0 * sum(1 for v in r if v > GAGNANT_R) / len(r), "total_r": sum(r), "baisse_r": _baisse(r)}


def seuils_depuis_reference(trades_ref, jours=JOURS_INTERRUPTEUR):
    """AUD-09 : les seuils de chaque marché d'après reference.json ([date, marché, R du jour, range/prix]), avec la règle écrite au
    début de ce fichier. Sert à vérifier SEUILS_INTERRUPTEUR (et à les recalculer si reference.json change)."""
    seuils = {}
    for marche in sorted({t[1] for t in trades_ref}):
        par_jour = {}
        for date, m, r, _ in trades_ref:
            if m == marche:
                par_jour[date] = par_jour.get(date, 0.0) + r
        suite = [par_jour[d] for d in sorted(par_jour)]
        fenetres = [mesurer(suite[i:i + jours]) for i in range(len(suite) - jours + 1)]
        if fenetres:
            seuils[marche] = {"jours_gagnants_min_pct": round(min(f["jours_gagnants_pct"] for f in fenetres) - 5.0, 2),
                              "total_min_r": round(1.25 * min(f["total_r"] for f in fenetres), 2),
                              "baisse_max_r": round(1.25 * max(f["baisse_r"] for f in fenetres), 2)}
    return seuils


def interrupteur(trades, jusqua, seuils=None):
    """Les trois mesures de l'interrupteur sur les 60 derniers jours de trade jusqu'à `jusqua` (toutes les données connues), et les
    seuils franchis. `seuils` : ceux du marché (SEUILS_INTERRUPTEUR) ; None (marché inconnu) = les mesures sans verdict."""
    par_jour = {}
    for t in trades:
        j = jour_de(t["date"])
        if j and j <= jusqua and t.get("r") is not None:
            par_jour[j] = par_jour.get(j, 0.0) + t["r"]
    jours = sorted(par_jour)[-JOURS_INTERRUPTEUR:]
    r = [par_jour[j] for j in jours]
    if not r:
        return {"jours": 0}
    m = mesurer(r)
    franchi = []
    if seuils:
        franchi = [nom for nom, ok in (("jours gagnants", m["jours_gagnants_pct"] >= seuils["jours_gagnants_min_pct"]),
                                       ("total", m["total_r"] >= seuils["total_min_r"]),
                                       ("baisse", m["baisse_r"] <= seuils["baisse_max_r"])) if not ok]
    return {
        "jours": len(r), "complet": len(r) >= JOURS_INTERRUPTEUR,
        "jours_gagnants_pct": round(m["jours_gagnants_pct"], 1), "total_r": round(m["total_r"], 2), "baisse_r": round(m["baisse_r"], 2),
        "seuils": seuils, "franchi": franchi,
    }


def interrupteurs(trades, jusqua):
    """ET-16 (26/11/2026, décision de l'utilisateur) : l'interrupteur jugé marché par marché. Additionner le Nasdaq et le S&P le
    même jour faisait bouger le total environ deux fois plus vite, et pouvait dire « coupe le robot » alors que chaque marché
    restait dans sa norme. AUD-09 : chaque symbole est jugé avec les seuils de son marché (pont.instrument_de) ; un symbole d'un
    autre marché a ses mesures, sans verdict. {symbole: interrupteur(...) avec « marche »}."""
    symboles = sorted({t.get("symbole") or "?" for t in trades})
    resultat = {}
    for s in symboles:
        marche = pont.instrument_de(s)
        resultat[s] = {**interrupteur([t for t in trades if (t.get("symbole") or "?") == s], jusqua, SEUILS_INTERRUPTEUR.get(marche)),
                       "marche": marche}
    return resultat


def texte_interrupteur(symbole, i):
    """AUD-09 : le message Telegram d'un interrupteur franchi (sur 60 jours de trade)."""
    s = i["seuils"]
    nom = {"nasdaq": "Nasdaq", "sp500": "S&P 500"}.get(i.get("marche"), symbole)
    details = []
    if "jours gagnants" in i["franchi"]:
        details.append(f"{_pct(i['jours_gagnants_pct'])} de jours gagnants (seuil {_pct(s['jours_gagnants_min_pct'])})")
    if "total" in i["franchi"]:
        details.append(f"total {_txt(i['total_r'], ' R', True)} (seuil {_txt(s['total_min_r'], ' R', True)})")
    if "baisse" in i["franchi"]:
        details.append(f"baisse de {_txt(i['baisse_r'], ' R')} (seuil {_txt(s['baisse_max_r'], ' R')})")
    return (f"{pont.NOM} : interrupteur franchi sur {symbole} ({nom}), sur ses {i['jours']} derniers jours de trade : "
            f"{', '.join(details)}. Décoche ce marché dans {pont.NOM} et fais le point avant de le relancer.")


def resumer(trimestre, trades_tous, executions, seances, aujourdhui, en_cours):
    debut, fin = bornes(trimestre)
    dans = lambda j: j is not None and debut <= j <= fin
    trades = [t for t in trades_tous if dans(jour_de(t["date"]))]
    # trades et jours de trade (tous symboles réunis)
    par_jour_r, par_jour_net = {}, {}
    for t in trades:
        j = jour_de(t["date"])
        par_jour_r[j] = par_jour_r.get(j, 0.0) + (t["r"] or 0.0)
        par_jour_net[j] = par_jour_net.get(j, 0.0) + t["net"]
    jours = sorted(par_jour_r)
    r_jours, net_jours = [par_jour_r[j] for j in jours], [par_jour_net[j] for j in jours]
    resume = {
        "trimestre": trimestre, "debut": debut.isoformat(), "fin": fin.isoformat(), "en_cours": en_cours,
        "genere_le": aujourdhui.isoformat(),
        "sources": sorted({e.get("source", "") for e in executions + seances} - {""}),
        "symboles": sorted({t["symbole"] for t in trades} | {e.get("symbole", "") for e in executions + seances} - {""}),
        "trades": {
            "n": len(trades), "gagnants_pct": _arrondi(100.0 * sum(1 for t in trades if (t["r"] or 0) > 0.05) / len(trades), 1) if trades else None,
            "total_r": _arrondi(sum(t["r"] or 0 for t in trades)), "total_net": _arrondi(sum(t["net"] for t in trades)),
        },
        "jours": {
            "n": len(jours), "gagnants_pct": _arrondi(100.0 * sum(1 for v in r_jours if v > 0.05) / len(jours), 1) if jours else None,
            "pire_r": _arrondi(min(r_jours)) if jours else None, "pire_net": _arrondi(min(net_jours)) if jours else None,
            "meilleur_r": _arrondi(max(r_jours)) if jours else None,
            "baisse_max_r": _arrondi(_baisse(r_jours)), "baisse_max_net": _arrondi(_baisse(net_jours)),
        },
    }
    # exécution, par type d'entrée (A, A+, B, D1…)
    par_type = {}
    for e in executions:
        type_ = e.get("entree", "?").split(" ")[0] + (" orpheline" if "orpheline" in e.get("entree", "") else "")
        par_type.setdefault(type_, []).append(e)
    execution = {}
    for type_, lignes in sorted(par_type.items()):
        stop = [e for e in lignes if nombre(e.get("glissement_sortie")) is not None]
        execution[type_] = {
            "positions": len(lignes), "incompletes": sum(1 for e in lignes if e.get("complet") != "1"),
            "glissement_entree": _stats([nombre(e.get("glissement_entree")) for e in lignes], 3),
            "spread_entree": _stats([nombre(e.get("spread_entree")) for e in lignes], 3),
            "sorties_au_stop": len(stop),
            "glissement_sortie_stop": _stats([nombre(e.get("glissement_sortie")) for e in stop], 3),
            "mfe_r": _stats([nombre(e.get("mfe_r")) for e in lignes]), "mae_r": _stats([nombre(e.get("mae_r")) for e in lignes]),
            "total_r": _arrondi(sum(nombre(e.get("r")) or 0 for e in lignes)),
            "total_net": _arrondi(sum(nombre(e.get("resultat_net")) or 0 for e in lignes)),
            "frais": _arrondi(sum((nombre(e.get("frais")) or 0) + (nombre(e.get("swap")) or 0) for e in lignes)),
        }
    resume["execution"] = execution
    # séances : décisions de 9:35, et ce que sont devenus les jours à ordres posés sans trade
    decisions = [s for s in seances if s.get("moment") == "decision"]
    familles = {}
    for s in decisions:
        famille = classer_etat(s.get("etat"))
        familles[famille] = familles.get(famille, 0) + 1
    fins = {(s.get("jour_ny"), s.get("symbole")): s for s in seances if s.get("moment") == "fin"}
    avec_exec = {(e.get("jour_ny"), e.get("symbole")) for e in executions}
    sans_trade = {}
    for s in decisions:
        cle = (s.get("jour_ny"), s.get("symbole"))
        if classer_etat(s.get("etat")) == "ordres posés" and cle not in avec_exec and cle in fins:
            famille = classer_etat(fins[cle].get("etat"))
            sans_trade[famille] = sans_trade.get(famille, 0) + 1
    # jours de semaine sans ligne « decision » (jour férié, ou EA arrêté), par symbole présent dans le trimestre
    manquants = {}
    derniere = min(fin, aujourdhui)
    for symbole in sorted({s.get("symbole") for s in seances}):
        vus = {jour_de(s.get("jour_ny")) for s in decisions if s.get("symbole") == symbole}
        j, liste = debut, []
        while j <= derniere:
            if j.weekday() < 5 and j not in vus:
                liste.append(j.isoformat())
            j += datetime.timedelta(days=1)
        manquants[symbole] = liste
    resume["seances"] = {"decisions": len(decisions), "familles": dict(sorted(familles.items(), key=lambda kv: -kv[1])),
                         "ordres_poses_sans_trade": sans_trade, "jours_de_semaine_sans_seance": manquants}
    # rapprochement : par jour et par symbole, le journal d'exécution doit retrouver le journal des trades
    net_trades, net_exec = {}, {}
    for t in trades:
        cle = (jour_de(t["date"]).isoformat(), t["symbole"])
        net_trades[cle] = net_trades.get(cle, 0.0) + t["net"]
    for e in executions:
        cle = (e.get("jour_ny"), e.get("symbole"))
        net_exec[cle] = net_exec.get(cle, 0.0) + (nombre(e.get("resultat_net")) or 0.0)
    ecarts = [{"jour": j, "symbole": s, "trades": round(net_trades.get((j, s), 0.0), 2), "execution": round(net_exec.get((j, s), 0.0), 2)}
              for (j, s) in sorted(set(net_trades) | set(net_exec))
              if (j, s) in net_exec and abs(net_trades.get((j, s), 0.0) - net_exec[(j, s)]) > 0.05]
    sans_journal = sorted(f"{j} {s}" for (j, s) in net_trades if (j, s) not in net_exec)
    resume["rapprochement"] = {"ecarts": ecarts, "jours_sans_journal_execution": sans_journal}
    resume["interrupteur"] = interrupteurs(trades_tous, min(fin, aujourdhui))
    return resume


# ───────────────────────── écriture ─────────────────────────
def _txt(v, unite="", signe=False, decimales=2):
    if v is None:
        return "—"
    s = f"{v:+.{decimales}f}" if signe else f"{v:.{decimales}f}"
    return s.replace(".", ",").replace("-", "−") + unite


def _pct(v):
    return _txt(v, " %", decimales=1)


def _liste(elements, n=10):
    """Une liste lisible : les n premiers, puis le nombre total (la liste complète est dans resume.json)."""
    return ", ".join(elements[:n]) + (f" … ({len(elements)} au total)" if len(elements) > n else "")


def resume_lisible(r):
    t, j = r["trades"], r["jours"]
    lignes = [f"# Strategy V11, {r['trimestre']} ({r['debut']} au {r['fin']}{', en cours' if r['en_cours'] else ''})", "",
              f"Généré le {r['genere_le']}. Sources : {', '.join(r['sources']) or '—'}. Symboles : {', '.join(r['symboles']) or '—'}.", "",
              "## Résultats", "",
              f"- Trades : {t['n']}, dont {_pct(t['gagnants_pct'])} gagnants ; total {_txt(t['total_r'], ' R', True)}, {_txt(t['total_net'], ' $', True)}.",
              f"- Jours de trade : {j['n']}, dont {_pct(j['gagnants_pct'])} gagnants. Pire jour {_txt(j['pire_r'], ' R', True)} ({_txt(j['pire_net'], ' $', True)}),"
              f" meilleur jour {_txt(j['meilleur_r'], ' R', True)}.",
              f"- Pire baisse du trimestre : {_txt(j['baisse_max_r'], ' R')} ({_txt(j['baisse_max_net'], ' $')}).", "",
              "## Exécution par type d'entrée", "",
              "Glissement et spread en prix du symbole (points d'indice) ; glissement positif = moins bon que le prix visé.", "",
              "| Entrée | Positions | Glissement d'entrée moyen / pire | Spread moyen | Sorties au stop | Glissement au stop moyen / pire | MFE moyen | MAE moyen | Total |",
              "|---|---|---|---|---|---|---|---|---|"]
    for type_, e in r["execution"].items():
        ge, gs = e["glissement_entree"], e["glissement_sortie_stop"]
        incompletes = f" ({e['incompletes']} incomplètes)" if e["incompletes"] else ""
        lignes.append(f"| {type_} | {e['positions']}{incompletes} | "
                      f"{_txt(ge['moyenne'])} / {_txt(ge['pire'])} | {_txt(e['spread_entree']['moyenne'])} | {e['sorties_au_stop']} | "
                      f"{_txt(gs['moyenne'])} / {_txt(gs['pire'])} | {_txt(e['mfe_r']['moyenne'], ' R')} | {_txt(e['mae_r']['moyenne'], ' R')} | "
                      f"{_txt(e['total_r'], ' R', True)} |")
    if not r["execution"]:
        lignes.append("| — | 0 | | | | | | | |")
    s = r["seances"]
    lignes += ["", "## Séances", "", f"Décisions de 9:35 : {s['decisions']}."]
    lignes += [f"- {famille} : {n}" for famille, n in s["familles"].items()]
    if s["ordres_poses_sans_trade"]:
        lignes += ["", "Jours à ordres posés finis sans trade :"] + [f"- {f} : {n}" for f, n in s["ordres_poses_sans_trade"].items()]
    for symbole, liste in s["jours_de_semaine_sans_seance"].items():
        if liste:
            lignes += ["", f"Jours de semaine sans séance pour {symbole} (jour férié, ou EA arrêté) : {_liste(liste)}."]
    rap = r["rapprochement"]
    lignes += ["", "## Contrôles", ""]
    lignes.append("- Journal d'exécution et journal des trades : " + ("d'accord jour par jour." if not rap["ecarts"] else
                  f"{len(rap['ecarts'])} écart(s) : " + ", ".join(f"{e['jour']} {e['symbole']} ({_txt(e['trades'])} contre {_txt(e['execution'])})" for e in rap["ecarts"]) + "."))
    if rap["jours_sans_journal_execution"]:
        lignes.append(f"- Jours de trade sans journal d'exécution (EA plus ancien) : {_liste(rap['jours_sans_journal_execution'])}.")
    for symbole, i in r["interrupteur"].items():          # ET-16 : chaque marché à part
        if not i.get("jours"):
            continue
        seuils = i.get("seuils")
        if not seuils:                                     # AUD-09 : marché inconnu, pas de seuil
            lignes.append(f"- Interrupteur {symbole} : marché inconnu, pas de seuil. Sur ses {i['jours']} derniers jours de trade : "
                          f"{_pct(i['jours_gagnants_pct'])} de jours gagnants, total {_txt(i['total_r'], ' R', True)}, baisse {_txt(i['baisse_r'], ' R')}.")
            continue
        # Correctif ET-11 (audit du 25/11/2026) : avant 60 jours de trade, un seuil dépassé disait « coupe le robot » (deux jours
        # perdants suffisaient). Les seuils se jugent sur 60 jours : avant, ce n'est qu'une indication.
        if not i["franchi"]:
            verdict = "Aucun seuil franchi."
        elif i["complet"]:
            verdict = "SEUIL FRANCHI : " + ", ".join(i["franchi"]) + f" : coupe {symbole} et fais le point."
        else:
            verdict = "Au-delà du seuil pour l'instant : " + ", ".join(i["franchi"]) + " (à juger sur 60 jours de trade)."
        lignes.append(f"- Interrupteur {symbole}, sur ses {i['jours']} derniers jours de trade{'' if i['complet'] else ' (moins de 60 : indicatif)'} : "
                      f"{_pct(i['jours_gagnants_pct'])} de jours gagnants (seuil {_pct(seuils['jours_gagnants_min_pct'])}), "
                      f"total {_txt(i['total_r'], ' R', True)} (seuil {_txt(seuils['total_min_r'], ' R', True)}), "
                      f"baisse {_txt(i['baisse_r'], ' R')} (seuil {_txt(seuils['baisse_max_r'], ' R')}). " + verdict)
    lignes += ["", "Ces chiffres sont ceux d'un trimestre : assez pour mesurer l'exécution (glissement, spread), trop peu pour juger la stratégie.", ""]
    return "\n".join(lignes)


def colonnes_lisibles():
    lignes = ["# Colonnes des fichiers de cet export", "", "Séparateur « ; », point décimal, prix dans l'unité du symbole, heures de New York sauf mention UTC.",
              "trades.csv : le journal des trades de l'EA (sortie en secondes UTC, date et heure de New York, symbole, sens, lots, R, résultat net,"
              " solde avant, raison, pyramide, devise).", ""]
    for fichier, colonnes in COLONNES_DOC.items():
        lignes += [f"## {fichier}.csv", ""] + [f"- `{nom}` : {texte}" for nom, texte in colonnes] + [""]
    return "\n".join(lignes)


def _ecrire_csv(chemin, entete, lignes):
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write(";".join(entete) + "\r\n")
        for ligne in lignes:
            f.write(";".join(str(ligne.get(c, "")) for c in entete) + "\r\n")


# Correctif ET-12 (audit du 25/11/2026) : un export à la fois. Un double clic sur « Exporter » lançait deux fils sur le même
# dossier provisoire (l'un l'effaçait pendant que l'autre écrivait).
_VERROU_EXPORT = threading.Lock()


def _remplacer(source, cible):
    """os.replace, avec de nouveaux essais : sous Windows, renommer un dossier échoue tant qu'un fichier dedans est ouvert
    (Excel, l'antivirus, l'indexeur)."""
    for essai in range(20):
        try:
            os.replace(source, cible)
            return
        except PermissionError:
            if essai == 19:
                raise
            time.sleep(0.25)


def exporter(dossier, trimestre, aujourdhui=None):
    """Écrit exports/<trimestre>/ (remplace un export existant du même trimestre). Retourne (chemin, résumé)."""
    with _VERROU_EXPORT:
        return _exporter(dossier, trimestre, aujourdhui)


def _exporter(dossier, trimestre, aujourdhui=None):
    aujourdhui = aujourdhui or aujourdhui_ny()
    debut, fin = bornes(trimestre)
    en_cours = not termine(trimestre, aujourdhui)
    dans = lambda texte: (lambda j: j is not None and debut <= j <= fin)(jour_de(texte))
    trades_tous = pont.lire_trades(dossier)
    executions, entete_exec = lire_journal(dossier, "execution")
    seances, entete_seances = lire_journal(dossier, "seances")
    executions = [e for e in executions if e.get("source") != "testeur" and dans(e.get("jour_ny"))]
    seances = [s for s in seances if s.get("source") != "testeur" and dans(s.get("jour_ny"))]
    resume = resumer(trimestre, trades_tous, executions, seances, aujourdhui, en_cours)
    racine = dossier_exports(dossier)
    os.makedirs(racine, exist_ok=True)
    final = os.path.join(racine, trimestre)
    provisoire = os.path.join(racine, f".{trimestre}.{os.getpid()}.provisoire")
    shutil.rmtree(provisoire, ignore_errors=True)
    os.makedirs(provisoire)
    colonnes_trades = list(pont.COLONNES_TRADE)
    _ecrire_csv(os.path.join(provisoire, "trades.csv"), colonnes_trades,
                [dict(zip(colonnes_trades, (t["sortie"], t["date"], t["heure"], t["symbole"], t["sens"], t["lots"], t["r"], t["net"],
                                            t["soldeAvant"], t["raison"], "1" if t["pyramide"] else "0", t["devise"])))
                 for t in trades_tous if dans(t["date"])])
    if entete_exec:
        _ecrire_csv(os.path.join(provisoire, "execution.csv"), entete_exec, executions)
    if entete_seances:
        _ecrire_csv(os.path.join(provisoire, "seances.csv"), entete_seances, seances)
    with open(os.path.join(provisoire, "resume.json"), "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2, allow_nan=False)   # AUD-16 : jamais de NaN dans le JSON
    with open(os.path.join(provisoire, "resume.md"), "w", encoding="utf-8") as f:
        f.write(resume_lisible(resume))
    with open(os.path.join(provisoire, "colonnes.md"), "w", encoding="utf-8") as f:
        f.write(colonnes_lisibles())
    # remplacement d'un seul coup : l'ancien export est écarté, le nouveau prend sa place, puis l'ancien est effacé
    ancien = None
    if os.path.exists(final):
        ancien = os.path.join(racine, f".{trimestre}.{os.getpid()}.ancien")
        shutil.rmtree(ancien, ignore_errors=True)
        _remplacer(final, ancien)
    _remplacer(provisoire, final)
    if ancien:
        shutil.rmtree(ancien, ignore_errors=True)
    return final, resume


def trimestres_avec_donnees(dossier):
    jours = {jour_de(t["date"]) for t in pont.lire_trades(dossier)}
    for base in ("execution", "seances"):
        lignes, _ = lire_journal(dossier, base)
        jours |= {jour_de(l.get("jour_ny")) for l in lignes if l.get("source") != "testeur"}
    return sorted({trimestre_de(j) for j in jours if j})


def exporter_trimestres_finis(dossier, aujourdhui=None):
    """Exporte chaque trimestre terminé qui a des données et pas encore d'export. Retourne les trimestres exportés."""
    aujourdhui = aujourdhui or aujourdhui_ny()
    faits = {e["nom"] for e in exports_faits(dossier) if not e["en_cours"]}
    nouveaux = []
    for trimestre in trimestres_avec_donnees(dossier):
        if termine(trimestre, aujourdhui) and trimestre not in faits:
            exporter(dossier, trimestre, aujourdhui)
            nouveaux.append(trimestre)
    return nouveaux
