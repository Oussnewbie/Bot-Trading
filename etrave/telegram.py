"""Telegram, côté interface : vérifier le jeton, trouver la discussion, envoyer un message d'essai.

Même parcours que l'onglet Connexions de Vigie. Les alertes de tous les jours, elles, partent de l'EA (MetaTrader) :
l'interface peut être fermée sans rien changer aux alertes.
"""
import json
import urllib.error
import urllib.request

from pont import Refus, lire_reglages

API = "https://api.telegram.org"
DELAI_S = 10


class Injoignable(Exception):
    """Telegram n'a pas répondu. Le message ne contient jamais le jeton."""


def appeler(jeton, methode, corps, ouvrir=urllib.request.urlopen, delai=DELAI_S):
    """Un appel à l'API des bots. Retourne la réponse de Telegram (`ok`, `result`, `description`) et son code HTTP."""
    requete = urllib.request.Request(f"{API}/bot{jeton}/{methode}", data=json.dumps(corps).encode("utf-8"),
                                     headers={"content-type": "application/json"}, method="POST")
    try:
        with ouvrir(requete, timeout=delai) as reponse:
            code, brut = reponse.status, reponse.read()
    except urllib.error.HTTPError as erreur:      # Telegram a répondu par un refus : sa réponse dit pourquoi
        code, brut = erreur.code, erreur.read()
    except Exception as erreur:                   # réseau coupé, délai dépassé… l'erreur d'origine peut citer l'adresse, donc le jeton
        raison = str(getattr(erreur, "reason", erreur)).replace(jeton, "***")
        raise Injoignable(f"Telegram injoignable ({raison})") from None
    try:
        reponse = json.loads(brut.decode("utf-8"))
        if not isinstance(reponse, dict):
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        reponse = {"ok": False, "description": f"réponse illisible (HTTP {code})"}
    reponse["status"] = code
    return reponse


def verifier(dossier, message, appel=appeler):
    """Vérifie la configuration enregistrée et dit quoi faire ensuite :
    jeton absent -> le saisir ; pas de discussion -> écrire au bot, ou choisir parmi celles où quelqu'un lui a écrit ;
    tout est là -> un message d'essai est envoyé (par l'interface, pas par MetaTrader)."""
    cles = lire_reglages(dossier)
    jeton, discussion = cles.get("telegram_jeton", ""), cles.get("telegram_discussion", "")
    if jeton == "":
        return {"step": "token-missing"}

    moi = appeler_ok(appel, jeton, "getMe", {})
    if not moi.get("ok"):
        raise Refus(f"Telegram refuse ce jeton ({_raison(moi)}). Vérifie-le auprès de @BotFather.")
    bot = (moi.get("result") or {}).get("username", "")

    if discussion == "":
        nouvelles = appeler_ok(appel, jeton, "getUpdates", {})
        discussions = {}
        for nouvelle in nouvelles.get("result") or []:
            chat = ((nouvelle or {}).get("message") or {}).get("chat") or {}
            if chat.get("id") is not None:
                discussions[str(chat["id"])] = chat.get("title") or chat.get("username") or chat.get("first_name") or chat.get("type") or ""
        if not discussions:
            return {"step": "no-chat", "bot": bot}
        return {"step": "choose-chat", "bot": bot, "chats": [{"id": i, "name": n} for i, n in discussions.items()]}

    envoi = appeler_ok(appel, jeton, "sendMessage", {"chat_id": discussion, "text": message})
    if not envoi.get("ok"):
        raise Refus(f"Le message d’essai n’est pas parti ({_raison(envoi)}). Vérifie la discussion choisie, et que tu as bien "
                    "écrit au bot au moins une fois.")
    return {"step": "sent", "bot": bot}


def appeler_ok(appel, jeton, methode, corps):
    reponse = appel(jeton, methode, corps)
    return reponse if isinstance(reponse, dict) else {"ok": False}


def _raison(reponse):
    return reponse.get("description") or f"HTTP {reponse.get('status')}"
