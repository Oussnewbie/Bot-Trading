# Rapport final — Stratégie Nasdaq (US100 / NQ)

Date : 20 et 21 novembre 2026. Données : Nasdaq CFD Dukascopy à la minute, bid et ask, du 2 janvier 2018 au 18 novembre 2026
(fournies par toi). Coûts comptés partout : spread réel des données + 1 point de glissement à chaque exécution.
« R » = la somme risquée sur un trade (si le stop est touché, on perd 1R).

## En bref

1. **Ta v6 est solide** : je l'ai reproduite à l'identique (mêmes 1 391 jours de trade que ton fichier de référence) et
   aucune des 8 familles de stratégies alternatives testées ne la bat.
2. **On ne peut pas prédire un stop un par un.** Les modèles font à peine mieux que pile ou face, et écarter les trades
   « risqués » fait perdre des grosses journées.
3. **Mais j'ai trouvé un schéma qui se répète, et il tient sur des données jamais vues** : après un trade gagnant, le
   signal suivant est mauvais (−0,39 R en moyenne sur 246 cas, perdant 8 années sur 9). Les grosses journées n'arrivent
   presque jamais deux fois de suite.
4. **Recommandation : l'ORB v7** = la v6 + « après un trade gagnant, on saute le signal suivant » + aucun ordre les jours
   de décision de la Fed et les jours fériés. Gain moyen par trade de +0,34 R à +0,55 R, pire baisse de 32 R à 22 R,
   gain total plus élevé avec 23 % de trades en moins. Le risque par trade ne change pas.
5. **Compléments (sections 10 à 13)** : CHoCH M1, 216 combinaisons, 187 indicateurs à l'entrée, 57 règles de gestion.
   Aucun indicateur ne filtre les stops, et les briques CHoCH font baisser le gain. Trois réglages ressortent et sont
   codés comme options coupées par défaut : tendance H4, SAR M5, sortie à 10:30. Ce sont des candidats, pas des preuves.
   Le CHoCH, testé de 83 façons (réglage, lecture en contexte, stratégie de retournement), n'apporte rien à la v7.
6. **Ce qui ne change pas** : environ 6 trades sur 10 finissent toujours en stop, et le gain dépend toujours d'une
   poignée de grosses journées.
7. **Strategy V8 (sections 14 et 15)** : la v7 + une entrée sur repli vers le prix moyen de séance (VWAP) + une entrée à
   10:00, chacune plafonnée au risque et aux lots de la cassure. Sur 2018-2026 : +986 R au lieu de +591 R, pour une pire
   baisse de 38 R au lieu de 22 R. Elle est **codée** (robot MT5 et script TradingView) et **compilée sans erreur** par
   MetaEditor et par l'analyseur de TradingView, comme la v7 et ta v6. Elle n'a pas encore été vue en train de tourner
   (le testeur de MetaTrader exige un compte) : testeur puis démo d'abord. C'est un candidat trouvé sur tout l'historique.

![Courbes de gain](resultats/courbes_2018_2026.png)

## 1. Ce que j'ai fait

- Contrôlé les données (3 millions de minutes) : propres, heure de New York vérifiée, spread réel mesuré (1,1 à 1,4 point).
- Écrit un moteur qui rejoue les trades minute par minute avec le bid et l'ask, selon les règles exactes de ton EA.
- Séparé l'historique en deux : **recherche** (2018-2024) et **coffre-fort** (janvier 2025 à novembre 2026). Tout a été
  cherché sur la première partie. Le coffre-fort n'a été ouvert qu'une fois, à la fin, avec des critères écrits à l'avance.
- Testé **149 variantes** avant d'ouvrir le coffre-fort (environ 770 avec les compléments des sections 10 à 14), toutes inscrites
  dans un registre, pour pouvoir corriger l'effet « à force de chercher, on finit par trouver quelque chose ».

## 2. Ce qui marche

| | ORB v6 | ORB v7 (recommandée) |
|---|---|---|
| **Recherche 2018-2024** | | |
| Trades | 1 113 | 856 |
| Gain moyen par trade | +0,36 R | +0,56 R |
| Gain total | +397 R | +475 R |
| Pire baisse | 32 R | 22 R |
| Pire série de pertes | 15 | 12 |
| **Coffre-fort 2025-2026 (jamais vu)** | | |
| Trades | 281 | 217 |
| Gain moyen par trade | +0,28 R | +0,54 R |
| Gain total | +79 R | +116 R |
| Pire baisse | 26 R | 19 R |
| Pire série de pertes | 11 | 10 |
| **Ensemble 2018-2026** | | |
| Trades par an | 157 | 121 |
| Trades gagnants | 20 % | 22 % |
| Trades finissant en stop | 64 % | 62 % |
| Gain moyen par trade | +0,34 R | +0,55 R |
| Gain total | +476 R | +591 R |
| Facteur de profit (gains ÷ pertes) | 1,48 | 1,78 |
| Années positives | 9 sur 9 | 9 sur 9 |
| Avec 2 points de glissement | +0,18 R | +0,38 R |

**D'où vient l'amélioration ?** Presque entièrement de la règle de mémoire. Les jours FOMC et jours fériés ajoutent peu
(une soixantaine de trades en 9 ans).

**Pourquoi la mémoire fonctionnerait-elle ?** Une journée de tendance est souvent suivie d'une journée de consolidation,
où les cassures d'ouverture échouent. Après un trade gagnant, le prix n'atteint +2R que dans 18 % des cas contre 32 %
d'habitude, et la pyramide se déclenche deux fois moins souvent. J'ai vérifié que ce n'est pas un effet déguisé de la
taille du range, de la volatilité ou de l'amplitude de la veille : l'effet est là dans tous ces cas, à l'achat comme à la vente.

## 3. Ce qui ne marche pas

- **Prédire le stop.** Score de 0,52 à 0,54 sur des trades jamais vus (0,50 = hasard). Les trades jugés « les plus
  risqués » contenaient un quart des plus grosses journées : les écarter fait perdre de l'argent.
- **Les autres stratégies** (coûts compris, 2018-2024) : élan de la première demi-heure (≈ 0 R), élan de fin de séance
  (−0,06 R), comblement du gap (−0,01 à −0,07 R), retour à la moyenne après extension (−0,25 à −0,33 R, perdant chaque
  année), tendance autour du prix moyen de séance (≈ 0 R), élan séance européenne vers américaine (≈ 0 R). Le repli sur
  le bord du range après cassure égale la v6 sans faire mieux (+0,35 R, pire baisse 78 R).
