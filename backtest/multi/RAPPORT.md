# Recherche de stratégies sur le Dow Jones, l'or, l'EUR/USD et le bitcoin — 15 novembre 2026

**Conclusion : rien ne passe.** Sur 8 708 variantes rejouées sur cinq symboles, les seules qui gagnent sur les deux moitiés
de l'historique sont la cassure du range de 9:30 sur le Nasdaq — la v5 déjà en place. Aucune stratégie n'est proposée
pour les autres symboles : en ajouter une aujourd'hui, ce serait choisir la plus chanceuse.

## Les données

M1 Dukascopy, bid et ask, du 2018-01-01 au 2026-11-13, regroupé en M5 (`donnees/`, voir `donnees/LISEZMOI.md`). EUR/USD,
Dow Jones et bitcoin ont été téléchargés le 15 novembre 2026, sans échec. Aucune bougie avec l'ask sous le bid.

| Symbole | Bougies M5 | Spread médian en séance | Glissement compté par exécution |
|---|---|---|---|
| Nasdaq (`nas100`) | 600 093 | 1,34 point (0,010 % du prix) | 0,1 point |
| Dow Jones (`dow`) | 600 374 | 2,3 points (0,007 %) | 0,25 point |
| Or (`or`) | 629 245 | 0,34 $ (0,018 %) | 0,03 $ |
| EUR/USD (`eurusd`) | 663 497 | 0,3 pip (0,003 %) | 0,1 pip |
| Bitcoin (`bitcoin`) | 886 255 | 1,2 à 1,8 % du prix en 2018-2020, 0,05 à 0,35 % depuis 2022 | 2 $ |

Le spread du bitcoin chez Dukascopy avant 2022 ne ressemble à aucun courtier d'aujourd'hui : le bitcoin est jugé sur
2022-01 → 2024-06 (recherche) puis 2024-07 → 2026-11 (vérification).

## La règle, écrite avant de lancer les tests

Quand on essaie des milliers de variantes, des dizaines gagnent par hasard. Donc :

1. **Candidate** : au moins 100 trades et un t de Student d'au moins 3 sur la période de recherche seule
   (mai 2018 → août 2022). Un t de 3 arrive par hasard environ une fois sur 750.
2. **Confirmée** : positive avec un t d'au moins 2 sur la période de vérification (septembre 2022 → novembre 2026), qui
   n'a pas servi à la choisir.
3. Tout le reste est rejeté, quel que soit son total sur 9 ans.

## Le banc de test (`banc.py`)

Mêmes conventions prudentes que le simulateur de la v5 : achat à l'ask, vente au bid, glissement en plus ; le stop gagne
quand un stop et un gain sont possibles dans la même bougie ; un stop déplacé ne vaut qu'à la bougie suivante ; les
indicateurs n'utilisent que des bougies clôturées. **Contrôle :** la v5 du Nasdaq y donne 1 426 trades et +435R, contre
1 427 trades et +438R dans le simulateur d'origine.

## 1. L'analyse brute : toutes les heures de la journée (`fenetres.py`)

C'est le travail qui avait fait sortir la fenêtre de 9:30 sur le Nasdaq, refait pour chaque symbole : une fenêtre tous
les quarts d'heure, 24 heures sur 24, quatre longueurs de range (5, 15, 30, 60 minutes), cassure brute et cassure
filtrée (RSI + élan), avec et sans pyramide. 1 392 fenêtres par symbole, 6 960 en tout.

| Symbole | Fenêtres gagnantes en recherche | Meilleure fenêtre (recherche) | Même fenêtre en vérification | Spread ÷ risque (médiane) |
|---|---|---|---|---|
| **Nasdaq** | 18 % | **9:30, range 5 min, filtres, pyramide : +260R, t = 3,6** | **+160R, t = 2,4 : confirmée** | 0,03 à 9:30 |
| Dow Jones | 21 % | 2:30, range 60 min, pyramide : +192R, t = 2,7 | −53R | 0,10 |
| Or | 2 % | 9:15, range 30 min : +36R, t = 0,8 | 0R | 0,14 |
| EUR/USD | 11 % | 8:30, range 15 min, filtres, pyramide : +90R, t = 1,9 | −27R | 0,04 |
| Bitcoin | 0 % | aucune fenêtre positive | — | 0,50 |

- **Nasdaq** : la seule heure où la cassure brute gagne sur les deux moitiés est celle de 9:00 à 10:00, avec le sommet à
  9:30 et un range de 5 minutes. L'analyse retrouve donc toute seule la fenêtre de la v5. Les autres heures perdent.
  Deux fenêtres voisines (9:45 range 15 min, 10:00 range 60 min) gagnent en recherche et pas en vérification.
- **Dow Jones** : à 9:30 la cassure ne gagne rien (v5 telle quelle : +2R en recherche, −13R en vérification). Un petit
  avantage apparaît à l'ouverture de Londres (2:30 à 3:15 New York) en recherche, et disparaît en vérification.
- **Or** : toutes les heures perdent. La moins mauvaise est celle de 8:00 à 9:30 New York.
- **EUR/USD** : la demi-heure des statistiques américaines (8:30) gagne en recherche et perd en vérification.
- **Bitcoin** : le spread vaut la moitié du risque d'un trade ; rien ne peut gagner en M5 à ce prix.

