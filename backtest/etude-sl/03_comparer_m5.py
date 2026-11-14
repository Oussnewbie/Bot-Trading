"""Étape 1.4a — Le M5 reconstruit à partir du M1 est-il le M5 du dépôt (donnees/) ? Bougie par bougie, bid et ask.

Écrit sorties/etape1_m5.md. Aucun trade n'est joué.
"""
import os

import numpy as np
import pandas as pd

import commun as C

if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    z = np.load(C.chemin_bougies("nas100", "M5"))
    moi = pd.DataFrame({c: z[c] for c in C.COLONNES}, index=z["t"])
    out = ["# Étape 1 — M5 reconstruit contre le M5 du dépôt (NAS100)\n"]
    total_diff = 0
    for cote, p in (("bid", "b"), ("ask", "a")):
        ref = pd.read_csv(os.path.join(C.M5_DEPOT, f"usatechidxusd-m5-{cote}-2015-01-01-2026-11-01.csv")).set_index("timestamp")
        m = moi[(moi.index >= ref.index[0]) & (moi.index <= ref.index[-1])]
        seul_moi, seul_ref = m.index.difference(ref.index), ref.index.difference(m.index)
        c = m.index.intersection(ref.index)
        out.append(f"## {cote}\n")
        out.append(f"- Dépôt : {len(ref)} bougies du {C.heure_ny([ref.index[0]])[0]:%Y-%m-%d %H:%M} au {C.heure_ny([ref.index[-1]])[0]:%Y-%m-%d %H:%M} (New York).")
        out.append(f"- Reconstruit sur les mêmes dates : {len(m)} bougies. Présentes seulement dans le reconstruit : {len(seul_moi)} ; seulement dans le dépôt : {len(seul_ref)}.")
        lignes = []
        diff_any = np.zeros(len(c), dtype=bool)
        for col_ref, col in (("open", p + "o"), ("high", p + "h"), ("low", p + "l"), ("close", p + "c")):
            d = (m.loc[c, col].values - ref.loc[c, col_ref].values)
            diff = np.abs(d) > 1e-6
            diff_any |= diff
            lignes.append(f"| {col_ref} | {int(diff.sum())} | {np.abs(d).max():.6f} |")
        dv = np.abs(m.loc[c, p + "v"].values - ref.loc[c, "volume"].values)
        out.append(f"- Bougies communes : {len(c)}, dont {int(diff_any.sum())} avec au moins un prix différent.\n")
        out.append("| Prix | Bougies différentes (> 0,000001) | Écart maximal |\n|---|---|---|")
        out.extend(lignes)
        out.append(f"\nVolume : écart maximal {dv.max():.5f} (le fichier du dépôt est arrondi à 4 décimales, le M1 à 5).\n")
        total_diff += len(seul_moi) + len(seul_ref) + int(diff_any.sum())
        for nom, idx in (("seulement dans le reconstruit", seul_moi), ("seulement dans le dépôt", seul_ref), ("prix différent", c[diff_any])):
            if len(idx):
                t = C.heure_ny(idx.values)
                out.append(f"Bougies « {nom} », par année : {pd.Series(1, index=t).groupby(t.year).sum().to_dict()} ; premières : {[f'{x:%Y-%m-%d %H:%M}' for x in t[:8]]}\n")
    out.append(f"**Verdict : {'identiques' if total_diff == 0 else str(total_diff) + ' écarts, voir ci-dessus'}.**")
    with open(os.path.join(C.SORTIES, "etape1_m5.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
