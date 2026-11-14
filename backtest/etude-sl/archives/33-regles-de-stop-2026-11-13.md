# Archive — 33 règles de stop au prix d'entrée (13 novembre 2026)

Section du README de la branche `claude/compassionate-cannon-ydoll7` (commit `caa8983`), supprimée de GitHub le 14 novembre 2026.
Faite sur l'ancien jeu de données (M5, 2015-2026, 1 915 trades). Le script `v5_exp11.py` reste dans ce commit.

### Le trade en gain qui finit en stop plein (`v5_exp11.py`)

Idée venue d'un trade du 13 novembre 2026 : en gain d'environ +0,6R, puis stop plein. Sur les 1 915 trades de la v5
(2015 → 2026), 1 134 finissent en stop plein (59 %). Gain atteint avant le stop, mesuré sans hypothèse :

| Avant le stop, le trade était monté à | Part des stops pleins |
|---|---|
| moins de +0,25R | 43 % |
| +0,25 à +0,5R | 21 % |
| +0,5 à +1R | 24 % |
| +1 à +1,5R | 12 % |

- **C'est récurrent** : un stop plein sur trois (36 %) était d'abord à +0,5R ou plus, soit un trade sur cinq. Même
  proportion sur les trois périodes.
- **Mais ces trades sont ceux qui paient** : les 1 189 trades qui atteignent +0,5R font **+0,93R en moyenne** si on ne
  touche pas au stop (35 % de stops pleins, 64 % à zéro ou mieux). À +1R : +1,53R en moyenne, 15 % de stops pleins.
- 33 règles testées sur les trois périodes, pyramide comprise, avec et sans filtre. Total de la v5 : +373R.

  | Règle | Stops pleins | Total 2015 → 2026 |
  |---|---|---|
  | **v5 : stop à l'entrée dès +1,5R** | 59 % | **+373R** |
  | stop à l'entrée dès +0,5R | 38 % | +222R |
  | stop à l'entrée dès +1R | 52 % | +292R |
  | stop à -0,5R dès +0,5R, puis à l'entrée dès +1,5R | 38 % | +357R |
  | stop à -0,5R après 30 minutes | 43 % | +373R |
  | sortie à la clôture revenue au prix d'entrée, après +0,5R | 40 % | +250R |
  | stop de départ à 0,5 range / 0,75 range / 1,5 range | 71 % / 65 % / 52 % | -41R / +160R / +234R |
  | les trois meilleures (stop à l'entrée dès +2R ; -0,5R dès +1R ; range borné à 0,25 ATR jour) | 52 à 63 % | +379R à +381R |

- Aucune règle ne fait mieux que la v5 au-delà du bruit (+8R sur 373R, pour 33 essais). Remonter le stop tôt supprime
  bien des stops pleins, mais les remplace par des sorties à zéro sur des trades qui seraient repartis.
- Deux règles gardent presque le même total avec moins de stops pleins : le stop à -0,5R dès +0,5R (-16R, un peu moins
  bon sur 2018-2026) et le stop à -0,5R après 30 minutes (même total). Elles ne gagnent pas plus ; elles changent la
  forme des pertes. Elles ne sont pas dans les scripts.
- La bougie de 10:00 (heure des annonces) porte 7 % des stops pleins, dans la continuité des bougies voisines.

### Les trades d'octobre et novembre 2026

`v5_recent.py` rejoue la v5 sur les dernières semaines avec les contrats à terme NQ de Yahoo Finance et donne, jour
par jour, le range, le RSI, les côtés permis et le résultat. Sur le 19 octobre → 12 novembre 2026 il retrouve les
11 trades de TradingView (BlackBull) : 6 stops de suite du 20 octobre au 2 novembre, puis deux journées de tendance
(+6,8R et +5,5R). Tous respectaient les deux filtres. Les perdants avaient souvent un RSI proche de 50, mais sur
12 ans un RSI plus marqué n'aide pas de façon stable (`v5_exp9.py`) : sur 2022-2026 les trades à RSI proche de 50
font même mieux que la moyenne. Six stops de suite sont dans la norme d'une stratégie à 57 % de stops.
