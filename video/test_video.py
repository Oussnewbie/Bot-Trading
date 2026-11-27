"""Contrôles de l'outil vidéo : nombres en lettres, lecture d'une journée (heure de Paris, séance finie, bougies), textes de la voix
(rien de secret, R expliqué), aucune mention du testeur à l'image, modèle de la présentation, et rien de personnel dans le dépôt."""
import datetime
import glob
import json
import os
import re
import sys

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
sys.path.insert(0, os.path.join(ICI, "..", "etrave"))
import journee       # noqa: E402
import mixage        # noqa: E402
import nombres       # noqa: E402
import presentation  # noqa: E402
import recap         # noqa: E402

sys.path.insert(0, os.path.join(ICI, "..", "robot"))
import test_robot    # noqa: E402  (l'empreinte des noms de prop firm)

UTC = datetime.timezone.utc


@pytest.fixture(autouse=True)
def garde_fous(tmp_path_factory, monkeypatch):
    """Aucune notification réelle (osascript) pendant les tests, et aucun état du mode automatique (registre des publications,
    verrou) écrit hors d'un dossier jetable : ni ~/Library/Application Support/Etrave, ni le Bureau. Rend les notifications."""
    import publication
    notes = []
    monkeypatch.setattr(publication, "prevenir", lambda titre, texte: notes.append((titre, texte)))
    try:
        import etat
        monkeypatch.setattr(etat, "DOSSIER", str(tmp_path_factory.mktemp("etat")))
    except ImportError:          # code d'avant le 27/11/2026 (preuve que les nouveaux tests échouaient)
        pass
    import voix                  # ni le vrai cache des voix (V-08 le purge)
    monkeypatch.setattr(voix, "CACHE", str(tmp_path_factory.mktemp("cache-voix")), raising=False)
    return notes


# ───────────────────────── nombres ─────────────────────────
@pytest.mark.parametrize("n, texte", [(0, "zéro"), (21, "vingt et un"), (71, "soixante et onze"), (80, "quatre-vingts"),
                                      (81, "quatre-vingt-un"), (91, "quatre-vingt-onze"), (100, "cent"), (180, "cent quatre-vingts"),
                                      (200, "deux cents"), (201, "deux cent un"), (1000, "mille"), (2026, "deux mille vingt-six"),
                                      (-3, "moins trois")])
def test_entiers(n, texte):
    assert nombres.entier(n) == texte


def test_decimaux_heures_dates():
    assert nombres.decimal(0.42, signe=True) == "plus zéro virgule quarante-deux"
    assert nombres.decimal(-0.05, signe=True) == "moins zéro virgule zéro cinq"
    assert nombres.decimal(-2.6717, 2, signe=True) == "moins deux virgule soixante-sept"
    assert nombres.decimal(0.0, signe=True) == "zéro"
    assert nombres.heure(21, 50) == "vingt et une heures cinquante"
    assert nombres.heure(15, 0) == "quinze heures" and nombres.heure(1, 5) == "une heure cinq"
    assert nombres.date_longue(datetime.date(2026, 12, 1)) == "mardi premier décembre"
    assert nombres.nombre_ecran(-2.6717) == "−2,67" and nombres.nombre_ecran(0.4) == "+0,40" and nombres.nombre_ecran(0) == "0,00"


# ───────────────────────── une journée écrite comme par l'EA ─────────────────────────
ENTETES = {
    "seances": "version;source;jour_ny;symbole;moment;heure_ny;range_bas;range_haut;range_prix;stop_mult;spread;cout_r;filtres;etat",
    "bougies": "version;source;jour_ny;symbole;heure_ny;ouverture;haut;bas;cloture;ticks",
    "execution": ("version;source;id_position;jour_ny;symbole;entree;sens;lots;entree_utc_ms;entree_ny;prix_vise;prix_entree;"
                  "glissement_entree;spread_entree;stop_initial;risque_prix;sortie_utc_ms;sortie_ny;stop_en_place;stop_virtuel;"
                  "prix_sortie;glissement_sortie;raison;raison_courtier;mfe_prix;mae_prix;mfe_r;mae_r;excursion;frais;swap;"
                  "resultat_net;r;range_prix;stop_mult;devise;complet"),
}


def ms(jour, hh, mm, tz=journee.NEW_YORK):
    return int(datetime.datetime(jour.year, jour.month, jour.day, hh, mm, tzinfo=tz).timestamp() * 1000)


def ecrire_journee(dossier, jour, source="reel", fin=True, bougies=True, positions=((1, "A", 9, 36, 100.0, 15, 50, 112.0, "Fin de journée"),)):
    j = jour.isoformat()
    sec = [f"1;{source};{j};NDX100;decision;09:35;95.00;101.00;6.00;3.00;0.6;0.02;Achat oui · RSI 55 (élan);Range traité"]
    if fin:
        sec.append(f"1;{source};{j};NDX100;fin;15:52;95.00;101.00;6.00;3.00;0.6;0.02;Achat oui · RSI 55 (élan);Pas de trade : vente bloquée (RSI)")
    lignes = {"seances": sec, "bougies": [], "execution": []}
    if bougies:
        for k in range(84):
            h, m = divmod(9 * 60 + 5 * k, 60)
            lignes["bougies"].append(f"1;{source};{j};NDX100;{h:02d}:{m:02d};100;102;98;101;500")
    for i, (sens, typ, he, me, pe, hs, mins, ps, raison) in enumerate(positions):
        net = (ps - pe) * sens * 10
        lignes["execution"].append(f"1;{source};{i + 1};{j};NDX100;{typ};{sens};1.00;{ms(jour, he, me)};;{pe};{pe};0;0.6;{pe - 18 * sens};18;"
                                   f"{ms(jour, hs, mins)};;;;{ps};;{raison};EA;;;;;;0;0;{net:.2f};{net / 180:.4f};6;3;USD;1")
    for base, contenu in lignes.items():
        with open(os.path.join(dossier, f"{base}-NDX100.csv"), "w", encoding="utf-8") as f:
            f.write(ENTETES[base] + "\r\n" + "".join(l + "\r\n" for l in contenu))


def test_journee_heure_de_paris_meme_quand_l_ecart_est_de_5_h(tmp_path):
    jour = datetime.date(2026, 3, 10)                  # New York à l'heure d'été, pas encore Paris : 9:36 → 14:36
    ecrire_journee(str(tmp_path), jour)
    j = journee.charger(str(tmp_path))
    m = j["marches"][0]
    assert j["jour"] == jour and m["nom"] == "Nasdaq 100" and m["instrument"] == "nasdaq"
    assert m["bougies"][0]["heure"].strftime("%H:%M") == "14:00" and m["positions"][0]["entree"].strftime("%H:%M") == "14:36"
    assert m["positions"][0]["points"] == pytest.approx(12.0) and m["zone"] == {"bas": 95.0, "haut": 101.0}
    jour2 = datetime.date(2026, 4, 16)                 # écart habituel de 6 h
    ecrire_journee(str(tmp_path), jour2)
    assert journee.charger(str(tmp_path), jour2)["marches"][0]["positions"][0]["entree"].strftime("%H:%M") == "15:36"


def test_journee_refusee_sans_ligne_fin_ou_sans_bougies(tmp_path):
    jour = datetime.date(2026, 4, 16)
    ecrire_journee(str(tmp_path), jour, fin=False)
    with pytest.raises(journee.JourneeIncomplete, match="Aucune séance finie"):
        journee.charger(str(tmp_path))
    ecrire_journee(str(tmp_path), jour, bougies=False)
    with pytest.raises(journee.JourneeIncomplete, match="Pas de bougies"):
        journee.charger(str(tmp_path), jour)


def _journee(tmp_path, source="reel", positions=None):
    jour = datetime.date(2026, 4, 16)
    kw = {} if positions is None else {"positions": positions}
    ecrire_journee(str(tmp_path), jour, source=source, **kw)
    return journee.charger(str(tmp_path), jour)


def test_voix_sans_secret_et_r_explique_une_fois(tmp_path):
    j = _journee(tmp_path, positions=((-1, "A", 9, 36, 100, 11, 36, 115, "Stop"), (-1, "D1", 9, 41, 99, 15, 50, 104, "Fin de journée"),
                                      (-1, "B", 9, 55, 98, 15, 50, 104, "Fin de journée")))
    textes = recap.repliques(j, recap.unite_du_jour(j))
    tout = " ".join(textes)
    for secret in ("RSI", "élan", "D1", " B ", "Range traité", "bloquée", "filtre"):
        assert secret not in tout
    assert tout.count("Un R, c'est le risque pris sur un trade.") == 1
    assert textes[1].startswith("Nasdaq. Quinze heures trente-six : le prix casse la zone par le bas, le robot vend. Trois ventes en tout. "
                                "La première vente part aussitôt contre nous : stop touché, quinze points plus haut. "
                                "Les deux autres tiennent jusqu'à la fin de séance. Résultat : moins ")
    assert textes[0] == "Jeudi seize avril. Journée rouge pour le robot… on regarde ça !"
    assert textes[-1].endswith("Abonne-toi pour voir la séance de demain !") and recap.mot_du_jour(j, recap.total(j, "r")) in textes[-1]


def test_meme_scenario_pas_raconte_deux_fois(tmp_path):
    j = _journee(tmp_path, positions=((1, "A", 9, 36, 100, 15, 50, 110, "Fin de journée"), (1, "D1", 9, 41, 101, 15, 50, 110, "Fin de journée")))
    m = j["marches"][0]
    j["marches"].append(dict(m, nom="S&P 500", voix="S et P cinq cents", symbole="SPX500", r=0.42))
    textes = recap.repliques(j, "r")
    assert textes[0].startswith("Jeudi seize avril. Journée verte")
    assert "le robot achète. Deux achats en tout. Les deux positions tiennent jusqu'à la fin de séance. Résultat : plus" in textes[1]
    assert textes[2] == "Même scénario sur le S et P cinq cents. Les deux positions tiennent jusqu'à la fin de séance. Résultat : plus zéro virgule quarante-deux R."
    assert "Un R, c'est le risque" not in textes[2]


def _pos(sens, he, ps, pe, raison, mfe, risque, minute=0):
    t = datetime.datetime(2026, 4, 16, he, minute, tzinfo=UTC)
    return {"sens": sens, "entree": t, "sortie": t + datetime.timedelta(hours=1), "prix_entree": pe, "prix_sortie": ps,
            "points": (ps - pe) * sens, "raison": raison, "mfe": mfe, "risque": risque, "r": None}


def test_le_mouvement_du_prix_est_raconte_en_points():
    """Jusqu'où le prix est allé en notre faveur avant le stop, de combien il s'est retourné, ce que les autres ont tenu."""
    stop = _pos(-1, 14, 160.0, 100.0, "Stop", 25.0, 60.0, 5)
    fin = _pos(-1, 13, 70.1, 100.0, "Fin de journée", 276.0, 300.0, 35)
    f = recap.faits({"positions": [fin, stop]})
    assert recap.phrase_stops(f) == ("La dernière vente va jusqu'à vingt-cinq points en notre faveur… puis le marché se retourne de "
                                     "quatre-vingt-cinq points : stop touché.")
    assert recap.phrase_fins(f) == ("L'autre position tient jusqu'à la fin de séance : jusqu'à deux cent soixante-seize points "
                                    "en notre faveur, puis le prix remonte.")
    aussitot = recap.faits({"positions": [_pos(1, 13, 96.5, 100.0, "Stop", 0.4, 3.5)]})
    assert recap.phrase_stops(aussitot) == "Le prix part aussitôt contre nous : stop touché, trois virgule cinq points plus bas."
    gagnant = recap.faits({"positions": [_pos(1, 13, 151.0, 100.0, "Stop remonté", 106.1, 36.0)]})
    assert recap.phrase_stops(gagnant) == ("Le prix va jusqu'à cent six points en notre faveur, puis sort au stop, "
                                           "avec cinquante et un points de gain.")
    assert recap.pts_ecran(-297.2) == "−297 pts" and recap.pts_ecran(0.57) == "+0,6 pt" and recap.pts_ecran(14.12) == "+14 pts"


def test_jour_sans_trade_ne_dit_pas_pourquoi(tmp_path):
    j = _journee(tmp_path, positions=())
    textes = recap.repliques(j, "r")
    # V-10 (27/11/2026, règle changée par le propriétaire) : « les conditions n'étaient pas réunies » était faux un jour bloqué (heure
    # du serveur, compte non autorisé, marché décoché, férié) ; « Le robot n'a pas tradé aujourd'hui », quelle que soit la raison
    assert "Nasdaq : le robot n'a pas tradé aujourd'hui." in textes[1] and "Journée sans trade" in textes[0]
    assert "RSI" not in " ".join(textes) and recap.mot_du_jour(j, None) in recap.MOTS_DU_JOUR["rien"]


def test_total_egal_a_la_somme_des_valeurs_affichees():
    j = {"marches": [{"positions": [1], "r": -1.4972}, {"positions": [1], "r": -0.5551}], "trades": 2}
    assert recap.total(j, "r") == -2.06          # −1,50 et −0,56 à l'écran : le total affiché doit être −2,06, pas −2,05


def test_seance_tradee_jamais_racontee_comme_sans_trade(tmp_path):
    jour = datetime.date(2026, 4, 16)
    ecrire_journee(str(tmp_path), jour, positions=())
    # l'état de fin dit qu'un trade a eu lieu, mais le journal d'exécution est vide (MetaTrader arrêté avant de l'écrire)
    chemin = os.path.join(str(tmp_path), "seances-NDX100.csv")
    texte = open(chemin, encoding="utf-8").read().replace("Pas de trade : vente bloquée (RSI)", "Achat terminé (Fin de journée)")
    open(chemin, "w", encoding="utf-8").write(texte)
    with pytest.raises(journee.JourneeIncomplete, match="aucune position"):
        journee.charger(str(tmp_path), jour)
    # le journal des trades du compte (écrit à chaque clôture) ne retrouve pas le journal d'exécution
    ecrire_journee(str(tmp_path), jour)
    sortie = int(datetime.datetime(2026, 4, 16, 19, 50, tzinfo=UTC).timestamp())
    with open(os.path.join(str(tmp_path), "trades-NDX100.csv"), "w", encoding="utf-8") as f:
        f.write(f"{sortie};2026.04.16;15:50;NDX100;1;1.00;0.67;120.00;10000;Fin de journée;0;USD\r\n"
                f"{sortie};2026.04.16;15:50;NDX100;1;1.00;-1.00;-180.00;10000;Stop;0;USD\r\n")
    with pytest.raises(journee.JourneeIncomplete, match="ne retrouve pas"):
        journee.charger(str(tmp_path), jour)
    with open(os.path.join(str(tmp_path), "trades-NDX100.csv"), "w", encoding="utf-8") as f:
        f.write(f"{sortie};2026.04.16;15:50;NDX100;1;1.00;0.67;120.00;10000;Fin de journée;0;USD\r\n")
    m = journee.charger(str(tmp_path), jour)["marches"][0]
    assert m["pct"] == pytest.approx(1.2) and len(m["positions"]) == 1


