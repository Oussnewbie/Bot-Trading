# Audit du 14 novembre 2026

> **Note du 14 novembre 2026, après l'audit.** Le dépôt a été nettoyé : les données M5 2015-2026 sur lesquelles cet
> audit a été fait ont été remplacées par du M1 2018-01-01 → 2026-11-13, et les scripts `v5_exp*.py` ont été retirés.
> Les chiffres ci-dessous (1 925 trades, +372R, -74R) portent sur l'ancien jeu de données ; sur les données actuelles
> la v5 fait 1 427 trades, +438R, pire baisse -25R (voir le README). Le texte de l'audit n'a pas été modifié.

Audit du dépôt tel qu'il est sur `main` : le simulateur Python, le script TradingView et l'EA MetaTrader 5 de l'ORB v5.
Ce document dit ce qui a été vérifié, ce qui a été corrigé, et ce qui attend une décision.

**Ce qui a pu être exécuté ici** : le simulateur Python, sur tout l'historique du dépôt.
**Ce qui n'a pas pu l'être** : le script Pine et l'EA MQL5. Il n'y a ni TradingView ni MetaTrader sur cette machine, donc
ils ont été audités à la lecture seulement. Aucune ligne de ces deux fichiers n'a été modifiée : les corrections
proposées sont décrites plus bas, à compiler et tester avant usage.

**Ce que le dépôt ne contient pas** : pas d'or, pas de stratégie à biais H4 / MA200 / swing / Fibonacci, pas de programme
« bot » autonome, pas de vérification automatique GitHub. La seule stratégie est l'ORB v5 sur NAS100. Les règles 1 à 7 du
README ont servi de « doc ».

## 1. Corrigé sur `main` (Python uniquement)

| # | Défaut | Preuve | Correction | Test |
|---|---|---|---|---|
| 1 | **Cache jamais invalidé.** Après un changement de données ou de code, `prep()` rendait l'ancien résultat sans prévenir. | Données remplacées par 2015-2016 seulement : le simulateur annonçait toujours 3 027 jours jusqu'au 2026-10-30 et 1 915 trades. | Le cache porte une empreinte des deux fichiers de données, de `v5_lab.py` et de `load10.py`. | `test_le_cache_est_refait_quand_les_donnees_changent` |
| 2 | **10 trades valides de janvier 2015 écartés.** `prep()` sautait tout jour sans 14 jours d'ATR journalier, alors que la v5 ne se sert pas de cet ATR. | La réécriture indépendante des règles trouve 1 925 trades, le simulateur 1 915 ; les 10 de différence sont tous avant le 23 janvier 2015. | Ces jours sont gardés. | `test_les_premiers_jours_ne_sont_pas_ecartes` |
| 3 | Une variante de recherche dont le stop n'a pas de valeur donnait un R « NaN » qui empoisonnait les totaux. | Lecture de `path()` : `risk <= 0` est faux pour NaN. | Pas de trade dans ce cas. | `test_un_stop_sans_valeur_ne_donne_pas_de_trade` |
| 4 | Appels pandas dépréciés (`dayofweek`), versions non fixées. | Avertissements à l'exécution avec pandas 3.1. | `day_of_week`, `requirements.txt`. | Les tests tournent avec les avertissements en erreur. |
| 5 | Aucun test. | — | 22 tests dans `tests/`. | — |

**Ce que ça change dans les chiffres** (correction 2) : 1 925 trades au lieu de 1 915, +372R au lieu de +373R, et surtout
**pire baisse de -74R au lieu de -69R**. Le README est à jour. Les en-têtes de `pine/ORB-v5.pine` et `mt5/ORB-v5.mq5`
citent encore les anciens chiffres (1 915 trades, -69R), puisque ces fichiers n'ont pas été touchés.

**Ce que ça change pour les signaux** : rien. Aucune règle, aucun réglage d'indicateur, aucun stop, aucun ratio et aucun
risque n'a changé. Le script TradingView et l'EA sont identiques à avant.

## 2. Vérifié et trouvé juste

- **Le simulateur applique le README.** Une réécriture naïve des règles 1 à 7 (`tests/regles_readme.py`), qui ne partage
  rien avec `v5_lab.py`, donne les mêmes 1 925 trades, au millionième de R près. 13 journées écrites à la main donnent le
  résultat calculé sur le papier dans les deux.
- **Pas d'information du futur.** En remplaçant toutes les bougies postérieures à 9:35 d'un jour J, rien de ce que le
  simulateur savait à 9:35 ce jour-là ne change, ni aucun trade des jours précédents.
