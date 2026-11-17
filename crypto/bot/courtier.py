"""Exécution : l'état du compte, le plan d'ordres, et deux courtiers (papier et Binance).

Montage (choisi par le test, voir LISEZMOI.md) :
 - ACHAT au comptant (BTC spot) : pas de financement à payer, aucune liquidation possible ;
 - VENTE en perpétuel USDⓈ-M BTCUSDT, couverte à 100 % : on transfère sur le portefeuille futures autant d'USDT que la
   taille de la vente (levier 1) ; liquidation seulement si le BTC double ;
 - jamais d'achat et de vente en même temps ; pas de levier dans cette version.
"""
import math
import os
from dataclasses import dataclass, field

FRAIS_SPOT, FRAIS_PERP, GLISSEMENT = 0.0010, 0.0005, 0.0002
MIN_SPOT_USDT, MIN_PERP_BTC, MIN_PERP_USDT = 10.0, 0.001, 100.0


@dataclass
class Etat:
    prix: float
    usdt_spot: float
    btc_spot: float
    usdt_futures: float          # solde du portefeuille futures, gains et pertes latents compris
    perp_btc: float              # position perpétuelle signée (négative = vente)

    @property
    def capital(self):
        return self.usdt_spot + self.btc_spot * self.prix + self.usdt_futures

    @property
    def exposition(self):
        return (self.btc_spot + self.perp_btc) * self.prix / self.capital if self.capital > 0 else 0.0


@dataclass
class Action:
    type: str                    # vendre_spot | acheter_spot | perp | vers_futures | vers_spot
    quantite: float              # BTC (signé pour perp) ou USDT pour les transferts
    motif: str = ""


@dataclass
class Plan:
    actions: list = field(default_factory=list)
    note: str = ""


def plan(e: Etat, cible: float, bande: float = 0.05) -> Plan:
    """Les ordres qui amènent le compte à `cible` (fraction du capital : > 0 achat au comptant, < 0 vente en perpétuel).
    `bande` : on ne retouche pas une position déjà dans le bon sens si l'écart est plus petit (évite de payer des frais
    pour des ajustements de quelques %). Fermer, ouvrir ou changer de sens se fait toujours."""
    C, px = e.capital, e.prix
    P = Plan()
    spot_vise = max(cible, 0.0) * C / px
    perp_vise = min(cible, 0.0) * C / px
    expo_actuelle = e.exposition

    meme_sens = (cible > 0 and e.btc_spot * px > MIN_SPOT_USDT and abs(e.perp_btc) < MIN_PERP_BTC) or \
                (cible < 0 and e.perp_btc <= -MIN_PERP_BTC and e.btc_spot * px < MIN_SPOT_USDT)
    if meme_sens and abs(cible - expo_actuelle) < bande:
        P.note = f"écart {cible - expo_actuelle:+.1%} sous la bande de {bande:.0%} : rien à faire"
        return P

    # 1. réduire ce qui doit baisser
    if e.btc_spot - spot_vise > 0 and (e.btc_spot - spot_vise) * px >= MIN_SPOT_USDT:
        q = e.btc_spot if spot_vise == 0 else e.btc_spot - spot_vise
        P.actions.append(Action("vendre_spot", q, "réduire l'achat" if spot_vise else "fermer l'achat"))
    if perp_vise - e.perp_btc > 0 and abs(e.perp_btc) >= MIN_PERP_BTC:
        q = -e.perp_btc if perp_vise == 0 else perp_vise - e.perp_btc
        P.actions.append(Action("perp", q, "fermer la vente" if perp_vise == 0 else "réduire la vente"))
    # 2. marge du perpétuel : exactement la taille de la vente visée (levier 1)
    marge_visee = -perp_vise * px
    if perp_vise == 0 and e.usdt_futures > 1:
        P.actions.append(Action("vers_spot", e.usdt_futures, "rapatrier la marge"))
    elif perp_vise < 0 and marge_visee - e.usdt_futures > 1:
        P.actions.append(Action("vers_futures", marge_visee - e.usdt_futures, "marge de la vente"))
    # 3. augmenter ce qui doit monter
    if perp_vise - e.perp_btc < 0 and abs(perp_vise - e.perp_btc) * px >= MIN_PERP_USDT:
        P.actions.append(Action("perp", perp_vise - e.perp_btc, "ouvrir la vente" if abs(e.perp_btc) < MIN_PERP_BTC else "augmenter la vente"))
    if spot_vise - e.btc_spot > 0 and (spot_vise - e.btc_spot) * px >= MIN_SPOT_USDT:
        P.actions.append(Action("acheter_spot", spot_vise - e.btc_spot, "ouvrir l'achat" if e.btc_spot * px < MIN_SPOT_USDT else "augmenter l'achat"))
    P.note = f"exposition {expo_actuelle:+.1%} -> {cible:+.1%}"
    return P


