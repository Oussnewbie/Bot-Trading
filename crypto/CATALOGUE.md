# Catalogue des stratégies, indicateurs et méthodes — et ce qu'ils donnent sur BTC et ETH

État au 17 novembre 2026. Pour chaque ligne : ce que c'est, qui l'utilise, les données nécessaires, et le **résultat
mesuré ici** (Binance 2018-2026, frais compris, choix sur BTC 2018-2022, vérification sur BTC 2023-2026 et sur l'ETH).

Légende du verdict :
- ✅ **avantage qui tient** sur les trois échantillons ;
- 🟡 **faible ou instable** : positif quelque part, pas partout ;
- ❌ **ne marche pas** ici, ou fait moins bien que le hasard ;
- ⬜ **non testé**, avec la raison.

« t » désigne le t de l'alpha contre l'achat-conservation : au-dessus de 2, c'est sérieux ; autour de 0, c'est du hasard.
Les détails sont dans `RAPPORT.md` et `RAPPORT-2.md`.

## 1. Stratégies d'institution (fonds, CTA, desks)

| Stratégie | Principe | Données | Verdict ici |
|---|---|---|---|
| **Suivi de tendance / momentum temporel (CTA, managed futures)** | Acheter ce qui monte, sortir ou vendre ce qui baisse, sur des semaines | Prix | ✅ À l'achat, en journalier : Ichimoku, MACD, moyennes, Donchian. Le cœur de la confluence. 🟡 À la vente (voir §5) |
| **Ciblage de volatilité / parité de risque** | Taille inversement proportionnelle à la volatilité | Prix | ✅ Réduit la pire baisse sans coûter de rendement ajusté du risque (dosage à 40 %) |
| **Cash-and-carry (base, « carry » du financement)** | Acheter le comptant, vendre le perpétuel : on encaisse le financement payé par le levier | Spot, perpétuel, financement | ✅ +12 % par an sur BTC, +14 % sur ETH (2020-2026), mais +7 % par an sur 2023-2026. Pire baisse < 3 % hors risque d'exchange. Neutre au marché. Risques réels : faillite de l'exchange (FTX 2022), liquidation de la jambe courte, financement négatif |
| **Signal de « carry crash » (BRI 2023)** | Un financement très élevé annonce les krachs | Financement | 🟡 BTC : 42 % de risque d'une chute de 15 % en 30 jours, contre 27 % sinon (45 jours seulement). Pas sur l'ETH. Utile comme alerte, pas comme signal |
| **Momentum en coupe transversale** | Acheter les cryptos les plus fortes, vendre les plus faibles (Liu-Tsyvinski-Wu) | 20 à 100 cryptos | ⬜ Impossible avec deux actifs : il faut un univers de cryptos |
| **Arbitrage statistique / paires (ETH/BTC)** | Retour à la moyenne d'un ratio | ETHBTC | ❌ Retour à la moyenne : Sharpe −1,5 à 0 (le ratio est en tendance depuis 2022). 🟡 Suivre la tendance du ratio (MA50) : Sharpe 0,9 puis 0,5, pire baisse −75 % |
| **Prime de volatilité (vente d'options)** | La volatilité implicite dépasse en moyenne la réalisée : vendre des options rapporte en moyenne | DVOL, options Deribit | 🟡 DVOL BTC au-dessus de la volatilité réalisée ensuite 75 % du temps (+8 points en moyenne), avec des pertes extrêmes en krach (−51 points en avril 2021). Pas simulé : il faut les prix historiques des options |
| **Apprentissage automatique (gradient boosting)** | ~60 caractéristiques, réentraîné tous les 3 mois | Tout | ❌ Walk-forward 2020-2026 : t de −1,6 à +0,7 ; pire que la confluence. Seul résultat visible : la littérature n'y trouve d'avantage qu'en coupe transversale sur des centaines de cryptos |
| **Régimes (modèle de Markov caché)** | États « haussier / baissier » estimés | Prix | 🟡 2 états, achat seul : Sharpe 0,83 BTC, 0,90 ETH ; moins bien qu'une simple MA200 ou que la confluence |
| **Tenue de marché / haute fréquence** | Capturer l'écart achat-vente, arbitrage de latence | Carnet d'ordres, ticks, colocalisation | ⬜ Hors de portée : infrastructure et données tick |
| **Événements (FOMC, CPI, ETF, déblocages de jetons)** | Positionnement autour d'annonces | Calendrier macro | ⬜ Non testé : pas de calendrier fiable gratuit. Piste ouverte |
| **Flux des ETF bitcoin** | Suivre les entrées et sorties des ETF | Farside, SoSoValue (clé) | ⬜ Pas de données gratuites par API. La littérature dit que les flux suivent le prix (corrélation 0,54 avec la semaine passée, 0,09 avec le lendemain) |
| **Exécution TWAP / VWAP** | Exécuter un gros ordre sans faire bouger le prix | Volume intrajournalier | Outil d'exécution, pas de prévision. Inutile pour les tailles d'un particulier |

## 2. Liquidité et order flow (ICT / SMC, Wyckoff, profil de volume)

| Méthode | Principe | Verdict ici |
|---|---|---|
| **Order flow : delta, CVD** | Achats agressifs − ventes agressives (taker buy de Binance) | 🟡 Seul : t ≈ 0. En **vote** dans la confluence, c'est l'outil qui compte le plus sur BTC (sans lui, Sharpe 1,18 → 0,97). Divergences prix/CVD : ❌ |
| **Spot qui mène le perpétuel** | Achat « réel » contre achat à levier | ❌ t ≈ 0 |
| **Liquidity sweep / stop hunt (chasse au-dessus du plus haut de la veille ou de la semaine)** | Le prix va chercher les stops puis se retourne | ❌ À la vente : t de −0,7 à −1,2. 🟡 À l'achat (chasse sous le plus bas de la veille), t ≈ 1 partout. Le plus haut et le plus bas de la veille **cassent plus souvent** que le hasard : ce sont des aimants à stops, pas des murs |
| **Fair value gaps (FVG)** | Les trous de cotation se « comblent » et servent d'appui | ❌ Pas plus de rebonds que des niveaux témoins (écart −2 à +1 point) |
| **Order blocks** | Dernière bougie opposée avant une impulsion | ❌ Pas plus de rebonds que le hasard |
| **Structure : BOS / CHoCH** | Cassure du dernier pivot = changement de tendance | 🟡 t 1,4 / 0,8 / 1,65 : c'est du suivi de tendance (≈ Donchian) sous un autre nom |
| **Zones premium / discount, OTE 0,62-0,79** | Acheter « en discount » dans une tendance haussière | ❌ t −1,2 à −1,8 |
| **Profil de volume (POC, VAH/VAL, HVN, LVN)** | Les prix très traités attirent ou repoussent | ❌ Aucune méthode ne bat ses témoins (sur 30 et 90 jours) |
| **VWAP ancrés (mois, trimestre, sommets)** | Prix moyen pondéré depuis une date clé | ✅ Comme **vote de tendance** (au-dessus / en dessous). ❌ Comme niveau de rebond |
| **Wyckoff (accumulation, spring, upthrust)** | Faux cassage du bas d'un range puis reprise | 🟡 Le spring ≈ chasse sous le plus bas de la veille (voir plus haut) |
| **Carte de liquidations, murs du carnet d'ordres** | Où sont les ordres et les liquidations | ⬜ Pas d'historique gratuit (estimations de vendeurs) |
| **Footprint (delta par niveau de prix)** | Order flow au tick | ⬜ Possible avec les aggTrades de Binance (plusieurs centaines de Go) ; le delta par bougie n'a rien donné seul |
| **Sessions / killzones (Asie, Londres, New York)** | Heures de liquidité | ❌ Heures de tenue : t de −5 à −10 après frais |

## 3. Indicateurs et méthodes populaires

| Indicateur | Usage testé | Verdict ici |
|---|---|---|
| **Moyennes mobiles (SMA/EMA 20-200, croisements, golden cross)** | Prix au-dessus, croisements | ✅ En journalier (t médian 1,2 / 0,3 / 1,4) |
| **MA200** | Filtre de régime | ✅ Comme filtre et comme vote (sans elle, Sharpe 1,18 → 1,00) |
| **Ichimoku** | Nuage, tenkan/kijun, signal complet | ✅ Le meilleur indicateur seul (t médian 1,9 / 0,5 / 2,0). La **kijun et le nuage rejettent le prix qui remonte par-dessous** (sur les 4 échantillons) |
| **MACD** | Signal, zéro, histogramme | ✅ En journalier (1,2 / 0,8 / 1,7) |
| **DMI / ADX** | +DI contre −DI, ADX > 20-25 | 🟡 DMI : 2,3 / 1,1 / 2,7 ; c'est encore de la tendance |
| **Keltner, Bollinger : cassure** | Sortie du canal | 🟡 Keltner 1,8 / 1,0 / 1,6 |
| **Supertrend, Parabolic SAR, Heikin-Ashi** | Suivi de tendance | 🟡 / ❌ SAR et Heikin-Ashi ≈ 0 |
| **Donchian / Turtle, ensemble de Donchian (Zarattini)** | Cassure des plus hauts de N jours | 🟡 Seul ou en ensemble : bon en recherche, ≈ 0 en vérification BTC |
| **RSI** | 30/70, 50, replis, RSI 2 de Connors | ❌ Comme oscillateur (médiane −0,5). En **vote** (> 50) : utile |
| **Stochastique** | 20/80 et > 50 | ❌ 20/80 (t −0,7 à −1,8) ; 🟡 > 50 (momentum) |
| **Bollinger : retour** | Rachat sous la bande basse | ❌ |
| **Fibonacci (retracements 0,382-0,618, extensions)** | Achat sur repli, vente sur rebond | ❌ À l'achat. 🟡 **À la vente** dans une tendance baissière (rebond jusqu'au 0,5-0,618) : Sharpe propre 0,5-0,8 sur les trois échantillons, mais peu de trades. Comme niveau de rebond : ❌ |
| **Points pivots « floor » (P, R1, S1…)** | Niveaux du jour, de la semaine, du mois | ❌ Pas mieux que le hasard ; ceux du jour cassent plus souvent |
| **Chiffres ronds (10 000 $, 1 000 $…)** | Barrières psychologiques | ❌ Comme rebond : moins bien que le hasard (ils cassent). Comme accélération après franchissement (Osler) : pas mieux que des niveaux témoins |
| **Figures de bougies (englobante, marteau, étoile filante)** | Retournement sur 5 jours | ❌ t −3,1 en vérification BTC (englobante) |
| **Figures chartistes (épaule-tête-épaule, triangles, drapeaux)** | Reconnaissance visuelle | ⬜ Pas de définition algorithmique standard ; la littérature les trouve rarement rentables nettes de frais |
| **Vagues d'Elliott, harmoniques** | Comptage de vagues | ⬜ Subjectif, impossible à tester proprement |
| **Indicateurs de cycle : multiple de Mayer, Pi cycle, MA 200 semaines, stock-to-flow, halving** | Sommets et creux de cycle | ⬜ / 🟡 2 à 6 signaux en 9 ans : impossible à juger statistiquement |
| **Calendrier : week-end, lundi, heures** | Effets saisonniers | ❌ |

## 4. Sentiment, dérivés et on-chain

| Donnée | Usage testé | Verdict ici |
|---|---|---|
| **Fear & Greed** | Contrarien (acheter la peur), suiveur | ❌ Contrarien. 🟡 Suiveur (> 50) : 2,2 en recherche, −0,5 en vérification. ✅ Comme **filtre de vente** : vendre les rebonds de soulagement (F&G remonté à 45 ou plus) en régime baissier |
| **Prime Coinbase (demande américaine)** | > 0 : achat | 🟡 1,1 / 1,0 / 1,8 |
| **Prime du perpétuel, financement** | Contrarien, suiveur | ❌ Direction. 🟡 Risque de krach (voir carry crash) |
| **Open interest, ratio long/short des takers** | Confirmation, purge | ❌ |
| **DVOL (volatilité implicite)** | Régime de volatilité | ❌ Direction ; utile pour la taille |
| **Stablecoins (masse en circulation)** | Liquidité qui entre | 🟡 Accélération sur 30 jours : 1,4 / 1,0 / 1,4, peu de trades |
| **Flux des exchanges, réserves (on-chain)** | Sorties = achat | 🟡 Instable : gagnant en recherche, perdant en vérification. En vote : utile sur l'ETH |
| **MVRV, hash ribbons, adresses actives, frais** | Valorisation, mineurs, activité | 🟡 / ❌ Trop peu de signaux (MVRV : 2 en 5 ans) ou instable |
| **ETH/BTC** | Appétit pour le risque | ❌ Seul. 🟡 En vote : aide un peu le BTC |

## 5. Ventes à découvert : ce qui ressort

| Méthode | Résultat (BTC recherche / BTC vérification / ETH) |
|---|---|
| Inverser les signaux d'achat (long/short symétrique) | Moins bon que l'achat seul : le financement et les rebonds baissiers mangent le gain |
| 11 710 variantes en vente seule | 6 % ont un Sharpe propre positif sur les trois échantillons ; < 1 % au-dessus de 0,3 |
| **Vendre les rebonds de soulagement en tendance baissière** (régime SMA200 + 90 j, F&G remonté ≥ 45, clôture < EMA10) | Sharpe propre 0,55 / 0,54 sur BTC ; −0,07 en vérification ETH. Retenu en option dans le système, avec cette réserve |
| Rejet de la SMA20/SMA50 ou du nuage en tendance baissière (stops réels) | t ≈ 1 à 2, faible mais du bon côté |
| Fibonacci 0,5-0,618 vendu en tendance baissière | Sharpe propre 0,5-0,8, peu de trades |
| Vendre la cupidité, les pics de prime ou de financement, les chasses de liquidité | ❌ Perdants |

## Le croisement retenu

Ce qui tient se combine en **trois couches** :
1. **Direction à l'achat** : confluence de tendance en journalier (MA200, Ichimoku, MACD, RSI > 50, VWAP du mois,
   position dans la jambe de Fibonacci, order flow 7 j, flux on-chain, ETH/BTC).
2. **Vente** (option) : vendre les rebonds de soulagement en régime baissier strict.
3. **Gestion du risque** : dosage par la volatilité, alerte « carry crash ».

À côté, pour le capital qui attend : le **cash-and-carry**, qui rapporte le financement sans parier sur le prix.
