"""Tests du lancement de l'outil vidéo en fin de journée par Étrave (demande de l'utilisateur du 27/11/2026) :
`python -m pytest etrave`. Aucun test ne lance le vrai outil vidéo : le lanceur est toujours remplacé."""
import datetime
import os
import sys

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import etrave  # noqa: E402
import export  # noqa: E402
import fin_de_journee as fdj  # noqa: E402

UTC = datetime.timezone.utc
SEANCE_COLONNES = "version;source;jour_ny;symbole;moment;heure_ny;range_bas;range_haut;range_prix;stop_mult;spread;cout_r;filtres;etat"


def utc_pour_ny(annee, mois, jour, heure, minute):
    """Instant UTC d'une heure de New York en hiver (UTC-5), comme le lundi 30/11/2026."""
    return datetime.datetime(annee, mois, jour, heure, minute, tzinfo=UTC) + datetime.timedelta(hours=5)


LUNDI_16H = utc_pour_ny(2026, 11, 30, 16, 0)


def etat(symbole, **cles):
    base = {"symbole": symbole, "en_marche": True, "position": False, "attente": False, "jambes": 0.0, "sortie_ny": "15:50"}
    base.update(cles)
    return base


def ligne_fin(dossier, symbole, jour="2026-11-30", moment="fin"):
    chemin = os.path.join(dossier, f"seances-{symbole}.csv")
    neuf = not os.path.exists(chemin)
    with open(chemin, "a", encoding="utf-8", newline="") as f:
        if neuf:
            f.write(SEANCE_COLONNES + "\r\n")
        f.write(f"2;demo;{jour};{symbole};{moment};15:52;1;2;1;3;0.5;0.1;FICTIF;Pas de trade\r\n")


def outil_installe(tmp_path):
    outil = tmp_path / "outil-video"
    (outil / "video").mkdir(parents=True)
    (outil / "video" / "outil.py").write_text("# FICTIF\n")
    (outil / "config-auto.json").write_text("{}\n")
    return str(outil)


@pytest.fixture()
def dossier(tmp_path):
    d = tmp_path / "etrave"
    d.mkdir()
    return str(d)


def test_heure_de_new_york_comme_l_export():
    for instant in (datetime.datetime(2026, 3, 8, 6, 30, tzinfo=UTC), datetime.datetime(2026, 3, 8, 7, 30, tzinfo=UTC),
                    datetime.datetime(2026, 11, 1, 5, 30, tzinfo=UTC), datetime.datetime(2026, 11, 1, 6, 30, tzinfo=UTC),
                    datetime.datetime(2026, 11, 30, 4, 59, tzinfo=UTC), LUNDI_16H):
        assert fdj.heure_ny(instant).date() == export.aujourdhui_ny(instant), instant
    assert fdj.heure_ny(LUNDI_16H) == datetime.datetime(2026, 11, 30, 16, 0)


def test_pas_avant_la_sortie_plus_cinq_minutes(dossier):
    ligne_fin(dossier, "NDX100")
    pret, texte = fdj.pret([etat("NDX100")], dossier, utc_pour_ny(2026, 11, 30, 15, 54))
    assert not pret and texte == "après 15:55 NY"
    # demi-séance : sortie à 12:45, donc prêt dès 12:50
    pret, _ = fdj.pret([etat("NDX100", sortie_ny="12:45")], dossier, utc_pour_ny(2026, 11, 30, 12, 50))
    assert pret


def test_pas_tant_qu_un_trade_ou_un_ordre_est_ouvert(dossier):
    ligne_fin(dossier, "NDX100")
    ligne_fin(dossier, "SPX500")
    for occupe in ({"position": True}, {"attente": True}, {"jambes": 1.0}):
        pret, texte = fdj.pret([etat("NDX100"), etat("SPX500", **occupe)], dossier, LUNDI_16H)
        assert not pret and texte == "trade ou ordre encore ouvert sur SPX500", occupe
    # le dernier état connu d'un EA arrêté compte aussi : sa position est peut-être encore ouverte
    pret, _ = fdj.pret([etat("NDX100"), etat("SPX500", en_marche=False, position=True)], dossier, LUNDI_16H)
    assert not pret


def test_pas_sans_la_ligne_de_fin_de_chaque_ea_en_marche(dossier):
    ligne_fin(dossier, "NDX100")
    ligne_fin(dossier, "SPX500", jour="2026-11-27")            # la ligne d'un autre jour ne compte pas
    ligne_fin(dossier, "SPX500", moment="decision")             # ni la ligne de 9:35
    pret, texte = fdj.pret([etat("NDX100"), etat("SPX500")], dossier, LUNDI_16H)
    assert not pret and texte == "ligne de fin pas encore écrite : SPX500"


def test_pret_quand_tout_est_clos(dossier):
    ligne_fin(dossier, "NDX100")
    ligne_fin(dossier, "SPX500")
    assert fdj.pret([etat("NDX100"), etat("SPX500")], dossier, LUNDI_16H) == (True, "séance close")
    # un EA arrêté sans trade n'empêche pas la vidéo de l'autre marché (l'outil vidéo signale le jour manquant)
    assert fdj.pret([etat("NDX100"), etat("SPX500", en_marche=False)], dossier, LUNDI_16H) == (True, "séance close")


