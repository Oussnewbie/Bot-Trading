# Recherche du 17 novembre 2026 — stops, entrée, flux d'ordres, gestion

Point de départ : beaucoup de stops semblent « pris à tort » (le prix touche le stop puis part dans le sens prévu).
Toute la recherche est rejouée **minute par minute** (M1 bid et ask Dukascopy, 2018-01 → 2026-11-13, glissement
0,1 point), avec la règle habituelle : une idée n'est retenue que si elle gagne sur 2018-05 → 2022-08 **et** sur
2022-09 → 2026-11, à risque égal. Environ 300 variantes ont été essayées en tout : attends-toi à quelques faux positifs
dans le détail, d'où cette règle.

## Ce qui a changé dans le bot

**Pyramide : ajout de 2 unités au lieu de 1** (même seuil +2R à la clôture M5, stop de l'ensemble 1R sous l'ajout).
Le pire cas d'un trade reste −1R : après l'ajout, la première unité a au moins +1R d'acquis et les deux unités ajoutées
risquent 1R chacune.

| | 2018-05 → 2022-08 | 2022-09 → 2026-11 | Tout | Pire baisse | Pire série |
|---|---|---|---|---|---|
| Sans pyramide | +165R | +134R | +312R | −24R | 13 |
| Ajout de 1 (v5 jusqu'ici) | +264R | +180R | +471R | −22R | 13 |
| **Ajout de 2 (v5 depuis l'EA 5.11)** | **+371R** | **+233R** | **+643R** | **−23R** | **15** |
| Ajout de 3 (pire cas −2R, écarté) | +479R | +286R | +814R | −27R | 15 |

- Mieux chaque année de 2018 à 2026. Sur l'ancien test M5 de 2015-2017, quand la stratégie perdait (−55R), la taille
  de l'ajout ne change rien, et la pire baisse passe de −74R à −76R.
- Prix : 149 trades montés à +2R finissent à −1R au lieu d'environ 0.
- Glissement par exécution : +643R avec 0,1 point, +565R avec 0,5 point, +455R avec 1 point.
- Le simulateur à la minute donne +471R pour l'ajout de 1, contre +438R pour l'ancien simulateur M5 : 36 trades que
  le M5 comptait en stop étaient des ordres annulés (l'autre côté du range touché avant l'entrée).

## Ce qui a été testé et n'a pas été retenu

**Placement du stop et de l'entrée** (tout perd ou ne gagne pas sur les deux périodes) : stop plus loin de 0,1 à
1 range à risque égal (+200 à +350R contre +471R), stop plus court, stop jugé à la clôture M5 (son gain dans l'étude
du 14 novembre venait de l'ambiguïté du M5), entrée plus loin que le niveau, entrée après une ou plusieurs clôtures M1
ou M5, ordre limite sur repli, moitié à la cassure et moitié sur repli, entrée au marché à 9:35 (le papier
Zarattini-Aziz), stop en fraction de l'ATR, ré-entrée après un stop (gain seulement sur 2022-2026), retournement au
stop. Les stops « pris à tort » existent, mais 4 stops sur 5 avaient tort sur le sens, et rien ne les distingue à
l'entrée : 72 % de tous les trades, et 2 gros gagnants sur 3, reviennent d'un quart de range dans le range dans les
5 minutes.

**Flux d'ordres du future NQ** (Databento, transactions avec le côté de l'agresseur, 9:28-10:00, 1 356 jours) : delta
de la bougie de 9:30, avant la cassure (5 s à 3 min), absorption au niveau, divergence, gros ordres, volume, delta
après l'entrée (5 s à 5 min) et au moment du piège. Une seule famille trie les trades sur les deux périodes : une ruée
d'agresseurs dans notre sens dans les 10 à 30 secondes avant la cassure donne un peu plus de stops (51 % → 60 %).
Aucun filtre, aucune sortie ni aucune entrée conditionnelle tirée de ces mesures n'améliore le résultat. Passer en
futures n'éviterait pas ces stops (le CFD suit le future) ; seul gain possible : des coûts plus bas.

**Gestion et money management** : seuil d'ajout à +1,5R, +2,5R ou +3R, deuxième et troisième ajouts, stop à
l'entrée à +1R, +2R ou jamais, stop suiveur, sortie plus tôt, sortie quand une clôture rend une part du gain, prise
partielle, retournement ou reprise après un retour au prix d'entrée : tout fait moins bien que la gestion actuelle avec
l'ajout de 2. Entre les trades, un risque fixe bat toutes les règles qui réduisent la mise après des pertes ou en
baisse : les résultats alternent (après 3 pertes de suite, le trade suivant fait +0,6R en moyenne, contre +0,2 à
+0,3R sinon, sur les deux périodes).

## Refaire les chiffres

```
git archive afb79de donnees/nas100 | tar -x       # les zips M1 2018-2026 (100 Mo), ignorés par git
python backtest/m1/reference.py                    # rejoue la v5 et refait interface/reference.json
```

`sim.py` : données du jour, signal et moteur de trade à la minute (décisions à la clôture M5 comme l'EA).
`gestion.py` : le même moteur avec une pyramide réglable (taille, seuil, plusieurs ajouts), stop à l'entrée et sortie
réglables. Les scripts des autres essais (entrées, flux d'ordres NQ) ne sont pas dans le dépôt ; leurs conclusions
sont ci-dessus.
