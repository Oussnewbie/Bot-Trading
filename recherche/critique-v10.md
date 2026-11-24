# Critique de la Strategy V10 : ce qu'elle lit du marché, ce qu'elle ne lit pas (24 novembre 2026)

Le but de l'utilisateur : **perdre moins souvent, et bien lire les baisses comme les hausses.**

D'où viennent les chiffres :
- les trades simulés de la V10, profil Confort, sur deux périodes : 2018-2026 avec le spread réel + 1 point, et 2010-2017 avec les
  coûts d'aujourd'hui ;
- les fichiers `resultats/trades_V10_confort_*.csv` ;
- le script qui les recalcule : `scripts/critique_v10.py`.

**Toutes ces données ont déjà servi à construire la V10.** Ce qui suit décrit le passé pour choisir des pistes ; rien ici ne
prouve qu'une piste marchera. Une piste ne compte que si elle passe un test écrit à l'avance, sur des données qui n'ont pas servi à
la trouver (dernière partie).

## 1. Ce que le robot regarde

| Information | À quoi elle sert |
|---|---|
| Bougie M5 de 9:30 (plus haut, plus bas) | Niveaux d'entrée ; le stop est à 3 ranges |
| RSI14 M5 de cette bougie (au-dessus ou en dessous de 50) | Côté permis |
| Plus haut et plus bas de 9:00-9:30 | Côté permis : le range doit les dépasser |
| VWAP de la séance | Entrée B (repli) |
| Bougies M5 de 9:35 à 9:45 | Entrées D (continuations) |
| Calendrier (Fed, jours fériés) | Jours sans trade |
| Résultat du trade précédent | Règle mémoire |

