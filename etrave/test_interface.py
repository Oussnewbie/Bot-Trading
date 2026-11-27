"""Tests de l'interface Étrave et de son accord avec l'EA (robot/Strategy-V11.mq5) : `python -m pytest etrave`.

L'EA ne peut pas être exécuté ici : ses fichiers sont fabriqués à la main dans le format qu'il écrit, et un test relit
le code MQL5 pour vérifier que les noms de clés, les bornes et le format du journal sont les mêmes des deux côtés.
"""
import datetime
import http.client
import json
import os
import re
import sys
import threading
import time
import urllib.error

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etrave  # noqa: E402
import export  # noqa: E402
import mt5  # noqa: E402
import pont  # noqa: E402
import risque  # noqa: E402
import telegram  # noqa: E402

JETON = "123456789:" + "A" * 35
EA = open(os.path.join(RACINE, "robot", "Strategy-V11.mq5"), encoding="utf-8-sig").read()


def faux_etat(dossier, symbole="NAS100", age=0.0, **cles):
    """Écrit un état comme le fait l'EA (cle=valeur, fin de ligne Windows)."""
    base = dict(version="1", ea="5.10", symbole=symbole, instrument="nasdaq", actif="1", terminal=r"C:\Program Files\MetaTrader 5",
                compte_type="demo", compte_serveur="Courtier-Demo", compte_login="12345678", devise="USD", solde="10000.00",
                capital="10000.00", marge_libre="10000.00", levier_compte="30", levier_symbole="20.0", connecte="1",
                trading_auto="1", heure_ny="2026.11.16 10:02", heure_serveur="17:02", horloge_ok="1", regles_test="1",
                risque_pct="0.5000", risque_source="mt5", range_bas="25010.5", range_haut="25050.5", filtres="Achat oui · Vente non (RSI) · RSI 61",
                jour="Achat stop 25050.5 · jusqu'à 09:45", attente="0", position="0", pos_sens="0", pos_entree="0", pos_stop="0",
                pos_lots="0", pos_resultat="0", pos_r="0", pos_pyramide="0", risque_argent="0", solde_depart="0", stats_n="0",
                stats_gagnants="0", stats_r="0", stats_baisse="0", stats_serie="0", telegram="0", telegram_envoi="jamais", telegram_essai="",
                jambes="0", v8_b="B attend la cassure", v9_d="D : 0 en cours")
    base.update(cles)
    chemin = os.path.join(dossier, f"etat-{symbole}.txt")
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write("".join(f"{k}={v}\r\n" for k, v in base.items()))
    quand = time.time() - age
    os.utime(chemin, (quand, quand))
    return chemin


@pytest.fixture()
def dossier(tmp_path):
    return str(tmp_path)


# ───────────────────────── réglages ─────────────────────────
def test_sans_fichier_rien_n_est_impose_a_l_ea(dossier):
    r = pont.reglages_publics(dossier)
    assert r["risquePct"] is None and r["levier"] is None
    assert r["instruments"] == {"nasdaq": True, "sp500": True}     # les deux marchés de la V11, cochés
    assert not r["telegramJeton"] and not r["telegramDiscussion"]


def test_risque_entre_les_bornes_et_confirmation_au_dela_de_0_5_pct(dossier):
    # AUD-05 : mot RISQUE demandé au-delà de 0,5 %. Plafond : 1 % après l'audit, 20 % depuis la décision de l'utilisateur du
    # 27/11/2026 (« pour des tests », tous comptes)
    assert pont.regler(dossier, {"risquePct": 0.5}) == ["risque_pct"]
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.5"
    for hors_bornes in (0, 0.04, 20.01, 25, 100, 1e9, -1, -20, "abc", "", None, True, "nan", "inf", "-inf", [20], {"x": 1}):
        with pytest.raises(pont.Refus):
            pont.regler(dossier, {"risquePct": hors_bornes}, "RISQUE")
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.5"       # aucune valeur hors bornes écrite
    with pytest.raises(pont.Refus, match="RISQUE"):
        pont.regler(dossier, {"risquePct": 0.75})                   # monter au-delà de 0,5 % : il faut le mot
    with pytest.raises(pont.Refus, match="RISQUE"):
        pont.regler(dossier, {"risquePct": 20})                     # le plafond aussi
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.5"       # rien n'a été écrit
    pont.regler(dossier, {"risquePct": 1}, "RISQUE")
    assert pont.reglages_publics(dossier)["risquePct"] == 1.0
    pont.regler(dossier, {"risquePct": 2.5}, "RISQUE")
    assert pont.reglages_publics(dossier)["risquePct"] == 2.5
    with pytest.raises(pont.Refus, match="RISQUE"):
        pont.regler(dossier, {"risquePct": 20}, "risque ")          # monter : le mot exact, en majuscules
    assert pont.lire_reglages(dossier)["risque_pct"] == "2.5"
    pont.regler(dossier, {"risquePct": "20"}, "RISQUE")             # le plafond, en texte : accepté avec le mot
    assert pont.reglages_publics(dossier)["risquePct"] == 20.0 and pont.lire_reglages(dossier)["risque_pct"] == "20"
    pont.regler(dossier, {"risquePct": 1})                          # baisser ne demande rien
    pont.regler(dossier, {"risquePct": 0.75})
    pont.regler(dossier, {"risquePct": "0,25"})                     # virgule française acceptée
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.25"


def test_levier_et_cases(dossier):
    pont.regler(dossier, {"levier": 20, "nasdaq": False})
    r = pont.reglages_publics(dossier)
    assert r["levier"] == 20 and r["instruments"] == {"nasdaq": False, "sp500": True}   # une case n'arrête que son marché
    pont.regler(dossier, {"sp500": False})
    assert pont.reglages_publics(dossier)["instruments"] == {"nasdaq": False, "sp500": False}
    pont.regler(dossier, {"levier": None})
    assert "levier" not in pont.lire_reglages(dossier)
    for faux in (0.5, 2001, "x"):
        with pytest.raises(pont.Refus):
            pont.regler(dossier, {"levier": faux})
    for autre in ("or", "dow", "eurusd", "bitcoin"):
        with pytest.raises(pont.Refus):
            pont.regler(dossier, {autre: True})                     # Nasdaq et S&P 500 seulement : aucun autre instrument
    pont.regler(dossier, {"nasdaq": True})
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"nasdaq": "oui"})
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"telegram_jeton": JETON})             # les secrets ne passent pas par ce chemin
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"mode": "live"})


def test_une_proposition_refusee_n_ecrit_rien(dossier):
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"nasdaq": False, "risquePct": 99})
    assert pont.lire_reglages(dossier) == {}


def fichier_occupe(monkeypatch, echecs):
    """reglages.txt illisible pendant `echecs` lectures (sous Windows : l'EA est en train de le lire)."""
    vrai_open, reste = open, [echecs]

    def faux_open(chemin, mode="r", *args, **kwargs):
        if str(chemin).endswith(pont.FICHIER_REGLAGES) and "r" in mode and reste[0] > 0:
            reste[0] -= 1
            raise PermissionError("occupé")
        return vrai_open(chemin, mode, *args, **kwargs)
    monkeypatch.setattr("builtins.open", faux_open)
    monkeypatch.setattr(pont.time, "sleep", lambda s: None)


def test_un_fichier_occupe_un_instant_n_efface_pas_les_autres_reglages(dossier, monkeypatch):
    """ET-02 / ET-03 (revue du 17/11/2026) : une lecture ratée effaçait les autres clés, case du Nasdaq comprise."""
    pont.regler(dossier, {"risquePct": 0.25, "nasdaq": False})
    fichier_occupe(monkeypatch, 3)
    pont.regler(dossier, {"levier": 20})
    cles = pont.lire_reglages(dossier)
    assert cles["risque_pct"] == "0.25" and cles["nasdaq"] == "0" and cles["levier"] == "20"


def test_un_fichier_toujours_occupe_refuse_au_lieu_d_ecraser(dossier, monkeypatch):
    pont.regler(dossier, {"risquePct": 0.25, "nasdaq": False})
    fichier_occupe(monkeypatch, 10_000)
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"levier": 20})
    monkeypatch.undo()
    assert pont.lire_reglages(dossier) == {"risque_pct": "0.25", "nasdaq": "0", "version": "1"}



def test_entrees_b_et_d_ouvertes_apres_la_sortie_de_a(dossier):
    """Relecture du 24/11/2026 : une fois A sortie, le bouton « Clôturer » disparaissait alors que B ou D étaient ouvertes."""
    faux_etat(dossier, position="0", attente="0", jambes="2", v8_b="B en cours +0,4R", v9_d="D : 1 en cours +0,2R")
    e = pont.lire_etats(dossier)[0]
    assert e["position"] is False and e["jambes"] == 2 and e["v8_b"] == "B en cours +0,4R"
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert "e.position || e.attente || e.jambes > 0" in page

def test_connexions_validees_et_jamais_renvoyees(dossier):
    with pytest.raises(pont.Refus) as refus:
        pont.enregistrer_connexions(dossier, {"telegram_jeton": "pas-un-jeton-secret"})
    assert "pas-un-jeton-secret" not in str(refus.value)            # le message ne répète pas la valeur
    with pytest.raises(pont.Refus):
        pont.enregistrer_connexions(dossier, {"risque_pct": "5"})
    assert pont.enregistrer_connexions(dossier, {"telegram_jeton": f"  {JETON} ", "telegram_discussion": "-100123456"}) == ["telegram_jeton", "telegram_discussion"]
    publics = pont.reglages_publics(dossier)
    assert publics["telegramJeton"] and publics["telegramDiscussion"]
    assert JETON not in json.dumps(publics) and "-100123456" not in json.dumps(publics)
    pont.enregistrer_connexions(dossier, {"telegram_jeton": "", "telegram_discussion": ""})
    assert "telegram_jeton" not in pont.lire_reglages(dossier)


def test_demande_de_cloture(dossier):
    with pytest.raises(pont.Refus):
        pont.demander_cloture(dossier, "NAS100", "oui")
    with pytest.raises(pont.Refus):
        pont.demander_cloture(dossier, "NAS100;XAUUSD", "CLOTURER")  # un symbole ne peut pas contenir de séparateur
    pont.demander_cloture(dossier, "NAS100", "CLOTURER", maintenant=1_763_000_000)
    assert pont.lire_reglages(dossier)["cloturer_NAS100"] == "1763000000;NAS100"
    assert pont.lire_reglages(dossier)["cloturer"] == "1763000000;NAS100"           # l'ancienne clé, pour un EA d'avant
    # Revue cloud du 25/11/2026 : une deuxième demande, pour un autre marché dans la même seconde, n'efface plus la première
    pont.demander_cloture(dossier, "US500", "CLOTURER", maintenant=1_763_000_000)
    r = pont.lire_reglages(dossier)
    assert r["cloturer_NAS100"] == "1763000000;NAS100" and r["cloturer_US500"] == "1763000000;US500"


# ───────────────────────── ce que dit l'EA ─────────────────────────
def test_etat_de_l_ea_et_silence(dossier):
    faux_etat(dossier, "NAS100", age=1, position="1", pos_sens="1", pos_r="1.25", pos_resultat="62.50", solde_depart="10000.00")
    faux_etat(dossier, "XAUUSD", age=120, instrument="autre", actif="1")
    nas, autre = pont.lire_etats(dossier)
    assert nas["symbole"] == "NAS100" and nas["en_marche"] and nas["position"] and nas["pos_r"] == 1.25 and nas["solde"] == 10000.0
    assert autre["instrument"] == "autre" and not autre["en_marche"]                     # muet depuis 2 minutes : arrêté


