# Données

Dukascopy, bougies **M1**, **bid et ask**, du **2018-01-01 au 2026-11-13**, heures en **UTC** (début de bougie).

| Dossier | Instrument Dukascopy | Fichiers |
|---|---|---|
| `nas100/` | `usatechidxusd` (Nasdaq 100 en CFD) | `usatechidxusd-m1-<année>.zip` |
| `or/` | `xauusd` (or contre dollar) | `xauusd-m1-<année>.zip` |
| `eurusd/` | `eurusd` (euro contre dollar) | `eurusd-m1-<année>.zip` |
| `dow/` | `usa30idxusd` (Dow Jones en CFD) | `usa30idxusd-m1-<année>.zip` |
| `bitcoin/` | `btcusd` (bitcoin contre dollar, cote aussi le week-end) | `btcusd-m1-<année>.zip` |

Chaque zip contient deux fichiers CSV, `…-m1-bid-<année>.csv` et `…-m1-ask-<année>.csv`, tels que les écrit
`npx dukascopy-node` : `timestamp` (millisecondes UTC), `open`, `high`, `low`, `close`, `volume`.

- Les minutes sans cotation sont absentes (pas de bougies plates).
- Le volume est un volume coté par Dukascopy (en millions), pas un nombre de ticks ni un volume de marché.
- Le Nasdaq n'a pas de cotation de nuit avant le 12 avril 2018 (début à 2:00 New York).
- EUR/USD, Dow Jones et bitcoin ont été ajoutés le 15 novembre 2026 pour la recherche de `backtest/multi/`.
- Le spread du bitcoin vaut 1,2 à 1,8 % du prix en 2018-2020, puis 0,05 à 0,35 % depuis 2022 : les années d'avant 2022
  ne servent pas à juger une stratégie.
- Rien n'est à décompresser : `backtest/nas100-10ans/load10.py` lit les zips, et reconstruit le M5 du simulateur dans
  `donnees/cache/` (hors git).

Pour refaire ou prolonger : `backtest/etude-sl/00_telecharger.sh` (changer `FIN`, puis `./00_telecharger.sh 2026` pour
refaire l'année en cours).

Pourquoi 2018 : avant, les données du Nasdaq sont absentes, sans spread ou sans cotation de nuit, et la v5 y perd. Le
détail est dans `backtest/etude-sl/sorties/historique-2011-2026/`.
