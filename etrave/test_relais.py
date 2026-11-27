"""Relais Telegram par Étrave (décision de l'utilisateur du 27/11/2026) : `python -m pytest etrave`.

L'EA écrit un fichier par message (Etrave/telegram-<secondes>-<n°>-<symbole>.txt : « v1;<genre>;<numéro> », puis le texte, avec
**gras**) ; Étrave les envoie dans l'ordre, en HTML, et les efface. Aucun appel réseau ici : Telegram est remplacé par un faux.
"""
import os
import re
import sys
import time

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import etrave  # noqa: E402
import pont  # noqa: E402
import telegram  # noqa: E402

JETON = "123456789:" + "A" * 35
MAINTENANT = 1795800000


@pytest.fixture()
def dossier(tmp_path):
    return str(tmp_path)


def configurer(dossier):
    pont.enregistrer_connexions(dossier, {"telegram_jeton": JETON, "telegram_discussion": "12345"})


def message(dossier, quand, n, symbole, texte, genre="msg", numero=0, ext=".txt"):
    nom = f"telegram-{quand}-{n:05d}-{symbole}{ext}"
    with open(os.path.join(dossier, nom), "w", encoding="utf-8", newline="") as f:
        f.write(f"v1;{genre};{numero}\r\n{texte}")
    return nom


class FauxTelegram:
    def __init__(self, reponses=()):
        self.appels, self.reponses = [], list(reponses)

    def __call__(self, jeton, methode, corps):
        assert jeton == JETON and methode == "sendMessage"
        self.appels.append(corps)
        if self.reponses:
            r = self.reponses.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        return {"ok": True, "status": 200}


def relayer(dossier, faux, **options):
    return telegram.relayer(dossier, faux, maintenant=options.pop("maintenant", MAINTENANT), attendre=lambda s: None, **options)


def restants(dossier):
    return sorted(n for n in os.listdir(dossier) if n.startswith("telegram-"))


def test_gras_et_echappement_html():
    texte = "🎯 **OBJECTIF ATTEINT · S&P 500**\n\n**Gain** +1 <2> $"
    assert telegram.rendre_html(texte) == "🎯 <b>OBJECTIF ATTEINT · S&amp;P 500</b>\n\n<b>Gain</b> +1 &lt;2&gt; $"
    assert telegram.texte_brut(texte) == "🎯 OBJECTIF ATTEINT · S&P 500\n\nGain +1 <2> $"


def test_les_messages_partent_dans_l_ordre(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 5, 2, "NDX100", "deux")
    message(dossier, MAINTENANT - 5, 1, "NDX100", "**un**")
    message(dossier, MAINTENANT - 6, 9, "SPX500", "zéro")
    message(dossier, MAINTENANT - 1, 0, "NDX100", "à moitié écrit", ext=".tmp")       # pas encore renommé par l'EA
    faux = FauxTelegram()
    r = relayer(dossier, faux)
    assert [c["text"] for c in faux.appels] == ["zéro", "<b>un</b>", "deux"]
    assert all(c["parse_mode"] == "HTML" and c["chat_id"] == "12345" for c in faux.appels)
    assert restants(dossier) == ["telegram-1795799999-00000-NDX100.tmp"]
    assert r["attente"] == 0 and r["dernier"] == "ok" and r["envoyes"] == 3


def test_reseau_coupe_rien_n_est_perdu(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 2, 1, "NDX100", "un")
    message(dossier, MAINTENANT - 1, 2, "NDX100", "deux")
    faux = FauxTelegram([telegram.Injoignable("Telegram injoignable (délai dépassé)")])
    r = relayer(dossier, faux)
    assert len(faux.appels) == 1 and len(restants(dossier)) == 2                       # l'ordre est gardé pour la prochaine fois
    assert r["dernier"] == "injoignable" and r["attente"] == 2


def test_refus_renvoye_en_texte_simple_puis_mis_de_cote(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 3, 1, "NDX100", "**un**")
    message(dossier, MAINTENANT - 2, 2, "NDX100", "**deux**")
    message(dossier, MAINTENANT - 1, 3, "NDX100", "trois")
    faux = FauxTelegram([{"ok": False, "status": 400, "description": "Bad Request: can't parse entities"}, {"ok": True, "status": 200},
                         {"ok": False, "status": 400, "description": "Bad Request: message is too long"},
                         {"ok": False, "status": 400, "description": "Bad Request: message is too long"}])
    r = relayer(dossier, faux)
    assert faux.appels[1] == {"chat_id": "12345", "text": "un"}                          # renvoyé sans HTML
    assert [c["text"] for c in faux.appels[2:]] == ["<b>deux</b>", "deux", "trois"]      # le refus ne bloque pas la file
    assert restants(dossier) == ["telegram-1795799998-00002-NDX100.refuse"]
    assert "message is too long" in r["erreur"] and r["attente"] == 0