def test_journal_des_trades(dossier):
    with open(os.path.join(dossier, "trades-NAS100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("1763322600;2026-11-16;15:50;NAS100;1;1.50;1.3000;65.20;10000.00;Fin de journée;1;USD\r\n")
        f.write("ligne abîmée\r\n")
        f.write("1763236200;2026-11-13;09:52;NAS100;-1;1.20;-1.0200;-51.00;10051.00;Stop;0;USD\r\n")
    perte, gain = pont.lire_trades(dossier)
    assert perte["net"] == -51.0 and perte["sens"] == -1 and not perte["pyramide"]
    assert gain["r"] == 1.3 and gain["pct"] == pytest.approx(0.652) and gain["pyramide"] and gain["raison"] == "Fin de journée"


# ───────────────────────── risque et marge ─────────────────────────
@pytest.mark.parametrize("pct, par_an, baisse, pire_jour", [(0.25, 11, 12, 1.5), (1.0, 41, 43, 6.0), (2.5, 73, 80, 15.0), (5.0, 24, 98, 29.9)])
def test_le_calcul_redonne_les_chiffres_connus_de_la_v11(pct, par_an, baisse, pire_jour):
    """26/11/2026 : la page Risque rejouait l'ancienne ORB v6 (Nasdaq seul, une position par jour). Elle rejoue la V11 sur le Nasdaq
    et le S&P 500 (données du courtier 2019-2026, toutes les entrées) : mêmes chiffres que l'étude du risque en % de la recherche."""
    s = risque.simuler(pct)
    assert s["trades"] == 1845 and s["jours"] == 1247 and s["unites"] == 15.0
    assert round(s["parAnPct"]) == par_an and round(s["pireBaissePct"]) == baisse and round(s["pireJourPct"], 1) == pire_jour
    assert s["reduitsPct"] == 0 and round(s["pireJourR"], 2) == 5.99
    ref = risque.charger()
    assert ref["source"].startswith("Strategy V11") and {t[1] for t in ref["trades"]} == {"nasdaq", "sp500"}


def test_la_marge_reduit_la_taille_quand_le_levier_manque():
    # range de 0,3 % du prix, levier 20, stop à 3 ranges (position 3 fois plus petite), 90 % de la marge pour 15 unités (A, B et
    # 3 D, chacune avec sa pyramide de 2) : 1,08 % de risque au plus. Avant le 25/11/2026 (v6 : 3 unités, stop à 1 range) : 1,8 %.
    assert risque.risque_possible(20, 0.003) == pytest.approx(0.0108)
    petit, grand = risque.simuler(1.0, levier=100), risque.simuler(20.0, levier=20)
    assert 0 < petit["reduitsPct"] < 10                             # à 1 % et 1:100, seuls les petits ranges coincent
    assert risque.simuler(0.25, levier=20)["reduitsPct"] < 2        # 0,25 % à 1:20 : la marge suffit presque toujours
    assert risque.simuler(1.0, levier=20)["reduitsPct"] > 10        # 1 % à 1:20 : réduit souvent
    assert grand["reduitsPct"] > 99 and grand["risqueMoyenPct"] < 5   # à 20 %, presque tous les jours sont réduits
    assert risque.simuler(20.0, levier=2000)["reduitsPct"] < 1
    assert grand["pireBaissePct"] < risque.simuler(20.0)["pireBaissePct"]


# ───────────────────────── Telegram ─────────────────────────
def faux_telegram(reponses):
    appels = []

    def appel(jeton, methode, corps):
        appels.append((methode, corps))
        return reponses[methode]
    return appel, appels


def test_parcours_telegram(dossier):
    assert telegram.verifier(dossier, "essai") == {"step": "token-missing"}
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON})
    moi = {"ok": True, "result": {"username": "etrave_bot"}}
    appel, _ = faux_telegram({"getMe": {"ok": False, "description": "Unauthorized", "status": 401}})
    with pytest.raises(pont.Refus, match="Unauthorized"):
        telegram.verifier(dossier, "essai", appel)
    appel, _ = faux_telegram({"getMe": moi, "getUpdates": {"ok": True, "result": []}})
    assert telegram.verifier(dossier, "essai", appel) == {"step": "no-chat", "bot": "etrave_bot"}
    appel, _ = faux_telegram({"getMe": moi, "getUpdates": {"ok": True, "result": [{"message": {"chat": {"id": 4242, "first_name": "Moi"}}}]}})
    assert telegram.verifier(dossier, "essai", appel) == {"step": "choose-chat", "bot": "etrave_bot", "chats": [{"id": "4242", "name": "Moi"}]}
    pont.enregistrer_connexions(dossier, {"telegram_discussion": "4242"})
    appel, appels = faux_telegram({"getMe": moi, "sendMessage": {"ok": True}})
    assert telegram.verifier(dossier, "essai", appel) == {"step": "sent", "bot": "etrave_bot"}
    assert appels[-1] == ("sendMessage", {"chat_id": "4242", "text": "essai"})


def test_telegram_injoignable_ne_cite_jamais_le_jeton():
    def ouvrir(requete, timeout):
        raise urllib.error.URLError(f"connexion refusée vers {requete.full_url}")
    with pytest.raises(telegram.Injoignable) as erreur:
        telegram.appeler(JETON, "getMe", {}, ouvrir=ouvrir)
    assert JETON not in str(erreur.value) and "***" in str(erreur.value)


# ───────────────────────── MetaTrader 5 ─────────────────────────
def test_fichier_de_demarrage_et_refus():
    assert mt5.texte_config("12345", "s3cr3t", "Courtier-Demo") == "[Common]\r\nLogin=12345\r\nPassword=s3cr3t\r\nServer=Courtier-Demo\r\nKeepPrivate=1\r\n"
    for mauvais in (("12a", "x", "Srv-1"), ("12345", "", "Srv-1"), ("12345", "a\nb", "Srv-1"), ("12345", "x", "Srv\r\n[Experts]")):
        with pytest.raises(pont.Refus) as refus:
            mt5.controler(*mauvais)
        assert "a\nb" not in str(refus.value)
    exe = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    with pytest.raises(pont.Refus, match="Windows"):
        mt5.lancer(exe, [exe], systeme="linux")
    with pytest.raises(pont.Refus, match="déjà ouvert"):
        mt5.lancer(exe, [exe], ouvert=True, systeme="win32")
    with pytest.raises(pont.Refus, match="reconnu"):
        mt5.lancer(r"C:\autre\programme.exe", [exe], systeme="win32")      # jamais un programme venu de la requête
    with pytest.raises(pont.Refus, match="introuvable"):
        mt5.lancer(None, [], systeme="win32")


def test_lancement_avec_connexion_puis_effacement():
    exe = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    lances, minuteries = [], []

    class Minuterie:
        def __init__(self, delai, action):
            minuteries.append((delai, action))

        def start(self):
            pass
    resultat = mt5.lancer(exe, [exe], ("12345", "mot de passe", "Courtier-Demo"), systeme="win32",
                          demarrer=lambda commande, cwd: lances.append(commande), minuterie=Minuterie)
    assert resultat == {"lance": True, "connexion": True}
    programme, option = lances[0]
    assert programme == exe and option.startswith("/config:")
    fichier = option[len("/config:"):]
    assert open(fichier, encoding="utf-16", newline="").read() == mt5.texte_config("12345", "mot de passe", "Courtier-Demo")
    delai, effacer = minuteries[0]
    assert delai == mt5.EFFACER_APRES_S
    effacer()
    assert not os.path.exists(fichier)                              # le mot de passe ne reste pas sur le disque


def test_terminaux_trouves():
    programme = os.path.join(r"C:\MT5 Courtier", "terminal64.exe")
    trouves = mt5.terminaux([{"terminal": r"C:\MT5 Courtier"}, {"terminal": r"C:\MT5 Courtier"}, {"terminal": r"C:\disparu"}], env={}, existe=lambda c: c == programme,
                            systeme="win32")
    assert trouves == [programme]
    assert mt5.est_ouvert(systeme="linux") is None


def test_installation_de_l_ea_et_demarrage_avec_windows(tmp_path):
    installation = tmp_path / "Program Files" / "MetaTrader 5"
    donnees = tmp_path / "AppData" / "MetaQuotes" / "Terminal" / "ABCDEF"
    installation.mkdir(parents=True)
    donnees.mkdir(parents=True)
    (donnees / "origin.txt").write_text(str(installation), encoding="utf-16")
    (installation / "metaeditor64.exe").write_bytes(b"")
    exe = str(installation / "terminal64.exe")
    env = {"APPDATA": str(tmp_path / "AppData")}
    assert mt5.dossiers_de_donnees(env) == {os.path.normcase(os.path.normpath(str(installation))): str(donnees)}
    source = os.path.join(RACINE, "robot", "Strategy-V11.mq5")

    def compilateur(commande, timeout):
        cible = commande[1][len("/compile:"):]
        open(cible[:-4] + ".ex5", "wb").close()
        open(commande[2][len("/log:"):], "w", encoding="utf-16").write("Strategy-V11.mq5 : information: compiling\nResult: 0 errors, 1 warnings\n")
    r = mt5.installer_ea(exe, [exe], source, env=env, systeme="win32", executer=compilateur)
    assert r["compile"] is True and r["journal"] == ["Result: 0 errors, 1 warnings"]
    copie = donnees / "MQL5" / "Experts" / "Etrave" / "Strategy-V11.mq5"
    assert copie.read_bytes() == open(source, "rb").read()
    rate = mt5.installer_ea(exe, [exe], source, env=env, systeme="win32", executer=lambda commande, timeout: None)
    assert rate["compile"] is False                                  # pas de nouveau programme : la compilation a échoué
    with pytest.raises(pont.Refus):
        mt5.installer_ea(exe, [exe], source, env=env, systeme="linux")
    with pytest.raises(pont.Refus):
        mt5.installer_ea(str(tmp_path / "autre.exe"), [exe], source, env=env, systeme="win32")
    assert mt5.demarrage_windows(True, r"C:\Bot-Trading", env=env, systeme="win32") is True
    assert "Etrave.bat" in open(mt5.fichier_demarrage(env, systeme="win32")).read()
    assert mt5.demarrage_windows(False, r"C:\Bot-Trading", env=env, systeme="win32") is False
    for systeme in ("win32", "darwin", "linux"):
        with pytest.raises(pont.Refus):
            mt5.demarrage_windows(True, "x", env={}, systeme=systeme)


def test_ouverture_automatique_de_metatrader(dossier):
    lances = []
    exe = os.path.join(r"C:\MT5", "terminal64.exe")
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_lancer=lambda chemin, connus, ident, ouvert: lances.append(chemin),
                             mt5_terminaux=lambda etats: [])
    assert app.ouvrir_mt5_si_demande() is False                      # option non cochée : rien
    pont.retenir_mt5(dossier, login="12345", serveur="Courtier-Demo", auto=True)
    publics = pont.reglages_publics(dossier)
    assert publics["mt5Auto"] and publics["mt5Login"] == "12345" and publics["mt5Serveur"] == "Courtier-Demo"
    assert app.ouvrir_mt5_si_demande() is False                      # aucun MetaTrader connu : rien, et pas d'erreur
    assert lances == []


# ───────────────────────── serveur local ─────────────────────────
@pytest.fixture()
def serveur(dossier):
    s = etrave.creer_serveur(dossier, 0, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [],   # jamais le vrai MetaTrader
                             appel_telegram=lambda jeton, methode, corps: {"ok": True, "result": {"username": "etrave_bot"}})
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def appeler(serveur, methode, chemin, corps=None, jeton=True, hote=None, type_contenu="application/json"):
    port = serveur.server_address[1]
    connexion = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    en_tetes = {"Host": hote or f"127.0.0.1:{port}"}
    if jeton:
        en_tetes["x-etrave-jeton"] = serveur.jeton if jeton is True else jeton
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode("utf-8")
        en_tetes["content-type"] = type_contenu
    connexion.request(methode, chemin, body=donnees, headers=en_tetes)
    reponse = connexion.getresponse()
    brut = reponse.read().decode("utf-8")
    connexion.close()
    return reponse.status, brut, reponse.headers


def test_la_page_et_ses_garde_fous(serveur):
    assert serveur.server_address[0] == "127.0.0.1"                  # jamais d'écoute sur le réseau
    code, page, en_tetes = appeler(serveur, "GET", "/", jeton=False)
    assert code == 200 and serveur.jeton in page and "<title>Étrave" in page
    assert "default-src 'none'" in en_tetes["content-security-policy"]
    assert not re.search(r"""(src|href)=["']https?://""", page)       # aucune ressource extérieure
    assert "innerHTML" not in page                                    # les données passent par textContent
    assert appeler(serveur, "GET", "/api/etat", jeton=False)[0] == 401
    assert appeler(serveur, "GET", "/api/etat", jeton="x" * 48)[0] == 401
    assert appeler(serveur, "GET", "/api/etat", hote="pirate.example:80")[0] == 403
    assert appeler(serveur, "GET", "/", jeton=False, hote="pirate.example")[0] == 403
    assert appeler(serveur, "POST", "/api/reglages", {"valeurs": {}}, type_contenu="text/plain")[0] == 415
    assert appeler(serveur, "GET", "/api/inconnu")[0] == 404
    assert appeler(serveur, "GET", "/autre")[0] == 404


