# Rapport — Stratégie Nasdaq (US100 / NQ) — session 3 : « maximiser le profit »

Date : 21 novembre 2026. « R » = la somme risquée sur un trade (si le stop est touché, on perd 1 R).
Données : ton fichier Nasdaq à la minute 2018 → novembre 2026 (Dukascopy, prix acheteur et vendeur), **plus 7 années que
j'ai trouvées cette session et que personne n'avait jamais regardées : fin 2010 → 2017** (HistData, même marché).
Le rapport de la session précédente (V7, V8) est conservé tel quel dans `rapport-session2.md`.

## En bref

1. **La nouvelle la plus importante n'est pas une stratégie, c'est un examen.** Jusqu'ici, tout avait été cherché et
   « vérifié » sur 2018-2026, la période sur laquelle ta V6 a été mise au point. J'ai trouvé 7 années de données d'avant
   2018 et j'ai fait passer à la V7, à la V8 et à mes nouvelles idées leur **premier vrai examen sur des données jamais vues**.
2. **Verdict : le backtest 2018-2026 est trop beau.** Sur 2010-2017, avec des coûts ramenés à leur poids d'aujourd'hui :
   la V7 gagne 16 R par an (au lieu de 67), la V8 39 R par an (au lieu de 111), avec des baisses 3 fois plus profondes.
   Avec les coûts au poids qu'ils avaient en 2018, **tout perd de l'argent** sur ces 7 années.
