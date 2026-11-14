# Étape 1 — qualité des données M1 (Dukascopy, bid et ask)

Fenêtre de l'étude : 2018-01-01 -> dernière bougie. L'historique complet (2011 -> 2026) et les raisons de ce choix sont dans `sorties/historique-2011-2026/`.

Heures de New York. Aucun trade n'est joué ici. Le calendrier américain est calculé par règles (NYSE) : il sert à expliquer les séances manquantes ou courtes, pas à les définir.

# nas100

M1 du 2018-01-02 02:05 au 2026-11-13 16:14 (New York)  2 998 259 bougies.

Bougies incohérentes (high sous open/close, low au-dessus) : bid 0, ask 0. Valeurs manquantes : 0. Prix nuls ou négatifs : 0.

Première série de 20 séances de suite avec au moins 90 % des minutes cotées (351 sur 390) : à partir du 2018-01-16.

## Jours et séances, par année

| Année | Jours ouvrés | Sans cotation en séance | dont jours fériés US | non expliqués | Séances courtes | dont fériés / demi-séances | non expliquées | Minutes cotées par séance (médiane, sur 390) | Séances avec un trou > 5 min | > 15 min | Fenêtre 9:00-9:45 incomplète |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 260 | 3 | 3 | 0 | 9 | 9 | 0 | 390 | 4 | 0 | 1 |
| 2019 | 261 | 3 | 3 | 0 | 9 | 9 | 0 | 390 | 0 | 0 | 0 |
| 2020 | 262 | 3 | 3 | 0 | 8 | 8 | 0 | 390 | 4 | 1 | 6 |
| 2021 | 261 | 3 | 3 | 0 | 7 | 7 | 0 | 390 | 0 | 0 | 0 |
| 2022 | 260 | 2 | 2 | 0 | 8 | 8 | 0 | 390 | 1 | 0 | 0 |
| 2023 | 260 | 4 | 4 | 0 | 8 | 8 | 0 | 390 | 1 | 1 | 0 |
| 2024 | 262 | 3 | 3 | 0 | 10 | 10 | 0 | 390 | 4 | 1 | 0 |
| 2025 | 261 | 4 | 4 | 0 | 10 | 10 | 0 | 390 | 3 | 0 | 0 |
| 2026 | 227 | 2 | 2 | 0 | 6 | 6 | 0 | 390 | 4 | 0 | 1 |

« Séance courte » : dernière cotation avant 15:45, ou moins de 60 % des minutes de la médiane de l'année. « Fenêtre incomplète » : il manque au moins une des neuf bougies M5 de 9:00 à 9:40 (hors jours sans cotation). Les trous sont comptés sur les séances complètes ; une minute sans cotation n'est pas une erreur en soi.

## Jours ouvrés à problème


**Jours ouvrés sans cotation en séance, hors jours fériés du calendrier : 0**.

**Séances courtes hors calendrier (panne, coupe-circuit, données) : 0**.

**Jours fériés du calendrier avec une séance complète dans les données (le CFD cote, ou le calendrier se trompe) : 0**.

**Demi-séances du calendrier avec une séance complète dans les données : 0**.

Jours fériés US du calendrier : 84, dont 27 sans cotation en séance, 57 en séance courte (dernière cotation médiane 12:58), 0 en séance complète.
Demi-séances du calendrier : 18, dont 0 sans cotation, 18 en séance courte (dernière cotation médiane 13:13), 0 en séance complète.

**Séances complètes avec un trou de plus de 15 minutes : 3**

| Jour | Minutes cotées | Plus grand trou (min) |
|---|---|---|
| 2020-03-16 (lun) | 374 | 17 |
| 2023-06-02 (ven) | 375 | 16 |
| 2024-08-12 (lun) | 361 | 30 |

**Fenêtre 9:00-9:45 incomplète (séance cotée) : 8**

| Jour | Bougies M5 présentes sur 9 | Minutes de 9:30-9:34 cotées | Férié / demi |
|---|---|---|---|
| 2018-02-14 (mer) | 8 | 0 |  |
| 2020-03-09 (lun) | 1 | 0 |  |
| 2020-03-12 (jeu) | 2 | 5 |  |
| 2020-03-13 (ven) | 3 | 5 |  |
| 2020-03-16 (lun) | 0 | 0 |  |
| 2020-03-18 (mer) | 3 | 5 |  |
| 2020-03-24 (mar) | 7 | 5 |  |
| 2026-03-10 (mar) | 8 | 5 |  |

## Spread (ask - bid, à la clôture de chaque M1), en points