- **Pas de bougie non clôturée.** Le RSI, le range et la fenêtre de l'élan sont lus sur des bougies terminées.
- **Fuseau et heure d'été.** Les fichiers sont en UTC ; la bougie de 9:30 New York tombe à 13:30 UTC en été (2 024 jours)
  et 14:30 UTC en hiver (1 022 jours). La pause quotidienne est bien entre 17:00 et 18:00 à New York toute l'année.
- **Côtés bid et ask.** Achat exécuté sur l'ask, stop d'un achat sur le bid, stop d'une vente sur l'ask.
- **Données.** 733 078 bougies bid et ask, 0 doublon, 0 valeur manquante, 0 bougie incohérente, ask jamais sous le bid.
- **Coûts.** Le spread est réel (bid et ask). Pas de swap à oublier : tout est fermé à 15:50.
- **Secrets.** Aucun jeton Telegram, aucune clé CallMeBot, aucun numéro de téléphone, aucun identifiant de courtier, de
  TradingView ou de prop firm dans le code ni dans l'historique git (toutes branches, fichiers supprimés compris).
- **Qui commande le bot.** Personne : ni le script ni l'EA ne lisent de commande. Ils ne font qu'envoyer.

## 3. Trouvé, non corrigé : une décision est nécessaire

### 3.1 Le glissement de 0,1 point est optimiste (coûts)

Le simulateur ajoute 0,1 point à chaque exécution. Sur un ordre stop à l'ouverture de New York, c'est peu.
v5 sur 2015 → 2026, même calcul avec d'autres glissements :

| Glissement par exécution | Total | Par trade | Pire baisse | 2015-17 | 2018-22 | 2023-26 |
|---|---|---|---|---|---|---|
| 0 point | +397R | +0,206R | -71R | -50R | +285R | +162R |
| **0,1 point (code actuel)** | **+372R** | **+0,193R** | **-74R** | -55R | +273R | +154R |
| 0,5 point | +269R | +0,140R | -121R | -105R | +234R | +140R |
| 1 point | +145R | +0,075R | -160R | -148R | +173R | +119R |
| 2 points | -96R | -0,050R | -241R | -228R | +52R | +80R |

Le résultat des années récentes résiste (le range fait 40 à 90 points). Celui de 2015-2017 non (le range faisait 9 points).
Je n'ai pas changé la valeur : c'est une hypothèse sur ton courtier, pas un bug. **Décision : mesurer ton glissement réel.**

### 3.2 Jours fériés américains et demi-séances

Le CFD cote ces jours-là, mais la bourse est fermée ou ferme à 13:00. Rien dans les règles ne les exclut.

- 48 trades de la v5 tombent un de ces jours sur 2015 → 2026. Ils font **-25,6R** au total (-0,53R par trade), contre
  +398R pour les 1 877 autres.
- Le simulateur sort à la dernière bougie disponible (vers 12:55 ou 13:10). **L'EA, lui, ne peut pas** : à 15:50 le marché
  est fermé. `mt5/ORB-v5.mq5:931-933` ferme au premier tick reçu après 15:50, donc à la réouverture de 18:00, après cinq
  heures sans cotation. Sur les 18 trades concernés, l'écart entre la dernière clôture et la réouverture va de -2,7R à
  +9,9R.
- **Le script Pine garde la position jusqu'à minuit.** `pine/ORB-v5.pine:434` ferme si la bougie est dans 15:45-16:00, ou
  si la date de New York a changé. Un jour écourté n'a pas de bougie entre 15:45 et 16:00, et les bougies de 18:00 à
  23:55 sont encore à la même date.
- Correction proposée pour le Pine, sans toucher à une règle : fermer dès que l'heure de New York est 15:45 ou plus.
  ```pine
  bool apresFlat = hour(time, TZ_NY) * 60 + minute(time, TZ_NY) >= 15 * 60 + 45
  if strategy.position_size != 0 and (apresFlat or (not na(cur) and nyDate != cur.day))
      strategy.close_all(comment = "Fin de journée")
  ```
- Ne plus trader ces jours-là est une règle de stratégie : la recherche l'a testée (branche `recherche/stops`, variante F3).

### 3.3 Écarts entre le code et le README

