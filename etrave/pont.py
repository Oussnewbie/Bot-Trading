"""Le pont entre l'interface Étrave et l'EA MetaTrader 5.

L'EA et l'interface ne se parlent que par des fichiers texte rangés dans le dossier commun de MetaTrader
(`…\\MetaQuotes\\Terminal\\Common\\Files\\Etrave`), le seul endroit que les deux peuvent lire et écrire :

    reglages.txt          écrit par l'interface, lu par l'EA toutes les 2 secondes
    etat-<symbole>.txt    écrit par chaque EA (un par graphique), lu par l'interface
    trades-<symbole>.csv  une ligne par trade clôturé, ajoutée par l'EA

Format : une ligne `cle=valeur` par réglage. Une clé absente de reglages.txt laisse à l'EA la valeur saisie dans
MetaTrader ; les noms de clés sont les mêmes dans robot/Strategy-V11.mq5 (etrave/test_interface.py vérifie l'accord).

Règles reprises de Vigie :
 - tout est validé AVANT d'écrire quoi que ce soit ;
 - les secrets (jeton et discussion Telegram) sont en ÉCRITURE SEULE : aucune fonction d'ici ne les renvoie à la page,
   qui sait seulement « renseigné » ou « vide » ;
 - une demande (clôture, essai) porte l'heure de sa création : l'EA ignore une demande vieille de plus de 2 minutes,
   un fichier oublié ne peut donc jamais fermer un trade futur.
"""
import glob
import math
import os
import re
import sys
import threading
import time

NOM = "Étrave"
SLOGAN = "la cassure de l’ouverture de New York"
SOUS_DOSSIER = "Etrave"
FICHIER_REGLAGES = "reglages.txt"

# Bornes du risque par trade, en % du solde (les mêmes dans l'EA : RISK_MIN, RISK_MAX). AUD-05 (audit du 26/11/2026) : plafond
# de 1 %, remonté à 20 % par décision de l'utilisateur du 27/11/2026 (« pour des tests », tous comptes) ; une valeur enregistrée
# au-dessus est ramenée au plafond par l'EA, et montrée ainsi par la page.
RISQUE_MIN, RISQUE_MAX = 0.05, 20.0
# Au-delà de ce risque, il faut confirmer en toutes lettres (AUD-05 : 0,5 %, avant 1 %). La page lit ce seuil ici (bornes).
RISQUE_A_CONFIRMER = 0.5
LEVIER_MAX = 2000.0
# L'EA réécrit son état toutes les 2 secondes : passé ce délai sans nouvelle, il est arrêté (ou MT5 fermé).
EA_MUET_S = 15.0
# Les deux marchés de la V11 (verrou du 25/11/2026, reconduit en V11 le 26/11/2026), une case chacun : l'EA classe son symbole « nasdaq » ou « sp500 »
# (InstrumentOf) et ne lit que sa case. Décochée, l'EA ne prend plus de nouveau trade.
INSTRUMENTS = {"nasdaq": True, "sp500": True}
# AUD-09 (audit du 26/11/2026) : le marché d'un symbole des journaux, comme InstrumentOf() dans l'EA (mêmes noms, même ordre ;
# etrave/test_interface.py vérifie l'accord). Les seuils de l'interrupteur sont par marché, les journaux par symbole.
NOMS_MARCHES = {"nasdaq": ("NAS", "NDX", "NQ", "USTEC", "US100", "USATECH", "TECH100"),
                "sp500": ("SPX", "SP500", "US500", "USA500", "S&P", "SPI500")}
DEBUTS_MARCHES = {"nasdaq": (), "sp500": ("ES1",)}      # noms qui doivent ouvrir le symbole (StringFind(...) == 0 dans l'EA)


def instrument_de(symbole):
    """« nasdaq », « sp500 » ou « autre », comme InstrumentOf() dans l'EA."""
    texte = str(symbole or "").upper()
    for marche, noms in NOMS_MARCHES.items():
        if any(nom in texte for nom in noms) or any(texte.startswith(debut) for debut in DEBUTS_MARCHES[marche]):
            return marche
    return "autre"