def test_reglages_par_la_page_sans_fuite_de_secret(serveur, dossier):
    faux_etat(dossier)
    assert appeler(serveur, "POST", "/api/connexions", {"valeurs": {"telegram_jeton": JETON, "telegram_discussion": "4242"}})[0] == 200
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 0.5, "levier": 20}})
    assert code == 200 and json.loads(brut)["reglages"]["risquePct"] == 0.5
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 0.9}})     # AUD-05 : mot au-delà de 0,5 %
    assert code == 422 and "RISQUE" in json.loads(brut)["error"]
    assert appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 0.9}, "confirmation": "RISQUE"})[0] == 200
    for chemin in ("/api/etat", "/api/trades", "/api/risque?pct=0.9&levier=20"):
        code, brut, _ = appeler(serveur, "GET", chemin)
        assert code == 200 and JETON not in brut and "4242" not in brut and "terminal" not in json.loads(brut).get("eas", [{}])[0]
    etat = json.loads(appeler(serveur, "GET", "/api/etat")[1])
    assert etat["eas"][0]["en_marche"] and etat["reglages"]["telegramJeton"] is True and etat["mt5"]["ouvert"] is True
    assert json.loads(appeler(serveur, "POST", "/api/connexions/telegram-test", {})[1])["step"] == "sent"
    assert appeler(serveur, "GET", "/api/risque?pct=99")[0] == 400


def test_cloture_et_essai_seulement_si_l_ea_tourne(serveur, dossier):
    faux_etat(dossier, age=300)
    assert appeler(serveur, "POST", "/api/cloturer", {"symbole": "NAS100", "confirmation": "CLOTURER"})[0] == 409
    assert appeler(serveur, "POST", "/api/connexions/telegram-test-mt5", {})[0] == 409
    faux_etat(dossier, age=0, position="1")
    assert appeler(serveur, "POST", "/api/cloturer", {"symbole": "NAS100", "confirmation": "non"})[0] == 422
    assert appeler(serveur, "POST", "/api/cloturer", {"symbole": "NAS100", "confirmation": "CLOTURER"})[0] == 200
    assert pont.lire_reglages(dossier)["cloturer"].endswith(";NAS100")
    assert appeler(serveur, "POST", "/api/connexions/telegram-test-mt5", {})[0] == 200
    assert "essai_telegram" in pont.lire_reglages(dossier)
    # MetaTrader ouvert (l'EA répond) : pas de changement de compte
    code, brut, _ = appeler(serveur, "POST", "/api/mt5/lancer", {"connexion": True, "login": "1", "motDePasse": "x", "serveur": "S"})
    assert code == 422 and "x" != json.loads(brut)["error"]


# ───────────────────────── accord avec l'EA ─────────────────────────
def definition(nom):
    return float(re.search(rf"#define\s+{nom}\s+([0-9.]+)", EA).group(1))


def test_memes_bornes_des_deux_cotes():
    assert definition("RISK_MIN") == pont.RISQUE_MIN and definition("RISK_MAX") == pont.RISQUE_MAX
    assert definition("LEVER_MAX") == pont.LEVIER_MAX
    assert definition("MARGIN_USE") == risque.PART_MARGE
    # Unités de marge : la même formule que Setup() dans l'EA, avec ses constantes (A, B, C coupée, D avec pyramide)
    const = lambda nom: re.search(rf"^const \S+\s+{nom}\s*=\s*([\w.]+);", EA, re.M).group(1)
    pyr, nd = float(const("InpPyrSize")), int(const("InpDCount"))
    assert const("InpUseB") == "true" and const("InpUseC") == "false" and const("InpUseD") == "true" and const("InpDPyr") == "true"
    assert "units += MathMin(InpDCount, D_MAX) * (1.0 + ((InpUsePyr && InpDPyr) ? InpPyrSize : 0.0));" in EA
    assert risque.PYRAMIDE == pyr and risque.ENTREES_D == nd
    assert risque.STOP_RANGES == float(const("InpStopMult")) == 3.0     # taille de la V10 : solde × risque ÷ (3 × range)
    assert "double perLot = (dist > 0 && ts > 0) ? dist * gStopMult / ts * tv : 0;" in EA and "double dist = gOrH - gOrL;" in EA
    assert "s.unites / (0.9 * s.stopRanges * s.rangeMedianPct / 100)" in open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert risque.UNITES == (1 + pyr) + (1 + pyr) + nd * (1 + pyr) == 15.0
    assert definition("UI_PERIOD") * 5 < pont.EA_MUET_S              # l'EA écrit bien plus souvent que le délai de silence


def test_memes_noms_de_cles_des_deux_cotes(dossier):
    ecrites_par_ea = set(re.findall(r'K[vd]\(h, "([a-z_0-9]+)"', EA))
    assert set(pont.NOMBRES) | set(pont.DRAPEAUX) <= ecrites_par_ea
    assert {"symbole", "instrument", "compte_type", "compte_serveur", "compte_login", "devise", "heure_ny", "filtres", "jour",
            "telegram_envoi", "telegram_essai", "terminal", "risque_source",
            "compte_autorise", "ea_build"} <= ecrites_par_ea                      # AUD-01, AUD-22
    # tout ce que l'interface écrit, l'EA sait le lire
    pont.regler(dossier, {"risquePct": 0.5, "levier": 20, "nasdaq": True})
    faux_etat(dossier, "NAS100", compte_type="reel", compte_login="87654321")      # AUD-01 : reel_autorise
    pont.autoriser_compte_reel(dossier, "87654321", "REEL", pont.lire_etats(dossier))
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON, "telegram_discussion": "4242"})
    pont.demander_essai_mt5(dossier)
    pont.demander_cloture(dossier, "NAS100", "CLOTURER")
    lues_par_ea = set(re.findall(r'k == "([a-z_]+)"', EA)) | set(pont.INSTRUMENTS)     # les cases : comparées à gInstr
    ecrites = {"cloturer_" if c.startswith("cloturer_") else c for c in pont.lire_reglages(dossier)} - {"version"}
    assert ecrites <= lues_par_ea
    assert 'k == "cloturer_" + gSymFile' in EA                                         # la clé de clôture propre au symbole
    assert list(pont.INSTRUMENTS) == ["nasdaq", "sp500"] and "k == gInstr" in EA
    assert 'return "nasdaq";' in EA and 'return "sp500";' in EA
    assert "reglages.txt" in EA and 'UI_DIR      "Etrave\\\\"' in EA
    assert pont.SOUS_DOSSIER == "Etrave" and pont.FICHIER_REGLAGES == "reglages.txt"


def test_journal_des_trades_meme_nombre_de_colonnes():
    for fonction in ("AppendTrade", "AppendLegTrade"):       # X-20 : les lignes passent par TradesWrite
        ecriture = re.search(rf"void {fonction}\(.*?TradesWrite\((.*?)\);\n  }}", EA, re.S).group(1)
        assert ecriture.count('";"') + 1 == len(pont.COLONNES_TRADE), fonction


def sans_textes(source):
    """Le code MQL5 sans ses commentaires, avec des chaînes et des caractères vidés (une chaîne peut contenir « // »)."""
    sortie, i, n = [], 0, len(source)
    while i < n:
        c = source[i]
        if c == "/" and source[i:i + 2] == "//":
            while i < n and source[i] != "\n":
                i += 1
        elif c in "\"'":
            j = i + 1
            while j < n and source[j] != c:
                j += 2 if source[j] == "\\" else 1
            sortie.append(c + c)
            i = j + 1
        else:
            sortie.append(c)
            i += 1
    return "".join(sortie)


def test_l_ea_reste_lisible_par_metatrader():
    """Pas un test de compilation (impossible ici) : seulement les fautes que l'on peut voir sans compilateur."""
    brut = open(os.path.join(RACINE, "robot", "Strategy-V11.mq5"), "rb").read()
    assert brut.startswith(b"\xef\xbb\xbf")                           # UTF-8 signé : MetaEditor lit bien les accents
    code = sans_textes(EA)
    for ouvrant, fermant in ("{}", "()", "[]"):
        assert code.count(ouvrant) == code.count(fermant), f"{ouvrant} et {fermant} ne s'équilibrent pas"
    appelees = set(re.findall(r"\b(ReadSettings|WriteState|FlushNotifs|UiClose|CheckClock|AppendTrade|MarginPerLot|InstrumentOf|SafeName)\(", code))
    for fonction in appelees:
        assert re.search(rf"^(void|double|string|bool)\s+{fonction}\(", code, re.M), f"{fonction} appelée mais pas définie"
    assert "void OnTimer()" in code and "EventSetTimer(UI_PERIOD)" in code and "EventKillTimer()" in code
    # les messages lents partent après les ordres : plus aucun envoi direct depuis Notify
    notify = re.search(r"void Notify\(string msg, bool tg = false\)(.*?)\n  }", EA, re.S).group(1)   # signature du 27/11/2026
    assert "SendTelegram" not in notify and "SendWhatsApp" not in notify
    assert EA.index("CheckEntries();\n   SyncPosition();") < EA.index("   FlushNotifs();\n   Panel();")


def test_les_ordres_d_entree_sont_poses_chez_le_courtier():
    """Depuis l'EA 6.10 : Buy Stop / Sell Stop posés chez le courtier, l'autre supprimé dès qu'une position existe."""
    code = sans_textes(EA)
    assert "trade.BuyStop(" in code and "trade.SellStop(" in code
    for fonction in ("PlaceStop", "DeletePendings", "CancelDay", "HasPending", "CloseOpposite"):
        assert re.search(rf"^(void|bool)\s+{fonction}\(", code, re.M), f"{fonction} manquante"
    sync = re.search(r"void SyncPosition\(\)(.*?)\n  }\n", code, re.S).group(1)
    assert "DeletePendings()" in sync                                     # le premier exécuté annule l'autre
    entrees = re.search(r"void CheckEntries\(\)(.*?)\n  }\n", code, re.S).group(1)
    assert "!gSrvL && ask >= gOrH" in entrees and "!gSrvS && bid <= gOrL" in entrees   # pas d'ordre au marché en double


def test_jours_feries_meme_regle_dans_l_ea_et_le_script():
    """Sortie avancée les jours fériés américains et les demi-séances : même heure et mêmes jours des deux côtés.
    (Les règles du calendrier ont été contrôlées à part sur les fermetures 2022-2025 de la Bourse de New York.)"""
    pine = open(os.path.join(RACINE, "robot", "Strategy-V11.pine"), encoding="utf-8").read()
    assert 'InpFlatShort = "12:45"' in EA and 'flatShortS = "1240-1600"' in pine          # bougie de 12:40 = clôture à 12:45
    assert "NYMin(ny) >= FlatMin(ny)" in EA and "NYMin(ToNY(r[0].time)) < FlatMin(ToNY(r[0].time))" in EA
    assert "shortDay and not na(time(timeframe.period, flatShortS, TZ_NY))" in pine
    # les onze fériés et les trois demi-séances, dans le même ordre
    for code in (EA, pine):
        corps = sans_textes(code)
        assert corps.count("(") == corps.count(")") and corps.count("[") == corps.count("]")
    assert EA.count("Observed(") == 6 and pine.count("observed(") == 6                       # 5 dates chômées + la définition
    assert "NthDow(y, 11, 4, 4)" in EA and "nthDow(y, 11, dayofweek.thursday, 4)" in pine      # Thanksgiving
    assert "MakeDate(y, 12, 24)" in EA and "y * 10000 + 1224" in pine                          # veille de Noël
    assert "(h + l - 7 * m + 114) % 31 + 1" in EA and "(h + l - 7 * m + 114) % 31 + 1" in pine  # Pâques


# ───────────────────────── revue cloud du 25/11/2026 ─────────────────────────
PAGE = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()


