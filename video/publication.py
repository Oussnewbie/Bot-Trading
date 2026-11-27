"""Ce qui part sur TikTok : un dossier par jour (sur le Bureau par défaut) avec la vidéo, sa description prête à coller et une image
de couverture, plus le mode automatique qui fabrique ces dossiers chaque soir.

    <Bureau>/Étrave TikTok/2026-11-25/recap-2026-11-25.mp4
                                     description.txt      à coller dans TikTok (accroche, résultats, compte, mentions, hashtags)
                                     couverture.jpg       l'écran titre, pour choisir la couverture
                                     avant-de-publier.txt les cases à cocher sur TikTok (conformité, 25/11/2026)

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


# Conformité TikTok (25/11/2026) : ce qu'il faut cocher, ou pas, au moment de publier ; écrit dans chaque dossier de publication.
AVANT_DE_PUBLIER = """Avant de publier sur TikTok :
- Cocher « Contenu généré par l'IA » (la voix est un clone ElevenLabs).
- NE PAS cocher « Contenu commercial » tant que rien n'est vendu (pas de signaux payants, pas de copie de trades, pas d'affiliation).
- Coller description.txt tel quel (la ligne du compte, la mention de risque).
- Publier à la main : pas d'outil de publication automatique.
- Si un jour quelque chose devient payant : tout revoir avant (case « Contenu commercial », mention « Publicité » en France,
  promotion des CFD interdite aux influenceurs rémunérés).
"""


def ecrire_avant_de_publier(dossier):
    with open(os.path.join(dossier, "avant-de-publier.txt"), "w", encoding="utf-8") as f:
        f.write(AVANT_DE_PUBLIER)


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
               "Chaque séance, gains comme pertes, sur le Telegram (gratuit, rien à vendre) : lien en bio.",
               "Pas un conseil en investissement. Le trading comporte un risque de perte en capital.", "",
               " ".join(config.get("hashtags") or HASHTAGS)]
    return "\n".join(l for l in lignes if l is not None).strip() + "\n"


def instant_couverture(video):
    """V-21 (audit du 27/11/2026) : la couverture était prise à 3,2 s fixes ; un titre plus court donnait le volet ou la scène suivante.
    L'instant est celui que la fabrication a noté dans recap.json (l'écran titre posé, avant le volet)."""
    try:
        with open(os.path.join(os.path.dirname(video), "recap.json"), encoding="utf-8") as f:
            return float(json.load(f)["couverture"])
    except (OSError, ValueError, KeyError, TypeError):
        return 1.0


def couverture(video, dossier):
    """La couverture : l'écran titre, la date et la couleur de la période posées."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{instant_couverture(video):.3f}", "-i", video, "-frames:v", "1", "-q:v", "2",
                    os.path.join(dossier, "couverture.jpg")], check=False, timeout=120)


def copier_video(video, dossier, nom):
    """La vidéo n'apparaît que complète ; V-20 : un nom provisoire propre au passage."""
    provisoire = os.path.join(dossier, f".{nom}.{os.getpid()}.partiel")
    shutil.copyfile(video, provisoire)
    os.replace(provisoire, os.path.join(dossier, nom))


# Décision du propriétaire (27/11/2026) : une vidéo faite à partir des journaux du testeur ne se publie jamais, c'est un essai. Elle ne va
# ni dans le dossier de publication (le Bureau), ni dans le registre des publications, ni dans une notification « à publier », mais
# dans <sortie>/essais-testeur/ESSAI-…, avec ESSAI-NE-PAS-PUBLIER.txt.
ESSAIS = "essais-testeur"
NE_PAS_PUBLIER = """ESSAI : NE PAS PUBLIER.
Cette vidéo est faite à partir des journaux du testeur de stratégie de MetaTrader (une simulation sur l'historique), pas d'une séance
du robot sur un compte. Décision du propriétaire du 27/11/2026 : une vidéo du testeur ne se publie jamais.
"""


def est_testeur(dossier_journaux=None, source=None):
    """Des journaux du testeur : le sous-dossier `testeur` du dossier de l'EA, ou des lignes écrites avec source=testeur."""
    nom = os.path.basename(os.path.normpath(os.path.expanduser(dossier_journaux))) if dossier_journaux else ""
    return nom.lower() == "testeur" or source == "testeur"


