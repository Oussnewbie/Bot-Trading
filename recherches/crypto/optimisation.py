"""Étape 12 : optimisations « d'ensemble » du système retenu (multi-unités, vente à 0,25).

O1 Capital qui dort : le système est investi en moyenne 25-35 % du temps. La part non utilisée (1 - |position|) va
   dans le cash-and-carry (comptant acheté + perpétuel vendu : on encaisse le financement). Hypothèse prudente :
   seule la MOITIÉ de cette part est placée (l'autre moitié sert de marge au perpétuel), coûts d'entrée et de sortie
   de 0,19 % à chaque changement de taille.
O2 Liquidité macro (FRED, gratuit) comme filtre des ACHATS, avec des délais de publication prudents :
   M2 américain (variation 13 semaines > 0 ; connu 17 jours après), bilan de la Fed (variation 13 semaines > 0 ;
   +2 jours), dollar large (sous sa MA50 ; +1 jour), Nasdaq (au-dessus de sa MA200 ; +1 jour), taux à 10 ans (sous sa
   MA50 ; +1 jour). Et chacun seul, comme stratégie d'achat.
Sortie : sorties/optimisation.txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import partage  # noqa: F401,E402  (donnees, indicateurs, btc : dans bitcoin/, partagés avec le bot)
import donnees as DN
import indicateurs as I
import moteur as M
import signaux as S
from confluence import votes_a_priori, dosage_vol
from dosage_vente import preparer, vente, stats_j
from multi_tf import caler
from recherche import PERIODES, OUT

MACRO = os.path.join(DN.D, "macro")


def carry_4h(actif, idx):
    sym = actif + "USDT"
    s = DN.bougies(sym, "spot", "1h").close
    p = DN.bougies(sym, "perp", "1h").close
    i = s.index.intersection(p.index)
    f = DN.financement(sym).reindex(i).fillna(0)
    brut = (s[i].pct_change().fillna(0) - p[i].pct_change().fillna(0) + f)
    g = np.searchsorted(idx.values, brut.index.values, side="right") - 1
    out = brut.groupby(g).apply(lambda x: (1 + x).prod() - 1)
    r = pd.Series(0.0, index=idx)
    ok = out.index[out.index >= 0]
    r.iloc[ok] = out.loc[ok].values
    return r


def macro(nom, decalage_j):
    d = pd.read_csv(os.path.join(MACRO, f"{nom}.csv"))
    d.columns = ["date", "v"]
    s = pd.Series(pd.to_numeric(d.v, errors="coerce").values, index=pd.to_datetime(d.date).dt.tz_localize("UTC")).dropna()
    s.index = s.index + pd.Timedelta(days=decalage_j)
    return s


def aligner(s, idx):
    pos = np.searchsorted(s.index.values, (idx + pd.Timedelta("1D")).values, side="right") - 1
    return pd.Series(np.where(pos >= 0, s.values[np.maximum(pos, 0)], np.nan), index=idx)


def main():
    pd.set_option("display.width", 250)
    print("== O1 : le capital qui dort placé en cash-and-carry ==")
    nets = {}
    for actif in ("BTC", "ETH"):
        p = preparer(actif)
        achat = S.etat(p["score"] >= 0.25) * p["t_h"].astype(float) * p["dose"][0.4]
        pos = (achat + vente(p, taille=0.25)).fillna(0)
        net, _ = M.rendements(pos, p["c"], "perp", p["fb"])
        cr = carry_4h(actif, p["c"].index)
        w = 0.5 * (1 - pos.abs())
        w = w.where(p["c"].index >= pd.Timestamp("2020-01-02", tz="UTC"), 0)       # pas de perpétuel avant 2020
        net_c = net + w.shift(1).fillna(0) * cr - w.diff().abs().fillna(0) * 0.0019
        bh = M.journalier(p["c"].pct_change().fillna(0))
        for nom, n in (("système seul", net), ("système + carry sur le capital libre", net_c)):
            nj = M.journalier(n)
            nets[(nom, actif)] = nj
            print(f"  {actif} {nom:<38}", "  ".join(
                f"{k}: Sh {x['sharpe']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%}"
                for k, x in ((k, stats_j(nj, bh, *v)) for k, v in PERIODES.items())))
        print(f"  {actif} part moyenne placée en carry : {w[w.index >= '2020-01-02'].mean():.0%} du capital")
    for nom in ("système seul", "système + carry sur le capital libre"):
        nj = (nets[(nom, "BTC")] + nets[(nom, "ETH")].reindex(nets[(nom, "BTC")].index).fillna(0)) / 2
        bh = nets[(nom, "BTC")] * 0
        print(f"  50/50 {nom:<36}", "  ".join(
            f"{k}: Sh {nj[(nj.index >= a) & (nj.index < b)].mean() / nj[(nj.index >= a) & (nj.index < b)].std() * np.sqrt(365):.2f} "
            f"cagr {(1 + nj[(nj.index >= a) & (nj.index < b)]).prod() ** (365 / ((nj.index >= a) & (nj.index < b)).sum()) - 1:.0%} "
            f"dd {((1 + nj[(nj.index >= a) & (nj.index < b)]).cumprod() / (1 + nj[(nj.index >= a) & (nj.index < b)]).cumprod().cummax() - 1).min():.0%}"
            for k, (a, b) in PERIODES.items()))

    print("\n== O2 : liquidité macro (filtre des achats de la confluence journalière, spot) ==")
    for actif in ("BTC", "ETH"):
        ctx = S.contexte(actif, "1d")
        idx = ctx["d"].index
        banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
        base = S.etat(votes_a_priori(ctx).mean(axis=1) >= 0.25) * dosage_vol(ctx, 0.4)
        m2 = aligner(macro("WM2NS", 17), idx); fed = aligner(macro("WALCL", 2), idx)
        dxy = macro("DTWEXBGS", 1); ndq = macro("NASDAQCOM", 1); t10 = macro("DGS10", 1)
        filtres = {
            "M2 en hausse (13 sem.)": m2 > aligner(macro("WM2NS", 17).shift(13), idx),
            "bilan Fed en hausse (13 sem.)": fed > aligner(macro("WALCL", 2).shift(13), idx),
            "dollar sous sa MA50": aligner(dxy, idx) < aligner(dxy.rolling(50).mean(), idx),
            "Nasdaq au-dessus de sa MA200": aligner(ndq, idx) > aligner(ndq.rolling(200).mean(), idx),
            "taux 10 ans sous sa MA50": aligner(t10, idx) < aligner(t10.rolling(50).mean(), idx),
        }
        def ligne(nom, p):
            r = banc.evaluer(p.fillna(0).values, "spot")
            print(f"  {actif} {nom:<46}", "  ".join(f"{k}: Sh {x['sharpe']:.2f} t {x['t_alpha']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%}"
                                                    for k, x in r.items() if x))
        ligne("confluence seule (référence)", base)
        for nom, f in filtres.items():
            ligne(f"confluence + {nom}", base.where(f.fillna(True), 0))
        for nom, f in filtres.items():
            ligne(f"seul : achat si {nom}", S.etat(f.fillna(False)) * dosage_vol(ctx, 0.4))


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "optimisation.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
