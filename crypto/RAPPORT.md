# Bitcoin et Ethereum : quelle stratégie avec RSI, MACD, VWAP, Ichimoku, MA200, Fibonacci, order flow ? — 17 novembre 2026

## En bref

- **Aucun outil seul ne tient.** 42 400 évaluations (354 variantes × 9 filtres × 3 unités de temps × spot/perpétuel × BTC
  et ETH). Avec la règle écrite à l'avance, 11 candidates sur le bitcoin, **0 confirmée**.
- **Ce qui marche, c'est de les assembler, lentement.** Une **confluence de 9 votes** (un réglage standard par outil
  demandé, fixé avant de voir les résultats), en **journalier**, **achat seulement**, avec une taille dosée par la
  volatilité, fait mieux que l'achat-conservation sur les trois échantillons :

| 2018-01 → 2026-11, spot, coûts compris | Sharpe | Gain par an | Pire baisse | Temps investi |
|---|---|---|---|---|
| **Bitcoin, confluence** | **1,18** | **+31 %** | **−28 %** | 28 % |
| Bitcoin, achat-conservation | 0,60 | +19 % | −81 % | 100 % |
| **Ethereum, confluence** (mêmes réglages, jamais servi à choisir) | **1,05** | **+28 %** | **−31 %** | 21 % |
| Ethereum, achat-conservation | 0,55 | +11 % | −94 % | 100 % |

- Ce n'est **pas** une machine à battre le bitcoin pendant ses années de hausse (2020 : +82 % contre +302 %). C'est une
  façon de **rester dans les grandes tendances et d'être dehors pendant les krachs** (2018 : −5 % contre −73 % ; 2022 :
  −12 % contre −64 %).
- Elle **ne passe pas complètement la barre fixée au départ** : t de l'alpha 2,5 en recherche (il fallait 3) et 1,3 sur la
  vérification BTC (il fallait 1,5). Elle la passe sur l'Ethereum (2,65). C'est le meilleur résultat de l'étude, pas une
  preuve.
- **Aujourd'hui (bougie du 16 novembre 2026) : hors marché sur les deux**, 8 votes baissiers sur 9.

Ce n'est pas un conseil en investissement, et le passé ne garantit rien.

## Une précision sur « le volume vient de la blockchain »

Le volume d'échange du bitcoin **ne vient pas de la blockchain** : les achats et ventes se font dans les carnets d'ordres
des exchanges (Binance, Coinbase…), hors chaîne. La blockchain ne voit que les **transferts** (par exemple des bitcoins
envoyés vers un exchange, souvent pour être vendus). Les deux ont donc été testés séparément :

- **Order flow** : le volume des acheteurs agressifs (*taker buy*) publié par Binance pour chaque bougie, spot et
  perpétuel. Delta = achats agressifs − ventes agressives ; CVD = somme du delta. C'est le vrai order flow, que les CFD
  (Dukascopy, MetaTrader) n'ont pas.
- **On-chain** : Coin Metrics (API gratuite) : flux entrant et sortant des exchanges, réserves des exchanges, MVRV,
  hashrate (hash ribbons), adresses actives, transactions, frais.

## Les données (`00_telecharger.sh`, `donnees.py`, hors git)

