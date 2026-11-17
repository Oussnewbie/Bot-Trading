# Deuxième passe : ventes, supports et résistances, sentiment, apprentissage, institutionnel — 17 novembre 2026

Suite de `RAPPORT.md`. Le catalogue complet des stratégies et indicateurs, avec le verdict de chacun, est dans
`CATALOGUE.md`. Mêmes règles : décision à la clôture, frais et financement réels, choix sur BTC 2018-2022,
vérification sur BTC 2023-2026 et sur l'ETH. Environ **80 000 évaluations** en tout.

Ce n'est pas un conseil en investissement, et le passé ne garantit rien.

## En bref

1. **Les ventes à découvert sont structurellement difficiles sur BTC et ETH.** La littérature le dit aussi : le
   momentum crypto gagne surtout à l'achat (Han-Kang-Ryu ; thèse Wisselink ; Liu-Tsyvinski). Sur 11 710 variantes
   jouées en vente seule, 6 % ont un rendement propre positif sur les trois échantillons. Une seule idée tient un peu :
   **vendre les rebonds de soulagement dans une tendance baissière**. Elle est ajoutée en option au système.
2. **Supports et résistances : aucune méthode ne fait rebondir le prix plus souvent que des niveaux pris au hasard.**
   Le test suit le protocole d'Osler (Fed de New York, 2000) : 29 méthodes, deux témoins décalés pour chaque niveau.
   - Le plus haut et le plus bas de la veille, les pivots du jour et les chiffres ronds **cassent plus souvent** que le
     hasard : ce sont des zones de stops.
   - Seuls la kijun et le nuage Ichimoku ont un comportement régulier, et il est baissier : ils rejettent le prix qui
     remonte par-dessous et ne tiennent pas comme support.
3. **Sentiment, dérivés et on-chain** servent comme filtres, pas comme signaux :
   - Fear & Greed pour choisir le moment d'une vente ;
   - le financement pour alerter d'un risque de krach (BTC seulement) ;
   - la prime Coinbase et les stablecoins donnent un faible plus.
4. **L'apprentissage automatique (LightGBM en walk-forward) et les modèles de régimes (HMM) font moins bien** que la
   confluence simple.
5. **La seule stratégie qui rapporte presque sans risque de marché est institutionnelle : le cash-and-carry**. On
   achète le comptant, on vend le perpétuel et on encaisse le financement : +12 % par an sur BTC depuis 2020, +7 % sur
   2023-2026. Le risque est celui de l'exchange, pas celui du prix.
6. **L'outil** : `python crypto/systeme.py --jour` donne chaque jour, pour BTC et ETH :
   - les 9 votes, le score et la décision (achat, vente ou rien) avec sa taille ;
   - le régime, l'alerte de krach, le sentiment ;
   - les niveaux proches, à titre d'information.

## 1. Les ventes

**Pourquoi c'est dur.** Le bitcoin a pris ×15 depuis 2017. Ses baisses sont rares (2018, 2022), et elles sont coupées
de rebonds de 20 à 40 % qui déclenchent les stops des vendeurs. Un vendeur sur perpétuel paie en plus le financement
quand il est négatif, c'est-à-dire justement quand tout le monde vend.

