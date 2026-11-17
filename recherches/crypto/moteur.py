"""Évaluation d'une position (série de -1, 0, +1 ou fractions) décidée à la CLÔTURE de chaque bougie.

- La position décidée à la clôture de t est tenue pendant la bougie t+1 (aucun regard vers le futur).
- Coût payé à chaque changement de position : |Δposition| × coût par côté (frais + glissement).
- Mode « perp » : le financement des perpétuels Binance est payé par les acheteurs et reçu par les vendeurs quand il
  est positif (avant sept. 2019, 0,01 % toutes les 8 h, le taux de base).
- Les rendements sont regroupés par jour (UTC) pour toutes les statistiques.
- alpha : régression des rendements journaliers de la stratégie sur ceux de l'actif (achat-conservation), t de Newey-West.
  Un alpha positif = la stratégie fait mieux que la même exposition moyenne prise au hasard.
"""
import numpy as np
import pandas as pd

MODES = {
    # coût par côté : frais taker + glissement
    "spot": dict(cout=0.0010 + 0.0002, financement=False, short=False),     # Binance spot 0,10 % + 0,02 %
    "perp": dict(cout=0.0005 + 0.0002, financement=True, short=True),       # Binance perpétuel 0,05 % + 0,02 %
    "court": dict(cout=0.0005 + 0.0002, financement=True, short=True, seul_court=True),   # perpétuel, ventes seules
}
RECHERCHE = (pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2026-11-17", tz="UTC"))


def financement_par_bougie(funding, index):
    """Somme des taux de financement tombant dans chaque bougie de `index`."""
    f = funding.reindex(funding.index.union(index)).fillna(0)
    pas = index.to_series().diff().median()
    g = f.groupby(np.searchsorted(index.values, f.index.values, side="right") - 1).sum()
    out = pd.Series(0.0, index=index)
    ok = g.index[(g.index >= 0)]
    out.iloc[ok] = g.loc[ok].values
    # avant le premier financement connu : 0,01 % par tranche de 8 h
    debut = funding.index.min()
    avant = index < debut
    base = 0.0001 * pas / pd.Timedelta("8h")
    out[avant] = base
    out[index > funding.index.max() + pd.Timedelta("8h")] = base      # après la dernière archive mensuelle
    return out


def rendements(pos, close, mode, funding_bougie=None):
    m = MODES[mode]
    p = pos.clip(lower=-1 if m["short"] else 0, upper=1).fillna(0)
    tenue = p.shift(1).fillna(0)
    r = close.pct_change().fillna(0)
    net = tenue * r - (p - p.shift(1).fillna(0)).abs().shift(1).fillna(0) * m["cout"]
    if m["financement"] and funding_bougie is not None:
        net = net - tenue * funding_bougie
    return net, tenue


def journalier(x):
    return (1 + x).groupby(x.index.floor("D")).prod() - 1


def nw_t(y, X, lags=5):
    """OLS y = a + b X, t de Newey-West de a et de b."""
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n = len(y)
    xe = X * e[:, None]
    S = xe.T @ xe
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        g = xe[l:].T @ xe[:-l]
        S += w * (g + g.T)
    XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ S @ XtXi
    se = np.sqrt(np.diag(V))
    return beta, beta / se


def stats(net_j, bh_j, tenue, debut, fin):
    s = (net_j.index >= debut) & (net_j.index < fin)
    y, x = net_j[s].values, bh_j[s].values
    if len(y) < 60:
        return None
    tm = (tenue.index >= debut) & (tenue.index < fin)
    t = tenue[tm]
    trades = int(((t != 0) & (t != t.shift(1).fillna(0))).sum())
    eq = np.cumprod(1 + y)
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    ans = len(y) / 365
    sharpe = y.mean() / y.std() * np.sqrt(365) if y.std() > 0 else 0
    (a, b), (ta, tb) = nw_t(y, x)
    return dict(sharpe=sharpe, cagr=eq[-1] ** (1 / ans) - 1, mdd=dd, expo=float(t.abs().mean()), trades=trades,
                trades_an=trades / ans, alpha_an=a * 365, t_alpha=ta, beta=b, total=eq[-1] - 1)


def evaluer(pos, close, mode, funding_bougie=None, periodes=None):
    net, tenue = rendements(pos, close, mode, funding_bougie)
    nj = journalier(net)
    bh = journalier(close.pct_change().fillna(0))
    periodes = periodes or {"R": RECHERCHE, "V": VALIDATION}
    return {k: stats(nj, bh, tenue, *v) for k, v in periodes.items()}


class Banc:
    """Version rapide de `evaluer` pour des milliers de variantes sur le même actif et la même unité de temps."""

    def __init__(self, close, funding_bougie, periodes=None):
        self.close = close
        self.r = close.pct_change().fillna(0).values
        self.fb = funding_bougie.reindex(close.index).fillna(0).values
        jour = close.index.floor("D")
        self.debut_jour = np.r_[0, np.flatnonzero(jour[1:] != jour[:-1]) + 1]
        self.jours = jour[self.debut_jour]
        self.periodes = periodes or {"R": RECHERCHE, "V": VALIDATION}
        self.masques = {k: (self.jours >= a) & (self.jours < b) for k, (a, b) in self.periodes.items()}
        self.masques_b = {k: (close.index >= a) & (close.index < b) for k, (a, b) in self.periodes.items()}
        self.bh = self._jour(self.r)

    def _jour(self, x):
        return np.expm1(np.add.reduceat(np.log1p(np.maximum(x, -0.999)), self.debut_jour))

    def evaluer(self, pos, mode):
        m = MODES[mode]
        p = np.clip(np.nan_to_num(np.asarray(pos, dtype=float)), -1 if m["short"] else 0, 0 if m.get("seul_court") else 1)
        tenue = np.r_[0.0, p[:-1]]
        chg = np.abs(np.diff(np.r_[0.0, tenue]))
        net = tenue * self.r - chg * m["cout"]
        if m["financement"]:
            net = net - tenue * self.fb
        nj = self._jour(net)
        res = {}
        for k, mk in self.masques.items():
            y, x = nj[mk], self.bh[mk]
            if len(y) < 60 or y.std() == 0:
                res[k] = None
                continue
            t = tenue[self.masques_b[k]]
            prev = np.r_[0.0, t[:-1]]
            trades = int(((t != 0) & (t != prev)).sum())
            eq = np.cumprod(1 + y)
            ans = len(y) / 365
            (a, b), (ta, tb) = nw_t(y, x)
            res[k] = dict(sharpe=y.mean() / y.std() * np.sqrt(365), cagr=eq[-1] ** (1 / ans) - 1,
                          mdd=(eq / np.maximum.accumulate(eq) - 1).min(), expo=float(np.abs(t).mean()),
                          trades=trades, alpha_an=a * 365, t_alpha=ta, beta=b, total=eq[-1] - 1)
        return res

    def achat_conservation(self):
        out = {}
        for k, mk in self.masques.items():
            y = self.bh[mk]; eq = np.cumprod(1 + y); ans = len(y) / 365
            out[k] = dict(sharpe=y.mean() / y.std() * np.sqrt(365), cagr=eq[-1] ** (1 / ans) - 1,
                          mdd=(eq / np.maximum.accumulate(eq) - 1).min(), total=eq[-1] - 1)
        return out
