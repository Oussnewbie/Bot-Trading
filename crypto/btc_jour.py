"""Le tableau du jour pour le BTC (système de RAPPORT-BTC.md), à partir des données de btc.py.

    python crypto/btc_jour.py                         profil « prudent » : vol 40 %, sans levier, vente 0,25
    python crypto/btc_jour.py --vol 0.6 --plafond 2   profil « dynamique » : vol 60 %, levier jusqu'à 2x

Mise à jour des données : python crypto/05_telecharger_btc_historique.py --maj (prix Bitstamp et on-chain), puis
bash crypto/00_telecharger.sh en changeant FIN_MOIS / les jours (order flow et ETH/BTC de Binance), et effacer
crypto/donnees/cache/. Sans order flow ni ETH/BTC à jour, ces deux votes sont absents et le score se fait sur 7.
"""
import argparse

import numpy as np
import pandas as pd

import btc

a = argparse.ArgumentParser()
a.add_argument("--vol", type=float, default=0.4)
a.add_argument("--plafond", type=float, default=1.0)
a.add_argument("--vente", type=float, default=0.25)
x = a.parse_args()

# seules les bougies CLÔTURÉES comptent : la bougie en cours (journalière ou 4h) est retirée
B = btc.tronquer(btc.brutes(), pd.Timestamp.now(tz="UTC"))
E = btc.elements(B)
v = E["votes"].iloc[-1]
sc = E["score"].iloc[-1]
ch, cb = E["conf"]["ema50/200"]
t4 = E["c4"].index[-1]
dose = min(x.plafond, x.vol / E["vol4"].iloc[-1])
etat4 = "haussière" if ch.iloc[-1] else ("baissière" if cb.iloc[-1] else "neutre")
s4 = E["score4"].iloc[-1]
if s4 >= 0.25 and ch.iloc[-1]:
    dec = f"ACHAT {dose:.0%} du capital" + (" (levier)" if dose > 1 else " (comptant)")
elif s4 <= -0.25 and cb.iloc[-1]:
    dec = f"VENTE {dose * x.vente:.0%} du capital (perpétuel)" if x.vente > 0 else "RIEN (vente désactivée)"
else:
    dec = "RIEN (stablecoins)"
print(f"BTC — dernier jour clôturé {E['votes'].index[-1]:%Y-%m-%d}, dernière bougie 4h {t4:%Y-%m-%d %H:%M} UTC, "
      f"prix {E['c4'].iloc[-1]:,.0f} $")
print("  Votes : " + "  ".join(f"{k} {'absent' if np.isnan(z) else f'{int(z):+d}'}" for k, z in v.items()))
print(f"  Score journalier {sc:+.2f} (achat >= +0,25 ; vente <= -0,25) ; tendance 4h {etat4}")
print(f"  Volatilité 30 j {E['vol4'].iloc[-1]:.0%} -> taille de base {dose:.0%} (profil vol {x.vol:.0%}, plafond {x.plafond:g}x)")
print(f"  DÉCISION : {dec}")