| Test | Résultat |
|---|---|
| Toutes les variantes de la grille en **vente seule** (`variantes-court.csv.gz`) | Sharpe propre médian négatif en vérification pour **toutes** les familles. 6,3 % positifs sur les trois échantillons, 0,8 % au-dessus de 0,3 |
| **104 setups précis avec stops réels** (`evenements.py`), heure par heure : rejet de la kijun, du nuage, de la SMA20/50 ou du VWAP du dernier sommet ; retest d'un support cassé ; cassure du plus bas de 20 jours ; chasse au-dessus du plus haut de la veille ou de la semaine ; RSI ; pics de prime ; cupidité ; prime Coinbase qui devient négative ; dans 4 régimes ; 6 sorties | Meilleurs : rejet de la SMA20, objectif 1,5R (t 1,55 / 1,05 / 1,43, +0,6 à +1,5 % par trade) ; rejet de la SMA50 en régime baissier (1,97 / 0,90 / 1,56). **Perdants** : vendre la cupidité (t −1,2 à −1,7), les pics de prime, les chasses de liquidité |
| Long/short symétrique de la confluence | Sharpe BTC 0,96 contre 1,18 en achat seul : la vente fait baisser le résultat |
| Ensemble de Donchian (Zarattini) en vente | ≈ 0 |
| Vente de tendance baissière (régime SMA200 en baisse + 90 j négatif, plus bas de 20 jours) | Sharpe propre 0,21 sur BTC 2018-2026 |
| … **en vendant les rebonds de soulagement** (Fear & Greed remonté à 45 ou plus en 5 jours, clôture < EMA10) | **0,57 / 0,60** sur BTC ; 1,08 puis 0,00 sur ETH |
| … avec en plus la prime Coinbase 7 j < 0 | 0,25 / 0,48 sur BTC |
| Alerte « carry crash » (BRI) : vendre 10 jours | ❌ Négatif |

**Module de vente retenu** (option) :
- **Régime** : clôture < SMA200, SMA200 en baisse sur 20 jours, rendement 90 jours < 0, score de confluence ≤ −0,25.
- **Entrée** : Fear & Greed remonté à 45 ou plus dans les 5 derniers jours, puis clôture sous l'EMA10. Pas de vente si
  le financement 3 jours est sous −0,01 % (ventes déjà encombrées).
- **Sortie** : au-dessus du plus haut de 10 jours ou de la SMA50.

Résultat :
- BTC : Sharpe propre 0,55 en recherche et 0,54 en vérification, exposé 2 % du temps.
- ETH : 1,04 puis −0,07.
- Ajouté à l'achat, il laisse le Sharpe BTC à 1,18 et monte le rendement de 31 à 33 % par an.

**Réserve** : ce module a été construit après avoir vu les résultats sur toutes les périodes. Sa vérification n'est
pas propre ; il faut le juger en démo.

## 2. Supports et résistances (`niveaux.py`, `test_niveaux.py`)

**Méthode (Osler 2000, adaptée au journalier).** Chaque jour à 00:00 UTC, chaque méthode donne ses niveaux, calculés
avec le passé seulement. Le lendemain, en 1h :
- une **touche** : le prix atteint le niveau par-dessus (support) ou par-dessous (résistance) ;
- un **rebond** : le prix repart de 0,5 ou 1 ATR journalier dans le sens du rejet avant de clôturer 0,5 ou 1 ATR
  de l'autre côté ;
- **témoins** : les mêmes niveaux décalés de ±1,5 ATR. Un niveau ne vaut que s'il fait mieux que ses témoins.

**29 méthodes** :
- pivots fractals 3/5/10 jours, avec 1, 2 ou 3 touches ;
- densité des pivots (KDE) ;
- plus haut et plus bas de la veille, de la semaine et du mois ;
- profil de volume 30/90 jours (POC, zone de valeur, HVN, LVN) ;
- VWAP ancrés aux pivots ;
- moyennes 20-200 ;
- kijun et nuage Ichimoku ;
- Fibonacci 90 jours ;
- chiffres ronds ;
- **fair value gaps** et **order blocks** (ICT) ;
- points pivots « floor » du jour, de la semaine et du mois.

**Résultat.** Le prix « rebondit » environ 55 % du temps, sur les vrais niveaux **comme sur les faux**. Aucune méthode
n'a d'écart positif régulier sur les quatre échantillons (BTC et ETH, recherche et vérification).