def ranger_essai(video, config, nom, journal=print):
    """Une vidéo du testeur, rangée hors du dossier de publication, marquée ESSAI. Rend son dossier."""
    dossier = os.path.join(os.path.expanduser(config["sortie"]), ESSAIS, f"ESSAI-{nom}")
    os.makedirs(dossier, exist_ok=True)
    copier_video(video, dossier, os.path.basename(video))
    with open(os.path.join(dossier, "ESSAI-NE-PAS-PUBLIER.txt"), "w", encoding="utf-8") as f:
        f.write(NE_PAS_PUBLIER)
    journal(f"{nom} : essai du testeur rangé dans {dossier} (jamais publié).")
    return dossier


def _jamais_par_dessus_un_essai(dossier):
    """Un dossier du Bureau fait autrefois à partir du testeur n'est jamais écrasé (rien n'est effacé sur le Bureau sans le demander) :
    la vraie vidéo attend que le dossier soit rangé à la main."""
    import etat
    if etat.vient_du_testeur(dossier):
        raise ValueError(f"le dossier « {os.path.basename(dossier)} » du Bureau contient un essai du testeur : à ranger à la main "
                         "avant de publier la vraie séance de ce jour")


def essai_fait(config, nom):
    dossier = os.path.join(os.path.expanduser(config["sortie"]), ESSAIS, f"ESSAI-{nom}")
    return os.path.isdir(dossier) and any(n.endswith(".mp4") for n in os.listdir(dossier))


def publier(j, video, config, journal=print):
    """Copie la vidéo dans le dossier du jour, écrit la description et la couverture. Rend le dossier."""
    if est_testeur(source=j.get("source")):
        raise ValueError("séance du testeur : une vidéo du testeur ne se publie jamais (décision du 27/11/2026), voir ranger_essai")
    dossier = os.path.join(os.path.expanduser(config.get("dossier_publication") or BUREAU), j["jour"].isoformat())
    _jamais_par_dessus_un_essai(dossier)
    os.makedirs(dossier, exist_ok=True)
    copier_video(video, dossier, f"recap-{j['jour'].isoformat()}.mp4")
    with open(os.path.join(dossier, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description(j, config))
    ecrire_avant_de_publier(dossier)
    couverture(video, dossier)
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
               "Chaque séance, gains comme pertes, sur le Telegram (gratuit, rien à vendre) : lien en bio.",
               "Pas un conseil en investissement. Le trading comporte un risque de perte en capital.", "",
               " ".join(config.get("hashtags") or HASHTAGS)]
    return "\n".join(lignes).strip() + "\n"


def publier_periode(p, video, config):
    """Le dossier d'un récap de la semaine (« Semaine du AAAA-MM-JJ ») ou du mois (« Mois AAAA-MM »)."""
    import recap_periode
    if est_testeur(source=p.get("source")):
        raise ValueError("période du testeur : une vidéo du testeur ne se publie jamais (décision du 27/11/2026), voir ranger_essai")
    dossier = os.path.join(os.path.expanduser(config.get("dossier_publication") or BUREAU), recap_periode.nom_dossier(p))
    _jamais_par_dessus_un_essai(dossier)
    os.makedirs(dossier, exist_ok=True)
    copier_video(video, dossier, os.path.basename(video))
    with open(os.path.join(dossier, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description_periode(p, config))
    ecrire_avant_de_publier(dossier)
    couverture(video, dossier)
    return dossier


def periodes_finies(jours, aujourd_hui, depuis):
    """Les semaines (lundi-vendredi) et les mois finis : [(genre, début, fin)]. Une période est finie quand sa dernière séance
    possible est passée, ou quand la séance de son dernier jour de séance (calendrier de l'EA : ni férié ni demi-séance) est finie
    dans les journaux. Seules celles qui se terminent à partir de `depuis` comptent."""
    import calendrier
    import recap_periode
    finis, vues, res = set(jours), set(), []
    for jour in sorted(jours):
        for genre, (debut, fin) in (("semaine", recap_periode.semaine_de(jour)), ("mois", recap_periode.mois_de(jour))):
            if (genre, debut) in vues or fin < depuis:
                continue
            vues.add((genre, debut))
            dernier = (calendrier.jours_de_seance(debut, fin) or [fin])[-1]
            if aujourd_hui > fin or dernier in finis:
                res.append((genre, debut, fin))
    return res


def prevenir(titre, texte):
    """Une notification du système (Mac) ; rien ailleurs."""
    if sys.platform == "darwin":
        script = f'display notification {json.dumps(texte)} with title {json.dumps(titre)}'
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True, timeout=30)


