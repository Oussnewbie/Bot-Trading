"""L'onglet Bitcoin d'Étrave : piloter le bot BTC (dossier bitcoin/) sans ligne de commande.

Le bot est un programme à part (il n'a rien à voir avec l'EA MetaTrader). Étrave et le bot se parlent par des fichiers :

    bitcoin/config.json           écrit par Étrave (mode, profil, levier, vente, ordres, coupe-circuit…), lu au démarrage
    <dossier Étrave>/btc-secrets.json
                                  clé et secret Binance + Telegram : ÉCRITURE SEULE, jamais renvoyés à la page
    bitcoin/etat/vivant.json   battement du bot (toutes les 15 s) : en marche, prochain cycle
    bitcoin/etat/etat.json     dernière décision, compte, stop de protection, coupe-circuit
    bitcoin/etat/journal.csv   une ligne par cycle (la courbe du capital)
    bitcoin/etat/PAUSE, FERMER, MAINTENANT, REARMER
                                  commandes : le bot les voit en moins de 15 s

Étrave n'a toujours besoin d'aucune bibliothèque : seul le bouton « Tester la connexion » utilise ccxt, s'il est installé.
"""
import csv
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

from pont import Refus, lire_reglages

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT = os.path.join(RACINE, "bitcoin")
ANCIEN_BOT = os.path.join(RACINE, "crypto", "bot")   # emplacement du bot avant la réorganisation du dépôt
CONFIG = os.path.join(BOT, "config.json")
PROFILS = os.path.join(BOT, "profils.json")
SECRETS = "btc-secrets.json"
BATTEMENT_S = 60                      # le bot réécrit vivant.json toutes les 15 s : au-delà d'une minute, il est arrêté

DEFAUT = dict(mode="papier", profil="prudent", levier=1, vente=0.25, ordres="limite", bande=0.05, perte_max=0.40,
              capital_papier=10_000)
LEVIER_A_CONFIRMER = 3
MOTS = {"reel": "REEL", "levier": "LEVIER", "fermer": "FERMER"}
CLE = re.compile(r"^[A-Za-z0-9]{40,100}$")


def _ecrire_json(chemin, donnees, secret=False):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    if secret:
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
    os.replace(tmp, chemin)


