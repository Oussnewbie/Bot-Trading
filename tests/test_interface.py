"""Tests de l'interface Étrave (dossier interface/) et de son accord avec l'EA (mt5/ORB-v5.mq5).

L'EA ne peut pas être exécuté ici : ses fichiers sont fabriqués à la main dans le format qu'il écrit, et un test relit
le code MQL5 pour vérifier que les noms de clés, les bornes et le format du journal sont les mêmes des deux côtés.
"""
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
sys.path.insert(0, os.path.join(RACINE, "interface"))

import etrave  # noqa: E402
import mt5  # noqa: E402
import pont  # noqa: E402
import risque  # noqa: E402
import telegram  # noqa: E402

JETON = "123456789:" + "A" * 35
EA = open(os.path.join(RACINE, "mt5", "ORB-v5.mq5"), encoding="utf-8-sig").read()


def faux_etat(dossier, symbole="NAS100", age=0.0, **cles):
    """Écrit un état comme le fait l'EA (cle=valeur, fin de ligne Windows)."""
    base = dict(version="1", ea="5.10", symbole=symbole, instrument="nasdaq", actif="1", terminal=r"C:\Program Files\MetaTrader 5",
                compte_type="demo", compte_serveur="Courtier-Demo", compte_login="12345678", devise="USD", solde="10000.00",
                capital="10000.00", marge_libre="10000.00", levier_compte="30", levier_symbole="20.0", connecte="1",
                trading_auto="1", heure_ny="2026.11.16 10:02", heure_serveur="17:02", horloge_ok="1", regles_test="1",
                risque_pct="0.5000", risque_source="mt5", range_bas="25010.5", range_haut="25050.5", filtres="Achat oui · Vente non (RSI) · RSI 61",
                jour="Achat stop 25050.5 · jusqu'à 09:45", attente="0", position="0", pos_sens="0", pos_entree="0", pos_stop="0",
                pos_lots="0", pos_resultat="0", pos_r="0", pos_pyramide="0", risque_argent="0", solde_depart="0", stats_n="0",
                stats_gagnants="0", stats_r="0", stats_baisse="0", stats_serie="0", telegram="0", telegram_envoi="jamais", telegram_essai="")
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
    assert r["instruments"] == {"nasdaq": True, "dow": False, "or": False, "eurusd": False, "bitcoin": False}   # seul le Nasdaq est validé
    assert not r["telegramJeton"] and not r["telegramDiscussion"]


def test_risque_entre_les_bornes_et_confirmation_au_dela_de_1_pct(dossier):
    assert pont.regler(dossier, {"risquePct": 0.5}) == ["risque_pct"]
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.5"
    for hors_bornes in (0, 0.04, 20.01, -1, "abc", None, True):
        with pytest.raises(pont.Refus):
            pont.regler(dossier, {"risquePct": hors_bornes}, "RISQUE")
    with pytest.raises(pont.Refus, match="RISQUE"):
        pont.regler(dossier, {"risquePct": 5})                      # monter au-delà de 1 % : il faut le mot
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.5"       # rien n'a été écrit
    pont.regler(dossier, {"risquePct": 20}, "RISQUE")
    assert pont.reglages_publics(dossier)["risquePct"] == 20.0
    pont.regler(dossier, {"risquePct": 2})                          # baisser ne demande rien
    pont.regler(dossier, {"risquePct": "0,25"})                     # virgule française acceptée
    assert pont.lire_reglages(dossier)["risque_pct"] == "0.25"


def test_levier_et_cases(dossier):
    pont.regler(dossier, {"levier": 20, "nasdaq": False})
    r = pont.reglages_publics(dossier)
    assert r["levier"] == 20 and r["instruments"]["nasdaq"] is False
    pont.regler(dossier, {"levier": None})
    assert "levier" not in pont.lire_reglages(dossier)
    for faux in (0.5, 2001, "x"):
        with pytest.raises(pont.Refus):
            pont.regler(dossier, {"levier": faux})
    for instrument in ("or", "dow", "eurusd", "bitcoin"):
        with pytest.raises(pont.Refus, match="ACTIVER"):
            pont.regler(dossier, {instrument: True})                # aucune stratégie validée : mot ACTIVER exigé
    pont.regler(dossier, {"or": True}, "ACTIVER")
    assert pont.lire_reglages(dossier)["or"] == "1"
    pont.regler(dossier, {"or": False})
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
    assert pont.lire_reglages(dossier)["cloturer"] == "1763000000;NAS100"


