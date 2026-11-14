# Étape 1 — inventaire des données téléchargées et reconstruites

Source : Dukascopy, M1 bid et ask, par `npx dukascopy-node` (voir `00_telecharger.sh`). Heures de New York.
H4 et D1 sont alignées sur 17:00 New York (minuit du serveur MT5) ; M3 à H1 sur l'heure ronde.

## nas100 (usatechidxusd)

- Années sans aucune donnée chez Dukascopy : bid aucune, ask aucune.
- Première bougie M1 : bid 2017-01-03 02:00:00-05:00, ask 2017-01-03 02:00:00-05:00 (heure de New York).
- Dernière bougie M1 : bid 2026-11-13 16:14:00-05:00, ask 2026-11-13 16:14:00-05:00.
- Doublons retirés : bid 0, ask 0. Minutes présentes d'un seul côté : bid seul 1, ask seul 1 (écartées).
- M1 retenu : 3 209 360 bougies.

| Année | Lignes bid | Lignes ask | Jours avec cotation | M1 par jour (médiane) |
|---|---|---|---|---|
| 2017 | 211101 | 211101 | 257 | 833 |
| 2018 | 305647 | 305647 | 297 | 975 |
| 2019 | 342115 | 342115 | 312 | 1334 |
| 2020 | 341059 | 341059 | 312 | 1335 |
| 2021 | 343906 | 343906 | 311 | 1335 |
| 2022 | 342776 | 342776 | 310 | 1335 |
| 2023 | 340978 | 340978 | 310 | 1335 |
| 2024 | 342269 | 342269 | 313 | 1328 |
| 2025 | 340536 | 340536 | 312 | 1329 |
| 2026 | 298974 | 298974 | 271 | 1335 |

| Horizon | Bougies | Première | Dernière |
|---|---|---|---|
| M1 | 3209360 | 2017-01-03 02:00 | 2026-11-13 16:14 |
| M3 | 1071399 | 2017-01-03 02:00 | 2026-11-13 16:12 |
| M5 | 642974 | 2017-01-03 02:00 | 2026-11-13 16:10 |
| M15 | 214617 | 2017-01-03 02:00 | 2026-11-13 16:00 |
| M30 | 108495 | 2017-01-03 02:00 | 2026-11-13 16:00 |
| H1 | 55434 | 2017-01-03 02:00 | 2026-11-13 16:00 |
| H4 | 14560 | 2017-01-03 01:00 | 2026-11-13 13:00 |
| D1 | 2548 | 2017-01-02 17:00 | 2026-11-12 17:00 |

## or (xauusd)

- Années sans aucune donnée chez Dukascopy : bid aucune, ask aucune.
- Première bougie M1 : bid 2017-01-02 18:00:00-05:00, ask 2017-01-02 18:00:00-05:00 (heure de New York).
- Dernière bougie M1 : bid 2026-11-13 16:59:00-05:00, ask 2026-11-13 16:59:00-05:00.
- Doublons retirés : bid 0, ask 0. Minutes présentes d'un seul côté : bid seul 0, ask seul 2 (écartées).
- M1 retenu : 3 497 131 bougies.

| Année | Lignes bid | Lignes ask | Jours avec cotation | M1 par jour (médiane) |
|---|---|---|---|---|
| 2017 | 352788 | 352788 | 309 | 1380 |
| 2018 | 353923 | 353923 | 312 | 1379 |
| 2019 | 353290 | 353290 | 312 | 1374 |
| 2020 | 355495 | 355495 | 312 | 1380 |
| 2021 | 354346 | 354346 | 310 | 1380 |
| 2022 | 354633 | 354633 | 310 | 1380 |
| 2023 | 352969 | 352969 | 309 | 1379 |
| 2024 | 355892 | 355892 | 313 | 1380 |
| 2025 | 354415 | 354415 | 312 | 1380 |
| 2026 | 309380 | 309382 | 271 | 1380 |

| Horizon | Bougies | Première | Dernière |
|---|---|---|---|
| M1 | 3497131 | 2017-01-02 18:00 | 2026-11-13 16:59 |
| M3 | 1166313 | 2017-01-02 18:00 | 2026-11-13 16:57 |
| M5 | 699817 | 2017-01-02 18:00 | 2026-11-13 16:55 |
| M15 | 233292 | 2017-01-02 18:00 | 2026-11-13 16:45 |
| M30 | 116660 | 2017-01-02 18:00 | 2026-11-13 16:30 |
| H1 | 58350 | 2017-01-02 18:00 | 2026-11-13 16:00 |
| H4 | 15253 | 2017-01-02 17:00 | 2026-11-13 13:00 |
| D1 | 2547 | 2017-01-02 17:00 | 2026-11-12 17:00 |