| Méthode | Écart de rebond avec les témoins | Lecture |
|---|---|---|
| Plus haut / plus bas de la veille | −5,4 et −6,6 points en recherche (z −3,1 et −3,9) | **Cassent plus souvent** : les stops y sont |
| Pivots « floor » du jour | z −2,4 (BTC), −4,0 (ETH) | Idem |
| Chiffres ronds BTC (1 000, 5 000, 10 000 $) | −2 à −6,5 points dans les deux périodes | Cassent plus souvent (ETH : mélangé) |
| POC du profil de volume 90 j | −8,7 points (BTC recherche), puis ≈ 0 | Rien |
| FVG, order blocks | −2,6 à +1,3 point | Rien |
| Pivots avec 2-3 touches | −0,6 à +2 points, z < 1 | Rien de significatif |
| **Kijun et nuage Ichimoku** (mouvement de 1 ATR) | Par-dessous : 55-60 % de rejets contre 47-52 % pour les témoins (z +1,1 à +3,7). Par-dessus : 44-56 % de rebonds contre 57-58 % (z −0,5 à −4,0) | Le nuage **repousse le prix qui remonte** et **ne tient pas comme support**, sur BTC et ETH, dans les deux périodes |

**Comment détecter un support ou une résistance, alors ?** Les niveaux « classiques » ne sont pas des murs : ce sont
des **zones où se trouvent les ordres** (stops et prises de bénéfice). Le prix y va souvent et les traverse plus
souvent qu'il ne rebondit. C'est ce qu'Osler a trouvé sur le forex (2003) : les prises de bénéfice se groupent sur les
chiffres ronds, les stops juste derrière, et le mouvement accélère une fois le niveau franchi. En pratique :
- un niveau sert à **placer un stop** (au-delà de la zone de stops, pas dedans) et à **savoir où le prix ira
  chercher la liquidité**, pas à acheter « parce que c'est un support » ;
- le seul niveau qui a un comportement mesurable ici est **le nuage Ichimoku vu par-dessous**. Il sert à la vente :
  le rejet du nuage fait partie des setups de vente les moins mauvais.

## 3. Les nouvelles données (`01_telecharger_extra.py`)

Toutes gratuites, sans clé :
- prime des perpétuels (Binance) ;
- bougies Coinbase BTC-USD et ETH-USD (prime Coinbase = demande américaine au comptant) ;
- Fear & Greed (2018 →) ;
- DVOL de Deribit (2021 →) ;
- masse des stablecoins (DefiLlama).

| Famille « sentiment » | Meilleur résultat (t BTC recherche / BTC vérification / ETH) |
|---|---|
| Fear & Greed > 50 (suiveur) | 2,2 / −0,5 / 2,3 |
| Fear & Greed contrarien (acheter la peur extrême) | ❌ (−0,8 à −1,4 en recherche) |
| Prime Coinbase 7 j > 0 | 1,1 / 1,0 / 1,8 |
| Stablecoins : accélération sur 30 j | 1,4 / 1,0 / 1,4 (peu de trades) |
| Prime perp contrarienne | 1,5 / −0,4 / −1,0 |
| DVOL | ❌ En direction |

**Alerte « carry crash »** (Schmeling-Schrimpf-Todorov, BRI 2023) : financement moyen 7 jours dans les 10 % les plus
hauts de l'année ET clôture sous l'EMA20.
- **BTC** : probabilité d'une chute de 15 % dans les 30 jours de 42 % contre 27 % le reste du temps. Seulement 45
  jours de signal en 9 ans.
- **ETH** : rien.
- Couper les achats de la confluence quand elle s'allume ne change rien. C'est une alerte, pas un signal.

## 4. Apprentissage automatique et régimes (`apprentissage.py`)

- **LightGBM**, ~60 caractéristiques (votes, distances aux moyennes, RSI, MACD, volatilité, order flow spot et perp,
  financement, primes, Fear & Greed, DVOL, stablecoins, on-chain, ETH/BTC). Il prédit le signe du rendement à 5
  jours et est réentraîné tous les 3 mois sur le passé seulement.
  - Sharpe de −0,9 à +0,7 selon le seuil et l'actif, t de l'alpha entre −2,1 et +0,7. Pire que la confluence, et pire que l'achat-conservation.
  - Utilisé pour filtrer la confluence, il la dégrade (Sharpe 1,18 → 0,60).
