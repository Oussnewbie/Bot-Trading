"""Étape 1.2 — Reconstruit M1 (bid + ask alignés), M3, M5, M15, M30, H1, H4 et D1 à partir des zips M1 de donnees/.

Écrit donnees/cache/bougies/<nom>-<horizon>.npz (hors git) et un inventaire dans sorties/etape1_inventaire.md.
"""
import os

import pandas as pd

import commun as C


def construire(nom, code, out):
    m1 = C.lire_m1(nom)
    ny = C.heure_ny(m1.index.values)
    out.append(f"\n## {nom} ({code})\n")
    out.append(f"- Fichiers : {len(C.load10.zips(nom))} zips dans `donnees/{nom}/`.")
    out.append(f"- Première bougie M1 : {ny[0]:%Y-%m-%d %H:%M}, dernière : {ny[-1]:%Y-%m-%d %H:%M} (heure de New York).")
    out.append(f"- M1 retenu (minutes présentes en bid et en ask) : {len(m1):,} bougies.".replace(",", " "))
    out.append("\n| Année | M1 | Jours avec cotation | M1 par jour (médiane) |\n|---|---|---|---|")
    jours = pd.Series(1, index=ny).groupby([ny.year, ny.normalize().tz_localize(None)]).sum()
    for an in sorted(set(ny.year)):
        j = jours.loc[an]
        out.append(f"| {an} | {int(j.sum())} | {len(j)} | {int(j.median())} |")
    out.append("\n| Horizon | Bougies | Première | Dernière |\n|---|---|---|---|")
    for h in C.HORIZONS:
        g = C.agreger(m1, h)
        C.enregistrer(g, nom, h)
        t = C.heure_ny([g.index[0], g.index[-1]])
        out.append(f"| {h} | {len(g)} | {t[0]:%Y-%m-%d %H:%M} | {t[1]:%Y-%m-%d %H:%M} |")
        print(nom, h, len(g), flush=True)


if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    out = ["# Étape 1 — inventaire des données du dépôt et des horizons reconstruits",
           "\nSource : Dukascopy, M1 bid et ask (`00_telecharger.sh`), un zip par année dans `donnees/`. Heures de New York.",
           "H4 et D1 sont alignées sur 17:00 New York (minuit du serveur MT5) ; M3 à H1 sur l'heure ronde."]
    for nom, code in C.INSTRUMENTS.items():
        construire(nom, code, out)
    with open(os.path.join(C.SORTIES, "etape1_inventaire.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