def _dates(jours, n=3):
    """« mer. 4 Nov. 2026, jeu. 5 Nov. 2026 et 2 autres »."""
    jours = sorted(set(jours))
    texte = ", ".join(nombres.date_courte(j) for j in jours[:n])
    return texte + (f" et {len(jours) - n} autre{'s' if len(jours) - n > 1 else ''}" if len(jours) > n else "")


def auto(config, dossier_journaux, journal=print, aujourd_hui=None, maintenant=None):
    """Le mode automatique : chaque séance finie, depuis `auto_depuis`, qui a au moins un trade (ou toutes avec auto_sans_trade) et
    pas encore publiée, devient une vidéo prête à publier ; puis les semaines et les mois finis. Un soir manqué est rattrapé au
    lancement suivant. Rend la liste des dossiers créés.

    maintenant (avec fuseau) : l'heure du passage, pour savoir quelles séances devraient déjà être dans les journaux ; par défaut
    l'heure réelle, ou la fin du jour `aujourd_hui` à New York quand seul `aujourd_hui` est donné.
    V-20 (audit du 27/11/2026) : un seul passage à la fois (verrou), sinon deux fabrications du même jour."""
    import etat
    try:
        with etat.verrou(config):
            return _auto(config, dossier_journaux, journal, aujourd_hui, maintenant)
    except etat.DejaEnCours as err:
        journal(f"Pas de passage : {err}.")
        return []