# ───────────────────────── ce que dit l'EA ─────────────────────────
def test_etat_de_l_ea_et_silence(dossier):
    faux_etat(dossier, "NAS100", age=1, position="1", pos_sens="1", pos_r="1.25", pos_resultat="62.50", solde_depart="10000.00")
    faux_etat(dossier, "XAUUSD", age=120, instrument="or", actif="0")
    nas, gold = pont.lire_etats(dossier)
    assert nas["symbole"] == "NAS100" and nas["en_marche"] and nas["position"] and nas["pos_r"] == 1.25 and nas["solde"] == 10000.0
    assert gold["instrument"] == "or" and not gold["en_marche"] and not gold["actif"]     # muet depuis 2 minutes : arrêté


def test_journal_des_trades(dossier):
    with open(os.path.join(dossier, "trades-NAS100.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("1763322600;2026-11-16;15:50;NAS100;1;1.50;1.3000;65.20;10000.00;Fin de journée;1;USD\r\n")
        f.write("ligne abîmée\r\n")
        f.write("1763236200;2026-11-13;09:52;NAS100;-1;1.20;-1.0200;-51.00;10051.00;Stop;0;USD\r\n")
    perte, gain = pont.lire_trades(dossier)
    assert perte["net"] == -51.0 and perte["sens"] == -1 and not perte["pyramide"]
    assert gain["r"] == 1.3 and gain["pct"] == pytest.approx(0.652) and gain["pyramide"] and gain["raison"] == "Fin de journée"


# ───────────────────────── risque et marge ─────────────────────────
@pytest.mark.parametrize("pct, par_an, baisse", [(0.25, 13, 6), (0.5, 26, 12), (1.0, 55, 23)])
def test_le_calcul_redonne_le_tableau_du_readme(pct, par_an, baisse):
    s = risque.simuler(pct)
    assert s["trades"] == 1427
    assert round(s["parAnPct"]) == par_an and round(s["pireBaissePct"]) == baisse
    assert s["reduitsPct"] == 0


def test_la_marge_reduit_la_taille_quand_le_levier_manque():
    # range de 0,3 % du prix, levier 20, 90 % de la marge pour deux unités : 2,7 % de risque au plus
    assert risque.risque_possible(20, 0.003) == pytest.approx(0.027)
    petit, grand = risque.simuler(1.0, levier=20), risque.simuler(20.0, levier=20)
    assert 0 < petit["reduitsPct"] < 5                              # à 1 %, seuls les très petits ranges coincent
    assert grand["reduitsPct"] > 99 and grand["risqueMoyenPct"] < 5   # à 20 %, presque tous les jours sont réduits
    assert risque.simuler(20.0, levier=2000)["reduitsPct"] < 1
    assert grand["pireBaissePct"] < risque.simuler(20.0)["pireBaissePct"]


def test_reference_a_jour(donnees_reelles):
    """interface/reference.json est bien ce que le simulateur donne sur les données du dépôt."""
    import construire_reference
    refait = construire_reference.construire()
    assert refait["trades"] == risque.charger()["trades"]


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
    trouves = mt5.terminaux([{"terminal": r"C:\MT5 Courtier"}, {"terminal": r"C:\MT5 Courtier"}, {"terminal": r"C:\disparu"}], env={}, existe=lambda c: c == programme)
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
    source = os.path.join(RACINE, "mt5", "ORB-v5.mq5")

    def compilateur(commande, timeout):
        cible = commande[1][len("/compile:"):]
        open(cible[:-4] + ".ex5", "wb").close()
        open(commande[2][len("/log:"):], "w", encoding="utf-16").write("ORB-v5.mq5 : information: compiling\nResult: 0 errors, 1 warnings\n")
    r = mt5.installer_ea(exe, [exe], source, env=env, systeme="win32", executer=compilateur)
    assert r["compile"] is True and r["journal"] == ["Result: 0 errors, 1 warnings"]
    copie = donnees / "MQL5" / "Experts" / "Etrave" / "ORB-v5.mq5"
    assert copie.read_bytes() == open(source, "rb").read()
    rate = mt5.installer_ea(exe, [exe], source, env=env, systeme="win32", executer=lambda commande, timeout: None)
    assert rate["compile"] is False                                  # pas de nouveau programme : la compilation a échoué
    with pytest.raises(pont.Refus):
        mt5.installer_ea(exe, [exe], source, env=env, systeme="linux")
    with pytest.raises(pont.Refus):
        mt5.installer_ea(str(tmp_path / "autre.exe"), [exe], source, env=env, systeme="win32")
    assert mt5.demarrage_windows(True, r"C:\Bot-Trading", env=env) is True
    assert "Etrave.bat" in open(mt5.fichier_demarrage(env)).read()
    assert mt5.demarrage_windows(False, r"C:\Bot-Trading", env=env) is False
    with pytest.raises(pont.Refus):
        mt5.demarrage_windows(True, "x", env={})


def test_ouverture_automatique_de_metatrader(dossier):
    lances = []
    exe = os.path.join(r"C:\MT5", "terminal64.exe")
    app = etrave.Application(dossier, mt5_ouvert=lambda: False, mt5_lancer=lambda chemin, connus, ident, ouvert: lances.append(chemin))
    assert app.ouvrir_mt5_si_demande() is False                      # option non cochée : rien
    pont.retenir_mt5(dossier, login="12345", serveur="Courtier-Demo", auto=True)
    publics = pont.reglages_publics(dossier)
    assert publics["mt5Auto"] and publics["mt5Login"] == "12345" and publics["mt5Serveur"] == "Courtier-Demo"
    assert app.ouvrir_mt5_si_demande() is False                      # aucun MetaTrader connu : rien, et pas d'erreur
    assert lances == []


# ───────────────────────── serveur local ─────────────────────────
@pytest.fixture()
def serveur(dossier):
    s = etrave.creer_serveur(dossier, 0, mt5_ouvert=lambda: False,
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
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 0.75, "levier": 20}})
    assert code == 200 and json.loads(brut)["reglages"]["risquePct"] == 0.75
    code, brut, _ = appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 10}})
    assert code == 422 and "RISQUE" in json.loads(brut)["error"]
    assert appeler(serveur, "POST", "/api/reglages", {"valeurs": {"risquePct": 10}, "confirmation": "RISQUE"})[0] == 200
    for chemin in ("/api/etat", "/api/trades", "/api/risque?pct=10&levier=20"):
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
    assert risque.UNITES == 2.0 and "InpPyrSize   = 1.0" in EA       # une unité de départ + une unité de pyramide
    assert definition("UI_PERIOD") * 5 < pont.EA_MUET_S              # l'EA écrit bien plus souvent que le délai de silence