| Année | Séance : médiane | 99e centile | maximum | 9:30-9:45 : médiane | 99e centile | Hors séance : médiane | Ask sous le bid | Spread nul | Aberrants en séance (> 10 × la médiane) | Spread de 9:35 / range de 9:30 (médiane) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 1.07 | 1.37 | 6.61 | 1.07 | 3.07 | 3.07 | 0 | 0 | 0 | 5.5 % |
| 2019 | 1.07 | 1.39 | 3.87 | 1.07 | 1.44 | 3.07 | 0 | 0 | 0 | 5.3 % |
| 2020 | 1.44 | 1.96 | 3.97 | 1.43 | 2.25 | 3.44 | 0 | 0 | 0 | 3.4 % |
| 2021 | 1.45 | 1.56 | 3.01 | 1.44 | 1.57 | 3.45 | 0 | 0 | 0 | 2.7 % |
| 2022 | 1.44 | 1.57 | 2.99 | 1.44 | 1.57 | 3.45 | 0 | 0 | 0 | 2.1 % |
| 2023 | 1.45 | 1.56 | 2.81 | 1.44 | 1.56 | 3.45 | 0 | 0 | 0 | 3.0 % |
| 2024 | 1.46 | 1.57 | 3.54 | 1.46 | 1.57 | 3.46 | 0 | 0 | 0 | 2.9 % |
| 2025 | 1.40 | 1.56 | 18.94 | 1.39 | 1.57 | 3.40 | 0 | 0 | 1 | 2.2 % |
| 2026 | 1.07 | 1.51 | 22.77 | 1.08 | 1.54 | 1.22 | 0 | 0 | 2 | 1.1 % |

Spreads aberrants en séance : 3 minutes sur 878172, réparties sur 3 jours. Les dix plus grands :

| Minute (New York) | Bid | Ask | Spread |
|---|---|---|---|
| 2026-03-24 09:44 | 23951.50 | 23974.27 | 22.77 |
| 2025-11-07 09:59 | 24890.55 | 24909.49 | 18.94 |
| 2026-06-01 09:59 | 30247.54 | 30261.25 | 13.72 |

Jours les plus touchés (minutes aberrantes) : 2025-11-07 (1), 2026-03-24 (1), 2026-06-01 (1).
Dont entre 9:30 et 10:00 : 3 minutes sur 3 jours.

## Sauts de prix

Variations de plus de 1.5 % entre deux M1 séparées de 5 minutes au plus : 17.

| Minute (New York) | Variation |
|---|---|
| 2022-10-13 08:30 | 3.44 % |
| 2022-11-10 08:31 | 3.44 % |
| 2025-04-09 13:19 | 2.94 % |
| 2022-07-13 08:30 | 2.60 % |
| 2020-03-03 10:00 | 2.22 % |
| 2022-09-13 08:30 | 2.16 % |
| 2022-12-02 08:30 | 1.94 % |
| 2022-12-13 08:30 | 1.82 % |
| 2025-04-09 13:28 | 1.78 % |
| 2025-04-07 10:18 | 1.75 % |
| 2020-03-18 15:59 | 1.67 % |
| 2025-04-07 10:10 | 1.59 % |
| 2025-04-07 11:14 | 1.56 % |
| 2022-12-09 08:30 | 1.55 % |
| 2022-11-02 14:36 | 1.53 % |

## Heures cotées hors séance, par année

Journée de trading de 17:00 à 17:00 New York, jours avec une séance cotée. Asie = 18:00-3:00, Londres = 3:00-8:00, avant l'ouverture = 8:00-9:30. Une fenêtre est « cotée » si plus de la moitié de ses minutes le sont.

| Année | Séances | M1 par journée (médiane) | Première cotation (médiane) | Dernière (médiane) | Asie cotée | Londres cotée | 8:00-9:30 cotée | Bougies H4 par journée (médiane, sur 6) | Journées avec 6 H4 |
|---|---|---|---|---|---|---|---|---|---|
| 2018 | 257 | 1331 | 18:00 | 16:14 | 72 % | 100 % | 100 % | 6 | 70 % |
| 2019 | 258 | 1335 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 99 % |
| 2020 | 259 | 1335 | 18:00 | 16:14 | 99 % | 99 % | 98 % | 6 | 97 % |
| 2021 | 258 | 1335 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 98 % |
| 2022 | 258 | 1335 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 97 % |
| 2023 | 254 | 1335 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 98 % |
| 2024 | 259 | 1329 | 18:03 | 16:14 | 100 % | 100 % | 100 % | 6 | 97 % |
| 2025 | 257 | 1332 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 97 % |
| 2026 | 225 | 1335 | 18:00 | 16:14 | 100 % | 100 % | 100 % | 6 | 97 % |

