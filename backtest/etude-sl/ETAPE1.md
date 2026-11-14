# Étape 1 — données et reproduction : résumé

Détail : [sorties/etape1_inventaire.md](sorties/etape1_inventaire.md), [sorties/etape1_qualite.md](sorties/etape1_qualite.md),
[sorties/etape1_m5.md](sorties/etape1_m5.md), [sorties/etape1_reproduction.md](sorties/etape1_reproduction.md).
Pour tout refaire : `./00_telecharger.sh`, puis `01_construire.py`, `02_qualite.py`, `03_comparer_m5.py`, `04_reproduction.py`.

## Données téléchargées (Dukascopy, M1 bid et ask, aucun échec)

| | Demandé | Première bougie réelle | Premier jour avec un vrai spread et la fenêtre 9:00-9:30 | Dernière bougie | M1 |
|---|---|---|---|---|---|
| Nasdaq CFD (`usatechidxusd`) | 2010-01-01 | 2011-09-19 | **2013-05-22** (qualité moyenne jusqu'en mai 2014) | 2026-11-13 | 4 252 808 |
| Or (`xauusd`) | 2010-01-01 | 2010-01-01 (2009-12-31 19:02 à New York) | **2010-01-01** | 2026-11-13 | 5 997 966 |

Le Nasdaq ne remonte pas à 2010 :
- 2010 : rien. 2011 : quatre séances en septembre, puis rien jusqu'au 19 janvier 2012.
- 2012-01-19 → 2013-02-22 : le bid et l'ask sont identiques (spread nul) et seule la séance 9:30-16:00 est cotée. Sans
  spread réel et sans la fenêtre 9:00-9:30, la v5 ne peut pas y être simulée.
- 2013-02-25 → 2013-05-21 : aucune cotation.
- À partir du 2013-05-22 : vrai spread et cotation hors séance. Mais jusqu'en mai 2014 la qualité reste moyenne :
  octobre 2013 n'a que 18 séances sur 23, le spread tombe à 0,25 point d'octobre 2013 à janvier 2014 (contre 2,2 avant et
  après), et une pause de cotation de 15 minutes revient chaque jour vers 14:15 ou 15:15 de septembre 2013 à mai 2014.

Horizons reconstruits pour les deux instruments : M1, M3, M5, M15, M30, H1, H4, D1 (H4 et D1 alignées sur 17:00 New York).

**La nuit manque sur le Nasdaq de 2015 à mi-2018.** La cotation ne commence qu'à 2:00 New York en 2015 (80 % des jours),
2016 et 2017, et la séance asiatique n'est complète qu'à partir de 2019 (72 % des jours en 2018). Ces années-là il n'y a
que 4 bougies H4 par jour au lieu de 6, et la bougie D1 commence à 2:00. Londres (3:00-8:00) et 8:00-9:30 sont cotées à
99-100 % depuis 2015. L'or est coté 23 heures sur 24 depuis 2010.

## Qualité à partir de 2015 (Nasdaq) et de 2010 (or)

- Aucune bougie incohérente, aucune valeur manquante, aucun doublon ; ask jamais sous le bid à partir de 2013.
- Nasdaq 2015-2026 : aucun jour ouvré manquant hors jours fériés ; 37 jours fériés sans séance ; 102 séances courtes, dont
  97 jours fériés ou demi-séances (le CFD cote jusqu'à 13:00 environ) et 5 hors calendrier (2 au 5 novembre 2015, arrêt à
  15:00 ; 31 décembre 2015, arrêt à 13:00). Fenêtre 9:00-9:45 incomplète : 10 séances en 12 ans.
- Spread du Nasdaq en séance : 1,0 à 1,5 point depuis 2015, mais 10 à 12 % du range de 9:30 en 2015-2017 contre 1 à 3 %
  depuis 2021. Spreads aberrants : 16 minutes en 12 ans, dont 12 le 4 janvier 2016 (jusqu'à 35 points).
- Or : séances complètes depuis 2010, aucun jour ouvré manquant. Spread de 0,24 à 0,62 dollar, soit 10 à 29 % du range
  M5 de 9:30 jusqu'en 2025 et 6 % en 2026 : l'ORB de 5 minutes y coûtera cher. Spreads aberrants : 24 au 26 mars 2020
  (jusqu'à 12,6 dollars), plus 2 minutes isolées en 2026.
- Sauts de prix en une minute (plus de 1,5 % sur le Nasdaq : 17 ; plus de 1 % sur l'or : 29) : la plupart tombent à des
  heures d'annonces (8:30, 10:00, 14:00) ou en avril 2025. Je ne les ai pas vérifiés un par un.

## Reproduction

| Contrôle | Résultat |
|---|---|
| M5 reconstruit depuis le M1 contre `donnees/`, 2015-01-01 → 2026-10-30 | 733 078 bougies bid et 733 078 ask, **0 écart de prix** |
| `v5_lab` + réglages de `orb_v5.py` sur `donnees/` | **1 925 trades, +372,4R, pire baisse -74,1R, 13 pertes de suite** : les 8 lignes du README |
| Le même sans les 10 trades de janvier 2015 que l'ancien code écartait | **1 915 trades, +373,0R, -69,1R** : les chiffres de la demande et de l'en-tête de l'EA |
| `v5_lab` sur le M5 reconstruit, mêmes dates | mêmes 1 925 trades, même R au trade près |

« 1 915 trades, +373R » est l'ancien chiffre, d'avant le correctif de l'audit (commit `d2cf90e`). Le README de `main` dit
1 925 trades, +372R, -74R. Les deux sont retrouvés et l'écart est expliqué.

## La v5 non modifiée, découpage de l'étude (M5 reconstruit, glissement 0,1 point du code)

| | Trades | R par trade | Total | Pire baisse | Pire série de pertes |
|---|---|---|---|---|---|
| 2013-05 → 2014 (jamais simulé jusqu'ici) | 231 | -0,144R | -33,2R | -53,1R | 26 |
| 2015 → 2017 | 505 | -0,108R | -54,6R | -74,1R | 11 |
| **Recherche (si elle commence au 2013-05-22) → 2017** | 736 | -0,119R | -87,8R | -122,8R | 26 |
| **Vérification : 2018 → 2022** | 822 | +0,332R | +273,0R | -21,8R | 9 |
| **Finale : 2023 → 2026-11-13** | 605 | +0,273R | +165,0R | -24,7R | 13 |
| Tout | 2 163 | +0,162R | +350,2R | -122,8R | 26 |

- La série de 26 pertes va du 2014-07-09 au 2014-09-11, dans la partie propre des données.
- Le spread coûte alors 27 à 32 % du range de 9:30 (10 à 12 % en 2015-2017, 1 à 3 % depuis 2021). Rejouée au prix milieu,
  la v5 de juin-décembre 2014 passe de -45R à -10R, et celle de 2015-2017 de -55R à +32R : le coût explique l'essentiel de
  la perte, pas toute. Cette comparaison est grossière (les trades ne sont pas exactement les mêmes).
- Période de recherche selon sa date de départ : depuis 2013-05-22, 736 trades et -88R ; depuis 2014-06-01, 596 trades et
  -100R ; depuis 2015-01-01, 505 trades et -55R.

## À savoir avant l'étape 2

1. **La période de recherche est celle où la v5 perd** (-55R à -100R selon son début), et la v5 a été choisie sur 2018-05 → 2022-08. Un pattern
   « dans le même sens sur les trois périodes » devra tenir à la fois quand la stratégie perd et quand elle gagne.
2. **La période finale 2023-2026 n'est pas vierge.** Le README y a mesuré la v5, et `research/RAPPORT.md` (branche
   `recherche/stops`) y a déjà lu une fois cinq variantes : stop à la clôture M5, filtre de spread, jours fériés, biais
   H4, et leur combinaison. Je les ai lus. `commun.charger` verrouille 2023+ pour tout ce qui n'est pas la v5 non modifiée.
3. **Le volume Dukascopy n'est pas un nombre de ticks.** Pour le « volume en ticks de la bougie de 9:30 », il faut
   télécharger les ticks de l'heure de l'ouverture (disponibles depuis 2013).
4. **Le texte de la demande est coupé** au milieu de l'étape 3 (« Teste ensuite une seule variante »).
5. **Variables de contexte limitées par les données** : les niveaux de la séance asiatique, et la tendance ou la MA200 en
   H4 et D1 sur bougies complètes, ne sont pas mesurables sur le Nasdaq de 2015 à mi-2018.
6. **Le verrou de la période finale** ne couvre que `commun.charger`. `v5_lab.prep()` sur les fichiers du dépôt lit encore
   2023+ : à fermer au début de l'étape 2, avant toute courbe contrefactuelle.
