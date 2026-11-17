# Revue du code : liste complète des constats

Six lecteurs indépendants, un par domaine, puis un vérificateur par domaine chargé de **réfuter** chaque constat en relisant le code.

- **Verdict** : *confirmé*, *plausible* ou *réfuté*.
- **Sévérité** : celle qui a été corrigée après vérification.
- **Oublis** : les « oublis » sont les problèmes ajoutés par le vérificateur.

Les constats marqués ★ ont en plus été contrôlés à la main pendant la revue, dans le code ou dans ccxt 4.5.93 (voir RAPPORT.md).

Les numéros de ligne des domaines « Stratégie BTC » et « Bot BTC : exécution » sont parfois décalés : un lecteur a numéroté des fichiers mis bout à bout. Le nom de la fonction citée fait foi.

## EA MetaTrader 5 comparé aux règles écrites et au script Pine

### EA-01 · majeur · confirme : Mauvais réglage d'heure d'été détecté mais non bloquant : range pris sur la mauvaise bougie environ 18 jours par an

`nasdaq/ORB-v6.mq5` : 217-229, 1373-1382, 1532-1535

**Constat.** ToNY() convertit l'heure serveur en heure de New York à partir de InpSrvGMT/InpSrvDST. J'ai réimplémenté ServerOffsetSec/ToNY/UsDst/EuDst en Python et je les ai comparés à zoneinfo pour chaque 9:30 NY réel entre 2018 et nov. 2026. Quand le réglage correspond au serveur, la conversion est juste : 0 erreur sur 2326 jours, aussi bien pour un serveur NY+7 réglé US que pour un serveur GMT+2/+3 à l'heure d'été européenne réglé EU. En cas d'erreur de réglage (US/EU inversés), 160 jours sur 2326 sont faux, soit les 3 semaines de mars et la semaine fin octobre/début novembre de chaque année. CheckClock() (l.1378-1380) et OnInit (l.1533-1535) ne font qu'afficher une alerte : gClockOk n'est jamais testé dans Setup() ni CheckEntries(). De plus, CheckClock ne tourne que dans OnTimer, donc seulement si InpUseUI est vrai et hors testeur.

**Scénario.** Le courtier est à GMT+2/+3 avec l'heure d'été européenne et l'EA garde le réglage par défaut SRV_DST_US. Entre le 2e et le dernier dimanche de mars, l'EA croit être à 9:30 NY alors qu'il est 10:30 NY. Le « range » est alors la bougie de 10:30, la fenêtre d'élan est 10:00-10:30 et la sortie « 15:50 » tombe à 16:50, soit environ 18 trades par an sur la mauvaise bougie, alors que l'alerte rouge s'affiche.

**Vérification.** Relu mq5:217-229 : ServerOffsetSec applique UsDst ou EuDst selon InpSrvDST, puis ToNY applique UsDst. Si le réglage est faux (serveur à l'heure d'été européenne, EA réglé SRV_DST_US), l'heure NY calculée a 1 h de retard pendant les semaines où les deux pays ne sont pas à la même heure. L'EA croit alors être à 9:30 alors qu'il est 10:30 à New York. gClockOk (l.162, 1381) n'est lu que par WriteState (l.1423). Setup, CheckEntries, OnNewBar et la sortie de 15:50 ne le testent jamais. L'alerte de OnInit (l.1533-1535) ne fait qu'afficher un message. CheckClock n'est appelé que dans OnTimer (l.1571), qui s'arrête dès la l.1563 si InpUseUI est faux ou dans le testeur. Je n'ai pas refait le décompte de 160 jours, mais l'ordre de grandeur (3 semaines en mars et 1 semaine fin octobre, chaque année) correspond aux règles américaines et européennes. Un réglage faux reste plausible, car le README (l.49-51) laisse ce choix à l'utilisateur. Pendant ces jours, tout se décale : la bougie du range, la fenêtre d'élan, et la sortie, qui tombe à 16:50 au lieu de 15:50.

### EA-04 · majeur · plausible : RSI lu au premier tick de 9:35 sans vérifier que l'indicateur a calculé la nouvelle bougie

`nasdaq/ORB-v6.mq5` : 826-828, 854-856, 1519

**Constat.** Setup() lit CopyBuffer(hRSI, 0, 1, 1, rsi), soit l'index 1 du RSI M5 (Wilder, PRICE_CLOSE sur les bougies bid), dès le tick qui ouvre la bougie de 9:35. Ce choix est conforme à la règle 2 : RSI de la bougie de 9:30 clôturée. Mais l'EA ne vérifie que le nombre de valeurs copiées, jamais BarsCalculated(hRSI) face à Bars(_Symbol, PERIOD_M5). En réel, un indicateur créé par iRSI est calculé de façon asynchrone. Au premier tick d'une nouvelle bougie, son tampon peut ne pas encore contenir la bougie de 9:35, et l'index 1 renverrait alors le RSI de 9:25. Le code ne lit pas non plus le RSI par l'heure (gOrTime), ce qui aurait évité ce risque. Hors de ce point, la mesure est conforme : Wilder comme ta.rsi, sur la clôture, bougie clôturée.

**Scénario.** Le RSI de 9:25 vaut 52 et celui de 9:30 vaut 48. L'EA autorise l'achat et bloque la vente, l'inverse du script Pine et du backtest. Le défaut ne touche que les jours où le RSI est proche de 50, mais il rend le comportement réel différent du test sans que rien ne le signale. À vérifier en démo en journalisant le RSI lu face à celui affiché sur le graphique.

**Vérification.** Relu mq5:818-828 et 1519. Le RSI est lu à l'index 1, au premier tick de la bougie de 9:35. L'EA ne contrôle ni BarsCalculated(hRSI) ni l'heure de la valeur lue. Dans MT5, les indicateurs d'un symbole sont calculés dans leur propre fil, et l'EA dans un autre. MetaQuotes recommande de tester BarsCalculated avant CopyBuffer, et des valeurs « en retard d'une bougie » au premier tick d'une nouvelle bougie sont souvent signalées. Ma certitude reste moyenne : je ne sais pas si, dans ce cas, CopyBuffer échoue (et l'EA réessaie, l.828) ou renvoie la valeur de 9:25. Si c'est la valeur de 9:25, le filtre de sens s'inverse sans aucun message. Le reste de la mesure est conforme : Wilder, sur la clôture, bougie clôturée de 9:30. À vérifier en démo en journalisant le RSI lu et celui du graphique.

### EA-05 · majeur · confirme : Achat déclenché par l'ask sur un high mesuré en bid : des trades que le graphique (Pine, backtest bid) ne prend pas

`nasdaq/ORB-v6.mq5` : 598-604, 832-833, 993-994

**Constat.** gOrH et gOrL sont le high et le low bid de la bougie de 9:30 (bougies MT5 en bid). Le Buy Stop est exécuté quand l'ask atteint gOrH. Si l'ask est déjà au-dessus à 9:35, PlaceStop renvoie false et CheckEntries achète au marché dès ask >= gOrH (l.993). La règle 3 dit « achat sur le high ». Le README admet « un spread plus tôt », mais ne dit pas que certains jours l'EA trade alors que le prix du graphique ne casse jamais le high. Mesuré sur les données Dukascopy M1 bid/ask 2018-2026 (2284 jours, avant filtres) : spread médian à 9:35 de 1,21 pt (P90 1,51), range 9:30 médian de 42,7 pts. Sur 113 jours (4,9 %), l'ask dépasse déjà gOrH à l'ouverture de 9:35 alors que le bid est en dessous, d'où un achat immédiat au marché. Sur 59 jours (2,6 %), l'ask touche gOrH entre 9:35 et 9:44 sans que le bid l'atteigne : ce sont des trades réels qu'un backtest sur le bid ou le script Pine n'a pas.

**Scénario.** Range 9:30 de 20000,0 à 20040,0 en bid, clôture à 20039,5 et spread de 1,2. À 9:35 l'ask vaut 20040,7 : achat immédiat alors que le bid ne casse jamais 20040. Le trade finit souvent au stop (-1R) ou au stop à l'entrée, et il n'existe pas dans le backtest, qui est ainsi trop optimiste ou au moins non représentatif de ces jours-là.

**Vérification.** Relu mq5:598-604, 832-833 et 993-994. gOrH est le high bid de la bougie M5. Le Buy Stop est déclenché par l'ask, et si l'ask est déjà au niveau ou à moins de gap, PlaceStop renvoie false et l'EA achète au marché dès ask >= gOrH. Le README (l.111) dit « un spread plus tôt », mais ne dit pas que cela crée des trades qui n'existent pas sur le prix du graphique. Je n'ai pas recalculé les 113 et 59 jours sur Dukascopy : ces chiffres restent à confirmer. La logique, elle, est juste. Ces trades sont par construction des cassures ratées sur le bid, donc probablement perdants. Un backtest fidèle à l'EA doit déclencher les achats sur l'ask.

### EA-02 · mineur · confirme : Envois WhatsApp/Telegram synchrones dans OnTick/OnTimer : l'EA est bloqué jusqu'à 5 s par message et par canal

`nasdaq/ORB-v6.mq5` : 371, 387, 401-402, 424-438, 1336-1337, 1572, 1612

**Constat.** FlushNotifs() appelle WebRequest (délai maximal de 5000 ms) pour chaque message en file (jusqu'à QUEUE_MAX=20), sur deux canaux, à la fin de OnTick et dans OnTimer. Un EA MT5 n'a qu'un seul fil : tant que l'envoi dure, aucun tick n'est traité. Le commentaire des lignes 401-402 dit qu'« un envoi lent ne retarde plus ni l'entrée ni un stop ». C'est vrai pour le tick en cours, faux pour les suivants : l'annulation quand le côté bloqué est touché (l.971), l'entrée au marché du côté surveillé (l.993-1000), le stop virtuel gVStop (l.1605), le stop remonté refusé par le courtier et la sortie de 15:50 (l.1608) attendent tous la fin des envois. L'essai Telegram (l.1336) est aussi synchrone et n'est pas bloqué pendant un trade ouvert (gIn n'est pas testé).

**Scénario.** À 9:35, le message « ORDRES PLACÉS » part juste après la pose des ordres. Si api.telegram.org ne répond pas, l'EA reste sourd 5 à 10 s. Sur un jour où seul l'achat est permis, le bas du range peut être touché pendant ce temps : l'EA ne supprime pas le Buy Stop chez le courtier, qui peut ensuite être exécuté alors que la règle 3 interdit le trade. Si 20 messages sont en attente avec deux canaux en échec, le blocage peut durer jusqu'à 200 s.

**Vérification.** Relu mq5:365-438, 1336-1337, 1572 et 1612. WebRequest est synchrone, avec un délai de 5000 ms, et FlushNotifs boucle sur toute la file pour chaque canal. Un EA MT5 traite ses événements l'un après l'autre : pendant l'envoi, aucun tick n'est traité. Le commentaire des l.401-402 est donc trompeur, et l'essai Telegram (l.1336) part même pendant un trade ouvert. J'abaisse la sévérité à mineur. Le stop initial, le stop remonté (s'il est accepté) et l'expiration datée sont exécutés côté courtier, et une réponse Telegram arrive normalement en moins d'une seconde. Pour que la règle 3 soit violée, il faut cumuler trois conditions pendant un blocage de quelques secondes : le côté bloqué est touché, le prix revient, puis il casse l'autre côté du range dans la même bougie M5. Sinon, le contrôle de clôture de bougie (l.1141) annule quand même la journée. Le blocage de 200 s suppose 20 messages en file et deux canaux en échec : c'est théorique.

### EA-03 · mineur · confirme : Validité des ordres : repli sur GTC avant DAY, et toute position au numéro magique est adoptée sans contrôle d'heure

`nasdaq/ORB-v6.mq5` : 605-607, 756-797, 1137-1144

**Constat.** PlaceStop choisit ORDER_TIME_SPECIFIED (expiration à 9:45 serveur) si le courtier l'accepte, sinon ORDER_TIME_GTC, et ORDER_TIME_DAY seulement en dernier. Avec GTC, seule l'EA annule l'ordre, au premier tick de la bougie de 9:45 (OnNewBar, l.1140). Si MetaTrader ou le VPS s'arrête après 9:35, le Buy Stop / Sell Stop reste posé, éventuellement plusieurs jours. Au redémarrage, SyncPosition (l.759) adopte toute position du symbole portant InpMagic, sans vérifier qu'elle a été ouverte avant 9:45 ni le jour même, et calcule gSL/gRisk à partir de gOrH/gOrL rechargés.

**Scénario.** Le courtier n'accepte pas l'expiration datée et MT5 plante à 9:38. L'ordre GTC posé au high est exécuté à 14:10, ou le lendemain matin sur un écart d'ouverture, avec le stop de l'ancien range. Le trade sort des règles (validité de 2 bougies, un trade par jour). Si l'exécution a lieu la nuit, la position peut perdre bien plus que 1R.

**Vérification.** Relu mq5:605-607 : l'ordre de préférence est SPECIFIED, puis GTC, puis DAY. Avec GTC, exp vaut 0 et seule l'EA annule l'ordre, à la l.1140. SyncPosition (l.759-786) adopte toute position portant InpMagic, sans contrôle d'heure. Correctif au scénario : si l'EA redémarre le même jour avant toute exécution, le premier tick appelle OnNewBar (gLastBar=0, l.1539). Avec late vrai, la l.1143 annule alors l'ordre resté posé. Si l'EA redémarre un autre jour avec une position adoptée, la l.1608 (NYDate != gPosDay) la ferme aussitôt. Le risque se limite donc à une exécution survenue pendant que MT5 était arrêté. Il faut en plus un courtier qui refuse l'expiration datée, ce qui est rare pour les CFD sur indices. Le défaut de code est réel, mais sa probabilité est faible : mineur.

### EA-06 · mineur · confirme : Juneteenth traité comme férié avant 2022, plus 3 autres faux jours courts (EA et Pine)

`nasdaq/ORB-v6.mq5` : 291-311 (Juneteenth l.306, 31 décembre l.305, jeudi avant un 4 juillet samedi l.302) ; nasdaq/ORB-v6.pine:180-191

**Constat.** J'ai comparé ShortDay() (et isShortDay du Pine, même règle) au calendrier officiel XNYS d'exchange_calendars 4.13.3, de 2008 à 2026. Juneteenth est appliqué toutes les années, alors que la NYSE ne le chôme que depuis 2022. L'EA sort donc à 12:45, sans pyramide après, des jours de séance normale : 2018-06-19, 2019-06-19, 2020-06-19 et 2021-06-18 (Juneteenth observé). S'y ajoutent 2021-12-31 (1er janvier un samedi : la NYSE était ouverte toute la journée), 2020-07-02 et 2026-07-02 (jeudi « par prudence » : séances normales selon XNYS). Cela fait 7 jours faux sur 2018-2026. Avant 2018, il y en a 13 autres : Juneteenth 2008 à 2017, 2009-07-02, 2015-07-02 et 2010-12-31. Tous les autres fériés et demi-séances de 2008 à 2026 sont justes, vendredi saint et Thanksgiving compris.

**Scénario.** Le 19 juin 2019, un achat en tendance est coupé à 12:45 au lieu de 15:50, et la pyramide est interdite après 12:45. L'effet porte sur au plus 7 trades sur 2018-2026 et 20 en comptant 2008-2017 (test hors échantillon d'avant 2018). Il est petit, mais à reproduire tel quel dans tout backtest qui prétend imiter l'EA.

**Vérification.** La ligne mq5:306 contient Observed(MakeDate(y,6,19)) sans condition d'année, et la ligne pine:189 est identique. La NYSE ne chôme Juneteenth que depuis 2022 : le 18 juin 2021 était une séance normale. La l.305 (Observed(MakeDate(y+1,1,1))) donne 2021-12-31, un jour d'ouverture complète, car la NYSE ne reporte pas un 1er janvier tombé un samedi. Le README l'admet d'ailleurs à la l.132. La l.302 traite par prudence le jeudi 2 juillet comme demi-séance quand le 4 tombe un samedi (2020 et 2026). D'après mes connaissances, ce n'était pas une demi-séance en 2020 ni en 2015, et le calendrier NYSE 2026 ne la mentionne pas, avec une certitude moyenne pour 2026. Les autres règles relues (MLK, Presidents' Day, vendredi saint par l'algorithme de Butcher, Memorial Day, Labor Day, Thanksgiving, veille de Noël, veille du 4 juillet du mardi au vendredi) sont correctes.

### EA-07 · mineur · confirme : Deuils nationaux absents du calendrier (5 déc. 2018 Bush, 9 jan. 2025 Carter)

`nasdaq/ORB-v6.mq5` : 256-258, 305-310

**Constat.** La NYSE était fermée le 2018-12-05 et le 2025-01-09, et ShortDay() renvoie false ces jours-là. Dans les données Dukascopy, les cotations s'arrêtent à 9:29 NY le 5 décembre 2018 et à 9:28 le 9 janvier 2025, puis reprennent à 18:00 : il n'y a pas de bougie de 9:30, donc Setup() ne prépare rien et il n'y a aucun trade. Pas d'effet avec ces données. De même, les vendredis saints avec chiffres de l'emploi (2021-04-02, 2023-04-07) n'ont pas de cotation après 9:14/9:15, donc pas de trade. Avant 2018, Sandy (2012-10-29/30) n'est pas non plus dans le calendrier.

**Scénario.** Un courtier qui publierait des cotations indicatives pendant la suspension des futures pourrait former une bougie de 9:30 : des ordres seraient alors posés sur un marché sans liquidité, avec une sortie à 15:50 alors que le sous-jacent est arrêté.

**Vérification.** Relu mq5:256-258 et 305-310 : aucune liste d'exceptions. Le README (l.130-131) le reconnaît. Le 5 décembre 2018 et le 9 janvier 2025, les futures CME sur indices ont cessé de coter vers 9:30 ET. Il est donc cohérent qu'aucune bougie de 9:30 n'existe et qu'aucun trade n'ait lieu. Je n'ai pas vérifié moi-même les heures de dernière cotation dans Dukascopy.

### EA-08 · mineur · confirme : Le stop des ventes, le stop à l'entrée et le stop de la pyramide coûtent un spread dans l'EA, zéro dans le Pine (écart absent du tableau du README)

`nasdaq/ORB-v6.mq5` : 599, 1031-1039, 1052-1053, 1605 ; README.md:109-117

**Constat.** Une vente a son stop à gOrH (high bid), déclenché par l'ask : la vente est stoppée quand le bid vaut gOrH moins le spread, un spread plus tôt que dans le Pine. Le stop au prix d'entrée (RaiseStop(gEntry)) d'un achat ouvert à l'ask est déclenché sur le bid, et inversement pour une vente : chaque sortie « Stop à l'entrée » perd donc environ un spread plus le glissement, alors que dans le Pine strategy.exit(stop = cur.entry) sort à 0. Le message de la l.1130 (« ne peut plus perdre que les frais ») et le tableau README (l.109-117), qui ne cite que les seuils et le côté bloqué, passent ce point sous silence.

**Scénario.** Avec un spread médian de 1,2 pt pour un range médian de 42,7 pts (Dukascopy), chaque stop à l'entrée coûte environ 0,03R, et chaque stop initial de vente est touché 1,2 pt plus tôt. Ces sorties ne doivent pas être comptées à 0R dans un backtest.

**Vérification.** mq5:599 : le stop d'une vente est à gOrH (bid), déclenché par l'ask chez MT5. La perte en argent reste exactement le range (vente au bid gOrL, rachat à l'ask gOrH), mais le stop est touché quand le bid vaut gOrH moins le spread, donc plus souvent. Le stop à l'entrée (l.1131, RaiseStop(gEntry)) est déclenché sur le prix opposé et coûte environ un spread. Dans le Pine (l.483), il sort à l'entrée, au glissement près. Le tableau du README (l.109-117) ne le dit pas. L'effet par sortie est faible, mais il va toujours dans le même sens.

### EA-09 · mineur · confirme : Pine : la règle « côté bloqué touché d'abord » est ignorée quand la cassure et le côté bloqué tombent dans la même bougie

`nasdaq/ORB-v6.pine` : 510-521, 582-586

**Constat.** Le Pine ne contrôle oppFirst qu'à la clôture d'une bougie, et seulement si strategy.position_size == 0. Si une bougie de 9:35 ou de 9:40 touche le côté bloqué puis le niveau permis, le simulateur de TradingView exécute quand même l'ordre stop, selon son chemin supposé dans la bougie (ouverture, plus haut, plus bas, clôture). L'EA, qui travaille au tick (l.971), annule la journée. Le Pine prend donc des trades que l'EA et la règle 3 refusent.

**Scénario.** Achat seul permis, la bougie de 9:35 descend sous orL puis monte au-dessus de orH. Le Pine achète, l'EA renonce. Un backtest construit comme le Pine surestime le nombre de trades sur les jours très volatils.

**Vérification.** pine:510 : le contrôle n'a lieu que si strategy.position_size == 0, et seulement à la clôture de la bougie (oppFirst, l.512). Si l'émulateur de TradingView suppose le chemin ouverture, plus bas, plus haut, clôture, l'ordre stop au high est exécuté dans la bougie. À la clôture, la position existe déjà et le contrôle est sauté. L'EA (mq5:971) annule au tick. Le Pine prend donc des trades que la règle 3 interdit.

### EA-10 · mineur · confirme : Stop de la pyramide calculé sur le prix affiché avant l'ordre, sans plancher : le pire cas -1R n'est pas garanti

`nasdaq/ORB-v6.mq5` : 1052-1054, 1079, 1090, 1026-1040

**Constat.** lock = ask (ou bid) au premier tick de la bougie suivante moins 1R. Il ne part pas de trade.ResultPrice() (apx, lu mais pas utilisé pour le stop), contrairement au « prix réel de l'ajout » du README, et rien ne l'empêche de tomber sous +1R ni sous le stop déjà à l'entrée. RaiseStop pose ce stop même s'il est moins bon que le précédent (gVStop est écrasé). Si le prix recule entre la clôture à +2R et le premier tick, ou si l'ajout glisse, le pire cas du trade devient lockR - 2 < -1R. Le Pine, qui calcule close - 1R, ne peut pas montrer ce cas.

**Scénario.** Clôture à +2,0R et premier tick à +1,5R après une annonce : lock = +0,5R. Si le stop est ensuite touché, le résultat est 0,5 - 2×1 = -1,5R, plus le glissement des 3 unités, au lieu du -1R annoncé. C'est rare (l'écart entre la clôture et l'ouverture M1 suivante est en général minime), mais possible les jours d'annonce.

**Vérification.** mq5:1052-1053 : lock est calculé sur l'ask ou le bid lu avant l'ordre, pas sur apx (l.1079, lu seulement pour le message). RaiseStop (l.1032, 1039) écrase gVStop et SetStopAll modifie le stop dans les deux sens, sans plancher. DoPyramid n'est déclenché que par r[1].close (l.1110-1112), sans contrôle du prix courant. Le calcul du pire cas (0,5 - 2 = -1,5R) est juste. C'est rare, car il faut un écart de plus de 0,5R entre la clôture et le tick suivant.

### EA-11 · mineur · confirme : 1R des seuils = |exécution − stop|, mais 1R du résultat = taille × range : les deux divergent pour une entrée au marché loin du niveau

`nasdaq/ORB-v6.mq5` : 767-771, 915, 1110, 1127, 1053, 733 ; nasdaq/ORB-v6.pine:380-382

**Constat.** La règle 4 définit 1R comme taille de départ × range. Les seuils de +1,5R et de +2R et l'écart de la pyramide utilisent pourtant gRisk = |gEntry - gSL| (prix d'exécution réel), alors que le R affiché vaut net / gRiskMoney (lots × range). Le Pine fait de même (risk contre usd). Quand l'EA entre au marché quelle que soit la distance (lancé entre 9:35 et 9:40, ou ouverture au-delà du niveau, cas admis dans les Limites du README), la perte au stop dépasse 1R et les seuils s'éloignent d'autant.

**Scénario.** Range de 30 pts, achat au marché 20 pts au-dessus du high : perte au stop de 50 pts, soit -1,67R affichés, et +1,5R placé à 75 pts au lieu de 45.

**Vérification.** mq5:769 : gRisk = |gEntry - gSL|, ce qui inclut le glissement et l'écart d'une entrée au marché. mq5:915 : gRiskMoney = lots × range. Les seuils des l.1110, 1127 et 1053 utilisent gRisk, le R affiché (l.733) utilise gRiskMoney. Le Pine (l.380-382) fait la même chose (risk contre usd). L'écart est négligeable pour une exécution normale de l'ordre stop, important pour une entrée au marché loin du niveau (cas décrit dans les limites du README, l.133-135).

### EA-12 · mineur · confirme : Filtre d'élan en >= au lieu de « dépasse » (strict)

`nasdaq/ORB-v6.mq5` : 857-858 ; nasdaq/ORB-v6.pine:546-547 ; README.md:22-23

**Constat.** extL = gOrH >= pH et extS = gOrL <= pL. La règle 2 dit « son high dépasse le plus haut de 9:00-9:30 », donc une comparaison stricte. L'EA et le Pine sont cohérents entre eux, mais pas avec le texte. Le cas d'égalité est plus fréquent chez un courtier qui cote à 1 ou 2 décimales.

**Scénario.** Le high de 9:30 égale exactement le plus haut de 9:00-9:25 : l'achat est permis par le code et interdit par la règle écrite.

**Vérification.** mq5:857-858 et pine:546-547 utilisent >= et <=, alors que la règle 2 du README dit « dépasse » et « sous ». L'EA et le Pine sont cohérents entre eux. Un cas d'égalité exacte au centième près est rare.

### EA-13 · mineur · plausible : Seuils des ventes calculés avec MqlRates.spread, qui n'est pas l'ask à la clôture ni au plus bas

`nasdaq/ORB-v6.mq5` : 1110, 1126, 1141

**Constat.** Pour mesurer les seuils « sur l'ask » des ventes, l'EA ajoute r[1].spread*_Point à la clôture ou au plus bas bid. Le champ spread d'une bougie MT5 est une seule valeur par bougie : en général le spread minimal, ou celui d'un tick, selon le courtier. Ce n'est ni l'ask à la clôture ni le plus bas de l'ask. Le +2R et le +1,5R des ventes sont donc légèrement plus faciles à atteindre que la règle « mesurés sur l'ask » ne le dit.

**Scénario.** Spread minimal de la bougie 0,8, spread à la clôture 2,5 : la pyramide de vente se déclenche avec 1,7 pt d'avance sur la règle. L'effet reste faible par rapport à un range médian de 42 pts.

**Vérification.** mq5:1110, 1126 et 1141 ajoutent r[1].spread*_Point à la clôture, au plus bas ou au plus haut bid. MqlRates.spread est une seule valeur entière par bougie. De mémoire, MT5 y stocke en général le spread minimal de la bougie, mais la documentation ne le précise pas et certains courtiers mettent 0. Le sens de l'erreur (seuils des ventes atteints un peu plus tôt) est donc plausible, sans certitude. L'effet est faible.

### EA-14 · mineur · confirme : Côté bloqué et « premier exécuté annule l'autre » assurés par l'EA seul : ordres doubles et choix de la mauvaise position

`nasdaq/ORB-v6.mq5` : 537-548, 638-651, 759-786, 971-975

**Constat.** Les deux ordres stop sont posés chez le courtier sans OCO. C'est l'EA qui supprime l'ordre restant, au tick suivant (SyncPosition puis DeletePendings) ou quand le côté bloqué est touché. Si les deux ordres sont exécutés entre deux ticks traités par l'EA (voir EA-02), FindPos parcourt les positions de la dernière à la première et adopte la plus récente. CloseOpposite ferme alors la première, l'inverse de la règle. Le résultat de la position fermée par CloseOpposite n'est compté ni dans RecordClose ni dans le journal (seuls gPosId et gPosId2 le sont). En compte netting, la seconde exécution annule ou retourne la position.

**Scénario.** Range très étroit et forte volatilité à 9:36 : achat puis vente exécutés en 1 s pendant un envoi Telegram. L'EA garde la vente et ferme l'achat au marché, avec deux spreads de perte non journalisés.

**Vérification.** mq5:537-548 : FindPos part de la fin de la liste, et la liste des positions est en pratique dans l'ordre d'ouverture, même si la documentation ne le garantit pas. Il renvoie donc la plus récente. CloseOpposite (l.638-651) ferme alors l'autre, la première exécutée, contrairement à la règle 3. RecordClose (l.706-708) ne compte que gPosId et gPosId2 : la position fermée par CloseOpposite n'apparaît ni dans les statistiques ni dans le CSV. Il n'y a pas d'OCO côté courtier. Le cas suppose que les deux ordres soient exécutés entre deux ticks traités par l'EA : il est rare.

### EA-15 · mineur · confirme : Trade exécuté puis stoppé sans que l'EA le voie : non journalisé, et deuxième trade possible le même jour

`nasdaq/ORB-v6.mq5` : 981-996

**Constat.** Si un ordre posé chez le courtier est exécuté puis stoppé avant que l'EA traite un tick (EA bloqué, voir EA-02), gIn ne passe jamais à vrai. Si aucun côté n'est surveillé par l'EA (watch faux), l'EA conclut « ordre disparu » après 10 s, et le trade à -1R manque au journal et aux statistiques. Si l'autre côté est surveillé (watch vrai, prix près du low à 9:35), la condition bid <= gOrL reste active : le stop du premier trade se trouve justement à gOrL, donc l'EA vend au marché. C'est un deuxième trade le même jour.

**Scénario.** Rare : il faut que le prix fasse l'aller-retour de tout le range pendant que l'EA est bloqué. La conséquence est un deuxième -1R possible et un journal faux.

**Vérification.** mq5:981-996 : si la position a été ouverte et fermée sans que SyncPosition la voie, gIn reste faux. Sans côté surveillé, il n'y a aucun RecordClose et la journée est annulée, soit par la l.971 (le stop est à gOrL, donc le bid y est probablement), soit par la l.989. Si l'autre côté est surveillé (!gSrvS) et que bid <= gOrL, la l.995 envoie une vente au marché : c'est un deuxième trade. Il faut que l'EA ne traite aucun tick pendant tout l'aller-retour du range : c'est rare.

### EA-16 · mineur · confirme : InpDeviation = 30 points, soit 0,3 pt sur un NAS100 coté à 2 décimales

`nasdaq/ORB-v6.mq5` : 81, 648, 663, 1517

**Constat.** Le glissement maximal vaut 30 points. Chez un courtier en exécution instantanée ou à la demande, cela représente 0,3 pt d'indice à 9:35 ou à 15:50. Les entrées au marché du côté surveillé (3 refus et la journée est perdue, l.1010) et les fermetures (stop virtuel, 15:50, 12:45) risquent alors des refus de cotation en boucle. En exécution « au marché », ce paramètre est ignoré.

**Scénario.** Le compte est en exécution instantanée et le prix est déjà au-delà du niveau à 9:35 : trois refus de cotation et « ENTRÉE REFUSÉE », alors que la cassure a bien lieu.

**Vérification.** mq5:81 et 1517 : SetDeviationInPoints(30). Pour un symbole coté à 2 décimales, cela fait 0,3 pt d'indice. Le paramètre ne compte qu'en exécution instantanée ou à la demande, rare pour les CFD sur indices, qui sont en général exécutés au marché. Le compteur gFails (l.1008-1010) coupe la journée après 3 refus, ce qui peut arriver en une seconde.

### EA-17 · mineur · confirme : Pine : ajout de la pyramide et stop à l'entrée exécutés au prix exact de la clôture qui a décidé (optimiste)

`nasdaq/ORB-v6.pine` : 26, 404-416, 481-484

**Constat.** Avec process_orders_on_close = true, strategy.entry (la pyramide) est exécuté à la clôture même qui a servi à constater +2R, et lockPx vaut cette clôture moins 1R. En réel, on ne peut agir qu'au tick suivant (ce que fait l'EA). Les seuls coûts modélisés sont slippage=2 ticks, sans commission ni spread dans le script. Le README le signale pour le stop, mais un backtest de type Pine reste légèrement optimiste sur le prix de l'ajout.

**Scénario.** Les jours de forte tendance à la clôture de la bougie de l'ajout, l'ajout coûte quelques points de plus en réel. L'effet est faible, mais toujours dans le même sens.

**Vérification.** pine:26 active process_orders_on_close=true. tryPyramid (l.406-416) entre au marché et calcule lockPx sur la clôture même qui a constaté +2R. Ce n'est pas à proprement parler un regard vers le futur, plutôt une exécution au prix exact de la décision, légèrement optimiste. Les seuls coûts modélisés dans le script sont slippage=2 ticks, sans commission (le README, l.93, demande de l'ajouter à la main).

### EA-18 · mineur · confirme : RSI pas prêt pendant toute la bougie de 9:35 : la journée est perdue sans message

`nasdaq/ORB-v6.mq5` : 819-828

**Constat.** Si CopyBuffer échoue (renvoie false) jusqu'à la bougie de 9:40, Setup() voit r[1] = 9:35, différent de mOR, et renvoie true : gSetupDue est remis à faux sans notification et sans gDayTxt.

**Scénario.** Historique M5 en cours de téléchargement après un redémarrage à 9:34 : pas de trade et aucune trace du motif.

**Vérification.** mq5:823-828 : si CopyBuffer échoue jusqu'à 9:40, r[1] vaut 9:35, différent de mOR, et Setup renvoie true sans message ni gDayTxt. gDay n'est pas mis à jour, mais OnNewBar ne remet plus gSetupDue à vrai, car la bougie de 9:30 n'est plus r[1]. La journée est perdue sans trace. C'est peu probable.

### EA-19 · mineur · confirme : État non sauvegardé : gUsePyrToday, gSetupDue, gDelDue, gGoneAt

`nasdaq/ORB-v6.mq5` : 446-473

