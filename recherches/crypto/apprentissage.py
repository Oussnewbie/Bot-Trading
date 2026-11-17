"""Étape 5 : apprentissage automatique et régimes, en walk-forward (jamais de données futures).

A. LightGBM : prédit le signe du rendement des 5 prochains jours à partir de ~60 caractéristiques journalières
   (votes de la confluence, distances aux moyennes, RSI, MACD, volatilité, order flow, financement, prime perp et
   Coinbase, Fear & Greed, DVOL, stablecoins, on-chain, ETH/BTC). Réentraîné tous les 3 mois sur tout le passé
   disponible (avec 5 jours d'écart pour que l'étiquette ne touche pas la période prédite).
   Position : achat si proba > seuil haut, vente si < seuil bas, sinon rien.
B. HMM gaussien à 2 et 3 états sur (rendement, volatilité 10 j) : probabilités FILTRÉES (algorithme avant, sans
   lissage qui regarderait le futur), refit annuel. Position : achat dans l'état au meilleur rendement moyen passé,
   vente (option) dans le pire.
C. Combinaisons : la confluence d'achat + module de vente « rebonds en tendance baissière ».
Sortie : sorties/apprentissage.txt
"""
import io
import os
import warnings
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

import partage  # noqa: F401,E402  (donnees, indicateurs, btc : dans bitcoin/, partagés avec le bot)
import indicateurs as I
import moteur as M
import signaux as S
from confluence import votes_a_priori, dosage_vol
from recherche import PERIODES, OUT

warnings.filterwarnings("ignore")


def caracteristiques(ctx):
    d = ctx["d"]; c = d.close
    X = votes_a_priori(ctx).add_prefix("vote_")
    for n in (10, 20, 50, 100, 200):
        X[f"dist_sma{n}"] = c / I.sma(c, n) - 1
    for n in (1, 5, 10, 20, 60):
        X[f"ret{n}"] = c.pct_change(n)
    X["rsi14"] = I.rsi(c, 14); X["rsi2"] = I.rsi(c, 2)
    m, s, h = I.macd(c); X["macd_n"] = m / c; X["histo_n"] = h / c
    r = c.pct_change()
    X["vol10"] = r.rolling(10).std(); X["vol30"] = r.rolling(30).std(); X["vol_ratio"] = X.vol10 / X.vol30
    X["range_pos90"] = (c - d.low.rolling(90).min()) / (d.high.rolling(90).max() - d.low.rolling(90).min())
    for n in (1, 7, 30):
        X[f"of_spot{n}"] = d.delta.rolling(n).sum() / d.volume.rolling(n).sum()
        X[f"of_perp{n}"] = ctx["perp"].delta.rolling(n).sum() / ctx["perp"].volume.rolling(n).sum()
    X["vol_rel"] = d.volume / d.volume.rolling(30).mean()
    X["funding7"] = ctx["funding"].rolling(7, min_periods=1).mean()
    X["prime7"] = ctx["prime"].rolling(7, min_periods=1).mean()
    X["prime_cb7"] = ctx["prime_cb"].rolling(7, min_periods=1).mean()
    X["fng"] = ctx["fng"]; X["fng_chg7"] = ctx["fng"].diff(7)
    X["dvol"] = ctx["dvol"]; X["dvol_chg7"] = ctx["dvol"].pct_change(7)
    X["stable30"] = ctx["stable"].pct_change(30)
    X["oi_chg7"] = ctx["oi"].pct_change(7)
    oc = ctx["onchain"]
    X["mvrv"] = oc.CapMVRVCur
    X["netflow30"] = (oc.FlowInExNtv - oc.FlowOutExNtv).rolling(30).mean() / oc.SplyExNtv
    X["adr_mom"] = oc.AdrActCnt.rolling(7).mean() / oc.AdrActCnt.rolling(90).mean() - 1
    X["sply_ex90"] = oc.SplyExNtv.pct_change(90)
    eb = ctx["ethbtc"]
    X["ethbtc_dist50"] = eb / I.sma(eb, 50) - 1; X["ethbtc_ret30"] = eb.pct_change(30)
    X["jour_semaine"] = d.index.dayofweek
    return X


def lgbm_walkforward(ctx, horizon=5, debut="2020-01-01", pas_mois=3):
    import lightgbm as lgb
    X = caracteristiques(ctx)
    c = ctx["d"].close
    y = (c.shift(-horizon) / c - 1 > 0).astype(float).where(c.shift(-horizon).notna())
    proba = pd.Series(np.nan, index=X.index)
    dates = pd.date_range(debut, X.index[-1].tz_localize(None), freq=f"{pas_mois}MS", tz="UTC")
    for a, b in zip(dates, list(dates[1:]) + [X.index[-1] + pd.Timedelta("1D")]):
        train = (X.index < a - pd.Timedelta(days=horizon)) & y.notna()
        test = (X.index >= a) & (X.index < b)
        if train.sum() < 500 or test.sum() == 0:
            continue
        mdl = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=8, min_child_samples=40,
                                 subsample=0.8, subsample_freq=1, colsample_bytree=0.6, verbose=-1, random_state=0)
        mdl.fit(X[train], y[train])
        proba[test] = mdl.predict_proba(X[test])[:, 1]
    imp = pd.Series(mdl.feature_importances_, index=X.columns).sort_values(ascending=False)
    return proba, imp


