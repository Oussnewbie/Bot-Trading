# La demande (texte reçu le 14 novembre 2026, en deux fois)

Gardée ici pour que l'étude puisse être reprise sans la conversation d'origine.
**Changements décidés depuis** : (1) l'étude et les données vont du 2018-01-01 au 2026-11-13, et non de 2010 à aujourd'hui ;
(2) le dépôt a été nettoyé et tout est sur `main` : la règle « ne modifie aucun fichier existant, branche etude-sl » ne
vaut plus pour ce nettoyage ; (3) les données M1 2018-2026 sont dans git, à la demande de l'utilisateur.

## Rôle

Tu es un quant spécialisé en stratégies intraday sur indices et or. Tu cherches la vérité, pas un backtest flatteur : un
résultat négatif bien prouvé vaut mieux qu'un pattern fragile.

## Contexte

- Stratégie : ORB v5, décrite dans le README. Code de référence : backtest/nas100-10ans/orb_v5.py (reproduction de la v5)
  et v5_lab.py (simulateur). L'EA MT5 est dans mt5/ORB-v5.mq5.
- Je trade uniquement des CFD, en prop firm (FundingPips) : la pire baisse compte autant que le gain.
- Mon problème : trop de SL, souvent sur une mèche, puis le prix repart dans mon sens.

## Règles

- Tout va dans backtest/etude-sl/. Un commit à la fin de chaque étape.
- Les achats entrent sur l'ask et sortent sur le bid, et l'inverse pour les ventes. Toujours le spread réel.
- Heures en New York, heure d'été américaine gérée (comme InpSrvDST dans l'EA).
- Résultats toujours en R, avec : nombre de trades, R par trade, total R, pire baisse en R, pire série de pertes.
- Arrêt à la fin de chaque étape, résumé court, attente du « go ».
- Skill writing-plans s'il est disponible, sous-agents pour les recherches web de l'étape 3.

## Étape 1 — Données et reproduction (faite, voir ETAPE1.md)

1. Télécharger avec npx dukascopy-node le M1 bid ET ask : usatechidxusd (Nasdaq CFD) et xauusd (or). Dire la vraie date de
   départ ; ne rien inventer.
2. Reconstruire M3, M5, M15, M30, H1, H4 et D1 à partir du M1.
3. Contrôler la qualité : jours manquants, trous intrajournaliers, spreads aberrants, jours fériés et demi-séances.
4. Vérifier que le M5 reconstruit colle avec donnees/, puis que orb_v5.py redonne les chiffres du README.

## Étape 2 — Autopsie des pertes

1. Classer chaque sortie perdante ou nulle selon sa cause : stop de départ, stop au prix d'entrée (InpBeR = 1,5R), stop
   commun de la pyramide, sortie de 15:50. Part de chaque cause en nombre et en R.
2. Pour chaque trade stoppé, regarder le M1 : MAE et MFE en R ; temps entre l'entrée et le stop ; stop touché par une mèche
   ou par une clôture M1/M5 ; spread au moment du stop ; de combien le prix a dépassé le stop (en % du range) ; si le prix
   est ensuite revenu au-delà de l'entrée, ou à +1R, +2R, avant 15:50.
3. Courbe contrefactuelle : pour une marge de stop de 0 % à 100 % du range, par pas de 10 %, combien de trades stoppés
   auraient fini gagnants, et que deviennent le total R et la pire baisse ? Même chose pour un stop déclenché à la clôture
   M1, M3 ou M5.
4. Avant de croiser quoi que ce soit, écrire dans etape2_hypotheses.md la liste des variables de contexte testées : taille
   du range / ATR ; gap d'ouverture ; tendance et MA200 en H1, H4 et D1 ; distance au plus haut/bas de la veille et aux
   sessions Asie et Londres ; volume en ticks de la bougie de 9:30 ; jour de la semaine ; annonces CPI, NFP, FOMC ;
   volatilité de la veille ; et toute autre variable jugée pertinente, déclarée avant d'avoir vu les résultats.
5. Comparer gagnants et perdants sur chaque variable.

## Anti-bruit

Couper la période en trois : recherche, vérification, et une période finale (2023 → 2026) testée une seule fois, à la toute
fin. (Découpage d'origine : début → 2017 / 2018 → 2022 / 2023 → 2026. Avec des données qui commencent en 2018, la coupe
recherche / vérification est à confirmer : proposition 2018-2020 / 2021-2022.)

Un pattern n'est retenu que s'il remplit toutes ces conditions :
- il va dans le même sens sur les trois périodes ;
- chaque case contient au moins 30 trades ;
- il bat 1 000 tirages au hasard (entrées aléatoires ou permutations), avec une p-value corrigée pour le nombre de tests
  (Benjamini-Hochberg) ;
- les réglages voisins donnent un résultat proche (pas un pic isolé) ;
- il améliore le total R ou la pire baisse sans dégrader l'autre de plus de 10 %. Réduire le nombre de SL ne suffit pas.

## Étape 3 — Corrections et compléments

1. Tester uniquement les corrections suggérées par l'étape 2, par exemple : marge au-delà du range ; stop à la clôture ;
   entrée sur retest du range plutôt qu'en ordre stop ; break-even plus tard ; stop de la pyramide plus large ; filtre de
   contexte. Une seule modification à la fois, puis les meilleures combinées.
2. Or : appliquer la v5 telle quelle, comme une expérience à part. Tester ensuite une seule variante logique : le range de
   l'ouverture du COMEX (8:20 NY). Ne pas forcer les réglages pour qu'elle marche.
3. Recherche web : quels compléments à un ORB sont documentés (VWAP, volume profile, order flow, sessions, régime de
   volatilité…) ? Les CFD n'ont ni vrai volume ni vrai delta. Dire ce qui est mesurable avec le volume en ticks et le
   bid/ask Dukascopy, et s'il existe une source gratuite de données futures NQ/GC intraday pour approcher le delta, avec la
   profondeur d'historique. Tout ce qui est retenu passe par l'anti-bruit.

## Livrable

backtest/etude-sl/RAPPORT.md, en français simple, avec :
1. la réponse en 5 lignes : d'où viennent mes SL ;
2. un tableau en trois colonnes : prouvé / probable / bruit ;
3. pour chaque correction retenue : son effet sur les trois périodes, et le réglage exact à mettre dans l'EA et dans le Pine ;
4. ce qui reste à vérifier en démo.

Plus les scripts qui refont toute l'étude avec une seule commande (`refaire.sh`).