def test_aucune_mention_demo_ou_reel_dans_l_image(tmp_path):
    """Tu dis démo ou réel dans la description : l'image n'en parle jamais, même pour une journée du testeur."""
    j = _journee(tmp_path, source="testeur")
    assert j["source"] == "testeur"
    images = [recap._index([{"id": "titre", "debut": 0, "duree": 3}], 3), recap.scene_titre(j, None, "r")[1],
              recap.scene_marche(j, j["marches"][0], 0, None, "r", 7.0)[1], recap.scene_bilan(j, None, "r", recap.repliques(j, "r")[-1])[1]]
    for texte in images + recap.repliques(j, "r"):
        for mot in ("Exemple", "testeur", "démo", "réel", "simulation"):
            assert mot not in texte, mot


def test_les_scenes_n_affichent_pas_le_type_d_entree(tmp_path):
    j = _journee(tmp_path, positions=((1, "D2", 9, 40, 100, 15, 50, 110, "Fin de journée"),))
    style, corps, script, reperes, fin = recap.scene_marche(j, j["marches"][0], 0, None, "r", 7.0)
    assert "D2" not in corps and "Le prix casse par le haut" in corps and "Achat 15:40" in corps
    # 27/11/2026 : les sons répétés sont désignés par leur famille (« @clic »), dont la prise est choisie au montage (V-17)
    assert all(r["son"] in mixage.catalogue() for r in recap.distribuer_prises([dict(r) for r in reperes]))


PASTILLE = re.compile(r'class="pastille[^"]*" style="left:(\d+)px; top:(\d+)px; font-size:(\d+)px[^"]*">([^<]+)<')


@pytest.mark.parametrize("positions", [
    ((1, "A", 9, 36, 100, 15, 50, 112.0, "Fin de journée"),),
    ((-1, "A", 9, 36, 100, 10, 2, 112, "Stop"), (-1, "D1", 9, 41, 99, 15, 50, 90, "Fin de journée"),
     (-1, "B", 9, 55, 98, 15, 50, 90, "Fin de journée"), (-1, "D2", 10, 30, 97, 15, 50, 90, "Fin de journée")),
    (),
])
def test_etiquettes_dans_les_zones_sures_de_tiktok(tmp_path, positions):
    """Chaque étiquette tient entre y = 240 et y = 1260 ; à gauche de x = 960 au-dessus de y = 840, de x = 780 en dessous."""
    j = _journee(tmp_path, positions=positions)
    morceaux = [recap.scene_marche(j, j["marches"][0], 0, None, "r", 7.0, True)[1], recap.scene_titre(j, None, "r")[1],
                recap.scene_bilan(j, None, "r", recap.repliques(j, "r")[-1])[1]]
    vues = 0
    for corps in morceaux:
        for gauche, haut, taille, texte in PASTILLE.findall(corps):
            gauche, haut, taille = int(gauche), int(haut), int(taille)
            droite, bas = gauche + recap._l(texte, taille), haut + taille * 1.34
            assert haut >= 240 and bas <= 1260, texte
            assert droite <= (780 if bas > 840 else 960) + 1, (texte, droite)
            vues += 1
    assert vues >= 3


def test_couleur_du_resultat():
    assert recap.couleur(1.2) == recap.COUL["vert"] and recap.couleur(-0.3) == recap.COUL["rouge"]
    assert recap.couleur(0.001) == recap.couleur(None) == recap.COUL["encre2"]


def test_camera_reste_dans_le_graphique():
    for px, py in ((recap.X0, recap.Y_HAUT), (recap.X1, recap.Y_BAS), (500, 650)):
        (tx, ty, s), (fx, fy) = recap.camera(px, py)
        # les bords du graphique, une fois zoomés, restent hors du cadre : on ne voit jamais au-delà du graphique
        assert s * recap.X0 + tx <= recap.X0 + 0.01 and s * recap.X1 + tx >= recap.X1 - 0.01
        assert s * recap.Y_HAUT + ty <= recap.Y_HAUT + 0.01 and s * recap.Y_BAS + ty >= recap.Y_BAS - 0.01
        assert recap.X0 - 0.01 <= fx <= recap.X1 + 0.01 and recap.Y_HAUT - 0.01 <= fy <= recap.Y_BAS + 0.01


def test_musique_du_jour(tmp_path):
    assert mixage.choisir_musique(None, datetime.date(2026, 11, 18)) is None
    assert mixage.choisir_musique(str(tmp_path / "absent"), datetime.date(2026, 11, 18)) is None
    for nom in ("b.mp3", "a.wav", "notes.txt"):
        (tmp_path / nom).write_bytes(b"")
    choix = {os.path.basename(mixage.choisir_musique(str(tmp_path), datetime.date(2026, 11, d))) for d in (17, 18)}
    assert choix == {"a.wav", "b.mp3"}


# ───────────────────────── présentation ─────────────────────────
def test_presentation_montant_et_annees():
    assert presentation.colonnes_montant("1 234,5 $").count('class="pr-col"') == 5
    bande, roulement = presentation.bande_annees(6)
    assert bande.count("<span>") == 10 and roulement == -1980 and bande.startswith("<span>6</span>") and bande.endswith("<span>5</span>")
    bande, roulement = presentation.bande_annees(5)
    assert bande == "<span>5</span>" and roulement == 0


def test_presentation_remplie_sans_reste(tmp_path):
    import shutil
    shutil.copytree(presentation.MODELE, tmp_path / "p")
    presentation.remplir({"nom": "Alex", "annees": 4, "montant": "1 000,00 $", "certificat": ""}, str(tmp_path / "p"))
    for f in glob.glob(str(tmp_path / "p" / "**" / "*.html"), recursive=True):
        assert "{{" not in open(f, encoding="utf-8").read()
    bruitages = json.load(open(os.path.join(presentation.MODELE, "bruitages.json"), encoding="utf-8"))["bruitages"]
    assert all(b["son"] in mixage.catalogue() for b in bruitages)


# ───────────────────────── le dépôt est public ─────────────────────────
def _personnel():
    """Ce qui est personnel, lu dans ta configuration privée (jamais écrit dans le dépôt, même pas dans ce test)."""
    chemin = os.path.expanduser("~/.config/etrave-video/config.json")
    if not os.path.exists(chemin):
        return []
    c = json.load(open(chemin, encoding="utf-8"))
    p = c.get("presentation", {})
    return [v for v in (c.get("voix_id"), p.get("nom"), p.get("montant")) if v and len(v) > 3]


def test_rien_de_personnel_ni_de_fichier_sous_licence_dans_video():
    interdits = _personnel() + [os.path.expanduser("~")]
    for chemin in glob.glob(os.path.join(ICI, "**", "*"), recursive=True):
        if os.path.isdir(chemin) or "__pycache__" in chemin:
            continue
        assert not re.search(r"\.(wav|mp3|m4a|ttf|otf|png|jpe?g|mp4)$", chemin, re.I), chemin   # sons, polices, certificat, voix, rendus
        texte = open(chemin, encoding="utf-8", errors="replace").read()
        assert not re.search(r"sk_[A-Za-z0-9]{20,}", texte), chemin                                # une clé d'API
        for interdit in interdits:
            assert interdit not in texte, (chemin, "donnée personnelle")
        assert not test_robot.noms_de_prop_firm(texte), (chemin, "prop firm nommée")       # conformité TikTok : jamais nommée


# ───────────────────────── publication automatique ─────────────────────────
import publication  # noqa: E402


def test_description_tiktok_dit_le_compte_sans_rien_de_secret(tmp_path):
    j = _journee(tmp_path, positions=((1, "D2", 9, 40, 100, 15, 50, 110, "Fin de journée"),))
    texte = publication.description(j, {})
    assert texte.startswith("Journée verte : récap de la séance du jeudi 16 Avril 2026.")
    assert "Trades réels, sur mon compte." in texte and "Nasdaq 100 : +" in texte and "Pas un conseil en investissement." in texte
    assert "D2" not in texte and "RSI" not in texte and "élan" not in texte
    assert "sur le Telegram (gratuit, rien à vendre) : lien en bio." in texte          # conformité TikTok : seulement ici
    j["source"] = "demo"
    assert "compte démo" in publication.description(j, {})
    assert "Mon texte" in publication.description(j, {"mention_compte": "Mon texte"})


def test_mode_automatique(tmp_path, monkeypatch):
    """Une vidéo par séance finie avec un trade, depuis auto_depuis ; rien pour un jour sans trade ; rien deux fois."""
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_journee(str(journaux), datetime.date(2026, 4, 16))
    faites = []

    def fausse_video(j, config, sortie, journal=print, rendre=True, exiger_voix=False):
        faites.append(j["jour"])
        chemin = os.path.join(sortie, "video.mp4")
        open(chemin, "wb").write(b"\0")
        return chemin
    monkeypatch.setattr(publication.recap, "fabriquer", fausse_video)
    monkeypatch.setattr(publication.subprocess, "run", lambda *a, **k: None)
    config = {"sortie": str(tmp_path / "rendus"), "dossier_publication": str(tmp_path / "bureau"), "auto_depuis": "2026-04-01"}
    dossiers = publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16))
    assert faites == [datetime.date(2026, 4, 16)] and len(dossiers) == 1
    assert sorted(os.listdir(dossiers[0])) == ["avant-de-publier.txt", "description.txt", "recap-2026-04-16.mp4"]
    avant = open(os.path.join(dossiers[0], "avant-de-publier.txt"), encoding="utf-8").read()       # conformité TikTok
    assert "Contenu généré par l'IA" in avant and "NE PAS cocher « Contenu commercial »" in avant and "Publier à la main" in avant
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16)) == []      # déjà publié
    assert publication.auto(dict(config, auto_depuis="2026-04-17"), str(journaux), lambda t: None) == []
    ecrire_journee(str(journaux), datetime.date(2026, 4, 16), positions=())                               # sans trade : rien
    config["dossier_publication"] = str(tmp_path / "bureau2")
    config["dossier_etat"] = str(tmp_path / "etat2")    # 27/11/2026 : un registre neuf (V-07), sinon « déjà publié » suffirait
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16)) == []
    assert faites == [datetime.date(2026, 4, 16)]


def test_semaines_et_mois_finis():
    j = datetime.date
    jours = [j(2026, 11, 23), j(2026, 11, 24), j(2026, 11, 25), j(2026, 11, 26), j(2026, 11, 27), j(2026, 11, 30)]
    # le vendredi 27 au soir : la semaine du 23 est finie (sa séance du vendredi est dans les journaux), novembre ne l'est pas
    assert publication.periodes_finies(jours[:5], j(2026, 11, 27), j(2026, 11, 25)) == [("semaine", j(2026, 11, 23), j(2026, 11, 27))]
    # le lundi 30 au soir : novembre est fini (dernier jour ouvré), la semaine du 30 non
    assert ("mois", j(2026, 11, 1), j(2026, 11, 30)) in publication.periodes_finies(jours, j(2026, 11, 30), j(2026, 11, 25))
    assert ("semaine", j(2026, 11, 30), j(2026, 12, 4)) not in publication.periodes_finies(jours, j(2026, 11, 30), j(2026, 11, 25))
    # une semaine finie avant `depuis` n'est pas refaite
    assert publication.periodes_finies([j(2026, 11, 16)], j(2026, 11, 30), j(2026, 11, 25)) == []


def test_recap_de_la_semaine_egal_a_la_somme_des_jours(tmp_path):
    import recap_periode
    for jour, ps in ((datetime.date(2026, 4, 13), 115.0), (datetime.date(2026, 4, 14), 90.0), (datetime.date(2026, 4, 15), None)):
        ecrire_journee(str(tmp_path), jour, positions=() if ps is None else ((1, "A", 9, 36, 100.0, 15, 50, ps, "Fin de journée"),))
        os.rename(tmp_path / "execution-NDX100.csv", tmp_path / f"e-{jour}.csv")
        for nom in ("seances", "bougies"):
            os.rename(tmp_path / f"{nom}-NDX100.csv", tmp_path / f"{nom[0]}-{jour}.csv")
    for nom, lettre in (("execution", "e"), ("seances", "s"), ("bougies", "b")):
        morceaux = sorted(tmp_path.glob(f"{lettre}-*.csv"))
        with open(tmp_path / f"{nom}-NDX100.csv", "w", encoding="utf-8") as f:
            f.write(morceaux[0].read_text(encoding="utf-8").splitlines(keepends=True)[0])
            for m in morceaux:
                f.writelines(m.read_text(encoding="utf-8").splitlines(keepends=True)[1:])
    p = recap_periode.charger(str(tmp_path), datetime.date(2026, 4, 13), datetime.date(2026, 4, 17), "semaine")
    jours = {d["jour"]: d for d in p["jours"]}
    assert len(p["jours"]) == 3 and len(p["avec"]) == 2 and len(p["gagnants"]) == 1 and len(p["perdants"]) == 1
    assert p["total"] == round(sum(round(d["total"], 2) for d in p["avec"]), 2)
    assert p["meilleur"]["jour"] == datetime.date(2026, 4, 13) and not jours[datetime.date(2026, 4, 15)]["trades"]
    textes = recap_periode.repliques(p)
    assert textes[1].startswith("Lundi : plus") and "Mercredi : pas de trade." in textes[1]
    texte = publication.description_periode(p, {})
    assert texte.startswith("Semaine ") and "Jours de trade : 2 sur 3, dont 1 gagnant" in texte and "D2" not in texte


def _png(chemin, largeur, hauteur):
    """Un en-tête PNG suffit : la vidéo ne lit que la taille de l'image avant de la copier."""
    chemin.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + largeur.to_bytes(4, "big") + hauteur.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00")


def test_preuve_seulement_avec_une_vraie_photo_de_l_historique(tmp_path):
    j = _journee(tmp_path, positions=((1, "A", 9, 36, 100.0, 15, 50, 112.0, "Fin de journée"),))
    assert recap.preuve_du_jour(j, "r") is None and "MetaTrader" not in " ".join(recap.repliques(j, "r"))
    (tmp_path / "captures").mkdir()
    _png(tmp_path / "captures" / "historique-2026-04-16.png", 760, 142)
    j = journee.charger(str(tmp_path), datetime.date(2026, 4, 16))
    preuve = recap.preuve_du_jour(j, "r")
    assert len(preuve["photos"]) == 1 and preuve["notes"][0][0].startswith("Nasdaq 100  +")
    assert recap.repliques(j, "r")[-2] == "Les trades du jour, dans l'historique de MetaTrader."


@pytest.mark.parametrize("hauteurs", [[142], [400], [142, 300]])
def test_photo_et_notes_dans_la_zone_sure(tmp_path, hauteurs):
    """La photo (ou les deux photos d'une période) et les résultats épinglés tiennent dans la zone sûre de TikTok."""
    photos = []
    for i, h in enumerate(hauteurs):
        _png(tmp_path / f"h{i}.png", 760, h)
        photos.append((str(tmp_path / f"h{i}.png"), "Historique MetaTrader"))
    notes = [("Nasdaq 100  −1,50 R", recap.COUL["rouge"]), ("S&P 500  −0,56 R", recap.COUL["rouge"]), ("Total  −2,06 R", recap.COUL["rouge"])]
    style, corps, script, reperes, fin, images = recap.scene_preuve("pv", {"photos": photos, "notes": notes}, None, "mer. 18 Nov. 2026")
    cartes = re.findall(r'class="pv-carte" style="left:(\d+)px; top:(\d+)px; width:(\d+)px"', corps)
    for (gauche, haut, largeur), h in zip(cartes, hauteurs):
        bas = int(haut) + (int(largeur) - 28) * h / 760 + 66
        assert int(gauche) + int(largeur) <= (780 if bas > 840 else 960) and bas <= 1260
    for gauche, haut, taille, texte in PASTILLE.findall(corps):
        bas = int(haut) + int(taille) * 1.34
        assert int(haut) >= 240 and bas <= 1260 and int(gauche) + recap._l(texte, int(taille)) <= 781, texte
    assert len(images) == len(hauteurs)