def _auto(config, dossier_journaux, journal, aujourd_hui, maintenant):
    import calendrier
    import etat
    import journee
    import recap_periode
    if maintenant is None:
        maintenant = (datetime.datetime.now(datetime.timezone.utc) if aujourd_hui is None
                      else datetime.datetime.combine(aujourd_hui, datetime.time(23, 59), tzinfo=journee.NEW_YORK))
    aujourd_hui = aujourd_hui or datetime.date.today()
    depuis = datetime.date.fromisoformat(config["auto_depuis"]) if config.get("auto_depuis") else aujourd_hui - datetime.timedelta(days=4)
    racine = os.path.expanduser(config.get("dossier_publication") or BUREAU)
    # V-07 (audit du 27/11/2026) : la mémoire des publications est hors du Bureau (etat.py) ; ranger le dossier ne refait plus rien
    registre = etat.Registre(config, dossier_journaux, journal)
    testeur = est_testeur(dossier_journaux)          # décision du 27/11/2026 : des essais, jamais publiés ni notifiés

    def alerter(cle, titre, texte):
        """V-09 : une notification par jour au plus pour un même souci (avant : à chaque lancement, sans fin)."""
        if not testeur and registre.a_prevenir(cle, aujourd_hui):
            prevenir(titre, texte)

    def rien(cle, pourquoi):                          # V-22 : pas relu à chaque passage (jamais pour un essai du testeur)
        if not testeur:
            registre.publies[cle] = {"rien": pourquoi}
            registre.enregistrer()

    if not os.path.isdir(dossier_journaux):
        journal(f"Journaux de l'EA introuvables : {dossier_journaux}")
        # V-01 : sans journaux, rien n'était dit
        alerter("journaux-introuvables", "Étrave : journaux introuvables",
                f"Le dossier des journaux de l'EA n'existe pas ({os.path.basename(dossier_journaux) or dossier_journaux}) : aucune vidéo.")
        return []
    nettoyer_rendus(config, journal)                 # V-08 : les rendus de travail de plus de 30 jours
    voix.purger_cache(config, journal=journal)       # V-08 : les morceaux de voix recalculables de plus de 30 jours
    try:
        finis = journee.jours_finis(dossier_journaux)
        premier = journee.premier_jour(dossier_journaux)
        ny = maintenant.astimezone(journee.NEW_YORK).date()
        dernier_du = ny if calendrier.seance_due(ny, maintenant) else ny - datetime.timedelta(days=1)
        manquants = journee.seances_manquantes(dossier_journaux, depuis, dernier_du, registre.decisions)
    except Exception as err:          # V-02 : un journal illisible ne doit jamais arrêter le passage sans prévenir
        journal(f"Journaux de l'EA illisibles ({type(err).__name__} : {err}).")
        alerter("journaux-illisibles", "Étrave : journaux illisibles", f"{type(err).__name__} : {str(err)[:120]}")
        return []
    # V-01 (audit du 27/11/2026) : un jour de séance de New York sans séance dans les journaux (MetaTrader fermé, EA arrêté, « JOUR
    # MANQUÉ ») ne disait rien (« Rien de nouveau à publier »). Une notification par jour au plus, qui liste les séances absentes.
    for jour, symbole, cause in manquants:
        journal(f"{jour} : séance absente ou incomplète : {cause}. Si le robot ne tournait pas : outil.py ignorer --jour {jour}.")
    if manquants:
        alerter("absentes", "Étrave : séance absente",
                f"{_dates(m[0] for m in manquants)} : séance absente ou incomplète dans les journaux (EA arrêté ?). Semaine et mois "
                "en attente ; détail dans recap-auto.log.")
    faits = []
    for jour in finis:
        if jour < depuis:
            continue
        cle = jour.isoformat()
        if essai_fait(config, cle) if testeur else registre.publie(cle, os.path.join(racine, cle)):
            continue
        decision = registre.decision(jour)
        if decision == "ignorer":
            continue
        try:
            j = journee.charger(dossier_journaux, jour, accepter=decision == "accepter")
        except Exception as err:
            # VID-32 (26/11/2026) : une séance illisible n'était notée que dans le journal ; la notification la fait corriger.
            # V-02 : toute erreur de lecture (pas seulement JourneeIncomplete) est attrapée, les autres jours continuent.
            texte = str(err) if isinstance(err, journee.JourneeIncomplete) else f"journal abîmé ({type(err).__name__} : {err})"
            journal(f"{jour} : pas de vidéo. {texte}")
            alerter(f"illisible:{cle}", "Étrave : séance illisible",
                    f"{nombres.date_courte(jour)} : {texte[:110]} (outil.py accepter ou ignorer --jour {cle})")
            continue
        for a in j.get("avertissements", []):
            journal(f"{jour} : attention, {a}.")
        essai = testeur or est_testeur(source=j.get("source"))
        if essai and essai_fait(config, cle):
            continue
        if not essai and etat.vient_du_testeur(os.path.join(racine, cle)):
            journal(f"{jour} : le dossier « {cle} » du Bureau contient un essai du testeur ; la vraie vidéo attend qu'il soit rangé.")
            alerter(f"essai-bureau:{cle}", "Étrave : dossier à ranger", f"« {cle} » sur le Bureau est un essai du testeur : à ranger "
                    "à la main pour publier la vraie séance.")
            continue
        if not j["trades"] and not config.get("auto_sans_trade"):
            if not essai:
                rien(cle, "pas de trade (auto_sans_trade non réglé)")
            continue
        # la photo de l'onglet Historique : seulement le soir même (l'onglet montre « Aujourd'hui »), avant de monter la vidéo
        if j["trades"] and not j.get("historique") and jour == aujourd_hui and config.get("historique") and not essai:
            import historique
            # Correctif VID-04 (audit du 25/11/2026) : une photo ratée (fenêtre plus petite que le cadre…) arrêtait tout le mode
            # automatique, récaps de la semaine et du mois compris. La vidéo se fait alors sans la photo.
            try:
                j["historique"] = historique.photographier_jour(config, dossier_journaux, jour, j["trades"], journal)
            except Exception as err:
                journal(f"Photo de l'historique impossible ({type(err).__name__} : {err}) : la vidéo se fait sans.")
        sortie = _sortie_auto(config, f"recap-{jour.isoformat()}" + ("-essai" if essai else ""))
        journal(f"{jour} : {j['trades']} position(s), fabrication de la vidéo{' (essai du testeur)' if essai else ''}…")
        # Correctif VID-03 (audit du 25/11/2026) : sans voix (réseau coupé, quota ElevenLabs), la vidéo était faite muette et jamais
        # refaite : la séance attend le lancement suivant. VID-18 : la voix est exigée même sans voix_id dans la configuration (une
        # nouvelle installation publiait muet). VID-19 : la notification dit la cause, pour la corriger, et toute panne prévient.
        dossier = _fabriquer_et_publier(lambda: recap.fabriquer(j, config, sortie, journal, exiger_voix=True),
                                        (lambda video: ranger_essai(video, config, cle, journal)) if essai else
                                        (lambda video: publier(j, video, config, journal)), f"Récap du {nombres.date_courte(jour)}",
                                        cle, journal, alerter)
        if not dossier:
            continue
        if essai:
            nettoyer_travail(sortie, journal)
            continue
        registre.noter_publie(cle, dossier)
        nettoyer_travail(sortie, journal)            # V-08 : après le contrôle et la copie dans le dossier de publication
        journal(f"{jour} : prêt dans {dossier}")
        prevenir("Étrave", f"Récap du {nombres.date_courte(jour)} prêt à publier (dossier « {os.path.basename(racine)} »).")
        faits.append(dossier)
    # les récaps de la semaine et du mois, une fois la période finie (rattrapés au lancement suivant s'ils ont été manqués)
    for genre, debut, fin in periodes_finies(finis, aujourd_hui, depuis):
        if not config.get("auto_hebdo" if genre == "semaine" else "auto_mensuel", True):
            continue
        nom = recap_periode.nom_dossier({"genre": genre, "debut": debut})
        # V-22 (audit du 27/11/2026) : chaque passage rechargeait toutes les semaines et tous les mois depuis auto_depuis avant de voir
        # qu'ils étaient publiés (environ 70 s par passage après un an). Le registre d'abord.
        if essai_fait(config, nom) if testeur else registre.publie(nom, os.path.join(racine, nom)):
            continue
        # V-12 (audit du 27/11/2026) : la démo lancée le lundi 30/11 publiait le soir même « Récap du mois de novembre, une séance ».
        if premier is None or debut < premier:
            journal(f"{nom} : pas de récap, la période commence avant le premier journal de l'EA ({premier}).")
            rien(nom, f"commence avant le premier journal ({premier})")
            continue
        absents = [m for m in manquants if debut <= m[0] <= fin]
        if absents:                                  # V-01, V-03 : jamais de période avec une séance en moins
            journal(f"{nom} : pas de vidéo, séance absente ou incomplète ({_dates(m[0] for m in absents)}).")
            alerter(f"bloque:{nom}", "Étrave : récap bloqué",
                    f"{nom} : séance absente ou incomplète ({_dates([m[0] for m in absents], 2)}). outil.py ignorer ou accepter --jour.")
            continue
        try:
            p = recap_periode.charger(dossier_journaux, debut, fin, genre, registre.decisions)
        except Exception as err:      # VID-07 : jamais de période avec une séance en moins ; V-02 : toute erreur est attrapée
            journal(f"{nom} : pas de vidéo. {type(err).__name__} : {err}")
            # VID-32 : la période attend que la séance soit corrigée ; la notification dit laquelle
            alerter(f"bloque:{nom}", "Étrave : récap bloqué", f"{nom} : {str(err)[:140]}")
            continue
        if not p["jours"] or (not p["avec"] and not config.get("auto_sans_trade")):
            rien(nom, "aucune séance tradée")
            continue
        essai = testeur or est_testeur(source=p.get("source"))
        if essai and essai_fait(config, nom):
            continue
        if not essai and etat.vient_du_testeur(os.path.join(racine, nom)):
            journal(f"{nom} : le dossier du Bureau contient un essai du testeur ; la vraie vidéo attend qu'il soit rangé.")
            alerter(f"essai-bureau:{nom}", "Étrave : dossier à ranger", f"« {nom} » sur le Bureau est un essai du testeur : à ranger à la main.")
            continue
        sortie = _sortie_auto(config, nom.replace(" ", "-").lower() + ("-essai" if essai else ""))
        journal(f"{nom} : {len(p['avec'])} jour(s) de trade, fabrication de la vidéo…")
        dossier = _fabriquer_et_publier(lambda: recap_periode.fabriquer(p, config, sortie, journal, exiger_voix=True),
                                        (lambda video: ranger_essai(video, config, nom, journal)) if essai else
                                        (lambda video: publier_periode(p, video, config)), nom, nom, journal, alerter)
        if not dossier:
            continue
        if essai:
            nettoyer_travail(sortie, journal)
            continue
        registre.noter_publie(nom, dossier)
        nettoyer_travail(sortie, journal)
        journal(f"{nom} : prêt dans {dossier}")
        prevenir("Étrave", f"{nom} : récap prêt à publier.")
        faits.append(dossier)
    if not faits:
        journal(f"Rien de nouveau à publier ({aujourd_hui.isoformat()}).")
    return faits


