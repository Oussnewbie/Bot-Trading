# Strategy V10

Robot de trading intrajournalier sur la cassure de l'ouverture de New York, pour le **Nasdaq 100** et le **S&P 500**.

| Version | Fichier | Rôle |
|---|---|---|
| MetaTrader 5 | `robot/Strategy-V10.mq5` | L'Expert Advisor. Version de référence : il voit le bid et l'ask et passe les ordres. |
| TradingView | `robot/Strategy-V10.pine` | Le même jeu de règles en Pine v6, avec alertes et calcul du lot à passer chez le courtier. |
| Étrave | `etrave/` | Page web locale qui règle et surveille l'EA : séance du jour, risque, Telegram, clôture, lancement de MetaTrader. |

État au 25 novembre 2026 : l'EA compile sans erreur ni avertissement et a tourné 12 mois dans le testeur de MetaTrader. Il n'a pas
encore tourné en démo ni en réel. Toutes les heures sont celles de New York (9:30 à New York = 15:30 à Paris la plupart de l'année).
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
mémoire. C'est la configuration la plus rentable des deux marchés réunis dans les tests. Restent réglables : le risque ou les lots
fixes, l'heure du serveur, les dates FOMC après janvier 2028, le numéro magique, les notifications et l'affichage. Changer une règle
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
  tant que la cassure est ouverte et que l'autre bord du range n'a pas été touché depuis. Stop à l'autre extrême de la bougie, écart
  multiplié par 3.
- B et D suivent la gestion de A, chacune dans son propre R (stop à l'entrée à +1,5 R, pyramide à +2 R avec un stop d'au moins
  +1 R), et ne risquent jamais plus de 1 R chacune. Elles restent ouvertes si la cassure sort avant elles. Jusqu'à 5 positions peuvent
  être ouvertes ensemble, toutes dans le même sens.

**Jours sans trade** : décisions de la Fed (FOMC, codées jusqu'au 26 janvier 2028), jours fériés américains et demi-séances. Aucun
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
| Nasdaq + S&P 500, 2019-2026, 0,1 lot sur 1 000 $, prix d'aujourd'hui | environ +9 200 $, 43 % de trades gagnants, pire journée −322 $, pire baisse −643 $ |
| Testeur MetaTrader, NDX100, 20/11/2025 → 19/11/2026, 0,1 lot sur 1 000 $ | +1 885 $, 379 trades, 53 % de jours gagnants, pire jour −91 $, pire baisse −321 $ |

- La dernière ligne est une bonne année (+76 R, contre environ +51 R pour une année médiane).
- Le glissement réel compte beaucoup : avec 3 points par exécution au lieu de 1, le gain baisse d'environ 37 % et la pire baisse double.
- Le S&P 500 gagne nettement moins que le Nasdaq et dépend davantage des coûts : sur les 12 mois du testeur, à 0,25 %, environ
  +47 R contre environ +84 R pour le Nasdaq (avant le correctif X-13). Le Dow Jones est exclu : testé tel quel, il ne gagne rien.
- Le capital peut stagner longtemps : jusqu'à 20 mois sans nouveau plus haut dans les tests 2018-2026.

## Installer l'EA dans MetaTrader 5

1. Hors séance et sans trade ouvert, retire tout ancien robot du graphique.
2. Copie `robot/Strategy-V10.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor et compile (F7) : tu dois lire « 0 errors ».
   Le bouton « Installer ou mettre à jour l'EA » d'Étrave fait la même chose.
3. Glisse Strategy-V10 sur le graphique **M5** du Nasdaq (NDX100 chez TradinGlobal) et sur celui du S&P 500 (SPX500), avec les mêmes
   réglages, et coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau. Si elle est fausse, corrige « Décalage GMT du serveur » et « Heure d'été du
   serveur ».

À savoir :
- **Compte « hedging » obligatoire.** Sur un compte « netting », B et D sont coupées.
- **Numéros magiques** : A = 50930, B = +1, D1 à D3 = +3 à +5. Le filet de sécurité de l'EA surveille de 50930 à 50939 : ne fais
  jamais tourner sur le même compte un autre robot qui utilise l'un de ces numéros.
- **Telegram** : dans Outils > Options > Expert Advisors, autorise `https://api.telegram.org` pour WebRequest.
- **Où le faire tourner** : un ordinateur sans mise en veille pour la démo, un VPS Windows pour le réel. MetaTrader doit rester ouvert
  de 9:30 à 15:50.
- **Dates FOMC** : après le 26 janvier 2028, saisis les jours de décision dans « Jours FOMC en plus » (format aaaa.mm.jj, séparés par
  des virgules) dès que la Fed les publie. Sinon le robot trade ces jours-là.
- `robot/mt5/` contient la configuration de la démo (`demo.ini`, `demo_1000.set`) et un modèle pour le testeur de stratégie
  (`testeur.ini`).

**Contrôle dans le testeur de stratégie** (Expert `Etrave\Strategy-V10`, M5, « Chaque tick basé sur des ticks réels », compte
hedging, modèle `robot/mt5/testeur.ini`) : du 20/11/2025 au 19/11/2026, la simulation donnait environ 410 trades sur 122 jours de
trade, 54 % de gagnants et +76 R (sur les prix du courtier : 413 trades sur 123 jours, les mêmes jours que le testeur) ; le testeur
doit en être proche. Sur une autre période, avec nettement moins de trades, moins de 35 %
de gagnants ou un résultat négatif, ne passe pas en réel.

## Utiliser le script TradingView

1. Ouvre un graphique **M5** du Nasdaq ou du S&P 500, avec les bougies hors séance. Colle `robot/Strategy-V10.pine` dans l'éditeur
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
2. Double-clique sur `etrave/Etrave.bat`. La page s'ouvre sur `http://127.0.0.1:8788` (ailleurs que sous Windows :
   `python etrave/etrave.py`).

| Onglet | Contenu |
|---|---|
| Séance | La frise du jour (range, cassure, entrées D, repli B, sortie) avec l'heure de New York, une ligne par marché (ce que fait l'EA, résultat ouvert, bouton « Clôturer »), les chiffres du compte, la courbe, la liste des trades et les exports trimestriels. Une case par marché arrête les nouveaux trades. |
| Risque | Risque par trade (de 0,05 % à 20 % ; au-delà de 1 %, il faut taper RISQUE) et levier du courtier. La simulation rejoue encore les trades de l'ancienne ORB v6. |
| Connexions | Telegram, connexion à un compte MetaTrader, installation de l'EA, lancement automatique. |