# Mots à taper pour confirmer : AUD-01 (compte réel), AUD-10 (arrêt d'urgence), AUD-19 (fermer MetaTrader quand l'EA ne répond plus
# alors que son dernier état disait un trade en cours).
MOTS = {"risque": "RISQUE", "cloturer": "CLOTURER", "reel": "REEL", "arret": "ARRET", "fermer": "FERMER"}
# AUD-01 : numéro d'un compte réel autorisé (reel_autorise), des chiffres seulement (fullmatch, ET-09).
LOGIN_REEL = re.compile(r"\d{1,20}")

REGLES = {
    "telegram_jeton": (re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{30,60}$"),
                       "Jeton Telegram : il a la forme 123456789:AA… (des chiffres, deux-points, puis une longue suite de "
                       "lettres et chiffres), tel que donné par @BotFather."),
    "telegram_discussion": (re.compile(r"^-?\d{4,20}$"),
                            "Discussion Telegram : c’est un nombre (négatif pour un groupe). Le bouton « Trouver ma "
                            "discussion » le remplit pour toi."),
}
SYMBOLE = re.compile(r"[A-Za-z0-9._#+-]{1,40}")   # fullmatch (ET-09) : « $ » acceptait un « \n » final


class Refus(Exception):
    """Une demande refusée : le message est fait pour être montré tel quel, et ne répète jamais une valeur secrète."""


def dossier_commun(env=None, systeme=sys.platform, existe=os.path.isdir):
    """Le dossier partagé avec l'EA. `ETRAVE_DOSSIER` passe avant tout (essais, MetaTrader installé ailleurs).

    Correctif du 26/11/2026 : sur Mac, MetaTrader 5 tourne dans le Wine de MetaQuotes et l'EA écrit dans le dossier commun de
    ce Wine (drive_c/users/<utilisateur>/AppData/Roaming/…). Étrave lisait ~/.etrave : ses réglages n'atteignaient pas l'EA."""
    env = os.environ if env is None else env
    if env.get("ETRAVE_DOSSIER"):
        return env["ETRAVE_DOSSIER"]
    if env.get("APPDATA"):
        return os.path.join(env["APPDATA"], "MetaQuotes", "Terminal", "Common", "Files", SOUS_DOSSIER)
    maison = env.get("HOME") or os.path.expanduser("~")
    if systeme == "darwin" and env.get("USER"):
        commun = os.path.join(maison, "Library", "Application Support", "net.metaquotes.wine.metatrader5", "drive_c", "users",
                              env["USER"], "AppData", "Roaming", "MetaQuotes", "Terminal", "Common")
        if existe(commun):
            return os.path.join(commun, "Files", SOUS_DOSSIER)
    return os.path.join(maison, ".etrave")


# ───────────────────────── fichiers cle=valeur ─────────────────────────
def lire_cles(chemin, strict=False):
    """Les lignes `cle=valeur` d'un fichier ; {} s'il est absent ou illisible à cet instant (l'EA est en train d'écrire).

    strict : pour un fichier qu'on va réécrire. Un fichier qui existe mais reste illisible lève Refus au lieu de rendre {} :
    réécrire à partir de {} effacerait toutes les autres clés (correctif ET-02 / ET-03 de la revue du 17/11/2026)."""
    texte = None
    for essai in range(20 if strict else 1):
        try:
            with open(chemin, "r", encoding="utf-8-sig", errors="replace") as f:
                texte = f.read()
            break
        except FileNotFoundError:
            return {}
        except OSError:
            if strict and essai < 19:
                time.sleep(0.05)
    if texte is None:
        if strict:
            raise Refus("Le fichier de réglages est occupé par MetaTrader : réessaie dans un instant.")
        return {}
    cles = {}
    for ligne in texte.splitlines():
        cle, egal, valeur = ligne.partition("=")
        if egal and cle.strip():
            cles[cle.strip()] = valeur.strip()
    return cles


