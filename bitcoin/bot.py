"""Le bot BTC. Voir LISEZMOI.md pour le fonctionnement complet. Se pilote depuis Étrave (onglet Bitcoin) ou à la main :

    python bitcoin/bot.py --config bitcoin/config.json            boucle : un cycle après chaque clôture 4h
    python bitcoin/bot.py --config bitcoin/config.json --une-fois un seul cycle, puis s'arrête
    python bitcoin/bot.py --config bitcoin/config.json --etat     affiche le compte et la décision, sans rien faire

Fichiers de commande, dans le dossier d'état (Étrave les crée pour toi) :
    PAUSE       plus aucun ordre (le bot continue d'analyser et d'alerter)
    REARMER     repartir après un coupe-circuit
    FERMER      tout fermer au prochain cycle, puis pause
    MAINTENANT  faire un cycle tout de suite (le bot le voit en moins de 15 secondes)
"""
import argparse
import csv
import json
import logging
import os
import sys
import time

import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from courtier import CourtierBinance, CourtierPapier, montage, plan, prix_stop  # noqa: E402
from donnees_live import SourceLive  # noqa: E402
import notif  # noqa: E402
from strategie import LEVIER_MAX, DonneesInvalides, PROFILS, decider  # noqa: E402

log = logging.getLogger("bot")
DEFAUT = dict(mode="papier", profil="prudent", levier=1, vente=None, ordres="limite", bande=0.05, perte_max=0.40,
              capital_papier=10_000, dossier=os.path.join(ICI, "etat"), delai_s=90, fichier_secrets=None)
VEILLE_S = 15


def charger_config(chemin):
    c = dict(DEFAUT)
    if chemin and os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            c.update({k: v for k, v in json.load(f).items() if v is not None or k == "vente"})
    if c["mode"] not in ("papier", "testnet", "reel"):
        raise ValueError("mode : papier, testnet ou reel")
    if c["profil"] not in PROFILS:
        raise ValueError(f"profil : {list(PROFILS)}")
    if c["ordres"] not in ("limite", "marche"):
        raise ValueError("ordres : limite ou marche")
    c["levier"] = int(min(max(int(c["levier"]), 1), LEVIER_MAX))
    return c


def secrets(cfg):
    """Clés Binance et Telegram : l'environnement d'abord, sinon le fichier de secrets écrit par Étrave."""
    s = {}
    f = cfg.get("fichier_secrets") or os.environ.get("ETRAVE_SECRETS_BTC")
    if f and os.path.exists(f):
        with open(f, encoding="utf-8") as h:
            s = json.load(h)
    return dict(cle=os.environ.get("BINANCE_API_KEY") or s.get("binance_cle"),
                secret=os.environ.get("BINANCE_API_SECRET") or s.get("binance_secret"),
                telegram_jeton=s.get("telegram_jeton"), telegram_discussion=s.get("telegram_discussion"))