def hmm_filtre(ctx, k=2, debut="2019-01-01"):
    from hmmlearn.hmm import GaussianHMM
    c = ctx["d"].close
    r = np.log(c).diff()
    obs = pd.concat([r, r.rolling(10).std()], axis=1).dropna()
    etat_bon = pd.Series(np.nan, index=c.index)
    etat_mauvais = pd.Series(np.nan, index=c.index)
    annees = range(pd.Timestamp(debut).year, c.index[-1].year + 1)
    for an in annees:
        a = pd.Timestamp(f"{an}-01-01", tz="UTC"); b = pd.Timestamp(f"{an + 1}-01-01", tz="UTC")
        tr = obs[obs.index < a]
        if len(tr) < 300:
            continue
        mdl = GaussianHMM(n_components=k, covariance_type="full", n_iter=200, random_state=0).fit(tr.values)
        moy = mdl.means_[:, 0]
        bon, mauvais = int(np.argmax(moy)), int(np.argmin(moy))
        # probabilités filtrées : passe avant sur tout jusqu'à b, on garde [a, b)
        X = obs[obs.index < b].values
        from scipy.stats import multivariate_normal
        B = np.column_stack([multivariate_normal(mdl.means_[j], mdl.covars_[j]).pdf(X) for j in range(k)])
        alpha = np.zeros((len(X), k)); p = mdl.startprob_
        for t in range(len(X)):
            p = (p @ mdl.transmat_ if t else p) * B[t]
            p = p / p.sum() if p.sum() > 0 else np.ones(k) / k
            alpha[t] = p
        idx = obs.index[obs.index < b]
        m = idx >= a
        etat_bon[idx[m]] = alpha[m, bon]
        etat_mauvais[idx[m]] = alpha[m, mauvais]
    return etat_bon, etat_mauvais


def module_vente(ctx):
    """Vendre les rebonds en tendance baissière : sous le nuage Ichimoku 9-26-52 ET score de confluence <= -0,25 ;
    vente quand le RSI 14 remonte au-dessus de 55 ou que le prix touche la SMA20 ou le 0,5 de la jambe de 60 jours ;
    rachat quand le RSI repasse sous 40, que la tendance cesse, ou au bout de 20 jours."""
    d = ctx["d"]; c = d.close
    ich = I.ichimoku(d, 9, 26, 52)
    bas = np.minimum(ich["spanA"], ich["spanB"])
    score = votes_a_priori(ctx).mean(axis=1)
    baisse = (c < bas) & (score <= -0.25)
    r = I.rsi(c, 14)
    hh, ll = d.high.rolling(60).max(), d.low.rolling(60).min()
    rebond = (r > 55) | (d.high >= I.sma(c, 20)) | (d.high >= ll + 0.5 * (hh - ll))
    entree = baisse & rebond
    sortie = (r < 40) | ~baisse
    p = S.tenir(entree, sortie)
    # au plus 20 jours
    grp = (p.diff() != 0).cumsum()
    age = p.groupby(grp).cumcount()
    return -(p.where(age < 20, 0))


def main():
    pd.set_option("display.width", 250)
    for actif in ("BTC", "ETH"):
        ctx = S.contexte(actif, "1d")
        banc = M.Banc(ctx["d"].close, ctx["funding_bougie"], PERIODES)
        print(f"\n######## {actif} ########  achat-conservation :",
              {k: round(v["sharpe"], 2) for k, v in banc.achat_conservation().items()})

        def montrer(nom, p, mode):
            r = banc.evaluer(p.fillna(0).values, mode)
            print(f"{nom:<55} {mode:<5}", "  ".join(
                f"{k}: Sh {x['sharpe']:.2f} t {x['t_alpha']:.2f} cagr {x['cagr']:.0%} dd {x['mdd']:.0%}" for k, x in r.items() if x))

        proba, imp = lgbm_walkforward(ctx)
        print("LightGBM — caractéristiques les plus utilisées :", ", ".join(imp.index[:12]))
        ok = proba.notna()
        for haut, bas in ((0.5, 0.5), (0.55, 0.45), (0.6, 0.4)):
            p = S.etat(proba > haut, proba < bas).where(ok, 0)
            montrer(f"lgbm 5j seuils {haut}/{bas}", p, "perp")
            montrer(f"lgbm 5j seuils {haut}/{bas}", p, "spot")
            montrer(f"lgbm 5j seuils {haut}/{bas} ventes seules", p, "court")
        for k in (2, 3):
            bon, mauvais = hmm_filtre(ctx, k)
            p = S.etat(bon > 0.6, mauvais > 0.6).fillna(0)
            montrer(f"HMM {k} états", p, "perp")
            montrer(f"HMM {k} états", p, "spot")
        conf = votes_a_priori(ctx).mean(axis=1)
        dose = dosage_vol(ctx, 0.4)
        longp = S.etat(conf >= 0.25) * dose
        vente = module_vente(ctx)
        montrer("confluence achat (référence)", longp, "spot")
        montrer("module vente seul", vente * dose, "court")
        montrer("confluence achat + module vente", longp + vente * dose, "perp")
        montrer("confluence achat+vente symétrique (score<=-0,25)", S.etat(conf >= 0.25, conf <= -0.25) * dose, "perp")
        if actif == "BTC":
            pr = proba.reindex(longp.index)
            filtre = longp.where((pr > 0.45) | pr.isna(), 0)
            montrer("confluence achat filtrée par lgbm>0,45", filtre, "spot")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    open(os.path.join(OUT, "apprentissage.txt"), "w").write(buf.getvalue())
    print(buf.getvalue())
