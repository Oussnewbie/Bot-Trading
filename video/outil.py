"""Étrave vidéo : l'outil tout en un des vidéos TikTok (récap de chaque séance, présentation de la chaîne).

    python3 video/outil.py verifier                  ce qui est prêt et ce qui manque (Node, ffmpeg, police, sons, voix, journaux)
    python3 video/outil.py jours [--testeur]         les séances finies trouvées dans les journaux de l'EA
    python3 video/outil.py recap [--jour AAAA-MM-JJ] [--testeur] [--sans-voix]
                                                     la vidéo récap d'une séance (par défaut la dernière finie)
    python3 video/outil.py presentation              la vidéo de présentation de la chaîne (profil local requis)
    python3 video/outil.py sons                      télécharge les bruitages Mixkit manquants dans ton dossier de sons
    python3 video/outil.py auto                      les séances finies avec un trade ou plus, pas encore publiées : vidéo,
                                                     description et couverture dans un dossier par jour (Bureau)
    python3 video/outil.py historique --essai        photographie la fenêtre de MetaTrader (Bureau) pour régler le cadre
                                                     du tableau de l'onglet Historique (voir historique.py)
    python3 video/outil.py certificat --essai        écrit le certificat flouté sur le Bureau, pour régler `masques_certificat`
    python3 video/outil.py installer                 lance `auto` tout seul chaque soir de semaine (copie l'outil hors du dépôt)
    python3 video/outil.py desinstaller              retire ce lancement automatique

La configuration est un fichier privé, hors du dépôt : ~/.config/etrave-video/config.json (modèle : video/config.exemple.json).
--testeur lit les journaux du testeur de stratégie (sous-dossier `testeur`). Démo, réel ou testeur n'apparaissent que dans la
description d'une publication (« simulation ») ; jamais dans la vidéo, la couverture ni un nom de fichier ou de dossier.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "..", "etrave"))      # pont.py et export.py d'Étrave : la même lecture des journaux
CONFIG = os.path.expanduser("~/.config/etrave-video/config.json")
# Lancé par launchd, cron ou une tâche planifiée, le PATH est réduit à /usr/bin:/bin : on y ajoute les dossiers habituels de Node et de ffmpeg (Homebrew, installateurs)
for _d in ("/usr/local/bin", "/opt/homebrew/bin"):
    if os.path.isdir(_d) and _d not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + _d
POLICE_MAC = "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf"


def charger_config(chemin=None):
    chemin = os.path.expanduser(chemin or CONFIG)
    config = json.load(open(chemin, encoding="utf-8")) if os.path.exists(chemin) else {}
    config.setdefault("police", POLICE_MAC)
    config.setdefault("unite", "r")
    config.setdefault("sortie", "~/Documents/Etrave-video")
    if not config.get("dossier_journaux"):
        config["dossier_journaux"] = dossier_par_defaut()
    return config


def dossier_par_defaut():
    """Le dossier commun de MetaTrader : Windows (APPDATA), ou MetaTrader pour Mac (son préfixe Wine)."""
    import pont
    if os.name == "nt":
        return pont.dossier_commun()
    vin = os.path.expanduser("~/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users")
    for utilisateur in sorted(os.listdir(vin)) if os.path.isdir(vin) else []:
        d = os.path.join(vin, utilisateur, "AppData", "Roaming", "MetaQuotes", "Terminal", "Common", "Files", "Etrave")
        if os.path.isdir(d):
            return d
    return ""


def dossier_journaux(config, testeur):
    d = os.path.expanduser(config["dossier_journaux"])
    return os.path.join(d, "testeur") if testeur else d


def verifier(config):
    lignes, ok = [], True

    def point(bon, texte, conseil=""):
        nonlocal ok
        ok = ok and bon
        lignes.append(("OK   " if bon else "MANQUE ") + texte + ("" if bon or not conseil else f"\n       → {conseil}"))
    point(shutil.which("node") is not None and shutil.which("npx") is not None, "Node.js (npx) pour le rendu HyperFrames",
          "installe Node.js 20 ou plus : https://nodejs.org")
    point(shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None, "ffmpeg et ffprobe", "brew install ffmpeg")
    point(shutil.which("curl") is not None, "curl (voix ElevenLabs, téléchargement des sons)")
    try:                                   # VID-02 : le Python de Windows n'a pas de fuseaux horaires sans le paquet tzdata
        import zoneinfo
        zoneinfo.ZoneInfo("America/New_York")
        tz = True
    except Exception:
        tz = False
    point(tz, "fuseaux horaires (New York, Paris)", "py -m pip install tzdata")
    point(os.path.exists(os.path.expanduser(config["police"])), f"police DIN Alternate Bold ({config['police']})",
          "réglage « police » : le chemin d'un fichier DIN Alternate Bold (fourni avec macOS)")
    import mixage
    sons = mixage.catalogue()
    dossier_sons = os.path.expanduser(config.get("sons") or "")
    presents = [n for n, s in sons.items() if dossier_sons and os.path.exists(os.path.join(dossier_sons, s["fichier"]))]
    point(len(presents) == len(sons), f"bruitages : {len(presents)} sur {len(sons)} dans « sons »", "python3 video/outil.py sons")
    point(bool(config.get("voix_id")), "voix_id (le clone ElevenLabs de ta voix)", "sans lui, aucune vidéo (jamais de vidéo muette)")
    point(os.path.exists(os.path.expanduser(config.get("cle_elevenlabs", "~/.config/elevenlabs/cle"))), "clé ElevenLabs (fichier privé)",
          "écris la clé seule dans ~/.config/elevenlabs/cle, puis chmod 600")
    if config.get("voix_id") and shutil.which("curl"):      # VID-22 : la clé, la voix et les crédits, avant le soir (lectures gratuites)
        import voix
        for bon, texte in voix.controle_compte(config):
            point(bon, texte)
    d = os.path.expanduser(config["dossier_journaux"])
    point(os.path.isdir(d), f"journaux de l'EA ({d or 'introuvable'})", "réglage « dossier_journaux » : le dossier …\\Common\\Files\\Etrave")
    if os.path.isdir(d):
        import glob
        point(bool(glob.glob(os.path.join(d, "bougies-*.csv"))), "journal des bougies (bougies-<symbole>.csv)",
              "il apparaît après la première séance de l'EA qui l'écrit (version avec BougiesRow)")
    print("\n".join(lignes))
    return ok


def telecharger_sons(config):
    import mixage
    dossier = os.path.expanduser(config.get("sons") or "~/Documents/Etrave-video/sons")
    os.makedirs(dossier, exist_ok=True)
    for nom, s in mixage.catalogue().items():
        chemin = os.path.join(dossier, s["fichier"])
        if os.path.exists(chemin):
            continue
        print("téléchargement :", s["fichier"])
        subprocess.run(["curl", "-sSfL", "--max-time", "60", "-o", chemin, s["url"]], check=False)
    print(f"Dossier des sons : {dossier} (à mettre dans « sons » de la configuration).")


def main(arguments=None):
    a = argparse.ArgumentParser(description="Étrave vidéo : récap de séance et présentation, en motion design.")
    a.add_argument("commande", choices=["verifier", "jours", "recap", "presentation", "sons", "auto", "installer", "desinstaller",
                                        "historique", "certificat"])
    a.add_argument("--essai", action="store_true", help="historique : toute la fenêtre de MetaTrader, pour régler le cadre")
    a.add_argument("--jour", help="date de la séance (New York), AAAA-MM-JJ ; par défaut la dernière finie")
    a.add_argument("--testeur", action="store_true", help="journaux du testeur de stratégie")
    a.add_argument("--sans-voix", action="store_true", help="ne pas appeler ElevenLabs")
    a.add_argument("--config", help=f"fichier de configuration (par défaut {CONFIG})")
    args = a.parse_args(arguments)
    config = charger_config(args.config)
    if args.sans_voix:
        config["voix_id"] = ""
    if args.commande == "verifier":
        return 0 if verifier(config) else 1
    if args.commande == "sons":
        telecharger_sons(config)
        return 0
    if args.commande == "historique":
        import historique
        import journee
        if args.essai:
            chemin, w, h = historique.essai()
            print(f"Fenêtre de MetaTrader photographiée : {chemin} ({w} x {h} pixels). Lis-y le cadre du tableau de l'onglet "
                  "Historique (x, y du haut de l'en-tête, largeur, hauteur de l'en-tête et d'une ligne) pour « historique » de "
                  "la configuration.")
            return 0
        dossier = dossier_journaux(config, False)
        jour = datetime.date.fromisoformat(args.jour) if args.jour else datetime.date.today()
        j = journee.charger(dossier, jour, bougies_requises=False)
        print(historique.photographier_jour(config, dossier, jour, j["trades"], print) or "Pas de photo.")
        return 0
    if args.commande == "certificat":
        import presentation
        profil = config.get("presentation") or {}
        if not profil.get("certificat"):
            print("Pas de « certificat » dans la partie « presentation » de la configuration.")
            return 1
        cible = os.path.join(os.path.expanduser("~/Desktop"), "certificat-floute.png")
        presentation.copier_certificat(profil, cible)
        print(f"Certificat {'flouté' if profil.get('masques_certificat') else 'sans masque (masques_certificat vide)'} : {cible}. "
              "Règle les rectangles [x, y, largeur, hauteur] (en pixels de l'image) dans « masques_certificat », puis relance.")
        return 0
    if args.commande == "installer":
        import installation
        installation.installer(config, args.config, print)
        return 0
    if args.commande == "desinstaller":
        import installation
        installation.desinstaller(print)
        return 0
    if args.commande == "auto":
        import publication
        print(f"— {datetime.datetime.now():%Y-%m-%d %H:%M} —", flush=True)
        racine = os.path.expanduser(config.get("dossier_publication") or publication.BUREAU)
        try:          # le droit d'écrire dans le dossier de publication (sur Mac, la première fois, macOS demande l'autorisation)
            os.makedirs(racine, exist_ok=True)
            essai = os.path.join(racine, ".ecriture")
            open(essai, "w").close()
            os.remove(essai)
        except OSError as err:
            print(f"Impossible d'écrire dans {racine} ({err}). Sur Mac : Réglages Système, Confidentialité et sécurité, "
                  "Fichiers et dossiers (ou Accès complet au disque), autoriser python3.")
            return 3
        publication.auto(config, dossier_journaux(config, args.testeur), lambda t: print(t, flush=True))
        return 0
    if args.commande == "presentation":
        import presentation
        print(presentation.fabriquer(config, print))
        return 0
    import journee
    dossier = dossier_journaux(config, args.testeur)
    if args.commande == "jours":
        jours = journee.jours_finis(dossier)
        print(f"{len(jours)} séance(s) finie(s) dans {dossier}" + (f" : du {jours[0]} au {jours[-1]}" if jours else ""))
        for j in jours[-10:]:
            print("  ", j.isoformat())
        return 0
    import recap
    try:
        j = journee.charger(dossier, datetime.date.fromisoformat(args.jour) if args.jour else None)
    except journee.JourneeIncomplete as err:
        print(err)
        return 2
    # VID-12 (audit du 25/11/2026) : « testeur » apparaissait dans le nom du dossier ; « essai » ne dit rien du compte
    sortie = os.path.join(os.path.expanduser(config["sortie"]), f"recap-{j['jour'].isoformat()}{'-essai' if args.testeur else ''}")
    os.makedirs(sortie, exist_ok=True)
    print(f"Séance du {j['jour']} : {j['trades']} position(s) sur {len(j['marches'])} marché(s).")
    import voix
    try:          # VID-18 : pas de vidéo muette sans le demander (--sans-voix)
        print("Vidéo :", recap.fabriquer(j, config, sortie, print, exiger_voix=not args.sans_voix))
    except voix.VoixIndisponible as err:
        print(f"Pas de voix : {err}. Pas de vidéo. Pour un essai sans voix : --sans-voix.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