def test_photo_de_l_historique_pas_reglee():
    import historique
    assert historique.photographier_jour({}, "/nulle/part", datetime.date(2026, 4, 16), 3, lambda t: None) is None


# ───────────────────────── audit du 25/11/2026 (VID-01 à VID-17) ─────────────────────────
def source_de(nom):
    return open(os.path.join(ICI, nom), encoding="utf-8").read()


def test_npx_et_fuseaux_horaires_sous_windows():
    """VID-01 : npx est un npx.cmd sous Windows, introuvable par subprocess sous le nom « npx ». VID-02 : tzdata sous Windows."""
    for nom in ("recap.py", "presentation.py"):
        assert 'HYPERFRAMES = [shutil.which("npx") or "npx", "-y", "hyperframes@' in source_de(nom), nom
    assert "except ZoneInfoNotFoundError:" in source_de("journee.py") and "pip install tzdata" in source_de("journee.py")
    assert "pip install tzdata" in source_de("outil.py") and "tzdata" in source_de("README.md")


def test_pas_de_video_muette_en_mode_automatique(tmp_path, monkeypatch):
    """VID-03 : sans voix (réseau, quota), la séance n'est pas publiée muette ; elle est refaite au lancement suivant."""
    import voix
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_journee(str(journaux), datetime.date(2026, 4, 16))
    demandes = []

    def sans_voix(j, config, sortie, journal=print, rendre=True, exiger_voix=False):
        demandes.append(exiger_voix)
        raise voix.VoixIndisponible("réseau coupé")
    monkeypatch.setattr(publication.recap, "fabriquer", sans_voix)
    monkeypatch.setattr(publication.subprocess, "run", lambda *a, **k: None)
    config = {"sortie": str(tmp_path / "rendus"), "dossier_publication": str(tmp_path / "bureau"), "auto_depuis": "2026-04-01",
              "voix_id": "x"}
    lignes = []
    assert publication.auto(config, str(journaux), lignes.append, datetime.date(2026, 4, 16)) == []
    assert demandes == [True] and any("voix indisponible" in l for l in lignes)
    assert not os.path.exists(tmp_path / "bureau" / "2026-04-16")


def test_photo_de_l_historique_jamais_apres_le_changement_de_jour_du_serveur(tmp_path, monkeypatch):
    """VID-05 : après 17:00 New York, « Aujourd'hui » montre le jour suivant et la ligne du solde. VID-04 : fenêtre trop petite,
    pas de photo tronquée. La photo de toute la fenêtre est effacée."""
    import historique
    utc = lambda *a: datetime.datetime(*a, tzinfo=datetime.timezone.utc)
    jour = datetime.date(2026, 11, 18)
    assert not historique.trop_tard(jour, utc(2026, 11, 18, 21, 20))     # 22:20 à Paris = 16:20 à New York
    assert historique.trop_tard(jour, utc(2026, 11, 18, 22, 50))         # 23:50 à Paris = 17:50 à New York
    assert historique.trop_tard(datetime.date(2026, 3, 18), utc(2026, 3, 18, 21, 20))   # 22:20 à Paris = 17:20 NY (mi-mars)
    cadre = {"historique": {"x": 0, "y": 10, "largeur": 100, "entete": 20, "ligne": 20}}
    lignes = []
    assert historique.photographier_jour(cadre, str(tmp_path), jour, 2, lignes.append, utc(2026, 11, 18, 22, 50)) is None
    assert "trop tard" in lignes[-1]
    temporaires = []

    def fausse_photo(png):
        temporaires.append(os.path.dirname(png))
        with open(png, "wb") as f:                                       # un PNG de 120 x 40 : plus petit que le cadre
            f.write(b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + (120).to_bytes(4, "big") + (40).to_bytes(4, "big"))
    monkeypatch.setattr(historique, "photographier_fenetre", fausse_photo)
    assert historique.photographier_jour(cadre, str(tmp_path), jour, 2, lignes.append, utc(2026, 11, 18, 21, 20)) is None
    assert "plus petite que le cadre" in lignes[-1] and not os.path.exists(temporaires[0])
    pub = source_de("publication.py")
    assert pub.index("try:\n                j[\"historique\"] = historique.photographier_jour(") > 0


def test_semaine_avec_une_seance_illisible_remise_a_plus_tard(tmp_path):
    """VID-07 : une séance illisible disparaissait de la semaine (« Semaine verte » avec un jour perdant en moins)."""
    import recap_periode
    ecrire_journee(str(tmp_path), datetime.date(2026, 4, 14))
    with open(os.path.join(str(tmp_path), "trades-NDX100.csv"), "w", encoding="utf-8") as f:   # un trade que l'exécution ne retrouve pas
        f.write("1776196200;2026-04-14;15:50;NDX100;1;0.10;-1.0000;-999.00;1000.00;Stop;0;USD\r\n")
    with pytest.raises(journee.JourneeIncomplete):
        recap_periode.charger(str(tmp_path), datetime.date(2026, 4, 13), datetime.date(2026, 4, 17), "semaine")


def test_noms_de_dossiers_et_python_de_windows():
    """VID-12 : jamais « testeur » dans un nom de dossier. VID-08 : sous Windows, pas le raccourci python3 du Microsoft Store."""
    outil = source_de("outil.py")
    assert "'-testeur'" not in outil and "'-essai' if args.testeur" in outil
    inst = source_de("installation.py")
    assert inst.index('if os.name == "nt":\n        base = os.path.join(sys.base_prefix, "python.exe")') < inst.index('shutil.which("python3")')


def test_semaine_a_cheval_sur_deux_mois_et_minutes_au_feminin():
    """VID-14 : « du 30 Novembre au 4 Décembre ». VID-17 : « quinze heures quarante et une »."""
    import recap_periode
    p = {"genre": "semaine", "debut": datetime.date(2026, 11, 30), "fin": datetime.date(2026, 12, 4), "jours": [], "avec": [],
         "total": 0.0, "par_marche": {}, "gagnants": [], "perdants": [], "meilleur": None, "pire": None, "source": "reel"}
    assert "Nov" in recap_periode._entete("s", p, "x")[0]
    assert nombres.heure(15, 41) == "quinze heures quarante et une" and nombres.heure(9, 31) == "neuf heures trente et une"
    assert nombres.heure(15, 11) == "quinze heures onze" and nombres.heure(1, 1) == "une heure une"
    assert "du {debut} au {p['fin'].day}" in source_de("publication.py")


# ───────────────────────── la voix, « absolument » (VID-18 à VID-22, 25/11/2026) ─────────────────────────
# Aucun appel réel à ElevenLabs : curl et ffprobe sont remplacés, aucun crédit n'est dépensé.
def config_voix(tmp_path):
    cle = tmp_path / "cle"
    cle.write_text("cle-de-test\n", encoding="utf-8")
    return {"voix_id": "voix-de-test", "cle_elevenlabs": str(cle), "cache_voix": str(tmp_path / "cache")}


def reponse_ok(texte="Bonjour à toi"):
    caracteres = list(texte)
    t = [i * 0.05 for i in range(len(caracteres))]
    return json.dumps({"audio_base64": "SUQzAAAA", "alignment": {"characters": caracteres, "character_start_times_seconds": t,
                                                                 "character_end_times_seconds": [x + 0.05 for x in t]}}).encode()


def test_voix_pannes_passageres_reessayees_et_causes_claires(tmp_path, monkeypatch):
    """VID-19 : pas de réseau puis panne 503 : réessayé dans le même lancement ; une clé refusée ou des crédits épuisés ne sont
    pas réessayés (chaque essai peut coûter) et la cause dit quoi faire."""
    import voix
    monkeypatch.setattr(voix, "ATTENTES", (0, 0))
    monkeypatch.setattr(voix, "duree", lambda chemin: 1.5)
    reponses = [("000", b"", b"curl: (6) Could not resolve host: api.elevenlabs.io"), ("503", b'{"detail":"down"}', b""),
                ("200", reponse_ok(), b"")]
    appels = []
    monkeypatch.setattr(voix, "appeler", lambda url, cle, corps=None: appels.append(url) or reponses[len(appels) - 1])
    rep = voix.replique("Bonjour à toi", config_voix(tmp_path))
    assert len(appels) == 3 and [m["mot"] for m in rep["mots"]] == ["Bonjour", "à", "toi"]
    assert os.path.exists(rep["fichier"]) and not glob.glob(str(tmp_path / "cache" / "*.part"))
    for code, corps, attendu in [("401", b'{"detail":{"status":"quota_exceeded","message":"This request exceeds your quota"}}',
                                  "crédits ElevenLabs épuisés"),
                                 ("401", b'{"detail":{"status":"invalid_api_key","message":"Invalid API key"}}', "clé ElevenLabs refusée"),
                                 ("404", b'{"detail":{"status":"voice_not_found","message":"not found"}}', "vérifier voix_id")]:
        appels.clear()
        monkeypatch.setattr(voix, "appeler", lambda url, cle, corps=None, c=code, r=corps: appels.append(url) or (c, r, b""))
        with pytest.raises(voix.VoixIndisponible, match=attendu):
            voix.replique("Un autre texte " + code + attendu, config_voix(tmp_path))
        assert len(appels) == 1
    assert "Could not resolve host" in voix.cause("000", b"", b"curl: (6) Could not resolve host: x")
    assert "connexion Internet" in voix.cause("000", b"", b"") and "panne chez ElevenLabs" in voix.cause("502", b"<html>")


def test_voix_reponse_illisible_jamais_gardee_en_cache(tmp_path, monkeypatch):
    """VID-20 : une réponse 200 sans son ou sans l'heure des mots est refusée et n'entre pas dans le cache."""
    import voix
    monkeypatch.setattr(voix, "duree", lambda chemin: 1.5)
    for corps in (b"pas du json", json.dumps({"audio_base64": "SUQz", "alignment": None}).encode(), json.dumps({"x": 1}).encode()):
        monkeypatch.setattr(voix, "appeler", lambda url, cle, c=None, r=corps: ("200", r, b""))
        with pytest.raises(voix.VoixIndisponible, match="prochain lancement"):
            voix.replique("Bonjour à toi", config_voix(tmp_path))
        assert not glob.glob(str(tmp_path / "cache" / "*.json")) and not glob.glob(str(tmp_path / "cache" / "*.mp3"))


def test_voix_cle_jamais_dans_la_commande(tmp_path, monkeypatch):
    """La clé passe par un fichier d'en-têtes temporaire, effacé après l'appel ; jamais dans la ligne de commande."""
    import voix
    vus = []

    class Sortie:
        stdout, stderr = b'{"ok":1}\n200', b""

    def faux_curl(commande, **k):
        entetes = next(a[1:] for a in commande if a.startswith("@"))
        vus.append((commande, open(entetes).read(), entetes))
        return Sortie()
    monkeypatch.setattr(voix.subprocess, "run", faux_curl)
    assert voix.appeler("https://api.elevenlabs.io/v1/user/subscription", "cle-secrete") == ("200", b'{"ok":1}', b"")
    commande, contenu, entetes = vus[0]
    assert "cle-secrete" not in " ".join(commande) and contenu == "xi-api-key: cle-secrete\n" and not os.path.exists(entetes)


def test_voix_prise_qui_ne_colle_pas_au_texte(tmp_path, monkeypatch):
    """VID-21 : une prise dont les mots ne collent pas aux scènes est mise de côté et redemandée une fois ; si l'écart revient, la
    prise reste (pas de crédits dépensés à chaque lancement) et le message demande une correction de l'outil."""
    import voix
    base = tmp_path / "abc"

    def fausse_prise(texte, config):
        for ext in (".mp3", ".json"):
            (tmp_path / ("abc" + ext)).write_text("x")
        return {"fichier": str(base) + ".mp3", "duree": 2.0, "mots": [{"mot": "un", "debut": 0, "fin": 0.2}]}
    monkeypatch.setattr(voix, "replique", fausse_prise)
    with pytest.raises(voix.VoixIndisponible, match="nouvelle prise au prochain lancement"):
        voix.recit(["un deux", "trois"], {})
    assert os.path.exists(str(base) + "-ecart.json") and not os.path.exists(str(base) + ".json")
    with pytest.raises(voix.VoixIndisponible, match="deux prises de suite"):
        voix.recit(["un deux", "trois"], {})
    assert os.path.exists(str(base) + ".json")


def test_voix_ffmpeg_jamais_de_fichier_tronque(tmp_path, monkeypatch):
    """VID-21 : un morceau de voix est écrit sous un nom provisoire, contrôlé, puis renommé ; un morceau vide n'est jamais gardé
    (avant, il était repris tel quel aux lancements suivants)."""
    import voix
    monkeypatch.setattr(voix.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(voix, "duree", lambda chemin: 0.0)
    sortie = str(tmp_path / "x-s0.wav")
    with pytest.raises(voix.VoixIndisponible, match="vide"):
        voix._ffmpeg(["-i", "entree.mp3"], sortie)
    assert not os.path.exists(sortie)
    (tmp_path / "y.wav").write_bytes(b"RIFF")
    voix.controle_pistes([{"fichier": str(tmp_path / "y.wav"), "duree": 1.0}])
    with pytest.raises(voix.VoixIndisponible, match="scène 2"):
        voix.controle_pistes([{"fichier": str(tmp_path / "y.wav"), "duree": 1.0}, None])
    with pytest.raises(voix.VoixIndisponible, match="scène 1"):
        voix.controle_pistes([{"fichier": str(tmp_path / "y.wav"), "duree": 0.0}])


def test_jamais_de_video_muette(tmp_path, monkeypatch):
    """VID-18 : la voix est exigée par défaut, en mode automatique même sans voix_id (une nouvelle installation publiait muet), et
    à la main sauf --sans-voix. La notification dit la cause."""
    import inspect
    import outil
    import recap_periode
    import voix
    assert inspect.signature(recap.fabriquer).parameters["exiger_voix"].default is True
    assert inspect.signature(recap_periode.fabriquer).parameters["exiger_voix"].default is True
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_journee(str(journaux), datetime.date(2026, 4, 16))
    demandes, notes = [], []

    def sans_voix(j, config, sortie, journal=print, rendre=True, exiger_voix=False):
        demandes.append(exiger_voix)
        raise voix.VoixIndisponible(voix.cause("401", b'{"detail":{"status":"quota_exceeded"}}'))
    monkeypatch.setattr(publication.recap, "fabriquer", sans_voix)
    monkeypatch.setattr(publication, "prevenir", lambda titre, texte: notes.append(texte))
    # 27/11/2026 : auto_depuis au jour du journal (avant : le 01/04) ; sinon V-01 prévient d'abord des séances d'avril absentes
    config = {"sortie": str(tmp_path / "rendus"), "dossier_publication": str(tmp_path / "bureau"), "auto_depuis": "2026-04-16"}
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16)) == []
    assert demandes == [True] and "crédits ElevenLabs épuisés" in notes[0]
    assert not os.path.exists(tmp_path / "bureau" / "2026-04-16")
    monkeypatch.setattr(recap, "fabriquer", sans_voix)
    fichier = tmp_path / "config.json"
    fichier.write_text(json.dumps({"sortie": str(tmp_path / "rendus"), "dossier_journaux": str(journaux), "police": "x"}))
    assert outil.main(["recap", "--jour", "2026-04-16", "--config", str(fichier)]) == 4 and demandes[-1] is True
    exiges = []                 # avec --sans-voix, la voix n'est plus exigée (un essai à la main)
    monkeypatch.setattr(recap, "fabriquer", lambda *a, exiger_voix=True, **k: exiges.append(exiger_voix) or "video.mp4")
    assert outil.main(["recap", "--jour", "2026-04-16", "--config", str(fichier), "--sans-voix"]) == 0
    assert exiges == [False]


