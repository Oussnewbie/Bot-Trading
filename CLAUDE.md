# CLAUDE.md — Strategy V11

## Le projet
Un seul robot, **Strategy V11** : cassure du range M5 de 9:30 New York (A), repli VWAP (B), continuations D1 à D3, stop à 3 ranges et
lots divisés par 3, risque par défaut de 0,25 % par trade. **V11 (26/11/2026, choix de l'utilisateur) = V10 + stop posé des D au prix
d'entrée de A** (taille et seuils +1,5 R / +2 R des D toujours sur le stop de la V10 ; pas de D si son niveau n'est pas au-delà de
l'entrée de A d'au moins un spread et de la distance minimale des stops), plus les corrections EX-1 à EX-7 de l'audit d'exécution. Deux versions qui suivent les mêmes règles :
- l'EA MetaTrader 5, `robot/Strategy-V11.mq5`, version de référence ;
- le script TradingView, `robot/Strategy-V11.pine`.

Les règles, l'installation et les chiffres des tests sont dans `README.md`.

**Périmètre (verrou du 25/11/2026, reconduit en V11 le 26/11/2026) : le Nasdaq 100 et le S&P 500, tradés ensemble** (un graphique M5
chacun).
- Le robot refuse tout autre symbole (`MarcheAutorise` dans l'EA, `runtime.error` dans le Pine). Le Dow est exclu.
- **Règles verrouillées en constantes** dans l'EA et le Pine : toutes les entrées (A, B, D1-D3), stop à 3 ranges (A, B ; taille des
  D), stop posé des D à l'entrée de A (V11), plancher de bruit (H1) coupé, pyramide, mémoire. Profil V10 choisi par l'utilisateur comme le plus rentable (critère gain) ; V11 retenue le 26/11/2026 comme meilleur compromis gain / pire baisse. Seuls restent réglables le
  compte (risque, lots fixes ; solde, taille de contrat et pas de lot dans le Pine), l'heure du serveur (détectée seule hors
  testeur, `InpSrvAuto`, et contre-vérifiée par `InpSrvGMT` : changer de courtier = régler `InpSrvGMT`, voir AUD-03), les FOMC en plus, l'exécution, les notifications et l'affichage. Demande de l'utilisateur du 26/11/2026 :
  « un double-clic, tout se met en place, je règle tout depuis Étrave ». Ne rends pas une règle réglable sans que l'utilisateur le demande.
- Hors sujet : bitcoin, or, devises, DAX.

## Échanges
- Réponds en français simple, sans jargon, avec des chiffres honnêtes (gains comme baisses).
- Le profil de l'utilisateur, son compte et ses choix personnels sont dans la mémoire privée de Claude sur son ordinateur, jamais dans
  ce fichier : le dépôt est public.

## Arborescence et commandes
```
robot/     Strategy-V11.mq5, Strategy-V11.pine, test_robot.py (contrôles du code de l'EA et du Pine),
           mt5/ (demo.ini, profil-Etrave-demo/, demo_1000.set, testeur.ini)
etrave/    interface web locale de l'EA (Python sans dépendance), export.py (export trimestriel) + test_interface.py, test_export.py,
           Etrave.bat (Windows) et Etrave.command (Mac) : double-clic = EA et profil à jour, MetaTrader ouvert, page ouverte
.claude/   commands/audit.md (/audit) et agents/auditeur.md (auditeur adapté au robot) ; rapports dans audits/ (ignoré)
video/     (branche communication/outil-video) vidéos TikTok : récap de séance et présentation, `python3 video/outil.py` ; README
```
- Tests : `.venv/bin/python -m pytest robot etrave -q` (175 tests et 1 ignoré sans l'outil vidéo au 27/11/2026 ; sur la branche
  `communication/outil-video`, ajouter `video`). Le `.venv` (Python 3.15) n'existe que dans le clone principal
  `~/Documents/GitHub/Bot-Trading` : depuis un worktree (dont `Bot-Trading-main`), utiliser `~/Documents/GitHub/Bot-Trading/.venv/bin/python`.