3. **L'avantage n'a pas disparu pour autant.** Il reste positif partout dès que les coûts pèsent peu, ce qui est le cas
   aujourd'hui : le Nasdaq vaut 25 000 à 29 000 points, le range d'ouverture fait 60 à 100 points, et un aller-retour
   coûte environ 3 % du risque (c'était 16 % en 2018 et 25 à 35 % en 2014-2017).
4. **Une vraie trouvaille : les « continuations ».** Les jours où la cassure est prise et tant qu'elle est ouverte,
   racheter la cassure de chacune des 3 bougies de 5 minutes suivantes (9:35, 9:40, 9:45) avec un stop court sous la bougie.
   C'est la seule nouveauté qui gagne à la fois sur les données connues et sur les données jamais vues.
5. **Strategy V9 = cassure V7 + repli VWAP + 3 continuations, sans l'entrée de 10:00.**

   | | V7 | V8 | **V9** |
   |---|---|---|---|
   | 2018-2026 (période de recherche) : gain total | +591 R | +986 R | **+1 614 R** |
   | 2018-2026 : pire baisse | 22 R | 38 R | 56 R |
   | 2010-2017 (**jamais vu**, coûts au poids d'aujourd'hui) : gain total | +113 R | +281 R | **+577 R** |
   | 2010-2017 : pire baisse | 64 R | 102 R | 170 R |
   | 2010-2017 avec les coûts au poids de 2018 | −75 R | −159 R | −157 R |

6. **Ce que la V9 ne change pas.** Il n'y a qu'une seule source de gain : la tendance du matin, les bons jours. Empiler des
   entrées, c'est la prendre plus de fois : le gain monte, la baisse aussi. La V9 fait un peu mieux que la V8 à baisse
   égale (+10 % sur les données connues, +23 % sur les données jamais vues), pas davantage.
7. **Recommandation.** Passer à la V9 **en divisant le risque par trade par deux** (0,25 % au lieu de 0,5 % : c'est le
   réglage par défaut des fichiers livrés), démo d'abord, et régler ses attentes sur un scénario prudent (section 6).
8. **Tout le reste a échoué** (section 7) : pyramide à plusieurs étages, cassures à d'autres heures, retournement les
   jours « mémoire », garder les gagnants la nuit, annonces de 8:30 et de la Fed, tri des entrées par un second modèle.

![Courbes sur 16 ans](resultats/v9_courbes_16_ans.png)

## 1. Ce que j'ai fait

- Repris le dossier de la session précédente et retrouvé ses chiffres au centième (V7 +591,33 R, V8 +986,17 R).
- Trouvé et contrôlé 7 années de Nasdaq à la minute d'avant 2018. Piège corrigé : le fournisseur annonce une heure
  fixe, en réalité ses horodatages suivent l'heure d'été de New York. Vérification : sur 2018, année commune, les deux
  sources bougent à 99 % de la même façon, et la stratégie rejouée sur l'une ou l'autre prend le même sens 160 jours sur 160.
- Écrit le protocole avant de chercher : recherche libre sur 2018-2026 ; puis jugement sur 2014-2017 (coffre 2A) ;
  puis confirmation finale sur 2010-2014 (coffre 2B). Chaque ouverture précédée d'une liste écrite de ce qui est jugé et comment.
- Cherché de nouvelles sources de gain sur 2018-2026 : environ 1 000 variantes de plus (environ 1 770 depuis le début), toutes comptées.
- Ouvert les deux coffres, une fois chacun. **Il ne reste plus aucune donnée jamais vue : plus aucun réglage n'est permis.**
- Codé la V9 pour MetaTrader 5 et TradingView, compilée et analysée sans erreur.

## 2. L'examen sur les données jamais vues

**Comment lire les coûts.** Avant 2018 le Nasdaq valait 2 300 à 6 500 points et le range d'ouverture 5 à 10 points.
Compter « 1 point de spread + 1 point de glissement » comme aujourd'hui reviendrait à prélever un tiers du risque à chaque
trade : aucune stratégie n'y survit, et ce n'est pas la question. J'ai donc compté les coûts **en proportion du prix**, à deux niveaux :
- « poids d'aujourd'hui » : ce que pèsent 1,3 point de spread et 1 point de glissement quand le Nasdaq est à 25 000 ;
- « poids de 2018 » : ce que pesaient 1,1 point de spread et 1 point de glissement quand il était à 7 000 (3 fois plus lourd).

**Les 7 années jamais vues réunies (2010-2017), coûts au poids d'aujourd'hui**

| Composante | Gain moyen par trade | 2018-2026 pour comparaison | Solidité (t) | Verdict (règle écrite avant d'ouvrir) |
|---|---|---|---|---|
| Cassure V7 (A) | +0,14 R | +0,55 R | 1,3 | positive, **non prouvée** |
| Règle de mémoire (écart pris − sautés) | +0,25 R | +0,81 R | 1,1 | bon sens, non prouvée ici |
| Repli VWAP (B) | +0,24 R | +0,33 R | 2,0 | **retenue** |
| Continuations 9:35-9:45 (D) | +0,28 R | +0,49 R | 2,3 | **retenue** |
| Continuations 9:50-10:05 | +0,06 R | +0,43 R | 0,6 | non retenues |
| Entrée de 10:00 (C) | +0,04 R | +0,23 R | 0,7 | option coupée par défaut |

« t » est une note de solidité : au-dessus de 1,65 il y a moins de 5 % de chances que ce soit du hasard ; avec 5 questions
posées à la fois, il faudrait 2,33 pour parler de preuve. B et D passent le premier seuil, pas le second.

**Les deux moitiés séparément** (coûts au poids d'aujourd'hui ; chaque moitié n'a été ouverte qu'une fois)

| | Coffre 2A : mi-2014 → 2017 | Coffre 2B : fin 2010 → mi-2014 |
|---|---|---|
| Cassure V7 (A), par trade | +0,19 R | +0,08 R |
| Repli VWAP (B), par trade | +0,23 R | +0,25 R |
| Continuations 9:35-9:45 (D), par trade | +0,39 R | +0,16 R |
| Entrée de 10:00 (C), par trade | −0,04 R | +0,13 R |
| V8, total | +144 R | +137 R |
| V9, total | +380 R | +197 R |

Par honnêteté : le choix « 3 continuations, sans C » a été fait après avoir vu 2A. C'est donc 2B qui le juge vraiment : la V9 y
reste devant la V8, avec un avantage plus mince, et C y est positive (d'où son statut d'option plutôt que de suppression).

**Ce qu'il faut retenir, sans arrondir les angles**
- Avec les coûts au poids de 2018 (ce que j'avais annoncé comme critère principal avant d'ouvrir le premier coffre),
  **rien n'est confirmé** : V7 −75 R, V8 −159 R, V9 −157 R sur 7 ans.
- Avec les coûts au poids d'aujourd'hui, tout est positif mais **2 à 4 fois plus faible** qu'en 2018-2026.
- La cassure elle-même est la composante la moins solide hors échantillon. Les entrées « de confirmation » (B et D), qui
  exigent que la cassure ait déjà fonctionné, tiennent mieux.
- Année par année sur 2010-2017 (V9) : −10, +14, −6, +139, +130, +167, +113, +30. Les trois premières années sont nulles ou négatives.

Détails : `resultats/56_coffre_2A.md`, `61_coffre_2B.md`, `57_controle_source_2018.md`.

## 3. Pourquoi 2018-2026 est-il tellement meilleur ?

Trois raisons, que les données ne permettent pas de séparer complètement :
1. **Les coûts.** Le range d'ouverture représentait 0,15 à 0,25 % du prix avant 2018 contre 0,25 à 0,5 % depuis. À coût
   égal en proportion, chaque trade perdait une plus grande part de son risque.
2. **Le marché.** Même avant coûts, le gain du trade de cassure est d'environ 0,3 R en 2014-2017 contre 0,6 R en
   2018-2026. J'ai cherché un indicateur connu à l'avance qui explique l'écart (volatilité des 14 ou 60 derniers jours,
   taille du range, tendance, moyenne 200 jours) : aucun ne le fait proprement.
3. **Le biais de sélection.** La V6 a été réglée sur 2018-2026. Une stratégie est toujours plus belle sur la période qui
   a servi à la construire. La littérature mesure ce rabais : −26 % pour des anomalies publiées, −73 % en médiane sur le
   ratio rendement / risque de 215 stratégies vendues par des banques (sources 1 à 3).

**Conséquence pratique** : pour l'avenir, attends-toi à un résultat quelque part **entre** la colonne 2010-2017 et la
colonne 2018-2026. Les trois dernières années (2024 : +0,34 R brut par trade A, 2025 : +0,62 R, 2026 : +0,64 R) ressemblent
davantage à l'après-2018.

Détails : `resultats/58_regime.md`, `59_lecons_2A.md`.

## 4. La trouvaille : les entrées de continuation (D)

**L'idée, écrite avant le test** : la V8 avait montré que le sens de la cassure reste exploitable plus tard dans la
journée. J'ai simulé une entrée sur la cassure de *chaque* bougie de 5 minutes de la séance, tous les jours, dans les deux
sens : 143 081 entrées. Une seule poche gagne : **les jours où la V7 trade, dans le sens du trade, tant qu'il est ouvert,
pendant la première demi-heure**. Partout ailleurs (autres jours, autre sens, après 10:30, cassure déjà stoppée), c'est perdant.

**La règle retenue**
- Jours et sens : ceux de la cassure V7 (A), seulement si A est entré et encore ouvert.
- À la clôture de la bougie de 9:35, puis de 9:40, puis de 9:45 : ordre stop sur l'extrême de cette bougie dans le sens du
  trade, valable 10 minutes. Stop à l'autre extrême de la bougie. Annulé si le prix touche d'abord ce stop.
- Gestion identique à la cassure, en multiples du stop de cette entrée : stop à l'entrée à +1,5 R, pyramide à +2 R, sortie 15:50.
- Taille : jamais plus de lots que A, jamais plus de 1 R de risque.

**Pourquoi 3 bougies et pas 7.** Sur 2018-2026 les 7 bougies jusqu'à 10:05 gagnaient toutes (+1 410 R à elles seules). Sur
les données jamais vues, seules les 3 premières tiennent ; les 4 suivantes tombent à zéro. J'ai retenu ce qui tient deux fois. Ce choix a été fait après le premier coffre ;
le second coffre, seul, le confirme en plus faible (+0,16 R par entrée, t = 0,9).

**Solidité**
- Réglages voisins : validité 5 à 20 minutes, stop d'une à deux bougies, stop à l'entrée à +1 ou +2 R, avec ou sans
  pyramide : tout reste positif, sur les deux périodes. C'est un plateau, pas un pic.
- Pire cas d'exécution dans la minute : résultat inchangé (1 610 R au lieu de 1 614 R).
- Un second modèle (boosting, 18 indicateurs, validé dans le temps) est incapable de trier les bonnes continuations des
  mauvaises (score 0,46 à 0,53, où 0,50 = hasard). On les prend donc toutes.

![Deux journées exemples](resultats/v9_exemples.png)

Détails : `resultats/47`, `48`, `48b`, `49`, `50`, `52`, `55`.

## 5. Strategy V9

| Entrée | Quand | Stop | Statut |
|---|---|---|---|
| **A · cassure** | ordres stop à 9:35, valables jusqu'à 9:45 (V7 : filtres, mémoire, hors FOMC et fériés) | autre côté du range | inchangée |
| **B · repli VWAP** | première bougie M5 qui revient toucher le prix moyen de séance et repart, jusqu'à 14:00 | sous les 2 dernières bougies | inchangée (retenue) |
| **D1, D2, D3 · continuations** | cassure de l'extrême des bougies de 9:35, 9:40, 9:45, tant que A est ouvert | autre extrême de la bougie | **nouveau** |
| C · 10:00 | si la cassure tient à 10:00 | autre côté du range | **coupée par défaut** |
| Garde-fou coût | aucun ordre si spread + 2 glissements > 25 % du range | — | **nouveau** (ne se déclenche jamais aux prix actuels ; il protège si le range redevenait minuscule) |

**V9 contre V8, à risque par trade égal**

| | V8 | V9 | Écart |
|---|---|---|---|
| 2018-2026 : gain total / pire baisse | +986 R / 38 R | +1 614 R / 56 R | +64 % de gain, +49 % de baisse |
| 2018-2026 : années positives, pire journée | 9 sur 9, −6,7 R | 9 sur 9, −5,4 R | |
| 2018-2026 avec 2 points de glissement | +716 R | +1 223 R | |
| 2010-2017 jamais vu : gain total / pire baisse | +281 R / 102 R | +577 R / 170 R | +105 % de gain, +67 % de baisse |
| 2010-2017 : années positives | 6 sur 8 | 6 sur 8 | |
| Positions ouvertes en même temps (maximum) | 3 | 5 | |
| Lots ouverts au maximum, pyramides comprises (en lots de A) | 7 | 15 (95 % des jours : 12 ou moins) | |

**Et si on pousse le curseur ?** Le réglage « nombre de bougies » permet de passer de 3 à 7 continuations (jusqu'à 10:05).
Sur 2018-2026 cela donne +2 270 R pour 76 R de pire baisse ; sur les données jamais vues, +641 R pour 229 R de pire baisse : presque
rien de plus que la V9 (+577 R) pour une baisse bien plus profonde. Les 4 bougies ajoutées ne tiennent pas hors échantillon : je ne
le recommande pas, mais le réglage existe et la décision t'appartient.

**À baisse égale** (on baisse le risque par trade de la V9 jusqu'à retrouver la pire baisse de la V8) : la V9 gagne 10 %
de plus sur 2018-2026 et 23 % de plus sur 2010-2017. C'est le vrai progrès ; le reste est du volume.

## 6. À quoi s'attendre, et comment régler le risque

Simulation de 10 000 années tirées au hasard dans chaque période (par blocs, pour garder les séries) :

| V9, sur un an | Si demain ressemble à 2018-2026 | Si demain ressemble à 2010-2017 |
|---|---|---|
| Gain médian | +173 R | +80 R |
| Mauvaise année (1 sur 20) | +10 R | −67 R |
| Risque d'une année négative | 4 % | 21 % |
| Baisse habituelle en cours d'année | 42 R | 61 R |
| Baisse d'une mauvaise année (1 sur 20) | 79 R | 118 R |

Pire baisse réellement observée : 56 R (2018-2026), **170 R** (2010-2017, étalée sur 2011-2013).

**Traduction en pourcentage du compte** (sans réinvestir les gains) :

| Risque par trade | Gain médian d'une année (prudent → favorable) | Baisse d'une mauvaise année (favorable → prudent) | Pire baisse des 16 ans |
|---|---|---|---|
| 0,10 % | +8 % → +17 % | 8 % → 12 % | 17 % |
| **0,25 % (réglage livré)** | +20 % → +43 % | 20 % → 30 % | 43 % |
| 0,50 % | +40 % → +87 % | 40 % → 59 % | 85 % |

- Avec la V8 à 0,5 % : gain médian +19 % → +54 %, baisse d'une mauvaise année 25 % → 42 %, pire baisse 51 %.
- **La V9 à 0,25 % par trade** ouvre au plus à peu près le même nombre de lots que la V8 à 0,5 % : pas de levier en plus.
  Remonter ce risque est ta décision ; les fichiers ne le font pas à ta place.
- Si ton compte a une limite de perte (souvent 10 %), c'est la colonne « prudent » qu'il faut regarder, pas le backtest.

Ce sont des ordres de grandeur tirés du passé, pas une promesse.

## 7. Ce qui ne marche pas (2018-2026, tout compté)

| Piste | Résultat |
|---|---|
| Pyramide à 2, 3, 4, 6 étages ; ajout plus tôt, plus tard, plus gros (276 variantes) | Rien de solide. Les écarts entre variantes tiennent à 2 ou 3 journées de ±25 R. Un second étage rapporte environ 0. |
| Ajout de la pyramide sur ordre stop à +2 R au lieu d'attendre la clôture M5 | +57 R (non significatif) sur 2018-2026, +88 R sur 2010-2017, mais baisse plus forte : piste à suivre, pas codée |
| Cassure d'une bougie M5 à d'autres heures (nuit, Europe, 8:30, 10:00, après-midi ; 74 variantes) | Perdant partout sauf 9:30-9:55. La nuit, les coûts mangent 0,4 à 1,3 R par trade. |
| Continuations hors des jours V7, ou une fois la cassure stoppée | Nul ou perdant |
| Retournement les jours sautés par la mémoire | +131 R sur 2018-2026, puis −58 R sur 2014-2017 : abandonné |
| « Miroir » de la cassure les jours mémoire (vendre au lieu d'acheter) | Nul |
| Garder pour la nuit les trades encore ouverts à 15:50 | Rien (+0,07 R, t = 0,5) |
| Cassure de la bougie de 8:30 les jours de grosse publication ; de 14:00 / 14:30 les jours FOMC | Perdant ou nul |
| Trier les continuations avec un second modèle | Aucun pouvoir de tri |
| Version « même levier que la V8 » (continuations sans pyramide, plafond de 7 lots) | Fait moins bien que la V8 sur les données jamais vues : non retenue |
| Entrée de 10:00 (C, héritée de la V8) | +0,04 R par trade hors échantillon : coupée par défaut |

**Un constat utile.** L'incertitude sur le total de 9 ans est d'environ ±130 R. Un réglage fin qui « rapporte 50 R de
plus » ne peut pas être distingué du hasard. Seuls les effets massifs ou confirmés ailleurs méritent d'être codés.

## 8. Les preuves anti-hasard

| Contrôle | Ce qu'il vérifie | Résultat |
|---|---|---|
| Coffre 2A (2014-2017) et coffre 2B (2010-2014), ouverts une fois chacun | Que ça marche sur des données jamais utilisées | Voir section 2 : non aux coûts de 2018 ; oui, en plus faible, aux coûts d'aujourd'hui |
| Contrôle de la source | Que l'écart ne vient pas des données | Sur 2018, les deux sources donnent le même sens 160 jours sur 160 et des gains voisins |
| Stabilité par année | Pas une seule bonne année | V9 : 9 années sur 9 (2018-2026), 6 sur 8 (2010-2017) |
| Fenêtres glissantes de 12 mois | Toutes les périodes | V9 : 100 % gagnantes sur 2018-2026 ; 81 % sur 2010-2017, pire fenêtre −157 R |
| Sensibilité aux réglages | Plateau, pas pic | Continuations positives pour 10 réglages voisins sur les deux périodes |
| Coûts | Survie à une mauvaise exécution | V9 2018-2026 : +1 614 R à 1 pt, +1 223 R à 2 pts, +799 R à 3 pts |
| Correction du nombre d'essais | Qu'avec 1 770 essais on n'a pas juste eu de la chance | Seuil 4,0 ; V7 4,6, V8 4,7, V9 4,7 sur 2018-2026. Mais c'est la période de recherche : la vraie mesure est la ligne 1 |
| Probabilité de surajustement (PBO) | La meilleure variante sur une moitié reste-t-elle bonne sur l'autre ? | 4 % sur 492 variantes. Peu parlant ici : les variantes qui empilent le plus gagnent partout |
| Dates FOMC 2011-2017 | Exactitude du calendrier utilisé avant 2018 | Vérifiées une à une sur le site de la Réserve fédérale |

## 9. Contrôle sur un autre indice : le S&P 500

Mêmes règles, aucun réglage, coûts au poids d'aujourd'hui (`resultats/62_sp500.md`). Fait après l'ouverture des coffres.

| S&P 500 | 2015-2017 | 2018-2025 |
|---|---|---|
| Cassure V7 (A) | +0,37 R | +0,29 R (t = 2,1) |
| Signaux sautés par la mémoire | −0,48 R | **−0,54 R (t = −4,7)** |
| Repli VWAP (B) | +0,20 R | +0,23 R |
| Continuations 9:35-9:45 (D) | −0,03 R | +0,23 R |
| Entrée de 10:00 (C) | +0,08 R | +0,25 R |

La règle de mémoire, peu visible sur le Nasdaq d'avant 2018, est très nette sur le S&P 500 : je la garde. Les autres effets
existent aussi, en plus petit. Avec des coûts doublés, presque tout s'efface : même leçon que sur le Nasdaq.

## 10. M5, M3, M1

Continuations calculées sur d'autres tailles de bougie, 9:35-10:05, 2018-2026 :

| Bougies | Entrées | Gain total à 1 pt | À 2 pts | Années positives |
|---|---|---|---|---|
| M1 | 13 599 | +1 906 R | +1 052 R | 6 sur 9 |
| M3 | 5 310 | +1 810 R | +1 424 R | 9 sur 9 |
| **M5** | 3 049 | +1 410 R | +1 072 R | 9 sur 9 |
| M10 | 1 472 | +653 R | +482 R | 9 sur 9 |
| M15 | 963 | +379 R | +274 R | 9 sur 9 |

Plus la bougie est courte, plus il y a d'entrées et plus le total monte, mais le M1 devient irrégulier et dépend des coûts.
Le M3 est un candidat sérieux ; je ne l'ai pas retenu parce qu'il n'a pas été jugé sur les données jamais vues avant leur
ouverture. La V9 reste en M5, comme ton trading actuel.

## 11. Risques et limites

- **Le résultat dépend du poids des coûts dans le range.** C'est la leçon centrale. Relève ton glissement réel en démo.
- **La cassure de base n'est pas prouvée hors de 2018-2026** (t = 1,3). Si le marché revenait au comportement de
  2011-2012, la V9 pourrait perdre pendant deux ans.
- **Plus de positions le même jour** : jusqu'à 5, dans le même sens. Une mauvaise journée coûte environ 4 à 5 R.
- **Compte « hedging » obligatoire** et marge pour 15 lots de A : d'où le risque par défaut ramené à 0,25 %.
- **Le robot V9 n'a jamais été vu en train de tourner** : compilé sans erreur, script TradingView analysé sans erreur,
  mais le testeur de MetaTrader exige un compte de courtier que je n'ai pas. Testeur puis démo avant tout argent réel.
- **Les données d'avant 2018 n'ont que le prix acheteur** : le spread y est supposé, pas mesuré.
- **Il ne reste plus de données jamais vues.** Toute nouvelle idée devra attendre des mois de marché réel, ou un autre indice.
- Aucun gain n'est garanti. Ce document n'est pas un conseil en investissement.

## 12. Prochaines étapes

1. Installer `Strategy-V9` (notice : `strategies/LISEZMOI.md`), lancer le testeur de MetaTrader sur 12 mois, m'envoyer le rapport.
2. Démo pendant quelques semaines : vérifier les messages « entrée D1 guettée », le glissement réel, la marge.
3. Garder le risque à 0,25 % par trade tant que la démo n'a pas confirmé l'exécution.
4. Tenir un relevé mensuel : gain en R, glissement moyen, coût en % du range. Si le coût dépasse durablement 10 % du range, réduire.
5. Pistes pour une prochaine session : la V9 sur un autre indice (DAX, S&P 500) pour diversifier vraiment ; les continuations
   en M3 ; la pyramide sur ordre stop. Chacune devra être jugée sur des données qui n'ont pas servi à la trouver.

## 13. Où sont les fichiers

- `rapport.md` : ce rapport. `rapport-session2.md` : le rapport précédent (V7, V8). `notes/nasdaq-progress.md` : le journal.
- `strategies/` : **Strategy-V9.mq5, Strategy-V9.pine, Strategy-V9.ex5** (compilé), la V8 et la V7, et la notice `LISEZMOI.md`.
- `resultats/` : un fichier par étape (44 à 63 pour cette session), les courbes, les listes de trades de la V9.
- `scripts/` : tout le code (`v9lib.py` = la bibliothèque ; `64_generer_v9.py` fabrique les deux fichiers de la V9).
- Les données de prix ne sont pas dans l'archive (trop lourdes). Les 7 années d'avant 2018 se retéléchargent avec `scripts/41_histdata.py`.

## Sources (session 3)

1. Suhonen, Lennkh et Perez (2017), 215 stratégies de banques : le ratio rendement / risque chute de 73 % en médiane entre le backtest et le réel — https://research.aalto.fi/en/publications/quantifying-backtest-overfitting-in-alternative-beta-strategies/
2. Wiecki, Campbell, Lent et Stauth (2016), 888 algorithmes : les mesures de backtest prédisent mal la suite, et plus on a testé, plus l'écart est grand — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220
3. McLean et Pontiff (2016), anomalies boursières : 26 % de rendement en moins hors échantillon, 58 % après publication — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623
4. Baltussen, Da, Lammers et Martens (2021), l'élan intrajournalier vient en partie des couvertures d'options : une cause qui peut varier d'une époque à l'autre — https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598
5. EdgeLab (2026), ORB sur 16 ans de contrats Nasdaq : la version naïve perd, une version filtrée garde un avantage modeste hors échantillon qui s'effrite depuis deux ans — https://edgelabtrading.com/blog/opening-range-breakout-nasdaq/
6. Backtests, Not Signals (2026), ORB sur le micro Nasdaq avec validation hors échantillon — https://backtestsnotsignals.substack.com/p/opening-range-breakout-real-edge
7. G. Brusco, audit d'un ORB Nasdaq : les conventions de simulation (glissement fixe, stops en dollars fixes alors que l'indice a changé d'échelle) déplacent le résultat — https://github.com/giovannibrusco/nq-intraday-breakout
8. Réserve fédérale, calendriers historiques du FOMC (pages 2011 à 2017, par exemple) — https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm

Les 10 sources de la session précédente sont dans `rapport-session2.md` et `notes/recherche-web.md`.

*Ce document n'est pas un conseil en investissement. Aucun gain n'est garanti. Les résultats passés ne préjugent pas des résultats futurs.*
