# Étrave — ORB v6 sur le Nasdaq (MetaTrader 5, interface, TradingView)

Cassure du range d'ouverture de New York (bougie M5 de 9:30) sur le Nasdaq (NAS100), dans le sens de l'élan de
l'ouverture, avec une pyramide sur les journées de tendance. Heures de New York (9:30 NY = 15:30 à Paris la plupart de
l'année). **Nasdaq uniquement** : la stratégie ne gagne sur aucun autre symbole testé (Dow Jones, or, EUR/USD, bitcoin).

| Fichier | Rôle |
|---|---|
| `mt5/ORB-v6.mq5` | L'Expert Advisor MetaTrader 5 (version 6.00). |
| `interface/`, `Etrave.bat` | **Étrave**, l'interface de l'EA : une page web locale (risque, levier, Telegram, suivi et clôture des trades, lancement de MetaTrader). |
| `pine/ORB-v6.pine` | La même stratégie pour TradingView (langage Pine v6), avec alertes Telegram. |
| `backtest/m1/` | Le simulateur à la minute qui refait les trades de référence de l'interface, et le rapport de la recherche du 17 novembre 2026. |

Le 15 novembre 2026 le dépôt a été réduit à ces éléments. Les données Dukascopy, les anciennes études et l'audit restent
dans l'historique git (dernier commit qui les contient : `afb79de`).

## Ce que dit le test

Nasdaq CFD Dukascopy, M1 bid et ask rejoués minute par minute, glissement de 0,1 point, 2018-01 → 2026-11 : 1 391
trades (156 par an), **+0,46R par trade, +643R**, pire baisse −23R, 15 pertes de suite au pire, 59 % de pertes pleines,
9 années positives sur 9.

