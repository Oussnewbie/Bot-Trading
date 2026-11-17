"""Alertes Telegram (facultatives). Jeton et discussion lus dans l'environnement : TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
Sans eux, les messages vont seulement dans le journal."""
import json
import logging
import os
import urllib.parse
import urllib.request

log = logging.getLogger("bot")


def envoyer(texte):
    log.info(texte.replace("\n", " | "))
    jeton, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not jeton or not chat:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": texte}).encode()
        with urllib.request.urlopen(f"https://api.telegram.org/bot{jeton}/sendMessage", data=data, timeout=15) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:  # noqa: BLE001  (une alerte ratée ne doit jamais arrêter le bot)
        log.warning(f"Telegram : {e}")
        return False
