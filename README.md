# Bot-Trading — stratégie AMD+ (TradingView, Pine Script v6)

Stratégie M5 « Accumulation → Manipulation → Distribution » : le range de l'Asie (et d'autres poches de liquidité)
se fait prendre pendant une kill zone, puis le prix se retourne. Toutes les heures sont en heure de New York.

## Contenu

| Fichier | Rôle |
|---|---|
| `pine/AMD-plus-v1.pine` | Première version : sweep du range asiatique puis reclôture dans le range. Tes réglages du 09/11/2026 en valeurs par défaut. |
| `pine/AMD-plus-v2.pine` | Version 2 : confirmation par changement de structure M5 (CHoCH), poches Asie / veille / Londres / NY matin, 3 kill zones, premium / discount, objectif sur la liquidité opposée, statistiques par séance et par poche. |
| `backtest/` | Simulateur Python qui reproduit les règles du script, bougie par bougie, pour tester des variantes hors de TradingView. |

## Utiliser un script

1. Dans TradingView, ouvre l'éditeur Pine, crée un nouveau script, colle le contenu du fichier `.pine` et enregistre.
2. Ajoute-le sur un graphique **M5**.
3. Après chaque changement de réglage, supprime et recrée les alertes Telegram : une alerte garde les réglages du moment où elle a été créée.

## Résultats du test (31/08 → 09/11/2026, futures NQ, ES, YM, RTY, or, euro)

| | Trades | Gagnants | Espérance | Total | Pire série |
|---|---|---|---|---|---|
| v1 (tes réglages) | 254 | 33 % | -0,01R | -2R | 9 pertes |
| v2 (réglages par défaut) | 110 | 42 % | +0,43R | +48R | 8 pertes |

- v2 positive sur les 6 marchés et sur chacun des 3 mois. Nasdaq seul : v1 -3R en 42 trades, v2 +5R en 19 trades.
- Ce qui compte le plus : la confirmation par CHoCH (la simple reclôture perd), le filtre premium / discount,
  l'objectif sur la poche de liquidité opposée.
- Aucun filtre de biais testé (journalier, H4, H1, dans le sens ou contre) n'a amélioré le résultat.
- Environ 0,4 trade par jour sur un seul marché ; environ 2,2 par jour sur les 6 marchés.

**Limites :** 60 jours seulement, et la meilleure de près de 800 variantes : le résultat réel sera probablement
moins bon. Les fills du simulateur sont prudents (si le stop et l'objectif sont dans la même bougie, c'est un stop).
À valider dans le testeur de stratégie de TradingView sur un historique plus long, puis en démo.

## Refaire les tests

Python 3 avec `pandas`, `numpy` et `yfinance` :

```bash
cd backtest
pip install pandas numpy yfinance
python fetch_data.py   # 60 derniers jours en M5 (limite de Yahoo Finance)
python exp.py          # v1 contre variantes de la v2, sur le Nasdaq
python grid.py         # grille de ~800 variantes sur 6 marchés (quelques minutes), écrit grid.json
python analyze.py      # classement de la grille et effet de chaque option
python best.py         # meilleure configuration et variantes autour, détail par séance et par poche
python final.py        # configuration finale : par mois et par marché
```

Les données téléchargées ne sont pas versionnées (`backtest/data/` est ignoré).

## Avertissement

Ce dépôt n'est pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures.
