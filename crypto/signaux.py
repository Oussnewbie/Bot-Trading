"""Toutes les variantes de signaux : chaque fonction renvoie une position voulue à la clôture de chaque bougie
(+1 achat, -1 vente, 0 rien). En mode « spot » les ventes deviennent 0 (on ne peut qu'acheter ou rester dehors).

Familles : tendance (MA, MA200, Donchian, Supertrend), Ichimoku, MACD, RSI, VWAP, Fibonacci, Bollinger,
order flow (volume acheteur/vendeur agressif de Binance, spot et perpétuel), financement, open interest,
on-chain (Coin Metrics), paire ETH/BTC. Puis des filtres qui croisent ces familles.
"""
import numpy as np
import pandas as pd

import donnees as DN
import indicateurs as I

TF_H = {"1h": 1, "4h": 4, "1d": 24}


def tenir(entree_l, sortie_l, entree_s=None, sortie_s=None):
    """Position avec mémoire : +1 de l'entrée achat jusqu'à la sortie achat, -1 de même pour la vente."""
    l = pd.Series(np.nan, index=entree_l.index)
    l[sortie_l.fillna(False)] = 0
    l[entree_l.fillna(False)] = 1
    l = l.ffill().fillna(0)
    if entree_s is None:
        return l
    s = pd.Series(np.nan, index=entree_s.index)
    s[sortie_s.fillna(False)] = 0
    s[entree_s.fillna(False)] = -1
    s = s.ffill().fillna(0)
    return (l + s).clip(-1, 1)


def etat(cond_l, cond_s=None):
    p = cond_l.fillna(False).astype(float)
    if cond_s is not None:
        p = p - cond_s.fillna(False).astype(float)
    return p


def contexte(actif, tf):
    """Toutes les séries alignées sur les bougies `tf` de l'actif (« BTC » ou « ETH »)."""
    sym = actif + "USDT"
    d = DN.bougies(sym, "spot", tf)
    idx = d.index
    fin = idx + pd.Timedelta(hours=TF_H[tf])             # heure de clôture de chaque bougie
    ctx = dict(d=d, tf=tf, actif=actif, n_an=365 * 24 / TF_H[tf])
    p = DN.bougies(sym, "perp", tf).reindex(idx)
    ctx["perp"] = p
    eb = DN.bougies("ETHBTC", "spot", tf).reindex(idx)
    ctx["ethbtc"] = eb.close.ffill()
    f = DN.financement(sym)
    from moteur import financement_par_bougie
    ctx["funding_bougie"] = financement_par_bougie(f, idx)
    fr = f.reindex(f.index.union(idx)).ffill().reindex(idx)      # dernier taux connu
    fr[idx < f.index.min()] = np.nan
    ctx["funding"] = fr
    m = DN.metriques(sym)
    ctx["oi"] = m.sum_open_interest_value.reindex(idx.union(m.index)).ffill().reindex(idx).where(idx >= m.index.min())
    ctx["ls_taker"] = m.sum_taker_long_short_vol_ratio.reindex(idx.union(m.index)).ffill().reindex(idx).where(idx >= m.index.min())
    oc = DN.onchain(actif.lower()).copy()
    oc.index = oc.index + pd.Timedelta(days=2)            # valeur du jour D utilisée à partir de D+2 00:00 UTC
    pos = np.searchsorted(oc.index.values, fin.values, side="right") - 1
    oca = oc.iloc[np.maximum(pos, 0)].copy()
    oca.index = idx
    oca[pos < 0] = np.nan
    ctx["onchain"] = oca
    return ctx


def barres(ctx, jours):
    """Nombre de bougies dans `jours` jours."""
    return max(2, int(round(jours * 24 / TF_H[ctx["tf"]])))


