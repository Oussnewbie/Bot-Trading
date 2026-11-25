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

UTC = datetime.timezone.utc


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
    assert textes[-1].endswith("Chaque séance est sur le Telegram : lien en bio !") and recap.mot_du_jour(j, recap.total(j, "r")) in textes[-1]


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
    assert "pas de trade aujourd'hui, les conditions n'étaient pas réunies." in textes[1] and "Journée sans trade" in textes[0]
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
    assert all(r["son"] in mixage.catalogue() for r in reperes)


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
    return [v for v in (c.get("voix_id"), p.get("nom"), p.get("montant"), p.get("libelle_montant", "").split(" ")[-1]) if v and len(v) > 3]


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


# ───────────────────────── publication automatique ─────────────────────────
import publication  # noqa: E402


def test_description_tiktok_dit_le_compte_sans_rien_de_secret(tmp_path):
    j = _journee(tmp_path, positions=((1, "D2", 9, 40, 100, 15, 50, 110, "Fin de journée"),))
    texte = publication.description(j, {})
    assert texte.startswith("Journée verte : récap de la séance du jeudi 16 Avril 2026.")
    assert "Trades réels, sur mon compte." in texte and "Nasdaq 100 : +" in texte and "Pas un conseil en investissement." in texte
    assert "D2" not in texte and "RSI" not in texte and "élan" not in texte
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
    assert sorted(os.listdir(dossiers[0])) == ["description.txt", "recap-2026-04-16.mp4"]
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16)) == []      # déjà publié
    assert publication.auto(dict(config, auto_depuis="2026-04-17"), str(journaux), lambda t: None) == []
    ecrire_journee(str(journaux), datetime.date(2026, 4, 16), positions=())                               # sans trade : rien
    config["dossier_publication"] = str(tmp_path / "bureau2")
    assert publication.auto(config, str(journaux), lambda t: None, datetime.date(2026, 4, 16)) == []


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
