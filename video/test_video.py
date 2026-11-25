"""Contrôles de l'outil vidéo : nombres en lettres, lecture d'une journée (heure de Paris, séance finie, bougies), textes de la voix
(rien de secret, R expliqué), mention « Exemple » des journées du testeur, modèle de la présentation, et rien de personnel dans le dépôt."""
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
    assert "le prix sort de la zone par le bas à quinze heures trente-six. Trois positions à la vente : un stop touché, deux sorties en fin de séance." in textes[1]
    assert textes[0] == "Récap de la séance du jeudi seize avril."
    assert textes[-1].endswith("Chaque séance est sur le Telegram, lien en bio.") and recap.mot_du_jour(j, recap.total(j, "r")) in textes[-1]


def test_jour_sans_trade_ne_dit_pas_pourquoi(tmp_path):
    j = _journee(tmp_path, positions=())
    textes = recap.repliques(j, "r")
    assert "pas de trade aujourd'hui, les conditions n'étaient pas réunies." in textes[1]
    assert "RSI" not in " ".join(textes) and recap.mot_du_jour(j, None) in recap.MOTS_DU_JOUR["rien"]


def test_mention_exemple_seulement_pour_le_testeur(tmp_path):
    scenes = [{"id": "titre", "debut": 0, "duree": 3}]
    assert "Exemple : journée du testeur" in recap._index(scenes, 3, True)
    assert "Exemple" not in recap._index(scenes, 3, False)
    assert _journee(tmp_path, source="testeur")["source"] == "testeur"


def test_les_scenes_n_affichent_pas_le_type_d_entree(tmp_path):
    j = _journee(tmp_path, positions=((1, "D2", 9, 40, 100, 15, 50, 110, "Fin de journée"),))
    style, corps, script, reperes = recap.scene_marche(j, j["marches"][0], 0, None, "r", 7.0)
    assert "D2" not in corps and "Achat" in corps and "Sortie de zone par le haut à 15:40" in corps
    assert all(r["son"] in mixage.catalogue() for r in reperes)


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