def test_les_entrees_b_et_d_comptent_dans_la_vue_d_ensemble(dossier):
    """A sortie, B ou D encore ouverte : la page disait « Aucun » trade, et la clôture parlait d'annuler des ordres."""
    faux_etat(dossier, position="0", jambes="1", v8_resultat="-180.00")
    e = pont.lire_etats(dossier)[0]
    assert e["v8_resultat"] == -180.0 and e["jambes"] == 1
    assert "const open = running().filter((e) => e.position || e.jambes > 0);" in PAGE
    assert "(e.pos_resultat || 0) + (e.v8_resultat || 0)" in PAGE
    fermeture = PAGE[PAGE.index("function askClose(e)"):PAGE.index("function niceTicks")]
    assert "legs ? `L’EA va fermer au marché" in fermeture and "entrée${n > 1 ? 's' : ''} B ou D" in fermeture


def test_lots_fixes_signales_par_la_page(dossier):
    """En lots fixes, la page disait le nouveau risque appliqué alors que l'EA ne s'en sert pas."""
    faux_etat(dossier, lots_fixes="0.10")
    assert pont.lire_etats(dossier)[0]["lots_fixes"] == 0.1
    assert "const fixedLots = () =>" in PAGE and "x.lots_fixes > 0" in PAGE
    assert PAGE.count("fixedLots()") >= 5            # tuile, état de la page Risque, tuile « Sur ton solde », message d'enregistrement


def test_meme_seuil_de_confirmation_du_risque_dans_la_page_et_le_serveur(dossier):
    """La page comparait au risque de l'EA, le serveur au fichier : un risque > 1 % pouvait être refusé sans dialogue."""
    assert "const savedRisk = () => (state && state.reglages.risquePct != null ? state.reglages.risquePct : 0);" in PAGE
    assert "draft.risque > bounds().risqueAConfirmer && draft.risque > savedRisk()" in PAGE
    # le serveur, sans risque enregistré : tout risque > 0,5 % (AUD-05, avant 1 %) demande le mot, même si l'EA tourne plus haut
    faux_etat(dossier, risque_pct="1.0000")
    with pytest.raises(pont.Refus, match="RISQUE"):
        pont.regler(dossier, {"risquePct": 0.8})
    assert pont.regler(dossier, {"risquePct": 0.8}, "RISQUE") == ["risque_pct"]


def test_les_cases_de_la_page_sont_celles_du_serveur():
    cases = dict(re.findall(r"(\w+): '([^']+)'", PAGE[PAGE.index("const INSTRUMENTS = {"):].split("\n")[0]))
    assert list(cases) == list(pont.INSTRUMENTS) and cases["sp500"] == "S&P 500"


def test_fichier_de_connexion_oublie_efface_au_demarrage(tmp_path):
    """Fenêtre d'Étrave fermée dans la minute d'un lancement : le fichier avec le mot de passe restait dans %TEMP%."""
    vieux, recent, autre = tmp_path / "etrave-ab12.ini", tmp_path / "etrave-cd34.ini", tmp_path / "autre.ini"
    for f in (vieux, recent, autre):
        f.write_text("[Common]\nPassword=secret\n", encoding="utf-16")
    maintenant = time.time()
    os.utime(vieux, (maintenant - 3600, maintenant - 3600))
    os.utime(autre, (maintenant - 3600, maintenant - 3600))
    assert mt5.effacer_connexions_oubliees(str(tmp_path), maintenant) == 1
    assert not vieux.exists() and recent.exists() and autre.exists()   # le fichier récent sert peut-être encore à MetaTrader
    assert "mt5.effacer_connexions_oubliees()" in open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()


def test_la_frise_de_la_seance_suit_les_heures_de_l_ea():
    """La frise d'Étrave dessine les fenêtres des règles : mêmes heures que l'EA, et la sortie du jour vient de l'EA."""
    const = lambda nom: re.search(rf"^const \S+\s+{nom}\s*=\s*\"?([\w:.]+)\"?;", EA, re.M).group(1)
    regles = dict(re.findall(r"(\w+): '(\d\d:\d\d)'", PAGE[PAGE.index("const REGLES_NY = {"):].split("\n")[0]))
    hm = lambda t: int(t[:2]) * 60 + int(t[3:])
    txt = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    assert regles["elan"] == const("InpPre") and regles["range"] == const("InpOR")
    assert regles["cassure"] == txt(hm(const("InpOR")) + 5)                                    # bougie M5 du range
    assert regles["finOrdres"] == txt(hm(const("InpOR")) + 5 * (1 + int(const("InpLiveBars"))))
    assert regles["debutD"] == txt(hm(const("InpOR")) + 10)                                    # D1 guettée à la clôture de 9:35
    assert regles["finD"] == txt(hm(const("InpOR")) + 5 * (1 + int(const("InpDCount"))) + int(const("InpDValid")))
    assert regles["finB"] == const("InpBEnd") and regles["sortie"] == const("InpFlat") and regles["sortieCourte"] == const("InpFlatShort")
    assert 'Kv(h, "sortie_ny", StringFormat("%02d:%02d", flatNy / 60, flatNy % 60));' in EA
    assert "(live[0] && live[0].sortie_ny) || REGLES_NY.sortie" in PAGE


# ───────────────────────── audit du 25/11/2026 (ET-05 à ET-15) ─────────────────────────
PAGE = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()


def test_une_seule_etrave_par_port_sous_windows():
    """ET-05 : sous Windows, SO_REUSEADDR laissait une deuxième Étrave écouter sur le même port (jetons mélangés)."""
    assert issubclass(etrave.Serveur, etrave.ThreadingHTTPServer)
    assert etrave.Serveur.allow_reuse_address == (not sys.platform.startswith("win"))
    source = open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()
    assert "SO_EXCLUSIVEADDRUSE" in source and 'serveur = Serveur(("127.0.0.1", port), Requete)' in source


def test_la_page_n_impose_pas_de_risque_par_defaut():
    """ET-06 : sans réglage ni EA vu, la page partait de 0,5 % et l'enregistrait avec le levier."""
    assert "const RISQUE_EA = 0.25;" in PAGE and ": 0.5);" not in PAGE
    assert re.search(r"InpRiskPct\s*=\s*0\.25;", EA)                          # la valeur de l'EA
    assert "if (draft.risqueTouche && (Math.abs(draft.risque - currentRisk())" in PAGE
    assert PAGE.count("draft.risqueTouche = true;") == 3                      # champ, curseur, boutons


def test_tasklist_illisible_ne_casse_pas_la_page():
    """ET-07 : la sortie de tasklist n'est pas en UTF-8 sur un Windows français."""
    vus = {}

    def executer(commande, **options):
        vus.update(options)
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
    assert mt5.est_ouvert(systeme="win32", executer=executer) is None
    assert vus.get("errors") == "replace"


def test_demarrage_avec_windows_chemin_accentue(tmp_path):
    """ET-08 : le fichier de démarrage est en UTF-8 ; cmd.exe doit passer en UTF-8 avant de lire le chemin."""
    env = {"APPDATA": str(tmp_path)}
    mt5.demarrage_windows(True, r"C:\Users\Jérôme\Bot-Trading\etrave", env=env, systeme="win32")
    texte = open(mt5.fichier_demarrage(env, systeme="win32"), encoding="utf-8").read()
    assert texte.index("chcp 65001") < texte.index("start ") and "Jérôme" in texte


def test_les_motifs_refusent_un_retour_a_la_ligne(dossier):
    """ET-09 : avec match, « $ » acceptait un « \\n » final (clé de réglage coupée en deux, dossier « 2027-T1\\n »)."""
    with pytest.raises(pont.Refus):
        pont.demander_cloture(dossier, "NAS100\n", "CLOTURER")
    with pytest.raises(etrave.Erreur):
        etrave.Application(dossier).traiter("POST", "/api/exports", {}, {"trimestre": "2027-T1\n"})
    assert not etrave.TRIMESTRE.fullmatch("2027-T1\n") and etrave.TRIMESTRE.fullmatch("2027-T1")
    with pytest.raises(pont.Refus):
        mt5.controler("123456\n7", "x", "TradinGlobal-Real")
    for nom in ("etrave.py", "pont.py", "mt5.py"):
        assert not re.search(r"[A-Z_]+\.match\(", open(os.path.join(RACINE, "etrave", nom), encoding="utf-8").read()), nom


def test_le_rafraichissement_ne_reecrit_pas_un_champ_en_saisie():
    """ET-13 : « 0. » devenait « 0 » au rafraîchissement, et la suite de la frappe donnait « 05 » (5 %)."""
    assert "const typing = (id) => fromInput === 'poll' && document.activeElement === $(id);" in PAGE
    assert "if (fromInput !== 'number' && !typing('risk-input'))" in PAGE and "if (fromInput !== 'lever' && !typing('lever-input'))" in PAGE


def test_textes_de_la_page():
    """ET-14 : pas de « · » pour joindre des textes générés par la page (règle de la page) ; l'export se fait 3 jours après."""
    script = PAGE[PAGE.index("<script"):]
    assert "` · " not in script and " · levier" not in script
    assert "au premier démarrage qui suit la fin du trimestre" not in PAGE and "trois jours après la fin du trimestre" in PAGE


def test_le_lanceur_essaie_python_avant_de_s_en_servir():
    """ET-15 : « python » peut être le raccourci du Microsoft Store, qui ne lance rien."""
    bat = open(os.path.join(RACINE, "etrave", "Etrave.bat"), encoding="utf-8").read()
    assert 'if defined PY %PY% -c "import sys" >nul 2>nul || set PY=' in bat
    assert bat.index("|| set PY=") < bat.index("if not defined PY (")


# ───────────────────────── tout en un double-clic (26/11/2026) ─────────────────────────
def _metatrader_mac(tmp_path):
    installation = tmp_path / "drive_c" / "Program Files" / "MetaTrader 5"
    installation.mkdir(parents=True)
    (installation / "metaeditor64.exe").write_bytes(b"")
    return str(installation / "terminal64.exe")


def test_mac_lancement_avec_le_profil_et_le_mac_eveille(tmp_path):
    """Mac : MetaTrader s'ouvre par le Wine de MetaQuotes sur le profil « Etrave-demo » (deux graphiques, la V11 sur chacun),
    trading automatique actif, dans une session à part (fermer le Terminal ne le ferme pas), et caffeinate le suit."""
    exe = _metatrader_mac(tmp_path)
    lances = []

    class Processus:
        pid = 4242

    def demarrer(commande, **options):
        lances.append((commande, options))
        if commande[0] == mt5.WINE:
            fichier = mt5.os.path.join("/", commande[-1][len("/config:Z:"):].replace("\\", "/").lstrip("/"))
            lances[-1] = (commande, options, open(fichier, encoding="utf-16", newline="").read())
        return Processus()
    r = mt5.lancer(exe, [exe], systeme="darwin", demarrer=demarrer, minuterie=lambda d, a: type("M", (), {"start": lambda s: None, "daemon": True})())
    assert r == {"lance": True, "connexion": False, "profil": "Etrave-demo"}
    (commande, options, config), (caf, options_caf) = lances
    assert commande[:2] == [mt5.WINE, r"C:\Program Files\MetaTrader 5\terminal64.exe"] or commande[0] == mt5.WINE
    assert "[Common]" not in config and "ProfileLast=Etrave-demo" in config and "AllowLiveTrading=1" in config
    assert options["start_new_session"] and options["env"]["WINEPREFIX"] == mt5.PREFIXE_WINE
    assert caf == ["caffeinate", "-i", "-w", "4242"] and options_caf["start_new_session"]
    profil = tmp_path / "drive_c" / "Program Files" / "MetaTrader 5" / "MQL5" / "Profiles" / "Charts" / "Etrave-demo"
    for nom in ("chart01.chr", "chart02.chr"):
        assert (profil / nom).read_bytes() == open(os.path.join(mt5.PROFIL_SOURCE, nom), "rb").read()


def test_profil_du_depot_lots_fixes_a_zero_et_v11_sur_les_deux_graphiques():
    for nom, symbole in (("chart01.chr", "NDX100"), ("chart02.chr", "SPX500")):
        texte = open(os.path.join(mt5.PROFIL_SOURCE, nom), encoding="utf-16").read()
        assert f"symbol={symbole}" in texte and "path=Experts\\Etrave\\Strategy-V11.ex5" in texte and "InpFixedLots=0.0" in texte


