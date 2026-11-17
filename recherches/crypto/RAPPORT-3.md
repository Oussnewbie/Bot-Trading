# Troisième passe : retournements de tendance, petites unités de temps, tendance de fond — 17 novembre 2026

Deux questions :
1. Comment détecter un retournement de tendance ?
2. Les ventes échouent-elles à cause de la hausse quasi exponentielle de la crypto, et marchent-elles mieux en M5,
   M15, M30, H1 ou H4 ?

Données : bougies 5 minutes de Binance (`02_telecharger_m5.sh`, 970 000 bougies par actif), regroupées en
15m, 30m, 1h, 4h et 1d. Recherche 2018-2022, vérification 2023-2026, BTC et ETH.

Ce n'est pas un conseil en investissement.

## En bref

1. **Aucun détecteur de retournement ne prévient mieux que le hasard, sur aucune unité de temps.** 16 détecteurs
   testés : divergences RSI, MACD et CVD, CHoCH, chasse de liquidité, climax de volume, englobante, RSI extrême,
   croisements… Leur « lift » (précision ÷ hasard) va de 0,87 à 1,06. La combinaison favorite des traders, divergence
   RSI + CHoCH, est la pire (0,87-0,93).
2. **Ce qui change les probabilités, c'est la tendance de l'unité supérieure.** En H4, quand le fond journalier est
   baissier, la prochaine baisse de 6 % arrive avant la hausse de 6 % dans 53 % des cas, contre 41 % quand il est
   haussier.
3. **La hausse de fond n'explique pas l'échec des ventes sur les petites unités.** Elle vaut 0,04 point de base par
   bougie en M5. Sur ces unités, ce sont les **frais** qui tuent tout : l'avantage brut d'un trade (−2 à +6 pb) est
   plus petit que l'aller-retour (4 pb en ordres limites, 14 pb au marché), à la vente comme à l'achat.
4. **Vendre contre la tendance de fond perd sur toutes les unités, même une fois la hausse de fond retirée** :
   −34 pb par trade en H1, −254 pb en journalier. Ce n'est pas la dérive, c'est le momentum de l'unité supérieure.
5. **Vendre dans le sens d'un fond baissier marche sur toutes les unités avant frais, et en H4 après frais.**
   Fond journalier baissier + tendance H4 baissière : Sharpe propre BTC 0,41 puis 0,24, ETH 0,71 puis 0,50. C'est
   **la première vente qui gagne dans les deux périodes sur les deux actifs**.
6. **Le système multi-unités améliore aussi l'achat.** Fond haussier + tendance H4 haussière : Sharpe BTC 1,34
   (contre 1,22 pour la confluence journalière seule), pire baisse −22 %.

## 1. Détecter un retournement (`retournements.py`)

**Vérité terrain : la « triple barrière » de López de Prado.** À la clôture de chaque bougie, on regarde la suite : le
prix touche-t-il d'abord +b % ou −b % dans les 100 bougies suivantes ? b suit l'unité de temps : 15 % en 1d, 6,1 % en
4h, 3,1 % en 1h, 2,2 % en 30m, 1,5 % en 15m, 0,9 % en 5m.

**Mesure.** Un détecteur de retournement baissier est utile si, après son signal, la baisse arrive en premier plus
souvent qu'au hasard : **lift = précision ÷ taux de base > 1**. Pour gagner en tradant avec un stop à +b et un
objectif à −b, il faut une précision au-dessus de 50 % + frais ÷ (2b).