def test_rien_le_week_end_ni_sans_ea(dossier):
    assert fdj.pret([etat("NDX100")], dossier, utc_pour_ny(2026, 11, 28, 16, 0)) == (False, "pas de séance le week-end")
    assert fdj.pret([], dossier, LUNDI_16H) == (False, "aucun EA en marche")
    assert fdj.pret([etat("NDX100", en_marche=False)], dossier, LUNDI_16H) == (False, "aucun EA en marche")


def test_commande_fixe_sans_shell(tmp_path):
    outil = outil_installe(tmp_path)
    commande = fdj.commande(outil, "/usr/local/bin/python3")
    assert commande == ["/usr/local/bin/python3", os.path.join(outil, "video", "outil.py"), "auto", "--config",
                        os.path.join(outil, "config-auto.json")]
    assert fdj.installe(outil) and not fdj.installe(str(tmp_path / "absent"))


def test_meme_dossier_et_meme_python_que_l_installation_de_l_outil_video():
    """Le dossier et l'interpréteur recopiés ici doivent rester ceux de video/installation.py (branche de l'outil vidéo)."""
    chemin = os.path.join(os.path.dirname(ICI), "video", "installation.py")
    if not os.path.exists(chemin):
        pytest.skip("outil vidéo absent de cette branche")
    texte = open(chemin, encoding="utf-8").read()
    assert '"~/Library/Application Support/Etrave/outil-video"' in texte
    assert '"Etrave", "outil-video"' in texte and '"~/.local/share/etrave/outil-video"' in texte
    assert '("/usr/local/bin/python3", "/opt/homebrew/bin/python3")' in texte
    assert fdj.dossier_outil_video(systeme="darwin", env={"HOME": "/Users/x"}) == "/Users/x/Library/Application Support/Etrave/outil-video"


def application(dossier, outil, appels, echec=False):
    def lancer(commande, journal_outil, env):
        appels.append((commande, journal_outil, env))
        if echec:
            raise OSError("FICTIF")
    return etrave.Application(dossier, mt5_terminaux=lambda etats: [], video_lancer=lancer, video_dossier=outil,
                              video_python="/usr/local/bin/python3")


def test_lancee_une_seule_fois_par_jour_et_visible_dans_l_etat(dossier, tmp_path):
    outil = outil_installe(tmp_path)
    appels = []
    app = application(dossier, outil, appels)
    etats = [etat("NDX100"), etat("SPX500")]
    assert app.verifier_fin_de_journee(etats, LUNDI_16H - datetime.timedelta(minutes=10)) is False   # 15:50 : trop tôt
    assert app.etat()["video"]["attente"] == "après 15:55 NY" and app.etat()["video"]["installe"] is True
    ligne_fin(dossier, "NDX100")
    ligne_fin(dossier, "SPX500")
    assert app.verifier_fin_de_journee(etats, LUNDI_16H) is True
    assert app.verifier_fin_de_journee(etats, LUNDI_16H + datetime.timedelta(minutes=1)) is False   # déjà lancée aujourd'hui
    assert len(appels) == 1
    commande, journal_outil, env = appels[0]
    assert commande[2] == "auto" and journal_outil == os.path.join(outil, "recap-auto.log")
    assert env["HYPERFRAMES_NO_TELEMETRY"] == "1" and env["HYPERFRAMES_NO_UPDATE_CHECK"] == "1"
    video = app.etat()["video"]
    assert video["derniere"] == {"jour": "2026-11-30", "heure_ny": "16:00", "resultat": "lancee"}
    # un autre processus Étrave (double-clic) relit le même fichier : pas de deuxième lancement
    autre = application(dossier, outil, appels)
    assert autre.verifier_fin_de_journee(etats, LUNDI_16H + datetime.timedelta(minutes=2)) is False and len(appels) == 1


def test_echec_du_lancement_retenu_sans_reessai_le_meme_jour(dossier, tmp_path):
    outil = outil_installe(tmp_path)
    appels = []
    app = application(dossier, outil, appels, echec=True)
    ligne_fin(dossier, "NDX100")
    assert app.verifier_fin_de_journee([etat("NDX100")], LUNDI_16H) is False
    assert app.etat()["video"]["derniere"]["resultat"] == "echec"
    assert app.verifier_fin_de_journee([etat("NDX100")], LUNDI_16H + datetime.timedelta(minutes=1)) is False and len(appels) == 1


def test_rien_si_l_outil_video_n_est_pas_installe(dossier, tmp_path):
    appels = []
    app = application(dossier, str(tmp_path / "absent"), appels)
    ligne_fin(dossier, "NDX100")
    assert app.verifier_fin_de_journee([etat("NDX100")], LUNDI_16H) is False and appels == []
    assert app.etat()["video"]["installe"] is False


def test_la_minuterie_de_main_verifie_chaque_minute():
    source = open(os.path.join(ICI, "etrave.py"), encoding="utf-8").read()
    assert "VIDEO_PERIODE_S = 60" in source and "verifier_fin_de_journee_puis_reprogrammer" in source