def ecrire_cles(chemin, cles):
    """Écriture d'un seul coup : fichier provisoire puis remplacement. Sous Windows le remplacement échoue pendant la
    fraction de seconde où l'EA lit le fichier : on réessaie."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    provisoire = chemin + ".tmp"
    with open(provisoire, "w", encoding="utf-8", newline="") as f:
        f.write("".join(f"{cle}={valeur}\r\n" for cle, valeur in cles.items()))
    try:
        os.chmod(provisoire, 0o600)
    except OSError:
        pass
    for essai in range(20):
        try:
            os.replace(provisoire, chemin)
            return
        except PermissionError:
            if essai == 19:
                raise
            time.sleep(0.05)


def lire_reglages(dossier):
    """Tout le fichier de réglages, secrets compris : usage interne, ne jamais le renvoyer à la page."""
    return lire_cles(os.path.join(dossier, FICHIER_REGLAGES))


# Une seule modification à la fois : la page envoie ses demandes sur plusieurs fils (serveur multi-fils), et deux
# lectures-réécritures simultanées perdraient l'une des deux.
_VERROU = threading.Lock()


def _modifier(dossier, changements):
    """Applique des changements (valeur None = retirer la clé). Retourne les clés réellement modifiées."""
    with _VERROU:
        return _modifier_sans_verrou(dossier, changements)


def _modifier_sans_verrou(dossier, changements):
    cles = lire_cles(os.path.join(dossier, FICHIER_REGLAGES), strict=True)
    changees = []
    for cle, valeur in changements.items():
        if valeur is None:
            if cle in cles:
                del cles[cle]
                changees.append(cle)
        elif cles.get(cle) != valeur:
            cles[cle] = valeur
            changees.append(cle)
    if changees:
        cles["version"] = "1"
        ecrire_cles(os.path.join(dossier, FICHIER_REGLAGES), cles)
    return changees


# ───────────────────────── réglages : risque, levier, instruments ─────────────────────────
def _nombre(texte):
    """Un nombre fini, ou None. AUD-16 (audit du 26/11/2026) : « nan » ou « inf » passaient en NaN dans le JSON de la page
    (illisible par le navigateur), et int(inf) faisait planter la lecture du journal des trades."""
    try:
        valeur = float(str(texte).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return valeur if math.isfinite(valeur) else None


def _decimal(valeur):
    return f"{valeur:.4f}".rstrip("0").rstrip(".")


def reglages_publics(dossier):
    """Ce que la page peut savoir des réglages : jamais le jeton ni la discussion Telegram."""
    cles = lire_reglages(dossier)
    risque, levier = _nombre(cles.get("risque_pct")), _nombre(cles.get("levier"))
    # AUD-05 : comme l'EA, une valeur au-dessus du plafond vaut le plafond ; risqueEnregistre garde la valeur du fichier pour
    # que la page explique « Réglé à 35 %, ramené au plafond de 20 % ».
    valable = risque is not None and risque >= RISQUE_MIN - 1e-9
    return {
        "risquePct": min(risque, RISQUE_MAX) if valable else None,
        "risqueEnregistre": risque if valable else None,
        "levier": levier if levier is not None and 1 <= levier <= LEVIER_MAX else None,
        "instruments": {nom: (cles[nom] == "1") if cles.get(nom) in ("0", "1") else defaut for nom, defaut in INSTRUMENTS.items()},
        # AUD-01 : le compte réel autorisé (son numéro n'est pas un secret ; le jeton Telegram, lui, n'est jamais renvoyé)
        "reelAutorise": cles["reel_autorise"] if LOGIN_REEL.fullmatch(cles.get("reel_autorise", "")) else "",
        "telegramJeton": cles.get("telegram_jeton", "") != "",
        "telegramDiscussion": cles.get("telegram_discussion", "") != "",
        # compte et serveur du dernier lancement (jamais le mot de passe), et les deux automatismes de lancement
        "mt5Login": cles.get("mt5_login", ""), "mt5Serveur": cles.get("mt5_serveur", ""), "mt5Auto": cles.get("mt5_auto") == "1",
        "bornes": {"risqueMin": RISQUE_MIN, "risqueMax": RISQUE_MAX, "risqueAConfirmer": RISQUE_A_CONFIRMER, "levierMax": LEVIER_MAX},
    }


def regler(dossier, proposition, confirmation=""):
    """Enregistre le risque, le levier et les cases des instruments. Retourne les clés modifiées.

    - risquePct : entre RISQUE_MIN et RISQUE_MAX ; au-delà de RISQUE_A_CONFIRMER, seulement avec le mot RISQUE.
    - levier    : celui du courtier sur l'instrument (20 pour 1:20) ; None ou 0 = laisser MetaTrader calculer seul.
    - nasdaq, sp500 : true ou false (l'interrupteur des nouveaux trades de ce marché).
    """
    if not isinstance(proposition, dict):
        raise Refus("Demande illisible.")
    actuels = reglages_publics(dossier)
    changements = {}
    for cle, valeur in proposition.items():
        if cle == "risquePct":
            risque = _nombre(valeur) if not isinstance(valeur, bool) else None
            if risque is None or not (RISQUE_MIN - 1e-9 <= risque <= RISQUE_MAX + 1e-9):
                raise Refus(f"Le risque par trade doit être entre {_decimal(RISQUE_MIN)} % et {_decimal(RISQUE_MAX)} % du solde.")
            if risque > RISQUE_A_CONFIRMER + 1e-9 and risque > (actuels["risquePct"] or 0) + 1e-9 and confirmation != MOTS["risque"]:
                raise Refus(f"Au-delà de {_decimal(RISQUE_A_CONFIRMER)} % par trade, confirme en tapant {MOTS['risque']}.")
            changements["risque_pct"] = _decimal(risque)
        elif cle == "levier":
            if valeur in (None, "", 0, "0"):
                changements["levier"] = None
                continue
            levier = _nombre(valeur) if not isinstance(valeur, bool) else None
            if levier is None or not (1 <= levier <= LEVIER_MAX):
                raise Refus(f"Le levier est un nombre entre 1 et {_decimal(LEVIER_MAX)} : 20 pour un levier de 1:20.")
            changements["levier"] = _decimal(levier)
        elif cle in INSTRUMENTS:
            if not isinstance(valeur, bool):
                raise Refus("Une case est cochée ou décochée, rien d’autre.")
            changements[cle] = "1" if valeur else "0"
        else:
            raise Refus("Ce réglage ne se modifie pas par ce chemin.")
    return _modifier(dossier, changements)


# ───────────────────────── connexions : Telegram ─────────────────────────
def enregistrer_connexions(dossier, valeurs):
    """Enregistre le jeton et la discussion Telegram (chaîne vide = effacer). Retourne les clés modifiées."""
    if not isinstance(valeurs, dict):
        raise Refus("Demande illisible.")
    changements = {}
    for cle, valeur in valeurs.items():
        if cle not in REGLES:
            raise Refus("Ce réglage ne se modifie pas par ce chemin.")
        if not isinstance(valeur, str):
            raise Refus("Valeur illisible.")
        motif, message = REGLES[cle]
        valeur = valeur.strip()
        if valeur != "" and not motif.fullmatch(valeur):
            raise Refus(message)
        changements[cle] = valeur or None
    return _modifier(dossier, changements)


def retenir_mt5(dossier, login=None, serveur=None, auto=None):
    """Retient le compte et le serveur du dernier lancement (pas le mot de passe) et l'ouverture automatique."""
    changements = {}
    if login is not None:
        changements["mt5_login"] = login
    if serveur is not None:
        changements["mt5_serveur"] = serveur
    if auto is not None:
        changements["mt5_auto"] = "1" if auto else "0"
    return _modifier(dossier, changements)


# ───────────────────────── demandes à l'EA ─────────────────────────
def demander_essai_mt5(dossier, maintenant=None):
    """Demande à l'EA d'envoyer lui-même un message d'essai sur Telegram. Retourne le numéro de la demande."""
    numero = str(int(time.time() if maintenant is None else maintenant))
    _modifier(dossier, {"essai_telegram": numero})
    return numero


def demander_cloture(dossier, symbole, confirmation, maintenant=None):
    """Demande à l'EA du symbole de fermer ses positions au marché (et d'annuler ses ordres du jour).

    La demande va dans une clé propre au symbole (cloturer_<symbole>) : deux demandes rapprochées pour deux marchés ne
    s'effacent plus (revue cloud du 25/11/2026). La clé commune « cloturer » est écrite aussi, pour un EA d'avant ce
    correctif ; l'EA à jour lit les deux et n'exécute qu'une fois une même demande."""
    if confirmation != MOTS["cloturer"]:
        raise Refus("Confirmation manquante.")
    if not isinstance(symbole, str) or not SYMBOLE.fullmatch(symbole):
        raise Refus("Symbole inconnu.")
    numero = str(int(time.time() if maintenant is None else maintenant))
    _modifier(dossier, {f"cloturer_{symbole}": f"{numero};{symbole}", "cloturer": f"{numero};{symbole}"})
    return numero


def arret_urgence(dossier, symboles, confirmation, maintenant=None):
    """AUD-10 (audit du 26/11/2026) : arrêt d'urgence, avec le mot ARRET. Les deux marchés sont décochés (plus aucun nouveau
    trade) et la clôture est demandée à l'EA de chaque symbole de `symboles` (ceux dont l'EA est en marche), en une seule
    écriture du fichier : l'EA lit les deux à la fois. Un symbole illisible n'empêche ni l'arrêt ni les autres clôtures.
    Retourne (numéro de la demande, symboles dont la clôture est demandée, symboles écartés)."""
    if confirmation != MOTS["arret"]:
        raise Refus(f"Pour l’arrêt d’urgence, tape {MOTS['arret']}.")
    numero = str(int(time.time() if maintenant is None else maintenant))
    changements = {nom: "0" for nom in INSTRUMENTS}
    fermes, ecartes = [], []
    for symbole in symboles:
        if isinstance(symbole, str) and SYMBOLE.fullmatch(symbole):
            changements[f"cloturer_{symbole}"] = f"{numero};{symbole}"
            changements["cloturer"] = f"{numero};{symbole}"          # l'ancienne clé, pour un EA d'avant les clés par symbole
            fermes.append(symbole)
        else:
            ecartes.append(str(symbole))
    _modifier(dossier, changements)
    return numero, fermes, ecartes


def autoriser_compte_reel(dossier, login, confirmation, etats):
    """AUD-01 (audit du 26/11/2026) : l'EA ne prend aucun trade sur un compte réel tant que reglages.txt ne contient pas
    `reel_autorise=<son numéro de compte>`. Étrave l'écrit seulement avec le mot REEL, et seulement pour le numéro d'un EA en
    marche sur un compte réel (état `compte_type=reel`) : on n'autorise jamais un compte qu'on ne voit pas. Retourne les clés
    modifiées."""
    if confirmation != MOTS["reel"]:
        raise Refus(f"Pour autoriser un compte réel, tape {MOTS['reel']}.")
    if not isinstance(login, str) or not LOGIN_REEL.fullmatch(login):
        raise Refus("Numéro de compte illisible : ce sont des chiffres uniquement.")
    if not any(e.get("en_marche") and e.get("compte_type") == "reel" and e.get("compte_login") == login for e in etats):
        raise Refus("Aucun EA en marche sur ce compte réel : ouvre MetaTrader 5 sur ce compte, puis réessaie.")
    return _modifier(dossier, {"reel_autorise": login})


def retirer_autorisation_reel(dossier):
    """AUD-01 : retire l'autorisation du compte réel (l'EA arrête de prendre de nouveaux trades sur ce compte)."""
    return _modifier(dossier, {"reel_autorise": None})


# ───────────────────────── ce que dit l'EA ─────────────────────────
NOMBRES = ("solde", "capital", "marge_libre", "levier_compte", "levier_symbole", "risque_pct", "range_bas", "range_haut",
           "pos_sens", "pos_entree", "pos_stop", "pos_lots", "pos_resultat", "pos_r", "risque_argent", "solde_depart",
           "stats_n", "stats_gagnants", "stats_r", "stats_baisse", "stats_serie", "jambes", "v8_resultat", "lots_fixes",
           # AUD-24 (audit du 26/11/2026) : lot minimum, pas de volume, argent par point de prix et par lot, prix (bid)
           "lot_min", "lot_pas", "valeur_point_lot", "prix")
DRAPEAUX = ("actif", "connecte", "trading_auto", "horloge_ok", "regles_test", "position", "pos_pyramide", "attente", "telegram")


def lire_etats(dossier, maintenant=None):
    """L'état de chaque EA (un par graphique), le plus récent d'abord pour un même instrument."""
    maintenant = time.time() if maintenant is None else maintenant
    etats = []
    for chemin in sorted(glob.glob(os.path.join(dossier, "etat-*.txt"))):
        cles = lire_cles(chemin)
        if not cles.get("symbole"):
            continue
        try:
            age = maintenant - os.path.getmtime(chemin)
        except OSError:
            continue
        etat = dict(cles)
        for cle in NOMBRES:
            etat[cle] = _nombre(cles.get(cle))
        for cle in DRAPEAUX:
            etat[cle] = cles.get(cle) == "1"
        # AUD-01 : 0 = compte réel pas autorisé, l'EA ne prend aucun trade. Clé absente (EA plus ancien) : None, ni oui ni non.
        etat["compte_autorise"] = {"1": True, "0": False}.get(cles.get("compte_autorise"))
        etat["age_s"] = round(age, 1)
        etat["en_marche"] = age < EA_MUET_S
        etats.append(etat)
    ordre = list(INSTRUMENTS)
    etats.sort(key=lambda e: (ordre.index(e["instrument"]) if e.get("instrument") in ordre else len(ordre), e["symbole"]))
    return etats


COLONNES_TRADE = ("sortie", "date", "heure", "symbole", "sens", "lots", "r", "net", "solde_avant", "raison", "pyramide", "devise")


def lire_trades(dossier):
    """Les trades clôturés, du plus ancien au plus récent. Une ligne abîmée est ignorée, jamais devinée."""
    trades = []
    for chemin in glob.glob(os.path.join(dossier, "trades-*.csv")):
        try:
            with open(chemin, "r", encoding="utf-8-sig", errors="replace") as f:
                lignes = f.read().splitlines()
        except OSError:
            continue
        for ligne in lignes:
            champs = ligne.split(";")
            if len(champs) != len(COLONNES_TRADE):
                continue
            t = dict(zip(COLONNES_TRADE, (c.strip() for c in champs)))
            sortie, lots, r, net, solde = (_nombre(t[c]) for c in ("sortie", "lots", "r", "net", "solde_avant"))
            if sortie is None or net is None or t["sens"] not in ("1", "-1"):
                continue
            trades.append({
                "sortie": int(sortie), "date": t["date"], "heure": t["heure"], "symbole": t["symbole"], "sens": int(t["sens"]),
                "lots": lots, "r": r, "net": net, "soldeAvant": solde,
                "pct": (100 * net / solde) if solde and solde > 0 else None,
                "raison": t["raison"], "pyramide": t["pyramide"] == "1", "devise": t["devise"],
            })
    trades.sort(key=lambda t: t["sortie"])
    return trades


# Alertes de sécurité de l'EA (demande de l'utilisateur du 27/11/2026 : dans Étrave, plus sur Telegram). L'EA ajoute une ligne à
# alertes-<symbole>.csv : secondes UTC ; symbole ; texte.
COLONNES_ALERTE = ("quand", "symbole", "texte")
ALERTES_FENETRE_S = 24 * 3600      # affichées pendant 24 heures
ALERTES_MAX = 10
ALERTE_TEXTE_MAX = 400
ALERTES_LECTURE_MAX = 256 * 1024   # un vieux fichier n'est lu que par sa fin


def lire_alertes(dossier, maintenant=None):
    """Les alertes des dernières 24 heures, la plus récente d'abord (10 au plus). Une ligne abîmée est ignorée, jamais devinée."""
    maintenant = time.time() if maintenant is None else maintenant
    alertes = []
    for chemin in glob.glob(os.path.join(dossier, "alertes-*.csv")):
        try:
            with open(chemin, "rb") as f:
                f.seek(max(0, os.path.getsize(chemin) - ALERTES_LECTURE_MAX))
                lignes = f.read().decode("utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for ligne in lignes:
            champs = ligne.split(";", len(COLONNES_ALERTE) - 1)
            if len(champs) != len(COLONNES_ALERTE):
                continue
            quand, symbole, texte = _nombre(champs[0]), champs[1].strip(), champs[2].strip()
            # une heure dans le futur (horloge fausse) ou plus vieille que 24 h : pas affichée
            if quand is None or not (maintenant - ALERTES_FENETRE_S <= quand <= maintenant + 300) or not symbole or not texte:
                continue
            alertes.append({"quand": int(quand), "symbole": symbole[:32], "texte": texte[:ALERTE_TEXTE_MAX]})
    alertes.sort(key=lambda a: a["quand"], reverse=True)
    return alertes[:ALERTES_MAX]