def test_mac_installation_de_l_ea_et_du_profil(tmp_path):
    exe = _metatrader_mac(tmp_path)
    source = os.path.join(RACINE, "robot", "Strategy-V11.mq5")
    vus = []

    def compilateur(commande, **options):
        vus.append((commande, options))
        installation = options["cwd"]
        open(os.path.join(installation, "MQL5", "Experts", "Etrave", "Strategy-V11.ex5"), "wb").close()
        open(os.path.join(installation, "MQL5", "Experts", "Etrave", "Strategy-V11.log"), "w", encoding="utf-16").write("Result: 0 errors, 0 warnings\n")
    r = mt5.installer_ea(exe, [exe], source, systeme="darwin", executer=compilateur, ouvert=False)
    assert r["compile"] is True and r["profil"] and r["journal"] == ["Result: 0 errors, 0 warnings"]
    commande, options = vus[0]
    assert commande[0] == mt5.WINE and commande[2] == "/compile:MQL5\\Experts\\Etrave\\Strategy-V11.mq5"
    assert mt5.ea_a_jour(os.path.dirname(exe), source)
    assert mt5.installer_ea(exe, [exe], source, systeme="darwin", executer=compilateur, ouvert=True)["profil"] is None   # MetaTrader ouvert


def test_mac_lancement_a_l_ouverture_de_session(tmp_path):
    env = {"HOME": str(tmp_path)}
    assert mt5.demarrage_windows(True, "/Users/x/Bot & Trading/etrave", env=env, systeme="darwin") is True
    texte = open(mt5.fichier_demarrage(env, systeme="darwin"), encoding="utf-8").read()
    assert "<string>/Users/x/Bot &amp; Trading/etrave/Etrave.command</string><string>--session</string>" in texte
    assert mt5.fichier_demarrage(env, systeme="darwin").startswith(str(tmp_path))
    assert mt5.demarrage_windows(False, "x", env=env, systeme="darwin") is False


def test_dossier_commun_sur_mac_celui_du_wine_de_metatrader():
    """Correctif du 26/11/2026 : sur Mac, l'EA écrit dans le dossier commun du Wine de MetaTrader, pas dans ~/.etrave."""
    env = {"HOME": "/Users/x", "USER": "x"}
    attendu = "/Users/x/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/x/AppData/Roaming/MetaQuotes/Terminal/Common/Files/Etrave"
    assert pont.dossier_commun(env, systeme="darwin", existe=lambda d: True) == attendu
    assert pont.dossier_commun(env, systeme="darwin", existe=lambda d: False) == "/Users/x/.etrave"
    assert pont.dossier_commun({"APPDATA": r"C:\A", "HOME": "/Users/x"}, systeme="win32").endswith("Etrave")


def test_fermer_metatrader_proprement_et_jamais_pendant_un_trade(serveur, dossier):
    vus = []
    assert mt5.fermer(systeme="darwin", executer=lambda c, **o: vus.append(c)) == {"ferme": True}
    assert mt5.fermer(systeme="win32", executer=lambda c, **o: vus.append(c)) == {"ferme": True}
    assert vus[0][1:] == ["taskkill", "/IM", "terminal64.exe"] and vus[1] == ["taskkill", "/IM", "terminal64.exe"]   # jamais /F
    fermes = []
    serveur.application._mt5_fermer = lambda: fermes.append(1) or {"ferme": True}
    faux_etat(dossier, age=0, position="1")
    code, brut, _ = appeler(serveur, "POST", "/api/mt5/fermer", {})
    assert code == 409 and "Clôturer" in json.loads(brut)["error"] and fermes == []
    faux_etat(dossier, age=0, position="0")
    assert appeler(serveur, "POST", "/api/mt5/fermer", {})[0] == 200 and fermes == [1]


def test_double_clic_ouvre_metatrader_et_met_l_ea_a_jour(dossier, monkeypatch):
    lances, installes = [], []
    exe = "/MT5/terminal64.exe"
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [exe],
                             mt5_lancer=lambda chemin, connus, ident, ouvert: lances.append(chemin),
                             mt5_installer=lambda chemin, connus, source, ouvert=None: installes.append(ouvert) or {"compile": True})
    monkeypatch.setattr(mt5, "donnees_de", lambda chemin, *a, **k: "/MT5")
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: False)
    monkeypatch.setattr(mt5, "est_mac", lambda systeme=None: False)
    assert app.ouvrir_mt5_si_demande() is False and lances == []                # sans la case ni le double-clic : rien
    assert app.ouvrir_mt5_si_demande(forcer=True) is False and lances == []    # Windows, compte jamais connecté : la page d'abord
    pont.retenir_mt5(dossier, login="12345", serveur="Courtier-Demo")
    assert app.ouvrir_mt5_si_demande(forcer=True) is True and lances == [exe] and installes == [False]
    monkeypatch.setattr(mt5, "est_mac", lambda systeme=None: True)
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: True)
    assert app.ouvrir_mt5_si_demande(forcer=True) is True and installes == [False]   # EA à jour : pas de recompilation


def test_lanceurs_double_clic():
    commande = os.path.join(RACINE, "etrave", "Etrave.command")
    assert os.access(commande, os.X_OK) and b"\r" not in open(commande, "rb").read()
    texte = open(commande, encoding="utf-8").read()
    assert 'set -- --tout "$@"' in texte and 'exec "$PY" etrave/etrave.py "$@"' in texte
    assert "etrave.py --tout %*" in open(os.path.join(RACINE, "etrave", "Etrave.bat"), encoding="utf-8").read()
    assert "*.command text eol=lf" in open(os.path.join(RACINE, ".gitattributes"), encoding="utf-8").read()


def test_se_connecter_installe_d_abord_l_ea_sur_un_vps_vierge(dossier, monkeypatch):
    ordre = []
    exe = r"C:\MT5\terminal64.exe"
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [exe],
                             mt5_installer=lambda chemin, connus, source, ouvert=None: ordre.append(("installer", ouvert)) or {"compile": True},
                             mt5_lancer=lambda chemin, connus, ident, ouvert: ordre.append(("lancer", ident[0])) or {"lance": True, "connexion": True})
    monkeypatch.setattr(mt5, "donnees_de", lambda chemin, *a, **k: r"C:\Data")
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: False)
    app.traiter("POST", "/api/mt5/lancer", {}, {"connexion": True, "login": "12345", "motDePasse": "x", "serveur": "Courtier-Demo"})
    assert ordre == [("installer", False), ("lancer", "12345")]


# ───────────────────────── audit du 26/11/2026 (AUD-01 à AUD-27) ─────────────────────────
def test_range_median_pris_sur_la_largeur_du_range():
    """AUD-15 : rangeMedianPct prenait le R du jour (t[2]) au lieu du range rapporté au prix (t[3]) : la page affichait
    « il faudrait environ 1:0 ». Médiane des deux marchés de reference.json : environ 0,26 % du prix."""
    s = risque.simuler(0.25)
    attendu = 100.0 * sorted(t[3] for t in risque.charger()["trades"])[len(risque.charger()["trades"]) // 2]
    assert s["rangeMedianPct"] == pytest.approx(attendu) and s["rangeMedianPct"] == pytest.approx(0.26, abs=0.005)


def _json_strict(brut):
    """Le JSON tel qu'un navigateur le lit : NaN et Infinity n'en font pas partie (json.loads de Python les accepte)."""
    def refuse(constante):
        raise ValueError(f"{constante} n'est pas du JSON")
    return json.loads(brut, parse_constant=refuse)


def test_valeurs_non_finies_jamais_dans_le_json(serveur, dossier):
    """AUD-16 : « solde=nan » dans un état passait en NaN dans /api/etat, que le navigateur ne sait pas lire (page figée sur
    « Interface arrêtée ») ; « inf » dans la colonne de sortie du journal des trades faisait planter /api/trades (int(inf))."""
    faux_etat(dossier, solde="nan", capital="inf", pos_r="-inf", marge_libre="1e999")
    with open(os.path.join(dossier, "trades-NAS100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("inf;2026-11-13;09:52;NAS100;-1;1.20;-1.0200;-51.00;10051.00;Stop;0;USD\r\n")
        f.write("1763322600;2026-11-16;15:50;NAS100;1;1.50;nan;65.20;10000.00;Fin de journée;1;USD\r\n")
        f.write("1763322700;2026-11-16;15:51;NAS100;1;1.50;1.0;NaN;10000.00;Fin de journée;1;USD\r\n")
    for chemin in ("/api/etat", "/api/trades"):
        code, brut, _ = appeler(serveur, "GET", chemin)
        assert code == 200 and "NaN" not in brut and "Infinity" not in brut, chemin
        _json_strict(brut)
    e = pont.lire_etats(dossier)[0]
    assert e["solde"] is None and e["capital"] is None and e["pos_r"] is None and e["marge_libre"] is None
    trades = pont.lire_trades(dossier)
    assert len(trades) == 1 and trades[0]["r"] is None                     # sortie infinie et résultat illisible : lignes écartées
    for texte in ("nan", "inf", "-inf", "1e999", "NaN", "Infinity"):
        assert pont._nombre(texte) is None
    assert "allow_nan=False" in open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()


def test_plafond_du_risque_a_20_pct(serveur, dossier):
    """AUD-05 : mot RISQUE au-delà de 0,5 % ; plafond de 1 % après l'audit, remonté à 20 % par décision de l'utilisateur du
    27/11/2026 (« pour des tests », tous comptes). Un risque enregistré au-dessus du plafond est montré ramené au plafond, comme
    l'EA l'applique, et la valeur enregistrée reste visible pour que la page l'explique."""
    assert pont.RISQUE_MAX == 20.0 and pont.RISQUE_A_CONFIRMER == 0.5
    pont.ecrire_cles(os.path.join(dossier, pont.FICHIER_REGLAGES), {"risque_pct": "2.5"})
    r = pont.reglages_publics(dossier)
    assert r["risquePct"] == 2.5 and r["risqueEnregistre"] == 2.5        # 2,5 % n'est plus ramené à 1 %
    pont.ecrire_cles(os.path.join(dossier, pont.FICHIER_REGLAGES), {"risque_pct": "35"})
    r = pont.reglages_publics(dossier)
    assert r["risquePct"] == 20.0 and r["risqueEnregistre"] == 35.0      # au-dessus du plafond : vaut le plafond
    assert r["bornes"]["risqueMax"] == 20.0 and r["bornes"]["risqueAConfirmer"] == 0.5
    assert pont.regler(dossier, {"risquePct": 10}) == ["risque_pct"]     # depuis 35 % (vu 20 %), baisser ne demande rien
    pont.ecrire_cles(os.path.join(dossier, pont.FICHIER_REGLAGES), {"risque_pct": "0.01"})
    assert pont.reglages_publics(dossier)["risquePct"] is None           # sous le minimum : ignorée, comme dans l'EA
    for pct in ("0.05", "1", "1.5", "20"):
        assert appeler(serveur, "GET", f"/api/risque?pct={pct}")[0] == 200
    for pct in ("20.01", "0", "-1", "nan", "inf", "abc"):
        assert appeler(serveur, "GET", f"/api/risque?pct={pct}")[0] == 400
    # la page : mêmes bornes de repli que le serveur, des boutons jusqu'au plafond et pas au-delà, et la phrase du plafond
    repli = re.search(r"risqueMin: ([\d.]+), risqueMax: ([\d.]+), risqueAConfirmer: ([\d.]+)", PAGE).groups()
    assert tuple(map(float, repli)) == (pont.RISQUE_MIN, pont.RISQUE_MAX, pont.RISQUE_A_CONFIRMER)
    boutons = [float(v) for v in re.search(r"const RISK_PRESETS = \[([^\]]+)\]", PAGE).group(1).split(",")]
    assert max(boutons) == pont.RISQUE_MAX and min(boutons) >= pont.RISQUE_MIN and boutons == sorted(boutons)
    assert 'id="risk-input" min="0.05" max="20"' in PAGE
    assert "ramené au plafond de" in PAGE and "AUD-05" in PAGE


def test_risque_a_20_pct_par_la_page(serveur, dossier):
    """Décision de l'utilisateur du 27/11/2026 : 20 % se règle depuis la page, avec le mot RISQUE ; au-delà, refusé ; deux
    envois identiques (double clic) laissent la même valeur."""
    faux_etat(dossier)
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 20}})
    assert code == 422 and "RISQUE" in json.loads(brut)["error"]
    for _ in range(2):
        code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 20}, "confirmation": "RISQUE"})
        assert code == 200 and json.loads(brut)["reglages"]["risquePct"] == 20.0
    assert pont.lire_reglages(dossier)["risque_pct"] == "20"
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 20.5}, "confirmation": "RISQUE"})
    assert code == 422 and "20 %" in json.loads(brut)["error"]
    assert pont.lire_reglages(dossier)["risque_pct"] == "20"