class Bot:
    def __init__(self, cfg, source=None, courtier=None):
        self.cfg = cfg
        os.makedirs(cfg["dossier"], exist_ok=True)
        self.f_etat = os.path.join(cfg["dossier"], "etat.json")
        self.f_journal = os.path.join(cfg["dossier"], "journal.csv")
        self.etat = json.load(open(self.f_etat, encoding="utf-8")) if os.path.exists(self.f_etat) else {}
        self.source = source or SourceLive()
        sec = secrets(cfg)
        notif.configurer(sec["telegram_jeton"], sec["telegram_discussion"])
        if courtier is not None:
            self.courtier = courtier
        elif cfg["mode"] == "papier":
            self.courtier = CourtierPapier(self.etat.get("papier"), cfg["capital_papier"], cfg["ordres"])
        else:
            self.courtier = CourtierBinance(sec["cle"], sec["secret"], testnet=cfg["mode"] == "testnet", ordres=cfg["ordres"])
        self.profil = dict(PROFILS[cfg["profil"]])
        if cfg.get("vente") is not None:
            self.profil["vente"] = float(cfg["vente"])
        self.levier = cfg["levier"]
        self.montage = montage(self.levier)
        self.courtier.configurer(self.levier, self.montage)

    # ── persistance
    def sauver(self):
        if isinstance(self.courtier, CourtierPapier):
            self.etat["papier"] = self.courtier.exporter()
        tmp = self.f_etat + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.etat, f, indent=1, default=str, ensure_ascii=False)
        os.replace(tmp, self.f_etat)

    def journal(self, ligne):
        neuf = not os.path.exists(self.f_journal)
        with open(self.f_journal, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(ligne))
            if neuf:
                w.writeheader()
            w.writerow(ligne)

    def drapeau(self, nom, retirer=False):
        p = os.path.join(self.cfg["dossier"], nom)
        ok = os.path.exists(p)
        if ok and retirer:
            os.remove(p)
        return ok

    def battement(self, prochain=None, statut="en attente"):
        """Fichier lu par Étrave pour savoir que le bot est vivant (réécrit toutes les 15 secondes)."""
        d = dict(pid=os.getpid(), heure=str(pd.Timestamp.now(tz="UTC")), prochain_cycle=str(prochain) if prochain else None,
                 statut=statut, mode=self.cfg["mode"], profil=self.cfg["profil"], levier=self.levier, montage=self.montage)
        tmp = os.path.join(self.cfg["dossier"], "vivant.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, os.path.join(self.cfg["dossier"], "vivant.json"))

    # ── un cycle
    def cycle(self, maintenant=None, executer=True, force=False):
        maintenant = maintenant or pd.Timestamp.now(tz="UTC")
        if self.drapeau("REARMER", retirer=True):          # demandé depuis Étrave après un coupe-circuit
            self.etat.pop("arrete", None)
            self.etat["pic"] = (self.etat.get("compte") or {}).get("capital", self.etat.get("pic"))
        if self.etat.get("arrete") and not self.drapeau("FERMER"):
            return dict(statut="arrêté", raison=self.etat["arrete"])
        B = self.source.charger(maintenant)
        try:
            d = decider(B, self.profil, maintenant, self.levier)
        except DonneesInvalides as e:
            notif.envoyer(f"⚠️ BTC bot : pas de décision ({e}). Aucun ordre.")
            self.etat["derniere_erreur"] = dict(heure=str(maintenant), message=str(e))
            self.sauver()
            return dict(statut="données invalides", raison=str(e))
        if executer and not force and str(d["bougie_4h"]) == self.etat.get("derniere_bougie"):
            return dict(statut="déjà traité", bougie=str(d["bougie_4h"]))
        self.courtier.fixer_prix(d["prix"], maintenant)
        evenements = []
        # stop de protection touché depuis le dernier cycle ? (le compte papier le vérifie sur les bougies 4h écoulées)
        if self.etat.get("derniere_bougie"):
            depuis = B["d4"][B["d4"].index > pd.Timestamp(self.etat["derniere_bougie"])]
            if len(depuis):
                s = self.courtier.verifier_stop(float(depuis.high.max()), float(depuis.low.min()))
                if s:
                    evenements.append(s)
                    notif.envoyer(f"🛑 BTC bot : stop de protection touché à {s['prix']:,.0f} $, position fermée.")
        e = self.courtier.etat()
        cible = d["cible"]
        pic = max(self.etat.get("pic", 0.0), e.capital)
        self.etat["pic"] = pic
        motif = ""
        if e.capital < pic * (1 - self.cfg["perte_max"]):
            cible, motif = 0.0, f"coupe-circuit : capital {e.capital:,.0f} < {1 - self.cfg['perte_max']:.0%} du plus haut {pic:,.0f}"
            self.etat["arrete"] = motif
        fermer = self.drapeau("FERMER")
        if fermer:
            cible, motif = 0.0, "fermeture demandée (FERMER)"
        pause = self.drapeau("PAUSE") and not fermer
        p = plan(e, cible, self.cfg["bande"], self.montage)
        execs = []
        if executer and not pause:
            for a in p.actions:
                try:
                    execs.append(self.courtier.executer(a))
                except Exception as ex:  # noqa: BLE001
                    notif.envoyer(f"❌ BTC bot : ordre {a.type} {a.quantite:.6f} refusé : {ex}")
                    raise
            stop = prix_stop(cible, d["prix"], self.montage)
            self.courtier.poser_stop(stop)
            self.etat["stop"] = stop
            if fermer:
                self.drapeau("FERMER", retirer=True)
                open(os.path.join(self.cfg["dossier"], "PAUSE"), "w").close()
        e2 = self.courtier.etat() if (execs or evenements) else e
        votes = " ".join(f"{k}{'?' if v is None else ('+' if v > 0 else '-')}" for k, v in d["votes"].items())
        msg = (f"BTC {d['prix']:,.0f} $ · bougie 4h {d['bougie_4h']:%d/%m %H:%M} UTC\n"
               f"score {d['score']:+.2f} · 4h {d['tendance_4h']} · {d['sens']} cible {cible:+.0%} (levier ×{self.levier})\n"
               f"votes : {votes}\n"
               f"capital {e2.capital:,.2f} $ · exposition {e2.exposition:+.0%}"
               + (f"\nordres : " + ", ".join(f"{x['type']} {x['quantite']:.5f}" for x in execs) if execs else f"\n{p.note}")
               + (f"\nstop de protection {self.etat.get('stop'):,.0f} $" if self.etat.get("stop") else "")
               + (f"\n⚠️ {motif}" if motif else "") + ("\n⏸ PAUSE : aucun ordre passé" if pause else ""))
        if executer:
            if execs or motif or d["sens"] != self.etat.get("dernier_sens"):
                notif.envoyer(msg)
            else:
                log.info(msg.replace("\n", " | "))
            self.etat.update(derniere_bougie=str(d["bougie_4h"]), dernier_sens=d["sens"], derniere_erreur=None,
                             derniere_decision=dict(d, bougie_4h=str(d["bougie_4h"]), jour=str(d["jour"]), cible_appliquee=cible,
                                                    heure=str(maintenant), levier=self.levier, montage=self.montage,
                                                    pause=pause, motif=motif),
                             compte=e2.public())
            self.journal(dict(heure=str(maintenant), bougie_4h=str(d["bougie_4h"]), prix=round(d["prix"], 2),
                              score=round(d["score"], 3), tendance_4h=d["tendance_4h"], cible=round(cible, 4),
                              capital=round(e2.capital, 2), exposition=round(e2.exposition, 4),
                              ordres=";".join(f"{x['type']}:{x['quantite']:.6f}" for x in evenements + execs),
                              motif=motif or ("pause" if pause else "")))
            self.sauver()
        return dict(statut="ok", decision=d, plan=p, execs=execs, capital=e2.capital, exposition=e2.exposition, message=msg)


def prochain_reveil(maintenant, delai_s):
    """Juste après la prochaine clôture 4h (00, 04, 08, 12, 16, 20 h UTC), avec un délai pour que la bougie soit publiée."""
    return maintenant.floor("4h") + pd.Timedelta("4h") + pd.Timedelta(seconds=delai_s)


def boucle(bot, cfg):
    notif.envoyer(f"▶️ BTC bot démarré ({cfg['mode']}, profil {cfg['profil']}, levier ×{bot.levier}, ordres {cfg['ordres']})")
    reveil = pd.Timestamp.now(tz="UTC")            # un premier cycle tout de suite
    while True:
        maintenant = pd.Timestamp.now(tz="UTC")
        demande = bot.drapeau("MAINTENANT", retirer=True)
        if maintenant >= reveil or demande:
            bot.battement(statut="cycle en cours")
            try:
                r = bot.cycle(force=demande)
                log.info(f"cycle : {r['statut']}")
                reveil = prochain_reveil(pd.Timestamp.now(tz="UTC"), cfg["delai_s"])
            except Exception as e:  # noqa: BLE001
                log.exception("cycle en erreur")
                notif.envoyer(f"❌ BTC bot : erreur de cycle ({e}). Nouvel essai dans 5 minutes.")
                bot.etat["derniere_erreur"] = dict(heure=str(maintenant), message=str(e)[:300])
                bot.sauver()
                reveil = pd.Timestamp.now(tz="UTC") + pd.Timedelta("5min")
        bot.battement(reveil)
        time.sleep(VEILLE_S)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--config", default=os.path.join(ICI, "config.json"))
    a.add_argument("--une-fois", action="store_true")
    a.add_argument("--etat", action="store_true")
    x = a.parse_args()
    cfg = charger_config(x.config)
    os.makedirs(cfg["dossier"], exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(cfg["dossier"], "bot.log"), encoding="utf-8")])
    if cfg["mode"] == "reel" and os.environ.get("BOT_REEL_CONFIRME") != "oui" and not cfg.get("reel_confirme"):
        sys.exit("Mode réel non confirmé : confirme-le dans Étrave (mot REEL), ou BOT_REEL_CONFIRME=oui dans l'environnement.")
    bot = Bot(cfg)
    log.info(f"démarrage : mode {cfg['mode']}, profil {cfg['profil']} {bot.profil}, levier ×{bot.levier} ({bot.montage}), "
             f"ordres {cfg['ordres']}, bande {cfg['bande']:.0%}, coupe-circuit {cfg['perte_max']:.0%}")
    if x.etat:
        r = bot.cycle(executer=False)
        print(r.get("message", r))
        return
    if x.une_fois:
        r = bot.cycle()
        print(r.get("message", r))
        return
    with open(os.path.join(cfg["dossier"], "bot.pid"), "w") as f:
        f.write(str(os.getpid()))
    boucle(bot, cfg)


if __name__ == "__main__":
    main()
