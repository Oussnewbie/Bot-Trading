# Recherche documentaire (20 novembre 2026)

Synthèse personnelle, sans reprise de texte. Chaque source est suivie de ce qu'elle implique pour notre travail.

1. **Zarattini et Aziz (2023), « Can Day Trading Really Be Profitable? »** — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
   ORB 5 minutes sur l'ETF du Nasdaq (QQQ, puis TQQQ) de 2016 à 2023, annoncé comme nettement supérieur à l'achat passif.
   Pour nous : confirme que la cassure du range de 5 minutes sur le Nasdaq est un effet étudié, pas une trouvaille isolée.
2. **Zarattini, Barbon et Aziz (2024), « A Profitable Day Trading Strategy for the U.S. Equity Market »** —
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
   ORB 5 minutes sur plus de 7 000 actions ; l'avantage se concentre sur les titres « en jeu » (volume anormal, nouvelle) ;
   comparaison avec 15, 30 et 60 minutes. Pour nous : justifie de tester la durée du range (5 min reste le meilleur chez nous)
   et l'idée qu'il faut un « carburant » (chez nous : le gap de la nuit ressort comme allié, le volume relatif non).
3. **QuantInsti (2026), « Opening Range Breakout: Behind the 1,484% Backtest »** —
   https://www.quantinsti.com/articles/opening-range-breakout-strategy/
   Lecture critique : le chiffre vedette dépend du levier et du plafond de position ; l'exécution à l'ouverture est la plus
   difficile à obtenir. Pour nous : cohérent avec notre forte sensibilité au glissement (0,36 R à 1 pt, 0,17 R à 2 pts).
4. **Gao, Han, Li et Zhou (2018), « Market Intraday Momentum », Journal of Financial Economics** —
   https://www.sciencedirect.com/science/article/pii/S0304405X18301351
   Le rendement de la première demi-heure prédit celui de la dernière (1993-2013), surtout les jours volatils.
   Réplication récente : https://temperancecapital.substack.com/p/market-intraday-momentum-replicates — l'effet est plat
   sur 2013-2019. Pour nous : notre test (A2) est perdant après coûts sur 2018-2024 ; piste abandonnée, en accord avec la réplication.
5. **Zarattini, Aziz et Barbon (2024), « Beat the Market: An Effective Intraday Momentum Strategy for SPY »** —
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
   Élan intrajournalier conditionné par une « zone de bruit » autour de l'ouverture, avec stops dynamiques.
   Pour nous : l'idée de n'agir que hors du bruit habituel rejoint nos filtres d'élan ; nos essais de stop suiveur ne font pas mieux
   que la gestion v6 (stop à l'entrée + stop remonté lors de la pyramide).
6. **Kaminski et Lo (2014), « When Do Stop-Loss Rules Stop Losses? »** — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338
   Un stop réduit toujours l'espérance si les prix sont une marche au hasard ; il n'ajoute de la valeur qu'en présence d'élan.
   Pour nous : explique pourquoi serrer le stop (demi-range) ou couper tôt dégrade le résultat.
7. **Bailey, Borwein, López de Prado et Zhu, « The Probability of Backtest Overfitting »** —
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
   Méthode CSCV : on découpe l'historique en blocs, on choisit la meilleure variante sur une moitié et on regarde son rang sur
   l'autre moitié, pour toutes les combinaisons. Pour nous : appliquée à toutes les variantes du registre (étape 8).
8. **Bailey et López de Prado (2014), « The Deflated Sharpe Ratio »** — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
   Corrige la performance pour le nombre d'essais et pour les distributions non normales. Pour nous : appliqué au candidat final,
   avec le nombre d'essais du registre.
9. **Méta-labeling : López de Prado (2018, Advances in Financial Machine Learning) ; Singh et Joubert (Hudson & Thames)** —
   https://hudsonthames.org/wp-content/uploads/2022/04/Does-Meta-Labeling-Add-to-Signal-Efficacy.pdf
   Un premier modèle donne le sens, un second décide de prendre ou non (et de la taille). Pour nous : étape 7, avec une
   régression logistique simple et une validation dans le temps uniquement.
10. **Crabel (1990), journées étroites NR4/NR7** — https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/narrow-range-day-nr7
    Une contraction de volatilité précède souvent une expansion. Pour nous : NR4/NR7/inside testés sur la v6, sans effet ;
    en revanche « pas de trade après un trade gagnant » (après une expansion) ressort nettement.


# Recherche documentaire — session 3 (21 novembre 2026)

Synthèse personnelle, sans reprise de texte. Thème : que vaut un backtest une fois sorti de la période qui a servi à le construire ?

11. **Suhonen, Lennkh et Perez (2017), « Quantifying Backtest Overfitting in Alternative Beta Strategies »** —
    https://research.aalto.fi/en/publications/quantifying-backtest-overfitting-in-alternative-beta-strategies/
    215 stratégies vendues par des banques : le ratio rendement / risque chute de 73 % en médiane entre le backtest et le réel,
    d'autant plus que la stratégie est complexe. Pour nous : notre rabais hors échantillon (gain par trade divisé par 2 à 4) est dans la norme.
12. **Wiecki, Campbell, Lent et Stauth (2016), « All that Glitters Is Not Gold »** — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2745220
    888 algorithmes : les mesures de backtest prédisent mal la performance suivante ; plus l'auteur a fait de backtests, plus l'écart est grand.
    Pour nous : ~1 770 essais sur 2018-2026 ; seule la période jamais vue compte comme mesure.
13. **McLean et Pontiff (2016), « Does Academic Research Destroy Stock Return Predictability? »** — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623
    Rendements 26 % plus faibles hors échantillon et 58 % après publication. Pour nous : une part du rabais est du surajustement, une part de l'usure.
14. **Baltussen, Da, Lammers et Martens (2021), « Hedging Demand and Market Intraday Momentum »** — https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598
    L'élan intrajournalier est lié aux couvertures des vendeurs d'options. Pour nous : une cause structurelle, donc variable dans le temps ;
    cohérent avec un avantage plus fort depuis 2018 qu'avant, sans que nous puissions le prouver.
15. **EdgeLab (2026), ORB sur 16 ans de contrats à terme Nasdaq** — https://edgelabtrading.com/blog/opening-range-breakout-nasdaq/
    La version naïve (cassure dans les deux sens, sans filtre) perd ; une version filtrée garde un avantage modeste hors échantillon, en baisse
    depuis deux ans. Pour nous : même ordre de grandeur que notre mesure hors échantillon ; l'ORB n'est pas mort mais il est mince.
16. **Backtests, Not Signals (2026), « Opening Range Breakout: Real Edge or Backtest Illusion? »** — https://backtestsnotsignals.substack.com/p/opening-range-breakout-real-edge
    ORB sur le micro Nasdaq avec validation hors échantillon, filtre de tendance et arrêt après une perte dans la séance.
17. **G. Brusco, nq-intraday-breakout (GitHub)** — https://github.com/giovannibrusco/nq-intraday-breakout
    Audit de l'effet des conventions de simulation ; rappelle qu'un stop ou un coût fixe en dollars ne pèse pas pareil quand l'indice change d'échelle.
    Pour nous : c'est exactement la leçon du coffre (le poids du coût dans le range décide du résultat).
18. **Réserve fédérale, calendriers historiques du FOMC** — https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm
    Dates des réunions 2011-2017 vérifiées une à une (scripts/65_verifier_fomc.py) : identiques à la liste utilisée.
