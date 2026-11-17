# Revue indépendante : ORB v6 (Nasdaq) et bot BTC

Revue du 17 novembre 2026, sur la branche `claude/cool-galileo-hzgjdo`. Le code des bots n'a pas été modifié.

## Verdict en une page

| Bot | Avantage après coûts | Pourquoi |
|---|---|---|
| **ORB v6, Nasdaq** | **Douteux** | Positif sur 2018-2026 tant que le glissement reste sous ~2 à 3 points par ordre stop. Mais le seul test hors échantillon dont on ait trace (avant 2018, chiffres du développeur, non vérifiés ici) est **négatif**. Le gain repose sur ~2 % des trades, et il disparaît vers 5 points de glissement. |
| **Bot BTC ×1** | **Douteux, plutôt plausible** pour la stratégie ; **le code d'exécution n'est pas prêt** | Il bat nettement achat-et-garde et MA200 en risque (pire baisse −22 % contre −81 % et −68 %). Mais ce gain vient du suivi de tendance et du dosage par la volatilité, pas des 9 votes : une simple EMA50/200 4h dosée fait presque aussi bien (Sharpe 1,12 contre 1,25, écart non significatif). Le réglage est 4e sur 135 de sa propre grille. **Avec la version actuelle de ccxt, le transfert vers les futures est mal formé** : la vente ne peut jamais s'ouvrir, et le testnet décrit dans LISEZMOI est impossible (partie A4). |
| **Bot BTC ×2 à ×10** | **Absent en pratique** | Les chiffres de levier affichés (`profils.json`) ignorent le coupe-circuit à −40 % du bot. Avec lui, ×2 lancé en 2018 s'arrête pour toujours en février 2020, et ×3 et au-delà encore plus tôt. |

Hors échantillon après le 13 novembre 2026 :
- **Nasdaq** : aucune donnée. Le fichier Dukascopy s'arrête le 13/11/2026 à 16:14 New York.
- **BTC** : 4 jours (+0,99 % contre −3,96 % pour achat-et-garde). C'est sans valeur statistique.

**Le vrai test hors échantillon reste donc à faire, en démo.**

## Sources et méthode

**Nasdaq**
- **Données** : NAS100 CFD Dukascopy, M1 bid et ask, du 2 janvier 2018 au 13 novembre 2026 (`git archive afb79de donnees/nas100`). C'est la seule lecture de l'historique git.
- **Avant 2018 : pas de données.** `datafeed.dukascopy.com` a répondu « 429 Too Many Requests » puis coupé les connexions, en renvoyant vers sa page d'export. Le test n'a donc **pas pu être fait**. `revue/LISEZMOI.md` dit comment le lancer avec des fichiers téléchargés à la main.

**BTC**, téléchargé pour la revue, sans clé :
- Bitstamp, API v2/ohlc : 1d et 4h, 2011-08 → 17/11/2026 ;
- Coin Metrics, API communautaire : FlowInExNtv et FlowOutExNtv ;
- data.binance.vision : 1h BTCUSDT et ETHBTC (2017-08 →), financement BTCUSDT (2020-01 → 2026-10).

**Backtests écrits pour la revue**
- **Nasdaq** (`revue/orb.py`) : écrit à partir des seules règles du README, sur le modèle « EA » décrit par le README.
  - Graphique au bid. Achat déclenché par l'ask, vente par le bid.
  - Stops côté opposé. Simulation à la minute.