- Étrave en essai : `.venv/bin/python etrave/etrave.py --sans-navigateur --port 8799 --dossier <dossier jetable>`, puis
  `http://127.0.0.1:8799`. Pour voir la page avec des données, écrire de faux `etat-<symbole>.txt` (format dans
  `etrave/test_interface.py`, `faux_etat`) et un `trades-<symbole>.csv`, et les réécrire toutes les 2 secondes (au-delà de 15 s sans
  nouvelle, l'EA est vu comme arrêté).

## MetaTrader 5 sur ce Mac
- **MetaTrader 5 pour Mac** (`/Applications/MetaTrader 5.app`, Wine fourni) et Rosetta 2 sont installés. Préfixe Wine :
  `~/Library/Application Support/net.metaquotes.wine.metatrader5`, plateforme dans `drive_c/Program Files/MetaTrader 5`.
- **Compiler** (depuis le dossier de la plateforme, après avoir copié `robot/Strategy-V11.mq5` dans `MQL5/Experts/Etrave/`) :
  `WINEPREFIX=<préfixe> WINEDEBUG=-all "/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine" "C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"MQL5\Experts\Etrave\Strategy-V11.mq5" /log:"MQL5\Experts\Etrave\compile.log"`,
  puis lire la ligne `Result:` du journal (UTF-16 : `iconv -f UTF-16LE -t UTF-8`). Après toute modification du `.mq5`, compile et
  rapporte la ligne `Result:` ; ne dis jamais « ça compile » sans l'avoir lue. Pour compiler une version qui n'est pas encore sur
  `main` sans toucher à l'EA installé, utilise un autre dossier de `MQL5/Experts/`, puis supprime-le.
- **Testeur** : MetaTrader fermé, `wine "C:\Program Files\MetaTrader 5\terminal64.exe" /config:"C:\Program Files\MetaTrader 5\<f>.ini"`,
  modèle `robot/mt5/testeur.ini` (fins de ligne Windows). Le terminal se ferme seul ; rapport HTML (UTF-16) dans `Tester/`, journal de
  l'agent dans `Tester/Agent-127.0.0.1-300x/logs/`. Dis à l'utilisateur de ne pas fermer MetaTrader pendant un test. **Piège** : sans
  `[TesterInputs]`, le testeur reprend les réglages du passage précédent ; écris toujours `InpFixedLots` et vérifie-le en tête du
  rapport. Les règles sont des constantes : une ligne `.set` ou `[TesterInputs]` à leur nom est ignorée sans message.
- **Compte de test : démo TradinGlobal-Real, hedging.** Symboles NDX100 et SPX500. NDX100 : 1 lot = 1 $ par point, minimum 0,1 lot,
  20 lots au plus par ordre ; heure du serveur GMT+2 / GMT+3 avec l'heure d'été américaine (réglages par défaut de l'EA).
- macOS 27 est la dernière version avec Rosetta complet : ne pas passer ce Mac à macOS 28 avant d'avoir un serveur Windows.

## Ce qu'on ne peut pas vérifier sur ce Mac
- **Le Pine** (pas de TradingView) : n'affirme jamais qu'un `.pine` modifié passe l'analyseur. La version du 21/11/2026 l'avait
  passé ; les modifications suivantes n'ont pas été analysées.
- **Étrave sous Windows** (lancement de MetaTrader avec le profil, installation de l'EA et du profil dans le dossier de données,
  fermeture, démarrage avec Windows, `Etrave.bat --tout`) et l'aspect de la page avec Consolas et Segoe UI. Le même chemin est vérifié sur Mac en vrai
  (26/11/2026 : double-clic sur `Etrave.command`, EA recompilé, profil posé, MetaTrader ouvert, deux EA `trading_auto=1`,
  heure du serveur détectée GMT+2, fermeture propre depuis la page).
- **Pas de `.ex5` dans le dépôt.** On compile sur ce Mac, ou l'utilisateur avec F7 dans MetaEditor, ou avec le bouton d'Étrave.
- Les deux fichiers du robot sont la source : on les modifie directement, en gardant l'EA et le Pine d'accord.
  - `etrave/test_interface.py` vérifie l'accord entre Étrave et l'EA (clés, bornes, journal des trades, heures des règles) et le
    calendrier des fériés entre l'EA et le Pine.
  - `robot/test_robot.py` relit le code pour vérifier chaque correctif. Un nouveau correctif ajoute son contrôle.

## État au 26 novembre 2026 et prochaine action
1. **V11 validée au testeur MT5** (ticks réels, 01/01/2025 → 25/11/2026, 0,1 lot, dépôt 10 000 $) : NDX100 +2 991,22 $, SPX500
   +413,92 $ ; Nasdaq + S&P : +3 405 $, 45 % de jours gagnants, pire jour −101 $, pire baisse −248 $ (V10 : +3 951 $, 47 %, −110 $,
   −360 $). Les corrections EX-1 à EX-7 ne changent aucun trade (mêmes entrées, même résultat au centime).
2. **Démo préparée pour la V11, jamais lancée en séance.** Profil MetaTrader « Etrave-demo » à deux graphiques M5 (NDX100 et
   SPX500), la V11 attachée à chacun avec lots fixes à 0 (demande de l'utilisateur du 26/11/2026 : la taille vient du risque
   d'Étrave ; compte démo de 10 000 $, 0,25 % ≈ 0,1 lot sur NDX100) (`robot/mt5/profil-Etrave-demo/`, fichiers UTF-16 générés puis relus par
   MetaTrader ; vérifié le 26/11/2026 : les deux EA se chargent, `trading_auto=1`, `lots_fixes=0.00`). **Lancement : double-clic sur
   `etrave/Etrave.command`** (ou `Étrave.command` du Bureau, qui l'appelle) avant 9:30 New York : `mt5.py` recompile l'EA si la
   source est plus récente que le `.ex5`, pose le profil, lance `wine terminal64.exe /config:<fichier temporaire>` (`[Charts]
   ProfileLast=Etrave-demo`, `[Experts] AllowLiveTrading=1`, sans `[Common]` : MetaTrader reprend le compte enregistré) dans une
   session à part, et `caffeinate -i -w <pid>`. Fermer avec le bouton d'Étrave (`taskkill` sans `/F`, refusé pendant un trade)
   pour que MetaTrader garde le profil. Un `[StartUp]` n'enregistre pas l'EA dans le profil. `robot/mt5/demo.ini` reste le modèle
   manuel. But : mesurer le **glissement réel** (entrées A, B, D et sortie de 15:50). Deux MetaTrader
   ne tournent pas ensemble : arrêter la démo pour un test.
3. Interrupteur, sur 60 jours de trade, **par marché** (AUD-09, 27/11/2026 ; `export.SEUILS_INTERRUPTEUR`, recalculés depuis
   `reference.json` : pire fenêtre de 60 jours × 1,25 pour le total et la baisse, pire part de jours gagnants − 5 points ; données
   déjà vues, pas une preuve) : Nasdaq < 26,67 % de jours gagnants, total < −14,54 R ou baisse > 23,88 R ; S&P 500 < 18,33 %,
   < −44,83 R ou > 48,64 R. Avant : 28 %, −40 R, 66 R, calculés pour la V10 et un seul marché. Étrave le vérifie toutes les 10 min,
   l'affiche dans l'onglet Séance et envoie un Telegram une fois par franchissement (`interrupteur.txt`), à 60 jours complets. Il
   n'arrête pas l'EA : c'est à l'utilisateur de décider.
4. Le risque par trade se décide une fois le glissement réel connu. C'est la décision de l'utilisateur.
5. Les variantes testées jusqu'au 26/11/2026 (protections contre les retournements, coupes, filtres de tendance, confirmations,
   largeur du stop, grilles de combinaisons) n'ont rien donné de mieux que la V10 ; la V11 est le compromis gain / pire baisse
   retenu. Ne pas les refaire : la prochaine donnée neuve est la démo.

## Discipline
- **Ne règle plus rien sur le Nasdaq à partir du backtest** : tout l'historique 2010 → 18/11/2026 a servi à la mise au point
  (environ 2 000 essais). Les seules données neuves sont celles de la démo et des trades réels. Le S&P 500 et le Dow 2019-2026 du
  courtier ont aussi été vus.
- Tout chiffre trouvé sur l'historique est un candidat, pas une preuve. Écrire l'hypothèse et le critère avant de regarder ; compter
  le spread réel + 1 point de glissement par exécution, puis 2 à 3 points en test de résistance.
- Ne jamais augmenter le risque par trade sans l'accord de l'utilisateur.

## Pièges connus du code
- `InstrumentOf()` (EA) classe le symbole « nasdaq », « sp500 » ou « autre » ; `MarcheAutorise()` s'en sert. Chaque marché a sa
  case marche / arrêt dans Étrave (`pont.INSTRUMENTS`, `INSTRUMENTS` de la page). Le risque, le levier et Telegram d'Étrave
  s'appliquent aux deux.
- Clôture depuis Étrave : une clé `cloturer_<symbole>` par marché, plus l'ancienne clé `cloturer` pour un EA plus ancien.
- La marge du stop de B (`B_BUF_PB` = 0,5 pb) et le coût du garde-fou (`COST_SLIP_PB` = 0,6 pb dans l'EA, `COST_BP` = 1,65 pb
  dans le Pine) sont en pb du prix, pour valoir sur les deux indices.
- **FOMC** : jours de décision codés jusqu'au 26/01/2028 (calendrier révisé de la Fed du 12/11/2026, provisoire). Le 27/10/2027 n'y
  est pas : pas de décision annoncée. Après la liste, l'EA lit l'événement `fed-interest-rate-decision` du calendrier économique de
  MetaTrader (`FomcCalendrier`, hors testeur ; vérifié le 26/11/2026 : mêmes dates de 2025 à 2027 sauf le 27/10/2027, que le calendrier de
  MetaTrader garde encore, heures du serveur). Le Pine n'a pas
  ce calendrier : `fomcExtra`. Si la Fed déplace une date, corriger les deux listes (un test vérifie leur accord).
- **Heure du serveur** (26/11/2026) : `DetecterHeureServeur` (hors testeur, `InpSrvAuto`) déduit le décalage d'hiver de
  `TimeTradeServer() - TimeGMT()` arrondi à l'heure (avertissement au-delà de 10 min d'écart à l'heure attendue), avec la règle `InpSrvDST` (US par défaut).
  AUD-03 (27/11/2026) : `CheckClock` exige que ce décalage détecté égale `InpSrvGMT` (GMT+2 chez TradinGlobal), sinon `gClockOk`
  faux et pas de trade : la détection ne se contrôlait qu'elle-même, et une horloge d'ordinateur fausse de 30 à 90 min faisait
  trader la bougie de 8:30 ou de 10:30. Changer de courtier = régler `InpSrvGMT`. Dans le testeur, `TimeGMT()` vaut l'heure du serveur.
- **Compte et état (AUD-01, AUD-02, 27/11/2026)** : un compte réel ne trade que si `reglages.txt` porte `reel_autorise=<numéro du
  compte>` (écrit par Étrave après le mot REEL ; `CompteAutorise`, garde dans `Setup` et `CheckEntries`) ; un compte démo trade
  toujours. L'état porte le numéro du compte (`<GV>login`) : `ChargerEtatDuCompte` efface l'état d'un autre compte au lieu de le
  relire ; un état sans numéro (d'avant le correctif) n'est repris que sur un compte démo ; rien n'est écrit (`Sv`) tant que le
  compte est inconnu (démarrage de MetaTrader). Verrou par symbole (AUD-11) : variable globale temporaire
  `StratV11_verrou_<symbole>_<magic>` et son battement `_bat` (minuteur toutes les 2 s, posé même sans interface).
- **Risque plafonné à 1 %** (AUD-05, 27/11/2026, choix de Claude sur délégation de l'utilisateur) : `RISK_MAX` = 1.0 dans l'EA et
  Étrave ; une valeur plus haute est ramenée à 1 % (l'utilisateur avait enregistré 2,5 % : pire baisse −80 % dans la simulation de
  la page). Ne le remonte jamais sans son accord. **Ce plafond ne vaut que pour le risque en %** : avec `InpFixedLots` > 0, la
  taille vient des lots fixes et n'est pas plafonnée (calcul des lots dans `Strategy-V11.mq5`, vérifié le 27/11/2026).
- Les numéros magiques 50930 à 50935 sont partagés avec d'anciennes versions (V9, ORB v6) ; le filet de sécurité et
  `EaPositions` surveillent 50930 à 50939. Préfixe d'état `StratV11_`. Compte
  **hedging** obligatoire.
- Le risque réglé dans Étrave passe avant les 0,25 % de l'EA. Après une mise à jour depuis la v6, il peut encore valoir 0,5 %.
- `etrave/reference.json` (26/11/2026) : la V11 rejouée par le simulateur sur les données M1 du courtier, Nasdaq + S&P 500,
  2019-03-28 → 2026-11-25, une ligne par marché et par jour (`date, marche, r, range_sur_prix`, R de toutes les jambes).
  `risque.simuler` compose jour par jour (somme des deux marchés), marge par ligne (15 unités). Recalculer avec
  `donnees/reference-v11/regenerer.sh` (hors dépôt, voir « Données hors dépôt »).
- **Étrave sur Mac** : le dossier partagé est celui du Wine de MetaTrader 5 pour Mac
  (`…/net.metaquotes.wine.metatrader5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files/Etrave`). Avant le
  26/11/2026, Étrave lisait `~/.etrave` : ses réglages n'atteignaient pas l'EA. Les tests n'utilisent jamais le vrai MetaTrader
  (`mt5_terminaux` injecté) : un test qui l'oublie compile et installe pour de vrai sur ce Mac.
- **Étrave en direct** : le détail (lots, stop) ne concerne que la cassure A. Pour B et D, la page affiche les lignes d'état `v8_b`
  et `v9_d` et leur résultat ouvert `v8_resultat`. La clé `jambes` garde le bouton « Clôturer » visible après la sortie de A ;
  `lots_fixes` dit à la page que le risque en % n'est pas utilisé ; `sortie_ny` donne l'heure de sortie du jour.
- Les entrées D ne posent aucun ordre chez le courtier : l'EA guette le niveau et entre au marché. V11 : stop posé = `gEntry` (prix
  d'entrée de A) ; `g.risk` reste la distance au stop de la V10 (`slV10`) pour +1,5 R et +2 R ; risque réel plafonné à celui de A
  (EX-2). Dans le Pine : champ `rsl` de `Leg` (stop de la V10) et paramètre `slOrdre` de `openLegStop`.
- **Journaux d'exécution et des séances (25/11/2026)** : `execution-<symbole>.csv` (une ligne par position fermée : mise en file par
  `ExecQueue` après la comptabilité de `RecordClose` / `LegRecord`, écrite par `JournalFlush` → `ExecRow` seulement hors de la séance
  (après la sortie de fin de journée ou avant 8:55 New York), sans position ni ordre, et à l'arrêt de l'EA : lire les ticks d'une
  entrée ancienne peut faire attendre l'EA jusqu'à 45 s. Une file non écrite est perdue si MetaTrader plante pendant la séance) et
  `seances-<symbole>.csv` (`SeanceRow` :
  « decision » à 9:35, « fin » après la sortie). En-têtes `EXEC_COLONNES` et `SEANCE_COLONNES` : l'export les lit par leur nom
  (`etrave/test_export.py` vérifie l'accord). Une valeur inconnue reste vide. Excursions : ticks pour les minutes d'entrée et de
  sortie, bougies M1 entre les deux. Dans le testeur, les journaux vont dans `Etrave\testeur\`, vidé à chaque passage : de quoi
  vérifier les journaux, pas de quoi régler le robot (historique déjà vu, glissement du testeur ≠ glissement réel).
- **Export trimestriel** (`etrave/export.py`) : `exports/<AAAA-Tn>/` dans le dossier d'Étrave, au démarrage puis toutes les 6 heures,
  pour chaque trimestre terminé depuis 3 jours (dates de New York) ; « Exporter le trimestre en cours » à la demande. Construit sous un
  nom provisoire puis renommé. C'est la matière des ajustements futurs : glissement réel, spread, excursions, jours sans trade.
- **Journal des bougies** (`bougies-<symbole>.csv`, `BougiesRow`) : les bougies M5 de 30 min avant le range jusqu'à la sortie, écrites
  une fois par jour avec la ligne « fin » (hors séance, une lecture). Sert la vidéo récap (`video/`). Testeur 12 mois NDX100 à 0,25 %
  sur 300 000 $ avec ce journal : 448 trades, +64 931,85 $, identique à la référence (avant X-13 ; après : 449 trades, +65 324,88 $).
- **Vidéos** (`video/`) : rien de personnel ni de fichier sous licence dans le dépôt (prénom, montant, certificat, voix, clé, voix_id,
  sons Mixkit, police DIN) : tout est dans `~/.config/etrave-video/config.json` et des dossiers locaux. Un test le vérifie en lisant
  les valeurs dans cette configuration. Démo, réel ou testeur : seulement dans la description de la publication (choix de l'utilisateur), jamais dans la vidéo, la couverture ni les noms de fichiers. Les
  raisons des filtres et le type d'entrée (A, B, D) ne sont jamais montrés : c'est le secret de la stratégie, à la demande de l'utilisateur.
  Preuve : photo de l'onglet Historique de MetaTrader prise par l'outil le soir même (`video/historique.py`, à régler une fois),
  épinglée avec le R en fin de vidéo ; jamais d'image fabriquée à la place. Récap : voix en une seule prise par vidéo (`voix.recit`, sinon le timbre change d'une scène à l'autre), chemin du prix en points
  (mfe du journal d'exécution), mode automatique (`outil.py installer` : agent launchd
  `com.etrave.recap-auto`, outil copié dans `~/Library/Application Support/Etrave/outil-video`, dossiers du jour sur le Bureau), vert et rouge réservés au résultat, caméra calée sur les mots de la voix (`voix.instant`), arrêts d'au moins 1,5 s,
  étiquettes posées dans les zones sûres de TikTok (`police.py` mesure les textes ; un test le vérifie). Musique facultative
  (`musique` de la configuration), jamais dans le dépôt.
- Jours fériés et demi-séances : aucun trade (`InpSkipShort`), même si `FlatMin` prévoit une sortie à 12:45.
- **Page d'Étrave (« terminal de trading sombre », décision de l'utilisateur du 27/11/2026, remplace la « carte marine » du
  25/11/2026)** : thème sombre par défaut quel que soit le réglage de l'ordinateur, clair au bouton (choix retenu sous la clé
  `theme-terminal`). Chiffres en chasse fixe des polices du système (`--f-num` : ui-monospace, SF Mono, Menlo, Consolas, Cascadia
  Mono ; Chrome sur Mac prend Menlo), texte en police du système ; aucune police extérieure (CSP). Une seule couleur d'accent, le
  bleu du logo (actions, voyants « en marche », fenêtre en cours, courbe) ; vert et rouge réservés aux résultats, le rouge servant
  aussi aux alarmes de sécurité (arrêt d'urgence plein, compte réel, EA arrêté, bandeaux graves) ; le magenta (`--mark`) est réservé
  à l'aiguille « maintenant ». Coins de 2 px, filets fins, aucune ombre, contraste AA vérifié dans les deux thèmes. Hiérarchie de
  l'onglet Séance : barre d'état (voyant par marché, démo/RÉEL, heure de New York, date de l'EA, « Arrêt d'urgence ») ; une ligne
  par marché (sens, état du jour, entrée, stop, range, règle en R tirée de `pos_r`, résultat ouvert en grand, « Clôturer ») ;
  interrupteur ; frise des règles (`REGLES_NY`, accord avec l'EA vérifié par un test ; fenêtres allumées seulement si l'EA a des
  ordres ou des positions) ; compte ; ligne « Vidéo du jour » (champ `video` de `/api/etat`, rien si absent) ; courbe ; trades et
  exports repliés. Les explications passent derrière un « ? » ou un pli (« Détail », « Les étapes ») dont l'ouverture est retenue
  (`foldOpen`) ; les avertissements de sécurité restent visibles. Les noms des variables CSS sont utilisés par le script : changer
  leurs valeurs, pas leurs noms. Pas de « · » pour joindre des textes générés par la page. Vérifier l'aspect à 390 px de large :
  la fenêtre de Chrome ne descend pas sous 500 px, passer par un Chrome headless (`Emulation.setDeviceMetricsOverride`).
- **Étrave, audit du 26/11/2026 (27/11/2026)** : bouton « Arrêt d'urgence » (mot ARRET : les deux cases décochées et une clôture
  demandée à chaque EA en marche, `pont.arret_urgence`) ; « Autoriser ce compte réel » (mot REEL, seulement le numéro d'un EA en
  marche sur un compte réel, `pont.autoriser_compte_reel`) ; risque de 0,05 à 1 %, mot RISQUE au-delà de 0,5 % ; « Fermer
  MetaTrader » refusé aussi sur le dernier état connu d'un EA muet (mot FERMER pour passer outre) ; « Installer l'EA » refusé
  pendant un trade ; au double-clic, MetaTrader n'est pas lancé si la compilation a échoué (`lancement.json`) ; version compilée
  (`ea_build`) affichée ; taille estimée et lot minimum dans l'onglet Risque (`risque.estimer_taille`) ; valeurs non finies refusées.
- **Vidéo de fin de journée** (`etrave/fin_de_journee.py`, demande de l'utilisateur du 27/11/2026 : « lancé en fin de journée quand
  tout est clôturé ») : chaque minute, Étrave regarde si la séance est close (au moins 5 min après `sortie_ny`, aucun trade, ordre ou
  jambe dans le dernier état de chaque EA, ligne « fin » du jour écrite par chaque EA en marche), puis lance une fois par jour de New
  York `outil.py auto` de l'outil vidéo installé (`~/Library/Application Support/Etrave/outil-video`, même dossier et même Python
  que `video/installation.py` ; un test le vérifie sur la branche de l'outil). Commande fixe en liste, sans shell, processus détaché,
  sortie dans `recap-auto.log`, jour retenu dans `video-fin-de-journee.txt` (avant le lancement : un échec n'est pas relancé chaque
  minute). La tâche programmée de l'outil (22:20 et 23:50) reste en secours. `/api/etat` renvoie `video` (installé, dernier
  lancement, ce qu'on attend).
- **Revues de code** : les constats corrigés portent leur numéro (EA-xx, X-xx, PINE-xx, ET-xx, VID-xx) dans un commentaire du code et
  un contrôle (`robot/test_robot.py`, `etrave/test_*.py`, `video/test_video.py`). Avant de déclarer un constat réglé, vérifie le code.
  - **Corrigés le 25/11/2026** : X-13 (stop des D compté depuis le déclenchement, comme le Pine et le simulateur ; testeur 12 mois
    NDX100 à 0,25 % sur 300 000 $ : 449 trades, +65 324,88 $, avant 448 et +64 931,85 $), X-14 (même commentaire pour tous les
    ordres), PINE-04 (`close_entries_rule = "ANY"`), PINE-05 (bougie de cassure comptée pour le bord opposé). Audit du soir :
    X-16 (identifiant de l'ajout de A recherché à chaque cotation), X-17 (pas de deuxième A après une réponse perdue), X-18 (jambe
    B/D déjà ouverte reprise après un plantage), X-19 (arrondi des jambes), X-20 (journaux verrouillés par Excel : lignes gardées),
    PINE-06 à PINE-08 (alertes d'annulation des D, de 15:50, lot de l'ajout des jambes), ET-05 à ET-15 (Étrave : un seul serveur par
    port sous Windows, aucun risque imposé par la page, dates de New York, export unique, encodages Windows), VID-01 à VID-17 (outil
    vidéo, sur sa branche : rendu et fuseaux sous Windows, jamais de vidéo muette ni de photo après 17:00 New York, semaines
    complètes). En-têtes de l'EA et du Pine réécrits (ils disaient « Nasdaq uniquement »).
  - **Audit d'exécution V11 du 26/11/2026, corrigés** : EX-1 (stop d'une D contrôlé contre le bid pour un achat et l'ask pour une
    vente, avec la distance minimale et le gel du courtier ; D pas armée à moins d'un spread de l'entrée de A), EX-2 (risque réel
    d'une D plafonné à celui de A, affiché tel quel), EX-3 (journal d'exécution version 2, textes et en-têtes, `InpDeviation`
    décrit), EX-5 (envois WhatsApp / Telegram différés pendant une D guettée ou un côté de A surveillé par l'EA), EX-7 (glissement de
    la sortie de 15:50 mesuré dans le journal, depuis `FlatRef`). Ouverts : EX-4 (à 0,1 lot, environ 1 D sur 4 sautée car son stop
    de la V10 est plus large que celui de A, alors que le stop posé serait plus proche : décision de l'utilisateur, à tester avant
    de changer), EX-6 (D en ordres stop chez le courtier si la démo montre un glissement des D nettement pire que celui de A),
    EX-8 (marge : 15 unités réservées, à vérifier avec le levier réel du compte ; démo sur deux graphiques). Pine V11 non vérifié sur
    TradingView.
  - **Audit du 26/11/2026** (rapport `audits/2026-11-26-2345.md`, hors dépôt), corrigés le 27/11/2026 avec un contrôle chacun
    (`test_aud…`) : AUD-01 (compte réel autorisé seulement depuis Étrave), AUD-02 (état propre au compte), AUD-03 et AUD-04 (heure
    contre-vérifiée par `InpSrvGMT`, écart annoncé par rapport à l'heure attendue), AUD-05 (risque plafonné à 1 %), AUD-06 (après une
    réponse perdue, l'historique des deals et des ordres est relu avant tout renvoi de A ; doublon de A de même taille ouvert à moins
    de 30 s fermé, plus pris pour une pyramide), AUD-07 (ordre stop déjà posé repris à la relance, état écrit avant la pose), AUD-08
    (stop du courtier relu chaque minute, `VerifierStops` : reposé ou position fermée), AUD-11 (un seul graphique par symbole),
    AUD-12 (EX-2 dans le Pine), AUD-17 (« JOUR MANQUÉ » quand l'EA n'a pas préparé le range ; pas d'entrée tardive), AUD-18 (jambe
    B/D inconnue de l'état reprise, `LegAdopt`), AUD-20 (clôture demandée réessayée toutes les 10 s), AUD-22 (`ea_build`), AUD-23
    (pas d'essai Telegram pendant un trade), AUD-24 (`lot_min`, `lot_pas`, `valeur_point_lot`, `prix` dans l'état), AUD-28 (même
    liste de marchés dans l'EA et le Pine). Étrave : AUD-01, AUD-05, AUD-09, AUD-10, AUD-15 (médiane du range sur la bonne colonne),
    AUD-16, AUD-19, AUD-21, AUD-22, AUD-24, AUD-25, AUD-26 (chiffres de la page), AUD-27 (échec d'effacement du fichier de
    connexion journalisé, réessayé). Testeur 01/01/2025 → 25/11/2026, 0,1 lot, après ces correctifs : transactions et journaux
    identiques à la V11 d'avant, au centime (NDX100 1 372 transactions, +2 991,22 $ ; SPX500 1 184, +413,92 $).
  - **Encore ouverts** :
    - X-11 / ET-04 : deux terminaux sur un même ordinateur partagent `reglages.txt` et les clôtures (règle d'usage dans le README) ;
    - X-02 : les sorties et le stop virtuel exigent un EA en marche (VPS) ;
    - R-04 : une bougie est perdue si `CopyRates` échoue ; R-05 : l'achat se déclenche sur l'ask (voulu) ; R-06 : le prochain jour
      faux du calendrier est le 31/12/2027 (le 02/07/2026 était traité en demi-séance « par prudence », voulu) ;
    - Pine : côté bloqué et annulation des D vus à la clôture, ajout au prix de clôture, pas de commission par défaut (limites du
      backtest TradingView) ; `legQty` au moins un pas (voulu) ; PINE-04 à PINE-08 pas encore vérifiés sur TradingView ; le lot
      affiché ignore le minimum du courtier ; le garde-fou coût (1,65 pb) vaut celui de l'EA pour un spread de 0,45 pb ;
    - EA, rares, signalés à l'audit : la perte d'une position fermée par `CloseOpposite` n'entre pas dans le R ; `gDayTxt` et
      `gFiltTxt` ne sont pas sauvegardés (ligne « fin » fausse après un redémarrage) ; `JournalFlush(true)` dans `OnDeinit` peut dépasser le délai de MetaTrader ;
    - Étrave : l'export ne sépare pas démo et réel (colonne `source` des journaux ; « pas grave » pour l'utilisateur). Réglé le
      26/11/2026 : l'interrupteur est jugé marché par marché (ET-16) ;
    - Vidéo : sur Mac, la capture de MetaTrader n'est pas contrôlée (écran verrouillé). Le trait « Jusqu'à … pts » et l'épingle des
      photos sont passés en bleu sur la branche vidéo (VID-31, 26/11/2026).
- Stops : fermer B/D au stop de A, B/D à l'entrée dès +0,5R, stop à +0,5R, A à l'entrée quand une jambe part ont été testés et
  rejetés (25/11/2026) ; ne pas les refaire.

## Données hors dépôt
- `donnees/` (ignoré par git, dans le clone `~/Documents/GitHub/Bot-Trading`) ne contient que `reference-v11/` : le calcul de
  `etrave/reference.json` (scripts, simulateur, données M1 du courtier, `regenerer.sh`, notice `LISEZMOI.md`). Vérifié le
  27/11/2026 : il redonne le fichier de `main` à l'octet près. **Seule copie : ne pas le supprimer.**
- La recherche (ancien dépôt, archives, données Dukascopy, études du 24 au 26/11/2026) a été supprimée le 27/11/2026 à la demande
  de l'utilisateur. Ne pas la reconstituer.

## Git
- Le dépôt GitHub est **public**. Aucune donnée personnelle dans le code (chat ID, numéro de compte réel, jetons).
- Historique repris à zéro le 25/11/2026 à la demande de l'utilisateur : `main` ne contient que la version finale.
- Ne mettre sur `main` que le robot, Étrave et ce qui les sert. Pas de dossier de recherche.
- Logo d'Étrave : hors dépôt, dans `~/Documents/Etrave-communication/logo/`. La branche `communication/roadmap-tiktok` et sa
  roadmap TikTok (périmée : V10, copy trading abandonné) ont été supprimées le 27/11/2026.
- **Historique public** : les fichiers actuels sont propres, mais l'historique public n'a jamais été nettoyé : ne jamais affirmer
  le contraire. Le réécrire demande l'accord explicite de l'utilisateur.
- `.gitattributes` : fins de ligne Windows pour `.bat`, `.cmd`, `.ini` et `.set` (à l'extraction et dans le zip de GitHub).
- Le jeton `gh` n'a pas la portée `workflow` : pousser un fichier `.github/workflows` est refusé.
- Pousser sur `main` ne déploie rien.

## Qualité, sécurité et audits
Les règles communes de l'utilisateur (méthode, tests, sécurité, design, audits) sont dans `~/.claude/CLAUDE.md` sur son Mac. Pour
une session qui ne les voit pas (cloud, VPS), l'essentiel :
- plan court et validation avant toute modification de plus d'un fichier ou d'une règle métier ; une tâche à la fois ;
- jamais « fini », « ça marche » ou « corrigé » sans avoir lancé les tests et le robot (testeur MetaTrader ou Étrave sur un dossier jetable), sortie réelle à l'appui ; ce qui n'a pas pu
  être vérifié va dans une section « Non vérifié » ;
- jamais de test supprimé, désactivé ou affaibli pour passer ; un bug corrigé = un test qui le reproduisait, écrit avant ;
- aucune donnée inventée, aucun secret dans le dépôt, pas de nouvelle dépendance sans le dire ;
- audits : `/audit [périmètre]` lance l'agent `auditeur` (`.claude/agents/auditeur.md`, adapté à ce projet) ; rapport complet dans
  `audits/` (ignoré par git : le dépôt est public) ; rien n'est corrigé avant que l'utilisateur ait choisi quoi traiter.
- argent réel : aucune action sur un compte réel sans confirmation explicite de l'utilisateur ; mise en production dans l'ordre
  testeur MetaTrader → démo → réel.

Si une règle commune contredit ce fichier, ce fichier tient (décision de l'utilisateur du 26/11/2026) : signale la contradiction,
ne change pas le code pour elle. Contradictions connues :
- **Perte journalière maximale** : absente de la V11. Le plafond de −2R par jour a été testé le 26/11/2026 et rejeté (gain −11 % sur
  le Nasdaq, −23 % sur le S&P). Ne l'ajoute pas sans demande.
- **Secrets** : pas de `.env`. Le jeton Telegram est dans `reglages.txt` d'Étrave (dossier commun de MetaTrader, hors dépôt) ou dans
  les entrées de l'EA.
- **Heure de New York** : l'EA la calcule depuis l'heure du serveur et la règle d'heure d'été américaine (MQL5 n'a pas de base de
  fuseaux horaires).
- **Période de test séparée** : il n'en reste plus sur le Nasdaq (voir « Discipline ») ; la seule donnée neuve est la démo.
- **Taille de position maximale** : en lots fixes (`InpFixedLots` > 0), le plafond de 1 % ne s'applique pas. Plafonner aussi les
  lots fixes est une décision de l'utilisateur.
- **Tests des règles de trading** : l'EA n'a que des contrôles du texte du code (`robot/test_robot.py`) et le testeur MetaTrader ;
  pas de test de comportement en MQL5.
