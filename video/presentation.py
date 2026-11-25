"""La vidéo de présentation de la chaîne (47,62 s) : le modèle `modeles/presentation/` rempli avec ton profil, rendu, puis ta voix et
les bruitages posés comme dans la version 6.

Ce qui est personnel n'est pas dans le dépôt : prénom, années de trading, montant et image du certificat, fichiers de ta voix. Ils sont
dans la partie « presentation » de ta configuration privée :

    "presentation": {
      "nom": "Prénom", "annees": 6, "montant": "12 345,67 $", "libelle_montant": "de récompenses <prop firm>",
      "certificat": "~/chemin/certificat.png", "alt_certificat": "Certificat de …",
      "voix": "~/chemin/du/dossier/des/repliques"      (1-accroche.mp3, 2-preuve.mp3, 3-robot.mp3, 3b-secret.mp3, …)
    }

Le minutage des scènes est celui des prises de la v6 : une autre prise ou un autre texte demande de recaler les scènes (data-start et
data-duration de index.html, et les instants des compositions) et les départs des répliques ci-dessous.
"""
import html
import json
import os
import shutil
import subprocess

import mixage

ICI = os.path.dirname(os.path.abspath(__file__))
MODELE = os.path.join(ICI, "modeles", "presentation")
HYPERFRAMES = [shutil.which("npx") or "npx", "-y", "hyperframes@0.9.94"]   # VID-01 : npx.cmd sous Windows
DUREE = 47.62
# (fichier de la réplique, départ dans la vidéo en s, coupe en s) : la prise 3 s'arrête dans le silence après « il vend. »
REPLIQUES = [("1-accroche", 0.10, None), ("2-preuve", 5.35, None), ("3-robot", 11.20, 9.45), ("3b-secret", 20.95, None),
             ("4-seance", 30.12, None), ("5-copie", 34.92, None), ("5b-copie", 38.92, None), ("6-fin", 43.17, None)]


def colonnes_montant(montant):
    """« 12 345,67 $ » → une colonne qui roule par chiffre, le reste (espaces, virgule, devise) tel quel."""
    morceaux, sep = [], ""
    for c in montant:
        if c.isdigit():
            if sep:
                morceaux.append(f'<span class="pr-sep">{html.escape(sep)}</span>')
                sep = ""
            morceaux.append(f'<span class="pr-col" data-chiffre="{c}"></span>')
        else:
            sep += c
    if sep:
        morceaux.append(f'<span class="pr-sep">{html.escape(sep)}</span>')
    return "".join(morceaux)


def bande_annees(annees):
    """Le chiffre des années roule jusqu'au « 5 » de « 15:30 » (le « 1 » s'écrit devant) : la bande et la distance à parcourir."""
    d = int(annees) % 10
    chiffres = [(d + k) % 10 for k in range(10)]
    pas = chiffres.index(5)
    return "".join(f"<span>{c}</span>" for c in chiffres[:pas + 1]), -220 * pas


def remplir(profil, projet):
    if int(profil["annees"]) not in range(1, 10):
        raise ValueError("« annees » : un seul chiffre (1 à 9), le chiffre qui roule jusqu'à 15:30.")
    bande, roulement = bande_annees(profil["annees"])
    valeurs = {
        "{{NOM}}": html.escape(profil["nom"]), "{{ANNEES}}": str(int(profil["annees"])), "{{MONTANT}}": html.escape(profil["montant"]),
        "{{MONTANT_COLONNES}}": colonnes_montant(profil["montant"]), "{{LIBELLE_MONTANT}}": html.escape(profil.get("libelle_montant", "")),
        "{{ALT_CERTIFICAT}}": html.escape(profil.get("alt_certificat", "Certificat")), "{{BANDE}}": bande, "{{ROULEMENT}}": str(roulement),
    }
    for racine, _, fichiers in os.walk(projet):
        for nom in fichiers:
            if nom.endswith(".html"):
                chemin = os.path.join(racine, nom)
                texte = open(chemin, encoding="utf-8").read()
                for cle, v in valeurs.items():
                    texte = texte.replace(cle, v)
                if "{{" in texte:
                    raise ValueError(f"Valeur du profil manquante dans {nom}.")
                open(chemin, "w", encoding="utf-8").write(texte)