- Période de choix (2018-05 → 2022-08) : +371R. Vérification (2022-09 → 2026-11) : +233R.
- **La v6 = les règles de la v5 avec une pyramide de 2 unités** (17 novembre 2026). Les fichiers v5 ont été retirés du
  dépôt (ils restent dans l'historique git). Avec un ajout d'une unité : +471R, pire baisse −22R ; sans pyramide : +312R.
  Le détail, et tout ce qui a été essayé sans succès (placement du stop, autres entrées, flux d'ordres du future NQ,
  sorties anticipées, règles de mise), est dans [backtest/m1/RAPPORT.md](backtest/m1/RAPPORT.md).
- **Avant 2018 la stratégie perdait** : −55R sur 2015-2017, −33R sur 2013-2014. L'ancien test 2015-2026 a connu une baisse
  de 76R avec la pyramide de 2 unités (74R avec une unité).
- Capital, gains réinvestis, 2018 → 2026 : 0,25 % par trade → +19 % par an, pire baisse −6 % ; 0,5 % → +40 %, −11 % ;
  1 % → +88 %, −22 %. Si une période comme 2015-2017 revenait : environ −17 % à 0,25 %, −32 % à 0,5 %, −53 % à 1 %.
- Le résultat dépend du glissement : +565R avec 0,5 point par exécution, +455R avec 1 point.
- Garde un risque fixe : réduire la mise après des pertes ou en période de baisse a fait moins bien dans le test.

Ce n'est pas un conseil en investissement, et le passé ne garantit rien. Fais tourner l'EA en démo avant le réel, et
choisis le risque en regardant la pire baisse.

## Les règles

1. **Range** : high et low de la bougie M5 de 9:30.
2. **Filtres** : achat permis si le RSI14 M5 de cette bougie est au-dessus de 50 **et** si son high dépasse le plus haut de
   9:00-9:30 ; vente si le RSI est sous 50 et le low sous le plus bas de 9:00-9:30. Aucun côté permis : pas de trade.
3. **Ordres** : achat sur le high et/ou vente sur le low, valables 2 bougies (jusqu'à 9:45). Le premier exécuté annule
   l'autre. Si un seul côté est permis et que l'autre est touché d'abord, pas de trade ce jour-là.
4. **Stop** de l'autre côté du range. 1R = taille de départ × range.
5. **Stop au prix d'entrée** dès +1,5R, décidé à la clôture d'une bougie après celle de l'entrée.
6. **Pyramide** : quand une bougie clôture à +2R ou plus, deux unités sont ajoutées et le stop de l'ensemble monte à 1R
   sous le prix de l'ajout. Le pire cas reste −1R : la première unité a au moins +1R d'acquis, les deux unités ajoutées
   risquent 1R chacune. Un seul ajout par trade.
7. **Sortie** à 15:50. Un seul trade par jour.
8. **Jours fériés américains et demi-séances** (le marché ferme vers 13:00) : sortie à 12:45, plus de pyramide ensuite.
   Le calendrier est calculé par l'EA et par le script (jour de l'an, Martin Luther King, Presidents' Day, vendredi
   saint, Memorial Day, Juneteenth, 4 juillet, Labor Day, Thanksgiving, Noël ; lendemain de Thanksgiving, veille de
   Noël, veille du 4 juillet). Cette règle a été ajoutée le 15 novembre 2026, après le test.

## Installer

1. Installe Python 3 ([python.org](https://www.python.org/downloads/), coche « Add python.exe to PATH »). Rien d'autre.
2. Double-clique sur `Etrave.bat` : la page s'ouvre sur `http://127.0.0.1:8788` (ailleurs que sous Windows :
   `python interface/etrave.py`).
3. Onglet **Connexions** : « Installer ou mettre à jour l'EA » le copie dans `MQL5\Experts\Etrave` et le compile ; les
   erreurs éventuelles s'affichent dans la page. À la main : copie `mt5/ORB-v6.mq5` dans `MQL5/Experts`, ouvre-le dans
   MetaEditor, F7.
4. Dans MetaTrader, glisse l'EA sur un graphique du Nasdaq (une seule fois, MetaTrader s'en souvient) et coche
   « Autoriser le trading algorithmique ».
5. **Heure du serveur** : la plupart des courtiers sont à GMT+2 en hiver avec l'heure d'été américaine (réglages par
   défaut). Si ce n'est pas le cas du tien, corrige « Décalage GMT du serveur » et « Heure d'été du serveur ». L'EA
   compare en continu avec l'heure réelle du serveur ; la page affiche une alerte rouge en cas d'écart.
6. Compte en mode **hedging** conseillé. MetaTrader doit rester ouvert de 9:30 à 15:50 New York.

## L'interface Étrave

- **Vue d'ensemble** : solde, trade en cours et résultat cumulé en argent, en % et en R, courbe des trades pris, liste
  des trades, case du Nasdaq (décochée : plus de nouveau trade), bouton « Clôturer le trade ». Les blocs se replient d'un
  clic sur leur titre.
- **Risque** : le seul réglage, de 0,05 % à 20 % du solde par trade, avec le levier de ton courtier. Pour la valeur
  choisie, la page rejoue les 1 391 trades du test : gain par an, pire baisse, série de 15 pertes, part des trades que la
  marge aurait obligé à réduire (la marge doit porter 3 unités : à 1 % de risque avec un levier de 1:20, 8 % des trades
  sont réduits ; à 0,5 %, 1 %). Au-delà de 1 %, il faut taper le mot RISQUE.
- **Connexions** : Telegram (jeton, « Trouver ma discussion et tester », « Essai depuis MetaTrader » qui dit si
  MetaTrader bloque l'adresse) ; MetaTrader 5 (connexion à un compte, installation de l'EA, ouverture automatique de
  MetaTrader au démarrage d'Étrave, lancement d'Étrave à l'ouverture de la session Windows).

L'interface et l'EA se parlent par des fichiers du dossier commun de MetaTrader
(`…\MetaQuotes\Terminal\Common\Files\Etrave`) : la page écrit `reglages.txt`, l'EA le relit toutes les 2 secondes et écrit
son état et ses trades. L'interface ne passe aucun ordre ; on peut la fermer sans rien changer à l'EA ni à ses alertes.

- Un nouveau risque vaut pour le trade suivant, jamais pour un trade ouvert.
- **Marge** : la position, ajout de la pyramide compris, ne demande jamais plus de 90 % de la marge libre. Si le risque
  demandé est trop grand pour le levier, l'EA réduit la taille et le dit dans le message « Ordres placés ».
- **Clôturer** : l'EA ferme le trade au marché (ou annule les ordres du jour) dans les 2 secondes ; une demande de plus de
  2 minutes est ignorée.
- **Telegram** : dans MetaTrader, Outils > Options > Expert Advisors, coche « Autoriser WebRequest pour les URL listées »
  et ajoute `https://api.telegram.org`. Exemple de message : `✅ ACHAT CLÔTURÉ : +1,3R · +0,65 % · +65,20 USD`.
- **Sécurité** : écoute sur 127.0.0.1 uniquement, jeton tiré au hasard à chaque lancement, aucune ressource extérieure.
  Le jeton Telegram n'est plus jamais affiché une fois enregistré ; le mot de passe du compte n'est écrit que dans un
  fichier provisoire effacé une minute après le lancement de MetaTrader. Sur un VPS, ouvre la page par le Bureau à
  distance : n'ouvre jamais le port 8788 sur internet.

**Où faire tourner l'EA** : ton ordinateur pour la démo (sans mise en veille), un VPS Windows pour le réel. Le VPS intégré
à MetaTrader n'a pas d'écran et ne lance aucun autre programme : l'EA y tourne, sans l'interface.

Tests de l'interface : `python -m pytest interface` (26 tests ; ils vérifient aussi que l'EA et l'interface emploient les
mêmes noms de fichiers, de clés et les mêmes bornes).

## TradingView

Colle `pine/ORB-v6.pine` dans l'éditeur Pine, sur un graphique **M5** du NAS100 avec les bougies hors séance. Dans
« Propriétés », ajoute une commission égale au spread de ton courtier. Alertes Telegram : une alerte sur la stratégie,
condition « Uniquement les appels de la fonction alert() », webhook `https://api.telegram.org/bot<TOKEN>/sendMessage`.
Après chaque mise à jour du script, supprime et recrée l'alerte.

## Ce que l'EA ne fait pas exactement comme le script TradingView

Les règles sont les mêmes. Les écarts viennent du spread, que TradingView ne voit pas (il n'a qu'un prix par bougie) :

| | Script TradingView | EA |
|---|---|---|
| Déclenchement d'un achat | quand le prix du graphique atteint le high | quand l'**ask** atteint le high (un spread plus tôt), exécution au marché |
| Vente : seuils de +1,5R et de +2R, côté bloqué touché | mesurés sur le prix du graphique | mesurés sur l'**ask** (le prix auquel une vente se rachète) : un spread plus exigeants |
| Stop de la pyramide | 1R sous la clôture de la bougie | 1R sous le prix réel de l'ajout, pris au premier tick de la bougie suivante |
| Filtre d'élan | une bougie entre 9:00 et 9:30 suffit | il en faut au moins deux |
| Taille | capital × risque ÷ range | la même, puis plafonnée par la marge (90 % de la marge libre, pyramide comprise) |
| Heure de New York | donnée par TradingView | calculée à partir de l'heure du serveur du courtier : dépend de deux réglages |
| En plus dans l'EA | — | risque et pause réglés depuis Étrave, clôture demandée depuis Étrave |

Ces écarts sont ceux du test d'origine, qui comptait le bid et l'ask : c'est lui que l'EA suit.

## Limites connues

- **L'EA ORB-v6 n'a jamais été compilé ni exécuté** : il a été modifié sans MetaTrader. Compile-le, corrige ce que le
  compilateur signale, et fais-le tourner en démo.
- Le lancement de MetaTrader, la connexion à un compte, l'installation de l'EA depuis la page et le lancement au démarrage
  de Windows n'ont jamais été essayés sous Windows.
- Le script TradingView a lui aussi été modifié les 15 et 17 novembre 2026 (sortie des jours fériés, taille de l'ajout)
  sans pouvoir être compilé : si l'éditeur Pine signale une erreur, renvoie-la. Ses réglages déjà enregistrés sur un
  graphique gardent l'ancienne taille d'ajout : remets « Taille de l'ajout » à 2 ou réinitialise les paramètres.
- Jours fériés : le calendrier a été contrôlé sur les fermetures de 2022 à 2025. Une fermeture exceptionnelle (deuil
  national, panne) n'y figure pas : ce jour-là la position passerait la fermeture. À l'inverse, environ deux fois par
  décennie il sort à 12:45 un jour normal (31 décembre quand le 1er janvier tombe un samedi).
- EA lancé entre 9:35 et 9:40 avec le prix déjà au-delà du range : il entre au marché, quelle que soit la distance.
- Après un plantage de MetaTrader, l'état de l'EA peut être ancien (stop de référence, pyramide).
- **Passer de la v5 à la v6** : fais-le hors séance, sans trade ouvert (la v6 ne reprend pas l'état d'un trade de la
  v5). Retire ORB-v5 de ses graphiques, supprime `ORB-v5.mq5` et `ORB-v5.ex5` de `MQL5\Experts\Etrave`, installe la v6
  depuis Étrave (onglet Connexions) et pose ORB-v6 sur le graphique du Nasdaq. Sur TradingView, supprime l'ancien script
  et son alerte, colle `pine/ORB-v6.pine` et recrée l'alerte.
- Arrondi des lots faux si le pas de volume du courtier n'est pas 1, 0,1 ou 0,01.
- Le journal des trades de l'interface commence avec la version 5.10 de l'EA ; la v6 continue le même journal.