| # | README | Code | Effet mesuré |
|---|---|---|---|
| a | Règle 4 : 1R = taille × range. | Le simulateur divise par la distance entrée-stop, plus grande que le range quand l'ordre est exécuté au-delà du niveau. Le Pine et l'EA suivent le README. | +377R au lieu de +372R sur 12 ans. Un stop plein coûte -1,02R en moyenne, -1,04R à -1,05R en 2015-2017, -1,68R au pire. |
| b | Règle 3 : si l'autre côté du range est touché d'abord, l'ordre est annulé. | Le Pine (`:438-449`) et l'EA (`:815-828`) ne regardent le côté bloqué qu'à la clôture d'une bougie. Si le prix touche le côté bloqué puis casse le bon côté dans la même bougie M5, ils entrent. | Non mesurable en M5. Le simulateur compte un stop plein quand les deux côtés sont touchés dans la bougie d'entrée : 163 trades sur 1 371 avant avril 2023 (12 %). |
| c | Règle 6 : sortie à 15:50. | Les messages Telegram du Pine disent « sortie à 15:45 NY » (`:384`, `:534`). La position sort bien à 15:50. | Texte du signal seulement. |
| d | Rien sur le nombre de bougies de 9:00-9:30. | Le simulateur et l'EA (`:586`) exigent au moins 2 bougies ; le Pine (`:471`) une seule. | 4 jours en 12 ans. |

Exemple pour (a), 22 février 2017, avec un glissement d'un demi-spread : le range fait 3,5 points et l'achat est exécuté
1,9 point au-dessus du niveau, à 5 346,7. Le stop à 5 341,3 sort à 5 340,4 : 6,3 points perdus pour 3,5 points de risque
prévu, soit -1,81R.

### 3.4 Sécurité

- **Identifiant de chat Telegram écrit en dur** : `pine/ORB-v5.pine:61`, valeur par défaut du réglage « Chat ID »
  (`-100357…927`). Il est dans l'historique depuis le premier commit (`2e53850`). Ce n'est pas un secret à lui seul : sans le
  jeton du bot, on ne peut rien envoyer. Mais quiconque lit le dépôt connaît ton canal. Je ne l'ai pas changé.
- **Le jeton du bot** n'est pas dans le dépôt. Il vit dans l'URL du webhook de l'alerte TradingView et dans les réglages
  de l'EA. Toute personne qui a ce jeton peut écrire dans ton canal : ne partage ni capture de l'alerte ni fichier de
  réglages (`.set`).
- **WhatsApp** : CallMeBot est un service tiers. Ton numéro, ta clé et le texte de chaque signal passent par lui, dans
  l'URL d'une requête GET (`mt5/ORB-v5.mq5:246`).
- **Entrées non bornées dans l'EA** : `InpRiskPct` n'a pas de maximum (`:46`), et `ParseHM` (`:203-209`) accepte « 25:99 ».
  Une faute de frappe sur le risque passe sans alerte. Le Pine borne le risque par le bas seulement (`:36`).
- **Cache du simulateur** : `v5_days.pkl` et `v5_bars.npz` sont relus avec pickle. Ne jamais y mettre un fichier venu
  d'ailleurs. Ils sont ignorés par git.
- **Limites de débit** : pas de boucle d'envoi. L'EA réessaie une entrée refusée 3 fois au plus (`:687-696`).

## 4. Script TradingView et EA : constats à la lecture

