#!/usr/bin/env python3
"""Étrave : l'interface de l'EA Strategy V11 (indices US) — une page web servie sur cet ordinateur uniquement.

    python etrave/etrave.py                 démarre et ouvre la page dans le navigateur
    python etrave/etrave.py --port 8790     autre port (8788 par défaut)
    python etrave/etrave.py --sans-navigateur
    python etrave/etrave.py --tout          ouvre aussi MetaTrader 5 (Mac : double-clic sur etrave/Etrave.command)

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
import fin_de_journee  # noqa: E402
import mt5  # noqa: E402
import pont  # noqa: E402
import risque  # noqa: E402
import telegram  # noqa: E402

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")
ICI = os.path.dirname(os.path.abspath(__file__))            # le dossier etrave/ (avec Etrave.bat)
RACINE = os.path.dirname(ICI)
SOURCE_EA = os.path.join(RACINE, "robot", "Strategy-V11.mq5")
PORT = 8788
CORPS_MAX = 64 * 1024
EN_TETE_JETON = "x-etrave-jeton"
# `tasklist` lance un programme : on ne le redemande pas à chaque rafraîchissement de la page.
MT5_OUVERT_CACHE_S = 5.0
# Export trimestriel automatique : au démarrage, puis toutes les 6 heures (un trimestre terminé est exporté une seule fois).
EXPORT_PERIODE_S = 6 * 3600
# AUD-09 (audit du 26/11/2026) : l'interrupteur (export.interrupteurs, seuils par marché) vérifié toutes les 10 minutes par une
# minuterie de main, jamais à chaque appel de la page ; un franchissement déjà annoncé sur Telegram est retenu dans ce fichier.
INTERRUPTEUR_PERIODE_S = 10 * 60
# Fin de journée (27/11/2026) : chaque minute, Étrave regarde si la séance est close pour lancer l'outil vidéo (fin_de_journee.py).
VIDEO_PERIODE_S = 60
FICHIER_INTERRUPTEUR = "interrupteur.txt"
# AUD-22 (audit du 26/11/2026) : double-clic dont l'installation ou la compilation de l'EA a échoué (MetaTrader pas lancé). Un
# fichier du dossier d'Étrave, pas une variable : le double-clic, Étrave déjà lancée, passe par un autre processus que la page.
FICHIER_LANCEMENT = "lancement.json"
# Correctif ET-09 (audit du 25/11/2026) : fullmatch partout. Avec match, « $ » acceptait un retour à la ligne final.
TRIMESTRE = re.compile(r"\d{4}-T[1-4]")


class Erreur(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def occupes(etats):
    """Les EA qui ont un trade ou un ordre : (symboles des EA en marche, états des EA muets dont le DERNIER état le disait).
    AUD-19 / AUD-21 (audit du 26/11/2026) : seuls les EA en marche étaient regardés ; un EA gelé ou un MetaTrader planté en
    pleine séance laissait fermer MetaTrader ou recompiler l'EA sans un mot."""
    occupe = lambda e: e["position"] or e["attente"] or (e["jambes"] or 0) > 0
    return [e["symbole"] for e in etats if e["en_marche"] and occupe(e)], [e for e in etats if not e["en_marche"] and occupe(e)]


def _muets_txt(muets):
    return " et ".join(f"{e['symbole']} (dernier état il y a {int(e['age_s'] // 60)} min)" if e["age_s"] >= 120 else
                       f"{e['symbole']} (dernier état il y a {int(e['age_s'])} s)" for e in muets)


