# Étape 1 — données et reproduction : résumé

Rapports : [sorties/etape1_inventaire.md](sorties/etape1_inventaire.md), [sorties/etape1_qualite.md](sorties/etape1_qualite.md),
[sorties/etape1_reference.md](sorties/etape1_reference.md). Pour tout refaire : `./refaire.sh`.

## Décision du 14 novembre 2026 : l'étude et le dépôt vont du 2018-01-01 au 2026-11-13

Le téléchargement complet (2010 → 2026) a montré que le Nasdaq de Dukascopy ne remonte pas à 2010 :

| | Demandé | Première bougie réelle | Ce qu'on trouve avant 2018 |
|---|---|---|---|
| Nasdaq CFD (`usatechidxusd`) | 2010-01-01 | 2011-09-19 | rien en 2010 ; spread nul jusqu'en février 2013 ; trou jusqu'au 2013-05-21 ; qualité moyenne jusqu'en mai 2014 ; pas de cotation de nuit de 2015 au 12 avril 2018 |
| Or (`xauusd`) | 2010-01-01 | 2010-01-01 | propre depuis 2010 |

Les preuves (inventaire, qualité, M5 identique à l'ancien fichier, reproduction de l'ancien README) sont dans
[sorties/historique-2011-2026/](sorties/historique-2011-2026/). Les données d'avant 2018 ont été retirées du dépôt.

## Données du dépôt (`donnees/`, M1 bid et ask, un zip par année, 194 Mo)

| | Première bougie (New York) | Dernière | M1 |
|---|---|---|---|
| Nasdaq CFD | 2018-01-02 02:05 | 2026-11-13 16:14 | 2 998 259 |
| Or | 2018-01-01 18:00 | 2026-11-13 16:59 | 3 144 343 |

Horizons reconstruits (hors git, `donnees/cache/bougies/`) : M1, M3, M5, M15, M30, H1, H4, D1. H4 et D1 sont alignées sur
17:00 New York, minuit du serveur MT5.

## Qualité, 2018 → 2026

- Aucune bougie incohérente, aucune valeur manquante, ask jamais sous le bid.
- Nasdaq : aucun jour ouvré manquant hors jours fériés (27 jours fériés sans séance) ; 75 séances courtes, toutes des
  jours fériés ou des demi-séances (le CFD cote jusqu'à 13:00 environ) ; fenêtre 9:00-9:45 incomplète 8 fois en 9 ans.
- Spread du Nasdaq en séance : 1,1 à 1,5 point, soit 5 % du range de 9:30 en 2018-2019 et 1 à 3 % depuis 2020. Spreads
  aberrants : 3 minutes en 9 ans.
- **La séance asiatique du Nasdaq ne commence que le 12 avril 2018.** De janvier à avril 2018 la cotation démarre à 2:00
  New York : pas de niveaux Asie, 4 bougies H4 par jour au lieu de 6.
- Les données commencent le 2018-01-01 : la MA200 en D1 n'existe qu'à partir d'octobre 2018, la MA200 en H4 à partir de
  mars 2018.
- Or : séances complètes, aucun jour manquant. Spread de 0,24 à 0,62 dollar, soit 20 % du range M5 de 9:30 en 2018-2019,
  10 à 13 % de 2020 à 2025, 6 % en 2026 : l'ORB de 5 minutes y coûtera cher. Spreads aberrants : 24 au 26 mars 2020.
- Sauts de prix en une minute (plus de 1,5 % sur le Nasdaq : 17 ; plus de 1 % sur l'or : 18) : la plupart tombent à des
  heures d'annonces (8:30, 10:00, 14:00) ou en avril 2025. Je ne les ai pas vérifiés un par un.

## Reproduction

| Contrôle | Résultat |
|---|---|
| M5 reconstruit depuis le M1 contre l'ancien fichier M5, 2015-01-01 → 2026-10-30 (avant son retrait) | 733 078 bougies bid et 733 078 ask, **0 écart de prix** |
| v5 sur l'ancien fichier | 1 925 trades, +372,4R, -74,1R : le README d'alors |
| Le même sans les 10 trades de janvier 2015 que l'ancien code écartait | 1 915 trades, +373,0R, -69,1R : les chiffres de la demande et de l'en-tête de l'EA |
| v5 sur les nouvelles données contre l'ancien fichier, 2018-01-01 → 2026-10-30 | **mêmes 1 420 trades, même R au trade près** |
| Réécriture indépendante des règles (`tests/regles_readme.py`) sur les nouvelles données | mêmes 1 427 trades |

## La v5 non modifiée, 2018-01-01 → 2026-11-13 (glissement 0,1 point du code)

| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|
| **Recherche : 2018 → 2020** (coupe proposée) | 498 | +0,347R | +172,8R | -21,8R | 9 |
| **Vérification : 2021 → 2022** (coupe proposée) | 324 | +0,309R | +100,2R | -13,4R | 8 |
| **Finale : 2023 → 2026-11-13** | 605 | +0,273R | +165,0R | -24,7R | 13 |
| Tout | 1 427 | +0,307R | +438,0R | -24,7R | 13 |

Pour mémoire, sur les années retirées : 2013-05 → 2014, 231 trades, -33,2R, 26 pertes de suite ; 2015 → 2017, 505 trades,
-54,6R, pire baisse -74,1R.

## À savoir avant l'étape 2

1. **2018-2026 est le régime où la v5 gagne, et celui où elle a été choisie** (mai 2018 → août 2022). La pire baisse y
   est de 25R ; elle était de 74R sur 2015-2017. Pour dimensionner le risque en prop firm, c'est 74R qu'il faut garder en
   tête. Et « dans le même sens sur les trois périodes » est plus facile à passer quand les trois se ressemblent.
2. **Le découpage est à confirmer.** La période finale reste 2023 → 2026 comme dans la demande. La période de recherche
   d'origine (début → 2017) n'existe plus : la coupe proposée est recherche 2018-2020, vérification 2021-2022.
3. **La période finale 2023-2026 n'est pas vierge** : voir [archives/](archives/). `commun.charger` la verrouille pour tout
   ce qui n'est pas la v5 non modifiée ; `v5_lab.prep()` sans argument la lit encore, à fermer au début de l'étape 2.
4. **Le volume Dukascopy n'est pas un nombre de ticks.** Le « volume en ticks de la bougie de 9:30 » demandera de
   télécharger les ticks de l'heure d'ouverture (étape 2).
