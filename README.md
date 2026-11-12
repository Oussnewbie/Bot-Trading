# Bot-Trading — stratégie ORB v5 (TradingView Pine v6 et MetaTrader 5)

Cassure du range d'ouverture de New York (ORB 5 minutes) sur le Nasdaq (NAS100), graphique M5,
seulement dans le sens de l'élan de l'ouverture, avec une pyramide sur les journées de tendance.
Toutes les heures sont en heure de New York (9:30 NY = 15:30 à Paris la plupart de l'année).

## Contenu

| Fichier | Rôle |
|---|---|
| `pine/ORB-v5.pine` | **La stratégie actuelle (v5)** pour TradingView : la v4 plus une pyramide à +2R. Alertes Telegram. |
| `mt5/ORB-v5.mq5` | **La v5 en Expert Advisor MetaTrader 5**, mêmes règles et mêmes paramètres. Notifications push MT5, WhatsApp et Telegram. |
| `pine/ORB-v4.pine`, `mt5/ORB-v4.mq5` | La v4 (sans pyramide), conservée. |
| `backtest/nas100-10ans/` | Recherche sur NAS100 M5, bid et ask, spread compté, 2015 → 2026. `orb_v5.py` reproduit la v5, `orb_v4.py` la v4. |
| `donnees/` | Données Dukascopy NAS100 CFD M5, bid et ask, 2015 → 2026 (zip). |

Les versions plus anciennes (AMD+ v1 et v2, ORB v3) ont été retirées ; elles restent dans l'historique git.

## À lire avant tout : ce que le test dit vraiment

La v5 a été choisie sur mai 2018 → août 2022, vérifiée sur septembre 2022 → octobre 2026, puis jugée sur
janvier 2015 → avril 2018, une période que personne n'avait regardée avant de figer la v5.

| Période | | Trades | Par trade | Total | Pire baisse |
|---|---|---|---|---|---|
| 2015-01 → 2018-04 (jamais vue) | v4 | 545 | -0,10R | -52R | -76R |
| | **v5** | 545 | -0,03R | **-19R** | -76R |
| 2018-05 → 2022-08 (période de choix) | v4 | 724 | +0,21R | +152R | -23R |
| | **v5** | 724 | +0,37R | **+267R** | -24R |
| 2022-09 → 2026-10 (vérification) | v4 | 646 | +0,17R | +111R | -27R |
| | **v5** | 646 | +0,20R | **+128R** | -34R |
| **Tout : 2015 → 2026** (11,8 ans) | v4 | 1 915 | +0,11R | +211R | -76R |
| | **v5** | 1 915 | **+0,20R** | **+376R** | -76R |

- **L'ORB a perdu trois années de suite, 2015, 2016 et 2017.** Le spread coûtait alors 10 à 13 % du risque à chaque
  trade (range de 9 points pour 1 point de spread ; 1 à 3 % depuis 2020), mais ce n'est pas tout : même sans spread,
  l'avantage de ces années n'est que de +0,04R par trade. Le test 2018-2026 seul était trop flatteur.
- **La pyramide de la v5 ajoute du gain sur les trois périodes** (+33R, +115R, +17R), avec et sans les filtres, et pour
  presque tous les réglages voisins. C'est l'amélioration la mieux vérifiée de tout le projet. Elle ne réduit pas les
  pertes : les stops de départ sont les mêmes que dans la v4.
- R par année de la v5 : 2015 -15, 2016 -10, 2017 -20, 2018 +113, 2019 +38, 2020 +46, 2021 +43, 2022 +52, 2023 +56,
  2024 +22, 2025 +30, 2026 +21. 163 trades par an.
- Capital, v5, intérêts composés :

  | Risque par trade | 2015 → 2026 | Pire baisse | 2018 → 2026 seulement | Pire baisse |
  |---|---|---|---|---|
  | 0,25 % | +8 % par an | -18 % | +12 % par an | -8 % |
  | 0,5 % | +16 % par an | -33 % | +24 % par an | -16 % |
  | 1 % | +30 % par an | -56 % | +50 % par an | -30 % |

- **Attends-toi à +0,15 à +0,20R par trade en moyenne, avec des années perdantes possibles et une baisse de 76R
  (trois ans sans nouveau sommet, d'août 2015 à août 2018) déjà vue dans l'historique.** Fais tourner la v5 en démo
  avant le réel, et choisis le risque par trade en regardant la colonne « pire baisse », pas le retour.

## Les règles de la v5

La v5 reprend les règles 1 à 6 de la v4 ci-dessous et ajoute une pyramide :

7. **Pyramide** : quand une bougie M5 clôture à +2R ou plus (bougie d'entrée comprise, sauf la dernière de la
   journée), on ajoute une unité au marché, de la même taille que la position de départ, et le stop de l'ensemble
   monte à +1R. Un seul ajout par trade. Après l'ajout, le pire cas est zéro : +1R sur la première unité, -1R sur
   l'ajout. La pyramide se déclenche sur 24 % des trades ; 44 % de ces trades finissent à zéro ou un peu en dessous,
   les autres font les grosses journées (meilleur trade +23R, contre +13R sans pyramide).

Le R affiché = résultat net de tout le trade (ajout compris) ÷ somme risquée au départ.

## Les règles de la v4

1. **Range** : high et low de la bougie M5 de 9:30.
2. **Filtres** (à 9:35, avant de poser les ordres) :
   - **RSI14 M5** de la bougie de 9:30 : au-dessus de 50, achat seulement ; en dessous, vente seulement.
   - **Élan de l'ouverture** : achat permis seulement si le high de la bougie de 9:30 dépasse le plus haut de
     9:00-9:30 ; vente seulement si son low passe sous le plus bas de 9:00-9:30.
   - Un côté n'est tradé que s'il passe les deux filtres. Aucun côté : pas de trade ce jour-là.
3. **Ordres** : achat stop sur le high et/ou vente stop sur le low, valables 2 bougies (jusqu'à 9:45).
   Le premier exécuté annule l'autre. Si un seul côté est permis et que l'autre côté du range est touché
   d'abord, l'ordre est annulé.
4. **Stop** de l'autre côté du range. **1R** = la somme perdue si le stop est touché (taille × range).
5. **Gestion** : stop au prix d'entrée dès +1,5R. Pas d'objectif : sortie à 15:50 (clôture de la bougie de 15:45).
6. Un seul trade par jour. Risque conseillé : **0,5 %** par trade.

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
- à la pyramide : un « + » sur la bougie, une ligne en tirets au prix de l'ajout, et le stop passe en vert à +1R ;
- à la sortie, tout s'arrête et s'estompe, le résultat en R reste affiché ; un jour sans trade ne laisse rien ;
- en haut à droite, un tableau : range du jour, côtés permis par les filtres, état du jour, historique et pire baisse.

Le **R** affiché = résultat net du trade (commission comprise) ÷ somme risquée : le même chiffre que le testeur.
Une sortie au prix d'entrée compte comme neutre dans la série de pertes, même si les frais la rendent un peu négative.

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
5. Pour comparer avec le test : testeur de stratégie, NAS100, période janvier 2015 → octobre 2026, modèle « Chaque tick
   basé sur des ticks réels », dépôt 10 000. Les données et le spread de ton broker ne sont pas ceux de Dukascopy :
   le résultat sera proche, pas identique.

Différences avec TradingView : l'entrée se fait au tick où l'ask (achat) ou le bid (vente) atteint le niveau, comme
le test Python ; le stop à l'entrée est décidé à la clôture de la bougie, comme dans le test ; si le broker refuse de
le poser (trop près du prix), l'EA ferme lui-même la position au prix d'entrée. La pyramide est décidée à la clôture
de la bougie M5, comme dans le test et dans le script Pine.

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

## Ce que la recherche de la v5 a testé

Tout a été exploré sur mai 2018 → août 2022 seulement (`v5_exp1.py` à `v5_exp6.py`), avec et sans les filtres :
- **Taille du stop** (0,5 à 1,5 range, 0,10 à 0,30 ATR jour, range borné) : le range entier reste le meilleur.
- **Entrée** (au-delà du niveau, à la clôture hors du range, sur retour au niveau) : l'ordre stop sur la cassure
  reste le meilleur ; l'entrée sur retour au niveau perd.
- **Gestion** (stop à l'entrée plus tôt ou plus tard, stops suiveurs, objectifs, sorties à 12:00 ou 14:00,
  ré-entrée après un stop) : rien de mieux que le stop à l'entrée dès +1,5R et la sortie à 15:50.
- **Contexte du jour** (gap, veille, NR7, force du RSI, largeur de 9:00-9:30, range contre ATR, coût, jour de la
  semaine… 78 tranches) : une seule dépasse le seuil du hasard, quand on en attend 4 par hasard. Aucun filtre ajouté.
- **Pyramide** : le seul vrai levier. Plateau large (ajout entre +1,5R et +2,5R, stop commun entre +0,5R et +1R).
  Une deuxième pyramide n'apporte rien.
- **Entrée en deux temps** (petite taille, complément dès +0,25R) : très bon avec des hypothèses dans la bougie,
  presque nul une fois simulé sans hypothèse (ajout à la clôture). Écarté : c'était un artefact des bougies M5.
- **Ranges de 15, 30 et 60 minutes** : presque pas d'avantage.

Puis vérification hors échantillon (`v5_exp7.py`, `v5_exp8.py`, `orb_v5.py`) : voir le tableau en haut de page.
Les filtres de la v4 n'ont rien apporté sur 2015-2018 (-52R avec, -50R sans) ; sur l'ensemble ils gardent le même
gain avec un tiers de trades en moins. Les données à la minute, qui auraient permis de simuler dans la bougie,
n'ont pas pu être téléchargées.

## Résultats de la v4 sur 2018-2026 (NAS100 CFD Dukascopy, spread réel compté)

Simulation identique au script (un seul ordre du côté permis, faux départs comptés en perte). `python orb_v4.py`
Ces chiffres ne couvrent pas 2015-2017, où la v4 perd 52R : voir le tableau en haut de page.

| | Trades | Stops pleins | Par trade | 2018-22 / 2022-26 | Total | Pire baisse / série | Années + |
|---|---|---|---|---|---|---|---|
| v3 (sans filtre) | 2 091 | 58 % | +0,113R | +0,14 / +0,09 | +237R | -33R / 13 | 8/9 |
| v3 + RSI seul | 1 547 | 58 % | +0,152R | +0,19 / +0,12 | +236R | -29R / 12 | 9/9 |
| v3 + élan seul | 1 583 | 57 % | +0,166R | +0,17 / +0,16 | +263R | -28R / 11 | 9/9 |
| **v4** (RSI + élan) | **1 369** | 57 % | **+0,193R** | +0,21 / +0,17 | **+264R** | **-27R** / 13 | **9/9** |

- 161 trades par an (environ un jour de bourse sur 1,6). R par année : 2018 +51, 2019 +23, 2020 +16, 2021 +34,
  2022 +24, 2023 +43, 2024 +7, 2025 +45, 2026 +22.
- À 0,5 % de risque : environ +16 % par an, pire baisse -13 %. À 1 % : environ +32 % par an, pire baisse -24 %.
- **À lire avec prudence** : le filtre d'élan a été trouvé en regardant toute la période. Choisie sur 2018-22
  seulement parmi 64 combinaisons de filtres, la meilleure fait +0,23R par trade sur 2018-22 puis +0,16R sur
  2022-26 (v3 : +0,09R) : le gain tient, mais il fond. Compte plutôt sur **+0,15R par trade** en réel, et fais
  tourner le script 2 à 3 mois en démo avant de passer en réel.

### Pourquoi les stops, et pourquoi on ne peut pas les éviter

Autopsie des 2 091 trades de la v3 (`v4_veille.py`, `v4_autopsie.py`, `v4_autopsie_eval.py`, `v4_fractal.py`,
`v4_preouverture.py`, `v4_sim.py`, `v4_filtres.py`, `v4_combos.py`) :
- 58 % de stops pleins, 23 % de gagnants qui font +3R en moyenne. 55 % des stops tombent dans les 15 minutes
  après l'entrée, 86 % dans la première heure : ce sont des faux départs de l'ouverture.
- 6 % des trades touchent les deux côtés du range dans la même bougie : -1R garanti, imprévisible.
- La bougie d'entrée qui reclôture dans le range annonce un stop 72 fois sur 100, mais sortir à cette clôture
  coûte plus (-0,32R) que garder (-0,14R) : les trades qui se retournent rapportent +494R. Éviter des stops
  n'est pas gagner plus.
- Structure (plus hauts / plus bas) M15, H1, H4, D1 alignée avec le trade : aucun effet stable.
  Niveaux de la veille, de la nuit ou de la semaine juste devant : aucun effet stable.
- Ce qui aide un peu : trader dans le sens de l'élan de l'ouverture (RSI, cassure de 9:00-9:30). Le taux de stops
  ne baisse presque pas ; ce sont les trades à petits gains qui disparaissent.
- Sans effet stable ou trop peu de trades : jour de la semaine, NFP, échéances, news de 8:30, gap, volatilité,
  taille du range, grosse journée la veille, cassure à 9:35 seulement. Pistes plus anciennes sans effet : MA200,
  MA50, EMA200 H1, MACD, Ichimoku, Bollinger, Fibonacci, stop plus large ou plus serré, stop à l'entrée dès +1R,
  prises partielles, inversion après un faux départ, entrée à la clôture hors du range.

## Refaire les tests

Python 3 avec `pandas` et `numpy`. Décompresse d'abord le zip de `donnees/` dans ce même dossier, puis :

```bash
cd backtest/nas100-10ans
python orb_v5.py            # la v5, la v4 et la v3 sur les trois périodes, simulation du capital
python v5_exp1.py           # v5 : stop, entrée, gestion, pyramides, ré-entrée, sorties (2018-22 seulement)
python v5_exp2.py           # v5 : grille de pyramides
python v5_exp3.py           # v5 : contexte du jour par tranches
python v5_exp4.py           # v5 : entrée en deux temps (avec hypothèses dans la bougie)
python v5_exp5.py           # v5 : ajouts décidés à la clôture (sans hypothèse)
python v5_exp6.py           # v5 : la pyramide avec les autres réglages
python v5_exp7.py           # pourquoi 2015-2017 perd : coût du spread, volatilité
python v5_exp8.py           # robustesse : pyramide et filtres période par période
python orb_v4.py            # la v4 et ses deux filtres, simulation du capital
python v4_combos.py         # 64 combinaisons de filtres, choisies sur 2018-22 et vérifiées sur 2022-26
python v4_veille.py         # trades selon la séance de la veille (à lancer avant v4_autopsie.py)
python v4_autopsie.py       # une ligne par trade : tout ce qui est connu à l'entrée
python v4_autopsie_eval.py  # chaque variable, par tranches, sur les deux moitiés
python v4_fractal.py        # structure multi-unités de temps et niveaux plus grands
python v4_preouverture.py   # fenêtre de l'élan : de 9:15 à la nuit entière
python v4_sim.py            # sortie si reclôture dans le range, entrée à la clôture
python v4_filtres.py        # filtres simulés comme le script
python orbv_var.py          # pistes de gestion : taille du stop, stop à l'entrée, partielles, stop dans le temps…
python orbx_part2.py        # filtres d'indicateurs
python strat.py             # stratégies d'indicateurs seules (RSI2, Donchian, MACD, Ichimoku, Bollinger, Fibonacci)
```

## Avertissement

Ce dépôt n'est pas un conseil en investissement. Les performances passées ne préjugent pas des performances futures.