class Application:
    """Les routes de l'interface, sans le transport HTTP (les tests l'appellent directement)."""

    def __init__(self, dossier, appel_telegram=None, mt5_ouvert=None, mt5_lancer=None, mt5_installer=None, mt5_demarrage=None,
                 mt5_fermer=None, mt5_terminaux=None, journal=None, video_lancer=None, video_dossier=None, video_python=None):
        self.dossier = dossier
        self.appel_telegram = appel_telegram or telegram.appeler
        self._mt5_ouvert = mt5_ouvert or mt5.est_ouvert
        self._mt5_lancer = mt5_lancer or mt5.lancer
        self._mt5_installer = mt5_installer or mt5.installer_ea
        self._mt5_demarrage = mt5_demarrage or mt5.demarrage_windows
        self._mt5_fermer = mt5_fermer or mt5.fermer
        self._mt5_terminaux = mt5_terminaux or mt5.terminaux
        self.journal = journal or (lambda message: None)
        self._ouvert = (0.0, None)
        self._interrupteur = None                       # AUD-09 : dernière vérification (verifier_interrupteur)
        self._interrupteur_annonce = set()              # franchissements déjà écrits dans le journal par ce processus
        self._verrou_interrupteur = threading.Lock()
        # Fin de journée : l'outil vidéo installé, lancé une fois par jour quand la séance est close (injectés par les tests)
        self._video_lancer = video_lancer or fin_de_journee.lancer
        self._video_dossier = video_dossier or fin_de_journee.dossier_outil_video()
        self._video_python = video_python
        self._video_attente = ""
        self._verrou_video = threading.Lock()

    # ── ce que la page affiche
    def etat(self):
        etats = pont.lire_etats(self.dossier)
        return {
            "nom": pont.NOM,
            "reglages": pont.reglages_publics(self.dossier),
            "eas": [{cle: valeur for cle, valeur in e.items() if cle != "terminal"} for e in etats],
            "mt5": self.mt5(etats),
            "lancement": self.lancement(self._mt5_terminaux(etats)),
            # AUD-09 : la dernière vérification de l'interrupteur (None avant la première), par symbole et avec son marché
            "interrupteur": self._interrupteur,
            "alertes": pont.lire_alertes(self.dossier),     # alertes de sécurité de l'EA (27/11/2026 : ici, plus sur Telegram)
            "video": self.video(),
        }

    # ── fin de journée : l'outil vidéo (demande de l'utilisateur du 27/11/2026)
    def video(self):
        return {"installe": fin_de_journee.installe(self._video_dossier), "derniere": fin_de_journee.derniere(self.dossier),
                "attente": self._video_attente}

    def verifier_fin_de_journee(self, etats=None, maintenant=None):
        """Lance l'outil vidéo une fois par jour de New York, quand la séance est close (fin_de_journee.pret). Retourne True s'il
        vient d'être lancé. Ne lève jamais d'erreur : la tâche programmée de l'outil vidéo reste en secours."""
        with self._verrou_video:
            try:
                etats = pont.lire_etats(self.dossier) if etats is None else etats
                if not fin_de_journee.installe(self._video_dossier):
                    self._video_attente = "outil vidéo pas installé"
                    return False
                jour = fin_de_journee.heure_ny(maintenant).date().isoformat()
                deja = fin_de_journee.derniere(self.dossier)
                if deja and deja["jour"] == jour:
                    self._video_attente = ""
                    return False
                pret, attente = fin_de_journee.pret(etats, self.dossier, maintenant)
                self._video_attente = attente
                if not pret:
                    return False
                heure = fin_de_journee.heure_ny(maintenant).strftime("%H:%M")
                commande = fin_de_journee.commande(self._video_dossier, self._video_python or fin_de_journee.python_outil_video())
                env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", HYPERFRAMES_NO_UPDATE_CHECK="1")
                # retenu AVANT le lancement : un échec ne relance pas chaque minute (la tâche de 22:20 réessaiera)
                fin_de_journee.retenir(self.dossier, jour, heure, "lancee")
                try:
                    self._video_lancer(commande, os.path.join(self._video_dossier, "recap-auto.log"), env)
                except OSError as erreur:
                    fin_de_journee.retenir(self.dossier, jour, heure, "echec")
                    self.journal(f"outil vidéo pas lancé ({type(erreur).__name__}) : la tâche programmée de 22:20 réessaiera")
                    return False
                self._video_attente = ""
                self.journal(f"séance close : outil vidéo lancé ({heure} New York)")
                return True
            except Exception as erreur:   # jamais de plantage d'Étrave pour la vidéo
                self.journal(f"fin de journée : vérification impossible ({type(erreur).__name__})")
                return False

    def verifier_interrupteur(self, aujourdhui=None):
        """AUD-09 : les trois mesures de l'interrupteur sur les 60 derniers jours de trade de chaque marché (journaux
        trades-<symbole>.csv, même fonction que l'export) ; au premier franchissement (60 jours de trade complets, ET-11), un
        message Telegram avec le jeton enregistré, une seule fois par franchissement. Ne lève jamais d'erreur."""
        with self._verrou_interrupteur:
            try:
                marches = export.interrupteurs(pont.lire_trades(self.dossier), aujourdhui or export.aujourdhui_ny())
            except Exception as erreur:
                self.journal(f"interrupteur pas vérifié ({type(erreur).__name__}), nouvel essai dans 10 minutes")
                return self._interrupteur
            self._interrupteur = {"verifie": int(time.time()), "marches": marches}
            try:
                self._prevenir_interrupteur(marches)
            except Exception as erreur:
                self.journal(f"interrupteur : message pas envoyé ({type(erreur).__name__}), nouvel essai dans 10 minutes")
            return self._interrupteur

    def _prevenir_interrupteur(self, marches):
        chemin = os.path.join(self.dossier, FICHIER_INTERRUPTEUR)
        try:
            retenus = pont.lire_cles(chemin, strict=True)
        except pont.Refus:
            return                                      # fichier occupé : on ne risque pas un deuxième message, essai suivant
        avant = dict(retenus)
        for symbole, i in marches.items():
            if not pont.SYMBOLE.fullmatch(symbole):
                continue
            if not (i.get("complet") and i.get("franchi")):
                retenus.pop(symbole, None)              # franchissement terminé : le prochain sera annoncé
                self._interrupteur_annonce.discard(symbole)
                continue
            if symbole in retenus:
                continue
            message = export.texte_interrupteur(symbole, i)
            if symbole not in self._interrupteur_annonce:
                self._interrupteur_annonce.add(symbole)
                self.journal(message)
            try:
                envoye = telegram.envoyer(self.dossier, message, self.appel_telegram)
            except (pont.Refus, telegram.Injoignable) as erreur:   # messages sans jeton (voir telegram.appeler)
                self.journal(f"interrupteur {symbole} : message Telegram pas parti ({erreur}), nouvel essai dans 10 minutes")
                continue
            if envoye:                                  # sans Telegram configuré : rien de retenu, envoyé une fois configuré
                retenus[symbole] = time.strftime("%Y-%m-%d %H:%M")
                self.journal(f"interrupteur {symbole} : message Telegram envoyé")
        if retenus != avant:
            pont.ecrire_cles(chemin, retenus)

    def _noter_lancement(self, ok, message=""):
        """AUD-22 : retient (ok=False) ou efface (ok=True) le dernier lancement de MetaTrader refusé faute d'EA compilé."""
        chemin = os.path.join(self.dossier, FICHIER_LANCEMENT)
        try:
            if ok:
                if os.path.exists(chemin):
                    os.remove(chemin)
                return
            with open(chemin + ".tmp", "w", encoding="utf-8") as f:
                json.dump({"ok": False, "quand": int(time.time()), "message": message}, f, ensure_ascii=False, allow_nan=False)
            os.replace(chemin + ".tmp", chemin)
        except OSError:
            pass

    def lancement(self, connus=None):
        """AUD-22 : le dernier lancement refusé (EA pas compilé), ou None. Effacé dès que l'EA compilé de `connus[0]` est plus
        récent que la source (compilé avec F7, ou par un autre chemin) : sinon le message restait, MetaTrader déjà ouvert."""
        try:
            with open(os.path.join(self.dossier, FICHIER_LANCEMENT), "r", encoding="utf-8") as f:
                lu = json.load(f)
        except (OSError, ValueError):
            return None
        if not isinstance(lu, dict) or lu.get("ok") is not False or not isinstance(lu.get("message"), str):
            return None
        donnees = mt5.donnees_de(connus[0]) if connus else None
        if donnees and mt5.ea_a_jour(donnees, SOURCE_EA):
            self._noter_lancement(True)
            return None
        quand = lu.get("quand")
        return {"ok": False, "quand": quand if isinstance(quand, int) and not isinstance(quand, bool) else None, "message": lu["message"][:2000]}

    def mt5(self, etats):
        en_marche = any(e["en_marche"] for e in etats)
        quand, ouvert = self._ouvert
        if time.time() - quand > MT5_OUVERT_CACHE_S:
            ouvert = self._mt5_ouvert()
            self._ouvert = (time.time(), ouvert)
        connus = self._mt5_terminaux(etats)
        return {
            "windows": sys.platform.startswith("win"),
            "mac": mt5.est_mac(),
            "pilotable": mt5.pilotable(),
            "ouvert": True if en_marche else ouvert,
            "terminaux": [{"id": i, "dossier": os.path.basename(os.path.dirname(chemin))} for i, chemin in enumerate(connus)],
            "demarrageWindows": bool(mt5.fichier_demarrage() and os.path.exists(mt5.fichier_demarrage())),
        }

    def _terminal(self, corps, etats):
        connus = self._mt5_terminaux(etats)
        choix = corps.get("terminal", 0)
        chemin = connus[choix] if isinstance(choix, int) and not isinstance(choix, bool) and 0 <= choix < len(connus) else None
        return chemin, connus

    def ouvrir_mt5_si_demande(self, forcer=False):
        """Au démarrage d'Étrave : ouvre MetaTrader s'il est fermé et que l'option est cochée (ou `forcer`, double-clic sur
        Etrave.command). Sur Mac, met d'abord à jour l'EA s'il a changé dans le dépôt (le profil « Etrave-demo » avec).
        Ne lève jamais d'erreur."""
        try:
            publics = pont.reglages_publics(self.dossier)
            if not (forcer or publics["mt5Auto"]) or self._mt5_ouvert() is not False:
                return False
            connus = self._mt5_terminaux(pont.lire_etats(self.dossier))
            if not connus:
                return False
            if forcer and not publics["mt5Auto"] and not mt5.est_mac() and not publics.get("mt5Login"):
                self.journal("Connecte d’abord MetaTrader 5 à ton compte depuis la page (Connexions) : Étrave l’ouvrira ensuite tout seul.")
                return False
            if not mt5.ea_a_jour(mt5.donnees_de(connus[0]), SOURCE_EA):
                try:
                    resultat = self._mt5_installer(connus[0], connus, SOURCE_EA, ouvert=False)
                except pont.Refus as refus:
                    resultat = {"compile": None, "journal": [str(refus)]}
                except Exception as erreur:
                    resultat = {"compile": None, "journal": [f"installation impossible ({type(erreur).__name__})"]}
                # AUD-22 (audit du 26/11/2026) : MetaTrader lancé malgré une compilation ratée démarrait avec l'ancien EA (ou
                # sans EA). Il n'est plus lancé ; le journal et la page disent pourquoi.
                if not resultat.get("compile"):
                    detail = " / ".join(resultat.get("journal", [])[-3:])
                    message = ("MetaTrader 5 pas ouvert : " + ("la compilation de l’EA a échoué" if resultat.get("compile") is False
                                                               else "l’EA n’a pas pu être installé et compilé")
                               + ", MetaTrader aurait démarré avec l’ancien EA ou sans EA." + (f" Détail : {detail}." if detail else "")
                               + " Corrige l’EA ou compile-le dans MetaEditor (F7), puis relance Étrave, ou clique sur « Installer ou "
                               "mettre à jour l’EA » (onglet Connexions).")
                    self.journal(message)
                    self._noter_lancement(False, message)
                    return False
                self.journal("EA et profil mis à jour dans MetaTrader 5")
            self._mt5_lancer(connus[0], connus, None, ouvert=False)
            self._noter_lancement(True)
            self.journal("MetaTrader 5 ouvert automatiquement (Nasdaq et S&P 500 avec la V11, profil Etrave-demo)")
            return True
        except Exception as erreur:
            self.journal(f"MetaTrader 5 pas ouvert automatiquement : {erreur}")
            return False

    def tailles(self, risque_pct):
        """AUD-24 : la taille estimée d'une cassure, par marché, pour chaque EA qui donne solde, prix, valeur du point, pas et lot
        minimum (EA en marche d'abord). Rien pour un EA en lots fixes : le risque en % n'y sert pas."""
        resultat, vus = [], set()
        for e in sorted(pont.lire_etats(self.dossier), key=lambda x: not x["en_marche"]):
            marche = e.get("instrument")
            if marche not in pont.INSTRUMENTS or marche in vus or (e.get("lots_fixes") or 0) > 0:
                continue
            taille = risque.estimer_taille(e.get("solde"), risque_pct, e.get("prix"), e.get("valeur_point_lot"), e.get("lot_pas"),
                                           e.get("lot_min"), marche)
            if taille:
                vus.add(marche)
                resultat.append({"symbole": e["symbole"], "devise": e.get("devise", ""), "enMarche": e["en_marche"], **taille})
        return resultat

    def exporter_trimestres_finis(self):
        """Exporte les trimestres terminés qui n'ont pas encore d'export. Ne lève jamais d'erreur : un export raté se refait au passage suivant."""
        try:
            for trimestre in export.exporter_trimestres_finis(self.dossier):
                self.journal(f"export du trimestre {trimestre} écrit dans {export.dossier_exports(self.dossier)}")
        except Exception as erreur:
            self.journal(f"export trimestriel impossible ({type(erreur).__name__}), nouvel essai plus tard")

    def exports(self):
        racine = export.dossier_exports(self.dossier)
        return {"exports": export.exports_faits(self.dossier), "dossier": racine,
                "journaux": os.path.join(racine, export.SOUS_DOSSIER_JOURNAUX),
                "enCours": export.trimestre_de(export.aujourdhui_ny())}

    def sauvegarder_journaux(self):
        """Copie les journaux de l'EA qui ont changé dans « Étrave exports/journaux/ » (demande de l'utilisateur du 27/11/2026).
        Ne lève jamais d'erreur : une copie ratée est refaite au passage suivant."""
        try:
            os.makedirs(export.dossier_exports(self.dossier), exist_ok=True)   # visible sur le Bureau avant le premier trade
            copies = export.copier_journaux(self.dossier)
        except Exception as erreur:
            self.journal(f"copie des journaux impossible ({type(erreur).__name__}), nouvel essai dans 10 minutes")
            return []
        if copies:
            self.journal(f"journaux copiés dans {os.path.join(export.dossier_exports(self.dossier), export.SOUS_DOSSIER_JOURNAUX)} : {', '.join(copies)}")
        return copies

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
            return {**risque.simuler(pct, levier), "tailles": self.tailles(pct)}
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
        if route == "POST /api/arret-urgence":
            # AUD-10 : décoche les deux marchés et demande la clôture à chaque EA en marche ; ceux qui ne tournent pas sont
            # signalés : leurs positions se ferment dans MetaTrader. Réarmer = recocher les cases des marchés.
            etats = pont.lire_etats(self.dossier)
            en_marche = list(dict.fromkeys(e["symbole"] for e in etats if e["en_marche"]))
            sans_ea = [s for s in dict.fromkeys(e["symbole"] for e in etats if not e["en_marche"]) if s not in en_marche]
            _, fermes, ecartes = pont.arret_urgence(self.dossier, en_marche, corps.get("confirmation", ""))
            sans_ea += ecartes
            message = "Les deux marchés sont décochés : plus aucun nouveau trade."
            if fermes:
                message += f" Clôture demandée sur {' et '.join(fermes)} : l’EA ferme tout dans les 2 secondes."
            if sans_ea:
                message += (f" L’EA ne tourne pas sur {' et '.join(sans_ea)} : ferme ses positions et ses ordres directement dans "
                            "MetaTrader 5.")
            message += " Pour repartir, recoche les cases des marchés (onglet Séance)."
            self.journal("ARRÊT D’URGENCE depuis la page : marchés décochés" + (f", clôture demandée sur {', '.join(fermes)}" if fermes else "")
                         + (f", EA arrêté sur {', '.join(sans_ea)}" if sans_ea else ""))
            return {"ok": True, "fermes": fermes, "sansEa": sans_ea, "message": message, "reglages": pont.reglages_publics(self.dossier)}
        if route == "POST /api/compte/autoriser":
            # AUD-01 : autoriser l'EA à trader sur le compte réel vu (mot REEL), ou retirer l'autorisation (sans mot : c'est
            # le sens prudent)
            if corps.get("retirer") is True:
                changees = pont.retirer_autorisation_reel(self.dossier)
                if changees:
                    self.journal("autorisation du compte réel retirée")
                return {"ok": True, "changees": changees, "reglages": pont.reglages_publics(self.dossier)}
            changees = pont.autoriser_compte_reel(self.dossier, corps.get("login"), corps.get("confirmation", ""),
                                                  pont.lire_etats(self.dossier))
            if changees:
                self.journal(f"compte réel n° {corps.get('login')} autorisé depuis la page")
            return {"ok": True, "changees": changees, "reglages": pont.reglages_publics(self.dossier)}
        if route == "POST /api/mt5/lancer":
            etats = pont.lire_etats(self.dossier)
            chemin, connus = self._terminal(corps, etats)
            identifiants = None
            if corps.get("connexion"):
                identifiants = (corps.get("login"), corps.get("motDePasse"), corps.get("serveur"))
            ouvert = any(e["en_marche"] for e in etats) or bool(self._mt5_ouvert())
            # VPS vierge : l'EA est compilé avant d'ouvrir les deux graphiques qui l'attendent (le profil vient avec).
            if not ouvert and chemin in connus and not mt5.ea_a_jour(mt5.donnees_de(chemin), SOURCE_EA):
                installe = self._mt5_installer(chemin, connus, SOURCE_EA, ouvert=False)
                self.journal("EA et profil installés dans MetaTrader 5" if installe.get("compile") else "EA copié, mais pas compilé")
            resultat = self._mt5_lancer(chemin, connus, identifiants, ouvert=ouvert)
            self._ouvert = (0.0, None)
            self.journal("MetaTrader 5 lancé" + (" avec connexion à un compte" if identifiants else ""))
            if identifiants:                                    # le compte et le serveur sont retenus, jamais le mot de passe
                pont.retenir_mt5(self.dossier, login=str(identifiants[0]).strip(), serveur=str(identifiants[2]).strip())
            return {"ok": True, **resultat}
        if route == "POST /api/mt5/installer":
            etats = pont.lire_etats(self.dossier)
            # AUD-21 : recompiler recharge l'EA, en pleine séance s'il a un trade ou un ordre : refusé, comme la fermeture
            en_cours, muets = occupes(etats)
            if en_cours:
                raise Erreur(409, "Un trade ou un ordre est en cours sur " + " et ".join(en_cours) + " : recompiler l’EA le recharge en "
                             "pleine séance. Installe après la clôture du trade ou après la séance.")
            chemin, connus = self._terminal(corps, etats)
            ouvert = any(e["en_marche"] for e in etats) or self._mt5_ouvert() is not False   # profil remplacé MetaTrader fermé
            if muets and ouvert:
                raise Erreur(409, f"L’EA ne répond plus sur {_muets_txt(muets)}, et ce dernier état disait un trade ou un ordre en "
                             "cours : recompiler le recharge. Vérifie dans MetaTrader 5, ferme-le (bouton « Fermer MetaTrader 5 »), "
                             "puis installe.")
            resultat = self._mt5_installer(chemin, connus, SOURCE_EA, ouvert=ouvert)
            self.journal("EA copié dans MetaTrader 5" + (" et compilé" if resultat.get("compile") else ""))
            if resultat.get("compile"):
                self._noter_lancement(True)                     # AUD-22 : le message d'un double-clic raté n'a plus lieu d'être
            return {"ok": True, **resultat}
        if route == "POST /api/mt5/fermer":
            # Fermer MetaTrader pendant un trade laisserait la sortie de 15:50 et les jambes sans surveillance (X-02).
            en_cours, muets = occupes(pont.lire_etats(self.dossier))
            if en_cours:
                raise Erreur(409, "Un trade ou un ordre est en cours sur " + ", ".join(en_cours) + " : clôture-le d’abord "
                             "(bouton « Clôturer »), puis ferme MetaTrader 5.")
            # AUD-19 : EA arrêté ou gelé dont le dernier état disait un trade ou un ordre : seulement avec le mot FERMER
            if muets and corps.get("confirmation") != pont.MOTS["fermer"]:
                raise Erreur(409, f"L’EA ne répond plus sur {_muets_txt(muets)}, et ce dernier état disait un trade ou un ordre en "
                             "cours. Fermer MetaTrader 5 le laisserait sans surveillance (stops surveillés par l’EA, sortie de 15:50) : "
                             f"vérifie dans MetaTrader, puis confirme en tapant {pont.MOTS['fermer']}.")
            resultat = self._mt5_fermer()
            self._ouvert = (0.0, None)
            self.journal("MetaTrader 5 fermé depuis la page")
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
            # AUD-16 : allow_nan=False, NaN et Infinity ne sont pas du JSON (le navigateur refuse toute la réponse). Une valeur
            # non finie qui passerait malgré pont._nombre donne une erreur 500 nette au lieu d'une page figée.
            donnees = corps.encode("utf-8") if isinstance(corps, str) else json.dumps(corps, ensure_ascii=False, allow_nan=False).encode("utf-8")
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
    lecteur = argparse.ArgumentParser(description=f"{pont.NOM} : l'interface de l'EA Strategy V11")
    lecteur.add_argument("--port", type=int, default=int(os.environ.get("ETRAVE_PORT", PORT)))
    lecteur.add_argument("--dossier", default=None, help="dossier partagé avec l'EA (par défaut : dossier commun de MetaTrader)")
    lecteur.add_argument("--sans-navigateur", action="store_true")
    lecteur.add_argument("--tout", action="store_true", help="ouvre aussi MetaTrader 5 s'il est fermé (Etrave.command sur Mac : "
                         "met l'EA et le profil à jour, ouvre les deux graphiques avec la V11 et garde le Mac éveillé)")
    options = lecteur.parse_args(arguments)
    dossier = options.dossier or pont.dossier_commun()
    os.makedirs(dossier, exist_ok=True)
    reprendre_ancienne_organisation()
    mt5.effacer_connexions_oubliees()   # mot de passe laissé par un arrêt brutal pendant un lancement de MetaTrader

    def journal(message):
        print(f"{time.strftime('%H:%M:%S')}  {message}", flush=True)
    mt5.journal = journal                                       # AUD-27 : les messages de mt5.py vont dans le même journal

    try:
        serveur = creer_serveur(dossier, options.port, journal=journal)
    except OSError:
        if deja_lancee(options.port):
            print(f"{pont.NOM} tourne déjà : http://127.0.0.1:{options.port}")
            if options.tout:                                    # double-clic alors qu'Étrave tourne : MetaTrader s'ouvre quand même
                Application(dossier, journal=journal).ouvrir_mt5_si_demande(forcer=True)
            if not options.sans_navigateur:
                webbrowser.open(f"http://127.0.0.1:{options.port}")
            return 0
        print(f"Le port {options.port} est pris par un autre programme. Essaie : python etrave/etrave.py --port {options.port + 1}")
        return 1
    print(f"{pont.NOM} — l'EA Strategy V11 (indices US)")
    print(f"  page     : {serveur.url}   (cet ordinateur uniquement)")
    print(f"  dossier  : {dossier}")
    print("  Laisse cette fenêtre ouverte tant que tu utilises la page. La fermer n'arrête ni l'EA ni ses alertes.")
    if not options.sans_navigateur:
        threading.Timer(0.6, lambda: webbrowser.open(serveur.url)).start()
    threading.Timer(1.0, serveur.application.ouvrir_mt5_si_demande, kwargs={"forcer": options.tout}).start()

    def exporter_puis_reprogrammer():
        serveur.application.exporter_trimestres_finis()
        minuterie = threading.Timer(EXPORT_PERIODE_S, exporter_puis_reprogrammer)
        minuterie.daemon = True
        minuterie.start()
    depart = threading.Timer(5.0, exporter_puis_reprogrammer)
    depart.daemon = True
    depart.start()

    def verifier_interrupteur_puis_reprogrammer():      # AUD-09 : toutes les 10 minutes, comme l'export
        serveur.application.verifier_interrupteur()
        serveur.application.sauvegarder_journaux()        # 27/11/2026 : copie des journaux sur le Bureau, s'ils ont changé
        minuterie = threading.Timer(INTERRUPTEUR_PERIODE_S, verifier_interrupteur_puis_reprogrammer)
        minuterie.daemon = True
        minuterie.start()
    interrupteur = threading.Timer(8.0, verifier_interrupteur_puis_reprogrammer)
    interrupteur.daemon = True
    interrupteur.start()

    def verifier_fin_de_journee_puis_reprogrammer():    # chaque minute : séance close, vidéo du jour lancée une fois
        serveur.application.verifier_fin_de_journee()
        minuterie = threading.Timer(VIDEO_PERIODE_S, verifier_fin_de_journee_puis_reprogrammer)
        minuterie.daemon = True
        minuterie.start()
    fin_journee = threading.Timer(12.0, verifier_fin_de_journee_puis_reprogrammer)
    fin_journee.daemon = True
    fin_journee.start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