class CourtierPapier:
    """Compte fictif : prix réels, frais et glissement du test, financement du perpétuel au taux de base (0,01 % / 8 h).
    L'état est gardé dans un fichier JSON par le bot."""

    def __init__(self, etat_json=None, capital=10_000.0):
        s = etat_json or {}
        self.usdt_spot = s.get("usdt_spot", capital)
        self.btc_spot = s.get("btc_spot", 0.0)
        self.usdt_futures = s.get("usdt_futures", 0.0)       # marge (sans les gains latents)
        self.perp_btc = s.get("perp_btc", 0.0)
        self.perp_prix = s.get("perp_prix", 0.0)
        self.dernier_financement = s.get("dernier_financement")
        self.prix_courant = s.get("prix", 0.0)

    def exporter(self):
        return dict(usdt_spot=self.usdt_spot, btc_spot=self.btc_spot, usdt_futures=self.usdt_futures, perp_btc=self.perp_btc,
                    perp_prix=self.perp_prix, dernier_financement=self.dernier_financement, prix=self.prix_courant)

    def fixer_prix(self, prix, maintenant=None):
        # financement : le vendeur reçoit 0,01 % de la valeur toutes les 8 h (taux de base)
        if maintenant is not None and self.perp_btc != 0 and self.dernier_financement:
            import pandas as pd
            n = int((maintenant - pd.Timestamp(self.dernier_financement)) / pd.Timedelta("8h"))
            self.usdt_futures += -self.perp_btc * prix * 0.0001 * max(n, 0)
        if maintenant is not None:
            self.dernier_financement = str(maintenant)
        self.prix_courant = prix

    def etat(self):
        latent = self.perp_btc * (self.prix_courant - self.perp_prix) if self.perp_btc else 0.0
        return Etat(self.prix_courant, self.usdt_spot, self.btc_spot, self.usdt_futures + latent, self.perp_btc)

    def executer(self, a: Action):
        px = self.prix_courant
        if a.type == "acheter_spot":
            q = min(a.quantite, self.usdt_spot / (px * (1 + GLISSEMENT) * (1 + FRAIS_SPOT)))
            self.usdt_spot -= q * px * (1 + GLISSEMENT) * (1 + FRAIS_SPOT)
            self.btc_spot += q
            return dict(type=a.type, quantite=q, prix=px * (1 + GLISSEMENT))
        if a.type == "vendre_spot":
            q = min(a.quantite, self.btc_spot)
            self.btc_spot -= q
            self.usdt_spot += q * px * (1 - GLISSEMENT) * (1 - FRAIS_SPOT)
            return dict(type=a.type, quantite=q, prix=px * (1 - GLISSEMENT))
        if a.type == "perp":
            q = a.quantite
            pxe = px * (1 + GLISSEMENT * math.copysign(1, q))     # on achète un peu plus cher, on vend un peu moins cher
            pos, entree = self.perp_btc, self.perp_prix
            if pos and math.copysign(1, q) != math.copysign(1, pos):
                # réduction : gain réalisé sur la partie fermée, au prix moyen d'entrée
                fermee = min(abs(q), abs(pos))
                self.usdt_futures += fermee * (pxe - entree) * math.copysign(1, pos)
                reste = abs(q) - fermee
                pos = pos + math.copysign(fermee, q)
                if reste > 1e-12:                                  # retournement : le reste ouvre une position neuve
                    pos, entree = math.copysign(reste, q), pxe
            else:
                nouveau = pos + q
                entree = (abs(pos) * entree + abs(q) * pxe) / abs(nouveau)
                pos = nouveau
            self.usdt_futures -= abs(q) * pxe * FRAIS_PERP
            self.perp_btc = pos if abs(pos) > 1e-12 else 0.0
            self.perp_prix = entree if self.perp_btc else 0.0
            return dict(type=a.type, quantite=q, prix=pxe)
        if a.type == "vers_futures":
            m = min(a.quantite, self.usdt_spot)
            self.usdt_spot -= m; self.usdt_futures += m
            return dict(type=a.type, quantite=m)
        if a.type == "vers_spot":
            m = min(a.quantite, max(self.usdt_futures, 0)) if not self.perp_btc else 0
            self.usdt_futures -= m; self.usdt_spot += m
            return dict(type=a.type, quantite=m)
        raise ValueError(a.type)


