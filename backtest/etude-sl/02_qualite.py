"""Étape 1.3 — Qualité du M1 : jours manquants, trous dans la séance, spreads aberrants, jours fériés, demi-séances.

Lit donnees/bougies/<instrument>-M1.npz (toute la période : on ne joue aucun trade ici), écrit sorties/etape1_qualite.md.
« Séance » = 9:30 -> 16:00 New York, la fenêtre de l'ORB v5, pour les deux instruments.
"""
import datetime as dt
import os

import numpy as np
import pandas as pd
from dateutil.easter import easter

import commun as C

SEANCE = (570, 960)          # 9:30 -> 16:00 en minutes
FENETRE_ORB = list(range(540, 585, 5))   # bougies M5 de 9:00 à 9:40 : élan, range, deux bougies d'ordre


# ───────────────────────── calendrier américain, par règles ─────────────────────────
def _nieme(an, mois, jour_sem, n):
    d = dt.date(an, mois, 1)
    return d + dt.timedelta((jour_sem - d.weekday()) % 7 + 7 * (n - 1))


def _dernier(an, mois, jour_sem):
    d = (dt.date(an + (mois == 12), mois % 12 + 1, 1)) - dt.timedelta(1)
    return d - dt.timedelta((d.weekday() - jour_sem) % 7)


def _observe(d):
    return d - dt.timedelta(1) if d.weekday() == 5 else d + dt.timedelta(1) if d.weekday() == 6 else d


def feries_us(an):
    """Jours de fermeture complète de la bourse de New York (règles du NYSE + fermetures exceptionnelles connues)."""
    f = {}
    ny = dt.date(an, 1, 1)
    if ny.weekday() != 5:                                   # un 1er janvier un samedi n'est pas reporté
        f[_observe(ny)] = "Jour de l'an"
    f[_nieme(an, 1, 0, 3)] = "Martin Luther King"
    f[_nieme(an, 2, 0, 3)] = "Presidents' Day"
    f[easter(an) - dt.timedelta(2)] = "Vendredi saint"
    f[_dernier(an, 5, 0)] = "Memorial Day"
    if an >= 2022:
        f[_observe(dt.date(an, 6, 19))] = "Juneteenth"
    f[_observe(dt.date(an, 7, 4))] = "Independence Day"
    f[_nieme(an, 9, 0, 1)] = "Labor Day"
    f[_nieme(an, 11, 3, 4)] = "Thanksgiving"
    f[_observe(dt.date(an, 12, 25))] = "Noël"
    for d, nom in ((dt.date(2012, 10, 29), "Ouragan Sandy"), (dt.date(2012, 10, 30), "Ouragan Sandy"),
                   (dt.date(2018, 12, 5), "Deuil national (G. H. W. Bush)"), (dt.date(2025, 1, 9), "Deuil national (J. Carter)")):
        if d.year == an:
            f[d] = nom
    return f


def demi_seances_us(an):
    """Jours où la bourse de New York ferme à 13:00."""
    d = {_nieme(an, 11, 3, 4) + dt.timedelta(1): "Lendemain de Thanksgiving"}
    if dt.date(an, 12, 24).weekday() < 4:
        d[dt.date(an, 12, 24)] = "Veille de Noël"
    if 1 <= dt.date(an, 7, 4).weekday() <= 4:
        d[dt.date(an, 7, 3)] = "Veille du 4 juillet"
    return d


# ───────────────────────── contrôle d'un instrument ─────────────────────────
def hm(m):
    return f"{int(m) // 60}:{int(m) % 60:02d}"


