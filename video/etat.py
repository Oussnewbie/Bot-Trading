"""La mémoire du mode automatique, hors du Bureau : ce qui est publié, les notifications déjà envoyées, les jours acquittés, et le
verrou qui empêche deux passages en même temps.

    <dossier d'état>/registre.json   {"journaux": {"<dossier des journaux>": {"publies": {clé: {...}},
                                                                             "alertes": {clé: "AAAA-MM-JJ"},
                                                                             "decisions": {"AAAA-MM-JJ": "accepter" | "ignorer"}}}}
    <dossier d'état>/video.verrou    le verrou d'un passage (auto ou recap)

Le dossier d'état est `dossier_etat` de la configuration, sinon ~/Library/Application Support/Etrave/video sur Mac (LOCALAPPDATA sous
Windows) : à côté de l'outil copié, mais pas dedans (une réinstallation ne l'efface pas). Chaque dossier de journaux a sa partie :
les essais du testeur (`--testeur`) ne se mêlent jamais aux séances du compte.

V-07 (audit du 27/11/2026) : le dossier du Bureau était la seule mémoire des publications ; le ranger refaisait toutes les vidéos
depuis `auto_depuis`, avec une notification chacune (et autant de crédits ElevenLabs sans cache). V-09 : une séance illisible
prévenait à chaque lancement, sans fin, et bloquait la semaine et le mois pour toujours ; elle s'acquitte (« accepter tel quel » ou
« ignorer ce jour ») et ne prévient plus qu'une fois par jour. V-20 : deux passages simultanés (launchd et un `auto` ou un `recap`
lancé à la main, ou Étrave en fin de séance) fabriquaient deux fois le même jour.
"""
import contextlib
import json
import os
import sys
import time


def _defaut():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Etrave/video")
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Etrave", "video")
    return os.path.expanduser("~/.local/share/etrave/video")


DOSSIER = _defaut()
DECISIONS = ("accepter", "ignorer")


def dossier(config):
    return os.path.expanduser((config or {}).get("dossier_etat") or DOSSIER)


class DejaEnCours(Exception):
    """Un autre passage de l'outil tient le verrou."""


@contextlib.contextmanager
def verrou(config):
    """Le verrou d'un passage (V-20) : un seul `auto` ou `recap` à la fois. Lève DejaEnCours si un autre le tient. Le système le
    rend tout seul si le processus s'arrête (plantage compris) : jamais de verrou oublié."""
    d = dossier(config)
    os.makedirs(d, exist_ok=True)
    f = open(os.path.join(d, "video.verrou"), "a+")
    try:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise DejaEnCours("un autre passage de l'outil vidéo est en cours (mode automatique, Étrave ou commande à la main) : "
                              "celui-ci s'arrête sans rien faire")
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                with contextlib.suppress(OSError):
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    finally:
        f.close()


class Registre:
    """Le registre des publications et des décisions d'un dossier de journaux. Un fichier abîmé est mis de côté (jamais d'arrêt du
    mode automatique pour lui : V-02) et un nouveau registre repart des dossiers du Bureau."""

    def __init__(self, config, dossier_journaux, journal=print):
        self.chemin = os.path.join(dossier(config), "registre.json")
        self.cle = os.path.normcase(os.path.abspath(os.path.expanduser(dossier_journaux or "")))
        self.journal = journal
        self.tout = self._lire()
        partie = self.tout.setdefault("journaux", {}).setdefault(self.cle, {})
        self.publies = partie.setdefault("publies", {})
        self.alertes = partie.setdefault("alertes", {})
        self.decisions = partie.setdefault("decisions", {})

    def _lire(self):
        if not os.path.exists(self.chemin):
            return {}
        try:
            with open(self.chemin, encoding="utf-8") as f:
                donnees = json.load(f)
            if not isinstance(donnees, dict) or not isinstance(donnees.get("journaux", {}), dict):
                raise ValueError("forme inattendue")
            return donnees
        except (OSError, ValueError) as err:
            ecart = f"{self.chemin}.abime-{time.strftime('%Y%m%d-%H%M%S')}"
            with contextlib.suppress(OSError):
                os.replace(self.chemin, ecart)
            self.journal(f"Registre des publications illisible ({err}) : mis de côté dans {ecart}, un nouveau repart des dossiers "
                         "de publication.")
            return {}

    def enregistrer(self):
        """Écrit sous un nom provisoire puis renomme : un arrêt pendant l'écriture ne laisse jamais un registre tronqué."""
        os.makedirs(os.path.dirname(self.chemin), exist_ok=True)
        provisoire = f"{self.chemin}.{os.getpid()}.part"
        with open(provisoire, "w", encoding="utf-8") as f:
            json.dump(self.tout, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(provisoire, self.chemin)

    # ── publications (V-07, V-22) ──
    def publie(self, cle, dossier_publication=None):
        """Déjà publié ? Le registre d'abord ; sinon un dossier de publication qui contient la vidéo (amorçage depuis le Bureau, puis
        noté dans le registre)."""
        if cle in self.publies:
            return True
        if dossier_publication and os.path.isdir(dossier_publication) and any(n.endswith(".mp4") for n in os.listdir(dossier_publication)):
            self.noter_publie(cle, dossier_publication)
            return True
        return False

    def noter_publie(self, cle, dossier_publication):
        self.publies[cle] = {"dossier": dossier_publication, "le": time.strftime("%Y-%m-%d %H:%M")}
        self.enregistrer()

    # ── notifications : une par jour au plus pour un même souci (V-09) ──
    def a_prevenir(self, cle, aujourd_hui):
        jour = aujourd_hui.isoformat()
        if self.alertes.get(cle) == jour:
            return False
        self.alertes[cle] = jour
        self.enregistrer()
        return True

    # ── jours acquittés (V-09) ──
    def decision(self, jour):
        return self.decisions.get(jour.isoformat())

    def decider(self, jour, quoi):
        if quoi not in DECISIONS:
            raise ValueError(f"décision inconnue : {quoi}")
        self.decisions[jour.isoformat()] = quoi
        self.enregistrer()