def test_trop_de_messages_telegram_fait_attendre(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 1, 1, "NDX100", "un")
    faux = FauxTelegram([{"ok": False, "status": 429, "description": "Too Many Requests", "parameters": {"retry_after": 7}}])
    r = relayer(dossier, faux)
    assert r["pauseJusqu"] == MAINTENANT + 7 and len(restants(dossier)) == 1
    faux2 = FauxTelegram()
    assert relayer(dossier, faux2, maintenant=MAINTENANT + 3, pause_jusqu=r["pauseJusqu"])["dernier"] == "pause" and faux2.appels == []
    assert relayer(dossier, faux2, maintenant=MAINTENANT + 8, pause_jusqu=r["pauseJusqu"])["envoyes"] == 1


def test_message_en_retard_dit_son_heure(dossier):
    configurer(dossier)
    quand = MAINTENANT - 3600
    message(dossier, quand, 1, "NDX100", "**ACHAT A · Nasdaq**")
    faux = FauxTelegram()
    relayer(dossier, faux)
    heure = time.strftime("%H:%M", time.localtime(quand))
    assert faux.appels[0]["text"] == f"<b>ACHAT A · Nasdaq</b>\n\n⏱ Envoyé en retard (message de {heure})"


def test_sans_telegram_rien_ne_part_et_rien_ne_s_entasse(dossier):
    message(dossier, MAINTENANT - 25 * 3600, 1, "NDX100", "vieux")
    message(dossier, MAINTENANT - 60, 2, "NDX100", "récent")
    faux = FauxTelegram()
    r = relayer(dossier, faux)
    assert faux.appels == [] and restants(dossier) == ["telegram-1795799940-00002-NDX100.txt"] and r["dernier"] == "inactif"


def test_essai_depuis_metatrader_rapporte_l_envoi_d_etrave(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 1, 1, "NDX100", "✅ **Essai réussi · Nasdaq**", genre="essai", numero=1795799999)
    r = relayer(dossier, FauxTelegram())
    assert r["essai"] == {"numero": "1795799999", "resultat": "ok"}


def test_fichier_illisible_mis_de_cote(dossier):
    configurer(dossier)
    with open(os.path.join(dossier, "telegram-1795799990-00001-NDX100.txt"), "w", encoding="utf-8") as f:
        f.write("pas d'en-tête")
    message(dossier, MAINTENANT - 1, 2, "NDX100", "bon")
    faux = FauxTelegram()
    r = relayer(dossier, faux)
    assert [c["text"] for c in faux.appels] == ["bon"] and restants(dossier) == ["telegram-1795799990-00001-NDX100.refuse"]
    assert "illisible" in r["erreur"]


def test_etrave_publie_l_etat_du_relais(dossier):
    configurer(dossier)
    message(dossier, MAINTENANT - 1, 1, "NDX100", "un")
    faux = FauxTelegram()
    app = etrave.Application(dossier, appel_telegram=faux, mt5_ouvert=lambda: False, mt5_terminaux=lambda etats: [])
    app.relayer_telegram(maintenant=MAINTENANT, attendre=lambda s: None)
    relais = app.etat()["telegramRelais"]
    assert relais["dernier"] == "ok" and relais["attente"] == 0 and relais["envoyes"] == 1


def test_le_relais_tourne_tout_seul():
    source = open(os.path.join(RACINE, "etrave", "etrave.py"), encoding="utf-8").read()
    assert "RELAIS_PERIODE_S = 5" in source
    boucle = source[source.index("def relayer_puis_reprogrammer():"):]
    assert "serveur.application.relayer_telegram()" in boucle[:boucle.index("minuterie.start()")]


def test_la_page_n_attend_plus_webrequest():
    page = open(os.path.join(RACINE, "etrave", "page.html"), encoding="utf-8").read()
    assert "WebRequest" not in page and "MT5_BLOCKED" not in page
    assert "state.telegramRelais" in page
