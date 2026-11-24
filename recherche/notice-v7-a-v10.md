# Strategy V10 — notice (21 novembre 2026)

**Nasdaq uniquement.** Testé tel quel sur le Dow Jones, le DAX, l'or, le Bitcoin, l'EUR/USD et le GBP/USD, ce robot ne gagne sur aucun.

## Ce que c'est
La V9 avec un réglage de plus, la **largeur du stop**, né de l'autopsie des stops : une fois sur trois, après un stop, le Nasdaq repart de
+2 R ou plus dans le sens du trade. Le stop d'un seul range de 5 minutes est trop court.

Le même fichier contient deux profils :

| | Profil **Confort** (réglage livré) | Profil **Tendance** (= la V9) |
|---|---|---|
| Largeur du stop (`InpStopMult` ; TradingView : « Stop à N fois la distance normale ») | **3** | 1 |
| « Un trade compte comme gagnant au-delà de (R) » (`InpMemR`) | **1** | 0,05 |
| Stop de la cassure (achat) | 3 ranges sous le niveau de cassure | l'autre bord du range |
| Taille des positions | 3 fois plus petite | — |
| Continuations D1 à D3 | seulement si l'autre bord du range n'a pas été touché depuis la cassure | tant que la cassure est ouverte |
| Somme risquée par trade | la même | la même |

Tout le reste est identique à la V9 : filtres, heures, repli VWAP (B), continuations (D), entrée de 10:00 coupée (C), stop ramené à
l'entrée à +1,5 R, pyramide à +2 R, sortie à 15:50, jours de Fed et fériés exclus, garde-fou coût.
Attention : avec un stop 3 fois plus loin, 1 R vaut 3 ranges. Le stop à l'entrée et la pyramide se déclenchent donc 3 fois plus loin, et plus rarement.

## Ce que disent les tests (détail : ../rapport.md)
| Nasdaq | Tendance (V9) | Confort |
|---|---|---|
| 2018-2026 (spread réel + 1 point) | +1 614 R, 18 % de trades gagnants, pire baisse 56 R | +477 R, **47 %**, pire baisse 32 R |
| 2010-2017, coûts au poids d'aujourd'hui | +577 R, 15 %, pire baisse 170 R | +194 R, **44 %**, pire baisse 53 R |
| 2010-2017, coûts au poids de 2018 | −157 R | +23 R |
| Plus longue série de jours perdants | 24 à 33 | 8 à 14 |
| Lots ouverts en même temps, au maximum | 15 | 5 |

