# Strategy V10 — cassure de l'ouverture de New York

Un robot de trading intrajournalier pour les **indices américains**, en deux versions qui suivent les mêmes règles :

- `robot/Strategy-V10.mq5` : l'Expert Advisor MetaTrader 5 (version 10.00). C'est la version de référence, car il voit le bid et l'ask.
  `robot/Strategy-V10.ex5` est le même robot déjà compilé.
- `robot/Strategy-V10.pine` : le script TradingView (Pine v6), avec ses alertes et le calcul du lot à passer chez le courtier.

**Où il tourne.** Il est en service sur le **Nasdaq (NAS100)**. Le Dow Jones et le S&P 500 sont à l'étude : rien n'est encore
validé sur ces deux indices (voir « Limites connues »).

**Étrave** (`etrave/`) est une page web locale qui règle et surveille l'EA : risque par trade, levier, Telegram, clôture d'un trade
et lancement de MetaTrader.

Toutes les heures sont celles de New York (9:30 NY = 15:30 à Paris la plupart de l'année). Ce n'est pas un conseil en investissement.

| Dossier | Contenu |
|---|---|
| `robot/` | Le robot : `.mq5`, `.ex5` et `.pine` |
| `etrave/` | L'interface locale de l'EA (Python, sans dépendance) et ses tests |
| `recherche/` | Les rapports de recherche, le journal, les idées écrites avant les tests, et les trades simulés de la V10 qui servent de référence |
| `CLAUDE.md` | Les consignes de travail sur ce dépôt |

## Les règles

**Le trade de cassure (A)**
1. **Range** : le plus haut et le plus bas de la bougie M5 de 9:30.
2. **Filtres** : l'achat est permis si le RSI14 M5 de cette bougie est au-dessus de 50 **et** si son plus haut dépasse le plus haut
   de 9:00-9:30. La vente suit la règle inverse. Si aucun côté n'est permis, pas de trade.
3. **Ordres** : à 9:35, un achat stop sur le haut et/ou une vente stop sur le bas, valables jusqu'à 9:45. Le premier exécuté annule
   l'autre.
4. **Stop élargi (profil Confort)** : 3 ranges au-delà du niveau de cassure. La taille est 3 fois plus petite qu'avec un stop d'un
   range, donc la somme risquée (1 R) ne change pas.
5. **Gestion** :
   - le stop passe au prix d'entrée dès +1,5 R ;
   - **pyramide** : quand une bougie clôture à +2 R, on ajoute 2 unités et le stop de l'ensemble monte à 1 R sous le prix de l'ajout ;
   - sortie à 15:50, ou à 12:45 les jours fériés américains et les demi-séances.
6. **Mémoire** : après un trade de cassure qui finit à plus de +1 R, le signal suivant n'est pas pris.
7. **Jours sans trade** : décisions de la Fed (FOMC), jours fériés américains et demi-séances.

**Les entrées de plus, seulement les jours où la cassure est prise, et dans son sens**
- **B · repli VWAP** : la première bougie M5 qui revient toucher le prix moyen de séance (à 0,1 range près), puis clôture du bon
  côté. Entrée au marché, jusqu'à 14:00.
- **D1, D2, D3 · continuations** : à la clôture des bougies de 9:35, 9:40 et 9:45, un ordre stop est posé sur l'extrême de la
  bougie, valable 10 minutes. Elles ne sont armées que si l'autre bord du range n'a pas été touché depuis la cassure.
- **C · entrée de 10:00** : coupée par défaut.
- B et D suivent la même gestion que A et ne risquent jamais plus de 1 R chacune. On peut avoir jusqu'à 5 positions ouvertes en même
  temps, toutes dans le même sens.

**Garde-fou coût** : aucun ordre ce jour-là si le spread plus 2 glissements pèse plus de 25 % du risque.

**Profil Tendance (la V9)** : largeur du stop = 1 et « gagnant au-delà de » = 0,05. Il gagne moins souvent, avec des pertes en série
plus longues.

**Risque par défaut** : 0,25 % du solde par trade. Le remonter double les gains comme les baisses. Si Étrave donne un risque, c'est
lui qui est utilisé.

## MetaTrader 5

1. Hors séance et sans trade ouvert, retire tout ancien robot (ORB v6, V9…) du graphique.
2. Copie `robot/Strategy-V10.mq5` dans `MQL5\Experts\Etrave`, ouvre-le dans MetaEditor et appuie sur F7 (tu dois lire « 0 errors »).
   Tu peux aussi copier `Strategy-V10.ex5` directement, ou cliquer sur « Installer ou mettre à jour l'EA » dans Étrave.
3. Glisse Strategy-V10 sur le graphique **M5** du Nasdaq et coche « Autoriser le trading algorithmique ».
4. Vérifie l'heure de New York affichée par le panneau. Si elle est fausse, corrige « Décalage GMT du serveur » et « Heure d'été du
   serveur ». Vérifie aussi la ligne « Entrées V10 : B … · C coupée · D … ».

À savoir :
- **Compte « hedging » obligatoire.** Sur un compte « netting », B et D sont coupées et seule la cassure est prise.
- **Numéros magiques** : A = 50930 (réglage), B = +1, C = +2, D1 à D3 = +3 à +5. Ce sont les mêmes que la V9 : ne fais jamais
  tourner les deux sur le même compte.
- **Dates FOMC** : celles de 2018 à 2026 sont dans le code. Pour 2027 et après, saisis-les dans « Jours FOMC après 2026 » dès que la
  Fed les publie, au format `2027.01.27` séparé par des virgules. Sinon le robot trade ces jours-là.
- **État** : le robot repart d'un état neuf (préfixe `StratV10_`). Installe-le un jour sans position.
- **Telegram** : dans Outils > Options > Expert Advisors, autorise `https://api.telegram.org` pour WebRequest.
- **Où le faire tourner** : ton ordinateur pour la démo (sans mise en veille), un VPS Windows pour le réel. MetaTrader doit rester
  ouvert de 9:30 à 15:50 New York.

### Le test à faire dans le testeur de stratégie
1. Ouvre Affichage > Testeur de stratégie et règle-le ainsi :
   - Expert : `Etrave\Strategy-V10`, symbole : ton Nasdaq, période : M5 ;
   - dates : les 12 derniers mois ;
   - modélisation : « Chaque tick basé sur des ticks réels » ;
   - compte hedging, levier 1:100.
2. Dans le Journal, tu dois voir passer « ORDRES PLACÉS … 1R = … », « entrée D1 guettée », « ACHAT D1 exécuté(e) »…
3. Enregistre le rapport en HTML pour le comparer trade par trade à
   `recherche/resultats/trades_V10_confort_2018_2026_1pt.csv`.
   - **Ordre de grandeur simulé** du 20 novembre 2025 au 19 novembre 2026 : environ 410 trades sur 122 jours, environ 50 % de gagnants
     et +76 R.
   - **Si le testeur ne colle pas**, ne passe pas en réel : c'est le cas avec nettement moins de trades, moins de 35 % de gagnants ou
     un résultat négatif.

### L'interrupteur : quand couper le robot
Sur 60 jours de trade (environ 6 mois), coupe le robot et fais le point si l'un de ces seuils est franchi :
- moins de 28 % de jours gagnants (16 ou moins sur 60) ;
- un total pire que −40 R ;
- une baisse de plus de 66 R depuis le dernier plus haut.

Ces seuils ne sont pas codés dans le robot. Le détail est dans `recherche/resultats/83_surveillance.md`.

## TradingView

1. Ouvre un graphique **M5** du NAS100, avec les bougies hors séance. Dans l'éditeur Pine, colle tout `robot/Strategy-V10.pine`, puis
   « Ajouter au graphique ». Dans « Propriétés », ajoute une commission égale au spread de ton courtier.
2. Crée une alerte sur la stratégie, avec la condition « Appels de la fonction alert() uniquement ». Pour Telegram, utilise le webhook
   `https://api.telegram.org/bot<TOKEN>/sendMessage` et renseigne le Chat ID dans les réglages. Après chaque mise à jour du script,
   supprime puis recrée l'alerte.
3. **Lot à passer chez le courtier** (groupe « Lots chez le courtier ») :
   - renseigne la taille de contrat (20 pour le NAS100 chez FundingPips : 1 lot = 20 $ par point) et le solde de ton compte ;
   - le script affiche alors le lot à saisir, déjà divisé par 3 avec le stop élargi.

**Lire le graphique**

| Ce que tu vois | Ce que ça veut dire | Ce que tu fais |
|---|---|---|
| Rectangle gris « 9:30 » et tirets verts / rouges « Achat stop · prix · lot » | les ordres de la cassure (A) sont à poser | poser l'ordre stop au prix indiqué, avec le lot affiché ; stop sur la ligne « SL » (3 ranges plus loin) |
| **Ligne orange** | le prix moyen de la séance (VWAP) depuis 9:30 | rien, c'est le repère de B |
| **Bande bleue** collée à la ligne orange | B est guettée | surveiller |
| **Étiquette bleue « ACHAT B »** (ou « VENTE B ») | signal B : la bougie a touché la bande et clôturé du bon côté | entrer au marché ; stop sur la ligne bleue « SL B » ; lot dans l'infobulle et l'alerte |
| **Tirets vert foncé « D1 stop · prix »**, juste après 9:40 | une continuation est guettée pendant 10 minutes | poser un ordre stop à ce prix, dans le sens de la cassure, avec le stop indiqué |
| Alerte « ACHAT D1 EXÉCUTÉ » | l'ordre a été touché | vérifier que le stop est en place |
| Tirets qui disparaissent sans exécution | pas de dépassement en 10 minutes, ou stop touché d'abord | annuler l'ordre s'il est encore chez le courtier |
| Petite étiquette « + » | pyramide sur cette entrée | ajouter 2 fois la taille de départ, remonter le stop au prix indiqué |
| « ⏸ mémoire », « ⏸ FOMC », « ⏸ férié » au-dessus du range | pas de trade aujourd'hui, et pourquoi | rien |

Le tableau en haut à droite dit la même chose en clair, ligne par ligne : A, B, C (« coupée »), D, Mémoire, puis l'historique en R et
le lot.

**Écarts avec l'EA.** TradingView ne voit que des bougies de 5 minutes et ne compte pas le spread : ses résultats sont un peu plus
beaux. Le VWAP dépend du volume, qui diffère d'un fournisseur à l'autre : le signal B peut se décaler d'une bougie. L'EA reste la
version de référence.

## Étrave (l'interface de l'EA)

1. Installe Python 3 ([python.org](https://www.python.org/downloads/), coche « Add python.exe to PATH »). Rien d'autre n'est nécessaire.
2. Double-clique sur `etrave/Etrave.bat`. La page s'ouvre sur `http://127.0.0.1:8788` (ailleurs que sous Windows :
   `python etrave/etrave.py`).

Ce qu'on trouve dans la page :
- **Vue d'ensemble** : solde, trade en cours, résultat cumulé en argent, en % et en R, courbe et liste des trades. La case du Nasdaq,
  une fois décochée, empêche tout nouveau trade. Le bouton « Clôturer » ferme toutes les positions du jour (A, B, D).
- **Risque** : le risque par trade (de 0,05 % à 20 % ; au-delà de 1 %, il faut taper RISQUE) et le levier du courtier.
  **Attention** : la simulation de cette page rejoue encore les trades de l'ancienne ORB v6 (`etrave/reference.json`), pas ceux de la V10.
- **Connexions** :
  - **Telegram** : jeton, recherche de la discussion, essai depuis MetaTrader.
  - **MetaTrader 5** : connexion à un compte, installation de l'EA (copie et compilation de `robot/Strategy-V10.mq5`), ouverture
    automatique de MetaTrader et lancement au démarrage de Windows.

L'interface et l'EA se parlent par des fichiers du dossier commun de MetaTrader (`…\MetaQuotes\Terminal\Common\Files\Etrave`). L'interface
ne passe aucun ordre : on peut la fermer sans rien changer à l'EA.

Côté sécurité, elle n'écoute que sur 127.0.0.1, avec un jeton tiré au hasard à chaque lancement, et le jeton Telegram n'est jamais
réaffiché. N'ouvre jamais le port 8788 sur internet.

Tests : `python -m pytest etrave`, à la racine du dépôt. Ils vérifient l'interface et son accord avec l'EA et le script Pine : mêmes
fichiers, mêmes clés, mêmes bornes, même calendrier des jours fériés.

## Limites connues

- **Le robot n'a jamais été vu en train de tourner.** Le `.mq5` compile sans erreur (MetaEditor, 21 novembre 2026) et le `.pine` passe
  l'analyseur de TradingView, mais personne ne l'a encore vu passer un ordre. Il faut le testeur de stratégie, puis une démo, avant
  tout argent réel.
- **Nasdaq seulement, pour l'instant.**
  - Le Dow Jones testé tel quel ne gagne rien.
  - Le S&P 500 n'a eu qu'un contrôle de la version précédente, avec un avantage qui disparaît à coûts doublés.
  - Sur ces deux indices, l'EA ne se règle pas depuis Étrave, qui ne connaît que le Nasdaq.
  - Plusieurs réglages sont en points d'indice, calibrés pour le Nasdaq : glissement supposé et marge du stop de B dans l'EA, coût
    du garde-fou dans le script.
- **Le glissement réel décide de tout.** Les tests supposent 1 point par exécution. Avec 3 points, le gain baisse d'environ 37 % et la
  pire baisse double. Relève le glissement que l'EA annonce dans le message « exécuté ».
- **Plateaux.** Le profil Confort a des baisses peu profondes, mais le capital peut stagner longtemps : jusqu'à 20 mois dans les tests
  2018-2026.
- **Le profil Confort a été réglé après avoir vu tout l'historique du Nasdaq.** Ses chiffres (`recherche/rapport-session4.md`) ne sont
  pas une preuve.
- **Jours fériés.** Une fermeture exceptionnelle de la Bourse (deuil national, panne) n'est pas dans le calendrier : ce jour-là, la
  position passerait la fermeture.
- **Ordres en attente.** Ne supprime pas à la main les ordres Buy Stop / Sell Stop de l'EA : 10 secondes après leur disparition, il
  renonce au trade du jour.
- **Après un plantage de MetaTrader**, l'état de l'EA peut être ancien.