def test_verifier_controle_la_voix_sans_depenser(tmp_path, monkeypatch):
    """VID-22 : `verifier` lit la voix et les crédits restants (deux lectures gratuites, jamais de synthèse)."""
    import voix
    urls = []

    def faux(url, cle, corps=None):
        urls.append((url, corps))
        if "subscription" in url:
            return "200", json.dumps({"character_count": 9000, "character_limit": 30000}).encode(), b""
        return "200", b"{}", b""
    monkeypatch.setattr(voix, "appeler", faux)
    lignes = voix.controle_compte(config_voix(tmp_path))
    assert all(bon for bon, _ in lignes) and "21000 caractères restants" in lignes[1][1]
    assert all(corps is None and "text-to-speech" not in url for url, corps in urls)
    monkeypatch.setattr(voix, "appeler", lambda url, cle, corps=None: ("401", b'{"detail":{"status":"invalid_api_key"}}', b""))
    assert not voix.controle_compte(config_voix(tmp_path))[0][0]


# ───────────────────────── conformité TikTok (25/11/2026) ─────────────────────────
def test_conformite_tiktok_telegram_seulement_dans_la_description(tmp_path):
    """La vidéo garde les gens sur TikTok : ni la voix ni les écrans ne parlent du Telegram (seulement la description) ; plus
    d'annonce de copy trading dans la présentation."""
    import recap_periode
    j = _journee(tmp_path, positions=((1, "A", 9, 36, 100, 15, 50, 110, "Fin de journée"),))
    textes = recap.repliques(j, recap.unite_du_jour(j))
    assert "telegram" not in " ".join(textes).lower() and textes[-1].endswith("Abonne-toi pour voir la séance de demain !")
    for nom in ("recap.py", "recap_periode.py"):
        code = source_de(nom)
        assert "Rejoins le Telegram" not in code and "lien en bio" not in code and "Chaque séance est sur le Telegram" not in code
    assert "Abonne-toi pour la suite !" in source_de("recap_periode.py")
    assert "sur le Telegram (gratuit, rien à vendre) : lien en bio." in publication.description(j, {})
    modeles = ""
    for chemin in glob.glob(os.path.join(ICI, "modeles", "**", "*.*"), recursive=True):
        modeles += open(chemin, encoding="utf-8", errors="replace").read()
    for interdit in ("Copy trading", "copy trading", "copier mes trades", "Abonné 1", "Telegram", "lien en bio"):
        assert interdit not in modeles, interdit
    assert os.path.exists(os.path.join(ICI, "modeles", "presentation", "compositions", "bilan.html"))
    assert [n for n, _, _ in presentation.REPLIQUES][-3:] == ["5-bilan", "5b-bilan", "6-fin"]
    assert "jeu" not in " ".join(m for l in recap.MOTS_DU_JOUR.values() for m in l).split()
    assert not any(" jeu" in m for l in recap_periode.MOTS_PERIODE.values() for m in l)


def test_presentation_minutage_d_accord():
    """La durée de la présentation : la même dans presentation.py, index.html et bruitages.json ; les scènes se suivent sans trou ;
    chaque réplique commence pendant sa scène."""
    index = open(os.path.join(ICI, "modeles", "presentation", "index.html"), encoding="utf-8").read()
    scenes = [(i, float(d), float(t)) for i, d, t in re.findall(r'<div id="(\w+)" data-composition-id="\w+" data-composition-src="[^"]+" '
                                                                 r'data-start="([\d.]+)" data-duration="([\d.]+)"', index)]
    assert [s[0] for s in scenes] == ["provoc", "preuve", "robot", "seance", "bilan", "fin"]
    fin = scenes[-1][1] + scenes[-1][2]
    assert abs(fin - presentation.DUREE) < 0.01 and f'data-duration="{presentation.DUREE:g}"' in index
    bruitages = json.load(open(os.path.join(ICI, "modeles", "presentation", "bruitages.json"), encoding="utf-8"))
    assert bruitages["duree"] == presentation.DUREE and all(b["t"] < presentation.DUREE for b in bruitages["bruitages"])
    for (a, da, ta), (b, db, tb) in zip(scenes[3:], scenes[4:]):
        assert abs(da + ta - db) < 0.01, (a, b)
    debut = dict((n, t) for n, t, _ in presentation.REPLIQUES)
    assert scenes[4][1] <= debut["5-bilan"] < debut["5b-bilan"] < scenes[5][1] <= debut["6-fin"] < presentation.DUREE


def test_certificat_floute_quand_des_masques_sont_regles(tmp_path, monkeypatch):
    """Conformité TikTok : avec `masques_certificat`, le certificat passe par un flou fort (ffmpeg) avant d'entrer dans la vidéo et
    la couverture ; sans masque, il est copié tel quel."""
    source = tmp_path / "certificat.png"
    _png(source, 600, 450)           # 27/11/2026 : un en-tête PNG (V-25 lit la taille de l'image pour contrôler les masques)
    appels = []
    monkeypatch.setattr(presentation.subprocess, "run", lambda commande, **k: appels.append(commande))
    cible = tmp_path / "copie.png"
    # V-25 (27/11/2026, règle changée) : sans masque, le certificat n'est plus copié net dans la vidéo (la prop firm sortirait nommée) ;
    # seul l'essai (`outil.py certificat --essai`, pour régler les masques) l'écrit tel quel
    with pytest.raises(ValueError, match="masques_certificat"):
        presentation.copier_certificat({"certificat": str(source)}, str(cible))
    presentation.copier_certificat({"certificat": str(source)}, str(cible), essai=True)
    assert appels == [] and cible.read_bytes() == source.read_bytes()
    presentation.copier_certificat({"certificat": str(source), "masques_certificat": [[62, 36, 206, 60], [325, 258, 145, 150]]},
                                   str(tmp_path / "floute.png"))
    filtre = appels[0][appels[0].index("-filter_complex") + 1]
    assert appels[0][0] == "ffmpeg" and "crop=206:60:62:36,boxblur=15:4" in filtre and "overlay=325:258" in filtre
    assert source_de("presentation.py").count("copier_certificat(profil, os.path.join(") == 2      # fabriquer et couverture
    exemple = json.load(open(os.path.join(ICI, "config.exemple.json"), encoding="utf-8"))["presentation"]
    assert "<prop firm>" not in json.dumps(exemple) and exemple["libelle_montant"] == "de récompenses en prop firm"


# ───────────────────────── audit du 26/11/2026 : coupures du son et défauts d'image (VID-23 à VID-30) ─────────────────────────
def _ffmpeg(*args):
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _phrases(tmp_path):
    """Une fausse voix : une phrase de 5 mots (0,25 s, 0,2 s entre eux), 1,5 s de silence, une phrase de 4 mots."""
    voix = str(tmp_path / "voix.wav")
    mots = [0.5 + 0.45 * i for i in range(5)] + [4.0 + 0.45 * i for i in range(4)]
    expr = "+".join(f"between(t,{a:.2f},{a + 0.25:.2f})" for a in mots)
    _ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=6:r=48000", "-af", f"volume='0.5*({expr})':eval=frame", voix)
    return voix


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg absent")
def test_bruitages_et_musique_jamais_haches_par_la_voix(tmp_path):
    """VID-23 : plus de compresseur commandé par la voix (il hachait les bruitages syllabe par syllabe) ; une baisse fixe pendant
    chaque phrase, avec des rampes. VID-30 : le contrôle mesure le hachage et le signale."""
    import controle
    assert "sidechaincompress" not in source_de("mixage.py")
    voix = _phrases(tmp_path)
    blocs = mixage.blocs_parole(voix)
    # les mots d'une phrase ne font qu'un bloc ; un silence de moins de 0,6 s (ici au début et à la fin du fichier) aussi
    assert len(blocs) == 2 and blocs[0][1] == pytest.approx(2.55, abs=0.05) and blocs[1][0] == pytest.approx(4.0, abs=0.05)
    sfx, sous = str(tmp_path / "bruitages.wav"), str(tmp_path / "bruitages-sous-voix.wav")
    _ffmpeg("-f", "lavfi", "-i", "sine=f=1000:d=6:r=48000", "-af", "volume=0.3", sfx)
    _ffmpeg("-i", sfx, "-af", f"asetnsamples=n=240,volume='{mixage.enveloppe(blocs, mixage.BAISSE_BRUITAGES)}':eval=frame", sous)
    a, b = controle.niveaux(sfx), controle.niveaux(sous)
    assert controle.hachage(sfx, sous) < 3.0
    assert b[150] - a[150] == pytest.approx(-9.0, abs=0.3) and b[160] - a[160] == pytest.approx(-9.0, abs=0.3)   # dans la phrase
    assert b[330] - a[330] == pytest.approx(0.0, abs=0.3)                                                       # entre les phrases
    hache = str(tmp_path / "hache.wav")               # l'ancien défaut : la baisse suit chaque syllabe
    _ffmpeg("-i", sfx, "-af", "volume='if(lt(mod(t,0.45),0.25),0.1,1)':eval=frame", hache)
    assert controle.hachage(sfx, hache) > 10


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg absent")
def test_controle_de_la_video_finie(tmp_path):
    """VID-30 : la voix coupée net et les bruitages hachés sont signalés dans controle.txt et le journal, sans bloquer."""
    import controle
    voix = _phrases(tmp_path)
    assert controle.bords_durs(voix)                  # des mots qui commencent et finissent net : signalés
    doux = str(tmp_path / "doux.wav")
    _ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=3:r=48000", "-af", "volume=0.5,afade=t=in:d=0.2,afade=t=out:st=2.6:d=0.4", doux)
    assert controle.bords_durs(doux) == []
    video = str(tmp_path / "v.mp4")
    _ffmpeg("-f", "lavfi", "-i", "color=c=white:s=108x192:d=3", "-i", doux, "-shortest", "-c:a", "aac", video)
    os.replace(doux, str(tmp_path / "voix.wav"))
    lignes = []
    remarques = controle.verifier(video, str(tmp_path), lignes.append)
    assert open(tmp_path / "controle.txt", encoding="utf-8").read() and all(r in " ".join(lignes) for r in remarques)
    assert "controle.verifier(finale, travail, journal)" in source_de("recap.py") + source_de("recap_periode.py") + source_de("presentation.py")


def _scene(tmp_path, positions):
    recap.POLICE = os.path.expanduser(recap.POLICE)
    j = _journee(tmp_path, positions=positions)
    return j, recap.scene_marche(j, j["marches"][0], 0, None, "r", 9.0)[1]


def test_rien_ne_deborde_du_graphique(tmp_path):
    """VID-25 : la découpe s'arrête au-dessus de l'axe des heures (caméra zoomée, les bougies passaient dessus). VID-26 : les ronds
    des sorties de fin de séance restent entiers dans le cadre (ils étaient coupés à moitié sur le bord droit)."""
    j, corps = _scene(tmp_path, ((-1, "A", 9, 36, 100, 15, 59, 104, "Fin de journée"), (-1, "D1", 9, 41, 99, 15, 59, 97, "Fin de journée")))
    clip = re.search(r'<clipPath id="m0-clip"><rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"', corps)
    axe = float(re.search(r'<line id="m0-axe"[^>]* y1="([\d.]+)"', corps).group(1))
    bas_clip, droite_clip = float(clip.group(2)) + float(clip.group(4)), float(clip.group(1)) + float(clip.group(3))
    assert bas_clip < axe
    ronds = re.findall(r'<circle cx="([\d.]+)" cy="[\d.]+" r="(\d+)" fill="#[0-9a-f]+" stroke=', corps.split('id="m0-ronds"')[1])
    assert ronds and all(float(cx) + float(r) <= droite_clip - 2 for cx, r in ronds)


def test_groupes_meles_et_stop_suivant(tmp_path):
    """VID-27 : un groupe de sorties qui gagne et perd à la fois n'est ni vert ni rouge (« 2 stops » en rouge à côté d'un
    « Stop +51 pts » vert), et la voix dit si l'autre stop gagne ou perd."""
    j, corps = _scene(tmp_path, ((-1, "A", 9, 36, 100, 11, 36, 98, "Stop"), (-1, "D1", 9, 41, 96, 11, 40, 99, "Stop")))
    assert f'background:{recap.COUL["encre2"]}; color:{recap.COUL["blanc"]}">2 stops<' in corps
    f = recap.faits(j["marches"][0])
    assert recap.phrase_stops(f).endswith("Un autre stop suit, en perte.")
    assert recap.couleur_groupe(f["stops"]) == recap.COUL["encre2"]
    assert recap.couleur_groupe(f["stops"][:1]) == recap.COUL["vert"] and recap.couleur_groupe(f["stops"][1:]) == recap.COUL["rouge"]


def test_meme_creux_dit_une_seule_fois_et_meme_scenario_avec_les_memes_resultats():
    """VID-28 : le plus loin des positions de fin de séance n'est pas redit s'il tombe sur la même bougie que celui du stop
    (« +106 » puis « +108 » pour le même creux). VID-29 : « Même scénario » seulement si les sorties ont aussi les mêmes résultats."""
    h = lambda mm: datetime.datetime(2026, 11, 17, 15, mm, tzinfo=UTC)
    bougies = [{"heure": h(5 * i), "h": 101, "l": 80 if i == 4 else 99, "o": 100, "c": 99.5} for i in range(10)]
    stop = {"sens": -1, "entree": h(1), "sortie": h(30), "mfe": 106, "points": 51, "r": 0.5, "raison": "Stop"}
    fin = {"sens": -1, "entree": h(2), "sortie": h(48), "mfe": 108, "points": 40, "r": 0.4, "raison": "Fin de journée"}
    m = {"bougies": bougies}
    f = {"stops": [stop], "fins": [fin], "autres": [], "n": 2, "sens": {-1}, "cote": "bas"}
    assert recap.mfe_deja_dit(m, f)
    assert recap.phrase_fins(f, True) == "L'autre position tient jusqu'à la fin de séance."
    assert "cent huit" in recap.phrase_fins(f)
    perte = dict(fin, r=-0.4, points=-40)
    g = dict(f, fins=[perte])
    assert recap.meme_scenario(f, dict(f)) and not recap.meme_scenario(f, g)


def test_vert_et_rouge_seulement_pour_le_resultat():
    """VID-31 (choix de l'utilisateur) : le chemin du prix (« Jusqu'à … pts », trait, point) et l'épingle des photos sont bleus ; le
    vert et le rouge ne disent que gagné ou perdu."""
    code = source_de("recap.py")
    assert recap.COUL_CHEMIN == recap.COUL["bleu"]
    assert code.count('f"Jusqu\'à {pts_ecran(') == 2 and 'COUL["vert"], COUL["blanc"],\n                                      _instant_apres' not in code
    assert all("COUL_CHEMIN" in l for l in code.splitlines() if '["exc", f"Jusqu\'à' in l)
    epingle = code[code.index(".{ident}-epingle {{"):code.index(".{ident}-epingle {{") + 400]
    assert "COUL['bleu']" in epingle and "rouge" not in epingle


