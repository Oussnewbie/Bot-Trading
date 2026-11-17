"""Exécution : l'état du compte, le plan d'ordres, et deux courtiers (papier et Binance).

Deux montages, choisis par le test (voir LISEZMOI.md et profils.py) :
 « comptant » (levier ×1) :
   - ACHAT au comptant (BTC spot) : pas de financement à payer, aucune liquidation possible ;
   - VENTE en perpétuel USDⓈ-M BTCUSDT couverte à 100 % (marge = taille de la vente) : liquidation seulement si le BTC
     double.
 « perpétuel » (levier ×2 à ×10) :
   - TOUT en perpétuel USDⓈ-M BTCUSDT, tout le capital en USDT sur le portefeuille futures, marge croisée ;
   - STOP DE PROTECTION posé chez Binance à mi-chemin de la liquidation (50 % ÷ exposition contre la position) : sans
     lui, le test liquide le compte dès ×4.
Jamais d'achat et de vente en même temps. Ordres limites « post-only » (frais de teneur de marché) re-placés au
meilleur prix pendant 2 minutes, puis au marché pour le reste.
"""
import math
import os
import time
from dataclasses import dataclass, field

FRAIS = {("spot", "marche"): 0.0010, ("spot", "limite"): 0.0010, ("perp", "marche"): 0.0005, ("perp", "limite"): 0.0002}
GLISSEMENT = {"marche": 0.0002, "limite": 0.0}
MIN_SPOT_USDT, MIN_PERP_BTC, MIN_PERP_USDT = 10.0, 0.001, 100.0
GLISSEMENT_STOP = 0.005


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

    def public(self):
        return dict(prix=round(self.prix, 2), capital=round(self.capital, 2), exposition=round(self.exposition, 4),
                    usdt_spot=round(self.usdt_spot, 2), btc_spot=round(self.btc_spot, 6),
                    usdt_futures=round(self.usdt_futures, 2), perp_btc=round(self.perp_btc, 6))


@dataclass
class Action:
    type: str                    # vendre_spot | acheter_spot | perp | vers_futures | vers_spot
    quantite: float              # BTC (signé pour perp) ou USDT pour les transferts
    motif: str = ""


@dataclass
class Plan:
    actions: list = field(default_factory=list)
    note: str = ""


def montage(levier):
    return "comptant" if levier <= 1 else "perpetuel"


def plan(e: Etat, cible: float, bande: float = 0.05, montage: str = "comptant") -> Plan:
    """Les ordres qui amènent le compte à `cible` (fraction du capital, signée). `bande` : on ne retouche pas une
    position déjà dans le bon sens si l'écart est plus petit (évite de payer des frais pour des ajustements de quelques
    %). Fermer, ouvrir ou changer de sens se fait toujours. Ordre : réduire, puis déplacer la marge, puis augmenter."""
    C, px = e.capital, e.prix
    P = Plan()
    expo = e.exposition
    if montage == "comptant":
        spot_vise, perp_vise = max(cible, 0.0) * C / px, min(cible, 0.0) * C / px
        meme_sens = (cible > 0 and e.btc_spot * px > MIN_SPOT_USDT and abs(e.perp_btc) < MIN_PERP_BTC) or \
                    (cible < 0 and e.perp_btc <= -MIN_PERP_BTC and e.btc_spot * px < MIN_SPOT_USDT)
    else:
        spot_vise, perp_vise = 0.0, cible * C / px
        meme_sens = e.btc_spot * px < MIN_SPOT_USDT and abs(e.perp_btc) >= MIN_PERP_BTC and cible != 0 and \
            math.copysign(1, cible) == math.copysign(1, e.perp_btc)
    if meme_sens and abs(cible - expo) < bande:
        P.note = f"écart {cible - expo:+.1%} sous la bande de {bande:.0%} : rien à faire"
        return P

    # 1. réduire ce qui doit baisser
    if e.btc_spot - spot_vise > 0 and (e.btc_spot - spot_vise) * px >= MIN_SPOT_USDT:
        q = e.btc_spot if spot_vise == 0 else e.btc_spot - spot_vise
        P.actions.append(Action("vendre_spot", q, "réduire l'achat" if spot_vise else "fermer l'achat au comptant"))
    if abs(e.perp_btc) >= MIN_PERP_BTC:
        retourne = perp_vise == 0 or math.copysign(1, perp_vise) != math.copysign(1, e.perp_btc)
        if retourne:
            P.actions.append(Action("perp", -e.perp_btc, "fermer la position perpétuelle"))
        elif abs(perp_vise) < abs(e.perp_btc) and (abs(e.perp_btc) - abs(perp_vise)) * px >= MIN_PERP_USDT:
            P.actions.append(Action("perp", perp_vise - e.perp_btc, "réduire la position perpétuelle"))
    # 2. la marge
    if montage == "comptant":
        marge_visee = -perp_vise * px                      # vente couverte à 100 %
        if perp_vise == 0 and e.usdt_futures > 1:
            P.actions.append(Action("vers_spot", e.usdt_futures, "rapatrier la marge"))
        elif perp_vise < 0 and marge_visee - e.usdt_futures > 1:
            P.actions.append(Action("vers_futures", marge_visee - e.usdt_futures, "marge de la vente"))
    else:
        dispo = e.usdt_spot + max(e.btc_spot - spot_vise, 0) * px
        if dispo > 1:
            P.actions.append(Action("vers_futures", dispo, "tout le capital sur le portefeuille futures"))
    # 3. augmenter ce qui doit monter
    deja = 0.0 if any(a.type == "perp" and "fermer" in a.motif for a in P.actions) else e.perp_btc
    if perp_vise != 0 and abs(perp_vise) > abs(deja) and (abs(perp_vise) - abs(deja)) * px >= MIN_PERP_USDT:
        P.actions.append(Action("perp", perp_vise - deja, "ouvrir la position perpétuelle" if deja == 0 else "augmenter la position perpétuelle"))
    if spot_vise - e.btc_spot > 0 and (spot_vise - e.btc_spot) * px >= MIN_SPOT_USDT:
        P.actions.append(Action("acheter_spot", spot_vise - e.btc_spot, "ouvrir l'achat au comptant" if e.btc_spot * px < MIN_SPOT_USDT else "augmenter l'achat"))
    P.note = f"exposition {expo:+.1%} -> {cible:+.1%}"
    return P


