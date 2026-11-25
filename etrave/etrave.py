#!/usr/bin/env python3
"""Étrave : l'interface de l'EA Strategy V10 (indices US) — une page web servie sur cet ordinateur uniquement.

    python etrave/etrave.py                 démarre et ouvre la page dans le navigateur
    python etrave/etrave.py --port 8790     autre port (8788 par défaut)
    python etrave/etrave.py --sans-navigateur

Aucune dépendance : Python 3.8 ou plus récent suffit. L'interface ne passe aucun ordre : elle écrit des réglages et des
demandes que l'EA lit (voir pont.py). La fermer ne change rien à l'EA ni à ses alertes.

Sécurité, comme le dashboard de Vigie — cette page peut changer le risque et fermer un trade, donc :
 - le serveur n'écoute que sur 127.0.0.1 : il est invisible depuis le réseau ;
 - chaque appel doit porter un jeton tiré au hasard au démarrage et glissé dans la page ;
 - l'en-tête Host doit être local : un site web ne peut pas se faire passer pour cette page (« DNS rebinding ») ;
 - aucune autorisation n'est donnée aux autres origines, et la page ne charge aucune ressource extérieure.
"""
import argparse
import hmac
import json
import os
import re
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import export  # noqa: E402
import mt5  # noqa: E402
import pont  # noqa: E402
import risque  # noqa: E402
import telegram  # noqa: E402

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")
ICI = os.path.dirname(os.path.abspath(__file__))            # le dossier etrave/ (avec Etrave.bat)
RACINE = os.path.dirname(ICI)
SOURCE_EA = os.path.join(RACINE, "robot", "Strategy-V10.mq5")
PORT = 8788
CORPS_MAX = 64 * 1024
EN_TETE_JETON = "x-etrave-jeton"
# `tasklist` lance un programme : on ne le redemande pas à chaque rafraîchissement de la page.
MT5_OUVERT_CACHE_S = 5.0
# Export trimestriel automatique : au démarrage, puis toutes les 6 heures (un trimestre terminé est exporté une seule fois).
EXPORT_PERIODE_S = 6 * 3600
# Correctif ET-09 (audit du 25/11/2026) : fullmatch partout. Avec match, « $ » acceptait un retour à la ligne final.
TRIMESTRE = re.compile(r"\d{4}-T[1-4]")


