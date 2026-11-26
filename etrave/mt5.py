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
 - le fichier de démarrage contient la connexion (si demandée), et le profil « Etrave-demo » avec le trading automatique
   quand ce profil est installé (26/11/2026) : ce profil dédié remplace les graphiques ouverts, ce qui évite deux EA sur un
   même symbole (ils doubleraient les ordres). Il n'est effacé tout de suite que s'il porte un mot de passe.

Autres automatismes : copier l'EA dans MetaTrader et le compiler (`installer_ea`, avec le compilateur MetaEditor livré
avec MetaTrader), ouvrir MetaTrader au démarrage d'Étrave, lancer Étrave au démarrage de Windows.

Jamais exécuté sous Windows depuis cet environnement : seuls le contenu des fichiers et les refus sont testés.

Sur Mac (26/11/2026, demande de l'utilisateur : « double-cliquer, tout se règle, je pilote tout depuis Étrave ») : MetaTrader 5
pour Mac tourne dans le Wine livré par MetaQuotes. Étrave y installe l'EA (copie et compilation) et le profil « Etrave-demo »
(deux graphiques M5, Nasdaq et S&P 500, la V11 sur chacun), lance MetaTrader sur ce profil AVEC le trading automatique, garde le
Mac éveillé tant qu'il tourne (caffeinate) et le ferme proprement (taskkill sans /F, pour que MetaTrader garde le profil).
Le démarrage attache donc l'EA : c'est le profil dédié qui évite un deuxième EA sur un symbole.

Sous Windows (même jour, VPS vierge : « cloner le dépôt, lancer Étrave, tout se configure ») : même chose. Le profil va dans le
dossier de données de MetaTrader (%APPDATA%\\MetaQuotes\\Terminal\\<id>), et le fichier de démarrage porte la connexion (si
demandée), le profil et le trading automatique. Jamais essayé sous Windows depuis ce Mac.
"""
import atexit
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from xml.sax.saxutils import escape

from pont import Refus

LOGIN = re.compile(r"\d{3,15}")   # fullmatch (ET-09)
SERVEUR = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]{1,63}")
MOT_DE_PASSE_MAX = 128
EFFACER_APRES_S = 60
PROGRAMME = "terminal64.exe"

# ───────────────────────── Mac : MetaTrader 5 pour Mac (Wine de MetaQuotes) ─────────────────────────
WINE = "/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine"
PREFIXE_WINE = os.path.expanduser("~/Library/Application Support/net.metaquotes.wine.metatrader5")
INSTALLATION_MAC = os.path.join(PREFIXE_WINE, "drive_c", "Program Files", "MetaTrader 5")
PROFIL = "Etrave-demo"
PROFIL_SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "robot", "mt5", "profil-Etrave-demo")
AGENT_MAC = "com.etrave.interface"


def est_mac(systeme=sys.platform):
    return systeme == "darwin"


def pilotable(systeme=sys.platform, existe=os.path.isfile):
    """Étrave peut-elle lancer et installer MetaTrader sur cet ordinateur ? Windows, ou Mac avec MetaTrader 5 pour Mac."""
    if systeme.startswith("win"):
        return True
    return est_mac(systeme) and existe(WINE) and existe(os.path.join(INSTALLATION_MAC, PROGRAMME))


def env_wine(env=None):
    e = dict(os.environ if env is None else env)
    e["WINEPREFIX"] = PREFIXE_WINE
    e["WINEDEBUG"] = "-all"
    return e


def chemin_windows(chemin):
    """Chemin vu par MetaTrader sous Wine : C:\\… dans le préfixe, sinon Z:\\… (la racine du Mac)."""
    racine = os.path.join(PREFIXE_WINE, "drive_c")
    if chemin.startswith(racine + os.sep):
        return "C:\\" + os.path.relpath(chemin, racine).replace("/", "\\")
    return "Z:" + chemin.replace("/", "\\")


def donnees_de(chemin, systeme=sys.platform, env=None):
    """Le dossier de données (celui qui contient MQL5) du MetaTrader `chemin`, ou None s'il n'existe pas encore."""
    installation = os.path.dirname(chemin)
    if est_mac(systeme):
        return installation
    return dossiers_de_donnees(env).get(os.path.normcase(os.path.normpath(installation)))


def ea_a_jour(donnees, source):
    """L'EA compilé dans MetaTrader est-il plus récent que la source du dépôt ?"""
    if not donnees:
        return True                                             # MetaTrader jamais ouvert : rien à mettre à jour
    programme = os.path.join(donnees, "MQL5", "Experts", "Etrave", os.path.basename(source)[:-4] + ".ex5")
    try:
        return os.path.getmtime(programme) >= os.path.getmtime(source)
    except OSError:
        return False


def installer_profil(donnees, source=PROFIL_SOURCE):
    """Copie le profil « Etrave-demo » du dépôt dans le dossier de données de MetaTrader (MetaTrader fermé). Le dossier ou None."""
    if not donnees or not os.path.isdir(source):
        return None
    cible = os.path.join(donnees, "MQL5", "Profiles", "Charts", PROFIL)
    os.makedirs(cible, exist_ok=True)
    for nom in sorted(os.listdir(source)):
        if nom.endswith((".chr", ".wnd")):
            shutil.copyfile(os.path.join(source, nom), os.path.join(cible, nom))
    return cible


def terminaux(etats, env=None, existe=os.path.isfile, systeme=sys.platform):
    """Les MetaTrader 5 installés : ceux qu'un EA a déjà signalés, puis ceux de Program Files. Sur Mac : celui de MetaTrader 5
    pour Mac (les dossiers signalés par l'EA y sont des chemins Windows du préfixe Wine)."""
    if est_mac(systeme):
        chemin = os.path.join(INSTALLATION_MAC, PROGRAMME)
        return [chemin] if existe(chemin) and existe(WINE) else []
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
    """MetaTrader 5 tourne-t-il sur cet ordinateur ? None si on ne peut pas le savoir (ni Windows ni Mac)."""
    if est_mac(systeme):
        try:
            return executer(["pgrep", "-f", PROGRAMME], capture_output=True, text=True, timeout=10).returncode == 0
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    if not systeme.startswith("win"):
        return None
    # Correctif ET-07 (audit du 25/11/2026) : tasklist écrit dans la page de code de la console (cp850 sur un Windows français),
    # pas en UTF-8. Un octet illisible (l'espace des milliers) levait UnicodeDecodeError à chaque rafraîchissement : erreur 500
    # et page « Interface arrêtée ». Les octets illisibles sont remplacés : seul le nom du programme compte.
    try:
        sortie = executer(["tasklist", "/FI", f"IMAGENAME eq {PROGRAMME}", "/NH"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=10).stdout
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return PROGRAMME in sortie.lower()


def dossiers_de_donnees(env=None):
    """Pour chaque MetaTrader installé, son dossier de données : {dossier d'installation: dossier de données}.
    MetaTrader range ses données dans %APPDATA%\\MetaQuotes\\Terminal\\<identifiant>, avec un fichier origin.txt qui dit
    de quelle installation il s'agit."""
    env = os.environ if env is None else env
    trouves = {}
    if not env.get("APPDATA"):
        return trouves
    for origine in glob.glob(os.path.join(env["APPDATA"], "MetaQuotes", "Terminal", "*", "origin.txt")):
        for encodage in ("utf-16", "utf-8-sig"):
            try:
                with open(origine, "r", encoding=encodage) as f:
                    installation = f.read().strip()
                break
            except (OSError, UnicodeError):
                installation = ""
        if installation:
            trouves[os.path.normcase(os.path.normpath(installation))] = os.path.dirname(origine)
    return trouves


def installer_ea(chemin, connus, source, env=None, systeme=sys.platform, executer=subprocess.run, ouvert=None):
    """Copie l'EA dans le dossier Experts de ce MetaTrader et le compile avec MetaEditor. Sur Mac, installe aussi le profil
    « Etrave-demo » si MetaTrader est fermé. Retourne ce qui s'est passé et les lignes du journal de compilation."""
    mac = est_mac(systeme)
    if not (systeme.startswith("win") or mac):
        raise Refus("L’installation dans MetaTrader 5 ne se fait que sous Windows ou sur un Mac avec MetaTrader 5 pour Mac.")
    if not connus or chemin not in connus:
        raise Refus("MetaTrader 5 introuvable sur cet ordinateur : installe-le, ouvre-le une fois, puis reviens ici.")
    installation = os.path.dirname(chemin)
    donnees = donnees_de(chemin, systeme, env)
    if not donnees:
        raise Refus("MetaTrader 5 n’a pas encore créé son dossier de données : ouvre-le une première fois, puis reviens ici.")
    cible = os.path.join(donnees, "MQL5", "Experts", "Etrave", os.path.basename(source))
    os.makedirs(os.path.dirname(cible), exist_ok=True)
    shutil.copyfile(source, cible)
    resultat = {"copie": True, "emplacement": os.path.join("MQL5", "Experts", "Etrave", os.path.basename(source)), "compile": None, "journal": []}
    editeur = os.path.join(installation, "metaeditor64.exe")
    if not os.path.isfile(editeur):
        resultat["journal"] = ["MetaEditor introuvable : ouvre l’EA dans MetaEditor et compile-le avec F7."]
        return resultat
    programme, journal = cible[:-4] + ".ex5", cible[:-4] + ".log"
    avant = os.path.getmtime(programme) if os.path.exists(programme) else 0.0
    resultat["profil"] = None if ouvert is not False else installer_profil(donnees)
    try:
        if mac:
            nom = os.path.basename(source)
            executer([WINE, chemin_windows(editeur), f"/compile:MQL5\\Experts\\Etrave\\{nom}", f"/log:MQL5\\Experts\\Etrave\\{nom[:-4]}.log"],
                     cwd=installation, env=env_wine(env), timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            executer([editeur, f"/compile:{cible}", f"/log:{journal}"], timeout=180)
    except (OSError, subprocess.SubprocessError):
        resultat["journal"] = ["MetaEditor n’a pas pu être lancé : ouvre l’EA dans MetaEditor et compile-le avec F7."]
        return resultat
    lignes = []
    for encodage in ("utf-16", "utf-8-sig"):
        try:
            with open(journal, "r", encoding=encodage) as f:
                lignes = [ligne.strip() for ligne in f.read().splitlines() if ligne.strip()]
            break
        except (OSError, UnicodeError):
            continue
    resultat["compile"] = os.path.exists(programme) and os.path.getmtime(programme) > avant
    utiles = [ligne for ligne in lignes if re.search(r"error|warning|erreur|avertissement|result|résultat", ligne, re.I)]
    resultat["journal"] = (utiles or lignes)[-40:]
    return resultat


def fichier_demarrage(env=None, systeme=sys.platform):
    """Le raccourci qui lance Étrave à l'ouverture de la session (Windows : dossier Démarrage ; Mac : agent launchd), ou None."""
    env = os.environ if env is None else env
    if est_mac(systeme):
        return os.path.join(env["HOME"], "Library", "LaunchAgents", AGENT_MAC + ".plist") if env.get("HOME") else None
    if not env.get("APPDATA"):
        return None
    return os.path.join(env["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "Etrave.bat")


def demarrage_windows(actif, dossier, env=None, systeme=sys.platform):
    """Pose ou retire le lancement d'Étrave à l'ouverture de la session (Windows ou Mac). dossier : celui d'Etrave.bat et
    d'Etrave.command (etrave/). Retourne l'état obtenu."""
    fichier = fichier_demarrage(env, systeme)
    if fichier is not None and est_mac(systeme):
        if actif:
            os.makedirs(os.path.dirname(fichier), exist_ok=True)
            commande = escape(os.path.join(dossier, "Etrave.command"))
            with open(fichier, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>\n'
                        f'<key>Label</key><string>{AGENT_MAC}</string>\n'
                        f'<key>ProgramArguments</key><array><string>/bin/sh</string><string>{commande}</string>'
                        '<string>--session</string></array>\n<key>RunAtLoad</key><true/>\n</dict></plist>\n')
        elif os.path.exists(fichier):
            os.remove(fichier)
        return os.path.exists(fichier)
    if fichier is None:
        raise Refus("Le lancement au démarrage ne se règle que sous Windows ou sur Mac.")
    if actif:
        os.makedirs(os.path.dirname(fichier), exist_ok=True)
        with open(fichier, "w", encoding="utf-8", newline="") as f:
            # Correctif ET-08 (audit du 25/11/2026) : fichier en UTF-8, lu par cmd.exe dans la page de code de la console ; sans
            # « chcp 65001 », un chemin accentué (C:\\Users\\Jérôme\\…) était mal lu et Étrave ne démarrait pas avec Windows.
            f.write(f'@echo off\r\nchcp 65001 >nul\r\nrem Lance Etrave (interface de l EA) a l ouverture de la session.\r\nstart "" /min "{os.path.join(dossier, "Etrave.bat")}" --sans-navigateur\r\n')
    elif os.path.exists(fichier):
        os.remove(fichier)
    return os.path.exists(fichier)


def texte_config(login, mot_de_passe, serveur):
    """Le fichier de démarrage : la connexion, et rien d'autre."""
    return f"[Common]\r\nLogin={login}\r\nPassword={mot_de_passe}\r\nServer={serveur}\r\nKeepPrivate=1\r\n"


def texte_config_profil(identifiants=None):
    """La connexion (si demandée), le profil « Etrave-demo » et le trading automatique activé."""
    connexion = texte_config(*identifiants) if identifiants else ""
    return (connexion + f"[Charts]\r\nProfileLast={PROFIL}\r\n"
            "[Experts]\r\nAllowLiveTrading=1\r\nAllowDllImport=0\r\nEnabled=1\r\nAccount=0\r\nProfile=0\r\n")


def controler(login, mot_de_passe, serveur):
    """Refuse des identifiants mal formés. Les messages ne répètent jamais le mot de passe."""
    if not isinstance(login, str) or not LOGIN.fullmatch(login.strip()):
        raise Refus("Numéro de compte : ce sont des chiffres uniquement (le « login » donné par ton courtier).")
    if not isinstance(serveur, str) or not SERVEUR.fullmatch(serveur.strip()):
        raise Refus("Serveur : recopie le nom exact donné par ton courtier, par exemple « MonCourtier-Demo ».")
    if not isinstance(mot_de_passe, str) or not (1 <= len(mot_de_passe) <= MOT_DE_PASSE_MAX) or any(ord(c) < 32 for c in mot_de_passe):
        raise Refus("Mot de passe vide ou illisible.")
    return login.strip(), mot_de_passe, serveur.strip()


def journal(message):
    """Où vont les messages de ce module. Étrave le remplace par son journal daté (main dans etrave.py)."""
    print(message, file=sys.stderr, flush=True)


# AUD-27 (audit du 26/11/2026) : fichiers de connexion (mot de passe en clair) qu'on n'a pas pu effacer. L'échec était avalé ;
# il est écrit dans le journal, et ces fichiers sont réessayés au lancement suivant (et au démarrage d'Étrave), quel que soit
# leur âge.
_A_EFFACER = set()
_VERROU_EFFACER = threading.Lock()


def _effacer_connexion(fichier):
    """Efface un fichier de connexion. True s'il n'existe plus ; sinon journalise (jamais le mot de passe) et le retient."""
    try:
        os.remove(fichier)
    except FileNotFoundError:
        pass
    except OSError as erreur:
        with _VERROU_EFFACER:
            _A_EFFACER.add(fichier)
        journal(f"Fichier de connexion à MetaTrader pas effacé ({type(erreur).__name__}) : {fichier}. Il contient le mot de passe "
                "du compte : nouvel essai au prochain lancement de MetaTrader depuis Étrave ; s'il reste, efface-le à la main.")
        return False
    with _VERROU_EFFACER:
        _A_EFFACER.discard(fichier)
    return True


def effacer_connexions_oubliees(dossier=None, maintenant=None):
    """Efface les fichiers de connexion (mot de passe en clair) qu'un arrêt brutal d'Étrave a laissés dans le dossier temporaire.

    Revue cloud du 25/11/2026 : fermer la fenêtre d'Étrave (ou éteindre Windows) dans la minute qui suit un lancement tue le
    programme avant la minuterie et atexit. On efface donc aussi, au démarrage et avant chaque lancement, tout fichier
    etrave-*.ini plus vieux que EFFACER_APRES_S : MetaTrader l'a lu depuis longtemps. Retourne le nombre de fichiers effacés."""
    dossier = tempfile.gettempdir() if dossier is None else dossier
    maintenant = time.time() if maintenant is None else maintenant
    effaces = 0
    with _VERROU_EFFACER:
        a_reessayer = sorted(_A_EFFACER)
    for fichier in a_reessayer:                                 # AUD-27 : les échecs précédents d'abord, quel que soit leur âge
        if os.path.exists(fichier) and _effacer_connexion(fichier):
            effaces += 1
        elif not os.path.exists(fichier):
            with _VERROU_EFFACER:
                _A_EFFACER.discard(fichier)
    for fichier in glob.glob(os.path.join(dossier, "etrave-*.ini")):
        try:
            vieux = maintenant - os.path.getmtime(fichier) >= EFFACER_APRES_S
        except OSError:                                         # déjà effacé entre-temps
            continue
        if vieux and _effacer_connexion(fichier):
            effaces += 1
    return effaces


def lancer(chemin, connus, identifiants=None, ouvert=False, systeme=sys.platform, demarrer=subprocess.Popen, minuterie=threading.Timer,
           env=None):
    """Lance MetaTrader 5. `identifiants` = (login, mot de passe, serveur) pour se connecter à ce compte, None pour
    rouvrir MetaTrader tel qu'il était. `connus` : les terminaux trouvés par `terminaux()`."""
    mac = est_mac(systeme)
    if not (systeme.startswith("win") or mac):
        raise Refus("MetaTrader 5 ne se lance que sous Windows ou sur un Mac avec MetaTrader 5 pour Mac : ouvre l’interface sur "
                    "l’ordinateur (ou le VPS) où il est installé.")
    if ouvert:
        raise Refus("MetaTrader 5 est déjà ouvert. Pour changer de compte, ferme-le d’abord toi-même (vérifie qu’aucun trade "
                    "n’est en cours), puis reviens ici.")
    if not connus:
        raise Refus("MetaTrader 5 introuvable sur cet ordinateur. Ouvre-le une première fois à la main et pose l’EA sur un "
                    "graphique : l’interface retiendra où il est installé.")
    if chemin not in connus:
        raise Refus("Ce programme n’est pas un MetaTrader 5 reconnu sur cet ordinateur.")
    commande = [WINE, chemin_windows(chemin)] if mac else [chemin]
    effacer_connexions_oubliees()
    donnees = donnees_de(chemin, systeme, env)
    if donnees and not os.path.isdir(os.path.join(donnees, "MQL5", "Profiles", "Charts", PROFIL)):
        installer_profil(donnees)
    # MetaTrader jamais ouvert (pas de dossier de données) : pas de profil à ouvrir, seulement la connexion.
    profil = bool(donnees) and os.path.isdir(os.path.join(donnees, "MQL5", "Profiles", "Charts", PROFIL))
    if identifiants is not None or profil:
        verifies = controler(*identifiants) if identifiants is not None else None
        descripteur, fichier = tempfile.mkstemp(prefix="etrave-", suffix=".ini")
        with os.fdopen(descripteur, "w", encoding="utf-16", newline="") as f:
            f.write(texte_config_profil(verifies) if profil else texte_config(*verifies))
        commande.append(f"/config:{chemin_windows(fichier) if mac else fichier}")

        def effacer():
            _effacer_connexion(fichier)                         # AUD-27 : un échec est journalisé et réessayé, plus avalé
        # Sans mot de passe (profil seul), le fichier reste jusqu'au prochain nettoyage (effacer_connexions_oubliees) : effacé à la
        # sortie d'Étrave, il disparaissait avant que MetaTrader le lise quand le double-clic trouvait Étrave déjà lancée.
        if verifies is not None:
            atexit.register(effacer)
            attente = minuterie(EFFACER_APRES_S, effacer)
            attente.daemon = True
            attente.start()
    try:
        if mac:
            # Session à part : fermer la fenêtre du Terminal (qui fait tourner Étrave) ne doit pas fermer MetaTrader.
            calme = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "start_new_session": True}
            processus = demarrer(commande, cwd=os.path.dirname(chemin), env=env_wine(env), **calme)
            pid = getattr(processus, "pid", None)
            if pid:                                             # le Mac reste éveillé tant que MetaTrader tourne
                demarrer(["caffeinate", "-i", "-w", str(pid)], **calme)
        else:
            demarrer(commande, cwd=os.path.dirname(chemin))
    except OSError:
        raise Refus("MetaTrader 5 n’a pas pu être lancé. Essaie de l’ouvrir à la main.") from None
    return {"lance": True, "connexion": identifiants is not None, **({"profil": PROFIL} if profil else {})}


def fermer(systeme=sys.platform, executer=subprocess.run):
    """Ferme MetaTrader 5 proprement (comme la croix de la fenêtre : il garde le profil et ses EA)."""
    if est_mac(systeme):
        commande = [WINE, "taskkill", "/IM", PROGRAMME]
        options = {"env": env_wine()}
    elif systeme.startswith("win"):
        commande = ["taskkill", "/IM", PROGRAMME]
        options = {}
    else:
        raise Refus("MetaTrader 5 ne se ferme d’ici que sous Windows ou sur un Mac avec MetaTrader 5 pour Mac.")
    try:
        executer(commande, capture_output=True, timeout=30, **options)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise Refus("MetaTrader 5 n’a pas pu être fermé d’ici : ferme-le à la main.") from None
    return {"ferme": True}
