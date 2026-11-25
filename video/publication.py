"""Ce qui part sur TikTok : un dossier par jour (sur le Bureau par défaut) avec la vidéo, sa description prête à coller et une image
de couverture, plus le mode automatique qui fabrique ces dossiers chaque soir.

    <Bureau>/Étrave TikTok/2026-11-25/recap-2026-11-25.mp4
                                     description.txt      à coller dans TikTok (accroche, résultats, compte, mentions, hashtags)
                                     couverture.jpg       l'écran titre, pour choisir la couverture

La description (la bio de la publication) est le seul endroit qui dit de quel compte viennent les trades, d'après le journal de
l'EA (« reel », « demo », « testeur ») : ni l'image, ni la couverture, ni le nom des fichiers. Rien de la méthode n'y figure.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

import nombres
import recap
import voix

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
    nom = f"recap-{j['jour'].isoformat()}.mp4"
    provisoire = os.path.join(dossier, "." + nom + ".partiel")
    shutil.copyfile(video, provisoire)
    os.replace(provisoire, os.path.join(dossier, nom))          # la vidéo n'apparaît que complète
    with open(os.path.join(dossier, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description(j, config))
    # la couverture : l'écran titre, une fois la date et la couleur de la journée posées
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3.2", "-i", video, "-frames:v", "1", "-q:v", "2",
                    os.path.join(dossier, "couverture.jpg")], check=False)
    return dossier


def description_periode(p, config):
    """Le texte de la publication d'un récap de la semaine ou du mois."""
    import recap_periode
    accroche = recap_periode.accroche(p)[1]
    if p["genre"] == "semaine":
        # VID-14 (audit du 25/11/2026) : une semaine à cheval sur deux mois disait « du 30 au 4 Décembre »
        debut = f"{p['debut'].day}" + ("" if p["debut"].month == p["fin"].month else f" {nombres.mois_ecran(p['debut'].month)}"
                                       + ("" if p["debut"].year == p["fin"].year else f" {p['debut'].year}"))
        quoi = f"récap de la semaine du {debut} au {p['fin'].day} {nombres.mois_ecran(p['fin'].month)} {p['fin'].year}"
    else:
        mois = nombres.mois_ecran(p["debut"].month)
        quoi = f"récap du mois {'d' + chr(39) if mois[0].lower() in 'aeiouéè' else 'de '}{mois} {p['debut'].year}"
    lignes = [f"{accroche} : {quoi}.", recap_periode.mot_periode(p), "", f"Total : {recap.ecran(p['total'], 'r')}"]
    lignes += [f"{nom} : {recap.ecran(v, 'r')}" for nom, v in p["par_marche"].items()]
    lignes.append(f"Jours de trade : {len(p['avec'])} sur {len(p['jours'])}, dont {len(p['gagnants'])} gagnant{recap._s(len(p['gagnants']))}")
    if p["meilleur"] and p["meilleur"]["total"] > 0:
        lignes.append(f"Meilleur jour : {recap_periode._jour_court(p['meilleur']['jour'])}, {recap.ecran(p['meilleur']['total'], 'r')}")
    if p["pire"] and p["pire"]["total"] < 0:
        lignes.append(f"Pire jour : {recap_periode._jour_court(p['pire']['jour'])}, {recap.ecran(p['pire']['total'], 'r')}")
    lignes += ["1 R = le risque pris sur un trade.", "", config.get("mention_compte") or COMPTE.get(p["source"], ""),
               "Chaque séance, gains comme pertes, sur le Telegram : lien en bio.",
               "Pas un conseil en investissement. Le trading comporte un risque de perte en capital.", "",
               " ".join(config.get("hashtags") or HASHTAGS)]
    return "\n".join(lignes).strip() + "\n"


def publier_periode(p, video, config):
    """Le dossier d'un récap de la semaine (« Semaine du AAAA-MM-JJ ») ou du mois (« Mois AAAA-MM »)."""
    import recap_periode
    dossier = os.path.join(os.path.expanduser(config.get("dossier_publication") or BUREAU), recap_periode.nom_dossier(p))
    os.makedirs(dossier, exist_ok=True)
    nom = os.path.basename(video)
    provisoire = os.path.join(dossier, "." + nom + ".partiel")
    shutil.copyfile(video, provisoire)
    os.replace(provisoire, os.path.join(dossier, nom))
    with open(os.path.join(dossier, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description_periode(p, config))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "3.2", "-i", video, "-frames:v", "1", "-q:v", "2",
                    os.path.join(dossier, "couverture.jpg")], check=False)
    return dossier