Ces constats viennent de deux lectures indépendantes du code (la mienne et celle d'un second relecteur), recoupées.
« Certain » = prouvé par la trace du code. « À confirmer » = dépend d'un comportement que seule l'exécution montre.
**Rien n'a été modifié dans ces deux fichiers.** Les corrections sont des propositions, non compilées.

### 4.1 À traiter en premier

| # | Fichier, lignes | Ce qui se passe | Conséquence | Statut |
|---|---|---|---|---|
| 1 | EA `:925-934`, Pine `:433-435`, `:334` | **Séance écourtée** (voir 3.2). L'EA n'a pas de minuterie : sans tick, rien ne tourne, donc la sortie se fait à la réouverture. Le Pine attend minuit, et peut même ajouter la pyramide le soir, car il ne l'interdit que de 15:45 à 16:00. | Position tenue pendant la fermeture, parfois tout le week-end (lendemain de Thanksgiving). Le stop peut être sauté par un écart d'ouverture. | Certain |
| 2 | EA `:250`, `:266`, `:653`, `:807-808`, `:917-921` | **Telegram ou WhatsApp lent retarde l'entrée.** `WebRequest` est bloquant, 5 secondes au plus par service. À 9:35:00, `Setup()` envoie « ORDRES ORB placés » (`:653`) avant que `CheckEntries()` (`:921`) regarde le prix. Même chose pour le stop au prix d'entrée : le message (`:807`) part avant le déplacement du stop (`:808`). | Jusqu'à 10 secondes de retard à l'ouverture, les ticks reçus entre-temps sont perdus. Entrée plus loin du niveau, donc perte possible de plus de 1R. Sans effet si seules les notifications push sont actives (réglage par défaut). | Certain pour l'ordre des appels |
| 3 | EA `:665-680`, `:893`, `:831-833` | **EA lancé ou relancé entre 9:35 et 9:40.** Il arme les ordres puis achète tout de suite au marché si le prix a déjà dépassé le niveau, quelle que soit la distance. La taille reste calculée sur le range. | Exemple : lancé à 9:39 avec le prix à +1R du niveau, la perte possible est de 2R pour 1R prévu. | Certain |
| 4 | EA `:294-309` | **État perdu si MT5 plante.** Les variables globales ne sont écrites sur disque qu'à la fermeture propre : il n'y a pas de `GlobalVariablesFlush`. Après un plantage en cours de trade, l'EA relit un état ancien : mauvais stop de référence, seuils +1,5R et +2R faux, pyramide possible une seconde fois. `gUsePyrToday` n'est jamais sauvegardé. | Signaux faux, troisième unité possible, deuxième trade possible le même jour si le plantage et le redémarrage ont lieu entre 9:35 et 9:40. | Certain, il faut un arrêt brutal |
| 5 | EA `:611-612`, `:725-726` | **Arrondi des lots faux si le pas de volume n'est pas une puissance de 10.** Avec un pas de 0,5, 0,25 ou 0,05, le nombre de décimales est mal calculé et `NormalizeDouble` arrondit vers le haut : 0,5 devient 1. | Risque jusqu'à doublé, ou ordre refusé. Sain pour les pas de 1, 0,1 et 0,01. | Certain si ton courtier a un tel pas |

Corrections proposées :

1. Pine : fermer dès 15:45 ou plus à l'heure de New York (extrait en 3.2), et interdire la pyramide hors séance.
   Sortir *avant* la fermeture demande une liste de dates : c'est une règle nouvelle. **D'ici là, coupe l'EA et l'alerte
   les jours de séance écourtée. Les prochains : jeudi 26 et vendredi 27 novembre 2026, jeudi 24 décembre 2026.**
2. EA : mettre les messages dans une file et les envoyer en fin de `OnTick`, après `CheckEntries()`.
   ```mql5
   string gOutbox[];
   void Notify(string msg) { int n = ArraySize(gOutbox); ArrayResize(gOutbox, n + 1); gOutbox[n] = msg; }
   void Flush() { for(int i = 0; i < ArraySize(gOutbox); i++) SendNow(gOutbox[i]); ArrayResize(gOutbox, 0); }  // SendNow = ancien corps de Notify
   // dernière ligne de OnTick : if(!gPend) Flush();
   ```
3. EA : au début de `CheckEntries()`, ne rien faire hors de la fenêtre de validité, et refuser le trade du jour si l'EA
   démarre après 9:35 avec un niveau déjà franchi. Le second point est une décision.
   ```mql5
   if(TimeCurrent() >= gOrTime + (InpLiveBars + 1) * BAR) return;
   ```
4. EA : `GlobalVariablesFlush();` en dernière ligne de `SaveState()`, et sauvegarder `gUsePyrToday`.
5. EA : compter les décimales du pas de volume au lieu de passer par `log10`.
   ```mql5
   int vd = 0; while(vd < 8 && MathAbs(step * MathPow(10, vd) - MathRound(step * MathPow(10, vd))) > 1e-9) vd++;
   ```

### 4.2 Moins graves

| # | Fichier, lignes | Ce qui se passe | Conséquence | Statut |
|---|---|---|---|---|
| 6 | EA `:730-731` | Le stop de la pyramide est posé 1R sous le prix du marché au moment de l'ajout, sans plancher. Le simulateur ajoute à la clôture, toujours à +2R ou plus. Si le premier tick de la bougie suivante est plus bas, ou après un redémarrage, le stop commun tombe sous +1R. | Le « pire cas zéro » de la règle 7 n'est plus garanti. | Certain |
| 7 | EA `:886-889` | Le réglage d'heure du serveur n'est contrôlé qu'au lancement. Un mauvais mode d'heure d'été ne se voit que les semaines où les États-Unis et l'Europe sont décalés (mars, fin octobre). | Range pris sur la mauvaise bougie pendant ces semaines, sans message. | Certain |
| 8 | EA `:704-718`, `:929` | Un stop remonté que le courtier a refusé (prix trop près) n'est jamais reposé. Seul l'EA le surveille. | Si MT5 se coupe ensuite, le courtier n'a que le stop d'origine : -1R au lieu de zéro. | Certain |
| 9 | EA `:801-804` | Le +1,5R n'est cherché que sur la dernière bougie close. Atteint pendant une coupure de MT5, il est oublié. | Pas de stop au prix d'entrée, là où le test en a un. | Certain |
| 10 | EA `:398-411`, `:932-933` | Une sortie de 15:50 refusée n'est écrite que dans le journal, à chaque tick. Aucun message. | La position peut passer la nuit sans que tu le saches. | Certain |
| 11 | EA `:681`, `:624-625` | Une exécution partielle est acceptée, mais la taille et la somme risquée gardent la valeur demandée. | Ajout de pyramide plus gros que la position, R affiché trop petit. Rare sur un indice. | Certain |
| 12 | EA `:879`, `:385-396` | Deux graphiques du même symbole avec le même numéro magique partagent l'état. | Deux entrées, risque doublé. | Certain |
| 13 | EA `:912-915`, `:781-782` | La bougie est marquée « traitée » avant le contrôle. Si `CopyRates` échoue à ce moment, les contrôles de cette bougie sont perdus. | Annulation, stop à l'entrée ou pyramide manqués pour une bougie. | À confirmer (échec rare) |
| 14 | EA `:678`, `:709`, `:731` | Les prix de stop sont arrondis à `_Digits`, pas au pas de cotation du symbole. | Stop refusé chez un courtier dont le pas diffère, donc pyramide refusée. | À confirmer selon le courtier |
| 15 | Pine `:434-435`, `:394-399` | Le message de sortie de fin de journée part à 15:55 : TradingView ne voit le trade fermé qu'à l'exécution suivante du script. | Si tu fermes à la main sur le signal, tu sors 5 minutes après le bot. | Certain |
| 16 | Pine `:482`, `:532` | La « Taille » du message est calculée sur le capital simulé par TradingView (capital de départ plus gains simulés depuis le début du graphique), pas sur ton compte. | Taille à ne pas recopier telle quelle. | Certain |
| 17 | Pine `:460` | Pas de garde sur la bougie clôturée. | Sans effet avec les réglages actuels. Si tu coches « À chaque tick » dans les propriétés, les ordres sont posés sur un range en formation. | Certain sous cette condition |
| 18 | Pine `:118` | Deux `alert()` peuvent tomber sur la même bougie (exécution et pyramide). La doc ne dit pas clairement si les deux partent. | Un message de pyramide pourrait manquer. | À confirmer dans TradingView |
| 19 | EA `:560` | Le RSI est lu sans vérifier que l'indicateur a fini son calcul. | Mauvais côté possible si le RSI est proche de 50 au premier tick de 9:35. | À confirmer |

### 4.3 Vérifié et trouvé juste dans le Pine et l'EA

- Règles 1, 2, 4, 5, 6 et 7 : mêmes calculs que le simulateur, sur des bougies clôturées (indice 1 dans l'EA, exécution à
  la clôture dans le Pine). L'entrée au tick de l'EA est voulue et correspond au test.
- Conversion vers l'heure de New York dans l'EA (`UsDst`, `EuDst`, `ToNY`) : juste, y compris les semaines de décalage
  entre les États-Unis et l'Europe, si le réglage du serveur est bon. Le Pine utilise le fuseau `America/New_York`.
- Un trade par jour, week-end normal, fermeture manuelle, compte netting, refus d'entrée ou de pyramide notifié une
  fois sans boucle, redémarrage propre de l'EA en cours de trade.
- Format du message Telegram du Pine : guillemets, barres obliques inverses et retours à la ligne sont échappés.
- Aucun secret n'est écrit dans le journal : les messages d'erreur ne citent que l'hôte, jamais l'URL ni le jeton.
  MT5 garde en revanche les réglages en clair dans les fichiers `.set` et les profils de graphique.

## 5. Ce qui reste lent ou compliqué

- EA : le panneau est reconstruit à chaque tick et `SyncPosition` tourne deux fois par tick. Sans conséquence.
- Les chemins d'objectif (`InpTgtR`, `tgtR`) ne servent pas à la v5.
- `v5_lab.py` change de dossier courant à l'import (`os.chdir`) et garde l'état dans deux variables globales (`G`, `D`).
  Ça marche ; je n'y ai pas touché.
- `rsi()` rend 50 quand il n'y a eu aucune baisse depuis le début des données, là où le RSI vaut 100. Sans effet sur les
  données réelles (il y a toujours eu une baisse après quelques bougies).
- Rien n'est lent : toute la référence se rejoue en une seconde.

## 6. Vérification automatique GitHub

Il n'y en a pas, et je n'ai pas pu en ajouter : le jeton `gh` de cette machine n'a pas le droit `workflow`. Pour en avoir
une : `gh auth refresh -s workflow`, puis ajouter un fichier `.github/workflows/tests.yml` qui lance `pytest tests`.
