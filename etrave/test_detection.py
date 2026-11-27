"""Détection automatique de la discussion Telegram (décision de l'utilisateur du 27/11/2026) : `python -m pytest etrave`.

Étrave lit les nouvelles du bot (getUpdates, rien n'est effacé chez Telegram). Elle bascule seule vers un groupe quand le
propriétaire (le compte de la discussion privée avec le bot) y ajoute le bot ou y tape /start@<bot>. Un groupe où quelqu'un d'autre
ajoute le bot est montré, jamais choisi seul. Numéros fictifs : le dépôt est public.
"""
import os
import sys

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etrave  # noqa: E402
import pont  # noqa: E402
import telegram  # noqa: E402

JETON = "123456789:" + "A" * 35
MOI, INCONNU, GROUPE, AUTRE_GROUPE = "111222333", 444555666, -1001234567890, -1009876543210
DEPART = 1795800000


@pytest.fixture()
def dossier(tmp_path):
    d = str(tmp_path)
    pont.enregistrer_connexions(d, {"telegram_jeton": JETON, "telegram_discussion": MOI})
    return d


def commande(uid, chat, titre, de, texte="/start@Etrave_bot", date=DEPART + 30, genre="supergroup"):
    return {"update_id": uid, "message": {"message_id": uid, "date": date, "text": texte, "from": {"id": de, "is_bot": False},
                                          "chat": {"id": chat, "title": titre, "type": genre}}}


def ajout(uid, chat, titre, par, statut="member", date=DEPART + 30):
    return {"update_id": uid, "my_chat_member": {"date": date, "from": {"id": par}, "chat": {"id": chat, "title": titre, "type": "supergroup"},
                                                 "old_chat_member": {"status": "left"}, "new_chat_member": {"status": statut, "user": {"id": 999}}}}


class FauxBot:
    def __init__(self, nouvelles=(), refus_envoi=None):
        self.nouvelles, self.envois, self.refus_envoi = list(nouvelles), [], refus_envoi

    def __call__(self, jeton, methode, corps):
        assert jeton == JETON
        if methode == "getMe":
            return {"ok": True, "status": 200, "result": {"id": 999, "username": "Etrave_bot"}}
        if methode == "getUpdates":
            return {"ok": True, "status": 200, "result": list(self.nouvelles)}
        assert methode == "sendMessage"
        self.envois.append(corps)
        if self.refus_envoi and str(corps["chat_id"]) == str(self.refus_envoi):
            return {"ok": False, "status": 403, "description": "Forbidden: bot is not a member of the supergroup chat"}
        return {"ok": True, "status": 200}


