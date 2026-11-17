"""Étape 7 : stratégies d'institution, neutres au marché ou presque.

I1 Cash-and-carry (base) : acheter le comptant et vendre le perpétuel pour la même quantité. On ne parie plus sur le
   prix : on encaisse le financement payé par les acheteurs à levier (et la variation de l'écart perp - comptant).
   Coûts : 0,10 % + 0,05 % + 2 × 0,02 % à l'entrée et autant à la sortie. Variantes : toujours, ou seulement quand le
   financement moyen des 7 derniers jours dépasse 0, 5 ou 10 % par an.
I2 Paire ETH/BTC (arbitrage statistique) : retour à la moyenne du ratio ETH/BTC (z-score 30/60/90 jours, entrée à
   ±1,5 ou ±2, sortie à 0), contre la tendance du ratio (au-dessus / en dessous de sa MA50). Coût : deux jambes de
   perpétuel, 0,14 % par côté.
I3 Prime de volatilité (options) : la volatilité implicite DVOL de Deribit comparée à la volatilité réalisée ENSUITE
   sur 30 jours. Une prime positive en moyenne = vendre des options (straddles couverts, covered calls) rapporte en
   moyenne, avec de grosses pertes lors des krachs. Mesure descriptive : pas de prix d'options historiques ici.
Sortie : sorties/institutionnel.txt
"""
import io
import os
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I
import moteur as M
import signaux as S
from recherche import PERIODES, OUT


def resume(r, nom, an=365 * 24):
    for per, (a, b) in PERIODES.items():
        x = r[(r.index >= a) & (r.index < b)]
        if len(x) < 100:
            continue
        j = M.journalier(x)
        eq = (1 + j).cumprod()
        print(f"  {nom:<46} {per}: rendement/an {eq.iloc[-1] ** (365 / len(j)) - 1:+.1%}  Sharpe {j.mean() / j.std() * np.sqrt(365):.2f}"
              f"  pire baisse {(eq / eq.cummax() - 1).min():.1%}  temps investi {(x != 0).mean():.0%}")


def carry(actif):
    sym = actif + "USDT"
    s = DN.bougies(sym, "spot", "1h").close
    p = DN.bougies(sym, "perp", "1h").close
    idx = s.index.intersection(p.index)
    s, p = s[idx], p[idx]
    f = DN.financement(sym).reindex(idx).fillna(0)
    brut = s.pct_change().fillna(0) - p.pct_change().fillna(0) + f        # long comptant, court perp, financement reçu
    f7 = DN.financement(sym).rolling(21, min_periods=1).mean().reindex(idx).ffill() * 3 * 365     # % par an
    cout = 0.0010 + 0.0005 + 2 * 0.0002
    print(f"{actif} — financement moyen {f.sum() / (len(f) / 8760):.1%} par an (2020-2026)")
    for seuil in (None, 0.0, 0.05, 0.10):
        actif_ = pd.Series(1.0, index=idx) if seuil is None else (f7 > seuil).astype(float).shift(1).fillna(0)
        net = actif_ * brut - actif_.diff().abs().fillna(actif_.iloc[0]) * cout
        resume(net, "cash-and-carry " + ("toujours" if seuil is None else f"si financement 7 j > {seuil:.0%}/an"))


def paire():
    ctx = S.contexte("ETH", "1d")
    eb = ctx["ethbtc"]
    M.MODES["paire"] = dict(cout=0.0014, financement=False, short=True)
    banc = M.Banc(eb, pd.Series(0.0, index=eb.index), PERIODES)
    print("ETH/BTC — achat-conservation du ratio :", {k: round(v["sharpe"], 2) for k, v in banc.achat_conservation().items()})
    for n in (30, 60, 90):
        z = I.zscore(np.log(eb), n)
        for k in (1.5, 2.0):
            p = S.tenir(z < -k, z > 0, z > k, z < 0)
            r = banc.evaluer(p.values, "paire")
            print(f"  retour à la moyenne z{n} ±{k}:", "  ".join(f"{a}: Sh {x['sharpe']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%} n {x['trades']}"
                                                         for a, x in r.items() if x))
    for n in (20, 50, 100):
        p = S.etat(eb > I.sma(eb, n), eb < I.sma(eb, n))
        r = banc.evaluer(p.values, "paire")
        print(f"  tendance du ratio MA{n}:      ", "  ".join(f"{a}: Sh {x['sharpe']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%} n {x['trades']}"
                                                   for a, x in r.items() if x))


def prime_vol(actif):
    v = pd.read_csv(f"{DN.X}/dvol-{actif}.csv")
    dv = pd.Series(v.close.values / 100, index=pd.to_datetime(v.t, unit="ms", utc=True))
    h = DN.bougies(actif + "USDT", "spot", "1h").close
    r = np.log(h).diff()
    rv_futur = r.rolling(24 * 30).std().shift(-24 * 30) * np.sqrt(24 * 365)
    x = pd.DataFrame({"iv": dv, "rv": rv_futur.reindex(dv.index)}).dropna()
    x["prime"] = x.iv - x.rv
    print(f"{actif} — DVOL moyen {x.iv.mean():.0%}, volatilité réalisée ensuite {x.rv.mean():.0%} : prime moyenne "
          f"{x.prime.mean():+.1%} ; positive {(x.prime > 0).mean():.0%} du temps ; pire {x.prime.min():+.0%} ({x.prime.idxmin():%Y-%m})")


def main():
    print("== I1 cash-and-carry ==")
    for a in ("BTC", "ETH"):
        carry(a)
    print("\n== I2 paire ETH/BTC ==")
    paire()
    print("\n== I3 prime de volatilité ==")
    for a in ("BTC", "ETH"):
        prime_vol(a)


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "institutionnel.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