| Source | Contenu | Période |
|---|---|---|
| Binance spot | BTCUSDT, ETHUSDT, **ETHBTC** en 1h, avec volume acheteur agressif | 2017-08 → 2026-11-16 |
| Binance perpétuels | BTCUSDT, ETHUSDT en 1h, financement (funding), open interest et ratios long/short | 2020-01 (OI : 2021-12) → 2026-11-16 |
| Coin Metrics | on-chain journalier BTC et ETH | 2015 → 2026-11-16 |
| Dukascopy (comme le Nasdaq) | BTC/USD (repris de l'historique git) et **ETH/USD** (téléchargé) en M1 bid et ask | 2018 → 2026-11 |

Dukascopy n'a pas de vrai volume : il sert seulement à mesurer ce que coûterait un CFD sur MetaTrader (spread réel).

## La méthode

Mêmes précautions que pour le Nasdaq :

- Tout signal est calculé à la **clôture** d'une bougie et exécuté pour la bougie suivante. Les données on-chain du jour
  D ne sont utilisées qu'à partir de D+2 à 00:00 UTC.
- Coûts : spot 0,10 % de frais + 0,02 % de glissement à chaque achat et à chaque vente ; perpétuel 0,05 % + 0,02 %,
  avec le **financement réel** payé ou reçu.
- Mesure : l'**alpha** contre l'achat-conservation (régression des rendements journaliers, t de Newey-West). Un signal
  qui gagne seulement parce que le bitcoin a monté a un alpha nul. C'est la seule mesure honnête sur un actif qui a pris
  ×15 depuis août 2017.
- **Choix sur le bitcoin 2018-2022** (recherche : deux krachs, deux hausses), **vérification sur le bitcoin 2023-2026**,
  et sur l'**Ethereum** en entier avec les mêmes réglages.

**Règle écrite avant de lancer** (`recherche.py`) : candidate = t de l'alpha ≥ 3 en recherche, Sharpe au-dessus de
l'achat-conservation, au moins 15 trades ; confirmée = t ≥ 1,5 en vérification BTC **et** t ≥ 1,5 sur l'ETH.

## Étape 1 : chaque outil et ses variantes (`signaux.py`, `recherche.py`)

354 variantes par actif et unité de temps, chacune seule puis filtrée par 9 filtres (MA200, MA200 journalière, nuage
Ichimoku, MACD, order flow 7 j, flux on-chain, financement pas extrême, ETH/BTC monte, ETH/BTC baisse).

| Famille | Variantes | Ce qui a été essayé |
|---|---|---|
| Tendance | 33 | prix > SMA/EMA 20 à 200, croisements (10/30 … 50/200), MA200 + pente, Donchian 20/55/100, Supertrend, momentum 30/90/180 j |
| Ichimoku | 18 | 9-26-52, 20-60-120 (réglage crypto), 10-30-60 : nuage, tenkan/kijun, kijun, signal complet (+ chikou + nuage futur) avec sortie kijun ou nuage |
| MACD | 20 | 12-26-9, 8-21-5, 24-52-18, 5-35-5, 19-39-9 : ligne de signal, zéro, les deux, histogramme |
| RSI | 39 | 7/14/21/28 : > 50, hystérésis 55/45, retour 30/70 · 25/75 · 20/80, replis dans la tendance, RSI 2 de Connors |
| VWAP | 15 | ancré semaine / mois / trimestre / année, glissant 3 à 90 j, ancré au plus bas 30/90/180 j, bandes de retour |
| Fibonacci | 108 | jambes de 10/30/60 j, entrée 0,382 / 0,5 / 0,618, stop 0,786 ou 1, cible 1 / 1,272 / 1,618, avec ou sans MA200 |
| Bollinger | 8 | cassure et retour, 20/50 bougies, 2 et 2,5 écarts-types |
| Order flow | 53 | ratio delta/volume 1 à 30 j (spot et perp), contre sa moyenne, capitulation (z-score), divergence et confirmation prix/CVD, cassure avec volume, spot qui mène le perp |
| Dérivés | 23 | financement contrarien / suiveur / négatif, open interest qui confirme ou se purge, excès d'OI, ratio taker long/short |
| On-chain | 19 | flux net des exchanges, réserves des exchanges, MVRV (seuils, rang, z-score), hash ribbons, adresses, transactions, frais |
| ETH/BTC | 14 | ETH/BTC au-dessus de sa MA 20 à 200, sur 7/30/90 j, dans les deux sens |
| Calendrier | 2-4 | hors week-end, lundi, heures d'Asie / Londres / New York |

**Résultat : 11 candidates sur 21 200 évaluations BTC, aucune confirmée.** Six des onze sont des signaux on-chain
(t ≈ 3 en recherche, nuls ou négatifs en vérification : de la chance). La plus solide est l'Ichimoku journalier complet avec
sortie à la kijun : t = 3,0 en recherche, 2,65 sur l'ETH, mais 0,3 sur la vérification BTC.

Médiane du t de l'alpha de chaque famille, sans filtre (positif = la famille fait mieux que le hasard) :

| Famille | 1d recherche | 1d vérif. | 1d ETH | 4h recherche | 4h vérif. | 4h ETH | 1h vérif. |
|---|---|---|---|---|---|---|---|
| **Ichimoku** | **1,76** | 0,31 | **1,92** | 1,28 | 0,01 | **2,22** | −2,31 |
| **Tendance (MA, Donchian…)** | **1,20** | 0,25 | **1,38** | 1,29 | 0,65 | **2,04** | −1,29 |
| **MACD** | **1,10** | **1,04** | **1,75** | 0,54 | −0,83 | 0,86 | −4,72 |
| VWAP | 0,40 | 0,00 | 0,14 | 1,39 | −0,26 | 1,29 | −1,04 |
| Bollinger | 0,34 | 0,77 | 0,77 | 0,80 | 0,42 | 0,97 | −1,01 |
| On-chain | 0,14 | 0,00 | 0,38 | 0,14 | −0,04 | 0,60 | −0,03 |
| Order flow | 0,11 | 0,22 | 0,04 | −0,21 | −0,55 | −0,09 | −1,11 |
| Dérivés (funding, OI) | 0,07 | −0,02 | −0,38 | −0,32 | −0,50 | −0,73 | −0,86 |
| Fibonacci | −0,24 | −0,82 | 0,00 | 0,43 | −0,52 | 0,35 | −0,57 |
| ETH/BTC (seul) | −0,37 | −0,24 | −0,13 | −0,77 | −1,25 | −0,53 | −3,00 |
| RSI | −0,50 | 0,11 | −0,24 | −0,83 | −0,45 | −0,29 | −2,13 |
| Calendrier | −0,74 | −1,23 | −1,87 | −5,57 | −7,59 | −6,13 | −8,14 |

Ce que cela dit :

- **Le bitcoin se trade en tendance, pas en retour à la moyenne.** Ichimoku, MACD et moyennes mobiles gagnent un peu
  partout en journalier ; RSI (surachat/survente, replis), Fibonacci et Bollinger « retour » ne gagnent nulle part de
  façon régulière.
- **En 1h, tout perd** une fois les frais payés (médianes de −1 à −8) : comme pour le bitcoin en M5 sur Dukascopy, les
  coûts mangent les petits mouvements. Le journalier est l'unité de temps qui tient.
- **Order flow seul : presque rien.** Le ratio d'achats agressifs suit le prix au lieu de le précéder. Il aide comme
  filtre lent (ratio 30 jours au-dessus de sa moyenne de 6 mois, avec la MA200) et comme vote dans la confluence.
- **Financement et open interest : rien.** Être contrarien quand le funding est extrême ne gagne ni sur BTC ni sur ETH.
- **On-chain : instable.** Les meilleures variantes en recherche (réserves des exchanges, flux nets) se retournent en
  vérification. Le MVRV n'a donné que 2 trades en 5 ans : impossible à juger.
- **ETH/BTC seul ne prédit rien**, ni pour le BTC ni pour l'ETH. Comme **un vote parmi neuf**, il aide un peu le bitcoin
  (voir plus bas).
- **Les filtres** qui aident le plus souvent, sur les trois échantillons : la MA200, l'order flow 7 j et le nuage
  Ichimoku. Les filtres ETH/BTC et financement ne servent pas.

## Étape 2 : assembler les outils (`confluence.py`)

Chaque outil vote +1, −1 ou 0 à la clôture journalière (00:00 UTC). Deux jeux de votes :

- **« a priori »**, écrit pendant que la grille tournait, avant d'en voir les résultats : un réglage standard par outil
  demandé.
- **« choisis »** : pour chaque famille, la variante qui avait le meilleur t sur la recherche.

| Bitcoin, spot, seuil 0,5, dosage 40 % | Sharpe recherche (t) | Sharpe vérification (t) |
|---|---|---|
| Votes **choisis** (optimisés) | 1,77 (3,7) | 0,71 (0,6) |
| Votes **a priori** (standards) | 1,00 (2,0) | **1,25 (1,8)** |

Exemple classique de sur-optimisation : les votes « choisis » brillent sur la période qui a servi à les choisir et
s'effondrent ensuite. **Les réglages standards généralisent mieux.** C'est la version retenue.

## Étape 3 : robustesse de la confluence a priori (`robustesse.py`, `sorties/robustesse.txt`)

- **Seuil et dosage voisins** : en journalier, tous les seuils de 0,15 à 0,5 et tous les dosages de 30 à 50 % gagnent
  sur la recherche, la vérification et l'ETH (Sharpe 2018-2026 entre 0,97 et 1,21 sur le BTC). Le seuil 0,25 et le
  dosage 40 % ont été pris sur la recherche ; le résultat n'est pas une pointe isolée.
- **En 4h, la même confluence perd sa vérification BTC** (t de −0,8 à 0). Elle est journalière.
- **Retirer un outil** : sur le BTC, chaque retrait fait baisser le Sharpe 2018-2026 (de 1,18 à 0,97-1,15). Les plus
  utiles : **order flow** (sans lui 0,97), MA200 (1,00), MACD (1,01), VWAP (1,02), ETH/BTC (1,05). Sur l'ETH, Ichimoku et
  order flow n'aident pas (sans eux 1,21 et 1,08 contre 1,05).
- **Version « prix seul »** (MA200, Ichimoku, MACD, RSI, VWAP, Fibonacci : codable dans TradingView ou MetaTrader sans
  données externes) : Sharpe 1,16 sur le BTC, presque aussi bien ; 0,95 sur l'ETH, moins bien, avec une pire baisse de
  −41 %.
- **Exécution en retard d'un jour** : Sharpe BTC 1,18 → 1,01, ETH 1,05 → 0,88. Il faut exécuter peu après 00:00 UTC
  (1:00 à Paris l'hiver, 2:00 l'été) : c'est un bot, pas un humain qui regarde le soir.
- **Année par année** (BTC) : −5 %, +121 %, +82 %, +20 %, −12 %, +41 %, +57 %, +4 %, +16 % de 2018 à 2026 ; la pire baisse
  dans une année ne dépasse jamais −25 %.
- **Vente à découvert (perpétuel)** : n'ajoute rien (Sharpe BTC 2018-2026 0,96 contre 1,18 en achat seul). Le
  financement payé et les rebonds violents des marchés baissiers mangent le gain des ventes.
- **Sur un CFD MetaTrader** (spread réel Dukascopy + swap) : sur 2023-2026, Sharpe BTC 1,16 sans swap, 1,02 avec 10 %
  par an, 0,88 avec 20 %, 0,74 avec 30 % ; l'ETH (spread 0,2 %) tombe à 0,58. **Le swap des CFD crypto coûte cher** :
  le spot (Binance ou un autre exchange) convient mieux.

## La stratégie proposée : « Confluence 9 », journalière, achat seulement

À chaque clôture journalière (00:00 UTC), neuf votes, +1 ou −1 (0 quand l'outil est neutre) :

| Vote | +1 (haussier) | −1 (baissier) |
|---|---|---|
| MA200 | clôture > SMA 200 jours | clôture < SMA 200 |
| Ichimoku 9-26-52 | clôture au-dessus du nuage | au-dessous (0 dans le nuage) |
| MACD 12-26-9 | MACD > ligne de signal | MACD < signal |
| RSI 14 | > 50 | < 50 |
| VWAP | clôture > VWAP ancré au 1er du mois | < VWAP du mois |
| Fibonacci | clôture > 0,618 de la jambe des 90 derniers jours (plus bas → plus haut) | < 0,382 (0 entre les deux) |
| Order flow | achats agressifs > ventes agressives sur 7 jours (Binance spot) | l'inverse |
| On-chain | flux net vers les exchanges < 0 en moyenne sur 30 jours (des bitcoins sortent) | > 0 |
| ETH/BTC | ETH/BTC > sa SMA 50 jours (appétit pour le risque) | < SMA 50 |

- **Score** = moyenne des 9 votes. **Investi si score ≥ 0,25** (au moins environ 6 votes haussiers contre 3), sinon
  hors marché.
- **Taille** = capital × min(1 ; 40 % ÷ volatilité annualisée des 30 derniers jours). Le bitcoin ayant une volatilité
  de 50 à 80 %, on est souvent investi à 50-80 % du capital, jamais à levier.
- Ordres passés au marché juste après 00:00 UTC.

Sans le dosage par la volatilité (tout ou rien) : Sharpe 1,13, +40 % par an, pire baisse −39 %, 138 entrées en 9 ans.

## Ce qu'il reste à décider ensemble

1. **Où l'exécuter.** Spot sur un exchange par un petit bot Python (les 9 votes sont disponibles par API : bougies et
   volume acheteur de Binance, on-chain de Coin Metrics), ou la version « prix seul » dans TradingView / MetaTrader en
   acceptant le swap du CFD.
2. **Bitcoin seul, ou bitcoin + Ethereum** (deux tiers / un tiers par exemple : les deux ne sont pas toujours investis
   en même temps).
3. **Avant tout argent réel** : faire tourner la stratégie en papier ou en démo plusieurs mois. La vérification
   2023-2026 a été regardée pour toutes les variantes ; seule une période vraiment nouvelle dira si l'avantage tient.

## Limites

- t de l'alpha de 2,5 en recherche et 1,3 en vérification BTC : un avantage plausible, pas démontré. Sur 9 ans le t est
  de 2,9 sur BTC et 2,65 sur ETH, mais ces chiffres mélangent recherche et vérification.
- La stratégie gagne surtout en évitant les krachs : il y en a eu deux en 9 ans (2018, 2022). Trois ou quatre décisions
  importantes font une grosse partie du résultat.
- Le choix des neuf outils vient de ta demande, mais l'idée que la tendance marche mieux que le retour à la moyenne sur
  le bitcoin est connue : la confluence « a priori » n'est pas totalement naïve.
- Données on-chain de Coin Metrics : elles peuvent être révisées après coup ; les valeurs testées sont celles
  d'aujourd'hui.
- Coûts de Binance supposés : 0,10 % par exécution en spot. Un autre exchange peut être plus cher.

## Refaire

```bash
bash crypto/00_telecharger.sh            # ≈ 15 min, 430 Mo dans crypto/donnees/ (hors git)
python crypto/recherche.py 4             # ≈ 2 min : sorties/variantes.csv.gz (42 400 lignes) et achat-conservation.csv
python crypto/confluence.py 1d           # sorties/confluence-1d.csv
python crypto/robustesse.py              # sorties/robustesse.txt
python crypto/signal_du_jour.py          # les 9 votes au dernier jour clôturé
```

Python 3 avec pandas et numpy ; Node.js pour Dukascopy (`npx dukascopy-node`).