**Constat.** Après un redémarrage, une pyramide refusée par le courtier (gUsePyrToday = faux) peut être retentée, et une suppression d'ordre en échec (gDelDue) est oubliée. Le README le signale de façon générale (« l'état peut être ancien »).

**Scénario.** Pyramide refusée pour marge à 11:00, puis redémarrage de MT5 : nouvel essai à la bougie suivante, avec un nouveau message d'erreur ou un ajout pris plus tard que prévu.

**Vérification.** SaveState (mq5:446-459) ne sauvegarde ni gUsePyrToday, ni gSetupDue, ni gDelDue, ni gGoneAt, ni gFails. Après un refus de la pyramide, gPyr est remis à faux (l.1073) : si MT5 redémarre, gUsePyrToday reprend sa valeur par défaut (vrai) et la pyramide est retentée. Le README (l.139) le signale de façon générale.

### EA-20 · mineur · confirme : Arrondi du lot sans marge d'erreur (EA) contre avec marge (Pine)

`nasdaq/ORB-v6.mq5` : 885, 899-900

**Constat.** MathFloor(bal*risk/perLot/step)*step, sans le +0.000001 que le Pine utilise (l.114) : un quotient de 83,0 calculé 82,9999999 donne un pas de lot en moins. Avec un pas de 0,5, vd = round(0,30) = 0, et NormalizeDouble(lots, 0) peut arrondir au-dessus de la taille permise (limite admise par le README).

**Scénario.** Risque légèrement inférieur à la valeur demandée, ou supérieur avec un pas de volume inhabituel.

**Vérification.** La l.885 ne prévoit pas de marge d'erreur, contrairement à la l.1048 (pyramide) et au Pine (l.114). La l.899 arrondit -log10(0,5)=0,30 à 0, puis NormalizeDouble(2.5, 0) donne 3, soit 20 % de risque en plus. Un pas de 0,5 est inhabituel sur le NAS100.

### EA-21 · mineur · confirme : Trading des fériés pleins sur futures (pas d'ouverture du comptant à 9:30)

`nasdaq/ORB-v6.mq5` : 313, 1608 ; README.md:34

