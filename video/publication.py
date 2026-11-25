"""Ce qui part sur TikTok : un dossier par jour (sur le Bureau par défaut) avec la vidéo, sa description prête à coller et une image
de couverture, plus le mode automatique qui fabrique ces dossiers chaque soir.

    <Bureau>/Étrave TikTok/2026-11-25/recap-2026-11-25.mp4
                                     description.txt      à coller dans TikTok (accroche, résultats, compte, mentions, hashtags)
                                     couverture.jpg       l'écran titre, pour choisir la couverture

La description dit de quel compte viennent les trades, d'après le journal de l'EA (« reel », « demo », « testeur ») : jamais dans
l'image, toujours dans le texte. Rien de la méthode n'y figure (ni type d'entrée, ni filtre).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

import nombres
import recap

BUREAU = "~/Desktop/Étrave TikTok"
HASHTAGS = ["#trading", "#nasdaq", "#sp500", "#daytrading", "#tradingautomatique"]
COMPTE = {
    "reel": "Trades réels, sur mon compte.",
    "demo": "Trades pris sur un compte démo.",
    "concours": "Trades pris sur un compte de concours.",
    "testeur": "Exemple du testeur de stratégie (simulation), pas un trade réel.",
}


def description(j, config):
    """Le texte de la publication TikTok."""
    unite = recap.unite_du_jour(j, config.get("unite", "r"))
    t = recap.total(j, unite)
    jour_sem, jour_mois, annee = nombres.date_ecran(j["jour"])
    accroche = recap.accroche(j, unite)[1]
    lignes = [f"{accroche} : récap de la séance du {jour_sem} {jour_mois} {annee}.", recap.mot_du_jour(j, t), ""]
    for m in j["marches"]:
        v = recap.valeur(m, unite)
        if m["positions"] and v is not None:
            lignes.append(f"{m['nom']} : {recap.ecran(round(v, recap.DECIMALES[unite]), unite)}")
        else:
            lignes.append(f"{m['nom']} : pas de trade")
    if t is not None and sum(1 for m in j["marches"] if m["positions"]) > 1:
        lignes.append(f"Total : {recap.ecran(t, unite)}")
    if unite == "r" and j["trades"]:
        lignes.append("1 R = le risque pris sur un trade.")
    lignes += ["", config.get("mention_compte") or COMPTE.get(j["source"], ""),
               "Chaque séance, gains comme pertes, sur le Telegram : lien en bio.",
               "Pas un conseil en investissement. Le trading comporte un risque de perte en capital.", "",
               " ".join(config.get("hashtags") or HASHTAGS)]
    return "\n".join(l for l in lignes if l is not None).strip() + "\n"


def publier(j, video, config, journal=print):
    """Copie la vidéo dans le dossier du jour, écrit la description et la couverture. Rend le dossier."""
    dossier = os.path.join(os.path.expanduser(config.get("dossier_publication") or BUREAU), j["jour"].isoformat())
    os.makedirs(dossier, exist_ok=True)
    nom = f"recap-{j['jour'].isoformat()}{'-exemple' if j['source'] == 'testeur' else ''}.mp4"
    provisoire = os.path.join(dossier, "." + nom + ".partiel")
    shutil.copyfile(video, provisoire)
    os.replace(provisoire, os.path.join(dossier, nom))          # la vidéo n'apparaît que complète
    with open(os.path.join(dossier, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description(j, config))
    # la couverture : l'écran titre, une fois la date et la couleur de la journée posées
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3.2", "-i", video, "-frames:v", "1", "-q:v", "2",
                    os.path.join(dossier, "couverture.jpg")], check=False)
    return dossier


def prevenir(titre, texte):
    """Une notification du système (Mac) ; rien ailleurs."""
    if sys.platform == "darwin":
        script = f'display notification {json.dumps(texte)} with title {json.dumps(titre)}'
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)


def auto(config, dossier_journaux, journal=print, aujourd_hui=None):
    """Le mode automatique : chaque séance finie, depuis `auto_depuis`, qui a au moins un trade (ou toutes avec auto_sans_trade) et
    pas encore de dossier de publication, devient une vidéo prête à publier. Un soir manqué est rattrapé au lancement suivant.
    Rend la liste des dossiers créés."""
    import journee
    aujourd_hui = aujourd_hui or datetime.date.today()
    depuis = datetime.date.fromisoformat(config["auto_depuis"]) if config.get("auto_depuis") else aujourd_hui - datetime.timedelta(days=4)
    racine = os.path.expanduser(config.get("dossier_publication") or BUREAU)
    if not os.path.isdir(dossier_journaux):
        journal(f"Journaux de l'EA introuvables : {dossier_journaux}")
        return []
    faits = []
    for jour in journee.jours_finis(dossier_journaux):
        if jour < depuis:
            continue
        cible = os.path.join(racine, jour.isoformat())
        if os.path.isdir(cible) and any(n.endswith(".mp4") for n in os.listdir(cible)):
            continue
        try:
            j = journee.charger(dossier_journaux, jour)
        except journee.JourneeIncomplete as err:
            journal(f"{jour} : pas de vidéo. {err}")
            continue
        if not j["trades"] and not config.get("auto_sans_trade"):
            continue
        sortie = os.path.join(os.path.expanduser(config["sortie"]), f"recap-{jour.isoformat()}")
        os.makedirs(sortie, exist_ok=True)
        journal(f"{jour} : {j['trades']} position(s), fabrication de la vidéo…")
        try:
            video = recap.fabriquer(j, config, sortie, journal)
            dossier = publier(j, video, config, journal)
        except Exception as err:       # une séance ratée ne doit pas bloquer les suivantes ; elle sera retentée au prochain lancement
            journal(f"{jour} : échec ({type(err).__name__} : {err}). Nouvel essai au prochain lancement.")
            continue
        journal(f"{jour} : prêt dans {dossier}")
        prevenir("Étrave", f"Récap du {nombres.date_courte(jour)} prêt à publier (dossier « {os.path.basename(racine)} »).")
        faits.append(dossier)
    if not faits:
        journal(f"Rien de nouveau à publier ({aujourd_hui.isoformat()}).")
    return faits