- **Changer d'unité de temps.** Range de 1 minute : +0,24 R mais pire baisse de 94 R, tué par les coûts. Range de 3 minutes :
  +0,34 R, pire baisse 61 R. Range de 10 à 30 minutes : +0,05 à +0,13 R. Le M5 reste le meilleur.
- **Modifier la gestion.** Objectif de gain fixe, stop suiveur, stop plus serré, sortie avant 15:50, suppression de la
  pyramide : tout dégrade. Les réglages actuels (stop à l'entrée à +1,5R, pyramide à +2R) sont sur un plateau correct.
- **Journée étroite la veille** (idée classique de « compression ») : aucun effet.
- **Bougie d'ouverture « franche », pré-marché calme** : ressortaient à l'autopsie, ne tiennent pas sur les années non vues.
- **Le modèle à 46 indicateurs** (méta-labeling) : ne fait pas mieux que la règle de mémoire seule. On garde la règle.

## 4. Réponse à ton idée centrale

*« Si les stops suivent un schéma qui se répète, on peut apprendre à le reconnaître avant l'entrée. »*

À moitié vrai. Le stop lui-même n'est pas prévisible : le taux de stops ne bouge presque pas (64 % → 62 %). Ce qui est
prévisible, c'est **l'absence de grosse journée** : le lendemain d'un gain, le trade n'a presque aucune chance de
devenir un gros gagnant, donc il ne vaut pas son risque. On n'évite pas les stops ; on évite les jours où le billet de
loterie est mauvais.

## 5. La stratégie recommandée : ORB v7

Tout ce qui suit s'ajoute à la v6, qui reste inchangée (range M5 de 9:30, filtres RSI et élan, ordres jusqu'à 9:45,
stop de l'autre côté, stop à l'entrée à +1,5R, pyramide de 2 unités à +2R, sortie 15:50).

1. **Règle de mémoire.** Après un trade pris qui finit à plus de +0,05 R, le signal suivant n'est pas pris. Ce jour-là
   l'EA ne pose aucun ordre ; il regarde seulement si la cassure se serait déclenchée. Si oui, la règle est « consommée »
   et le trading reprend. Sinon (pas de cassure), elle reste en attente pour le jour suivant.
2. **Aucun ordre les jours de décision de la Fed (FOMC).**
3. **Aucun ordre les jours fériés américains et les demi-séances.**

Les règles 2 et 3 ne touchent pas à la mémoire. Aucune de ces règles n'augmente le risque : elles retirent des trades.

Fichiers : `strategies/ORB-v7.mq5` (MetaTrader 5), `strategies/ORB-v7.pine` (TradingView), notice dans
`strategies/LISEZMOI.md`. Chaque règle a son interrupteur dans les réglages.

## 6. À quoi s'attendre

Simulation sur 10 000 années tirées au hasard dans l'historique 2018-2026 (par blocs, pour garder les séries) :

| Sur un an | ORB v6 | ORB v7 |
|---|---|---|
| Gain médian | +52 R | +64 R |
| Mauvaise année (1 sur 20) | −9 R | +7 R |
| Risque d'une année négative | 8 % | 3 % |
| Pire baisse habituelle (médiane) | 21 R | 17 R |
| Pire baisse probable (19 cas sur 20) | 40 R | 31 R |
| Pire baisse extrême (99 cas sur 100) | 52 R | 40 R |
| Série de pertes à prévoir (19 cas sur 20) | 17 | 16 |

**En clair** : même avec la v7, il faut s'attendre à des séries de 10 à 16 pertes d'affilée et à des baisses de 17 à 31 R
dans une année normale. Avec 0,5 % de risque par trade, 31 R font 15,5 % du compte ; avec 0,25 %, environ 8 %.
Si ton compte a une limite de perte maximale (10 % chez beaucoup de sociétés de financement), règle le risque par trade
pour que 40 R restent en dessous. Ce sont des ordres de grandeur tirés du passé, pas une promesse.

## 7. Les preuves anti-hasard

| Contrôle | Ce qu'il vérifie | Résultat |
|---|---|---|
| Coffre-fort 2025-2026 | Que la règle marche sur des données jamais utilisées | 4 critères sur 4 remplis ; les 51 trades sautés ont perdu 0,50 R en moyenne ; chance que ce soit du hasard : 2 % |
| Stabilité par année | Que ça ne vient pas d'une seule bonne année | v7 positive 9 années sur 9 ; trades sautés perdants 8 années sur 9 |
| Fenêtres glissantes de 12 mois | Que ça marche quelle que soit la période | 99 % des fenêtres positives (v6 : 96 %) |
| Sensibilité aux réglages | Un plateau, pas un pic isolé | La mémoire améliore le gain moyen dans 21 réglages de base sur 21 ; même résultat avec un seuil de gain de 0,05 R, 1 R ou 2 R |
| Probabilité de surajustement (PBO) | On choisit la meilleure variante sur une moitié des données et on regarde son classement sur l'autre | 14 à 20 % sur les 149 variantes (50 % = choix au hasard) |
| Correction du nombre d'essais | Qu'avec 149 essais on n'a pas juste eu de la chance | Seuil exigé : 3,6. v6 : 3,3 (échoue de peu). v7 : 4,2 (passe) |
| Glissement à 2 et 3 points | Que ça survit à une mauvaise exécution | v7 : +0,38 R à 2 pts sur 2018-2026, +0,20 R à 3 pts sur 2018-2024 (v6 : +0,18 R et +0,06 R) |

Une version plus sévère de la correction du nombre d'essais fait échouer tous les candidats, v6 comprise. Elle est faussée
par les stratégies de retour à la moyenne, très perdantes, qui gonflent la dispersion des résultats ; je la signale par honnêteté.

## 8. Risques et limites

- **La v7 n'a jamais été compilée ni exécutée**, pas plus que ta v6 (c'est écrit dans ton README). Je n'ai pas MetaTrader
  ici. Compile-la, corrige ce que le compilateur signale, et fais-la tourner en démo avant tout.
- **Le coût d'exécution est le point faible.** Chaque point de glissement en plus coûte 0,15 à 0,2 R par trade. L'EA
  affiche le glissement de chaque entrée : relève-le quelques semaines chez ton courtier.
