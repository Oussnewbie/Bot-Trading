"""Étape 1.2 — Assemble le M1 bid + ask de chaque instrument et reconstruit M3, M5, M15, M30, H1, H4 et D1.

Lit donnees/brut/<instrument>/<instrument>-m1-<bid|ask>-<année>.csv (voir 00_telecharger.sh), écrit
donnees/bougies/<nom>-<horizon>.npz et un inventaire dans sorties/etape1_inventaire.md.
"""
import glob
import os

import numpy as np
import pandas as pd

import commun as C


def lire_cote(code, cote):
    morceaux, inventaire = [], []
    for f in sorted(glob.glob(os.path.join(C.BRUT, code, f"{code}-m1-{cote}-*.csv"))):
        an = int(os.path.basename(f)[:-4].rsplit("-", 1)[1])
        d = pd.read_csv(f)
        inventaire.append((an, len(d)))
        if len(d):
            morceaux.append(d)
    vides = sorted(int(os.path.basename(f)[:-5].rsplit("-", 1)[1]) for f in glob.glob(os.path.join(C.BRUT, code, f"{code}-m1-{cote}-*.vide")))
    d = pd.concat(morceaux, ignore_index=True)
    doublons = int(d.timestamp.duplicated().sum())
    d = d.drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
    return d, inventaire, vides, doublons


def construire(nom, code, out):
    b, inv_b, vides_b, dup_b = lire_cote(code, "bid")
    a, inv_a, vides_a, dup_a = lire_cote(code, "ask")
    seul_b, seul_a = b.index.difference(a.index), a.index.difference(b.index)
    commun = b.index.intersection(a.index)
    m1 = pd.DataFrame({
        "bo": b.loc[commun, "open"], "bh": b.loc[commun, "high"], "bl": b.loc[commun, "low"], "bc": b.loc[commun, "close"], "bv": b.loc[commun, "volume"],
        "ao": a.loc[commun, "open"], "ah": a.loc[commun, "high"], "al": a.loc[commun, "low"], "ac": a.loc[commun, "close"], "av": a.loc[commun, "volume"],
    })
    m1.index.name = "t"
    ny = C.heure_ny(m1.index.values)
    out.append(f"\n## {nom} ({code})\n")
    out.append(f"- Années sans aucune donnée chez Dukascopy : bid {vides_b or 'aucune'}, ask {vides_a or 'aucune'}.")
    out.append(f"- Première bougie M1 : bid {C.heure_ny([b.index[0]])[0]}, ask {C.heure_ny([a.index[0]])[0]} (heure de New York).")
    out.append(f"- Dernière bougie M1 : bid {C.heure_ny([b.index[-1]])[0]}, ask {C.heure_ny([a.index[-1]])[0]}.")
    out.append(f"- Doublons retirés : bid {dup_b}, ask {dup_a}. Minutes présentes d'un seul côté : bid seul {len(seul_b)}, ask seul {len(seul_a)} (écartées).")
    out.append(f"- M1 retenu : {len(m1):,} bougies.".replace(",", " "))
    out.append("\n| Année | Lignes bid | Lignes ask | Jours avec cotation | M1 par jour (médiane) |\n|---|---|---|---|---|")
    jours = pd.Series(1, index=ny).groupby([ny.year, ny.normalize().tz_localize(None)]).sum()
    da, db = dict(inv_a), dict(inv_b)
    for an in sorted(set(da) | set(db) | set(vides_b)):
        j = jours.loc[an] if an in jours.index.get_level_values(0) else pd.Series(dtype=float)
        out.append(f"| {an} | {db.get(an, 0)} | {da.get(an, 0)} | {len(j)} | {int(j.median()) if len(j) else 0} |")
    out.append("\n| Horizon | Bougies | Première | Dernière |\n|---|---|---|---|")
    for h in C.HORIZONS:
        g = C.agreger(m1, h)
        C.enregistrer(g, nom, h)
        t = C.heure_ny([g.index[0], g.index[-1]])
        out.append(f"| {h} | {len(g)} | {t[0]:%Y-%m-%d %H:%M} | {t[1]:%Y-%m-%d %H:%M} |")
        print(nom, h, len(g), flush=True)


if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    out = ["# Étape 1 — inventaire des données téléchargées et reconstruites",
           "\nSource : Dukascopy, M1 bid et ask, par `npx dukascopy-node` (voir `00_telecharger.sh`). Heures de New York.",
           "H4 et D1 sont alignées sur 17:00 New York (minuit du serveur MT5) ; M3 à H1 sur l'heure ronde."]
    for nom, code in C.INSTRUMENTS.items():
        construire(nom, code, out)
    with open(os.path.join(C.SORTIES, "etape1_inventaire.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