def test_seance_illisible_et_recap_bloque_previennent(tmp_path, monkeypatch):
    """VID-32 : une séance illisible, et la semaine qu'elle bloque, envoient une notification (avant : le journal seulement)."""
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    # 27/11/2026 : une séance sans trade le lundi 13 avant la séance illisible du 14 (avant : le 14 seul) ; V-12 ne fait plus de récap
    # d'une semaine commencée avant le premier journal de l'EA
    ecrire_jours(str(journaux), [(datetime.date(2026, 4, 13), {"positions": ()}), (datetime.date(2026, 4, 14), {})])
    with open(journaux / "trades-NDX100.csv", "w", encoding="utf-8") as f:     # un trade que l'exécution ne retrouve pas
        f.write("1776196200;2026-04-14;15:50;NDX100;1;0.10;-1.0000;-999.00;1000.00;Stop;0;USD\r\n")
    notes = []
    monkeypatch.setattr(publication, "prevenir", lambda titre, texte: notes.append(titre))
    monkeypatch.setattr(publication.recap, "fabriquer", lambda *a, **k: pytest.fail("pas de vidéo pour une séance illisible"))
    config = {"sortie": str(tmp_path / "rendus"), "dossier_publication": str(tmp_path / "bureau"), "auto_depuis": "2026-04-13"}
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 20)) == []
    assert "Étrave : séance illisible" in notes and "Étrave : récap bloqué" in notes


# ───────────────────────── audit du 27/11/2026 (V-01 à V-28) ─────────────────────────
# Les nouveaux modules (calendrier, etat…) sont importés dans les tests : le fichier reste lisible par le code d'avant le correctif,
# pour prouver que chaque test échouait.
D = datetime.date
GAIN = ((1, "A", 9, 36, 100.0, 15, 50, 112.0, "Fin de journée"),)
PERTE = ((1, "A", 9, 36, 100.0, 10, 5, 82.0, "Stop"),)
SEMAINE = [(D(2026, 11, k), {}) for k in (2, 3, 4, 5, 6)]


def ecrire_jours(dossier, jours, symbole="NDX100"):
    """Plusieurs séances dans les mêmes journaux, comme l'EA les écrit jour après jour : [(jour, options d'ecrire_journee)]."""
    import shutil
    import tempfile
    tous = {b: [] for b in ENTETES}
    for jour, options in jours:
        t = tempfile.mkdtemp()
        ecrire_journee(t, jour, **options)
        for b in tous:
            tous[b] += [l.replace("NDX100", symbole) for l in open(os.path.join(t, f"{b}-NDX100.csv"), encoding="utf-8").read().splitlines()[1:]]
        shutil.rmtree(t)
    for b, lignes in tous.items():
        with open(os.path.join(dossier, f"{b}-{symbole}.csv"), "w", encoding="utf-8") as f:
            f.write(ENTETES[b] + "\r\n" + "".join(l + "\r\n" for l in lignes))


def faux_rendus(monkeypatch):
    """La fabrication remplacée par un fichier vide : rend la liste de ce qui a été fabriqué (jours, (genre, début))."""
    import recap_periode
    faites = []

    def video(j, config, sortie, journal=print, rendre=True, exiger_voix=True, **k):
        faites.append(j["jour"])
        chemin = os.path.join(sortie, "v.mp4")
        open(chemin, "wb").write(b"\0")
        return chemin

    def periode(p, config, sortie, journal=print, rendre=True, exiger_voix=True, **k):
        faites.append((p["genre"], p["debut"]))
        chemin = os.path.join(sortie, "p.mp4")
        open(chemin, "wb").write(b"\0")
        return chemin
    monkeypatch.setattr(publication.recap, "fabriquer", video)
    monkeypatch.setattr(recap_periode, "fabriquer", periode)
    monkeypatch.setattr(publication.subprocess, "run", lambda *a, **k: None)
    return faites


def config_auto(tmp_path, **kw):
    c = {"sortie": str(tmp_path / "rendus"), "dossier_publication": str(tmp_path / "bureau"), "dossier_etat": str(tmp_path / "etat"),
         "auto_depuis": "2026-11-02"}
    c.update(kw)
    return c


def test_calendrier_des_seances_comme_l_ea():
    """V-01, V-03, V-10 : les jours de séance attendus suivent le calendrier de l'EA (ShortDay : fériés et demi-séances, y compris
    ses choix « par prudence »). calendrier.py est une copie de la règle : ce test vérifie l'accord avec le code de l'EA."""
    import calendrier
    feries = [D(2026, 1, 1), D(2026, 1, 19), D(2026, 2, 16), D(2026, 4, 3), D(2026, 5, 25), D(2026, 6, 19), D(2026, 7, 3), D(2026, 9, 7),
              D(2026, 11, 26), D(2026, 12, 25), D(2025, 7, 4), D(2027, 6, 18), D(2027, 7, 5), D(2027, 12, 31)]
    demi = [D(2026, 7, 2), D(2026, 11, 27), D(2026, 12, 24), D(2025, 7, 3), D(2025, 11, 28), D(2025, 12, 24)]
    normaux = [D(2026, 11, 25), D(2026, 3, 16), D(2026, 7, 6), D(2025, 1, 9), D(2027, 12, 30)]   # le 09/01/2025 (deuil) n'y est pas
    assert all(calendrier.ferie_ou_demi(d) for d in feries + demi)
    assert not any(calendrier.ferie_ou_demi(d) for d in normaux)
    assert calendrier.jours_de_seance(D(2026, 11, 23), D(2026, 11, 29)) == [D(2026, 11, 23), D(2026, 11, 24), D(2026, 11, 25)]
    ea = open(os.path.join(ICI, "..", "robot", "Strategy-V11.mq5"), encoding="utf-8").read()
    corps = ea[ea.index("bool ShortDay(datetime ny)"):ea.index("int FlatMin(datetime ny)")]
    for regle in ("Observed(MakeDate(y, 1, 1)) || d == Observed(MakeDate(y + 1, 1, 1))", "NthDow(y, 1, 1, 3)", "NthDow(y, 2, 1, 3)",
                  "GoodFriday(y)", "LastDow(y, 5, 1)", "Observed(MakeDate(y, 6, 19))", "Observed(j4)", "NthDow(y, 9, 1, 1)",
                  "NthDow(y, 11, 4, 4)", "Observed(MakeDate(y, 12, 25))", "d == tg + 86400 || d == MakeDate(y, 12, 24)",
                  "(s4.day_of_week >= 2 && s4.day_of_week <= 5) ? j4 - 86400 : s4.day_of_week == 6 ? j4 - 2 * 86400"):
        assert regle in corps, regle
    assert "bool shortD = InpSkipShort && ShortDay(ny1);" in ea           # l'EA ne trade pas ces jours-là
    utc = datetime.timezone.utc
    assert not calendrier.seance_due(D(2026, 11, 25), datetime.datetime(2026, 11, 25, 20, 50, tzinfo=utc))   # 15:50 à New York
    assert calendrier.seance_due(D(2026, 11, 25), datetime.datetime(2026, 11, 25, 21, 20, tzinfo=utc))       # 22:20 à Paris


def test_v01_jour_de_seance_absent_des_journaux_previent(tmp_path, monkeypatch, garde_fous):
    """V-01 : MetaTrader fermé, EA arrêté ou « JOUR MANQUÉ » (aucune ligne ce jour-là) : « Rien de nouveau à publier », sans
    notification. Chaque jour de séance de New York (calendrier de l'EA) est comparé aux journaux, et l'absence prévient."""
    faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {}), (D(2026, 11, 5), {}), (D(2026, 11, 6), {})])
    publication.auto(config_auto(tmp_path), str(journaux), lambda t: None, D(2026, 11, 6))
    absentes = [texte for titre, texte in garde_fous if "absente" in titre]
    assert absentes and "mer. 4 Nov." in absentes[0] and "lun. 2" not in absentes[0]
    garde_fous.clear()                 # aucun journal du tout : l'état réel de ce Mac du 25 au 26/11
    vide = tmp_path / "vide"
    vide.mkdir()
    publication.auto(config_auto(tmp_path, auto_depuis="2026-11-24", dossier_etat=str(tmp_path / "etat2")), str(vide), lambda t: None,
                     D(2026, 11, 25))
    assert any("absente" in t and "mar. 24 Nov." in x and "mer. 25 Nov." in x for t, x in garde_fous)
    garde_fous.clear()                 # le dossier des journaux n'existe pas
    publication.auto(config_auto(tmp_path, dossier_etat=str(tmp_path / "etat3")), str(tmp_path / "nulle-part"), lambda t: None,
                     D(2026, 11, 6))
    assert any("journaux" in t for t, _ in garde_fous)


def test_v02_ligne_abimee_ne_bloque_pas_les_autres_jours(tmp_path, monkeypatch, garde_fous):
    """V-02 : une ligne de bougies au bon nombre de colonnes mais à l'heure abîmée (« 15h50 ») levait ValueError hors du mode
    automatique : plus aucune vidéo, même pour les jours sains, sans notification. Une panne imprévue de `auto` prévient aussi."""
    import outil
    faites = faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {})])
    f = journaux / "bougies-NDX100.csv"
    f.write_text(f.read_text(encoding="utf-8").replace("2026-11-02;NDX100;15:50;", "2026-11-02;NDX100;15h50;", 1), encoding="utf-8")
    e = journaux / "execution-NDX100.csv"         # et une milliseconde absurde le même jour
    with pytest.raises(journee.JourneeIncomplete, match="abîmé"):
        journee.charger(str(journaux), D(2026, 11, 2))
    publication.auto(config_auto(tmp_path), str(journaux), lambda t: None, D(2026, 11, 3))
    assert faites == [D(2026, 11, 3)]
    assert any("illisible" in t and "lun. 2 Nov." in x for t, x in garde_fous)
    lignes = e.read_text(encoding="utf-8").splitlines()
    champs = lignes[2].split(";")
    champs[8] = "9" * 30
    e.write_text("\r\n".join(lignes[:2] + [";".join(champs)]) + "\r\n", encoding="utf-8")
    with pytest.raises(journee.JourneeIncomplete):
        journee.charger(str(journaux), D(2026, 11, 3))
    garde_fous.clear()
    monkeypatch.setattr(publication, "auto", lambda *a, **k: 1 / 0)
    fichier = tmp_path / "config.json"
    fichier.write_text(json.dumps(dict(config_auto(tmp_path), dossier_journaux=str(journaux), police="x")))
    assert outil.main(["auto", "--config", str(fichier)]) == 5
    assert any("échec" in t for t, _ in garde_fous)


def test_v03_perte_sans_ligne_fin_bloque_la_semaine(tmp_path, monkeypatch, garde_fous):
    """V-03 : la perte du mercredi est dans le journal d'exécution, mais la ligne « fin » manque (MetaTrader arrêté avant 15:52) :
    « Semaine verte, 4 sur 4, dont 4 gagnants ». La période attend, avec une cause claire. Avec deux marchés, la journée n'est pas
    racontée sans celui qui n'a pas fini."""
    import recap_periode
    faites = faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {}), (D(2026, 11, 4), {"positions": PERTE, "fin": False}),
                                 (D(2026, 11, 5), {}), (D(2026, 11, 6), {})])
    with pytest.raises(journee.JourneeIncomplete, match="2026-11-04"):
        recap_periode.charger(str(journaux), D(2026, 11, 2), D(2026, 11, 6), "semaine")
    publication.auto(config_auto(tmp_path), str(journaux), lambda t: None, D(2026, 11, 6))
    assert ("semaine", D(2026, 11, 2)) not in faites and not (tmp_path / "bureau" / "Semaine du 2026-11-02").exists()
    assert any("bloqué" in t and "4 Nov." in x for t, x in garde_fous)
    deux = tmp_path / "deux"
    deux.mkdir()
    ecrire_jours(str(deux), [(D(2026, 11, 4), {"positions": PERTE, "fin": False})])
    ecrire_jours(str(deux), [(D(2026, 11, 4), {})], symbole="SPX500")
    with pytest.raises(journee.JourneeIncomplete, match="NDX100"):
        journee.charger(str(deux), D(2026, 11, 4))


def test_v05_dossier_de_publication_interdit_previent(tmp_path, garde_fous):
    """V-05 : sans droit d'écrire dans le dossier de publication (autorisation du Bureau refusée en arrière-plan, nouveau Python),
    `auto` rendait 3 avec une ligne dans le journal, sans notification."""
    import outil
    interdit = tmp_path / "interdit"
    interdit.mkdir()
    interdit.chmod(0o500)
    try:
        fichier = tmp_path / "config.json"
        fichier.write_text(json.dumps(dict(config_auto(tmp_path), dossier_publication=str(interdit / "Étrave TikTok"),
                                           dossier_journaux=str(tmp_path), police="x")))
        assert outil.main(["auto", "--config", str(fichier)]) == 3
        assert any("accès" in t for t, _ in garde_fous)
    finally:
        interdit.chmod(0o700)


def test_v07_dossier_range_apres_publication_pas_refait(tmp_path, monkeypatch, garde_fous):
    """V-07 : ranger le dossier « Étrave TikTok » après publication refaisait toutes les vidéos depuis auto_depuis, avec une
    notification chacune. Le registre des publications est hors du Bureau ; un registre neuf (mise à jour) repart des dossiers."""
    import shutil
    faites = faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), SEMAINE)
    c = config_auto(tmp_path)
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 6))
    assert len(faites) == 6                        # cinq jours et la semaine
    shutil.rmtree(c["dossier_publication"])
    faites.clear()
    garde_fous.clear()
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 9))
    assert faites == [] and not any(t == "Étrave" for t, _ in garde_fous)
    # mise à jour depuis l'outil d'avant (pas encore de registre) : les dossiers déjà sur le Bureau ne sont pas refaits
    c2 = config_auto(tmp_path, dossier_etat=str(tmp_path / "etat2"), dossier_publication=str(tmp_path / "bureau2"))
    publication.auto(c2, str(journaux), lambda t: None, D(2026, 11, 6))
    shutil.rmtree(c2["dossier_etat"])
    faites.clear()
    publication.auto(c2, str(journaux), lambda t: None, D(2026, 11, 6))
    assert faites == []