def test_compte_reel_autorise_seulement_avec_le_mot_reel(serveur, dossier):
    """AUD-01 : l'EA ne trade plus sur un compte réel sans `reel_autorise=<numéro>` dans reglages.txt. Étrave l'écrit seulement
    avec le mot REEL, pour le numéro d'un EA en marche sur un compte réel ; « retirer » efface la clé. Numéros inventés."""
    faux_etat(dossier, "NAS100", compte_type="reel", compte_login="87654321", compte_autorise="0")
    faux_etat(dossier, "US500", instrument="sp500", compte_type="demo", compte_login="12345678")
    nas, us = pont.lire_etats(dossier)
    assert nas["compte_autorise"] is False and us.get("compte_autorise") is None    # clé absente (EA plus ancien) : ni oui ni non
    autoriser = lambda corps: appeler(serveur, "POST", "/api/compte/autoriser", corps)
    for corps in ({"login": "87654321", "confirmation": "non"}, {"login": "87654321"},
                  {"login": "12345678", "confirmation": "REEL"},                   # compte démo : rien à autoriser
                  {"login": "11112222", "confirmation": "REEL"},                   # aucun EA sur ce compte
                  {"login": "87654321\n", "confirmation": "REEL"}, {"login": "8765 4321", "confirmation": "REEL"},
                  {"login": "1" * 21, "confirmation": "REEL"}, {"login": 87654321, "confirmation": "REEL"},
                  {"login": "", "confirmation": "REEL"}, {"login": None, "confirmation": "REEL"}):
        code, brut, _ = autoriser(corps)
        assert code == 422, corps
    assert "reel_autorise" not in pont.lire_reglages(dossier)
    code, brut, _ = autoriser({"login": "87654321", "confirmation": "REEL"})
    assert code == 200 and pont.lire_reglages(dossier)["reel_autorise"] == "87654321"
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON, "telegram_discussion": "4242"})
    publics = pont.reglages_publics(dossier)
    assert publics["reelAutorise"] == "87654321" and JETON not in json.dumps(publics) and "4242" not in json.dumps(publics)
    assert autoriser({"retirer": True})[0] == 200 and "reel_autorise" not in pont.lire_reglages(dossier)
    assert pont.reglages_publics(dossier)["reelAutorise"] == ""
    faux_etat(dossier, "NAS100", age=300, compte_type="reel", compte_login="87654321", compte_autorise="0")
    assert autoriser({"login": "87654321", "confirmation": "REEL"})[0] == 422        # EA arrêté : on ne sait pas sur quel compte
    # la page : bandeau, confirmation par le mot REEL, ligne « Compte réel autorisé » et « Retirer l'autorisation »
    assert "le robot ne prend aucun trade tant que tu ne l’as pas autorisé" in PAGE and "e.compte_autorise === false" in PAGE
    assert "'/api/compte/autoriser'" in PAGE and "mot: 'REEL'" in PAGE
    assert "Compte réel autorisé" in PAGE and "Retirer l’autorisation" in PAGE and "AUD-01" in PAGE


def test_arret_d_urgence(serveur, dossier):
    """AUD-10 : un geste pour tout arrêter. Avec le mot ARRET : les deux marchés décochés (plus de nouveau trade) et la clôture
    demandée à chaque EA en marche ; un EA arrêté est signalé (ses positions se ferment dans MetaTrader). Le réarmement = recocher."""
    faux_etat(dossier, "NAS100", position="1")
    faux_etat(dossier, "US500", age=300, instrument="sp500", attente="1")
    pont.regler(dossier, {"nasdaq": True, "sp500": True})
    for corps in ({}, {"confirmation": "arret"}, {"confirmation": "CLOTURER"}):
        assert appeler(serveur, "POST", "/api/arret-urgence", corps)[0] == 422
    assert pont.reglages_publics(dossier)["instruments"] == {"nasdaq": True, "sp500": True}   # rien sans le mot
    code, brut, _ = appeler(serveur, "POST", "/api/arret-urgence", {"confirmation": "ARRET"})
    r = json.loads(brut)
    assert code == 200 and r["fermes"] == ["NAS100"] and r["sansEa"] == ["US500"] and "MetaTrader" in r["message"]
    cles = pont.lire_reglages(dossier)
    assert cles["nasdaq"] == "0" and cles["sp500"] == "0" and cles["cloturer_NAS100"].endswith(";NAS100") and "cloturer_US500" not in cles
    assert pont.reglages_publics(dossier)["instruments"] == {"nasdaq": False, "sp500": False}
    pont.regler(dossier, {"nasdaq": True})                                  # réarmer = recocher la case
    assert pont.reglages_publics(dossier)["instruments"]["nasdaq"] is True
    # aucun EA du tout : les cases sont quand même décochées
    for nom in os.listdir(dossier):
        if nom.startswith("etat-"):
            os.remove(os.path.join(dossier, nom))
    code, brut, _ = appeler(serveur, "POST", "/api/arret-urgence", {"confirmation": "ARRET"})
    assert code == 200 and json.loads(brut)["fermes"] == [] and pont.lire_reglages(dossier)["nasdaq"] == "0"
    # la page : un bouton toujours visible (dans l'en-tête), le mot ARRET, le résultat, et comment repartir
    entete = PAGE[PAGE.index('<header class="top">'):PAGE.index("</header>")]
    assert 'id="btn-urgence"' in entete and "Arrêt d’urgence" in entete
    assert "mot: 'ARRET'" in PAGE and "'/api/arret-urgence'" in PAGE and "recoche les cases" in PAGE and "AUD-10" in PAGE


def test_fermer_metatrader_quand_l_ea_ne_repond_plus_pendant_un_trade(serveur, dossier):
    """AUD-19 : le refus ne regardait que les EA en marche. Un EA gelé (ou MetaTrader planté) dont le DERNIER état disait un trade
    ou un ordre laissait fermer MetaTrader sans un mot. Il faut maintenant taper FERMER dans ce cas."""
    fermes = []
    serveur.application._mt5_fermer = lambda: fermes.append(1) or {"ferme": True}      # jamais le vrai taskkill
    for cles in ({"position": "1"}, {"attente": "1"}, {"jambes": "2"}):
        faux_etat(dossier, age=60, **cles)                                            # muet depuis une minute
        code, brut, _ = appeler(serveur, "POST", "/api/mt5/fermer", {})
        assert code == 409 and "FERMER" in json.loads(brut)["error"] and fermes == [], cles
        assert appeler(serveur, "POST", "/api/mt5/fermer", {"confirmation": "fermer"})[0] == 409
    assert appeler(serveur, "POST", "/api/mt5/fermer", {"confirmation": "FERMER"})[0] == 200 and fermes == [1]
    faux_etat(dossier, age=0, position="1")                                           # EA en marche : clôturer d'abord, même avec le mot
    assert appeler(serveur, "POST", "/api/mt5/fermer", {"confirmation": "FERMER"})[0] == 409 and fermes == [1]
    faux_etat(dossier, age=60, position="0", attente="0", jambes="0")                 # rien en cours : pas de mot
    assert appeler(serveur, "POST", "/api/mt5/fermer", {})[0] == 200 and fermes == [1, 1]
    assert "mot: 'FERMER'" in PAGE and "AUD-19" in PAGE


def test_pas_d_installation_pendant_un_trade(serveur, dossier):
    """AUD-21 : « Installer ou mettre à jour l'EA » recompile, ce qui recharge l'EA en pleine séance. Refusé pendant un trade ou un
    ordre, comme la fermeture ; un dernier état « trade en cours » d'un EA muet bloque tant que MetaTrader est ouvert."""
    installes = []
    serveur.application._mt5_installer = lambda chemin, connus, source, ouvert=None: installes.append(ouvert) or {"compile": True, "journal": []}
    for cles in ({"position": "1"}, {"attente": "1"}, {"jambes": "1"}):
        faux_etat(dossier, age=0, **cles)
        code, brut, _ = appeler(serveur, "POST", "/api/mt5/installer", {})
        assert code == 409 and "recharge" in json.loads(brut)["error"] and installes == [], cles
    faux_etat(dossier, age=60, position="1")
    serveur.application._mt5_ouvert = lambda: True
    serveur.application._ouvert = (0.0, None)
    assert appeler(serveur, "POST", "/api/mt5/installer", {})[0] == 409 and installes == []   # EA gelé, MetaTrader ouvert
    serveur.application._mt5_ouvert = lambda: False
    assert appeler(serveur, "POST", "/api/mt5/installer", {})[0] == 200 and installes == [False]   # MetaTrader fermé : rien à recharger
    faux_etat(dossier, age=0, position="0", attente="0", jambes="0")
    assert appeler(serveur, "POST", "/api/mt5/installer", {})[0] == 200 and len(installes) == 2


def test_double_clic_sans_metatrader_si_l_ea_n_a_pas_compile(dossier, monkeypatch):
    """AUD-22 : au double-clic, une compilation ratée lançait quand même MetaTrader avec l'ancien EA (ou sans EA). Il n'est plus
    lancé ; le journal et la page le disent (petit fichier du dossier : le double-clic peut venir d'un autre processus)."""
    lances, messages = [], []
    exe = "/MT5/terminal64.exe"
    reponses = [{"compile": False, "journal": ["Strategy-V11.mq5(12,3) : error 256: undeclared identifier", "Result: 1 errors, 0 warnings"]},
                {"compile": None, "journal": ["MetaEditor introuvable : ouvre l’EA dans MetaEditor et compile-le avec F7."]},
                pont.Refus("MetaTrader 5 n’a pas encore créé son dossier de données : ouvre-le une première fois, puis reviens ici.")]

    def installer(chemin, connus, source, ouvert=None):
        reponse = reponses.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [exe], mt5_installer=installer,
                             mt5_lancer=lambda chemin, connus, ident, ouvert: lances.append(chemin), journal=messages.append)
    monkeypatch.setattr(mt5, "donnees_de", lambda chemin, *a, **k: "/MT5")
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: False)
    monkeypatch.setattr(mt5, "est_mac", lambda systeme=None: True)
    for _ in range(3):
        assert app.ouvrir_mt5_si_demande(forcer=True) is False and lances == []
        assert "pas ouvert" in messages[-1]
        lancement = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: []).etat()["lancement"]   # autre processus
        assert lancement["ok"] is False and "pas ouvert" in lancement["message"]
    assert "Result: 1 errors" in messages[0] and "MetaEditor introuvable" in messages[1] and "dossier de données" in messages[2]
    app._mt5_installer = lambda chemin, connus, source, ouvert=None: {"compile": True, "journal": []}
    assert app.ouvrir_mt5_si_demande(forcer=True) is True and lances == [exe] and app.etat()["lancement"] is None
    # « Installer ou mettre à jour l'EA » réussi depuis la page efface aussi le message
    app._noter_lancement(False, "essai")
    assert app.traiter("POST", "/api/mt5/installer", {}, {})["compile"] is True and app.etat()["lancement"] is None
    assert "state.lancement" in PAGE and "e.ea_build" in PAGE and "AUD-22" in PAGE


