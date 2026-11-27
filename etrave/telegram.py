"""Telegram, côté interface : vérifier le jeton, trouver la discussion, envoyer un message d'essai.

Même parcours que l'onglet Connexions de Vigie. Les alertes de tous les jours, elles, partent de l'EA (MetaTrader) :
l'interface peut être fermée sans rien changer aux alertes.
"""
import glob
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

from pont import Refus, brancher_discussion, lire_destination, lire_reglages

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


def envoyer(dossier, message, appel=appeler):
    """AUD-09 (audit du 26/11/2026) : un message d'Étrave elle-même (l'interrupteur franchi), avec le jeton et la discussion
    enregistrés. False s'il en manque un (rien n'est envoyé) ; Refus si Telegram refuse ; Injoignable s'il ne répond pas."""
    cles = lire_reglages(dossier)
    jeton, discussion = cles.get("telegram_jeton", ""), cles.get("telegram_discussion", "")
    if jeton == "" or discussion == "":
        return False
    envoi = appeler_ok(appel, jeton, "sendMessage", {"chat_id": discussion, "text": message})
    if not envoi.get("ok"):
        raise Refus(f"Telegram a refusé le message ({_raison(envoi)}).")
    return True


def appeler_ok(appel, jeton, methode, corps):
    reponse = appel(jeton, methode, corps)
    return reponse if isinstance(reponse, dict) else {"ok": False}


def _raison(reponse):
    return reponse.get("description") or f"HTTP {reponse.get('status')}"


# ───────────────────────── relais des messages de l'EA (décision de l'utilisateur du 27/11/2026) ─────────────────────────
# MetaTrader pour Mac oublie l'autorisation WebRequest à chaque redémarrage : l'EA n'envoie plus Telegram. Il écrit un fichier par
# message, Etrave/telegram-<secondes>-<n°>-<symbole>.txt (« v1;<genre>;<numéro> », puis le texte avec ses **gras**), sous un nom
# provisoire puis renommé. Étrave les envoie dans l'ordre, en HTML (titres en gras), et les efface.
FICHIER_MESSAGE = re.compile(r"telegram-(\d+)-(\d{5})-([A-Za-z0-9._-]{1,40})\.txt")
RETARD_S = 30 * 60                  # au-delà, le message dit son heure : Étrave était fermée
GARDE_SANS_TELEGRAM_S = 24 * 3600   # Telegram pas configuré : les messages sont jetés après 24 heures
ENVOIS_MAX = 20                     # par passage ; Telegram accepte environ un message par seconde dans une discussion