- **Seconde implémentation** (`revue/croise/`) : écrite séparément par un autre agent, qui n'avait accès ni à mon code ni au code des bots. Elle retrouve **exactement les mêmes 1 391 trades, avec le même R à 0,01 près**.
- **BTC** (`revue/btc_backtest.py`) : les décisions viennent de `bitcoin/btc.py` (`btc.elements` + `btc.position`, ce qu'applique `strategie.decider`). Les rendements sont recalculés par une comptabilité de compte :
  - bande de 5 % ;
  - exposition qui dérive avec le prix ;
  - frais comptant et perpétuel ;
  - financement payé par la position détenue à 00:00, 08:00 et 16:00 UTC ;
  - coupe-circuit ;
  - levier, avec stop et liquidation.

**Ordre de travail.** `etrave/reference.json`, `bitcoin/profils.json`, les textes de `etrave/page.html` et les constantes de `etrave/risque.py` n'ont été ouverts qu'**après** mes résultats (partie D).

---

## A. Revue du code

### Méthode

- **Lecture.** Six lecteurs indépendants, un par domaine :
  - l'EA comparé aux règles ;
  - l'EA, compilation et exécution ;
  - le script Pine ;
  - la stratégie BTC et son backtest ;
  - l'exécution du bot BTC chez Binance ;
  - Étrave.
- **Vérification.** Un vérificateur par domaine devait **réfuter** chaque constat en relisant le code. Résultat :
  - 135 constats : 115 confirmés, 19 plausibles, **1 seul réfuté** ;
  - 24 oublis ajoutés par les vérificateurs.
- **Contrôles à la main.** J'ai refait moi-même les points marqués ★, dans le code et dans ccxt 4.5.93, la version actuelle.
- **La liste complète**, avec les preuves, est dans [revue_code_complete.md](revue_code_complete.md).

Les **62 tests du dépôt passent** (`python -m pytest`, avec les données que j'ai téléchargées). Mais :
- aucun ne fait d'appel ccxt réel ;
- l'un d'eux exige un Sharpe supérieur à 1 sur la période déjà vue (`bitcoin/test_bot.py`).

Un test qui passe ne prouve donc ni que l'exécution marche, ni que la stratégie a un avantage.

### A1. Regards vers le futur

**Nasdaq : aucun trouvé dans les règles ni dans l'EA.**
- Le range, le RSI (bougie de 9:30 clôturée) et la fenêtre de l'élan sont tous connus à 9:35.
- Mes deux backtests indépendants et `reference.json` donnent les mêmes 1 391 jours de trade.
- Un risque d'exécution est **plausible** (EA-04, non prouvé) : au premier tick de 9:35, le RSI est lu sans vérifier que l'indicateur a fini de calculer la bougie. Il pourrait alors lire le RSI de 9:25.

**BTC : pas de décalage des prix vers le futur.**
- `btc.caler` et `btc.tronquer` décalent correctement les données.
- Le score journalier n'est même utilisé qu'avec 4 heures de retard.

Deux sources d'écart avec le réel :
- **Coin Metrics** (BTC-01). Le fichier historique contient des flux révisés. Le bot, lui, reçoit des valeurs « flash » : j'ai vu le statut `flash` sur les données de novembre 2026. L'effet est probablement borné, puisque retirer complètement ce vote ne fait passer le Sharpe que de 1,25 à 1,19.
- **Bitstamp contre Binance.** Même sens dans 98,5 % des cas (voir partie C).

### A2. Écarts entre l'EA, le script Pine et les règles écrites

| Point | Règle (README) | EA | Script Pine |
|---|---|---|---|
| Achat | sur le high du range | ask ≥ high bid : 4,9 % des jours, l'ask est déjà au-dessus à 9:35, d'où un achat au marché immédiat ; 2,6 % des jours, des trades que le prix bid ne déclenche jamais (EA-05). Inclus dans mon backtest, qui modélise l'EA. | prix du graphique |
| Côté bloqué et cassure dans la même bougie | pas de trade | contrôlé tick par tick | **non respecté** : le côté bloqué n'est vu qu'à la clôture (PINE-02) |
| Élan | « dépasse » (>) | `>=` | `>=`. Effet nul sur 2018-2026 dans mon test. |
| Stop à l'entrée à +1,5R | à la clôture d'une bougie après l'entrée | mesuré sur l'ask pour une vente | sur le plus haut ou le plus bas, exécuté au prix de clôture (optimiste) |
| Pyramide | +2R à la clôture | ajout au tick suivant, stop sans plancher : le pire cas −1R n'est **pas garanti** (EA-07, EA-10) | ajout au prix de clôture qui l'a déclenchée (optimiste), possible sur la bougie d'entrée |
| Jours fériés | calendrier de la NYSE | Juneteenth appliqué avant 2022, plus 31/12/2021, 02/07/2020 et 02/07/2026 : **7 jours de séance normale** sortis à 12:45. Deuils nationaux absents. | identique |
| Fériés pleins | « sortie à 12:45 » | trade le range de 9:30 de contrats à terme sans ouverture au comptant | identique |
| Coûts du backtest | — | — | glissement de 2 ticks, pas de commission par défaut (PINE-01). L'historique M5 de TradingView ne couvre que quelques mois. **Un backtest Pine ne peut pas valider la stratégie.** |

### A3. L'EA en réel (jamais compilé)

**Compilation.** Aucune erreur certaine n'a été trouvée, seulement quelques points à surveiller (EA-25 : une variable `exp`, `char[]` contre `uchar[]`, des conversions implicites). **Non vérifié sans MetaEditor.**

Les risques d'exécution les plus graves, tous **confirmés** à la relecture :
1. **Heure du serveur.** Un mauvais réglage d'heure d'été n'est que signalé : l'EA continue à trader. Avec SRV_DST_US sur un serveur à l'heure d'été européenne, environ 18 trades par an se font sur la bougie de 10:30 (EA-01).
2. **Ordres stop sans expiration fiable.** L'EA préfère GTC à DAY et ne supprime pas ses ordres quand il s'arrête. Un plantage à 9:38 peut laisser un ordre exécuté l'après-midi ou le lendemain. Au redémarrage, toute position portant le numéro magique est adoptée (EA-01, EA-03 d'exécution).
3. **Sortie de 15:50, stop à l'entrée refusé, stop virtuel** : ils n'existent que si l'EA tourne et reçoit des cotations. **Un VPS est indispensable.**
4. **Redémarrage en plein trade** : avec un état périmé, une seconde pyramide ou une clôture immédiate sont possibles (EA-03).
5. **Envois Telegram et WhatsApp synchrones** : jusqu'à 5 s par message et par canal, et jusqu'à 200 s si 20 messages échouent, sans aucun contrôle de prix pendant ce temps (EA-08).
6. **Entrée au marché « quelle que soit la distance »** (lancement tardif, niveau trop proche du prix) : le risque n'est pas borné (EA-06).
7. **Arrondi des lots.** Avec un pas de volume de 0,5, 0,25 ou 0,05, `NormalizeDouble(lots, round(-log10(pas)))` peut **arrondir vers le haut** : 0,5 lot devient 1, ce qui double le risque (EA-04, relu).
8. **Deux instances sur le même compte, et dossier commun partagé.** Un compte démo et un compte réel sur la même machine partagent `reglages.txt` : même risque, même case Nasdaq, et une demande « Clôturer » ferme aussi le trade de l'autre terminal (ET-04 et l'oubli « dossier commun » du domaine EA).

### A4. Le bot BTC chez Binance (jamais exécuté)

**En l'état, le bot ne peut pas tourner correctement en réel.**