def test_taille_estimee_avec_lot_minimum_et_pas_de_volume(serveur, dossier):
    """AUD-24 : l'onglet Risque ignorait le lot minimum et l'arrondi au pas de volume. Estimation par marché : risque en argent =
    solde × risque ; stop ≈ 3 × range médian du marché (reference.json) × prix ; lots arrondis vers le bas au pas (comme l'EA)."""
    trades_ref = risque.charger()["trades"]
    med = sorted(t[3] for t in trades_ref if t[1] == "nasdaq")[len([t for t in trades_ref if t[1] == "nasdaq"]) // 2]
    t = risque.estimer_taille(10000, 0.25, 21000, 1.0, 0.1, 0.1, "nasdaq")
    stop = 3 * med * 21000
    assert t["stopPrix"] == pytest.approx(stop) and t["argentParLot"] == pytest.approx(stop) and t["risqueArgent"] == pytest.approx(25)
    assert t["lotsBruts"] == pytest.approx(25 / stop) and t["lots"] == pytest.approx(0.1)          # 10 000 $ à 0,25 % ≈ 0,1 lot (CLAUDE.md)
    assert not t["sousMinimum"] and not t["arrondiTropFort"] and t["reductionPct"] == pytest.approx(100 * (1 - 0.1 * stop / 25))
    petit = risque.estimer_taille(1000, 0.25, 21000, 1.0, 0.1, 0.1, "nasdaq")
    assert petit["sousMinimum"] and petit["lots"] == 0                                               # sous le lot minimum : aucun trade
    arrondi = risque.estimer_taille(15000, 0.25, 21000, 1.0, 0.1, 0.1, "nasdaq")
    assert arrondi["lots"] == pytest.approx(0.1) and arrondi["reductionPct"] > 30 and arrondi["arrondiTropFort"]
    # 0,3 lot tout rond ne devient pas 0,2 (0.3 / 0.1 = 2.9999999999999996 en virgule flottante)
    vpl = 100 / (3 * med * 21000)
    assert risque.estimer_taille(12000, 0.25, 21000, vpl, 0.1, 0.1, "nasdaq")["lots"] == pytest.approx(0.3)
    sp = risque.estimer_taille(10000, 0.25, 6000, 1.0, 0.1, 0.1, "sp500")
    med_sp = sorted(x[3] for x in trades_ref if x[1] == "sp500")[len([x for x in trades_ref if x[1] == "sp500"]) // 2]
    assert sp["stopPrix"] == pytest.approx(3 * med_sp * 6000)                                          # médiane propre au marché
    for absurde in ((0, 0.25, 21000, 1, 0.1, 0.1), (-5, 0.25, 21000, 1, 0.1, 0.1), (10000, 0, 21000, 1, 0.1, 0.1),
                    (10000, 0.25, None, 1, 0.1, 0.1), (10000, 0.25, 21000, float("nan"), 0.1, 0.1), (10000, 0.25, 21000, 1, 0, 0.1),
                    (10000, 0.25, 21000, 1, -0.1, 0.1), (True, 0.25, 21000, 1, 0.1, 0.1), (10000, 0.25, 21000, 1, 0.1, float("inf"))):
        assert risque.estimer_taille(*absurde, "nasdaq") is None, absurde
    assert risque.estimer_taille(10000, 0.25, 21000, 1, 0.1, 0.1, "autre") is None
    # la route : seulement pour un EA qui donne ces clés, et pas en lots fixes
    faux_etat(dossier, "NAS100", solde="10000", prix="21000", valeur_point_lot="1", lot_pas="0.1", lot_min="0.1")
    faux_etat(dossier, "US500", instrument="sp500")                                                    # EA sans ces clés : rien
    tailles = json.loads(appeler(serveur, "GET", "/api/risque?pct=0.25")[1])["tailles"]
    assert [x["symbole"] for x in tailles] == ["NAS100"] and tailles[0]["lots"] == pytest.approx(0.1)
    assert json.loads(appeler(serveur, "GET", "/api/risque?pct=0.05")[1])["tailles"][0]["sousMinimum"] is True
    faux_etat(dossier, "NAS100", lots_fixes="0.10", solde="10000", prix="21000", valeur_point_lot="1", lot_pas="0.1", lot_min="0.1")
    assert json.loads(appeler(serveur, "GET", "/api/risque?pct=0.25")[1])["tailles"] == []
    assert "Aucun trade sur ${nom} avec ce solde et ce risque" in PAGE and "s.tailles" in PAGE and "AUD-24" in PAGE


def test_banniere_heure_du_serveur_en_detection_automatique():
    """AUD-25 : depuis la détection automatique (InpSrvAuto, 26/11/2026), la bannière demandait de corriger « Décalage GMT » ou
    « Heure d'été » de l'EA, qui ne servent plus qu'au testeur. Elle fait d'abord vérifier l'horloge de l'ordinateur."""
    banniere = PAGE[PAGE.index("heure du serveur mal réglée"):][:700]
    assert "corrige « Décalage GMT du serveur » ou « Heure d’été du serveur »" not in PAGE
    assert "l’horloge de cet ordinateur" in banniere and "heure automatique" in banniere and "GMT+2 en hiver" in banniere
    assert "« Décalage GMT du serveur »" in banniere and "AUD-25" in PAGE


def test_fichier_de_connexion_pas_efface_journalise_puis_reessaye(monkeypatch, tmp_path):
    """AUD-27 : l'échec de la suppression du fichier de connexion (mot de passe en clair, dossier temporaire) était avalé. Il est
    maintenant écrit dans le journal (sans le mot de passe) et la suppression est réessayée au lancement suivant."""
    messages, lances, minuteries = [], [], []
    monkeypatch.setattr(mt5, "journal", messages.append, raising=False)
    monkeypatch.setattr(mt5.tempfile, "tempdir", str(tmp_path))                  # jamais le vrai dossier temporaire

    class Minuterie:
        daemon = True

        def __init__(self, delai, action):
            minuteries.append(action)

        def start(self):
            pass
    exe = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    mt5.lancer(exe, [exe], ("12345", "s3cr3t-mdp", "Courtier-Demo"), systeme="win32", demarrer=lambda commande, cwd: lances.append(commande),
               minuterie=Minuterie)
    fichier = lances[0][1][len("/config:"):]
    assert os.path.dirname(fichier) == str(tmp_path) and os.path.exists(fichier)
    vrai_remove = os.remove

    def refuse(chemin):
        raise PermissionError("fichier ouvert par un autre programme")
    monkeypatch.setattr(mt5.os, "remove", refuse)
    minuteries[0]()                                                               # la minute est passée : effacement refusé
    monkeypatch.setattr(mt5.os, "remove", vrai_remove)
    assert os.path.exists(fichier) and len(messages) == 1
    assert fichier in messages[0] and "s3cr3t-mdp" not in messages[0] and "prochain lancement" in messages[0]
    mt5.lancer(exe, [exe], None, systeme="win32", demarrer=lambda commande, cwd: lances.append(commande), minuterie=Minuterie)
    assert not os.path.exists(fichier)                                            # réessayé au lancement suivant, même avant une minute
    assert "mt5.journal = journal" in open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()


def test_marche_d_un_symbole_comme_instrument_of_dans_l_ea():
    """AUD-09 : les journaux sont par symbole, les seuils de l'interrupteur par marché. Même classement que InstrumentOf() de l'EA."""
    corps = re.search(r"string InstrumentOf\(string sym\)(.*?)\n  }", EA, re.S).group(1)
    regles = re.findall(r"if\((.*?)\)\s*return \"(\w+)\";", corps, re.S)
    assert [m for _, m in regles] == list(pont.NOMS_MARCHES)
    for condition, marche in regles:
        assert tuple(re.findall(r'StringFind\(s, "([^"]+)"\) >= 0', condition)) == pont.NOMS_MARCHES[marche], marche
        assert tuple(re.findall(r'StringFind\(s, "([^"]+)"\) == 0', condition)) == pont.DEBUTS_MARCHES[marche], marche
        assert len(re.findall(r"StringFind\(", condition)) == len(pont.NOMS_MARCHES[marche]) + len(pont.DEBUTS_MARCHES[marche])
    for symbole, marche in (("NDX100", "nasdaq"), ("NAS100.cash", "nasdaq"), ("ustec", "nasdaq"), ("SPX500", "sp500"), ("US500", "sp500"),
                            ("ES1!", "sp500"), ("XES1", "autre"), ("XAUUSD", "autre"), ("", "autre"), (None, "autre")):
        assert pont.instrument_de(symbole) == marche, symbole


def _trades_jours(dossier, symbole, resultats, debut=datetime.date(2027, 1, 4)):
    with open(os.path.join(dossier, f"trades-{symbole}.csv"), "w", encoding="utf-8", newline="") as f:
        for i, r in enumerate(resultats):
            jour = (debut + datetime.timedelta(days=i)).isoformat()
            f.write(f"{1_798_000_000 + i * 86400};{jour};15:50;{symbole};1;0.10;{r};{r * 25:.2f};10000.00;Fin de journée;0;USD\r\n")


def test_interrupteur_visible_et_telegram_une_seule_fois_par_franchissement(dossier):
    """AUD-09 : l'interrupteur n'était calculé que dans l'export trimestriel. Étrave le vérifie toutes les 10 minutes (minuterie de
    main), le montre dans l'onglet Séance et, au premier franchissement sur 60 jours de trade, envoie un message Telegram, une seule
    fois (retenu dans interrupteur.txt du dossier d'Étrave). Jamais calculé à chaque appel de la page."""
    appels = []

    def appel(jeton, methode, corps):
        appels.append((methode, corps))
        return {"ok": True}
    nouvelle = lambda: etrave.Application(dossier, appel_telegram=appel, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    app, fin = nouvelle(), datetime.date(2027, 12, 31)
    assert app.etat()["interrupteur"] is None                                     # pas encore vérifié
    _trades_jours(dossier, "NDX100", [-0.3] * 60)                                 # −18 R : au-delà de −14,54 R (Nasdaq)
    _trades_jours(dossier, "SPX500", [-0.3] * 60)                                 # −18 R : en deçà de −44,83 R (S&P 500)
    app.verifier_interrupteur(fin)                                                # Telegram pas configuré : rien d'envoyé, rien de retenu
    assert appels == [] and not os.path.exists(os.path.join(dossier, "interrupteur.txt"))
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON, "telegram_discussion": "4242"})
    app.verifier_interrupteur(fin)
    marches = app.etat()["interrupteur"]["marches"]
    nas, sp = marches["NDX100"], marches["SPX500"]
    assert nas["marche"] == "nasdaq" and nas["complet"] and nas["total_r"] == -18.0 and set(nas["franchi"]) == {"jours gagnants", "total"}
    assert sp["marche"] == "sp500" and "total" not in sp["franchi"] and sp["seuils"] == export.SEUILS_INTERRUPTEUR["sp500"]
    assert [m for m, _ in appels] == ["sendMessage", "sendMessage"] and appels[0][1]["chat_id"] == "4242"
    assert "NDX100" in appels[0][1]["text"] and "SPX500" in appels[1][1]["text"] and JETON not in appels[0][1]["text"]
    app.verifier_interrupteur(fin)
    nouvelle().verifier_interrupteur(fin)                                         # Étrave relancée : toujours le même franchissement
    assert len(appels) == 2
    _trades_jours(dossier, "NDX100", [0.5, -0.2] * 30)                            # plus rien de franchi : la mémoire s'efface
    app.verifier_interrupteur(fin)
    assert app.etat()["interrupteur"]["marches"]["NDX100"]["franchi"] == [] and "NDX100" not in pont.lire_cles(os.path.join(dossier, "interrupteur.txt"))
    _trades_jours(dossier, "NDX100", [-0.3] * 60)                                 # nouveau franchissement : nouveau message
    app.verifier_interrupteur(fin)
    assert len(appels) == 3 and "NDX100" in appels[2][1]["text"]
    # Telegram injoignable : pas retenu, nouvel essai à la vérification suivante
    _trades_jours(dossier, "NDX100", [0.5, -0.2] * 30)
    app.verifier_interrupteur(fin)

    def injoignable(jeton, methode, corps):
        raise telegram.Injoignable("Telegram injoignable (réseau coupé)")
    app.appel_telegram = injoignable
    _trades_jours(dossier, "NDX100", [-0.3] * 60)
    app.verifier_interrupteur(fin)
    assert "NDX100" not in pont.lire_cles(os.path.join(dossier, "interrupteur.txt"))
    app.appel_telegram = appel
    app.verifier_interrupteur(fin)
    assert len(appels) == 4
    # moins de 60 jours de trade (ET-11) ou marché inconnu : jamais de message
    for nom in os.listdir(dossier):
        if nom.startswith(("trades-", "interrupteur")):
            os.remove(os.path.join(dossier, nom))
    _trades_jours(dossier, "NDX100", [-1.0] * 2)
    _trades_jours(dossier, "XAUUSD", [-1.0] * 60)
    app.verifier_interrupteur(fin)
    assert len(appels) == 4 and app.etat()["interrupteur"]["marches"]["XAUUSD"]["seuils"] is None
    source = open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()
    assert "INTERRUPTEUR_PERIODE_S = 10 * 60" in source and "serveur.application.verifier_interrupteur()" in source
    assert "state.interrupteur" in PAGE and "rien à signaler" in PAGE and "franchi : " in PAGE and "AUD-09" in PAGE


def test_arret_d_urgence_echec_visible_meme_interface_arretee():
    """AUD-10 : Étrave arrêtée, l'appel échouait et le résultat (bandeau construit après « if (!state) return; ») ne s'affichait
    pas : on pouvait croire l'arrêt envoyé. L'échec se voit maintenant (message bref et bandeau)."""
    entete = PAGE[PAGE.index("function renderHeader()"):PAGE.index("// ---------------------------------------------------------------- vue d'ensemble")]
    corps = entete[:entete.index("\n}\n")]
    assert "if (!state) return;" not in corps and corps.index("if (urgence) banners.push(") < corps.index("if (!state) {")
    assert "toast(`Arrêt d’urgence pas envoyé : ${error.message}`)" in PAGE


def test_message_du_double_clic_efface_une_fois_l_ea_compile(dossier, monkeypatch):
    """AUD-22 : après une compilation ratée, l'utilisateur compile avec F7 et relance ; si MetaTrader est déjà ouvert, le double-clic
    s'arrête avant d'effacer le message, et la page disait encore « MetaTrader 5 pas ouvert ». Le message part dès que l'EA compilé
    est plus récent que la source."""
    exe = "/MT5/terminal64.exe"
    app = etrave.Application(dossier, mt5_ouvert=lambda: True, mt5_terminaux=lambda etats: [exe],
                             mt5_lancer=lambda chemin, connus, ident, ouvert: None)
    monkeypatch.setattr(mt5, "donnees_de", lambda chemin, *a, **k: "/MT5")
    monkeypatch.setattr(mt5, "est_mac", lambda systeme=None: True)
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: False)
    app._noter_lancement(False, "MetaTrader 5 pas ouvert : la compilation de l’EA a échoué.")
    assert app.etat()["lancement"]["ok"] is False                                   # EA toujours pas compilé : le message reste
    monkeypatch.setattr(mt5, "ea_a_jour", lambda donnees, source: True)             # compilé avec F7
    assert app.ouvrir_mt5_si_demande(forcer=True) is False                          # MetaTrader déjà ouvert : rien à lancer
    assert app.etat()["lancement"] is None and not os.path.exists(os.path.join(dossier, etrave.FICHIER_LANCEMENT))