def rendre_html(texte):
    """Le texte de l'EA en HTML de Telegram : & < > échappés d'abord (« S&P 500 »), puis **gras** en <b>gras</b>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(texte, quote=False))


def texte_brut(texte):
    return texte.replace("**", "")


def messages_en_attente(dossier):
    """Les messages déposés par l'EA, dans l'ordre : (secondes, n°, symbole, chemin). Les fichiers provisoires sont ignorés."""
    trouves = []
    for chemin in glob.glob(os.path.join(dossier, "telegram-*.txt")):
        m = FICHIER_MESSAGE.fullmatch(os.path.basename(chemin))
        if m:
            trouves.append((int(m.group(1)), int(m.group(2)), m.group(3), chemin))
    return sorted(trouves)


def _effacer(chemin):
    try:
        os.remove(chemin)
    except OSError:
        pass


def _mettre_de_cote(chemin):
    """Un message que Telegram refuse, ou illisible, est gardé à part (.refuse) : il ne bloque pas les suivants."""
    try:
        os.replace(chemin, chemin[:-len(".txt")] + ".refuse")
    except OSError:
        _effacer(chemin)


def relayer(dossier, appel=appeler, maintenant=None, attendre=time.sleep, pause_jusqu=0):
    """Envoie les messages de l'EA. Retourne l'état du relais : attente (messages restants), dernier (ok, injoignable, refus,
    pause, inactif ou vide), erreur, envoyes, pauseJusqu (Telegram a demandé d'attendre), essai (résultat de « Essai depuis
    MetaTrader »). Ne lève jamais d'erreur réseau : un message non envoyé reste pour le passage suivant, dans l'ordre."""
    maintenant = time.time() if maintenant is None else maintenant
    cles = lire_reglages(dossier)
    jeton, discussion = cles.get("telegram_jeton", ""), cles.get("telegram_discussion", "")
    messages = messages_en_attente(dossier)
    etat = {"attente": len(messages), "dernier": "", "quand": int(maintenant), "erreur": "", "envoyes": 0, "pauseJusqu": pause_jusqu,
            "essai": None}
    if jeton == "" or discussion == "":
        for quand, _, _, chemin in messages:
            if maintenant - quand > GARDE_SANS_TELEGRAM_S:
                _effacer(chemin)
        etat.update(attente=len(messages_en_attente(dossier)), dernier="inactif")
        return etat
    if maintenant < pause_jusqu:
        etat["dernier"] = "pause"
        return etat
    for rang, (quand, _, _, chemin) in enumerate(messages[:ENVOIS_MAX]):
        if rang:
            attendre(1.0)
        try:
            with open(chemin, "r", encoding="utf-8-sig", errors="replace") as f:
                brut = f.read().replace("\r\n", "\n")
        except OSError:
            continue
        entete, _, texte = brut.partition("\n")
        champs = entete.split(";")
        if len(champs) != 3 or champs[0] != "v1" or not texte.strip():
            _mettre_de_cote(chemin)
            etat["erreur"] = f"message illisible mis de côté ({os.path.basename(chemin)})"
            continue
        genre, numero = champs[1], champs[2]
        if maintenant - quand > RETARD_S:
            texte = texte.rstrip("\n") + "\n\n⏱ Envoyé en retard (message de " + time.strftime("%H:%M", time.localtime(quand)) + ")"
        try:
            reponse = appeler_ok(appel, jeton, "sendMessage", {"chat_id": discussion, "text": rendre_html(texte), "parse_mode": "HTML"})
            nouveau = (reponse.get("parameters") or {}).get("migrate_to_chat_id")
            if not reponse.get("ok") and isinstance(nouveau, int):
                # le groupe est devenu un supergroupe : son numéro a changé, Telegram donne le nouveau (suivi tout seul)
                local = lire_destination(dossier)
                brancher_discussion(dossier, str(nouveau), local["nom"], local["proprietaire"] or None)
                discussion = str(nouveau)
                reponse = appeler_ok(appel, jeton, "sendMessage", {"chat_id": discussion, "text": rendre_html(texte), "parse_mode": "HTML"})
            if not reponse.get("ok") and reponse.get("status") != 429:
                # le HTML refusé (balise mal formée…) : renvoyé une fois en texte simple
                reponse = appeler_ok(appel, jeton, "sendMessage", {"chat_id": discussion, "text": texte_brut(texte)})
        except Injoignable as erreur:
            etat.update(dernier="injoignable", erreur=str(erreur))
            break
        if not reponse.get("ok") and reponse.get("status") == 429:
            attente = (reponse.get("parameters") or {}).get("retry_after")
            attente = attente if isinstance(attente, (int, float)) and 0 < attente <= 3600 else 5
            etat.update(dernier="pause", pauseJusqu=int(maintenant + attente), erreur=f"Telegram demande d’attendre {int(attente)} s")
            break
        if not reponse.get("ok"):
            _mettre_de_cote(chemin)
            etat.update(dernier="refus", erreur=f"Telegram a refusé un message ({_raison(reponse)})")
            if genre == "essai":
                etat["essai"] = {"numero": numero, "resultat": "refus"}
            continue
        _effacer(chemin)
        etat["envoyes"] += 1
        etat["dernier"] = "ok"
        if genre == "essai":
            etat["essai"] = {"numero": numero, "resultat": "ok"}
    etat["attente"] = len(messages_en_attente(dossier))
    return etat


# ───────────────────────── détection de la discussion (décision de l'utilisateur du 27/11/2026) ─────────────────────────
COMMANDE_START = re.compile(r"/start(?:@(\w+))?(?:\s.*)?", re.S)


def proprietaire(dossier):
    """Le compte Telegram du propriétaire : celui enregistré, sinon celui de la discussion privée en cours. Vide : personne ne
    fait basculer les alertes (première installation : choix à la main dans Étrave)."""
    p = lire_destination(dossier)["proprietaire"]
    if p:
        return p
    d = lire_reglages(dossier).get("telegram_discussion", "")
    return d if re.fullmatch(r"\d{4,20}", d) else ""


def demande_de_bascule(nouvelle, bot, prop):
    """L'identifiant et le titre du groupe si cette nouvelle est une demande du propriétaire : il y a ajouté le bot, ou y a tapé
    /start (ou /start@<ce bot>). Sinon None. Un groupe où quelqu'un d'autre ajoute le bot n'est jamais choisi seul."""
    evt = nouvelle.get("message") or nouvelle.get("my_chat_member") or {}
    chat = evt.get("chat") or {}
    if not prop or chat.get("type") not in ("group", "supergroup") or str((evt.get("from") or {}).get("id", "")) != prop:
        return None
    if "my_chat_member" in nouvelle:
        if (evt.get("new_chat_member") or {}).get("status") not in ("member", "administrator"):
            return None
    else:
        m = COMMANDE_START.fullmatch((evt.get("text") or "").strip())
        if not m or (m.group(1) and m.group(1).lower() != (bot or "").lower()):
            return None
    return str(chat["id"]), chat.get("title") or ""