# ─────────────────────────────── familles ───────────────────────────────
def f_tendance(ctx):
    d = ctx["d"]; c = d.close; out = {}
    for kind in ("sma", "ema"):
        for n in (20, 50, 100, 150, 200):
            m = I.ma(c, n, kind)
            out[f"tendance/prix>{kind}{n}"] = etat(c > m, c < m)
        for a, b in ((10, 50), (20, 50), (20, 100), (50, 200), (10, 30)):
            fa, fb = I.ma(c, a, kind), I.ma(c, b, kind)
            out[f"tendance/croise-{kind}{a}-{b}"] = etat(fa > fb, fa < fb)
    m200 = I.sma(c, 200)
    for k in (10, 20, 50):
        pente = m200 - m200.shift(k)
        out[f"tendance/ma200+pente{k}"] = etat((c > m200) & (pente > 0), (c < m200) & (pente < 0))
    for n in (20, 55, 100):
        hh, ll = d.high.rolling(n).max().shift(), d.low.rolling(n).min().shift()
        hx, lx = d.high.rolling(n // 2).max().shift(), d.low.rolling(n // 2).min().shift()
        out[f"tendance/donchian{n}"] = tenir(c > hh, c < lx, c < ll, c > hx)
    for n, mult in ((10, 3), (10, 2), (20, 3), (14, 4)):
        st = I.supertrend(d, n, mult)
        out[f"tendance/supertrend{n}x{mult}"] = etat(st > 0, st < 0)
    for jours in (30, 90, 180):          # momentum « séries temporelles »
        k = barres(ctx, jours)
        out[f"tendance/momentum{jours}j"] = etat(c > c.shift(k), c < c.shift(k))
    return out


def f_ichimoku(ctx):
    d = ctx["d"]; c = d.close; out = {}
    for p in ((9, 26, 52), (20, 60, 120), (10, 30, 60)):
        ich = I.ichimoku(d, *p)
        haut = np.maximum(ich["spanA"], ich["spanB"]); bas = np.minimum(ich["spanA"], ich["spanB"])
        nom = "-".join(map(str, p))
        out[f"ichimoku/nuage{nom}"] = etat(c > haut, c < bas)
        out[f"ichimoku/tk{nom}"] = etat(ich["tenkan"] > ich["kijun"], ich["tenkan"] < ich["kijun"])
        out[f"ichimoku/kijun{nom}"] = etat(c > ich["kijun"], c < ich["kijun"])
        fort_l = (c > haut) & (ich["tenkan"] > ich["kijun"]) & (ich["chikou_ok"] > 0) & (ich["futurA"] > ich["futurB"])
        fort_s = (c < bas) & (ich["tenkan"] < ich["kijun"]) & (ich["chikou_ok"] < 0) & (ich["futurA"] < ich["futurB"])
        out[f"ichimoku/complet{nom}"] = etat(fort_l, fort_s)
        # entrée sur signal complet, sortie quand la clôture repasse sous la kijun (gestion classique)
        out[f"ichimoku/complet-sortie-kijun{nom}"] = tenir(fort_l, c < ich["kijun"], fort_s, c > ich["kijun"])
        out[f"ichimoku/complet-sortie-nuage{nom}"] = tenir(fort_l, c < bas, fort_s, c > haut)
    return out


def f_macd(ctx):
    c = ctx["d"].close; out = {}
    for p in ((12, 26, 9), (8, 21, 5), (24, 52, 18), (5, 35, 5), (19, 39, 9)):
        m, s, h = I.macd(c, *p)
        nom = "-".join(map(str, p))
        out[f"macd/signal{nom}"] = etat(m > s, m < s)
        out[f"macd/zero{nom}"] = etat(m > 0, m < 0)
        out[f"macd/signal+zero{nom}"] = etat((m > s) & (m > 0), (m < s) & (m < 0))
        out[f"macd/histo-monte{nom}"] = etat(h > h.shift(), h < h.shift())
    return out


def f_rsi(ctx):
    d = ctx["d"]; c = d.close; out = {}
    m200 = I.sma(c, 200)
    for n in (7, 14, 21, 28):
        r = I.rsi(c, n)
        out[f"rsi/{n}>50"] = etat(r > 50, r < 50)
        out[f"rsi/{n}-hysteresis55-45"] = tenir(r > 55, r < 45, r < 45, r > 55)
        for bas, haut in ((30, 70), (25, 75), (20, 80)):
            out[f"rsi/{n}-retour{bas}-{haut}"] = tenir(r < bas, r > 50, r > haut, r < 50)
        for x, y in ((35, 60), (40, 65), (45, 70), (30, 55)):
            out[f"rsi/{n}-repli{x}-{y}-dans-tendance"] = tenir((r < x) & (c > m200), (r > y) | (c < m200),
                                                             (r > 100 - x) & (c < m200), (r < 100 - y) | (c > m200))
    r2 = I.rsi(c, 2); m5 = I.sma(c, 5)
    for seuil in (5, 10, 20):
        out[f"rsi/connors2<{seuil}"] = tenir((r2 < seuil) & (c > m200), (c > m5) | (c < m200),
                                             (r2 > 100 - seuil) & (c < m200), (c < m5) | (c > m200))
    return out


def f_vwap(ctx):
    d = ctx["d"]; c = d.close; out = {}
    for per, nom in (("W", "semaine"), ("M", "mois"), ("Q", "trimestre"), ("Y", "annee")):
        v = I.vwap_ancre(d, per)
        out[f"vwap/ancre-{nom}"] = etat(c > v, c < v)
    for jours in (3, 7, 30, 90):
        v = I.vwap_glissant(d, barres(ctx, jours))
        out[f"vwap/glissant{jours}j"] = etat(c > v, c < v)
    for jours in (30, 90, 180):
        n = barres(ctx, jours)
        v = I.vwap_depuis_plus_bas(d, n)
        out[f"vwap/ancre-plus-bas{jours}j"] = etat(c > v)
    m200 = I.sma(c, 200)
    for jours in (7, 30):
        n = barres(ctx, jours)
        v = I.vwap_glissant(d, n)
        z = (c - v) / c.rolling(n).std()
        for k in (1.5, 2.0):
            out[f"vwap/bande{jours}j-{k}-retour"] = tenir((z < -k) & (c > m200), (z > 0) | (c < m200 * 0.97),
                                                         (z > k) & (c < m200), (z < 0) | (c > m200 * 1.03))
    return out


def jambes(d, n):
    h, l = pd.Series(d.high.values), pd.Series(d.low.values)
    # position du max/min dans la fenêtre glissante, sans rolling.apply (lent) : via l'âge du dernier extrême
    hh, ll = h.rolling(n).max().values, l.rolling(n).min().values
    idx = np.arange(len(h))
    der_h = pd.Series(np.where(h.values >= hh, idx, np.nan)).ffill().values   # dernière bougie qui fait le max courant
    der_l = pd.Series(np.where(l.values <= ll, idx, np.nan)).ffill().values
    return der_h, der_l, hh, ll


def fibo(d, n, niveau, stop, cible, tendance, pre=None):
    """Retracement de Fibonacci sur la dernière jambe des n bougies (plus bas -> plus haut si le plus haut est le plus
    récent : jambe haussière). Achat à la clôture quand le prix revient au niveau (0,382 / 0,5 / 0,618) et clôture
    au-dessus ; stop à la clôture sous le niveau `stop` (0,786 ou 1 = plus bas de la jambe) ; sortie à l'extension
    `cible` (1 = ancien plus haut, 1,272, 1,618). Symétrique à la vente. Jambe figée à l'entrée."""
    h, l, c = d.high.values, d.low.values, d.close.values
    ih, il, hh, ll = pre if pre is not None else jambes(d, n)
    tend = tendance.values
    pos = np.zeros(len(c)); cur = 0; st = tg = 0.0
    for i in range(n, len(c)):
        if cur == 1:
            if c[i] < st or c[i] >= tg:
                cur = 0
        elif cur == -1:
            if c[i] > st or c[i] <= tg:
                cur = 0
        if cur == 0 and not np.isnan(ih[i - 1]):
            H, L = hh[i - 1], ll[i - 1]; R = H - L
            if R > 0:
                up = ih[i - 1] > il[i - 1]                  # le plus haut est venu après le plus bas
                if up and tend[i] >= 0:
                    lv = H - niveau * R
                    if l[i] <= lv and c[i] > lv and c[i] > H - stop * R:
                        cur, st, tg = 1, H - stop * R - 1e-9, L + cible * R
                elif not up and tend[i] <= 0:
                    lv = L + niveau * R
                    if h[i] >= lv and c[i] < lv and c[i] < L + stop * R:
                        cur, st, tg = -1, L + stop * R + 1e-9, H - cible * R
        pos[i] = cur
    return pd.Series(pos, index=d.index)


def f_fibonacci(ctx):
    d = ctx["d"]; c = d.close; out = {}
    m200 = I.sma(c, 200)
    filtres = {"": pd.Series(0, index=d.index), "+ma200": np.sign(c - m200).fillna(0)}
    for jours in (10, 30, 60):
        n = barres(ctx, jours)
        pre = jambes(d, n)
        for niv in (0.382, 0.5, 0.618):
            for stop in (0.786, 1.0):
                for cible in (1.0, 1.272, 1.618):
                    for fn, tend in filtres.items():
                        out[f"fibonacci/{jours}j-{niv}-stop{stop}-cible{cible}{fn}"] = fibo(d, n, niv, stop, cible, tend, pre)
    return out


def f_bollinger(ctx):
    c = ctx["d"].close; out = {}
    m200 = I.sma(c, 200)
    for n in (20, 50):
        for k in (2.0, 2.5):
            m, hb, bb = I.bollinger(c, n, k)
            out[f"bollinger/{n}-{k}-cassure"] = tenir(c > hb, c < m, c < bb, c > m)
            out[f"bollinger/{n}-{k}-retour"] = tenir((c < bb) & (c > m200), c > m, (c > hb) & (c < m200), c < m)
    return out


def f_orderflow(ctx):
    """Volume acheteur agressif (taker buy) de Binance : delta = achats agressifs - ventes agressives.
    CVD = somme du delta. Spot depuis 2017, perpétuel depuis 2020."""
    d = ctx["d"]; c = d.close; out = {}
    m200 = I.sma(c, 200)
    for src, x in (("spot", d), ("perp", ctx["perp"])):
        delta, vol = x.delta, x.volume
        dispo = vol.notna()
        for jours in (1, 3, 7, 30):
            n = barres(ctx, jours)
            ratio = delta.rolling(n).sum() / vol.rolling(n).sum()          # -1 à +1
            out[f"orderflow/{src}-ratio{jours}j"] = etat(ratio > 0, ratio < 0).where(dispo, 0)
            mu = ratio.rolling(barres(ctx, 180), min_periods=n).mean()
            out[f"orderflow/{src}-ratio{jours}j-vs-moyenne"] = etat(ratio > mu, ratio < mu).where(dispo, 0)
            z = I.zscore(ratio, barres(ctx, 90))
            out[f"orderflow/{src}-capitulation{jours}j-z2"] = tenir(z < -2, z > 0, z > 2, z < 0).where(dispo, 0)
            out[f"orderflow/{src}-capitulation{jours}j-z2+ma200"] = tenir((z < -2) & (c > m200), (z > 0) | (c < m200),
                                                                         (z > 2) & (c < m200), (z < 0) | (c > m200)).where(dispo, 0)
            # divergence : prix en hausse sur n bougies mais CVD en baisse (ventes agressives) -> vente, et inversement
            cvd = delta.cumsum()
            dp, dc = c - c.shift(n), cvd - cvd.shift(n)
            out[f"orderflow/{src}-divergence{jours}j"] = etat((dp < 0) & (dc > 0), (dp > 0) & (dc < 0)).where(dispo, 0)
            out[f"orderflow/{src}-confirmation{jours}j"] = etat((dp > 0) & (dc > 0), (dp < 0) & (dc < 0)).where(dispo, 0)
        # cassure avec volume : clôture au plus haut de 20 bougies, volume > 2x la moyenne, delta positif
        hh, ll = d.high.rolling(20).max().shift(), d.low.rolling(20).min().shift()
        vm = vol.rolling(50).mean()
        out[f"orderflow/{src}-cassure-volume"] = tenir((c > hh) & (vol > 2 * vm) & (delta > 0), c < I.sma(c, 20),
                                                       (c < ll) & (vol > 2 * vm) & (delta < 0), c > I.sma(c, 20)).where(dispo, 0)
    # spot qui mène : les achats agressifs du spot dépassent ceux du perpétuel (achat « réel » plutôt que levier)
    for jours in (3, 7, 30):
        n = barres(ctx, jours)
        rs = d.delta.rolling(n).sum() / d.volume.rolling(n).sum()
        rp = ctx["perp"].delta.rolling(n).sum() / ctx["perp"].volume.rolling(n).sum()
        out[f"orderflow/spot-mene{jours}j"] = etat(rs > rp, rs < rp).where(rp.notna(), 0)
    return out


def f_derives(ctx):
    """Financement et open interest des perpétuels Binance."""
    c = ctx["d"].close; out = {}
    fr = ctx["funding"]
    for jours in (3, 7, 30):
        n = barres(ctx, jours)
        fm = fr.rolling(n, min_periods=1).mean()
        rg = I.rang_glissant(fm, barres(ctx, 365))
        dispo = fr.notna()
        out[f"derives/funding{jours}j-contrarien"] = etat(rg < 0.2, rg > 0.8).where(dispo, 0)
        out[f"derives/funding{jours}j-suiveur"] = etat(rg > 0.8, rg < 0.2).where(dispo, 0)
        out[f"derives/funding{jours}j-negatif-achat"] = tenir(fm < 0, fm > 0.0001).where(dispo, 0)
    oi = ctx["oi"]; dispo = oi.notna()
    for jours in (1, 3, 7, 30):
        n = barres(ctx, jours)
        doi, dp = oi / oi.shift(n) - 1, c / c.shift(n) - 1
        out[f"derives/oi{jours}j-confirme"] = etat((doi > 0) & (dp > 0), (doi > 0) & (dp < 0)).where(dispo, 0)
        out[f"derives/oi{jours}j-purge"] = etat((doi < 0) & (dp < 0), (doi < 0) & (dp > 0)).where(dispo, 0)
        z = I.zscore(doi, barres(ctx, 90))
        out[f"derives/oi{jours}j-excès-contrarien"] = tenir((z > 2) & (dp < 0), z < 0, (z > 2) & (dp > 0), z < 0).where(dispo, 0)
    ls = ctx["ls_taker"]
    for jours in (1, 7):
        n = barres(ctx, jours)
        lm = ls.rolling(n).mean()
        out[f"derives/taker-ls{jours}j"] = etat(lm > 1, lm < 1).where(ls.notna(), 0)
    return out


def f_onchain(ctx):
    oc = ctx["onchain"]; c = ctx["d"].close; out = {}
    an = barres(ctx, 365)
    net = oc.FlowInExNtv - oc.FlowOutExNtv              # > 0 : des bitcoins entrent sur les exchanges (pour être vendus)
    for jours in (7, 30):
        s = net.rolling(barres(ctx, jours)).mean()
        out[f"onchain/fluxnet{jours}j-sortie=achat"] = etat(s < 0, s > 0)
        z = I.zscore(s, an)
        out[f"onchain/fluxnet{jours}j-z1"] = etat(z < -1, z > 1)
    sx = oc.SplyExNtv
    for jours in (30, 90):
        k = barres(ctx, jours)
        out[f"onchain/reserve-exchanges{jours}j-baisse=achat"] = etat(sx < sx.shift(k), sx > sx.shift(k))
    mv = oc.CapMVRVCur
    out["onchain/mvrv<1-achat->3.5-vente"] = tenir(mv < 1, mv > 3.5)
    out["onchain/mvrv<1.5-achat->3-vente"] = tenir(mv < 1.5, mv > 3)
    rg = I.rang_glissant(mv, barres(ctx, 4 * 365))
    out["onchain/mvrv-rang4ans"] = etat(rg < 0.3, rg > 0.9)
    mvz = I.zscore(mv, barres(ctx, 365))
    out["onchain/mvrv-z-annuel"] = etat(mvz < -1, mvz > 1.5)
    for a, b in ((30, 60), (7, 30)):
        if oc.HashRate.notna().sum() > 1000:
            ha, hb = oc.HashRate.rolling(barres(ctx, a)).mean(), oc.HashRate.rolling(barres(ctx, b)).mean()
            out[f"onchain/hash-ribbon{a}-{b}"] = etat(ha > hb)
            # signal « hash ribbon » classique : sortie de capitulation des mineurs + prix au-dessus de sa SMA 10 j
            cap = (ha < hb).rolling(barres(ctx, 60)).max() > 0
            out[f"onchain/hash-ribbon-achat{a}-{b}"] = tenir((ha > hb) & cap & (c > I.sma(c, barres(ctx, 10))), ha < hb)
    for a, b in ((30, 90), (7, 30)):
        aa, ab = oc.AdrActCnt.rolling(barres(ctx, a)).mean(), oc.AdrActCnt.rolling(barres(ctx, b)).mean()
        out[f"onchain/adresses{a}-{b}"] = etat(aa > ab, aa < ab)
        ta, tb = oc.TxCnt.rolling(barres(ctx, a)).mean(), oc.TxCnt.rolling(barres(ctx, b)).mean()
        out[f"onchain/transactions{a}-{b}"] = etat(ta > tb, ta < tb)
    fe = oc.FeeTotNtv.rolling(barres(ctx, 7)).mean()
    rgf = I.rang_glissant(fe, an)
    out["onchain/frais-bas-achat"] = etat(rgf < 0.2, rgf > 0.9)
    return {k: v.fillna(0) for k, v in out.items()}


def f_ethbtc(ctx):
    """La paire ETH/BTC. Pour le bitcoin : ETH/BTC qui monte = appétit pour le risque (alt season) ;
    on teste les deux sens, la recherche dira lequel compte."""
    eb = ctx["ethbtc"]; out = {}
    for n in (20, 50, 100, 200):
        m = I.sma(eb, n)
        out[f"ethbtc/eth-fort-ma{n}"] = etat(eb > m, eb < m)
        out[f"ethbtc/btc-fort-ma{n}"] = etat(eb < m, eb > m)
    for jours in (7, 30, 90):
        k = barres(ctx, jours)
        out[f"ethbtc/eth-fort-{jours}j"] = etat(eb > eb.shift(k), eb < eb.shift(k))
        out[f"ethbtc/btc-fort-{jours}j"] = etat(eb < eb.shift(k), eb > eb.shift(k))
    return out


def f_calendrier(ctx):
    d = ctx["d"]; out = {}
    if ctx["tf"] == "1d":
        wd = d.index.dayofweek
        out["calendrier/hors-week-end"] = etat(pd.Series(wd < 5, index=d.index).shift(-1).fillna(False).astype(bool))
        out["calendrier/lundi"] = etat(pd.Series(wd == 6, index=d.index))   # décidé dimanche soir
    else:
        h = d.index.hour
        for a, b, nom in ((13, 21, "ny"), (0, 8, "asie"), (7, 15, "londres"), (21, 24, "soir-us")):
            tenue = pd.Series((h >= a) & (h < b), index=d.index)
            out[f"calendrier/heures-{nom}"] = etat(tenue.shift(-1).fillna(False).astype(bool))
    return out


FAMILLES = [f_tendance, f_ichimoku, f_macd, f_rsi, f_vwap, f_fibonacci, f_bollinger, f_orderflow, f_derives,
            f_onchain, f_ethbtc, f_calendrier]


def tous(ctx):
    out = {}
    for f in FAMILLES:
        out.update(f(ctx))
    return out


def filtres(ctx):
    """Filtres de régime : +1 = les achats sont permis, -1 = les ventes, 0 = rien. Une variante filtrée garde sa
    position seulement quand le filtre est du même signe."""
    d = ctx["d"]; c = d.close
    ich = I.ichimoku(d, 9, 26, 52)
    haut = np.maximum(ich["spanA"], ich["spanB"]); bas = np.minimum(ich["spanA"], ich["spanB"])
    oc = ctx["onchain"]
    net = (oc.FlowInExNtv - oc.FlowOutExNtv).rolling(barres(ctx, 30)).mean()
    n7 = barres(ctx, 7)
    of = d.delta.rolling(n7).sum() / d.volume.rolling(n7).sum()
    fr = ctx["funding"].rolling(barres(ctx, 7), min_periods=1).mean()
    rgf = I.rang_glissant(fr, barres(ctx, 365))
    eb = ctx["ethbtc"]
    j200 = I.sma(c, barres(ctx, 200))          # MA200 JOURNALIÈRE quelle que soit l'unité
    m, s, _ = I.macd(c, 12, 26, 9)
    return {
        "ma200": np.sign(c - I.sma(c, 200)).fillna(0),
        "ma200j": np.sign(c - j200).fillna(0),
        "nuage": etat(c > haut, c < bas),
        "macd": np.sign(m - s).fillna(0),
        "orderflow7j": np.sign(of).fillna(0),
        "onchain-flux": etat(net < 0, net > 0).fillna(0),
        "funding-pas-extreme": etat(rgf < 0.9, rgf > 0.1).where(fr.notna(), 1),
        "ethbtc-monte": np.sign(eb - I.sma(eb, 50)).fillna(0),
        "ethbtc-baisse": -np.sign(eb - I.sma(eb, 50)).fillna(0),
    }


def filtrer(pos, filtre):
    return pos.where(np.sign(pos) == np.sign(filtre), 0)