# ───────────────────────── alertes de sécurité de l'EA (demande de l'utilisateur du 27/11/2026) ─────────────────────────
# Elles ne vont plus sur Telegram : l'EA les écrit dans alertes-<symbole>.csv, Étrave les affiche en tête de page pendant 24 heures.
def test_alertes_de_l_ea(dossier):
    maintenant = 1795800000
    with open(os.path.join(dossier, "alertes-NDX100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"{maintenant - 90000};NDX100;HORLOGE : vieille de plus de 24 h\r\n")
        f.write("ligne abîmée\r\n")
        f.write(f"pas-un-nombre;NDX100;texte\r\n")
        f.write(f"{maintenant - 3600};NDX100;STOP ABSENT chez le courtier, reposé à 21500.0\r\n")
        f.write(f"{maintenant - 60};NDX100;\r\n")                                         # texte vide : ignoré
        f.write(f"{maintenant - 30};NDX100;JOUR MANQUÉ aujourd'hui · trop tard ; reprise demain\r\n")   # « ; » dans le texte
    with open(os.path.join(dossier, "alertes-SPX500.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"{maintenant - 600};SPX500;" + "x" * 5000 + "\r\n")
        f.write(f"{maintenant + 86400};SPX500;dans le futur : horloge fausse\r\n")
    alertes = pont.lire_alertes(dossier, maintenant=maintenant)
    assert [a["quand"] for a in alertes] == [maintenant - 30, maintenant - 600, maintenant - 3600]   # la plus récente d'abord
    assert alertes[0] == {"quand": maintenant - 30, "symbole": "NDX100", "texte": "JOUR MANQUÉ aujourd'hui · trop tard ; reprise demain"}
    assert len(alertes[1]["texte"]) == pont.ALERTE_TEXTE_MAX


def test_alertes_au_plus_dix(dossier):
    maintenant = 1795800000
    with open(os.path.join(dossier, "alertes-NDX100.csv"), "w", encoding="utf-8", newline="") as f:
        for i in range(25):
            f.write(f"{maintenant - i};NDX100;alerte {i}\r\n")
    alertes = pont.lire_alertes(dossier, maintenant=maintenant)
    assert len(alertes) == pont.ALERTES_MAX == 10 and alertes[0]["texte"] == "alerte 0"


def test_alertes_sans_fichier(dossier):
    assert pont.lire_alertes(dossier) == []


def test_un_gros_fichier_d_alertes_n_est_lu_que_par_la_fin(dossier):
    maintenant = 1795800000
    with open(os.path.join(dossier, "alertes-NDX100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"{maintenant - 100};NDX100;{'a' * 300}\r\n" * 5000)                  # environ 1,6 Mo d'anciennes lignes
        f.write(f"{maintenant - 5};NDX100;la dernière\r\n")
    assert pont.lire_alertes(dossier, maintenant=maintenant)[0]["texte"] == "la dernière"


def test_l_etat_donne_les_alertes(dossier):
    with open(os.path.join(dossier, "alertes-NDX100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"{int(time.time()) - 10};NDX100;FERMETURE DE SÉCURITÉ : 1 position fermée au marché\r\n")
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    assert app.etat()["alertes"][0]["symbole"] == "NDX100"


def test_accord_ea_etrave_sur_les_alertes():
    """Le nom du fichier et l'ordre des colonnes écrits par l'EA sont ceux qu'Étrave lit."""
    assert 'UI_DIR + "alertes-" + gSymFile + ".csv"' in EA
    assert 'IntegerToString((long)TimeGMT()) + ";" + gSymFile + ";" + txt' in EA
    assert pont.COLONNES_ALERTE == ("quand", "symbole", "texte")


def test_la_page_affiche_les_alertes():
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    bloc = page[page.index("for (const a of state.alertes || [])"):]
    bloc = bloc[:bloc.index("\n  }\n")]
    assert "alerteMasquee(cle)" in bloc and "'Masquer'" in bloc and "class: 'banner bad'" in bloc
    assert "innerHTML" not in page                                                    # le texte de l'EA n'est jamais du HTML
    assert "const cle = `alerte:${a.quand}:${a.symbole}`;" in bloc


# ───────────────────────── copie des journaux sur le Bureau (demande de l'utilisateur du 27/11/2026) ─────────────────────────
def test_etrave_sauvegarde_les_journaux(dossier):
    with open(os.path.join(dossier, "trades-NDX100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("1763322600;2026-11-16;15:50;NDX100;1;1.50;1.3000;65.20;10000.00;Fin de journée;1;USD\r\n")
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    assert app.sauvegarder_journaux() == ["trades-NDX100.csv"]
    assert app.sauvegarder_journaux() == []                                            # inchangé : pas recopié
    assert app.exports()["journaux"] == os.path.join(export.dossier_exports(dossier), export.SOUS_DOSSIER_JOURNAUX)


def test_une_copie_ratee_des_journaux_ne_bloque_rien(dossier, monkeypatch):
    def en_panne(d):
        raise OSError("disque plein")
    monkeypatch.setattr(export, "copier_journaux", en_panne)
    messages = []
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [], journal=messages.append)
    assert app.sauvegarder_journaux() == [] and "copie des journaux impossible" in messages[0]


def test_la_copie_des_journaux_tourne_toute_seule():
    source = open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()
    boucle = source[source.index("def verifier_interrupteur_puis_reprogrammer():"):]
    assert "serveur.application.sauvegarder_journaux()" in boucle[:boucle.index("minuterie.start()")]
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert "exportsInfo.journaux" in page


def test_le_dossier_d_exports_existe_des_le_depart(dossier):
    """Plan du 27/11/2026 : « Étrave exports » est créé tout seul, avant le premier trade, pour que l'utilisateur sache où regarder."""
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    assert app.sauvegarder_journaux() == [] and os.path.isdir(export.dossier_exports(dossier))


def test_la_page_dit_ce_que_telegram_recoit():
    """Demande de l'utilisateur du 27/11/2026 : Telegram ne reçoit plus la pyramide ni le stop déplacé ; les alertes de sécurité
    s'affichent dans Étrave."""
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert "pyramide, stop déplacé" not in page
    assert "Connexion réussie, ordres posés, entrées exécutées et clôtures (en R et en dollars)" in page
    assert "Les alertes de sécurité s’affichent en tête de cette page" in page


# ───────────────────────── objectif de A dans Étrave (décision de l'utilisateur du 27/11/2026) ─────────────────────────
def test_objectif_par_defaut_4R(dossier):
    assert pont.reglages_publics(dossier)["objectifR"] == 4.0


@pytest.mark.parametrize("valeur, ecrit", [(0, "0"), (1, "1"), (4, "4"), (4.5, "4.5"), (10, "10"), ("6", "6")])
def test_objectif_enregistre(dossier, valeur, ecrit):
    pont.regler(dossier, {"objectifR": valeur})
    assert pont.lire_reglages(dossier)["objectif_r"] == ecrit
    assert pont.reglages_publics(dossier)["objectifR"] == float(ecrit)


@pytest.mark.parametrize("valeur", [0.5, 0.99, -1, 10.01, 11, 1e9, "abc", "", None, True, False, [4], float("nan"), float("inf")])
def test_objectif_hors_bornes_refuse(dossier, valeur):
    with pytest.raises(pont.Refus):
        pont.regler(dossier, {"objectifR": valeur})
    assert "objectif_r" not in pont.lire_reglages(dossier)


def test_objectif_illisible_dans_le_fichier_vaut_4R(dossier):
    with open(os.path.join(dossier, pont.FICHIER_REGLAGES), "w", encoding="utf-8") as f:
        f.write("objectif_r=n'importe quoi\n")
    assert pont.reglages_publics(dossier)["objectifR"] == 4.0                          # comme l'EA, qui ignore la valeur


def test_accord_ea_etrave_sur_l_objectif():
    assert '#define TGT_MIN     1.0' in EA and '#define TGT_MAX     10.0' in EA and 'const double       InpTgtR      = 4.0;' in EA
    assert (pont.OBJECTIF_MIN, pont.OBJECTIF_MAX, pont.OBJECTIF_DEFAUT) == (1.0, 10.0, 4.0)
    assert 'k == "objectif_r"' in EA and "objectif_r" in pont.NOMBRES and "pos_objectif" in pont.NOMBRES


def test_la_page_regle_l_objectif():
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert 'id="objectif-input" min="0" max="10" step="0.5"' in page
    assert "api('/api/reglages', { valeurs: { objectifR: valeur } })" in page
    note = page[page.index("function renderObjectif()"):]
    note = note[:note.index("\n}\n")]
    sim = page[page.index("const SIM_OBJECTIF = "):]
    sim = sim[:sim.index("\n")]                                                         # simulation 2025-2026 (Nasdaq + S&P 500)
    assert sim == "const SIM_OBJECTIF = [['sans', 156.4], ['1 R', 90.1], ['1,5 R', 108.1], ['2 R', 108.4], ['3 R', 123.7], ['4 R', 146.4], ['5 R', 156.4]];"
    assert "SIM_OBJECTIF.map(" in note
    assert "déjà vues" in note and "règle mémoire" in note
    assert "C’est le seul réglage" not in page


def test_la_note_de_l_objectif_n_affiche_jamais_null():
    """Essai dans Chrome du 27/11/2026 : replaceChildren(texte, null) écrivait « null » à la fin de la note."""
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    note = page[page.index("function renderObjectif()"):]
    note = note[:note.index("\n}\n")]
    assert ".filter(Boolean)" in note and ": null)" not in note
