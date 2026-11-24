# CLAUDE.md — Bot-Trading (Strategy V10)

## Le projet
Un seul robot, **Strategy V10** : cassure du range M5 de 9:30 New York, repli VWAP (B), continuations D1 à D3, profil **Confort**
(stop ×3 et lots ÷3), risque par défaut de 0,25 % par trade. Il existe en deux versions qui suivent les mêmes règles :
- l'EA MetaTrader 5, `robot/Strategy-V10.mq5`, qui est la version de référence ;
- le script TradingView, `robot/Strategy-V10.pine`.

Les règles et l'installation sont dans `README.md`.

**Périmètre : les indices américains uniquement.**
- **Nasdaq (NAS100)** : en service.
- **Dow Jones (US30) et S&P 500 (US500)** : à étudier, rien n'est validé.
- Hors sujet : bitcoin, or, devises, DAX. Le bot BTC et ces marchés ont été retirés le 24 novembre 2026.

## L'utilisateur
- Il écrit en français. Réponds-lui en français simple, sans jargon, avec des chiffres honnêtes.
- Il fait tourner l'EA sur **ses fonds propres**.
- Pour les challenges de prop firm, il lit le script Pine **à la main**. Ne recherche pas les règles des prop firms et n'en parle pas,
  sauf s'il le demande.
- Ses critères ont évolué. En session 2 : même risque par trade, le plus gros gain total. En session 4 : un bon taux de réussite et
  comprendre les stops. Demande-lui avant de trancher entre ces deux critères.

## Arborescence
```
robot/       Strategy-V10.mq5, .ex5 (compilé), .pine
etrave/      interface web locale de l'EA (Python sans dépendance) + test_interface.py
recherche/   rapports des sessions 2 à 4, journal (notes/nasdaq-progress.md), trades V10 de référence
```

Commandes, à lancer depuis la racine du dépôt :
- Tests : `.venv/bin/python -m pytest etrave -q` (28 tests ; il faut seulement pytest). Le `.venv` du dépôt tourne sous Python 3.15.
- Étrave : `.venv/bin/python etrave/etrave.py --sans-navigateur --port 8799 --dossier <dossier jetable>`, puis la page sur
  `http://127.0.0.1:8799`.

## Ce qu'on ne peut pas vérifier sur ce Mac
- **Pas de MetaEditor ni de TradingView.** N'affirme jamais qu'un `.mq5` ou un `.pine` modifié compile.
  - Le `.mq5` a compilé avec 0 erreur sous Wine, sur la plateforme Claude, le 21 novembre 2026. La recette est dans
    `recherche/notes/nasdaq-progress.md`, session 2.
  - Le `.pine` est passé par l'analyseur de TradingView.
- **Modifier le `.mq5` rend le `.ex5` périmé.** Dis-le à l'utilisateur : il recompile avec F7, ou avec le bouton d'Étrave.
- **Les deux fichiers du robot sont maintenant la source.** Ils avaient été générés depuis la V9 par des scripts restés dans l'archive
  (`81_generer_v10.py`). On les modifie désormais directement, en gardant l'EA et le Pine d'accord. `etrave/test_interface.py` vérifie
  une partie de cet accord : clés d'Étrave, journal des trades, calendrier des fériés.
- **Le robot n'a jamais été vu en train de tourner** : ni testeur MT5, ni backtest TradingView, ni démo.

## État au 24 novembre 2026 et prochaine action
1. L'utilisateur passe la V10 dans le testeur MT5 : 12 derniers mois, « chaque tick basé sur des ticks réels », compte hedging. Compare
   son rapport trade par trade à `recherche/resultats/trades_V10_confort_2018_2026_1pt.csv` (jour, sens, heure, prix à quelques points
   près). Ordre de grandeur sur le 20/11/2025 → 19/11/2026 : environ 410 trades, environ 50 % de gagnants, +76 R.
2. Ensuite, la démo. Mesure le **glissement réel** des ordres stop de 9:35 : c'est la variable qui décide de tout (les tests supposent
   1 point).
3. Interrupteur, sur 60 jours de trade : moins de 28 % de jours gagnants, un total pire que −40 R, ou une baisse de plus de 66 R. Ces
   seuils ne sont pas codés dans le robot.
4. Le risque par trade (0,25 % ou plus) se décide une fois le glissement réel connu. C'est la décision de l'utilisateur.

