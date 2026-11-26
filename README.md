# Strategy V11

Robot de trading intrajournalier sur la cassure de l'ouverture de New York, pour le **Nasdaq 100** et le **S&P 500**.

| Version | Fichier | Rôle |
|---|---|---|
| MetaTrader 5 | `robot/Strategy-V11.mq5` | L'Expert Advisor. Version de référence : il voit le bid et l'ask et passe les ordres. |
| TradingView | `robot/Strategy-V11.pine` | Le même jeu de règles en Pine v6, avec alertes et calcul du lot à passer chez le courtier. |
| Étrave | `etrave/` | Page web locale qui règle et surveille l'EA : séance du jour, risque, Telegram, clôture, lancement de MetaTrader. |

État au 26 novembre 2026 : la V11 (la V10 avec le stop des continuations D au prix d'entrée de la cassure A, plus les corrections
d'un audit d'exécution) compile sans erreur ni avertissement et a tourné de janvier 2025 à novembre 2026 dans le testeur de
MetaTrader, sur le Nasdaq et le S&P 500. Elle n'a pas encore tourné en démo ni en réel. Toutes les heures sont celles de New York (9:30 à New York = 15:30 à Paris la plupart de l'année).
Ce dépôt n'est pas un conseil en investissement.

## Sommaire

