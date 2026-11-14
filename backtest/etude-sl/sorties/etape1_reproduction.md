# Étape 1 — reproduction de la v5

Simulateur : `backtest/nas100-10ans/v5_lab.py`, réglages de `orb_v5.py`, sans aucune modification. Glissement 0,1 point (celui du code).

## 1. Sur les données du dépôt (`donnees/`, M5)

| Période | | Trades | R par trade | Total | Pire baisse | Pire série | README | Verdict |
|---|---|---|---|---|---|---|---|---|
| 2015-01 → 2018-04 | sans pyramide | 555 | -0.094R | -52.1R | -78.2R | 11 | 555 trades, -52R, -78R | identique |
| 2015-01 → 2018-04 | v5 | 555 | -0.057R | -31.4R | -74.1R | 11 | 555 trades, -31R, -74R | identique |
| 2018-05 → 2022-08 | sans pyramide | 724 | +0.210R | +151.9R | -22.6R | 9 | 724 trades, +152R, -23R | identique |
| 2018-05 → 2022-08 | v5 | 724 | +0.344R | +248.8R | -21.8R | 9 | 724 trades, +249R, -22R | identique |
| 2022-09 → 2026-10 | sans pyramide | 646 | +0.172R | +111.3R | -27.4R | 13 | 646 trades, +111R, -27R | identique |
| 2022-09 → 2026-10 | v5 | 646 | +0.240R | +155.0R | -24.7R | 13 | 646 trades, +155R, -25R | identique |
| Tout : 2015 → 2026 | sans pyramide | 1925 | +0.110R | +211.1R | -78.2R | 13 | 1925 trades, +211R, -78R | identique |
| Tout : 2015 → 2026 | v5 | 1925 | +0.193R | +372.4R | -74.1R | 13 | 1925 trades, +372R, -74R | identique |

**Les 8 lignes du README sont retrouvées.**

## 2. D'où viennent « 1 915 trades, +373R »

Avant l'audit du 14 novembre 2026 (commit `d2cf90e`), le simulateur écartait les jours sans ATR journalier sur 14 jours, c'est-à-dire les premières semaines de 2015. La v5 n'utilise pas cet ATR. En rejouant la v5 sans ces jours :

| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|
| v5 sans les jours écartés par l'ancien code | 1915 | +0.195R | +373.0R | -69.1R | 13 |
| v5 du code actuel | 1925 | +0.193R | +372.4R | -74.1R | 13 |

Ancien chiffre attendu : 1915 trades, +373R, pire baisse -69R → **retrouvé**.
Les 10 trades de différence vont du 2015-01-02 au 2015-01-21 et totalisent -0.64R : 01-02 -1.01R, 01-05 -1.01R, 01-06 -1.01R, 01-08 +6.24R, 01-12 +1.17R, 01-13 -1.00R, 01-14 -1.00R, 01-16 -1.00R, 01-20 -1.01R, 01-21 -1.01R.

## 3. Sur le M5 reconstruit à partir du M1 téléchargé, de 2018-01-01 à la fin des données du dépôt

Le M1 de l'étude commence en 2017 (amorçage du RSI) ; les trades sont comparés à partir du 2018-01-01.

| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|
| Données du dépôt | 1420 | +0.301R | +427.0R | -24.7R | 13 |
| M5 reconstruit depuis le M1 | 1420 | +0.301R | +427.0R | -24.7R | 13 |

Trade par trade : 1420 trades dans le dépôt, 1420 dans le reconstruit, 1420 à la même minute ; écart maximal de R sur ces trades : 0.00e+00.

**Mêmes trades, mêmes R.**

## 4. La v5 non modifiée sur la fenêtre de l'étude (M5 reconstruit)

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

Rappel : avant 2018 la v5 perd (2015-2017 : -55R, pire baisse -74R ; détail dans `sorties/historique-2011-2026/`). La pire baisse lue sur 2018-2026 ne contient pas ce régime.

**Verdict de l'étape : reproduction réussie.**
