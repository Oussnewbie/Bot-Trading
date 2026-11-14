# Rapport — les stops de l'ORB v5 (NAS100)

Branche `recherche/stops`. Rien ici n'est passé dans le bot. Les scripts, le détail et les 516 lignes de résultats sont
dans ce dossier ([JOURNAL.md](JOURNAL.md), [resultats.csv](resultats.csv), [sorties/](sorties/)).

## En bref

- **Les sorties sur mèche existent et elles sont fréquentes.** Sur 837 stops pleins, la bougie M5 du stop reclôture du
  bon côté une fois sur deux, et le prix atteint ensuite +1R dans 42 % des cas.
- **Aucune des 466 variantes testées ne corrige ça de façon fiable.** Éloigner le stop sauve les mèches et perd autant
  sur les vrais retournements. Une fois compté le nombre d'essais, la meilleure variante a une chance sur trois de devoir
  sa place au hasard.
- **Un seul changement tient sur les deux périodes : ne pas trader les jours fériés américains et les demi-séances.**
  Il est petit (+18R puis +10R) et concerne 49 trades en 12 ans.
- **Le stop « à la clôture M5 » gagne sur le papier (+48R puis +36R), mais je ne le recommande pas.** Tout son gain vient
  des jours où l'entrée et le stop tombent dans la même bougie M5, dont l'ordre est inconnu sans données à la minute.
- **Le résultat de la v5 dépend beaucoup du glissement.** Sur la mise au point : +233R avec 0,1 point, +116R avec un
  demi-spread, 0R avec un spread entier. C'est le point le plus important à vérifier chez ton courtier.

## 1. Données et référence

**Données** (détail : [sorties/00_qualite_donnees.md](sorties/00_qualite_donnees.md))

| | |
|---|---|
| Instrument | NAS100 en CFD (Dukascopy). **Or : aucune donnée dans le dépôt.** |
| Horizon | M5 seulement. Pas de M1 ni de ticks. H4 et M15 sont reconstruits à partir du M5. |
| Prix | Bid et ask, 733 078 bougies chacun |
| Période | 2015-01-01 → 2026-10-30 |
| Défauts | 0 doublon, 0 valeur manquante, 0 bougie incohérente, ask jamais sous le bid |
| Trous | 27 trous de plus de 5 minutes en séance en 12 ans (surtout mars 2020). En 2015-2017 une partie de la nuit manque. |
| Séances écourtées | 102 jours (3,3 %) : 74 jours fériés US, 23 demi-séances, 5 pannes ou coupe-circuits |
| Calendrier économique | Absent. Les annonces sont approchées par des règles. |

**Découpage.** Mise au point : 2015-01-02 → 2023-04-12 (70 % du calendrier, 1 371 trades). Vérification :
2023-04-13 → 2026-10-30 (554 trades). La vérification a été ouverte une seule fois, sur 5 finalistes figés dans git avant.

**La vérification n'est pas vierge.** Le README et la branche `claude/compassionate-cannon-ydoll7` avaient déjà mesuré
la v5 et 33 règles de stop sur tout 2015-2026. J'avais lu ces chiffres avant de commencer.

**Référence** (mise au point, détail : [sorties/01_reference.md](sorties/01_reference.md))

| Référence | R par trade | Total | Profit factor | Pire baisse | 2015-17 | 2018-23 |
|---|---|---|---|---|---|---|
| Code actuel : R sur entrée-stop, glissement 0,1 point | +0,167 | +229R | 1,27 | -74R | -55R | +283R |
| Doc stricte : R sur le range, glissement 0,1 point | +0,170 | +233R | 1,27 | -76R | -54R | +288R |
| **Doc stricte, glissement d'un demi-spread (retenue)** | **+0,085** | **+116R** | **1,13** | **-138R** | -121R | +236R |
| Doc stricte, glissement d'un spread entier | 0,000 | 0R | 1,00 | -185R | -173R | +172R |

- « Code actuel » et « doc stricte » diffèrent sur un seul point : le simulateur divise par la distance entrée-stop, alors
  que le README, le script TradingView et l'EA divisent par le range. L'écart est de 2 %.
- Le spread est réel dans les données, élargissement à l'ouverture compris. Le glissement, lui, est une hypothèse. Un
  demi-spread vaut environ 0,55 point par exécution.
- Commission : 0. Swap : 0, aucune position ne passe la nuit.
- Toute la recherche utilise la référence « demi-spread ». Les finalistes sont aussi mesurés avec les deux autres.