def test_v09_seance_illisible_previent_une_fois_par_jour_et_s_acquitte(tmp_path, monkeypatch, garde_fous):
    """V-09 : une séance illisible prévenait à chaque lancement, sans fin, et bloquait la semaine et le mois pour toujours. Une
    notification par jour au plus ; `outil.py accepter` la prend telle quelle, `outil.py ignorer` la laisse de côté."""
    import outil
    faites = faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), SEMAINE)
    with open(journaux / "trades-NDX100.csv", "w", encoding="utf-8") as f:     # un trade que l'exécution ne retrouve pas
        f.write("1793900000;2026-11-04;15:50;NDX100;1;0.10;-1.0000;-999.00;1000.00;Stop;0;USD\r\n")
    c = config_auto(tmp_path)
    for _ in range(2):                              # 22:20 puis 23:50 : une seule notification ce soir-là
        publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 6))
    assert sum(1 for t, _ in garde_fous if "illisible" in t) == 1 and ("semaine", D(2026, 11, 2)) not in faites
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 9))
    assert sum(1 for t, _ in garde_fous if "illisible" in t) == 2               # le lendemain, un rappel
    fichier = tmp_path / "config.json"
    fichier.write_text(json.dumps(dict(c, dossier_journaux=str(journaux), police="x")))
    assert outil.main(["accepter", "--jour", "2026-11-04", "--config", str(fichier)]) == 0
    garde_fous.clear()
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 9))
    assert D(2026, 11, 4) in faites and ("semaine", D(2026, 11, 2)) in faites
    assert not any("illisible" in t for t, _ in garde_fous)
    # « ignorer » : un jour sans aucune séance (le robot ne tournait pas) ne bloque plus la semaine
    autre = tmp_path / "autre"
    autre.mkdir()
    ecrire_jours(str(autre), [(D(2026, 11, k), {}) for k in (2, 3, 5, 6)])
    c2 = config_auto(tmp_path, dossier_etat=str(tmp_path / "etat2"), dossier_publication=str(tmp_path / "bureau2"))
    faites.clear()
    publication.auto(c2, str(autre), lambda t: None, D(2026, 11, 6))
    assert ("semaine", D(2026, 11, 2)) not in faites
    fichier.write_text(json.dumps(dict(c2, dossier_journaux=str(autre), police="x")))
    import etat
    with etat.verrou(c2):              # pendant un passage, la décision n'est pas perdue en silence : elle est refusée
        assert outil.main(["ignorer", "--jour", "2026-11-04", "--config", str(fichier)]) == 6
    assert etat.Registre(c2, str(autre)).decision(D(2026, 11, 4)) is None
    assert outil.main(["ignorer", "--jour", "2026-11-04", "--config", str(fichier)]) == 0
    publication.auto(c2, str(autre), lambda t: None, D(2026, 11, 6))
    assert faites[-1] == ("semaine", D(2026, 11, 2))


def test_v12_pas_de_recap_d_une_periode_commencee_avant_le_premier_journal(tmp_path, monkeypatch):
    """V-12 : la démo lancée le lundi 30/11 publiait le soir même « Récap du mois de novembre. Mois rouge… Une séance »."""
    faites = faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 30), {"positions": PERTE})])
    publication.auto(config_auto(tmp_path, auto_depuis="2026-11-30"), str(journaux), lambda t: None, D(2026, 11, 30))
    assert faites == [D(2026, 11, 30)]


def test_v20_deux_passages_en_meme_temps(tmp_path, monkeypatch):
    """V-20 : `auto` ou `recap` lancé à la main pendant le passage de launchd (ou d'Étrave) fabriquait deux fois le même jour (voix
    demandée deux fois, même nom provisoire). Un verrou : le second passage s'arrête sans rien faire."""
    import threading
    import time
    import outil
    faux_rendus(monkeypatch)
    faites = []

    def lente(j, config, sortie, journal=print, rendre=True, exiger_voix=True, **k):
        faites.append(j["jour"])
        time.sleep(0.5)
        chemin = os.path.join(sortie, "v.mp4")
        open(chemin, "wb").write(b"\0")
        return chemin
    monkeypatch.setattr(publication.recap, "fabriquer", lente)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {})])
    c = config_auto(tmp_path)
    passages = [threading.Thread(target=publication.auto, args=(c, str(journaux), lambda t: None, D(2026, 11, 2))) for _ in range(2)]
    for p in passages:
        p.start()
    for p in passages:
        p.join()
    assert faites == [D(2026, 11, 2)]
    import etat
    lignes = []
    with etat.verrou(c):
        assert publication.auto(c, str(journaux), lignes.append, D(2026, 11, 3)) == [] and "en cours" in lignes[-1]
        fichier = tmp_path / "config.json"
        fichier.write_text(json.dumps(dict(c, dossier_journaux=str(journaux), police="x")))
        assert outil.main(["recap", "--jour", "2026-11-02", "--config", str(fichier)]) == 6


def test_v22_periode_deja_publiee_pas_rechargee(tmp_path, monkeypatch):
    """V-22 : chaque lancement rechargeait toutes les semaines et tous les mois depuis auto_depuis avant de tester s'ils étaient
    publiés (environ 70 s par lancement après un an). Le registre est lu d'abord."""
    import recap_periode
    faux_rendus(monkeypatch)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), SEMAINE)
    c = config_auto(tmp_path)
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 6))
    monkeypatch.setattr(recap_periode, "charger", lambda *a, **k: pytest.fail("période déjà publiée rechargée"))
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 6))


def test_v06_chaque_commande_a_un_delai(tmp_path, monkeypatch, garde_fous):
    """V-06 : aucun `timeout=` sur le rendu HyperFrames ni sur ffmpeg ; un Chrome sans tête bloqué gardait la tâche launchd « en
    cours » et les lancements suivants n'avaient pas lieu. Chaque commande a un délai ; le rendu est arrêté avec tous ses processus
    (Chrome compris) et le mode automatique prévient."""
    import ast
    import sys as _sys
    import time
    for nom in sorted(glob.glob(os.path.join(ICI, "*.py"))):
        if os.path.basename(nom).startswith("test_"):
            continue
        for n in ast.walk(ast.parse(open(nom, encoding="utf-8").read())):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("run", "Popen", "check_output") \
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess":
                assert n.func.attr == "Popen" or any(k.arg == "timeout" for k in n.keywords), f"{os.path.basename(nom)}:{n.lineno}"
    debut = time.time()
    with pytest.raises(recap.CommandeBloquee, match="bloqué"):
        recap.executer([_sys.executable, "-c", "import time; time.sleep(30)"], str(tmp_path), 1, "essai")
    assert time.time() - debut < 10
    faux_rendus(monkeypatch)
    monkeypatch.setattr(publication.recap, "fabriquer", lambda *a, **k: (_ for _ in ()).throw(recap.CommandeBloquee("rendu HyperFrames bloqué")))
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {})])
    assert publication.auto(config_auto(tmp_path), str(journaux), lambda t: None, D(2026, 11, 2)) == []
    assert any("rendu bloqué" in t for t, _ in garde_fous)


def test_v08_fichiers_de_travail_effaces_et_rendus_purges(tmp_path, monkeypatch):
    """V-08 : chaque rendu gardait environ 100 Mo (son/, projet/, image-muette.mp4) sans rien effacer : 25 à 30 Go par an. En mode
    automatique, ils sont effacés après le contrôle et la publication (la vidéo, recap.json et controle.txt restent) ; les rendus du
    mode automatique de plus de 30 jours sont purgés, jamais un récap fait à la main. Les morceaux de voix recalculables aussi."""
    import time
    import voix
    faux_rendus(monkeypatch)

    def video(j, config, sortie, journal=print, rendre=True, exiger_voix=True, **k):
        for d in ("son", "projet"):
            os.makedirs(os.path.join(sortie, d), exist_ok=True)
        open(os.path.join(sortie, "son", "controle.txt"), "w").write("ok")
        open(os.path.join(sortie, "image-muette.mp4"), "wb").write(b"\0")
        open(os.path.join(sortie, "recap.json"), "w").write("{}")
        chemin = os.path.join(sortie, "recap-2026-11-02.mp4")
        open(chemin, "wb").write(b"\0")
        return chemin
    monkeypatch.setattr(publication.recap, "fabriquer", video)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {})])
    c = config_auto(tmp_path)
    publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 2))
    rendu = tmp_path / "rendus" / "recap-2026-11-02"
    assert sorted(n for n in os.listdir(rendu) if not n.startswith(".")) == ["controle.txt", "recap-2026-11-02.mp4", "recap.json"]
    vieux, main_ = tmp_path / "rendus" / "recap-2026-09-01", tmp_path / "rendus" / "recap-2026-09-02"
    for d in (vieux, main_):
        d.mkdir()
        (d / "recap-x.mp4").write_bytes(b"\0")
    (vieux / ".rendu-auto").write_text("")
    for d in (vieux, main_, rendu):
        os.utime(d, (time.time() - 40 * 86400,) * 2) if d != rendu else None
    assert publication.nettoyer_rendus(c, lambda t: None) == ["recap-2026-09-01"]
    assert not vieux.exists() and main_.exists() and rendu.exists()          # un récap fait à la main n'est jamais purgé
    cache = tmp_path / "cache"
    cache.mkdir()
    for nom in ("abc.mp3", "abc.json", "abc-s0.wav", "abc-s0-t1.1-p0.3.wav", "neuf-s0.wav"):
        (cache / nom).write_bytes(b"\0")
    for nom in ("abc.mp3", "abc.json", "abc-s0.wav", "abc-s0-t1.1-p0.3.wav"):
        os.utime(cache / nom, (time.time() - 40 * 86400,) * 2)
    voix.purger_cache({"cache_voix": str(cache)})
    assert sorted(os.listdir(cache)) == ["abc.json", "abc.mp3", "neuf-s0.wav"]     # les prises payées restent


def test_v10_jour_sans_trade_dit_que_le_robot_n_a_pas_trade(tmp_path):
    """V-10 : « Les conditions n'étaient pas réunies » couvrait aussi l'heure du serveur fausse, le compte non autorisé, le marché
    décoché et les fériés : faux ces jours-là. La voix et l'écran disent « Le robot n'a pas tradé aujourd'hui », sans la raison ; les
    fériés et les demi-séances ne comptent pas comme séances dans la semaine et le mois."""
    import recap_periode
    j = _journee(tmp_path, positions=())
    textes = recap.repliques(j, "r")
    corps = recap.scene_marche(j, j["marches"][0], 0, None, "r", 7.0)[1]
    tout = " ".join(textes) + corps + " ".join(m for l in recap.MOTS_DU_JOUR.values() for m in l)
    assert "conditions" not in tout and "préféré" not in tout and "observer" not in tout
    assert textes[1] == "Nasdaq : le robot n'a pas tradé aujourd'hui." and textes[-1].startswith("Bilan : le robot n'a pas tradé aujourd'hui.")
    assert "Le robot n'a pas tradé" in corps
    semaine = tmp_path / "semaine"
    semaine.mkdir()
    ecrire_jours(str(semaine), [(D(2026, 11, 23), {}), (D(2026, 11, 24), {}), (D(2026, 11, 25), {}),
                                (D(2026, 11, 26), {"positions": ()}), (D(2026, 11, 27), {"positions": ()})])   # Thanksgiving, demi-séance
    p = recap_periode.charger(str(semaine), D(2026, 11, 23), D(2026, 11, 27), "semaine")
    assert [d["jour"] for d in p["jours"]] == [D(2026, 11, 23), D(2026, 11, 24), D(2026, 11, 25)]
    assert "Jeudi" not in recap_periode.repliques(p)[1] and "3 sur 3" in publication.description_periode(p, {})


def test_v11_seuls_le_nasdaq_et_le_sp500_sont_lus(tmp_path):
    """V-11 : `recap --testeur` racontait le Dow (DJI30, fichiers d'un passage précédent du testeur) comme 3e marché, compté au bilan.
    Seuls le Nasdaq et le S&P 500 sont lus, et des versions de journal différentes sont signalées."""
    ecrire_jours(str(tmp_path), [(D(2026, 11, 18), {})])
    ecrire_jours(str(tmp_path), [(D(2026, 11, 18), {}), (D(2026, 11, 19), {})], symbole="DJI30")
    j = journee.charger(str(tmp_path), D(2026, 11, 18))
    assert [m["symbole"] for m in j["marches"]] == ["NDX100"] and journee.jours_finis(str(tmp_path)) == [D(2026, 11, 18)]
    b = tmp_path / "bougies-NDX100.csv"
    b.write_text(b.read_text(encoding="utf-8").replace("\n1;reel;", "\n2;reel;"), encoding="utf-8")
    assert any("versions" in a for a in journee.charger(str(tmp_path), D(2026, 11, 18))["avertissements"])


def test_v19_bougies_ecrites_deux_fois(tmp_path):
    """V-19 : BougiesRow écrit deux fois le même jour (ligne « fin » réécrite après un redémarrage) : 166 bougies au lieu de 83, la
    journée dessinée deux fois. Une bougie par heure, dans l'ordre."""
    ecrire_jours(str(tmp_path), [(D(2026, 11, 18), {})])
    b = tmp_path / "bougies-NDX100.csv"
    lignes = b.read_text(encoding="utf-8").splitlines()
    b.write_text("\r\n".join(lignes + lignes[1:]) + "\r\n", encoding="utf-8")
    m = journee.charger(str(tmp_path), D(2026, 11, 18))["marches"][0]
    heures = [c["heure"] for c in m["bougies"]]
    assert len(heures) == 84 and heures == sorted(heures)


def test_v21_couverture_prise_apres_le_titre_pose(tmp_path, monkeypatch):
    """V-21 : la couverture était prise à 3,2 s fixes ; un titre plus court donnait le volet ou la scène suivante en couverture.
    L'instant est lu dans recap.json (le titre posé, avant le volet)."""
    j = _journee(tmp_path, positions=GAIN)
    sortie = tmp_path / "rendu"
    sortie.mkdir()
    video = sortie / "recap-2026-04-16.mp4"
    video.write_bytes(b"\0")
    (sortie / "recap.json").write_text(json.dumps({"couverture": 1.234, "scenes": [{"id": "titre", "debut": 0, "duree": 2.6}]}))
    appels = []
    monkeypatch.setattr(publication.subprocess, "run", lambda commande, **k: appels.append(commande))
    publication.publier(j, str(video), {"dossier_publication": str(tmp_path / "bureau")})
    ffmpeg = next(a for a in appels if a[0] == "ffmpeg")
    assert ffmpeg[ffmpeg.index("-ss") + 1] == "1.234"


def test_v23_meme_regle_des_marches_qu_etrave(tmp_path):
    """V-23 : la règle des marchés était recopiée dans journee.py et avait divergé d'Étrave (un S&P « ES1… » était « autre »)."""
    import pont
    for symbole in ("NDX100", "USTEC", "US100.cash", "SPX500", "US500", "ES1!", "ES1", "DJI30", "GER40", "XAUUSD", "nq1!"):
        assert journee.instrument(symbole) == pont.instrument_de(symbole), symbole
    assert journee.instrument("ES1!") == "sp500"


def test_v24_telemetrie_d_hyperframes_coupee(tmp_path, monkeypatch):
    """V-24 : la CLI HyperFrames contient une télémétrie (PostHog) et une recherche de mise à jour ; l'outil ne posait ni
    HYPERFRAMES_NO_TELEMETRY ni HYPERFRAMES_NO_UPDATE_CHECK. Posées pour chaque rendu et dans l'agent launchd."""
    import installation
    vus = []

    class Faux:
        returncode = 0

        def __init__(self, commande, **k):
            vus.append(k.get("env") or {})

        def communicate(self, timeout=None):
            return b"", b""
    monkeypatch.setattr(recap.subprocess, "Popen", Faux)
    recap.executer(["hyperframes", "render"], str(tmp_path), 5, "rendu")
    assert vus[0].get("HYPERFRAMES_NO_TELEMETRY") == "1" and vus[0].get("HYPERFRAMES_NO_UPDATE_CHECK") == "1"
    plist = installation.texte_plist(["/usr/bin/python3", "outil.py", "auto"], str(tmp_path), str(tmp_path / "recap-auto.log"))
    assert "<key>HYPERFRAMES_NO_TELEMETRY</key><string>1</string>" in plist
    assert "<key>HYPERFRAMES_NO_UPDATE_CHECK</key><string>1</string>" in plist