L'interface et l'EA se parlent par des fichiers du dossier commun de MetaTrader (`…\MetaQuotes\Terminal\Common\Files\Etrave`).
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
de l'interrupteur. Le bouton « Exporter le trimestre en cours » le fait à la demande. Dans le testeur de stratégie, les journaux vont
dans le sous-dossier `testeur\` et ne sont jamais exportés.

Sur 60 jours de trade, coupe le robot et fais le point si l'un de ces seuils est franchi : moins de 28 % de jours gagnants, un total
pire que −40 R, ou une baisse de plus de 66 R depuis le dernier plus haut. Ces seuils ont été calculés pour toutes les entrées à
0,25 % ; ils ne sont pas codés dans le robot. En lots fixes sur 1 000 $, 1 R vaut environ 25 à 30 $ : −40 R serait le compte entier.

## Limites connues

- **Glissement** : les tests supposent 1 point par exécution. Relève le glissement que l'EA annonce dans le message « exécuté ».
- **EA en marche obligatoire** : sorties, stop au prix d'entrée et filet de sécurité ne fonctionnent que si l'EA tourne, d'où le VPS.
- **Ordres en attente** : ne supprime pas à la main les ordres stop de l'EA ; 10 secondes après leur disparition, il renonce au trade.
- **EA lancé en retard** : après 9:35, si le prix a déjà franchi le niveau, l'EA entre au marché, avec plus de glissement, et renonce si
  le risque réel dépasserait 1,25 R.
- **Heure du serveur** : si elle ne correspond plus aux réglages, l'EA ne pose aucun ordre ce jour-là et le signale.
- **Un seul MetaTrader avec l'EA par ordinateur** : deux terminaux partagent les réglages d'Étrave, et un « Clôturer » fermerait les deux.
- **Fermetures exceptionnelles** de la Bourse (deuil national, panne) : absentes du calendrier, la position passerait la fermeture.
- **Arrêt brutal** : après un plantage, un ordre stop peut rester chez le courtier jusqu'à son expiration (9:45, ou la fin de la
  journée selon le courtier).
- **Étrave sous Windows** : le lancement de MetaTrader, l'installation de l'EA depuis la page et le démarrage avec Windows n'ont pas
  encore été essayés sous Windows.

## Organisation du dépôt

```
robot/
  Strategy-V10.mq5     Expert Advisor MetaTrader 5
  Strategy-V10.pine    script TradingView
  test_robot.py        contrôles du code de l'EA et du script
  mt5/                 configuration de la démo et modèle du testeur de stratégie
etrave/
  etrave.py            serveur local de l'interface (Python, sans dépendance)
  page.html            la page
  export.py            export trimestriel des journaux de l'EA
  pont.py, mt5.py, risque.py, telegram.py
  test_interface.py, test_export.py   tests de l'interface, de l'export et de leur accord avec l'EA
video/                 vidéos TikTok en motion design : récap de chaque séance et présentation (voir video/README.md)
CLAUDE.md              consignes de travail sur ce dépôt
```

Tests, à la racine du dépôt : `python -m pytest robot etrave video`. Ils relisent le code de l'EA et du script (ce ne sont pas des tests de
compilation) et vérifient l'accord entre Étrave et l'EA : fichiers, clés, bornes, heures des règles, calendrier des jours fériés.