- **La mémoire reste une régularité statistique**, pas une loi. Le coffre-fort la confirme, mais sur 51 trades seulement.
  Elle peut s'affaiblir. Je n'ai qu'un instrument et qu'une source de données.
- **FOMC et jours fériés** : le sens est logique et confirmé dans le coffre (13 trades, −0,97 R en moyenne), mais
  l'échantillon est trop petit pour être une preuve.
- **Le gain reste concentré** : moins de 4 % des trades font tout le résultat. Manquer une grosse journée (panne, VPS
  éteint, ordre refusé) coûte cher.
- **Le coffre-fort est maintenant « usé »** : il a servi une fois pour la v7, puis une seconde fois pour la famille
  « tendance ». Toute nouvelle idée testée sur 2025-2026 ne serait plus un test propre.
- **Dates FOMC** : incluses jusqu'à décembre 2026. À compléter chaque année dans les réglages, sinon l'EA trade ces jours-là.
- **Tes acquis précédents** (RSI 65/35) avaient été trouvés sur tout l'historique : je n'ai pas pu les valider proprement.
  Pour information, le RSI 65/35 seul fait +0,71 R sur 142 trades dans le coffre, avec une pire baisse de 15 R : c'est
  une option « prudente » qui divise le nombre de trades par deux. Pendant la recherche, la mémoire n'ajoutait presque rien par-dessus.

## 9. Prochaines étapes

0. **Strategy V8** : lancer `Strategy-V8.mq5` dans le testeur de stratégie de MetaTrader (compte « hedging »), m'envoyer
   le rapport HTML pour comparaison, puis démo. Coller `Strategy-V8.pine` sur TradingView (notice : `strategies/LISEZMOI.md`).
1. La v7 et la V8 se compilent sans erreur (vérifié le 21 novembre 2026 avec MetaEditor) : plus rien à corriger de ce côté.
2. Lancer la v7 ou la V8 en démo. Vérifier sur quelques semaines : le message « règle mémoire » après chaque gain, l'absence
   d'ordre les jours FOMC, le glissement réel.
3. Comparer, sur TradingView, la v7 avec la mémoire activée puis désactivée, pour voir l'effet de tes propres yeux.
4. Ajouter les dates FOMC de 2027 dès leur publication par la Réserve fédérale.
5. Dans 6 à 12 mois, rejuger la règle de mémoire sur les nouvelles données (elles seront un nouveau coffre-fort).
6. Si tu veux aller plus loin : tester la mémoire sur un autre indice (S&P 500, DAX) serait la meilleure preuve
   indépendante. Une piste expérimentale de « score » existe aussi (`resultats/14_score_experimental.md`) :
   +0,63 R et pire baisse de 12 R dans le coffre, mais plus fragile et plus lourde à coder.

## 10. Complément : peut-on peaufiner la v7 avec la structure M1 (CHoCH) ou la tendance H1 / H4 ?

Demandes faites après le premier rapport. Tout est testé sur **les trades gardés par la v7**, avec les idées et les critères
écrits avant chaque test. 31 variantes de plus (180 au total à ce stade). **La v7 par défaut reste inchangée.**

### Structure M1 (CHoCH, cassure de structure, prise de liquidité, fair value gap) — 18 variantes, 2018-2024

| Usage | Résultat (v7 : +0,56 R par trade, +475 R, pire baisse 22 R) |
|---|---|
| Filtre : structure M1 alignée avant l'entrée | Sans effet : 91 % des trades v7 ont déjà une structure alignée (les filtres de la v6 le garantissent) |
| Filtre : prise de liquidité avant la cassure | L'inverse de la théorie : après un balayage, +0,09 à +0,41 R ; sans balayage, +0,60 à +0,72 R |
| Filtre : fair value gap dans le sens | Sans effet (+0,51 R avec, +0,62 R sans) |
| Entrée sur repli + CHoCH M1, stop sous le repli | Évite 284 perdants et ne rate aucun gagnant, mais ne gagne que +218 à +250 R : on entre 13 à 18 minutes plus tard, plus cher, et le stop plus court saute plus souvent |
| Sortie anticipée sur CHoCH contraire | Voir ci-dessous |
| Stop suiveur sous le dernier creux (M1 ou M5) | +0,04 R (M1) et +0,27 R (M5) : coupe les grosses journées |
| Pyramide sur repli + CHoCH au lieu de l'ajout à +2R | +0,26 / +0,30 R ; sur les trades à pyramide, +2,96 R en moyenne au lieu de +3,83 R |

**« Le CHoCH divise les stops par presque 3 : pourquoi ne pas le prendre ? »** Parce qu'il divise aussi le gain :

| | v7 | v7 + sortie sur CHoCH contraire |
|---|---|---|
| Trades finissant en stop plein | 64 % | 24 à 27 % |
| Trades gagnants | 22 % | 27 à 32 % |
| Gain moyen par trade | +0,56 R | +0,19 à +0,24 R |
| Gain total 2018-2024 | +475 R | +165 à +205 R |
| Pire baisse | 22 R | 26 à 31 R |
| Pire série de pertes | 12 | 12 |
| Grosses journées conservées (> 5R) | 84 | 32 à 44 |

Un stop plein devient une petite perte, mais reste une perte : la série de pertes ne raccourcit pas. Et sur les 525 trades
coupés par la règle, 334 auraient fini en stop (0,75 R économisé chacun, soit +250 R) mais 128 auraient fini gagnants
(4,27 R perdu chacun, soit −547 R). C'est le même piège que le « verrou à +0,4R » de tes acquis : plus joli, moins rentable.
Ta propre règle le dit : un meilleur taux de réussite ne compte que si le gain moyen ne baisse pas.

### Tendance H1 / H4 / jour (MA200, EMA50, VWAP) — 12 filtres

Résultats sur 2018-2024, trades dans le sens de l'indicateur / à contre-sens :

| Filtre (prix du bon côté de…) | Stops pleins | Gain moyen | Effet sur le gain total |
|---|---|---|---|
| MA200 en H1 | 57 % / 55 % | +0,69 R / +0,36 R | −123 R |
| MA200 en H4 | 56 % / 57 % | +0,68 R / +0,39 R | −149 R |
| EMA50 en H1 | 56 % / 57 % | +0,63 R / +0,40 R | −116 R |
| Pente de la MA200 H1 | 54 % / 59 % | +0,74 R / +0,34 R | −132 R |
| MA200 en jours | 56 % / 59 % | +0,60 R / +0,28 R | −99 R |
| VWAP de la session, de la semaine, de la veille | 56-58 % / 53-56 % | +0,54 à +0,57 R / +0,53 à +0,61 R | −113 à −174 R |