Tout se décide dans les 15 premières minutes, avec trois informations sur le prix du Nasdaq lui-même. Le robot **ne voit pas** :
- la séance de la nuit (sauf la demi-heure avant l'ouverture) ;
- les annonces économiques, sauf la Fed ;
- le niveau de peur du marché (VIX) ;
- la position des teneurs de marché sur les options ;
- les autres marchés.

Il traite aussi **les achats et les ventes exactement de la même façon**, et son stop dépend **seulement du range de 5 minutes**.

## 2. Ce que disent les trades

### 2.1 Les ventes sont nettement plus faibles que les achats

| Part de trades gagnants | 2018-2026 | 2010-2017 |
|---|---|---|
| Cassure A : achats / ventes | 52,5 % / 44,9 % | 54,1 % / 39,5 % |
| Repli B : achats / ventes | 48,6 % / 39,5 % | 48,7 % / 37,8 % |
| Continuations D : achats / ventes | 51,2 % / 40,2 % | 45,1 % / 36,4 % |

| | Trades gagnants | Jours gagnants | Total | Pire baisse |
|---|---|---|---|---|
| V10 telle quelle, 2018-2026 | 46,7 % | 42,6 % | +477 R | 32 R |
| Achats seulement, 2018-2026 | 51,0 % | 45,2 % | +325 R | 22 R |
| Ventes seulement, 2018-2026 | 41,6 % | 39,6 % | +152 R | 43 R |
| V10 telle quelle, 2010-2017 | 43,8 % | 42,5 % | +194 R | 53 R |
| Achats seulement, 2010-2017 | 48,8 % | 48,4 % | +138 R | 23 R |
| Ventes seulement, 2010-2017 | 37,8 % | 35,6 % | +56 R | 55 R |

- Sur la cassure A, l'écart est présent presque chaque année : toutes les années de 2011 à 2017, et 7 années sur 9 de 2018 à 2026.
- **Ce n'est pas une affaire de tendance de fond.** Quand le prix est sous sa moyenne des 50 derniers jours de trade, les ventes
  ne font pas mieux : 42,5 % de gagnantes en 2018-2026, et 28,7 % en 2010-2017, avec −0,18 R par trade.
- Le robot lit donc les baisses moins bien que les hausses : une cassure vers le bas échoue plus souvent qu'une cassure vers le
  haut.
- **Limite :** sans les ventes, le gain total baisse d'environ 30 %. « Achats seulement » perd moins souvent, mais gagne moins.

### 2.2 Les jours à petit range d'ouverture fournissent l'essentiel des stops

On compare le range de 9:30 du jour à la moyenne des 20 derniers jours de trade, puis on range les jours en cinq groupes égaux.

| | Range relatif | Cassure A au stop plein | Jours gagnants | Gain moyen par jour |
|---|---|---|---|---|
| 2018-2026, les 20 % de jours au plus petit range | 0,59 | **42,5 %** | 36,3 % | +0,12 R |
| 2018-2026, les autres jours | 0,79 à 1,71 | 12,8 à 21,8 % | 43,1 à 45,6 % | +0,31 à +0,70 R |
| 2010-2017, les 20 % de jours au plus petit range | 0,54 | **37,1 %** | 37,7 % | −0,06 R |
| 2010-2017, les autres jours | 0,75 à 1,74 | 19,2 à 26,9 % | 39,5 à 46,1 % | +0,01 à +0,46 R |

Le stop vaut 3 fois le range du jour. Quand ce range est inhabituellement petit, le stop retombe dans le bruit normal de la
séance : c'est exactement la cause des stops trouvée en session 4. Le stop est mesuré sur la mauvaise chose : la bougie de
5 minutes au lieu de l'agitation habituelle du marché.

### 2.3 Les mauvais jours sont des jours où tout perd en même temps

| | 2018-2026 | 2010-2017 |
|---|---|---|
| Jours perdants | 55,9 % | 55,5 % |
| Jours où tous les trades finissent au stop plein | 20,6 %, en moyenne −1,95 R | 22,4 %, en moyenne −2,15 R |
| Jours où la cassure A est stoppée : résultat du jour | −2,00 R (2,3 trades) | −2,19 R (2,5 trades) |
| Jours où A tient jusqu'à 15:50 : résultat du jour | +1,14 R | +1,12 R |

Les entrées B et D suivent le sort de A. Quand la cassure échoue, elles ajoutent environ −1 R à la perte du jour. La journée se
joue donc presque entièrement sur un point : la cassure de 9:30 va-t-elle tenir ?

### 2.4 Ce que sont les trades perdants

- Environ 53 à 56 % des trades ne gagnent pas.
- Un peu plus de la moitié de ces trades finissent au stop plein (−1 R de leur entrée).
- Environ 40 % vont jusqu'à 15:50 sans avancer, et finissent vers −0,29 R. Ils pèsent dans le taux de réussite, peu dans le
  résultat.

### 2.5 Ce qui n'est pas solide

- **Lundi et mardi** sont un peu plus faibles sur les deux périodes, mais l'écart est petit. Ce n'est pas une piste.
- **Ce qui suit un jour gagnant ou perdant** donne un sens différent selon la période. On l'ignore.

## 3. Ce qui a déjà été essayé, et qu'il ne faut pas refaire

Environ 2 000 essais. Le détail est dans `rapport-session2.md` à `rapport-session4.md`, dans `notes/nasdaq-progress.md` et dans les
registres.

- **Filtres d'indicateurs et de tendance, sans effet :**
  - moyennes mobiles (MA200 H1, H4 et jour, EMA50), DI H4, SAR, RSI H1, MACD, Ichimoku, Fibonacci ;
  - VWAP, 187 indicateurs à l'entrée ;
  - un méta-modèle à 46 indicateurs : il ne prédit pas le stop (score de 0,52 à 0,54, et 0,50 serait le pur hasard).
- **Structure ICT / SMC :** CHoCH, prise de liquidité, FVG, stop suiveur de structure. Ça a détruit le gain.
- **Contexte de la journée :** gap, élan de la première demi-heure, NR4 / NR7, annonces de 8:30, « le Dow confirme le Nasdaq ».
  Rien n'a tenu.
- **Gestion de la sortie :**
  - objectifs fixes de +1 R et +2 R, sortie de la moitié à +1 R ;
  - sorties à 10:30 et à 12:00, entrée après la clôture M5, pas de pyramide ;
  - pyramide à plusieurs étages ;
  - largeurs de stop de 1 à 8 ranges : c'est de là que vient la V10.
- **Le même robot ailleurs :** Dow, DAX, or, devises et Bitcoin. Rien.

## 4. Axes d'amélioration, du plus prometteur au moins

### Axe 1 : traiter les baisses à part
- **L'idée :** une cassure vers le bas n'a pas la même chance de tenir qu'une cassure vers le haut. Le robot devrait exiger plus
  avant de vendre, ou gérer la vente autrement : stop, durée, objectif.
- **Pourquoi c'est crédible :**
  - l'écart tient sur 16 ans et dans les deux tendances de fond ;
  - il existe des explications connues, à vérifier par la recherche : la dérive haussière des actions américaines, et les ventes
    d'ouverture rachetées dans la séance.
- **La version la plus simple :** les achats seulement. On perd moins souvent et la pire baisse est plus faible, mais le gain total
  baisse d'environ 30 %.
- **La bonne version reste à trouver :** une information qui sépare les ventes qui tiennent de celles qui échouent.

### Axe 2 : un stop mesuré sur l'agitation habituelle du marché, pas sur la bougie de 5 minutes
- **L'idée :** les jours à petit range, le stop de 3 ranges tombe dans le bruit et saute 37 à 43 % du temps.
- **À tester :** un stop au moins égal à une mesure du bruit des jours précédents. Par exemple :
  - la moyenne des ranges d'ouverture récents ;
  - la « zone de bruit » de Zarattini et coll. : le mouvement moyen depuis l'ouverture, à cette heure-là, sur les 14 derniers jours.
- **Ce qui a déjà été fait :** jamais testé ainsi. Les largeurs testées étaient toutes des multiples du range du jour. Dans l'étude des
  stops v5, la « zone de bruit » a servi de filtre, pas de stop.

### Axe 3 : lire la position des teneurs de marché sur les options (le « gamma »)
- **L'idée :**
  - quand les teneurs de marché sont « gamma négatif », leurs couvertures amplifient les mouvements, et une cassure a plus de
    chances de continuer ;
  - quand ils sont « gamma positif », ils freinent les mouvements, et les cassures échouent plus souvent.
- **Pourquoi c'est crédible :**
  - c'est l'explication avancée par Baltussen, Da, Lammers et Martens (2021) pour l'élan intrajournalier, source 14 de
    `notes/recherche-web.md` ;
  - c'est aussi une piste pour lire les deux sens, puisque le gamma agit sur les hausses comme sur les baisses.
- **Ce qui a déjà été fait :** jamais testé. La source a été citée, sans les données.
- **Données :** à vérifier par la recherche. SqueezeMetrics publie un historique quotidien gratuit (GEX et DIX) pour le S&P 500.

### Axe 4 : le niveau de peur du marché (VIX et sa courbe)
- **L'idée :** le comportement de l'ouverture change selon la volatilité attendue. Un VIX élevé, ou une courbe inversée (VIX au-dessus
  de VIX3M), signale un marché tendu.
- **Ce qui a déjà été fait :** aucune mesure de volatilité implicite n'a été testée. La volatilité passée (14 et 60 jours) a seulement
  servi à expliquer les écarts entre périodes.
- **Données :** historique quotidien public du CBOE.

### Axe 5, plus fragile : couper B et D quand la cassure montre son échec
- **L'idée :** B et D ajoutent environ −1 R les jours où A échoue. Une règle en temps réel ne les prendrait plus si A est déjà en
  perte au moment du signal.
- **Pourquoi c'est fragile :** B et D ont été construites sur ces données, et toucher à leur gestion revient à régler encore sur le
  passé.

## 5. Comment juger une piste sans se tromper

**Sur quelles données :**
- **Le S&P 500 Dukascopy 2018-2026, bid et ask, est le meilleur juge disponible.**
  - Ces données n'ont jamais été chargées, et la V10 Confort n'a jamais tourné sur le S&P.
  - Seul un contrôle des entrées de la V9 a été fait, sur des données HistData en bid seul, et l'asymétrie achats / ventes n'y a pas
    été regardée.
  - L'indice est différent, mais très lié au Nasdaq : c'est un test à moitié indépendant.
- **Le Dow 2024-2026 n'a jamais été ouvert.** La cassure n'y gagne rien, donc il ne servira qu'à une idée qui ne dépend pas de
  l'avantage de la cassure.
- **Le Nasdaq après le 19/11/2026 et les trades de démo** sont les seules vraies données neuves sur le Nasdaq.

**Comment :**
- Pour chaque axe, écrire avant de regarder : la règle exacte, sans réglage à chercher, le critère de réussite, et les données qui
  jugent.
- Ajouter l'essai au registre.
- Juger une seule fois.

## 6. Prochaines étapes proposées

1. **Recherche documentaire (Research) sur les axes 1 à 4 :**
   - ce que dit la littérature ;
   - quelles données historiques existent pour le gamma et le VIX, et à quelle heure elles sont connues (sans regarder vers le
     futur) ;
   - à quelle forme simple de règle elles mènent.
2. **Recréer le simulateur de la V10 dans le dépôt**, à partir des scripts de l'archive, et vérifier qu'il retrouve +477 R sur
   2018-2026. Charger ensuite le S&P 500 Dukascopy.
3. **Choisir un axe, l'écrire à l'avance, et le juger sur le S&P 500.**
