# Bot-Trading — stratégie ORB v4 (TradingView, Pine Script v6)

Cassure du range d'ouverture de New York (ORB 5 minutes) sur le Nasdaq (NAS100), graphique M5,
seulement dans le sens de l'élan de l'ouverture.
Toutes les heures sont en heure de New York (9:30 NY = 15:30 à Paris la plupart de l'année).

## Contenu

| Fichier | Rôle |
|---|---|
| `pine/ORB-v4.pine` | **La stratégie.** Range de la bougie de 9:30, ordres stop sur le high et/ou le low selon les filtres, valables jusqu'à 9:45, stop de l'autre côté du range, stop remonté au prix d'entrée dès +1,5R, sortie à 15:45. Alertes Telegram. |
| `backtest/nas100-10ans/` | Recherche sur 8 ans et demi de NAS100 (bid et ask, spread compté). `orb_v4.py` reproduit la v4. |
| `donnees/` | Données Dukascopy NAS100 CFD M5, bid et ask, 2015 → 2026 (zip). |

Les anciennes versions (AMD+ v1 et v2, ORB v3) ont été retirées ; elles restent dans l'historique git.

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

## Utiliser la v4

1. Dans TradingView, ouvre l'éditeur Pine, crée un nouveau script, colle le contenu de `pine/ORB-v4.pine` et enregistre.
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
- à la sortie, tout s'arrête et s'estompe, le résultat en R reste affiché ; un jour sans trade ne laisse rien ;
- en haut à droite, un tableau : range du jour, côtés permis par les filtres, état du jour, historique et pire baisse.

Le **R** affiché = résultat net du trade (commission comprise) ÷ somme risquée : le même chiffre que le testeur.
Une sortie au prix d'entrée compte comme neutre dans la série de pertes, même si les frais la rendent un peu négative.

## Résultats (NAS100 CFD Dukascopy, mai 2018 → octobre 2026, spread réel compté)

Simulation identique au script (un seul ordre du côté permis, faux départs comptés en perte). `python orb_v4.py`

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