def fabriquer(config, journal=print):
    profil = config.get("presentation")
    if not profil:
        raise SystemExit("La configuration n'a pas de partie « presentation » (voir video/config.exemple.json).")
    sortie = os.path.join(os.path.expanduser(config["sortie"]), "presentation")
    projet = os.path.join(sortie, "projet")
    if os.path.isdir(projet):
        shutil.rmtree(projet)
    shutil.copytree(MODELE, projet, ignore=shutil.ignore_patterns("bruitages.json"))
    os.makedirs(os.path.join(projet, "assets", "fonts"), exist_ok=True)
    shutil.copy(os.path.expanduser(config["police"]), os.path.join(projet, "assets", "fonts", "din-alternate-bold.ttf"))
    shutil.copy(os.path.expanduser(profil["certificat"]), os.path.join(projet, "assets", "certificat.png"))
    remplir(profil, projet)
    journal(f"Rendu de l'image ({DUREE} s)…")
    muette = os.path.abspath(os.path.join(sortie, "image-muette.mp4"))
    subprocess.run(HYPERFRAMES + ["render", "--quality", "delivery", "--output", muette], cwd=projet, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    travail = os.path.join(sortie, "son")
    os.makedirs(travail, exist_ok=True)
    dossier_voix = os.path.expanduser(profil.get("voix", ""))
    repliques = [{"fichier": os.path.join(dossier_voix, f"{n}.mp3"), "t": t, "coupe": c} for n, t, c in REPLIQUES
                 if os.path.exists(os.path.join(dossier_voix, f"{n}.mp3"))]
    if len(repliques) < len(REPLIQUES):
        journal(f"{len(REPLIQUES) - len(repliques)} réplique(s) absente(s) de {dossier_voix or '(pas de dossier de voix)'}.")
    voix = mixage.piste_voix(repliques, DUREE, os.path.join(travail, "voix.wav"))
    reperes = json.load(open(os.path.join(MODELE, "bruitages.json"), encoding="utf-8"))["bruitages"]
    bruitages, manquants = mixage.piste_bruitages(reperes, config.get("sons"), DUREE, os.path.join(travail, "bruitages.wav"))
    if manquants:
        journal(f"{len(manquants)} bruitage(s) absent(s) : python3 video/outil.py sons")
    # la musique de fond : `musique_presentation` si tu en choisis une, sinon le premier morceau du dossier `musique`
    musique = mixage.piste_musique(config.get("musique_presentation") or config.get("musique"), None, DUREE,
                                   os.path.join(travail, "musique.wav"), journal)
    finale = os.path.join(sortie, "presentation-etrave.mp4")
    mixage.assembler(muette, voix, bruitages, finale, travail, musique)
    return finale


COUVERTURE = os.path.join(ICI, "modeles", "couverture-presentation")


def couverture(config, sortie_jpg, journal=print):
    """La couverture de la vidéo de présentation (1080 x 1920, JPG) : l'accroche, le logo, les marchés, le certificat."""
    profil = config.get("presentation") or {}
    travail = os.path.join(os.path.expanduser(config["sortie"]), "presentation", "couverture")
    if os.path.isdir(travail):
        shutil.rmtree(travail)
    shutil.copytree(COUVERTURE, travail)
    os.makedirs(os.path.join(travail, "assets", "fonts"), exist_ok=True)
    shutil.copy(os.path.expanduser(config["police"]), os.path.join(travail, "assets", "fonts", "din-alternate-bold.ttf"))
    shutil.copy(os.path.expanduser(profil["certificat"]), os.path.join(travail, "assets", "certificat.png"))
    remplir(profil, travail)
    images = os.path.join(travail, "images")
    subprocess.run(HYPERFRAMES + ["snapshot", "--at", "0.5", "--no-end", "-o", images], cwd=travail, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    png = next(os.path.join(images, n) for n in sorted(os.listdir(images)) if n.startswith("frame-") and n.endswith(".png"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", png, "-q:v", "2", sortie_jpg], check=True)
    return sortie_jpg