Séances sans séance asiatique cotée : 75, dont 75 depuis 2018 ; la dernière série se termine le 2018-04-12. Part des séances avec l'Asie cotée, par mois de 2018 : 01 : 0 %, 02 : 0 %, 03 : 0 %, 04 : 57 %, 05 : 100 %, 06 : 100 %, 07 : 100 %, 08 : 100 %, 09 : 100 %, 10 : 100 %, 11 : 100 %, 12 : 100 %.

# or

M1 du 2018-01-01 18:00 au 2026-11-13 16:59 (New York)  3 144 343 bougies.

Bougies incohérentes (high sous open/close, low au-dessus) : bid 0, ask 0. Valeurs manquantes : 0. Prix nuls ou négatifs : 0.

Première série de 20 séances de suite avec au moins 90 % des minutes cotées (351 sur 390) : à partir du 2018-01-16.

## Jours et séances, par année

| Année | Jours ouvrés | Sans cotation en séance | dont jours fériés US | non expliqués | Séances courtes | dont fériés / demi-séances | non expliquées | Minutes cotées par séance (médiane, sur 390) | Séances avec un trou > 5 min | > 15 min | Fenêtre 9:00-9:45 incomplète |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 261 | 3 | 3 | 0 | 8 | 8 | 0 | 390 | 0 | 0 | 0 |
| 2019 | 261 | 3 | 3 | 0 | 8 | 8 | 0 | 390 | 1 | 0 | 0 |
| 2020 | 262 | 3 | 3 | 0 | 8 | 8 | 0 | 390 | 1 | 0 | 0 |
| 2021 | 261 | 3 | 3 | 0 | 7 | 7 | 0 | 390 | 0 | 0 | 0 |
| 2022 | 260 | 2 | 2 | 0 | 8 | 8 | 0 | 390 | 1 | 0 | 0 |
| 2023 | 260 | 3 | 3 | 0 | 8 | 8 | 0 | 390 | 0 | 0 | 0 |
| 2024 | 262 | 3 | 3 | 0 | 9 | 9 | 0 | 390 | 0 | 0 | 0 |
| 2025 | 261 | 3 | 3 | 0 | 9 | 9 | 0 | 390 | 0 | 0 | 0 |
| 2026 | 227 | 2 | 2 | 0 | 6 | 6 | 0 | 390 | 0 | 0 | 0 |

« Séance courte » : dernière cotation avant 15:45, ou moins de 60 % des minutes de la médiane de l'année. « Fenêtre incomplète » : il manque au moins une des neuf bougies M5 de 9:00 à 9:40 (hors jours sans cotation). Les trous sont comptés sur les séances complètes ; une minute sans cotation n'est pas une erreur en soi.

## Jours ouvrés à problème


**Jours ouvrés sans cotation en séance, hors jours fériés du calendrier : 0**.

**Séances courtes hors calendrier (panne, coupe-circuit, données) : 0**.

**Jours fériés du calendrier avec une séance complète dans les données (le CFD cote, ou le calendrier se trompe) : 2**

| Jour | Férié | Minutes cotées | Dernière |
|---|---|---|---|
| 2018-12-05 (mer) | Deuil national (G. H. W. Bush) | 389 | 15:59 |
| 2025-01-09 (jeu) | Deuil national (J. Carter) | 390 | 15:59 |

**Demi-séances du calendrier avec une séance complète dans les données : 5**

| Jour | Demi-séance | Minutes cotées | Dernière |
|---|---|---|---|
| 2018-07-03 (mar) | Veille du 4 juillet | 390 | 15:59 |
| 2019-07-03 (mer) | Veille du 4 juillet | 389 | 15:59 |
| 2023-07-03 (lun) | Veille du 4 juillet | 386 | 15:59 |
| 2024-07-03 (mer) | Veille du 4 juillet | 390 | 15:59 |
| 2025-07-03 (jeu) | Veille du 4 juillet | 390 | 15:59 |

Jours fériés US du calendrier : 85, dont 25 sans cotation en séance, 58 en séance courte (dernière cotation médiane 14:22), 2 en séance complète.
Demi-séances du calendrier : 18, dont 0 sans cotation, 13 en séance courte (dernière cotation médiane 13:44), 5 en séance complète.

**Séances complètes avec un trou de plus de 15 minutes : 0**.

**Fenêtre 9:00-9:45 incomplète (séance cotée) : 0**.

## Spread (ask - bid, à la clôture de chaque M1), en points