def _lire_json(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def reprendre_ancien_dossier(ancien=ANCIEN_BOT, nouveau=BOT, donnees=os.path.join(RACINE, "donnees", "crypto")):
    """Le bot était dans crypto/bot/ jusqu'au 17 novembre 2026. Ses fichiers locaux (hors git : config.json et etat/)
    restent là-bas après la mise à jour du dépôt : ils sont déplacés une fois dans bitcoin/, et le dossier d'état noté
    dans config.json suit. Rien n'est écrasé. Retourne la liste de ce qui a été repris."""
    faits = []
    vivant = os.path.join(ancien, "etat", "vivant.json")
    if os.path.exists(vivant) and time.time() - os.path.getmtime(vivant) < BATTEMENT_S:
        return faits                               # l'ancien bot tourne encore : on n'y touche pas
    for nom in ("config.json", "etat"):
        a, n = os.path.join(ancien, nom), os.path.join(nouveau, nom)
        if os.path.exists(a) and not os.path.exists(n):
            try:
                shutil.move(a, n)
                faits.append(nom)
            except OSError:
                pass
    cfg = os.path.join(nouveau, "config.json")
    c = _lire_json(cfg, None)
    meme = lambda x, y: os.path.normcase(os.path.abspath(x)) == os.path.normcase(os.path.abspath(y))  # noqa: E731
    if isinstance(c, dict) and c.get("dossier") and meme(c["dossier"], os.path.join(ancien, "etat")):
        c["dossier"] = os.path.join(nouveau, "etat")
        _ecrire_json(cfg, c)
        faits.append("dossier d'état")
    # les données crypto locales (hors git) : crypto/donnees/ -> donnees/crypto/
    a, n = os.path.join(os.path.dirname(ancien), "donnees"), donnees
    if os.path.isdir(a) and not os.path.exists(n):
        try:
            os.makedirs(os.path.dirname(n), exist_ok=True)
            shutil.move(a, n)
            faits.append("données crypto")
        except OSError:
            pass
    # l'ancien dossier, s'il ne reste que des fichiers de cache de Python
    for d in (ancien, os.path.dirname(ancien)):
        try:
            shutil.rmtree(os.path.join(d, "__pycache__"), ignore_errors=True)
            os.rmdir(d)
        except OSError:
            pass
    return faits


class Bitcoin:
    def __init__(self, dossier, config=CONFIG, lancer=None, tuer=None, tester=None):
        self.dossier = dossier                       # dossier d'Étrave (secrets)
        self.config = config
        self._lancer = lancer or self._lancer_processus
        self._tuer = tuer or self._tuer_processus
        self._tester = tester or self._tester_binance

    # ── chemins
    @property
    def f_secrets(self):
        return os.path.join(self.dossier, SECRETS)

    def cfg(self):
        c = dict(DEFAUT)
        c.update({k: v for k, v in (_lire_json(self.config, {}) or {}).items()})
        c.setdefault("dossier", os.path.join(os.path.dirname(self.config), "etat"))
        if not c.get("dossier"):
            c["dossier"] = os.path.join(os.path.dirname(self.config), "etat")
        return c

    def etat_dir(self):
        return self.cfg()["dossier"]

    # ── réglages
    def reglages_publics(self):
        c = self.cfg()
        r = {k: c.get(k) for k in ("mode", "profil", "levier", "vente", "ordres", "bande", "perte_max", "capital_papier")}
        if r["vente"] is None:                         # « null » = la vente du profil (quart de taille)
            r["vente"] = 0.25
        return r

    def regler(self, valeurs, confirmation=""):
        if not isinstance(valeurs, dict) or not valeurs:
            raise Refus("Aucun réglage reçu.")
        c = self.cfg()
        nouveau = {}
        for cle, v in valeurs.items():
            if cle == "mode":
                if v not in ("papier", "testnet", "reel"):
                    raise Refus("Mode : papier, testnet ou réel.")
                if v in ("testnet", "reel") and not self.cles()["renseignees"]:
                    raise Refus("Enregistre d’abord ta clé API Binance (onglet Connexion Binance).")
                if v == "reel" and c.get("mode") != "reel" and str(confirmation).strip().upper() != MOTS["reel"]:
                    raise Refus("Passer en argent réel : tape le mot REEL pour confirmer.")
            elif cle == "profil":
                if v not in ("prudent", "equilibre"):
                    raise Refus("Profil : prudent ou équilibré.")
            elif cle == "levier":
                if isinstance(v, bool) or not isinstance(v, (int, float)) or int(v) != v or not 1 <= v <= 10:
                    raise Refus("Levier : un nombre entier de 1 à 10.")
                v = int(v)
                if v > LEVIER_A_CONFIRMER and v > int(c.get("levier", 1)) and str(confirmation).strip().upper() != MOTS["levier"]:
                    raise Refus(f"Levier ×{v} : au-delà de ×{LEVIER_A_CONFIRMER}, le test montre des pertes de 70 à 100 %. "
                                "Tape le mot LEVIER pour confirmer.")
            elif cle == "vente":
                if v not in (0, 0.25, 0.5):
                    raise Refus("Vente : 0 (désactivée), 0,25 ou 0,5.")
            elif cle == "ordres":
                if v not in ("limite", "marche"):
                    raise Refus("Ordres : limite ou marché.")
            elif cle == "bande":
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.01 <= v <= 0.20:
                    raise Refus("Ajustement minimal : entre 1 % et 20 %.")
            elif cle == "perte_max":
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.10 <= v <= 0.90:
                    raise Refus("Coupe-circuit : entre 10 % et 90 % de baisse.")
            elif cle == "capital_papier":
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 100 <= v <= 10_000_000:
                    raise Refus("Capital du mode papier : entre 100 et 10 000 000.")
            else:
                raise Refus(f"Réglage inconnu : {cle}")
            nouveau[cle] = v
        changees = [k for k, v in nouveau.items() if c.get(k) != v]
        if changees:
            c.update(nouveau)
            c["reel_confirme"] = c["mode"] == "reel"
            c["fichier_secrets"] = self.f_secrets
            _ecrire_json(self.config, c)
        return changees

    # ── clés
    def cles(self):
        s = _lire_json(self.f_secrets, {}) or {}
        cle = s.get("binance_cle") or ""
        return dict(renseignees=bool(cle and s.get("binance_secret")), fin=cle[-4:] if cle else None,
                    telegram=bool(s.get("telegram_jeton") and s.get("telegram_discussion")))

    def enregistrer_cles(self, cle, secret):
        cle, secret = str(cle or "").strip(), str(secret or "").strip()
        if not CLE.match(cle) or not CLE.match(secret):
            raise Refus("Clé ou secret Binance invalide : ce sont deux longues suites de lettres et de chiffres "
                        "(64 caractères), copiées depuis Binance > Gestion des API.")
        s = _lire_json(self.f_secrets, {}) or {}
        s.update(binance_cle=cle, binance_secret=secret)
        self._telegram(s)
        _ecrire_json(self.f_secrets, s, secret=True)
        self._ecrire_chemin_secrets()
        return self.cles()

    def effacer_cles(self):
        s = _lire_json(self.f_secrets, {}) or {}
        s.pop("binance_cle", None); s.pop("binance_secret", None)
        _ecrire_json(self.f_secrets, s, secret=True)
        c = self.cfg()
        if c.get("mode") != "papier":
            c["mode"], c["reel_confirme"] = "papier", False
            _ecrire_json(self.config, c)
        return self.cles()

    def _telegram(self, s):
        """Le bot utilise le même Telegram que l'EA : on recopie ce qui est enregistré dans l'onglet Connexions."""
        r = lire_reglages(self.dossier)
        if r.get("telegram_jeton") and r.get("telegram_discussion"):
            s.update(telegram_jeton=r["telegram_jeton"], telegram_discussion=r["telegram_discussion"])

    def _ecrire_chemin_secrets(self):
        c = self.cfg()
        if c.get("fichier_secrets") != self.f_secrets:
            c["fichier_secrets"] = self.f_secrets
            _ecrire_json(self.config, c)

    def tester(self):
        s = _lire_json(self.f_secrets, {}) or {}
        if not (s.get("binance_cle") and s.get("binance_secret")):
            raise Refus("Aucune clé Binance enregistrée.")
        return self._tester(s["binance_cle"], s["binance_secret"], self.cfg().get("mode") == "testnet")

    @staticmethod
    def _tester_binance(cle, secret, testnet):
        if importlib.util.find_spec("ccxt") is None:
            raise Refus("Le module ccxt n’est pas installé : dans une fenêtre de commande, tape  pip install ccxt pandas numpy")
        import ccxt
        try:
            opts = dict(apiKey=cle, secret=secret, enableRateLimit=True, timeout=15000)
            spot, fut = ccxt.binance(opts), ccxt.binanceusdm(opts)
            if testnet:
                spot.set_sandbox_mode(True); fut.set_sandbox_mode(True)
            bs, bf = spot.fetch_balance(), fut.fetch_balance()
        except Exception as e:  # noqa: BLE001
            texte = str(e)
            for secret_ in (cle, secret):
                texte = texte.replace(secret_, "***")
            if "restricted location" in texte:
                raise Refus("Binance refuse cette connexion depuis ce pays (restricted location).") from None
            if "Invalid API-key" in texte or "-2015" in texte or "-2014" in texte:
                raise Refus("Clé refusée par Binance : vérifie la clé, l’adresse IP autorisée et les droits « spot » "
                            "et « futures ».") from None
            raise Refus(f"Binance injoignable : {texte[:160]}") from None
        return dict(ok=True, usdt_spot=float(bs.get("USDT", {}).get("total") or 0), btc_spot=float(bs.get("BTC", {}).get("total") or 0),
                    usdt_futures=float(bf.get("USDT", {}).get("total") or 0), testnet=testnet)

    # ── le processus du bot
    def processus(self):
        v = _lire_json(os.path.join(self.etat_dir(), "vivant.json"))
        if not v:
            return dict(en_marche=False)
        try:
            age = time.time() - _horodatage(v.get("heure"))
        except (TypeError, ValueError):
            age = 1e9
        return dict(en_marche=age < BATTEMENT_S, age_s=round(age), statut=v.get("statut"),
                    prochain_cycle=v.get("prochain_cycle"), mode=v.get("mode"), levier=v.get("levier"), pid=v.get("pid"))

    def dependances(self):
        return {m: importlib.util.find_spec(m) is not None for m in ("pandas", "numpy", "ccxt")}

    def demarrer(self):
        if self.processus()["en_marche"]:
            raise Refus("Le bot tourne déjà.")
        manque = [m for m, ok in self.dependances().items() if not ok and m != "ccxt"]
        if self.cfg().get("mode") != "papier" and not self.dependances()["ccxt"]:
            manque.append("ccxt")
        if manque:
            raise Refus(f"Il manque {', '.join(manque)} : dans une fenêtre de commande, tape  pip install {' '.join(manque)}")
        c = self.cfg()
        if c.get("mode") != "papier" and not self.cles()["renseignees"]:
            raise Refus("Enregistre d’abord ta clé API Binance.")
        s = _lire_json(self.f_secrets, {}) or {}
        self._telegram(s)
        _ecrire_json(self.f_secrets, s, secret=True)
        c["fichier_secrets"] = self.f_secrets
        _ecrire_json(self.config, c)
        os.makedirs(self.etat_dir(), exist_ok=True)
        pid = self._lancer([sys.executable, os.path.join(BOT, "bot.py"), "--config", self.config], self.etat_dir())
        return dict(ok=True, pid=pid)

    def arreter(self):
        p = self.processus()
        pid = p.get("pid") or _lire_pid(self.etat_dir())
        if not pid:
            raise Refus("Le bot ne tourne pas.")
        self._tuer(int(pid))
        try:
            os.remove(os.path.join(self.etat_dir(), "vivant.json"))
        except OSError:
            pass
        return dict(ok=True)

    @staticmethod
    def _lancer_processus(commande, dossier):
        journal = open(os.path.join(dossier, "console.log"), "a", encoding="utf-8")
        opts = dict(stdout=journal, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=RACINE)
        if sys.platform.startswith("win"):
            opts["creationflags"] = 0x00000008 | 0x00000200        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            opts["start_new_session"] = True
        return subprocess.Popen(commande, **opts).pid

    @staticmethod
    def _tuer_processus(pid):
        if sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    # ── commandes
    def _drapeau(self, nom, present=True):
        p = os.path.join(self.etat_dir(), nom)
        os.makedirs(self.etat_dir(), exist_ok=True)
        if present:
            open(p, "w").close()
        elif os.path.exists(p):
            os.remove(p)

    def pause(self, active):
        self._drapeau("PAUSE", bool(active))
        return dict(ok=True, pause=bool(active))

    def fermer(self, confirmation):
        if str(confirmation).strip().upper() != MOTS["fermer"]:
            raise Refus("Tout fermer : tape le mot FERMER pour confirmer.")
        self._drapeau("FERMER"); self._drapeau("MAINTENANT")
        return dict(ok=True)

    def analyser(self):
        self._drapeau("MAINTENANT")
        return dict(ok=True)

    def rearmer(self):
        if self.processus()["en_marche"]:                 # le bot le fera lui-même dans les 15 secondes
            self._drapeau("REARMER"); self._drapeau("MAINTENANT")
            return dict(ok=True)
        f = os.path.join(self.etat_dir(), "etat.json")
        e = _lire_json(f, {}) or {}
        e.pop("arrete", None)
        e["pic"] = (e.get("compte") or {}).get("capital", e.get("pic"))
        _ecrire_json(f, e)
        return dict(ok=True)

    # ── tout ce que la page affiche
    def etat(self):
        d = self.etat_dir()
        e = _lire_json(os.path.join(d, "etat.json"), {}) or {}
        return dict(
            reglages=self.reglages_publics(), cles=self.cles(), processus=self.processus(), dependances=self.dependances(),
            decision=e.get("derniere_decision"), compte=e.get("compte"), stop=e.get("stop"), arrete=e.get("arrete"),
            erreur=e.get("derniere_erreur"), pic=e.get("pic"),
            drapeaux={n.lower(): os.path.exists(os.path.join(d, n)) for n in ("PAUSE", "FERMER", "MAINTENANT")},
            journal=lire_journal(os.path.join(d, "journal.csv")), log=queue_log(os.path.join(d, "bot.log")),
            profils=_lire_json(PROFILS, {}) or {})


def _horodatage(texte):
    """Secondes depuis 1970 d'un horodatage ISO écrit par pandas (« 2026-11-17 10:59:01.2+00:00 »)."""
    from datetime import datetime
    return datetime.fromisoformat(str(texte).replace(" ", "T")).timestamp()


def _lire_pid(dossier):
    try:
        with open(os.path.join(dossier, "bot.pid")) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def lire_journal(chemin, nombre=1500):
    try:
        with open(chemin, encoding="utf-8", newline="") as f:
            lignes = list(csv.DictReader(f))
    except OSError:
        return []
    out = []
    for l in lignes[-nombre:]:
        try:
            out.append(dict(heure=l["heure"][:19], prix=float(l["prix"]), score=float(l["score"]), tendance=l.get("tendance_4h"),
                            cible=float(l["cible"]), capital=float(l["capital"]), exposition=float(l["exposition"]),
                            ordres=l.get("ordres") or "", motif=l.get("motif") or ""))
        except (KeyError, ValueError):
            continue
    return out


def queue_log(chemin, nombre=40):
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            return [l.rstrip("\n")[:400] for l in f.readlines()[-nombre:]]
    except OSError:
        return []
