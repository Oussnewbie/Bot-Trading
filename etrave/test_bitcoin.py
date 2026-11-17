"""Tests de l'onglet Bitcoin d'Étrave (pilotage du bot BTC) : `python -m pytest etrave`."""
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bitcoin  # noqa: E402
import etrave  # noqa: E402
import pont  # noqa: E402
from test_interface import JETON, appeler  # noqa: E402

CLE, SECRET = "A1" * 32, "b2" * 32


@pytest.fixture()
def btc(tmp_path):
    lances, tues = [], []
    b = bitcoin.Bitcoin(str(tmp_path / "etrave"), config=str(tmp_path / "bot" / "config.json"),
                        lancer=lambda cmd, dossier: lances.append(cmd) or 4242, tuer=tues.append,
                        tester=lambda cle, secret, testnet: dict(ok=True, usdt_spot=1000.0, btc_spot=0.0, usdt_futures=0.0, testnet=testnet))
    os.makedirs(b.dossier, exist_ok=True)
    b.lances, b.tues = lances, tues
    return b


def ecrire_battement(b, age_s=0):
    import datetime
    os.makedirs(b.etat_dir(), exist_ok=True)
    heure = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=age_s)
    with open(os.path.join(b.etat_dir(), "vivant.json"), "w") as f:
        json.dump(dict(pid=4242, heure=str(heure), statut="en attente", mode="papier", levier=1), f)


def test_reglages_par_defaut_et_bornes(btc):
    assert btc.reglages_publics()["mode"] == "papier" and btc.reglages_publics()["levier"] == 1
    assert btc.regler({"levier": 2, "vente": 0, "ordres": "marche"}) == ["levier", "vente", "ordres"]
    c = json.load(open(btc.config))
    assert c["levier"] == 2 and c["vente"] == 0 and c["fichier_secrets"] == btc.f_secrets
    for mauvais in ({"levier": 11}, {"levier": 0}, {"levier": 2.5}, {"levier": True}, {"vente": 0.3}, {"ordres": "x"},
                    {"perte_max": 0.95}, {"bande": 0}, {"inconnu": 1}, {"profil": "fou"}):
        with pytest.raises(pont.Refus):
            btc.regler(mauvais)


def test_levier_fort_et_argent_reel_demandent_un_mot(btc):
    with pytest.raises(pont.Refus, match="LEVIER"):
        btc.regler({"levier": 5})
    assert btc.regler({"levier": 5}, "levier") == ["levier"]
    with pytest.raises(pont.Refus, match="clé"):
        btc.regler({"mode": "reel"}, "REEL")                    # pas de clé enregistrée
    btc.enregistrer_cles(CLE, SECRET)
    with pytest.raises(pont.Refus, match="REEL"):
        btc.regler({"mode": "reel"})
    assert btc.regler({"mode": "reel"}, "REEL") == ["mode"]
    assert json.load(open(btc.config))["reel_confirme"] is True


def test_cles_en_ecriture_seule_et_telegram_partage(btc):
    with pytest.raises(pont.Refus):
        btc.enregistrer_cles("trop-court", SECRET)
    pont.enregistrer_connexions(btc.dossier, {"telegram_jeton": JETON, "telegram_discussion": "4242"})
    c = btc.enregistrer_cles(CLE, SECRET)
    assert c == dict(renseignees=True, fin=CLE[-4:], telegram=True)
    s = json.load(open(btc.f_secrets))
    assert s["binance_secret"] == SECRET and s["telegram_jeton"] == JETON
    texte = json.dumps(btc.etat())
    assert SECRET not in texte and CLE not in texte and JETON not in texte
    btc.regler({"mode": "testnet"})
    assert btc.effacer_cles()["renseignees"] is False and btc.reglages_publics()["mode"] == "papier"


def test_demarrer_arreter_et_commandes(btc):
    r = btc.demarrer()
    assert r["pid"] == 4242 and btc.lances[0][-2:] == ["--config", btc.config]
    ecrire_battement(btc)
    assert btc.processus()["en_marche"] is True
    with pytest.raises(pont.Refus, match="déjà"):
        btc.demarrer()
    btc.pause(True)
    assert btc.etat()["drapeaux"]["pause"] is True
    with pytest.raises(pont.Refus, match="FERMER"):
        btc.fermer("non")
    btc.fermer("fermer")
    assert btc.etat()["drapeaux"]["fermer"] and btc.etat()["drapeaux"]["maintenant"]
    btc.rearmer()                                              # bot en marche : il le fera lui-même
    assert os.path.exists(os.path.join(btc.etat_dir(), "REARMER"))
    btc.arreter()
    assert btc.tues == [4242] and btc.processus()["en_marche"] is False


def test_bot_muet_depuis_plus_d_une_minute_est_arrete(btc):
    ecrire_battement(btc, age_s=120)
    assert btc.processus()["en_marche"] is False


