"""Alertes Telegram (facultatives). Jeton et discussion : variables TELEGRAM_TOKEN et TELEGRAM_CHAT_ID, sinon le
fichier de secrets d'Étrave. Sans eux, les messages vont seulement dans le journal."""
import json
import logging
import os
import urllib.parse
import urllib.request

log = logging.getLogger("bot")


_CONF = {}


def configurer(jeton=None, chat=None):
    """Jeton et discussion venus du fichier de secrets d'Étrave (l'environnement passe avant)."""
    _CONF.update(jeton=jeton, chat=chat)


def envoyer(texte):
    log.info(texte.replace("\n", " | "))
    jeton = os.environ.get("TELEGRAM_TOKEN") or _CONF.get("jeton")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or _CONF.get("chat")
    if not jeton or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": texte}).encode()
        with urllib.request.urlopen(f"https://api.telegram.org/bot{jeton}/sendMessage", data=data, timeout=15) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:  # noqa: BLE001  (une alerte ratée ne doit jamais arrêter le bot)
        log.warning(f"Telegram : {e}")
        return False