def test_memes_noms_de_cles_des_deux_cotes(dossier):
    ecrites_par_ea = set(re.findall(r'K[vd]\(h, "([a-z_0-9]+)"', EA))
    assert set(pont.NOMBRES) | set(pont.DRAPEAUX) <= ecrites_par_ea
    assert {"symbole", "instrument", "compte_type", "compte_serveur", "compte_login", "devise", "heure_ny", "filtres", "jour",
            "telegram_envoi", "telegram_essai", "terminal", "risque_source"} <= ecrites_par_ea
    # tout ce que l'interface écrit, l'EA sait le lire
    pont.regler(dossier, {"risquePct": 0.5, "levier": 20, "nasdaq": True, "or": False})
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON, "telegram_discussion": "4242"})
    pont.demander_essai_mt5(dossier)
    pont.demander_cloture(dossier, "NAS100", "CLOTURER")
    lues_par_ea = set(re.findall(r'k == "([a-z_]+)"', EA)) | set(pont.INSTRUMENTS)     # les cases : comparées à gInstr
    assert set(pont.lire_reglages(dossier)) - {"version"} <= lues_par_ea
    for instrument in pont.INSTRUMENTS:
        assert f'return "{instrument}";' in EA                       # l'EA sait reconnaître chaque instrument de l'interface
    assert 'active = gInstr == "nasdaq" || gInstr == "autre";' in EA and pont.VALIDES == ("nasdaq",)
    assert "reglages.txt" in EA and 'UI_DIR      "Etrave\\\\"' in EA
    assert pont.SOUS_DOSSIER == "Etrave" and pont.FICHIER_REGLAGES == "reglages.txt"


def test_journal_des_trades_meme_nombre_de_colonnes():
    ecriture = re.search(r"void AppendTrade.*?FileWrite\(h,(.*?)\);\s*FileClose", EA, re.S).group(1)
    assert ecriture.count('";"') + 1 == len(pont.COLONNES_TRADE)


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
    brut = open(os.path.join(RACINE, "mt5", "ORB-v5.mq5"), "rb").read()
    assert brut.startswith(b"\xef\xbb\xbf")                           # UTF-8 signé : MetaEditor lit bien les accents
    code = sans_textes(EA)
    for ouvrant, fermant in ("{}", "()", "[]"):
        assert code.count(ouvrant) == code.count(fermant), f"{ouvrant} et {fermant} ne s'équilibrent pas"
    appelees = set(re.findall(r"\b(ReadSettings|WriteState|FlushNotifs|UiClose|CheckClock|AppendTrade|MarginPerLot|InstrumentOf|SafeName)\(", code))
    for fonction in appelees:
        assert re.search(rf"^(void|double|string|bool)\s+{fonction}\(", code, re.M), f"{fonction} appelée mais pas définie"
    assert "void OnTimer()" in code and "EventSetTimer(UI_PERIOD)" in code and "EventKillTimer()" in code
    # les messages lents partent après les ordres : plus aucun envoi direct depuis Notify
    notify = re.search(r"void Notify\(string msg\)(.*?)\n  }", EA, re.S).group(1)
    assert "SendTelegram" not in notify and "SendWhatsApp" not in notify
    assert EA.index("CheckEntries();\n   SyncPosition();") < EA.index("   FlushNotifs();\n   Panel();")