- **Les indicateurs de tendance ne filtrent pas les stops** : même taux dans le sens et contre la tendance, sur 2018-2024
  comme sur 2025-2026 (52 % / 51 % pour la MA200 H1).
- Les trades dans le sens des moyennes mobiles gagnent un peu plus par trade. Les VWAP n'apportent rien de stable.

**Sur mes critères.** J'exigeais trois choses : trades gardés meilleurs au moins 5 années sur 7, moins de 2 chances sur
1 000 que ce soit du hasard (seuil durci parce que 30 variantes ont été essayées), et gain total non réduit de plus de 10 %.
Ce troisième critère était le mien, pas le tien. Relus avec les tiens seulement (gain moyen plus haut, pire baisse plus
faible, série pas plus longue, régularité), 7 filtres de tendance sur 12 passent sur 2018-2024. Il leur manquait la preuve :
avec des résultats aussi dispersés, mon échantillon ne peut distinguer du hasard qu'un écart d'au moins 0,45 R, et celui de
la MA200 H1 est de 0,33 R. « Pas prouvé » ne veut pas dire « faux ».

**Second regard sur 2025-2026** (annoncé à l'avance, une seule hypothèse jugée : la MA200 H1). Trades dans le sens : +0,73 R ;
à contre-sens : +0,29 R. Même sens, même ampleur que pendant la recherche. Mais une année sur deux seulement (en 2025 c'est
l'inverse), et 21 % de chances que ce soit du hasard sur cette période seule ; 7 % sur 2018-2026 entier. C'est une
indication favorable, pas une preuve.

**Rejouée comme l'EA la jouerait** (filtre d'abord, mémoire ensuite), l'option MA200 H1 donnait sur 2018-2026 : 70 trades par an,
+0,65 R par trade, +400 R au total (v7 : 121 trades, +0,55 R, +591 R). Elle a depuis été remplacée par un signal de tendance
mieux étayé, trouvé par le balayage de la section 11.

### Pourquoi presque rien de tout cela ne marche

Le taux de stops de cette stratégie est presque une constante (environ 6 sur 10), quel que soit le contexte. Le gain
vient de la queue : quelques journées qui partent sans se retourner. Le CHoCH est un outil pour repérer les retournements ;
appliqué à une stratégie qui vit des journées sans retournement, il coupe précisément ce qui paie. Et un filtre n'est utile
que s'il retire des trades perdants en moyenne : seule la règle de mémoire le fait nettement. L'idée derrière elle n'est
d'ailleurs pas « bête » : c'est le vieux principe « après une expansion vient une contraction », écrit en une ligne.

Détails : `resultats/16_structure_smc.md`, `17_structure_pyramide.md`, `18_tendance_h1_h4.md`, `19_tendance_coffre.md`,
`19_tendance_2018_2026.md`, `19_option_tendance.md`.

## 11. Combinaisons et balayage large d'indicateurs

Demandes suivantes : « la meilleure combinaison » des briques CHoCH et du biais H1 / H4, puis VWAP, MA200, Fibonacci, MACD
et d'autres indicateurs, sur plusieurs unités de temps, pour l'entrée, la gestion et la sortie.

**À lire avant les chiffres.** Tout ce qui suit est mesuré sur 2018-2026 entier, à ta demande et sans seuil d'acceptation.
Il n'existe plus de données jamais vues : ce sont des **candidats**, pas des preuves. Environ 470 essais de plus ont été
faits ici (environ 650 depuis le début). Pour ne pas se raconter d'histoire, chaque volet indique ce que le hasard seul
aurait produit avec autant d'essais.

### 11.1 Les 216 combinaisons (biais H1 / H4 x 4 briques CHoCH), rejouées comme l'EA

| Ratio | Meilleure combinaison | Son résultat | La v7 | Rang de la v7 |
|---|---|---|---|---|
| Gains ÷ pertes | v7 + biais MA200 H4, aucune brique CHoCH | 2,00 | 1,78 | 13e sur 216 |
| Gain total ÷ pire baisse | la v7 elle-même | 26,8 | 26,8 | 1re |
| Gain moyen par trade | v7 + biais MA200 H4, aucune brique CHoCH | +0,69 R | +0,55 R | 4e |
| Taux de réussite | biais H4 + entrée CHoCH + pyramide sur repli + stop suiveur M1 | 44 % | 22 % | 204e |

- Les quatre briques CHoCH font baisser le résultat, seules comme combinées. En moyenne sur la grille : sortie CHoCH, +0,04 à
  +0,07 R par trade contre +0,23 R sans ; stop suiveur, +0,03 à +0,08 R contre +0,23 R.
- Les empiler maximise le taux de réussite (44 %) et ne laisse que +0,17 R par trade et +62 R au total (v7 : +591 R).
- Le biais de tendance est la seule brique qui monte les ratios.
- Test de l'année mise de côté (on choisit la meilleure sur 8 années, on la juge sur la 9e) : « meilleure selon gains ÷ pertes »
  donne 1,62, moins que la v7 (1,78). « Meilleure selon le gain moyen » donne +0,64 R contre +0,55 R, pour +361 R contre +591 R.

### 11.2 187 indicateurs lus à l'entrée (M5, M15, H1, H4, jour)

Moyennes mobiles simples et exponentielles (20 à 200), pentes, croisements, MACD (3 réglages), RSI (7, 14, 21), ADX et DI,
Bollinger, stochastique, Ichimoku, Supertrend, SAR parabolique, VWAP (session, semaine, mois, veille), zones de Fibonacci
(veille, nuit, 5 et 20 jours).

- **Aucun ne filtre les stops.** 14 semblent le faire au seuil habituel ; le hasard seul en donnerait environ 9 ; aucun ne
  résiste à la correction.
- **Pour le gain, l'effet est collectif** : près de 9 indicateurs de tendance sur 10 vont dans le même sens (trades alignés
  meilleurs de 0,2 à 0,3 R en moyenne). Ce n'est pas un indicateur précis qui compte, c'est « dans le sens de la tendance de fond ».