- [Les règles](#les-règles)
- [Ce que disent les tests](#ce-que-disent-les-tests)
- [Installer l'EA dans MetaTrader 5](#installer-lea-dans-metatrader-5)
- [Utiliser le script TradingView](#utiliser-le-script-tradingview)
- [Étrave, l'interface de l'EA](#étrave-linterface-de-lea)
- [Surveiller le robot](#surveiller-le-robot)
- [Limites connues](#limites-connues)
- [Organisation du dépôt](#organisation-du-dépôt)

## Les règles

Les règles sont fixées dans le code, à l'identique dans l'EA et dans le script : toutes les entrées, stop à 3 ranges, pyramide,
mémoire, et stop des continuations D au prix d'entrée de A (V11). La V10 était la configuration la plus rentable des deux marchés
réunis ; la V11 gagne environ 15 % de moins avec une pire baisse environ 30 % plus faible (choix du 26 novembre 2026). Restent réglables : le risque ou les lots
fixes, le numéro magique, les notifications et l'affichage. L'heure du serveur et les jours de la Fed se trouvent seuls (voir plus
bas). Changer une règle
demande de modifier le code et de recompiler.

**Cassure (A)**
1. **Range** : plus haut et plus bas de la bougie M5 de 9:30.
2. **Filtres** : l'achat est permis si le RSI 14 M5 de cette bougie dépasse 50 et si son plus haut atteint ou dépasse celui de
   9:00-9:30. La vente suit la règle inverse. Si aucun côté n'est permis, pas de trade.
3. **Ordres** : à 9:35, achat stop sur le haut et vente stop sur le bas, valables jusqu'à 9:45. Le premier exécuté annule l'autre.
4. **Stop** : 3 ranges au-delà du niveau de cassure. La taille est divisée par 3, donc la somme risquée (1 R) ne change pas.
5. **Gestion** : stop au prix d'entrée dès +1,5 R. Quand une bougie clôture à +2 R, ajout de 2 unités (pyramide) et stop de
   l'ensemble à 1 R sous le prix de l'ajout. Sortie à 15:50.
6. **Mémoire** : après une cassure qui finit au-delà de +1 R, le signal suivant n'est pas pris.

**Entrées supplémentaires**, seulement les jours où la cassure est prise, et dans son sens :
- **B, repli sur le VWAP** : la première bougie M5 qui revient toucher le prix moyen de la séance (à 0,1 range près) puis clôture du
  bon côté. Entrée au marché, jusqu'à 14:00. Stop au-delà de l'extrême des 2 dernières bougies M5 (marge de 0,5 pb du prix), écart
  multiplié par 3.
- **D1, D2, D3, continuations** : à la clôture des bougies de 9:35, 9:40 et 9:45, le dépassement de l'extrême de la bougie est guetté
  pendant 10 minutes. L'EA surveille ce niveau et entre au marché ; aucun ordre n'apparaît chez le courtier. Elles ne sont armées que
  tant que la cassure est ouverte et que l'autre bord du range n'a pas été touché depuis. **V11 : le stop d'une D est le prix
  d'entrée de la cassure A.** Une bougie dont l'extrême n'est pas au-delà de l'entrée de A (d'au moins un spread) ne donne pas de D.
  La taille et le R d'une D se calculent encore sur le stop de la V10 (l'autre extrême de la bougie, écart multiplié par 3).
- B et D suivent la gestion de A, chacune dans son propre R (stop à l'entrée à +1,5 R, pyramide à +2 R avec un stop d'au moins
  +1 R), et ne risquent jamais plus que la cassure. Elles restent ouvertes si la cassure sort avant elles. Jusqu'à 5 positions
  peuvent être ouvertes ensemble, toutes dans le même sens.

**Jours sans trade** : décisions de la Fed (FOMC, codées jusqu'au 26 janvier 2028, puis lues dans le calendrier économique de
MetaTrader), jours fériés américains et demi-séances. Aucun
ordre non plus si le spread plus deux glissements pèse plus de 25 % du risque du jour.

**Taille** : 0,25 % du solde par trade par défaut. Sur un petit compte, le lot minimum du courtier dépasse ce risque : le réglage
« Lots fixes pour la cassure » (`InpFixedLots`) impose alors la taille, par exemple 0,1 lot sur 1 000 $. Le risque en % suit alors la
largeur du stop. B et D ne prennent jamais plus de lots ni plus de risque que la cassure : en lots fixes, une entrée B ou D dont le
stop est plus large que celui de la cassure est sautée.

## Ce que disent les tests

Ces chiffres viennent de données déjà vues pendant la mise au point : ils disent ce que les règles auraient fait, pas ce qu'elles
feront.

| Test | Résultat |
|---|---|
| Nasdaq 2018-2026, spread réel + 1 point de glissement | +477 R, 47 % de trades gagnants, pire baisse −32 R, pire journée −5,1 R |
| Nasdaq 2010-2017, coûts au poids d'aujourd'hui | +194 R, 44 % de trades gagnants, pire baisse −53 R ; avec les coûts au poids de 2018, +23 R seulement |
| V10, Nasdaq + S&P 500, 2019-2026, 0,1 lot sur 1 000 $, historique ramené aux prix d'aujourd'hui | environ +9 200 $, 43 % de trades gagnants, pire journée −322 $, pire baisse −643 $ |
| Testeur MetaTrader, NDX100, 20/11/2025 → 19/11/2026, 0,1 lot sur 1 000 $ (V10) | +1 885 $, 379 trades, 53 % de jours gagnants, pire jour −91 $, pire baisse −321 $ |
| **V11**, testeur MetaTrader, NDX100 + SPX500, 01/01/2025 → 25/11/2026, 0,1 lot (deux passages de 10 000 $ additionnés) | **+3 405 $, 45 % de jours gagnants, pire jour −101 $, pire baisse −248 $** (V10 : +3 951 $, 47 %, −110 $, −360 $) |
| V11, simulateur, Nasdaq + S&P 500, 2019 → 25/11/2026, 0,1 lot, prix du courtier à chaque date (pas ramenés à aujourd'hui) | +5 343 $, 42 % de jours gagnants, pire jour −101 $, pire baisse −252 $ (V10 : +6 414 $, 42 %, −126 $, −360 $) |

- La ligne V10 du testeur est une bonne année (+76 R, contre environ +51 R pour une année médiane).
- La V11 gagne environ 15 % de moins que la V10 et sa pire baisse est environ 30 % plus faible : à 0,1 lot, le stop « 3 ranges »
  ne peut pas être compensé par des lots divisés par 3, et le stop des D à l'entrée de A limite la perte des jours qui se retournent.
  Le testeur et le simulateur concordent (Nasdaq : +2 991 $ contre +3 016 $, même signe 99 % des jours ; S&P : le simulateur est
  plus prudent, +309 $ contre +414 $).
- Le glissement réel compte beaucoup : avec 3 points par exécution au lieu de 1, le gain baisse d'environ 37 % et la pire baisse double.
- Le S&P 500 a été testé avec ces règles (prix du courtier 2019-2026, données déjà vues, et 12 mois dans le testeur) : il gagne
  nettement moins que le Nasdaq et dépend davantage des coûts. Le Dow Jones est exclu : testé tel quel, il ne gagne rien.
- Le capital peut stagner longtemps : jusqu'à 20 mois sans nouveau plus haut dans les tests 2018-2026.

## Installer et lancer : un double-clic

Une fois MetaTrader 5 installé, **Étrave installe et lance tout**. Elle compile l'EA, pose le profil « Etrave-demo » : deux
graphiques M5, NDX100 et SPX500 (noms de TradinGlobal), la V11 sur chacun, lots fixes à 0. Puis elle ouvre MetaTrader sur ce profil,
trading automatique actif. Le reste se règle dans la page : risque, marchés, Telegram, compte.

**Sur un Mac** (MetaTrader 5 pour Mac) : double-clique sur `etrave/Etrave.command`. MetaTrader s'ouvre avec les deux graphiques,
le Mac reste éveillé tant qu'il tourne, et la page d'Étrave s'ouvre. L'EA est recompilé si le dépôt a changé depuis le dernier
lancement.

**Sur un VPS Windows vierge** :
1. Installe MetaTrader 5 depuis le site de ton courtier et ouvre-le une fois.
2. Installe Python 3 ([python.org](https://www.python.org/downloads/), coche « Add python.exe to PATH »).
3. Récupère le dépôt (`git clone`, ou « Code > Download ZIP » sur GitHub, puis décompresse).
4. Double-clique sur `etrave/Etrave.bat`. Dans l'onglet Connexions, saisis le numéro de compte, le mot de passe et le serveur, puis
   « Lancer MetaTrader 5 et se connecter ». Si MetaTrader est resté ouvert après son installation, ferme-le d'abord avec le bouton
   « Fermer MetaTrader 5 ».
5. Coche « Ouvrir MetaTrader 5 tout seul quand Étrave démarre » et « Lancer Étrave à l'ouverture de la session Windows ». Pour qu'un
   VPS redémarré reparte seul, active aussi l'ouverture de session automatique de Windows.

Ce chemin Windows n'a pas encore été essayé sur un vrai Windows (il est développé et vérifié sur Mac) : au premier lancement,
vérifie que les deux graphiques portent la V11 et que le bouton « Trading algo » est vert.

**À la main** : copie `robot/Strategy-V11.mq5` dans `MQL5\Experts\Etrave`, compile-le dans MetaEditor (F7, « 0 errors »), puis
glisse Strategy-V11 sur le graphique **M5** du Nasdaq et sur celui du S&P 500. Coche « Autoriser le trading algorithmique ». Retire
d'abord tout ancien robot (Strategy-V10 en particulier).

**Heure du serveur** : l'EA la déduit tout seul de l'horloge de l'ordinateur, à l'heure près (heure d'été américaine, comme
TradinGlobal ; avertissement si l'horloge semble décalée de plus de 10 minutes), et le panneau affiche l'heure de New York. Garde l'heure de l'ordinateur en réglage automatique. Les réglages « Décalage GMT du
serveur » et « Heure d'été du serveur » ne servent plus qu'au testeur, ou si tu coupes « Heure du serveur détectée
automatiquement ».

À savoir :
- **Compte « hedging » obligatoire.** Sur un compte « netting », B et D sont coupées.
- **Numéros magiques** : A = 50930, B = +1, D1 à D3 = +3 à +5. Le filet de sécurité de l'EA surveille de 50930 à 50939 : ne fais
  jamais tourner sur le même compte un autre robot qui utilise l'un de ces numéros.
- **Telegram** : dans Outils > Options > Expert Advisors, autorise `https://api.telegram.org` pour WebRequest.
- **Où le faire tourner** : un ordinateur sans mise en veille pour la démo, un VPS Windows pour le réel. MetaTrader doit rester ouvert
  de 9:30 à 15:50.
- **Dates FOMC** : après le 26 janvier 2028, l'EA lit les décisions de la Fed dans le calendrier économique de MetaTrader. Ce
  calendrier a les mêmes dates que la liste codée pour 2025-2027, sauf le 27/10/2027, qu'il garde alors que la Fed l'a retiré
  (vérifié le 26/11/2026) : il peut donc contenir une date périmée. « Jours FOMC en plus »
  (aaaa.mm.jj, séparés par des virgules) reste là si le calendrier manquait une date. Le testeur n'a pas ce calendrier.
- `robot/mt5/` contient la configuration de la démo (`demo.ini`, qui ouvre le profil `profil-Etrave-demo` : deux graphiques M5, Nasdaq
  et S&P 500, la V11 sur chacun, lots fixes à 0 : la taille vient du risque réglé dans
  Étrave ; `demo_1000.set`, l'ancien réglage à 0,1 lot) et un modèle pour le testeur de stratégie
  (`testeur.ini`).

**Contrôle dans le testeur de stratégie** (Expert `Etrave\Strategy-V11`, M5, « Chaque tick basé sur des ticks réels », compte
hedging, modèle `robot/mt5/testeur.ini` : 0,1 lot, dépôt de 10 000 $ pour ne pas être limité par la marge) : du 01/01/2025 au 25/11/2026 (date de fin 2026.11.26 : MetaTrader l'exclut), la V11
donnait sur NDX100 +2 991 $ sur 237 jours de trade et 48 % de jours gagnants, et sur SPX500 +414 $ sur 221 jours ; le testeur doit
en être proche. Sur une autre période, avec nettement moins de trades, moins de 35 %
de gagnants ou un résultat négatif, ne passe pas en réel.

## Utiliser le script TradingView

1. Ouvre un graphique **M5** du Nasdaq ou du S&P 500, avec les bougies hors séance. Colle `robot/Strategy-V11.pine` dans l'éditeur
   Pine, puis « Ajouter au graphique ». Dans « Propriétés », ajoute une commission égale au spread de ton courtier.
2. Crée une alerte « Appels de la fonction alert() uniquement ». Pour Telegram, webhook
   `https://api.telegram.org/bot<TOKEN>/sendMessage` et ton Chat ID dans les réglages du script. Après chaque mise à jour du script,
   supprime puis recrée l'alerte.
3. Dans « Lots chez le courtier », renseigne la taille de contrat et le solde du compte : le script affiche le lot à saisir.

| Sur le graphique | Ce que ça veut dire | Ce que tu fais |
|---|---|---|
| Rectangle « 9:30 » et tirets « Achat stop » / « Vente stop » | ordres de la cassure A | poser l'ordre stop au prix et au lot indiqués, stop donné dans l'alerte |
| Ligne orange | prix moyen de la séance (VWAP) | rien, c'est le repère de B |
| Étiquette « ACHAT B » ou « VENTE B » | signal B | entrer au marché, stop sur la ligne « SL B » |
| Tirets « D1 stop » | continuation guettée 10 minutes | poser un ordre stop à ce prix, dans le sens de la cassure |
| Alerte « D1 ANNULÉE » | délai passé, ou niveau d'annulation (dans l'alerte « GUETTÉE ») touché d'abord | supprimer l'ordre stop de cette D |
| Ligne pointillée grise, alerte « stop déplacé au prix d'entrée » | +1,5 R atteint | remonter le stop au prix d'entrée |
| Étiquette « + » | pyramide | ajouter 2 fois la taille de départ (lot donné dans l'alerte), remonter le stop |
| Alerte « FIN DE JOURNÉE » | 15:50 | fermer toutes les positions au marché |
| « ⏸ mémoire », « ⏸ FOMC », « ⏸ férié » | pas de trade aujourd'hui | rien |

TradingView ne voit que des bougies (5 minutes, et 1 minute pour le VWAP) et ne compte pas le spread : ses résultats sont un peu plus
beaux que ceux de l'EA, qui reste la référence. Le lot affiché ne connaît pas le minimum de ton courtier : sous ce minimum, n'entre
pas (l'EA saute alors l'entrée).

## Étrave, l'interface de l'EA

1. Installe Python 3 ([python.org](https://www.python.org/downloads/), coche « Add python.exe to PATH »). Rien d'autre n'est nécessaire.
2. Double-clique sur `etrave/Etrave.bat` (Windows) ou `etrave/Etrave.command` (Mac) : MetaTrader s'ouvre s'il est fermé (voir plus
   haut), puis la page sur `http://127.0.0.1:8788`. Ailleurs : `python etrave/etrave.py`.

| Onglet | Contenu |
|---|---|
| Séance | La frise du jour (range, cassure, entrées D, repli B, sortie) avec l'heure de New York, une ligne par marché (ce que fait l'EA, résultat ouvert, bouton « Clôturer »), les chiffres du compte, la courbe, la liste des trades et les exports trimestriels. Une case par marché arrête les nouveaux trades. |
| Risque | Risque par trade (de 0,05 % à 20 % ; au-delà de 1 %, il faut taper RISQUE) et levier du courtier. La simulation rejoue la V11 sur le Nasdaq et le S&P 500 (données du courtier 2019-2026, toutes les entrées) : gain par an, pire baisse, pire série et pire journée à ce risque. |
| Connexions | Telegram, connexion à un compte MetaTrader, installation de l'EA et des deux graphiques, ouverture et fermeture de MetaTrader, lancement automatique. |

L'interface et l'EA se parlent par des fichiers du dossier commun de MetaTrader (`…\MetaQuotes\Terminal\Common\Files\Etrave` ;
sur Mac, le même dossier dans le Wine de MetaTrader 5 pour Mac).
L'interface ne passe aucun ordre : la fermer ne change rien à l'EA. Elle n'écoute que sur 127.0.0.1, avec un jeton tiré au hasard à
chaque lancement ; n'ouvre jamais son port sur internet.

## Surveiller le robot

**Journaux et export trimestriel.** En plus du journal des trades, l'EA écrit dans le dossier d'Étrave :
- `execution-<symbole>.csv` : une ligne par position fermée (A, ajout de pyramide, B, D) avec le prix visé et le prix obtenu (le
  glissement réel), le spread, le stop en place et le prix de sortie, le plus grand gain et la plus grande perte latents avant la
  sortie, les frais et le résultat ;
- `seances-<symbole>.csv` : ce que l'EA a décidé à 9:35 et l'état du jour après la sortie, qu'il y ait eu un trade ou non.

Après chaque trimestre (dates de New York), Étrave écrit tout seul `exports/<trimestre>/` : les lignes du trimestre, un résumé
(`resume.md`, et `resume.json` pour l'analyse), la description des colonnes, le rapprochement avec le journal des trades et l'état
de l'interrupteur, marché par marché (ses seuils ont été calculés pour un marché). Le bouton « Exporter le trimestre en cours » le fait à la demande. Dans le testeur de stratégie, les journaux vont
dans le sous-dossier `testeur\` et ne sont jamais exportés.

Sur 60 jours de trade, coupe le robot et fais le point si l'un de ces seuils est franchi : moins de 28 % de jours gagnants, un total
pire que −40 R, ou une baisse de plus de 66 R depuis le dernier plus haut. Ces seuils ont été calculés pour toutes les entrées à
0,25 % ; ils ne sont pas codés dans le robot. En lots fixes sur 1 000 $, 1 R vaut environ 25 à 30 $ : −40 R serait le compte entier.

## Limites connues

- **Glissement** : les tests supposent 1 point par exécution. Relève le glissement que l'EA annonce dans le message « exécuté ». Le
  journal d'exécution le mesure aussi pour la sortie de 15:50 (depuis la version 2 du journal, V11).
- **Petit compte** : à 0,1 lot, une D dont le stop de la V10 est plus large que celui de la cassure est sautée (environ 1 D sur 4
  dans le testeur 2025-2026), même si son stop réel, l'entrée de A, serait plus proche. C'est la règle testée ; la changer
  demande un nouveau test. Avec environ 1 000 $, vérifie aussi que la marge libre suffit : l'EA réserve la marge de 15 unités
  (cassure, B, D et leurs ajouts) et ne prend pas le trade sinon.
- **Notifications** : les messages Telegram et WhatsApp attendent pendant qu'une D est guettée ou qu'un côté de la cassure est
  surveillé par l'EA (un envoi bloque l'EA jusqu'à 3 secondes).
- **EA en marche obligatoire** : sorties, stop au prix d'entrée et filet de sécurité ne fonctionnent que si l'EA tourne, d'où le VPS.
- **Ordres en attente** : ne supprime pas à la main les ordres stop de l'EA ; 10 secondes après leur disparition, il renonce au trade.
- **EA lancé en retard** : après 9:35, si le prix a déjà franchi le niveau, l'EA entre au marché, avec plus de glissement, et renonce si
  le risque réel dépasserait 1,25 R.
- **Heure du serveur** : détectée par l'EA à partir de l'horloge de l'ordinateur. Une horloge ou un fuseau faux décalerait le range :
  laisse l'ordinateur régler son heure tout seul. Le panneau affiche l'heure de New York à vérifier.
- **Un seul MetaTrader avec l'EA par ordinateur** : deux terminaux partagent les réglages d'Étrave, et un « Clôturer » fermerait les deux.
- **Fermetures exceptionnelles** de la Bourse (deuil national, panne) : absentes du calendrier, la position passerait la fermeture.
- **Arrêt brutal** : après un plantage, un ordre stop peut rester chez le courtier jusqu'à son expiration (9:45, ou la fin de la
  journée selon le courtier).
- **Étrave sous Windows** : le lancement de MetaTrader, l'installation de l'EA depuis la page et le démarrage avec Windows n'ont pas
  encore été essayés sous Windows.

## Organisation du dépôt

```
robot/
  Strategy-V11.mq5     Expert Advisor MetaTrader 5
  Strategy-V11.pine    script TradingView
  test_robot.py        contrôles du code de l'EA et du script
  mt5/                 configuration de la démo et modèle du testeur de stratégie
etrave/
  etrave.py            serveur local de l'interface (Python, sans dépendance)
  page.html            la page
  export.py            export trimestriel des journaux de l'EA
  pont.py, mt5.py, risque.py, telegram.py
  test_interface.py, test_export.py   tests de l'interface, de l'export et de leur accord avec l'EA
CLAUDE.md              consignes de travail sur ce dépôt
```

Tests, à la racine du dépôt : `python -m pytest robot etrave`. Ils relisent le code de l'EA et du script (ce ne sont pas des tests de
compilation) et vérifient l'accord entre Étrave et l'EA : fichiers, clés, bornes, heures des règles, calendrier des jours fériés.
