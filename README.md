# Bot-Trading — stratégie ORB v3 (TradingView, Pine Script v6)

Cassure du range d'ouverture de New York (ORB 5 minutes) sur le Nasdaq (NAS100), graphique M5.
Toutes les heures sont en heure de New York (9:30 NY = 15:30 à Paris la plupart de l'année).

## Contenu

| Fichier | Rôle |
|---|---|
| `pine/ORB-v3.pine` | **La stratégie à utiliser.** Range de la bougie de 9:30, achat stop sur le high et vente stop sur le low (le premier exécuté annule l'autre), ordres valables jusqu'à 9:45, stop de l'autre côté du range, stop remonté au prix d'entrée dès +1,5R, sortie à 15:45. Filtre RSI14 M5 en option. Risque 0,5 % par trade. Affichage épuré, alertes Telegram. |
| `pine/AMD-plus-v2.pine` | Ancienne stratégie (sweep de liquidité puis changement de structure). **Perdante sur 8 ans : ne pas la trader.** Gardée pour mémoire. |
| `backtest/nas100-10ans/` | Recherche sur 8 ans et demi de NAS100 (bid et ask, spread compté) : v2, familles de setups, ORB, filtres d'indicateurs, gestion du trade. |
| `backtest/` (racine) | Premier simulateur, testé sur 60 jours de futures (Yahoo Finance). Résultats trop courts pour être fiables. |
| `donnees/` | Données Dukascopy NAS100 CFD M5, bid et ask, 2015 → 2026 (zip). |

## Utiliser la v3

1. Dans TradingView, ouvre l'éditeur Pine, crée un nouveau script, colle le contenu de `pine/ORB-v3.pine` et enregistre.
2. Ajoute-le sur un graphique **M5** du NAS100.
3. Dans « Propriétés », ajoute une commission égale au spread de ton broker : le testeur de TradingView ne compte pas le spread d'un CFD.
4. Alertes Telegram : une alerte sur la stratégie, condition « Uniquement les appels de la fonction alert() », webhook
   `https://api.telegram.org/bot<TOKEN>/sendMessage` (plan TradingView payant nécessaire, Essential suffit).
   Après chaque changement de réglage, supprime et recrée l'alerte.

Ce que tu vois sur le graphique :
- à 9:35, une petite boîte grise sur le range de 9:30 et les deux ordres en tirets avec leur prix ;
- à l'exécution, l'ordre opposé disparaît, l'entrée (trait épais) et le stop (rouge) restent, avec le résultat en R en direct ;
  le stop devient gris quand il passe au prix d'entrée ;
- à la sortie, les lignes s'arrêtent et s'estompent, le résultat en R reste affiché ; un jour sans cassure ne laisse rien ;
- en haut à droite, un petit tableau : range du jour, état du jour, historique et pire baisse.

## Résultats (NAS100 CFD Dukascopy, mai 2018 → octobre 2026, spread réel compté)

Méthode : réglages choisis sur mai 2018 → août 2022, vérifiés sur septembre 2022 → octobre 2026 sans retouche.
Avant mai 2018, Dukascopy ne cote pas la nuit : ces années ne sont pas utilisées.

| | Trades | Par trade | 2018-22 / 2022-26 | Total | Pire baisse | Pire série | Années + |
|---|---|---|---|---|---|---|---|
| v2 (sweep de liquidité, ICT) | 885 | -0,15R | -0,24 / -0,06 | -135R | -154R | 16 | 2/9 |
| ORB de base (sortie 15:50) | 2 189 | +0,108R | +0,13 / +0,09 | +237R | -48R | 18 | 7/9 |
| **ORB v3** (cassure avant 9:45, stop à l'entrée dès +1,5R) | 2 091 | **+0,114R** | +0,14 / +0,09 | +238R | **-32R** | **13** | **8/9** |
| ORB v3 + filtre RSI14 M5 (option) | 1 547 | +0,153R | +0,19 / +0,12 | +237R | -29R | 12 | 9/9 |

- À 0,5 % de risque par trade : environ +14 % par an, pire baisse -15 %. À 1 % : environ +27 % par an, pire baisse -28 %.
  C'est l'historique, pas une promesse.
- Sans effet ou nuisibles : MA200, MA50, EMA200 H1, MACD, Ichimoku, Bollinger, Fibonacci, stop plus large ou plus serré,
  stop à l'entrée dès +1R, prises partielles, inversion après un faux départ.
- Stratégies d'indicateurs testées seules : seuls le RSI(2) journalier et la cassure de Donchian sont légèrement positifs,
  avec trop peu de trades (environ 9 par an).

## Refaire les tests

Python 3 avec `pandas` et `numpy`. Décompresse d'abord le zip de `donnees/` dans ce même dossier, puis :

```bash
cd backtest/nas100-10ans
python orbx_run.py     # calcule les indicateurs à 9:35 (orb_features.pkl) et teste les filtres
python orbv_run.py     # anatomie des trades perdants et gagnants
python orbv_var.py     # pistes de gestion : taille du stop, stop à l'entrée, partielles, stop dans le temps…
python orbv_combo.py   # version retenue (v3) et simulation du capital
python orbx_part2.py   # filtres d'indicateurs sur la première cassure
python famgrid.py      # grille ORB et continuation après sweep
python var10.py        # variantes de la v2 sur 8 ans
python strat.py        # stratégies d'indicateurs seules (RSI2, Donchian, MACD, Ichimoku, Bollinger, Fibonacci)
```

## Avertissement

Ce dépôt n'est pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures.