- **HMM gaussien** (probabilités filtrées, sans regard vers le futur, réestimé chaque année) :
  - 2 états, achat seul : Sharpe 0,83 (BTC) et 0,90 (ETH), avec une pire baisse de −71 % et −75 % ;
  - 3 états : moins bien.
- C'est conforme à la littérature : l'apprentissage ne gagne de façon reproductible qu'en coupe transversale sur des
  centaines de cryptos, et les HMM ne battent pas une simple MA200 une fois les frais payés.

## 5. Hypothèses de la littérature (`hypotheses.py`)

| Hypothèse | Résultat |
|---|---|
| Chiffres ronds : le mouvement continue après franchissement (Osler) | ❌ Pas mieux que des niveaux témoins (rang 17/21 et 6/21 sur BTC) |
| Ensemble de Donchian 10-160 jours (Zarattini-Pagani-Barbon) | Recherche : Sharpe 0,99 (BTC), 1,12 (ETH). Vérification : 0,33 et 0,23. Moins bien que la confluence ; les mélanger n'aide pas |
| Heure de décision 20, 21, 22 ou 23 h UTC au lieu de minuit | Sharpe BTC 1,06 à 1,21, ETH 1,00 à 1,10 : **la confluence ne dépend pas de l'heure** (bonne nouvelle pour la robustesse ; pas de gain à 22 h) |

## 6. Stratégies d'institution (`institutionnel.py`)

**Cash-and-carry.** On achète 1 BTC au comptant et on vend 1 BTC en perpétuel : le prix ne compte plus, on encaisse le
financement (11,6 % par an en moyenne sur BTC, 13,6 % sur ETH, 2020-2026).

| | 2020-2022 | 2023-2026 | 2020-2026 | Pire baisse |
|---|---|---|---|---|
| BTC, toujours investi | +18,5 % par an | +7,3 % | +12,1 % | −2,5 % |
| ETH, toujours investi | +23,5 % | +7,4 % | +14,1 % | −1,8 % |
| BTC, seulement si financement 7 j > 0 | +16,2 % | +5,8 % | +10,2 % | −2,7 % |

Le rendement baisse avec le temps (plus de capital fait ce trade : ETF, Ethena…). Ce que le test ne montre pas :
- la faillite de l'exchange (FTX, novembre 2022) ;
- la liquidation de la jambe courte si le prix double sans marge suffisante ;
- le capital immobilisé (comptant + marge du perpétuel) : rapporté au capital total, le rendement est plus bas,
  sauf si l'exchange accepte le comptant comme garantie (« portfolio margin »).

**Paire ETH/BTC** :
- retour à la moyenne du ratio : ❌ Sharpe −1,5 à 0 ;
- suivre sa tendance (MA50) : Sharpe 0,9 puis 0,5, avec une pire baisse de −75 %.

**Prime de volatilité** : la DVOL de BTC est au-dessus de la volatilité réalisée ensuite 75 % du temps, de 8 points en
moyenne, mais elle a été 51 points en dessous en avril 2021. Vendre des options rapporte en moyenne et perd beaucoup
en krach. Pas simulé : il faudrait les prix historiques des options Deribit (payants).

## 7. Le système et l'outil (`systeme.py`)

| 2018-2026 | Sharpe | Gain par an | Pire baisse | Temps investi |
|---|---|---|---|---|
| BTC achat seul (confluence, spot) | 1,18 | +31 % | −28 % | 28 % |
| BTC achat + module de vente (perp) | 1,18 | +33 % | −30 % | 30 % |
| ETH achat seul | 1,05 | +28 % | −31 % | 21 % |
| ETH achat + vente | 1,07 | +32 % | −37 % | 25 % |
| Achat-conservation BTC / ETH | 0,60 / 0,55 | +19 % / +11 % | −81 % / −94 % | 100 % |

