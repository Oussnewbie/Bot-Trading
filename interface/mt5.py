"""Lancer MetaTrader 5 et le connecter à un compte, depuis l'interface.

Un EA ne peut pas changer de compte : la connexion se fait au LANCEMENT de MetaTrader, avec un fichier de démarrage
(`terminal64.exe /config:fichier.ini`, section [Common] : Login, Password, Server). L'interface écrit ce fichier, lance
MetaTrader, puis l'efface une minute plus tard. MetaTrader garde ensuite le compte en mémoire (comme quand on coche
« Enregistrer le mot de passe ») : l'interface, elle, ne garde JAMAIS le mot de passe.

Garde-fous :
 - le programme lancé est toujours un `terminal64.exe` trouvé sur cet ordinateur (dossier indiqué par l'EA, ou
   Program Files) : une requête ne peut pas faire lancer autre chose ;
 - rien n'est lancé si MetaTrader est déjà ouvert : changer de compte avec un trade en cours le laisserait sans
   surveillance. Il faut d'abord fermer MetaTrader soi-même ;
 - le fichier de démarrage ne contient que la connexion : il n'attache aucun EA et n'active pas le trading
   automatique (deux EA sur le même symbole doubleraient les ordres).

Jamais exécuté sous Windows depuis cet environnement : seuls le contenu du fichier et les refus sont testés.
"""
import atexit
import glob
import os
import re
import subprocess
import sys
import tempfile
import threading

from pont import Refus

LOGIN = re.compile(r"^\d{3,15}$")
SERVEUR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}$")
MOT_DE_PASSE_MAX = 128
EFFACER_APRES_S = 60
PROGRAMME = "terminal64.exe"


def terminaux(etats, env=None, existe=os.path.isfile):
    """Les MetaTrader 5 installés : ceux qu'un EA a déjà signalés, puis ceux de Program Files."""
    env = os.environ if env is None else env
    candidats = [os.path.join(e["terminal"], PROGRAMME) for e in etats if e.get("terminal")]
    for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        if env.get(variable):
            candidats += sorted(glob.glob(os.path.join(env[variable], "*", PROGRAMME)))
    vus, trouves = set(), []
    for chemin in candidats:
        cle = os.path.normcase(os.path.normpath(chemin))
        if cle not in vus and existe(chemin):
            vus.add(cle)
            trouves.append(chemin)
    return trouves


def est_ouvert(systeme=sys.platform, executer=subprocess.run):
    """MetaTrader 5 tourne-t-il sur cet ordinateur ? None si on ne peut pas le savoir (autre système que Windows)."""
    if not systeme.startswith("win"):
        return None
    try:
        sortie = executer(["tasklist", "/FI", f"IMAGENAME eq {PROGRAMME}", "/NH"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return PROGRAMME in sortie.lower()


def texte_config(login, mot_de_passe, serveur):
    """Le fichier de démarrage : la connexion, et rien d'autre."""
    return f"[Common]\r\nLogin={login}\r\nPassword={mot_de_passe}\r\nServer={serveur}\r\nKeepPrivate=1\r\n"


def controler(login, mot_de_passe, serveur):
    """Refuse des identifiants mal formés. Les messages ne répètent jamais le mot de passe."""
    if not isinstance(login, str) or not LOGIN.match(login.strip()):
        raise Refus("Numéro de compte : ce sont des chiffres uniquement (le « login » donné par ton courtier).")
    if not isinstance(serveur, str) or not SERVEUR.match(serveur.strip()):
        raise Refus("Serveur : recopie le nom exact donné par ton courtier, par exemple « MonCourtier-Demo ».")
    if not isinstance(mot_de_passe, str) or not (1 <= len(mot_de_passe) <= MOT_DE_PASSE_MAX) or any(ord(c) < 32 for c in mot_de_passe):
        raise Refus("Mot de passe vide ou illisible.")
    return login.strip(), mot_de_passe, serveur.strip()


def lancer(chemin, connus, identifiants=None, ouvert=False, systeme=sys.platform, demarrer=subprocess.Popen, minuterie=threading.Timer):
    """Lance MetaTrader 5. `identifiants` = (login, mot de passe, serveur) pour se connecter à ce compte, None pour
    rouvrir MetaTrader tel qu'il était. `connus` : les terminaux trouvés par `terminaux()`."""
    if not systeme.startswith("win"):
        raise Refus("MetaTrader 5 ne se lance que sous Windows : ouvre l’interface sur l’ordinateur (ou le VPS) où il est installé.")
    if ouvert:
        raise Refus("MetaTrader 5 est déjà ouvert. Pour changer de compte, ferme-le d’abord toi-même (vérifie qu’aucun trade "
                    "n’est en cours), puis reviens ici.")
    if not connus:
        raise Refus("MetaTrader 5 introuvable sur cet ordinateur. Ouvre-le une première fois à la main et pose l’EA sur un "
                    "graphique : l’interface retiendra où il est installé.")
    if chemin not in connus:
        raise Refus("Ce programme n’est pas un MetaTrader 5 reconnu sur cet ordinateur.")
    commande = [chemin]
    if identifiants is not None:
        login, mot_de_passe, serveur = controler(*identifiants)
        descripteur, fichier = tempfile.mkstemp(prefix="etrave-", suffix=".ini")
        with os.fdopen(descripteur, "w", encoding="utf-16", newline="") as f:
            f.write(texte_config(login, mot_de_passe, serveur))
        commande.append(f"/config:{fichier}")

        def effacer():
            try:
                os.remove(fichier)
            except OSError:
                pass
        atexit.register(effacer)
        attente = minuterie(EFFACER_APRES_S, effacer)
        attente.daemon = True
        attente.start()
    try:
        demarrer(commande, cwd=os.path.dirname(chemin))
    except OSError:
        raise Refus("MetaTrader 5 n’a pas pu être lancé. Essaie de l’ouvrir à la main.") from None
    return {"lance": True, "connexion": identifiants is not None}