- **Le meilleur : le sens du mouvement en H4 (DI+ contre DI−, 14 périodes).** Trades alignés +0,97 R, à contre-sens +0,14 R,
  9 années sur 9. En tenant compte des 187 essais, il reste 6 % de chances que ce soit du hasard (limite). Il tient quand on
  décale les bougies H4 (8 alignements testés : +0,81 à +0,97 R contre +0,14 à +0,29 R) et pour des longueurs de 10 à 28.
  Choisi sans connaître l'année jugée, c'est lui qui sort 6 fois sur 9, et il se confirme les 6 fois.
- **Le SAR parabolique M5** écarte 15 % des trades, qui perdent en moyenne 0,23 R (9 années sur 9). Seul, il ne résiste pas
  à la correction (37 %), mais il ne coûte rien au gain total.
- MACD, Fibonacci, Ichimoku, stochastique, Bollinger, VWAP : rien de solide pris isolément.

### 11.3 57 règles de gestion pilotées par des indicateurs (mêmes trades que la v7)

- Aucune n'améliore le gain de façon mesurable (au mieux +0,006 R par trade).
- Sorties sur croisement contraire (moyennes, MACD, SAR, VWAP de séance, Supertrend, RSI) : −0,22 R par trade en moyenne.
- Objectifs en extensions de Fibonacci : −0,21 R en moyenne ; l'objectif à 1,618 R donne 41 % de réussite et +0,07 R par trade.
- « Rendu de gain » de Fibonacci (sortir si le prix rend 38 à 79 % du gain maximal) : −0,11 R. Stop suiveur en ATR : −0,05 R.
- Pyramide conditionnée par un indicateur : sans effet.
- **Seule famille neutre : la sortie au temps.** « Si à 10:30 le trade n'a pas atteint +0,5 R, on sort » : même gain total,
  stops pleins de 55 % à 45 %. Les versions 11:30 et 13:00 donnent pareil.

### 11.4 Les candidats, rejoués comme l'EA les jouerait (2018-2026, 1 point de glissement)

| Profil | Trades par an | Gain moyen | Gain total | Gains ÷ pertes | Pire baisse | Stops pleins | Gain moyen à 2 pts | Risque d'année négative |
|---|---|---|---|---|---|---|---|---|
| **v7 (par défaut, vérifiée sur données jamais vues)** | 121 | +0,55 R | +591 R | 1,78 | 22 R | 55 % | +0,38 R | 3 % |
| v7 + SAR M5 | 102 | +0,66 R | +592 R | 1,94 | 22 R | 54 % | +0,49 R | 3 % |
| v7 + tendance H4 (DI) | 61 | +0,79 R | +425 R | 2,15 | 23 R | 55 % | +0,60 R | 5 % |
| v7 + tendance H4 + SAR M5 | 51 | +0,91 R | +413 R | 2,35 | 18 R | 53 % | +0,72 R | 6 % |
| v7 + sortie à 10:30 | 118 | +0,58 R | +604 R | 1,94 | 26 R | 45 % | +0,38 R | 2 % |
| v7 + tendance H4 + SAR M5 + sortie à 10:30 | 51 | +0,89 R | +399 R | 2,46 | 18 R | 46 % | +0,69 R | 6 % |

Toutes ces lignes sont positives 9 années sur 9 et dans les deux moitiés de l'historique.

### 11.5 Ce que je retiens

- **« Meilleure combinaison pour le meilleur ratio »** : tendance H4 + SAR M5 + sortie à 10:30 (gains ÷ pertes 2,46, contre 1,78).
  Elle ne contient aucune des quatre briques CHoCH. Elle gagne un tiers de moins au total, avec 2,4 fois moins de trades.
- **Le candidat « sans regret »** : v7 + SAR M5. Même gain total, 16 % de trades en moins.
- **La sortie à 10:30** est la seule chose trouvée qui réduit les stops pleins sans coûter de gain. Sa pire baisse observée
  est un peu plus haute (26 R contre 22 R), ses baisses habituelles un peu plus courtes.
- **Statut** : ces trois réglages sont codés dans l'EA et le script comme options, **coupées par défaut**. Ils ont été trouvés
  en fouillant tout l'historique ; la tendance H4 est la mieux étayée. Le vrai test sera la démo et les données à venir.
  Sur TradingView, tu peux déjà comparer la v7 avec et sans chaque option : les données de TradingView ne sont pas celles
  de mon test, c'est donc une vérification en partie indépendante.

Détails : `resultats/20_combinaisons.md`, `21_scan_indicateurs_entree.md`, `22_scan_indicateurs_gestion.md`,
`23_candidats_balayage.md`, `24_annee_mise_de_cote.md`.

## 12. Le CHoCH : ce qui restait à tester

Deux choses n'avaient pas été testées : le CHoCH « lu en contexte » plutôt qu'avec une définition mécanique, et le CHoCH
comme stratégie à part entière. C'est fait, sur 2018-2026 entier (65 essais de plus, environ 715 au total ; toujours pas de
données jamais vues).

### 12.1 CHoCH « lu en contexte », sur les trades de la v7 et sur ses profils (17 lectures)

