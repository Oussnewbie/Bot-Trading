"""Étrave vidéo : l'outil tout en un des vidéos TikTok (récap de chaque séance, présentation de la chaîne).

    python3 video/outil.py verifier                  ce qui est prêt et ce qui manque (Node, ffmpeg, police, sons, voix, journaux)
    python3 video/outil.py jours [--testeur]         les séances finies trouvées dans les journaux de l'EA
    python3 video/outil.py recap [--jour AAAA-MM-JJ] [--testeur] [--sans-voix]
                                                     la vidéo récap d'une séance (par défaut la dernière finie)
    python3 video/outil.py presentation              la vidéo de présentation de la chaîne (profil local requis)
    python3 video/outil.py sons                      télécharge les bruitages Mixkit manquants dans ton dossier de sons

La configuration est un fichier privé, hors du dépôt : ~/.config/etrave-video/config.json (modèle : video/config.exemple.json).
--testeur lit les journaux du testeur de stratégie (sous-dossier `testeur`) : la vidéo porte alors la mention « Exemple ».
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
    point(os.path.exists(os.path.expanduser(config["police"])), f"police DIN Alternate Bold ({config['police']})",
          "réglage « police » : le chemin d'un fichier DIN Alternate Bold (fourni avec macOS)")
    import mixage
    sons = mixage.catalogue()
    dossier_sons = os.path.expanduser(config.get("sons") or "")
    presents = [n for n, s in sons.items() if dossier_sons and os.path.exists(os.path.join(dossier_sons, s["fichier"]))]
    point(len(presents) == len(sons), f"bruitages : {len(presents)} sur {len(sons)} dans « sons »", "python3 video/outil.py sons")
    point(bool(config.get("voix_id")), "voix_id (le clone ElevenLabs de ta voix)", "sans lui, la vidéo est faite sans voix")
    point(os.path.exists(os.path.expanduser(config.get("cle_elevenlabs", "~/.config/elevenlabs/cle"))), "clé ElevenLabs (fichier privé)",
          "écris la clé seule dans ~/.config/elevenlabs/cle, puis chmod 600")
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
    a.add_argument("commande", choices=["verifier", "jours", "recap", "presentation", "sons"])
    a.add_argument("--jour", help="date de la séance (New York), AAAA-MM-JJ ; par défaut la dernière finie")
    a.add_argument("--testeur", action="store_true", help="journaux du testeur (vidéo marquée « Exemple »)")
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
    sortie = os.path.join(os.path.expanduser(config["sortie"]), f"recap-{j['jour'].isoformat()}{'-exemple' if args.testeur else ''}")
    os.makedirs(sortie, exist_ok=True)
    print(f"Séance du {j['jour']} : {j['trades']} position(s) sur {len(j['marches'])} marché(s).")
    print("Vidéo :", recap.fabriquer(j, config, sortie, print))
    return 0


if __name__ == "__main__":
    sys.exit(main())