**Sharpe « dégonflé »** (Bailey et López de Prado), sur l'alpha de l'achat BTC. C'est la probabilité que l'avantage
soit réel compte tenu du nombre d'essais :
- 100 % si c'était le seul essai ;
- 90 % pour 15 essais (la confluence et ses variantes de seuil et de dosage) ;
- 42 % pour 1 000 essais ;
- 11 % pour 70 000 (toute l'étude).

La confluence a été définie avant de voir la grille, donc 15 est le chiffre honnête. Mais l'idée de « tendance » a pu
venir de ce qu'on sait du bitcoin. ETH : 82 % pour 15 essais.

**Le tableau du jour** (`python crypto/systeme.py --jour`), bougie du 16 novembre 2026 :

```
BTC — clôture 64 883 $ : 8 votes baissiers sur 9 (seul l'on-chain est haussier), score −0,78 → HORS MARCHÉ.
  Régime baissier strict : non (la SMA200 ne baisse pas encore assez). Fear & Greed 10 (peur extrême) :
  la vente attend un rebond de soulagement (F&G ≥ 45). Alerte « carry crash » : OUI (financement +11 %/an,
  prix sous l'EMA20).
ETH — clôture 1 821 $ : même score, régime baissier strict : oui, vente en attente d'un rebond de soulagement.
```

## Ce qui reste ouvert

- **Données payantes ou lourdes** :
  - options historiques (vraie simulation de vente de volatilité) ;
  - liquidations et carnet d'ordres ;
  - aggTrades de Binance (footprint) ;
  - flux des ETF.
- **Momentum en coupe transversale** sur 20 à 50 cryptos : c'est là que la littérature trouve le plus fort avantage, à
  l'achat comme à la vente. Il faut élargir l'univers (Binance publie toutes les paires).
- **Événements macro** (FOMC, CPI) : pas encore testés.
- **Démo** : seule une période nouvelle dira si la confluence et le module de vente tiennent.

## Refaire

```bash
python crypto/01_telecharger_extra.py          # 1 min : prime perp, Coinbase, Fear & Greed, DVOL, stablecoins
python crypto/recherche.py 4                   # grille achat / achat-vente (49 840 lignes)
MODES=court SUFFIXE=-court python crypto/recherche.py 4    # grille vente seule (24 920 lignes)
python crypto/test_niveaux.py 4                # supports et résistances (≈ 25 min)
python crypto/test_niveaux.py --supp           # FVG, order blocks, pivots classiques
python crypto/evenements.py                    # setups à stops réels
python crypto/apprentissage.py                 # LightGBM, HMM, achat + vente
python crypto/hypotheses.py                    # hypothèses de la littérature
python crypto/institutionnel.py                # cash-and-carry, paire ETH/BTC, prime de volatilité
python crypto/systeme.py                       # le système, le Sharpe dégonflé et le tableau du jour
python crypto/systeme.py --jour                # le tableau du jour seul
```

Bibliothèques en plus de pandas et numpy : `scipy`, `lightgbm`, `hmmlearn` (`pip install scipy lightgbm hmmlearn`).

## Sources principales

- Osler (2000), *Support for Resistance*, FRBNY Economic Policy Review ; Osler (2003), Journal of Finance.
- Liu et Tsyvinski (2021), *Risks and Returns of Cryptocurrency*, RFS ; Liu, Tsyvinski et Wu (2022), JF.
- Han, Kang et Ryu, *Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market* (momentum surtout en
  marché haussier).
- Schmeling, Schrimpf et Todorov (2023), *Crypto Carry*, BIS Working Paper 1087.
- Zarattini, Pagani et Barbon (2025), *Catching Crypto Trends*, SSRN 5209907.
- Hudson et Urquhart (2021), Annals of Operations Research ; Gerritsen et al. (2020), Finance Research Letters.
- Fonseca, Pacheco et Lobão (2019) ; Lee et Seong (2019) : barrières psychologiques du bitcoin.
- Bailey et López de Prado (2014), *The Deflated Sharpe Ratio*.