## 2. Diagnostic des stops

Détail : [sorties/02_diagnostic_stops.md](sorties/02_diagnostic_stops.md), un stop par ligne dans
[sorties/02_diagnostic_stops.csv](sorties/02_diagnostic_stops.csv).

Sur 1 371 trades, 878 perdent : 837 stops pleins (-1,08R en moyenne), 30 stops remontés un peu sous zéro, 11 sorties de
15:50 en perte.

**Ce que fait le prix après un stop plein**

| | Mise au point | Vérification |
|---|---|---|
| Stops pleins (part des trades) | 837 (61 %) | 315 (57 %) |
| La bougie M5 du stop reclôture du bon côté | 49 % | 56 % |
| Le prix revient ensuite au prix d'entrée | 69 % | 67 % |
| Le prix atteint ensuite +1R | 42 % | 37 % |
| Sortie sur mèche, définition retenue | 19 % | 18 % |

- Dépassement du stop dans sa bougie : 4 points en médiane, soit 0,56 ATR M5 ou 0,21R.
- 19 % des stops tombent dans la bougie d'entrée, 55 % dans le premier quart d'heure, 84 % dans l'heure.

**Définition de la mèche.** J'en ai testé neuf. Je retiens : *après le stop, le prix ne le dépasse pas de plus de 0,5R,
puis atteint +1R avant 15:50*. Les définitions plus larges (« le prix revient à l'entrée », 69 %) comptent des trades
qui n'auraient rien rapporté. Celle-ci décrit un trade qu'un stop un peu plus loin aurait vraiment sauvé.

**Les trois catégories** (mise au point)

| Catégorie | Stops | Part | Gain si le stop était 0,5R plus loin, taille inchangée |
|---|---|---|---|
| Idée fausse (le prix continue contre moi) | 673 | 80 % | **-284R** |
| Sortie sur mèche | 140 | 17 % | **+288R** |
| Stop dû au spread (dépassé de moins d'un spread sur toute la journée) | 24 | 3 % | +49R |

Total : +53R, pour un risque par trade 50 % plus grand. À risque égal, c'est nul.

**Quand.** La part de mèches monte à 33 % pour les stops de la bougie d'entrée et à 28 % entre 9:35 et 9:40. Elle tombe
à 9 % après une heure et à 2 % après midi. Quand la bougie du stop reclôture du bon côté, 31 % sont des mèches ; quand
elle clôture au-delà, moins de 15 %.

**Pourquoi.** Je n'ai pas trouvé de cause qu'on puisse filtrer. La part de mèches reste entre 12 % et 25 % quel que soit :
le jour de la semaine, le sens, un stop sur un chiffre rond, un stop au niveau du plus bas de 9:00-9:30, un stop près des
niveaux de la veille, la bougie de 10:00, le premier vendredi du mois, un spread élargi ou le biais H4. Seule la taille
du range compte un peu : 12 % de mèches quand le range est très grand, 25 % quand il est petit. C'est le bruit de
l'ouverture, pas une chasse aux stops repérable.

## 3. Variantes testées

466 variantes, toutes sur la mise au point, toutes dans [resultats.csv](resultats.csv) : 319 seules et 147 combinaisons.
Le dépôt en avait déjà testé environ 260 avant.

| Famille | Variantes | Meilleure (écart avec la v5) | Lecture |
|---|---|---|---|
| A. Placement du stop : marge en points, en ATR, en % du range, en spread, ou stop plus court | 39 | +0,1 ATR M5 : +13R (t = 0,7) | Toute marge sérieuse coûte : +10 % du range -46R, +0,25 ATR -21R, +1 spread -17R |
| A. Stop derrière un swing (9:00, 1 h, 2 h, 4 h, nuit, swing M15) | 31 | -25R | Aucun swing ne fait mieux que le bord du range |
| A. Stop en ATR jour | 10 | 0,2 ATR jour : +39R | Pic isolé : 0,15 fait -34R et 0,25 fait -61R |
| B. Stop jugé à la clôture M5, avec stop de secours | 13 | +48R, taille inchangée | Voir la partie 5 : gain non fiable |
| C. Entrée plus loin que le niveau, à la clôture, ou ordre gardé si le côté bloqué est touché | 9 | -50R | Pire dans tous les cas |
| C. Entrée sur retracement dans le range (0 à 61,8 %) | 15 | -94R | Pire dans tous les cas |
| C. Attendre que la liquidité soit prise, puis entrer | 30 | -71R | Trop peu de trades, et ils perdent |
| C. Ré-entrée après un stop sur mèche | 30 | -1R | Jusqu'à -218R |
| C. Confirmation par le volume | 4 | +15R (t = 0,2) | Rien |
| D. Filtre de coût (spread ou range trop petit) | 8 | +60R, pire baisse -53R | Agit sur 2015-2017 seulement |
| D. Volatilité, RSI plus marqué | 12 | +38R (t = 1,4) | Même effet : évite 2015-2017 |
| D. Jours fériés US et demi-séances | 3 | +18R (t = 1,9 à 2,8) | Petit, régulier |
| D. Jour de la semaine, annonces, entrée à 9:35 seule | 11 | +23R (t = 0,6) | Rien de net |
| E. Objectif, stop à l'entrée, sortie partielle, stop suiveur, sortie horaire | 63 | +19R (t = 0,8) | La gestion actuelle reste la meilleure |
| E. Pyramide | 8 | taille 2 : +93R (t = 2,9) | Pire baisse -157R, 32 pertes de suite : plus de mise, pas un meilleur stop |
| F. RSI, fenêtre de l'élan, validité des ordres, durée du range | 14 | RSI 21 : +15R | Range de 10, 15 ou 30 minutes : -92R à -166R |
| F. Biais H4 (structure H4 + MA200 H4) | 3 | « pas contre le biais » : +40R | Biais strict : -79R, il ne garde que 277 trades |
| G. Stop resserré avec le temps | 16 | +11R | Rien |
| Combinaisons par 2 et par 3 | 147 | coût + clôture + 9:35 : +125R (t = 2,2) | Voir la partie 5 |

Trois choses à retenir :

- **La pyramide porte la stratégie.** Sans elle la v5 tombe de +116R à +27R.
- **Le biais H4 strict de ta demande** (structure et MA200 d'accord, sinon pas de trade) fait perdre 79R sur l'ORB.
- **Les entrées « SMC »** (liquidité prise d'abord, retracement de Fibonacci dans le range) perdent toutes sur cette
  stratégie. Elles n'ont été testées que comme greffes sur l'ORB, pas comme stratégie à part.

## 4. Validation

Détail : [sorties/05_validation.md](sorties/05_validation.md).

- **Nombre d'essais.** 17 variantes sur 466 dépassent t = 2. La meilleure atteint t = 3,47. Par hasard seul, la meilleure
  de 466 variantes atteint 3,01 en médiane. Probabilité que ce 3,47 soit dû au hasard : **33 %**. Rien ne passe la
  correction.
- **Test glissant.** Chaque année de 2018 à 2023, j'applique la variante qui avait le mieux fait jusque-là. Résultat :
  +107R, contre +236R pour la v5 sans rien changer. Choisir le gagnant du passé a fait perdre 129R.
- **Plateaux.** Le stop à la clôture donne +39R à +48R pour tout stop de secours entre 0,5R et 2R. Le filtre de coût
  tient à 10 % et 7 %, plus à 5 %. Le stop à 0,2 ATR jour est un pic isolé, écarté.
- **Monte Carlo.** La pire baisse observée de la v5 (-138R) dépasse 99 % des tirages où l'on mélange l'ordre des trades
  (-115R). Les pertes ne sont pas réparties au hasard : elles sont groupées sur 2015-2017.

| Pire baisse probable, tout l'historique, coûts réalistes | Observée | 95 % des tirages sous | 99 % sous |
|---|---|---|---|
| v5 | -138R | -94R à -108R | -115R à -137R |
| F3 (jours fériés) | -126R | -89R à -97R | -109R à -126R |

Les deux bornes viennent de deux méthodes : mêmes trades dans un autre ordre, puis trades tirés avec remise.

## 5. Les cinq finalistes

Figés sur la mise au point, puis mesurés une fois sur la vérification. Détail et exemples :
[sorties/06_verification.md](sorties/06_verification.md).

**Avant / après, coûts réalistes**

| | Mise au point | | | | Vérification | | | | |
|---|---|---|---|---|---|---|---|---|---|
| | Trades | R/trade | Total | Pire baisse | Trades | R/trade | Total | Pire baisse | Écart vs v5 |
| **v5 actuelle** | 1 371 | +0,085 | +116R | -138R | 554 | +0,230 | +127R | -29R | |
| F1. Stop à la clôture M5, secours 0,5R plus loin | 1 371 | +0,119 | +163R | -160R | 554 | +0,294 | +163R | -25R | +36R (t = 1,3) |
| F1b. Le même à risque égal | 1 371 | +0,079 | +109R | -107R | 554 | +0,196 | +109R | -17R | -19R |
| F2. Pas de trade si spread > 10 % du range | 1 071 | +0,164 | +175R | -53R | 551 | +0,234 | +129R | -26R | +2R |
| F3. Pas de trade les jours fériés US ni les demi-séances | 1 335 | +0,100 | +134R | -126R | 541 | +0,254 | +137R | -24R | +10R (t = 2,9) |
| F4. Pas de trade contre un biais H4 net | 1 091 | +0,143 | +156R | -99R | 429 | +0,294 | +126R | -29R | -1R |
| F5. Coût + stop à la clôture + entrée à 9:35 | 1 028 | +0,234 | +241R | -54R | 511 | +0,267 | +136R | -23R | +9R (t = 0,3) |

Autres mesures sur la vérification :

| | Réussite | Profit factor | Série de pertes | Stops de départ | dont mèches |
|---|---|---|---|---|---|
| v5 | 31 % | 1,39 | 13 | 57 % | 18 % |
| F1 | 36 % | 1,45 | 9 | 50 % | 9 % |
| F2 | 31 % | 1,40 | 13 | 57 % | 19 % |
| F3 | 32 % | 1,44 | 13 | 56 % | 18 % |
| F4 | 31 % | 1,49 | 12 | 58 % | 20 % |
| F5 | 35 % | 1,40 | 8 | 51 % | 9 % |

R par année, coûts réalistes (la coupe tombe en avril 2023) :

| | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v5 | -59 | -25 | -37 | +90 | +27 | +33 | +37 | +40 | +55 | +20 | +37 | +24 |
| F1 | -68 | -31 | -46 | +138 | +19 | +31 | +54 | +58 | +55 | +37 | +56 | +24 |
| F2 | -29 | -1 | +2 | +59 | +25 | +35 | +35 | +40 | +58 | +20 | +37 | +24 |
| F3 | -52 | -21 | -34 | +86 | +35 | +34 | +37 | +41 | +58 | +22 | +41 | +25 |
| F4 | -50 | -10 | -18 | +97 | +30 | +34 | +40 | +43 | +43 | +3 | +40 | +30 |
| F5 | -28 | -5 | -1 | +99 | +18 | +35 | +58 | +53 | +56 | +11 | +57 | +25 |

### F3 — Pas de trade les jours fériés US ni les demi-séances · confiance moyenne

- Tient sur les deux périodes (+18R puis +10R) et avec les trois hypothèses de coûts (t de 1,9 à 3,3).
- Raison simple : ces jours-là la bourse est fermée ou ferme à 13:00. Il n'y a pas de vraie ouverture à casser, et la
  sortie de 15:50 n'existe pas.
- Limite : 36 trades retirés sur la mise au point, 13 sur la vérification. C'est sous ton seuil de 100 : sur ces seuls
  trades, **pas assez de données** pour conclure par les chiffres. L'argument est d'abord logique.
- Sauvé : 2023-09-04 (Labor Day), achat à 9:35 à 15 539,9, stop 15 527,7 touché à 10:15 → -1,26R évité.
  2024-05-27 (Memorial Day), achat à 9:35 à 18 834,3, stop touché à 10:05 → -1,14R évité.
- Rendu pire : 2018-07-03 (demi-séance), vente à 9:35 à 7 101,3, sortie à 13:10 à 7 005,8 → +6,48R perdu.
  2024-07-04, vente à 9:35 à 20 151,5 → +0,33R perdu.

### F1 — Stop jugé à la clôture M5, stop de secours 0,5R plus loin · confiance faible

- Sur le papier : +48R puis +36R, deux fois moins de mèches (18 % → 9 %), 9 pertes de suite au lieu de 13.
- Le prix : quand le stop saute, la perte moyenne passe de -1,03R à -1,28R, et 82 trades de la vérification perdent plus
  de 1,5R. À risque égal (F1b), le total baisse de 19R.
- **Le problème** ([sorties/07_bougie_entree.md](sorties/07_bougie_entree.md), mise au point) :

  | Cas | Jours | Écart F1 - v5 |
  |---|---|---|
  | La v5 est stoppée dans la bougie d'entrée (ordre inconnu en M5) | 163 | **+52R** |
  | La v5 est stoppée plus tard (ordre sûr) | 674 | **-5R** |

  Quand l'entrée et le stop sont dans la même bougie, le test compte un stop plein pour la v5. Si le stop a été touché
  *avant* l'entrée, la vraie v5 n'est pas stoppée non plus, et il n'y a rien à sauver. Sans ces jours ambigus, F1 fait
  entre -48R et +48R : on ne peut pas trancher.
- Je n'ai pas refait ce découpage sur la vérification : c'aurait été une seconde lecture. Mais deux des trois plus gros
  trades « sauvés » de la vérification sont de ce type (2025-04-24 et 2024-07-17, v5 stoppée à 9:35).
- Le gain repose sur peu de jours : sur la mise au point, 5 jours font +81R, et sans eux l'écart est de -33R.
- Sauvé : 2024-04-19, vente à 9:35 à 17 299,7, stop 17 347,6. La v5 est stoppée à 9:40 (-1,03R) ; la variante tient et
  sort à 15:45 à 17 008,7 (+10,07R).
- Rendu pire : 2023-11-29, achat à 9:35 à 16 150,2, stop 16 106,4. La v5 perd -1,05R à 10:05 ; la variante sort au stop de
  secours à 16 084,4 (-1,58R).

### F2 — Pas de trade si le spread dépasse 10 % du range · confiance nulle pour l'avenir

- +60R sur la mise au point, pire baisse divisée par 2,6. Tout vient de 2015-2017, quand le range faisait 9 points.
- Sur la vérification : 3 trades retirés, +2R. Le range fait aujourd'hui 40 à 90 points pour 1 à 1,5 point de spread.
- Utile seulement comme garde-fou si les ranges redevenaient minuscules.
- Sauvé : 2017-03-13, achat à 9:35 à 5 391,6, stop 5 383,0 → -1,92R évité. Rendu pire : 2018-03-27, vente à 9:35 à
  6 769,4, sortie à 15:45 à 6 491,0 → +16,84R perdu.

### F4 — Pas de trade contre un biais H4 net · confiance nulle

- +40R sur la mise au point, -1R sur la vérification, avec 125 trades en moins.
- Rendu pire : 2024-07-11, vente à 9:40 à 20 643,0, sortie à 15:45 à 20 253,3 → +19,76R perdu.
  Sauvé : 2024-05-17, vente à 9:35 à 18 547,3, stop touché à 9:35 → -1,07R évité.

### F5 — Filtre de coût + stop à la clôture + entrée à 9:35 seulement · confiance faible

- +125R sur la mise au point, +9R sur la vérification (t = 0,3). C'était la meilleure de 466 : le gain s'est évaporé,
  comme la correction pour le nombre d'essais l'annonçait.
- Elle hérite du problème de F1 : sans les jours ambigus, -27R sur la mise au point.

## 6. Limites et ce qui a été laissé de côté

- **Or** : aucune donnée, rien n'a été testé.
- **Stop à la clôture M1** : pas de données M1. Le même manque empêche de trancher F1.
- **Annonces économiques** : pas de calendrier. Seules des approximations ont été testées (premier vendredi du mois,
  bougie de 8:30 anormale, bougie de 10:00). CPI et FOMC ne sont pas datés.
- **Rollover** : sans objet, tout est fermé à 15:50.
- **Stratégie H4 / swing / Fibonacci de ta demande** : elle n'est pas dans le dépôt. Je ne l'ai pas inventée.
- **Spread** : celui de Dukascopy. Celui de ton courtier peut changer tous les totaux.
- **Pyramide de taille 2** : meilleur total seul, écartée des finalistes. Elle n'agit pas sur les stops.
- **La pyramide actuelle** est sensible à son réglage : sur la mise au point, coûts du code, l'ajout à +1,5R donne +250R,
  à +2R +229R, à +2,5R +108R, à +3R +73R. Ce n'est pas le sujet de cette recherche, mais c'est à savoir.

## 7. Décisions qui t'attendent

1. **Jours fériés (F3)** : l'ajouter ou non au script TradingView et à l'EA. C'est le seul changement que je défendrais.
2. **Glissement** : relever sur 20 à 30 trades réels l'écart entre le niveau et le prix exécuté chez ton courtier. Tant
   que ce chiffre n'est pas connu, le vrai total de la v5 est quelque part entre +116R et +233R sur la mise au point.
3. **Données M1** : en ajouter au dépôt si tu veux trancher le stop à la clôture et les 12 % de trades où l'entrée et le
   stop sont dans la même bougie.
4. **Or et stratégie H4/swing** : me dire si elles existent ailleurs, ou si l'ORB v5 est bien le bot à suivre.
