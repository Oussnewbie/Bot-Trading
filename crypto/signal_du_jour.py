"""Les 9 votes de la confluence et la position voulue, à la dernière bougie journalière CLÔTURÉE (00:00 UTC).
Relancer 00_telecharger.sh (en changeant les dates de fin) puis effacer donnees/cache/ pour mettre à jour."""
import signaux as S
from confluence import votes_a_priori, dosage_vol
from robustesse import SEUIL, VOL

for actif in ("BTC", "ETH"):
    ctx = S.contexte(actif, "1d")
    v = votes_a_priori(ctx).iloc[-1]
    sc = v.mean()
    dose = dosage_vol(ctx, VOL).iloc[-1]
    pos = (1 if sc >= SEUIL else 0) * dose
    print(f"{actif} — bougie du {ctx['d'].index[-1]:%Y-%m-%d} (clôture {ctx['d'].close.iloc[-1]:,.0f} $)")
    print("   " + "  ".join(f"{k} {int(x):+d}" for k, x in v.items()))
    print(f"   score {sc:+.2f} (seuil {SEUIL}) -> position {pos:.0%} du capital (dosage volatilité {dose:.0%})\n")