def test_v25_certificat_jamais_net_ni_masque_hors_de_l_image(tmp_path, monkeypatch):
    """V-25 : `masques_certificat` vide, ou un certificat remplacé par une image d'une autre taille : le certificat était copié net
    (la prop firm nommée dans la vidéo et la couverture). Refus de rendre sans masque, et masques contrôlés dans l'image."""
    source = tmp_path / "certificat.png"
    _png(source, 600, 450)
    monkeypatch.setattr(presentation.subprocess, "run", lambda *a, **k: None)
    with pytest.raises(ValueError, match="masques_certificat"):
        presentation.copier_certificat({"certificat": str(source), "masques_certificat": []}, str(tmp_path / "a.png"))
    with pytest.raises(ValueError, match="hors de l'image"):
        presentation.copier_certificat({"certificat": str(source), "masques_certificat": [[500, 400, 200, 100]]}, str(tmp_path / "b.png"))
    presentation.copier_certificat({"certificat": str(source), "masques_certificat": [[10, 10, 100, 50]]}, str(tmp_path / "c.png"))


def test_v26_presentation_jamais_sans_une_replique(tmp_path, monkeypatch):
    """V-26 : un dossier de répliques déplacé ou incomplet donnait une présentation avec « N réplique(s) absente(s) », muette sans
    aucune réplique ; contraire à « voix exigée partout ». Refus avant même le rendu."""
    import voix
    source = tmp_path / "certificat.png"
    _png(source, 600, 450)
    (tmp_path / "voix").mkdir()
    for nom, _, _ in presentation.REPLIQUES[:-1]:
        (tmp_path / "voix" / f"{nom}.mp3").write_bytes(b"\0")
    monkeypatch.setattr(presentation.subprocess, "run", lambda *a, **k: pytest.fail("rendu ou ffmpeg lancé sans toutes les répliques"))
    monkeypatch.setattr(recap, "executer", lambda *a, **k: pytest.fail("rendu lancé sans toutes les répliques"), raising=False)
    config = {"sortie": str(tmp_path / "sortie"), "police": recap.POLICE,
              "presentation": {"nom": "Alex", "annees": 4, "montant": "1 000,00 $", "certificat": str(source),
                               "masques_certificat": [[10, 10, 100, 50]], "voix": str(tmp_path / "voix")}}
    with pytest.raises(voix.VoixIndisponible, match="6-fin"):
        presentation.fabriquer(config, lambda t: None)


def test_v28_pas_de_le_prix_repete_ni_de_plus_loin_minuscule():
    """V-28 : « Le prix va jusqu'à … en notre faveur, puis le prix remonte » répétait « le prix » ; « jusqu'à zéro virgule sept
    point en notre faveur » (S&P du 09/06/2025). Un plus loin sous 2 points n'est pas dit."""
    fin = _pos(-1, 13, 70.1, 100.0, "Fin de journée", 60.0, 30.0)
    f = recap.faits({"positions": [fin]})
    texte = recap.phrase_fins(f)
    assert texte.count("prix") == 1 and texte.startswith("Le prix va jusqu'à soixante points en notre faveur")
    petit = recap.faits({"positions": [_pos(-1, 13, 100.4, 100.0, "Fin de journée", 0.7, 30.0)]})
    assert "jusqu'à zéro" not in recap.phrase_fins(petit) and recap.phrase_fins(petit).startswith("Sortie en fin de séance")
    gain = recap.faits({"positions": [_pos(1, 13, 101.2, 100.0, "Stop remonté", 1.5, 30.0)]})
    assert "jusqu'à" not in recap.phrase_stops(gain)


# ───────────────────────── le son (V-15 à V-18) ─────────────────────────
SYNTHETIQUES = {"click-select-1109", "sweep-small-fast-166", "bell-notification-933", "swoosh-wind-short-1461"}


def _bruitages_d_une_journee(tmp_path):
    """Les bruitages d'un récap de séance (deux marchés, stops et sorties de fin de séance, photo) et d'un récap de semaine, tels que
    la fabrication les écrit dans recap.json (sans rendu ni voix)."""
    import recap_periode
    j = _journee(tmp_path, positions=((-1, "A", 9, 36, 100, 10, 2, 112, "Stop"), (-1, "D1", 9, 41, 99, 15, 50, 90, "Fin de journée"),
                                      (-1, "B", 9, 55, 98, 15, 50, 90, "Fin de journée")))
    j["marches"].append(dict(j["marches"][0], nom="S&P 500", voix="S et P cinq cents", symbole="SPX500", ordre=1))
    (tmp_path / "captures").mkdir(exist_ok=True)
    _png(tmp_path / "captures" / "h.png", 760, 142)
    j["historique"] = str(tmp_path / "captures" / "h.png")
    config = {"police": os.path.expanduser(recap.POLICE), "unite": "r"}
    sortie = tmp_path / "rendu"
    sortie.mkdir(exist_ok=True)
    recap.fabriquer(j, config, str(sortie), lambda t: None, rendre=False, exiger_voix=False)
    jour = json.load(open(sortie / "recap.json", encoding="utf-8"))["bruitages"]
    semaine = tmp_path / "semaine"
    semaine.mkdir(exist_ok=True)
    ecrire_jours(str(semaine), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {"positions": PERTE}), (D(2026, 11, 4), {"positions": ()})])
    p = recap_periode.charger(str(semaine), D(2026, 11, 2), D(2026, 11, 6), "semaine")
    s2 = tmp_path / "rendu-semaine"
    s2.mkdir(exist_ok=True)
    recap_periode.fabriquer(p, config, str(s2), lambda t: None, rendre=False, exiger_voix=False)
    return jour, json.load(open(s2 / "recap.json", encoding="utf-8")).get("bruitages", [])


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg absent")
def test_v15_le_pic_de_chaque_bruitage_tombe_sur_l_image(tmp_path, monkeypatch):
    """V-15 : l'outil posait le DÉBUT du fichier sur l'image, alors que le pic vient après (whoosh-cinematic-fast-1492 culmine à
    1,081 s et était coupé à 0,7 s : jamais entendu à son pic). Le pic mesuré une fois par earshot (sons.json) tombe une image après
    l'instant voulu ; la coupe garde le pic ; un repère près du début de la vidéo rogne le début du fichier au lieu de retarder le pic."""
    import controle
    catalogue = mixage.catalogue()
    jour, semaine = _bruitages_d_une_journee(tmp_path)
    for r in jour + semaine:
        assert catalogue[r["son"]].get("pic") is not None, r["son"]
    assert catalogue["whoosh-cinematic-fast-1492"]["pic"] == pytest.approx(1.081, abs=0.02)
    _ffmpeg("-f", "lavfi", "-i", "aevalsrc='exp(-pow((t-0.5)/0.02,2))*sin(2*PI*800*t)':d=1:s=48000", str(tmp_path / "essai.wav"))
    monkeypatch.setattr(mixage, "catalogue", lambda: {"essai": {"fichier": "essai.wav", "pic": 0.5, "attaque": 0.46}})
    for t, max_dur in ((1.0, 0.2), (0.1, None)):
        sortie = str(tmp_path / f"pic-{t}.wav")
        mixage.piste_bruitages([dict({"t": t, "son": "essai"}, **({"max_dur": max_dur} if max_dur else {}))], str(tmp_path), 2.0, sortie,
                               caler=True)
        v = controle.niveaux(sortie, 0.005)
        assert v.index(max(v)) * 0.005 == pytest.approx(t + 1 / 30, abs=0.012), t


def test_v16_aucun_bruitage_synthetique(tmp_path):
    """V-16 : earshot realness jugeait click-select-1109 (0,13, 8 fois par vidéo) et sweep-small-fast-166 (0,16) « likely
    code-synthesized », bell-notification-933 incertain (une sonnerie, proscrite par sound.md), swoosh-wind-short-1461 incertain.
    Remplacés par de vrais enregistrements déjà dans le dossier des sons (rien de téléchargé) ; p_reel mesuré par earshot dans sons.json."""
    catalogue = mixage.catalogue()
    jour, semaine = _bruitages_d_une_journee(tmp_path)
    for r in jour + semaine:
        assert r["son"] not in SYNTHETIQUES, r
        assert catalogue[r["son"]]["p_reel"] >= 0.77, r["son"]
    assert all(catalogue[n]["p_reel"] < 0.5 for n in ("click-select-1109", "sweep-small-fast-166"))


def test_v17_prises_en_rotation_et_coups_secondaires_plus_bas(tmp_path, monkeypatch):
    """V-17 : le même swoosh à chaque volet (« the most common tell ») et 1,98 coup saillant par seconde (références 0,10 à 1,66) :
    les prises tournent (deux ou trois par famille, sans aléatoire) et les coups secondaires sont 4 dB plus bas."""
    jour, semaine = _bruitages_d_une_journee(tmp_path)
    assert semaine
    for liste in (jour, semaine):
        volets = [r["son"] for r in liste if r.get("famille") == "volet"]
        assert len(volets) >= 3 and len(set(volets)) >= 2 and all(a != b for a, b in zip(volets, volets[1:]))
        clics = [r for r in liste if r.get("famille") == "clic"]
        assert len({(r["son"], r.get("demi_tons", 0)) for r in clics}) >= 2
        assert sum(1 for r in liste if r.get("secondaire")) >= len(liste) // 2
    vus = []
    monkeypatch.setattr(mixage, "_pic", lambda f: -6.0)
    monkeypatch.setattr(mixage.subprocess, "run", lambda commande, **k: vus.append(commande[commande.index("-filter_complex") + 1]))
    monkeypatch.setattr(mixage.os.path, "exists", lambda chemin: True)
    mixage.piste_bruitages([{"t": 1, "son": "hit-wood-hard-2182", "gain_db": -6}, {"t": 2, "son": "hit-wood-hard-2182", "gain_db": -6,
                                                                                  "secondaire": True}], "/sons", 3.0, "x.wav", caler=True)
    gains = [float(x) for x in re.findall(r"volume=(-?[\d.]+)dB", vus[0])]
    assert gains[0] - gains[1] == pytest.approx(4.0)


def test_v18_panoramique_leger_des_bruitages(tmp_path, monkeypatch):
    """V-18 : voix mono et bruitages mono, earshot « nearly mono » (côté −18,4 dB, corrélation 0,97). Un léger panoramique suit la
    place de l'action à l'écran (au plus ±0,35)."""
    jour, _ = _bruitages_d_une_journee(tmp_path)
    pans = [r.get("pan", 0) for r in jour]
    assert any(p > 0.05 for p in pans) and any(p < -0.05 for p in pans) and all(abs(p) <= 0.35 for p in pans)
    vus = []
    monkeypatch.setattr(mixage, "_pic", lambda f: -6.0)
    monkeypatch.setattr(mixage.subprocess, "run", lambda commande, **k: vus.append(commande[commande.index("-filter_complex") + 1]))
    monkeypatch.setattr(mixage.os.path, "exists", lambda chemin: True)
    mixage.piste_bruitages([{"t": 1, "son": "hit-wood-hard-2182", "pan": 0.3}], "/sons", 3.0, "x.wav", caler=True)
    assert "pan=stereo|c0=0.700*c0|c1=1.000*c1" in vus[0]


# ───────────────────────── l'image sur un téléphone (V-13, V-14) ─────────────────────────
def _rep_fictive(texte, debut=0.4, pas=0.3):
    """Une réplique aux heures de mots régulières (une pause de 0,25 s après chaque phrase), pour caler une scène sans voix."""
    mots, t = [], debut
    for m in texte.split():
        mots.append({"mot": m, "debut": round(t, 3), "fin": round(t + pas * 0.8, 3)})
        t += pas + (0.25 if m.endswith((".", "!", "?", "…")) else 0.0)
    return {"mots": mots, "duree": round(t, 3), "fichier": "x.wav", "texte": texte}


def _caches_a_zero(script):
    """Les éléments cachés à l'image 0 : gsap.set à l'opacité 0 ou au volet fermé, et les apparitions (wipe, pop, fromTo depuis
    l'opacité 0) dont GSAP pose l'état de départ dès l'image 0."""
    caches = set()
    for cibles, options in re.findall(r"gsap\.set\((\[[^\]]*\]|\"[^\"]+\"), \{([^}]*)\}", script):
        if "opacity: 0" in options or "inset(-30% 100%" in options:
            caches.update(re.findall(r'"([^"]+)"', cibles))
    caches.update(re.findall(r'(?:wipe|pop)\("([^"]+)"', script))
    for cible, depart, reste in re.findall(r'tl\.fromTo\("([^"]+)", \{([^}]*)\}, \{([^}]*)\}', script):
        if "opacity: 0" in depart and "immediateRender: false" not in reste:
            caches.add(cible)
    return caches


def test_v13_date_et_couleur_du_jour_des_la_premiere_image(tmp_path):
    """V-13 : l'image 0 était vide (le titre arrivait ensuite), alors que c'est la vignette du fil TikTok ; la couleur du jour
    n'arrivait qu'à 1,5-2 s. La date et la couleur sont là dès l'image 0 ; le tampon de la couleur bouge sur le mot de la voix."""
    import recap_periode
    j = _journee(tmp_path, positions=GAIN)
    style, corps, script, reperes, fin = recap.scene_titre(j, _rep_fictive(recap.repliques(j, "r")[0]), "r")
    caches = _caches_a_zero(script)
    assert not caches & {"#ti-jour", "#ti-date", "#ti-annee", "#ti-badge"}, caches
    assert "Journée verte" in corps and "#ti-badge" in script
    semaine = tmp_path / "semaine"
    semaine.mkdir()
    ecrire_jours(str(semaine), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {})])
    p = recap_periode.charger(str(semaine), D(2026, 11, 2), D(2026, 11, 6), "semaine")
    script = recap_periode.scene_titre(p, None)[2]
    assert not _caches_a_zero(script) & {"#pt-gros", "#pt-bas", "#pt-badge"}


def _instants(script):
    """Les instants où quelque chose bouge dans le script d'une scène (débuts des animations)."""
    t = [float(x) for x in re.findall(r'(?:wipe|pop)\("[^"]+", ([\d.]+)', script)]
    t += [float(x) for x in re.findall(r"\}, ([\d.]+)\);", script)]
    return sorted(t)


