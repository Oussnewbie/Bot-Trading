# Journal de recherche — Nasdaq (US100 / NQ)

> Ce fichier est la mémoire du projet. Au début d'une session : le lire en entier et reprendre à « PROCHAINE ACTION ».

## État au 2026-11-20 (session 1)

### Données
- Fournies par l'utilisateur via Google Drive (zip de 100 Mo) : Dukascopy USATECH.IDX/USD, M1, bid ET ask,
  2018-01-02 -> 2026-11-18, 3 002 322 minutes communes. Horodatage en millisecondes UTC.
- Copie de travail : /workspace/data/m1.parquet (NON incluse dans le zip de sortie : trop lourde ; l'utilisateur a l'original).
- Qualité : aucun doublon, aucune valeur manquante, aucune bougie incohérente, bid/ask alignés, heure de New York vérifiée
  (l'activité bondit à 9:30 hiver comme été). Spread réel en séance : ~1,1 pt (2018-19, 2026), ~1,4 pt (2020-25).
  Détail : resultats/01_qualite_donnees.md.
- Dukascopy n'est plus téléchargeable librement depuis le sandbox (429 -> S3 payant). HistData (bid seul) existe en secours.

### Protocole (fixé avant toute recherche)
- Recherche : 2018-01-01 -> 2024-12-31. Coffre-fort : 2025-01-01 -> 2026-11-18, ouvert une seule fois à la fin.
- Coûts : spread réel + 1 pt de glissement par exécution (2 et 3 pts en test de résistance).
- Chaque variante testée est inscrite dans resultats/registre_essais.csv (149 essais avant l'ouverture du coffre).
- Réserve : les « acquis » des sessions précédentes (RSI 65/35, FOMC) ont été trouvés sur 2018-2026 entier ; pour eux le coffre
  n'est pas un test propre. Les totaux annuels 2025-2026 de la v6 nue avaient été vus dans reference.json (sans servir à choisir).

### Étapes faites
1. Dossier, code de départ (depart/), règles exactes (notes/regles-baseline-v6.md).
2. Moteur à la minute bid/ask (scripts/moteur.py). Reproduction de la v6 : 1391/1391 mêmes jours que la référence du dépôt,
   pyramide identique à 100 %, corrélation des R 0,9998 (resultats/02_baseline_vs_reference.md). Seul écart : quand le prix ouvre
   au-delà du niveau, la référence divise par le risque réel, moi par le risque prévu (comme la taille de position de l'EA).
   Baseline recherche, 1 pt : 1113 trades, +0,356 R, 19,8 % gagnants, PF 1,49, pire baisse 32 R, t = 3,34. À 2 pts : +0,165 R.
3. Autopsie des stops (resultats/05, 06) : prédire le stop = quasi impossible (AUC 0,52-0,54 hors échantillon) et écarter les
   « plus risqués » fait perdre des grosses journées. Prédire le gros gagnant = un peu possible (AUC 0,57-0,62).
   Règles simples testées (seuils fixés sur 2018-19) : bougie franche et pré-marché calme ne tiennent pas ; H1 fort concentre
   la qualité mais sacrifie le total ; « pas de trade après un trade gagnant » tient 5/5 années.
4. Stratégies alternatives (resultats/08, 09 ; idées écrites avant dans notes/idees-strategies.md) : élan d'ouverture, fin de
   séance, gap fade, retour à la moyenne, VWAP, sessions = rien ou perdant. Repli après cassure = égale la v6 sans faire mieux.
   Gap confirmé = ORB déguisé. Compression (NR4/NR7/inside) = aucun effet. Aucune alternative ne bat la v6.
5. M5/M3/M1 (resultats/07) : range M5 le meilleur (seul 7/7 années, pire baisse la plus faible) ; M1 tué par les coûts ;
   10-30 min sans avantage. Gestion v6 (stop entrée 1,5R, pyramide 2R x2) sur un plateau correct.
6. Recherche web : notes/recherche-web.md (10 sources).
7. Méta-labeling (resultats/10) : le modèle logistique à 46 indicateurs ne fait pas mieux que la règle mémoire seule.
   « Mémoire puis logistique 8 indicateurs, écarte 30 % » : +0,78 R sur 2020-24 mais indicateurs choisis après avoir vu la
   recherche -> expérimental seulement.
8. Validation sur la recherche (resultats/11, 12) : règle mémoire applicable en réel (« après un trade pris gagnant, on saute
   1 signal ») ; améliore 21 réglages de base sur 21 ; PBO 14-20 % ; t = 4,06 (C1) et 4,19 (C2) contre un seuil Bonferroni de
   3,59 pour 149 essais ; Sharpe déflaté : passe sous hypothèse de hasard pur (96-98 %), échoue avec la dispersion de tous les
   essais (faussée par les stratégies très perdantes) ; pire baisse probable sur 1 an (95 %) : 40 R (v6) -> 33 R (C1) -> 31 R (C2).

### Candidats (définis AVANT l'ouverture du coffre)
- C0 : ORB v6 telle quelle.
- C1 (candidat principal) : v6 + mémoire = après un trade pris qui finit à plus de +0,05 R, le signal suivant est sauté (un seul).
- C2 (version complète) : C1 + aucun ordre les jours FOMC ni les jours fériés/demi-séances.
- C3 (expérimental, pour information) : mémoire puis score logistique à 8 indicateurs ajusté sur 2018-2024, écarte les 30 % les
  moins bien notés.

### PRÉ-ENREGISTREMENT DU TEST DU COFFRE-FORT (écrit avant de regarder)
Attendu si l'effet est réel (d'après la recherche, 1 pt) : C0 ~ +0,36 R ; C1 ~ +0,51 R ; trades sautés ~ -0,36 R.
Marge d'erreur attendue sur ~280 trades : environ ±0,2 R sur le gain moyen (une seule grosse journée déplace le résultat).
Le test est donc peu puissant ; il peut contredire nettement, il ne peut pas prouver seul.
Critères :
- K1 : C1 a un gain moyen positif dans le coffre (1 pt).
- K2 : gain moyen de C1 >= celui de C0.
- K3 : les trades sautés par la mémoire ont un gain moyen inférieur à celui des trades gardés.
- K4 : pire baisse de C1 <= celle de C0.
Décision : K1+K2+K3 vrais -> la mémoire est « confirmée dans la limite du test » et C2 est recommandée.
K3 faux -> « non confirmée » : recommandation = v6 + hors FOMC seulement, la mémoire reste une piste à observer en démo.
K1 faux -> alerte sur la v6 elle-même.
Après l'ouverture : plus aucun réglage. Toute idée nouvelle devra attendre des données postérieures au 2026-11-18.

### COFFRE OUVERT le 2026-11-20 (une seule fois) — resultats/13_coffre_fort.md
Glissement 1 pt, 2025-01-01 -> 2026-11-18 :
- C0 v6 : 281 trades, +0,282 R, total +79,3 R, pire baisse 26,2 R, série 11.
- C1 v6 + mémoire : 230 trades, +0,455 R, total +104,6 R, pire baisse 20,4 R, série 10.
- C2 v6 + mémoire + hors FOMC/jours courts : 217 trades, +0,536 R, total +116,4 R, pire baisse 19,3 R, série 10.
- Trades sautés par la mémoire : 51, -0,497 R en moyenne (total -25,3 R), 1 gros gagnant perdu sur 19 ; p = 0,020 (permutation, coffre seul).
- K1, K2, K3, K4 : OUI. Décision appliquée : mémoire « confirmée dans la limite du test », C2 recommandée = ORB v7.
- Pour information : C3 expérimental +0,632 R (171 trades, pire baisse 11,6 R) ; RSI 65/35 seul +0,705 R (142 trades, pas un test propre).
- Ensemble 2018-2026, 1 pt : C0 +0,341 R (476 R, pire baisse 32,0) ; C2 +0,551 R (591 R, pire baisse 22,1), 9 années positives sur 9.
- IMPORTANT : le coffre est usé. Plus aucun réglage sur 2018-2026. Toute idée nouvelle attend des données postérieures au 2026-11-18.

### Livrables (session 1 terminée)
- rapport.md (rapport final), strategies/ORB-v7.mq5, strategies/ORB-v7.pine, strategies/LISEZMOI.md, strategies/reference-v7.json,
  resultats/courbes_2018_2026.png, resultats/14_score_experimental.md, registre des 149 essais.
- Les fichiers v7 sont générés par scripts/14_generer_v7.py à partir de la v6 (remplacements exacts vérifiés). NON compilés.

### COMPLÉMENT (même session, demande de l'utilisateur) — structure M1 et tendance H1/H4 sur les trades gardés par la v7
Idées et critères écrits avant dans notes/idees-strategies.md. Recherche 2018-2024 seulement. Registre : 179 essais.
- Structure (scripts/moteur_smc.py, 16_smc.py, 17_smc_pyramide.py ; resultats/16, 17) : 18 variantes, 0 retenue.
  Filtre structure M1 alignée : 91 % des trades v7 déjà alignés, sans effet. Prise de liquidité : effet inverse de la théorie
  (non significatif au seuil corrigé). FVG : rien. Entrée repli + CHoCH : évite 284 perdants, 0 gagnant raté, mais total 218-250 R
  contre 475 R. Sortie CHoCH contraire : stops pleins 64 % -> 25 %, gain moyen 0,19-0,24 R, 40 grosses journées sur 84 coupées.
  Stop suiveur de structure : 0,04 R (M1), 0,27 R (M5). Pyramide sur repli + CHoCH : 0,26-0,30 R.
- Tendance (scripts/18_tendance.py ; resultats/18) : 12 filtres (MA200 H1/H4/jour, EMA50 H1, pente, empilement, 3 VWAP, RSI H1), 0 retenu.
  Taux de stops identique dans le sens et contre la tendance. Trades alignés sur les MA : +0,60 à +0,74 R contre +0,28 à +0,39 R,
  5 années sur 7, mais p = 0,06 à 0,25 avant correction et -100 à -230 R sur le total. VWAP : rien.
- Le coffre 2025-2026 n'a PAS été rouvert (aucune variante ne passe). La v7 est inchangée.
- Proposé à l'utilisateur, en attente de sa réponse : regarder « v7 + MA200 H1 alignée » sur 2025-2026 à titre d'indication
  (python3 scripts/18_tendance.py coffre). Ce serait un regard de plus sur le coffre, pas une preuve.

### SECOND REGARD SUR LE COFFRE — pré-déclaration (écrite avant de regarder)
L'utilisateur conteste mes critères (« le problème vient peut-être de ton contexte »). Constat honnête : le critère « gain total
non réduit de plus de 10 % » était le mien, pas le sien (sa mission : gain moyen par trade, pire baisse, séries, robustesse sur
données jamais vues). Avec ses critères, la famille « moyennes mobiles alignées » améliore gain moyen et pire baisse sur 2018-2024 ;
il ne lui manque que la preuve. Le test qui tranche est donc 2025-2026.
- Hypothèse jugée (une seule) : T1, v7 + prix du bon côté de la MA200 H1 à 9:35. Les 11 autres filtres sont affichés pour information.
- Attendu si l'effet est réel : trades alignés ~ +0,69 R, contre-tendance ~ +0,36 R (écart ~0,3 R). Sur ~215 trades, la marge
  d'erreur sur cet écart est d'environ ±0,5 R : le test ne peut que donner une indication.
- Lecture : alignés > contre-tendance ET (v7 + T1) a un gain moyen >= v7 et une pire baisse <= v7 -> « indication favorable »,
  T1 devient une option prudente documentée (interrupteur, coupé par défaut tant que de nouvelles données ne confirment pas).
  Sinon -> abandonné. Dans les deux cas : aucun réglage n'est modifié après avoir regardé.
- Les variantes de structure (CHoCH) ne sont pas regardées dans le coffre : elles font baisser le gain moyen, critère n°1 de l'utilisateur.

### SECOND REGARD SUR LE COFFRE — résultat (resultats/19_tendance_coffre.md, 19_option_tendance.md)
- T1 (MA200 H1) dans le coffre, tri après coup : alignés +0,729 R (122 trades), contre-tendance +0,289 R (95) ; 1 année sur 2 ;
  p = 0,21 sur le coffre seul ; 2018-2026 entier : +0,701 contre +0,345 R, 6 années sur 9, p = 0,074. Taux de stops identique.
- Version jouable (filtre d'abord, mémoire ensuite), 2018-2026, 1 pt : 619 trades, +0,645 R, total +399,6 R, pire baisse 23,9 R,
  série 10 (v7 : 1073, +0,551 R, +591,3 R, 22,1 R, 12). Coffre : 121 trades, +0,685 R, +82,9 R, pire baisse 22,3 R (v7 : 19,3 R).
  Sur un an : gain médian 41 R (v7 64 R), risque d'année négative 6,5 % (v7 3,0 %).
- Décision (conforme à la pré-déclaration, avec la nuance que la version jouable n'améliore pas la pire baisse) : option
  InpUseTrend / useTrend ajoutée à ORB-v7.mq5 et ORB-v7.pine, COUPÉE PAR DÉFAUT. La v7 par défaut est inchangée.
- Registre : 180 essais. Le coffre a maintenant servi deux fois (v7, puis famille tendance).
- Question de l'utilisateur « pourquoi pas le CHoCH qui divise les stops par 3 » : répondu (rapport section 10) : stops pleins
  64 % -> 24-27 %, mais gain moyen 0,56 -> 0,19-0,24 R, total 475 -> 165-205 R, pire baisse 22 -> 26-31 R, série inchangée.
  Non codé dans l'EA ; à ne coder que s'il le demande explicitement en connaissance de cause.

### COMBINAISONS ET BALAYAGES (demandes suivantes de l'utilisateur, 2018-2026 entier, sans seuil d'acceptation)
Environ 470 essais de plus (~650 au total). Plus aucune donnée jamais vue : tout ceci = candidats, pas preuves.
- 216 combinaisons biais H1/H4 x 4 briques CHoCH (scripts/20, resultats/20) : v7 = 1re en gain total / pire baisse, 13e en gains / pertes.
  Meilleure en gains / pertes et gain moyen : v7 + MA200 H4 sans aucune brique CHoCH (PF 2,00, +0,69 R, +381 R). Les briques CHoCH
  dégradent partout. Meilleur taux de réussite 44 % avec +62 R au total. Année mise de côté : PF 1,62 (< v7 1,78).
- 187 indicateurs à l'entrée (scripts/21, 24) : aucun ne filtre les stops ; 0 significatif après correction ; meilleur = DI H4 aligné
  (+0,97 R contre +0,14 R, 9/9 années, p corrigé 0,062, robuste à 8 alignements de bougies H4 et aux longueurs 10-28, sélectionné
  6 fois sur 9 en année mise de côté et confirmé 6/6). SAR M5 aligné : écartés -0,23 R (p corrigé 0,37), gain total inchangé.
- 57 règles de gestion (scripts/22) : aucune amélioration ; sorties sur indicateur -0,22 R ; objectifs Fibonacci -0,21 R ;
  seule famille neutre = sortie au temps (10:30 si < +0,5 R : stops pleins 55 % -> 45 %, même total).
- Versions jouables (scripts/23) 2018-2026, 1 pt : v7 121/an +0,551 R 591 R PF 1,78 DD 22,1 ; +SAR M5 102/an +0,656 R 592 R PF 1,94 DD 22,0 ;
  +DI H4 (bougies courtier) 61/an +0,785 R 425 R PF 2,15 DD 22,9 ; +DI H4 + SAR 51/an +0,905 R 413 R PF 2,35 DD 18,4 ;
  +sortie 10:30 118/an +0,577 R 604 R PF 1,94 DD 25,6 ; les trois 51/an +0,887 R 399 R PF 2,46 DD 17,7.
- Livré : ORB-v7.mq5 / .pine avec 3 options COUPÉES PAR DÉFAUT (InpUseDI / useDI, InpUseSar / useSar, InpUseTime / useTime).
  L'option MA200 H1 a été retirée (dominée par le DI H4). La v7 par défaut est inchangée. Toujours non compilé.
- À faire valider par l'utilisateur : comparaison avec / sans option sur TradingView (données différentes = contrôle en partie indépendant), démo.

### CHoCH : ce qui restait à tester (demande de l'utilisateur) — scripts/25, 26 ; resultats/25, 26 ; ~715 essais au total
- K1, CHoCH « en contexte » sur les trades v7 (17 lectures : zigzag 0,5/1/1,5 range, M5, impulsion, au contact d'un niveau H1/H4/jour) :
  seule la structure la plus large est neutre (+0,002 R, 14 trades touchés) ; les autres coûtent de -0,03 à -0,40 R par trade.
  Même constat rejoué sur v7 + SAR M5 et v7 + DI H4 + SAR M5.
- K2, CHoCH comme stratégie de retournement (balayage d'un niveau frais veille / nuit / pivot H1 / pivot H4 + cassure de structure
  M1 ou M5 ; 48 variantes) : 9 positives, meilleure +0,086 R sur 209 trades (t = 0,36), 2 positives à 2 pts, aucune solide.
  Moyennes : -0,05 R (gestion v6), -0,07 R (sortie 15:50), -0,11 R (objectif 3R), -0,12 R (objectif 2R).
- K3 : filtre DI H4 sur les retournements = aucun effet utile ; addition à la v7 = +18 R (+3 %) et pire baisse 22 -> 27 R.
- Conclusion : rien à ajouter à la v7. Aucun changement de code.

### L'ORB COMME FILTRE (question de l'utilisateur) — scripts/27, resultats/27 ; ~760 essais au total
2018-2026 entier, jours pris par la v7, 1 pt. Référence v7 : 121/an, +0,551 R, +591 R, pire baisse 22,1 R.
- Repli sur VWAP de séance dans le sens de la cassure, gestion v6 : 813 trades, +0,515 R (R propre, stop = 0,73 range), +267 R à taille
  v7, 8/9 années ; ajouté à la v7 : +858 R, pire baisse 38,2 R (ratio 22,5 < 26,8). Repli sur MME20 M5 : ~0.
- Entrée à heure fixe si la cassure tient (stop de l'autre côté du range) : 10:00 -> 538 trades, 48 % de réussite, +0,233 R propre,
  +244 R à taille v7 ; 10:30 -> 489 trades, 53 %, +0,185 R, +233 R, 9/9 années ; 11:00 -> +0,08 à +0,11 R.
- Échec de l'ORB comme signal : retournement après stop plein = -0,22 à -0,42 R (1 année positive sur 9) ; côté bloqué pris = ~0.
- ORB comme filtre des retournements CHoCH : dans le sens -0,06 à -0,13 R ; contre +0,07 à +0,17 R (t ~ 1).
- Conclusion : l'ORB est un bon filtre de sens, mais entrer sur la cassure reste la meilleure exploitation. Aucun changement de code.

### CRITÈRE PRÉCISÉ PAR L'UTILISATEUR + EMPILEMENT (scripts/28, resultats/28)
L'utilisateur précise : même risque par trade, le plus gros gain total ; la pire baisse est secondaire ; ne plus parler de FundingPips.
Empilement sur les jours v7, même nombre de lots par entrée, 2018-2026, 1 pt (2 pts) :
- v7 seule : +591 R (+407), pire baisse 22 R, baisse médiane sur 1 an 17 R, 95 % 31 R.
- v7 + repli VWAP : +858 R (+615), pire baisse 38 R, médiane 1 an 26 R, 95 % 50 R ; 332 jours à plus de 1,5 R de perte.
- v7 + entrée 10:00 : +835 R (+621), pire baisse 35 R. v7 + les deux : +1102 R (+830), pire baisse 42 R, 9/9 années.
- Gain / baisse : 26,8 / 22,5 / 24,2 / 26,1 -> empiler = à peu près trader la v7 plus gros (v7 x 1,45 : +857 R, 32 R ; à 2 pts +589 R, 56 R).
- Repli VWAP robuste à ses réglages : 27/27 positifs (+0,40 à +0,53 R par trade), t = 3,3, 8/9 années.
- Rien n'est codé pour l'empilement. En attente : l'utilisateur doit dire quel empilement il veut voir codé (cela veut dire
  accepter explicitement 2 ou 3 positions ouvertes le même jour).

### STRATEGY V8 — vérifiée sur les données (codée ensuite : voir la section suivante) (scripts/29_v8.py, resultats/29_v8.md, v8_courbes.png, v8_exemples.png)
Demande de l'utilisateur : V8 = v7 + repli VWAP + entrée 10:00, sans la règle « un trade par jour », à voir sur les données avant de coder.
- ERREUR CORRIGÉE : dans le script 28, l'entrée à 10:00 aux lots de la v7 risquait ~1,9 R par trade. Règle de taille de la V8 :
  chaque trade <= 1 R de risque et <= lots de la v7 (lots = lots v7 x min(1, range / distance au stop)).
- Définition rejouée : jours de la v7 (mémoire fondée sur le trade de cassure). A = cassure v7. B = premier repli sur le VWAP de
  séance après la cassure (bougie M5 qui touche le VWAP à 0,1 range près, clôture du bon côté et dans le sens ; entrée marché ;
  stop 1 pt au-delà de l'extrême des 2 dernières M5 ; stop à l'entrée +1,5R et pyramide 2 unités à +2R en multiples de son stop ;
  jusqu'à 14:00 ; annulé si une M5 clôture de l'autre côté du range). C = à 10:00 si le prix est au-delà du niveau de cassure et
  que le stop du range n'a pas été touché : marché, stop autre côté du range, stop à l'entrée +1,5R, sortie 15:50, pas de pyramide.
- Résultats 2018-2026, 1 pt : V8 2424 trades (273/an), +986 R (111/an), 9/9 années, pire baisse 37,9 R, gain/baisse 26,1
  (v7 : +591 R, 22,1 R, 26,8). A +591 R ; B 813 trades +0,331 R = +269 R ; C 538 trades +0,233 R = +126 R (48 % de réussite).
  À 2 pts : +716 R, baisse 50,6 R (v7 +407 R, 38,6 R). Sur 1 an : médiane +107 R, baisse type 27 R, 95 % 49 R, 99 % 63 R.
  Pire journée -6,7 R (2025-10-10). Jusqu'à 3 positions en même temps, exposition max 7 lots de départ (v7 : 3).
- Lever tout plafond n'apporte rien : 2e repli +0,08 R, 3e -0,07 R, nouvelle cassure après stop +0,08 R ; total +1017 à +1037 R
  pour 50 à 60 R de baisse. => V8 retenue = A + 1 repli VWAP + entrée 10:00 (3 trades par jour au plus).
- Accord donné ensuite (« go code la v8 en pine et en EA ») : codée le 21 novembre. Note d'origine : (gros ajout : l'EA v7 ne gère qu'un trade par jour ; il faudra gérer 3 positions
  avec leurs stops, le VWAP de séance en M1, les lots plafonnés, la marge pour 7 unités). Environ 770 essais au total.

### STRATEGY V8 — CODÉE ET COMPILÉE (session du 21 novembre 2026)
- Fichiers : strategies/Strategy-V8.mq5 (2 397 lignes) et strategies/Strategy-V8.pine (1 175 lignes), produits par
  scripts/30_generer_v8.py à partir de strategies/ORB-v7.* et des morceaux de scripts/v8_morceaux/ (ancres vérifiées).
- Vérification préalable (scripts/29b_v8_verif_code.py, resultats/29b_v8_verif_code.md) : la V8 telle que le code la joue
  (bougies M5 complètes pour le stop de B) donne +1008 R / 37,7 R de pire baisse / 9 années sur 9 ; avec un VWAP sans volume
  +979 R / 37,2 R. Le résultat ne dépend donc pas du volume du courtier. Référence gardée : +986 R (script 29).
- COMPILATION RÉELLE : MetaTrader 5 installé sous Wine 11.22 (winehq-devel) dans /workspace/mt5/prefix2/drive_c/MT5
  (l'installateur ne marche que sous Wine 9 d'Ubuntu, MetaEditor ne marche que sous Wine 11 : installer avec l'un, copier le
  dossier, lancer terminal64.exe /portable une fois pour déballer MQL5/Include). scripts/32_compiler_mq5.sh compile et affiche
  le journal. Résultat : Strategy-V8.mq5, ORB-v7.mq5 et ORB-v6.mq5 : 0 erreur, 0 avertissement.
- PINE : scripts/31_verifier_pine.py envoie le script à l'analyseur de l'éditeur Pine de TradingView (pine-facade
  translate_light, sans compte). Strategy-V8.pine et ORB-v7.pine : 0 erreur, 0 avertissement (l'analyseur détecte bien les
  fautes : 4 versions cassées exprès ont toutes été signalées).
- Reste non vérifié : le comportement à l'exécution (voir ci-dessous).

- TESTEUR MT5 : tenté, impossible sans compte. Les données M1 ont été chargées dans MetaTrader comme symbole personnalisé
  « US100dk » (scripts/33_export_mt5.py écrit MQL5/Files/us100_m1.bin au format MqlRates, heure serveur = New York + 7 h ;
  scripts/ImportUS100.mq5 crée le symbole et charge 3 002 322 bougies ; lancé par terminal64.exe /portable /config:import.ini
  avec [StartUp] Script=ImportUS100). Mais le testeur lancé par /config:tester.ini s'arrête sur « tester not started because
  the account is not specified », avec ou sans Login= dans [Tester]. Il faut un compte (démo) connecté dans le terminal.
  Je n'ai PAS ouvert de compte démo (inscription avec nom, e-mail, téléphone : décision de l'utilisateur).
- Aperçu de l'affichage TradingView : scripts/34_apercu_tradingview.py -> resultats/v8_apercu_tradingview.png (dessin à
  partir de deux vraies journées, 2019-07-24 gagnante et 2025-11-17 perdante ; ce n'est pas une capture).
- Levier nécessaire pour la V8 (7 unités, 0,5 % de risque) : médiane 1:12, 95 % des jours sous 1:24, maximum 1:39.
- Documents mis à jour : strategies/LISEZMOI.md (notice V8 en tête, v7 ensuite), rapport.md (point 7 de « En bref »,
  section 15 nouvelle, « Où sont les fichiers » devient 16), LISEZMOI.md racine. strategies/Strategy-V8.ex5 = le robot compilé.
- Environ 772 essais au total (les 2 rejeux de vérification du script 29b compris). Rien n'a été écrit sur GitHub.

### PROCHAINE ACTION (session suivante)
1. Attendre le retour de l'utilisateur : rapport HTML du testeur de stratégie MT5 sur Strategy-V8 (compte hedging), ou ses
   observations en démo / sur TradingView. Comparer aux trades de resultats/trades_V8.csv (jour, sens, heure d'entrée de A, B, C).
   S'il signale un comportement anormal : corriger dans scripts/v8_morceaux/ puis relancer 30_generer_v8.py, 32_compiler_mq5.sh
   et 31_verifier_pine.py (ne jamais corriger les fichiers générés à la main).
2. Pour recompiler dans une nouvelle session (le bac à sable est effacé) : apt-get install wine wine64 (Wine 9 d'Ubuntu) ->
   xvfb-run wine mt5setup.exe /auto (installe dans Program Files/MetaTrader 5) ; puis installer winehq-devel (Wine 11, dépôt
   dl.winehq.org, architecture i386 ajoutée), nouveau préfixe avec WINEDLLOVERRIDES="mscoree=d;mshtml=d", y copier le dossier
   MetaTrader 5 (C:\MT5), lancer une fois terminal64.exe /portable sous Xvfb pour déballer MQL5/Include, puis
   scripts/32_compiler_mq5.sh. Sous Wine 9, MetaEditor s'arrête sur « A debugger has been found » ; sous Wine 11,
   l'installateur reste bloqué : d'où les deux étapes.
3. Si l'utilisateur le demande explicitement : ouvrir un compte démo MetaQuotes pour faire tourner le testeur ici (il doit
   fournir le nom et l'e-mail à utiliser), ou pousser la V8 sur GitHub (nasdaq/) et mettre à jour Étrave (SOURCE_EA, bouton
   d'installation, affichage de B et C).
4. Ne PAS relancer de recherche de réglages sur 2018-2026. Pistes permises : autre instrument (S&P 500, DAX) pour confirmer
   la mémoire et la V8 de façon indépendante ; nouvelles données après 2026-11-18 ; suivi du glissement réel en démo.
5. Pour relancer les scripts d'analyse : remettre les deux CSV Dukascopy dans /workspace/data/brut/extrait/Nasdaq 8 ans/ puis
   lancer scripts/01_charger_donnees.py, 04_features.py, etc. dans l'ordre.

### Acquis des sessions précédentes (rappel)
- v6 à 1 pt : ~0,33 R, ~20 % gagnants, PF 1,48. Verrou +0,4R : cosmétique. FOMC exclus : +0,033 R/trade. RSI 65/35 : 0,52 R/trade,
  deux fois moins de trades.

### Points de vigilance
- L'EA ORB-v6.mq5 du dépôt n'a jamais été compilé ni exécuté (README). Toute version livrée ici non plus.
- GitHub : lecture seule. Ne rien écrire sans demande explicite.


---

## SESSION 3 (2026-11-21) — « maximiser le profit, recherche maximale » (demande explicite de l'utilisateur)

### Reprise
- Le lien « V8 » de l'utilisateur contenait tout le dossier sortie/ de la session précédente : restauré dans /workspace/sortie/.
- Données Dukascopy remises dans /workspace/data/brut/extrait/Nasdaq 8 ans/ ; m1.parquet reconstruit ; 29_v8.py relancé :
  v7 +591,33 R et V8 +986,17 R retrouvés au chiffre près.

### NOUVELLES DONNÉES JAMAIS VUES (trouvées cette session)
- HistData.com, NSXUSD (Nasdaq 100 CFD), M1, prix BID seul, 2010-11-15 -> 2018-12-31 (scripts/41_histdata.py, 42_charger_histdata.py,
  resultats/42_qualite_histdata_NSXUSD.md). Copie de travail : /workspace/data/hd_NSXUSD.parquet.
- PIÈGE CORRIGÉ : le site annonce « EST sans heure d'été » ; en réalité l'horodatage suit l'heure locale de New York (vérifié semaine
  par semaine contre Dukascopy sur 2018 : corrélation des variations à la minute 0,99 à décalage 0 après correction ; le bond de 9:30
  est présent hiver comme été chaque année 2011-2017).
- Écart de niveau avec Dukascopy : +8 pts en médiane (jusqu'à 25-29) = base de type contrat à terme ; sans effet sur une stratégie intrajournalière.
- Range M5 d'ouverture 2011-2017 : 5 à 11 pts (0,15 à 0,26 % du prix) contre 0,27 % en 2018. Régime plus calme.
- Dukascopy direct (datafeed .bi5) : répond 503 la plupart du temps (13 fichiers en 4 min) -> abandonné. scripts/40_dukascopy.py gardé au cas où.
- S&P 500 (SPXUSD) HistData 2010-2026 en cours de téléchargement pour un contrôle sur un autre indice.

### PROTOCOLE DE LA SESSION 3 (écrit avant toute recherche)
- Terrain de recherche : Dukascopy 2018-01-02 -> 2026-11-18 (déjà entièrement vu : tout ce qu'on y trouve = candidat).
- COFFRE N°2, deux moitiés, AUCUN résultat de stratégie n'y est regardé pendant la recherche :
  - Coffre 2A = 2014-07-01 -> 2017-12-31 : jugement des candidats à la fin de la recherche (un seul passage, liste figée avant).
  - Coffre 2B = 2010-11-15 -> 2014-06-30 : confirmation finale de LA stratégie retenue, figée, un seul passage, plus aucun réglage après.
- Coûts dans le coffre n°2 (pas d'ask) : spread = 1,5 point de base du prix (niveau relatif réel de 2018, l'année la plus chère de
  l'étude), glissement = 1,43 point de base du prix par exécution (= 1 pt à 7 000, comme en 2018). Pour information seulement :
  version « 1 pt de spread + 1 pt de glissement fixes » (très dure à ces niveaux de prix : le range fait 5 à 10 pts).
- VWAP dans le coffre : sans volume (vérifié équivalent en session 2).
- Coûts sur 2018-2026 : (M1) spread réel + 1 pt de glissement = convention de l'étude ; (M2) 2 pts ; (M3) glissement proportionnel
  au prix calé sur 2018 (1,43 pb : 1 pt à 7 000, 3,6 pts à 25 000) comme test de résistance pour les années récentes.
- Constat utile : le coût en R a été divisé par ~5 entre 2018 (range 19 pts, coût ~3 pts = 0,16 R) et 2026 (range 94 pts, 0,03 R),
  si le glissement reste de 1 pt. Les variantes « tuées par les coûts » en 2018-2024 méritent d'être relues sous cet angle.
- Garde-fous maintenus malgré « oublie ce qui te freine » : risque par trade <= 1 R (jamais augmenté sans accord explicite),
  aucune donnée inventée, tout essai compté au registre, honnêteté sur ce qui est prouvé ou non. Ce qui est levé : l'interdiction de
  rechercher sur 2018-2026, la limite de 2 tentatives par piste, le critère « peu de stops » (le critère est le gain total à risque égal).

### PLAN
0. Outils : bibliothèque unique (v8lib) qui rejoue v7 / V8 sur n'importe quel jeu de données avec coûts par jour ; simulateur généralisé
   (pyramide à plusieurs étages). Contrôle : retrouver +986,17 R.
1. Radiographie du profit : d'où viennent les R (pyramide, queue des grosses journées, achats / ventes, coût en R par année).
2. Familles de recherche (idées écrites AVANT dans notes/idees-strategies.md, section « Session 3 ») : pyramide à étages ; entrées
   supplémentaires les jours v7 ; jours sans signal v6 ; carte générale des entrées (apprentissage) ; autres séances ; relecture M1/M3
   aux coûts d'aujourd'hui.
3. Assemblage d'un candidat V9, validation glissante, PBO, puis coffre 2A, puis coffre 2B, puis code MQ5 / Pine, rapport, zip.

### AVANCEMENT (recherche sur 2018-2026, tout compté : environ 940 essais de plus, ~1 700 au total)
- Étape 0 faite : scripts/v9lib.py (rejoue v6 / v7 / V8 sur tout jeu de données, coût par jour, simulateur généralisé sim_gen) ;
  scripts/43_controle_v9lib.py : v6 475,96 R, v7 591,33 R, V8 986,17 R retrouvés au centième (1 pt), 406,48 / 715,88 (2 pts).
- Étape 1, radiographie (resultats/44) : A = 591 R dont 305 R unité de départ + 287 R pyramide ; 29 % des trades ont une pyramide ;
  100 meilleurs trades = +1 087 R, les 973 autres = -496 R ; +2R atteint 33 %, +4R 14 %, +6R 5 % ; coût du trade A : 0,16 R (2018-19)
  -> 0,03 R (2026) ; petits ranges (en % du prix) = meilleurs trades (quintile bas +0,73 / +0,90 R, quintile haut +0,13 R).
- Famille P, pyramide à étages (resultats/45, 45b ; 276 variantes) : RIEN de solide. Constat clé : la règle de mémoire rend le total
  chaotique (un trade qui passe de +0,04 à +0,06 R change la suite) -> comparer les gestions sur des jours FIXES. Sur jours fixes :
  ajout sur ordre stop à +2R au lieu de la clôture M5 = +57 R (1 pt), +127 R (2 pts), mais t apparié 0,9 à 1,9 et l'écart tient à
  quelques trades de ±25 R. 2e étage : ~0. Erreur type du total sur 9 ans ≈ 128 R : un réglage fin n'est pas démontrable.
- Famille T, autres heures (resultats/46 ; 74 variantes) : cassure M5 perdante à toutes les heures sauf 9:30-9:55. Nuit / Europe tuées
  par les coûts (0,4 à 1,3 R par trade). 9:30 est unique.
- Famille Q, CONTINUATIONS (resultats/47, 48, 48b, 49, 50) = LA trouvaille de la session. Les jours v7, dans le sens de A, A encore
  ouvert : ordre stop sur l'extrême de chaque bougie M5 suivante (9:35 ... 10:05), stop à l'autre extrême de la bougie, valable 10 min,
  gestion v6, lots plafonnés à ceux de A. Par bougie : +0,4 à +0,96 R propre, 7 bougies = +1 410 R (1 pt), +1 072 R (2 pts), 9/9 années,
  pire cas dans la minute : identique. Plateau large (fenêtre, validité, stop 1 à 2 bougies, stop à l'entrée, M3 / M5 : tout positif).
  Hors jours v7 (mémoire, sans signal) : nul ou négatif. A déjà sorti : négatif.
  MAIS : c'est le même avantage exploité plus de fois. t par jour 4,6 (A) -> 4,6 à 4,9 (assemblages) ; gain ÷ baisse 27 -> 25 à 30.
  A + 7 D avec pyramide : 2 001 R, baisse 66 R ; V8 + 7 D : 2 396 R, baisse 79 R, pire jour -10,1 R ; à plafond 7 lots (celui de la V8) :
  A + 7 D sans pyramide 1 341 R, baisse 52 R (V8 : 986 R, 38 R).
- Famille S, carte générale (resultats/52 ; 143 081 entrées simulées, tous jours, toutes bougies 9:35-14:55, deux sens) : la seule poche
  positive est celle des continuations (jours v7, sens de A, A ouvert, avant 10:30). Rien ailleurs.
- Méta-labeling des D (resultats/55) : AUC hors échantillon 0,46 à 0,53 ; tous les cinquièmes positifs -> on les prend toutes.
- R1, retournement les jours mémoire (resultats/53, 54) : +131 R en lots plafonnés (477 trades, t = 1,45, 8/9 années), +36 R à 2 pts.
  Faible. Gardé « pour information » seulement. Miroir à objectif fixe : nul.
- W (garder la nuit) : rien (t < 1). Publications 8:30 et FOMC 14:00 / 14:30 : négatif ou nul.

### PRÉ-ENREGISTREMENT DU COFFRE 2A (écrit AVANT de regarder ; 2014-07-01 -> 2017-12-31, HistData NSXUSD)
Coûts : spread 1,5 pb du prix, glissement 1,43 pb du prix par exécution (primaire). Pour information : 1 pt + 1 pt fixes.
VWAP sans volume. Mêmes règles que sur 2018-2026 (scripts/v9lib.py : orb_v6, filtre_v7, jambes), aucun réglage changé.
Hypothèses jugées (5) :
- H1 : cassure v6 (tous les signaux hors FOMC / jours courts) : gain moyen > 0.
- H2 : mémoire : les signaux pris font mieux que les signaux sautés (écart > 0).
- H3 : jambe B (repli VWAP) : gain moyen > 0.   - H4 : jambe C (10:00) : gain moyen > 0.
- H5 : jambes D (7 continuations 9:35-10:05, avec pyramide, A ouvert, lots plafonnés) : gain moyen > 0 (ensemble des 7).
Pour information (non jugé) : D bougie par bougie ; D sans pyramide ; E (retournement jours mémoire) ; A sans pyramide ; coûts fixes.
Lecture : « confirmé » = moyenne > 0 et t par jour >= 1,65 ; « prouvé au seuil corrigé pour 5 hypothèses » = t >= 2,33 ;
« indication favorable » = moyenne > 0 mais t < 1,65 ; « non confirmé » = moyenne <= 0 -> la composante est RETIRÉE de la V9.
Attendu si les effets sont réels (coûts relatifs plus lourds qu'en 2018-2026 : ~0,2 à 0,3 R par trade A, range 0,15 à 0,2 % du prix) :
A ≈ +0,3 à +0,5 R ; écart mémoire ≈ +0,5 R ; B ≈ +0,2 R ; C ≈ +0,15 R ; D ≈ +0,3 R par entrée (en R de A).
Puissance : ~420 trades A (erreur type ≈ 0,12 R) ; mémoire : ~90 signaux sautés seulement (test peu puissant).
Après lecture : la V9 est assemblée avec ce qui n'est pas « non confirmé », figée, puis jugée une seule fois sur le coffre 2B.

### PROCHAINE ACTION
Ouvrir le coffre 2A (scripts/56_coffre_2A.py), puis assembler la V9, puis coffre 2B.


---

## SESSION 4 (2026-11-21, suite) — « régler les limites, bon winrate, cause des SL, 7 marchés »

### Demande de l'utilisateur
« Il faut régler ces limites, trouver une stratégie qui analyse très bien les graphiques ; je trade le Nasdaq, le Dow Jones, le gold,
le BTC, l'EURUSD, le GBPUSD » + « tu peux aussi prendre le DAX, en CFD ; je préfère Dukascopy à HistData ». « On doit avoir un bon
winrate et trouver la cause des SL. »

### Données (toutes Dukascopy, bid + ask, M1)
- Le serveur de fichiers datafeed (.bi5) répond 503 ; en revanche l'interface des graphiques (freeserv.dukascopy.com, chart/json3,
  5 000 bougies par appel) répond sans faute. scripts/68_dukascopy_api.py + 68b_tout_telecharger.sh. Contrôle : sur janvier-février 2018,
  34 514 minutes sur 34 514 communes avec le fichier Nasdaq de l'utilisateur, 99,96 à 99,99 % des prix identiques.
- Téléchargés dans /workspace/data/dk/ : USA30.IDX/USD (Dow), DEU.IDX/EUR (DAX), XAU/USD, EUR/USD, GBP/USD (2012 -> 2026-11-20),
  BTC/USD (2017 ->), USATECH.IDX/USD 2012-2017 (pour refaire le coffre du Nasdaq avec de vrais spreads).
- HistData (EURUSD, GBPUSD, XAUUSD) et Binance (BTCUSDT) téléchargés au début, gardés en secours seulement.

### LA CAUSE DES STOPS (Nasdaq, V9 ; scripts/70, resultats/70_causes_sl.md) — identique sur 2018-2026 et sur 2010-2017
- 63 à 65 % des trades finissent en stop plein ; 15 à 18 % gagnent ; jours gagnants 17 à 21 % ; un jour de trade sur deux, TOUTES les entrées sont stoppées.
- AVANT le stop : 32 % fausse cassure immédiate (10 min ou moins, jamais +0,5R) ; 21 % essoufflement ; 32 à 37 % parti (+0,5 à +1,5R) puis revenu ;
  10 à 13 % pyramide ajoutée puis retour.
- APRÈS le stop : dans 34 % des cas le marché va ensuite à +2R ou plus dans le sens du trade (bonne idée, stop trop court) ; 27 % mauvais sens ;
  39 % pas de direction. 47 % des stops tombent avant 10:00, 72 % avant 10:30.
- Conclusion : la première cause des stops n'est pas le sens, c'est la LARGEUR du stop (un range M5, soit 0,2 à 0,3 % du prix, à l'heure la plus agitée).

### LES REMÈDES, UN PAR UN (scripts/71, 72 ; resultats/71_remedes.md, 72_largeur_stop.md) — mêmes signaux, seule la gestion change
- Objectif fixe : +1R -> 52 % de réussite mais total ≈ 0 ; +2R -> 36 %, total divisé par 5. Moitié à +1R : 36 %, total divisé par 2.
  Stop à l'entrée dès +1R, entrée après clôture M5, sortie 12:00, sans pyramide : tout fait baisser le total. Sortie 10:30 : neutre.
- STOP ÉLARGI (k fois le range, lots divisés par k, risque inchangé) : plateau net pour k = 2,5 à 4.
  A seule, k = 3 : réussite 51 % / 47 % (2018-2026 / 2010-2017), stops pleins 23 % / 26 %, total +143 R / +82 R, pire baisse 11 R / 14 R,
  t = 4,0 / 2,6 (la V9 : t = 4,6 / 1,3). Avec objectif +1R : 53 %, +76 R / +76 R, t = 3,0 / 3,2.
  A + D, k = 3 : 48,5 % / 44,6 %, +625 R / +304 R, pire baisse 32 R / 44 R, t = 4,8 / 2,8 (V9 : +1 345 R / +426 R, 49 R / 138 R, t = 4,7 / 2,0).
  Avec 3 pts de glissement (2018-2026) : k = 3 +406 R (t = 3,2) contre +697 R (t = 2,6, baisse 124 R) pour k = 1.
  Avec les coûts « poids de 2018 » sur 2010-2017 : k = 3 +115 R contre -95 R pour k = 1. => le stop large répare en grande partie la dépendance aux coûts.
- Rejoué comme le robot (scripts/v10lib.py, 73 ; A + B + D, les D armées tant que A est ouvert) : k = 3 donne 454 à 513 R (2018-2026) et
  142 à 241 R (2010-2017) selon la règle de mémoire ; les variantes de mémoire se valent (bruit). Détail k = 3, mémoire A > +1R :
  A +117 / +76 R, B +94 / +25 R, D1-D3 +243 / +111 R ; réussite 46 % / 44 %, pire baisse 35 R / 61 R, 8/9 et 8/8 années.
- RÉSERVE : ces variantes ont été regardées APRÈS l'ouverture des coffres du Nasdaq. Le choix de k s'appuie sur un plateau présent dans
  les 4 jeux (2 périodes x 2 niveaux de coût), mais la vraie preuve doit venir des 6 autres marchés, jamais vus.

### PRÉ-ENREGISTREMENT DU TEST MULTI-MARCHÉS (écrit AVANT de regarder un seul résultat sur le Dow, le DAX, l'or, le BTC, l'EUR/USD, le GBP/USD)
Question : l'avantage « cassure de l'ouverture dans le sens de l'élan » existe-t-il sur d'autres marchés, et le profil à stop large y tient-il ?
- Même gabarit que le Nasdaq, sans aucun réglage : range = première bougie M5 après l'ouverture ; filtres v6 (RSI M5 > / < 50, range qui dépasse
  les 30 minutes précédentes) ; ordres valables 10 min ; sortie 6 h 20 après l'ouverture ; B jusqu'à 4 h 30 après l'ouverture ; D1-D3.
- Ouverture PRINCIPALE de chaque marché (fixée a priori) : Dow 9:30 New York ; DAX 9:00 Francfort ; or 8:20 New York (ouverture du COMEX) ;
  EUR/USD et GBP/USD 8:00 Londres ; BTC 9:30 New York (jours ouvrés). Ouvertures SECONDAIRES, pour information seulement : DAX 9:30 New York ;
  or 8:00 Londres et 9:30 New York ; EUR/USD et GBP/USD 8:00 New York ; BTC 0:00 UTC.
- Jours FOMC et fériés américains exclus pour les séances de New York seulement.
- Coûts : spread réel Dukascopy + glissement par exécution de 0,6 pb du prix (indices, or), 0,45 pb (EUR/USD, GBP/USD ; commission comprise),
  2 pb (BTC). Test de résistance : glissement doublé.
- Trois profils jugés, définis ci-dessus et figés : (1) TENDANCE = V9 (k = 1, mémoire d'origine) ; (2) CONFORT = k = 3, même gestion, mémoire
  « après un trade A à plus de +1R, on saute le signal suivant », D armées seulement si le stop du range (l'autre bord) n'a pas été touché
  depuis la cassure ; (3) CONFORT + OBJECTIF = idem avec sortie à +1R, sans pyramide. Chacun en version « A seule » et « A + B + D ».
- Période : du début des données (2012, 2017 pour le BTC) au 31 décembre 2023. Les années 2024-2026 de ces 6 marchés forment le COFFRE 3,
  qui ne sera ouvert qu'une fois, à la fin, pour ce qui sera livré.
- Lecture, par marché et par profil : « confirmé » si gain moyen > 0 et t par jour >= 1,65 ; « favorable » si > 0 ; « non » sinon.
  Preuve d'ensemble : t de la somme des 6 marchés (à poids égaux) >= 2,13 (seuil corrigé pour 3 profils).
- Attendu honnête : Dow proche du Nasdaq (même heure, marchés liés) ; DAX plausible ; or, devises et BTC incertains (ranges M5 petits par
  rapport aux coûts, surtout en devises). Un marché où le coût d'un aller-retour dépasse 25 % du range M5 sera déclaré « non tradable en tendance ».

### RÉSULTAT DU TEST MULTI-MARCHÉS (scripts/74, 75 ; resultats/74_qualite_marches.md, 75_multi_marches_principal_2023-12-31.md, _secondaire_)
Données : 2012 a un spread nul sur le Dow et le DAX (inutilisable) -> départ 2013 pour ces deux marchés. Période jugée : -> 2023-12-31.
Total A + B + D, en R, profils Tendance / Confort / Confort + objectif :
- Dow 9:30 New York : -38 / -26 / +11 (A seule Tendance +38, t = 0,36 ; coût 10 % du range).            -> rien
- DAX 9:00 Francfort : -16 / +19 / -21 (coût 9 %).                                                       -> rien
- Or 8:20 New York : -287 / -60 / -95 (coût 24 % du range).                                              -> négatif
- EUR/USD 8:00 Londres : -771 / -170 / -106 (coût 17 %).                                                 -> négatif
- GBP/USD 8:00 Londres : -760 / -246 / -188 (coût 21 %).                                                 -> négatif
- BTC 9:30 New York : -3 468 / -1 165 / -1 218 (spread Dukascopy 50 à 120 $ = 95 % du range M5 en médiane). -> intradable en M5
- Ensemble : t = -7,6 / -5,5 / -7,8. Aucune ligne « confirmée ». Glissement doublé : pire partout.
- Séances secondaires (pour information) : seul « DAX à 9:30 New York » est positif (Tendance A seule +201 R, t = 1,64 ; Confort A + B + D
  +159 R, t = 1,49) : non significatif, non retenu. Or Londres / 9:30, devises 8:00 New York, BTC 0:00 UTC : négatifs.
- CONCLUSION : l'avantage « cassure de l'ouverture » est propre au Nasdaq (et un peu au S&P 500, vu en session 3). NE PAS copier le robot
  sur les autres marchés. Le profil Confort n'a donc PAS reçu de preuve indépendante.

### « LE DOW CONFIRME » (scripts/76, resultats/76_confirmation_dow.md) — hypothèse écrite avant
Les jours où les filtres v6 du Dow vont dans le même sens que le Nasdaq : écart +0,02 R par jour (t = 0,03) sur 2018-2023 et -0,22 R
(t = -0,34) sur 2013-2017. Bougie d'ouverture du Dow, cassure du Dow : rien non plus. -> abandonné.

### TOURNOI DE STRATÉGIES « DE MANUEL » SUR BOUGIES LONGUES (scripts/77, 78, v11lib.py ; resultats/78_tournoi_2023-12-31.md)
Idées et critères écrits avant (notes/idees-strategies.md, S1 à S5). 7 marchés, -> 2023-12-31, spread réel + glissement + portage.
Critère « candidat » : >= 60 trades, t >= 2, >= 60 % d'années positives. RÉSULTAT : AUCUN CANDIDAT sur 35 couples.
- S1 repli en tendance (jour, RSI 2 < 10 au-dessus de la moyenne 200 j) : Nasdaq 67,6 % de réussite, +0,09 R (t = 1,56, 102 trades) ;
  Dow 75,8 %, +0,08 R (t = 1,55, 99 trades) ; DAX, or, devises, BTC <= 0.
- S2 cassure 20 jours : Nasdaq +0,28 R (t = 1,4), Dow +0,30 R (t = 1,1) ; BTC +1,87 R (47 trades ; achats +3,98 R ; t = 1,5) ; reste négatif.
- S3 la nuit sur indices : brut +2 à +4 pb par nuit, net négatif (portage du CFD). S4 repli H1 : négatif partout (t = -2,5 à -28).
- S5 cassure 55 heures : ~0 (indices +0,08 à +0,12 R, t < 1,4 ; devises et BTC négatifs).
- S6 cassure du range asiatique à Londres (scripts/79, resultats/79) : EUR/USD, GBP/USD, or, 3 gestions : tout négatif ou nul (t de -3,3 à -0,1).
- COFFRE 3 (2024-01-01 -> 2026-11-19 du Dow, du DAX, de l'or, du BTC, de l'EUR/USD, du GBP/USD) : JAMAIS OUVERT, faute de candidat. Il reste disponible.

### PROFIL CONFORT FINAL, TEL QUE CODÉ (scripts/v10lib.py, 80 ; resultats/80_confort_final.md)
k = 3 ; mémoire « après un trade A à plus de +1R on saute le signal suivant » ; D armées seulement si l'autre bord du range est intact ; A + B + D1-D3.
- 2018-2026, 1 pt : Confort +477 R, 46,7 % de réussite, 29,5 % de stops pleins, baisse 32 R, t = 4,18, 8/9 années (2019 : -12 ; 2018 : +168 = 35 % du total).
  V9 : +1 614 R, 18,0 %, 62,8 %, 56 R, t = 4,66, 9/9.
- 2018-2026, 3 pts : Confort +301 R (baisse 70) ; V9 +799 R (baisse 157).
- 2010-2017, coûts d'aujourd'hui : Confort +194 R, 43,8 %, baisse 53 R, t = 2,11, 8/8 ; V9 +577 R, 15,1 %, baisse 170 R, t = 2,20, 6/8.
- 2010-2017, coûts poids 2018 : Confort +23 R ; V9 -157 R. 2013-2017 Dukascopy, vrais spreads : Confort +1 R ; V9 -66 R.
- Sur un an (tirages par blocs) : Confort médiane +51 R, baisse typique 18 R, 1 sur 20 : 35 R (si l'avenir ressemble à 2018-2026) ;
  +27 R, 23 % d'années négatives, 26 R, 52 R (s'il ressemble à 2010-2017). V9 : +170 R / 42 / 78 ; +77 R / 21 % / 62 / 119.
- Séries de jours perdants : 8 à 14 (V9 : 24 à 33). Lots ouverts au maximum : 5 (V9 : 15). Pire journée : -5,1 R (V9 : -5,4 R).
- Variantes : « Confort A seule » +117 / +76 R, 49 % / 47 %, t = 3,3 / 2,43 ; « Confort + objectif +1R » 54 % / 51,5 %, +240 / +115 R.
- LECTURE : à pire baisse égale sur 16 ans (170 R contre 53 R, facteur 3,2) les deux profils rapportent autant (2 191 R contre 671 x 3,2 = 2 147 R).
  Le Confort n'apporte PAS plus de profit : il apporte 2 à 3 fois plus de trades gagnants, des séries de pertes 3 fois plus courtes, 3 fois moins
  de lots et une bien moindre dépendance aux coûts. RÉSERVE : mis au point après avoir vu tout l'historique du Nasdaq ; aucune preuve indépendante.

- PLATEAUX ET SURVEILLANCE (scripts/83_surveillance.py, resultats/83_surveillance.md) : plus longue attente d'un nouveau plus haut :
  Confort 230 jours de trade (déc. 2018 -> août 2020, 20 mois) et 334 (avr. 2015 -> déc. 2017, 32 mois) ; V9 78 (7,5 mois) et 298 (31 mois).
  => le Confort a des baisses moins profondes mais des plateaux PLUS LONGS que la V9 sur 2018-2026. À dire à l'utilisateur.
  Sur 60 jours de trade (Confort) : 43 % de jours gagnants en moyenne, pire passage 28,3 % ; total médian +9 à +19 R, pire -23 à -33 R ;
  1 fois sur 100 par tirage : 28 à 30 % de jours gagnants, -25 à -41 R. Seuils d'alerte donnés : < 28 % de jours gagnants, < -40 R, baisse > 66 R.
  En pourcentage à 0,25 % : année médiane +13 % (type 2018-2026) ou +7 % (type 2010-2017) ; pire baisse 16 ans 13 % ; pire journée -1,3 %.

### STRATEGY V10 (scripts/81_generer_v10.py, 82_figure_v10.py)
- strategies/Strategy-V10.mq5 (2 634 lignes), Strategy-V10.pine (1 286 lignes), Strategy-V10.ex5. Généré à partir de Strategy-V9.*.
- Nouveau réglage InpStopMult / stopMult = 3 (profil Confort ; 1 = profil Tendance = V9). Stop de A = niveau de cassure - k x range (StopA),
  lots calculés sur k x range, jambes B et D élargies de même, D armées seulement si !gV8StopHit, garde-fou coût rapporté au risque,
  InpMemR / memR = 1,0, préfixe d'état « StratV10_ », version 10.00.
- RISQUE PAR DÉFAUT : 0,25 % par trade, comme la V9 (une première génération était à 0,5 % ; corrigé : le remonter est la décision de l'utilisateur).
- MetaEditor : 0 erreur, 0 avertissement (resultats/compilation/Strategy-V10.compilation.txt). Analyseur Pine : succès.
- Non vérifié : exécution réelle (testeur MT5, backtest TradingView, démo).
- Figure : resultats/v10_confort_contre_v9.png. Trades : resultats/trades_V10_confort_*.csv.

### ESSAIS DE LA SESSION 4 (resultats/registre_session4.md)
Environ 240 cellules : 42 remèdes de gestion, 54 largeurs de stop, 13 variantes de mémoire, 78 marché x profil (pré-enregistrées), 3 filtres Dow,
35 couples du tournoi, 9 range asiatique, 4 profils finaux. Total depuis le début : environ 2 000.

### ÉTAT À LA FIN DE LA SESSION 4
- Livré : Strategy V10 (Confort par défaut, Tendance en changeant 2 réglages), rapport.md (session 4), rapport-session3.md, rapport-session2.md.
- Nasdaq : plus aucune donnée vierge (2010-2026 entièrement vus). NE PLUS RIEN RÉGLER sur le Nasdaq.
- Autres marchés : recherche faite sur -> 2023 ; coffre 3 (2024-2026) fermé et disponible pour UNE idée future, écrite à l'avance.

### PROCHAINE ACTION
Attendre le retour de l'utilisateur (testeur MT5 sur 12 mois, puis démo). Ensuite, par ordre d'utilité :
1. Mesurer le glissement RÉEL sur les ordres stop à 9:35 (c'est la variable qui décide de tout) et comparer les trades démo aux trades simulés.
2. Pistes non prouvées, à ne creuser que sur demande et avec le coffre 3 comme juge : repli en tendance sur bougies jour (Nasdaq, Dow :
   ~70 % de réussite, gain trop petit pour être prouvé seul ; à tester en panier d'indices) ; cassure 20 jours à l'achat seul sur le BTC (47 trades,
   trop peu) ; DAX à 9:30 New York (t = 1,6).
3. Ne pas copier la V10 sur le Dow, le DAX, l'or, le BTC, l'EUR/USD ou le GBP/USD.


---

## SESSION 5 (2026-11-24, Claude Code sur le Mac de l'utilisateur)

- Dépôt nettoyé (main = V10 seule), correctifs d'exécution de l'EA et d'Étrave (non compilés), critique de la V10
  (`recherche/critique-v10.md`), recherche documentaire (`recherche/reports/Pistes ORB asymétrie stop gamma VIX.md`).
- Simulateur dans le dépôt (`recherche/simulateur/`) : retrouve les 3 612 trades de la V10 à l'identique.
- Quatre règles et le critère A écrits AVANT tout chargement du S&P 500 (`notes/idees-strategies.md`, « SESSION 5 », commit f400ceb),
  codées et vérifiées (réglages neutres = V10 exacte) avant les données (commit 8d1887f).
- VIX (Cboe) et GEX (SqueezeMetrics) téléchargés le 24/11 dans `donnees/externes/` (jusqu'au 23/11/2026).
- **S&P 500 Dukascopy : téléchargement automatique refusé par Dukascopy (HTTP 403, dukascopy-node 1.51.1, la dernière version).**
  Pas de contournement (pas d'imitation d'un navigateur). Les données sont à fournir par l'utilisateur, comme le Nasdaq.
- Essai à blanc de `s5_juger.py` sur le Nasdaq déjà vu (contrôle du code seulement, 500 tirages, écrit hors du dépôt), au coût de
  0,6 pb : R0 46,7 % de trades gagnants, +499 R ; H1 47,2 %, +455 R ; H2 51,4 %, +378 R ; H3 47,2 %, +298 R ; H4 44,9 %, +218 R.
  Ces chiffres décrivent des données déjà vues. Ils ne changent aucune règle et ne jugent rien.

### PROCHAINE ACTION
Recevoir les CSV M1 bid et ask du S&P 500 (`usa500idxusd`, 2018-01-01 → 2026-11-24) et les mettre dans `donnees/brut/sp500/`. Puis
lancer `s5_qualite.py`, relire, écrire une éventuelle exclusion, et lancer une seule fois `s5_juger.py`.