Structure plus large (vagues d'au moins 0,5, 1 ou 1,5 fois le range), structure M5, cassure avec impulsion, CHoCH au
contact d'un niveau H1 / H4 / jour ; en sortie anticipée et en stop suiveur.

| Lecture | Effet sur le gain moyen par trade (v7 : +0,55 R) |
|---|---|
| Structure très large (vagues ≥ 1,5 range) | +0,002 R : neutre, parce qu'elle ne touche que 14 trades sur 1 073 |
| CHoCH M5, avant le stop à l'entrée | −0,03 à −0,06 R |
| Structure large (vagues ≥ 1 range) | −0,05 à −0,17 R |
| CHoCH M1 au contact d'un niveau H1 / H4 / jour | −0,14 à −0,20 R |
| CHoCH M1 avec impulsion | −0,22 à −0,30 R |
| Structure serrée (vagues ≥ 0,5 range) | −0,24 à −0,40 R |

Plus la structure est fine, plus la règle coupe de grosses journées ; plus elle est large, moins elle fait quoi que ce soit.
Même constat rejoué sur les profils v7 + SAR M5 et v7 + tendance H4 + SAR M5.

### 12.2 CHoCH comme stratégie de retournement (48 variantes)

Règle : le prix dépasse un niveau « frais » (plus haut / bas de la veille, de la nuit, dernier sommet / creux H1 ou H4),
revient du bon côté dans les 30 minutes avec une cassure de structure M1 ou M5 ; entrée dans le sens du retournement, stop
1 point au-delà de l'extrême. Quatre gestions : objectif 2R, objectif 3R, sortie 15:50 avec stop à l'entrée, gestion v6.

- 9 variantes sur 48 ont un gain moyen positif ; la meilleure fait +0,09 R par trade sur 209 trades, ce qui ne se distingue
  pas de zéro. 2 seulement restent positives avec 2 points de glissement. Aucune n'est statistiquement solide.
- En moyenne : −0,05 R par trade avec la gestion v6, −0,07 R avec sortie à 15:50, −0,11 R avec objectif 3R, −0,12 R avec objectif 2R.
- Par niveau : plus haut / bas de la veille −0,24 R ; pivots H4 −0,11 R ; pivots H1 −0,07 R ; nuit −0,03 R.
- Les objectifs fixes donnent 33 à 36 % de réussite, mais un gain moyen négatif.

### 12.3 Avec les combinaisons de la v7

- Filtre de tendance H4 appliqué aux retournements : pas de différence utile (+0,01 R dans le sens, −0,01 R contre, sur 1 606 trades).
- Additionnée à la v7 sur le même compte, la meilleure variante ajoute +18 R en 9 ans (+3 %) et fait monter la pire baisse
  de 22 R à 27 R. Même résultat avec v7 + SAR M5 ; avec le profil sélectif, la pire baisse passe de 18 R à 26 R.

**Conclusion** : sur le Nasdaq et sur ces données, le CHoCH n'apporte rien à la v7, ni comme réglage, ni lu en contexte,
ni comme seconde stratégie. Cela ne dit rien d'un trader qui l'utilise à la main avec d'autres éléments de jugement.

Détails : `resultats/25_choch_contexte.md`, `26_choch_retournement.md`.

## 13. Et si l'ORB servait de filtre plutôt que d'entrée ?

Idée : la cassure d'ouverture ne sert qu'à dire dans quel sens trader ce jour-là ; l'entrée se fait autrement. Deux formes
avaient déjà été testées (repli sur le bord du range : +0,35 R, pire baisse 78 R ; entrée sur CHoCH M1 après la cassure :
+218 à +250 R contre +475 R). Les formes restantes, sur 2018-2026 entier (45 essais de plus, environ 760 au total) :

| Méthode (jours pris par la v7) | Trades par an | Réussite | Gain moyen (1R = son propre stop) | Gain total à taille égale à la v7 | Ajoutée à la v7 : total / pire baisse |
|---|---|---|---|---|---|
| **v7, entrée sur la cassure (référence)** | 121 | 22 % | +0,55 R | +591 R | +591 R / 22 R |
| Repli sur le prix moyen de séance (VWAP), gestion v6 | 92 | 16 % | +0,52 R | +267 R | +858 R / 38 R |
| Repli sur le VWAP, sortie 15:50 | 92 | 24 % | +0,32 R | +183 R | +774 R / 35 R |
| Repli sur la moyenne mobile 20 en M5 | 87 | 12 à 19 % | −0,02 à +0,01 R | +23 à +39 R | — |
| Entrée à 10:00 si la cassure tient, sortie 15:50 | 61 | 48 % | +0,23 R | +244 R | +835 R / 34 R |
| Entrée à 10:30 si la cassure tient, sortie 15:50 | 55 | 53 % | +0,19 R | +233 R | +824 R / 33 R |
| Entrée à 11:00 si la cassure tient | 51 | 51 % | +0,08 à +0,11 R | +131 à +156 R | — |

- **Le sens donné par l'ORB est exploitable autrement** : le repli sur le VWAP et l'entrée à heure fixe sont positifs, 8 ou 9
  années sur 9. C'est une confirmation que l'avantage est bien dans le sens de la cassure.
- **Mais aucune de ces entrées ne fait mieux que la cassure elle-même.** À taille de position égale, elles gagnent 40 à 45 %
  de ce que gagne la v7.
- **Les ajouter à la v7 n'est pas une diversification** : ce sont les mêmes journées. Le gain total monte (+858 R) mais la
  pire baisse monte plus vite (38 R contre 22 R). Augmenter simplement la taille de la v7 de 45 % donnerait le même gain
  avec une pire baisse de 32 R.
- **L'entrée à 10:00 ou 10:30 est la seule variante de toute l'étude à environ 50 % de réussite avec un gain positif**
  (9 années sur 9 pour 10:30). Le prix à payer : un stop 2 fois plus large et un gain par trade 2 à 3 fois plus faible.
- **L'échec de l'ORB comme signal perd nettement** : se retourner quand la v6 touche son stop donne −0,22 à −0,42 R par
  trade, perdant 8 années sur 9. Prendre le côté bloqué par les filtres quand il casse en premier : zéro.
- **L'ORB comme filtre des retournements CHoCH** : les retournements dans le sens de la cassure du jour perdent (−0,06 à
  −0,13 R) ; ceux à contre-sens font +0,07 à +0,17 R, ce qui ne se distingue pas du hasard.

**Conclusion** : l'ORB est un bon filtre de sens, mais la meilleure façon d'exploiter ce sens reste d'entrer sur la cassure.

Détails : `resultats/27_orb_comme_filtre.md`.

### 13 bis. Empiler ces entrées sur la v7 (critère : même risque par trade, le plus gros gain total)

Précision demandée par l'utilisateur : la pire baisse est secondaire, ce qui compte est le gain total à risque par trade
égal. Chaque entrée utilise le même nombre de lots que la v7. 2018-2026, 1 point.

**Correction (voir section 14)** : à lots égaux, l'entrée à 10:00 risquait en réalité environ 1,9 R par trade, parce que son stop
est presque deux fois plus loin. Les colonnes « entrée 10:00 » ci-dessous sont donc surévaluées ; la section 14 refait le calcul
avec au plus 1 R de risque par trade.

| | v7 seule | v7 + repli VWAP | v7 + entrée 10:00 | v7 + repli VWAP + entrée 10:00 |
|---|---|---|---|---|
| Gain total | +591 R | +858 R | +835 R | +1 102 R |
| Gain par an | +67 R | +97 R | +94 R | +124 R |
| Années positives | 9 sur 9 | 9 sur 9 | 9 sur 9 | 9 sur 9 |
| Pire année | +33 R | +37 R | +31 R | +45 R |
| Pire baisse de tout l'historique | 22 R | 38 R | 35 R | 42 R |
| Baisse d'une année type (médiane) | 17 R | 26 R | 22 R | 30 R |
| Baisse d'une mauvaise année (1 sur 20) | 31 R | 50 R | 41 R | 57 R |
| Gain total ÷ pire baisse | 26,8 | 22,5 | 24,2 | 26,1 |
| Jours où la perte dépasse 1,5 R | 1 | 332 | 204 | 421 |
| Pire journée | −3,2 R | −3,9 R | −6,7 R | −7,4 R |
| Gain total avec 2 points de glissement | +407 R | +615 R | +621 R | +830 R |