def periodes_finies(jours, aujourd_hui, depuis):
    """Les semaines (lundi-vendredi) et les mois finis : [(genre, début, fin)]. Une période est finie quand sa dernière séance
    possible est passée, ou quand la séance de son dernier jour ouvré est finie dans les journaux. Seules celles qui se terminent
    à partir de `depuis` comptent."""
    import recap_periode
    finis, vues, res = set(jours), set(), []
    for jour in sorted(jours):
        for genre, (debut, fin) in (("semaine", recap_periode.semaine_de(jour)), ("mois", recap_periode.mois_de(jour))):
            if (genre, debut) in vues or fin < depuis:
                continue
            vues.add((genre, debut))
            dernier_ouvre = fin
            while dernier_ouvre.weekday() > 4:
                dernier_ouvre -= datetime.timedelta(days=1)
            if aujourd_hui > fin or dernier_ouvre in finis:
                res.append((genre, debut, fin))
    return res


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
        # la photo de l'onglet Historique : seulement le soir même (l'onglet montre « Aujourd'hui »), avant de monter la vidéo
        if j["trades"] and not j.get("historique") and jour == aujourd_hui and config.get("historique"):
            import historique
            # Correctif VID-04 (audit du 25/11/2026) : une photo ratée (fenêtre plus petite que le cadre…) arrêtait tout le mode
            # automatique, récaps de la semaine et du mois compris. La vidéo se fait alors sans la photo.
            try:
                j["historique"] = historique.photographier_jour(config, dossier_journaux, jour, j["trades"], journal)
            except Exception as err:
                journal(f"Photo de l'historique impossible ({type(err).__name__} : {err}) : la vidéo se fait sans.")
        sortie = os.path.join(os.path.expanduser(config["sortie"]), f"recap-{jour.isoformat()}")
        os.makedirs(sortie, exist_ok=True)
        journal(f"{jour} : {j['trades']} position(s), fabrication de la vidéo…")
        # Correctif VID-03 (audit du 25/11/2026) : sans voix (réseau coupé, quota ElevenLabs), la vidéo était faite muette et jamais
        # refaite. Avec une voix réglée, la séance attend le lancement suivant, et la notification le dit.
        try:
            video = recap.fabriquer(j, config, sortie, journal, exiger_voix=bool(config.get("voix_id")))
            dossier = publier(j, video, config, journal)
        except voix.VoixIndisponible as err:
            journal(f"{jour} : voix indisponible ({err}). Pas de vidéo muette : nouvel essai au prochain lancement.")
            prevenir("Étrave", f"Récap du {nombres.date_courte(jour)} : voix indisponible, nouvel essai au prochain lancement.")
            continue
        except Exception as err:       # une séance ratée ne doit pas bloquer les suivantes ; elle sera retentée au prochain lancement
            journal(f"{jour} : échec ({type(err).__name__} : {err}). Nouvel essai au prochain lancement.")
            continue
        journal(f"{jour} : prêt dans {dossier}")
        prevenir("Étrave", f"Récap du {nombres.date_courte(jour)} prêt à publier (dossier « {os.path.basename(racine)} »).")
        faits.append(dossier)
    # les récaps de la semaine et du mois, une fois la période finie (rattrapés au lancement suivant s'ils ont été manqués)
    import recap_periode
    for genre, debut, fin in periodes_finies(journee.jours_finis(dossier_journaux), aujourd_hui, depuis):
        if not config.get("auto_hebdo" if genre == "semaine" else "auto_mensuel", True):
            continue
        try:
            p = recap_periode.charger(dossier_journaux, debut, fin, genre)
        except journee.JourneeIncomplete as err:      # VID-07 : jamais de période avec une séance en moins
            journal(f"{genre} du {debut.isoformat()} : pas de vidéo. {err}")
            continue
        cible = os.path.join(racine, recap_periode.nom_dossier(p))
        if (os.path.isdir(cible) and any(n.endswith(".mp4") for n in os.listdir(cible))) or not p["jours"]:
            continue
        if not p["avec"] and not config.get("auto_sans_trade"):
            continue
        sortie = os.path.join(os.path.expanduser(config["sortie"]), recap_periode.nom_dossier(p).replace(" ", "-").lower())
        os.makedirs(sortie, exist_ok=True)
        journal(f"{recap_periode.nom_dossier(p)} : {len(p['avec'])} jour(s) de trade, fabrication de la vidéo…")
        try:
            video = recap_periode.fabriquer(p, config, sortie, journal, exiger_voix=bool(config.get("voix_id")))
            dossier = publier_periode(p, video, config)
        except voix.VoixIndisponible as err:
            journal(f"{recap_periode.nom_dossier(p)} : voix indisponible ({err}). Nouvel essai au prochain lancement.")
            prevenir("Étrave", f"{recap_periode.nom_dossier(p)} : voix indisponible, nouvel essai au prochain lancement.")
            continue
        except Exception as err:
            journal(f"{recap_periode.nom_dossier(p)} : échec ({type(err).__name__} : {err}). Nouvel essai au prochain lancement.")
            continue
        journal(f"{recap_periode.nom_dossier(p)} : prêt dans {dossier}")
        prevenir("Étrave", f"{recap_periode.nom_dossier(p)} : récap prêt à publier.")
        faits.append(dossier)
    if not faits:
        journal(f"Rien de nouveau à publier ({aujourd_hui.isoformat()}).")
    return faits
