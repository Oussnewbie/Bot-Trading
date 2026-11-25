# CLAUDE.md — Strategy V10

## Le projet
Un seul robot, **Strategy V10** : cassure du range M5 de 9:30 New York (A), repli VWAP (B), continuations D1 à D3, stop à 3 ranges et
lots divisés par 3, risque par défaut de 0,25 % par trade. Deux versions qui suivent les mêmes règles :
- l'EA MetaTrader 5, `robot/Strategy-V10.mq5`, version de référence ;
- le script TradingView, `robot/Strategy-V10.pine`.

Les règles, l'installation et les chiffres des tests sont dans `README.md`.

**Périmètre (verrou du 25/11/2026, choix de l'utilisateur) : le Nasdaq 100 et le S&P 500, tradés ensemble** (un graphique M5 chacun).
- Le robot refuse tout autre symbole (`MarcheAutorise` dans l'EA, `runtime.error` dans le Pine). Le Dow est exclu.
- **Règles verrouillées en constantes** dans l'EA et le Pine : toutes les entrées (A, B, D1-D3), stop à 3 ranges, plancher de bruit
  (H1) coupé, pyramide, mémoire. Profil choisi par l'utilisateur comme le plus rentable (critère gain). Seuls restent réglables le
  compte (risque, lots fixes ; solde, taille de contrat et pas de lot dans le Pine), l'heure du serveur, les FOMC après janvier 2028,
  l'exécution, les notifications et l'affichage. Ne rends pas une règle réglable sans que l'utilisateur le demande.
- Hors sujet : bitcoin, or, devises, DAX.

## Échanges
- Réponds en français simple, sans jargon, avec des chiffres honnêtes (gains comme baisses).
- Le profil de l'utilisateur, son compte et ses choix personnels sont dans la mémoire privée de Claude sur son ordinateur, jamais dans
  ce fichier : le dépôt est public.

## Arborescence et commandes
```
robot/     Strategy-V10.mq5, Strategy-V10.pine, test_robot.py (contrôles du code de l'EA et du Pine),
           mt5/ (demo.ini, demo_1000.set, testeur.ini)
etrave/    interface web locale de l'EA (Python sans dépendance), export.py (export trimestriel) + test_interface.py, test_export.py
video/     (branche communication/outil-video) vidéos TikTok : récap de séance et présentation, `python3 video/outil.py` ; README
```
- Tests : `.venv/bin/python -m pytest robot etrave -q` (107 tests ; sur la branche `communication/outil-video`, ajouter `video`). Le `.venv` du dépôt tourne sous Python 3.15.
- Étrave en essai : `.venv/bin/python etrave/etrave.py --sans-navigateur --port 8799 --dossier <dossier jetable>`, puis
  `http://127.0.0.1:8799`. Pour voir la page avec des données, écrire de faux `etat-<symbole>.txt` (format dans
  `etrave/test_interface.py`, `faux_etat`) et un `trades-<symbole>.csv`, et les réécrire toutes les 2 secondes (au-delà de 15 s sans
  nouvelle, l'EA est vu comme arrêté).

## MetaTrader 5 sur ce Mac
- **MetaTrader 5 pour Mac** (`/Applications/MetaTrader 5.app`, Wine fourni) et Rosetta 2 sont installés. Préfixe Wine :
  `~/Library/Application Support/net.metaquotes.wine.metatrader5`, plateforme dans `drive_c/Program Files/MetaTrader 5`.
- **Compiler** (depuis le dossier de la plateforme, après avoir copié `robot/Strategy-V10.mq5` dans `MQL5/Experts/Etrave/`) :
  `WINEPREFIX=<préfixe> WINEDEBUG=-all "/Applications/MetaTrader 5.app/Contents/SharedSupport/wine/bin/wine" "C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"MQL5\Experts\Etrave\Strategy-V10.mq5" /log:"MQL5\Experts\Etrave\compile.log"`,
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
- **Étrave sous Windows** (lancement de MetaTrader, installation de l'EA, démarrage avec Windows) et la police Bahnschrift.
- **Pas de `.ex5` dans le dépôt.** On compile sur ce Mac, ou l'utilisateur avec F7 dans MetaEditor, ou avec le bouton d'Étrave.
- Les deux fichiers du robot sont la source : on les modifie directement, en gardant l'EA et le Pine d'accord.
  - `etrave/test_interface.py` vérifie l'accord entre Étrave et l'EA (clés, bornes, journal des trades, heures des règles) et le
    calendrier des fériés entre l'EA et le Pine.
  - `robot/test_robot.py` relit le code pour vérifier chaque correctif. Un nouveau correctif ajoute son contrôle.

## État au 25 novembre 2026 et prochaine action
1. **Testeur MT5** (NDX100 TradinGlobal, 20/11/2025 → 19/11/2026, ticks réels) : mêmes 123 jours de trade que le simulateur de la
   recherche, du même signe chaque jour. Ajouts de pyramide de plus de 20 lots refusés par le courtier : l'ajout est désormais borné à
   20 lots (passages suivants à 300 000 $ : aucun refus de volume ; sans effet à 0,1 lot).
2. **Testeur, 12 mois, 0,1 lot fixe sur 1 000 $** (`InpFixedLots = 0.1`), code du 25/11/2026 au soir (après X-13 et l'audit) :
   +1 885,09 $, 379 trades, 123 jours de trade, 53 % de jours gagnants, pire jour −91 $, pire baisse −321 $ (jour par jour ; −330 $
   sur le solde). Avant le verrouillage des règles : +1 886,96 $. Une bonne année (+76 R contre environ +51 R pour une année
   médiane). Audit : à 0,25 % sur 300 000 $, mêmes 449 trades et +65 324,88 $ qu'après X-13, transaction par transaction.
3. **Démo préparée, jamais lancée en séance.** Relance : MetaTrader fermé, copier `robot/mt5/demo.ini` dans le dossier de la
   plateforme et `robot/mt5/demo_1000.set` en UTF-16 dans `MQL5/Presets/StrategyV10_demo_1000.set`, puis
   `terminal64.exe /config:"C:\Program Files\MetaTrader 5\demo.ini"` et `caffeinate -i -w <pid>`, avant 9:30 New York. But : mesurer
   le **glissement réel** (les tests supposent 1 point). Deux MetaTrader ne tournent pas ensemble : arrêter la démo pour un test.
4. Interrupteur, sur 60 jours de trade : moins de 28 % de jours gagnants, un total pire que −40 R, ou une baisse de plus de 66 R. Non
   codé, calculé pour toutes les entrées à 0,25 %. En lots fixes sur 1 000 $, −40 R serait le compte entier.
5. Le risque par trade se décide une fois le glissement réel connu. C'est la décision de l'utilisateur.

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
  est pas : pas de décision annoncée. Les suivants se saisissent dans `InpFomc` (EA) et `fomcExtra` (Pine). Si la Fed déplace une
  date, corriger les deux listes (un test vérifie leur accord).
- Les numéros magiques 50930 à 50935 sont partagés avec d'anciennes versions (V9, ORB v6) ; le filet de sécurité et
  `EaPositions` surveillent 50930 à 50939. Préfixe d'état `StratV10_`. Compte
  **hedging** obligatoire.
- Le risque réglé dans Étrave passe avant les 0,25 % de l'EA. Après une mise à jour depuis la v6, il peut encore valoir 0,5 %.
- `etrave/reference.json` contient les trades de l'**ORB v6** : la page Risque simule donc la v6, avec la marge de la V10 (15 unités
  réservées, position 3 fois plus petite). Le refaire à partir des trades V10 est un chantier ouvert.
- **Étrave en direct** : le détail (lots, stop) ne concerne que la cassure A. Pour B et D, la page affiche les lignes d'état `v8_b`
  et `v9_d` et leur résultat ouvert `v8_resultat`. La clé `jambes` garde le bouton « Clôturer » visible après la sortie de A ;
  `lots_fixes` dit à la page que le risque en % n'est pas utilisé ; `sortie_ny` donne l'heure de sortie du jour.
- Les entrées D ne posent aucun ordre chez le courtier : l'EA guette le niveau et entre au marché.
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
  sur 300 000 $ avec ce journal : 448 trades, +64 931,85 $, identique à la référence.
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
- **Page d'Étrave (« carte marine », 25/11/2026)** : thème clair par défaut, mode nuit ; chiffres en DIN (Bahnschrift sous Windows,
  DIN Alternate en gras seulement sur Mac), aucune police extérieure (CSP). L'onglet Séance dessine les fenêtres des règles
  (`REGLES_NY`, accord avec l'EA vérifié par un test) et ne les allume que si l'EA a des ordres ou des positions. Le magenta
  (`--mark`) est réservé à l'aiguille « maintenant ». Les noms des variables CSS sont utilisés par le script : changer leurs valeurs,
  pas leurs noms. Pas de « · » pour joindre des textes générés par la page.
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
  - **Encore ouverts** :
    - X-11 / ET-04 : deux terminaux sur un même ordinateur partagent `reglages.txt` et les clôtures (règle d'usage dans le README) ;
    - X-02 : les sorties et le stop virtuel exigent un EA en marche (VPS) ;
    - R-04 : une bougie est perdue si `CopyRates` échoue ; R-05 : l'achat se déclenche sur l'ask (voulu) ; R-06 : le prochain jour
      faux du calendrier est le 31/12/2027 (le 02/07/2026 était traité en demi-séance « par prudence », voulu) ;
    - Pine : côté bloqué et annulation des D vus à la clôture, ajout au prix de clôture, pas de commission par défaut (limites du
      backtest TradingView) ; `legQty` au moins un pas (voulu) ; PINE-04 à PINE-08 pas encore vérifiés sur TradingView ; le lot
      affiché ignore le minimum du courtier ; le garde-fou coût (1,65 pb) vaut celui de l'EA pour un spread de 0,45 pb ;
    - EA, rares, signalés à l'audit : la perte d'une position fermée par `CloseOpposite` n'entre pas dans le R ; `gDayTxt` et
      `gFiltTxt` ne sont pas sauvegardés (ligne « fin » fausse après un redémarrage) ; un jour où `Setup` n'aboutit pas de toute la
      bougie de 9:35 disparaît sans message ; `JournalFlush(true)` dans `OnDeinit` peut dépasser le délai de MetaTrader ;
    - Étrave, décisions de l'utilisateur : l'interrupteur additionne les R du Nasdaq et du S&P le même jour (seuils calculés pour
      toutes les entrées, pas pour deux marchés) ; l'export ne sépare pas démo et réel (colonne `source` des journaux) ;
    - Vidéo, à décider avec l'utilisateur : le trait « Jusqu'à +106 pts » est vert et l'épingle des photos rouge, alors que vert et
      rouge sont réservés au résultat ; sur Mac, la capture de MetaTrader n'est pas contrôlée (écran verrouillé).
- Test des stops (25/11/2026, pré-enregistré, historique déjà vu) : fermer B/D au stop de A ≈ neutre ; B/D à l'entrée dès +0,5R,
  stop à +0,5R au lieu de l'entrée, A à l'entrée quand une jambe part : moins bons. Les stops restent tels quels.

## Données et archives (hors dépôt)
- **Sauvegarde complète de l'ancien dépôt** (recherche, rapports, simulateur, toutes les branches et étiquettes, avant le nouveau
  départ du 25/11/2026) : `~/Desktop/Bot-Trading-sauvegarde-2026-11-25.bundle`. Pour la consulter :
  `git clone ~/Desktop/Bot-Trading-sauvegarde-2026-11-25.bundle <dossier>`.
- Archive de la recherche : `~/Desktop/Strategy v10.zip`. Nasdaq M1 Dukascopy 2018 → 18/11/2026 : `~/Desktop/Nasdaq 8 ans/`.
- `donnees/` (ignoré par git) : données de travail locales.

## Git
- Le dépôt GitHub est **public**. Aucune donnée personnelle dans le code (chat ID, numéro de compte réel, jetons).
- Historique repris à zéro le 25/11/2026 à la demande de l'utilisateur : `main` ne contient que la version finale.
- Ne mettre sur `main` que le robot, Étrave et ce qui les sert. Pas de dossier de recherche.
- `communication/roadmap-tiktok` : logo d'Étrave et roadmap TikTok de l'utilisateur, hors `main` à sa demande (PR #1 fermée sans
  fusion le 25/11/2026). Elle part d'un ancien `main` (70a7576) : ses fichiers du robot sont périmés.
- `.gitattributes` : fins de ligne Windows pour `.bat`, `.cmd`, `.ini` et `.set` (à l'extraction et dans le zip de GitHub).
- Le jeton `gh` n'a pas la portée `workflow` : pousser un fichier `.github/workflows` est refusé.
- Pousser sur `main` ne déploie rien.
