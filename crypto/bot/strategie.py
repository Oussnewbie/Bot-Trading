"""La décision : exactement le système testé (btc.elements + btc.position), appliqué aux données du cycle.

Une seule source de vérité pour la logique : le bot n'a pas sa propre copie des règles. S'il y a un écart entre le test
et le bot, c'est un bug ; `test_bot.py` le vérifie.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import btc  # noqa: E402

PROFILS = {
    # vol_cible : volatilité visée ; plafond : exposition maximale (1 = pas de levier) ; vente : taille de la vente
    "prudent": dict(vol_cible=0.4, plafond=1.0, vente=0.25),
    "equilibre": dict(vol_cible=0.6, plafond=1.0, vente=0.25),
}
SEUIL, CONFIRMATION = 0.25, "ema50/200"


class DonneesInvalides(Exception):
    pass


def verifier(B, maintenant):
    """Refuse de décider sur des données trop vieilles ou trouées."""
    d1, d4 = B["d1"], B["d4"]
    if len(d1) < 260 or len(d4) < 250:
        raise DonneesInvalides(f"historique trop court ({len(d1)} jours, {len(d4)} bougies 4h)")
    fin4 = d4.index[-1] + pd.Timedelta("4h")
    if maintenant - fin4 > pd.Timedelta("4h"):
        raise DonneesInvalides(f"dernière bougie 4h clôturée à {fin4:%Y-%m-%d %H:%M} : données en retard")
    fin1 = d1.index[-1] + pd.Timedelta("1D")
    if maintenant - fin1 > pd.Timedelta("1D"):
        raise DonneesInvalides(f"dernière bougie journalière clôturée à {fin1:%Y-%m-%d} : données en retard")
    if (d4.close.iloc[-50:] <= 0).any() or d4.close.iloc[-50:].isna().any():
        raise DonneesInvalides("prix nuls ou manquants dans les dernières bougies 4h")


def decider(B, profil, maintenant):
    verifier(B, maintenant)
    p = PROFILS[profil] if isinstance(profil, str) else profil
    E = btc.elements(B)
    pos = btc.position(E, seuil=SEUIL, confirmation=CONFIRMATION, vente=p["vente"], vol_cible=p["vol_cible"])
    cible = float(np.clip(pos.iloc[-1], -p["plafond"], p["plafond"]))
    ch, cb = E["conf"][CONFIRMATION]
    votes = E["votes"].iloc[-1]
    absents = [k for k, v in votes.items() if np.isnan(v)]
    if len(absents) > 2:
        raise DonneesInvalides(f"trop de votes absents : {absents}")
    return dict(
        bougie_4h=E["c4"].index[-1], jour=E["votes"].index[-1], prix=float(E["c4"].iloc[-1]),
        votes={k: (None if np.isnan(v) else int(v)) for k, v in votes.items()},
        score=float(E["score4"].iloc[-1]), tendance_4h="haussière" if ch.iloc[-1] else ("baissière" if cb.iloc[-1] else "neutre"),
        volatilite=float(E["vol4"].iloc[-1]), cible=cible,
        sens="ACHAT" if cible > 0 else ("VENTE" if cible < 0 else "RIEN"))