| Détecteur (médiane BTC + ETH, 6 unités) | Lift retournement baissier (recherche / vérification) | Lift retournement haussier |
|---|---|---|
| Divergence RSI + CHoCH | 0,87 / 0,93 | 0,93 / 0,91 |
| Climax de volume (volume × 3, longue mèche) | 0,90 / 0,96 | 0,95 / 1,02 |
| RSI > 70 (< 30) | 0,91 / 1,00 | 0,95 / 0,99 |
| Usure (1re clôture sous l'EMA20 après 20 bougies dessus) | 0,93 / 1,01 | 0,93 / 0,98 |
| Divergence RSI | 0,96 / 1,02 | 0,97 / 1,02 |
| Englobante au sommet / au creux | 0,98 / 0,99 | 0,99 / 0,99 |
| Retour dans les bandes de Bollinger | 0,98 / 1,00 | 0,99 / 1,01 |
| CHoCH (cassure de la structure) | 0,99 / 1,01 | 0,98 / 0,98 |
| Divergence CVD (order flow) | 1,00 / 0,96 | 1,00 / 1,04 |
| Divergence CVD + CHoCH | 1,00 / 0,98 | 1,03 / 1,06 |
| Chasse de liquidité (plus haut de 20 bougies dépassé, clôture dessous) | 1,00 / 1,00 | 0,98 / 1,00 |
| Clôture sous l'EMA50, sous la kijun | 1,00 / 0,98-0,99 | 0,99-1,00 |
| Croisement EMA 9/21 | 1,01 / 1,00 | 1,00 / 1,00 |
| Divergence MACD | 1,03 / 0,98 | 0,97 / 0,97 |
| Sortie du nuage Ichimoku | 1,03 / 1,02 | 1,01 / 1,01 |

Même chose avec le filtre de tendance de fond (lift médian 0,90 à 1,04) et unité par unité (0,91 à 1,06, hors un
cas à 1,33 en journalier sur trop peu de signaux).

**Pourquoi ?** Un détecteur de retournement se déclenche à chaque sommet local, et la plupart des sommets locaux ne
sont pas des retournements, mais des pauses dans la tendance. Sur un marché à momentum comme la crypto, une
divergence annonce plus souvent une continuation qu'un retournement.

**Ce qui marche à la place : lire l'état de la tendance de l'unité supérieure**, pas chercher le point de
retournement.

| Taux de base : la baisse de b % arrive d'abord (recherche / vérification) | 15m | 1h | 4h |
|---|---|---|---|
| Fond journalier baissier (dans le sens d'une vente) | 49 % / 42 % | 52 % / 45 % | 53 % / 45 % |
| Sans filtre | 47 % / 40 % | 49 % / 43 % | 48 % / 41 % |
| Fond journalier haussier (vente contre la tendance) | 46 % / 40 % | 46 % / 42 % | 41 % / 40 % |

Concrètement, un retournement se **constate** quand l'unité supérieure a changé d'état. Dans la confluence, c'est le
score journalier qui passe sous −0,25 (MA200, nuage, MACD, VWAP, order flow… basculent ensemble). On entre ensuite sur
l'unité inférieure quand elle s'aligne. On rate le sommet, mais on prend le milieu du mouvement, avec beaucoup moins
de faux signaux.

## 2. Petites unités de temps et hausse de fond (`petites_tf.py`)

41 signaux (tendance, retour à la moyenne, retournement, order flow) sur 6 unités, BTC et ETH, à l'achat et à la
vente, sans filtre, dans le sens de la tendance de fond journalière, et contre elle. Pour chacun :
- le gain brut par trade ;
- le gain une fois la dérive haussière retirée (le rendement moyen de la période ôté de chaque bougie) ;
- le Sharpe net en ordres limites (0,02 % par côté) et au marché (0,07 %), financement compris.

**La dérive haussière par bougie** (BTC) : 0,04 pb en 5m, 0,1 en 15m, 0,4 en 1h, 1,4 en 4h, 9 en 1d (recherche).
Elle ne pèse que sur les trades tenus plusieurs jours.

**Ventes, médiane des 41 signaux, gain par trade en pb (recherche / vérification)** :

| Unité | Contre la tendance de fond | Contre, sans la dérive | Sans filtre | Dans le sens | Dans le sens, sans la dérive | Sharpe au marché, dans le sens |
|---|---|---|---|---|---|---|
| 5m | −4,7 / −2,4 | −3,8 / −1,5 | −1,5 / −1,6 | +0,8 / 0,0 | +3,0 / +1,0 | −1,7 / −2,6 |
| 15m | −14 / −6 | −11 / −4 | −4 / −4 | +2,0 / +1,4 | +4,3 / +4,2 | −0,8 / −1,0 |
| 30m | −22 / −14 | −18 / −10 | −5 / −10 | +4 / +1 | +10 / +6 | −0,3 / −0,5 |
| 1h | −45 / −26 | −34 / −18 | −19 / −14 | +8 / 0 | +20 / +10 | −0,1 / −0,3 |
| **4h** | −81 / −51 | −66 / −24 | −28 / −28 | **+57 / +27** | +89 / +52 | **+0,20 / +0,14** |
| 1d | −327 / −124 | −254 / −41 | −170 / −160 | +89 / −14 | +183 / +49 | +0,19 / −0,07 |

Lecture :
- **Contre la tendance de fond** : perdant partout, même sans la dérive. La hausse de fond n'est pas la cause : vendre
  contre la tendance de l'unité supérieure est perdant en soi.
- **Dans le sens** : gagnant partout avant frais, et la dérive retirée l'améliore (sur le journalier, elle coûte
  environ 90 pb par trade aux vendeurs). **Les frais avalent tout en dessous de H4.**
- Les achats suivent la même règle : dans le sens, Sharpe au marché +0,67 puis +0,51 en H4 ; contre, négatif partout.

**Meilleures ventes en H4 dans le sens d'un fond baissier**, positives après frais au marché sur les quatre
échantillons (BTC et ETH × recherche et vérification) :

| Signal | Sharpe BTC (R / V) | Sharpe ETH (R / V) |
|---|---|---|
| Chasse de liquidité + delta vendeur, tenue 8 jours | 0,76 / 0,25 | 0,42 / 0,50 |
| EMA50 < EMA200 en 4h | 0,26 / 0,23 | 0,31 / 0,25 |
| Englobante au sommet, tenue 8 jours | 0,68 / 0,24 | 0,31 / trop peu |
| Divergence CVD + CHoCH, tenue 8 jours | 0,81 / 0,17 | trop peu / 0,40 |

En H1, M30 et M15, aucune vente ne reste positive sur les quatre échantillons.

## 3. Le système multi-unités (`multi_tf.py`)

La journée donne le sens (score de confluence connu à la clôture de la veille), le H4 donne l'entrée :
- **achat** si score ≥ 0,25 ET EMA50 > EMA200 et clôture > EMA200 en 4h ;
- **vente** si score ≤ −0,25 ET EMA50 < EMA200 et clôture < EMA200 en 4h ;
- taille : 40 % ÷ volatilité 30 jours.

| Évalué en 4h, frais compris | BTC Sharpe (R / V / 2018-2026) | BTC gain par an, pire baisse | ETH Sharpe (R / V / 2018-2026) | ETH gain par an, pire baisse |
|---|---|---|---|---|
| Confluence journalière, achat | 1,35 / 1,04 / 1,22 | +32 %, −27 % | 1,29 / 0,86 / 1,11 | +30 %, −31 % |
| **Fond + H4, achat** | **1,52 / 1,11 / 1,34** | +35 %, **−22 %** | 1,30 / 0,91 / 1,14 | +30 %, −34 % |
| Fond + H4, achat et vente | 1,17 / 0,92 / 1,07 | +39 %, −33 % | 1,30 / 0,95 / 1,15 | **+43 %**, −41 % |
| … la vente seule | 0,41 / 0,24 / 0,35 | +6 %, −43 % | 0,71 / 0,50 / 0,62 | +14 %, −49 % |
| + chasse de liquidité en fond baissier | 1,08 / 0,51 / 0,85 | moins bien | 1,15 / 0,72 / 0,97 | moins bien |
| Achat-conservation | 0,43 / 0,99 / 0,60 | +19 %, −81 % | 0,60 / 0,48 / 0,55 | +11 %, −94 % |

- **Achat** : la confirmation H4 améliore le BTC sur les deux périodes et ne change presque rien sur l'ETH.
- **Vente** : elle gagne sur les deux actifs et les deux périodes, avec un vrai alpha (t de 1,7 à 2,8, parce qu'elle
  gagne quand le marché baisse). Mais sa pire baisse est lourde (−43 % et −49 %). Ajoutée à l'achat, elle **augmente
  le rendement** (BTC +39 % contre +35 %, ETH +43 % contre +30 %), mais **baisse le Sharpe sur le BTC** et creuse la
  pire baisse.
  - C'est donc un choix : un système achat seul plus régulier, ou un système achat + vente plus rentable et plus
    secoué. Un compromis à tester : la vente à demi-taille.
- **Réserves** :
  - le croisement EMA50/200 en 4h a été retenu après avoir vu qu'il tenait sur les quatre échantillons ;
  - la vérification n'est donc pas totalement propre ;
  - le déclencheur « chasse de liquidité » ajouté au système le dégrade en vérification.

`python recherches/crypto/systeme.py --jour` affiche maintenant la ligne multi-unités. Au 16 novembre 2026, fond baissier et
tendance 4h baissière sur BTC et ETH : **VENTE** selon le système multi-unités, alors que la confluence journalière seule
dit « hors marché ».

## 4. Doser la vente (`dosage_vente.py`)

La partie achat reste fixe (fond haussier + tendance H4). La vente est testée sous 20 formes, toutes écrites avant de
lancer :
- taille de 0 à 1 × celle de l'achat ;
- volatilité cible plus basse ;
- taille proportionnelle au score ;
- seuil plus strict ;
- pas de vente en peur extrême ;
- pas de vente quand le financement est négatif ;
- sortie plus rapide ;
- durée maximale de 30 jours ;
- frein quand la vente perd 15 % ;
- quelques combinaisons.

**Règle écrite avant** : meilleur Sharpe du système sur BTC 2018-2022. **Elle désigne la vente à quart de taille.**

| Système complet, Sharpe (2018-2022 / 2023-2026 / 2018-2026) | BTC | ETH | Portefeuille 50/50 BTC-ETH |
|---|---|---|---|
| Achat seul | 1,35 / 1,03 / 1,21 | 1,13 / 0,84 / 1,01 | 1,39 / 1,09 / 1,26 |
| **Vente à 0,25** (choisie) | **1,41 / 1,06 / 1,26** | **1,27 / 0,93 / 1,13** | **1,50 / 1,17 / 1,36** |
| Vente à 0,5 | 1,36 / 1,04 / 1,23 | 1,33 / 0,97 / 1,18 | 1,50 / 1,17 / 1,37 |
| Vente à 1 (pleine taille) | 1,17 / 0,92 / 1,07 | 1,30 / 0,95 / 1,15 | 1,35 / 1,08 / 1,24 |

| 2018-2026 | Gain par an (BTC / ETH / 50-50) | Pire baisse (BTC / ETH / 50-50) |
|---|---|---|
| Achat seul | +31 % / +26 % / +29 % | −23 % / −34 % / −22 % |
| **Vente à 0,25** | +34 % / +31 % / +33 % | −22 % / −31 % / −21 % |
| Vente à 0,5 | +36 % / +35 % / +37 % | −22 % / −31 % / −24 % |
| Vente à 1 | +39 % / +43 % / +43 % | −33 % / −41 % / −36 % |

- **La vente à quart de taille améliore tout, sur les échantillons qui n'ont pas servi à la choisir** : Sharpe plus
  haut, rendement plus haut, pire baisse égale ou plus faible, sur BTC 2023-2026, sur l'ETH et sur le portefeuille.
  La vente rapporte quand l'achat est dehors : elle remplit les années baissières sans ajouter de risque, tant
  qu'elle reste petite.
- **À demi-taille**, c'est presque pareil, avec 3 à 4 % de rendement en plus par an et un peu plus de pire baisse.
  C'est l'alternative raisonnable.
- **À pleine taille**, la vente dégrade le BTC. Ses pertes dans les rebonds violents (−43 % de pire baisse à elle
  seule) pèsent plus que ses gains.
- **Ce qui n'aide pas** :
  - Taille proportionnelle au score, sortie rapide à l'EMA20, frein après une perte de 15 % : moins bien.
  - Ne pas vendre en peur extrême (F&G < 20) : **moins bien**. Les baisses continuent souvent en pleine peur ; les
    rebonds violents viennent plus tard.
  - Filtre de financement négatif : ne change rien (il ne se déclenche presque jamais en même temps que le reste).
- **Combinaisons trouvées après coup** : « 0,5 + seuil −0,5 » donne 1,39 sur le portefeuille, mais elle n'a pas été
  choisie par la règle. Elle n'est pas retenue.

**Système retenu** :
- **Achat** à la taille pleine du dosage (40 % ÷ volatilité 30 j) quand le fond journalier est haussier et le H4
  aussi.
- **Vente** au quart de cette taille, en perpétuel, quand le fond journalier est baissier et le H4 aussi.
- Sur un portefeuille 50/50 BTC-ETH, 2018-2026 : Sharpe 1,36, +33 % par an, pire baisse −21 %. L'achat-conservation
  fait 0,60, +19 % et −81 % sur le BTC.

## Ce que ça change pour l'outil

1. **Ne pas chercher à attraper le sommet** : aucun indicateur ne le fait mieux que le hasard, ni en M5 ni en
   journalier.
2. **Lire la tendance de l'unité supérieure, puis entrer sur l'unité inférieure dans son sens** : journalier → H4.
3. **Rester en H4 ou au-dessus**, sauf à trader en ordres limites et avec un avantage par trade bien supérieur à
   4 pb, ce qu'aucun signal testé n'a.
4. **Les ventes existent, mais seulement quand le journalier et le H4 sont baissiers tous les deux.** Jamais contre la
   tendance de fond. Et petites : un quart de la taille d'un achat.

## Refaire

```bash
bash recherches/crypto/02_telecharger_m5.sh       # 30 s : bougies 5 minutes BTC et ETH (280 Mo)
python recherches/crypto/petites_tf.py 4          # 41 signaux × 6 unités × 3 filtres × achat/vente (≈ 10 min)
python recherches/crypto/retournements.py 4       # 16 détecteurs × 6 unités × 3 filtres (≈ 5 min)
python recherches/crypto/multi_tf.py              # le système multi-unités
python recherches/crypto/dosage_vente.py          # 20 façons de doser la vente
```
