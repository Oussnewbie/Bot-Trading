"""Le bot BTC. Voir LISEZMOI.md pour le fonctionnement complet.

    python crypto/bot/bot.py --config crypto/bot/config.json            boucle : un cycle après chaque clôture 4h
    python crypto/bot/bot.py --config crypto/bot/config.json --une-fois un seul cycle, puis s'arrête
    python crypto/bot/bot.py --config crypto/bot/config.json --etat     affiche le compte et la décision, sans rien faire

Arrêts manuels, dans le dossier d'état : un fichier PAUSE (plus aucun ordre) ou FERMER (tout fermer, puis pause).
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
from courtier import CourtierBinance, CourtierPapier, plan  # noqa: E402
from donnees_live import SourceLive  # noqa: E402
import notif  # noqa: E402
from strategie import DonneesInvalides, PROFILS, decider  # noqa: E402

log = logging.getLogger("bot")
DEFAUT = dict(mode="papier", profil="prudent", vente=None, bande=0.05, perte_max=0.40, capital_papier=10_000,
              dossier=os.path.join(ICI, "etat"), delai_s=90)


def charger_config(chemin):
    c = dict(DEFAUT)
    if chemin and os.path.exists(chemin):
        with open(chemin) as f:
            c.update(json.load(f))
    if c["mode"] not in ("papier", "testnet", "reel"):
        raise ValueError("mode : papier, testnet ou reel")
    if c["profil"] not in PROFILS:
        raise ValueError(f"profil : {list(PROFILS)}")
    return c


class Bot:
    def __init__(self, cfg, source=None, courtier=None):
        self.cfg = cfg
        os.makedirs(cfg["dossier"], exist_ok=True)
        self.f_etat = os.path.join(cfg["dossier"], "etat.json")
        self.f_journal = os.path.join(cfg["dossier"], "journal.csv")
        self.etat = json.load(open(self.f_etat)) if os.path.exists(self.f_etat) else {}
        self.source = source or SourceLive()
        if courtier is not None:
            self.courtier = courtier
        elif cfg["mode"] == "papier":
            self.courtier = CourtierPapier(self.etat.get("papier"), cfg["capital_papier"])
        else:
            self.courtier = CourtierBinance(testnet=cfg["mode"] == "testnet")
        self.profil = dict(PROFILS[cfg["profil"]])
        if cfg.get("vente") is not None:
            self.profil["vente"] = float(cfg["vente"])

    # ── persistance
    def sauver(self):
        if isinstance(self.courtier, CourtierPapier):
            self.etat["papier"] = self.courtier.exporter()
        tmp = self.f_etat + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.etat, f, indent=1, default=str)
        os.replace(tmp, self.f_etat)

    def journal(self, ligne):
        neuf = not os.path.exists(self.f_journal)
        with open(self.f_journal, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ligne))
            if neuf:
                w.writeheader()
            w.writerow(ligne)

    def drapeau(self, nom):
        return os.path.exists(os.path.join(self.cfg["dossier"], nom))

    # ── un cycle
    def cycle(self, maintenant=None, executer=True):
        maintenant = maintenant or pd.Timestamp.now(tz="UTC")
        if self.etat.get("arrete"):
            return dict(statut="arrêté", raison=self.etat["arrete"])
        B = self.source.charger(maintenant)
        try:
            d = decider(B, self.profil, maintenant)
        except DonneesInvalides as e:
            notif.envoyer(f"⚠️ BTC bot : pas de décision ({e}). Aucun ordre.")
            return dict(statut="données invalides", raison=str(e))
        if executer and str(d["bougie_4h"]) == self.etat.get("derniere_bougie"):
            return dict(statut="déjà traité", bougie=str(d["bougie_4h"]))
        self.courtier.fixer_prix(d["prix"], maintenant)
        e = self.courtier.etat()
        cible = d["cible"]
        # coupe-circuit : perte depuis le plus haut du capital
        pic = max(self.etat.get("pic", 0.0), e.capital)
        self.etat["pic"] = pic
        motif = ""
        if e.capital < pic * (1 - self.cfg["perte_max"]):
            cible, motif = 0.0, f"coupe-circuit : capital {e.capital:,.0f} < {1 - self.cfg['perte_max']:.0%} du plus haut {pic:,.0f}"
            self.etat["arrete"] = motif
        if self.drapeau("FERMER"):
            cible, motif = 0.0, "fichier FERMER"
        pause = self.drapeau("PAUSE") and not self.drapeau("FERMER")
        p = plan(e, cible, self.cfg["bande"])
        execs = []
        if executer and not pause:
            for a in p.actions:
                try:
                    execs.append(self.courtier.executer(a))
                except Exception as ex:  # noqa: BLE001
                    notif.envoyer(f"❌ BTC bot : ordre {a.type} {a.quantite:.6f} refusé : {ex}")
                    raise
            if self.drapeau("FERMER"):
                open(os.path.join(self.cfg["dossier"], "PAUSE"), "w").close()
        e2 = self.courtier.etat() if execs else e
        votes = " ".join(f"{k}{'?' if v is None else ('+' if v > 0 else '-')}" for k, v in d["votes"].items())
        msg = (f"BTC {d['prix']:,.0f} $ · bougie 4h {d['bougie_4h']:%d/%m %H:%M} UTC\n"
               f"score {d['score']:+.2f} · 4h {d['tendance_4h']} · {d['sens']} cible {cible:+.0%}\n"
               f"votes : {votes}\n"
               f"capital {e2.capital:,.2f} $ · exposition {e2.exposition:+.0%}"
               + (f"\nordres : " + ", ".join(f"{x['type']} {x['quantite']:.5f}" for x in execs) if execs else f"\n{p.note}")
               + (f"\n⚠️ {motif}" if motif else "") + ("\n⏸ PAUSE : aucun ordre passé" if pause else ""))
        if executer:
            if execs or motif or d["sens"] != self.etat.get("dernier_sens"):
                notif.envoyer(msg)
            else:
                log.info(msg.replace("\n", " | "))
            self.etat.update(derniere_bougie=str(d["bougie_4h"]), dernier_sens=d["sens"])
            self.journal(dict(heure=str(maintenant), bougie_4h=str(d["bougie_4h"]), prix=round(d["prix"], 2),
                              score=round(d["score"], 3), tendance_4h=d["tendance_4h"], cible=round(cible, 4),
                              capital=round(e2.capital, 2), exposition=round(e2.exposition, 4),
                              ordres=";".join(f"{x['type']}:{x['quantite']:.6f}" for x in execs), motif=motif or ("pause" if pause else "")))
            self.sauver()
        return dict(statut="ok", decision=d, plan=p, execs=execs, capital=e2.capital, exposition=e2.exposition, message=msg)


def prochain_reveil(maintenant, delai_s):
    """Juste après la prochaine clôture 4h (00, 04, 08, 12, 16, 20 h UTC), avec un délai pour que la bougie soit publiée."""
    b = maintenant.floor("4h") + pd.Timedelta("4h")
    return b + pd.Timedelta(seconds=delai_s)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--config", default=os.path.join(ICI, "config.json"))
    a.add_argument("--une-fois", action="store_true")
    a.add_argument("--etat", action="store_true")
    x = a.parse_args()
    cfg = charger_config(x.config)
    os.makedirs(cfg["dossier"], exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(cfg["dossier"], "bot.log"))])
    if cfg["mode"] == "reel" and os.environ.get("BOT_REEL_CONFIRME") != "oui":
        sys.exit("Mode réel : définis BOT_REEL_CONFIRME=oui dans l'environnement pour confirmer (garde-fou).")
    bot = Bot(cfg)
    log.info(f"démarrage : mode {cfg['mode']}, profil {cfg['profil']} {bot.profil}, bande {cfg['bande']:.0%}, "
             f"coupe-circuit {cfg['perte_max']:.0%}")
    if x.etat:
        r = bot.cycle(executer=False)
        print(r.get("message", r))
        return
    if x.une_fois:
        r = bot.cycle()
        print(r.get("message", r))
        return
    notif.envoyer(f"▶️ BTC bot démarré ({cfg['mode']}, profil {cfg['profil']})")
    while True:
        try:
            r = bot.cycle()
            log.info(f"cycle : {r['statut']}")
        except Exception as e:  # noqa: BLE001
            log.exception("cycle en erreur")
            notif.envoyer(f"❌ BTC bot : erreur de cycle ({e}). Nouvel essai dans 5 minutes.")
            time.sleep(300)
            continue
        reveil = prochain_reveil(pd.Timestamp.now(tz="UTC"), cfg["delai_s"])
        time.sleep(max(5, (reveil - pd.Timestamp.now(tz="UTC")).total_seconds()))


if __name__ == "__main__":
    main()