def _fabriquer_et_publier(fabriquer, publier_, quoi, cle, journal, alerter):
    """La vidéo puis son dossier de publication ; None après une panne (prévenue, refaite au lancement suivant)."""
    import recap as recap_
    try:
        return publier_(fabriquer())
    except voix.VoixIndisponible as err:
        journal(f"{quoi} : voix indisponible : {err}. Pas de vidéo muette : nouvel essai au prochain lancement.")
        alerter(f"voix:{cle}", "Étrave : pas de voix", f"{quoi} : {str(err)[:150]}")
    except (recap_.CommandeBloquee, subprocess.TimeoutExpired) as err:   # V-06 : un rendu ou un ffmpeg bloqué est arrêté, et prévenu
        journal(f"{quoi} : {err}. Nouvel essai au prochain lancement.")
        alerter(f"bloque-rendu:{cle}", "Étrave : rendu bloqué", f"{quoi} : {str(err)[:150]}")
    except Exception as err:       # une séance ratée ne doit pas bloquer les suivantes ; elle sera retentée au prochain lancement
        journal(f"{quoi} : échec ({type(err).__name__} : {err}). Nouvel essai au prochain lancement.")
        alerter(f"echec:{cle}", "Étrave : échec", f"{quoi} : {type(err).__name__}, détail dans recap-auto.log")
    return None


