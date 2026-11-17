"""Les biais, corrigés un par un, sur le BTC seul (voir btc.py). Sortie : sorties/btc-biais.txt

B1 Choix après coup -> walk-forward : chaque 1er janvier (2014 -> 2026), le réglage au meilleur Sharpe sur tout le
   passé disponible (depuis 2012-07) parmi les 135 de la grille est retenu pour l'année qui suit.
B2 Trop peu de cycles -> 2012-2017 (Bitstamp), jamais utilisé : 3 krachs de plus (2013-2015, début 2018 exclu).
B3 Complexité inutile -> comparaison avec achat-conservation, MA200 seule, croisement EMA 50/200, confluence seule.
B4 Surajustement de la grille -> PBO par CSCV (16 blocs, 12 870 combinaisons) ; plateau des réglages voisins.
B5 Chance -> bootstrap par blocs de 20 jours : intervalles de confiance, probabilité de battre les références.
B6 Date de départ -> départ chaque trimestre de 2013 à 2024.
B7 Frais -> × 0,5, 1, 2, 3.
B8 Regard vers le futur -> audit : 40 instants au hasard, le système est recalculé avec les seules données connues à
   cet instant ; sa position doit être IDENTIQUE à celle du calcul complet.
"""
import io
import itertools
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import partage  # noqa: F401,E402  (donnees, indicateurs, btc : dans bitcoin/, partagés avec le bot)
import btc
import indicateurs as I

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sorties")
T = lambda s: pd.Timestamp(s, tz="UTC")


def nom(r):
    return f"seuil {r['seuil']}, conf. {r['confirmation']}, vente {r['vente']}, vol {r['vol_cible']}"


def ligne(n, y, periodes):
    print(f"  {n:<44}", "  ".join(f"{k}: " + "Sh {sharpe:.2f} cagr {cagr:+.0%} dd {mdd:.0%}".format(**btc.stats(btc.periode(y, a, b)))
                                  for k, (a, b) in periodes.items()))


def bootstrap(series, n=2000, bloc=20, seed=0):
    """Rééchantillonnage stationnaire par blocs, appliqué aux mêmes jours pour toutes les séries (comparaisons appariées)."""
    rng = np.random.default_rng(seed)
    L = len(series[0])
    out = []
    for _ in range(n):
        idx = []
        while len(idx) < L:
            s = rng.integers(0, L); k = rng.geometric(1 / bloc)
            idx.extend(range(s, min(s + k, L)))
        idx = np.array(idx[:L])
        out.append([x[idx] for x in series])
    return out


def sh(x):
    return x.mean() / x.std() * np.sqrt(365) if x.std() > 0 else 0


def dd(x):
    eq = np.cumprod(1 + x)
    return (eq / np.maximum.accumulate(eq) - 1).min()