- **À risque par trade égal, empiler rapporte plus** : +45 % avec le repli VWAP, +86 % avec les deux entrées, toutes les
  années restant positives.
- **Le rapport gain ÷ baisse reste du même ordre** (22 à 27). Empiler revient à peu près à trader la v7 plus gros : la v7
  à taille multipliée par 1,45 donne +857 R pour 32 R de pire baisse à 1 point de glissement, et +589 R pour 56 R à 2 points
  (contre +615 R pour 47 R avec le repli VWAP). Les deux façons se valent.
- **Ce qui change concrètement** : deux ou trois positions peuvent perdre le même jour. Avec le repli VWAP, environ un jour
  de trade sur trois coûte autour de 1,9 R au lieu de 1,1 R.
- **Le repli VWAP n'est pas un réglage chanceux** : 27 réglages voisins testés, tous positifs (+0,40 à +0,53 R par trade,
  +200 à +293 R ajoutés), positif 8 années sur 9.
- Comme tout ce qui suit l'ouverture du coffre : trouvé sur l'historique, pas vérifié sur des données nouvelles.

Détails : `resultats/28_empilement.md`.

## 14. Strategy V8, rejouée sur les données avant tout code

Demande : V8 = v7 + repli VWAP + entrée à 10:00, sans la règle « un trade par jour », à voir sur les données avant de coder.
Rejouée jour par jour sur 2018-2026 (spread réel + 1 point de glissement). Le code a été écrit ensuite : voir la section 15.

**Règle de taille** : chaque trade risque au plus 1 R et n'utilise jamais plus de lots que le trade de la v7.

**Les trois entrées de la V8** (les mêmes jours que la v7 : filtres v6, hors FOMC et fériés, règle de mémoire)

| Entrée | Règle | Trades | Réussite | Gain moyen | Gain total |
|---|---|---|---|---|---|
| A. Cassure | celle de la v7, inchangée | 1 073 | 22 % | +0,55 R | +591 R |
| B. Repli VWAP | après la cassure, première bougie M5 qui touche le prix moyen de séance et repart ; stop sous les 2 dernières bougies M5 ; gestion v6 ; jusqu'à 14:00 | 813 | 16 % | +0,33 R | +269 R |
| C. Entrée à 10:00 | si le prix est toujours au-delà du niveau de cassure ; stop de l'autre côté du range ; environ 0,6 fois les lots de la v7 ; sortie 15:50 | 538 | 48 % | +0,23 R | +126 R |

**V8 contre v7**

