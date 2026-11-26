"""Lancement de l'outil vidéo en fin de journée, une fois tout clôturé (demande de l'utilisateur du 27/11/2026 : « je préfère qu'il
soit lancé en fin de journée quand tout est clôturé »).

Étrave regarde chaque minute si la séance de New York est close :
 - au moins MARGE_MIN minutes après la sortie de fin de journée de l'EA (`sortie_ny` de son état : 15:50, 12:45 une demi-séance) ;
 - aucun EA (dernier état connu, même s'il ne répond plus) n'a de trade, d'ordre ou de jambe ouverts ;
 - chaque EA en marche a écrit sa ligne « fin » du jour dans `seances-<symbole>.csv` (il écrit ses bougies et son journal
   d'exécution dans la même minute).
Alors elle lance `outil.py auto` de l'outil vidéo installé (`video/outil.py installer`), une seule fois par jour de New York (retenu
dans FICHIER, partagé par tous les processus Étrave). La tâche programmée de l'outil vidéo (22:20 et 23:50, heure de l'ordinateur)
reste en secours : l'outil ne refait jamais une vidéo déjà faite.

Sécurité : la commande est fixe (dossier d'installation connu, interpréteur connu, arguments en liste, sans shell) ; rien n'est lu
dans un fichier que l'EA, MetaTrader ou une page pourraient écrire.
"""
import datetime
import os
import shutil
import subprocess
import sys

import export

MARGE_MIN = 5
FICHIER = "video-fin-de-journee.txt"
SORTIE_DEFAUT = "15:50"


# ───────────────────────── l'outil vidéo installé (comme video/installation.py) ─────────────────────────
def dossier_outil_video(systeme=sys.platform, env=None):
    """Le dossier où `outil.py installer` copie l'outil vidéo : le même que dossier_installation() de video/installation.py
    (un test vérifie l'accord sur la branche de l'outil vidéo)."""
    env = os.environ if env is None else env
    maison = env.get("HOME") or os.path.expanduser("~")
    if systeme == "darwin":
        return os.path.join(maison, "Library", "Application Support", "Etrave", "outil-video")
    if systeme.startswith("win"):
        return os.path.join(env.get("LOCALAPPDATA", maison), "Etrave", "outil-video")
    return os.path.join(maison, ".local", "share", "etrave", "outil-video")


def python_outil_video(systeme=sys.platform):
    """L'interpréteur du mode automatique de l'outil vidéo : le même choix que python_hors_depot() de video/installation.py (pas le
    .venv du dépôt, ni le raccourci du Microsoft Store sous Windows)."""
    if systeme.startswith("win"):
        base = os.path.join(sys.base_prefix, "python.exe")
        if os.path.exists(base):
            return base
    for chemin in ("/usr/local/bin/python3", "/opt/homebrew/bin/python3"):
        if os.path.exists(chemin):
            return chemin
    return shutil.which("python3") or shutil.which("python") or sys.executable


def installe(dossier_outil):
    return os.path.isfile(os.path.join(dossier_outil, "video", "outil.py")) and os.path.isfile(os.path.join(dossier_outil, "config-auto.json"))


def commande(dossier_outil, python):
    return [python, os.path.join(dossier_outil, "video", "outil.py"), "auto", "--config", os.path.join(dossier_outil, "config-auto.json")]


# ───────────────────────── la séance est-elle close ? ─────────────────────────
def decalage_ny(utc):
    """Heures de retard de New York sur UTC : 4 en été, 5 en hiver (règle américaine, la même que export.aujourdhui_ny et l'EA)."""
    mars = datetime.datetime(utc.year, 3, 1, tzinfo=datetime.timezone.utc)
    novembre = datetime.datetime(utc.year, 11, 1, tzinfo=datetime.timezone.utc)
    debut_ete = mars + datetime.timedelta(days=(6 - mars.weekday()) % 7 + 7, hours=7)
    fin_ete = novembre + datetime.timedelta(days=(6 - novembre.weekday()) % 7, hours=6)
    return 4 if debut_ete <= utc < fin_ete else 5


def heure_ny(maintenant=None):
    """L'heure de New York, sans fuseau (un test vérifie que sa date est celle de export.aujourdhui_ny)."""
    utc = maintenant or datetime.datetime.now(datetime.timezone.utc)
    return (utc - datetime.timedelta(hours=decalage_ny(utc))).replace(tzinfo=None)


def _minutes(texte):
    try:
        heures, minutes = str(texte).split(":")
        return int(heures) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return None


def pret(etats, dossier, maintenant=None):
    """(True, "séance close") quand la vidéo du jour peut être lancée, sinon (False, ce qu'on attend), en mots courts."""
    ny = heure_ny(maintenant)
    if ny.weekday() >= 5:
        return False, "pas de séance le week-end"
    actifs = [e for e in etats if e.get("en_marche")]
    if not actifs:
        return False, "aucun EA en marche"
    for e in etats:
        if e.get("position") or e.get("attente") or (e.get("jambes") or 0) > 0:
            return False, f"trade ou ordre encore ouvert sur {e.get('symbole', '?')}"
    sortie = max((_minutes(e.get("sortie_ny")) or _minutes(SORTIE_DEFAUT)) for e in actifs) + MARGE_MIN
    if ny.hour * 60 + ny.minute < sortie:
        return False, f"après {sortie // 60:02d}:{sortie % 60:02d} NY"
    jour = ny.date().isoformat()
    lignes, _ = export.lire_journal(dossier, "seances")
    fins = {l.get("symbole") for l in lignes if l.get("moment") == "fin" and str(l.get("jour_ny", ""))[:10] == jour}
    manquants = [e.get("symbole", "?") for e in actifs if e.get("symbole") not in fins]
    if manquants:
        return False, "ligne de fin pas encore écrite : " + ", ".join(manquants)
    return True, "séance close"


# ───────────────────────── une fois par jour ─────────────────────────
def derniere(dossier):
    """Le dernier lancement retenu : {"jour", "heure_ny", "resultat"} ou None."""
    try:
        with open(os.path.join(dossier, FICHIER), "r", encoding="utf-8") as f:
            jour, heure, resultat = f.read().strip().split(";")
    except (OSError, ValueError):
        return None
    if len(jour) != 10 or resultat not in ("lancee", "echec"):
        return None
    return {"jour": jour, "heure_ny": heure, "resultat": resultat}


def retenir(dossier, jour, heure, resultat):
    chemin = os.path.join(dossier, FICHIER)
    with open(chemin + ".tmp", "w", encoding="utf-8") as f:
        f.write(f"{jour};{heure};{resultat}\n")
    os.replace(chemin + ".tmp", chemin)


def lancer(commande_outil, journal_outil, env):
    """Lance l'outil vidéo sans l'attendre (il met plusieurs minutes), détaché d'Étrave, sortie ajoutée à son journal."""
    options = {"stdin": subprocess.DEVNULL, "cwd": os.path.dirname(os.path.dirname(commande_outil[1])), "env": env}
    if sys.platform.startswith("win"):
        options["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        options["start_new_session"] = True
    with open(journal_outil, "a", encoding="utf-8") as sortie:
        sortie.write(f"— {datetime.datetime.now():%Y-%m-%d %H:%M} (lancé par Étrave, séance close) —\n")
        sortie.flush()
        subprocess.Popen(commande_outil, stdout=sortie, stderr=subprocess.STDOUT, **options)
