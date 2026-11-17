# Trader le BTC : la stratégie, une fois les biais corrigés — 17 novembre 2026

Document de référence pour le BTC seul. Les rapports précédents (`RAPPORT.md` à `RAPPORT-4.md`) racontent la
recherche ; celui-ci donne **ce qui reste quand on retire tout ce qui pouvait fausser le jugement**.

Ce n'est pas un conseil en investissement. Le passé ne garantit rien.

## En bref

- **La stratégie tient sur 2012-2017, cinq années jamais utilisées par la recherche** : Sharpe 2,71 contre 1,99 pour
  l'achat-conservation, pire baisse −25 % contre −85 %.
- **Elle bat l'achat-conservation et la MA200 seule pour toutes les dates de départ testées** (chaque trimestre de 2013
  à 2024). Le rééchantillonnage donne 100 % et 99 % de probabilité qu'elle ait un meilleur Sharpe que ces deux
  références.
- **Le résultat ne vient pas d'un réglage chanceux** : les 135 réglages de la grille battent tous l'achat-conservation
  (Sharpe 1,41 à 1,98 contre 1,23). Choisis automatiquement chaque année avec le passé seul, ils font aussi bien que
  le réglage retenu.
- **Aucun regard vers le futur** : recalculée à 40 instants au hasard avec les seules données connues à cet instant,
  la position est identique au calcul complet.
- **Ce qu'elle n'est pas** : un moyen de gagner plus que l'achat-conservation pendant les grandes hausses. Elle gagne
  plus que l'achat-conservation pour 42 % des dates de départ seulement. **Son avantage, c'est de diviser la pire
  baisse par trois à quatre.** Avec un levier mesuré, on peut transformer cet avantage en rendement (voir § 4).

## 1. Les biais, et comment ils ont été corrigés (`btc.py`, `btc_biais.py`, `sorties/btc-biais.txt`)

| Biais | Correction | Résultat |
|---|---|---|
| **Choix faits après avoir vu les données** | Walk-forward : chaque 1er janvier, le meilleur réglage sur le passé seul (parmi 135) est appliqué à l'année suivante. Plus aucun choix humain | 2014-2026 hors échantillon : Sharpe 1,44, pire baisse −17 %. Le réglage fixe fait 1,47 et −22 % ; l'achat-conservation 0,86 et −83 % |
| **Trop peu de cycles** (2 krachs en 2018-2026) | Prix Bitstamp depuis 2011 : 2012-2017 ajoute le krach de 2013-2015 (−85 %) et celui de 2014 | Sur ces années jamais vues : Sharpe 2,71 (achat-conservation 1,99, MA200 2,39), pire baisse −25 % |
| **Complexité inutile** | Comparaison avec des règles simples | Le système bat la MA200 seule (Sharpe 1,47 sur 2012-2026) et le croisement EMA 50/200 (1,35) sur chaque période. La confluence seule fait déjà 1,80 ; la confirmation 4h et la vente ajoutent un peu (1,89) |
| **Surajustement de la grille** | Probabilité de surajustement (PBO, CSCV sur 16 blocs) ; plateau des réglages voisins | PBO 17 % : choisir « le meilleur » réglage n'apporte pas grand-chose, mais **tous** les réglages gagnent. Les seuils de 0,15 à 0,5 donnent tous un Sharpe de 1,81 à 1,93 |
| **Chance** | Rééchantillonnage par blocs de 20 jours (2 000 tirages) | Sharpe 1,35 à 2,44 (intervalle à 90 %), pire baisse −26 % à −48 %. Achat-conservation : Sharpe 0,74 à 1,73, pire baisse −69 % à −94 % |
| **Date de départ** | Départ chaque trimestre de 2013 à 2024 | Meilleur Sharpe que l'achat-conservation et la MA200 dans 100 % des cas ; pire baisse toujours ≈ −21 à −25 % |
| **Frais** | × 0,5 à × 3 | Frais triplés : Sharpe 1,55 sur 2012-2026, 0,99 sur 2018-2026 (achat-conservation 0,60) |
| **Regard vers le futur** | Recalcul à 40 instants au hasard avec les données tronquées | Écart de position : 0 |
| **Bougie non clôturée en direct** | `btc_jour.py` retire la bougie en cours | Corrigé |

**Ce que les tests ont changé dans mon jugement :**
- **La vente à quart de taille est neutre sur l'historique long** : Sharpe médian 1,77 sans vente, 1,74 à 0,25, 1,62
  à 0,5. Sur 2018-2026 elle aidait un peu ; sur 2012-2017 non. Le walk-forward la choisit 3 années sur 13. Elle reste
  **optionnelle** : elle rapporte pendant les années baissières mais ne change pas le rapport gain/risque.