def controle(nom, out):
    df = C.charger(nom, "M1", finale=True, motif="qualite des donnees")
    ny = df.index
    mins = (ny.hour * 60 + ny.minute).values
    jour = ny.tz_localize(None).normalize()
    df = df.assign(mins=mins, jour=jour, an=ny.year, sp=df.ac - df.bc)
    out.append(f"\n# {nom}\n")
    out.append(f"M1 du {ny[0]:%Y-%m-%d %H:%M} au {ny[-1]:%Y-%m-%d %H:%M} (New York), {len(df):,} bougies.".replace(",", " "))

    # cohérence des bougies
    bad_b = ((df.bh < df[["bo", "bc"]].max(axis=1)) | (df.bl > df[["bo", "bc"]].min(axis=1)) | (df.bh < df.bl)).sum()
    bad_a = ((df.ah < df[["ao", "ac"]].max(axis=1)) | (df.al > df[["ao", "ac"]].min(axis=1)) | (df.ah < df.al)).sum()
    out.append(f"\nBougies incohérentes (high sous open/close, low au-dessus) : bid {bad_b}, ask {bad_a}. "
               f"Valeurs manquantes : {int(df[C.COLONNES].isna().sum().sum())}. Prix nuls ou négatifs : {int((df[['bl', 'al']] <= 0).sum().sum())}.")

    # table des jours ouvrés
    s = df[(df.mins >= SEANCE[0]) & (df.mins < SEANCE[1])]
    ecart = s.groupby("jour").mins.diff()
    J = s.groupby("jour").agg(n=("mins", "size"), premier=("mins", "min"), dernier=("mins", "max"))
    J["trou"] = ecart.groupby(s.jour).max().reindex(J.index).fillna(0)
    J["trou"] = np.maximum(J.trou, J.premier - SEANCE[0] + 1)          # un début tardif est un trou
    orb = df[df.mins.isin(range(540, 585))]
    J["orb"] = orb.groupby("jour").mins.apply(lambda m: len(set(m // 5 * 5))).reindex(J.index).fillna(0)
    J["a930"] = df[(df.mins >= 570) & (df.mins < 575)].groupby("jour").size().reindex(J.index).fillna(0)
    tous = df.groupby("jour").size()
    ouvres = pd.bdate_range(jour.min(), jour.max())
    T = pd.DataFrame(index=ouvres).join(J).join(tous.rename("n_jour"))
    T["n_jour"] = T.n_jour.fillna(0); T["n"] = T.n.fillna(0)
    ans = sorted(set(T.index.year))
    fer, demi = {}, {}
    for an in ans:
        fer.update(feries_us(an)); demi.update(demi_seances_us(an))
    T["ferie"] = [fer.get(d.date(), "") for d in T.index]
    T["demi"] = [demi.get(d.date(), "") for d in T.index]
    med = T[T.n > 0].groupby(T[T.n > 0].index.year).n.median()
    T["med"] = [med.get(d.year, np.nan) for d in T.index]
    T["sans"] = T.n == 0
    T["courte"] = (T.n > 0) & ((T.dernier < 945) | (T.n < 0.6 * T.med))
    cal = (T.ferie != "") | (T.demi != "")

    # premier jour à partir duquel la séance est dense de façon durable
    dense = (T.n >= 0.9 * 390).rolling(20).sum() == 20
    debut_dense = dense.idxmax() - pd.tseries.offsets.BDay(19) if dense.any() else None
    out.append(f"\nPremière série de 20 séances de suite avec au moins 90 % des minutes cotées (351 sur 390) : "
               f"{'à partir du ' + format(debut_dense, '%Y-%m-%d') if debut_dense is not None else 'jamais'}.")

    out.append("\n## Jours et séances, par année\n")
    out.append("| Année | Jours ouvrés | Sans cotation en séance | dont jours fériés US | non expliqués | Séances courtes | dont fériés / demi-séances | non expliquées "
               "| Minutes cotées par séance (médiane, sur 390) | Séances avec un trou > 5 min | > 15 min | Fenêtre 9:00-9:45 incomplète |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for an in ans:
        t = T[T.index.year == an]; c = cal[T.index.year == an]
        pleines = t[(t.n > 0) & ~t.courte]
        out.append(f"| {an} | {len(t)} | {t.sans.sum()} | {(t.sans & (t.ferie != '')).sum()} | {(t.sans & ~c).sum()} | {t.courte.sum()} | {(t.courte & c).sum()} | {(t.courte & ~c).sum()} "
                   f"| {int(t[t.n > 0].n.median()) if (t.n > 0).any() else 0} | {(pleines.trou > 5).sum()} | {(pleines.trou > 15).sum()} | {((t.n > 0) & (t.orb < len(FENETRE_ORB))).sum()} |")
    out.append("\n« Séance courte » : dernière cotation avant 15:45, ou moins de 60 % des minutes de la médiane de l'année. "
               "« Fenêtre incomplète » : il manque au moins une des neuf bougies M5 de 9:00 à 9:40 (hors jours sans cotation). "
               "Les trous sont comptés sur les séances complètes ; une minute sans cotation n'est pas une erreur en soi.")

    def liste(titre, sel, cols, maxi=60):
        x = T[sel]
        out.append(f"\n**{titre} : {len(x)}**" + ("" if len(x) else "."))
        if len(x):
            out.append("")
            out.append("| Jour | " + " | ".join(n for n, _ in cols) + " |"); out.append("|---|" + "---|" * len(cols))
            for d, r in x.head(maxi).iterrows():
                out.append(f"| {d:%Y-%m-%d} ({'lun mar mer jeu ven'.split()[d.day_of_week]}) | " + " | ".join(str(f(r)) for _, f in cols) + " |")
            if len(x) > maxi:
                out.append(f"\n… et {len(x) - maxi} autres, par année : {x.iloc[maxi:].groupby(x.iloc[maxi:].index.year).size().to_dict()}")

    out.append("\n## Jours ouvrés à problème\n")
    liste("Jours ouvrés sans cotation en séance, hors jours fériés du calendrier", T.sans & ~cal,
          [("M1 sur toute la journée", lambda r: int(r.n_jour))])
    liste("Séances courtes hors calendrier (panne, coupe-circuit, données)", T.courte & ~cal,
          [("Minutes cotées", lambda r: int(r.n)), ("Première", lambda r: hm(r.premier)), ("Dernière", lambda r: hm(r.dernier)), ("Plus grand trou (min)", lambda r: int(r.trou))])
    liste("Jours fériés du calendrier avec une séance complète dans les données (le CFD cote, ou le calendrier se trompe)",
          (T.ferie != "") & (T.n > 0) & ~T.courte, [("Férié", lambda r: r.ferie), ("Minutes cotées", lambda r: int(r.n)), ("Dernière", lambda r: hm(r.dernier))])
    liste("Demi-séances du calendrier avec une séance complète dans les données", (T.demi != "") & (T.n > 0) & ~T.courte,
          [("Demi-séance", lambda r: r.demi), ("Minutes cotées", lambda r: int(r.n)), ("Dernière", lambda r: hm(r.dernier))])
    f_ = T[T.ferie != ""]; d_ = T[T.demi != ""]
    out.append(f"\nJours fériés US du calendrier : {len(f_)}, dont {int(f_.sans.sum())} sans cotation en séance, {int(f_.courte.sum())} en séance courte "
               f"(dernière cotation médiane {hm(f_[f_.courte].dernier.median()) if f_.courte.any() else '—'}), {int(((f_.n > 0) & ~f_.courte).sum())} en séance complète.")
    out.append(f"Demi-séances du calendrier : {len(d_)}, dont {int(d_.sans.sum())} sans cotation, {int(d_.courte.sum())} en séance courte "
               f"(dernière cotation médiane {hm(d_[d_.courte].dernier.median()) if d_.courte.any() else '—'}), {int(((d_.n > 0) & ~d_.courte).sum())} en séance complète.")
    liste("Séances complètes avec un trou de plus de 15 minutes", (T.n > 0) & ~T.courte & (T.trou > 15),
          [("Minutes cotées", lambda r: int(r.n)), ("Plus grand trou (min)", lambda r: int(r.trou))], maxi=40)
    liste("Fenêtre 9:00-9:45 incomplète (séance cotée)", (T.n > 0) & (T.orb < len(FENETRE_ORB)),
          [("Bougies M5 présentes sur 9", lambda r: int(r.orb)), ("Minutes de 9:30-9:34 cotées", lambda r: int(r.a930)), ("Férié / demi", lambda r: r.ferie or r.demi or "")], maxi=40)

    # spreads
    out.append("\n## Spread (ask - bid, à la clôture de chaque M1), en points\n")
    out.append("| Année | Séance : médiane | 99e centile | maximum | 9:30-9:45 : médiane | 99e centile | Hors séance : médiane | Ask sous le bid | Spread nul | Aberrants en séance (> 10 × la médiane) "
               "| Spread de 9:35 / range de 9:30 (médiane) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    dans = (df.mins >= SEANCE[0]) & (df.mins < SEANCE[1])
    ouv = (df.mins >= 570) & (df.mins < 585)
    r930 = df[(df.mins >= 570) & (df.mins < 575)].groupby("jour").agg(h=("bh", "max"), l=("bl", "min"))
    s935 = df[(df.mins >= 575) & (df.mins < 580)].groupby("jour").agg(bo=("bo", "first"), ao=("ao", "first"))
    cout = ((s935.ao - s935.bo) / (r930.h - r930.l).replace(0, np.nan)).dropna()
    aberrants = []
    for an in ans:
        x = df[df.an == an]; xs = x[dans[df.an == an]]; xo = x[ouv[df.an == an]]; xh = x[~dans[df.an == an]]
        if not len(xs):
            continue
        m = xs.sp.median()
        ab = xs[xs.sp > 10 * m]
        aberrants.append(ab)
        c = cout[cout.index.year == an]
        out.append(f"| {an} | {m:.2f} | {xs.sp.quantile(0.99):.2f} | {xs.sp.max():.2f} | {xo.sp.median():.2f} | {xo.sp.quantile(0.99):.2f} | {xh.sp.median():.2f} "
                   f"| {(x.sp < 0).sum()} | {(x.sp == 0).sum()} | {len(ab)} | {100 * c.median():.1f} % |")
    ab = pd.concat(aberrants) if aberrants else df.iloc[:0]
    out.append(f"\nSpreads aberrants en séance : {len(ab)} minutes sur {int(dans.sum())}, réparties sur {ab.jour.nunique()} jours. Les dix plus grands :\n")
    out.append("| Minute (New York) | Bid | Ask | Spread |\n|---|---|---|---|")
    for t, r in ab.sort_values("sp", ascending=False).head(10).iterrows():
        out.append(f"| {t:%Y-%m-%d %H:%M} | {r.bc:.2f} | {r.ac:.2f} | {r.sp:.2f} |")
    j_ab = ab.groupby("jour").size().sort_values(ascending=False).head(10)
    out.append(f"\nJours les plus touchés (minutes aberrantes) : {', '.join(f'{d:%Y-%m-%d} ({n})' for d, n in j_ab.items())}.")
    ab_orb = ab[(ab.mins >= 570) & (ab.mins < 600)]
    out.append(f"Dont entre 9:30 et 10:00 : {len(ab_orb)} minutes sur {ab_orb.jour.nunique()} jours.")

    # sauts de prix
    seuil = 0.015 if nom == "nas100" else 0.01
    mid = (df.bc + df.ac) / 2
    saut = mid.pct_change().abs()
    meme = np.diff(df.index.as_unit("s").asi8, prepend=0) <= 300
    gros = saut[(saut > seuil).values & meme]
    out.append(f"\n## Sauts de prix\n\nVariations de plus de {100 * seuil:.1f} % entre deux M1 séparées de 5 minutes au plus : {len(gros)}.")
    if len(gros):
        out.append("\n| Minute (New York) | Variation |\n|---|---|")
        for t, v in gros.sort_values(ascending=False).head(15).items():
            out.append(f"| {t:%Y-%m-%d %H:%M} | {100 * v:.2f} % |")
    return T


def debut_nas(out):
    """Le début de l'historique du Nasdaq, mois par mois : spread nul, heures cotées, mois vides."""
    df = C.charger("nas100", "M1", finale=True, motif="qualite des donnees")
    df = df[df.index < "2015-03-01"]
    ny = df.index
    df = df.assign(mins=ny.hour * 60 + ny.minute, jour=ny.tz_localize(None).normalize(), sp=df.ac - df.bc)
    s = df[(df.mins >= SEANCE[0]) & (df.mins < SEANCE[1])]
    J = s.groupby("jour").agg(n=("mins", "size"), sp=("sp", "median"), nul=("sp", lambda x: (x == 0).mean()))
    J["pre"] = df[(df.mins >= 540) & (df.mins < 570)].groupby("jour").size().reindex(J.index).fillna(0)
    J["hors"] = df[(df.mins < 540) | (df.mins >= 960)].groupby("jour").size().reindex(J.index).fillna(0)
    ouvres = pd.Series(1, index=pd.bdate_range(J.index[0], "2015-02-27"))
    ouvres = ouvres.groupby(ouvres.index.to_period("M")).sum()
    M = J.groupby(J.index.to_period("M")).agg(seances=("n", "size"), n=("n", "median"), sp=("sp", "median"), nul=("nul", "mean"),
                                              pre=("pre", lambda x: (x >= 25).sum()), hors=("hors", "median")).reindex(ouvres.index)
    trous = s[s.groupby("jour").mins.diff() > 15]
    reprise = trous.mins.map(hm).value_counts()
    pause = trous[trous.mins.isin([870, 930])]
    out.append("\n## Le début de l'historique du Nasdaq, mois par mois (jusqu'à février 2015)\n")
    out.append(f"- Premier jour avec un vrai spread (médiane de séance > 0) : **{J[J.sp > 0].index[0]:%Y-%m-%d}**. Dernier jour à spread nul : {J[J.sp == 0].index[-1]:%Y-%m-%d}.")
    out.append(f"- Premier jour avec la fenêtre 9:00-9:30 cotée (au moins 25 minutes sur 30) : **{J[J.pre >= 25].index[0]:%Y-%m-%d}**.")
    out.append(f"- Trous de plus de 15 minutes en séance avant mars 2015 : {len(trous)}, dont reprise à 14:30 : {int(reprise.get('14:30', 0))}, à 15:30 : {int(reprise.get('15:30', 0))} "
               f"(une pause de cotation quotidienne de 15 minutes, de {pause.jour.min():%Y-%m} à {pause.jour.max():%Y-%m}).\n")
    out.append("| Mois | Jours ouvrés | Séances cotées | Minutes par séance (médiane) | Spread médian | Part des minutes à spread nul | Séances avec 9:00-9:30 | Minutes hors séance par jour (médiane) |")
    out.append("|---|---|---|---|---|---|---|---|")
    for m, r in M.iterrows():
        if pd.isna(r.seances):
            out.append(f"| {m} | {ouvres[m]} | 0 | — | — | — | — | — |")
        else:
            out.append(f"| {m} | {ouvres[m]} | {int(r.seances)} | {int(r.n)} | {r.sp:.2f} | {100 * r.nul:.0f} % | {int(r.pre)} | {int(r.hors)} |")


if __name__ == "__main__":
    os.makedirs(C.SORTIES, exist_ok=True)
    out = ["# Étape 1 — qualité des données M1 (Dukascopy, bid et ask)",
           "\nHeures de New York. Aucun trade n'est joué ici. Le calendrier américain est calculé par règles (NYSE) : "
           "il sert à expliquer les séances manquantes ou courtes, pas à les définir."]
    for nom in C.INSTRUMENTS:
        controle(nom, out)
        if nom == "nas100":
            debut_nas(out)
    with open(os.path.join(C.SORTIES, "etape1_qualite.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