def test_v14_graphique_plus_grand_sous_titres_et_mouvement(tmp_path):
    """V-14 : graphique de 850 x 340 px, moitié basse vide pendant presque toute la scène, aucun sous-titre alors que l'histoire
    en points n'est dite qu'à la voix, et 4,6 s sans aucun changement (check HyperFrames, dead_stretch). Graphique plus haut,
    sous-titres calés sur les mots de la voix (chiffres comme à l'écran), dans la zone sûre de TikTok sous le graphique, un
    mouvement au moins toutes les 3 s."""
    assert recap.Y_BAS - recap.Y_HAUT >= 420 and recap.Y_BAS <= 840 and recap.X1 <= 960
    recap.POLICE = os.path.expanduser(recap.POLICE)
    j = _journee(tmp_path, positions=((-1, "A", 9, 36, 100, 10, 2, 112, "Stop"), (-1, "D1", 9, 41, 99, 15, 50, 90, "Fin de journée"),
                                      (-1, "B", 9, 55, 98, 15, 50, 90, "Fin de journée")))
    for p in j["marches"][0]["positions"]:
        p["mfe"], p["risque"] = 103.0, 18.0
    texte = recap.repliques(j, "r")[1]
    rep = _rep_fictive(texte)
    style, corps, script, reperes, fin = recap.scene_marche(j, j["marches"][0], 0, rep, "r", rep["duree"] + 1, True)
    duree = max(fin, rep["duree"] + 0.6)
    st_style, st_corps, st_script, groupes = recap.scene_sous_titres([{"id": "m0", "debut": 0.0, "duree": duree, "rep": rep}])
    assert groupes and any("103 pts" in g["texte"] for g in groupes) and not any("cent trois" in g["texte"] for g in groupes)
    precedent_fin = 0.0
    for g in groupes:
        assert len(g["lignes"]) <= 2 and all(recap.police.largeur(l, g["taille"], recap.POLICE) <= 656 for l in g["lignes"])
        assert recap.Y_BAS + 40 <= g["haut"] and g["haut"] + len(g["lignes"]) * g["taille"] * 1.2 <= 1260
        assert g["debut"] >= precedent_fin - 0.001 and g["debut"] >= 0.1 and g["fin"] > g["debut"]
        precedent_fin = g["fin"]
    assert st_script.count('visibility: "hidden"') >= len(groupes)                 # extinction dure de chaque groupe
    for secret in ("RSI", "D1", " B ", "élan", "testeur"):
        assert secret not in st_corps
    for x in re.findall(r'<text x="([\d.]+)" y="[\d.]+" font-size="28"[^>]*text-anchor="middle">\d\d:\d\d<', corps):
        assert float(x) - 34 >= 120, x                     # ni « 14:00 » contre le bord gauche (zone sûre de TikTok)
    assert all(int(g) >= 120 for g, _, _, _ in PASTILLE.findall(corps))
    instants = sorted(set(_instants(script) + [g["debut"] for g in groupes]))
    trous = [b - a for a, b in zip([0.0] + instants, instants + [duree]) if a < duree - 1.0]
    assert max(trous) <= 3.0, max(trous)


def test_video_du_testeur_jamais_publiee(tmp_path, monkeypatch, garde_fous):
    """Décision du propriétaire (27/11/2026) : une vidéo faite à partir des journaux du testeur ne se publie jamais, c'est un essai.
    Ni dans le dossier de publication du Bureau, ni dans le registre des publications, ni dans une notification « à publier » : dans
    un dossier d'essais marqué ESSAI, hors du Bureau. Que les journaux viennent de `Etrave/testeur/` ou portent source=testeur."""
    faites = faux_rendus(monkeypatch)
    testeur = tmp_path / "Etrave" / "testeur"
    testeur.mkdir(parents=True)
    ecrire_jours(str(testeur), [(D(2026, 11, k), {"source": "testeur"}) for k in (2, 3, 4, 5, 6)])
    c = config_auto(tmp_path)
    assert publication.auto(c, str(testeur), lambda t: None, D(2026, 11, 6)) == []
    assert D(2026, 11, 6) in faites and ("semaine", D(2026, 11, 2)) in faites           # les essais sont faits…
    assert not (tmp_path / "bureau").exists() or not os.listdir(tmp_path / "bureau")    # … jamais sur le Bureau
    registre = tmp_path / "etat" / "registre.json"
    assert not registre.exists() or "2026-11-06" not in registre.read_text(encoding="utf-8")
    assert not any(t == "Étrave" or "publier" in x for t, x in garde_fous)
    essais = tmp_path / "rendus" / "essais-testeur"
    assert sorted(os.listdir(essais))[:2] == ["ESSAI-2026-11-02", "ESSAI-2026-11-03"]
    assert "NE PAS PUBLIER" in (essais / "ESSAI-2026-11-06" / "ESSAI-NE-PAS-PUBLIER.txt").read_text(encoding="utf-8")
    faites.clear()
    publication.auto(c, str(testeur), lambda t: None, D(2026, 11, 6))                     # un essai déjà fait n'est pas refait
    assert faites == []
    # des journaux du testeur copiés ailleurs (source=testeur) : même règle
    copie = tmp_path / "copie"
    copie.mkdir()
    ecrire_jours(str(copie), [(D(2026, 11, 2), {"source": "testeur"})])
    publication.auto(config_auto(tmp_path, dossier_etat=str(tmp_path / "etat2")), str(copie), lambda t: None, D(2026, 11, 2))
    assert not (tmp_path / "bureau").exists() or not os.listdir(tmp_path / "bureau")
    # et la publication elle-même refuse une séance du testeur
    j = journee.charger(str(copie), D(2026, 11, 2))
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\0")
    with pytest.raises(ValueError, match="testeur"):
        publication.publier(j, str(video), {"dossier_publication": str(tmp_path / "bureau")})
    # un ancien dossier du Bureau fait à partir du testeur ne compte jamais comme la publication d'une vraie séance, et n'est pas écrasé
    vieux = tmp_path / "bureau3" / "2026-11-03"
    vieux.mkdir(parents=True)
    (vieux / "recap-2026-11-03.mp4").write_bytes(b"\0")
    (vieux / "description.txt").write_text(publication.COMPTE["testeur"], encoding="utf-8")
    reel = tmp_path / "reel"
    reel.mkdir()
    ecrire_jours(str(reel), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {})])
    faites.clear()
    c3 = config_auto(tmp_path, dossier_etat=str(tmp_path / "etat3"), dossier_publication=str(tmp_path / "bureau3"))
    publication.auto(c3, str(reel), lambda t: None, D(2026, 11, 3))
    assert faites == [D(2026, 11, 2)] and (vieux / "recap-2026-11-03.mp4").read_bytes() == b"\0"
    assert any("ranger" in t for t, _ in garde_fous)
    assert publication.COMPTE["testeur"] in (vieux / "description.txt").read_text(encoding="utf-8")


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg absent")
def test_v04_photo_de_la_fenetre_de_metatrader_et_pas_d_un_rectangle(tmp_path, monkeypatch):
    """V-04 : sur Mac, `screencapture -R` photographiait un RECTANGLE de l'écran : une fenêtre posée sur MetaTrader, l'écran
    verrouillé ou un dialogue partaient épinglés comme « Historique MetaTrader ». La fenêtre de MetaTrader est photographiée par son
    numéro (`screencapture -l`, même recouverte), et une image presque unie ou noire est refusée. Aucune vraie capture ici."""
    import historique
    appels = []
    liste = "Google Chrome|943|0|1440|778\nFinder|12|0|300|200\nMetaTrader 5|1300|0|1400|900\nMetaTrader 5|1301|3|200|100"

    class Sortie:
        def __init__(self, stdout=""):
            self.stdout, self.stderr, self.returncode = stdout, "", 0

    def faux(commande, **k):
        appels.append(commande)
        if commande[0] == "osascript":
            return Sortie(liste)
        open(commande[-1], "wb").write(b"\x89PNG")
        return Sortie()
    monkeypatch.setattr(historique.subprocess, "run", faux)
    historique._fenetre_mac(str(tmp_path / "f.png"))
    capture = next(c for c in appels if c[0] == "screencapture")
    assert "-R" not in capture and capture[capture.index("-l") + 1] == "1300"
    liste = "Google Chrome|943|0|1440|778"
    with pytest.raises(historique.PhotoImpossible, match="introuvable"):
        historique._fenetre_mac(str(tmp_path / "g.png"))
    monkeypatch.undo()
    noire, mire = str(tmp_path / "noire.png"), str(tmp_path / "mire.png")
    _ffmpeg("-f", "lavfi", "-i", "color=c=black:s=800x400", "-frames:v", "1", noire)
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=800x400", "-frames:v", "1", mire)
    assert historique.image_presque_unie(noire) and not historique.image_presque_unie(mire)
    for source, attendu in ((noire, None), (mire, "photo")):
        monkeypatch.setattr(historique, "photographier_fenetre", lambda png, s=source: __import__("shutil").copy(s, png))
        lignes = []
        cadre = {"historique": {"x": 0, "y": 10, "largeur": 600, "entete": 30, "ligne": 30}}
        r = historique.photographier_jour(cadre, str(tmp_path), D(2026, 11, 18), 3, lignes.append,
                                          datetime.datetime(2026, 11, 18, 21, 20, tzinfo=UTC))
        assert (r is None and "presque unie" in " ".join(lignes)) if attendu is None else (r and os.path.exists(r)), lignes


# ───────────────────────── V-27 : de bout en bout, sans Chrome ni réseau ─────────────────────────
def _voix_simulee(monkeypatch, dossier):
    """voix.replique remplacée par une voix SIMULÉE (un son par mot, un silence entre les scènes) au format d'ElevenLabs : aucun
    appel réseau (voix.appeler interdit), aucun crédit. La découpe par scène (voix.recit) et le rythme (voix.rythmer) sont les vrais."""
    import math
    import struct
    import wave
    import voix
    monkeypatch.setattr(voix, "appeler", lambda *a, **k: pytest.fail("appel réseau à ElevenLabs"))

    def replique(texte, config, avant="", apres=""):
        taux, mots, t, morceaux = 16000, [], 0.15, []
        for scene in texte.split(voix.SEPARATEUR):
            for m in scene.split():
                mots.append({"mot": m, "debut": round(t, 3), "fin": round(t + 0.2, 3)})
                t += 0.3
            t += 0.6
        n = int((t + 0.2) * taux)
        echantillons = bytearray(2 * n)
        for m in mots:
            for i in range(int(m["debut"] * taux), int(m["fin"] * taux)):
                v = int(9000 * math.sin(2 * math.pi * 180 * i / taux) * math.sin(math.pi * (i / taux - m["debut"]) / 0.2))
                struct.pack_into("<h", echantillons, 2 * i, v)
        chemin = os.path.join(dossier, f"voix-{len(texte)}.wav")
        with wave.open(chemin, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(taux)
            w.writeframes(bytes(echantillons))
        return {"fichier": chemin, "duree": round(n / taux, 3), "mots": mots, "texte": texte}
    monkeypatch.setattr(voix, "replique", replique)


def _rendu_sans_chrome(monkeypatch):
    """Le rendu HyperFrames (Chrome) remplacé par une image unie de la durée du projet ; tout le reste (voix, bruitages, musique,
    mixage, contrôle, couverture, publication) tourne pour de vrai avec ffmpeg."""
    def executer(commande, dossier, delai, quoi):
        sortie = commande[commande.index("--output") + 1]
        duree = float(re.search(r'data-composition-id="main" data-start="0" data-duration="([\d.]+)"',
                                open(os.path.join(dossier, "index.html"), encoding="utf-8").read()).group(1)) if os.path.exists(
            os.path.join(dossier, "index.html")) else 45.3
        _ffmpeg("-f", "lavfi", "-i", f"color=c=white:s=108x192:d={duree}:r=30", "-pix_fmt", "yuv420p", sortie)
    monkeypatch.setattr(recap, "executer", executer)


def _sons(tmp_path):
    """Le dossier des sons : un vrai fichier pour chaque nom du catalogue (un bruit bref), et une musique."""
    import shutil
    sons = tmp_path / "sons"
    sons.mkdir()
    _ffmpeg("-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:r=48000:a=0.5", "-af", "afade=t=out:st=0.1:d=0.5", str(sons / "bref.wav"))
    for s in mixage.catalogue().values():
        shutil.copy(sons / "bref.wav", sons / s["fichier"])
    _ffmpeg("-f", "lavfi", "-i", "sine=f=330:d=12:r=48000", "-ac", "2", str(tmp_path / "musique.wav"))
    return str(sons), str(tmp_path / "musique.wav")


def _duree(chemin):
    import subprocess
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", chemin],
                                capture_output=True, text=True, timeout=60).stdout)


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg absent")
def test_v27_de_bout_en_bout_sans_chrome(tmp_path, monkeypatch, garde_fous):
    """V-27 : recap.fabriquer, recap_periode.fabriquer, presentation.fabriquer, voix.recit et rythmer, mixage (voix, bruitages,
    musique, assemblage), le contrôle du son et la publication n'étaient jamais exécutés par les tests. Ici, tout tourne pour de vrai
    (ffmpeg), du journal de l'EA au dossier de publication, avec une voix simulée et une image unie à la place de Chrome."""
    import recap_periode
    _voix_simulee(monkeypatch, str(tmp_path))
    _rendu_sans_chrome(monkeypatch)
    sons, musique = _sons(tmp_path)
    journaux = tmp_path / "journaux"
    journaux.mkdir()
    ecrire_jours(str(journaux), [(D(2026, 11, 2), {"positions": ((-1, "A", 9, 36, 100, 10, 2, 112, "Stop"),
                                                                 (-1, "D1", 9, 41, 99, 15, 50, 90, "Fin de journée"))})])
    c = config_auto(tmp_path, sons=sons, musique=musique, police=os.path.expanduser(recap.POLICE), voix_id="simulee",
                    cache_voix=str(tmp_path / "cache"))
    dossiers = publication.auto(c, str(journaux), lambda t: None, D(2026, 11, 2))
    assert len(dossiers) == 1
    assert sorted(os.listdir(dossiers[0])) == ["avant-de-publier.txt", "couverture.jpg", "description.txt", "recap-2026-11-02.mp4"]
    rendu = tmp_path / "rendus" / "recap-2026-11-02"
    info = json.load(open(rendu / "recap.json", encoding="utf-8"))
    assert abs(_duree(os.path.join(dossiers[0], "recap-2026-11-02.mp4")) - info["duree"]) < 0.2
    assert "Niveau" in (rendu / "controle.txt").read_text(encoding="utf-8") and not (rendu / "son").exists()
    assert any(t == "Étrave" for t, _ in garde_fous)                       # « prêt à publier »
    # la semaine (sans publication : la fabrication seule)
    semaine = tmp_path / "semaine"
    semaine.mkdir()
    ecrire_jours(str(semaine), [(D(2026, 11, 2), {}), (D(2026, 11, 3), {"positions": PERTE})])
    p = recap_periode.charger(str(semaine), D(2026, 11, 2), D(2026, 11, 6), "semaine")
    (tmp_path / "rendu-semaine").mkdir()
    video = recap_periode.fabriquer(p, c, str(tmp_path / "rendu-semaine"), lambda t: None)
    assert _duree(video) > 5 and os.path.exists(tmp_path / "rendu-semaine" / "son" / "controle.txt")
    # la présentation, avec un profil d'essai FICTIF (aucune donnée personnelle)
    (tmp_path / "repliques").mkdir()
    for nom, _, _ in presentation.REPLIQUES:
        _ffmpeg("-f", "lavfi", "-i", "sine=f=200:d=1.5:r=44100", "-f", "mp3", str(tmp_path / "repliques" / f"{nom}.mp3"))
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=600x450", "-frames:v", "1", str(tmp_path / "certificat.png"))
    profil = {"nom": "Alex", "annees": 4, "montant": "1 000,00 $", "certificat": str(tmp_path / "certificat.png"),
              "masques_certificat": [[10, 10, 200, 60]], "voix": str(tmp_path / "repliques")}
    video = presentation.fabriquer(dict(c, presentation=profil), lambda t: None)
    assert abs(_duree(video) - presentation.DUREE) < 0.2