def test_journal_et_decision_lus(btc):
    os.makedirs(btc.etat_dir(), exist_ok=True)
    with open(os.path.join(btc.etat_dir(), "journal.csv"), "w") as f:
        f.write("heure,bougie_4h,prix,score,tendance_4h,cible,capital,exposition,ordres,motif\n"
                "2026-11-17 08:01:30+00:00,2026-11-17 04:00:00+00:00,64740.1,-0.778,baissière,-0.2313,9998.38,-0.2314,perp:-0.035,\n")
    with open(os.path.join(btc.etat_dir(), "etat.json"), "w") as f:
        json.dump(dict(derniere_decision=dict(sens="VENTE", score=-0.78), compte=dict(capital=9998.38), stop=None), f)
    e = btc.etat()
    assert e["journal"][0]["capital"] == 9998.38 and e["decision"]["sens"] == "VENTE"
    assert e["profils"]["leviers"][0]["levier"] == 1           # le tableau du levier, livré avec le bot


def test_routes_http_du_bitcoin(tmp_path, btc):
    s = etrave.creer_serveur(btc.dossier, 0, mt5_ouvert=lambda: False, btc=btc,
                             appel_telegram=lambda jeton, methode, corps: {"ok": True})
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        assert appeler(s, "GET", "/api/btc/etat", jeton=False)[0] == 401
        code, brut, _ = appeler(s, "GET", "/api/btc/etat")
        assert code == 200 and json.loads(brut)["reglages"]["mode"] == "papier"
        code, brut, _ = appeler(s, "POST", "/api/btc/reglages", {"valeurs": {"levier": 4}})
        assert code == 422 and "LEVIER" in json.loads(brut)["error"]
        assert appeler(s, "POST", "/api/btc/reglages", {"valeurs": {"levier": 4}, "confirmation": "LEVIER"})[0] == 200
        code, brut, _ = appeler(s, "POST", "/api/btc/cles", {"cle": CLE, "secret": SECRET})
        assert code == 200 and SECRET not in brut and CLE not in brut
        code, brut, _ = appeler(s, "POST", "/api/btc/tester", {})
        assert code == 200 and json.loads(brut)["usdt_spot"] == 1000.0
        assert appeler(s, "POST", "/api/btc/demarrer", {})[0] == 200
        assert appeler(s, "POST", "/api/btc/pause", {"pause": True})[0] == 200
        assert appeler(s, "POST", "/api/btc/fermer", {"confirmation": "x"})[0] == 422
        assert appeler(s, "POST", "/api/btc/inconnu", {})[0] == 404
        assert SECRET not in appeler(s, "GET", "/api/btc/etat")[1]
    finally:
        s.shutdown(); s.server_close()


def test_reprise_de_l_ancien_dossier_crypto_bot(tmp_path):
    """Réorganisation du dépôt : config.json, etat/ et les données restés dans crypto/ passent dans les nouveaux dossiers."""
    ancien, nouveau, donnees = tmp_path / "crypto" / "bot", tmp_path / "bitcoin", tmp_path / "donnees" / "crypto"
    (ancien / "etat").mkdir(parents=True); nouveau.mkdir(); (tmp_path / "crypto" / "donnees" / "historique").mkdir(parents=True)
    (ancien / "__pycache__").mkdir()
    (ancien / "etat" / "journal.csv").write_text("t,capital\n")
    (ancien / "config.json").write_text(json.dumps({"mode": "papier", "levier": 2, "dossier": str(ancien / "etat")}))
    fait = bitcoin.reprendre_ancien_dossier(str(ancien), str(nouveau), str(donnees))
    assert fait == ["config.json", "etat", "dossier d'état", "données crypto"]
    c = json.loads((nouveau / "config.json").read_text())
    assert c["levier"] == 2 and c["dossier"] == str(nouveau / "etat")
    assert (nouveau / "etat" / "journal.csv").exists() and (donnees / "historique").is_dir()
    assert not (tmp_path / "crypto").exists()                        # l'ancien dossier vide disparaît
    assert bitcoin.reprendre_ancien_dossier(str(ancien), str(nouveau), str(donnees)) == []     # une seule fois


def test_reprise_ne_touche_pas_un_bot_qui_tourne_ni_n_ecrase(tmp_path):
    ancien, nouveau = tmp_path / "crypto" / "bot", tmp_path / "bitcoin"
    (ancien / "etat").mkdir(parents=True); nouveau.mkdir()
    (ancien / "config.json").write_text('{"levier": 3}')
    (ancien / "etat" / "vivant.json").write_text("{}")                # battement récent : l'ancien bot tourne
    assert bitcoin.reprendre_ancien_dossier(str(ancien), str(nouveau), str(tmp_path / "d")) == []
    assert (ancien / "config.json").exists()
    os.remove(ancien / "etat" / "vivant.json")
    (nouveau / "config.json").write_text('{"levier": 1}')            # déjà un réglage dans bitcoin/ : rien n'est écrasé
    assert bitcoin.reprendre_ancien_dossier(str(ancien), str(nouveau), str(tmp_path / "d")) == ["etat"]
    assert json.loads((nouveau / "config.json").read_text())["levier"] == 1