def prix_stop(cible, prix, montage):
    """Stop de protection du montage perpétuel : à mi-chemin de la liquidation. Aucun en montage comptant."""
    if montage != "perpetuel" or cible == 0:
        return None
    s = 0.5 / abs(cible)
    return round(prix * (1 - s), 1) if cible > 0 else round(prix * (1 + s), 1)


class CourtierPapier:
    """Compte fictif : prix réels, frais et glissement du test, financement au taux de base (0,01 % / 8 h, payé par les
    acheteurs en perpétuel, reçu par les vendeurs), stop de protection vérifié sur le plus haut / plus bas des bougies
    4h écoulées. L'état est gardé dans un fichier JSON par le bot."""

    def __init__(self, etat_json=None, capital=10_000.0, ordres="marche"):
        s = etat_json or {}
        self.usdt_spot = s.get("usdt_spot", capital)
        self.btc_spot = s.get("btc_spot", 0.0)
        self.usdt_futures = s.get("usdt_futures", 0.0)       # marge (sans les gains latents)
        self.perp_btc = s.get("perp_btc", 0.0)
        self.perp_prix = s.get("perp_prix", 0.0)
        self.stop = s.get("stop")
        self.dernier_financement = s.get("dernier_financement")
        self.prix_courant = s.get("prix", 0.0)
        self.ordres = ordres

    def exporter(self):
        return dict(usdt_spot=self.usdt_spot, btc_spot=self.btc_spot, usdt_futures=self.usdt_futures, perp_btc=self.perp_btc,
                    perp_prix=self.perp_prix, stop=self.stop, dernier_financement=self.dernier_financement, prix=self.prix_courant)

    def configurer(self, levier, montage_):
        pass

    def fixer_prix(self, prix, maintenant=None):
        if maintenant is not None and self.perp_btc != 0 and self.dernier_financement:
            import pandas as pd
            n = int((maintenant - pd.Timestamp(self.dernier_financement)) / pd.Timedelta("8h"))
            self.usdt_futures += -self.perp_btc * prix * 0.0001 * max(n, 0)
        if maintenant is not None:
            self.dernier_financement = str(maintenant)
        self.prix_courant = prix

    def verifier_stop(self, haut, bas):
        """Le stop a-t-il été touché pendant les bougies écoulées ? Si oui, la position est fermée au prix du stop moins
        le glissement, comme le ferait Binance."""
        if not self.stop or not self.perp_btc:
            return None
        p = self.stop["prix"]
        if (self.perp_btc > 0 and bas <= p) or (self.perp_btc < 0 and haut >= p):
            px = p * (1 - GLISSEMENT_STOP) if self.perp_btc > 0 else p * (1 + GLISSEMENT_STOP)
            q = -self.perp_btc
            self._perp(q, px, "marche")
            self.stop = None
            return dict(type="stop", quantite=q, prix=px)
        return None

    def poser_stop(self, prix):
        self.stop = {"prix": prix} if prix else None

    def etat(self):
        latent = self.perp_btc * (self.prix_courant - self.perp_prix) if self.perp_btc else 0.0
        return Etat(self.prix_courant, self.usdt_spot, self.btc_spot, self.usdt_futures + latent, self.perp_btc)

    def _perp(self, q, pxe, mode):
        pos, entree = self.perp_btc, self.perp_prix
        if pos and math.copysign(1, q) != math.copysign(1, pos):
            fermee = min(abs(q), abs(pos))
            self.usdt_futures += fermee * (pxe - entree) * math.copysign(1, pos)
            reste = abs(q) - fermee
            pos = pos + math.copysign(fermee, q)
            if reste > 1e-12:
                pos, entree = math.copysign(reste, q), pxe
        else:
            nouveau = pos + q
            entree = (abs(pos) * entree + abs(q) * pxe) / abs(nouveau)
            pos = nouveau
        self.usdt_futures -= abs(q) * pxe * FRAIS[("perp", mode)]
        self.perp_btc = pos if abs(pos) > 1e-12 else 0.0
        self.perp_prix = entree if self.perp_btc else 0.0

    def executer(self, a: Action):
        px, mode = self.prix_courant, self.ordres
        g, fs = GLISSEMENT[mode], FRAIS[("spot", mode)]
        if a.type == "acheter_spot":
            q = min(a.quantite, self.usdt_spot / (px * (1 + g) * (1 + fs)))
            self.usdt_spot -= q * px * (1 + g) * (1 + fs)
            self.btc_spot += q
            return dict(type=a.type, quantite=q, prix=px * (1 + g))
        if a.type == "vendre_spot":
            q = min(a.quantite, self.btc_spot)
            self.btc_spot -= q
            self.usdt_spot += q * px * (1 - g) * (1 - fs)
            return dict(type=a.type, quantite=q, prix=px * (1 - g))
        if a.type == "perp":
            pxe = px * (1 + g * math.copysign(1, a.quantite))
            self._perp(a.quantite, pxe, mode)
            if not self.perp_btc:
                self.stop = None
            return dict(type=a.type, quantite=a.quantite, prix=pxe)
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
    """Binance réel (ou testnet) par ccxt. Clé SANS droit de retrait, limitée à l'adresse IP de la machine du bot,
    droits « lecture », « spot » et « futures » seulement."""

    SPOT, PERP = "BTC/USDT", "BTC/USDT:USDT"
    ESSAIS_LIMITE, ATTENTE_S = 8, 15

    def __init__(self, cle, secret, testnet=False, ordres="limite"):
        import ccxt
        if not cle or not secret:
            raise RuntimeError("clé et secret Binance manquants (onglet Bitcoin d'Étrave, ou BINANCE_API_KEY / BINANCE_API_SECRET)")
        opts = dict(apiKey=cle, secret=secret, enableRateLimit=True)
        self.spot = ccxt.binance(opts)
        self.fut = ccxt.binanceusdm(opts)
        if testnet:
            self.spot.set_sandbox_mode(True)
            self.fut.set_sandbox_mode(True)
        self.spot.load_markets(); self.fut.load_markets()
        self.ordres = ordres

    def configurer(self, levier, montage_):
        """Levier et marge du perpétuel : ×1 isolée pour la vente couverte, ×L croisée pour le montage perpétuel."""
        try:
            self.fut.set_margin_mode("isolated" if montage_ == "comptant" else "cross", self.PERP)
        except Exception:  # noqa: BLE001  (déjà réglé, ou impossible tant qu'une position est ouverte)
            pass
        try:
            self.fut.set_leverage(1 if montage_ == "comptant" else int(math.ceil(levier)), self.PERP)
        except Exception:  # noqa: BLE001
            pass

    def fixer_prix(self, prix, maintenant=None):
        pass

    def verifier_stop(self, haut, bas):
        return None            # chez Binance, le stop s'exécute tout seul : on le voit dans les soldes

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

    # ── ordres
    def _ordre(self, ex, sym, cote, quantite, params=None):
        """Ordre limite post-only au meilleur prix, re-placé jusqu'à 8 fois (≈ 2 min), puis le reste au marché."""
        params = dict(params or {})
        restant = float(ex.amount_to_precision(sym, quantite))
        fait, ids = 0.0, []
        if self.ordres == "limite":
            for _ in range(self.ESSAIS_LIMITE):
                if restant <= 0:
                    break
                carnet = ex.fetch_order_book(sym, 5)
                prix = carnet["bids"][0][0] if cote == "buy" else carnet["asks"][0][0]
                try:
                    o = ex.create_order(sym, "limit", cote, restant, prix, {**params, "postOnly": True})
                except Exception:  # noqa: BLE001  (le prix a bougé : l'ordre aurait été preneur, on recommence)
                    time.sleep(1)
                    continue
                ids.append(o["id"])
                time.sleep(self.ATTENTE_S)
                o = ex.fetch_order(o["id"], sym)
                if o.get("status") != "closed":
                    try:
                        ex.cancel_order(o["id"], sym)
                    except Exception:  # noqa: BLE001  (déjà exécuté entre-temps)
                        pass
                    o = ex.fetch_order(o["id"], sym)
                rempli = float(o.get("filled") or 0)
                fait += rempli
                restant = float(ex.amount_to_precision(sym, max(restant - rempli, 0))) if restant - rempli > 0 else 0.0
        if restant > 0:
            try:
                o = ex.create_order(sym, "market", cote, restant, None, params)
                ids.append(o["id"]); fait += float(o.get("filled") or restant)
            except Exception as e:  # noqa: BLE001
                if fait == 0:
                    raise
                raise RuntimeError(f"{fait} exécuté en limite, le reste au marché a échoué : {e}") from None
        return dict(quantite=fait, ordres=ids)

    def executer(self, a: Action):
        if a.type == "acheter_spot":
            r = self._ordre(self.spot, self.SPOT, "buy", a.quantite * 0.998)          # garde de quoi payer les frais
        elif a.type == "vendre_spot":
            libre = float(self.spot.fetch_balance().get("BTC", {}).get("free", 0) or 0)
            r = self._ordre(self.spot, self.SPOT, "sell", min(a.quantite, libre))
        elif a.type == "perp":
            reduit = "fermer" in a.motif or "réduire" in a.motif
            if reduit:
                self.annuler_stop()
            r = self._ordre(self.fut, self.PERP, "buy" if a.quantite > 0 else "sell", abs(a.quantite),
                            {"reduceOnly": True} if reduit else {})
        elif a.type == "vers_futures":
            libre = float(self.spot.fetch_balance().get("USDT", {}).get("free", 0) or 0)
            m = math.floor(min(a.quantite, libre) * 100) / 100
            r = dict(quantite=m, ordres=[str(self.spot.transfer("USDT", m, "spot", "future").get("id"))]) if m > 0 else dict(quantite=0)
        elif a.type == "vers_spot":
            libre = float(self.fut.fetch_balance().get("USDT", {}).get("free", 0) or 0)
            m = math.floor(min(a.quantite, libre) * 100) / 100
            r = dict(quantite=m, ordres=[str(self.spot.transfer("USDT", m, "future", "spot").get("id"))]) if m > 0 else dict(quantite=0)
        else:
            raise ValueError(a.type)
        return dict(type=a.type, **r)

    def annuler_stop(self):
        for o in self.fut.fetch_open_orders(self.PERP):
            if "STOP" in str(o.get("type", "")).upper() or o.get("stopPrice"):
                try:
                    self.fut.cancel_order(o["id"], self.PERP)
                except Exception:  # noqa: BLE001
                    pass

    def poser_stop(self, prix):
        """Stop au marché qui ferme toute la position perpétuelle (closePosition), déclenché sur le prix de marque."""
        self.annuler_stop()
        if not prix:
            return
        pos = self.etat().perp_btc
        if abs(pos) < MIN_PERP_BTC:
            return
        self.fut.create_order(self.PERP, "STOP_MARKET", "sell" if pos > 0 else "buy", abs(pos), None,
                              {"stopPrice": prix, "closePosition": True, "workingType": "MARK_PRICE"})