À pire baisse égale, les deux profils rapportent à peu près autant. Le Confort gagne plus souvent, pas davantage ; il résiste mieux aux
coûts ; en contrepartie il peut stagner longtemps (jusqu'à 20 à 32 mois sans nouveau plus haut dans les tests).
Le Confort a été mis au point après avoir vu tout l'historique : ce n'est pas une preuve.

## Le risque par trade : 0,25 %, inchangé
Le fichier est livré à **0,25 % par trade, comme la V9**. À ce réglage, dans les tests : pire journée −1,3 % du compte, pire baisse 8 %
(2018-2026) et 13 % (2010-2017). Revenir à 0,5 % (ton réglage des V6 à V8) double tout : gains, pire journée (−2,6 %), pires baisses
(16 % et 26,5 %). C'est ta décision ; attends d'avoir mesuré ton glissement réel en démo.
Si l'interface Étrave donne un risque, c'est lui qui est utilisé, comme avant.

## Ce qui a été vérifié, et ce qui ne l'a pas été
| Vérification | Résultat |
|---|---|
| `Strategy-V10.mq5` compilé avec MetaEditor (MetaTrader 5, sous Wine) | **0 erreur, 0 avertissement** (`../resultats/compilation/Strategy-V10.compilation.txt`) ; `Strategy-V10.ex5` = le robot compilé |
| `Strategy-V10.pine` passé dans l'analyseur de l'éditeur Pine de TradingView | 0 erreur ; 3 versions cassées exprès ont bien été signalées |
| Règles du profil Confort rejouées sur les données | oui (`../resultats/80_confort_final.md`, trades : `../resultats/trades_V10_confort_*.csv`) |
| **Robot vu en train de tourner** (testeur de MetaTrader, backtest TradingView, démo) | **NON** : le testeur exige un compte de courtier |

## MetaTrader 5 : installation
1. Hors séance et sans trade ouvert : **retire la V9** (ou tout robot précédent) du graphique du Nasdaq.
   La V10 utilise les mêmes numéros magiques que la V9 : ne fais jamais tourner les deux sur le même compte.
2. Copie `Strategy-V10.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor, touche F7 (« 0 errors »).
   (Ou copie directement `Strategy-V10.ex5`.)
3. Glisse Strategy-V10 sur le graphique M5 du Nasdaq, coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau, et la ligne « Entrées V10 : B … · C coupée · D … ».

À savoir :
- **Compte « hedging » obligatoire**, comme pour la V9. Sur un compte « netting », le robot coupe B, C et D.
- **Numéros magiques inchangés** : A = celui des réglages (50930), B = +1, C = +2, D1 = +3, D2 = +4, D3 = +5.
- **Réglage nouveau** (groupe « V10 — largeur du stop ») : `InpStopMult`, de 1 à 10. Valeur testée : 3. Entre 2,5 et 4 les résultats des tests se valent.
- **Message modifié** à 9:35 : « ORDRES PLACÉS · Range 9:30 : … (x points) · 1R = (3x points) », et le stop affiché est 3 ranges plus loin.
- **Garde-fou coût** : il compare maintenant le coût au risque (3 ranges) et non plus au range. Il se déclenche donc encore plus rarement.
- **Marge** : le calcul est celui de la V9 ; comme les lots sont 3 fois plus petits, la marge demandée l'est aussi.
- Le robot repart d'un état neuf (préfixe « StratV10_ ») : il ne reprend pas la mémoire de la V9. Installe-le un jour sans position.
- **Pour retrouver exactement la V9** : largeur du stop = 1 et « gagnant au-delà de » = 0,05.

## Le test à faire chez toi (10 minutes)
1. MetaTrader 5 > Affichage > Testeur de stratégie. Expert : Etrave\Strategy-V10. Symbole : ton Nasdaq. Période : M5.
   Dates : les 12 derniers mois. Modélisation : « Chaque tick basé sur des ticks réels ». Compte « hedging », levier 1:100.
2. Démarrer. Dans le « Journal » tu dois voir passer « ORDRES PLACÉS … 1R = … », « entrée D1 guettée », « ACHAT D1 exécuté(e) »…
3. Onglet « Backtest » > clic droit > Rapport > enregistrer en HTML et envoie-moi le fichier : je comparerai ses trades à
   `../resultats/trades_V10_confort_2018_2026_1pt.csv`.
   Ordre de grandeur de ma simulation sur les 12 derniers mois (20 novembre 2025 → 19 novembre 2026) : environ 410 trades sur 122 jours
   (122 cassures, 98 replis, 190 continuations), environ 50 % de trades gagnants, +76 R, une baisse de 12 R en cours de route.
   Sur une année ordinaire : 40 à 50 % de gagnants et une baisse de 15 à 35 R à un moment de l'année.
   Si ton testeur donne nettement moins de trades, un taux de réussite sous 35 % ou un résultat négatif, ne passe pas en réel : envoie-moi le rapport.

## L'interrupteur : quand couper le robot
Sur 60 jours de trade (environ 6 mois), coupe et fais le point si l'un de ces seuils est franchi :
- moins de 28 % de jours gagnants (16 ou moins sur 60) — la normale est 43 % ;
- un total pire que −40 R — la normale est +9 à +19 R ;
- une baisse de plus de 66 R depuis le dernier plus haut — la pire des tests est 53 R.
Ces seuils ne sont pas codés dans le robot. Détail : `../resultats/83_surveillance.md`.

## TradingView
1. Graphique **M5** du NAS100, avec les bougies hors séance. Éditeur Pine > colle tout `Strategy-V10.pine` > « Ajouter au graphique ».
2. Alerte sur la stratégie, condition « Appels de la fonction alert() uniquement ». Supprime l'ancienne.
3. Ce qui change à l'écran par rapport à la V9 : la ligne de stop (« SL ») est 3 ranges plus loin ; les tailles indiquées dans les alertes
   sont 3 fois plus petites ; l'infobulle du stop dit « Stop élargi : 3 ranges… » ; les tirets des continuations n'apparaissent pas si
   l'autre bord du range a été touché depuis la cassure. Le reste de l'affichage est celui de la V9, décrit plus bas.
4. Réglages : groupe « V10 — largeur du stop », et « Risque par trade » (0,25 %).

---

# Strategy V9 — notice (21 novembre 2026)

## Ce que c'est
La V8, revue après un examen sur 7 années de données jamais vues (2010-2017). Trois changements :

| | V8 | V9 |
|---|---|---|
| **A · cassure** (V7 : filtres, mémoire, hors FOMC et fériés) | oui | oui, inchangée |
| **B · repli VWAP** | oui | oui, inchangée |
| **C · entrée de 10:00** | oui | **coupée par défaut** (ne gagne presque rien sur les données jamais vues) |
| **D1, D2, D3 · continuations** | — | **nouveau** |
| **Garde-fou coût** | — | **nouveau** |
| Risque par trade par défaut | 0,5 % | **0,25 %** |

**Les continuations (D), en clair.** Tant que la cassure A est ouverte :
- à **9:40** (clôture de la bougie de 9:35), on guette pendant 10 minutes le dépassement du plus haut de cette bougie (pour un
  achat ; du plus bas pour une vente). Si le prix le dépasse : entrée **D1**, stop à l'autre bout de la bougie ;
- pareil à **9:45** avec la bougie de 9:40 (**D2**), et à **9:50** avec la bougie de 9:45 (**D3**) ;
- si le prix touche d'abord le stop prévu, ou si 10 minutes passent, l'entrée est abandonnée ;
- ensuite chaque entrée vit sa vie comme la cassure : stop au prix d'entrée à +1,5 R, pyramide à +2 R, sortie à 15:50 ;
- taille : jamais plus de lots que A, jamais plus de 1 R de risque.

**Le garde-fou coût.** Si le spread du moment + 2 glissements supposés (1 point chacun) pèse plus de 25 % du range du jour,
aucun ordre ce jour-là. Aux prix actuels (range de 60 à 100 points) il ne se déclenche jamais ; il est là pour le jour où
le range redeviendrait minuscule, situation dans laquelle la stratégie perdait de l'argent avant 2018.

## Ce que disent les tests (détail : ../rapport.md)
| | V8 | V9 |
|---|---|---|
| 2018-2026, période de recherche (spread réel + 1 point) | +986 R, pire baisse 38 R | +1 614 R, pire baisse 56 R |
| 2010-2017, **jamais vu**, coûts au poids d'aujourd'hui | +281 R, pire baisse 102 R | +577 R, pire baisse 170 R |
| 2010-2017, coûts au poids de 2018 | −159 R | −157 R |

Le backtest 2018-2026 est une vision optimiste. Règle tes attentes et ton risque sur la ligne du milieu.

## Pourquoi 0,25 % par trade
La V9 peut avoir 5 positions ouvertes en même temps (A, B, D1, D2, D3) et jusqu'à 15 lots de A pyramides comprises, contre
3 positions et 7 lots pour la V8. À 0,25 % par trade, elle ouvre au plus à peu près autant de lots que la V8 à 0,5 %.
Remonter ce chiffre est ta décision : une mauvaise journée coûte 4 à 5 R, une mauvaise année 80 à 120 R.

## Ce qui a été vérifié, et ce qui ne l'a pas été
| Vérification | Résultat |
|---|---|
| `Strategy-V9.mq5` compilé avec MetaEditor (MetaTrader 5, sous Wine) | **0 erreur, 0 avertissement** (`../resultats/compilation/Strategy-V9.compilation.txt`) ; `Strategy-V9.ex5` = le robot compilé |
| `Strategy-V9.pine` passé dans l'analyseur de l'éditeur Pine de TradingView | 0 erreur ; 4 versions cassées exprès dans le code nouveau ont bien été signalées |
| Règles de la V9 rejouées sur les données | oui (`../resultats/63_validation_finale.md`, listes de trades `../resultats/trades_V9_*.csv`) |
| **Robot vu en train de tourner** (testeur de MetaTrader, backtest TradingView, démo) | **NON** : le testeur exige un compte de courtier |

## MetaTrader 5 : installation
1. Hors séance et sans trade ouvert : retire l'ancien robot du graphique du Nasdaq.
2. Copie `Strategy-V9.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor, touche F7 (« 0 errors »).
   (Ou copie directement `Strategy-V9.ex5`.)
3. Glisse Strategy-V9 sur le graphique du Nasdaq, coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau, et la ligne « Entrées V9 : B … · C coupée · D … ».

À savoir :
- **Compte « hedging » obligatoire.** Sur un compte « netting », le robot coupe B, C et D et se comporte comme la V7.
- **Marge** : la taille est calculée pour que les 15 lots possibles tiennent dans la marge libre. Si elle manque, le robot
  réduit toutes les tailles et te prévient.
- **Numéros magiques** : A = celui des réglages (50930), B = +1, C = +2, D1 = +3, D2 = +4, D3 = +5.
- **Réglages nouveaux** (groupe « V9 ») : interrupteur des continuations, nombre de bougies (3), validité (10 minutes),
  pyramide sur les continuations (oui), garde-fou coût (0,25 ; 0 pour le couper), glissement supposé (1 point).
- **Messages nouveaux** : dans le journal, « entrée D1 guettée 10 min : achat si l'ask atteint … » ; puis « ACHAT D1 exécuté(e) :
  continuation… » ; à la clôture « ENTRÉE D1 CLÔTURÉE ». Les jours trop chers : « PAS DE TRADE aujourd'hui : coût trop lourd… ».
- Le robot repart d'un état neuf (il ne reprend pas la mémoire de la V8) : installe-le un jour sans position.
- **Étrave** : le bouton « Clôturer » ferme aussi les entrées D. L'état des D est écrit dans la clé `v9_d` du fichier d'état.

## Le test à faire chez toi (10 minutes)
1. MetaTrader 5 > Affichage > Testeur de stratégie. Expert : Etrave\Strategy-V9. Symbole : ton Nasdaq. Période : M5.
   Dates : les 12 derniers mois. Modélisation : « Chaque tick basé sur des ticks réels ». Compte « hedging », levier 1:100.
2. Démarrer. Dans le « Journal » tu dois voir passer « entrée D1 guettée », « ACHAT D1 exécuté(e) », « ENTRÉE B CLÔTURÉE »…
3. Onglet « Backtest » > clic droit > Rapport > enregistrer en HTML et envoie-moi le fichier : je comparerai ses trades à
   `../resultats/trades_V9_recherche_2018_2026_1pt.csv`. Ordre de grandeur sur un an : environ 380 trades (120 cassures,
   90 replis, 170 continuations), 15 à 25 % de gagnants, une baisse de 40 à 80 R en cours de route.

## TradingView
1. Graphique **M5** du NAS100, avec les bougies hors séance. Éditeur Pine > colle tout `Strategy-V9.pine` > « Ajouter au graphique ».
2. Alerte sur la stratégie, condition « Appels de la fonction alert() uniquement ». Supprime l'ancienne.
3. Ce qui change à l'écran par rapport à la V8 :

| Ce que tu vois | Ce que ça veut dire | Ce que tu fais |
|---|---|---|
| **Tirets verts foncés** avec « D1 stop · prix », juste après 9:40 | une continuation est guettée pendant 10 minutes | poser un ordre stop à ce prix, dans le sens de la cassure, stop sur la ligne pointillée (l'autre bout de la bougie), lot indiqué dans l'alerte |
| Alerte « D1 GUETTÉE : ordre stop d'achat à … pendant 10 min · stop … » | même chose, avec la taille | idem |
| Alerte « ACHAT D1 EXÉCUTÉ (continuation) » | l'ordre a été touché | rien : vérifier que le stop est en place |
| Les tirets disparaissent sans alerte d'exécution | pas de dépassement en 10 minutes, ou stop touché d'abord | annuler l'ordre stop s'il est encore chez le courtier |
| Ligne « D · continuations » du tableau | combien sont en cours, guettées, ou terminées | — |
| Ligne « C » du tableau : « coupée » | normal en V9 | — |

Le garde-fou coût de TradingView se règle en points (3,3 par défaut = 1,3 de spread + 2 × 1 de glissement), parce que
TradingView ne connaît pas le spread de ton courtier.

Le reste de l'affichage (range, cassure A, ligne orange du VWAP, bande bleue et étiquettes de B) est celui de la V8,
décrit plus bas.

---

# Strategy V8 — notice

## Ce que c'est
La v7 (trade **A**, la cassure du range de 9:30, inchangée) plus deux entrées, seulement les jours où la cassure est prise :

| Entrée | Quand | Stop | Gestion |
|---|---|---|---|
| **A · cassure** | ordres stop à 9:35, valables jusqu'à 9:45 (v7) | autre côté du range | stop à l'entrée à +1,5 R, pyramide à +2 R, sortie 15:50 |
| **B · repli VWAP** | après la cassure et jusqu'à 14:00 : première bougie M5 qui revient toucher le prix moyen de séance (VWAP), puis clôture du bon côté et dans le sens du trade. Entrée au marché à la clôture de cette bougie. Une fois par jour. | 1 point au-delà de l'extrême des 2 dernières bougies | comme A, en multiples de son propre stop |
| **C · 10:00** | à 10:00 New York, si le prix est toujours au-delà du niveau de cassure et que le stop du range n'a pas été touché | autre côté du range | stop à l'entrée à +1,5 R, pas de pyramide, sortie 15:50 |

**Taille** : B et C ne prennent jamais plus de lots que A et ne risquent jamais plus que A (1 R). Le risque par trade
n'augmente pas ; ce qui augmente, c'est le nombre de trades ouverts en même temps (jusqu'à 3, dans le même sens).
La règle mémoire ne regarde que A. B est abandonnée si une bougie M5 clôture de l'autre côté du range.

## Ce qui a été vérifié, et ce qui ne l'a pas été
| Vérification | Résultat |
|---|---|
| `Strategy-V8.mq5` compilé avec MetaEditor (MetaTrader 5 build 6327) | **0 erreur, 0 avertissement** |
| `ORB-v7.mq5` et `ORB-v6.mq5` compilés de la même façon | 0 erreur, 0 avertissement |
| `Strategy-V8.pine` et `ORB-v7.pine` passés dans l'analyseur de l'éditeur Pine de TradingView | 0 erreur, 0 avertissement |
| Règles de la V8 rejouées sur les données 2018-2026, telles que le code les applique | +1 008 R, pire baisse 38 R, 9 années sur 9 (`../resultats/29b_v8_verif_code.md`) |
| **Robot vu en train de tourner** (testeur de MetaTrader, backtest TradingView, démo) | **NON** : le testeur de MetaTrader exige un compte de courtier, que je n'ai pas |

Donc : le code se compile, les règles sont celles du test, mais **personne ne l'a encore vu passer un ordre**.
Testeur de stratégie puis compte démo avant tout argent réel.

## MetaTrader 5 : installation
1. Hors séance et sans trade ouvert : retire l'ancien robot (v6 ou v7) du graphique du Nasdaq.
2. Copie `Strategy-V8.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor, touche F7 (tu dois lire « 0 errors »).
3. Glisse Strategy-V8 sur le graphique du Nasdaq, coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau. Le panneau a deux lignes de plus :
   « Cassure (A) » et « Entrées V8 : B … · C … ».

À savoir :
- **Compte « hedging » obligatoire** (plusieurs positions sur le même symbole). Sur un compte « netting », le robot le
  dit au lancement, coupe B et C et ne prend que la cassure, comme la v7.
- **Marge** : la taille est calculée pour que les 7 unités possibles (A + sa pyramide, B + sa pyramide, C) tiennent dans
  90 % de la marge libre. Sur l'historique, avec 0,5 % de risque par trade : un levier de 1:25 sur l'indice suffit
  95 % des jours, 1:40 suffit toujours ; avec 1:20, la taille serait réduite environ 1 jour sur 8. Avec 1 % de risque,
  double ces chiffres. Quand la marge manque, le robot réduit toutes les tailles et te prévient (« ORDRES PLACÉS »).
- **Numéros magiques** : A = celui des réglages (50930), B = +1, C = +2. Ne lance pas un autre robot avec ces numéros.
- **Statistiques du panneau** : A, B et C comptent chacun pour un trade ; le R de B et de C est rapporté à la somme risquée par A.
- **Messages** : « ACHAT B exécuté : repli sur le VWAP… », « PAS D'ENTRÉE C aujourd'hui » avec la raison,
  « ENTRÉE B abandonnée » si une bougie clôture de l'autre côté du range.
- **Étrave** : le bouton « Clôturer » ferme A, B et C. La page n'affiche que l'état de A, comme avant : B et C n'y
  apparaissent pas encore (leur état est écrit dans le fichier d'état, clés `v8_b`, `v8_c`, `v8_resultat`, prêt pour une
  mise à jour de l'interface ; leurs trades clôturés sont bien ajoutés au journal des trades, marqués « V8 B » / « V8 C »).
  Le bouton « Installer ou mettre à jour l'EA » réinstalle encore la v6 : ne t'en sers pas.
- Réglages V8 (groupe « V8 ») : chaque entrée a son interrupteur. Les valeurs par défaut sont celles du test.

## Le test à faire chez toi (10 minutes)
1. MetaTrader 5, menu Affichage > Testeur de stratégie.
2. Expert : Etrave\Strategy-V8. Symbole : ton Nasdaq. Période : M5. Dates : les 12 derniers mois.
   Modélisation : « Chaque tick basé sur des ticks réels ». Dépôt 100 000, levier 1:100.
3. Démarrer. Dans l'onglet « Journal », tu dois voir passer « ACHAT B exécuté », « ENTRÉE C CLÔTURÉE », etc.
4. Onglet « Backtest », clic droit > Rapport > enregistrer en HTML, et envoie-moi le fichier : je comparerai ses trades
   à ceux de mes calculs (`../resultats/trades_V8.csv`). Ordres de grandeur attendus sur un an : environ 270 trades,
   16 à 48 % de gagnants selon l'entrée, une baisse de 25 à 50 R en cours de route.
Le compte utilisé pour le test doit être « hedging », sinon B et C restent coupées.

## TradingView : installation
1. Graphique M5 du NAS100, avec les bougies hors séance (comme pour la v6).
2. Éditeur Pine > colle tout `Strategy-V8.pine` > « Ajouter au graphique ».
3. Alerte : crée une alerte sur la stratégie, condition « Appels de la fonction alert() uniquement ». Supprime l'ancienne.

## TradingView : lire le graphique (quand entrer)
![Aperçu](../resultats/v8_apercu_tradingview.png)

| Ce que tu vois | Ce que ça veut dire | Ce que tu fais |
|---|---|---|
| Rectangle gris « 9:30 » et tirets verts / rouges avec « Achat stop · prix · lot » | les ordres de la cassure (A) sont à poser | poser l'ordre stop au prix indiqué, stop de l'autre côté du range, avec le lot affiché |
| **Ligne orange** | le prix moyen de la séance (VWAP) depuis 9:30 | rien, c'est le repère de B |
| **Bande bleue** collée à la ligne orange | B est guettée : on attend qu'une bougie revienne toucher cette bande | surveiller |
| **Étiquette bleue « ACHAT B » (ou « VENTE B »)** sous la bougie, fond bleu | la bougie a touché la bande et a clôturé du bon côté : signal B | entrer au marché tout de suite ; le stop est la ligne bleue en tirets « SL B » ; le lot est dans l'info-bulle et dans l'alerte |
| **Trait vertical violet** en pointillé, étiquette « C · 10:00 ? » | l'heure de l'entrée C ; l'info-bulle donne le prix à tenir | attendre 10:00 |
| **Étiquette violette « ACHAT C »** et « C ✓ » | à 10:00 la cassure tenait : signal C | entrer au marché ; stop = l'autre côté du range (« SL C ») |
| « C ✕ » en gris | pas d'entrée C ; la raison est dans l'info-bulle et dans le tableau | rien |
| Lignes pleines bleue / violette avec une étiquette à droite | entrées B et C en cours, avec leur résultat en R en direct | — |
| Petite étiquette « + » | pyramide sur cette entrée ; le stop affiché remonte | ajouter 2 fois la taille de départ, remonter le stop au prix indiqué |
| Étiquettes « B +1,2R », « C −1,0R » | résultat final de chaque entrée | — |
| « ⏸ mémoire », « ⏸ FOMC », « ⏸ férié » au-dessus du range | pas de trade aujourd'hui, et pourquoi | rien |

Le **tableau** (en haut à droite) dit la même chose en clair, ligne par ligne :
« A · cassure », « B · repli VWAP » (par exemple *guettée : une bougie doit toucher 21 352,4 puis clôturer au-dessus de
21 348,1*), « C · 10:00 » (*à 10:00 NY si le prix est au-dessus de 21 400,0*), « Mémoire » (la prochaine cassure
sera-t-elle prise ?), puis l'historique en R et le lot.

Réglages d'affichage (groupe « Affichage ») : VWAP, zone de repli et repères peuvent être masqués séparément.

## Écarts connus entre le robot MT5 et le script TradingView
- TradingView ne voit que des bougies de 5 minutes et ne compte pas le spread : ses résultats sont un peu plus beaux.
  Le robot MT5 est la version de référence.
- Le VWAP dépend du volume, qui n'est pas le même chez TradingView et chez ton courtier : certains jours, la bougie du
  signal B peut différer d'une bougie, ou le signal exister d'un côté et pas de l'autre. Le test montre que le résultat
  d'ensemble ne dépend pas du volume (+979 R sans volume, +986 R avec).
- Entrée C : le robot entre à la première cotation à partir de 10:00, le script à la clôture de la bougie de 9:55. C'est le même instant.
- Sur TradingView, B et C s'exécutent à la clôture de la bougie du signal ; le robot entre à la première cotation de la
  bougie suivante. C'est le même prix à quelques dixièmes de point près.

## Ce que les tests donnent (rappel)
2018-2026, spread réel + 1 point de glissement : 273 trades par an, +986 R (v7 : +591 R), 9 années positives sur 9,
pire baisse 38 R (v7 : 22 R), pire journée −6,7 R (v7 : −3,2 R). À 2 points de glissement : +716 R, pire baisse 51 R.
La V8 a été trouvée sur tout l'historique (environ 770 essais) : c'est un candidat, pas une preuve. Aucun gain n'est garanti.

Fichiers : `Strategy-V8.mq5`, `Strategy-V8.pine`, `Strategy-V8.ex5` (déjà compilé, pour dépanner ; préfère F7 sur le .mq5).

---

# ORB v7 — notice

## Ce que c'est
La v6 de ton dépôt, plus trois règles (chacune avec son interrupteur dans les réglages, groupe « Filtres v7 ») :
1. **Mémoire** : après un trade pris qui finit à plus de +0,05 R, le signal suivant n'est pas pris (un seul).
2. **Aucun ordre les jours de décision de la Fed (FOMC).**
3. **Aucun ordre les jours fériés américains et demi-séances.**
Le risque par trade ne change pas. Tout le reste est identique à la v6 (environ 215 lignes modifiées sur 1 615 dans l'EA, 110 dans le script).

## Options (toutes coupées par défaut)
Trouvées en fouillant tout l'historique 2018-2026 (environ 650 essais au total) : ce sont des candidats, pas des preuves.
Chiffres rejoués comme l'EA les joue, 1 point de glissement ; v7 seule : 121 trades par an, +0,55 R, +591 R, pire baisse 22 R.

| Option | Ce qu'elle fait | Résultat dans les tests |
|---|---|---|
| Tendance H4 (DI+ contre DI−, 14) | Achat seulement si DI+ > DI− sur la dernière bougie H4 close, vente dans le cas inverse | 61 trades par an, +0,79 R, +425 R, pire baisse 23 R |
| SAR parabolique M5 (0,02 / 0,2) | Achat seulement si le SAR de la bougie de 9:30 est sous sa clôture, vente s'il est au-dessus | 102 trades par an, +0,66 R, +592 R, pire baisse 22 R |
| Sortie au temps (10:30, +0,5 R) | À 10:30, ferme un trade qui n'a ni stop à l'entrée ni pyramide et qui est sous +0,5 R | 118 trades par an, +0,58 R, +604 R, stops pleins 45 % au lieu de 55 %, pire baisse 26 R |
| Tendance H4 + SAR M5 | les deux filtres | 51 trades par an, +0,91 R, +413 R, pire baisse 18 R |
| Les trois | | 51 trades par an, +0,89 R, +399 R, gains ÷ pertes 2,46, stops pleins 46 %, pire baisse 18 R |

Un jour écarté par un filtre ne touche pas à la règle mémoire. Aucune option n'augmente le risque par trade.
Conseil : laisse-les coupées en réel tant que la démo ou TradingView ne t'ont pas montré le même effet sur tes propres données.
L'ancienne option « MA200 H1 » a été retirée : la tendance H4 fait mieux dans tous les tests.

## Avertissement
Depuis le 21 novembre 2026, `ORB-v7.mq5` est compilé avec MetaEditor (0 erreur, 0 avertissement) et `ORB-v7.pine` passe
l'analyseur de TradingView (0 erreur). Il n'a pas été vu en train de tourner : testeur de stratégie puis démo d'abord.

## MetaTrader 5
1. Hors séance et sans trade ouvert : retire ORB-v6 du graphique du Nasdaq.
2. Copie `ORB-v7.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor, touche F7.
3. Glisse ORB-v7 sur le graphique du Nasdaq, coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau, comme pour la v6.

À savoir :
- **Étrave** : la v7 écrit les mêmes fichiers que la v6, donc la page devrait continuer à fonctionner. Mais le bouton
  « Installer ou mettre à jour l'EA » réinstalle la **v6** : ne t'en sers pas tant que l'interface n'a pas été mise à jour.
- Les statistiques du panneau repartent de zéro (la v7 garde son propre état, pour ne pas reprendre un état de la v6).
- **Dates FOMC** : celles de 2018 à 2026 sont dans le code. Pour 2027 et après, saisis-les dans « Jours FOMC après 2026 »
  (format 2027.01.27, séparées par des virgules) dès que la Réserve fédérale les publie. Sans cela, l'EA trade ces jours-là.
- **Jour d'observation** : après un gain, l'EA envoie « PAS D'ORDRE aujourd'hui (règle mémoire) ». Si la cassure se
  déclenche, il envoie « SIGNAL SAUTÉ » et reprend le lendemain. Sinon « PAS DE SIGNAL », et la règle reste en attente.
- Au premier lancement, la mémoire est vide : le premier signal est pris, même si ton dernier trade en v6 était gagnant.

## TradingView
Colle `ORB-v7.pine` dans l'éditeur Pine sur un graphique M5 du NAS100 avec les bougies hors séance, comme pour la v6.
Supprime et recrée l'alerte. Pour voir l'effet de la mémoire : compare les résultats avec la case « Mémoire » cochée puis décochée.

Écart connu entre l'EA et le script un jour d'observation : l'EA regarde les cotations une par une (le côté bloqué touché
d'abord annule le signal) ; le script ne voit que des bougies de 5 minutes (si les deux côtés sont touchés dans la même
bougie, il compte le signal comme déclenché). C'est rare.

## reference-v7.json
Les 1 073 trades de la v7 rejoués sur 2018-2026 (spread réel + 1 point de glissement), au même format que
`etrave/reference.json`. Si tu veux que la page « Risque » d'Étrave simule la v7, remplace ce fichier par celui-ci
(garde une copie de l'ancien). L'ancien fichier utilisait 0,1 point de glissement : celui-ci est plus prudent.

## Ce que les tests donnent (rappel)
2018-2026, 1 point de glissement : +0,55 R par trade, 121 trades par an, pire baisse 22 R, 9 années positives sur 9.
Coffre-fort 2025-2026 : +0,54 R par trade sur 217 trades. Détail dans `rapport.md`. Aucun gain n'est garanti.