def main():
    B = btc.brutes()
    E = btc.elements(B)
    banc = btc.Banc4h(B, E["c4"])
    idx4 = E["c4"].index
    per = {"2012-17 (neuf)": btc.NOUVEAU, "2018-26": btc.ANCIEN, "2012-26": (btc.DEBUT, btc.ANCIEN[1])}

    # ── références (B3)
    d1 = B["d1"]; c1 = d1.close
    vol4 = E["vol4"]; dose = (0.4 / vol4).clip(upper=1).fillna(0)
    sma200 = btc.caler((c1 > I.sma(c1, 200)).astype(float), idx4)
    ema = btc.caler((I.ema(c1, 50) > I.ema(c1, 200)).astype(float), idx4)
    refs = {"achat-conservation": pd.Series(1.0, index=idx4),
            "MA200 journalière, tout ou rien": sma200,
            "MA200 journalière, dosée 40 %": sma200 * dose,
            "EMA 50/200 journalières, dosée": ema * dose,
            "confluence seule (sans 4h, sans vente)": btc.position(E, 0.25, "aucune", 0.0, 0.4),
            "FINAL (confluence + 4h + vente 0,25)": btc.position(E, **btc.FINAL)}
    Y = {k: banc.journalier(p) for k, p in refs.items()}
    print("== B2 + B3 : années jamais vues et références simples ==")
    for k, y in Y.items():
        ligne(k, y, per)

    # ── grille (B1, B4)
    G = pd.DataFrame({i: banc.journalier(btc.position(E, **r)) for i, r in enumerate(btc.REGLAGES)})
    G = G[G.index >= btc.DEBUT]
    print("\n== B1 : walk-forward, réglage choisi chaque année avec le passé seul ==")
    wf = pd.Series(np.nan, index=G.index)
    for an in range(2014, 2027):
        a, b = T(f"{an}-01-01"), T(f"{an + 1}-01-01")
        passe = G[G.index < a]
        s = passe.mean() / passe.std() * np.sqrt(365)
        i = int(s.idxmax())
        wf[(G.index >= a) & (G.index < b)] = G.loc[(G.index >= a) & (G.index < b), i]
        print(f"  {an} : {nom(btc.REGLAGES[i])} (Sharpe passé {s.max():.2f})")
    wf = wf.dropna()
    per_wf = {"2014-17 (neuf)": (T("2014-01-01"), T("2018-01-01")), "2018-26": btc.ANCIEN, "2014-26": (T("2014-01-01"), btc.ANCIEN[1])}
    ligne("walk-forward (hors échantillon)", wf, per_wf)
    for k in ("achat-conservation", "MA200 journalière, dosée 40 %", "FINAL (confluence + 4h + vente 0,25)"):
        ligne(k, Y[k], per_wf)

    # ── PBO (B4)
    print("\n== B4 : probabilité de surajustement (CSCV, 135 réglages, 16 blocs) ==")
    X = G.dropna().values
    S_ = 16
    blocs = np.array_split(np.arange(len(X)), S_)
    somme = np.array([X[b].sum(0) for b in blocs]); carre = np.array([(X[b] ** 2).sum(0) for b in blocs]); nb = np.array([len(b) for b in blocs])
    logits = []
    for comb in itertools.combinations(range(S_), S_ // 2):
        m = np.zeros(S_, bool); m[list(comb)] = True
        def sharpe_sel(mask):
            n = nb[mask].sum(); mu = somme[mask].sum(0) / n; var = carre[mask].sum(0) / n - mu ** 2
            return mu / np.sqrt(var)
        si, so = sharpe_sel(m), sharpe_sel(~m)
        best = np.argmax(si)
        rang = (so < so[best]).mean() + 0.5 / len(so)
        logits.append(np.log(rang / (1 - rang)))
    logits = np.array(logits)
    print(f"  PBO = {(logits <= 0).mean():.1%} (probabilité que le meilleur réglage d'une moitié de l'histoire soit "
          f"sous la médiane dans l'autre moitié ; < 10 % = peu de surajustement)")
    print(f"  rang médian hors échantillon du meilleur réglage : {np.median(1 / (1 + np.exp(-logits))):.0%} des réglages battus")
    s_all = G.mean() / G.std() * np.sqrt(365)
    print(f"  Sharpe 2012-2026 de la grille : min {s_all.min():.2f}, médiane {s_all.median():.2f}, max {s_all.max():.2f} ;"
          f" FINAL {s_all[btc.REGLAGES.index(btc.FINAL)]:.2f} (rang {int((s_all < s_all[btc.REGLAGES.index(btc.FINAL)]).sum()) + 1}/135)")
    print("  Plateau (Sharpe 2012-2026, confirmation ema50/200, vol 0,4) — lignes : seuil ; colonnes : taille de la vente")
    tab = pd.DataFrame({k: [s_all[btc.REGLAGES.index(dict(seuil=s, confirmation="ema50/200", vente=k, vol_cible=0.4))]
                            for s in (0.0, 0.15, 0.25, 0.35, 0.5)] for k in (0.0, 0.25, 0.5)}, index=[0.0, 0.15, 0.25, 0.35, 0.5])
    print(tab.round(2).to_string())
    print("  Par confirmation (médiane des Sharpe 2012-2026) :",
          {cf: round(float(np.median([s_all[i] for i, r in enumerate(btc.REGLAGES) if r["confirmation"] == cf])), 2)
           for cf in ("aucune", "ema50/200", "ema20/50")})
    print("  Par taille de vente (médiane) :",
          {k: round(float(np.median([s_all[i] for i, r in enumerate(btc.REGLAGES) if r["vente"] == k])), 2) for k in (0.0, 0.25, 0.5)})

    # ── bootstrap (B5)
    print("\n== B5 : bootstrap par blocs de 20 jours (2 000 tirages, 2012-07 -> 2026-11) ==")
    noms = ["FINAL (confluence + 4h + vente 0,25)", "achat-conservation", "MA200 journalière, dosée 40 %"]
    base = pd.concat({k: Y[k] for k in noms}, axis=1)
    base = base[base.index >= btc.DEBUT].dropna()
    tir = bootstrap([base[k].values for k in noms])
    shs = np.array([[sh(x) for x in t] for t in tir]); dds = np.array([[dd(x) for x in t] for t in tir])
    for j, k in enumerate(noms):
        print(f"  {k:<40} Sharpe {np.percentile(shs[:, j], 5):.2f} à {np.percentile(shs[:, j], 95):.2f} (90 %) ; "
              f"pire baisse {np.percentile(dds[:, j], 5):.0%} à {np.percentile(dds[:, j], 95):.0%}")
    print(f"  P(FINAL a un meilleur Sharpe que l'achat-conservation) = {(shs[:, 0] > shs[:, 1]).mean():.0%}")
    print(f"  P(FINAL a un meilleur Sharpe que la MA200 dosée)        = {(shs[:, 0] > shs[:, 2]).mean():.0%}")
    print(f"  P(FINAL a une pire baisse plus faible que l'achat-conservation) = {(dds[:, 0] > dds[:, 1]).mean():.0%}")

    # ── date de départ (B6)
    print("\n== B6 : départ chaque trimestre de 2013 à 2024, jusqu'au 2026-11 ==")
    rows = []
    for dep in pd.date_range("2013-01-01", "2024-10-01", freq="QS", tz="UTC"):
        f = btc.stats(Y["FINAL (confluence + 4h + vente 0,25)"][lambda x: x.index >= dep])
        h = btc.stats(Y["achat-conservation"][lambda x: x.index >= dep])
        m = btc.stats(Y["MA200 journalière, dosée 40 %"][lambda x: x.index >= dep])
        rows.append(dict(depart=dep.strftime("%Y-%m"), sh_final=f["sharpe"], sh_bh=h["sharpe"], sh_ma200=m["sharpe"],
                         cagr_final=f["cagr"], cagr_bh=h["cagr"], dd_final=f["mdd"], dd_bh=h["mdd"]))
    t = pd.DataFrame(rows)
    print(f"  FINAL meilleur Sharpe que l'achat-conservation : {(t.sh_final > t.sh_bh).mean():.0%} des départs ; que la MA200 : "
          f"{(t.sh_final > t.sh_ma200).mean():.0%} ; meilleur rendement que l'achat-conservation : {(t.cagr_final > t.cagr_bh).mean():.0%} ;"
          f" pire baisse plus faible : {(t.dd_final > t.dd_bh).mean():.0%}")
    print(t.iloc[::4].round(2).to_string(index=False))

    # ── frais (B7)
    print("\n== B7 : frais × 0,5 / 1 / 2 / 3 (FINAL, 2012-2026 et 2018-2026) ==")
    for k in (0.5, 1, 2, 3):
        y = btc.Banc4h(B, E["c4"], frais=k).journalier(refs["FINAL (confluence + 4h + vente 0,25)"])
        ligne(f"frais × {k}", y, {"2012-26": per["2012-26"], "2018-26": btc.ANCIEN})

    # ── audit anti-futur (B8)
    print("\n== B8 : audit anti-futur (40 instants au hasard) ==")
    rng = np.random.default_rng(1)
    pos_full = refs["FINAL (confluence + 4h + vente 0,25)"]
    candidats = idx4[(idx4 >= T("2013-06-01")) & (idx4 < T("2026-11-01"))]
    ecarts = []
    for t0 in rng.choice(candidats, 40, replace=False):
        t0 = pd.Timestamp(t0)
        fin = t0 + pd.Timedelta("4h")                 # la bougie t0 vient de clôturer
        Et = btc.elements(btc.tronquer(B, fin))
        pt = btc.position(Et, **btc.FINAL)
        ecarts.append(abs(pt.iloc[-1] - pos_full.loc[t0]) if pt.index[-1] == t0 else np.nan)
    ecarts = np.array(ecarts)
    print(f"  {np.isfinite(ecarts).sum()} instants comparés ; écart maximal de position = {np.nanmax(ecarts):.2e} "
          f"({'AUCUN regard vers le futur' if np.nanmax(ecarts) < 1e-9 else 'ÉCART : à corriger'})")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "btc-biais.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