| Année | Séance : médiane | 99e centile | maximum | 9:30-9:45 : médiane | 99e centile | Hors séance : médiane | Ask sous le bid | Spread nul | Aberrants en séance (> 10 × la médiane) | Spread de 9:35 / range de 9:30 (médiane) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 0.24 | 0.33 | 0.55 | 0.23 | 0.33 | 0.24 | 0 | 0 | 0 | 19.7 % |
| 2019 | 0.29 | 0.35 | 1.93 | 0.29 | 0.35 | 0.29 | 0 | 0 | 0 | 20.5 % |
| 2020 | 0.38 | 1.85 | 12.63 | 0.40 | 2.08 | 0.41 | 0 | 0 | 227 | 13.0 % |
| 2021 | 0.34 | 0.46 | 1.67 | 0.35 | 0.49 | 0.36 | 0 | 0 | 0 | 11.6 % |
| 2022 | 0.34 | 0.49 | 1.60 | 0.35 | 0.49 | 0.38 | 0 | 0 | 0 | 12.1 % |
| 2023 | 0.33 | 0.42 | 1.29 | 0.33 | 0.45 | 0.33 | 0 | 0 | 0 | 12.2 % |
| 2024 | 0.37 | 0.56 | 1.80 | 0.38 | 0.59 | 0.38 | 0 | 0 | 0 | 10.7 % |
| 2025 | 0.56 | 1.02 | 4.36 | 0.59 | 1.10 | 0.59 | 0 | 0 | 0 | 9.9 % |
| 2026 | 0.62 | 1.44 | 7.37 | 0.63 | 1.45 | 0.68 | 0 | 0 | 2 | 5.9 % |

Spreads aberrants en séance : 229 minutes sur 883449, réparties sur 5 jours. Les dix plus grands :

| Minute (New York) | Bid | Ask | Spread |
|---|---|---|---|
| 2020-03-24 10:25 | 1594.82 | 1607.45 | 12.63 |
| 2020-03-24 10:24 | 1592.04 | 1604.18 | 12.14 |
| 2020-03-24 09:41 | 1598.62 | 1609.92 | 11.31 |
| 2020-03-24 10:12 | 1599.74 | 1610.73 | 10.99 |
| 2020-03-24 10:21 | 1590.75 | 1601.14 | 10.39 |
| 2020-03-24 10:11 | 1601.07 | 1611.22 | 10.15 |
| 2020-03-24 11:38 | 1608.94 | 1618.33 | 9.39 |
| 2020-03-24 09:40 | 1601.11 | 1610.31 | 9.21 |
| 2020-03-24 15:20 | 1621.00 | 1629.87 | 8.87 |
| 2020-03-24 15:21 | 1620.44 | 1629.31 | 8.87 |

Jours les plus touchés (minutes aberrantes) : 2020-03-24 (215), 2020-03-25 (7), 2020-03-26 (5), 2026-02-02 (1), 2026-08-28 (1).
Dont entre 9:30 et 10:00 : 29 minutes sur 3 jours.

## Sauts de prix

Variations de plus de 1.0 % entre deux M1 séparées de 5 minutes au plus : 18.

| Minute (New York) | Variation |
|---|---|
| 2021-08-08 18:57 | 2.55 % |
| 2026-01-29 10:27 | 2.35 % |
| 2026-09-04 08:30 | 1.57 % |
| 2026-02-01 20:10 | 1.49 % |
| 2026-07-14 08:30 | 1.43 % |
| 2026-03-23 07:05 | 1.30 % |
| 2026-07-02 08:30 | 1.28 % |
| 2022-11-10 08:30 | 1.28 % |
| 2026-01-30 03:33 | 1.24 % |
| 2026-02-01 20:09 | 1.21 % |
| 2026-02-11 08:30 | 1.18 % |
| 2026-03-24 07:01 | 1.15 % |
| 2021-08-08 19:03 | 1.13 % |
| 2020-01-05 18:01 | 1.06 % |
| 2026-02-01 20:07 | 1.06 % |

## Heures cotées hors séance, par année

Journée de trading de 17:00 à 17:00 New York, jours avec une séance cotée. Asie = 18:00-3:00, Londres = 3:00-8:00, avant l'ouverture = 8:00-9:30. Une fenêtre est « cotée » si plus de la moitié de ses minutes le sont.

| Année | Séances | M1 par journée (médiane) | Première cotation (médiane) | Dernière (médiane) | Asie cotée | Londres cotée | 8:00-9:30 cotée | Bougies H4 par journée (médiane, sur 6) | Journées avec 6 H4 |
|---|---|---|---|---|---|---|---|---|---|
| 2018 | 258 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 98 % |
| 2019 | 258 | 1378 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 99 % |
| 2020 | 259 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 98 % |
| 2021 | 258 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 98 % |
| 2022 | 258 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 100 % |
| 2023 | 256 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 100 % |
| 2024 | 259 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 100 % |
| 2025 | 258 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 100 % |
| 2026 | 225 | 1380 | 18:00 | 16:59 | 100 % | 100 % | 100 % | 6 | 99 % |