class Erreur(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Application:
    """Les routes de l'interface, sans le transport HTTP (les tests l'appellent directement)."""

    def __init__(self, dossier, appel_telegram=None, mt5_ouvert=None, mt5_lancer=None, mt5_installer=None, mt5_demarrage=None, journal=None):
        self.dossier = dossier
        self.appel_telegram = appel_telegram or telegram.appeler
        self._mt5_ouvert = mt5_ouvert or mt5.est_ouvert
        self._mt5_lancer = mt5_lancer or mt5.lancer
        self._mt5_installer = mt5_installer or mt5.installer_ea
        self._mt5_demarrage = mt5_demarrage or mt5.demarrage_windows
        self.journal = journal or (lambda message: None)
        self._ouvert = (0.0, None)

    # ── ce que la page affiche
    def etat(self):
        etats = pont.lire_etats(self.dossier)
        return {
            "nom": pont.NOM,
            "reglages": pont.reglages_publics(self.dossier),
            "eas": [{cle: valeur for cle, valeur in e.items() if cle != "terminal"} for e in etats],
            "mt5": self.mt5(etats),
        }

    def mt5(self, etats):
        en_marche = any(e["en_marche"] for e in etats)
        quand, ouvert = self._ouvert
        if time.time() - quand > MT5_OUVERT_CACHE_S:
            ouvert = self._mt5_ouvert()
            self._ouvert = (time.time(), ouvert)
        connus = mt5.terminaux(etats)
        return {
            "windows": sys.platform.startswith("win"),
            "ouvert": True if en_marche else ouvert,
            "terminaux": [{"id": i, "dossier": os.path.basename(os.path.dirname(chemin))} for i, chemin in enumerate(connus)],
            "demarrageWindows": bool(mt5.fichier_demarrage() and os.path.exists(mt5.fichier_demarrage())),
        }

    def _terminal(self, corps, etats):
        connus = mt5.terminaux(etats)
        choix = corps.get("terminal", 0)
        chemin = connus[choix] if isinstance(choix, int) and not isinstance(choix, bool) and 0 <= choix < len(connus) else None
        return chemin, connus

    def ouvrir_mt5_si_demande(self):
        """Au démarrage d'Étrave : ouvre MetaTrader s'il est fermé et que l'option est cochée. Ne lève jamais d'erreur."""
        try:
            if not pont.reglages_publics(self.dossier)["mt5Auto"] or self._mt5_ouvert() is not False:
                return False
            connus = mt5.terminaux(pont.lire_etats(self.dossier))
            if not connus:
                return False
            self._mt5_lancer(connus[0], connus, None, ouvert=False)
            self.journal("MetaTrader 5 ouvert automatiquement")
            return True
        except Exception:
            return False

    def exporter_trimestres_finis(self):
        """Exporte les trimestres terminés qui n'ont pas encore d'export. Ne lève jamais d'erreur : un export raté se refait au passage suivant."""
        try:
            for trimestre in export.exporter_trimestres_finis(self.dossier):
                self.journal(f"export du trimestre {trimestre} écrit dans {export.dossier_exports(self.dossier)}")
        except Exception as erreur:
            self.journal(f"export trimestriel impossible ({type(erreur).__name__}), nouvel essai plus tard")

    def exports(self):
        return {"exports": export.exports_faits(self.dossier), "dossier": export.dossier_exports(self.dossier),
                "enCours": export.trimestre_de(export.aujourdhui_ny())}

    # ── routes
    def traiter(self, methode, chemin, parametres, corps):
        route = f"{methode} {chemin}"
        if route == "GET /api/etat":
            return self.etat()
        if route == "GET /api/trades":
            return {"trades": pont.lire_trades(self.dossier)}
        if route == "GET /api/exports":
            return self.exports()
        if route == "POST /api/exports":
            trimestre = corps.get("trimestre") or export.trimestre_de(export.aujourdhui_ny())
            if not isinstance(trimestre, str) or not TRIMESTRE.fullmatch(trimestre):
                raise Erreur(400, "Trimestre illisible : il a la forme 2027-T1.")
            chemin_export, resume = export.exporter(self.dossier, trimestre)
            self.journal(f"export du trimestre {trimestre} écrit dans {chemin_export}")
            return {"ok": True, "trimestre": trimestre, "chemin": chemin_export, "resume": resume, **self.exports()}
        if route == "GET /api/risque":
            pct, levier = pont._nombre(parametres.get("pct")), pont._nombre(parametres.get("levier"))
            if pct is None or not (pont.RISQUE_MIN - 1e-9 <= pct <= pont.RISQUE_MAX + 1e-9):
                raise Erreur(400, "Risque hors bornes")
            if levier is not None and not (1 <= levier <= pont.LEVIER_MAX):
                levier = None
            return risque.simuler(pct, levier)
        if route == "POST /api/reglages":
            changees = pont.regler(self.dossier, corps.get("valeurs"), corps.get("confirmation", ""))
            if changees:
                self.journal(f"réglages modifiés : {', '.join(changees)}")
            return {"ok": True, "changees": changees, "reglages": pont.reglages_publics(self.dossier)}
        if route == "POST /api/connexions":
            changees = pont.enregistrer_connexions(self.dossier, corps.get("valeurs"))
            if changees:
                self.journal(f"connexions modifiées : {', '.join(changees)}")
            return {"ok": True, "changees": changees, "reglages": pont.reglages_publics(self.dossier)}
        if route == "POST /api/connexions/telegram-test":
            message = f"✅ Essai réussi : les alertes de {pont.NOM} arriveront ici."
            return {"ok": True, **telegram.verifier(self.dossier, message, self.appel_telegram)}
        if route == "POST /api/connexions/telegram-test-mt5":
            if not any(e["en_marche"] for e in pont.lire_etats(self.dossier)):
                raise Erreur(409, "L’EA ne tourne pas : ouvre MetaTrader 5 et pose l’EA sur un graphique, puis réessaie.")
            return {"ok": True, "numero": pont.demander_essai_mt5(self.dossier)}
        if route == "POST /api/cloturer":
            etats = [e for e in pont.lire_etats(self.dossier) if e["symbole"] == corps.get("symbole")]
            if not etats or not etats[0]["en_marche"]:
                raise Erreur(409, "L’EA de ce symbole ne tourne pas : ferme le trade directement dans MetaTrader 5.")
            numero = pont.demander_cloture(self.dossier, corps.get("symbole"), corps.get("confirmation", ""))
            self.journal(f"clôture demandée sur {corps.get('symbole')}")
            return {"ok": True, "numero": numero}
        if route == "POST /api/mt5/lancer":
            etats = pont.lire_etats(self.dossier)
            chemin, connus = self._terminal(corps, etats)
            identifiants = None
            if corps.get("connexion"):
                identifiants = (corps.get("login"), corps.get("motDePasse"), corps.get("serveur"))
            ouvert = any(e["en_marche"] for e in etats) or bool(self._mt5_ouvert())
            resultat = self._mt5_lancer(chemin, connus, identifiants, ouvert=ouvert)
            self._ouvert = (0.0, None)
            self.journal("MetaTrader 5 lancé" + (" avec connexion à un compte" if identifiants else ""))
            if identifiants:                                    # le compte et le serveur sont retenus, jamais le mot de passe
                pont.retenir_mt5(self.dossier, login=str(identifiants[0]).strip(), serveur=str(identifiants[2]).strip())
            return {"ok": True, **resultat}
        if route == "POST /api/mt5/installer":
            chemin, connus = self._terminal(corps, pont.lire_etats(self.dossier))
            resultat = self._mt5_installer(chemin, connus, SOURCE_EA)
            self.journal("EA copié dans MetaTrader 5" + (" et compilé" if resultat.get("compile") else ""))
            return {"ok": True, **resultat}
        if route == "POST /api/mt5/options":
            if isinstance(corps.get("auto"), bool):
                pont.retenir_mt5(self.dossier, auto=corps["auto"])
            demarrage = None
            if isinstance(corps.get("demarrageWindows"), bool):
                demarrage = self._mt5_demarrage(corps["demarrageWindows"], ICI)
            return {"ok": True, "reglages": pont.reglages_publics(self.dossier), "demarrageWindows": demarrage}
        raise Erreur(404, "Route inconnue")


class Serveur(ThreadingHTTPServer):
    """Correctif ET-05 (audit du 25/11/2026) : HTTPServer active SO_REUSEADDR. Sous Windows, cette option laisse un deuxième
    programme écouter sur un port déjà pris : une deuxième Étrave (raccourci de démarrage puis double-clic sur Etrave.bat)
    démarrait sur le même port, chacune avec son jeton, et la page recevait au hasard « Jeton absent ou invalide ».
    Sous Windows, le port est donc réservé (SO_EXCLUSIVEADDRUSE) : la deuxième voit le port pris et ouvre la première."""
    allow_reuse_address = not sys.platform.startswith("win")

    def server_bind(self):
        if sys.platform.startswith("win") and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def creer_serveur(dossier, port=PORT, **options):
    """Le serveur HTTP local. `serveur.jeton` et `serveur.url` servent aux tests et au lancement."""
    application = Application(dossier, **options)
    jeton = secrets.token_hex(24)

    class Requete(BaseHTTPRequestHandler):
        server_version = "Etrave"
        sys_version = ""

        def log_message(self, *arguments):   # pas de journal par requête : la page interroge toutes les 2 secondes
            pass

        def repondre(self, code, corps, type_contenu="application/json; charset=utf-8"):
            donnees = corps.encode("utf-8") if isinstance(corps, str) else json.dumps(corps, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            for nom, valeur in (
                ("content-type", type_contenu), ("content-length", str(len(donnees))), ("cache-control", "no-store"),
                ("x-content-type-options", "nosniff"), ("x-frame-options", "DENY"), ("referrer-policy", "no-referrer"),
                # la page n'a besoin d'aucune ressource extérieure
                ("content-security-policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                            "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"),
            ):
                self.send_header(nom, valeur)
            self.end_headers()
            self.wfile.write(donnees)

        def servir(self, methode):
            try:
                port_reel = self.server.server_address[1]
                if self.headers.get("host", "") not in (f"127.0.0.1:{port_reel}", f"localhost:{port_reel}"):
                    raise Erreur(403, "Accès réservé à cet ordinateur (http://127.0.0.1)")
                url = urllib.parse.urlsplit(self.path)
                if methode == "GET" and url.path == "/":
                    with open(PAGE, "r", encoding="utf-8") as f:
                        page = f.read()
                    page = page.replace("__JETON__", jeton).replace("__NOM__", pont.NOM).replace("__SLOGAN__", pont.SLOGAN)
                    return self.repondre(200, page, "text/html; charset=utf-8")
                if not url.path.startswith("/api/"):
                    raise Erreur(404, "Page inconnue")
                donne = self.headers.get(EN_TETE_JETON, "")
                if not hmac.compare_digest(donne.encode("utf-8"), jeton.encode("utf-8")):
                    raise Erreur(401, "Jeton absent ou invalide : recharge la page")
                corps = {}
                if methode == "POST":
                    if "application/json" not in self.headers.get("content-type", ""):
                        raise Erreur(415, "JSON attendu")
                    try:
                        taille = int(self.headers.get("content-length", "0"))
                    except ValueError:
                        raise Erreur(400, "Requête illisible") from None
                    if taille > CORPS_MAX:
                        raise Erreur(413, "Requête trop volumineuse")
                    try:
                        corps = json.loads(self.rfile.read(taille).decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        raise Erreur(400, "JSON illisible") from None
                    if not isinstance(corps, dict):
                        raise Erreur(400, "JSON illisible")
                parametres = {cle: valeurs[-1] for cle, valeurs in urllib.parse.parse_qs(url.query).items()}
                self.repondre(200, application.traiter(methode, url.path, parametres, corps))
            except Erreur as erreur:
                self.repondre(erreur.code, {"ok": False, "error": str(erreur)})
            except pont.Refus as refus:
                self.repondre(422, {"ok": False, "error": str(refus)})
            except telegram.Injoignable as erreur:
                # le message est déjà nettoyé de tout jeton (voir telegram.appeler)
                self.repondre(502, {"ok": False, "error": f"{erreur}. Vérifie ta connexion internet."})
            except Exception as erreur:   # jamais de détail technique vers la page
                application.journal(f"erreur interne ({type(erreur).__name__})")
                self.repondre(500, {"ok": False, "error": "Erreur interne de l’interface"})

        def do_GET(self):
            self.servir("GET")

        def do_POST(self):
            self.servir("POST")

    # 127.0.0.1 uniquement : jamais d'écoute sur le réseau.
    serveur = Serveur(("127.0.0.1", port), Requete)
    serveur.daemon_threads = True
    serveur.jeton = jeton
    serveur.application = application
    serveur.url = f"http://127.0.0.1:{serveur.server_address[1]}"
    return serveur


def deja_lancee(port):
    """Une interface Étrave répond-elle déjà sur ce port ?"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1.5) as reponse:
            return f"<title>{pont.NOM}" in reponse.read(4096).decode("utf-8", "replace")
    except (OSError, urllib.error.URLError):
        return False


def reprendre_ancienne_organisation():
    """Après la réorganisation du dépôt (17 novembre 2026) : lancement au démarrage de Windows redirigé vers
    etrave/Etrave.bat (il visait Etrave.bat à la racine du dépôt)."""
    fichier = mt5.fichier_demarrage()
    try:
        if fichier and os.path.exists(fichier) and os.path.join(RACINE, "Etrave.bat") in open(fichier, encoding="utf-8").read():
            mt5.demarrage_windows(True, ICI)
            print("Lancement au démarrage de Windows mis à jour : " + os.path.join(ICI, "Etrave.bat"))
    except OSError:
        pass


def main(arguments=None):
    lecteur = argparse.ArgumentParser(description=f"{pont.NOM} : l'interface de l'EA Strategy V10")
    lecteur.add_argument("--port", type=int, default=int(os.environ.get("ETRAVE_PORT", PORT)))
    lecteur.add_argument("--dossier", default=None, help="dossier partagé avec l'EA (par défaut : dossier commun de MetaTrader)")
    lecteur.add_argument("--sans-navigateur", action="store_true")
    options = lecteur.parse_args(arguments)
    dossier = options.dossier or pont.dossier_commun()
    os.makedirs(dossier, exist_ok=True)
    reprendre_ancienne_organisation()
    mt5.effacer_connexions_oubliees()   # mot de passe laissé par un arrêt brutal pendant un lancement de MetaTrader

    def journal(message):
        print(f"{time.strftime('%H:%M:%S')}  {message}", flush=True)

    try:
        serveur = creer_serveur(dossier, options.port, journal=journal)
    except OSError:
        if deja_lancee(options.port):
            print(f"{pont.NOM} tourne déjà : http://127.0.0.1:{options.port}")
            if not options.sans_navigateur:
                webbrowser.open(f"http://127.0.0.1:{options.port}")
            return 0
        print(f"Le port {options.port} est pris par un autre programme. Essaie : python etrave/etrave.py --port {options.port + 1}")
        return 1
    print(f"{pont.NOM} — l'EA Strategy V10 (indices US)")
    print(f"  page     : {serveur.url}   (cet ordinateur uniquement)")
    print(f"  dossier  : {dossier}")
    print("  Laisse cette fenêtre ouverte tant que tu utilises la page. La fermer n'arrête ni l'EA ni ses alertes.")
    if not options.sans_navigateur:
        threading.Timer(0.6, lambda: webbrowser.open(serveur.url)).start()
    threading.Timer(1.0, serveur.application.ouvrir_mt5_si_demande).start()

    def exporter_puis_reprogrammer():
        serveur.application.exporter_trimestres_finis()
        minuterie = threading.Timer(EXPORT_PERIODE_S, exporter_puis_reprogrammer)
        minuterie.daemon = True
        minuterie.start()
    depart = threading.Timer(5.0, exporter_puis_reprogrammer)
    depart.daemon = True
    depart.start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