# V-08 (audit du 27/11/2026) : chaque rendu gardait environ 100 Mo (son/ en WAV 24 bits, projet/, image-muette.mp4), sans jamais rien
# effacer : 25 à 30 Go par an. En mode automatique, ils sont effacés une fois la vidéo contrôlée et copiée dans le dossier de
# publication (la vidéo, recap.json et controle.txt restent), et les dossiers de rendu de plus de 30 jours sont purgés.
TRAVAIL = ("son", "projet", "image-muette.mp4")
GARDE_JOURS = 30


def nettoyer_travail(sortie, journal=print):
    """Les fichiers de travail d'un rendu, une fois la vidéo publiée : controle.txt (le contrôle du son) passe à côté de la vidéo."""
    controle_ = os.path.join(sortie, "son", "controle.txt")
    if os.path.exists(controle_):
        os.replace(controle_, os.path.join(sortie, "controle.txt"))
    for nom in TRAVAIL:
        chemin = os.path.join(sortie, nom)
        try:
            if os.path.isdir(chemin):
                shutil.rmtree(chemin)
            elif os.path.exists(chemin):
                os.remove(chemin)
        except OSError as err:
            journal(f"Nettoyage de {chemin} impossible : {err}")


MARQUE_AUTO = ".rendu-auto"


def _rendu_auto(chemin, nom):
    """Seuls les dossiers que le mode automatique a créés lui-même (nom et marque) sont purgés : jamais un récap fait à la main, un
    essai du testeur ou la présentation, même si `auto` tourne avec la configuration de tous les jours."""
    import re
    return (bool(re.fullmatch(r"recap-\d{4}-\d{2}-\d{2}|semaine-du-\d{4}-\d{2}-\d{2}|mois-\d{4}-\d{2}", nom))
            and os.path.exists(os.path.join(chemin, MARQUE_AUTO)))


def _sortie_auto(config, nom):
    sortie = os.path.join(os.path.expanduser(config["sortie"]), nom)
    os.makedirs(sortie, exist_ok=True)
    open(os.path.join(sortie, MARQUE_AUTO), "w").close()
    return sortie


def nettoyer_rendus(config, journal=print, maintenant=None):
    """Les dossiers de rendu du mode automatique de plus de GARDE_JOURS jours (date de modification), dans `sortie`."""
    import time
    racine = os.path.expanduser(config.get("sortie") or "")
    if not racine or not os.path.isdir(racine):
        return []
    limite = (maintenant or time.time()) - GARDE_JOURS * 86400
    purges = []
    for nom in sorted(os.listdir(racine)):
        chemin = os.path.join(racine, nom)
        try:
            if os.path.isdir(chemin) and _rendu_auto(chemin, nom) and os.path.getmtime(chemin) < limite:
                shutil.rmtree(chemin)
                purges.append(nom)
        except OSError as err:
            journal(f"Purge de {chemin} impossible : {err}")
    if purges:
        journal(f"{len(purges)} rendu(s) de plus de {GARDE_JOURS} jours effacé(s) : {', '.join(purges[:5])}…")
    return purges
