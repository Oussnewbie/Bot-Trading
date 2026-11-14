# Étape 1 — la v5 de référence sur les données du dépôt

Simulateur : `backtest/nas100-10ans/v5_lab.py`, réglages de `orb_v5.py`, sans aucune modification. Glissement 0,1 point (celui du code).

## 1. Périodes du README (choix de la v5, puis vérification)

| Période | | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|---|
| 2018-01 → 2018-04 (avant la période de choix) | sans pyramide | 50 | +0.175R | +8.8R | -9.1R | 5 |
| 2018-01 → 2018-04 (avant la période de choix) | v5 | 50 | +0.463R | +23.1R | -9.1R | 5 |
| 2018-05 → 2022-08 (période de choix) | sans pyramide | 724 | +0.210R | +151.9R | -22.6R | 9 |
| 2018-05 → 2022-08 (période de choix) | v5 | 724 | +0.344R | +248.8R | -21.8R | 9 |
| 2022-09 → 2026-11 (vérification) | sans pyramide | 653 | +0.184R | +119.9R | -27.4R | 13 |
| 2022-09 → 2026-11 (vérification) | v5 | 653 | +0.254R | +166.0R | -24.7R | 13 |
| Tout : 2018 → 2026-11 | sans pyramide | 1427 | +0.197R | +280.6R | -27.4R | 13 |
| Tout : 2018 → 2026-11 | v5 | 1427 | +0.307R | +438.0R | -24.7R | 13 |

## 2. Les bougies M5 de l'étude contre celles du simulateur

1427 trades par le chargeur du simulateur, 1427 par les bougies de l'étude, 1427 à la même minute ; écart maximal de R : 0.00e+00. **Mêmes trades, mêmes R.**

## 3. Découpage de l'étude

Du 2018-01-03 au 2026-11-13. La coupe recherche / vérification (2021-01-01) est une proposition.

| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|
| **Recherche : 2018 → 2020** | 498 | +0.347R | +172.8R | -21.8R | 9 |
| **Vérification : 2021 → 2022** | 324 | +0.309R | +100.2R | -13.4R | 8 |
| **Finale : 2023 → 2026-11** | 605 | +0.273R | +165.0R | -24.7R | 13 |
| Tout : 2018 → 2026-11 | 1427 | +0.307R | +438.0R | -24.7R | 13 |

Par année :

| Année | Jours simulables | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|---|
| 2018 | 256 | 166 | +0.558R | +92.5R | -16.4R | 7 |
| 2019 | 258 | 158 | +0.226R | +35.7R | -11.7R | 6 |
| 2020 | 254 | 174 | +0.256R | +44.6R | -21.6R | 9 |
| 2021 | 258 | 165 | +0.296R | +48.8R | -13.4R | 7 |
| 2022 | 258 | 159 | +0.323R | +51.4R | -10.0R | 8 |
| 2023 | 256 | 166 | +0.372R | +61.7R | -19.0R | 6 |
| 2024 | 259 | 154 | +0.155R | +23.9R | -19.8R | 13 |
| 2025 | 257 | 151 | +0.281R | +42.5R | -17.5R | 8 |
| 2026 | 225 | 134 | +0.276R | +36.9R | -15.9R | 11 |

Rappel : avant 2018 la v5 perd (2015-2017 : -55R, pire baisse -74R ; 2013-05 → 2014 : -33R, 26 pertes de suite). Ces années ne sont plus dans le dépôt ; le détail est dans `sorties/historique-2011-2026/`. La pire baisse lue sur 2018-2026 ne contient pas ce régime.