| | v7 | V8 |
|---|---|---|
| Trades par an | 121 | 273 (jusqu'à 3 par jour) |
| Gain total | +591 R | +986 R |
| Gain par an | +67 R | +111 R |
| Années positives | 9 sur 9 | 9 sur 9 |
| Pire année | +33 R | +36 R |
| Pire baisse de tout l'historique | 22 R | 38 R |
| Gain total ÷ pire baisse | 26,8 | 26,1 |
| Baisse d'une année type / d'une mauvaise année (1 sur 20) | 16 R / 31 R | 27 R / 49 R |
| Risque d'une année négative | 3,5 % | 3,2 % |
| Pire journée | −3,2 R | −6,7 R |
| Jours perdants d'affilée (maximum) | 12 | 23 |
| Gain total / pire baisse à 2 points de glissement | +407 R / 39 R | +716 R / 51 R |

![V8 contre v7](resultats/v8_courbes.png)

![Deux journées exemples](resultats/v8_exemples.png)

**Lever complètement la règle « un trade par jour » ne rapporte rien de plus**

| Variante | Gain total | Pire baisse |
|---|---|---|
| V8 (un repli VWAP par jour) | +986 R | 38 R |
| 2 replis VWAP par jour | +1 016 R | 47 R |
| Replis VWAP illimités | +1 017 R | 50 R |
| V8 + nouvelle cassure après un stop | +1 006 R | 49 R |
| Replis illimités + nouvelle cassure | +1 037 R | 60 R (une année négative ; à 2 points : +705 R pour 103 R de baisse) |

Seul le premier repli de la journée a un avantage : +0,33 R par trade, contre +0,08 R pour le deuxième et −0,07 R pour le
troisième. Rentrer sur une nouvelle cassure après un stop rapporte +0,08 R par trade. Ces entrées en plus ajoutent environ
3 % de gain pour 25 à 60 % de baisse en plus.

**Ce que la V8 change concrètement**
- Jusqu'à 3 positions ouvertes en même temps (2 ou plus 69 % des jours, 3 dans 41 % des jours). Pyramides comprises,
  l'exposition peut atteindre 7 fois le lot de départ, contre 3 pour la v7 : il faut la marge correspondante.
- Les trois positions vont dans le même sens. Une mauvaise journée coûte environ 3,3 R ; la pire de l'historique
  (10 octobre 2025, retournement brutal avec pyramides ouvertes) a coûté 6,7 R, contre 3,2 R pour la v7.
- Comme tout ce qui a été trouvé depuis l'ouverture du coffre : candidat issu de l'historique (environ 770 essais),
  pas vérifié sur des données nouvelles.

Détails : `resultats/29_v8.md`, listes de trades `resultats/trades_V8*.csv`.

## 15. Strategy V8 : le code, et ce qui a été vérifié

**Ce qui est livré** (dossier `strategies/`)
- `Strategy-V8.mq5` : le robot MetaTrader 5 (2 397 lignes ; la v7 + environ 600 lignes pour les entrées B et C).
- `Strategy-V8.pine` : le script TradingView (1 175 lignes), avec l'affichage demandé pour voir quand entrer.
- `LISEZMOI.md` : installation pas à pas, lecture du graphique, réglages, test à faire chez toi.

**Comment le robot traite les trois entrées**
- A (la cassure) : le code de la v7, inchangé.
- B et C : chacune est une position à part, avec son numéro, son stop chez le courtier, son stop à l'entrée à +1,5 R,
  et pour B sa pyramide à +2 R. Leur taille est calculée au moment de l'entrée : jamais plus de lots que A, jamais plus
  que la somme risquée par A. La marge est réservée dès le matin pour les 7 unités possibles.
- Il faut un compte « hedging ». Sur un compte « netting », le robot coupe B et C et se comporte comme la v7.

**Vérifications faites**

| Vérification | Outil | Résultat |
|---|---|---|
| Le robot V8 se compile | MetaEditor (MetaTrader 5 build 6327, installé pour l'occasion) | 0 erreur, 0 avertissement |
| La v7 et ta v6 se compilent | MetaEditor | 0 erreur, 0 avertissement (première compilation réelle de ces fichiers) |
| Les scripts TradingView V8 et v7 sont corrects | analyseur de l'éditeur Pine de TradingView | 0 erreur, 0 avertissement |
| L'analyseur détecte bien les fautes | 4 versions cassées exprès | 4 sur 4 signalées |
| Les règles codées donnent le résultat du test | rejeu sur les données, avec les mêmes calculs que le code | voir ci-dessous |

Le code diffère du test de la section 14 sur deux détails. Je les ai rejoués pour vérifier qu'ils ne changent rien :

| Version rejouée 2018-2026 | Gain total | Pire baisse | Années positives | À 2 points de glissement |
|---|---|---|---|---|
| Test de la section 14 | +986 R | 37,9 R | 9 sur 9 | +716 R |
| Comme le code : stop de B sur les 2 dernières bougies M5 complètes | +1 008 R | 37,7 R | 9 sur 9 | +741 R |
| Prix moyen (VWAP) calculé sans volume | +979 R | 37,2 R | 9 sur 9 | +716 R (8 sur 9) |
| Les deux à la fois | +1 005 R | 37,7 R | 9 sur 9 | +738 R (8 sur 9) |

Le résultat ne dépend donc ni du volume (qui change d'un courtier à l'autre et sur TradingView) ni de ce détail de stop.
Je garde +986 R comme chiffre de référence : l'écart entre ces lignes est du bruit.

**Ce qui n'a PAS été vérifié**
- Le robot n'a pas été vu en train de tourner. Le testeur de stratégie de MetaTrader refuse de démarrer sans compte de
  courtier (« account is not specified »), même sur des données locales. J'ai chargé tes données dans MetaTrader comme
  symbole de test, mais je n'ai pas ouvert de compte démo à ta place.
- Le backtest TradingView n'a pas été lancé (il faut un compte TradingView).
- À faire chez toi : le test de 10 minutes décrit dans la notice, puis une période de démo.

**Sur TradingView : ce que tu verras**

![Aperçu de l'affichage TradingView](resultats/v8_apercu_tradingview.png)

Dessin fait à partir de deux vraies journées de tes données (une qui gagne, une qui perd), pas une capture d'écran.
- Ligne orange : le prix moyen de la séance (VWAP). Bande bleue : la zone où un repli déclenche B.
- Étiquette bleue « ACHAT B » ou « VENTE B » : la bougie à la clôture de laquelle on entre. Tirets bleus : son stop.
- Trait vertical violet : 10:00. « ACHAT C » si la cassure tient, sinon « C ✕ » avec la raison.
- Le tableau écrit en clair ce qui est attendu pour A, B et C, avec les prix à surveiller.
- Une alerte est envoyée à chaque événement, avec le prix, le stop et le lot à passer chez le courtier.

**Rappel des risques de la V8**
- Jusqu'à 3 positions dans le même sens : une mauvaise journée coûte environ 3 R, la pire de l'historique 6,7 R.
- La pire baisse passe de 22 R à 38 R (51 R avec 2 points de glissement). Règle ton risque par trade en conséquence :
  le même pourcentage par trade donne des creux presque deux fois plus profonds qu'avec la v7.
- Levier : avec 0,5 % de risque, 1:25 suffit 95 % des jours ; avec 1:20 la taille est réduite environ 1 jour sur 8.
- Trouvée sur tout l'historique, après environ 770 essais : candidat, pas preuve. Aucun gain n'est garanti.

Détails : `resultats/29b_v8_verif_code.md`, journaux de compilation dans `resultats/compilation/`.

## 16. Où sont les fichiers

- `rapport.md` : ce rapport. `notes/nasdaq-progress.md` : le journal, pour reprendre plus tard.
- `strategies/` : **Strategy-V8.mq5, Strategy-V8.pine** (et Strategy-V8.ex5 déjà compilé), ORB-v7.mq5, ORB-v7.pine, notice, et `reference-v7.json` (les 1 073 trades de la v7, au format de ton interface Étrave).
- `resultats/` : un fichier par étape (qualité des données, reproduction, autopsie, alternatives, validation, coffre-fort),
  le registre des essais et les grilles des balayages, les listes de trades.
- `scripts/` : tout le code d'analyse. `notes/` : idées écrites avant les tests, règles exactes de la v6, recherche documentaire.
- Les données de prix ne sont pas dans l'archive (trop lourdes) : garde ton fichier d'origine.

## Sources

1. Zarattini et Aziz (2023), ORB 5 minutes sur le Nasdaq — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
2. Zarattini, Barbon et Aziz (2024), ORB sur les actions « en jeu » — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
3. QuantInsti (2026), lecture critique de l'ORB — https://www.quantinsti.com/articles/opening-range-breakout-strategy/
4. Gao, Han, Li et Zhou (2018), élan intrajournalier — https://www.sciencedirect.com/science/article/pii/S0304405X18301351
5. Réplication récente de l'élan intrajournalier — https://temperancecapital.substack.com/p/market-intraday-momentum-replicates
6. Zarattini, Aziz et Barbon (2024), élan intrajournalier sur SPY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
7. Kaminski et Lo (2014), quand un stop aide-t-il ? — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338
8. Bailey, Borwein, López de Prado et Zhu, probabilité de surajustement — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
9. Bailey et López de Prado (2014), Sharpe corrigé du nombre d'essais — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
10. Singh et Joubert, méta-labeling — https://hudsonthames.org/wp-content/uploads/2022/04/Does-Meta-Labeling-Add-to-Signal-Efficacy.pdf

*Ce document n'est pas un conseil en investissement. Aucun gain n'est garanti. Les résultats passés ne préjugent pas des résultats futurs.*