class CourtierBinance:
    """Binance réel (ou testnet) par ccxt. Clés lues dans l'environnement : BINANCE_API_KEY et BINANCE_API_SECRET.
    Clé SANS droit de retrait, limitée à l'adresse IP de la machine du bot, droits « spot » et « futures » seulement."""

    SPOT, PERP = "BTC/USDT", "BTC/USDT:USDT"

    def __init__(self, testnet=False):
        import ccxt
        cle, secret = os.environ.get("BINANCE_API_KEY"), os.environ.get("BINANCE_API_SECRET")
        if not cle or not secret:
            raise RuntimeError("BINANCE_API_KEY et BINANCE_API_SECRET doivent être définies dans l'environnement")
        opts = dict(apiKey=cle, secret=secret, enableRateLimit=True)
        self.spot = ccxt.binance(opts)
        self.fut = ccxt.binanceusdm(opts)
        if testnet:
            self.spot.set_sandbox_mode(True)
            self.fut.set_sandbox_mode(True)
        self.spot.load_markets(); self.fut.load_markets()
        try:
            self.fut.set_leverage(1, self.PERP)
            self.fut.set_margin_mode("isolated", self.PERP)
        except Exception:  # noqa: BLE001  (déjà réglé, ou position ouverte)
            pass

    def fixer_prix(self, prix, maintenant=None):
        pass

    def etat(self):
        px = float(self.spot.fetch_ticker(self.SPOT)["last"])
        bs = self.spot.fetch_balance()
        bf = self.fut.fetch_balance()
        marge = float(bf["info"].get("totalMarginBalance", bf.get("USDT", {}).get("total", 0) or 0))
        pos = 0.0
        for p in self.fut.fetch_positions([self.PERP]):
            q = float(p.get("contracts") or 0)
            pos += -q if p.get("side") == "short" else q
        return Etat(px, float(bs.get("USDT", {}).get("total", 0) or 0), float(bs.get("BTC", {}).get("total", 0) or 0), marge, pos)

    def executer(self, a: Action):
        if a.type == "acheter_spot":
            q = float(self.spot.amount_to_precision(self.SPOT, a.quantite * 0.998))     # garde de quoi payer les frais
            o = self.spot.create_order(self.SPOT, "market", "buy", q)
        elif a.type == "vendre_spot":
            libre = float(self.spot.fetch_balance().get("BTC", {}).get("free", 0) or 0)
            q = float(self.spot.amount_to_precision(self.SPOT, min(a.quantite, libre)))
            o = self.spot.create_order(self.SPOT, "market", "sell", q)
        elif a.type == "perp":
            q = float(self.fut.amount_to_precision(self.PERP, abs(a.quantite)))
            reduit = "fermer" in a.motif or "réduire" in a.motif
            o = self.fut.create_order(self.PERP, "market", "buy" if a.quantite > 0 else "sell", q,
                                      params={"reduceOnly": True} if reduit else {})
        elif a.type == "vers_futures":
            o = self.spot.transfer("USDT", round(a.quantite, 2), "spot", "future")
        elif a.type == "vers_spot":
            libre = float(self.fut.fetch_balance().get("USDT", {}).get("free", 0) or 0)
            o = self.spot.transfer("USDT", round(min(a.quantite, libre), 2), "future", "spot")
        else:
            raise ValueError(a.type)
        return dict(type=a.type, quantite=a.quantite, ordre=o.get("id") if isinstance(o, dict) else str(o),
                    prix=(o.get("average") if isinstance(o, dict) else None))