## Discipline de recherche (à respecter)
- Environ 2 000 essais ont déjà été faits. Tout chiffre trouvé sur l'historique est un **candidat**, pas une preuve.
- **Nasdaq** : 2010 → 18/11/2026 a été vu en entier (Dukascopy 2018-2026, HistData 2010-2017). **Ne règle plus rien sur le Nasdaq à
  partir du backtest.** Les seules données neuves sont celles qui arrivent après le 19/11/2026, et les trades de démo.
- **Dow Jones** : la recherche s'est arrêtée au 31/12/2023. Les années **2024-2026 n'ont jamais été ouvertes** (le « coffre 3 »).
  Elles servent à juger **une seule fois une seule idée**, écrite à l'avance avec son critère dans `recherche/notes/idees-strategies.md`.
  - La V10 transposée telle quelle : Confort −26 R, Tendance −38 R. Pas d'élan à l'ouverture (t = 0,4).
  - Piste non prouvée : le repli en tendance sur bougies jour (76 % de réussite, +0,08 R par trade, t = 1,55).
- **S&P 500** : seul un contrôle de la V9 a été fait (HistData, bid seul), sur 2015-2017 et 2018-2025 (`recherche/resultats/62_sp500.md`).
  - Sur 2018-2025, aux coûts d'aujourd'hui : +677 R, t = 2,2.
  - À coûts doublés : +172 R, t = 0,6, donc plus rien de significatif.
  - Le profil Confort n'y a jamais été testé.
  - Les données Dukascopy (bid + ask) du S&P n'ont jamais été chargées.
- Méthode, chaque fois :
  - écrire l'hypothèse et le critère avant de regarder ;
  - compter les coûts ainsi : spread réel + 1 point de glissement par exécution, puis 2-3 points en test de résistance ;
  - inscrire chaque essai au registre ;
  - ne jamais augmenter le risque par trade sans l'accord de l'utilisateur.

## Pièges connus du code
- `InstrumentOf()` (EA) ne reconnaît que les symboles du Nasdaq. US30 et US500 tombent dans « autre » : la case d'Étrave ne les commande
  pas (`etrave/pont.py`, `INSTRUMENTS = {"nasdaq": True}`).
- Certains réglages sont **en points d'indice et calibrés pour le Nasdaq** : `InpBBuf` (1 point, marge du stop de B), `InpCostSlip`
  (1 point de glissement supposé) et `costPts` du Pine (3,3 points). Ils sont à revoir avant tout test sur le Dow ou le S&P : un point
  y pèse bien plus lourd par rapport au range.
- **FOMC** : les dates sont codées jusqu'en 2026. Celles de 2027 se saisissent dans `InpFomc` (EA) et `fomcExtra` (Pine). C'est à faire
  dès que la Fed les publie.
- Les numéros magiques 50930 à 50935 sont partagés avec la V9. Le préfixe d'état est `StratV10_`. Le compte doit être en mode
  **hedging**.
- `etrave/reference.json` contient encore les trades de l'**ORB v6** : la page Risque d'Étrave simule donc la v6. Le refaire à partir des
  trades V10 est un chantier ouvert. La V10 tient jusqu'à 5 positions, alors que `risque.py` suppose une seule position avec sa pyramide.
- Le script Pine a un vrai chat ID Telegram de l'utilisateur comme valeur par défaut : n'envoie jamais rien vers lui.

## Données (hors dépôt, `donnees/` est ignoré par git)
- **Nasdaq M1**, Dukascopy, bid et ask, du 01/01/2018 au 19/11/2026 : `~/Desktop/Nasdaq 8 ans/` (deux CSV, horodatage en ms UTC),
  avec la même chose en zip à côté.
- **L'archive complète de la recherche** est `~/Desktop/Strategy v10.zip` (identique à `~/Desktop/sortie 3/`). Elle contient les
  scripts, tous les résultats et les versions V7 à V9.
  - Les scripts pointent vers `/workspace` et demandent numba et des fichiers parquet : il faut les adapter avant de les relancer.
  - Le téléchargement Dukascopy (Dow, S&P…) passe par `scripts/68_dukascopy_api.py`, qui interroge l'API des graphiques
    freeserv.dukascopy.com.
- Les anciennes données v5 (zips M1 Nasdaq 2018-2026) et l'étude des stops v5 sont dans la branche `archive/etude-stops-v5`.

## Git
- Ne mettre sur `main` que la V10 et ce qui la sert.
- Branches d'archive à ne pas supprimer : `archive/etude-stops-v5` (ancienne étude des stops v5) et `claude/cool-galileo-hzgjdo`
  (revue indépendante de l'ORB v6 et du bot BTC).
- Le jeton `gh` n'a pas la portée `workflow` : pousser un fichier `.github/workflows` est refusé.
- Pousser sur `main` ne déploie rien.