def appli(dossier, bot):
    app = etrave.Application(dossier, appel_telegram=bot, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    app._detection_depart = DEPART
    return app


def test_bascule_quand_je_tape_start_dans_le_groupe(dossier):
    bot = FauxBot([commande(10, GROUPE, "Trading & co", int(MOI))])
    d = appli(dossier, bot).detecter_telegram()
    cles, local = pont.lire_reglages(dossier), pont.lire_destination(dossier)
    assert cles["telegram_discussion"] == str(GROUPE) and local == {"proprietaire": MOI, "nom": "Trading & co"}
    assert bot.envois[0]["chat_id"] == str(GROUPE) and "<b>Alertes Étrave branchées ici</b>" in bot.envois[0]["text"]
    assert bot.envois[1]["chat_id"] == MOI and "Trading &amp; co" in bot.envois[1]["text"]          # un mot en privé, titre échappé
    assert d["bascule"]["titre"] == "Trading & co"


def test_bascule_quand_j_ajoute_le_bot(dossier):
    appli(dossier, FauxBot([ajout(11, GROUPE, "Trading", int(MOI), statut="administrator")])).detecter_telegram()
    assert pont.lire_reglages(dossier)["telegram_discussion"] == str(GROUPE)


@pytest.mark.parametrize("nouvelle", [ajout(12, GROUPE, "Piège", INCONNU), commande(13, GROUPE, "Piège", INCONNU),
                                      commande(14, GROUPE, "Trading", int(MOI), texte="/start@AutreBot"),
                                      commande(15, GROUPE, "Trading", int(MOI), texte="bonjour"),
                                      ajout(16, GROUPE, "Trading", int(MOI), statut="left"),
                                      commande(17, GROUPE, "Trading", int(MOI), date=DEPART - 600)])      # avant le démarrage d'Étrave
def test_pas_de_bascule(dossier, nouvelle):
    bot = FauxBot([nouvelle])
    d = appli(dossier, bot).detecter_telegram()
    assert pont.lire_reglages(dossier)["telegram_discussion"] == MOI and bot.envois == [] and d["bascule"] is None


def test_un_groupe_d_un_inconnu_est_montre_jamais_choisi(dossier):
    d = appli(dossier, FauxBot([ajout(12, GROUPE, "Piège", INCONNU)])).detecter_telegram()
    assert d["groupes"] == [{"id": str(GROUPE), "titre": "Piège", "type": "supergroup"}]


def test_sans_proprietaire_connu_rien_n_est_automatique(tmp_path):
    d = str(tmp_path)
    pont.enregistrer_connexions(d, {"telegram_jeton": JETON})                                   # première installation : choix à la main
    bot = FauxBot([commande(10, GROUPE, "Trading", int(MOI))])
    appli(d, bot).detecter_telegram()
    assert "telegram_discussion" not in pont.lire_reglages(d) and bot.envois == []


def test_une_seule_bascule_par_evenement_et_le_proprietaire_reste(dossier):
    bot = FauxBot([commande(10, GROUPE, "Trading", int(MOI))])
    app = appli(dossier, bot)
    app.detecter_telegram()
    app.detecter_telegram()
    assert len(bot.envois) == 2                                                                # pas de seconde annonce
    bot.nouvelles.append(commande(20, AUTRE_GROUPE, "Trading 2", int(MOI)))                    # le propriétaire reste connu
    app.detecter_telegram()
    assert pont.lire_reglages(dossier)["telegram_discussion"] == str(AUTRE_GROUPE)


def test_le_bot_ne_peut_pas_ecrire_dans_le_groupe(dossier):
    bot = FauxBot([commande(10, GROUPE, "Trading", int(MOI))], refus_envoi=GROUPE)
    d = appli(dossier, bot).detecter_telegram()
    assert pont.lire_reglages(dossier)["telegram_discussion"] == MOI                           # les alertes ne sont pas perdues
    assert "ne peut pas écrire" in d["erreur"] and d["bascule"] is None


def test_groupe_devenu_supergroupe_suivi_tout_seul(dossier):
    pont.brancher_discussion(dossier, "-4012345678", "Trading", proprietaire=MOI)
    migration = {"update_id": 30, "message": {"message_id": 30, "date": DEPART + 30, "from": {"id": int(MOI)}, "migrate_to_chat_id": GROUPE,
                                              "chat": {"id": -4012345678, "title": "Trading", "type": "group"}}}
    appli(dossier, FauxBot([migration])).detecter_telegram()
    assert pont.lire_reglages(dossier)["telegram_discussion"] == str(GROUPE) and pont.lire_destination(dossier)["nom"] == "Trading"


def test_le_relais_suit_un_groupe_devenu_supergroupe(dossier):
    pont.brancher_discussion(dossier, "-4012345678", "Trading", proprietaire=MOI)
    with open(os.path.join(dossier, "telegram-1795800000-00001-NDX100.txt"), "w", encoding="utf-8") as f:
        f.write("v1;msg;0\nun")
    envois = []

    def appel(jeton, methode, corps):
        envois.append(corps)
        if corps["chat_id"] == "-4012345678":
            return {"ok": False, "status": 400, "description": "Bad Request: group chat was upgraded to a supergroup chat",
                    "parameters": {"migrate_to_chat_id": GROUPE}}
        return {"ok": True, "status": 200}
    r = telegram.relayer(dossier, appel, maintenant=DEPART + 5, attendre=lambda s: None)
    assert r["envoyes"] == 1 and envois[-1]["chat_id"] == str(GROUPE)
    assert pont.lire_reglages(dossier)["telegram_discussion"] == str(GROUPE)


def test_changer_de_discussion_a_la_main_efface_l_ancien_nom(dossier):
    pont.brancher_discussion(dossier, str(GROUPE), "Trading", proprietaire=MOI)
    pont.enregistrer_connexions(dossier, {"telegram_discussion": MOI})
    assert pont.lire_destination(dossier) == {"proprietaire": MOI, "nom": ""}
    assert pont.reglages_publics(dossier)["telegramGroupe"] is False


@pytest.mark.parametrize("discussion, nom", [("abc", "Trading"), ("-12", "Trading"), (str(GROUPE), "a\nb"), (str(GROUPE), "x" * 81)])
def test_brancher_refuse_les_valeurs_illisibles(dossier, discussion, nom):
    with pytest.raises(pont.Refus):
        pont.brancher_discussion(dossier, discussion, nom)


def test_la_page_montre_la_destination():
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert "Alertes envoyées dans" in page and "telegramDiscussionNom" in page and "state.telegramDetection" in page
    assert "telegram_discussion_nom: g.titre" in page                                          # le bouton d'un groupe vu


def test_la_detection_tourne_toute_seule():
    source = open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()
    assert "DETECTION_PERIODE_S = 10" in source
    boucle = source[source.index("def detecter_puis_reprogrammer():"):]
    assert "serveur.application.detecter_telegram()" in boucle[:boucle.index("minuterie.start()")]


# ───────────────────────── revue de sécurité du 27/11/2026 : un nom de groupe ne glisse jamais une ligne dans un fichier ─────────────
PIEGES = ["x proprietaire=444555666", "x nom=y", "x\x0bproprietaire=1", "x\x0cproprietaire=1", "x\x1cproprietaire=1",
          "x\x85proprietaire=1", "x\rproprietaire=1", "x\nproprietaire=1", "x\x00y"]


@pytest.mark.parametrize("nom", PIEGES)
def test_un_nom_avec_un_separateur_est_refuse(dossier, nom):
    with pytest.raises(pont.Refus):
        pont.brancher_discussion(dossier, str(GROUPE), nom)
    with pytest.raises(pont.Refus):
        pont.enregistrer_connexions(dossier, {"telegram_discussion": str(GROUPE), "telegram_discussion_nom": nom})
    assert pont.lire_destination(dossier)["proprietaire"] == MOI


def test_les_fichiers_ne_se_decoupent_que_sur_les_vrais_retours_a_la_ligne(tmp_path):
    chemin = str(tmp_path / "f.txt")
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write("a=1 b=2\x0bc=3\r\nd=4\ne=5\r\n")
    assert pont.lire_cles(chemin) == {"a": "1 b=2\x0bc=3", "d": "4", "e": "5"}               # comme l'EA, qui lit ligne par ligne


@pytest.mark.parametrize("valeur", ["1\r2", "1\n2", "1 2", "1\x0b2", "1\x852"])
def test_ecrire_refuse_une_valeur_avec_un_separateur(tmp_path, valeur):
    with pytest.raises(ValueError):
        pont.ecrire_cles(str(tmp_path / "f.txt"), {"cle": valeur})


def test_un_titre_de_groupe_piege_est_nettoye_avant_la_bascule(dossier):
    bot = FauxBot([commande(10, GROUPE, "Trading proprietaire=444555666", int(MOI))])
    appli(dossier, bot).detecter_telegram()
    assert pont.lire_destination(dossier) == {"proprietaire": MOI, "nom": "Trading proprietaire=444555666"}
    assert pont.lire_reglages(dossier)["telegram_discussion"] == str(GROUPE)