- **La confirmation 4h par l'EMA 50/200 est la meilleure des trois** (Sharpe médian 1,82, contre 1,71 sans
  confirmation et 1,67 avec l'EMA 20/50).
- **Un seuil plus strict (0,5) fait aussi bien ou un peu mieux que 0,25** : le walk-forward le choisit chaque année.
  La différence est dans le bruit.

## 2. Ce qui reste incertain (et ne peut pas être corrigé par un test)

- **Le BTC change** : marché de détail en 2013, institutionnel avec les ETF depuis 2024. Les mouvements sont moins
  extrêmes et l'avantage diminue : Sharpe 2,71 en 2012-2017, 1,27 en 2018-2026, environ 1,1 pour un départ en 2023.
- **Discrétionnaire et événements** (régulation, faillites d'exchanges, ETF) : hors du système.
- **Seule une période vraiment nouvelle** dira si l'avantage tient : d'où la démo.

## 3. La stratégie

**À chaque clôture journalière (00:00 UTC), 9 votes :**
- **MA200** : prix au-dessus ou en dessous de la moyenne 200 jours ;
- **Ichimoku 9-26-52** : au-dessus du nuage, en dessous, ou dedans (vote 0) ;
- **MACD 12-26-9** : au-dessus ou en dessous de sa ligne de signal ;
- **RSI 14** : au-dessus ou en dessous de 50 ;
- **VWAP du mois** : prix au-dessus ou en dessous du VWAP ancré au 1er du mois ;
- **Fibonacci 90 jours** : au-dessus du 0,618 de la jambe ou sous le 0,382 (vote 0 entre les deux) ;
- **Order flow 7 jours** (Binance) : achats agressifs supérieurs ou inférieurs aux ventes agressives ;
- **On-chain 30 jours** : bitcoins qui sortent des exchanges ou qui y entrent ;
- **ETH/BTC** : au-dessus ou en dessous de sa SMA 50 jours.

**Score** = moyenne des votes disponibles.

**À chaque clôture 4h** (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC) :

| Condition | Action |
|---|---|
| Score ≥ +0,25 ET en 4h EMA50 > EMA200 et prix > EMA200 | **ACHAT** |
| Score ≤ −0,25 ET en 4h EMA50 < EMA200 et prix < EMA200 | **VENTE** à un quart de la taille (optionnelle) |
| Sinon | **Rien** (stablecoins) |

**Taille** = capital × min(plafond ; volatilité cible ÷ volatilité du BTC sur 30 jours).

## 4. Choisir son profil de risque (2012-2026, coût d'emprunt du levier compris)

| Profil | Volatilité cible / plafond | Sharpe | Gain par an 2018-2026 | Pire baisse |
|---|---|---|---|---|
| Achat-conservation | — | 0,60 (2018-26) | +19 % | −81 % |
| **Prudent** (par défaut) | 40 % / 1× (sans levier) | 1,89 | +34 % | −25 % |
| Équilibré | 60 % / 1× | 1,80 | +40 % | −32 % |
| **Dynamique** | 60 % / 2× | 1,90 | +57 % | −38 % |
| Agressif | 80 % / 2× | 1,84 | +66 % | −46 % |

- Le Sharpe reste à peu près le même : **le profil ne change pas la qualité de la stratégie, seulement la
  quantité de risque prise.**
- Le profil « dynamique » rapporte environ trois fois plus que l'achat-conservation sur 2018-2026, avec une pire
  baisse deux fois plus petite.
- **Le levier ajoute des risques que le test ne voit pas** : krach éclair qui saute le stop, liquidation, faillite de
  l'exchange.
- **Règle de prudence** : commencer en « prudent », passer au-dessus seulement après plusieurs mois de démo conformes
  au test.

## 5. Utilisation

```bash
python recherches/crypto/btc_jour.py                          # profil prudent
python recherches/crypto/btc_jour.py --vol 0.6 --plafond 2    # profil dynamique
python recherches/crypto/btc_jour.py --vente 0                # sans vente
```

Au 17 novembre 2026, bougie 4h de 04:00 UTC : 8 votes baissiers sur 9 (score −0,78), tendance 4h baissière →
**vente de 23 % du capital** en profil prudent (34 % en dynamique), ou rien si la vente est désactivée.

**Mise à jour des données** :
- `python recherches/crypto/05_telecharger_btc_historique.py --maj` : prix Bitstamp et on-chain ;
- les fichiers Binance (order flow, ETH/BTC) se mettent à jour avec `00_telecharger.sh`. S'ils manquent, ces deux
  votes sont absents et le score se calcule sur 7 votes.

**Pour refaire les tests** : `python recherches/crypto/btc_biais.py` (≈ 1 min).