**Critiques**
1. **★ Le transfert spot ↔ futures est mal formé** avec ccxt 4.5.93 (`courtier.py`, `executer`, `transfer('USDT', m, 'spot', 'future')`).
   - ccxt ne connaît plus `future` et envoie `type=MAIN_ISOLATED_MARGIN&toSymbol=FUTURE` (requête capturée sans l'envoyer).
   - **La vente et tout le montage à levier ne peuvent pas être financés.**
   - En ×1, le plan vend d'abord le BTC, puis échoue au transfert. Le bot se retrouve donc à plat au lieu de vendeur, avec une alerte d'erreur toutes les 5 minutes.
   - Sur le rendement, l'effet est faible : sans vente, Sharpe 1,22 contre 1,25.
2. **★ Le stop de protection n'est jamais annulé.** ccxt envoie le STOP_MARKET vers l'API des ordres conditionnels (algo) de Binance. Mais `annuler_stop` appelle `fetch_open_orders` sans `trigger=True` et ne le voit donc pas. Les stops s'empilent, ou sont refusés, à chaque cycle (leviers ×2 et plus).
3. **★ Le coupe-circuit peut laisser la position ouverte et bloquer le bot.** `etat['arrete']` est posé *avant* la fermeture. Si un ordre échoue, ou si PAUSE est actif, le bot reste « arrêté » avec la position ouverte (`bot.py`, `cycle`).
4. **★ Passer du papier au réel garde `etat.json`.** Le plus haut du compte papier (`pic`), par exemple 10 000 $, est repris tel quel. Avec un capital réel inférieur à 60 % de ce montant, le coupe-circuit se déclenche au premier cycle réel : **il vend tout et arrête le bot**.
5. **Un deuxième bot peut être lancé** depuis Étrave pendant un cycle long. Le battement n'est écrit qu'avant et après le cycle, Étrave déclare le bot mort après 60 s, et un cycle avec des ordres limites dure plusieurs minutes. Le risque est de doubler les ordres (ET-01). La reproduction faite par le vérificateur montre que « Démarrer » est accepté.

**Majeurs**
- **★ Le testnet est impossible tel quel.** ccxt refuse le bac à sable des futures (« not supported for futures anymore… use demo trading »). Les transferts n'ont pas de testnet, et les deux testnets demandent deux paires de clés. **La « première étape : testnet » de LISEZMOI ne peut pas être faite.**
- **Erreurs avalées sans contrôle :**
  - ordres limites dont les erreurs sont ignorées, sans identifiant client ni nettoyage, ce qui peut doubler une position ;
  - réglages de marge et de levier dont les erreurs sont ignorées ;
  - mode Hedge du compte jamais vérifié.
- **Marge à 100 % exactement** : un refus « Margin is insufficient » est plausible.
- **« Arrêter » est sans effet** sous systemd ou `lancer_bot.bat` : le bot redémarre.
- **Réponse 451 (« restricted location »)** au démarrage : le bot plante en boucle sans alerte.
- **La clé décrite dans LISEZMOI n'a pas la permission « Universal Transfer »**, nécessaire aux transferts.
- **Le capital compté** inclut tout l'USDT et tout le BTC du compte spot, même ce qui n'est pas au bot.

### A5. Étrave

- **`reglages.txt`** : écrit sans verrou, et une lecture ratée efface les autres clés à l'écriture suivante, ce qui peut réactiver la case Nasdaq (ET-02, ET-03).
- **Réglages du bot BTC changés en marche** : ils n'ont aucun effet avant un redémarrage, y compris l'effacement de la clé (ET-06).
- **« Arrêter »** tue le bot au milieu d'un ordre, ce qui peut laisser un ordre limite chez Binance (ET-07).
- **Clé Binance** rangée dans le dossier commun de MetaTrader, lisible par tout programme MQL5 (ET-08, plausible).

Sur la sécurité, le serveur n'écoute que sur 127.0.0.1, avec un jeton : rien de grave n'a été trouvé de ce côté.

---

## B. Backtest ORB v6 (Nasdaq), 2018-01-02 → 2026-11-13

### Hypothèses de coûts

| Coût | Modèle |
|---|---|
| Spread | Celui de Dukascopy, payé dans les prix (entrée à l'ask pour un achat, sortie au bid…). Médiane en séance : 1,1 point en 2018-2019, 1,45 point de 2020 à 2025, 1,07 point en 2026. Entre 9:30 et 9:45 : médiane 1,29 point, 90e centile 1,51 point. **Il est presque constant : il ne montre pas l'élargissement d'ouverture d'un courtier de détail.** |
| Glissement | Ajouté sur chaque ordre stop (entrée, stop de protection) et sur chaque ordre au marché (ajout, sortie de 15:50). De 0 à 5 points, ou en part du range. |
| Commission | 0 par défaut, 0,5 point par unité et par côté en variante. |
| Financement | Aucun : pas de position la nuit. |
| Ambiguïtés à la minute | Deux niveaux touchés dans la même minute : 8 trades sur 1 391. Le choix (le plus proche de l'ouverture ou le pire cas) ne change pas le résultat. |

### Résultat de base et sensibilité aux coûts

1R = taille de départ × range, comme dans le README. Le capital par an suppose 0,5 % de risque, composé, sans plafond de marge.

| Glissement (stop / marché) | Trades | R moyen | t | R total | Pire baisse | Pire série | Capital/an à 0,5 % |
|---|---|---|---|---|---|---|---|
| 0 / 0 | 1 391 | **+0,483** | 4,9 | +672 | −23 R | 15 | +42 % |
| 0,5 / 0,5 | 1 391 | +0,401 | 4,2 | +557 | −26 R | 15 | +34 % |
| **1 / 0,5** (hypothèse centrale) | 1 391 | **+0,364** | 3,8 | +506 | −29 R | 15 | +30 % |
| 2 / 1 | 1 391 | +0,215 | 2,3 | +299 | −48 R | 21 | +16 % |
| 3 / 1 | 1 391 | +0,150 | 1,7 | +209 | −62 R | 21 | +10 % |
| 5 / 0 | 1 391 | +0,009 | 0,1 | +12 | −109 R | 25 | −1 % |
| 5 / 1 | 1 391 | −0,040 | −0,5 | −55 | −146 R | 25 | −5 % |
| 2 / 1, spread +1 point, commission 0,5 | 1 401 | +0,126 | 1,4 | +176 | −81 R | 24 | +8 % |

Un spread plus large que celui de Dukascopy pèse autant : +2 points donnent +0,35 R, +4 points donnent +0,24 R.

Avec un glissement **proportionnel au range** :

| Glissement par ordre stop | R moyen | t |
|---|---|---|
| 2 % du range | +0,39 | 4,0 |
| 5 % du range | +0,28 | 2,9 |
| 10 % du range | +0,08 | 0,9 |

**Le point mort est autour de 5 points, ou 10 % du range, par ordre stop.** Les ranges de 2018-2019 étaient petits (médiane 18-20 points contre 64-104 points en 2025-2026), donc un même glissement en points pèse 3 à 5 fois plus sur ces années-là.

### D'où vient le gain (glissement 0)

| Variante | Trades | R moyen | t | Pire baisse |
|---|---|---|---|---|
| ORB nue, sans filtre, sans stop à l'entrée, sans pyramide | 2 184 | +0,122 | 2,8 | −40 R |
| Filtres seuls | 1 391 | +0,231 | 4,0 | −22 R |
| Filtres + stop à l'entrée | 1 391 | +0,235 | 4,3 | −24 R |
| Filtres + pyramide | 1 391 | +0,452 | 4,5 | −26 R |
| **v6 complète** | 1 391 | +0,483 | 4,9 | −23 R |

- **La pyramide fait tout le bénéfice net** : les 370 trades avec ajout font +1 377 R, les 1 021 autres −706 R.
- **Le stop à l'entrée n'apporte presque rien** : +0,004 R.
- **La distribution des R** : médiane −1 R, 20,6 % de trades gagnants, 62 % de pertes pleines.
- **Concentration** : les 10 meilleurs trades font 242 R, les 20 meilleurs 420 R, sur 672 R au total.
  - Sans les 2 % meilleurs trades (27), le R moyen tombe à +0,11 sans glissement, et à **−0,006 avec 1 point de glissement**.
- **L'ORB nue ne survit pas aux coûts** : +0,064 R à 1 point (intervalle à 95 % : −0,01 à +0,14), +0,006 R à 2 points.

### Réglages voisins (glissement 1 / 0,5 ; v6 = +0,364 R)

| Réglage | R moyen | Réglage | R moyen |
|---|---|---|---|
| Stop à l'entrée 1,0 / 1,25 / 1,75 / 2,0 R | 0,29 / 0,32 / 0,35 / 0,34 | Sans stop à l'entrée | 0,33 |
| Pyramide à 1,5 / 1,75 / 2,5 / 3 R | 0,42 / 0,38 / **0,21** / **0,21** | Sans pyramide | 0,18 |
| Ajout ×1 / ×1,5 / ×3 | 0,26 / 0,31 / 0,46 | Stop de l'ensemble à 0,75 / 1,25 / 1,5 R | 0,28 / 0,34 / 0,39 |
| Ordres valables 1 / 3 / 4 / 6 bougies | 0,36 / 0,35 / 0,35 / 0,35 | RSI 7 / 10 / 21 / 28 | 0,30 / 0,33 / 0,38 / 0,40 |
| RSI au seuil 45 / 55 | 0,35 / 0,33 | Élan depuis 8:30 / 8:45 / 9:15 / 9:25 | 0,36 / 0,36 / 0,34 / 0,33 |
| Sortie 12:00 / 15:00 / 15:30 / 15:55 | **0,17** / 0,29 / 0,36 / 0,37 | **Range de 10 / 15 min** | **0,15 / 0,10** |
| Achats seuls / ventes seules | 0,41 (t 3,2) / 0,32 (t 2,2) | | |

La plupart des réglages voisins restent dans un plateau entre 0,29 et 0,40 R : ce n'est pas un pic isolé. Trois choix sont sensibles :
- **la bougie de 5 minutes** : 10 ou 15 minutes divisent le gain par 2,5 à 3,5 ;
- **le seuil de la pyramide** : à 2,5 R ou 3 R, le gain baisse de 40 % ;
- **la sortie tardive.**

### Période et date de départ (glissement 1 / 0,5)

| | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|---|
| R moyen | 0,69 | 0,16 | 0,33 | 0,35 | 0,39 | 0,51 | 0,19 | 0,23 | 0,40 |
| t | 1,9 | 0,6 | 1,2 | 1,7 | 1,5 | 1,7 | 0,6 | 0,8 | 1,2 |
| R moyen à 2 / 1 points | 0,21 | −0,03 | 0,21 | 0,22 | 0,34 | 0,36 | 0,10 | 0,19 | 0,37 |

\* 2026 : jusqu'au 13 novembre.

- Toutes les années sont positives à 1 point, **mais aucune n'est significative seule**.
- La meilleure année est la première, 2018 (+113 R).
- Sommes de R sur fenêtres glissantes :

  | Fenêtre | Pire | Part des fenêtres négatives |
  |---|---|---|
  | 6 mois | −25 R | 14 % |
  | 12 mois | −7 R | 2 % |
  | 24 mois | +27 R | 0 % |

### Rééchantillonnage et surajustement

Intervalle de confiance à 95 % du R moyen, par blocs de 20 trades :

| Glissement | Intervalle |
|---|---|
| 0 | [0,32 ; 0,66] |
| 1 / 0,5 | [0,20 ; 0,53] |
| 2 / 1 | [0,05 ; 0,38] |

- **Une année simulée** (157 trades tirés au hasard, glissement 1) : 9,8 % d'années perdantes. Le 5e centile est à −13 R.
- **Surajustement.** Le meilleur de *N* essais sans aucun avantage atteint en moyenne t ≈ √(2 ln N). Le t observé correspond donc au meilleur d'environ :
  - **150 000** essais indépendants sans glissement ;
  - **1 200** à 1 point ;
  - **15** à 2 points.

  Les essais réels sont corrélés (variantes voisines), donc leur nombre effectif est plus petit que leur nombre brut. Le résultat ne s'explique pas *seulement* par la sélection sur 2018-2026. **Mais il n'a pas été confirmé hors échantillon, et la trace d'avant 2018 est négative** (partie D).

### Ce qui peut casser en réel

**Marge.** À 0,5 % de risque, les 3 unités (départ + ajout) valent 4,9 fois le capital en médiane, et 44 fois au plus. La taille est réduite par la marge sur :

| Levier du courtier | à 0,5 % | à 1 % | à 2 % |
|---|---|---|---|
| 1:10 | 8 % des trades | 56 % | 94 % |
| 1:20 | 1 % | 8 % | 56 % |

**Comptes financés.** Si tu trades chez un fournisseur de compte financé, comme FundingPips cité dans le README, ses règles comptent. Avec les règles courantes (−10 % de perte maximale, à vérifier chez lui), en rejouant 2018-2026 depuis chaque trade de départ, glissement 1 :

| Risque | Épreuve « +8 % avant −10 % » | Compte financé, perte max atteinte en un an |
|---|---|---|
| 0,5 % | réussie dans 94 % des départs, échouée dans 5 % | 5 % des départs |
| 1 % | réussie dans 75 % des départs, **échouée dans 25 %** | **30 %** des départs |

Une règle de « régularité » (aucun jour ne doit peser plus de X % du gain) serait difficile à tenir : le gain vient de quelques journées de forte tendance.

**Pires trades.** −3,2 R le 10 octobre 2025 : le stop a été sauté pendant une chute brutale (la minute de 10:58 manque dans les données). Puis −1,7 R.

**Jours fériés.** Les 39 trades pris des jours fériés ou de demi-séance font −0,58 R en moyenne. Ces jours-là, le CFD suit les contrats à terme alors que la bourse au comptant est fermée : il n'y a pas d'ouverture de New York à 9:30.

---

## C. Backtest du bot BTC

### Hypothèses de coûts

| Coût | Modèle |
|---|---|
| Comptant | 0,10 % de frais (Binance VIP 0, sans BNB) + 0,03 % de glissement par côté |
| Perpétuel | 0,04 % (moyenne entre maker 0,02 % et taker 0,05 %) + 0,03 % |
| Avant 2017 | 0,35 % par côté (Bitstamp) |
| Financement | Taux réels Binance depuis 2020, payés par la position détenue à l'heure du paiement. Avant 2020 : 0 pour la vente (variante à −10 %/an : aucun effet visible). En levier, les achats en perpétuel paient 10 %/an avant 2020. |
| Exécution | À la clôture 4h Bitstamp. Le bot réel agit 90 s après, chez Binance. |

### Le bot (×1, profil prudent) face aux règles simples

| Règle | 2012-07 → 2017 | **2018 → 13/11/2026** | 2022 → 13/11/2026 |
|---|---|---|---|
| **Bot ×1** | +135 %/an, Sh 2,69, dd −26 % | **+34 %/an, Sh 1,25, dd −22 %** | +20 %/an, Sh 0,91, dd −22 % |
| Achat et garde | +303 %/an, Sh 1,99, dd −85 % | +20 %/an, Sh 0,61, dd −81 % | +8 %/an, Sh 0,40, dd −67 % |
| MA200 journalière (100 % ou rien) | +313 %/an, Sh 2,12, dd −71 % | +18 %/an, Sh 0,58, dd −68 % | **+24 %/an**, Sh 0,80, dd −29 % |
| MA200 + même dosage (40 % de vol.) | +147 %/an, Sh 2,40, dd −45 % | +19 %/an, Sh 0,72, dd −42 % | +20 %/an, Sh 0,78, dd −24 % |
| Dosage seul (toujours acheteur) | +142 %/an, Sh 2,14, dd −61 % | +20 %/an, Sh 0,63, dd −65 % | +9 %/an, Sh 0,41, dd −55 % |
| **EMA50/200 4h seule + dosage** | +119 %/an, Sh 2,38, dd −39 % | **+32 %/an, Sh 1,12, dd −31 %** | +15 %/an, Sh 0,65, dd −31 % |
| Votes seuls (sans tendance 4h) | +133 %/an, Sh 2,57, dd −29 % | +31 %/an, Sh 1,14, dd −29 % | +19 %/an, Sh 0,86, dd −25 % |

Le bot est exposé à 31 % en moyenne. Il passe 75 ordres par an et fait tourner 28 fois son capital chaque année : environ 3,6 % par an de frais.

### Coûts

| Coûts | 2018-2026 | 2012-2017 |
|---|---|---|
| ×0 | +38 %/an, Sh 1,38 | |
| ×1 | +34 %/an, Sh 1,25 | |
| ×2 | +29 %/an, Sh 1,12 | +47 %/an |
| ×3 | +25 %/an, Sh 0,99 | −1 %/an |

**Sans la bande de 5 %**, le bot passerait 2 192 ordres par an au lieu de 75, pour un résultat équivalent (Sharpe 1,26). La bande est utile.

### Robustesse

- **Grille du code (`btc.REGLAGES`, 135 combinaisons, 2018-2026).**
  - Sharpe médian 1,00 ; du 10e au 90e centile, 0,83 à 1,16.
  - **Le réglage retenu (1,25) est 4e sur 135** : il a été choisi parmi les meilleurs. Une attente honnête est plus proche du Sharpe médian de la grille (~1,0) que de 1,25.
- **Retrait d'un vote.** Le Sharpe reste entre 1,10 et 1,25 : aucun vote n'est indispensable.
  - Avec seulement MA200, Ichimoku, MACD et RSI : Sharpe 1,25 aussi.
  - Avec MA200 seule : 0,99.
  - Sans le vote on-chain : 1,19.
- **Binance contre Bitstamp** (le bot réel lit Binance). Même sens sur 98,5 % des bougies 4h depuis juin 2018 (écart moyen d'exposition 0,008). Sur prix Binance, depuis juin 2018 : Sharpe 1,39, contre 1,28 sur Bitstamp.
- **Date de départ.** Sur 12 mois, à partir de chaque jour de 2018 à 2025 :

  | Règle | Part des départs perdants | Pire 12 mois | Médiane |
  |---|---|---|---|
  | Bot | 10 % | −18 % | +24 % |
  | MA200 dosée | 31 % | | |
  | Achat et garde | 36 % | | |

  Le bot bat la MA200 dosée dans 61 % des départs.
- **Années civiles**, bot / MA200 dosée / achat-garde :

  | Année | Bot | MA200 dosée | Achat-garde |
  |---|---|---|---|
  | 2018 | +6 % | −24 % | −73 % |
  | 2019 | +103 % | +36 % | +87 % |
  | 2020 | +109 % | +107 % | +304 % |
  | 2021 | +20 % | −13 % | +57 % |
  | 2022 | −3 % | 0 % | −65 % |
  | 2023 | +31 % | +65 % | +154 % |
  | 2024 | +64 % | +60 % | +111 % |
  | 2025 | −2 % | −10 % | −7 % |
  | 2026 | +16 % | −1 % | −23 % |

- **Rééchantillonnage par blocs de 60 jours (2018-2026).** Sharpe du bot : IC95 [0,49 ; 1,95].

  | Écart de Sharpe | Médiane | IC95 | P(≤ 0) |
  |---|---|---|---|
  | Bot − MA200 dosée | +0,43 | [−0,07 ; +0,97] | 4,9 % |
  | Bot − achat-garde | +0,55 | [−0,06 ; +1,18] | 3,7 % |
  | **Bot − EMA50/200 4h dosée** | **+0,09** | **[−0,19 ; +0,40]** | **26 %** |

- **2012-2017** : l'ordre et l'ETH/BTC n'existent pas encore (2 votes absents). Ce n'est donc pas le même système, et ce n'est pas un test hors échantillon. Toute la famille « tendance + dosage » y brille, achat-et-garde aussi.
- **Le coupe-circuit dépend du chemin.** Le profil « équilibré » (60 %), lancé en juillet 2012, prend le krach d'août 2012 à pleine taille. Il touche −40 % sur une clôture 4h en octobre 2012 et ne repart jamais : +5 %/an au lieu de +180 %/an sans coupe-circuit.

### Levier (montage perpétuel dès ×2)

| Levier | Sans coupe-circuit, 2018-2026 | **Avec le coupe-circuit à −40 % du bot**, 2018-2026 | Arrêt définitif (départ 2018) |
|---|---|---|---|
| ×1 | +34 %/an, Sh 1,25, dd −22 % | identique | jamais |
| ×2 | +61 %/an, Sh 1,17, dd −42 % | **+16 %/an, Sh 0,69** | 19/02/2020 |
| ×3 | +87 %/an, Sh 1,17, dd −59 % | +27 %/an, Sh 0,80 | 14/08/2019 |
| ×4 | +104 %/an, Sh 1,17, dd −72 % | +36 %/an, Sh 0,83 | 27/06/2019 |
| ×5 | +73 %/an, Sh 1,05, dd −92 % | +1 %/an | 24/02/2019 |
| ×7 | +31 %/an, dd −98 % | −3 %/an | 25/07/2018 |
| ×10 | −57 %/an, dd −100 % | −2 %/an | 08/01/2018 |

Mon stop de protection et ma liquidation sont vérifiés sur le plus haut et le plus bas de chaque bougie 4h : un saut à l'intérieur de la bougie n'est pas vu.

---

## D. Comparaison avec `etrave/reference.json` et `bitcoin/profils.json`

### Nasdaq : `reference.json` (et `risque.py`, `page.html`)

**Les trades sont reproduits.** Mêmes 1 391 jours de trade, sans un de plus ni un de moins. Avec le même glissement de 0,1 point :

| | R moyen | R total | Pyramides |
|---|---|---|---|
| `reference.json` | +0,462 | +643 | 368 |
| Ma simulation | +0,467 | +649 | 370 |

- Les écarts restent sous 0,02 R sauf sur quelques trades avec pyramide, où ils atteignent 1,9 R. L'ajout y est probablement pris à un autre prix : l'EA prend « le premier tick suivant », moi l'ouverture de la minute suivante.
- **Le calcul est donc juste. Ce qui pose problème, c'est l'hypothèse de coût.**

**0,1 point de glissement est irréaliste** pour des ordres stop à l'ouverture de New York. La page Risque rejoue `risque.py` sur ces trades. Le même calcul sur mes trades donne :

| Risque | Page (0,1 point) | Glissement 1 / 0,5 | Glissement 2 / 1 |
|---|---|---|---|
| 0,5 % | +40 %/an, baisse −11 % | +30 %/an, −14 % | +16 %/an, −22 % |
| 1 % | +88 %/an, −22 % | +61 %/an, −27 % | +29 %/an, −40 % |
| 2 % (levier 1:20) | +145 %/an, −33 % | +94 %/an, −38 % | +40 %/an, −59 % |

**Le point le plus important de toute la revue se trouve dans les textes du dépôt :**
- `page.html`, ligne 302 : « Nasdaq avant 2018 : la stratégie perdait (−55R sur 2015-2017, −33R sur 2013-2014). L'ancien test 2015-2026 a connu une baisse de 76R. »
- `risque.py` : `PIRE_BAISSE_ANCIEN_TEST_R = 76`.

C'est exactement la période que tu désignes comme le seul vrai test hors échantillon. **D'après le développeur lui-même, la stratégie y perd** : −88 R sur 5 ans, soit environ −0,1 R par trade si la fréquence était la même. Je n'ai pas pu le vérifier (données bloquées).

S'il est exact, le gain de 2018-2026 tient à un **régime** : un Nasdaq très tendanciel et de plus en plus volatil, avec des ranges passés de 18-20 points à 64-104 points. Il ne tient pas à une propriété stable de la règle. Avec de vrais coûts, les deux périodes réunies (2013-2026) donneraient un résultat modeste.

### BTC : `profils.json`

| ×1 | 2012-2026 | 2018-2026 | 2022-2026 |
|---|---|---|---|
| `profils.json` | +67 %, Sh 1,91, dd −25 % | +35 %, Sh 1,28, dd −21 % | +21 %, Sh 0,94, dd −21 % |
| Ma comptabilité | +66 %, Sh 1,88, dd −26 % | +34 %, Sh 1,25, dd −22 % | +20 %, Sh 0,91, dd −22 % |

- **Pour ×1, accord à 1-3 % près.** Mes coûts sont un peu plus élevés (0,13 % par côté contre 0,12 %) et j'applique la bande de 5 %.
- **Pour ×2 à ×4 sans coupe-circuit, accord aussi.** ×2 : +62 %, Sh 1,17, dd −42 % dans le fichier, contre +61 %, 1,17, −42 % chez moi. ×3 : +88 %, Sh 1,18, dd −59 %, contre +87 %, 1,17, −59 %.

**L'écart de fond : `profils.py` ne simule pas le coupe-circuit à −40 %** que le bot applique (`perte_max`, par défaut 0,40). Toutes les lignes ×2 et plus de `profils.json` (et les textes de la page qui en viennent) décrivent donc un bot qui **continuerait** après −42 % à −100 %. Le vrai bot se serait arrêté pour de bon. Exemple : la page dit pour ×2 « Rapporte presque deux fois plus ». Avec le coupe-circuit, ×2 lancé en 2018 fait +16 %/an contre +34 % pour ×1.

**Le signe du financement d'une vente avant 2020 n'est pas le même dans les deux codes :**
- dans `profils.py`, la vente **reçoit** 10 %/an (`fund = +0.10/365/6`, puis `fin -= tenu * fund` avec `tenu < 0`) ;
- dans `btc.Banc4h`, elle **paie** 10 %/an (`fund[avant] = -0.10/365/6`).

L'effet est faible : la vente ne fait qu'un quart de la taille, et il ne joue qu'avant 2020.

---

## E. Verdicts, fragilités et plan de démo

### Verdicts

**ORB v6, Nasdaq : avantage DOUTEUX.**

Pour :
- un gain positif chaque année de 2018 à 2026 à 1 point de glissement ;
- un plateau de réglages voisins ;
- deux implémentations indépendantes qui concordent.

Contre :
- un résultat très sensible au glissement (point mort vers 5 points, ou 10 % du range, par ordre stop) ;
- un gain concentré sur 2 % des trades ;
- l'ORB nue qui ne survit pas aux coûts ;
- **une trace d'avant 2018 négative**, d'après les textes du dépôt ;
- **aucune donnée hors échantillon récente.**

Les chiffres de la page Risque (0,1 point de glissement) surestiment le gain d'au moins un quart, et probablement de moitié.

**Bot BTC ×1 : avantage DOUTEUX mais plausible**, et surtout un **meilleur profil de risque** que les règles simples.

- La part défendable est connue et documentée ailleurs : le suivi de tendance et le dosage par la volatilité sur le BTC.
- Les 9 votes n'ajoutent rien de démontrable par rapport à une EMA50/200 4h dosée.
- Le réglage a été choisi 4e sur 135.
- Attente raisonnable : un Sharpe autour de 0,8 à 1,0, avec des années plates (2022 : −3 % ; 2025 : −2 %), pas 1,25.

**Bot BTC à levier ×2 et plus : avantage ABSENT** une fois le coupe-circuit pris en compte. Les chiffres affichés sont trompeurs.

### Classement de ce qui est le plus fragile

1. **L'exécution du bot BTC.** Ce n'est pas un risque mais un défaut certain, constaté dans ccxt 4.5.93 (partie A4) :
   - transfert vers les futures mal formé ;
   - stop de protection jamais annulé ;
   - coupe-circuit qui peut laisser la position ouverte ;
   - passage papier → réel qui déclenche le coupe-circuit ;
   - second processus possible.
2. **Le Nasdaq avant 2018** : selon les textes du dépôt, la stratégie y perdait (−55 R sur 2015-2017, −33 R sur 2013-2014), et je n'ai pas pu le vérifier.
3. **Le glissement réel des ordres stop à 9:35-9:45**, et l'écart de spread entre Dukascopy (~1,3 point, presque constant) et ton courtier. Le point mort est vers 5 points par ordre stop.
4. **La dépendance du Nasdaq à quelques journées de tendance**, via la pyramide. Sans les 2 % meilleurs trades, il ne reste rien à 1 point de glissement.
5. **Le levier du bot BTC, présenté sans le coupe-circuit.**
6. **L'EA jamais compilé ni exécuté** (partie A3) :
   - heure du serveur seulement signalée ;
   - ordres GTC ;
   - envois Telegram bloquants ;
   - reprise après plantage ;
   - arrondi des lots qui peut doubler le risque ;
   - dossier commun partagé entre démo et réel.
7. **La sélection du réglage BTC** (4e sur 135) et les données Coin Metrics : valeurs « flash » en direct, valeurs révisées dans l'historique.

### Ce qu'il faut vérifier en démo avant l'argent réel

**Nasdaq (EA, compte démo du courtier réel, au moins 40 à 60 trades, soit 3 à 4 mois)**

1. **Compiler l'EA**, puis vérifier sur 5 jours que l'heure de New York calculée est juste, en particulier pendant les semaines où l'Europe et les États-Unis changent d'heure à des dates différentes (mars et octobre-novembre).
2. **Pour chaque trade, relever le glissement d'entrée et de stop**, en points et en part du range (le message « exécuté » le donne). Relever aussi le spread à 9:30-9:45.
3. **Comparer chaque trade de démo au même jour rejoué** par `revue/orb.py` sur les données Dukascopy du jour. Même jour, même sens, même ajout. Un écart de sens ou de pyramide sur plus de 1 trade sur 10 signale un bug d'exécution.
4. Vérifier :
   - que la pyramide s'exécute avec le bon lot et que le stop de l'ensemble se pose ;
   - que la sortie de 15:50 a lieu même si Telegram est lent ;
   - qu'un redémarrage de MetaTrader en plein trade est bien repris.

**BTC.** Le testnet tel que décrit est impossible (partie A4). Il faut d'abord corriger :
- le transfert ;
- l'annulation du stop ;
- l'ordre de pose du drapeau `arrete` ;
- la remise à zéro de `etat.json` au changement de mode ;
- le verrou contre un second processus.

Je ne l'ai pas fait : tu m'as demandé de ne pas modifier les bots sans ton accord. Ensuite, utiliser le « trading démo » de Binance (pris en charge par ccxt avec `enable_demo_trading`) ou un compte réel minuscule.

1. Faire tourner `--une-fois` en démo sur chaque type de transition : ouvrir un achat, réduire, passer en vente, fermer. Lire le journal ligne par ligne et vérifier, après chaque transition :
   - les soldes, spot et futures ;
   - la marge isolée et le levier 1 ;
   - le transfert de marge.
2. Comparer chaque décision du bot à `btc.position` recalculé le même jour.
3. Ne pas utiliser le levier > 1 tant que le coupe-circuit n'est pas pris en compte dans les chiffres affichés.

### Quels résultats de démo doivent te faire arrêter

**Nasdaq**
- **Glissement moyen par ordre stop supérieur à 3 points, ou à 5 % du range.** À ce niveau, le R moyen attendu passe sous +0,15, puis sous 0 vers 5 points. Les frais suffisent à l'annuler.
- Après 50 trades, **un R moyen inférieur à −0,25**. Avec un écart-type de ~3,7 R par trade, c'est environ 2 écarts-types sous l'hypothèse centrale de +0,36. 50 trades ne permettent pas de *prouver* l'avantage, mais cela suffit pour rejeter l'hypothèse centrale.
- Plus de 1 trade sur 10 qui diffère du rejeu (sens, entrée, pyramide).
- **Une série de plus de 20 pertes.** Le pire du test est 15 sans glissement, 21 à 2 points.

**BTC**
- Une seule erreur d'ordre en testnet : mauvaise quantité, mauvais sens, ou ordre à moitié passé non rattrapé au cycle suivant. Elle doit être corrigée et suivie de nouvelles semaines sans anomalie.
- Une décision du bot différente de `btc.position` sur les mêmes données.
- En réel ×1, une baisse de plus de 25 % : le pire du test depuis 2018 est −22 %.

### Ce que je n'ai pas pu vérifier

- **Le Nasdaq avant 2018 et après le 13 novembre 2026** : pas de données.
- **Le glissement et le spread réels de ton courtier** : seuls des scénarios sont donnés.
- **La compilation de l'EA et du script Pine** : pas de MetaEditor ni de TradingView ici. La partie A dit ce qui est *probable*, pas ce qui est *certain*.
- **Tout appel réel à Binance.** L'API de trading répond 451 (« restricted location ») depuis cet environnement.
- **Les valeurs Coin Metrics « flash »** que le bot aurait vues en direct dans le passé : seules les valeurs révisées sont téléchargeables. Le retrait complet du vote on-chain ne change le Sharpe que de 1,25 à 1,19, donc l'effet est probablement limité.
- **Le nombre d'essais réellement faits** pour choisir les règles (tu ne l'as pas donné). Mes calculs de surajustement l'encadrent seulement.
