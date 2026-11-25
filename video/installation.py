"""Le lancement automatique, chaque soir de semaine après la séance : `python3 video/outil.py installer`.

L'outil est copié hors du dépôt (changer de branche ne le casse pas). Sur Mac, il va dans
~/Library/Application Support/Etrave/outil-video, avec ses sons, sa musique et ses rendus : seul le dossier de publication (le
Bureau) demande une autorisation à macOS, une fois. Une configuration propre au mode automatique (config-auto.json) y est écrite
à partir de ta configuration. Puis le lancement est programmé :
- sur Mac, un agent launchd à 22:20 et 23:50 (heure de l'ordinateur), du lundi au vendredi ; un Mac en veille à cette heure-là le
  lance à son réveil ;
- sous Windows (le VPS), une tâche planifiée aux mêmes heures (non testé sur ce Mac).
La séance finit à 21:50 à Paris (20:50 les semaines où les heures d'été ne changent pas le même jour en Europe et aux États-Unis).

`python3 video/outil.py desinstaller` retire la programmation (les vidéos déjà faites restent).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
ETIQUETTE = "com.etrave.recap-auto"
HEURES = [(22, 20), (23, 50)]
FICHIERS_ETRAVE = ("export.py", "pont.py")


def dossier_installation():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Etrave/outil-video")
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Etrave", "outil-video")
    return os.path.expanduser("~/.local/share/etrave/outil-video")


def python_hors_depot():
    """Un Python installé sur la machine (pas celui d'un environnement du dépôt, qui disparaîtrait avec lui)."""
    for p in ("/usr/local/bin/python3", "/opt/homebrew/bin/python3"):
        if os.path.exists(p):
            return p
    return shutil.which("python3") or shutil.which("python") or sys.executable


def copier_outil(cible):
    """Le code de l'outil et ce qu'il lit d'Étrave, au même agencement que dans le dépôt (video/, etrave/)."""
    for sous in ("video", "etrave"):
        os.makedirs(os.path.join(cible, sous), exist_ok=True)
    for nom in os.listdir(ICI):
        if nom.endswith(".py") and not nom.startswith("test_") or nom == "sons.json":
            shutil.copy2(os.path.join(ICI, nom), os.path.join(cible, "video", nom))
    modeles = os.path.join(cible, "video", "modeles")
    if os.path.isdir(modeles):
        shutil.rmtree(modeles)
    shutil.copytree(os.path.join(ICI, "modeles"), modeles)
    for nom in FICHIERS_ETRAVE:
        shutil.copy2(os.path.join(ICI, "..", "etrave", nom), os.path.join(cible, "etrave", nom))


def copier_dossier(source, cible):
    """Sons et musique copiés à côté de l'outil (sur Mac, le dossier Documents demanderait une autorisation de plus)."""
    source = os.path.expanduser(source or "")
    if not source or not os.path.exists(source):
        return None
    if os.path.isfile(source):
        os.makedirs(cible, exist_ok=True)
        shutil.copy2(source, os.path.join(cible, os.path.basename(source)))
        return os.path.join(cible, os.path.basename(source))
    shutil.copytree(source, cible, dirs_exist_ok=True)
    return cible


def installer(config, chemin_config, journal=print):
    cible = dossier_installation()
    os.makedirs(cible, exist_ok=True)
    copier_outil(cible)
    auto_cfg = os.path.join(cible, "config-auto.json")
    ancien = json.load(open(auto_cfg, encoding="utf-8")) if os.path.exists(auto_cfg) else {}
    c = dict(config)
    c.pop("presentation", None)                      # le mode automatique ne fait que les récaps
    c["sons"] = copier_dossier(config.get("sons"), os.path.join(cible, "sons")) or config.get("sons")
    if config.get("musique"):
        c["musique"] = copier_dossier(config["musique"], os.path.join(cible, "musique")) or config["musique"]
    c["sortie"] = os.path.join(cible, "rendus")
    c["dossier_publication"] = config.get("dossier_publication") or "~/Desktop/Étrave TikTok"
    # les séances d'avant l'installation ne sont pas refaites (sauf si tu choisis une date dans auto_depuis)
    c["auto_depuis"] = config.get("auto_depuis") or ancien.get("auto_depuis") or datetime.date.today().isoformat()
    with open(auto_cfg, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)
    os.chmod(auto_cfg, 0o600)
    os.makedirs(os.path.expanduser(c["dossier_publication"]), exist_ok=True)
    py = python_hors_depot()
    commande = [py, os.path.join(cible, "video", "outil.py"), "auto", "--config", auto_cfg]
    journal_auto = os.path.join(cible, "recap-auto.log")
    if sys.platform == "darwin":
        plist = os.path.expanduser(f"~/Library/LaunchAgents/{ETIQUETTE}.plist")
        heures = "".join(f"""
      <dict><key>Weekday</key><integer>{jour}</integer><key>Hour</key><integer>{h}</integer><key>Minute</key><integer>{m}</integer></dict>"""
                         for jour in range(1, 6) for h, m in HEURES)
        arguments = "".join(f"\n      <string>{a}</string>" for a in commande)
        with open(plist, "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>{ETIQUETTE}</string>
    <key>ProgramArguments</key>
    <array>{arguments}
    </array>
    <key>StartCalendarInterval</key>
    <array>{heures}
    </array>
    <key>EnvironmentVariables</key>
    <dict><key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
    <key>WorkingDirectory</key><string>{cible}</string>
    <key>StandardOutPath</key><string>{journal_auto}</string>
    <key>StandardErrorPath</key><string>{journal_auto}</string>
    <key>ProcessType</key><string>Background</string>
  </dict>
</plist>
""")
        domaine = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domaine, plist], capture_output=True)
        r = subprocess.run(["launchctl", "bootstrap", domaine, plist], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"launchctl a refusé l'agent : {r.stderr.strip()}")
        journal(f"Programmé : du lundi au vendredi à {', '.join(f'{h}:{m:02d}' for h, m in HEURES)} (agent {ETIQUETTE}).")
    elif os.name == "nt":
        tr = subprocess.list2cmdline(commande)
        for i, (h, m) in enumerate(HEURES):
            subprocess.run(["schtasks", "/Create", "/F", "/SC", "WEEKLY", "/D", "MON,TUE,WED,THU,FRI", "/ST", f"{h:02d}:{m:02d}",
                            "/TN", f"Etrave recap auto {i + 1}", "/TR", tr], check=True)
        journal(f"Programmé : tâches planifiées « Etrave recap auto » du lundi au vendredi à {', '.join(f'{h}:{m:02d}' for h, m in HEURES)}.")
    else:
        journal("Programmation automatique non prise en charge sur ce système : lance `outil.py auto` chaque soir.")
    journal(f"Outil copié dans {cible} ; journal du mode automatique : {journal_auto}")
    journal(f"Vidéos prêtes à publier : {os.path.expanduser(c['dossier_publication'])}")
    return cible


def desinstaller(journal=print):
    if sys.platform == "darwin":
        plist = os.path.expanduser(f"~/Library/LaunchAgents/{ETIQUETTE}.plist")
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", plist], capture_output=True)
        if os.path.exists(plist):
            os.remove(plist)
    elif os.name == "nt":
        for i in range(len(HEURES)):
            subprocess.run(["schtasks", "/Delete", "/F", "/TN", f"Etrave recap auto {i + 1}"], capture_output=True)
    journal("Lancement automatique retiré (l'outil copié et les vidéos restent).")
