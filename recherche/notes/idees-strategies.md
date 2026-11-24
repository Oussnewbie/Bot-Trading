# Idées de stratégies — écrites AVANT les tests (20 novembre 2026)

Règle : pour chaque piste, l'idée de marché est écrite ici avant de lancer le moindre test. Coûts : spread réel + 1 point
de glissement par exécution (2 points en test de résistance). Recherche sur 2018-2024 seulement. Chaque variante testée est
inscrite au registre (resultats/registre_essais.csv). Une piste sans résultat après 2 tentatives est notée et abandonnée.

## Famille ORB (enrichissement de la v6)
- **H1. Durée du range (M1, M3, M5, 10, 15, 30 min).** Idée : un range plus long = stop plus large = coûts plus faibles
  en proportion et moins de fausses cassures, mais entrée plus tardive et moins de trades à gros multiple. Un range plus
  court = l'inverse. Attendu : M1/M3 pénalisés par les coûts (le stop fait quelques points seulement).
- **H2. Gestion (stop à l'entrée, pyramide).** Idée : la v6 gagne grâce aux rares journées de tendance ; la pyramide les
  amplifie, le stop à l'entrée coupe des trades qui auraient fini gagnants. On veut voir un plateau, pas un pic.
  Contrainte : le pire cas après l'ajout ne doit jamais dépasser -1R (pas de risque accru).
- **H3. Durée de validité des ordres (10, 30, 60, 150 min).** Idée : une cassure tardive est-elle encore bonne ?
- **H4. Sortie (stop suiveur, objectif fixe, heure de sortie).** Idée : un objectif fixe coupe les grosses journées ;
  un stop suiveur large pourrait protéger sans les couper.
- **H5. Stop plus serré (demi-range).** Idée : double les multiples des gagnants mais augmente le nombre de stops.

## Stratégies alternatives
- **A. Élan de la première demi-heure (« opening drive »).** Idée : les gros intervenants qui passent des ordres toute la
  journée poussent dans le même sens ; le sens de 9:30-10:00 tend à se prolonger (effet documenté par Gao, Han, Li et Zhou
  sur les ETF d'indices). Entrée à 10:00 dans le sens de la première demi-heure, stop sur l'extrême opposé, sortie 15:50.
- **A2. Élan de fin de séance.** Idée : même étude, la première demi-heure prédit la dernière (couvertures de fin de
  journée). Entrée à 15:30 dans le sens de la première demi-heure, sortie à 15:59.
- **B. Gap de la nuit.** Idée « fade » : un gap modéré sans nouvelle est souvent comblé (les market makers reviennent vers
  la clôture de la veille). Idée « go » : un gros gap sur nouvelle se prolonge. Entrée à 9:30/9:35, objectif = clôture de
  la veille (fade) ou sortie 15:50 (go).
- **C. Retour à la moyenne après extension.** Idée : en milieu de séance, sans nouvelle, un écart extrême par rapport au
  prix moyen de la séance attire des contreparties ; le prix revient vers la moyenne. Entrée contre le mouvement quand le
  prix s'écarte de plus de k écarts-types de la moyenne de séance, objectif la moyenne, stop au-delà.
- **D. Continuation avec repli (« pullback »).** Idée : après une vraie cassure, le prix revient souvent tester le bord du
  range ; acheter ce test donne un meilleur prix et évite les cassures qui échouent tout de suite. Ordre limite sur le
  bord du range après une cassure d'au moins 1R, stop de l'autre côté.
- **E. Cassure après compression.** Idée (Crabel) : la volatilité alterne contraction et expansion ; une journée étroite
  (plus petit range des 4 ou 7 derniers jours, journée « inside ») précède souvent une journée de tendance. ORB seulement
  ces jours-là. Lien direct avec la « mémoire » trouvée à l'autopsie (après un gain = après une expansion).
- **F. Tendance autour du prix moyen de séance (substitut du VWAP, le CFD n'ayant pas de vrai volume).** Idée : quand le
  prix tient au-dessus de la moyenne de séance après la première heure, les acheteurs dominent ; suivre ce côté avec un
  stop sous la moyenne.
- **G. Élan par session.** Idée : le sens de la séance européenne (3:00-9:30 New York) reflète l'information de la nuit ;
  la séance américaine le prolonge-t-elle ou le corrige-t-elle ? Entrée à 9:35 dans le sens (ou contre), stop en ATR.

## Filtres et méta-modèle (appliqués à la meilleure base)
- **M1. Mémoire.** Ne pas trader après un trade gagnant (contraction après expansion). Variantes pour vérifier le plateau.
- **M2. Élan H1 aligné**, **RSI M5 65/35** (acquis), **FOMC et jours courts exclus** (acquis).
- **M3. Méta-labeling.** Un second modèle (logistique, peu de variables) note chaque signal ; on ne prend que les mieux
  notés. Jamais d'augmentation du risque par trade.

# Complément du 20 novembre 2026 (demande de l'utilisateur) — principes de structure, écrits AVANT les tests

Demande : « peaufiner la v7 avec d'autres principes du trading (CHoCH M1 ou du même genre), sur les mêmes trades gardés ».
Base : les trades gardés par la v7 (mêmes jours, même sens). Recherche sur 2018-2024 (856 trades) ; le coffre 2025-2026
ne sera regardé que pour une idée qui passe les critères ci-dessous (et ce second regard est moins propre que le premier).

## Définitions (fixées à l'avance, aucun réglage optimisé)
- Sommet / creux M1 : une bougie dont le plus haut (plus bas) dépasse celui des k bougies de chaque côté ; il n'est « confirmé »
  que k minutes plus tard. k = 2 (k = 3 en variante quand c'est précisé).
- Cassure de structure : clôture M1 au-delà du dernier sommet (ou creux) confirmé. C'est un **CHoCH** si elle va contre le sens
  de la cassure précédente (changement de caractère), une **BOS** si elle va dans le même sens (continuation).

## S1. Filtre : structure M1 alignée avant l'entrée
Idée : si les petites vagues M1 du pré-marché et de la bougie d'ouverture vont déjà dans le sens de la cassure, les acheteurs
(ou vendeurs) ont la main ; sinon la cassure a plus de chances d'échouer.
Variantes : (a) dernière cassure M1 depuis 8:00 dans le sens du trade ; (b) idem depuis 9:00 ; (c) le dernier événement est un CHoCH dans le sens du trade.

## S2. Filtre : prise de liquidité avant la cassure
Idée (école ICT) : le marché va d'abord chercher les stops d'un côté (faux mouvement) avant de partir de l'autre. Une cassure
à la hausse précédée d'un balayage d'un plus bas serait plus fiable.
Variantes : (a) la bougie d'ouverture a aussi balayé le côté opposé de 9:00-9:30 ; (b) le plus bas de la nuit (minuit-9:00) a
été balayé entre 9:00 et 9:35 puis repris ; (c) le plus bas de la veille a été balayé avant 9:35 puis repris. (Symétrique pour une vente.)

## S3. Filtre : « fair value gap » dans le sens du trade
Idée : une bougie d'impulsion qui laisse un trou (le bas de la bougie 3 au-dessus du haut de la bougie 1) signale un
déséquilibre acheteur. Variantes : (a) un tel trou existe dans les bougies M1 de 9:30-9:34 ; (b) il n'est pas comblé à 9:35.

## S4. Entrée affinée : attendre un repli puis un CHoCH M1
Idée : au lieu d'acheter la cassure, attendre un creux M1 plus haut (repli) puis la reprise (clôture M1 au-dessus du dernier
sommet M1), et placer le stop sous ce creux : stop plus court, moins de fausses cassures subies.
Risque connu : les grosses journées partent souvent sans repli ; on entre plus tard et plus cher.
Règle : après la cassure v7, premier creux M1 confirmé puis clôture au-dessus du dernier sommet confirmé -> entrée au marché ;
stop sur ce creux ; annulé si le stop v7 est touché avant ou s'il est 11:00. Gestion v6 (seuils en multiples du nouveau stop).
Variantes : k = 2, k = 3. Résultat donné **à taille de position égale à la v7** (donc sans augmenter ni le risque ni le levier).

## S5. Sortie anticipée : CHoCH M1 contre la position
Idée : si la structure M1 casse contre nous (clôture sous le dernier creux confirmé pour un achat), sortir tout de suite au
lieu d'attendre le stop plein : on réduirait la taille moyenne des pertes.
Risque connu : tous mes tests de stops plus serrés ont dégradé le résultat ; celui-ci est un stop serré « intelligent ».
Variantes : structure comptée depuis 9:30 ou depuis l'entrée ; sortie seulement avant le stop à l'entrée / la pyramide, ou jusqu'à la pyramide.

## S6. Stop suiveur de structure
Idée : une fois le stop à l'entrée acquis, remonter le stop sous le dernier creux confirmé (M1 avec k = 3, ou M5 avec k = 2)
pour verrouiller les gains en suivant la structure. Risque connu : coupe les grosses journées.

## Critères (écrits avant de regarder)
16 nouvelles variantes. Une variante n'est retenue que si, sur 2018-2024 :
- filtres : les trades gardés font mieux que les écartés au moins 5 années sur 7, avec moins de 3 chances sur 1 000 que ce soit
  du hasard (seuil corrigé pour 16 essais), et sans faire baisser le gain total de plus de 10 % ;
- entrée / sortie / stop : amélioration du gain moyen trade par trade avec la même exigence statistique, au moins 5 années sur 7,
  et une pire baisse qui ne se dégrade pas.
Si aucune ne passe : le coffre n'est pas rouvert et la v7 reste telle quelle.

## S7 (ajouté après les 16 premières variantes, écrit avant son test). Pyramide sur repli + CHoCH M1
Idée : la pyramide fait l'essentiel du gain. Au lieu d'ajouter dès qu'une bougie M5 clôture à +2R (achat de la force), attendre
ensuite un creux M1 plus haut puis une clôture M1 au-dessus du dernier sommet M1 (CHoCH / reprise), ajouter là, et placer le stop
de l'ensemble sous ce creux. Garde-fou : le stop n'est jamais plus bas que le niveau qui garantit un pire cas de -1R (comme la v6).
Risque connu : S4, S5 et S6 montrent que les stops de structure, plus serrés, coupent les grosses journées.
Variantes : k = 2, k = 3. Mêmes critères. Total des variantes « structure » : 18 (le seuil de 3 chances sur 1 000 reste valable).

## T. Filtres de tendance H1 / H4 / jour (demande de l'utilisateur : « MA200, VWAP… peut-être qu'ils filtreront les SL ») — écrit avant le test
Idée : une cassure d'ouverture dans le sens de la tendance de fond aurait plus de suite ; contre la tendance, elle buterait
plus souvent (donc plus de stops). Tous les indicateurs sont lus à 9:35 sur la dernière bougie entièrement close ; le prix
comparé est la clôture de 9:34. « Aligné » = prix au-dessus pour un achat, au-dessous pour une vente.
Base : trades gardés par la v7, recherche 2018-2024.
- T1. Moyenne mobile simple 200 en H1 alignée.
- T2. Moyenne mobile simple 200 en H4 alignée.
- T3. Moyenne exponentielle 50 en H1 alignée.
- T4. Pente de la MA200 H1 dans le sens du trade (MA200 d'aujourd'hui contre celle d'il y a 10 heures).
- T5. Empilement en H1 : prix > EMA50 > MA200 (achat), l'inverse pour une vente.
- T6. MA200 H1 ET MA200 H4 alignées.
- T7. Moyenne mobile 200 jours alignée (2018 presque absent : il faut 200 jours d'historique).
- T8. VWAP de la session en cours (ancré à 18:00 la veille, pondéré par le volume Dukascopy, qui n'est qu'un substitut pour un CFD) aligné.
- T9. VWAP de la semaine (ancré au dimanche 18:00) aligné.
- T10. VWAP de la séance américaine de la veille aligné.
- T11. RSI 14 en H1 du bon côté de 50 (déjà vu sur la v6, refait sur les trades v7).
- T12. Tout aligné : MA200 H1 + MA200 H4 + VWAP de la semaine.
Mêmes critères que pour les variantes de structure, avec un seuil durci puisque la famille compte maintenant 30 essais :
moins de 2 chances sur 1 000 que l'écart soit du hasard, trades gardés meilleurs au moins 5 années sur 7, gain total non réduit de plus de 10 %.

## C. Combinaisons demandées par l'utilisateur (écrit avant le test)
Demande : « fais la meilleure combinaison entre la suppression des critères trop sévères, le biais H1 et H4 et ces 4 briques
(sortie sur CHoCH contraire, entrée après repli + CHoCH, pyramide sur repli + CHoCH, stop suiveur sous le dernier creux), pour
avoir le meilleur ratio sur 2018 jusqu'à la dernière date ».
- Base : v7 (mémoire + hors FOMC / jours fériés), rejouée de façon séquentielle comme l'EA (le filtre de tendance d'abord, la mémoire sur les trades pris).
- Grille (216 combinaisons) : biais {aucun, MA200 H1, MA200 H4, H1 et H4} x entrée {cassure v7, repli + CHoCH k=2, k=3} x sortie CHoCH
  {non, avant le stop à l'entrée, jusqu'à la pyramide} x pyramide {à +2R, sur repli + CHoCH} x stop suiveur {non, creux M5, creux M1}.
- Taille de position égale à la v7 (1R = range d'ouverture) : ni risque ni levier accrus.
- Aucun seuil d'acceptation, comme demandé. Classement sur 2018-2026 entier selon trois ratios : gains ÷ pertes, gain total ÷ pire
  baisse, taux de réussite. Combinaisons de moins de 250 trades signalées (ratios instables).
- Avertissement méthodologique : c'est une optimisation sur tout l'historique, coffre compris. Le meilleur chiffre est biaisé vers
  le haut par construction. Pour le mesurer : sélection « année mise de côté » (on choisit la meilleure sur 8 années, on la juge
  sur la 9e, pour chaque année).

## I. Balayage large d'indicateurs (demande de l'utilisateur : « VWAP, MA200, Fibonacci, MACD ou d'autres, en jouant sur les
paramètres et les unités de temps, pour l'entrée, la gestion ou la sortie ») — écrit avant le test
Base : les trades de la v7, 2018-2026 entier (demande explicite de l'utilisateur ; le coffre a déjà servi).
- Volet 1, à l'entrée (9:35) : environ 170 indicateurs lus sur la dernière bougie close en M5, M15, H1, H4 et jour, alignés sur le
  sens du trade : prix contre moyennes simples et exponentielles (20, 50, 100, 200), pentes, croisements, MACD (3 réglages),
  RSI (7, 14, 21), ADX et DI, bandes de Bollinger (position, resserrement), stochastique, Ichimoku, Supertrend, SAR parabolique,
  VWAP (session, semaine, mois, veille), position du niveau d'entrée dans les zones de Fibonacci de la veille, de la nuit, des
  5 et 20 derniers jours. Idée commune : un contexte de tendance ou de position « favorable » donnerait de meilleures cassures.
- Volet 2, en cours de trade : sorties sur croisement contraire (EMA 9/20/50 M5, EMA20 M15, VWAP de séance, MACD M5/M15,
  Supertrend, RSI), rendu de gain de Fibonacci (sortie si le prix rend 38,2 / 50 / 61,8 / 78,6 % du gain maximal), objectifs en
  extensions de Fibonacci (1,618 / 2,618 / 4,236 / 6,854 R), stop suiveur en ATR, sortie au temps si le trade n'avance pas,
  pyramide conditionnée par un indicateur. Idée commune : un indicateur verrait la fin du mouvement avant le stop.
- Garde-fou statistique : avec plusieurs centaines d'essais, une vingtaine paraîtront « significatifs » par pur hasard. Pour
  chaque volet je calcule donc ce que donnerait le MEILLEUR de N indicateurs sans aucun pouvoir (permutations), et je compare.

## K. Ce qui n'avait pas été testé sur le CHoCH (demande de l'utilisateur) — écrit avant le test
Période : 2018-2026 entier (plus de données jamais vues). Spread réel + 1 pt de glissement (2 pts en contrôle).

### K1. CHoCH « lu en contexte », appliqué aux trades de la v7 puis à ses profils
Idée : ma première définition (sommets / creux M1 confirmés en 2-3 minutes) capte du bruit. Un trader regarde une structure plus
significative et le contexte. Quatre lectures, chacune utilisée en sortie anticipée (avant le stop à l'entrée, ou jusqu'à la
pyramide) et, pour la première, en stop suiveur :
- a. Vagues en amplitude (zigzag) : un sommet / creux n'existe que si le prix s'en est éloigné de 0,5, 1 ou 1,5 fois le range d'ouverture.
- b. Structure M5 (sommets / creux sur bougies M5, confirmés après 1 ou 2 bougies).
- c. Cassure avec impulsion : le CHoCH M1 ne compte que si la bougie qui casse a un corps d'au moins 1,5 fois le corps moyen des 20 dernières.
- d. CHoCH sur niveau : le CHoCH M1 contraire ne compte que si le prix est arrivé à moins de 0,1 ATR d'un niveau devant lui
  (plus haut / bas de la veille, de la nuit, dernier sommet / creux H1 ou H4).
Attendu honnête : plus la structure est large, moins la règle coupe de grosses journées ; reste à voir si elle apporte quelque chose.

### K2. CHoCH comme stratégie à part entière : retournement sur un niveau H1 / H4 / jour
Idée (école ICT / SMC) : les stops s'accumulent au-delà des niveaux visibles. Le prix va les chercher (balayage), puis repart
dans l'autre sens ; un CHoCH sur petite unité de temps confirme le retournement.
Règles fixées à l'avance :
- Niveaux « frais » (non touchés pendant la nuit) : plus haut / bas de la veille, plus haut / bas de la nuit, dernier sommet /
  creux H1 non cassé (5 jours), dernier sommet / creux H4 non cassé (10 jours).
- Séance de 9:30 à 15:00. Balayage = le prix dépasse le niveau. Dans les 30 minutes : une clôture qui casse la structure dans
  l'autre sens (M1 ou M5) ET qui est revenue du bon côté du niveau -> entrée au marché à la minute suivante.
- Stop 1 point au-delà de l'extrême du balayage. 1R = distance au stop. Deux trades par jour au plus. Jours FOMC et fériés exclus (comme la v7).
- Gestions : objectif 2R ; objectif 3R ; sortie 15:50 avec stop à l'entrée à +1,5R ; gestion v6 (stop à l'entrée + pyramide).
- Variantes : chaque famille de niveaux seule et toutes ensemble ; CHoCH M1 ou M5 ; avec un stop minimal de 0,05 ATR (pour limiter le poids des coûts).
- Avertissement : le stop est court, donc à risque égal en % la taille de position serait plus grosse que celle de la v7 (plus de
  levier). Les résultats sont donnés en R de cette stratégie ; rien n'est activé sans accord explicite.

### K3. « Avec les combinaisons de la v7 »
- Appliquer à la stratégie de retournement le filtre de tendance H4 (dans le sens / contre) et regarder les deux groupes.
- Additionner la stratégie de retournement à chaque profil de la v7 (même compte, 1R chacun) : gain total, pire baisse, lien entre les deux.

## L. « L'ORB comme filtre plutôt que comme base » (question de l'utilisateur) — écrit avant le test
Déjà testé sous cette forme : repli sur le bord du range après cassure (famille D, +0,35 R, pas mieux que la v6) ; entrée sur repli +
CHoCH M1 après la cassure (S4, +218 à +250 R contre +475 R). Formes restantes, 2018-2026 entier, spread réel + 1 pt :
- L1. Biais ORB + repli plus tard dans la séance. Idée : la cassure d'ouverture dit qui a la main ce jour-là ; un retour sur le prix
  moyen de séance (VWAP) ou sur la moyenne exponentielle 20 en M5, suivi d'une bougie M5 qui repart, offre une entrée à meilleur
  prix avec un stop plus court. Jusqu'à 14:00, un trade par jour, annulé si le prix clôture de l'autre côté du range.
  Variantes : référence VWAP ou MME20 ; avec ou sans exigence que la cassure ait d'abord atteint +1R ; gestion v6 ou sortie 15:50.
- L2. Biais ORB + entrée à heure fixe. Idée : si à 10:00, 10:30 ou 11:00 le prix est toujours au-delà du niveau de cassure, la
  journée est « validée » ; on entre alors, stop de l'autre côté du range.
- L3. L'échec de l'ORB comme signal. Idée : une cassure qui échoue piège ceux qui l'ont suivie ; leur sortie alimente le mouvement
  inverse. a) quand le trade v6 touche son stop plein, on se retourne au même prix, stop sur le niveau de cassure d'origine ;
  b) les jours où le côté bloqué par les filtres est touché d'abord, on prend ce côté-là.
- L4. L'ORB comme filtre des retournements CHoCH (K2). Idée : un retournement sur balayage de niveau a plus de chances de réussir
  s'il va dans le sens de la cassure du jour (« acheter le creux d'un jour haussier »).
Mesures : gain moyen en R propre à chaque méthode, et à taille de position égale à la v7 (R de la v7) pour comparer les totaux ;
seule, et additionnée à la v7. Une trentaine de variantes de plus (environ 745 au total). Aucune donnée jamais vue.

## V8. « Strategy V8 » (demande de l'utilisateur) — définition écrite avant de la rejouer
V8 = v7 + repli VWAP + entrée à 10:00, sans la règle « un trade par jour ». À voir sur les données AVANT de coder.
Correction : dans le tableau d'empilement (script 28), l'entrée à 10:00 utilisait les lots de la v7 avec un stop ~1,9 fois plus
loin, donc ~1,9 R de risque par trade. Règle de taille de la V8 : chaque trade risque au plus 1 R ET n'utilise jamais plus de lots
que le trade de la v7 (lots = lots v7 x min(1, range / distance au stop)).
- Jours : ceux de la v7 (filtres v6, hors FOMC et fériés, mémoire fondée sur le résultat du trade de cassure).
- Trade A : la cassure v7, inchangée.
- Trade B : repli sur le VWAP de séance après la cassure (bougie M5 qui touche le VWAP à 0,1 range près, clôture du bon côté et dans
  le sens) ; entrée au marché ; stop 1 point au-delà de l'extrême des 2 dernières bougies M5 ; gestion v6 en multiples de son propre
  stop ; jusqu'à 14:00 ; annulé si une bougie M5 clôture de l'autre côté du range.
- Trade C : à 10:00, si le prix est toujours au-delà du niveau de cassure et que le stop du range n'a pas été touché : entrée au
  marché, stop de l'autre côté du range, stop à l'entrée à +1,5R, sortie 15:50.
- Sans la règle « un trade par jour » : variantes avec 2, 3 ou un nombre illimité de replis VWAP par jour (un seul ouvert à la fois),
  et une nouvelle entrée sur la cassure (même niveau, jusqu'à 11:00) après un stop plein du trade A.
- Mesures : total, par an, pire baisse, année par année, pire journée, positions ouvertes en même temps, glissement à 2 points.


---

# SESSION 3 (21 novembre 2026) — « maximiser le profit » : idées écrites AVANT les tests

Critère de l'utilisateur : le plus gros gain total sur l'historique, à risque par trade égal (au plus 1 R par trade), rentabilité
maximale. Terrain de recherche : 2018-2026 (déjà vu : tout y est « candidat »). Preuve : coffre n°2 (2010-2017, jamais vu), en deux
moitiés (2A puis 2B). Coûts : spread réel + 1 pt de glissement (2 pts et glissement proportionnel en tests de résistance).
Deux mesures suivies partout : le gain total (critère de l'utilisateur) ET le gain ÷ pire baisse (pour distinguer un vrai progrès
d'un simple « on trade plus gros »).

## P. Pyramide à plusieurs étages
Idée : le gain vient des rares journées de tendance (la pyramide fait passer la v6 de +0,16 à +0,36 R par trade). Aujourd'hui on
n'ajoute qu'une fois, à +2R. Les jours où le prix fait +6R, +10R, d'autres ajouts pourraient amplifier encore, puisque la tendance
intrajournalière du Nasdaq persiste (effet d'élan documenté). Garde-fou : après chaque ajout, le pire résultat possible du trade
reste >= -1R (le stop remonte). Variantes : 2e ajout à +4R, 3e à +6R ; ajout sur ordre stop (dans la minute) plutôt qu'à la clôture
M5 ; premier ajout plus tôt mais plus petit ; pyramide sur l'entrée C (qui n'en a pas). Risque connu : chaque ajout resserre le stop
et augmente l'exposition (marge) : toute variante qui demande plus de lots ouverts sera signalée comme telle.

## Q. Entrées supplémentaires les jours v7, dans le sens de la cassure
Idée : la V8 a montré que le sens de la cassure reste exploitable plus tard (repli VWAP, 10:00). D'autres « secondes chances »
existent peut-être : cassure d'un nouveau plus haut du jour après une pause (drapeau), repli sur le niveau de cassure, 2e entrée
horaire. Risque connu : ce sont les mêmes journées ; le total monte mais la pire baisse aussi. Je note donc gain ÷ baisse.

## R. Les jours où la v7 ne fait rien (environ un jour sur deux)
- R1. Jours sautés par la mémoire. Idée : si le signal qui suit un gain perd en moyenne 0,4 R, le trade inverse gagne peut-être
  (vendre la cassure : objectif = l'autre bord du range, stop = 1 range au-delà). C'est l'effet « contraction après expansion » joué
  dans l'autre sens. Risque connu : les coûts se paient deux fois ; la symétrie n'est pas parfaite.
- R2. Jours sans signal v6 (filtres RSI / élan non alignés, ou pas de cassure en 10 minutes). Idée : une tendance peut démarrer plus
  tard ; cassure du plus haut / bas des 30 ou 60 premières minutes avec un stop serré (taille du range M5) plutôt qu'un stop large.
- R3. Jours FOMC : après l'annonce de 14:00, cassure du range 14:00-14:05 (mouvements violents, mais glissement réel inconnu : informatif).

## S. Carte générale des entrées (apprentissage sur toutes les bougies M5 de la séance)
Idée : au lieu de deviner des figures, mesurer partout. Pour chaque bougie M5 de 9:35 à 15:00, on simule une entrée dans le sens
du mouvement du jour avec un stop standard et la gestion v6, puis on regarde quelles conditions connues à ce moment (heure, distance
à l'ouverture, position par rapport au VWAP et au range d'ouverture, tendance de fond, volatilité, mémoire de la veille) donnent un
gain moyen positif après coûts. Modèle simple (arbre peu profond / boosting avec importance des variables), validation dans le temps
uniquement (apprendre sur le passé, tester sur le futur). Ce qui en sort doit se résumer en une règle lisible, sinon ce n'est pas retenu.

## T. Autres heures de la journée
Idée : la cassure de 9:30 marche parce que c'est le moment où l'information de la nuit rencontre la liquidité. D'autres rendez-vous
existent : ouverture de l'Europe (3:00 New York), publications de 8:30 et 10:00, reprise de 13:30-14:00, dernière heure.
Balayage : cassure de la bougie M5 de chaque demi-heure, gestion v6, coûts réels (le spread de nuit est plus large). Attendu
honnête : 9:30 est probablement unique ; le balayage sert aussi de contrôle (un effet partout serait suspect).

## U. Relecture « coûts d'aujourd'hui »
Idée : le Nasdaq a été multiplié par 4 depuis 2018 alors que spread et glissement en points n'ont pas bougé. Le coût en R a donc été
divisé par ~5. Des variantes écartées en session 1 parce que « tuées par les coûts » (range M1 ou M3, stop à mi-range) sont peut-être
devenues les meilleures aux niveaux de prix actuels. Test : mêmes variantes, résultat par période (2018-2020 / 2021-2023 / 2024-2026)
et sous l'hypothèse « coûts relatifs de 2025-2026 appliqués à toutes les années ». Attention : si le glissement réel grandit avec
le prix, l'avantage disparaît ; d'où le test de résistance « glissement proportionnel ».

## W. Garder les gros gagnants pour la nuit
Idée : une journée de tendance clôture souvent près de son extrême ; le mouvement se prolonge-t-il jusqu'à l'ouverture suivante ?
Étude d'événement d'abord (rendement de 15:50 à 9:30 le lendemain après une grosse journée), sans rien coder. Coûts : swap de nuit du CFD.

## X. Achats contre ventes
Idée : le Nasdaq monte sur longue période ; les ventes ont peut-être une espérance plus faible, ou une gestion différente à adopter.

## Y. Contrôle sur un autre indice (S&P 500)
Idée : si la mémoire, le repli VWAP et l'entrée de 10:00 sont des effets réels du marché actions américain, ils doivent apparaître
aussi sur le S&P 500 (données HistData 2010-2026). C'est une preuve indépendante partielle (les deux indices sont très liés).


## Après le coffre 2A, avant le coffre 2B (écrit le 21 novembre 2026, avant d'ouvrir 2B)
Ce que 2A a appris : aux coûts « niveau 2018 » tout perd ; aux coûts d'aujourd'hui en proportion, A, B et les 3 premières continuations
sont positives, C est négative, les continuations tardives (9:50-10:05) sont nulles, E (retournement les jours mémoire) est nettement négative.
Candidat figé pour 2B : **V9 = A + B + D 9:35 / 9:40 / 9:45 avec pyramide, sans C**. Idée : garder seulement ce qui a tenu deux fois
(recherche puis 2A). Le choix des 3 bougies utilise 2A : c'est donc 2B qui le juge. Idée de bon sens ajoutée : un garde-fou qui coupe le
trading quand le coût d'un aller-retour dépasse 25 % du range (la stratégie perdait dans ce régime). Règles de décision : voir le journal.

## Après le coffre 2B
Plus aucune idée nouvelle n'est testée sur 2010-2026. Pistes notées pour plus tard (à juger ailleurs) : V9 sur le DAX ou le S&P 500,
continuations en M3, pyramide sur ordre stop.


---

# SESSION 4 (21 novembre 2026) — 7 marchés : idées écrites AVANT les tests

Constat de départ (test pré-enregistré, resultats/75) : le gabarit de la cassure d'ouverture ne marche ni sur le Dow, ni sur le DAX, ni sur
l'or, ni sur le BTC, ni sur l'EUR/USD, ni sur le GBP/USD. Sur ces marchés le range M5 est trop petit par rapport aux coûts (10 à 30 % du
risque, 30 à 1 000 % pour le BTC chez Dukascopy) et l'élan de l'ouverture n'existe pas. Il faut donc (a) des horizons plus longs, où le coût
ne pèse presque rien, et (b) des idées propres à chaque famille de marché. Paramètres « de manuel », fixés à l'avance, aucune optimisation.
Recherche : début des données -> 31 décembre 2023. Coffre 3 : 2024-01-01 -> 2026-11-19, ouvert une fois pour ce qui passe le filtre.
Coûts : spread réel Dukascopy + glissement (0,6 pb indices et or ; 0,45 pb devises ; 2 pb BTC) + portage par nuit (taux directeur + 2,5 % par an
à l'achat sur indices et or ; 1,5 % par an sur les devises ; 15 % par an à l'achat et 5 % à la vente sur le BTC : valeurs prudentes à vérifier chez le courtier).

## S1. Repli en tendance, bougies du jour (« acheter la faiblesse dans une tendance haussière »)
Idée : sur les indices actions, une forte baisse de 1 à 3 jours dans une tendance de fond haussière est le plus souvent une prise de bénéfices ou
une vente forcée, que le marché rachète dans les jours suivants (prime de risque + retour à la moyenne à court terme, documentés depuis les années 1990).
Taux de réussite attendu élevé (60 à 75 %), gains petits, pertes rares mais plus grosses. Règle : clôture au-dessus de la moyenne 200 jours ET
RSI 2 jours sous 10 -> achat à la clôture ; sortie quand la clôture repasse au-dessus de la moyenne 5 jours, ou après 10 jours ; stop à 3 ATR(14).
Indices : achat seulement. Or, BTC, devises : aussi le miroir à la vente (sous la moyenne 200 jours, RSI 2 au-dessus de 90).
## S1b. Le même sans filtre de tendance (devises, or) : RSI 2 sous 10 -> achat ; au-dessus de 90 -> vente ; même sortie.
Idée : les grandes devises oscillent plus qu'elles ne tendent ; un excès de 2 jours se corrige. Attendu : faible, les coûts de portage comptent.
## S2. Cassure de 20 jours (suivi de tendance)
Idée : l'or et le BTC font de longues tendances (flux d'investissement lents) ; acheter un plus haut de 20 jours et tenir tant que le plus bas de
10 jours tient. Taux de réussite attendu bas (30 à 40 %), gains rares mais gros. Stop à 2 ATR(20). Indices : achat seulement.
## S3. La nuit sur les indices
Idée : l'essentiel de la hausse des actions se fait entre la clôture et l'ouverture suivante (prime de nuit documentée). Achat à 15:59, vente à
9:31 le lendemain (DAX : 17:29 -> 9:01). Attendu : positif avant coûts, mais le portage du CFD (taux + 2,5 %) et le spread en mangent l'essentiel.
## S4. Repli en tendance, bougies H1 (la version « dans la journée » de S1)
Règle : prix au-dessus de la moyenne exponentielle 200 heures ET moyenne 50 au-dessus de la 200 ; RSI 2 heures sous 10 -> achat à la clôture H1 ;
sortie au-dessus de la moyenne 5 heures ou après 24 heures ; stop à 3 ATR(14) H1. Miroir à la vente (indices : achat seulement en version principale).
## S5. Cassure de 55 heures (suivi de tendance H1)
Règle : clôture H1 au-dessus du plus haut des 55 heures précédentes -> achat ; sortie sous le plus bas des 20 heures ; stop à 2 ATR(20) H1. Miroir.

## Critères écrits avant de regarder
- Un couple (stratégie, marché) est « candidat » si, sur la recherche : au moins 60 trades, gain moyen > 0, t >= 2,0, et au moins 60 % d'années positives.
- Les candidats, et eux seuls, passent le coffre 3 (2024-2026) : « confirmé » si le gain moyen y est positif ; preuve d'ensemble si la somme des
  candidats y est positive avec t >= 1,65.
- Environ 40 couples testés : avec t >= 2, le hasard seul en laisserait passer 1 ; d'où le coffre.


## S6. Cassure du range asiatique à l'ouverture de Londres (devises, or) — écrit avant le test
Idée : c'est LA stratégie intrajournalière classique des devises. La nuit asiatique est calme ; l'arrivée de Londres apporte les ordres et le prix
sort du range de la nuit. Le range (0:00-7:00 Londres) fait 20 à 40 pips : le coût n'en pèse que 3 à 6 %, contrairement au range M5.
Règle : ordres stop sur le plus haut et le plus bas de 0:00-7:00 Londres, valables de 7:00 à 12:00, le premier touché seulement ; stop de l'autre
côté du range ; sortie à 16:00 Londres. Trois gestions fixées : (a) sortie 16:00 seule ; (b) objectif +1R ; (c) stop à l'entrée dès +1R.
Marchés : EUR/USD, GBP/USD, or. Recherche jusqu'au 31 décembre 2023. Mêmes critères de candidature (t >= 2, 60 % d'années positives).

## Après les tests de la session 4 (écrit le 21 novembre 2026)
- Gabarit « cassure d'ouverture » transposé sans réglage au Dow, au DAX, à l'or, au BTC, à l'EUR/USD, au GBP/USD : aucun marché confirmé.
- S1 à S6 : aucun couple (stratégie, marché) n'atteint le critère écrit (>= 60 trades, t >= 2, >= 60 % d'années positives). Le coffre 3 n'a pas été ouvert.
- Ce qui s'en approche le plus, noté sans conclure : S1 sur Nasdaq et Dow (68 % et 76 % de réussite, +0,09 et +0,08 R, t ≈ 1,55) ; S2 sur le BTC à l'achat
  (+3,98 R par trade, 23 trades) ; DAX à 9:30 New York (t = 1,6). Les regrouper après coup en « panier » serait du tri a posteriori : toute suite doit
  être écrite à l'avance et jugée sur le coffre 3.
- Leçon : sur ces marchés, à l'échelle de la journée, les règles classiques ne laissent rien après les coûts d'un CFD. Rien n'est retenu hors Nasdaq.
- Nasdaq : le seul changement retenu en session 4 est la largeur du stop (profil Confort de la V10). Il n'augmente pas le gain à baisse égale.