Deuxième mesure brute, sans aucune règle de trading : le lien entre le mouvement d'une demi-heure et celui des deux heures
suivantes, à chaque demi-heure (`sorties/prolongement.csv`). Onze heures montraient un lien de même signe sur les deux
moitiés (par exemple l'or à 13:00 : le mouvement se retourne). En classant les jours par rang, le lien disparaît
(corrélation de rangs entre −0,07 et +0,03) : il venait de quelques journées extrêmes. Rejouées comme de vrais trades,
les onze perdent sur les deux moitiés.

## 2. Les familles de stratégies demandées (`familles.py`, `recherche.py`) — 1 510 variantes en M5

Cassure d'ouverture (toutes les ouvertures utiles : 2:00, 3:00, 8:00, 8:20, 9:30 selon le symbole), cassure d'un range de
séance (avant-marché, nuit, Asie, Londres, 24 heures précédentes = supports et résistances de la veille), prise de
liquidité (ICT / SMC : dépassement du range puis clôture de nouveau dedans), repli RSI, repli sur le VWAP, retour au VWAP
(bandes à 2 et 2,5 écarts-types), croisement MACD M15, centre de gravité Belkhayate (régression polynomiale M15, sans
repeinte), chacune avec et sans biais MA200 H1, et trois gestions (stop à l'entrée, objectif 2R, pyramide de la v5).

## 3. Stratégies tenues plusieurs jours (`swing.py`) — 220 variantes

Parce qu'en M5 le spread pèse 10 à 50 % du risque sur l'or et le bitcoin : cassure Donchian H1 et H4 avec stop suiveur,
repli RSI dans la tendance, croisement MACD H1 et H4, RSI2 journalier. Le financement de nuit est compté (6 % par an à
l'achat sur les indices et l'or, 3 % sur l'EUR/USD, 20 % sur le bitcoin : hypothèses à vérifier chez ton courtier).

## 4. Effets d'horaire connus (`horaires.py`) — 18 tests

Dérive de nuit des indices, élan de la dernière demi-heure, hausse de l'or pendant l'Asie, devise qui baisse pendant ses
heures de bureau. Aucun ne gagne une fois le spread et la nuit payés.

## Résultat des sections 2 à 4 (1 748 variantes)

| Symbole | Variantes | Gagnantes en recherche | Meilleure (t en recherche) | La même en vérification | Candidates | Confirmées |
|---|---|---|---|---|---|---|
| **Nasdaq** | 230 | 61 % | ORB 9:30, 5 min, filtres, pyramide (3,5) | +163R, t = 2,4 | 5 | **4** |
| Dow Jones | 230 | 27 % | ORB 9:30, 15 min, filtres + MA200, objectif 2R (1,6) | −20R | 0 | 0 |
| Or | 434 | 9 % | MACD H4 avec MA200, sur plusieurs jours (1,3) | +12R, t = 0,9 | 0 | 0 |
| EUR/USD | 529 | 15 % | ORB 9:30, 30 min, sans filtre (1,3) | +51R, t = 1,1 | 0 | 0 |
| Bitcoin (2022-2026) | 325 | 6 % | Donchian H4, 60 bougies (1,3) | −4R | 0 | 0 |

Les cinq candidates sont toutes la cassure de 9:30 du Nasdaq, range de 5 minutes, avec pyramide ; quatre sont confirmées
(avec les filtres de la v5, avec ou sans biais MA200, validité 10 ou 60 minutes), la cinquième (sans filtre) a un t de
1,7 en vérification. Le biais MA200 H1 n'apporte rien : même R par trade environ, deux fois moins de trades.

Familles qui perdent sur **tous** les symboles, dans les deux moitiés : retour au VWAP, centre de gravité Belkhayate,
repli RSI en M5, prise de liquidité. En M5, un trade de retour à la moyenne vise un petit gain que le spread mange.

## Ce que cela veut dire

- **L'EA ne doit trader que le Nasdaq.** Dans l'interface Étrave, les quatre autres symboles sont décochés, et les cocher
  demande une confirmation.
- **L'avantage du Nasdaq est isolé.** Un indice très proche, le Dow Jones, ne le montre pas, et la v5 perdait avant 2018
  (README). C'est une raison de plus de rester sur un petit risque et de surveiller la pire baisse.
- **Ce qui n'a pas été testé** : données en ticks, carnet d'ordres et vrai volume (les CFD n'en ont pas), annonces
  économiques, stratégies à plusieurs trades par jour, autres courtiers et leurs spreads, heures de Londres en heure de
  Londres (les trois semaines de décalage d'heure d'été par an ne sont pas corrigées).
- **Limite de la vérification** : les résultats de vérification ont été regardés pour toutes les variantes, pas seulement
  pour les candidates. Les prochaines idées n'auront plus de période vraiment neuve ; seul un compte démo en donnera une.

## Refaire

```bash
python backtest/multi/fenetres.py       # 3 minutes : sorties/fenetres.csv, sorties/prolongement.csv
python backtest/multi/recherche.py      # 1 minute  : sorties/variantes.csv
python backtest/multi/swing.py          # sorties/variantes-swing.csv
python backtest/multi/horaires.py       # sorties/variantes-horaires.csv
```

Les fichiers de `sorties/` gardent toutes les variantes, les perdantes aussi.
