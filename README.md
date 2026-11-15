# Bot-Trading — stratégie ORB v5 (TradingView Pine v6 et MetaTrader 5)

Cassure du range d'ouverture de New York (ORB 5 minutes) sur le Nasdaq (NAS100), graphique M5,
seulement dans le sens de l'élan de l'ouverture, avec une pyramide sur les journées de tendance.
Toutes les heures sont en heure de New York (9:30 NY = 15:30 à Paris la plupart de l'année).

## Contenu

| Fichier | Rôle |
|---|---|
| `pine/ORB-v5.pine` | **La stratégie** pour TradingView. Alertes Telegram. |
| `mt5/ORB-v5.mq5` | **La même stratégie en Expert Advisor MetaTrader 5**, mêmes règles et mêmes paramètres. Notifications push MT5, WhatsApp et Telegram. |
| `interface/`, `Etrave.bat` | **Étrave, l'interface de l'EA** : une page web locale pour régler le risque, cocher les instruments, brancher Telegram, suivre et clôturer les trades. Voir [L'interface Étrave](#linterface-étrave). |
| `backtest/or/v5_sur_or.py` | La v5 appliquée telle quelle à l'or : elle y perd (-137R sur 2018-2026). |
| `backtest/multi/` | **La recherche du 15 novembre 2026 sur le Dow Jones, l'or, l'EUR/USD et le bitcoin** : 8 708 variantes, rien ne passe hors du Nasdaq. Voir [RAPPORT.md](backtest/multi/RAPPORT.md). |
| `backtest/nas100-10ans/` | Le simulateur Python : `v5_lab.py` (simulateur), `orb_v5.py` (les réglages de la v5 et ses tableaux), `load10.py` (lecture des données). |
| `backtest/etude-sl/` | L'étude en cours sur les stops (novembre 2026) : scripts numérotés, rapports dans `sorties/`, `refaire.sh` pour tout refaire. |
| `tests/` | Les tests automatiques du simulateur (`pytest`), dont une réécriture indépendante des règles (`regles_readme.py`). |
| `donnees/` | Données Dukascopy **M1, bid et ask, du 2018-01-01 au 2026-11-13** : Nasdaq CFD (`nas100/`), or (`or/`), EUR/USD (`eurusd/`), Dow Jones CFD (`dow/`) et bitcoin (`bitcoin/`), un zip par année. Voir [donnees/LISEZMOI.md](donnees/LISEZMOI.md). |
| `AUDIT.md` | L'audit du 14 novembre 2026, fait sur l'ancien jeu de données 2015-2026. |

Le dépôt a été nettoyé le 14 novembre 2026 : les versions précédentes (AMD+ v1 et v2, ORB v3 et v4), les scripts
d'expérience `v5_exp1.py` à `v5_exp10.py`, `v5_recent.py` et l'ancien fichier M5 2015-2026 ont été retirés. Ils restent
dans l'historique git (dernier commit qui les contient : `2c0c65c`).

## À lire avant tout : ce que le test dit vraiment

La v5 a été choisie sur mai 2018 → août 2022, puis vérifiée sur septembre 2022 → novembre 2026.
« Sans pyramide » = les mêmes règles sans la règle 7 (l'ancienne v4). Données du dépôt, glissement de 0,1 point.

| Période | | Trades | Par trade | Total | Pire baisse |
|---|---|---|---|---|---|
| 2018-01 → 2018-04 (avant la période de choix) | sans pyramide | 50 | +0,18R | +9R | -9R |
| | **v5** | 50 | +0,46R | **+23R** | -9R |
| 2018-05 → 2022-08 (période de choix) | sans pyramide | 724 | +0,21R | +152R | -23R |
| | **v5** | 724 | +0,34R | **+249R** | -22R |
| 2022-09 → 2026-11 (vérification) | sans pyramide | 653 | +0,18R | +120R | -27R |
| | **v5** | 653 | +0,25R | **+166R** | -25R |
| **Tout : 2018 → 2026-11** (8,9 ans) | sans pyramide | 1 427 | +0,20R | +281R | -27R |
| | **v5** | 1 427 | **+0,31R** | **+438R** | -25R |

**Ce tableau ne montre que les bonnes années.** Avant 2018 l'ORB perdait, et ces années ne sont plus dans le dépôt :

| Période (données retirées le 14 novembre 2026) | Trades | Par trade | Total | Pire baisse |
|---|---|---|---|---|
| 2013-05 → 2014 (regardée pour la première fois en novembre 2026) | 231 | -0,14R | -33R | -53R, 26 pertes de suite |
| 2015 → 2017 | 505 | -0,11R | -55R | -74R |
| Tout l'ancien test : 2015-01 → 2026-10 | 1 925 | +0,19R | +372R | **-74R** |

- **L'ORB a perdu de mi-2013 à 2017** (2013 -11R, 2014 -23R, 2015 -44R, 2016 -4R, 2017 -7R). Le spread coûtait alors
  10 à 32 % du risque à chaque trade (range de 8 à 10 points pour 1 à 2 points de spread ; 1 à 6 % depuis 2018), mais ce
  n'est pas tout : même sans spread, l'avantage de 2015-2017 n'était que de +0,04R à +0,07R par trade.
- **La pyramide ajoute du gain sur toutes les périodes** (+14R, +97R, +46R ici ; +21R sur 2015-2018), avec et sans les
  filtres. Elle ne réduit pas les pertes : les stops de départ sont les mêmes.
- R par année : 2018 +93, 2019 +36, 2020 +45, 2021 +49, 2022 +51, 2023 +62, 2024 +24, 2025 +42, 2026 +37.
  161 trades par an, soit environ un jour de bourse sur 1,6. 58 % de stops pleins. Pire série : 13 pertes.
- Capital, intérêts composés, 2018 → 2026-11 :

  | Risque par trade | Par an | Pire baisse 2018-2026 | Pire baisse de l'ancien test 2015-2026 |
  |---|---|---|---|
  | 0,25 % | +13 % | -6 % | -17 % |
  | 0,5 % | +26 % | -12 % | -32 % |
  | 1 % | +55 % | -23 % | -56 % |

- **Le résultat dépend du glissement.** Avec 0,5 point par exécution au lieu de 0,1, le total 2018 → 2026 passe de +438R
  à +385R ; avec 1 point, à +304R.
- **Attends-toi à +0,2 à +0,3R par trade tant que le marché ressemble à 2018-2026, avec une baisse de 25R déjà vue dans
  cette période et de 74R dans la précédente** (trois ans et demi sans nouveau sommet, de janvier 2015 à juillet 2018).
  Fais tourner la v5 en démo avant le réel, et choisis le risque par trade en regardant la pire baisse, pas le retour.

Le détail des années retirées (données, qualité, résultats) est dans
[backtest/etude-sl/sorties/historique-2011-2026/](backtest/etude-sl/sorties/historique-2011-2026/).

## Les règles de la v5

1. **Range** : high et low de la bougie M5 de 9:30.
2. **Filtres** (à 9:35, avant de poser les ordres) :
   - **RSI14 M5** de la bougie de 9:30 : au-dessus de 50, achat seulement ; en dessous, vente seulement.
   - **Élan de l'ouverture** : achat permis seulement si le high de la bougie de 9:30 dépasse le plus haut de
     9:00-9:30 ; vente seulement si son low passe sous le plus bas de 9:00-9:30.
   - Un côté n'est tradé que s'il passe les deux filtres. Aucun côté : pas de trade ce jour-là.
3. **Ordres** : achat stop sur le high et/ou vente stop sur le low, valables 2 bougies (jusqu'à 9:45).
   Le premier exécuté annule l'autre. Si un seul côté est permis et que l'autre côté du range est touché
   d'abord, l'ordre est annulé.
4. **Stop** de l'autre côté du range. **1R** = la somme perdue si le stop est touché (taille de départ × range).
5. **Stop au prix d'entrée** dès +1,5R, décidé à la clôture d'une bougie après celle de l'entrée.
6. **Sortie** à 15:50 (clôture de la bougie de 15:45). Pas d'objectif. Un seul trade par jour.
7. **Pyramide** : quand une bougie M5 clôture à +2R ou plus (bougie d'entrée comprise, sauf la dernière de la
   journée), on ajoute une unité au marché, de la même taille que la position de départ, et le stop de l'ensemble
   monte à 1R sous le prix de l'ajout (donc au moins à +1R). Un seul ajout par trade. Après l'ajout, le pire cas est
   zéro : l'ajout perd 1R, la première unité gagne au moins 1R. Sur 2018-2026 la pyramide se déclenche sur 26 % des
   trades ; la moitié sont ensuite stoppés au stop remonté et finissent un peu au-dessus de zéro (+0,3R en moyenne), les
   autres font les grosses journées (meilleur trade +23R, contre +13R sans pyramide).

Le **R** affiché = résultat net de tout le trade (ajout et commission compris) ÷ somme risquée au départ : le même
chiffre que le testeur. Une sortie au prix d'entrée compte comme neutre dans la série de pertes.

## Utiliser la v5 dans TradingView

1. Dans TradingView, ouvre l'éditeur Pine, crée un nouveau script, colle le contenu de `pine/ORB-v5.pine` et enregistre.
2. Ajoute-le sur un graphique **M5** du NAS100, avec les bougies hors séance (le filtre d'élan a besoin de 9:00-9:30).
3. Dans « Propriétés », ajoute une commission égale au spread de ton broker : le testeur de TradingView ne compte pas
   le spread d'un CFD. Le R affiché par le script en tient compte.
4. Alertes Telegram : une alerte sur la stratégie, condition « Uniquement les appels de la fonction alert() », webhook
   `https://api.telegram.org/bot<TOKEN>/sendMessage` (plan TradingView payant nécessaire, Essential suffit).
   Après chaque changement de réglage ou de version, supprime et recrée l'alerte.

Ce que tu vois sur le graphique :
- à 9:35, la fenêtre de l'élan (9:00-9:30, cadre bleu pointillé), le range de 9:30 (boîte grise avec sa taille)
  et l'ordre permis en tirets ; le côté bloqué par un filtre est en pointillés gris, avec la raison ;
- à l'exécution : l'entrée (trait épais), le stop (rouge), le niveau de +1,5R (pointillés gris), une zone rouge
  de l'entrée au stop et une zone verte jusqu'au meilleur prix atteint, avec le résultat en R en direct ;
  à +1,5R, le stop devient gris au prix d'entrée et la zone rouge s'arrête ;
- à la pyramide : un « + » sur la bougie, une ligne en tirets au prix de l'ajout, et le stop passe en vert, 1R sous l'ajout ;
- à la sortie, tout s'arrête et s'estompe, le résultat en R reste affiché ; un jour sans trade ne laisse rien ;
- en haut à droite, un tableau : range du jour, côtés permis par les filtres, état du jour, historique et pire baisse.

## Utiliser l'EA MetaTrader 5

1. Dans MT5 : Fichier > Ouvrir le dossier des données > `MQL5/Experts`, copie `mt5/ORB-v5.mq5`, ouvre-le dans
   MetaEditor et compile (F7).
2. Glisse l'EA sur un graphique du NAS100 de ton broker (n'importe quel horizon : il lit toujours les bougies M5),
   coche « Autoriser le trading algorithmique ».
3. **Heure du serveur** : la plupart des brokers sont à GMT+2 en hiver avec l'heure d'été américaine (réglages par
   défaut). Le panneau en haut à gauche affiche l'heure de New York calculée : elle doit être juste. Au lancement en
   réel, l'EA compare aussi avec l'heure réelle du serveur et prévient si le réglage est faux.
4. Compte en mode **hedging** conseillé (l'ajout de la pyramide est alors une deuxième position). MT5 doit tourner
   pendant la séance de New York (VPS conseillé) : l'EA gère lui-même l'entrée au niveau du range, la pyramide et la
   sortie de 15:50 ; les stops sont posés chez le broker. Avec la pyramide, la position double : vérifie la marge.
5. Pour comparer avec le test : testeur de stratégie, NAS100, période janvier 2018 → novembre 2026, modèle « Chaque tick
   basé sur des ticks réels », dépôt 10 000. Les données et le spread de ton broker ne sont pas ceux de Dukascopy :
   le résultat sera proche, pas identique.

Différences avec TradingView : l'entrée se fait au tick où l'ask (achat) ou le bid (vente) atteint le niveau, comme
le test Python ; le stop à l'entrée et la pyramide sont décidés à la clôture de la bougie M5, comme dans le test ; si
le broker refuse de poser un stop (trop près du prix), l'EA ferme lui-même la position à ce niveau.

L'en-tête de `pine/ORB-v5.pine` cite encore l'ancien test (1 915 trades, +373R sur 2015-2026) : ce fichier n'a pas été
touché. `mt5/ORB-v5.mq5` a été modifié le 15 novembre 2026 pour l'interface Étrave (version 5.10) **sans pouvoir être
compilé ici** : compile-le dans MetaEditor (F7) et fais-le tourner en démo avant tout.

## L'interface Étrave

Une page web servie sur ton ordinateur (ou ton VPS), au même style que le dashboard de Vigie, en trois onglets :

- **Vue d'ensemble** : solde, trade en cours et résultat cumulé en R, en % et en argent, courbe des trades pris, liste des
  trades, et une ligne par instrument avec sa case à cocher et le bouton « Clôturer le trade ».
- **Risque** : le seul réglage, de 0,05 % à 20 % du solde par trade, avec le levier de ton courtier. Pour la valeur
  choisie, la page rejoue le test : gain par an, pire baisse, série de 13 pertes, et la part des trades que la marge
  aurait obligé à réduire. Au-delà de 1 %, il faut taper le mot RISQUE.
- **Connexions** : Telegram (jeton, « Trouver ma discussion et tester », puis « Essai depuis MetaTrader » qui dit si
  MetaTrader bloque l'adresse), et MetaTrader 5 : connexion à un compte, bouton « Installer ou mettre à jour l'EA »
  (copie dans `MQL5\Experts\Etrave` et compilation, avec les erreurs affichées dans la page), ouverture automatique de
  MetaTrader au démarrage d'Étrave, lancement d'Étrave à l'ouverture de la session Windows.

Chaque bloc de la page se replie d'un clic sur son titre ; seule la courbe reste toujours affichée.

### L'installer

1. Installe Python 3 ([python.org](https://www.python.org/downloads/), coche « Add python.exe to PATH »). Rien d'autre.
2. Double-clique sur `Etrave.bat` : la page s'ouvre sur `http://127.0.0.1:8788`. Sur un autre système :
   `python interface/etrave.py`.
3. Onglet Connexions : « Installer ou mettre à jour l'EA » le copie dans MetaTrader et le compile (ou fais-le à la
   main, voir plus haut). Glisse ensuite l'EA sur le graphique du Nasdaq, une seule fois : MetaTrader s'en souvient.
   Le réglage « Lire le risque, les cases et Telegram dans l'interface Étrave » est coché par défaut.

L'interface peut être fermée à tout moment : l'EA garde ses réglages et continue d'envoyer ses alertes.

### Comment elle parle à l'EA

Par des fichiers texte du dossier commun de MetaTrader (`…\MetaQuotes\Terminal\Common\Files\Etrave`) : la page écrit
`reglages.txt`, l'EA le relit toutes les 2 secondes et écrit son état (`etat-<symbole>.txt`) et ses trades
(`trades-<symbole>.csv`). L'interface ne passe aucun ordre elle-même.

- Un réglage absent du fichier laisse à l'EA la valeur saisie dans MetaTrader. Dans le testeur de stratégie, seuls les
  réglages de MetaTrader comptent.
- Un nouveau risque vaut pour le trade suivant, jamais pour un trade ouvert. L'EA l'annonce sur Telegram.
- **Marge** : l'EA n'ouvre jamais une position (ajout de la pyramide compris) qui demande plus de 90 % de la marge
  libre. Si le risque demandé est trop grand pour le levier, il réduit la taille et le dit dans le message « Ordres
  placés ». Il retient la marge la plus prudente entre celle de MetaTrader et celle du levier saisi dans la page.
- **Instruments** : le même EA, posé sur le graphique de chaque symbole ; il reconnaît le sien à son nom. Cinq cases :
  Nasdaq (cochée), Dow Jones, or, EUR/USD et bitcoin (décochées : aucune stratégie n'y passe les tests, voir
  `backtest/multi/RAPPORT.md` ; en cocher une demande le mot ACTIVER). Une case décochée arrête les nouveaux trades,
  pas le trade en cours.
- **Clôturer** : la demande porte son heure ; l'EA ignore une demande de plus de 2 minutes. Il ferme le trade au
  marché, ou annule les ordres du jour s'il n'est pas encore entré. Pas de nouveau trade ce jour-là.
- **Telegram** : les messages partent de MetaTrader, après le passage des ordres (un envoi lent ne retarde plus
  l'entrée : défaut n° 2 de l'audit). Exemple de clôture :
  `✅ ACHAT CLÔTURÉ : +1,3R · +0,65 % · +65,20 USD` puis la raison, le prix de sortie, le solde et le cumul.
- **Heure du serveur** : l'EA vérifie en continu que ses réglages d'heure correspondent au serveur ; la page affiche une
  alerte rouge si ce n'est plus le cas.

### Sécurité

Comme le dashboard de Vigie : écoute sur 127.0.0.1 uniquement, jeton tiré au hasard à chaque lancement, contrôle de
l'en-tête Host, aucune ressource extérieure. Le jeton Telegram est écrit dans `reglages.txt` et n'est plus jamais
affiché. Le mot de passe du compte MetaTrader n'est écrit que dans un fichier de démarrage provisoire, effacé une minute
après le lancement. Sur un VPS, ouvre la page par le Bureau à distance : n'ouvre jamais le port 8788 sur internet.

### Où faire tourner l'EA

MetaTrader 5 doit rester ouvert de 9:30 à 15:50 New York. Ton ordinateur suffit pour la démo (sans mise en veille) ; pour
le réel, un **VPS Windows** (2 cœurs, 4 Go) avec MetaTrader 5, ce dépôt et Python. Le VPS intégré à MetaTrader n'a pas
d'écran et ne lance aucun autre programme : l'EA y tourne, mais sans l'interface.

### Limites

- L'EA modifié **n'a jamais été compilé ni exécuté** : ni la lecture des réglages, ni l'écriture de l'état, ni le calcul
  de marge, ni les messages n'ont tourné dans MetaTrader. Les tests (`tests/test_interface.py`) couvrent l'interface et
  l'accord des noms de fichiers et de clés entre les deux côtés.
- Le lancement de MetaTrader, la connexion à un compte, l'installation et la compilation de l'EA depuis la page et le
  lancement au démarrage de Windows n'ont jamais été essayés sous Windows : seuls leurs fichiers et leurs refus sont
  testés. La page ne pose pas l'EA sur le graphique à ta place (deux EA sur le même symbole doubleraient les ordres).
- Le journal des trades commence avec cette version : les trades antérieurs ne sont pas repris.
- Le risque est le même pour tous les instruments cochés : deux instruments le même jour, c'est deux fois le risque.
- Les autres défauts de l'EA listés dans [AUDIT.md](AUDIT.md) (séances écourtées, état perdu après un plantage de
  MetaTrader, arrondi des lots…) ne sont pas corrigés.

### Notifications WhatsApp

MetaTrader n'envoie pas de WhatsApp tout seul ; l'EA passe par CallMeBot, un service gratuit pour usage personnel :
1. Sur le site de CallMeBot (rubrique WhatsApp API), récupère le numéro du bot et enregistre-le dans tes contacts.
2. Envoie-lui sur WhatsApp le message indiqué sur le site (« I allow callmebot to send me messages ») : il répond avec
   ta clé API.
3. Dans MT5 : Outils > Options > Expert Advisors, coche « Autoriser WebRequest pour les URL listées » et ajoute
   `https://api.callmebot.com`.
4. Dans les paramètres de l'EA : « WhatsApp via CallMeBot » = true, ton numéro au format international (+33…) et la clé.

Les messages passent par ce service tiers (non officiel). Autres possibilités : les notifications push de
l'appli MetaTrader 5 (gratuites, sans service tiers : copie ton MetaQuotes ID de l'appli mobile dans Outils > Options >
Notifications), ou Telegram (ajoute `https://api.telegram.org` à la même liste, puis le jeton du bot et le chat ID).

## Ce que la recherche a montré

Les scripts de cette recherche ont été retirés du dépôt le 14 novembre 2026 (ils sont dans l'historique git, commit
`2c0c65c`). Ce qu'ils avaient montré, sur mai 2018 → août 2022 seulement, avec et sans les filtres :
- **Taille du stop** (0,5 à 1,5 range, 0,10 à 0,30 ATR jour, range borné) : le range entier reste le meilleur.
- **Entrée** (au-delà du niveau, à la clôture hors du range, sur retour au niveau) : l'ordre stop sur la cassure
  reste le meilleur ; l'entrée sur retour au niveau perd.
- **Gestion** (stop à l'entrée plus tôt ou plus tard, stops suiveurs, objectifs, sorties à 12:00 ou 14:00,
  ré-entrée après un stop) : rien de mieux que le stop à l'entrée dès +1,5R et la sortie à 15:50.
- **Contexte du jour** (gap, veille, NR7, force du RSI, largeur de 9:00-9:30, range contre ATR, coût, jour de la
  semaine… 78 tranches) : une seule dépasse le seuil du hasard, quand on en attend 4 par hasard. Aucun filtre ajouté.
- **Pyramide** : le seul vrai levier. Plateau large (ajout entre +1,5R et +2,5R, stop commun entre +0,5R et +1R).
  Une deuxième pyramide n'apporte rien. Avec un stop fixe à +1R, une pyramide stoppée finissait à -0,35R en moyenne
  (l'ajout se fait à la clôture, souvent au-dessus de +2R) ; avec le stop à 1R sous le prix de l'ajout, elle ne perd
  plus jamais, pour le même total.
- **Entrée en deux temps** (petite taille, complément dès +0,25R) : très bon avec des hypothèses dans la bougie,
  presque nul une fois simulé sans hypothèse (ajout à la clôture). Écarté : c'était un artefact des bougies M5.

Puis vérification hors échantillon : voir les tableaux en haut de page. Les filtres n'ont rien apporté sur 2015-2018
(-52R avec, -53R sans).

### Pourquoi les stops, et pourquoi on ne peut pas les éviter

Autopsie des trades faite avec des bougies M5 sur 2015-2026 (scripts dans l'historique git). L'étude de
`backtest/etude-sl/` la reprend avec des données à la minute :
- Environ 58 % de stops pleins, pour des gagnants qui font +3R en moyenne. 55 % des stops tombent dans les
  15 minutes après l'entrée, 86 % dans la première heure : ce sont des faux départs de l'ouverture.
- 6 % des trades sans filtre touchent les deux côtés du range dans la même bougie : -1R garanti, imprévisible.
- La bougie d'entrée qui reclôture dans le range annonce un stop 72 fois sur 100, mais sortir à cette clôture
  coûte plus (-0,32R) que garder (-0,14R) : les trades qui se retournent rapportent trop. Éviter des stops
  n'est pas gagner plus.
- Structure (plus hauts / plus bas) M15, H1, H4, D1 alignée avec le trade, niveaux de la veille, de la nuit ou de la
  semaine juste devant, grosse journée la veille : aucun effet stable.
- Ce qui aide un peu : trader dans le sens de l'élan de l'ouverture (les deux filtres). Le taux de stops ne baisse
  presque pas ; ce sont les trades à petits gains qui disparaissent.

Deux recherches plus récentes sur les stops (466 variantes, puis 33 règles de stop au prix d'entrée), faites sur l'ancien
jeu de données, sont gardées dans [backtest/etude-sl/archives/](backtest/etude-sl/archives/).

## Refaire les tests

Python 3 avec `pandas` et `numpy` (versions testées dans `requirements.txt`). Les données sont lues directement dans les
zips de `donnees/` : rien à décompresser.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python backtest/nas100-10ans/orb_v5.py     # la v5 sur les trois périodes, avec et sans pyramide, capital
.venv/bin/python -m pytest tests                     # les tests du simulateur
backtest/etude-sl/refaire.sh                         # l'étude sur les stops, du début à la fin
```

Dans les sorties de `orb_v5.py`, « v3 » désigne la stratégie sans filtre ni pyramide et « v4 » les filtres sans pyramide.

Le premier lancement reconstruit le M5 à partir du M1 (une trentaine de secondes) et le garde dans `donnees/cache/`,
hors git. Le simulateur garde aussi un cache (`v5_days.pkl`, `v5_bars.npz`) à côté des scripts ; tout est refait tout
seul dès que les données, `v5_lab.py` ou `load10.py` changent.

### Tests automatiques

- `tests/regles_readme.py` : les règles 1 à 7 réécrites naïvement, jour par jour, sans rien partager avec `v5_lab.py`.
  Les deux donnent les mêmes 1 427 trades sur 2018 → 2026-11, au millionième de R près.
- `tests/test_regles_a_la_main.py` : 13 journées écrites à la main (stop plein, trou à l'ouverture, stop d'une vente
  déclenché par l'ask, stop au prix d'entrée, pyramide, côté bloqué touché d'abord…), résultat calculé sur le papier.
- `tests/test_simulateur.py` : aucune information du futur (on change les bougies d'après 9:35, rien de ce qui précède
  ne bouge), heure d'été, cache, qualité des données, chiffres de référence.

## Audit du 14 novembre 2026

Le détail est dans [AUDIT.md](AUDIT.md). Il a été fait sur l'ancien jeu de données (M5, 2015-2026). L'essentiel :

- Le simulateur applique bien les règles ci-dessus : une réécriture indépendante donnait les mêmes 1 925 trades sur
  2015-2026, et donne les mêmes 1 427 trades sur les données actuelles.
- Deux défauts du simulateur ont été corrigés (cache jamais invalidé, 10 trades de janvier 2015 écartés).
- **Jours fériés américains et demi-séances** : l'EA et le script TradingView gardent la position pendant la fermeture
  du marché. Coupe-les ces jours-là en attendant une correction.
- Le script TradingView n'a pas été modifié. L'EA l'a été le 15 novembre 2026, pour l'interface Étrave et pour le
  défaut n° 2 (messages envoyés après les ordres), sans pouvoir être compilé ici. Les autres défauts et les corrections
  proposées sont listés dans AUDIT.md.

## Avertissement

Ce dépôt n'est pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures.