**Constat.** La règle 8 prévoit une sortie à 12:45 les jours fériés, donc des trades ces jours-là : c'est conforme. Mais lors des fériés NYSE où seuls les futures cotent jusqu'à 13:00 (MLK, Presidents' Day, Memorial Day, Juneteenth, 4 juillet, Labor Day, Thanksgiving), la « bougie d'ouverture » de 9:30 n'est pas une ouverture. Les données Dukascopy montrent des cotations jusqu'à 12:59 le 2018-01-15. Je le note comme caractéristique à évaluer à part dans le backtest, pas comme bug.

**Scénario.** Environ 7 jours par an où le range de 9:30 est celui d'un marché sans ouverture du comptant et peu liquide.

**Vérification.** C'est conforme à la règle 8 : sortie à 12:45 les jours fériés, donc des trades ces jours-là. Le ShortDay de la l.313 et la sortie de la l.1608 le confirment. Ce n'est pas un bug, mais une caractéristique à isoler dans le backtest, car la bougie de 9:30 de ces jours-là n'est pas une ouverture du comptant. Je n'ai pas vérifié dans les données les cotations jusqu'à 12:59 le 15 janvier 2018.

### EA-22 · mineur · confirme : Pine : identifiant de discussion Telegram personnel codé en dur par défaut

`nasdaq/ORB-v6.pine` : 63

**Constat.** tgChat a pour valeur par défaut "-1003571455927", un identifiant réel. Toute personne qui reçoit le script et crée une alerte avec son jeton tente d'écrire dans cette discussion. Inversement, le script partagé révèle l'identifiant.

**Scénario.** Script partagé à un tiers : ses alertes visent la discussion de l'auteur (échec, ou messages reçus si son bot en fait partie).

**Vérification.** pine:63 : input.string("-1003571455927", ...). C'est un identifiant de groupe ou de canal Telegram (préfixe -100), codé en dur par défaut, et le script partagé le révèle. Pour un tiers, l'alerte échoue (chat introuvable) sauf si son propre bot est membre de cette discussion.

### EA-23 · mineur · confirme : Bornes du risque différentes entre le Pine et l'EA

`nasdaq/ORB-v6.pine` : 31 ; nasdaq/ORB-v6.mq5:102-103

**Constat.** Le Pine a un minimum de 0,1 %, l'EA et l'interface un minimum de 0,05 % : un risque de 0,05 % réglé dans Étrave ne peut pas être reproduit dans le Pine.

**Scénario.** Lot affiché par le Pine différent de celui de l'EA pour un risque inférieur à 0,1 %.

**Vérification.** pine:31 a minval = 0.1, mq5:102 a RISK_MIN 0.05. C'est un écart d'interface, sans effet sur les règles.

### Oublis relevés par le vérificateur

- **mineur** · Niveau de stop minimal du courtier non contrôlé pour le stop initial : sur un range étroit, la journée est perdue après 3 refus (`nasdaq/ORB-v6.mq5` : 602-604, 611-618, 999-1018) : PlaceStop ne compare le gap (STOPS_LEVEL ou FREEZE_LEVEL) qu'à la distance entre le prix d'entrée et le marché, jamais à la distance entre l'entrée et le stop (le range). Si le range est plus petit que le niveau de stop minimal du courtier, BuyStop et SellStop sont refusés avec INVALID_STOPS, et la boucle ne réessaie que pour INVALID_FILL (l.617). Le côté passe alors en surveillance par l'EA, et trade.Buy ou trade.Sell avec le même stop est refusé à chaque tick : gFails atteint 3 en quelques ticks et la journée est perdue (« ENTRÉE REFUSÉE »). Cela touche justement les jours à range étroit, où 1R est petit, donc ceux qui donnent les plus gros multiples de R. Le backtest les garde. C'est plausible selon le courtier (niveau de stop non nul sur le NAS100).
- **mineur** · Ordre opposé resté posé (suppression refusée) au niveau du stop : stop puis retournement non suivi par l'EA (`nasdaq/ORB-v6.mq5` : 782, 1593-1594, 756-809, 638-651) : Les deux côtés sont permis (gPendDir=0) et le Buy Stop est exécuté. SyncPosition appelle DeletePendings (l.782). Si le courtier refuse la suppression (gDelDue), le Sell Stop reste posé à gOrL, exactement au stop de l'achat. Quand l'achat est stoppé, la vente est ouverte au même prix. SyncPosition voit alors tk > 0 avec gIn vrai et ne détecte ni la clôture de l'achat ni le changement de sens. CloseOpposite ferme la vente au tick suivant (au mieux un spread et du glissement perdus), et le résultat de cette vente n'est jamais journalisé. En compte netting, la position est retournée. C'est rare, mais ni EA-14 ni EA-15 ne couvrent ce cas, qui ne dépend pas d'un blocage de l'EA.
- **mineur** · Pine : la règle « côté bloqué touché d'abord » n'est contrôlée qu'à la clôture de la bougie, aussi pour la bougie de 9:40 et quel que soit l'ordre réel (`nasdaq/ORB-v6.pine` : 510-513) : Ce point complète EA-09. Même sans exécution dans la bougie, le Pine compare low <= orL sur toute la bougie à sa clôture. L'EA, lui, compare le bid au tick (mq5:971). Dans les deux outils, un backtest construit sur des bougies M5 ne peut pas savoir lequel des deux côtés a été touché en premier dans une bougie qui touche les deux niveaux. Tout backtest qui prétend reproduire l'EA doit donc descendre au tick ou au moins à la minute, et le dire.

### Non vérifié par le lecteur

- Compilation de l'EA et du script Pine : ni MetaEditor ni l'éditeur Pine ne sont disponibles ici. J'ai relu la syntaxe MQL5 (signatures CTrade BuyStop/SellStop/PositionClose, ternaires string, conversions) sans trouver d'erreur évidente, mais seule une compilation le confirmera. Le fichier .mq5 est en UTF-8 avec BOM.
- Calcul asynchrone d'iRSI au premier tick d'une nouvelle bougie (EA-04) : risque connu de MT5, non reproduit faute de terminal. À vérifier en démo en journalisant BarsCalculated(hRSI) et la valeur lue.
- Contenu exact de MqlRates.spread (minimal ou dernier tick) chez le courtier visé (EA-13).
- Modes d'expiration (SYMBOL_EXPIRATION_MODE) et d'exécution (instantanée ou au marché) acceptés par le courtier (EA-03, EA-16).
- Comportement exact du simulateur TradingView pour un ordre stop posé à la clôture avec process_orders_on_close=true quand la clôture égale le niveau (exécution sur la bougie de 9:30 elle-même ?).
- Statut NYSE du 2026-07-02 : séance normale selon exchange_calendars 4.13.3, sans confirmation par une source officielle.
- Horaires réels d'un courtier CFD lors des deuils nationaux et des vendredis saints : seules les données Dukascopy ont été contrôlées (pas de bougie de 9:30 ces jours-là).
- Je n'ai mesuré qu'avant filtres les jours de déclenchement par l'ask seul (113 et 59 jours, EA-05) : leur effet en R sur la stratégie filtrée relève du backtest, pas de cette revue de code.
- Je n'ai pas exécuté le code de l'EA : la conversion d'heure, le calendrier et l'écart spread/range ont été vérifiés par une réimplémentation Python (/tmp/claude-0/ea/cal.py, /tmp/claude-0/ea/tz.py, /tmp/claude-0/ea/spr.py) sur les données donnees/nas100 (Dukascopy M1 bid et ask).

## EA MetaTrader 5 : compilation et exécution

### EA-01 · majeur · confirme : Ordres stop sans expiration fiable : GTC préféré à DAY, et aucun ordre supprimé à l'arrêt de l'EA

`nasdaq/ORB-v6.mq5` : 605-607, 1551-1557

**Constat.** PlaceStop choisit le type d'expiration ainsi : `tt = (em & SYMBOL_EXPIRATION_SPECIFIED) != 0 ? ORDER_TIME_SPECIFIED : (em & SYMBOL_EXPIRATION_GTC) != 0 ? ORDER_TIME_GTC : ORDER_TIME_DAY;`. Si le courtier n'accepte pas d'expiration à une heure donnée, l'EA prend donc GTC (valable jusqu'à annulation) avant DAY, c'est-à-dire le pire choix. La fin de validité de 9:45 ne dépend plus alors que de l'EA (OnNewBar `late`, CancelDay). OnDeinit (1551-1557) ne supprime aucun ordre en attente. Si l'EA est retiré, recompilé hors séance ou si le terminal ou le VPS s'arrête entre 9:35 et 9:45, les Buy Stop et Sell Stop restent chez le courtier avec leur seul stop.

**Scénario.** Courtier sans SYMBOL_EXPIRATION_SPECIFIED (seulement GTC|DAY) et VPS qui redémarre à 9:38. Le Buy Stop GTC est exécuté à 11:20, voire un autre jour. Personne ne gère la position : pas de stop au prix d'entrée, pas de sortie à 15:50, seul le stop de l'autre côté du range protège. Elle passe donc la nuit. Un gap de NAS100 à l'ouverture (souvent 0,5 à 1,5 %) contre un range typique de 0,15 à 0,3 % franchit le stop et coûte plusieurs R : 3 à 5R à 0,5 % de risque, soit 1,5 à 2,5 % du compte. Même avec l'expiration à 9:45, un ordre exécuté entre la mort de l'EA et 9:45 n'aura aucune sortie de fin de journée.

**Vérification.** Ligne 606 relue : l'ordre de préférence est SPECIFIED, puis GTC, puis DAY, donc GTC passe avant DAY. Ligne 607 : exp vaut 0 hors SPECIFIED. OnDeinit (1551-1557) ne fait qu'EventKillTimer, IndicatorRelease et Comment : aucun OrderDelete. Si l'EA redémarre, LoadState remet gPend et OnNewBar (late, 1140) annule au premier tick : le risque concerne donc un EA qui ne revient pas. Le scénario (position exécutée sans gestion, sans sortie à 15:50, qui passe la nuit avec son seul stop au bord du range) est réaliste. Le choix de GTC avant DAY est bien le pire des deux. Les chiffres du gap sont des ordres de grandeur, pas des mesures.

### EA-02 · majeur · confirme : La sortie de 15:50, le stop au prix d'entrée refusé et le stop virtuel n'existent que si l'EA tourne et reçoit des cotations

`nasdaq/ORB-v6.mq5` : 1026-1040, 1597-1610, 669-686

**Constat.** La sortie de fin de journée (`NYMin(ny) >= FlatMin(ny)`, ligne 1608) et le stop virtuel gVStop (1605) ne sont contrôlés que dans OnTick. Le stop au prix d'entrée et le stop remonté après la pyramide ne sont posés chez le courtier que si `bid - sl > STOPS_LEVEL` (1038-1039) et si PositionModify réussit (FREEZE_LEVEL non vérifié). Sinon le seul garde-fou est gVStop, surveillé par l'EA. Après la pyramide, si SetStopAll échoue, l'unité de départ garde son ancien stop chez le courtier (bord du range ou prix d'entrée) : seul l'ajout porte le stop à `lock`.

**Scénario.** Le terminal se déconnecte à 13:00 avec une position à +2,5R, pyramide faite, et la modification du stop de l'unité de départ a été refusée (prix dans le niveau de gel). Le marché se retourne : l'ajout sort à `lock` (−2R sur 2 unités), mais l'unité de départ redescend jusqu'à son ancien stop au prix d'entrée (0R au lieu de +1R). Le trade finit à environ −2R au lieu de −1R. Sans reconnexion, rien ne sort à 15:50 : la position passe la nuit avec le risque de gap de EA-01.

**Vérification.** Code relu. La sortie de fin de journée (1607-1609) et gVStop (1605) ne vivent que dans OnTick. RaiseStop (1038) ne pose le stop chez le courtier que si bid-sl > STOPS_LEVEL ; sinon il ne fait rien, sans message, et seul gVStop reste. FREEZE_LEVEL n'est pas regardé. Un échec de SetStopAll n'est qu'imprimé (682). Correction au scénario : il est souvent PIRE que décrit. DoPyramid (1108) passe AVANT le contrôle du stop au prix d'entrée (1124), peut se déclencher dès la bougie d'entrée (r[1].time >= gFillBar) et met gBE=true (1050). Le stop de l'unité de départ chez le courtier peut donc encore être gOrL (-1R) au moment de l'ajout. Si SetStopAll échoue et que l'EA ne tourne plus, le pire cas vaut -1R (départ) -2R (ajout), soit -3R, et non -2R. La probabilité d'un refus de modification reste faible : lock est à gRisk du prix, bien au-delà du niveau des stops.

### EA-03 · majeur · confirme : Redémarrage après un plantage : état perdu ou périmé, ce qui permet une seconde pyramide, une clôture immédiate du trade du jour ou un trade compté deux fois

`nasdaq/ORB-v6.mq5` : 443-473, 537-548, 756-797, 1108-1113, 1597-1610

**Constat.** L'état est sauvé avec GlobalVariableSet, sans jamais appeler GlobalVariablesFlush(). Rien ne garantit son écriture sur disque avant un arrêt brutal du terminal (plantage, coupure du VPS). gUsePyrToday, gDelDue, gFails et gGoneAt ne sont pas sauvés du tout. Au redémarrage, SyncPosition (759-785) adopte toute position portant le bon magic quand gIn est faux. FindPos renvoie la dernière position de la liste, qui peut être l'AJOUT de la pyramide. L'adoption remet `gPyr=false` et `gUsePyrToday=true`, et prend `gSL = gOrL/gOrH` dans un état éventuellement d'un autre jour, ce qui fausse `gRisk = |gEntry-gSL|`. À l'inverse, si l'état chargé dit `gIn=true` (ancien trade), la position du jour n'est pas adoptée et gPosDay est périmé. La ligne 1608 `NYDate(ny) != gPosDay` ferme alors tout de suite le trade du jour (« Fin de journée »), et RecordClose relit l'historique de l'ancien gPosId, ce qui enregistre et notifie à nouveau un vieux trade.

**Scénario.** Le VPS plante à 11:00 alors que la pyramide est faite (3 unités). Au redémarrage, l'état sur disque est celui de la veille (gIn faux, range de la veille). L'EA adopte l'ajout comme « trade » avec gPyr=false. À la clôture suivante, si curR, calculé avec un gRisk faux, dépasse 2, il ajoute 2×gLots : 5 unités au lieu de 3. Il remonte aussi le stop de tout l'ensemble à un niveau calculé sur un R faux. Le pire cas n'est plus −1R mais environ −3R. Le README dit seulement que « l'état peut être ancien » : il ne dit pas qu'un second ajout est possible.

**Vérification.** Faits vérifiés : aucun appel à GlobalVariablesFlush. gUsePyrToday, gDelDue, gFails, gGoneAt et gSetupDue ne figurent pas dans SaveState (446-459). FindPos (537-548) part de la fin de la liste et renvoie la première position qui correspond, soit en pratique la plus récente (l'ajout). L'adoption (763-785) remet gPyr=false et gUsePyrToday=true, et calcule gSL et gRisk à partir de gOrL/gOrH chargés. Cas gIn=true périmé, vérifié pas à pas : SyncPosition n'entre dans aucune branche. CloseOpposite (1598) ferme même une position du jour de sens opposé à l'ancien gDir. Puis 1608 (NYDate != gPosDay) ferme tout, et RecordClose relit l'ancien gPosId et enregistre et notifie une seconde fois l'ancien trade. Certitude moyenne (de mémoire) sur la persistance : MT5 écrit les variables globales à la fermeture normale du terminal, et GlobalVariablesFlush existe pour forcer l'écriture. Après un plantage, l'état peut donc dater du dernier arrêt propre. Le « -3R » du scénario est une estimation qui dépend du gRisk faux.

### EA-04 · majeur · confirme : Arrondi des lots faux : il peut ARRONDIR VERS LE HAUT, jusqu'à doubler le risque, ou donner un volume invalide

`nasdaq/ORB-v6.mq5` : 885, 893, 899-900, 1047-1048

**Constat.** Le nombre de décimales vient de `vd = (int)MathMax(0, MathRound(-MathLog10(step)))`, puis `lots = NormalizeDouble(lots, vd)`. Avec un pas de 0,5, vd vaut 0 : 0,5 lot devient 1,0 et 1,5 devient 2,0. Avec un pas de 0,25, vd vaut 1 : 0,75 devient 0,8, qui n'est pas un multiple du pas, donc TRADE_RETCODE_INVALID_VOLUME. Le plafond de marge (893) est calculé avant cet arrondi, qui peut donc le dépasser. Par ailleurs, `MathFloor(x/step)*step` sans epsilon (885, 893) peut perdre un pas : 82,99999 donne 82. Le README signale l'arrondi faux sans dire qu'il peut AUGMENTER le risque.

**Scénario.** Courtier au pas de 0,5 lot, compte de 10 000 $, risque de 0,5 %, range de 25 pts à 1 $/pt/lot : le calcul donne 2 lots, puis 1,5 lot sur une autre journée, qui devient 2 lots (+33 % de risque). Pour 0,5 lot calculé, la position est de 1 lot : risque doublé, et une perte de 1R coûte 1 % au lieu de 0,5 %. Avec un pas de 0,25, les deux ordres stop sont refusés, le marché aussi (3 refus), et il n'y a aucun trade, peut-être pendant des mois sans qu'on comprenne pourquoi.

**Vérification.** Lignes 899-900 : vd = round(-log10(step)). Pas de 0,5 : vd=0, et NormalizeDouble(0.5,0) donne 1 et 1.5 donne 2 (arrondi au plus proche, demi vers le haut). Pas de 0,25 : vd=1, et 0,75 donne 0,8, qui n'est pas un multiple du pas (INVALID_VOLUME). Pas de 0,05 : vd=1, et 0,05 donne 0,1 (risque doublé sur les petits comptes). Le plafond de marge (893) est appliqué avant cet arrondi. MathFloor sans epsilon (885) peut perdre un pas, dans le sens prudent. DoPyramid (1048) a bien un epsilon, mais garde le même NormalizeDouble. Le README dit seulement « arrondi faux » sans préciser qu'il peut AUGMENTER la taille. La gravité dépend du courtier (pas exotiques), mais l'effet est un risque doublé sans alerte : majeur maintenu.

### EA-06 · majeur · confirme : Entrée au marché par l'EA « quelle que soit la distance » : risque non borné et pyramide hors de son pire cas

`nasdaq/ORB-v6.mq5` : 603-604, 992-1000, 767-771, 1048-1053

**Constat.** Un côté non posé chez le courtier (prix trop près, refus, EA lancé ou reconnecté tard) est surveillé : `if(gPendDir != -1 && !gSrvL && ask >= gOrH) d = 1;`, puis `trade.Buy(gLots, ..., sl=gOrL)`, sans aucun plafond d'écart entre le prix et le niveau. La taille gLots reste celle calculée pour un range de 1R, alors que la distance réelle au stop vaut (prix − gOrL). SyncPosition prend `gRisk = |gEntry-gSL|`, plus grand, pour les seuils et pour la distance du stop de la pyramide. L'ajout de 2×gLots avec un stop à 1×gRisk risque donc plus de 2R en argent.

**Scénario.** Reconnexion à 9:43 alors que le prix est 1,5 range au-dessus du high : achat au marché, le stop au low est à 2,5 ranges, et une perte coûte −2,5R (1,25 % à 0,5 % de risque). Si la pyramide se déclenche (+2R mesuré avec gRisk = 2,5 ranges), l'ajout perd 2×2,5 = 5 « R de range » au stop remonté : pire cas d'environ −2,5R au lieu de −1R.

**Vérification.** Lignes 993-1000 : aucun plafond d'écart entre le prix et le niveau, la taille reste gLots, et le stop est à gOrL. SyncPosition (767-769) prend gRisk = |gEntry-gSL|, plus grand. Les seuils et lock (1053) en découlent, et l'ajout de 2×gLots risque 2×gRisk/range R. Correction au scénario : une « reconnexion à 9:43 » ne relance PAS Setup, car OnNewBar ne voit plus la bougie de 9:30 en r[1] (1147-1149). Le cas est réel seulement : (a) si l'EA est lancé entre 9:35 et 9:40 avec le prix déjà au-delà du niveau (documenté dans le README) ; (b) si un côté surveillé (PlaceStop refusé) subit une déconnexion ou un blocage (WebRequest, EA-08) pendant la cassure. Le README signale la distance, pas l'amplification par la pyramide.

### EA-07 · majeur · confirme : Pyramide : l'ajout se fait au premier tick suivant, pas à la clôture, et le pire cas de −1R n'est pas garanti

`nasdaq/ORB-v6.mq5` : 1043-1094, 1108-1113

**Constat.** La décision se prend sur la clôture `r[1].close` (bid), mais l'ajout part au marché au premier tick de la bougie suivante, au prix ask A, avec `lock = A - gDir*InpPyrGap*gRisk`. Si A < entrée + 2R (le prix a reculé entre la clôture et le tick, spread ou glissement), le stop de l'ensemble est sous +1R pour l'unité de départ. Le pire cas, `lockR - 2`, est alors pire que −1R. La notification le calcule bien, mais aucune garde n'annule l'ajout dans ce cas. L'exposition triple : tout glissement sur le stop remonté (gap, annonce de 10:00 ou de 14:00) coûte 3 fois plus. Le README (règle 6) affirme pourtant « Le pire cas reste −1R ».

**Scénario.** Clôture à +2,05R, premier tick suivant 0,3R plus bas (ask à +1,75R) : le stop de l'ensemble est à +0,75R, et le pire cas vaut 0,75 − 2 = −1,25R. Avec 3 pts de glissement sur un stop dans un mouvement rapide et un range de 15 pts : 3 unités × 0,2R, soit −0,6R de plus. Pire cas réaliste d'environ −1,85R au lieu de −1R.

**Vérification.** Décision sur r[1].close (1110), puis ajout au prix du marché du tick courant (1052-1053). lockR = (ask-1R-entrée)/gRisk vaut moins de 1 si l'ask est sous entrée+2R. Aucune garde : lockR n'est utilisé que dans le message (1093). En temps normal, l'ask du premier tick vaut à peu près la clôture plus le spread, donc lockR est à peu près curR-1+spread, au moins 1. Il faut un recul entre la clôture et le premier tick pour dégrader. En revanche, l'exposition passe de 1 à 3 unités, et tout glissement sur le stop remonté coûte 3 fois plus. L'affirmation du README « le pire cas reste -1R » (règle 6, et commentaire lignes 21-22) est donc fausse en réel. Les chiffres du scénario sont illustratifs.

### EA-08 · majeur · confirme : WebRequest (Telegram, WhatsApp) bloque l'EA jusqu'à 5 s par message et par canal, sans aucun contrôle de prix pendant ce temps

`nasdaq/ORB-v6.mq5` : 371, 387, 403-438, 1336-1337, 1561-1575, 1612

**Constat.** FlushNotifs est appelé à la fin de chaque OnTick et dans OnTimer. Il envoie la file (jusqu'à QUEUE_MAX = 20 messages) de façon synchrone, avec un délai de 5000 ms par WebRequest et deux canaux possibles. Un EA MQL5 n'a qu'un fil d'exécution : pendant l'envoi, aucun OnTick n'est traité. Le côté surveillé n'entre pas, le côté bloqué n'annule pas les ordres, gVStop n'est pas vérifié, la sortie de 15:50 attend. L'essai Telegram demandé depuis Étrave appelle SendTelegram directement dans OnTimer. Il n'est refusé (« occupe ») que si gPend ou gSetupDue est vrai, PAS quand une position est ouverte. Au-delà de 20 messages, les suivants sont abandonnés sans trace.

**Scénario.** Réseau lent ou api.telegram.org injoignable (le délai d'attente joue) avec Telegram et WhatsApp actifs : « ORDRES PLACÉS » bloque environ 10 s à 9:35, puis « ACHAT exécuté » encore 10 s. Avec un seul côté permis, si le prix touche le côté bloqué puis le côté permis pendant ces 10 s, le Buy Stop est exécuté alors que la règle annulait le jour. Autre cas : un essai Telegram lancé depuis Étrave pendant un trade bloque 5 s au moment où gVStop est franchi, d'où 5 s de glissement en plus sur un mouvement de 10 à 20 pts.

**Vérification.** WebRequest est synchrone, avec 5000 ms (371, 387). FlushNotifs (424-438) envoie toute la file : jusqu'à 20 messages × 2 canaux × 5 s, soit 200 s au pire si l'hôte ne répond pas. Il est appelé à la fin d'OnTick (1612) et dans OnTimer (1572). Un EA MQL5 traite ses événements en série, donc aucun OnTick pendant ce temps. L'essai Telegram (1336-1337) part directement depuis ReadSettings, dans OnTimer. Il n'est refusé que si gPend ou gSetupDue, pas si gIn. Les ordres et les stops posés chez le courtier restent actifs ; ce qui est suspendu, c'est la logique de l'EA : côté bloqué, gVStop, 15:50, CloseOpposite, côté surveillé. Nuance : au-delà de QUEUE_MAX, le message est encore imprimé et envoyé en push (406-414). « Sans trace » est donc exagéré.

### EA-11 · majeur · confirme : Rien n'empêche deux instances de trader le même compte (deux graphiques, ou VPS MetaTrader plus terminal local)

`nasdaq/ORB-v6.mq5` : 914-922, 1522, 537-548, 553-556

**Constat.** Setup pose ses ordres sans vérifier qu'un ordre ou une position avec le même magic existe déjà. Deux instances sur le même symbole partagent le magic, les variables globales (préfixe GV identique) et le fichier etat-<symbole>.txt. Chacune considère les ordres de l'autre comme les siens (MyOrder) et peut les supprimer. Le README conseille le VPS de MetaTrader pour le réel, mais la migration vers ce VPS n'arrête pas l'EA du terminal local : chaque terminal a ses propres variables globales et trade de son côté.

**Scénario.** L'utilisateur migre vers le VPS MetaTrader et laisse son PC allumé avec le trading algorithmique actif. À 9:35, deux Buy Stop et deux Sell Stop sont posés, et la cassure exécute deux achats : 2R de risque, et 4 unités de pyramide en plus. À 0,5 %, une perte coûte 1 %, un trade avec pyramide raté jusqu'à 2 %.

**Vérification.** Setup (914-922) ne vérifie ni ordre ni position existants. GV (1522) ne dépend que du symbole et du magic. MyOrder, FindPos, ClosePos et DeletePendings agissent sur tout ce qui porte le magic. Deux instances posent donc chacune leurs ordres : risque doublé. Petite inexactitude : le README ne « conseille » pas le VPS de MetaTrader. Il conseille un VPS Windows et décrit celui de MetaTrader comme possible sans l'interface. La migration vers le VPS MetaTrader ne coupe pas l'EA local (MetaQuotes demande de le désactiver soi-même) : le scénario est réaliste.

### EA-05 · mineur · plausible : La perte au stop dépasse systématiquement 1R : la taille ignore le spread et le glissement

`nasdaq/ORB-v6.mq5` : 598-599, 876-885, 915, 949-952

**Constat.** `perLot = dist/ts*tv` et `gRiskMoney = lots*perLot` ne tiennent compte que du range high−low (prix bid de la bougie). L'achat est déclenché sur l'ask au high et son stop sur le bid au low. La perte réelle vaut donc range + spread à la sortie + glissement à l'entrée et au stop, plus la commission. Le message « ORDRES PLACÉS » annonce `gRiskMoney ... risqués (x %)`, ce qui sous-estime la perte réelle. Le seuil de 1R utilisé ensuite (gRisk = |gEntry-gSL|, ligne 769) inclut le glissement d'entrée, alors que le R affiché (gRiskMoney) ne l'inclut pas : l'EA mélange deux unités.

**Scénario.** Range de 12 pts, spread de 1,5 pt à 9:35, 1 pt de glissement sur le stop : un trade perdant coûte (12+1,5+1)/12, soit environ −1,2R, donc 0,6 % au lieu des 0,5 % choisis. Sur une série de 8 pertes, la baisse est d'environ 4,8 % au lieu de 4 %. Plus le range est étroit, plus l'écart est grand : avec 6 pts, une perte coûte environ −1,4R.

**Vérification.** La partie sur le spread est fausse. Achat : déclenché quand l'ask atteint H, donc entrée à H. Le stop se déclenche quand le bid atteint L, donc sortie à L. Perte = H-L, exactement le range. Vente : entrée au bid L, stop quand l'ask atteint H, perte = H-L aussi. Le spread ne s'ajoute pas à la perte au stop : il rend seulement le déclenchement plus fréquent. Restent le glissement (entrée et stop) et la commission, que la taille (883, 915) n'inclut pas. C'est cohérent avec la règle écrite (1R = lots × range) et c'est un coût d'exécution, pas un bug. Le « 1,2R » du scénario est surestimé, car il compte 1,5 pt de spread à tort. Le mélange des deux unités est réel, mais c'est le doublon d'EA-24.

### EA-09 · mineur · confirme : Une heure du serveur fausse est seulement signalée : l'EA continue de trader sur la mauvaise bougie

`nasdaq/ORB-v6.mq5` : 217-229, 1373-1382, 1532-1535, 1541-1545

**Constat.** L'heure de New York dépend de deux réglages, InpSrvGMT et InpSrvDST. OnInit fait un Alert et CheckClock un Notify quand l'écart réel dépasse 30 min, mais Setup, CheckEntries et la sortie ne sont jamais bloqués (gClockOk n'est lu que pour l'affichage). CheckClock n'est appelé que dans OnTimer, qui n'existe que si InpUseUI est vrai : sans Étrave, aucun contrôle continu. Le contrôle compare aussi TimeTradeServer() à TimeGMT(), qui dépend de l'horloge et du fuseau du PC ou du VPS : fausses alertes possibles, qu'on finit par ignorer.

**Scénario.** Courtier à l'heure d'été européenne, EA laissé sur SRV_DST_US : pendant les 2 à 3 semaines de mars et la semaine de fin octobre où les deux heures d'été ne coïncident pas, le « range de 9:30 » est en fait la bougie de 8:30 ou de 10:30. La sortie se fait à 14:50 ou 16:50, et le filtre d'élan porte sur une autre fenêtre. On a environ 15 à 20 trades par an hors stratégie, avec le risque normal.

**Vérification.** gClockOk n'est lu que pour l'affichage (1381, 1423). Ni Setup, ni CheckEntries, ni la sortie ne sont bloqués. Correction : CheckClock tourne dès qu'InpUseUI est vrai, ce qui est le réglage par défaut, même sans Étrave lancée (OnTimer est armé en 1544 quel que soit l'état du fichier). « Sans Étrave, aucun contrôle » n'est vrai que si InpUseUI=false. TimeGMT dépend bien de l'horloge du PC. Le scénario d'heure d'été mal réglée (environ 4 semaines par an) est exact, mais l'utilisateur est prévenu par push et Telegram au changement d'état. Sévérité ramenée à mineur.

### EA-10 · mineur · plausible : Données M5 et RSI lus sans vérifier qu'ils sont à jour au premier tick de la bougie ; une copie ratée efface la bougie entière

`nasdaq/ORB-v6.mq5` : 1583-1588, 1102-1105, 816-828, 1519

**Constat.** OnTick met `gLastBar = bt` AVANT OnNewBar. Si `CopyRates(_Symbol, PERIOD_M5, 0, 3, r) < 3` (série M5 pas encore synchronisée, fréquent quand le graphique n'est pas en M5), OnNewBar sort sans rien faire et la bougie n'est plus jamais contrôlée. Selon la bougie, on perd la préparation du range de 9:30, le stop au prix d'entrée (le high de la bougie à +1,5R est oublié : la bougie suivante ne regarde que son propre r[1]) ou la pyramide. Setup lit `CopyBuffer(hRSI,0,1,1,rsi)` sans vérifier BarsCalculated(hRSI) ni l'heure de la bougie lue. Si l'indicateur n'a pas encore recalculé la nouvelle bougie, la valeur peut être celle de 9:25, et le filtre RSI se fait sur la mauvaise bougie. Si r[1] n'est pas encore la bougie de 9:30, Setup renvoie true (« terminé ») sans message : journée perdue en silence.

**Scénario.** EA posé sur un graphique H1, premier tick de 9:35 avec la série M5 pas encore reconstruite : pas de trade ce jour-là, et aucun message « PAS DE TRADE ». Autre cas : RSI de 9:25 à 48 et RSI de 9:30 à 58 après une grosse bougie haussière. Le filtre interdit l'achat que le backtest prenait, et ce sont justement les jours de forte tendance qui portent la pyramide.

**Vérification.** Le code fait bien gLastBar=bt avant OnNewBar (1586), et OnNewBar sort en silence si CopyRates < 3 (1104). Mais iTime(_Symbol,M5,0) non nul (1584) et CopyRates(M5,0,3) viennent de la même série : un échec de l'un sans l'autre est peu probable. Pour le RSI (826), le risque d'un buffer pas encore recalculé au premier tick de la bougie existe en MQL5 : BarsCalculated et l'heure de la bougie ne sont pas vérifiés. Certitude moyenne : pour un indicateur créé sur le symbole du graphique, le calcul précède en général OnTick. Setup qui renvoie true sans message si r[1] n'est plus 9:30 (823) : exact, mais seulement si le RSI n'est pas prêt pendant toute la bougie de 9:35.

### EA-12 · mineur · confirme : Réponse inconnue (délai dépassé) à la pose d'un ordre stop ou à une entrée au marché : position possiblement doublée

`nasdaq/ORB-v6.mq5` : 609-622, 921-922, 1000-1018

**Constat.** PlaceStop renvoie false pour tout code de retour autre que DONE ou PLACED. Après TRADE_RETCODE_TIMEOUT ou une erreur réseau, l'ordre peut pourtant exister chez le courtier. L'EA passe alors ce côté en surveillance (gSrvL faux) et envoie AUSSI un ordre au marché quand l'ask atteint le high, sans regarder si un Buy Stop à son magic existe (HasPending n'est pas consulté sur ce chemin). Même chose pour trade.Buy : après un échec annoncé alors que l'ordre est passé, gFails++ et nouvel essai au tick suivant, si la position n'est pas encore visible.

**Scénario.** Connexion lente à 9:35 : le Buy Stop est posé mais le terminal reçoit un délai dépassé. À la cassure, le serveur exécute le Buy Stop et l'EA achète au marché : 2 positions de gLots, perte de 2R au stop. CloseOpposite ne ferme que le sens contraire.

**Vérification.** PlaceStop (613) ne retient que DONE ou PLACED. Sur un délai dépassé, gSrvL=false, le côté passe en surveillance, et CheckEntries (993-1000) achète au marché sans regarder HasPending. Si le Buy Stop existait chez le courtier, les deux s'exécutent dans le même sens. CloseOpposite (646) n'agit que sur le sens contraire. Scénario réaliste mais rare.

### EA-13 · mineur · confirme : Double exécution : FindPos prend la dernière position de la liste, pas la première exécutée

`nasdaq/ORB-v6.mq5` : 537-548, 638-651, 756-782

**Constat.** La règle dit que le premier ordre exécuté annule l'autre. Le stop de l'achat (gOrL) est au même prix que l'entrée de la vente : lors d'une traversée rapide du range, le stop de l'achat et le Sell Stop se déclenchent ensemble, avant que l'EA (qui ne supprime l'ordre opposé qu'au tick suivant l'exécution, ligne 782) ait réagi. Si l'EA voit l'achat déjà fermé (RecordClose, gIn=false) avant que la vente n'apparaisse, la vente est adoptée comme un NOUVEAU trade du jour. Si les deux sont visibles en même temps, FindPos parcourt la liste depuis la fin et peut prendre la seconde comme « le » trade, et CloseOpposite ferme alors la première.

**Scénario.** Range de 8 pts traversé en moins d'une seconde à 9:36 : l'achat est stoppé (−1R) et la vente est adoptée, avec un second risque de 1R le même jour alors que les règles et le backtest n'en comptent qu'un. En réseau lent ou pendant un blocage WebRequest (EA-08), la fenêtre s'allonge.

**Vérification.** Vérifié. Si l'EA voit l'achat ouvert, SyncPosition supprime l'ordre opposé au tick suivant (782). Si l'achat est déjà fermé (RecordClose met gIn=false, 801-806) avant que la vente apparaisse, la vente est adoptée comme un nouveau trade (759). Si les deux sont visibles à l'adoption, FindPos prend la plus récente, et CloseOpposite ferme la première. Il faut que le range soit traversé entre deux traitements de tick : rare, sauf pendant un blocage WebRequest (EA-08).

### EA-14 · mineur · plausible : L'identifiant de l'ajout est cherché tout de suite après l'ordre : la position peut ne pas être encore listée, et le R du trade devient faux

`nasdaq/ORB-v6.mq5` : 1079-1089, 701-733, 646

**Constat.** Juste après trade.Buy, la boucle sur PositionsTotal cherche une position dont l'identifiant diffère de gPosId. Or la liste des positions du terminal peut se mettre à jour un peu après le retour d'OrderSend. Si l'ajout n'y est pas encore, gPosId2 reste à 0 et RecordClose n'ajoute pas son résultat : le R, le % et le journal d'Étrave sont faux, et le message Telegram « CLÔTURÉ » aussi. À l'inverse, la boucle prend n'importe quelle autre position portant le magic, y compris une position opposée restée ouverte, que CloseOpposite épargne ensuite (`id == gPosId2`).

**Scénario.** Trade avec pyramide stoppé au stop remonté : l'unité de départ fait +1R, l'ajout −2R. Si l'ajout n'est pas compté, le journal affiche +1R au lieu de −1R. Les statistiques et la « pire baisse » de l'interface deviennent trop optimistes.

**Vérification.** La boucle 1081-1089 tourne juste après trade.Buy. Il est connu en MT5 (certitude moyenne) qu'après un OrderSend synchrone réussi, la position peut ne pas encore figurer dans PositionsTotal. gPosId2 n'est jamais recherché de nouveau. RecordClose (708) ignore alors l'ajout : R et journal faux. La boucle prend aussi n'importe quelle autre position portant le magic, y compris une position opposée encore ouverte. Aucun effet direct sur l'argent : l'ajout porte son propre stop (lock), et ClosePos ferme toutes les positions au magic.

### EA-15 · mineur · confirme : Exécution partielle ou ordre seulement « placé » traités comme une entrée complète

`nasdaq/ORB-v6.mq5` : 1002, 1068, 915, 1048

**Constat.** TRADE_RETCODE_DONE_PARTIAL et TRADE_RETCODE_PLACED comptent comme des succès pour un ordre au marché. gLots et gRiskMoney ne sont pas recalculés sur le volume réel (POSITION_VOLUME). La pyramide fait 2×gLots, donc plus de 2 fois la position réelle, et le pire cas dépasse −1R. Un ordre au marché seulement PLACED puis rejeté met gPend à faux : journée perdue en silence.

**Scénario.** Remplissage partiel de 0,6 lot sur 1 lot demandé : l'ajout est de 2 lots, soit 3,3 fois la position de départ, et le pire cas après l'ajout vaut environ −2,3R de la position réelle.

**Vérification.** Lignes 1002 et 1068 : DONE_PARTIAL et PLACED comptent comme des succès. gLots et gRiskMoney ne sont jamais recalculés sur POSITION_VOLUME. La pyramide fait 2×gLots (1048). Une exécution partielle d'un ordre au marché sur un CFD est rare. Un ordre « PLACED » puis rejeté met gPend=false : journée perdue sans message.

### EA-16 · mineur · confirme : InpDeviation = 30 « points » : la tolérance dépend du nombre de décimales du symbole

`nasdaq/ORB-v6.mq5` : 81, 1517, 648, 663, 1000, 1066

**Constat.** 30 points font 0,3 point d'indice si _Digits = 2, et 3 points si _Digits = 1. En exécution instantanée ou sur demande, une cassure rapide donne des requotes. L'entrée au marché est retentée au plus 3 fois, à des prix de plus en plus mauvais, puis abandonnée. La pyramide n'a qu'un essai (gPyr=true dès le premier). En exécution « Market », le paramètre est ignoré et le glissement n'a pas de limite.

**Scénario.** Courtier en exécution instantanée avec des prix à 2 décimales : à la cassure, 3 requotes et « ENTRÉE REFUSÉE ». Ce sont justement les journées de forte tendance qui sont perdues, ce qui biaise le résultat réel par rapport au backtest.

**Vérification.** InpDeviation=30 points (81, 1517), donc 0,3 ou 3 points d'indice selon _Digits. Le paramètre n'a d'effet qu'en exécution instantanée ou sur demande. La plupart des CFD NAS100 sont en exécution « Market », où la tolérance est ignorée et le glissement sans limite. Entrée surveillée limitée à 3 échecs (1010), pyramide à un seul essai (1049) : exact.

### EA-17 · mineur · confirme : Ordres en attente refusés pour d'autres raisons : remplissage, expiration SPECIFIED_DAY seule, range plus petit que le niveau des stops

`nasdaq/ORB-v6.mq5` : 602-622, 999-1000

**Constat.** Le contrôle `gap` porte sur la distance du prix d'entrée, pas sur celle du stop (gOrL), qui doit aussi dépasser SYMBOL_TRADE_STOPS_LEVEL. Avec un range plus petit que ce niveau, l'ordre stop est refusé (INVALID_STOPS), l'entrée au marché aussi, 3 fois, et il n'y a pas de trade. Si le courtier n'autorise que SYMBOL_EXPIRATION_SPECIFIED_DAY, l'EA envoie ORDER_TIME_DAY, peut-être interdit : refus, puis mode surveillé avec plus de glissement. Le nouvel essai en ORDER_FILLING_RETURN n'a lieu que sur INVALID_FILL, et RETURN est refusé en exécution « Market ».

**Scénario.** Niveau des stops de 10 pts chez le courtier et range de 7 pts : aucun trade ces jours-là, alors que le backtest les compte.

**Vérification.** Le contrôle de gap (602-603) porte sur la distance du prix d'entrée, pas sur celle du stop. Un range plus petit que STOPS_LEVEL donne INVALID_STOPS, puis un ordre au marché avec sl=gOrL, lui aussi refusé (bid-L, à peu près range moins spread, sous le niveau), 3 fois : pas de trade. Le cas ORDER_TIME_DAY quand DAY n'est pas permis (606) est possible. Les points sur le mode de remplissage sont plausibles mais dépendent du courtier. Rare sur le NAS100, où les ranges font en général 10 à 40 pts.

### EA-18 · mineur · confirme : Clôture demandée depuis Étrave : un refus n'est pas retenté et l'utilisateur n'est pas prévenu

`nasdaq/ORB-v6.mq5` : 1359-1369, 653-666, 1566-1570

**Constat.** UiClose appelle ClosePos une seule fois, et gCloseDue est remis à faux avant. ClosePos ne fait qu'un PrintFormat en cas de refus (requote, marché fermé, fermeture interdite) : aucune nouvelle tentative, aucune notification. Le message « CLÔTURE demandée » part pourtant avant.

**Scénario.** Clic sur « Clôturer » pendant une requote ou un instant de marché fermé : la position reste ouverte alors que l'utilisateur la croit fermée. Elle continue jusqu'au stop ou à 15:50.

**Vérification.** gCloseDue est remis à faux avant UiClose (1568-1569). ClosePos (653-666) fait une seule tentative et, en cas d'échec, un PrintFormat sans Notify. Le message « CLÔTURE demandée » part avant (1364). Aucune nouvelle tentative. Autre cas : si ni gIn ni gPend n'est vrai à cet instant, la demande est perdue sans réponse.

### EA-19 · mineur · plausible : Compte en netting : les positions se fondent, et l'ordre opposé ou une position manuelle change la position de l'EA

`nasdaq/ORB-v6.mq5` : 1536-1537, 537-548, 1066

**Constat.** L'EA ne refuse pas le mode netting, il l'écrit seulement dans le journal. En netting, un Buy Stop exécuté pendant qu'une position manuelle est ouverte s'y ajoute. POSITION_MAGIC reste celui de la position d'origine, FindPos ne la trouve pas, et après 10 s l'EA annule la journée (« ordre disparu »). La position manuelle a alors grossi et son stop a pu être remplacé. La pyramide en netting change aussi le prix moyen et le stop de toute la position.

**Scénario.** Position manuelle ouverte sur NAS100 en netting : le Buy Stop l'augmente, l'EA ne la gère pas (pas de sortie à 15:50), et le risque réel n'est connu de personne.

**Vérification.** Le mode netting n'est qu'imprimé (1536-1537). Le comportement de POSITION_MAGIC et de SL/TP quand une position netting est augmentée est cité de mémoire (certitude moyenne : le magic reste celui d'origine, et le SL de l'ordre ajouté remplace celui de la position). Si le magic n'est pas celui de l'EA, FindPos ne trouve rien, HasPending est faux, et au bout de 10 s : « ORDRE DISPARU » (984-989). Le README conseille le mode hedging. Le scénario suppose une position manuelle ouverte sur le même symbole.

### EA-20 · mineur · confirme : Filtre d'élan : égalité acceptée (>=) alors que le README dit « dépasse »

`nasdaq/ORB-v6.mq5` : 857-858

**Constat.** `extL = ... gOrH >= pH`, `extS = ... gOrL <= pL`. La règle 2 du README dit « son high dépasse le plus haut de 9:00-9:30 », donc strictement. Le script Pine fait la même chose (`orH >= preH`). C'est un écart entre le texte et le code, pas entre l'EA et Pine.

**Scénario.** Un high de 9:30 exactement égal au plus haut de 9:00-9:30 autorise l'achat. C'est rare (prix à 1 ou 2 décimales), mais cela fait des trades en plus par rapport à la règle écrite.

**Vérification.** EA 857-858 : `>=` et `<=`. Pine 546-547 : `orH >= preH`, `orL <= preL`. Le README (règle 2) dit « dépasse » et « sous ». L'écart sépare le texte du code, pas l'EA du Pine. Il est rare, avec des prix à 1 ou 2 décimales.

### EA-21 · mineur · confirme : Calendrier des jours fériés : jours normaux traités comme demi-séances, et fermetures exceptionnelles absentes

`nasdaq/ORB-v6.mq5` : 291-311

**Constat.** Le 31 décembre est marqué jour férié quand le 1er janvier tombe un samedi (`Observed(MakeDate(y+1,1,1))`), alors que le NYSE ouvre normalement ce jour-là. Le 2 juillet est marqué « par prudence » quand le 4 tombe un samedi. Juneteenth est marqué chaque année, y compris avant 2022 : seuls les tests 2018-2021 dans le testeur sont touchés. Les fermetures exceptionnelles (deuil national du 9 janvier 2025, par exemple) n'y sont pas, et la position y passerait la fermeture. Ces limites sont signalées dans le README.

**Scénario.** Le 31/12/2027 (le 1er janvier 2028 tombe un samedi), sortie à 12:45 et pas de pyramide ensuite : une journée de tendance est coupée. Un jour de fermeture imprévue, la position reste ouverte jusqu'à la réouverture, avec le risque de gap.

**Vérification.** Ligne 305 : Observed(MakeDate(y+1,1,1)) marque le 31/12 quand le 1er janvier tombe un samedi. Le NYSE ouvre normalement ce jour-là (31/12/2021 par exemple). Ligne 302 : le jeudi 2 juillet est marqué quand le 4 tombe un samedi, alors que c'est une séance normale (2020, 2015). Juneteenth est marqué avant 2022. Les fermetures exceptionnelles manquent. Le README signale le 31/12 et les fermetures exceptionnelles, pas le 2 juillet.

### EA-22 · mineur · confirme : Journal des trades et état pour Étrave : écritures perdues sans nouvel essai, lots de la pyramide absents

`nasdaq/ORB-v6.mq5` : 1394-1452, 1456-1475

**Constat.** AppendTrade écrit `DoubleToString(gLots, 2)`, la taille de départ sans l'ajout. Si FileOpen échoue (fichier verrouillé), la ligne est perdue : un simple Print, sans nouvel essai. WriteState ne vérifie pas le résultat de FileMove. Pendant qu'Étrave lit etat-*.txt (Python ouvre sans FILE_SHARE_DELETE sous Windows), le remplacement échoue et l'état affiché garde un cycle de retard. Sans gravité pour l'argent, mais le suivi réel dans l'interface peut être incomplet.

**Scénario.** Une ligne de trade perdue, et la courbe et les statistiques d'Étrave ne correspondent plus au compte : le suivi en démo, qui doit servir de juge, est biaisé.

**Vérification.** Ligne 1472 : DoubleToString(gLots,2), sans l'ajout. Si FileOpen échoue : un Print, puis abandon (1461-1465). FileMove n'est pas vérifié (1451). Côté Python, lire_cles fait un open() simple, sans FILE_SHARE_DELETE sous Windows : un remplacement pendant la lecture peut échouer, et l'état garde un cycle de retard. Effet limité au suivi.

### EA-23 · mineur · confirme : reglages.txt : retour silencieux aux réglages de MetaTrader et jeton Telegram en clair dans le dossier commun

`nasdaq/ORB-v6.mq5` : 1243-1357

**Constat.** La lecture est atomique, car Étrave écrit un fichier provisoire puis le remplace ; l'EA garde ses valeurs si le fichier est illisible APRÈS une première lecture. Mais si la première lecture échoue, ou si une clé est absente ou mal encodée (fichier retouché à la main en UTF-16, virgule décimale), le risque revient à InpRiskPct et la case Nasdaq à « cochée ». Un changement de risque est notifié, pas une case réactivée lors de la toute première lecture. Le jeton Telegram est stocké en clair dans Common\Files\Etrave, lisible par tout programme ou EA de l'utilisateur (le chmod 600 côté Python est sans effet sous Windows). La demande `cloturer` est protégée par l'heure de création (120 s) et par son numéro (gCloseSeen persistant) : correct.

**Scénario.** reglages.txt réenregistré en UTF-16 par un éditeur : l'EA ne trouve plus aucune clé. Il trade au risque de MetaTrader (0,5 % par défaut) même si l'interface affiche 0,25 %, ou trade alors que la case Nasdaq est décochée.

**Vérification.** Si la toute première lecture échoue (h invalide et gUiLoaded faux, 1259-1263), les valeurs par défaut s'appliquent (InpRiskPct, active=true). Étrave (pont.ecrire_cles) écrit en UTF-8 sans BOM, en CRLF, par fichier provisoire puis os.replace : le format normal est donc correct. Le risque ne vient que d'une retouche à la main. Le jeton Telegram est en clair dans Common\Files\Etrave, et chmod 600 est sans effet sous Windows. La protection de `cloturer` par l'âge (120 s) et par le numéro est correcte.

### EA-24 · mineur · confirme : Unités de R incohérentes entre les seuils et le résultat affiché

`nasdaq/ORB-v6.mq5` : 767-771, 915, 733, 1438

**Constat.** Le README définit 1R = taille de départ × range. L'EA mesure les seuils de +1,5R (stop au prix d'entrée) et de +2R (pyramide), ainsi que la distance du stop de la pyramide, avec `gRisk = |gEntry - gSL|`, c'est-à-dire la distance réelle depuis le prix exécuté, glissement compris. Le R affiché et enregistré vient de `net / gRiskMoney`, calculé sur le seul range. Les deux diffèrent dès qu'il y a du glissement, et beaucoup en mode surveillé (EA-06).

**Scénario.** 2 pts de glissement sur un range de 10 pts : les seuils sont à 1,5×12 et 2×12 pts au lieu de 15 et 20 pts. Le stop au prix d'entrée et la pyramide arrivent plus tard que dans le backtest, et le R affiché ne correspond pas à celui des seuils.

**Vérification.** gRisk = |gEntry-gSL| (769) inclut le glissement d'entrée, et sert aux seuils de +1,5R et +2R et à lock (1053). Le R affiché et enregistré vaut net/gRiskMoney (733, 1438), avec gRiskMoney = lots × range (915). Les deux diffèrent dès qu'il y a du glissement. Avec un Buy Stop exécuté exactement au niveau, ils coïncident.

### EA-25 · mineur · plausible : Compilation : peu d'erreurs probables, mais quelques points à surveiller (variable `exp`, char[] contre uchar[], conversions implicites)

`nasdaq/ORB-v6.mq5` : 607, 384, 450-458, 602, 773

**Constat.** Relecture ligne à ligne : les signatures de CTrade (BuyStop/SellStop avec type_time et expiration, PositionClose(ticket, deviation), PositionModify(ticket, sl, tp), SetTypeFillingBySymbol), les constantes (SYMBOL_EXPIRATION_*, TRADE_RETCODE_INVALID_FILL, DEAL_FEE, DEAL_REASON_*), FileOpen(…, 0, CP_UTF8), FileMove et OrderCalcMargin semblent correctes. Le fichier est en UTF-8 avec BOM, donc les accents sont bien lus par MetaEditor. Points à risque : (1) ligne 607, variable locale `datetime exp`, du même nom que l'alias MQL5 de MathExp (`exp`) : au mieux un avertissement, peut-être une erreur. (2) Ligne 384, `StringToCharArray(body, data, …)` avec `char data[]` alors que le prototype documenté attend `uchar&[]` : c'est un usage courant qui compile en principe. (3) Conversions implicites bool→double (Sv("pend", gPend)…), long→double (MathMax de deux SymbolInfoInteger) et opérateur % sur un datetime (`t - t % BAR`) : avertissements probables. L'EA peut aussi appeler AppendTrade et MarginPerLot avant leur définition : MQL5 l'accepte.

**Scénario.** Si `exp` est refusé, l'EA ne compile pas et le README dit de « corriger ce que le compilateur signale ». Une correction faite à la hâte sur la gestion de l'expiration peut alors aggraver EA-01.

**Vérification.** Relecture des signatures, de mémoire : CTrade::BuyStop(volume, price, symbol, sl, tp, type_time, expiration, comment), PositionClose(ticket, deviation), PositionModify(ticket, sl, tp), FileOpen(name, flags, delimiter, codepage), FileMove(src, common, dst, mode) et OrderCalcMargin sont conformes. StringToCharArray vers char[] : c'est l'usage de l'exemple officiel de WebRequest, qui compile (certitude élevée). Conversions bool→double, long→double et datetime % int : au plus des avertissements. La variable `exp` (607), homonyme de la fonction exp() : certitude faible ; à mon avis au pire un avertissement « hides function ». Je n'ai trouvé aucune erreur de compilation certaine. Non vérifiable sans MetaEditor.

### EA-26 · mineur · confirme : Plafond du volume : l'ajout de 2×gLots peut dépasser SYMBOL_VOLUME_MAX ou SYMBOL_VOLUME_LIMIT

`nasdaq/ORB-v6.mq5` : 898, 1048, 1066-1078

**Constat.** `lots = MathMin(lots, vmax)` ne s'applique qu'à la taille de départ. L'ajout fait `gLots*InpPyrSize` sans comparaison à vmax ni à SYMBOL_VOLUME_LIMIT (volume total permis). Il est alors refusé, et le trade continue sans pyramide (un message « refusée »).

**Scénario.** Gros compte ou risque élevé avec gLots = vmax : la pyramide, qui porte une grande part du gain de la stratégie, ne se fait jamais. Le résultat réel est inférieur au backtest sans qu'on comprenne pourquoi.

**Vérification.** vmax n'est appliqué qu'à la taille de départ (898). L'ajout de 2×gLots (1048) n'est comparé ni à vmax ni à SYMBOL_VOLUME_LIMIT. Il est alors refusé, et un message « Pyramide refusée » est envoyé (1072) : « sans qu'on comprenne » est exagéré. Ne concerne que les gros comptes ou les risques élevés.

### EA-27 · mineur · confirme : Reconnaissance du Nasdaq par sous-chaîne : la case d'Étrave peut être sans effet ou agir sur un autre symbole

`nasdaq/ORB-v6.mq5` : 1161-1167, 1295-1296

**Constat.** InstrumentOf cherche « NAS », « NDX », « NQ », « USTEC », « US100 », « USATECH » ou « TECH100 » dans le nom du symbole. « US Tech 100 » ou « USTECH 100 », avec une espace, ne sont pas reconnus : gInstr vaut « autre », et la clé « nasdaq » (l'interrupteur des nouveaux trades) est ignorée. À l'inverse, « NQ » se retrouve dans des noms sans rapport.

**Scénario.** Avec un symbole nommé « US Tech 100 », décocher la case Nasdaq dans Étrave n'empêche pas l'EA de prendre le trade du lendemain.

**Vérification.** InstrumentOf (1161-1167) cherche des sous-chaînes. « US TECH 100 » ne contient ni USTEC, ni TECH100, ni NAS : gInstr vaut « autre ». Étrave n'écrit que la clé `nasdaq` (pont.INSTRUMENTS), donc la case est sans effet sur ce symbole (1295). Les faux positifs avec « NQ » sont sans conséquence, puisque l'EA n'est posé que sur le Nasdaq.

### Oublis relevés par le vérificateur

- **majeur** · Dossier commun partagé par TOUS les terminaux et comptes : une demande « Clôturer » ferme aussi le trade de l'autre terminal (démo et réel) (`nasdaq/ORB-v6.mq5` : 1255-1318, 1396, 1451, 1460) : reglages.txt, etat-<symbole>.txt et trades-<symbole>.csv sont dans Common\Files\Etrave, partagé par tous les terminaux MT5 de l'utilisateur Windows. Les noms ne dépendent que du nom du symbole (gSymFile), pas du compte ni du terminal. La demande `cloturer=<n>;<symbole>` est exécutée par CHAQUE EA dont gSymFile correspond (1309). Avec un terminal démo et un terminal réel ouverts en même temps sur un même nom de symbole (cas courant pendant la phase de démo conseillée), cliquer « Clôturer » pour la démo ferme aussi le trade réel. Le risque réglé s'applique aux deux. Les deux EA écrasent tour à tour le même etat-*.txt, et le journal CSV (sans colonne de compte) mélange démo et réel, ce qui fausse le suivi de démo qui doit servir de juge.
- **mineur** · État (variables globales) non lié au compte : un changement de compte dans le même terminal hérite de gIn, gDay et des statistiques (`nasdaq/ORB-v6.mq5` : 1522, 461-473, 798-808) : GV = "ORBv6_"+symbole+magic, sans le numéro de compte, alors que les variables globales sont propres au terminal, pas au compte. Passage d'un compte démo au compte réel dans le même terminal : si l'état dit gIn=true, SyncPosition (tk==0 && gIn) appelle RecordClose. HistorySelectByPosition ne trouve aucun deal sur le nouveau compte, et au bout de 50 ticks un trade fantôme à 0R est enregistré et notifié. Si la démo a déjà traité le range du jour (gDay), le compte réel ne trade pas ce jour-là. Les statistiques gN, gSumR et gDD de la démo continuent sur le réel.
- **mineur** · Réinitialisation de l'EA en cours de trade (changement d'un paramètre, d'unité de temps, recompilation) : drapeaux non sauvés remis à zéro (`nasdaq/ORB-v6.mq5` : 143, 1539, 1072-1075, 1104-1113) : Sans aucun plantage, toute réinitialisation (paramètre modifié dans MT5 pendant un trade, changement d'unité de temps du graphique, mise à jour de l'EA depuis Étrave) recharge l'état sans gUsePyrToday, gFails, gDelDue ni gGoneAt, et remet gLastBar=0. Après une pyramide refusée (gUsePyrToday=false, gPyr=false), la réinitialisation remet gUsePyrToday=true. La dernière bougie close est réévaluée tout de suite, et l'ajout est retenté hors de la règle (à un autre prix, voire plus tard dans la journée).
- **mineur** · Pyramide avant le stop au prix d'entrée : l'unité de départ garde chez le courtier son stop au bord du range (-1R) (`nasdaq/ORB-v6.mq5` : 1108-1113, 1050, 1124, 1038-1039) : Le contrôle de la pyramide passe avant celui du stop au prix d'entrée, et peut se déclencher dès la bougie d'entrée. DoPyramid met gBE=true, donc RaiseStop(gEntry) n'est jamais appelé. Seul RaiseStop(lock) remonte le stop de l'unité de départ, et seulement si bid-lock > STOPS_LEVEL et si PositionModify réussit. En cas d'échec, combiné à un arrêt de l'EA, la perte vaut -1R (départ) -2R (ajout), soit -3R. C'est pire que le scénario d'EA-02, qui supposait le stop de départ déjà au prix d'entrée.

### Non vérifié par le lecteur

- Pas de MetaEditor ni de MetaTrader dans cet environnement : la compilation n'a pas été tentée. Les points de EA-25 (variable `exp`, StringToCharArray avec char[], avertissements de conversion) sont à confirmer par F7.
- Comportement exact de l'écriture sur disque des variables globales MT5 sans GlobalVariablesFlush() lors d'un arrêt brutal : d'après la documentation, l'écriture n'est garantie qu'à la fermeture normale du terminal. Non testé.
- Sémantique de MqlRates.spread pour une bougie M5 (spread minimal, moyen ou de clôture) : elle conditionne les seuils mesurés sur l'ask pour les ventes (lignes 1110, 1126, 1141). Non vérifiée.
- Risque que CopyBuffer(hRSI) renvoie la valeur de la bougie précédente au premier tick d'une nouvelle bougie (EA-10) : connu en MQL5 mais dépendant du terminal et de l'horizon du graphique, à confirmer en démo en notant le RSI affiché le matin.
- Paramètres réels du courtier (modes d'expiration et de remplissage, SYMBOL_TRADE_STOPS_LEVEL et FREEZE_LEVEL, pas de volume, exécution Market ou Instant, nombre de décimales) : inconnus, ils décident si EA-01, EA-04, EA-16 et EA-17 se produisent.
- Temps de réponse de WebRequest (Telegram, CallMeBot) depuis le VPS : la durée de blocage d'EA-08 est la borne théorique (5 s par message et par canal), pas une mesure.
- Partage de fichiers sous Windows entre Python (Étrave) et FileOpen/FileMove de MQL5 : déduit des modes de partage, pas observé.
- Le script Pine n'a été lu que pour comparer les règles (filtre d'élan, pyramide à la clôture, sortie à 15:45/15:50, côté bloqué) ; il n'a pas été audité en entier ni compilé.
- Fichiers exclus par les règles d'indépendance et non ouverts : etrave/reference.json, bitcoin/profils.json, etrave/page.html, etrave/risque.py. L'historique git n'a pas été consulté.

## Script TradingView (Pine v6)

### PINE-01 · majeur · confirme : Backtest Pine sans coût réaliste par défaut : pas de commission et glissement de 2 ticks seulement

`nasdaq/ORB-v6.pine` : 24-27 (strategy(..., slippage = 2)), 22-23

**Constat.** La déclaration strategy() ne fixe ni commission_type ni commission_value : la commission vaut 0 par défaut. Le seul coût codé est slippage = 2, exprimé en ticks (syminfo.mintick). Sur un CFD NAS100 à 0,01 ou 0,1 de tick, cela fait 0,02 à 0,2 point. Le README (l. 92-93) demande d'ajouter à la main « une commission égale au spread ». Même ainsi, le glissement réel des ordres stop d'entrée dans la volatilité de 9:35-9:45 n'est pas modélisé. Le coût de la pyramide n'est pas compté non plus : 3 unités ouvertes, dont 2 au marché, puis fermées. Autre ambiguïté : TradingView prélève la commission à l'entrée et à la sortie, et l'expression « égale au spread » ne dit pas s'il faut saisir un spread entier ou un demi-spread par côté.

**Scénario.** Avec les réglages tels que livrés, le testeur affiche un résultat sans spread. Exemple : spread de 1,5 à 3 points à l'ouverture, range moyen d'environ 40 points en 2024-2026 et 1 à 3 points de glissement sur l'entrée stop. Le coût réel tourne autour de 0,05 à 0,1R par unité et par aller-retour, soit jusqu'à environ 0,2-0,3R sur les trades pyramidés (3 unités). Il peut absorber une grande partie, voire la totalité, d'une espérance de l'ordre de 0,1-0,2R par trade. Tout chiffre tiré du testeur Pine sans commission saisie est donc surestimé.

**Vérification.** Relu ORB-v6.pine:24-27 : strategy() ne contient ni commission_type ni commission_value, donc la commission vaut 0 par défaut. slippage = 2 est exprimé en ticks : 0,02 à 0,2 point sur un CFD NAS100, soit un coût négligeable. Le coût à saisir est bien laissé à l'utilisateur (commentaire l. 22-23, README l. 92-93). TradingView prélève la commission à chaque ordre, entrée et sortie, et à chacune des 3 unités en cas de pyramide. Saisir « le spread » comme commission par ordre compte donc 2 spreads par aller-retour : c'est l'ambiguïté que signale le lecteur. Le chiffrage en R du scénario est un ordre de grandeur plausible, pas une mesure. Je baisse la sévérité à « majeur » : le manque est documenté dans le script et dans le README. Il reste que le résultat du testeur, avec les réglages livrés, ne compte aucun spread.

### PINE-02 · majeur · confirme : Règle 3 non respectée dans une même bougie : le côté bloqué touché d'abord n'annule pas l'entrée exécutée ensuite

`nasdaq/ORB-v6.pine` : 443-458, 510-521 (EA : nasdaq/ORB-v6.mq5:1139-1143)

**Constat.** L'annulation « côté bloqué touché d'abord » n'est vérifiée qu'à la clôture de la bougie (l. 510-512 : oppFirst = pDir == 1 ? low <= orL ...). Elle exige en plus strategy.position_size == 0. Or l'ordre stop permis reste actif pendant toute la bougie, et l'émulateur l'exécute en cours de bougie. Si la même bougie touche d'abord orL puis orH (cas d'un achat seul), le trade est pris, alors que la règle 3 du README dit « Si un seul côté est permis et que l'autre est touché d'abord, pas de trade ». L'EA fait de même : les ordres sont posés chez le courtier, et `opp` n'est évalué que dans OnNewBar (mq5:1141). L'écart concerne donc les deux implémentations et ne figure pas dans le tableau des écarts du README.

**Scénario.** Achat seul permis. La bougie de 9:35 descend à orL - 2 points puis monte et casse orH avant 9:40. La règle écrite exige « pas de trade ». Pine et l'EA entrent pourtant à l'achat, avec un stop à orL qui vient d'être visité. Le backtest compte donc des trades que la règle exclut, sur les journées aux bougies les plus larges, qui sont aussi les plus volatiles.

**Vérification.** Pine:510-512 : l'annulation « côté bloqué touché d'abord » n'est testée que si strategy.position_size == 0 et à la clôture de la bougie. Si la même bougie touche orL puis orH (achat seul permis), l'ordre stop est rempli en cours de bougie. À la clôture, la branche 443 crée le trade et passe pend à false (l. 445), si bien que la l. 510 ne s'exécute pas. L'émulateur suit le chemin O-L-H-C quand l'ouverture est plus près du bas. Sinon il suit O-H-L-C : entrée, puis stop à orL, soit -1R. Dans les deux cas, un trade est compté là où la règle 3 du README dit « pas de trade ». EA vérifié à mq5:1139-1143 : `opp` n'est évalué que dans OnNewBar et seulement si !gIn, alors que les Buy/Sell Stop sont posés chez le courtier. Les deux versions ont donc le même écart, qui n'est pas dans le tableau du README. La fréquence est sans doute faible : il faut une bougie de 9:35 ou de 9:40 qui traverse tout le range, un jour où un seul côté est permis. Je garde « majeur » parce que l'écart n'est pas documenté et touche les journées les plus volatiles.

### PINE-03 · majeur · plausible : Jour sans trade décidé par le capital TradingView et le pas de taille, pas par le solde du courtier : biais contre les grands ranges et alertes « pas de trade » à tort

`nasdaq/ORB-v6.pine` : 96-97, 554-555, 565-570, 577

**Constat.** La quantité vaut qty = floor((strategy.initial_capital + strategy.netprofit) × riskPct/100 ÷ (dist × pointvalue × fx) ÷ qtyStep) × qtyStep (l. 554), puis go = ... and qty > 0 (l. 555). Le pas qtyStep vient de syminfo.mincontract, sinon d'une valeur par défaut (l. 96-97). Si qty arrondit à 0, aucun ordre n'est posé et l'alerte « pas de trade aujourd'hui : taille nulle » part (l. 566-570), même quand lotBal est renseigné (100 000 par exemple) et que le lot du courtier serait non nul. Le lot lotsFor n'est calculé que dans la branche go (l. 577). Ce sont donc les réglages de la stratégie TradingView (capital de 10 000 par défaut, pas du flux), et non le compte réel, qui décident si l'on trade.

**Scénario.** Si syminfo.mincontract vaut 1 sur le flux NAS100 choisi, le risque vaut 10 000 × 0,5 % = 50 $. Tout range de plus de 50 points (fréquent depuis 2022, avec un indice entre 15 000 et 25 000) donne qty = 0. Le backtest ne garde alors que les petits ranges, d'où un biais de sélection. Et l'utilisateur qui suit les alertes reçoit « pas de trade » ces jours-là, alors que l'EA traderait. Avec un pas de 0,01, l'effet disparaît : il dépend du flux (non vérifiable sans TradingView).

**Vérification.** Mécanisme confirmé. Pine:554-555 : qty se calcule sur strategy.initial_capital + strategy.netprofit et sur qtyStep, et go exige qty > 0. lotsFor/pLots n'est calculé que dans la branche go (l. 577), donc lotBal n'intervient jamais dans la décision. Si qty arrondit à 0, l'alerte « pas de trade aujourd'hui : taille nulle » part (l. 566-570). L'ampleur dépend de syminfo.mincontract sur le flux choisi (l. 97) : avec un pas de 1 et 50 $ de risque, tout range de plus de 50 points avec pointvalue 1 donne qty = 0, d'où un biais de sélection et de fausses alertes. Avec 0,01 (valeur par défaut des CFD/indices, l. 96), l'effet disparaît. Je ne peux pas vérifier mincontract sans TradingView, d'où « plausible ».

### PINE-04 · majeur · confirme : Alertes trop tardives pour un suivi manuel : sortie annoncée après 15:50, stop à l'entrée et exécution annoncés à la clôture de bougie

`nasdaq/ORB-v6.pine` : 127-129, 443-458, 466-472, 481-497, 506-507

**Constat.** Toutes les alertes sont émises avec alert.freq_once_per_bar_close, et la stratégie ne calcule qu'à la clôture des bougies (pas de calc_on_every_tick ni de calc_on_order_fills). La sortie de fin de journée est remplie à la clôture de la bougie de 15:45 par close_all (l. 506-507). Mais l'alerte « clôturé » n'est émise que par recordClose, à la bougie suivante (l. 466-472), soit vers 15:55, et aucune alerte ne prévient avant 15:50. L'exécution d'entrée est signalée à la clôture de la bougie d'exécution, jusqu'à 5 minutes après. L'ordre de passer le stop au prix d'entrée arrive lui aussi à la clôture (l. 497). Le README présente pourtant le script comme une source de lots « à saisir dans MetaTrader », donc pour un usage manuel. Il faut aussi compter les délais des webhooks TradingView.

**Scénario.** Un utilisateur trade à la main chez FundingPips à partir des alertes. Il apprend la sortie de 15:50 vers 15:55 au plus tôt, et la position reste ouverte pendant la fin de séance. Si une bougie atteint +1,5R puis repart, le stop n'est déplacé qu'après la clôture et la réception de l'alerte. Le prix est souvent déjà revenu : l'exécution réelle n'a plus rien à voir avec le backtest.

**Vérification.** Pine:128 : toutes les alertes passent par alert.freq_once_per_bar_close, et strategy() n'a ni calc_on_every_tick ni calc_on_order_fills. La sortie de fin de journée est ordonnée à la clôture de la bougie de 15:45 (l. 506-507, remplie à 15:50 grâce à process_orders_on_close). L'alerte « clôturé » n'est émise qu'à la bougie suivante, par la branche 466 → recordClose, soit vers 15:55. Nuance : le stop à l'entrée et la pyramide sont décidés à la clôture par la règle elle-même, comme dans l'EA ; le retard de ces deux alertes vient donc du webhook, pas du code. Le vrai risque en manuel, que le lecteur n'explicite pas, est l'OCA. Les jours où les deux côtés sont permis, l'utilisateur pose deux stops dans MT5. Il n'apprend l'exécution qu'à la clôture de la bougie, jusqu'à 5 minutes plus tard. Pendant ce temps, l'ordre de vente sur orL reste actif au même prix que le stop de l'achat : un retour à orL coupe l'achat et ouvre une vente, ce que le backtest (oca.cancel) exclut. Comme le README (l. 97-103) présente le script comme source de lots à saisir à la main, je garde « majeur ».

### PINE-05 · mineur · confirme : Taille illimitée par la marge dans le backtest (margin_long = margin_short = 0) avec une pyramide ×3

`nasdaq/ORB-v6.pine` : 26, 554, 407

**Constat.** margin_long = 0 et margin_short = 0 suppriment tout contrôle de marge et tout appel de marge. La taille, capital × risque ÷ range, plus l'ajout de 2× sur la pyramide, peut correspondre à un levier notionnel de plusieurs dizaines de fois le capital, impossible chez le courtier. L'EA, lui, plafonne la position à 90 % de la marge libre, pyramide comprise (mq5:886-896). Le tableau du README mentionne la différence de taille, sans dire que les résultats en $ du testeur Pine supposent un levier infini.

**Scénario.** Capital de 10 000 $, risque de 0,5 % et range de 8 points, ce qui arrive les jours calmes : qty = 6,25 unités, soit environ 125 000 $ de notionnel à 20 000 points. Après la pyramide, environ 375 000 $, soit 37 fois le capital. Avec le levier 1:20 d'un prop firm, l'EA réduirait la taille ou ne pourrait pas ajouter. Le testeur Pine compte le gain plein, surtout sur les journées de tendance qui font l'essentiel du résultat.

**Vérification.** Pine:26 : margin_long = 0 et margin_short = 0, donc aucun contrôle de marge ni appel de marge dans l'émulateur. Le chiffrage du scénario est juste : 10 000 $ × 0,5 % ÷ 8 points, avec pointvalue 1, donnent qty = 6,25, soit environ 125 000 $ de notionnel, puis environ 375 000 $ après l'ajout. L'EA plafonne bien à 90 % de la marge libre (README l. 72-73, et le tableau l. 115 le mentionne). Je baisse à « mineur » : la différence de taille est documentée dans le tableau du README, et les statistiques en R du tableau Pine (l. 638-642) n'en dépendent pas. Seuls le rapport en $ et la capitalisation du testeur supposent un levier illimité.

### PINE-06 · mineur · confirme : Filtre d'élan : >= au lieu de « dépasse » (strict)

`nasdaq/ORB-v6.pine` : 546-547 (EA : nasdaq/ORB-v6.mq5:857-858)

**Constat.** extL = ... orH >= preH et extS = ... orL <= preL. Le README (règle 2) dit « son high dépasse le plus haut de 9:00-9:30 » et « le low sous le plus bas », donc des comparaisons strictes. L'EA utilise aussi >= et <=, si bien que les deux implémentations s'accordent entre elles mais pas avec la règle écrite. Le tableau des écarts du README ne le mentionne pas.

**Scénario.** Le high de la bougie de 9:30 égale exactement le plus haut de 9:00-9:25 : simple test du niveau, sans dépassement. Pine et l'EA autorisent l'achat, alors que la règle écrite le bloque. L'écart est rare sur des prix à 0,1 ou 0,01 près, mais change le jeu de trades du backtest.

**Vérification.** Pine:546-547 : orH >= preH et orL <= preL. EA vérifié à mq5:857-858 : mêmes >= et <=. La règle 2 du README dit « dépasse » et « sous », donc des comparaisons strictes. L'écart vaut pour les deux implémentations et n'est pas dans le tableau du README. Il ne joue qu'en cas d'égalité exacte, rare avec des prix au 0,1 ou au 0,01 près.

### PINE-07 · mineur · confirme : Juneteenth traité comme férié avant 2022 (et la veille du 4 juillet « par prudence ») : sortie à 12:45 des jours normaux

`nasdaq/ORB-v6.pine` : 186-191 (EA : nasdaq/ORB-v6.mq5:302-310)

**Constat.** isShortDay compte observed(noon(y, 6, 19)) chaque année, alors que la Bourse de New York n'observe Juneteenth que depuis 2022. Elle marque aussi le jeudi comme demi-séance quand le 4 juillet tombe un samedi (l. 187, « par prudence »), ce que la règle 8 du README ne prévoit pas (« veille du 4 juillet »). Ces jours-là, la position est fermée à 12:45 et la pyramide est interdite après 12:40, sans raison de marché. L'EA a exactement le même calendrier (mq5:302, 306). Le README ne signale que le cas du 31 décembre et dit le calendrier contrôlé sur 2022-2025.

**Scénario.** Dans le backtest, les journées normales du 19/06/2018, du 19/06/2019, du 19/06/2020, du 18/06/2021, puis du 02/07/2020 et du 02/07/2026 (à vérifier sur le calendrier officiel) sortent à 12:45. Le test hors échantillon d'avant 2018 en est aussi faussé : tous les 19 juin observés (2008-2017) et le 02/07/2015. L'effet sur le total est faible (1 à 2 jours par an), mais il en change le résultat.

**Vérification.** Pine:189 : observed(noon(y, 6, 19)) est compté chaque année, sans condition y >= 2022. La Bourse de New York n'observe Juneteenth que depuis 2022 (certitude élevée). Pine:187 : quand le 4 juillet tombe un samedi, pre4 vaut le jeudi (« par prudence »). Les jeudis 02/07/2015 et 02/07/2020 étaient, à ma connaissance, des séances complètes ; 2026 reste à vérifier. EA identique (mq5:302, 306). Effet : sortie à 12:45 et pas de pyramide après 12:40 environ 1 jour par an sur 2018-2021, ainsi que sur tout test avant 2018. La règle 8 ne prévoit que la « veille du 4 juillet ». L'effet sur le total est faible.

### PINE-08 · mineur · confirme : Pyramide permise sur la bougie d'entrée, stop à l'entrée exclu de cette bougie : asymétrie non documentée

`nasdaq/ORB-v6.pine` : 458, 481 (EA : nasdaq/ORB-v6.mq5:1108, 1116)

**Constat.** Après détection de l'exécution, tryPyramid(cur) est appelé sur la bougie même de l'entrée (l. 458). Le passage du stop au prix d'entrée exige au contraire bar_index > cur.fillBar (l. 481). L'EA fait de même (r[1].time >= gFillBar pour la pyramide, > pour le stop à l'entrée). La règle 6 du README (« quand une bougie clôture à +2R ») ne dit pas si la bougie d'entrée compte. La règle 5 l'exclut explicitement pour le stop à l'entrée.

**Scénario.** La bougie de 9:35 casse le high à 9:36 et clôture à +2,2R. Pine et l'EA ajoutent 2 unités au marché à 9:40 et remontent le stop à +1,2R. Si cette même bougie avait seulement touché +1,5R sur son plus haut, le stop serait resté à -1R. Ce choix pèse sur les journées de cassure franche, celles qui font le résultat de la pyramide.

**Vérification.** Pine:458 : tryPyramid(cur) est appelé sur la bougie même de la détection de l'exécution. Pine:481 : le stop à l'entrée exige bar_index > cur.fillBar. EA identique (mq5:1108 : r[1].time >= gFillBar, et 1116 : >). C'est conforme à la lettre du README : la règle 5 exclut explicitement la bougie d'entrée, la règle 6 ne le fait pas. Le code n'a donc pas de bug ; c'est la règle qui est ambiguë, et les deux versions s'accordent entre elles. Le lecteur a raison de dire que ce choix pèse sur les journées de cassure franche.

### PINE-09 · mineur · confirme : Seuil de +1,5R mesuré sur le plus haut ou le plus bas de la bougie, et non sur la clôture comme pour la pyramide

`nasdaq/ORB-v6.pine` : 53, 481

**Constat.** Le test du stop à l'entrée est high >= entry + beR × risk (ou low pour une vente), évalué à la clôture. Le README (règle 5) dit « dès +1,5R, décidé à la clôture d'une bougie après celle de l'entrée », sans préciser si c'est le plus haut ou la clôture. La règle 6 dit explicitement « clôture ». L'EA mesure lui aussi sur le plus haut du bid (mq5:1126-1127), donc l'accord est bon. Mais la décision tombe à la clôture, alors que le seuil a été touché plus tôt : si le prix est déjà revenu sous l'entrée, Pine sort à la clôture (l'ordre stop est rempli au passage de clôture de process_orders_on_close) et l'EA à l'ouverture suivante (RaiseStop, mq5:1033-1036). La perte dépasse alors les frais.

**Scénario.** Achat. La bougie monte à +1,6R puis clôture à -0,4R. À sa clôture, le stop est mis à l'entrée et se déclenche aussitôt : sortie vers -0,4R, étiquetée « Stop à l'entrée ». La série de pertes n'est pas incrémentée (l. 394 : why == "Stop à l'entrée"), si bien que la statistique « pertes de suite » minimise ce cas.

**Vérification.** Pine:481 : le seuil est testé sur high/low, et l'infobulle l. 53 le documente. Il est conforme à l'EA (mq5:1126-1127). Si la clôture est déjà repassée sous l'entrée, le strategy.exit modifié (l. 483) est un stop déjà franchi. Avec process_orders_on_close, l'émulateur le remplit à la clôture : je suis presque sûr de ce comportement. L'EA ferme au marché dans ce cas (RaiseStop, mq5:1033-1036). Correction au scénario : la l. 394 ne se contente pas de ne pas incrémenter la série, elle la remet à 0 (S.streak := ... : 0). Une sortie « Stop à l'entrée » à -0,4R efface donc la série de pertes en cours, ce qui fausse « pertes de suite » plus encore que ce que dit le lecteur. Le cas est rare : il faut un aller-retour de plus de 1,5R dans une bougie de 5 minutes.

### PINE-10 · mineur · confirme : Ajout de la pyramide rempli au prix de clôture qui a servi à le décider

`nasdaq/ORB-v6.pine` : 26 (process_orders_on_close = true), 406-416

**Constat.** Avec process_orders_on_close = true, le strategy.entry au marché de la pyramide est rempli à la clôture même de la bougie où l'on vient de constater close >= +2R, plus 2 ticks de glissement. En réel, l'ajout ne peut partir qu'au tick suivant : l'EA le passe au premier tick de la bougie suivante, à l'ask. Le stop de l'ensemble est en plus calculé depuis close (l. 410), pas depuis le prix d'exécution. L'écart sur le stop est documenté dans le README, pas le léger avantage sur le prix d'ajout. Le même mécanisme fait sortir le stop à l'entrée à la clôture de la bougie de décision.

**Scénario.** Clôture de bougie à +2,0R suivie d'un écart d'ouverture de 3 points contre la position. Pine ajoute 2 unités au prix de clôture, l'EA 3 points plus mal, plus le spread. Sur des trades pyramidés, l'écart vaut environ 2 × 3 pts ÷ range, soit 0,15R pour un range de 40 points.

**Vérification.** Pine:26 et 414 : l'entrée au marché de la pyramide est remplie à la clôture de la bougie de décision (process_orders_on_close), et le commentaire l. 403 le dit. Le stop part de close (l. 410). L'EA ajoute au premier tick de la bougie suivante, à l'ask. Le biais existe mais le scénario l'exagère : sur un CFD qui cote en continu, l'écart entre la clôture d'une bougie M5 et le tick suivant vaut en général le spread plus quelques ticks, pas 3 points. L'avantage est réel mais petit, et le spread manquant est déjà couvert par PINE-01.

### PINE-11 · mineur · confirme : 1R en argent calculé sur le range, mais les seuils en R mesurés depuis le prix d'exécution réel

`nasdaq/ORB-v6.pine` : 380-382, 406, 481, 387

**Constat.** newTrade fixe risk = |entry - sl|, soit l'entrée exécutée avec glissement ou écart d'ouverture, mais usd = sz × (orH - orL). Les seuils de +1,5R et +2R et le stop de la pyramide utilisent risk. Le R final (l. 387 : pnl ÷ usd) utilise le range. Le README (règle 4) définit 1R = taille × range. L'EA fait pareil (gRisk = |gEntry - gSL|, mq5:770-773).

**Scénario.** Range de 30 points, ouverture de la bougie de 9:35 à orH + 10 : risk = 40. Les seuils passent à +60 et +80 points au lieu de +45 et +60. Une perte au stop vaut 40/30 = -1,33R, et le « pire cas -1R » après la pyramide devient environ -1,33R.

**Vérification.** Pine:380-382 : risk = |entry - sl| à partir du prix exécuté, mais usd = sz × (orH - orL). Les seuils (l. 406, 481, 410) utilisent risk, et le R final (l. 387) utilise usd, défini sur le range. EA identique (mq5:769-770). Sur TradingView, entry = max(open, orH) + 2 ticks. Comme close(9:30) <= orH, un écart de 10 points suppose un trou de 10 points entre deux bougies consécutives d'un CFD continu, ce qui est très rare. L'écart réel est presque toujours de quelques ticks. Le mécanisme est confirmé, le scénario chiffré est irréaliste dans Pine. En réel, il peut jouer davantage dans l'EA, avec le glissement sur l'ordre stop.

### PINE-12 · mineur · plausible : Exécution possible dès la clôture de la bougie de 9:30 : le stop à l'entrée n'est alors pas testé sur la bougie de 9:35

`nasdaq/ORB-v6.pine` : 26, 443-458, 481, 582-586

**Constat.** Les ordres stop sont créés à la clôture de la bougie de 9:30. Avec process_orders_on_close = true, l'émulateur fait une tentative à cette clôture : si close == orH (clôture au plus haut) ou close == orL, l'ordre est rempli tout de suite. La détection n'a lieu qu'à la bougie suivante (l. 443), et dans la branche de création, ce qui fait sauter le test du stop à l'entrée de la l. 481 sur la bougie de 9:35, pourtant postérieure à l'entrée. L'alerte « exécuté » arrive aussi avec une bougie de retard.

**Scénario.** Bougie de 9:30 clôturant exactement à son plus haut, puis bougie de 9:35 montant à +1,8R et redescendant. Le stop reste à orL alors que la règle 5 l'aurait mis à l'entrée. L'effet est rare et mal connu, parce qu'il dépend de cette tentative d'exécution à la clôture.

**Vérification.** Les ordres stop sont créés à la clôture de la bougie de 9:30 (l. 582-586), après les blocs d'exécution (l. 443-503). Avec process_orders_on_close, l'émulateur les traite à cette clôture : un achat stop à orH est rempli si close == orH. Si c'est le cas, la détection n'a lieu qu'à la bougie de 9:35, dans la branche 443. Le test du stop à l'entrée de la l. 481 (branche else-if) est alors sauté sur la bougie de 9:35, pourtant postérieure à l'entrée, et cur.best n'y est pas mis à jour non plus. La logique du code est confirmée. Le remplissage à la clôture d'un stop créé sur cette même clôture correspond à mon souvenir du fonctionnement de l'émulateur, mais je ne peux pas le tester sans TradingView. Le cas est rare.

### PINE-13 · mineur · confirme : Ordre intra-bougie supposé par l'heuristique OHLC (pas de use_bar_magnifier)

`nasdaq/ORB-v6.pine` : 24-27

**Constat.** strategy() n'active pas use_bar_magnifier. Pour une bougie qui touche l'entrée et le stop, ou orH et orL dans une journée à deux côtés, l'émulateur suppose un parcours ouverture, plus haut, plus bas, clôture (ou l'inverse) selon que l'ouverture est plus près du plus haut ou du plus bas. Le côté exécuté et l'arrêt dans la même bougie viennent donc d'une hypothèse, pas des ticks. Le flux de TradingView ne connaît pas non plus le spread (l'ask), comme le dit le README.

**Scénario.** Bougie de 9:35 de 60 points qui traverse tout le range de 30 points. Le backtest choisit le côté selon la position de l'ouverture. Le résultat (-1R) est souvent le même, mais le côté et le prix de sortie peuvent différer de la réalité, et du testeur MT5 en ticks réels.

**Vérification.** strategy() (l. 24-27) n'active pas use_bar_magnifier. L'heuristique de l'émulateur est connue : O-H-L-C si l'ouverture est plus près du haut, O-L-H-C sinon. Elle décide quel côté est exécuté, si l'exécution et le stop ont lieu dans la même bougie, et le cas de PINE-02. C'est une limite connue de l'outil plus qu'un bug du script. Le bar magnifier demande en outre un abonnement payant.

### PINE-14 · mineur · plausible : Validité des ordres comptée en bougies et non en heure

`nasdaq/ORB-v6.pine` : 510-511

**Constat.** late = bar_index - pBar >= liveBars. Si le flux n'a pas de bougie à 9:35 ou 9:40 (trou de données, flux peu actif un jour férié), les ordres restent actifs au-delà de 9:45. Il y a aussi des jours où le contrat à terme ferme tôt : le vendredi saint qui tombe un jour de chiffres de l'emploi (2021, 2026 : séance CME raccourcie vers 10:15). La bougie de sortie de 12:40 n'existe alors pas, et la position n'est fermée qu'à la première bougie du jour suivant (l. 506 : nyDate != cur.day), donc après le week-end.

**Scénario.** Vendredi saint avec une séance courte du contrat à terme : entrée à 9:40, plus de cotation après 10:15. Le backtest garde la position jusqu'à l'ouverture du dimanche soir. En réel, le CFD ne cote plus et la position passe le week-end.

**Vérification.** Pine:511 : late = bar_index - pBar >= liveBars, donc la validité est comptée en bougies. L'EA, lui, compte en temps (mq5:1140 : r[0].time >= gOrTime + (InpLiveBars+1)×BAR), un petit écart non documenté. L'absence de bougies de 9:35 ou 9:40 sur un CFD en pleine séance est très improbable. Le cas du vendredi saint qui tombe un jour de chiffres de l'emploi (séance courte du contrat à terme, 2021) est réel. Comme la bougie de 12:40 n'existe pas, la position n'est fermée qu'à la première bougie d'un autre jour (l. 506). Je ne sais pas si le CFD de TradingView cote ce jour-là, et les dates 2026 restent à vérifier : d'où « plausible ».

### PINE-15 · mineur · confirme : Textes d'alerte faux : « sortie à 15:45 NY » (sortie réelle à 15:50, ou à 12:45 les jours fériés)

`nasdaq/ORB-v6.pine` : 456, 613

**Constat.** L'alerte d'exécution (l. 456) et celle des ordres placés (l. 613) disent « Sortie à 15:45 NY ». Le script sort pourtant à la clôture de la bougie de 15:45, soit 15:50 (l. 197, 506), et à 12:45 les jours de demi-séance, ce que les alertes ne disent pas. L'EA, lui, annonce 12:45 ces jours-là (mq5:794).

**Scénario.** Le lendemain de Thanksgiving, l'alerte dit 15:45 alors que le script sort à 12:45 et que le marché ferme à 13:00. Un utilisateur manuel qui se fie à l'alerte garde la position au-delà de la fermeture.

**Vérification.** Pine:456 (« Sortie à 15:45 NY si ni stop ni objectif ») et l. 613 (« · sortie à 15:45 NY ») : le texte est faux. La sortie a lieu à la clôture de la bougie de 15:45, soit 15:50 (l. 44, 197, 506), et à 12:45 les jours fériés et les demi-séances, ce que les alertes n'indiquent jamais (shortDay n'y est pas utilisé). L'EA, lui, adapte son texte. Pour un usage manuel, un jour de demi-séance, l'alerte induit en erreur.

### PINE-16 · mineur · confirme : Identifiant de discussion Telegram codé en dur par défaut

`nasdaq/ORB-v6.pine` : 63

**Constat.** tgChat vaut par défaut "-1003571455927", un groupe ou canal précis. Toute copie du script envoie ses alertes (niveaux, tailles, résultats) à ce chat si le bot de l'utilisateur en est membre. Sinon, les alertes échouent sans bruit.

**Scénario.** Un tiers colle le script avec son propre jeton de bot sans changer le chat : ses messages partent vers le chat de l'auteur, ou nulle part, sans erreur visible dans TradingView.

**Vérification.** Pine:63 : tgChat a pour valeur par défaut "-1003571455927", un identifiant de canal ou de groupe Telegram réel. Toute copie du script vise ce chat. Les envois échouent sans bruit si le bot de l'utilisateur n'en est pas membre, sinon ils fuient vers ce chat. Il y a aussi une fuite d'une donnée personnelle de l'auteur dans un fichier public.

### PINE-17 · mineur · confirme : Lot calculé sur le range du flux TradingView, sans contrôle de marge, et le tableau recalcule un lot différent de l'alerte

`nasdaq/ORB-v6.pine` : 112-114, 577-579, 640-641

**Constat.** lotsFor = floor(bal × riskPct/100 ÷ (dist × lotSize × fx) ÷ lotStep + 1e-6) × lotStep. Le calcul est juste pour un symbole en USD (fx = 1), mais dist vient du flux TradingView (prix du graphique, souvent bid ou mid d'un autre fournisseur), pas des prix de FundingPips. Les niveaux d'ordre annoncés viennent aussi de ce flux. Rien ne vérifie la marge (l'EA, si : 90 % de la marge libre, 3 unités). Le tableau (l. 640-641) recalcule le lot à barstate.islast avec le strategy.netprofit du moment quand lotBal = 0 : il peut différer du lot pLots envoyé dans l'alerte de 9:35. riskPct a minval = 0,1, alors qu'Étrave permet 0,05 %.

**Scénario.** Le range de 9:30 vaut 30 points sur le flux TradingView et 33 chez le courtier, une fois le spread ajouté. Le lot de l'alerte risque environ 10 % de plus ou de moins que prévu, et les niveaux saisis à la main sont décalés. Si le lot de l'ajout (2× le lot) dépasse la marge, l'ajout est refusé chez le courtier.

**Vérification.** Pine:112-114 : lotsFor se calcule sur le range du flux TradingView, sans contrôle de marge. Pine:640-641 : à barstate.islast, le tableau recalcule lotsFor avec le strategy.netprofit du moment quand lotBal = 0, ce qui peut différer de pLots, figé à 9:35 et envoyé dans l'alerte. Pine:31 : minval = 0,1 pour riskPct, alors que le README (l. 59) annonce 0,05 % côté Étrave. La formule du lot est correcte pour un symbole en USD : 100 000 × 0,5 % ÷ (30 × 20) = 0,83, conforme à l'exemple du README.

### PINE-18 · mineur · confirme : Arrondi de qty sans epsilon (contrairement à lotsFor et à la pyramide)

`nasdaq/ORB-v6.pine` : 554

**Constat.** qty = math.floor(x / qtyStep) × qtyStep, sans + 0.000001, alors que lotsFor (l. 114), pLotsA (l. 578) et la pyramide (l. 407) l'ajoutent. Une erreur d'arrondi binaire peut faire tomber x / qtyStep = 4.9999999 à 4.

**Scénario.** Capital × risque ÷ (range × pointvalue) tombe exactement sur un multiple du pas, par exemple 0,5. L'arrondi retire un pas, d'où une taille un peu plus petite. L'effet est négligeable en R mais rend la quantité incohérente avec le lot affiché.

**Vérification.** Pine:554 : math.floor(x / qtyStep) × qtyStep, sans le + 0.000001 utilisé l. 114, 407 et 578. Une erreur d'arrondi binaire peut retirer un pas. L'effet est négligeable ; c'est une simple incohérence.

### PINE-19 · mineur · plausible : Compilation : aucune erreur certaine trouvée, avertissements possibles

`nasdaq/ORB-v6.pine` : 197, 165-177, 623-625

**Constat.** J'ai relu tout le script : types définis par l'utilisateur et leurs champs modifiés dans des fonctions, appels strategy.* et alert() dans des fonctions, request.currency_rate en portée globale, ta.rsi en portée globale, lignes de continuation indentées hors multiples de 4, divisions entières sous math.floor (compatible avec la division fractionnaire de la v6), pas de bool à na. Je n'ai pas trouvé d'erreur certaine. Risques résiduels : time(timeframe.period, flatShortS, TZ_NY) est le second opérande d'un `and` paresseux en v6 (l. 197), ce qui peut provoquer l'avertissement « should be called on each calculation ». cellRow se termine par table.cell (retour void), un usage normalement accepté.

**Scénario.** Le script n'a pas été compilé depuis les modifications des 15 et 17 novembre 2026 (README l. 127-129). Une erreur de l'éditeur Pine reste possible sur un point que je ne peux pas tester sans TradingView.

**Vérification.** Relecture complète de mon côté, de mémoire de Pine v6, avec une certitude moyenne à bonne. Points vérifiés : types définis par l'utilisateur dont les champs ont des valeurs par défaut ; var Trade cur = na et na(cur) ; méthodes .set_x2/.set_bgcolor sur des champs ; strategy.closedtrades.size, strategy.opentrades.entry_bar_index et str.format_time, qui existent ; request.currency_rate(..., ignore_invalid_currency) en portée globale ; ta.rsi global ; aucune fonction ne réassigne une variable globale par := (elles ne modifient que des champs d'objets, ce qui est permis) ; strategy.* et alert() appelés dans des fonctions (permis) ; math.floor sur des divisions entières devenues fractionnaires en v6 ; lignes de continuation indentées hors multiples de 4 ; ternaires imbriqués sur plusieurs lignes entre parenthèses ; cellRow qui se termine par un appel void. Je n'ai pas trouvé d'erreur certaine. Le seul point douteux est `S.nClosed += 1` (l. 389) et `cur.pnl +=` (l. 469), un opérateur composé sur un champ d'objet que je crois accepté. L'avertissement sur time() dans un `and` paresseux (l. 197) reste possible mais ne bloque pas la compilation.

### Oublis relevés par le vérificateur

- **majeur** · Historique M5 limité : le testeur Pine ne voit que quelques semaines ou mois de trades (`nasdaq/ORB-v6.pine` : 24-27, 86-87) : Le script exige un graphique M5 (l. 86-87) avec les bougies hors séance. Un CFD NAS100 cote environ 23 h sur 24, soit environ 276 bougies M5 par jour. Selon l'abonnement, TradingView charge de l'ordre de 5 000 à 40 000 bougies, hors Deep Backtesting : c'est-à-dire environ 20 à 140 séances, donc quelques dizaines à une centaine de trades. Les statistiques du testeur et du tableau (l. 638-642) n'ont donc aucune portée statistique pour juger un avantage. Ne pas citer un résultat Pine comme preuve. Les limites exactes par abonnement n'ont pas été vérifiées.
- **mineur** · Exécuté puis stoppé dans la même bougie : aucune alerte « exécuté » n'est envoyée (`nasdaq/ORB-v6.pine` : 459-465) : Si l'entrée et le stop ont lieu dans la même bougie, la branche else (l. 459-465) appelle openDraw puis recordClose : seule l'alerte « clôturé » part. Un utilisateur manuel qui a posé ses ordres d'après l'alerte « Ordres placés » n'est jamais prévenu de l'exécution. Il apprend en même temps l'entrée et la perte, et doit encore annuler lui-même l'ordre opposé (l'OCA n'existe pas dans MT5).
- **mineur** · Série de pertes remise à zéro par une sortie « Stop à l'entrée » perdante (`nasdaq/ORB-v6.pine` : 394-395) : S.streak := why != "Stop à l'entrée" and r < -0.05 ? S.streak + 1 : 0. Une sortie étiquetée « Stop à l'entrée » mais à -0,4R (cas de PINE-09, ou glissement) ne compte pas comme perte et remet la série à 0. Le tableau sous-estime donc la « pire série de pertes ».
- **mineur** · Trades pris les jours fériés où le marché au comptant est fermé : « range d'ouverture » sans ouverture (`nasdaq/ORB-v6.pine` : 188-197, 532) : Les jours fériés complets (Martin Luther King, Presidents' Day, Juneteenth, etc.), isShortDay ne fait qu'avancer la sortie à 12:45. La bougie de 9:30 du CFD (adossé au contrat à terme, qui cote jusqu'à 13:00) sert quand même de range, et le RSI et le filtre d'élan sont calculés comme d'habitude. C'est conforme à la lettre de la règle 8, mais il n'y a pas d'ouverture de New York ce jour-là : liquidité réduite et spread plus large chez le courtier. Ces jours sont inclus dans le backtest sans coût particulier. À isoler dans les résultats.
- **mineur** · Fin de validité des ordres : Pine compte en bougies, l'EA en temps (`nasdaq/ORB-v6.pine` : 510-511 (EA : nasdaq/ORB-v6.mq5:1140)) : Pine annule quand bar_index - pBar >= liveBars, l'EA quand r[0].time >= gOrTime + (InpLiveBars+1)×BAR. Les deux s'accordent si aucune bougie ne manque, mais divergent sur un flux à trous. L'écart ne figure pas dans le tableau du README.

### Non vérifié par le lecteur

- Compilation réelle du script Pine v6 : aucun compilateur Pine n'est disponible hors de TradingView. L'analyse est une relecture manuelle.
- Valeur de syminfo.mincontract, syminfo.mintick et syminfo.pointvalue sur le flux NAS100 de TradingView utilisé. Elle conditionne la gravité de PINE-03 (jours sautés pour « taille nulle ») et le poids réel de slippage = 2 ticks (PINE-01).
- Comportement exact de l'émulateur de TradingView avec process_orders_on_close = true pour un ordre stop créé à la clôture et pour un stop d'exit déplacé derrière le prix : exécution au passage de clôture supposée d'après la documentation (PINE-09, PINE-10, PINE-12), non observée.
- Livraison de plusieurs appels alert() dans une même exécution avec alert.freq_once_per_bar_close, et délais réels des webhooks TradingView vers Telegram.
- Calendrier officiel NYSE 2026 pour le jeudi 2 juillet 2026 (demi-séance ou séance normale) et horaires CME/CFD du vendredi saint 2021 et 2026.
- Profondeur d'historique M5 disponible sur TradingView pour le CFD NAS100. Sans Deep Backtesting, le testeur Pine ne couvre probablement que quelques mois, pas 2018-2026.
- Taille de contrat FundingPips NAS100 (20 unités par lot) : non vérifiée chez le courtier.
- Je n'ai rien exécuté. Aucun backtest n'a servi aux constats de cette partie (revue de code seulement), et les fichiers de résultats (reference.json, profils.json, page.html, risque.py) n'ont pas été ouverts.

## Stratégie BTC et son backtest (btc.py, profils.py…)

### BTC-01 · majeur · confirme : Flux on-chain Coin Metrics : le backtest utilise des valeurs recalculées en 2026, que le bot n'avait pas en temps réel

`bitcoin/btc.py` : 42-44, 77-81 (et bitcoin/donnees_live.py:233-238)

**Constat.** brutes() lit donnees/crypto/historique/coinmetrics-btc-2010.csv et votes() n'applique qu'un décalage de 2 jours (`oc.index = oc.index + pd.Timedelta("2D")`, l.77). Ce décalage corrige le délai de publication, pas les révisions. Dans le fichier, les 5 686 lignes ont le statut « flash », mais leur colonne FlowInExNtv-status-time montre qu'elles ont toutes été recalculées entre avril et novembre 2026 : 993 lignes le 2026-04-02, 711 le 2026-04-03, etc. En médiane, une valeur datée de 2018 a été écrite 2 832 jours après sa date ; une valeur de 2024, 648 jours après. Seules les lignes récentes de 2026 ont un délai d'environ 1,1 jour. Les flux vers les plateformes dépendent de l'étiquetage des adresses, que Coin Metrics complète après coup. Le backtest 2012-2026 voit donc l'étiquetage de 2026. En direct, le bot reçoit des valeurs flash (donnees_live.onchain), qui ne seront pas celles du fichier.

**Scénario.** J'ai mesuré sur les données réelles, sans calcul de rendement : retirer le vote on-chain change le sens de la position (signe) sur 7,7 % des bougies 4h en 2012-2017 et sur 8,1 % en 2018-2026. Sur ces bougies-là, le backtest repose en partie sur une information future. Je n'ai pas pu chiffrer l'écart de rendement : il faudrait les anciennes versions (vintages) des séries Coin Metrics.

**Vérification.** Code relu : btc.py:42-44 lit le fichier Coin Metrics complet, et btc.py:77 décale seulement l'index de 2 jours. Le searchsorted des l.79-80 fait que le vote du jour J n'utilise que les données jusqu'à J-1, puis caler les reporte à J+1. Le délai de publication est donc bien couvert, mais rien ne traite les révisions. J'ai vérifié sur le fichier : 5 686 lignes, toutes au statut « flash ». Les status-time datent du 2026-04-02 (993 lignes), du 2026-04-03 (711), etc. Écart médian entre la date de la valeur et son écriture : 5 023 jours pour 2012, 2 832 pour 2018, 648 pour 2024 et 1,1 jour pour 2026. J'ai retrouvé aussi les mêmes taux de bougies qui changent de signe sans le vote on-chain : 7,7 % sur 2012-2017 et 8,1 % sur 2018-2026. Le bot en direct lit les valeurs flash par l'API. La fonction onchain est en réalité à donnees_live.py:60-65, pas aux l.233-238 citées : le lecteur a pris la numérotation d'une concaténation. L'effet sur le rendement n'est pas chiffrable sans les anciennes versions des séries, donc « majeur » plutôt que « critique ».

### ★ BTC-02 · majeur · confirme : Financement avant 2020 : la vente reçoit 10 %/an dans profils.simuler, mais le paie dans Banc4h

`bitcoin/profils.py` : 311-315, 340-341 (contre bitcoin/btc.py:135-136, 146)

**Constat.** Avant 2020, Banc4h prend `fund[avant] = -0.10/365/6` puis `net += where(t<0, -t*fund, 0)` : un vendeur paie 10 %/an (commentaire « un vendeur paie ~10 %/an pour emprunter »). profils.simuler prend `fund = np.full(len(idx), 0.10/365/6)`, positif, puis `fin -= tenu*fund[i]` avec `if perp or tenu < 0`. Pour tenu<0, cela donne +|tenu|×10 %/an : la vente encaisse le financement. Les deux bancs se contredisent sur 2012-2019, et profils.json (lu par Étrave) prend l'hypothèse favorable.

**Scénario.** Sur les données réelles, la position est vendeuse 22 % du temps en 2012-2017, avec une taille moyenne de -0,16. Écart entre les deux hypothèses : environ 2 × 10 % × 0,16 × 0,22 ≈ 0,7 à 0,9 point de rendement par an à ×1, et environ ×L au-delà (de l'ordre de 7 à 9 points/an à ×10) sur la colonne « 2012-2026 » de profils.json. Les colonnes 2018-2026 et 2022-2026 sont peu touchées (financement réel depuis 2020).

**Vérification.** Les deux bancs se contredisent bien. profils.py:37 prend fund = +0,10/365/6 avant 2020 (bonnes lignes : profils.py:37-41 et 66-67, pas 311-315 et 340-341). À ×1, perp vaut False, donc seule la branche `tenu < 0` s'applique : fin -= tenu*fund donne +|tenu|×10 %/an, et la vente encaisse. Banc4h (btc.py:136) prend fund = -0,10/365/6, et net += -t*fund pour t<0 fait payer le vendeur. La docstring de btc.py:15-16 (« 10 % par an de coût d'emprunt ») va dans le sens de Banc4h. Correction du chiffrage : la règle s'applique jusqu'au 2020-01-01, donc aussi en 2018-2019. Sur ces deux années, j'ai mesuré 46 % de bougies vendeuses (taille moyenne -0,156), soit un écart d'environ 2×0,1×0,156×0,46 ≈ 1,4 point/an. Cela fait environ 0,3 point/an sur la colonne 2018-2026 à ×1, et à peu près L fois plus au-delà. Contrairement à ce que dit le lecteur, la colonne 2018-2026 est donc touchée elle aussi. Sur 2012-2019 : 28,6 % de bougies vendeuses, taille moyenne -0,159, écart ≈ 0,9 point/an.

### BTC-03 · majeur · confirme : La période 2012-2017 (« NOUVEAU ») ne teste pas le même système, et les noms NOUVEAU/ANCIEN sont inversés

`bitcoin/btc.py` : 13-16, 28-30, 96, 128, 135-136 ; bitcoin/profils.py:26

**Constat.** NOUVEAU = 2012-07 → 2018-01 et ANCIEN = 2018-01 → 2026-11-17 : la période la plus ancienne s'appelle « nouveau ». Ces noms laissent penser que 2018-2026 a servi au développement et que 2012-2017 est un test ajouté ensuite. Mais avant 2017-08, les votes orderflow et ethbtc sont absents : le score est la moyenne de 7 votes et non de 9, donc le seuil 0,25 correspond à un autre nombre net de votes (2/7 = 0,29 contre 3/9 = 0,33). Sur cette période, les coûts valent 0,30 % par côté, le financement est forfaitaire et les prix viennent de Bitstamp seul. Un résultat sur 2012-2017 ne valide donc pas la règle à 9 votes que le bot applique. Autre point : ANCIEN se termine au 2026-11-17, codé en dur, et englobe les jours après le 13 novembre. Dans le fichier Bitstamp, la journée du 17 et la bougie 4h de 16:00 sont partielles (téléchargées vers 16:05) ; elles sont exclues par `< b`, mais la borne n'est pas tenue à jour.

**Scénario.** Si l'on présente 2012-2017 comme une preuve hors échantillon, c'est la robustesse d'une variante à 7 votes qui est mesurée, pas celle du bot. Le vrai hors échantillon (après le 13/11/2026) se réduit à quelques jours, et il entre dans les colonnes « 2018-2026 » et « 2022-2026 ».

**Vérification.** btc.py:29-30 : NOUVEAU = 2012-07 → 2018, ANCIEN = 2018 → 2026-11-17 en dur. Les noms suivent sans doute la chronologie du développement (ancien = période de mise au point, nouveau = données ajoutées) plutôt que d'être une coquille ; le terme « inversés » relève donc de l'interprétation, mais le fond est juste. Je l'ai vérifié : le premier vote orderflow valide date du 2017-08-23 et le premier vote ethbtc du 2017-09-19. Avant, le score est une moyenne de 7 votes : il faut un solde net de 2 votes (0,286) au lieu de 3 sur 9 (0,333). Les coûts valent 0,30 % jusqu'au 2017-01-01 seulement (btc.py:128) : 2017 est déjà à 0,12 %. Les dernières barres Bitstamp sont partielles : le 4h du 2026-11-17 16:00 a un volume de 11,1, contre 247 pour la bougie précédente, et le 1d du 2026-11-17 a 469 contre 990. Le `< b` les exclut bien. Le vrai hors échantillon après le 13/11 ne compte que quelques jours, noyés dans les colonnes 2018-2026 et 2022-2026.

### BTC-04 · majeur · confirme : Surajustement : la recherche réelle dépasse largement les 135 réglages de REGLAGES, et la sélection n'est pas reproductible

`bitcoin/btc.py` : 116-119, 123-160 ; bitcoin/indicateurs.py:24-113 ; bitcoin/donnees.py:62-72, 91-173

**Constat.** REGLAGES = 5 seuils × 3 confirmations × 3 tailles de vente × 3 volatilités cibles = 135 combinaisons, et FINAL tombe au milieu de la grille. Mais le choix des 9 votes et de leurs paramètres n'est pas dans la grille : Fibonacci sur 90 jours aux niveaux 0,382 et 0,618, order flow sur 7 jours, on-chain sur 30 jours, ETH/BTC contre sa moyenne de 50 jours, VWAP ancré au mois alors que vwap_ancre accepte aussi la semaine, le trimestre et l'année. Le dépôt garde la trace d'essais abandonnés, inutilisés par la stratégie : atr, supertrend, bollinger, zscore, rang_glissant, vwap_glissant, vwap_depuis_plus_bas ; open interest et ratios long/short (metriques), Dukascopy, prime du perpétuel, Coinbase, Fear & Greed, DVOL, stablecoins, bougies 5 min, clôture journalière décalée (`decalage`, « 22 = 22:00 UTC »). Il cite aussi des scripts absents (01_telecharger_extra.py, 02_telecharger_m5.sh). Banc4h, stats, periode, REGLAGES et NOUVEAU ne sont appelés nulle part dans le dépôt : le code qui a servi à choisir FINAL n'y est pas.

**Scénario.** Le nombre réel d'essais est inconnu, mais il dépasse probablement plusieurs centaines de variantes. Un Sharpe obtenu sur 2018-2026 doit donc être fortement déprécié (Sharpe dégonflé, test de White ou Hansen). On ne peut pas refaire la sélection pour vérifier que FINAL n'a pas été pris au sommet d'un pic isolé.

**Vérification.** Grille de btc.py:116-118 : 5×3×3×3 = 135 combinaisons. FINAL est au milieu de chaque dimension. Un grep sur le dépôt, hors revue/, confirme que Banc4h, stats, periode, REGLAGES et NOUVEAU ne sont appelés nulle part ; FINAL ne sert qu'à test_bot.py:199. Restent inutilisés par la stratégie : indicateurs.py:31-113 (atr, vwap_glissant, vwap_depuis_plus_bas, rang_glissant, zscore, bollinger, supertrend), ainsi que donnees.py:62-77 (decalage), 91-98 (metriques), 110-129 (dukascopy) et 132-173 (prime_perp, coinbase, Fear & Greed/DVOL/stablecoins, m5). Les scripts 01_telecharger_extra.py et 02_telecharger_m5.sh sont cités (donnees.py:132, 163) mais absents du dépôt. Le nombre réel d'essais reste inconnu : c'est une inférence, mais elle est solide.

### BTC-05 · majeur · confirme : Dépendance à l'API communautaire Coin Metrics : une panne bloque toute décision, et des données figées passent sans alerte

`bitcoin/donnees_live.py` : 233-238, 251 ; bitcoin/btc.py:77-81 ; bitcoin/strategie.py:300-312 ; bitcoin/bot.py:127

**Constat.** SourceLive.charger appelle onchain() sans garde. Une erreur HTTP (ConnectionError après 4 essais), une réponse sans les métriques FlowInExNtv/FlowOutExNtv (KeyError sur `d[[...]]`) ou une liste `data` vide (KeyError sur `d.time`) fait échouer tout le cycle à bot.py:127, en dehors du try qui traite DonneesInvalides. LISEZMOI dit pourtant qu'un vote manquant est seulement « absent ». Le bot ne peut alors plus rien faire, même réduire la position ; il réessaie toutes les 5 minutes. À l'inverse, votes() prend la dernière valeur disponible (`searchsorted(...)-1`), et verifier() ne contrôle ni la fraîcheur des données on-chain ni celle d'ETH/BTC : si Coin Metrics cesse de publier, le vote on-chain reste figé sur une vieille moyenne 30 jours sans alerte. Le backtest, lui, a toujours une valeur à J-2.

**Scénario.** L'API communautaire est gratuite, limitée en débit, et son catalogue de métriques a déjà changé par le passé. Le jour où FlowInExNtv n'y est plus servi, le bot reste bloqué dans sa dernière position (sans stop en montage ×1) jusqu'à une intervention manuelle. Avec un retard de publication de plusieurs jours, il décide sur un vote on-chain périmé alors que le backtest supposait une donnée fraîche.

**Vérification.** donnees_live.py:60-65 (pas 233-238) : onchain() n'a pas de garde. SourceLive.charger (l.71-79) l'appelle sans try, et bot.py:127 appelle charger avant le try qui ne traite que DonneesInvalides (l.128-134). L'exception remonte à boucle (l.219-224) : alerte, puis nouvel essai toutes les 5 minutes, sans aucun ordre, même pour réduire la position. À ×1, il n'y a pas de stop chez Binance. Deux nuances. Une liste `data` vide provoque une AttributeError sur `d.time` (pas une KeyError) : le résultat est le même. Pour ETH/BTC, une série figée ne fige pas le vote : eb est réindexé sur l'index de d1 (btc.py:82), donc le vote devient absent. Seul l'on-chain se fige, par le searchsorted-1 de btc.py:79-80. verifier (strategie.py:27-38) ne contrôle que d1 et d4. Le scénario est réaliste pour une API communautaire.

### BTC-06 · mineur · confirme : Financement attribué à la nouvelle position au lieu de l'ancienne (décalage d'une bougie)

`bitcoin/btc.py` : 129-134, 146 ; bitcoin/profils.py:308-315, 341

**Constat.** `g = searchsorted(idx, f.index, side="right") - 1` range le financement de 00:00, 08:00 et 16:00 dans la bougie qui commence à cette heure. Or la position t[i] de cette bougie est celle décidée à la clôture précédente, c'est-à-dire à cette même heure. Le bot ne passe ses ordres qu'à +90 s, voire jusqu'à environ 2 minutes de plus avec les ordres limites. Binance fait payer le financement aux positions ouvertes à l'instant T, donc à l'ancienne position.

**Scénario.** Ce n'est faux que lorsque la position change à 00:00, 08:00 ou 16:00 UTC, environ une fois sur deux changements. L'effet est faible (un taux de 0,01 % à 0,1 % par paiement appliqué à la mauvaise taille), mais il est systématique quand le bot ouvre ou ferme une vente juste à l'heure du financement.

**Vérification.** btc.py:130 et profils.py:35 : `searchsorted(idx, f.index, side='right') - 1` place le paiement de 08:00 dans la bougie qui commence à 08:00. Dans journalier, t[i] = p[i-1] est la position décidée à la clôture de 08:00 et tenue pendant cette bougie ; dans simuler, tenu = pos[i-1] et fund[i] (l.47, 67). Le bot n'exécute qu'à +90 s ou plus (bot.py:204), donc la position présente à 08:00:00 est l'ancienne. Le décalage d'une bougie est réel, mais il ne compte que lorsque la position change à 00:00, 08:00 ou 16:00. Effet faible.

### BTC-07 · mineur · confirme : Pas de données de financement après le 31/10/2026 16:00 : novembre 2026 est compté sans financement

`bitcoin/btc.py` : 129-134 ; bitcoin/profils.py:308-315 ; bitcoin/donnees.py:82-88

**Constat.** DN.financement('BTCUSDT') couvre 2020-01-01 → 2026-10-31 16:00 (7 488 paiements). Pour toute bougie postérieure, fund vaut 0 sans avertissement, dans Banc4h comme dans simuler, alors que les prix vont jusqu'au 17/11.

**Scénario.** Sur la seule période vraiment hors échantillon (après le 13/11/2026), ni les ventes ni les positions à levier (achats en perpétuel) ne paient ni ne reçoivent de financement. Pour un levier ×5 acheteur avec un financement de +10 %/an, cela fait environ 2,3 % sur 17 jours qui manquent.

**Vérification.** J'ai vérifié le cache BTCUSDT-funding : 7 488 paiements du 2020-01-01 00:00 au 2026-10-31 16:00. Dans Banc4h (btc.py:132-134) comme dans simuler (profils.py:39-41), fund vaut 0 pour toute bougie postérieure à 2020 sans paiement, sans avertissement. Les prix Bitstamp vont jusqu'au 2026-11-17. Le chiffrage (×5, +10 %/an, 17 jours ≈ 2,3 %) suppose une position acheteuse ×5 pendant tout le mois. C'est un majorant : l'effet est mineur.

### BTC-08 · mineur · confirme : Le backtest suppose un rééquilibrage continu et gratuit vers une fraction constante, alors que le bot a une bande de 5 %

`bitcoin/btc.py` : 140-147

**Constat.** `net = t*self.r - chg*self.cout` applique chaque bougie la même fraction t du capital, comme si la position était remise à t à chaque bougie, et ne facture que les changements de cible (`chg = |diff(t)|`). La dérive due au prix est donc corrigée sans frais. Le bot réel ne corrige rien sous 5 % du capital. test_rejeu (test_bot.py:161-190) ne compare les deux que sur 2018-2026, avec une tolérance de 0,25 point de Sharpe.

**Scénario.** Les écarts de trajectoire entre le backtest et le bot sont invisibles avant 2018. L'effet porte sur la forme de la courbe (rééquilibrage forcé contre dérive libre) plutôt que sur les frais ; Banc4h est même un peu prudent sur les frais, car il paie chaque petit changement de dose.

**Vérification.** btc.py:141-146 : net = t*r - |Δt|*coût. La position est remise gratuitement à la fraction t à chaque bougie, et seuls les changements de cible sont facturés. Le bot ne retouche rien dans la bande de 5 % (courtier.py:79-81). test_rejeu (test_bot.py:161-190) ne compare les deux que depuis 2018, sur les prix Binance, avec une tolérance de 0,25 de Sharpe. Le constat est exact et l'effet probablement faible.

### BTC-09 · mineur · confirme : Des votes à 0 sont comptés « présents », alors que les règles écrites ne prévoient que +1, −1 ou absent

`bitcoin/btc.py` : 66-67, 70, 74, 96

**Constat.** `etat(...)` renvoie 0 quand le prix est dans le nuage d'Ichimoku ou entre les niveaux 38,2 % et 61,8 % de Fibonacci, et sgn() renvoie 0 sur une égalité exacte. Ces 0 entrent dans la moyenne et diluent le score. LISEZMOI dit pourtant « chacun +1, −1 ou absent → score = moyenne des votes présents ».

**Scénario.** Sur les données réelles, Ichimoku vaut 0 sur 15 % des jours et Fibonacci sur 19 %. Ces jours-là, il faut plus de votes favorables pour franchir ±0,25. La règle publiée ne permet pas de refaire le calcul à l'identique.

**Vérification.** btc.py:67, 70 et 74 : etat() renvoie 0 dans le nuage d'Ichimoku et entre les niveaux 38,2 % et 61,8 % de Fibonacci. Ces 0 entrent dans la moyenne (l.96, skipna ne retire que les NaN). Mesuré depuis 2012-07 : Ichimoku vaut 0 sur 14,4 % des jours et Fibonacci sur 19,2 %. Les autres votes ne valent jamais 0. LISEZMOI dit « +1, −1 ou absent » : l'écart avec la règle écrite est réel.

### BTC-10 · mineur · confirme : Les chiffres du backtest viennent de Bitstamp BTC/USD, alors que le bot négocie Binance BTCUSDT ; le test de concordance est lâche

`bitcoin/btc.py` : 34-41 ; bitcoin/donnees_live.py:246-251 ; bitcoin/test_bot.py:193-204

**Constat.** Le backtest calcule les prix, les tendances 4h, la VWAP (pondérée par le volume Bitstamp) et la volatilité sur Bitstamp. Le bot calcule tout sur Binance BTCUSDT (en USDT, avec le volume Binance). test_concordance n'exige que 90 % de positions de même signe.

**Scénario.** Mesuré depuis 2018-06 : 98,5 % des bougies 4h ont le même signe de position, sans aucune bougie de sens opposé (les 1,5 % restants opposent une position et une absence de position) ; écart moyen de taille 0,008. Les votes divergent sur 1,5 % des jours pour la VWAP, 1,0 % pour le MACD, environ 0,6 % pour Ichimoku et le RSI. Impact limité, mais le seuil de 90 % du test laisserait passer une divergence bien plus forte (par exemple un décrochage de l'USDT).

**Vérification.** J'ai refait le calcul de test_concordance (SourceHistorique contre brutes, FINAL, depuis 2018-06-01). Même signe : 98,52 %, sens opposé : 0,0 %, écart absolu moyen de taille : 0,0079. Ce sont les chiffres du lecteur. Le seuil `accord > 0.9` (test_bot.py:204) est lâche. La volatilité, la VWAP et les tendances 4h du backtest viennent bien de Bitstamp (btc.py:34-41).

### BTC-11 · mineur · confirme : Le test de parité ne reproduit ni la fenêtre du bot en direct ni les données flash

`bitcoin/test_bot.py` : 145-158 (et bitcoin/donnees_live.py:255-274)

**Constat.** test_le_bot_decide_exactement_comme_le_backtest passe par SourceHistorique : historique Binance complet depuis 2017, fichier Coin Metrics révisé complet, ETH/BTC complet. En direct, le bot n'a que 1 000 jours, 1 500 bougies 4h, 150 jours de Coin Metrics flash et 200 jours d'ETH/BTC. Le test ne couvre donc ni les fenêtres courtes ni les données on-chain non révisées. J'ai vérifié sur des données synthétiques que l'amorçage des moyennes ewm (adjust=False) est négligeable : EMA200 4h sur 1 499 bougies, écart relatif de 4,8e-8 ; MACD et RSI sur 999 jours, identiques au calcul complet. Le vrai trou du test est donc la source des données on-chain (voir BTC-01), pas la longueur des fenêtres.

**Scénario.** Le test passe alors que le bot réel peut décider autrement à chaque fois qu'une valeur flash de Coin Metrics diffère de la valeur révisée et que le vote on-chain est décisif (environ 8 % des bougies, voir BTC-01).

**Vérification.** test_bot.py:145-158 passe par SourceHistorique (donnees_live.py:82-101, pas 255-274), qui garde tout l'historique Binance et tout le fichier Coin Metrics révisé. SourceLive (l.71-79) n'a que 1 000 jours, 1 500 bougies 4h, 200 jours d'ETH/BTC et 150 jours de Coin Metrics flash. Pour les ewm (indicateurs.py:10-28), l'amorçage sur plus de 1 000 bougies est bien négligeable : (1-2/201)^1300 ≈ 2e-6. Le vrai trou du test, ce sont les données on-chain non révisées. Je n'ai pas refait la mesure synthétique du lecteur.

### BTC-12 · mineur · confirme : Un test exige un Sharpe supérieur à 1 sur la période déjà vue

`bitcoin/test_bot.py` : 161-190

**Constat.** `assert sh_bot > 1.0 and abs(sh_bot - sh_bt) < 0.25` fait d'une performance passée sur 2018-2026 une condition de réussite. Le « backtest » de ce test (l.183-187) n'est pas Banc4h : pas de financement, frais fixes à 0,12 %, prix Binance. Il ne valide donc pas les chiffres Bitstamp de profils.py.

**Scénario.** Le test ne montre que la cohérence entre le rejeu papier et un calcul simplifié sur des données vues. Sa réussite peut être prise à tort pour une preuve d'avantage.

**Vérification.** test_bot.py:190 : `assert sh_bot > 1.0 and abs(sh_bot - sh_bt) < 0.25`. Le « backtest » des l.183-187 n'a ni financement ni coûts avant 2017, il prend 0,12 % fixe et les prix Binance. Ce n'est pas Banc4h, ni simuler. Le test fait d'une performance déjà vue une condition de réussite et ne valide pas profils.json.

### BTC-13 · mineur · confirme : Le modèle de stop et de liquidation de profils.simuler ne correspond pas au montage réel

`bitcoin/profils.py` : 327-338 (contre bitcoin/courtier.py:114-119)

**Constat.** (a) À ×1, la vente est en marge isolée égale à sa taille. LISEZMOI : liquidation si le BTC double, avec une perte limitée à cette marge. simuler applique pourtant `liq = 1/|tenu| - 0.005`, soit +399,5 % pour tenu = -0,25, et met tout le capital à zéro. (b) simuler ne pose un stop que si |tenu| > 1, alors que prix_stop en pose un pour toute position du montage perpétuel. Pour une position acheteuse de moins de 0,5, il donne même un prix négatif : `prix*(1-0.5/|cible|)`. (c) Le stop est testé sur le plus bas Bitstamp en dernier prix, alors que le vrai stop porte sur le prix de marque Binance. (d) Les sauts de prix au-delà du stop ne sont pas simulés (c'est documenté). (e) Chaque stop coûte environ 50 % du capital, et la simulation reprend la position dès la bougie suivante, comme le ferait le bot.

**Scénario.** Effet chiffré faible sur les données 4h, car le BTC n'a jamais doublé en 4h. Mais le nombre de « stops » et de « liquidations » affiché dans profils.json ne décrit pas le risque réel d'une liquidation en marge isolée ni d'un stop rejeté par Binance (prix négatif) à fort levier et faible exposition.

**Vérification.** Bonnes lignes : profils.py:53-69. (a) À L=1, liq = 1/|tenu| - 0,005, soit +399,5 % pour tenu = -0,25, et e = 0 met tout le capital à zéro. Pourtant courtier.py:246 passe en marge isolée ×1 : la liquidation arrive vers +100 % et la perte est limitée à la marge. Le seuil est trop large et la perte trop forte, mais l'événement n'a jamais lieu sur ces données. (b) Le stop n'est simulé que si |tenu| > 1 (l.57), alors que prix_stop (courtier.py:114-119) en pose un pour toute position du montage perpétuel. Pour 0 < cible < 0,5 à l'achat, le prix serait négatif. J'ai mesuré qu'à ×2 et ×3 aucune cible acheteuse < 0,5 n'est apparue depuis 2019-09. En revanche, des ventes avec |cible| < 0,5 existent (25 % des bougies à ×2) : leur stop est placé à plus de deux fois le prix ; Binance l'accepte-t-il ? Je ne l'ai pas vérifié. (c) et (d) sont exacts. (e) e *= 1 - |tenu|*(s+0,005) ≈ 0,5 : chaque stop coûte bien environ la moitié du capital. Au total : mineur pour les chiffres, mais cela rejoint l'oubli sur le coupe-circuit.

### BTC-14 · mineur · confirme : profils.json est calculé pour le seul profil prudent (vente 0,25), quelle que soit la configuration

`bitcoin/profils.py` : 307, 363

**Constat.** simuler() et main() codent en dur `seuil=0.25, confirmation='ema50/200', vente=0.25, vol_cible=0.4`. bot.py:79-81 accepte pourtant le profil `equilibre` (volatilité cible 0,6) et `vente` réglable (0 ou autre). Étrave affiche les chiffres de profils.json pour chaque levier sans tenir compte du profil choisi.

**Scénario.** Avec profil equilibre et levier ×3, l'exposition réelle vaut 1,5 fois celle des chiffres montrés (risque, pire baisse, liquidations sous-estimés).

**Vérification.** profils.py:33 et 89 codent en dur vente=0,25 et vol_cible=0,4 (pas aux l.307 et 363 citées). bot.py:79-81 accepte le profil equilibre (vol_cible 0,6, strategie.py:18) et une vente réglable. etrave/bitcoin.py:33 et 370 lisent profils.json, qui n'a aucune dimension de profil. Je n'ai pas ouvert page.html (interdit) : je n'ai donc pas vérifié l'affichage. Correction : le rapport 1,5 est un majorant. Avec le plafond de dose à 1, il tombe à 1,25 quand la volatilité vaut 0,5 et à 1 sous 0,4.

### BTC-15 · mineur · confirme : Les votes contrôlés et affichés ne sont pas ceux du jour qui a servi au score (cycle de 00:00)

`bitcoin/strategie.py` : 327-337 (et bitcoin/btc.py:87-90)

**Constat.** caler() n'utilise un jour J qu'à partir des bougies 4h qui commencent à J+1 00:00. Au cycle de 00:01:30, la dernière bougie 4h est celle de J 20:00 : le score vient donc de J-1. Pourtant `votes = E['votes'].iloc[-1]` (jour J) sert au contrôle « plus de 2 votes absents » et au message Telegram/Étrave. Ce retard de 4h n'est pas un regard vers le futur : il est prudent, et identique dans le backtest et le bot. Je l'ai vérifié sur des données synthétiques.

**Scénario.** Une fois par jour, le message affiche des votes qui ne correspondent pas au score ni à la décision. Un vote absent le jour J peut bloquer une décision qui n'utilise que J-1, et inversement.

**Vérification.** strategie.py:54-60 (pas 327-337). À 00:01:30 le jour J+1, tronquer garde la bougie journalière J (J + 1 jour ≤ t) et la bougie 4h de J 20:00. caler (btc.py:87-90) donne à cette bougie le jour dont la disponibilité tombe au plus tard à 20:00, c'est-à-dire J-1. Le score vient donc de J-1, alors que `votes = E['votes'].iloc[-1]` et `jour` désignent J. Ce sont ces votes de J qui servent au contrôle des absents et au message. Aux autres cycles de la journée, les deux correspondent. Ce n'est pas un regard vers le futur.

### BTC-16 · mineur · confirme : Les fenêtres glissantes comptent des lignes, pas du temps, et sans min_periods : un trou désactive un vote longtemps

`bitcoin/btc.py` : 76, 78, 82-83

**Constat.** `of.delta.rolling(7)`, `(...).rolling(30)` et `I.sma(eb, 50)` (min_periods = n) propagent un NaN sur 7, 30 ou 50 jours. Pour le on-chain, la moyenne porte sur 30 lignes et non 30 jours : un trou dans la réponse de Coin Metrics étire la fenêtre. En direct, une journée ETH/BTC absente rend le vote ethbtc absent pendant 50 jours.

**Scénario.** Le jeu historique n'a aucun jour manquant depuis 2017 (j'ai vérifié : 0 jour manquant pour BTCUSDT et ETHBTC, mais 30 et 28 jours bâtis avec moins de 24 bougies 1h). En direct, un trou ponctuel suffit à rendre un vote absent pendant des semaines. Avec un autre vote absent, il n'en faut qu'un troisième pour que le bot cesse de décider.

**Vérification.** btc.py:76 : of est réindexé sur l'index de d1, donc la fenêtre de 7 lignes fait 7 jours tant que d1 n'a pas de trou. btc.py:78 : rolling(30) porte sur les lignes du fichier Coin Metrics, non réindexées : un jour manquant étire la fenêtre, et une valeur NaN rend le vote absent pendant 30 lignes. btc.py:82-83 et indicateurs.py:7 : sma avec min_periods=50, donc une journée ETH/BTC manquante rend le vote absent pendant 50 jours. Le scénario est peu probable avec les klines Binance, mais exact. Je n'ai pas revérifié le décompte des journées à moins de 24 bougies 1h.

### Oublis relevés par le vérificateur

- **majeur** · Le coupe-circuit à 40 % n'est simulé ni dans profils.simuler ni dans Banc4h : dès ×2, les chiffres de profils.json décrivent une trajectoire que le bot ne suivrait pas (`bitcoin/profils.py` : 29-72 (contre bitcoin/bot.py:31, 149-154)) : Le bot ferme tout et s'arrête si le capital tombe à plus de 40 % sous son plus haut (perte_max=0,40 par défaut), puis il faut le réarmer à la main. simuler n'en tient pas compte. J'ai mesuré la pire baisse de simuler, avec stop. Depuis 2012-07 : ×1 -31 %, ×2 -66 %, ×3 -72 %, ×5 -96 %. Depuis 2018 : ×1 -23 %, ×2 -46 % (seuil franchi le 2020-02-20), ×3 -62 %, ×5 -93 %. Dès ×2, le bot réel aurait donc été arrêté. Les rendements annuels affichés par levier dans Étrave supposent qu'il continue.
- **mineur** · Stops, liquidations et exposition maximale comptent la période de chauffe 2011-09 → 2012-06 (`bitcoin/profils.py` : 44-46, 92-96) : La boucle de simuler part de la première bougie de 2011, pas de DEBUT. Les positions sont non nulles dès le 2011-09-20, sur 58 % des bougies avant DEBUT, jusqu'à une exposition de 1,0, avec un score calculé sur quelques votes seulement (MA200 encore absente). n_stop, n_liq et expo_max (sans filtre DEBUT, contrairement à expo_moyenne) incluent cette période. Une ruine pendant la chauffe marquerait aussi toutes les colonnes comme ruinées.
- **mineur** · Ventes de 2012-2016 non exécutables comme simulées, avec un coût d'emprunt forfaitaire arbitraire (`bitcoin/btc.py` : 128, 135-136 (et bitcoin/profils.py:37)) : Le backtest vend à découvert sur les prix Bitstamp dès 2012 (22 % des bougies sur 2012-2017). Or Bitstamp n'offrait pas la vente à découvert, et les perpétuels ne datent que de 2016. Le coût réel d'un emprunt sur marge (Bitfinex) était variable et souvent supérieur à 10 %/an. Le résultat sur 2012-2016 repose donc sur une hypothèse non vérifiable, prise dans un sens dans Banc4h et dans l'autre dans simuler (voir BTC-02). Mon niveau de certitude sur les conditions de marge de l'époque est moyen.

### Non vérifié par le lecteur

- L'ampleur des révisions de Coin Metrics : sans les anciennes versions (vintages) de FlowInExNtv et FlowOutExNtv, je n'ai pas pu mesurer combien de signes du vote on-chain changent entre les valeurs flash d'origine et les valeurs recalculées en 2026, ni l'effet sur le rendement.
- Que l'API communautaire Coin Metrics serve bien FlowInExNtv et FlowOutExNtv aujourd'hui, avec quel délai et quel débit autorisé : aucun appel réseau fait.
- Le comportement de data-api.binance.vision/api/v3/klines avec endTime seul (pagination des 1 500 bougies 4h) : non testé contre l'API.
- Aucun rendement calculé : conformément à la consigne, aucun backtest long. Les chiffres donnés (8 % de bougies où le vote on-chain est décisif, 98,5 % d'accord Binance/Bitstamp, part et taille des ventes) portent sur les décisions, pas sur les rendements. L'écart de financement de BTC-02 est un ordre de grandeur estimé, pas simulé.
- Que l'horodatage Bitstamp soit le début de la bougie : je l'ai déduit des données, la clôture de la bougie 4h de 20:00 égale la clôture journalière dans 100 % des cas ; pas confirmé par la documentation Bitstamp.
- courtier.py et bot.py (passage des ordres, marge isolée, STOP_MARKET) sont hors de mon domaine : je ne les ai lus que pour les points qui touchent au calcul (prix_stop, ordre des opérations dans le cycle).
- Le nombre réel de variantes essayées avant de retenir FINAL : le code de sélection n'est pas dans le dépôt.

## Bot BTC : exécution chez Binance

### ★ BTC-EX-01 · critique · confirme : Transfert spot -> futures mal formé avec la version actuelle de ccxt : la vente et tout le montage à levier ne peuvent jamais s'ouvrir

`bitcoin/courtier.py` : 322-329 (transfer 'spot'->'future' et 'future'->'spot')

**Constat.** Le code appelle self.spot.transfer('USDT', m, 'spot', 'future'). Dans ccxt 4.5.93 (la version que donne aujourd'hui `pip install ccxt`, que LISEZMOI ne fige pas), la clé 'future' n'existe plus dans options['accountsByType'] (seuls main/spot/funding/margin/cross/linear/swap/inverse/option restent). convert_type_to_account renvoie alors 'FUTURE', que ccxt prend pour un symbole de marge isolée. J'ai simulé hors ligne, avec sapiPostAssetTransfer intercepté : spot->future envoie {'type': 'MAIN_ISOLATED_MARGIN', 'toSymbol': 'FUTURE'} et future->spot envoie {'type': 'ISOLATED_MARGIN_MAIN', 'fromSymbol': 'FUTURE'}. Binance refusera ces demandes. Correspondance 'future' -> 'UMFUTURE' : présente jusqu'à ccxt 4.5.85, absente à partir de 4.5.90 (wheels comparées). Le nom de compte correct reste 'future' avec un ccxt ancien, 'linear'/'swap' avec un ccxt récent.

**Scénario.** Montage x1, signal VENTE alors que le compte détient du BTC : le plan est vendre_spot -> vers_futures -> perp. Le BTC est vendu, puis le transfert lève une exception (bot.py:165-167). Le cycle s'arrête et reprend toutes les 5 minutes avec le même échec. Le compte reste à 0 % au lieu de -25 % x dose, et Telegram reçoit une erreur toutes les 5 minutes. En x2 à x10, rien ne s'ouvre jamais : le capital reste en USDT au comptant. La stratégie exécutée n'est donc pas celle du backtest (ni vente, ni levier). Si un ancien ccxt était installé, ce constat disparaît, mais BTC-EX-02 s'aggrave.

**Vérification.** courtier.py:325 et 329 appellent bien self.spot.transfer('USDT', m, 'spot', 'future') puis ('future','spot'). J'ai installé ccxt 4.5.93 dans un venv à part et intercepté sapiPostAssetTransfer. options['accountsByType'] ne contient plus 'future' (seulement cross, funding, inverse, linear, main, margin, option, spot, swap), et la requête envoyée est {'type': 'MAIN_ISOLATED_MARGIN', 'toSymbol': 'FUTURE'}. Dans l'autre sens, c'est {'type': 'ISOLATED_MARGIN_MAIN', 'fromSymbol': 'FUTURE'}. Le code de transfer (binance.py:9620-9667) traite tout identifiant inconnu comme un symbole de marge isolée. Avec ccxt 4.5.85, la même simulation donne MAIN_UMFUTURE et UMFUTURE_MAIN, ce qui est correct. Je n'ai pas vérifié les versions 4.5.87 à 4.5.92 une par une. LISEZMOI.md:88 dit seulement « pip install ccxt », sans fixer de version : on installe donc aujourd'hui la 4.5.93. Le scénario est juste : l'ordre « vendre_spot » s'exécute, puis le transfert lève une exception à bot.py:165-167 et le compte reste à plat. En x2-x10, aucune position ne s'ouvre. Voir aussi l'oubli sur la permission « Universal Transfer », qui peut faire échouer le transfert même avec un ancien ccxt.

### ★ BTC-EX-02 · critique · confirme : Stop de protection : jamais annulé ni déplacé avec un ccxt récent, refusé avec un ccxt ancien

`bitcoin/courtier.py` : 334-351 ; bitcoin/bot.py:168-170

**Constat.** poser_stop envoie create_order(PERP, 'STOP_MARKET', ..., {stopPrice, closePosition: True, workingType: 'MARK_PRICE'}). Avec ccxt 4.5.93, j'ai simulé la requête : elle part sur fapiPrivatePostAlgoOrder (type STOP_MARKET, triggerPrice, closePosition true, algoType CONDITIONAL, sans quantité), ce qui est correct. Mais annuler_stop appelle fetch_open_orders(PERP) sans {'trigger': True}. Cet appel interroge fapiPrivateGetOpenOrders (les ordres ordinaires) et ne voit donc jamais l'ordre conditionnel ; cancel_order sans trigger ne viserait pas non plus l'API algo. Binance refuse un second closePosition dans le même sens (code -4130, que ccxt connaît ; non vérifié en direct). Avec un ccxt sans routage algo (avant environ 4.5.40), STOP_MARKET part sur /fapi/v1/order. Binance renvoie alors -4120 « Order type not supported for this endpoint. Please use the Algo Order API endpoints instead. » (message repris dans la table d'erreurs de ccxt).

**Scénario.** Levier x3, achat ouvert au cycle 1 avec un stop à P x (1 - 0,5/3). Cycle 2 : le stop n'est pas vu, donc pas annulé, et le nouveau stop est refusé. L'exception survient à bot.py:169, après les ordres. derniere_bougie, le journal et etat.json ne sont jamais mis à jour, le cycle est rejoué toutes les 5 minutes et le stop reste à son ancien prix, qui peut être très loin. Lors d'un passage de l'achat à la vente, l'ancien stop SELL closePosition reste en place. Avec un ccxt ancien : aucun stop n'est jamais posé, et chaque cycle en x2-x10 finit en erreur. Dans tous les cas, la position à levier n'a pas la protection prévue et seule la liquidation la borne.

**Vérification.** Vérifié dans ccxt 4.5.93. fetch_open_orders (binance.py:7824-7859) n'interroge fapiPrivateGetOpenAlgoOrders que si params contient stop, trigger ou conditional. Sans ce paramètre, il interroge fapiPrivateGetOpenOrders. annuler_stop (courtier.py:335) n'en passe aucun. cancel_order (binance.py:8279-8288) ne vise l'API algo que si trigger est vrai. À l'inverse, create_order avec stopPrice est routé vers fapiPrivatePostAlgoOrder (algoType CONDITIONAL, binance.py:6788-6823). ccxt 4.5.85 se comporte de la même façon. La table d'erreurs de ccxt contient bien -4120 « Please use the Algo Order API endpoints instead » et -4130. poser_stop étant appelé à chaque cycle (bot.py:169), dès le deuxième cycle dans le même sens le nouveau stop closePosition est refusé : le cycle lève une exception après les ordres, derniere_bougie n'est jamais mise à jour, et le cycle est rejoué toutes les 5 minutes. Lors d'un retournement, l'ancien stop du sens opposé n'est pas annulé. Je n'ai pas vérifié en direct le comportement de Binance (-4130, ordres conditionnels absents de /fapi/v1/openOrders). Il est cohérent avec la migration vers le service Algo que reflète ccxt. Certitude moyenne à haute.

### BTC-EX-03 · critique · confirme : Ordres orphelins : toutes les erreurs sont avalées, sans identifiant client ni nettoyage au démarrage, ce qui peut doubler la position

`bitcoin/courtier.py` : 283-299 (except Exception: continue ; cancel avalé) ; bot.py:209-216 (cycle relancé au démarrage)

**Constat.** Dans _ordre, toute exception de create_order est traitée comme « le prix a bougé » (except Exception: sleep(1); continue), y compris un RequestTimeout ou une erreur réseau alors que Binance a peut-être accepté l'ordre. L'id n'est alors pas mémorisé, et l'ordre n'est ni annulé ni compté dans « fait ». Un échec de cancel_order est lui aussi avalé : si l'ordre reste ouvert, la boucle en place un autre pour « restant ». Si le processus est tué pendant time.sleep(15) (Arrêter dans Étrave, redémarrage Windows, systemd), l'ordre limite (GTC LIMIT_MAKER au comptant, GTX en perpétuel) reste dans le carnet. Aucun code n'annule les ordres ouverts au début d'un cycle, et aucun newClientOrderId ne permet d'éviter les doublons. Le plan suivant part des soldes : un ordre en attente n'apparaît pas dans perp_btc et sera donc placé une seconde fois.

**Scénario.** Montage x3, ouverture de 0,4 BTC en perpétuel. create_order dépasse le délai d'attente mais l'ordre est accepté. La boucle replace 0,4 BTC 1 seconde plus tard, puis envoie le reste au marché. Si l'ordre fantôme s'exécute aussi, la position atteint 0,8 BTC, soit environ x6 au lieu de x3, et la liquidation se rapproche de moitié. Même effet si le bot est tué pendant l'attente de 15 s puis relancé : le premier cycle tourne aussitôt (reveil = maintenant) et replace l'ordre complet.

**Vérification.** Le code est confirmé. courtier.py:283-287 avale toute exception de create_order, délai d'attente compris. Un échec de cancel_order est avalé lignes 292-295. Plusieurs appels sont en dehors du try : fetch_order_book (281) et fetch_order (290, 296). S'ils lèvent une exception après la création d'un ordre, celui-ci reste dans le carnet sans être suivi. Aucun newClientOrderId n'est passé, et rien n'annule les ordres ouverts au démarrage : annuler_stop ne vise que les STOP. Avec ccxt, le post-only devient LIMIT_MAKER au comptant et GTX en perpétuel, deux ordres persistants. En revanche, l'ampleur annoncée est exagérée. La marge initiale réservée par les ordres ouverts plafonne le notionnel total à ceil(L) x capital, puisque set_leverage(ceil(L)) est appelé. Passer de 0,4 à 0,8 BTC (x6 avec un levier 3) est donc impossible si le levier est bien réglé. Le doublement est possible seulement quand la cible vaut au plus L/2, soit dose ≤ 0,5. En x1, le solde USDT et la marge isolée à levier 1 l'empêchent presque toujours. Je garde « critique » pour une autre raison : un ordre orphelin non suivi peut s'exécuter plus tard à contre-sens, après un retournement. Au comptant, il bloque le BTC, donc libre ≈ 0 et amount_to_precision lève une exception (voir EX-15). Un arrêt pendant le sleep de 15 s est fréquent (bouton Arrêter d'Étrave, redémarrage Windows).

### ★ BTC-EX-04 · critique · confirme : Le coupe-circuit peut laisser la position ouverte et bloquer le bot définitivement

`bitcoin/bot.py` : 125-126, 152-158, 161-167, 219-223 ; courtier.py:317-319

**Constat.** self.etat['arrete'] est posé (ligne 154) AVANT que la fermeture soit exécutée. (a) Si un ordre de fermeture échoue (exception ligne 167), boucle() sauvegarde l'état avec 'arrete' (lignes 222-223). Au cycle suivant, la ligne 125 renvoie « arrêté » sans plus rien tenter, alors que la position est toujours ouverte. (b) Si un fichier PAUSE existe (pause posée depuis Étrave), le coupe-circuit pose 'arrete' mais n'exécute aucun ordre (ligne 161). L'état est sauvé, et après la levée de la pause le bot reste « arrêté » avec la position ouverte. (c) En perpétuel, executer('perp', 'fermer') appelle annuler_stop() avant l'ordre : si cet ordre échoue, la position peut rester sans stop (si l'annulation a fonctionné ; voir BTC-EX-02).

**Scénario.** Le capital tombe sous 60 % du plus haut pendant que le bot est en pause, ou pendant que Binance refuse un ordre (minimum, marge, réseau). Le message Telegram « ⚠️ coupe-circuit … » laisse croire que tout est fermé. En réalité la position reste ouverte, sans surveillance, jusqu'à ce que l'utilisateur crée FERMER ou REARMER. Au-delà de -40 %, la perte continue sans limite, jusqu'à la liquidation en montage à levier.

**Vérification.** bot.py:152-154 pose etat['arrete'] avant d'exécuter le plan. Cas (a) : une exception à la ligne 167 remonte, et boucle() sauvegarde l'état avec 'arrete' (lignes 222-223). Au cycle suivant, la ligne 125 renvoie « arrêté » sans action, sauf s'il existe un fichier FERMER. Le dernier message reçu est « erreur de cycle… Nouvel essai dans 5 minutes », ce qui est trompeur : l'essai suivant ne fait rien, puis silence. Cas (b) : avec PAUSE, pause=True, donc aucun ordre, mais 'arrete' est sauvegardé (lignes 188-198). C'est un écart avec LISEZMOI.md:31 (« le bot ferme tout et s'arrête »). Dans ce cas, le message Telegram indique tout de même « ⏸ PAUSE : aucun ordre passé ». Il est donc moins trompeur que ne le dit le lecteur, mais la position reste ouverte. Cas (c) : il est exact que annuler_stop est appelé avant l'ordre de fermeture (courtier.py:318-319). Avec un ccxt récent, cet appel n'annule rien de toute façon (EX-02).

### BTC-EX-05 · majeur · confirme : Étrave croit le bot arrêté pendant un cycle, ce qui permet d'en lancer un second sur le même compte

`bitcoin/bot.py` : 110-117, 213-216, 252-254 ; etrave/bitcoin.py:35, 261-269, 278-292

**Constat.** Le battement (vivant.json) n'est écrit qu'avant et après bot.cycle(). Un cycle avec des ordres limites dure 8 x (15 s + appels) ≈ 2 min par ordre, soit 4 à 6 min pour un plan vendre_spot + transfert + perp, plus le téléchargement des données. Étrave considère le bot arrêté au-delà de 60 s sans battement (BATTEMENT_S = 60) et accepte alors « Démarrer ». bot.pid est écrit mais ne sert jamais de verrou. lancer_bot.bat ne vérifie rien non plus.

**Scénario.** Pendant un rééquilibrage, la page affiche « arrêté » et l'utilisateur clique sur Démarrer. Le second processus lance aussitôt un cycle (reveil = maintenant) et lit des soldes que le premier n'a pas fini de modifier. Les deux envoient les mêmes ordres et la position est doublée (x2 visé -> x4 en montage perpétuel). Même risque si le .bat lancé par le Planificateur de tâches tourne en même temps qu'un bot démarré depuis Étrave.

**Vérification.** Le battement n'est écrit qu'aux lignes 214 et 225 de bot.py, rien pendant cycle(). etrave/bitcoin.py:35 fixe BATTEMENT_S = 60, et processus() (lignes 261-269) déclare le bot arrêté au-delà. demarrer() (ligne 279) ne refuse que si en_marche, et bot.pid n'est jamais vérifié comme verrou. Un cycle comprend le téléchargement de 1 000 + 1 500 + 200 bougies, Coin Metrics, puis jusqu'à 8 x 15 s par ordre. Il dure facilement plus de 60 s. Je baisse la sévérité à « majeur » pour trois raisons. Il faut une action de l'utilisateur pendant cette fenêtre. En x1 (le défaut), le second processus est presque toujours bloqué par le solde USDT au comptant et par la marge isolée déjà réservée. En x2+, le doublement est plafonné par ceil(L) x capital (voir EX-03) : de x2 visé on peut passer à x4 seulement si la dose est ≤ 0,5.

### ★ BTC-EX-06 · majeur · confirme : Testnet inutilisable : la « première étape » de LISEZMOI est impossible

`bitcoin/courtier.py` : 234-240, 325, 329

**Constat.** Avec ccxt 4.5.x (au moins depuis 4.5.20), tout appel privé futures en mode sandbox lève NotSupported : « testnet/sandbox mode is not supported for futures anymore … consider using the demo trading » (vérifié par sign() sur fapiPrivateV3). Le transfert sapi n'a pas d'URL de test : NotSupported « does not have a testnet/sandbox URL for sapi endpoints » (vérifié). De plus, les testnets spot (testnet.binance.vision) et futures (testnet.binancefuture.com) demandent deux paires de clés distinctes, alors que CourtierBinance n'en utilise qu'une pour les deux. Le mode démo de Binance (enable_demo_trading) n'est pas géré.

**Scénario.** L'utilisateur passe en mode testnet comme le recommande LISEZMOI. Chaque cycle échoue dès etat() -> fetch_balance futures, avec un message toutes les 5 minutes. Faute de pouvoir tester, il risque de passer directement en réel sans qu'aucun appel (transfert, marge, stop) ait jamais été validé.

**Vérification.** Vérifié avec ccxt 4.5.93, en appelant sign() en mode sandbox. Pour fapiPrivateV3 'account', j'obtiens NotSupported « testnet/sandbox mode is not supported for futures anymore… consider using the demo trading » (binance.py:12532-12533). Pour sapi, NotSupported « does not have a testnet/sandbox URL for sapi endpoints ». Le spot privé passe bien par testnet.binance.vision. load_markets ne plante pas : fetch_currencies est sauté en sandbox. En revanche, etat() lève l'exception sur fut.fetch_balance à chaque cycle. enable_demo_trading existe (binance.py:3117) mais n'est jamais utilisé. CourtierBinance n'a qu'une paire de clés pour les deux testnets. La « première étape : le testnet » de LISEZMOI.md:191 est donc impossible avec ce code.

### BTC-EX-07 · majeur · plausible : Marge à 100 % exactement : refus « Margin is insufficient » (-2019) probables

`bitcoin/courtier.py` : 95-99, 101-103, 250 ; strategie.py:311

**Constat.** Montage comptant : la marge transférée vaut exactement -perp_vise x prix 'last' (ligne 95), avec marge isolée et levier 1. Pour une vente, Binance calcule la marge initiale sur max(mark, prix de l'ordre), plus la perte d'ouverture (open loss) d'un ordre au marché. Avec un ordre post-only placé au meilleur ask (au-dessus de 'last'), la marge demandée dépasse la marge déposée, sauf si la troncature de la quantité au pas de 0,001 BTC compense par chance. Montage perpétuel : cible = pos x L et levier = ceil(L) = L. Dès que pos = 1 (volatilité ≤ volatilité cible, fréquent en « prudent »), la marge initiale demandée vaut tout le portefeuille. Toute différence de prix ou toute perte d'ouverture provoque alors un refus. Non vérifié en direct (API bloquée, code 451).

**Scénario.** x3, volatilité du BTC à 35 %, cible 3,0 : ordre limite d'achat de 3 x C / P avec exactement C en marge. Si Binance refuse ou n'exécute qu'une partie, le reste part au marché et est de nouveau refusé (-2019), et le cycle échoue. Si cela tombe après la vente du comptant, le compte reste à plat ou en exposition partielle, et la tentative se répète toutes les 5 minutes.

**Vérification.** Le code est confirmé. Ligne 95 : marge_visee = -perp_vise x prix 'last' du ticker spot (ligne 261). Ligne 250 : levier 1, marge isolée. Ligne 76 : en perpétuel, cible = pos x L avec un levier de ceil(L) = L, donc la marge initiale vaut 100 % du portefeuille dès que pos = 1. amount_to_precision tronque la quantité vers le bas, ce qui laisse un peu de marge. Mais le prix vient du spot alors que l'ordre part en perpétuel : un écart (base) de 0,02 à 0,1 % entre les deux, ou la perte d'ouverture d'un ordre au marché, peuvent dépasser cette réserve. Le refus -2019 dépend donc de la base, de la taille du compte et des règles exactes de marge de Binance. Je ne peux pas le vérifier sans accès à l'API (451 depuis cette machine). Je le classe plausible, pas confirmé.

### BTC-EX-08 · majeur · confirme : Réglage marge isolée/croisée et levier : erreurs avalées sans vérification, et réglage fait seulement au démarrage

`bitcoin/courtier.py` : 243-252 ; bot.py:82-84

**Constat.** set_margin_mode et set_leverage sont enveloppés dans except Exception: pass, et le résultat n'est jamais relu (pas de fetch_leverage ni de lecture de marginType). Binance refuse de changer de mode de marge tant qu'une position ou un ordre est ouvert (-4048), refuse la marge isolée en mode Multi-Assets (-4168), et refuse de réduire le levier en marge isolée avec une position ouverte (-4161). Ces réglages ne sont appliqués qu'à la création du Bot : changer le levier dans Étrave n'a aucun effet tant que le bot n'est pas relancé.

**Scénario.** Passage de x1 (vente isolée ouverte) à x3 : le passage en marge croisée échoue sans message. La position reste isolée avec sa marge d'origine, alors que le stop est calculé pour une marge croisée sur tout le capital (0,5/|cible|) ; il peut se retrouver au-delà du prix de liquidation de la position isolée. Autre cas : si set_leverage(1) échoue et que le symbole reste au levier par défaut de Binance (20), la vente isolée ne reçoit que 5 % du notionnel en marge et est liquidée sur une hausse d'environ 5 % au lieu d'environ 100 %.

**Vérification.** courtier.py:245-252 : deux blocs try/except Exception: pass, sans relecture du résultat. configurer n'est appelé que dans Bot.__init__ (bot.py:84). Les codes Binance cités (-4048 changement de marge avec position ouverte, -4168 mode Multi-Assets, -4161 baisse du levier en marge isolée) viennent de ma mémoire de la documentation : certitude moyenne. Le cas « levier 20 par défaut » suppose que set_leverage échoue, ce qui est rare : il faudrait un incident réseau ou de droits. Mais rien ne le détecterait, et en marge isolée la vente serait alors liquidée vers +5 %. Changer le levier dans Étrave réécrit config.json (etrave/bitcoin.py:178-183) mais n'a aucun effet tant que le bot n'est pas relancé.

### BTC-EX-09 · majeur · confirme : Le coupe-circuit à -40 % ne borne rien : il n'est vérifié que toutes les 4 h, et le stop coûte à lui seul 50 % du capital

`bitcoin/bot.py` : 147-154 ; courtier.py:114-119

**Constat.** Le stop est posé à une distance s = 0,5/|cible| du prix. La perte quand il est touché vaut |cible| x s = 50 % du capital à tout levier, plus le glissement (0,5 % x levier dans le compte papier) et le financement. Le coupe-circuit, lui, ne compare le capital au plus haut qu'à chaque clôture 4h (après le téléchargement des données). Rien ne surveille le compte entre deux cycles.

**Scénario.** x10, cible 10 : le stop est à -5 %. Une baisse de 5 % en quelques minutes coûte -50 % et plus (glissement x10, prix de marque), soit bien au-delà des -40 % annoncés. Si le stop ne fonctionne pas (BTC-EX-02), la liquidation arrive vers -9,6 % de prix, soit environ -100 % du capital, avant même le cycle suivant.

**Vérification.** courtier.py:118 : s = 0,5/|cible|. La perte au stop vaut |cible| x s x capital, soit 50 % à tout levier, plus GLISSEMENT_STOP x levier dans le compte papier (ligne 162). Le coupe-circuit (bot.py:152) n'est évalué qu'une fois par cycle de 4 h, après le téléchargement des données. LISEZMOI.md:31 promet une fermeture à -40 %. Avec un levier, cette limite n'existe donc pas : le stop lui-même coûte au moins 50 %.

### BTC-EX-10 · majeur · confirme : « Tout fermer » et le coupe-circuit dépendent de Coin Metrics et du miroir de données de Binance

`bitcoin/bot.py` : 127-134, 155-157 ; donnees_live.py:27-37, 60-65

**Constat.** cycle() télécharge les données et appelle decider() AVANT de lire le compte, de tester le coupe-circuit et de traiter FERMER. Une panne de Coin Metrics ou de data-api.binance.vision (ConnectionError, KeyError sur j['data'], limite de requêtes) fait échouer tout le cycle. Une donnée en retard ou plus de 2 votes absents (DonneesInvalides) fait sortir du cycle ligne 134. Dans les deux cas, aucune action n'est faite sur le compte, et un vote on-chain manquant ne devient pas un vote « absent » : l'erreur interrompt tout.

**Scénario.** L'API communautaire de Coin Metrics tombe ou change de format pendant une forte baisse. L'utilisateur crée FERMER depuis Étrave : rien n'est fermé tant que les données ne reviennent pas. Le coupe-circuit à -40 % n'est pas évalué non plus, et la position reste ouverte sans gestion.

**Vérification.** bot.py:127-134 : source.charger() et decider() passent avant courtier.etat(), avant le coupe-circuit (ligne 152) et avant FERMER (ligne 155). donnees_live._get lève ConnectionError après 4 essais (ligne 37). onchain() fait j['data'] sans aucune protection (ligne 63). Un DonneesInvalides fait sortir du cycle à la ligne 134, et boucle() ne réessaie alors qu'à la clôture 4h suivante. LISEZMOI.md:141 promet « tout est fermé au prochain cycle ». Une panne de Coin Metrics suffit donc à bloquer FERMER et le coupe-circuit.

### BTC-EX-11 · majeur · confirme : « Arrêter » dans Étrave est sans effet quand le bot tourne via lancer_bot.bat ou systemd

`bitcoin/lancer_bot.bat` : 4-8 ; bitcoin/bot-btc.service:12-13 ; etrave/bitcoin.py:294-303

**Constat.** Le .bat relance python en boucle 60 s après chaque arrêt, et le service systemd a Restart=always (RestartSec=60). Étrave ne tue que le PID de python (taskkill /T sur ce PID, ou SIGTERM). LISEZMOI recommande le .bat (Planificateur de tâches) ou le service pour un fonctionnement en continu.

**Scénario.** L'utilisateur clique sur Arrêter pour suspendre le bot pendant une anomalie et croit qu'il ne passe plus d'ordres. Une minute plus tard, le bot est relancé et fait aussitôt un cycle complet, avec ordres.

**Vérification.** lancer_bot.bat:4-8 relance le bot en boucle avec un délai de 60 s. Pour bot-btc.service, les lignes réelles sont 14-15 (Restart=always, RestartSec=60), pas 12-13. etrave/bitcoin.py:294-303 ne tue que le PID lu dans vivant.json. Restart=always relance même après un SIGTERM qui ne vient pas de systemctl stop. Le .bat continue vers « goto boucle ». LISEZMOI.md:149-151 recommande ces deux modes de lancement.

### BTC-EX-12 · majeur · confirme : « restricted location » (451) au démarrage : le bot plante et redémarre en boucle, sans aucune alerte Telegram

`bitcoin/courtier.py` : 230-241 ; bot.py:71-78, 241

**Constat.** ccxt traduit le code HTTP 451 en ExchangeNotAvailable. CourtierBinance.__init__ appelle load_markets() dès la construction du Bot. Le spot, avec clés, appelle aussi sapi capital/config/getall et margin/allPairs. L'exception sort de main() avant boucle(), donc avant le message « ▶️ démarré » et sans aucun notif.envoyer(). Le .bat et systemd relancent le bot toutes les 60 s sans rien signaler. Vérifié depuis cette machine : api.binance.com, fapi.binance.com, testnet.binance.vision et demo-fapi répondent 451 « Service unavailable from a restricted location », alors que data-api.binance.vision et testnet.binancefuture.com répondent 200. Les commandes --etat en mode papier fonctionnent donc et masquent le problème. Pendant un cycle, une erreur 451 dans la boucle d'ordres limites est en plus prise pour « le prix a bougé » (8 essais silencieux).

**Scénario.** Le VPS change d'adresse IP ou de pays, ou Binance restreint le pays, alors qu'une vente ou une position à levier est ouverte. Le bot plante en boucle sans aucun message et la position n'est plus gérée (stop éventuellement périmé, coupe-circuit inactif). Étrave affiche « arrêté », sans dire pourquoi.

**Vérification.** ccxt traduit '451' en ExchangeNotAvailable (base/exchange.py:262). Depuis cette machine, curl renvoie 451 pour api.binance.com et fapi.binance.com, et 200 pour data-api.binance.vision. CourtierBinance.__init__ appelle load_markets (courtier.py:240) depuis Bot() (bot.py:78, 241), avant boucle() et donc avant tout notif.envoyer : aucune alerte au démarrage, et le .bat ou systemd relance en boucle sans rien dire. Un détail est faux : pendant un cycle, une erreur 451 n'est pas avalée 8 fois. courtier.etat() (bot.py:147) et fetch_order_book (courtier.py:281) sont hors du try et lèvent l'exception. boucle() envoie alors « ❌ erreur de cycle » toutes les 5 minutes. Le silence ne concerne donc que le démarrage ou le redémarrage, par exemple après le redémarrage d'un VPS.

### BTC-EX-13 · majeur · confirme : Compte papier : le financement n'est jamais prélevé avec des cycles de 4 h

`bitcoin/courtier.py` : 146-153

**Constat.** fixer_prix compte n = floor((maintenant - dernier_financement) / 8h), puis remet dernier_financement à maintenant à chaque appel. Comme le bot l'appelle toutes les 4 h, n vaut toujours 0. Vérifié : avec 0,4 BTC acheté en perpétuel à 50 000 $ sur 30 jours de cycles de 4 h, j'obtiens 0,00 $ de financement prélevé, contre environ 180 $ attendus à 0,01 % par 8 h. test_rejeu_execution_2018_2026 (test_bot.py:173-177) appelle fixer_prix toutes les 4 h et ne compte donc aucun financement non plus.

**Scénario.** Démo en mode papier à x3 en achat : le résultat est surestimé d'environ 0,01 % x 3 par jour x 365 x 3 ≈ 33 % par an de financement non payé (≈ 11 % par an par unité d'exposition achetée au taux de base, davantage en marché haussier où le financement monte). L'utilisateur jugerait le levier sur une démo trop flatteuse. À x1, l'effet est faible : seule la vente est en perpétuel, et le financement qu'elle reçoit est oublié.

**Vérification.** courtier.py:146-153 : n = int(Δ/8h) puis dernier_financement = maintenant à chaque appel. Je l'ai reproduit : 0,6 BTC acheté en perpétuel à 50 000 $, 180 appels toutes les 4 h, donne 0,00 $ de financement. Avec des appels toutes les 8 h sur 30 jours, on obtient bien -270 $. bot.py:137 appelle fixer_prix à chaque cycle de 4 h. test_bot.py:174 fait de même, et le calcul de comparaison (lignes 184-185) n'inclut pas non plus le financement. L'estimation d'environ 33 %/an à x3 au taux de base est arithmétiquement juste (3 x 0,03 %/jour x 365).

### BTC-EX-14 · majeur · confirme : Mode de position Hedge non vérifié

`bitcoin/courtier.py` : 243-252, 316-321

**Constat.** Le bot n'appelle ni set_position_mode(False) ni fetch_position_mode. Si le compte futures est en mode Hedge (dualSidePosition), Binance refuse tout ordre sans positionSide (-4061), et reduceOnly n'y est pas accepté.

**Scénario.** Compte réglé en Hedge (souvent le cas après du trading manuel) : le BTC est vendu au comptant, puis l'ordre perpétuel est refusé. Le compte reste à plat au lieu d'être vendeur, avec une erreur toutes les 5 minutes.

**Vérification.** Aucun appel à set_position_mode ni fetch_position_mode dans courtier.py. En mode Hedge, un ordre sans positionSide est refusé (-4061, de mémoire, certitude moyenne à haute), et reduceOnly n'y est pas admis. Les ordres partent sans positionSide (lignes 320-321 et 350-351). « Souvent le cas » est une supposition du lecteur : le mode One-way est le défaut des comptes Binance. Mais rien ne vérifie le mode, et en x1 l'échec arrive après la vente au comptant.

### BTC-EX-15 · mineur · confirme : Reste trop petit après une exécution partielle : le cycle échoue au milieu du plan

`bitcoin/courtier.py` : 275, 299-307, 314-315

**Constat.** amount_to_precision lève InvalidOrder quand la quantité est inférieure au pas (vérifié : 4e-8 BTC lève l'erreur sur le spot et sur le perpétuel). vendre_spot utilise min(quantité, BTC libre) : si le BTC est bloqué dans un ordre orphelin, le libre vaut environ 0 et l'appel lève une exception. Le reste envoyé au marché après une exécution partielle en limite peut être sous le notionnel minimal (100 USDT en perpétuel hors reduceOnly d'après le code, 5 USDT au comptant). Binance le refuse et on obtient RuntimeError('… exécuté en limite, le reste au marché a échoué').

**Scénario.** Ouverture perpétuelle de 0,03 BTC : 0,029 BTC s'exécute en limite, le reste de 0,001 BTC (≈ 65 $) part au marché et est refusé. Le cycle échoue avant la pose du stop ; il se rattrape 5 minutes plus tard, avec une fenêtre sans stop et une alerte d'erreur.

**Vérification.** Dans ccxt 4.5.93, amount_to_precision lève InvalidOrder quand le résultat tronqué vaut '0' (base/exchange.py:6771-6775). vendre_spot fait min(quantité, libre) (courtier.py:314-315). Si le BTC est bloqué par un ordre orphelin, libre vaut environ 0 et l'appel lève une exception à la ligne 275. Le reste envoyé au marché sous 100 USDT de notionnel en perpétuel lève un RuntimeError (lignes 304-307). Au cycle suivant, 5 minutes plus tard, l'écart reste sous MIN_PERP_USDT (ligne 106) : il n'y a plus d'action et le stop est posé. L'erreur se corrige donc seule, mais laisse une fenêtre sans stop.

### BTC-EX-16 · mineur · confirme : Capital mal mesuré : portefeuille Funding, BNB et Earn ignorés ; un retrait déclenche le coupe-circuit

`bitcoin/courtier.py` : 260-269 ; bot.py:149-154

**Constat.** Le capital = USDT et BTC du portefeuille spot + totalMarginBalance des futures. Un dépôt crédité sur le portefeuille Funding, le BNB (frais payés en BNB) et Simple Earn ne sont pas comptés. Le plus haut (pic) n'est jamais corrigé des dépôts ni des retraits.

**Scénario.** L'utilisateur retire 45 % de son compte : au cycle suivant, le capital passe sous 60 % du plus haut et le coupe-circuit ferme tout puis s'arrête. À l'inverse, un dépôt gonfle le plus haut pour toujours. Si l'option « payer les frais en BNB » est active, la consommation de BNB n'apparaît pas dans le capital : elle échappe au journal, qui sous-estime donc les coûts.

**Vérification.** courtier.py:261-269 : le capital ne compte que l'USDT et le BTC du portefeuille spot et totalMarginBalance des futures. Le pic (bot.py:149) n'est jamais corrigé des dépôts ni des retraits : un retrait de plus de 40 % déclenche le coupe-circuit. En revanche, le point « un dépôt gonfle le plus haut pour toujours » n'est pas un bug en soi : le capital et le pic augmentent ensemble.

### BTC-EX-17 · mineur · confirme : Prix du stop négatif quand la cible est faible

`bitcoin/courtier.py` : 114-119

**Constat.** s = 0,5/|cible| ; pour un achat, le stop vaut prix x (1 - s), ce qui est négatif dès que |cible| < 0,5. Binance refuse un tel prix, et l'exception à bot.py:169 fait échouer le cycle à chaque tentative.

**Scénario.** x2 avec une dose < 0,25 (volatilité > 160 % en prudent) : cas rare, mais le cycle tourne alors en boucle d'erreurs toutes les 5 minutes.

**Vérification.** Vérifié : prix_stop(0.4, 50000, 'perpetuel') = -12500,0. Pour un achat en x2, il faut une dose = vol_cible/vol < 0,25 (btc.py:109), soit une volatilité > 160 % en prudent et > 240 % en équilibré. C'est rare. Pour une vente, le stop est au-dessus du prix et toujours positif.

### BTC-EX-18 · mineur · confirme : Compte papier en ordres limites : remplissage supposé total au prix moyen, sans glissement

`bitcoin/courtier.py` : 19-20, 193-208

**Constat.** En mode papier avec ordres='limite' (la valeur par défaut), le glissement vaut 0 et le perpétuel paie les frais de teneur de marché (0,02 %) sur toute la quantité. En réel, le reste part au marché après environ 2 minutes, et le prix peut avoir bougé pendant l'attente.

**Scénario.** Lors des retournements rapides (ceux qui comptent le plus), la démo papier sous-estime les coûts d'exécution par rapport au réel.

**Vérification.** courtier.py:19-20 : GLISSEMENT['limite'] = 0 et frais perpétuels de teneur de marché à 0,02 % sur toute la quantité. L'ordre par défaut est 'limite' (bot.py:31). executer (lignes 193-208) remplit tout au prix de la clôture. Le réel fait 2 minutes de limites, puis le marché pour le reste.

### BTC-EX-19 · mineur · plausible : L'horloge locale décide de la bougie traitée : un cycle peut être sauté ou une bougie incomplète prise pour clôturée

`bitcoin/bot.py` : 135-136, 202-204, 218 ; btc.py:52-56

**Constat.** tronquer garde les bougies telles que index + 4h <= maintenant, avec maintenant = horloge locale. Si data-api publie la bougie avec plus de 90 s de retard, la dernière bougie est déjà traitée : le cycle renvoie « déjà traité », et le prochain réveil est 4 h plus tard. Si l'horloge locale avance de plus de 90 s, une bougie encore ouverte chez Binance est traitée comme clôturée. ccxt est utilisé sans adjustForTimeDifference (recvWindow de 10 s) : une dérive de l'horloge provoque -1021 sur tous les appels privés.

**Scénario.** Un PC Windows mal synchronisé décide sur une bougie 4h incomplète, ou perd une décision toutes les 4 h.

**Vérification.** Le cas « horloge locale en avance » est confirmé par le code. btc.tronquer (btc.py:52-56) filtre avec maintenant = horloge locale (bot.py:121). Si l'horloge avance de plus de 90 s, la bougie en cours, que data-api renvoie toujours, est prise pour clôturée. Le cas « bougie publiée en retard » est mal décrit. Si la dernière bougie reçue est celle d'avant, fin4 = T - 4 h, et maintenant - fin4 = 4 h + 90 s > 4 h : on obtient DonneesInvalides (strategie.py:32-34), pas « déjà traité ». L'effet est le même : le cycle est perdu jusqu'à la clôture suivante, plus une alerte. Les réglages ccxt (adjustForTimeDifference désactivé, recvWindow de 10 s) viennent de ma mémoire de ccxt : certitude moyenne.

### BTC-EX-20 · mineur · confirme : Le mode --etat (« AUCUN ordre ») modifie quand même le compte futures

`bitcoin/bot.py` : 84, 241-247

**Constat.** Bot.__init__ appelle toujours courtier.configurer(), qui fait set_margin_mode et set_leverage, y compris avec --etat.

**Scénario.** Un simple --etat lancé avec levier=3 dans la configuration passe le symbole en marge croisée x3 sur le compte réel, même si un autre usage du compte en dépendait.

**Vérification.** bot.py:241 construit Bot(cfg) avant le test de x.etat (ligne 244), et Bot.__init__ appelle courtier.configurer (ligne 84), donc set_margin_mode et set_leverage, sur le compte réel.

### BTC-EX-21 · mineur · confirme : Petits comptes : la vente n'est jamais ouverte

`bitcoin/courtier.py` : 21, 106

**Constat.** Une ouverture en perpétuel exige au moins 100 USDT de notionnel (MIN_PERP_USDT). La vente vaut 0,25 x dose x capital : sous environ 400 USDT / dose de capital, elle n'est jamais ouverte, alors que l'achat au comptant est sorti.

**Scénario.** Avec un capital de 300 $, chaque signal de VENTE laisse le compte à plat : l'écart avec le backtest n'est signalé nulle part.

**Vérification.** courtier.py:21 fixe MIN_PERP_USDT = 100, et la ligne 106 exige (|perp_vise| - |deja|) x px ≥ 100. Une vente de 0,25 x dose x C ne s'ouvre donc pas si C < 400/dose. Le minimum de 100 USDT de Binance pour BTCUSDT perpétuel est réel (de mémoire). Rien ne signale l'écart, à part la note du plan.

### BTC-EX-22 · mineur · plausible : Coin Metrics en direct renvoie des valeurs provisoires (« flash ») : le vote on-chain du bot diffère de celui du backtest

`bitcoin/donnees_live.py` : 60-65

**Constat.** L'API communautaire renvoie FlowInExNtv et FlowOutExNtv avec le statut « flash » (constaté le 17/11/2026 pour les 10-11/11), valeurs révisées ensuite. Le backtest utilise le fichier historique déjà révisé : il voit des valeurs que le bot n'avait pas en direct.

**Scénario.** Sur les jours où la moyenne sur 30 jours du flux net est proche de 0, le vote on-chain peut changer de signe entre le direct et le backtest. Effet probablement faible, non mesuré.

**Vérification.** J'ai interrogé l'API communautaire de Coin Metrics : FlowInExNtv et FlowOutExNtv du 08 au 13/11/2026 ont le statut « flash ». L'ampleur des révisions ultérieures n'est pas mesurée. Le bot retarde déjà les données on-chain de 2 jours (btc.tronquer, +2D) et lisse sur 30 jours. L'effet est probablement faible.

### BTC-EX-23 · mineur · confirme : Les tests ne vérifient aucun appel ccxt réel

`bitcoin/test_bot.py` : 277-319

**Constat.** FauxExchange ne couvre que _ordre (limite puis marché). Rien ne teste transfer, set_margin_mode, set_leverage, la lecture des soldes par etat(), le stop STOP_MARKET avec closePosition ni annuler_stop. Les 25 tests passent, alors que BTC-EX-01, 02, 06 et 14 cassent en réel.

**Scénario.** « pytest vert » donne une fausse assurance sur l'exécution chez Binance.

**Vérification.** test_bot.py:277-319 : FauxExchange n'imite que amount_to_precision, fetch_order_book, create_order, fetch_order et cancel_order pour _ordre. Une recherche de transfer, annuler_stop, set_margin et set_leverage dans les tests ne donne rien. poser_stop n'est testé que sur CourtierPapier (ligne 236).

### BTC-EX-25 · mineur · confirme : Alertes Telegram toutes les 5 minutes pendant une panne persistante

`bitcoin/bot.py` : 219-224

**Constat.** Chaque échec du cycle envoie « ❌ … Nouvel essai dans 5 minutes », sans regrouper ni espacer les messages. Les erreurs persistantes (BTC-EX-01, 02, 06) produisent environ 288 messages par jour.

**Scénario.** L'utilisateur coupe les notifications du bot, et une alerte importante (coupe-circuit, stop) passe ensuite inaperçue.

**Vérification.** bot.py:219-224 envoie un message à chaque échec et réessaie 5 minutes plus tard, sans espacer les messages ni les regrouper. Avec EX-02 (refus du stop à chaque cycle en x2+) ou EX-06 (testnet), cela fait environ 288 messages par jour.

### BTC-EX-24 · sans-objet · refute : Après un stop touché, la position est rouverte au cycle suivant

`bitcoin/bot.py` : 159-170

**Constat.** Aucun état ne retient qu'un stop a été touché. Si le signal ne change pas, le plan rouvre la position entière au levier visé à la clôture 4h suivante, et le nouveau stop est de nouveau à -50 % du capital.

**Scénario.** Deux stops en 8 h à x5 font perdre environ 75 % du capital, avant même que le coupe-circuit soit évalué.

**Vérification.** Le stop est placé pour qu'un déclenchement coûte environ 50 % du capital (|cible| x 0,5/|cible|, courtier.py:118), plus le glissement. Après un stop, le capital vaut au plus environ 0,5 x pic, donc moins que 0,6 x pic. Au cycle suivant, bot.py:152-154 déclenche le coupe-circuit avec cible = 0 et pose 'arrete' : la position n'est pas rouverte. Le scénario « deux stops en 8 h » ne peut se produire que si l'exposition réelle est très inférieure à la cible, par exemple après une exécution partielle. Le vrai problème est déjà couvert par EX-09 : le stop coûte plus que le coupe-circuit annoncé.

### Oublis relevés par le vérificateur

- **majeur** · La clé API décrite dans LISEZMOI n'a pas la permission « Universal Transfer » nécessaire aux transferts spot ↔ futures (`bitcoin/LISEZMOI.md` : 115-118 ; courtier.py:224-225, 325, 329) : ccxt.transfer appelle POST /sapi/v1/asset/transfer. D'après la documentation de Binance (de mémoire, certitude moyenne à haute), cet appel exige l'option « Permits Universal Transfer » sur la clé. LISEZMOI ne demande que « lecture, trading spot et trading futures ». Même avec un ccxt ancien où 'future' est encore correct, la vente en x1 et tout le montage à levier échoueraient donc au transfert, après la vente du BTC au comptant.
- **majeur** · LISEZMOI promet « pas d'ordre à moitié », mais le plan s'exécute ordre par ordre, sans retour en arrière (`bitcoin/bot.py` : 162-167 ; LISEZMOI.md:192-193) : Les actions du plan (vendre_spot, puis vers_futures, puis perp) partent une à une. Un échec au milieu laisse les ordres précédents exécutés : par exemple le BTC vendu sans vente perpétuelle ouverte, soit un compte à plat au lieu d'une vente. C'est le cas exact de EX-01, EX-06, EX-07 et EX-14. La phrase de LISEZMOI selon laquelle le bot « ne passe pas d'ordre à moitié » est fausse.
- **majeur** · L'état du mode papier (pic, dernière bougie) est repris tel quel lors du passage en réel : coupe-circuit au premier cycle réel (`bitcoin/bot.py` : 69, 124, 149-154 ; etrave/bitcoin.py:139-185) : Le papier et le réel partagent le même dossier et le même etat.json, et changer de mode dans Étrave (regler) ne réinitialise rien. Exemple : pic papier à 12 000 $ (capital_papier 10 000 plus les gains), compte réel de 5 000 $. Au premier cycle réel, 5 000 < 0,6 x 12 000 : le coupe-circuit se déclenche, la cible passe à 0 et le bot se met à l'arrêt. Il vend au passage tout BTC présent sur le compte spot. derniere_bougie, repris du papier, peut aussi faire renvoyer « déjà traité » au premier cycle.
- **mineur** · Le bot considère tout l'USDT et tout le BTC du compte spot comme son capital (`bitcoin/courtier.py` : 260-269, 84-86) : Rien n'impose un sous-compte dédié. Un BTC que l'utilisateur détient à côté sur le même compte est compté dans le capital, et il est vendu dès que la cible n'est plus à l'achat (vendre_spot vend e.btc_spot en entier). Combiné à l'oubli précédent ou à FERMER, le bot peut liquider des avoirs que l'utilisateur ne lui destinait pas.
- **majeur** · Les erreurs de fetch_order et fetch_order_book, hors du try dans _ordre, laissent un ordre vivant et non suivi (`bitcoin/courtier.py` : 281, 290, 296) : Si fetch_order (ligne 290) lève une exception (réseau, 451, limite de requêtes) juste après un create_order réussi, l'exception sort de _ordre. L'ordre limite reste dans le carnet sans être annulé, et le cycle suivant le replace à partir des soldes. Cela complète EX-03, qui ne traite que les exceptions de create_order et de cancel_order.
- **mineur** · Des données en retard bloquent toute décision pendant 4 h (`bitcoin/bot.py` : 130-134, 216-218) : Quand decider lève DonneesInvalides, cycle() se termine normalement et boucle() programme le réveil suivant à la clôture 4h d'après, au lieu de réessayer quelques minutes plus tard. Un retard de quelques minutes du miroir data-api fait donc perdre toute la décision 4h, avec le traitement de FERMER et du coupe-circuit.

### Non vérifié par le lecteur

- Aucun appel réel ni testnet chez Binance : depuis cette machine, api.binance.com, fapi.binance.com, testnet.binance.vision et demo-fapi.binance.com répondent 451 « restricted location ». Seuls data-api.binance.vision et testnet.binancefuture.com (public) répondent.
- Les requêtes ccxt ont été vérifiées hors ligne avec ccxt 4.5.93 (installé dans le dossier de travail temporaire) : endpoints de Binance interceptés, informations des marchés réelles chargées depuis exchangeInfo (spot via data-api, futures via le testnet public). Pour les versions plus anciennes de ccxt (4.4.50, 4.5.0 à 4.5.90), j'ai seulement cherché des chaînes dans les wheels téléchargées ; je n'ai rien exécuté avec ces versions.
- Les refus côté Binance (-4130 pour un second closePosition dans le même sens, -4120 pour STOP_MARKET envoyé hors API algo, -2019 pour une marge à 100 %, -4061 en mode Hedge, et le rejet du transfert MAIN_ISOLATED_MARGIN avec toSymbol=FUTURE) viennent de la table d'erreurs de ccxt et de la documentation de Binance. Ils n'ont pas été observés en direct.
- Les filtres du perpétuel BTCUSDT en production (pas de quantité 0,001, notionnel minimal 100) n'ont pas pu être lus (451) : le testnet donne un pas de 0,0001 et un minimum de 50.
- Comportement d'un ancien stop SELL closePosition qui resterait en place quand la position est passée vendeuse : non vérifié.
- Je n'ai lu que la partie lancement, arrêt et réglages de etrave/bitcoin.py (pour BTC-EX-05, 08 et 11). Le reste d'Étrave n'a pas été examiné ; page.html, risque.py, reference.json et profils.json n'ont pas été ouverts.
- La gestion des frais en BNB n'a pas pu être testée : aucun compte n'était disponible.
- L'effet chiffré du statut « flash » de Coin Metrics sur les votes n'a pas été mesuré.

## Interface Étrave

### ET-01 · critique · confirme : Deuxième bot BTC lancé pendant un cycle long : ordres en double

`etrave/bitcoin.py` : 35, 260-269, 274-292 (avec bitcoin/bot.py:110-117, 210-226 et bitcoin/courtier.py:228, 272-299)

**Constat.** Étrave juge le bot « en marche » seulement si vivant.json date de moins de BATTEMENT_S = 60 s (bitcoin.py:35, 268). Le bot réécrit ce fichier une fois au début du cycle (bot.py:214, statut « cycle en cours »), puis seulement après la fin du cycle (bot.py:225). Or un cycle dure souvent plus de 60 s : téléchargement des données, puis chaque ordre limite attend 15 s et peut être replacé 8 fois (courtier.py:228, 289), soit environ 2 min par action, et un rééquilibrage en compte plusieurs. Pendant ce temps, processus() renvoie en_marche=False (il ignore statut='cycle en cours') et demarrer() (bitcoin.py:275) accepte de lancer un second processus. Aucun verrou ne l'en empêche : bot.pid est écrit (bot.py:252) mais jamais contrôlé. Le second bot fait tout de suite un cycle (bot.py:209). Il relit un etat.json où derniere_bougie n'est pas encore à jour, puisque le premier bot ne sauve qu'en fin de cycle (bot.py:198). Il calcule donc son plan sur des soldes que le premier bot est en train de modifier. Reproduit : avec un vivant.json vieux de 75 s et statut 'cycle en cours', demarrer() renvoie {'ok': True} et lance une seconde commande.

**Scénario.** Mode réel, levier ×2 (perpétuel) : à 04:01:30 UTC le bot passe d'une vente à un achat (fermer, puis ouvrir). L'ordre limite ne passe pas tout de suite. À 04:02:40, la page montre le bot « arrêté » et l'utilisateur clique sur Démarrer. Le second bot lit les mêmes soldes à moitié modifiés et repasse les mêmes ordres. Ensuite, deux boucles tournent pour toujours sur le même compte et se disputent les ordres limites et le stop de protection (annuler_stop puis poser_stop). L'exposition peut être doublée le temps d'un cycle.

**Vérification.** Relu : bitcoin.py:35 (BATTEMENT_S=60) et 268 (en_marche = age < 60, statut ignoré). bot.py:214 écrit le battement « cycle en cours » une seule fois, et le suivant n'arrive qu'en 225, après bot.cycle(). En mode « limite », chaque action peut durer jusqu'à 8 × (15 s + appels) (courtier.py:228, 278-299). demarrer() (274-276) ne contrôle que en_marche, et bot.pid (bot.py:252) n'est jamais lu comme verrou. Reproduit dans le scratchpad : avec un vivant.json vieux de 75 s et le statut 'cycle en cours', processus() renvoie en_marche=False et demarrer() renvoie {'ok': True} puis lance la commande. La sévérité critique tient, parce que l'effet dure : une fois lancées, les deux boucles se réveillent à la même heure (floor 4h + 90 s) et lisent les mêmes soldes à chaque rééquilibrage. Sans verrou, l'exposition peut donc être doublée à chaque changement de cible, pas une seule fois. La page n'en montre rien, puisque les deux processus écrivent le même vivant.json. Le déclenchement demande un clic sur Démarrer pendant une fenêtre de 1 à 3 min, mais la page affiche justement « arrêté » pendant cette fenêtre.

### ET-03 · majeur · confirme : Une lecture ratée de reglages.txt efface toutes les autres clés à l'écriture suivante (interrupteur Nasdaq réactivé)

`etrave/pont.py` : 68-74, 109-123

**Constat.** lire_cles() renvoie {} pour toute OSError (« l'EA est en train d'écrire »). _modifier() part de ce dictionnaire vide et réécrit un fichier qui ne contient que la clé modifiée et version=1. Disparaissent alors : nasdaq=0, levier, telegram_jeton, telegram_discussion, cloturer et risque_pct. Côté EA, une clé absente veut dire la valeur par défaut (ORB-v6.mq5:1248, 1254) : active=true et risk=InpRiskPct.

**Scénario.** Le Nasdaq a été décoché dans la page pour ne plus trader. Un antivirus ou un outil de sauvegarde tient le fichier ouvert en exclusivité un instant, ou la course de ET-02 se produit, au moment où l'utilisateur change le levier. Le fichier réécrit n'a plus nasdaq=0 : l'EA reprend les trades dès 9:35, au risque saisi dans MetaTrader, et les alertes Telegram de l'interface s'arrêtent.

**Vérification.** Relu : pont.py:68-74 renvoie {} pour toute OSError, et _modifier (111-123) repart de ce {} puis réécrit le fichier. Reproduit en forçant lire_cles à renvoyer {} : après regler(levier=20), le fichier ne contient plus que 'levier=20' et 'version=1', et nasdaq=0, risque_pct et telegram_jeton ont disparu. Côté EA (ORB-v6.mq5:1248-1254, 1290-1291), une clé absente veut dire active=true et risk=InpRiskPct. Le comportement est asymétrique : l'EA garde l'état précédent quand sa lecture échoue (1259-1262), Étrave efface tout. Le déclencheur est rare : sous Windows, open() de Python partage lecture et écriture, et l'EA ouvre avec FILE_SHARE_READ|FILE_SHARE_WRITE. Il faut donc un tiers qui ouvre le fichier en exclusif (antivirus, sauvegarde). Je garde « majeur » parce que la conséquence est silencieuse et touche l'interrupteur de trading et le risque.

### ET-04 · majeur · confirme : Un seul reglages.txt pour tous les MetaTrader de la machine : la démo et le réel partagent risque, interrupteur et clôture

`etrave/pont.py` : 57-64, 230-238 ; nasdaq/ORB-v6.mq5:100, 1255, 1303-1316, 1396-1451, 1460

**Constat.** Tous les terminaux MT5 d'un même utilisateur Windows partagent le dossier Common\Files. Le fichier de réglages est unique, et les fichiers d'état et de trades ne portent que le nom du symbole (etat-NAS100.txt, trades-NAS100.csv), ni le login ni le serveur. La demande de clôture vise elle aussi seulement '<numéro>;<symbole>'.

**Scénario.** Le README conseille la démo avant le réel. Un utilisateur fait donc tourner une démo et un compte réel (ou deux comptes de prop firm) sur le même PC. Un risque de 5 % réglé « pour essayer » sur la démo s'applique aussi au compte réel. « Clôturer » ferme les deux trades, et décocher le Nasdaq coupe les deux. Les deux EA écrivent tour à tour etat-NAS100.txt : la page affiche alternativement le solde et la position de l'un puis de l'autre. Le journal des trades mélange les deux comptes, ce qui fausse les statistiques affichées.

**Vérification.** Relu : pont.py:57-64 (un seul dossier Common\Files\Etrave). L'EA écrit etat-<gSymFile>.txt (ORB-v6.mq5:1396, 1451) et trades-<gSymFile>.csv (1460), dont les noms ne portent ni le login ni le serveur. Ces deux champs sont bien écrits à l'intérieur du fichier d'état (1411-1412), mais le nom de fichier est le même pour deux comptes : les deux EA s'écrasent tour à tour. La clôture vise '<numéro>;<symbole>' (pont.py:237), et chaque EA la compare avec son propre gCloseSeen (1310), donc les deux ferment. risque_pct et la clé nasdaq sont lus par tous les EA. Le dossier commun est bien partagé par tous les terminaux d'un même utilisateur Windows. Le README (ligne 17) conseille la démo avant le réel, ce qui rend plausible d'avoir les deux sur le même PC.

### ET-06 · majeur · confirme : Changer les réglages du bot BTC pendant qu'il tourne n'a aucun effet (y compris l'effacement de la clé)

`etrave/bitcoin.py` : 139-186, 207-215 ; bitcoin/bot.py:36-48, 229-241

**Constat.** bot.py lit config.json une seule fois, au démarrage (charger_config). Pourtant regler() réécrit config.json et répond {ok, changees, reglages} avec les nouvelles valeurs, et effacer_cles() remet mode='papier' dans config.json, sans arrêter ni relancer le bot et sans signaler que rien n'est appliqué. reglages_publics() renvoie la configuration écrite, pas celle du processus (seuls mode et levier figurent aussi dans vivant.json). Je n'ai pas pu vérifier ce que la page en affiche (page.html non ouverte).

**Scénario.** Le bot tourne en réel au levier ×5. L'utilisateur, inquiet, met le levier à 1, le coupe-circuit à 20 %, ou efface la clé : la page affiche « ×1, papier », mais le bot continue au levier ×5 avec la clé gardée en mémoire et l'ancien coupe-circuit à 40 %, jusqu'au prochain arrêt manuel. Avec bot-btc.service (Restart=always), le cas inverse existe : un passage de testnet à réel enregistré sans redémarrage prend effet en silence au prochain plantage.

**Vérification.** Relu : bot.py:36-48 et 235-241 lisent config.json une seule fois. Bot.__init__ (71-84) crée CourtierBinance avec la clé gardée en mémoire et fixe self.levier. Côté Étrave, regler() (bitcoin.py:180-186) et effacer_cles() (207-215) n'écrivent que config.json, sans relancer le bot ni prévenir. reglages_publics() (132-137) renvoie la configuration écrite. Atténuation : processus() renvoie aussi mode et levier tirés de vivant.json (269), et la page peut les afficher, ce que je n'ai pas pu vérifier (page.html non ouverte). L'effacement de la clé ne coupe pas un bot réel en marche : confirmé par le code.

### ET-07 · majeur · confirme : « Arrêter » tue le bot sans prévenir au milieu d'un ordre : ordre limite laissé chez Binance, rééquilibrage à moitié fait

`etrave/bitcoin.py` : 294-304, 316-324

**Constat.** arreter() lance taskkill /T /F sous Windows, ou SIGTERM ailleurs, qui tue Python sans nettoyage. Le bot n'a aucun gestionnaire d'arrêt propre. L'arrêt ne vérifie pas si un cycle est en cours (statut 'cycle en cours' dans vivant.json). Si le processus meurt pendant les 15 s d'attente d'un ordre limite post-only (courtier.py:289), cet ordre reste posé chez Binance et peut s'exécuter plus tard, alors que plus aucun bot ne tourne. S'il meurt entre « réduire » et « ouvrir », le compte reste dans un état intermédiaire. vivant.json est ensuite supprimé, donc la page dit « arrêté » même si taskkill a échoué (résultat ignoré, ligne 319).

**Scénario.** Changement de sens en perpétuel, puis clic sur Arrêter au milieu : la position courte est fermée, l'ordre limite d'achat de 0,15 BTC reste dans le carnet et s'exécute une heure plus tard. Il n'y a pas de stop de protection, puisque poser_stop n'a jamais été appelé, et plus personne ne surveille la position.

**Vérification.** Relu : arreter() (bitcoin.py:294-304) n'examine pas le statut 'cycle en cours'. Sous Windows, taskkill /F tue sans nettoyage, et son code de retour est ignoré (319). Ailleurs, SIGTERM (322) tue aussi sans nettoyage, puisque Python n'installe pas de gestionnaire et que bot.py n'en a pas. Dans _ordre (courtier.py:284-296), l'ordre post-only est posé puis le processus dort 15 s avant fetch/cancel : tué pendant ce sommeil, l'ordre reste dans le carnet. Dans le cas « fermer » puis « ouvrir » en perpétuel, l'ordre d'ouverture n'est pas reduceOnly (courtier.py:317-321) et poser_stop n'est appelé qu'après toutes les actions (bot.py:168-169). La position ouverte plus tard n'aurait donc pas de stop. vivant.json est effacé même si le kill a échoué. Le prochain démarrage repartirait des soldes réels, mais rien ne surveille la position entre-temps.

### ★ ET-10 · majeur · confirme : Mode testnet impossible avec ccxt récent : « Tester la connexion » échoue et le bot aussi

`etrave/bitcoin.py` : 236-257 (et bitcoin/courtier.py:237-239)

**Constat.** En testnet, le code appelle set_sandbox_mode(True) sur binanceusdm, puis fut.fetch_balance(). Dans ccxt 4.5.93 (version actuelle sur PyPI, vérifiée dans la source de binance.py), tout appel privé futures sur testnet.binancefuture.com en mode bac à sable lève NotSupported (« testnet/sandbox mode is not supported for futures anymore… consider using the demo trading »), sauf si l'option disableFuturesSandboxWarning est fixée, ce que le code ne fait pas. L'exception est convertie en « Binance injoignable : … ».

**Scénario.** L'utilisateur suit LISEZMOI (« Première étape : le testnet ») après pip install ccxt. Le test de connexion échoue toujours, et le bot en testnet plante dès sa première lecture des soldes futures. La seule étape de validation prévue avant le réel est donc inutilisable, ce qui pousse à passer directement en réel.

**Vérification.** Vérifié dans la source de ccxt 4.5.93 (wheel PyPI téléchargée dans le scratchpad), ccxt/binance.py:12532-12533, dans sign() pour fapiPrivate/V2/V3 : `if url.find('testnet.binancefuture.com') > -1 and self.isSandboxModeEnabled and not options['disableFuturesSandboxWarning']: raise NotSupported('... testnet/sandbox mode is not supported for futures anymore ...')`. etrave/bitcoin.py:243-245 appelle set_sandbox_mode(True) puis fut.fetch_balance() sans cette option. L'exception tombe dans le except générique et devient « Binance injoignable : … » (255). courtier.py:237-239 fait de même. Le bot échouera donc à son premier appel privé futures (etat() → fut.fetch_balance), et LISEZMOI:88 installe ccxt sans fixer de version. L'étape « testnet » recommandée (LISEZMOI:191) est donc inutilisable telle quelle.

### ET-11 · majeur · plausible : Le bot peut s'arrêter sur PermissionError quand Étrave lit vivant.json au moment où il le remplace (Windows)

`etrave/bitcoin.py` : 57-62, 260-261, 361-370 ; bitcoin/bot.py:110-117, 214, 225

**Constat.** Sous Windows, os.replace échoue (PermissionError) si un autre processus a le fichier cible ouvert sans FILE_SHARE_DELETE, ce qui est le cas de open() en Python. Étrave lit vivant.json, etat.json, journal.csv et bot.log à chaque rafraîchissement de la page. Le bot remplace vivant.json toutes les 15 s, et l'appel bot.battement(reveil) en bot.py:225 se trouve hors du try/except : une seule collision termine le processus, sans alerte Telegram. Lancé par Étrave, il n'est pas relancé. Une collision sur etat.json (sauver, bot.py:93) fait aussi échouer le cycle en cours après ses ordres.

**Scénario.** La page reste ouverte toute la journée. Après quelques jours, une lecture tombe pendant le remplacement : le bot s'arrête en silence. La page l'affiche « arrêté », mais personne ne la regarde (le bot était censé tourner sans intervention), et la position reste sans gestion ni stop replacé. Non reproduit sous Windows.

**Vérification.** Relu : bot.py:110-117 (os.replace de vivant.json), puis 214 et 225, deux appels à battement() hors du try. Toute exception y sort de boucle() puis de main(), et le processus meurt. bot.py:222-223 rappelle aussi sauver() dans le except. Si sauver échoue une seconde fois, l'exception sort de la boucle et le processus meurt aussi. Sous Windows, MoveFileEx avec remplacement échoue (accès refusé) si un autre processus tient la cible ouverte sans FILE_SHARE_DELETE, ce qui est le cas de open() en Python (CRT, partage lecture et écriture seulement) : j'en suis assez sûr. Étrave lit vivant.json et etat.json à chaque GET /api/btc/etat (bitcoin.py:261, 363). Ordre de grandeur : une fenêtre de lecture d'environ 0,1 ms toutes les 2 s, contre 5 760 remplacements par jour, donne de l'ordre d'une collision tous les quelques jours quand la page est ouverte. Je n'ai pas pu le reproduire sous Windows, et j'ignore à quelle fréquence la page interroge l'onglet BTC.

### ET-12 · majeur · confirme : Arrêter depuis Étrave un bot lancé par lancer_bot.bat ou systemd : il redémarre, d'où deux instances

`etrave/bitcoin.py` : 274-304 ; bitcoin/lancer_bot.bat:4-8 ; bitcoin/bot-btc.service:15-16

**Constat.** LISEZMOI propose aussi lancer_bot.bat (boucle qui relance au bout de 60 s) et un service systemd (Restart=always). Étrave tue le PID et efface vivant.json, puis montre le bot comme arrêté. Le superviseur le relance 60 s plus tard. Si l'utilisateur a entre-temps cliqué sur Démarrer, deux bots tournent sur le même compte (voir ET-01).

**Scénario.** Bot démarré à l'ouverture de session par le Planificateur (lancer_bot.bat) ; l'utilisateur clique Arrêter puis Démarrer dans Étrave pour appliquer un nouveau levier ; une minute plus tard deux boucles passent des ordres.

**Vérification.** lancer_bot.bat:4-8 relance python bitcoin\bot.py 60 s après chaque arrêt. bot-btc.service:15-16 relance aussi (Restart=always, RestartSec=60), même après un SIGTERM venu d'ailleurs que systemctl. arreter() (bitcoin.py:294-304) ne tue que le PID de python et efface vivant.json. demarrer() voit alors en_marche=False et lance un second bot, puis le superviseur relance le sien : on retombe sur les deux boucles de ET-01. Même sans clic sur Démarrer, « Arrêter » est sans effet durable sous superviseur, et la page affiche « arrêté » pendant 60 s. Note : lancer_bot.bat suppose les clés dans l'environnement, mais config.json contient fichier_secrets une fois qu'Étrave l'a écrit. Le bot relancé lit donc aussi le fichier.

### ET-02 · mineur · confirme : Écriture de reglages.txt sans verrou : demande de clôture, risque ou case Nasdaq perdus

`etrave/pont.py` : 83-101, 109-124 (serveur multi-thread : etrave/etrave.py:292)

**Constat.** _modifier() lit, modifie puis réécrit le fichier sans aucun verrou, alors que ThreadingHTTPServer (etrave.py:292) traite chaque requête dans son propre thread. De plus, ecrire_cles() utilise toujours le même fichier provisoire 'reglages.txt.tmp' (pont.py:87). Deux POST simultanés (réglages et clôture, double clic, deux onglets) écrivent donc dans le même .tmp, et chacun écrase les changements de l'autre. Le second os.replace lève FileNotFoundError, qui n'est pas rattrapée (seule PermissionError l'est, ligne 98) : la page reçoit une erreur 500. Mesuré sur 300 essais (Linux, regler(risque 0,25) en même temps que demander_cloture) : clôture perdue 128 fois, nouveau risque perdu 163 fois, FileNotFoundError 268 fois. Sous Windows, le détail diffère (os.replace échoue tant qu'une autre poignée est ouverte), mais une mise à jour peut toujours en effacer une autre.

**Scénario.** L'utilisateur baisse le risque de 5 % à 0,5 % et, presque en même temps, clique sur « Clôturer le trade ». L'une des deux demandes disparaît en silence : soit le trade reste ouvert alors que la page a affiché « ok » avec un numéro, soit le trade suivant de 9:35 part à 5 % au lieu de 0,5 %.

**Vérification.** Le mécanisme est exact. Relu : pont.py:109-124 (lecture, modification, écriture sans verrou), 87 (même .tmp pour tous les threads), 98 (seule PermissionError est rattrapée), et etrave.py:292 (ThreadingHTTPServer). Reproduit avec deux threads lancés ensemble (regler 0,25 et demander_cloture) : 195 mises à jour perdues sur 200, et 167 exceptions (FileNotFoundError, d'où une réponse 500). Je baisse la sévérité, car il faut deux POST d'écriture dans la même fenêtre de quelques millisecondes : la lecture, l'écriture et le remplacement prennent environ 1 ms, et jusqu'à environ 1 s sous Windows seulement si l'EA tient le fichier ouvert à ce moment-là (boucle de 20 × 50 ms). Le rafraîchissement de la page ne fait que des GET, qui n'écrivent rien. Deux clics humains sur deux actions différentes, chacune avec son mot de confirmation, ont peu de chances de tomber aussi près. Je n'ai pas pu vérifier si page.html envoie parfois deux POST à la fois.

### ET-05 · mineur · confirme : La case Nasdaq ne commande pas l'EA si le nom du symbole n'est pas reconnu

`nasdaq/ORB-v6.mq5` : 1161-1167, 1295-1296 ; etrave/pont.py:39

**Constat.** L'EA ne lit la clé 'nasdaq' que si InstrumentOf(_Symbol) renvoie "nasdaq". Il faut pour cela que le nom contienne NAS, NDX, NQ, USTEC, US100, USATECH ou TECH100. Sinon gInstr vaut "autre", une clé qu'Étrave n'écrit jamais : l'EA reste actif quelle que soit la case. Étrave ne prévient pas, puisque lire_etats() classe simplement l'EA à la fin de la liste.

**Scénario.** Le Nasdaq s'appelle « USA100.IDX » chez Dukascopy MT5 (USA100 ne contient pas US100) ou « US Tech 100 » chez certains courtiers. L'utilisateur décoche le Nasdaq (l'interrupteur décrit dans le README) et l'EA continue de prendre un trade par jour. Le README dit aussi « Nasdaq uniquement », mais l'EA trade n'importe quel symbole « autre » sans que l'interface puisse l'arrêter.

**Vérification.** Relu : InstrumentOf (ORB-v6.mq5:1161-1167). Seul le cas « nasdaq » lit la clé correspondante (1295), sinon gInstr vaut « autre », clé qu'Étrave n'écrit jamais (pont.py:39). Avec active=true par défaut (1253), l'EA trade alors sans tenir compte de la case. Vérifié : « USA100 » ne contient pas « US100 », et « US TECH 100 » ne contient pas « TECH100 » à cause de l'espace. Je baisse la sévérité, car les noms courants (NAS100, US100, USTEC, NDX100, USTECH100, USATECHIDXUSD) sont bien reconnus, y compris NAS100 chez FundingPips, cité par le README. Je ne suis pas sûr du nom exact du symbole chez Dukascopy MT5. Je n'ai pas pu vérifier si la page signale un EA classé « autre ».

### ET-08 · mineur · plausible : Clé et secret Binance rangés dans le dossier commun de MetaTrader, lisible par tout programme MQL5

`etrave/bitcoin.py` : 34, 116-118, 195-205 ; etrave/etrave.py:62, 330 ; etrave/pont.py:57-64

**Constat.** Le dossier d'Étrave est pont.dossier_commun(), c'est-à-dire %APPDATA%\MetaQuotes\Terminal\Common\Files\Etrave, et btc-secrets.json y est écrit. Or tout EA ou indicateur MQL5 de n'importe quel terminal peut lire ce dossier (FILE_COMMON), puis envoyer son contenu ailleurs par WebRequest. Le os.chmod(0o600) ne protège rien sous Windows (bitcoin.py:51, pont.py:91). Le jeton Telegram (reglages.txt, aussi recopié dans btc-secrets.json) est exposé de la même façon. Le bot BTC n'a pourtant aucun besoin d'être dans ce dossier.

**Scénario.** Un indicateur gratuit du Market, ou un EA « signal » installé pour essai, lit Etrave\btc-secrets.json et envoie la clé. Même sans droit de retrait, une clé avec trading spot et futures permet de vider le compte en tradant contre soi sur une paire illiquide, sauf si l'accès est bien limité à l'IP de la machine (la machine compromise est justement celle dont l'IP est autorisée).

**Vérification.** Le fait est exact : f_secrets = dossier Étrave = Common\Files\Etrave (bitcoin.py:116-118, etrave.py:330, pont.py:57-64). Tout EA ou script MQL5 peut lire ce dossier avec FILE_COMMON, et os.chmod(0o600) ne fait rien d'utile sous Windows. Deux corrections au scénario. (1) Un indicateur ne peut pas appeler WebRequest (restriction MQL5 dont je suis assez sûr) : il faut un EA ou un script. Celui-ci peut en revanche exfiltrer vers api.telegram.org, que le README fait justement autoriser. (2) Si la clé est limitée à l'IP comme le demande LISEZMOI:118, elle ne sert à rien hors de la machine, et un programme MQL5 ne peut pas joindre api.binance.com sans autorisation explicite de l'URL. Le risque existe, mais il suppose un programme malveillant déjà exécuté dans MT5, qui pourrait de toute façon trader le compte MT5. D'où « mineur ».

### ET-09 · mineur · plausible : Le programme lancé (terminal64.exe, metaeditor64.exe) se choisit par un fichier etat-*.txt du dossier commun

`etrave/mt5.py` : 40-53, 88-110, 167-198 ; etrave/etrave.py:101-113

**Constat.** terminaux() met en tête de liste les chemins lus dans le champ 'terminal' des fichiers etat-*.txt. N'importe quel programme MQL5 peut écrire ces fichiers dans Common\Files\Etrave, ainsi qu'un binaire (FileWriteArray). Au démarrage d'Étrave avec mt5Auto, ouvrir_mt5_si_demande() lance connus[0] sans rien demander. installer_ea() exécute de même metaeditor64.exe depuis ce dossier. Le garde-fou annoncé dans la docstring (« une requête ne peut pas faire lancer autre chose ») ne couvre pas le cas d'un fichier déposé.

**Scénario.** Un programme MQL5 malveillant écrit Etrave\x\terminal64.exe et etat-AAA.txt (symbole=AAA, instrument=nasdaq, terminal=...\Etrave\x). Au démarrage suivant de Windows, Étrave (lancé à l'ouverture de session, option « ouvrir MetaTrader » cochée) exécute ce binaire hors du bac à sable de MetaTrader.

**Vérification.** Relu : mt5.terminaux (40-53) met en premier les chemins 'terminal' lus dans etat-*.txt. Le seul contrôle est existe(chemin) : on ne vérifie ni que le chemin est hors du dossier commun, ni qu'il s'agit d'un vrai MT5. ouvrir_mt5_si_demande (etrave.py:101-113) lance connus[0] sans confirmation quand mt5Auto est coché. lire_etats trie par instrument puis symbole (pont.py:269), donc un faux etat-AAA.txt passe en tête. La docstring de mt5.py (9-10) promet plus que ce que fait le code. La faisabilité dépend de la possibilité, pour un programme MQL5, d'écrire un fichier nommé terminal64.exe dans Common\Files. Je le crois possible (pas de filtre d'extension dans FileOpen, à ma connaissance), mais sans certitude. L'attaque suppose aussi du code MQL5 malveillant déjà en place. Cela reste une vraie sortie du bac à sable, mais elle est peu probable pour un utilisateur seul.

### ET-13 · mineur · confirme : Le mot REEL écrit reel_confirme=true et rend inutile le garde-fou BOT_REEL_CONFIRME

`etrave/bitcoin.py` : 183 ; bitcoin/bot.py:239

**Constat.** LISEZMOI présente BOT_REEL_CONFIRME=oui comme un « garde-fou supplémentaire » pour le mode réel. Mais regler() écrit c['reel_confirme'] = (mode == 'reel'), et bot.py accepte le réel si ce drapeau est vrai. La seule protection est donc le mot REEL, accepté en minuscules (strip().upper()). Une modification à la main de config.json suffit aussi.

**Scénario.** Il suffit d'une saisie « reel » dans la page pour que le prochain démarrage passe en argent réel, sans la seconde barrière décrite dans la documentation.

**Vérification.** bitcoin.py:183 écrit c['reel_confirme'] = mode == 'reel'. bot.py:239 accepte le réel si BOT_REEL_CONFIRME vaut oui OU si reel_confirme est vrai. Le message d'erreur du bot présente d'ailleurs ces deux voies comme équivalentes. bitcoin.py:150 accepte « reel » en minuscules (strip().upper()). LISEZMOI:122 parle bien d'un « garde-fou supplémentaire », qui n'existe donc pas sur le chemin Étrave. C'est un écart documentaire, avec une seule barrière (le mot REEL) au lieu de deux.

### ET-14 · mineur · confirme : Demande de clôture consommée sans effet entre la clôture de 9:30 et la pose des ordres

`nasdaq/ORB-v6.mq5` : 1303-1316, 1360-1369

**Constat.** UiClose() n'agit que si gIn ou gPend est vrai. Si gSetupDue est vrai (préparation en cours, RSI pas encore prêt), la demande est marquée comme vue (gCloseSeen) et rien ne se passe. Les ordres sont ensuite posés normalement, et Étrave a déjà répondu {ok, numero}.

**Scénario.** À 9:35:01, l'utilisateur demande « Clôturer » pour ne pas trader ce jour-là. La demande est avalée et les Buy Stop / Sell Stop sont posés une seconde plus tard.

**Vérification.** ORB-v6.mq5:1303-1316 marque la demande comme vue (gCloseSeen, Sv), et UiClose (1360-1369) n'agit que si gIn ou gPend est vrai. Si gSetupDue est vrai (1149, 1589-1590), rien n'est fait et les ordres sont posés juste après. Le README (« ferme le trade au marché (ou annule les ordres du jour) dans les 2 secondes ») laisse croire le contraire. La fenêtre est en général très courte (Setup réussit au premier tick si le RSI est prêt), d'où « mineur ».

### ET-15 · mineur · confirme : Fichier .ini avec le mot de passe MT5 laissé dans %TEMP% si Étrave est fermé avant 60 s

`etrave/mt5.py` : 183-196

**Constat.** Le mot de passe est écrit en clair dans un fichier etrave-*.ini de %TEMP%. Il est effacé par un Timer en thread démon (60 s) ou par atexit. Fermer la fenêtre console (CTRL_CLOSE_EVENT), fermer la session ou tuer le processus n'exécute ni l'un ni l'autre : le fichier reste. Inversement, si MetaTrader met plus de 60 s à lire sa configuration (premier lancement, mise à jour), la connexion échoue.

**Scénario.** L'utilisateur lance MT5 avec connexion depuis la page, puis ferme la fenêtre noire d'Étrave aussitôt : le mot de passe du compte réel reste dans %TEMP%.

**Vérification.** mt5.py:183-196 : le mot de passe est écrit en clair par mkstemp dans %TEMP%, et l'effacement passe par un Timer démon de 60 s plus un atexit. Fermer la console (CTRL_CLOSE_EVENT, sans gestionnaire Python), fermer la session ou tuer le processus n'exécute ni l'un ni l'autre. Le fichier reste dans le %TEMP% de l'utilisateur, protégé par les ACL du profil, ce qui limite l'exposition. L'échec de connexion si MT5 lit sa configuration après 60 s est plausible, mais je ne l'ai pas vérifié.

### ET-16 · mineur · plausible : Sous Windows, SO_REUSEADDR permet à deux Étrave d'écouter le même port

`etrave/etrave.py` : 292, 337-346

**Constat.** http.server.HTTPServer met allow_reuse_address=1. Sous Windows, SO_REUSEADDR autorise un second bind sur 127.0.0.1:8788 au lieu de lever OSError. La branche deja_lancee() n'est alors jamais atteinte. Chaque instance a son propre jeton, et des requêtes arrivent sur l'autre instance (401). ouvrir_mt5_si_demande est lancé deux fois. Non vérifié sous Windows.

**Scénario.** Étrave lancé à l'ouverture de session (--sans-navigateur), puis double-clic sur Etrave.bat : deux serveurs, la page renvoie « Jeton absent ou invalide » au hasard.

**Vérification.** HTTPServer fixe allow_reuse_address=1, et socketserver.TCPServer.server_bind pose alors SO_REUSEADDR. Sous Windows, SO_REUSEADDR permet un second bind sur un port déjà en écoute par le même utilisateur, sauf SO_EXCLUSIVEADDRUSE (documentation Microsoft, j'en suis assez sûr). La branche deja_lancee (etrave.py:339-344) ne serait alors pas atteinte. Non vérifié sous Windows. Les conséquences restent bénignes (401, deux tentatives d'ouverture de MT5, la seconde voyant MT5 ouvert).

### ET-17 · mineur · confirme : arreter() tue un PID périmé (vivant.json ou bot.pid jamais effacé)

`etrave/bitcoin.py` : 294-299, 379-384

**Constat.** arreter() prend p['pid'] même quand le battement a plusieurs heures (bot planté), ou bot.pid, qui n'est jamais supprimé. Il lance ensuite taskkill /T /F sans vérifier que ce PID est bien un python bot.py. Windows réutilise vite les PID.

**Scénario.** Le bot a planté pendant la nuit, l'utilisateur clique « Arrêter » par précaution : taskkill /F /T tue un autre programme et ses enfants, par exemple le navigateur ou MetaTrader s'il a récupéré ce PID.

**Vérification.** arreter() (bitcoin.py:295-299) prend p['pid'] sans regarder l'âge du battement, ou bot.pid, que bot.py:252 écrit et que personne n'efface. Le PID n'est pas vérifié avant taskkill /T /F (319). Windows réutilise les PID. Le scénario demande un bot mort avec vivant.json resté en place (crash) puis un clic sur Arrêter : plausible, et la conséquence touche hors trading.

### ET-18 · mineur · confirme : Jeton de la page donné à tout processus ou utilisateur local

`etrave/etrave.py` : 243-250

**Constat.** GET / renvoie la page avec le jeton dès que l'en-tête Host est local. Le Host et le jeton bloquent bien les sites web (DNS rebinding, CSRF : l'en-tête personnalisé impose un preflight, OPTIONS n'est pas géré, X-Frame-Options est à DENY). En revanche, n'importe quel processus local, ou un autre utilisateur d'un VPS partagé en RDP, obtient le jeton par une simple requête, puis peut fixer le risque à 20 % (le mot RISQUE est une simple chaîne), clôturer, ou passer le bot en réel.

**Scénario.** VPS Windows multi-session : un autre compte lance curl http://127.0.0.1:8788/, récupère le jeton et règle le risque à 20 % avec confirmation='RISQUE'.

**Vérification.** etrave.py:243-250 : GET / avec un Host local renvoie la page avec le jeton, sans autre contrôle. Contre les sites web, la protection tient : le jeton dans un en-tête personnalisé déclenche une preflight, OPTIONS n'est pas géré, aucune réponse ne porte d'ACAO, et l'en-tête Host bloque le DNS rebinding. Tout processus local ou autre session RDP sur la même machine obtient en revanche le jeton. Le mot RISQUE n'est qu'une chaîne connue. Cela n'a d'importance que sur une machine partagée.

### ET-19 · mineur · confirme : Content-Length négatif accepté

`etrave/etrave.py` : 260-267

**Constat.** Avec taille = int('-1'), le test taille > CORPS_MAX est faux, puis rfile.read(-1) lit jusqu'à la fin de la connexion, sans délai maximal ni taille maximale (aucun timeout de socket). Il faut le jeton pour y arriver.

**Scénario.** Un client local qui détient le jeton peut bloquer un thread et remplir la mémoire.

**Vérification.** etrave.py:260-267 : int('-1') passe le test taille > CORPS_MAX, puis rfile.read(-1) lit jusqu'à la fermeture de la connexion, sans délai maximal sur le socket. Il faut le jeton. L'effet se limite à un thread et à de la mémoire.

### ET-20 · mineur · confirme : Installer l'EA depuis la page recompile pendant qu'un trade est ouvert

`etrave/mt5.py` : 88-125 ; etrave/etrave.py:166-170

**Constat.** installer_ea() copie puis compile ORB-v6.mq5 sans vérifier l'état de l'EA (position, ordres en attente, heure). Recompiler un .ex5 attaché à un graphique fait recharger l'EA par MT5 (OnDeinit/OnInit, puis état relu depuis les GlobalVariables). Le README demande de le faire « hors séance, sans trade ouvert », mais rien ne l'impose.

**Scénario.** Clic sur « Mettre à jour l'EA » à 10:15 avec une pyramide en cours : l'EA redémarre au milieu du trade. Son état dépend de ce qui avait été sauvegardé, et ce code n'a jamais été compilé.

**Vérification.** mt5.py:88-125 copie puis compile sans lire l'état de l'EA (position, ordres, heure), et etrave.py:166-170 ne vérifie rien non plus. Quand un .ex5 attaché à un graphique est recompilé, MT5 recharge l'EA (OnDeinit avec REASON_RECOMPILE, puis OnInit et LoadState) : j'en suis sûr. La reprise dépend de LoadState, que je n'ai pas audité. Le README (140) demande de le faire hors séance, sans que rien ne l'impose.

### ET-21 · mineur · confirme : Mots de confirmation traités différemment selon l'onglet ; coupe-circuit réglable jusqu'à 90 % sans confirmation

`etrave/pont.py` : 171, 232 ; etrave/bitcoin.py:150, 159, 171-173, 340

**Constat.** RISQUE et CLOTURER doivent être tapés exactement, alors que REEL, LEVIER et FERMER sont acceptés en minuscules et avec espaces. perte_max peut passer de 0,40 à 0,90 sans aucun mot, ce qui revient presque à supprimer le coupe-circuit. Pour le Nasdaq, la confirmation n'est demandée qu'en cas de hausse au-dessus de 1 % : passer de 20 % à 5 % se fait sans mot. C'est cohérent avec le code, mais ambigu face au README (« Au-delà de 1 %, il faut taper le mot RISQUE »).

**Scénario.** Le coupe-circuit à 90 % est réglé d'un clic, sans avertissement.

**Vérification.** pont.py:171 et 232 comparent exactement (!= 'RISQUE', != 'CLOTURER'), alors que bitcoin.py:150, 159 et 340 font strip().upper(). perte_max accepte 0,10-0,90 sans aucun mot (171-173). Baisser le risque Nasdaq sans mot est volontaire et testé (test_interface.py:73). C'est une incohérence mineure, et un coupe-circuit à 90 % reste un choix explicite de l'utilisateur.

### ET-22 · mineur · confirme : Jeton Telegram du bot BTC jamais mis à jour ni effacé après un changement dans Connexions

`etrave/bitcoin.py` : 217-221, 285-287

**Constat.** _telegram() ne recopie le jeton et la discussion que s'ils sont tous les deux renseignés, et seulement lors de enregistrer_cles() ou demarrer(). Effacer ou changer le Telegram dans Connexions laisse l'ancien jeton dans btc-secrets.json, et le bot en cours garde le sien. Par ailleurs, les variables d'environnement BINANCE_API_KEY/SECRET passent avant le fichier (bot.py:58-59), alors que « Tester la connexion » teste les clés du fichier.

**Scénario.** Après avoir révoqué l'ancien bot Telegram, l'utilisateur ne reçoit plus les alertes BTC (stop touché, erreur de cycle) sans que rien ne le signale. Autre cas : le test de clé est vert alors que le bot utilise d'autres clés, celles de setx.

**Vérification.** bitcoin.py:217-221 : la recopie ne se fait que si le jeton et la discussion sont tous deux remplis. Un effacement dans Connexions ne se propage donc jamais à btc-secrets.json. Le bot en marche garde la configuration chargée au démarrage (bot.py:71-72). bot.py:58-59 donne la priorité à l'environnement pour la clé Binance, alors que tester() (229-233) n'essaie que le fichier. Même ordre pour Telegram dans notif.py:22-23.

### ET-23 · mineur · confirme : « Tout fermer » demandé bot arrêté : fermeture immédiate au prochain Démarrer

`etrave/bitcoin.py` : 339-347

**Constat.** fermer() crée FERMER et MAINTENANT sans vérifier que le bot tourne. Les drapeaux restent jusqu'au prochain lancement, qui ferme tout dès son premier cycle puis se met en pause. De même, rearmer() hors marche réécrit etat.json pendant qu'un bot au battement périmé, en plein cycle long, l'écrasera ensuite.

**Scénario.** Clic sur « Tout fermer » par erreur, bot arrêté. Des jours plus tard, Démarrer ferme la position au marché sans nouvelle confirmation.

**Vérification.** fermer() (bitcoin.py:339-343) pose FERMER et MAINTENANT sans vérifier que le bot tourne, et demarrer() ne les nettoie pas. Au lancement suivant : MAINTENANT déclenche un cycle forcé, FERMER met la cible à 0 (bot.py:155-157) puis pose PAUSE (171-173). La page expose bien les drapeaux (bitcoin.py:368), ce qui réduit la surprise. rearmer() hors marche réécrit etat.json, qu'un bot vivant au battement périmé écrasera en fin de cycle (bot.py:198) : exact.

### ET-24 · mineur · plausible : EA vu comme arrêté si OnTimer est bloqué plus de 15 s

`etrave/pont.py` : 36, 266 ; etrave/etrave.py:146-149

**Constat.** L'état n'est écrit que dans OnTimer (ORB-v6.mq5:1573). Les WebRequest synchrones (Telegram, CallMeBot) ou des ClosePos qui réessaient peuvent bloquer plus de 15 s. Pendant ce temps, Étrave refuse « Clôturer » (409 : « ferme le trade directement dans MetaTrader 5 »).

**Scénario.** Telegram lent au moment d'une alerte : la clôture d'urgence depuis la page est refusée pendant quelques secondes.

**Vérification.** pont.py:36 (EA_MUET_S = 15) et etrave.py:146-149 (409 si en_marche est faux). Chaque WebRequest a un délai de 5 s (ORB-v6.mq5:371, 387), et FlushNotifs tourne dans OnTimer. Il faut au moins trois envois lents, ou un OnTick bloqué, pour dépasser 15 s. Le blocage est temporaire et la page renvoie vers MT5.

### ET-25 · mineur · confirme : Etrave.bat : alias Python du Microsoft Store et caractère % dans le chemin du raccourci de démarrage

`etrave/Etrave.bat` : 6-8 ; etrave/mt5.py:145

**Constat.** where python trouve aussi l'alias WindowsApps\python.exe, qui ouvre le Store au lieu de lancer Python : le message « Python n'est pas installé » ne s'affiche jamais. Le .bat de démarrage écrit par demarrage_windows() met le chemin tel quel : un % dans le nom d'un dossier y serait lu comme une variable.

**Scénario.** Sur un Windows neuf sans Python, double-clic sur Etrave.bat : le Store s'ouvre ou rien ne se passe, sans explication.

**Vérification.** Etrave.bat:6-8 : sur un Windows neuf, `where python` trouve l'alias WindowsApps\python.exe. Nuance : l'alias récent affiche dans la console un message « Python est introuvable… Microsoft Store » et sort avec le code 9009, et `if errorlevel 1 pause` le laisse lisible. Ce n'est donc pas « sans explication », mais le message prévu n'est pas montré. mt5.py:145 : un % dans le chemin serait bien interprété par cmd dans le .bat écrit. C'est un cas rare.

### Oublis relevés par le vérificateur

- **critique** · Passage papier → réel sans remise à zéro de etat.json : coupe-circuit au premier cycle réel et vente de tout le BTC au comptant (`etrave/bitcoin.py` : 139-186 (avec bitcoin/bot.py:69, 147-154, 159-169)) : regler() change le mode dans config.json, mais le dossier d'état reste le même pour tous les modes et etat.json n'est ni remis à zéro ni séparé. En réel, le bot recharge le 'pic' du mode papier (10 000 $ par défaut, ou le plus haut du papier) et calcule pic = max(pic, capital réel). Si le capital Binance est sous 60 % de ce pic (avec perte_max = 0,40), le coupe-circuit se déclenche dès le premier cycle : cible 0, 'arrete' posé, puis vente de tout le BTC spot du compte, y compris celui que l'utilisateur détenait avant le bot, puisque Etat.capital compte tout le solde. Reproduit avec un faux courtier : la décision veut +80 % d'exposition, un compte réel de 3 700 $ et un etat.json papier avec pic=10 000 donnent l'ordre [vendre_spot 0,03 BTC 'fermer l'achat au comptant'] et le motif « coupe-circuit : capital 3,700 < 60% du plus haut 10,000 ». derniere_bougie et stop sont eux aussi repris du papier.
- **mineur** · Démarrer répond « ok » même si le bot meurt aussitôt, sans alerte (`etrave/bitcoin.py` : 274-292 (avec bitcoin/bot.py:235-241, 71-84)) : demarrer() renvoie {ok, pid} dès que Popen a réussi. Or Bot(cfg) et CourtierBinance (load_markets, et aussi la NotSupported du testnet de ET-10, un « restricted location » ou un mode réel non confirmé) peuvent faire échouer le processus avant la boucle, hors de tout try, et sans message Telegram (notif.envoyer n'est appelé qu'une fois boucle() lancée). Le journal d'Étrave note « bot BTC : demarrer » et l'erreur n'apparaît que dans console.log. La page ne montre le bot « arrêté » qu'au rafraîchissement suivant, sans dire pourquoi.
- **mineur** · La reprise de l'ancien dossier crypto/bot repose sur le même test des 60 s et peut déplacer config.json et etat/ sous un ancien bot en plein cycle (`etrave/bitcoin.py` : 65-80 ; etrave/etrave.py:309-314) : reprendre_ancien_dossier() s'exécute à chaque lancement d'Étrave. Elle juge que l'ancien bot est arrêté si son vivant.json date de plus de 60 s, ce qui arrive pendant un long cycle (comme en ET-01). Elle déplace alors etat/ pendant que ce bot écrit dedans : le os.replace de battement() ou de sauver() vise un dossier qui n'existe plus, le bot plante et sa position n'est plus suivie. Le cas est rare : migration unique, avec un ancien bot lancé hors d'Étrave.

### Non vérifié par le lecteur

- Aucun comportement propre à Windows n'a été exécuté : partage de fichiers entre os.replace et FileOpen de MQL5 (FILE_SHARE_READ|FILE_SHARE_WRITE sans partage de suppression), FileMove(FILE_REWRITE) pendant une lecture par Étrave, SO_REUSEADDR sur 127.0.0.1:8788, taskkill /T /F, tasklist, /config: de terminal64.exe, CTRL_CLOSE_EVENT et atexit. ET-02 est mesuré sous Linux seulement. ET-11 et ET-16 restent plausibles, non reproduits.
- Je n'ai pas ouvert etrave/page.html, etrave/risque.py ni etrave/reference.json, conformément aux règles. Je ne sais donc pas si la page affiche le mode et le levier réels du bot en marche (ET-06), si elle remplit d'elle-même un mot de confirmation, si elle permet des POST concurrents (fréquence réelle de ET-02), ni ce que renvoie GET /api/risque.
- L'EA n'a pas été compilé (pas de MetaTrader ici). Je n'ai donc pas pu vérifier que ReadSettings et WriteState se comportent comme le code le laisse croire, notamment FileReadString en mode FILE_TXT|FILE_ANSI avec CP_UTF8, ni que la recompilation recharge l'EA sur le graphique (ET-20).
- ET-10 : l'erreur NotSupported de ccxt sur le testnet futures est vérifiée dans la source de ccxt 4.5.93 (wheel téléchargé depuis PyPI), mais ccxt n'est pas installé ici et aucun appel n'a été fait. Je ne connais pas la version de ccxt de l'utilisateur.
- Je n'ai pas lu en entier les tests etrave/test_interface.py et etrave/test_bitcoin.py. Ils passent (37 tests, lancés sur une copie dans le scratchpad). Le test d'accord des clés n'appelle pas retenir_mt5 (clés mt5_login, mt5_serveur et mt5_auto, que l'EA ignore sans dommage). Aucun test ne couvre la concurrence, le battement pendant un cycle long, ni une lecture ratée suivie d'une écriture.
- Les bornes du risque (0,05 à 20 %) et du levier (1 à 2000) sont identiques dans pont.py et l'EA : vérifié, sans écart. Les noms de clés écrits par Étrave (risque_pct, levier, nasdaq, telegram_jeton, telegram_discussion, essai_telegram, cloturer) sont tous lus par l'EA (ORB-v6.mq5:1280-1303) : sans écart. L'horloge de la demande de clôture (time.time() d'un côté, TimeGMT() de l'autre, sur la même machine) est cohérente. Je n'ai pas examiné les autres parties de l'EA, hors du périmètre de cette revue.
