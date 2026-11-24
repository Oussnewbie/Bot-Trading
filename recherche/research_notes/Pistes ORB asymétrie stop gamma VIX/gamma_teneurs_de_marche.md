# Gamma des teneurs de marché (GEX), momentum intraday et cassures d'ouverture sur S&P 500 / Nasdaq 100

Notes de recherche du 24 novembre 2026. Robot visé : cassure du range des 5 premières minutes à 9:30 New York sur le CFD Nasdaq 100, deux sens, stop à 3 fois le range, sortie à 15:50.

Niveaux de preuve utilisés ci-dessous :
- **[lu en entier]** : texte primaire téléchargé et lu (Baltussen et al. 2021, livre blanc GEX de SqueezeMetrics, note SqueezeMetrics du 19/04/2020, « The Implied Order Book », Zarattini, Aziz et Barbon 2024).
- **[résumé secondaire]** : seulement via un résumé ou une page d'auteur (Adams et al., Dim, Eraker et Vilkov, Ni et al., Barbon et Buraschi).
- **[extrait de recherche]** : seulement via un extrait de moteur de recherche, non vérifié sur la page.
- **[calcul propre]** : calcul fait sur le fichier DIX.csv téléchargé le 24/11/2026 et sur ses copies de la Wayback Machine.
- **[commercial / faible]** : billet non relu par des pairs, publié par un vendeur.

## 1. Baltussen, Da, Lammers et Martens (2021, JFE), « Hedging Demand and Market Intraday Momentum » : que trouve exactement l'article ?

### Takeaway
Sur l'indice S&P 500, le rendement « reste de la journée » (de la clôture de la veille jusqu'à 30 minutes avant la clôture) ne prédit la dernière demi-heure que lorsque le gamma net des teneurs de marché de **la veille** (NGE t−1) est négatif : bêta 6,63 (t = 4,78, R² 3,58 %), contre 0,82 (t = 1,03, R² 0,05 %) quand il est positif. Le test gamma porte seulement sur le S&P 500 et seulement sur la dernière demi-heure. Le Nasdaq 100 montre le momentum intraday sans condition, mais il n'a pas été testé avec le gamma.

### Cited Findings
- **Échantillon et marchés** [lu en entier] : plus de 60 contrats à terme (actions, obligations, matières premières, devises), de décembre 1974 à mai 2020. La dernière demi-heure (r_LH) est prédite par le reste de la journée (r_ROD, de la clôture de la veille à 30 min avant la clôture). La prédictibilité « s'inverse les jours suivants » — [Baltussen et al. 2021, JFE 142:377-403, PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Nasdaq 100 inclus, sans condition de gamma** [lu en entier] : NQ de 1996-04-12 à 2020-05-01 (6 017 jours, séance 9:30-16:00) ; ES de 1982-04-23 à 2020-05-01 (9 535 jours) — [Baltussen et al. 2021, tableau A1](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Régressions par marché** [lu en entier] (coefficients ×100, t entre parenthèses) :
  - NQ : β_ROD = 6,36 (7,97), R² 4,10 %, R² hors échantillon 3,76 % ; β_ONFH (veille + première demi-heure) = 7,45 (5,33), R² 2,01 %.
  - ES : β_ROD = 6,18 (4,97), R² 3,41 %, R² hors échantillon 2,29 % ; β_ONFH = 5,24 (3,38), R² 0,98 %, R² hors échantillon −1,68 %.
  - [Baltussen et al. 2021, tableau en annexe, panneau B](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Toutes les actions ensemble** [lu en entier] : β_ROD = 4,14 (t 7,50). La dernière demi-heure de la veille s'inverse : β_LH,t−1 ≈ −6,7 (t ≈ −2,7) — [Baltussen et al. 2021, tableau 4](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Mesure du gamma (NGE)** [lu en entier] :
  - Calculée sur tout l'intérêt ouvert des options sur l'indice S&P 500 (OptionMetrics de 1996 à fin 2017, puis données SqueezeMetrics jusqu'en mai 2020).
  - Hypothèses : (i) toutes les options passent par des teneurs qui couvrent leur delta ; (ii) les calls sont vendus par les investisseurs et achetés par les teneurs ; (iii) les puts sont achetés par les investisseurs et vendus par les teneurs ; (iv) les teneurs couvrent exactement leur delta.
  - Formule : NGE = Σ Γ·OI·(+100 pour les calls, −100 pour les puts)·P_t, divisé par la capitalisation du S&P 500.
  - Les auteurs disent avoir vérifié les calculs de SqueezeMetrics sur OptionMetrics de 2002 à 2017, avec des résultats « virtually identical ».
  - [Baltussen et al. 2021, section 4.1, éq. 13-15 et note 7](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Répartition des jours** [lu en entier] : de 1996 à mai 2020, 2 930 jours à NGE négatif et 3 158 à NGE positif. La note 8 précise que la mesure ne couvre que les options cotées et ignore les positions de gré à gré (OTC) — [Baltussen et al. 2021, section 4.1 et note 8](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Tableau 7, effet conditionnel** [lu en entier] : contrat à terme S&P 500, janvier 1996 à mai 2020, t de Newey-West, coefficients ×100. **Le conditionnement utilise NGE t−1**, donc sans regard vers l'avant.
  - NGE t−1 ≥ 0 : constante 0,00 (0,17) ; β_ROD = 0,82 (1,03) ; R² 0,05 %.
  - NGE t−1 < 0 : constante −0,01 (−0,63) ; β_ROD = 6,63 (4,78) ; R² 3,58 %.
  - Selon les auteurs, des tests non publiés donnent le même résultat avec le rendement veille + première demi-heure (r_ONFH) ou avec le rendement entre la première et la dernière demi-heure (r_M).
  - [Baltussen et al. 2021, tableau 7](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Tableau 8, gamma continu** [lu en entier] :
  - r_ROD seul : 1,41 (1,72) ; terme I(NGE≤0)·r_ROD : 5,05 (3,04).
  - NGE·r_ROD : −123,04 (−3,42) : plus le NGE est négatif, plus le momentum est fort.
  - En différences : ΔNGE·Δr_ROD = −119,79 (−4,06). R² de 2,32 à 4,63 %.
  - Le résultat tient aussi avec les puts seuls.
  - [Baltussen et al. 2021, tableau 8](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Taille économique** [lu en entier] : la stratégie qui prend la dernière demi-heure dans le sens de r_ROD, sur un portefeuille à poids égaux de contrats actions, rapporte 6,86 %/an pour 3,96 % de volatilité (Sharpe 1,73, 55 % de jours gagnants). Avec le signal r_ONFH : 4,21 %/an, Sharpe 1,07. « Toujours long » sur la dernière demi-heure : 0,44 %/an, Sharpe 0,11. Ces chiffres sont **avant coûts** ; sur ES, le Sharpe net reste positif avec un coût d'un tick — [Baltussen et al. 2021, tableau 6 et section 3.5](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Autre source de couverture** [lu en entier] : les ETF à effet de levier rebalancent près de la clôture (demande = NAV·(x²−x)·r). Cheng et Madhavan estimaient qu'en février 2009 cette demande pesait 16,8 % (50,2 %) du volume au fixing de clôture un jour à 1 % (5 %) de variation — [Baltussen et al. 2021, section 4.2](https://academicweb.nd.edu/~zda/intramom.pdf)

### Inferences
- Ordre de grandeur : avec un rendement « reste de la journée » de +1 %, la dernière demi-heure attendue vaut environ +6,6 points de base les jours à gamma négatif, et environ +0,8 point de base (non significatif) les jours à gamma positif. L'effet est petit en points mais concentré sur les jours à gamma négatif.
- Le robot sort à 15:50. Il ne capte donc que 20 des 30 dernières minutes étudiées par l'article, et l'essentiel de son résultat se joue entre 9:35 et 15:30, une plage que le tableau 7 ne teste pas directement. Le test non publié avec r_M (de la fin de la première demi-heure à la dernière heure) est le plus proche du robot, mais il n'est pas chiffré.
- Pour le Nasdaq 100, on n'a qu'un momentum sans condition (β 6,36). L'effet du gamma est démontré sur le S&P 500, puis supposé valoir pour le Nasdaq 100.

### Gaps
- Aucun tableau ne conditionne les rendements du **matin** (cassure d'ouverture, de 9:35 à midi) sur le gamma : le résultat r_ONFH / r_M conditionné est « non publié ».
- La comparaison long/short par signe du gamma n'est pas publiée. L'article ne dit rien de l'asymétrie long/short.

## 2. Que disent les autres études sur le gamma des teneurs de marché et la dynamique intraday, depuis 2022 (0DTE) et sur la première demi-heure ou la première heure ?

### Takeaway
Les preuves de base vont dans le même sens : gamma négatif = volatilité plus forte et momentum ; gamma positif = volatilité plus faible et retours vers la moyenne. Cela vaut pour l'indice (SqueezeMetrics, Baltussen) et pour les actions individuelles (Ni et al. ; Barbon et Buraschi). Depuis 2022, les études sur les options à échéance du jour (0DTE) montrent que les teneurs sont plutôt **longs** gamma et que leur couverture **amortit** les mouvements, avec un effet qui s'éteint en une heure environ. Le momentum de fin de journée sans condition semble avoir disparu sur le S&P 500 depuis 2022, mais cette preuve est faible. Aucune étude trouvée ne teste une cassure d'ouverture contre le gamma.

### Cited Findings
- **Livre blanc SqueezeMetrics, « Gamma Exposure (GEX) »** [lu en entier] (mars 2016, révisé en décembre 2017) :
  - Formule : GEX = Γ·OI·100 pour les calls et Γ·OI·(−100) pour les puts, additionné sur tous les prix d'exercice et toutes les échéances ; pour le SPX, le résultat est exprimé en dollars.
  - Mêmes quatre hypothèses que Baltussen (calls vendus par les investisseurs, puts achetés).
  - Résultat : écart-type des rendements SPX à 1 jour de 0,55 % après le quartile de GEX le plus haut, contre 0,85 % après le deuxième. Pour le VIX, 0,51 % après le quartile le plus bas contre 0,66 % après le deuxième.
  - Interprétation des auteurs : un GEX positif fait que les teneurs achètent les creux et vendent les sommets, donc étouffe la volatilité ; un GEX négatif l'amplifie. Leur graphique compare les rendements SPX au GEX **de la veille**.
  - [SqueezeMetrics, livre blanc GEX (PDF)](https://squeezemetrics.com/download/white_paper.pdf)
- **SqueezeMetrics, « The Implied Order Book »** [lu en entier] (6 juillet 2020) :
  - Le GEX est maintenant calculé sur une position directionnelle des teneurs (« Dealer Directional Open Interest », DDOI), reconstruite à partir des transactions SPX signées une par une, puis vérifiée contre les variations réelles d'intérêt ouvert.
  - « A thorough analysis of SPX GEX back to 2004 yields... GEX is very rarely negative » : jamais en dessous de −200 M$ par point de SPX, parfois au-dessus de 1 Md$ par point.
  - [SqueezeMetrics, The Implied Order Book (PDF)](https://squeezemetrics.com/monitor/download/pdf/The_Implied_Order_Book.pdf)
- **Note SqueezeMetrics du 19/04/2020** [lu en entier] :
  - Lancement de « GEX 2.0 » : abandon des hypothèses d'origine (« all calls are sold, all puts are bought »), analyse des transactions jusqu'en 2004, ajout du vanna.
  - Observation : quand les teneurs sont longs gamma, ils « laissent passer » les écarts de la nuit et étouffent la volatilité pendant la séance ; les auteurs attendent « un léger retour vers la moyenne ».
  - [SqueezeMetrics, note hebdomadaire du 19/04/2020 (PDF)](https://notes.squeezemetrics.com/2020-04-19.pdf)
- **Ni, Pearson, Poteshman et White (2021), Review of Financial Studies 34(4):1952-1986** [résumé secondaire] : relation négative très significative entre le gamma de la position nette des couvreurs probables et la volatilité de l'action. Gamma positif = moins de volatilité, gamma négatif = plus de volatilité, et plus de risque de grands mouvements. L'étude porte sur **des actions individuelles**, pas sur des indices — [RePEc](https://econpapers.repec.org/RePEc:oup:rfinst:v:34:y:2021:i:4:p:1952-1986.) ; [version de travail](https://ou.edu/dam/price/Finance/CFS/paper/pdf/pearsonPoteshmanWhite.pdf)
- **Barbon et Buraschi, « Gamma Fragility »** [résumé secondaire] (document de travail, dernière révision le 19/03/2021) :
  - « Intra-day momentum (reversal) is explained by the interaction of negative (positive) ex-ante gamma imbalance » combinée au manque de liquidité ; l'effet est plus fort sur les titres les moins liquides.
  - Le déséquilibre de gamma est lié à la fréquence et à l'ampleur des krachs éclair.
  - Panel d'options sur actions ; aucun chiffre sur la page.
  - [page de l'auteur](https://abarbon.com/papers/gamma-fragility). Le co-auteur Buraschi est confirmé par la bibliographie de [Zarattini et al. 2024, réf. 21](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content).
- **Zarattini, Aziz et Barbon (2024), « Beat the Market », SPY** [lu en entier] :
  - Données : SPY en barres d'une minute (IQFeed), de mai 2007 à avril 2024.
  - Stratégie : momentum intraday avec une « zone de bruit » ; première position à 10:00.
  - Résultats : version de base 6,2 %/an, Sharpe 0,61 ; version avec dimensionnement selon la volatilité et stops suiveurs 19,6 %/an, Sharpe 1,33, perte maximale 25 %, environ 43 % de jours gagnants.
  - Texte extrait du PDF : « when the VIX is above 6, the Sharpe Ratio is approximately 1.50; ... when the VIX exceeds 40, the Sharpe Ratio escalates to ... 3.50 ». Le seuil « 6 » a peut-être été déformé par l'extraction du PDF (16 ?). Ce n'est pas vérifié sur la figure 8. La tendance reste claire : le Sharpe monte avec le VIX à l'ouverture.
  - **Section 4.5 « Gamma Imbalance » : les auteurs n'estiment PAS le gamma.** Ils prennent comme substitut le RSI 5 jours du SPY à la clôture de la veille : β = −3,25 point de base par point de RSI (p = 0,001). Leur lecture : après une baisse, les teneurs passent plus probablement à un gamma négatif et la stratégie gagne plus.
  - C'est un **indicateur de prix**, pas une mesure de gamma.
  - [Zarattini, Aziz et Barbon 2024, SFI 24-97 (PDF)](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- **Adams et al., « Do S&P500 Options Increase Market Volatility? Evidence from 0DTEs »** [résumé secondaire] (SSRN 5641974) :
  - La volatilité de l'indice est plus basse de 60 points de base annualisés les jours où les 0DTE existent (le résumé compare des jours avec et sans 0DTE avant 2022, sans préciser clairement lesquels) ; l'écart disparaît quand les 0DTE deviennent quotidiens.
  - Les besoins de couverture valaient environ 1 % avant 2022 ; les 0DTE les augmentent de 0,15 point. Un point de base de besoins en plus va avec 4 points de base de volatilité en moins.
  - Ce sont surtout les **positions plus longues qui arrivent à échéance** qui comptent (+24 points de base le jour d'échéance), contre +3 points de base pour les nouvelles positions 0DTE.
  - Les teneurs restent nets **positifs** en gamma tout au long de la journée d'échéance. Un gamma net plus élevé annonce moins de volatilité dans les 10 minutes suivantes, des retours plus forts du flux d'ordres sur les contrats E-mini et un momentum négatif à haute fréquence. **Tous ces effets s'éteignent en une heure environ.**
  - [Quantpedia, résumé de Adams et al.](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/)
- **Dim, Eraker et Vilkov (2024), « 0DTEs: Trading, Gamma Risk and Volatility Propagation »** [résumé secondaire] (SSRN 4692190) :
  - Aucune preuve que le gamma de l'intérêt ouvert des 0DTE propage ou augmente sans condition la volatilité de l'indice.
  - Un gamma plus élevé sur les 0DTE et les échéances courtes va avec une volatilité réalisée plus basse dans la journée.
  - Gamma mesuré « avec l'intérêt ouvert à l'ouverture et les gammas en dollars peu après ».
  - [Harbourfront Quant, résumé](https://harbourfrontquant.substack.com/p/impact-of-zero-dte-options-on-the) ; SSRN refuse la lecture automatique (code 403).
- **Cboe, Mandy Xu, « 0DTEs Decoded »** [lu, page de blog] (2 mai 2025) :
  - La couverture du gamma net des teneurs reste « de minimis, representing at best, just 0.2% of the SPX daily liquidity ».
  - L'activité des clients sur les 0DTE est « extremely balanced ».
  - Environ 2 millions de contrats 0DTE par jour, dont 50 à 60 % pour les particuliers. La méthode n'est pas décrite sur la page.
  - [Cboe Insights](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)
- **Billet FirmTape** [commercial / faible] :
  - 1 085 séances SPX, du 2022-04-14 au 2026-08-20 : la pente « dernière demi-heure contre reste de la journée » vaut +0,006 (t +0,6), jamais significative sur une année, avec des signes qui alternent.
  - Les jours de clôture en gamma court, la pente gagne +0,055 (t +3,1), positif chaque année. Ces jours représentent environ 15 % des séances.
  - Leur gamma vient de leur propre lecture des transactions 0DTE signées **à 15:30**, donc mesurée dans la journée et non la veille.
  - Une version fondée sur l'intérêt ouvert public ne montre « aucun » effet (sans chiffre). Billet promotionnel.
  - [dev.to, FirmTape](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0)
- **Mémoire de licence de Princeton, avril 2026** [extrait de recherche] : le canal « couverture qui s'auto-entretient » n'ajoute pas de pouvoir prédictif aux prévisions de variance intraday — [Princeton, mémoire](https://theses-dissertations.princeton.edu/entities/publication/61115cd1-cb09-4a8b-9230-ff488fc2a386)
- **Cassure d'ouverture (ORB) sur actions** [extrait de recherche] : Zarattini, Barbon et Aziz, « A Profitable Day Trading Strategy For The U.S. Equity Market » (SFI 24-98, SSRN 4729284), étudie surtout l'ORB à 5 minutes sur plus de 7 000 actions américaines. Je n'ai trouvé aucun test contre le gamma dans les extraits — [IDEAS/RePEc](https://ideas.repec.org/p/chf/rpseri/rp2498.html)

### Inferences
- L'effet le plus robuste du gamma est un effet de **volatilité** : un gamma bas ou négatif annonce de plus grandes amplitudes. Un effet de **direction** (continuation contre retour) est mieux établi pour la fin de journée que pour le matin.
- Pour une cassure à 9:35, Adams et al. suggèrent qu'un gamma positif freine les mouvements dans l'heure qui suit. C'est l'heure exacte où la cassure doit « partir ».
- Le rôle des positions plus longues qui arrivent à échéance (+24 points de base contre +3) laisse penser qu'un GEX calculé sur l'intérêt ouvert de la veille capte encore une bonne part du gamma du jour, même avec les 0DTE. C'est une déduction, pas un résultat testé.
- Le seul « effet gamma » publié sur une stratégie de momentum intraday sur SPY (Zarattini et al.) repose en réalité sur un RSI. Or l'utilisateur a déjà constaté que les indicateurs de prix ne prédisent pas les cassures ratées. Un filtre GEX n'a donc d'intérêt que s'il apporte une information **en plus** des rendements et de la volatilité récents (voir question 5).

### Gaps
- Je n'ai trouvé **aucune étude** sur cassure d'ouverture et gamma, ni sur la première demi-heure ou la première heure conditionnée au GEX de la veille, pour le S&P 500 ou le Nasdaq 100.
- Aucune étude trouvée ne dit si le gamma touche les cassures haussières et baissières différemment.
- Les textes complets d'Adams et al., de Dim, Eraker et Vilkov et de Ni et al. n'ont pas été lus : SSRN renvoie 403 et la RFS est payante. Les chiffres viennent de résumés.
- Il n'existe aucune réplication du résultat FirmTape relue par des pairs.

## 3. Quelles données de gamma historiques sont gratuites, quand chaque valeur est-elle publiée, et couvrent-elles le Nasdaq 100 ?

### Takeaway
La seule série historique gratuite et téléchargeable trouvée est le fichier DIX.csv de SqueezeMetrics. Il est quotidien, couvre **le S&P 500 seulement**, va du 2011-05-02 au 2026-11-23, et a 4 colonnes : date, price, dix, gex. Il répond toujours (vérifié le 24/11/2026). **La ligne datée t est publiée après la clôture de t** : fichier modifié à 17:58 heure de New York le 23/11/2026 ; sur les copies d'archive, la ligne du jour est présente entre 18:20 et 19:39, et absente avant l'ouverture. Elle sert à trader la séance t+1, jamais la séance t. Les valeurs ne sont pas révisées depuis au moins novembre 2020. En revanche, la méthode a changé en avril 2020 ; les unités et les hypothèses de la série publique ne sont pas documentées. Je n'ai trouvé aucun historique gratuit pour le NDX ou le QQQ.

### Cited Findings
- **Fichier et contenu** [calcul propre] :
  - Adresse : `https://squeezemetrics.com/monitor/static/DIX.csv`, HTTP 200 sans connexion le 24/11/2026.
  - 3 915 lignes du 2011-05-02 au 2026-11-23 ; colonnes `date,price,dix,gex`.
  - Exemple de dernière ligne : `2026-11-23,7237.17,0.39056858464075306,1619839458.299999`.
  - Un seul trou de plus de 4 jours : du 2012-10-26 au 2012-10-31.
  - [SqueezeMetrics DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Moment de publication** [calcul propre] :
  - En-tête `Last-Modified: Mon, 23 Nov 2026 22:58:35 GMT`, soit 17:58 heure de New York, et le fichier finit sur la ligne 2026-11-23.
  - Copies d'archive : prise le 2020-12-03 à 23:20 UTC, dernière ligne 2020-12-03 ; le 2025-04-29 à 23:17 UTC, dernière ligne 2025-04-29 ; le 2026-09-09 à 23:39 UTC, dernière ligne 2026-09-09.
  - Une copie prise le **lundi 2022-12-05 à 14:19 UTC (9:19 à New York, avant l'ouverture)** finit sur la ligne du **vendredi 2022-12-02**.
  - Conclusion : avant l'ouverture du jour t, la dernière valeur disponible est celle de la séance précédente.
  - [Index Wayback de DIX.csv](https://web.archive.org/cdx/search/cdx?url=squeezemetrics.com/monitor/static/DIX.csv) ; [copie du 05/12/2022](https://web.archive.org/web/20221205141903/https://squeezemetrics.com/monitor/static/DIX.csv) ; [copie du 03/12/2020](https://web.archive.org/web/20201203232000/https://squeezemetrics.com/monitor/static/DIX.csv)
- **Documentation SqueezeMetrics** :
  - « The public DIX and GEX chart is about an S&P 500 aggregate... GEX is an aggregate estimate of option gamma exposure. »
  - « DATE names the market session, not a guarantee that every field was available at that session's close. Check the newest published date before treating a row as current. »
  - Les unités et les options incluses ne sont pas précisées. La doc renvoie à des « dated notes on early GEX assumptions ».
  - [SqueezeMetrics docs](https://squeezemetrics.com/monitor/docs)
- **Définition du DIX** (colonne `dix`, sans rapport direct avec le gamma) : « DIX is the dollar-weighted average of dark-pool short-sale ratios for S&P 500 stocks. A short sale in a dark pool often comes from a dealer filling a customer's buy order, so a higher DIX can be a clue to buying that is otherwise hard to see. It is a proxy for that activity, not a count of customer buys or a promise about the next market move. » — [SqueezeMetrics, page DIX/GEX](https://squeezemetrics.com/monitor/dix)
- **Définition sur la page DIX** : « GEX estimates how much option dealers may need to change their S&P 500 hedges when prices move... It is an estimate of possible pressure on volatility, not a forecast of market direction. The calculation depends on assumptions about who holds the options. » — [SqueezeMetrics, page DIX/GEX](https://squeezemetrics.com/monitor/dix)
- **Pas de révision depuis novembre 2020** [calcul propre] : j'ai comparé trois copies d'archive au fichier du 24/11/2026.
  - Copie du 2020-11-29 : 2 412 lignes communes.
  - Copie du 2022-12-05 : 2 919 lignes communes.
  - Copie du 2025-04-29 : 3 520 lignes communes.
  - Résultat : **0** valeur changée pour gex, dix et price, aucun changement de signe, aucune date supprimée. La plus ancienne copie archivée date du 2020-11-29.
  - [copie du 29/11/2020](https://web.archive.org/web/20201129154647/https://squeezemetrics.com/monitor/static/DIX.csv) ; [copie du 29/04/2025](https://web.archive.org/web/20250429231757/https://squeezemetrics.com/monitor/static/DIX.csv)
- **Changement de méthode en avril 2020** [lu en entier] : la note du 19/04/2020 annonce l'abandon des hypothèses « all calls are sold, all puts are bought » au profit de données de transactions remontant à 2004 (GEX 2.0 / GEX+, avec le vanna) — [note SqueezeMetrics du 19/04/2020](https://notes.squeezemetrics.com/2020-04-19.pdf) ; méthode DDOI décrite dans [The Implied Order Book](https://squeezemetrics.com/monitor/download/pdf/The_Implied_Order_Book.pdf)
- **Part de jours à GEX négatif dans la série publique** [calcul propre] : 8,9 % sur l'ensemble ; médiane 2,59 Md.

  | Année | Jours GEX < 0 | Médiane (Md) | Minimum (Md) |
  |---|---|---|---|
  | 2011 | 17,6 % | 0,77 | −1,19 |
  | 2012 | 5,2 % | 1,84 | −1,22 |
  | 2013 | 0,8 % | 2,07 | −0,28 |
  | 2014 | 2,0 % | 3,00 | −0,49 |
  | 2015 | 9,1 % | 1,69 | −1,27 |
  | 2016 | 8,7 % | 1,87 | −1,82 |
  | 2017 | 0,8 % | 3,14 | −0,15 |
  | 2018 | 15,5 % | 2,47 | −2,57 |
  | 2019 | 7,1 % | 2,67 | −1,23 |
  | 2020 | 12,3 % | 3,49 | −2,96 |
  | 2021 | 6,3 % | 5,92 | −5,63 |
  | 2022 | 41,4 % | 0,48 | −7,50 |
  | 2023 | 9,2 % | 2,59 | −1,63 |
  | 2024 | 0,4 % (1 jour) | 5,15 | −0,04 |
  | 2025 | 3,6 % | 6,01 | −1,94 |
  | 2026 (au 23/11) | 4,9 % | 5,47 | −7,24 |

  [SqueezeMetrics DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Écart avec Baltussen** [lu en entier + calcul propre] : Baltussen compte environ 48 % de jours négatifs de 1996 à 2020 (2 930 sur 6 088), avec l'ancienne méthode. La série publique actuelle n'en a que 0,8 à 17,6 % par an de 2011 à 2020 — [Baltussen et al. 2021](https://academicweb.nd.edu/~zda/intramom.pdf) ; [DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Autres sources** [extrait de recherche, non vérifié] :
  - SpotGamma propose gratuitement un graphique des niveaux de gamma du SPX, du jour seulement.
  - FlashAlpha a une offre gratuite de 5 requêtes par jour, sans SPY ni QQQ ; l'historique SPY/SPX/QQQ/NDX à la minute depuis le 2018-04-16 est payant.
  - Barchart : export CSV du GEX réservé aux abonnés Premier.
  - OptionCharts affiche un GEX du NDX, sans export trouvé.
  - [FlashAlpha, données GEX gratuites](https://flashalpha.com/articles/free-gex-data-gamma-exposure-levels-any-ticker) ; [SpotGamma, niveaux gratuits](https://spotgamma.com/free-gex-levels/) ; [OptionCharts NDX](https://optioncharts.io/options/$NDX/gamma-exposure)

### Inferences
- **Jointure correcte** : pour la séance du jour t, prendre la **dernière ligne de DIX.csv dont la date est strictement antérieure à t**. Le lundi utilise donc la ligne du vendredi ; les jours fériés sont sautés. Joindre sur la même date revient à regarder vers l'avant : la ligne t contient la clôture du S&P 500 de t (colonne `price`) et a été calculée après cette clôture.
- La colonne `price` semble être le niveau du S&P 500 à la clôture de la date (7 237,17 le 2026-11-23). Ce n'est pas documenté.
- La série publique est cohérente avec la méthode DDOI (« very rarely negative ») et pas avec l'ancienne méthode naïve de Baltussen. Les seuils de signe de l'article (NGE < 0) **ne se transposent donc pas** tels quels.
- Avant novembre 2020, et surtout pour 2011-2020, l'historique a probablement été recalculé avec une méthode conçue en 2020, donc avec le recul : c'est un historique reconstruit, pas ce qu'on aurait vu en direct. Il n'est réellement « en direct et figé » que depuis fin 2020 au moins.
- Pour le Nasdaq 100, la seule solution gratuite serait de construire sa propre série à partir de maintenant (photo quotidienne de l'intérêt ouvert NDX ou QQQ). Pour le passé, il faut se contenter du GEX du S&P 500 comme substitut.

### Gaps
- **Unités du gex public non vérifiées.** Le livre blanc parle de dollars ; « The Implied Order Book » parle de $ par point de SPX (jamais sous −200 M$/pt). Or le CSV descend à −7,5 Md en 2022 et à −2,96 Md en mars 2020. Le chiffre GEX+ de 356 M$ « par point » au 17/04/2020 ne correspond pas non plus à la ligne du CSV de ce jour (1,907 Md).
  - Hypothèse plausible mais non confirmée : des $ par mouvement de 1 %, gamma seul.
  - Conséquence : seuls le signe et les rangs (percentiles) sont exploitables sans risque.
- **Contenu exact de la série publique non vérifié** : options SPX seules ou avec SPY, prise en compte ou non du vanna, intérêt ouvert de quel jour. L'heure de publication de l'intérêt ouvert par l'OCC n'a pas été vérifiée. Je ne peux pas dire si la ligne t utilise l'intérêt ouvert de la clôture de t−1 ou de t.
- **Pas de copie d'archive avant le 2020-11-29** : impossible de prouver que les valeurs d'avant 2020 ont été réécrites.
- **Livre blanc DIX « Short is Long » non lu** : l'adresse essayée (`squeezemetrics.com/download/short_is_long.pdf`) a renvoyé 404, alors que la doc donne `/monitor/download/pdf/short_is_long.pdf`. Le DIX n'est pas le sujet de cette note.
- Les offres SpotGamma, FlashAlpha, Barchart et OptionCharts n'ont pas été vérifiées en direct. Les sources institutionnelles payantes (Cboe DataShop, OptionMetrics) n'ont pas été vérifiées non plus.
- Je n'ai trouvé aucun historique gratuit de GEX pour NDX, QQQ ou NQ.

## 4. Quelle règle simple, sans optimisation, la littérature suggère-t-elle ?

### Takeaway
Une seule règle, fixée à l'avance, à tester : **ne prendre la cassure d'ouverture du jour t (deux sens, stop et sortie inchangés) que si le GEX de la dernière séance avant t est sous la médiane des 252 séances précédentes (fenêtre qui s'arrête à t−1).** C'est la version « gamma bas = momentum » des tableaux 7 et 8 de Baltussen. Elle reste utilisable avec la série publique, où le gamma négatif est trop rare (8,9 % des jours, un seul jour en 2024).

### Cited Findings
- Le momentum de fin de journée n'existe que quand NGE t−1 < 0 (β 6,63, t 4,78) et il grandit quand le gamma devient plus négatif (NGE·r_ROD −123,04, t −3,42). C'est une relation **continue**, pas seulement un effet de signe — [Baltussen et al. 2021, tableaux 7 et 8](https://academicweb.nd.edu/~zda/intramom.pdf)
- Un GEX de la veille élevé va avec des journées plus calmes (écart-type à 1 jour de 0,55 % contre 0,85 % entre les deux quartiles du haut) — [SqueezeMetrics, livre blanc GEX](https://squeezemetrics.com/download/white_paper.pdf)
- Gamma net positif = retours vers la moyenne et volatilité plus basse dans l'heure qui suit — [Quantpedia, résumé de Adams et al.](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/)
- **Série publique de 2011 à 2026** [calcul propre] :
  - La part de jours sous la médiane glissante (252 séances passées) varie de 25,6 % (2023) à 80,2 % (2015) selon l'année ; 2022 : 75,3 % ; 2024 : 29,0 %.
  - Comptage direct : sur 2 236 séances du CSV depuis le 2018-01-01, 252 ont un GEX de la veille < 0, dont 104 en 2022 ; 88 avant décembre 2020 et 164 ensuite.
  - [DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Même effet sur une stratégie de momentum SPY, avec un substitut prix** : un RSI(5) de la veille plus bas va avec des gains plus élevés (β −3,25 point de base par point de RSI, p 0,001) — [Zarattini et al. 2024, section 4.5](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

### Inferences
- **Règle G1, à écrire avant le test** :
  1. Pour chaque séance t, g = gex de la dernière ligne datée < t.
  2. m = médiane des 252 lignes précédentes, jusqu'à et y compris cette ligne-là.
  3. Si g < m, le robot trade normalement. Sinon, aucun trade.
  - Aucun paramètre à régler : la médiane et la fenêtre de 252 séances (un an) sont des choix conventionnels, fixés avant le test.
  - Une médiane **glissante** évite deux pièges : la dérive du niveau (médiane annuelle de 0,77 Md en 2011, d'environ 6 Md en 2025) et une médiane calculée sur tout l'échantillon, qui regarderait vers l'avant.
- **Ce qu'il faut regarder** : le gain moyen par trade, le taux de réussite et la part de cassures qui échouent (stop touché), dans les deux groupes (g < m et g ≥ m), **séparément pour les longs et les shorts**, et année par année. Hypothèse de la littérature : continuation plus forte et cassures ratées moins fréquentes quand g < m.
- **Contrôle obligatoire** : refaire le même découpage avec un filtre de volatilité connu la veille (médiane glissante du VIX ou de la volatilité réalisée sur 20 jours). Si la règle GEX ne fait pas mieux que ce filtre, le gamma n'apporte rien de plus qu'un indicateur de prix ou de volatilité. Les filtres RSI H1 et « élan de la première demi-heure » ont déjà échoué (`critique-v10.md`, section 3). Or le seul « effet gamma » publié sur le SPY (Zarattini et al.) passe par un RSI 5 jours. Il faut donc vérifier que G1 ne recopie pas ces filtres déjà rejetés.
- **Lien possible avec le stop (axe 2 de la critique)** : un GEX élevé va avec des journées calmes et des retours vers la moyenne. On peut donc s'attendre à de plus petits ranges d'ouverture et à plus de stops « dans le bruit » ces jours-là. Il serait utile de noter, dans le même test, le taux de stop touché par groupe de GEX, sans en faire un second critère.
- **Vérification descriptive, pas une règle** : refaire le découpage de Baltussen (GEX de la veille < 0 ou ≥ 0) pour voir le signe. Il y a trop peu de jours négatifs hors 2022 pour en faire une règle.
- **Variante pour les shorts, à garder pour plus tard** : n'autoriser les shorts que quand g < m. Les jours à GEX bas suivent des baisses (voir question 5) et le mécanisme du gamma négatif pousse la baisse dans le même sens que les vendeurs. Ce serait une seconde règle : ne la tester que si G1 passe, et sur une autre période.
- **Données qui jugent**, selon la discipline du projet (`recherche/critique-v10.md`, section 5, et `CLAUDE.md`) :
  - Le **S&P 500 Dukascopy 2018-2026** (environ 2 200 séances) est le meilleur juge. Il n'a jamais été chargé, et le GEX de SqueezeMetrics porte justement sur cet indice : pas de décalage entre l'indice et sa mesure.
  - Présenter les résultats **en deux morceaux** : de 2018 à novembre 2020, où l'historique a pu être reconstruit après coup avec la méthode d'avril 2020, puis de décembre 2020 à 2026, où les valeurs sont vérifiées figées. Un effet présent seulement dans le premier morceau serait suspect.
  - Le **Nasdaq 2010 à 18/11/2026 a déjà été vu en entier** : il ne peut servir qu'à décrire, pas à juger ni à régler.
  - Le **Nasdaq après le 19/11/2026 et la démo** servent de dernière vérification. Comme la règle coupe environ la moitié des jours, l'échantillon grossira lentement.
  - Le **Dow 2024-2026** ne convient pas : G1 dépend de l'avantage de la cassure, et la cassure n'y gagne rien.
- Écrire la règle, le critère de réussite et les données qui jugent dans `recherche/notes/idees-strategies.md` et au registre **avant** de regarder. Juger une seule fois.
- **Le critère de réussite n'est pas fixé ici** : gain total à risque égal, ou taux de réussite et pertes moins fréquentes ? C'est à l'utilisateur de choisir (voir `CLAUDE.md`). Il faut le lui demander avant le test.

### Gaps
- Aucune étude publiée n'a testé cette règle, ni aucune règle GEX, sur une cassure d'ouverture. Le gain attendu est inconnu.
- La littérature ne dit pas quel seuil (signe, médiane, quartile) convient à la série SqueezeMetrics actuelle. La médiane est un choix par défaut, pas un résultat.

## 5. Pièges : regard vers l'avant, changement de régime avec les 0DTE, GEX = estimation

### Takeaway
Les cinq pièges principaux : (1) utiliser la ligne du jour même ; (2) appliquer les seuils de Baltussen (ancienne méthode) à la série publique (nouvelle méthode, historique reconstruit) ; (3) confondre l'effet du gamma avec celui du marché récent, car le GEX suit fortement les rendements et la volatilité passés ; (4) le changement de régime des 0DTE depuis 2022, où le momentum sans condition a peut-être disparu et où les teneurs sont souvent longs gamma ; (5) la série est sur le S&P 500 alors que le robot trade le Nasdaq 100, et sa construction repose sur des hypothèses invérifiables sur qui détient les options.

### Cited Findings
- La ligne t de DIX.csv apparaît après la clôture de t (Last-Modified 17:58 heure de New York le 23/11/2026 ; à 9:19 le lundi 05/12/2022, la dernière ligne était celle du vendredi 02/12) — [DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv) ; [copie du 05/12/2022](https://web.archive.org/web/20221205141903/https://squeezemetrics.com/monitor/static/DIX.csv)
- « DATE names the market session, not a guarantee that every field was available at that session's close » — [SqueezeMetrics docs](https://squeezemetrics.com/monitor/docs)
- Baltussen conditionne sur NGE **t−1** — [Baltussen et al. 2021, tableau 7](https://academicweb.nd.edu/~zda/intramom.pdf)
- Changement de méthode en avril 2020 (fin de l'hypothèse « tous les calls vendus, tous les puts achetés », reconstruction depuis 2004) — [note SqueezeMetrics du 19/04/2020](https://notes.squeezemetrics.com/2020-04-19.pdf)
- La mesure de Baltussen ignore les options de gré à gré et suppose que les teneurs sont vendeurs de tous les puts et acheteurs de tous les calls — [Baltussen et al. 2021, note 8](https://academicweb.nd.edu/~zda/intramom.pdf)
- La page GEX elle-même précise : « The calculation depends on assumptions about who holds the options » et « not a forecast of market direction » — [SqueezeMetrics, page DIX/GEX](https://squeezemetrics.com/monitor/dix)
- **Le GEX suit le marché récent** [calcul propre, 2011-2026] :
  - Corrélation de rang entre le GEX du jour t et la volatilité réalisée sur 20 jours : −0,38 (corrélation simple −0,28).
  - Corrélation de rang entre le GEX du jour t et le rendement du S&P 500 sur 5 jours : +0,48.
  - Rendement absolu moyen du lendemain (clôture à clôture) : 1,55 % après un GEX < 0 (349 jours), contre 0,64 % après un GEX ≥ 0 (3 565 jours).
  - [DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Régime 0DTE** :
  - Teneurs nets longs gamma pendant les journées d'échéance, effets qui s'éteignent en environ une heure — [Quantpedia, résumé de Adams et al.](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/)
  - Couverture nette des teneurs d'environ 0,2 % de la liquidité du SPX au mieux, selon le Cboe — [Cboe Insights](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)
  - Momentum de fin de journée sans condition nul de 2022 à 2026 sur le SPX (t +0,6), mais présent les jours de gamma court mesuré à 15:30 — [FirmTape, faible / commercial](https://dev.to/firmtape/intraday-momentum-is-dead-in-the-0dte-era-we-measured-it-on-1085-spx-sessions-43g0)
- **Dérive du niveau** : médiane annuelle du GEX de 0,77 Md (2011) à 6,01 Md (2025) ; 41,4 % de jours négatifs en 2022 contre 0,4 % en 2024 — [DIX.csv](https://squeezemetrics.com/monitor/static/DIX.csv)
- **Le gamma n'est testé que sur le S&P 500** ; le Nasdaq 100 n'est testé que sans condition — [Baltussen et al. 2021](https://academicweb.nd.edu/~zda/intramom.pdf)

### Inferences
- **Piège du regard vers l'avant** : joindre sur la même date gonflerait artificiellement le filtre, car le GEX de t intègre déjà la clôture de t, et un GEX bas va avec les journées de baisse et de forte volatilité. Il faut toujours décaler d'une séance de bourse, et non d'un jour calendaire.
- **Piège de la confusion** : comme le GEX suit les rendements des 5 derniers jours et la volatilité, un filtre GEX risque de refaire un filtre « après une baisse » ou « volatilité haute ». Or l'utilisateur a déjà constaté que ce type d'indicateur de prix ne prédit pas les cassures ratées. D'où le contrôle obligatoire avec un filtre de volatilité (question 4).
- **Piège de la dominance de 2022** : les jours à gamma bas ou négatif sont concentrés en 2022, une année baissière et volatile. Un résultat porté par 2022 pourrait n'être qu'un effet de « marché baissier ». Il faut lire les résultats année par année.
- **Lien avec l'asymétrie long/short** : un GEX bas suit les baisses (corrélation de rang +0,48 avec le rendement sur 5 jours). Si les shorts réussissent mieux quand le GEX est bas, cela peut venir du gamma, ou simplement de la baisse déjà en cours.
  - `critique-v10.md` (section 2.1) montre déjà que les ventes ne font pas mieux quand le prix est sous sa moyenne 50 jours : la tendance de fond seule n'explique pas l'asymétrie.
  - Mais le GEX suit surtout le **court terme** (5 jours) et la volatilité. Le contrôle doit donc porter sur le rendement à 5 jours et sur la volatilité réalisée, pas seulement sur la moyenne 50 jours.
- **Horizon** : les effets publiés concernent la dernière demi-heure (Baltussen) ou l'heure qui suit (Adams). Le robot tient de 9:35 à 15:50. Un effet nul sur la journée entière ne contredirait donc pas la littérature, et un effet positif ne la confirmerait pas directement.
- **S&P 500 pour le Nasdaq 100** : les deux indices sont très corrélés au jour le jour, mais le positionnement des teneurs sur NDX ou QQQ peut différer, par exemple pendant les phases menées par les valeurs technologiques. Le GEX du S&P 500 reste un substitut.

### Gaps
- Je n'ai trouvé aucune mesure publiée de l'écart entre le gamma du S&P 500 et celui du Nasdaq 100 (NDX/QQQ) dans le temps.
- On ne sait pas si l'historique public d'avant 2020 a été recalculé ; la plus ancienne copie d'archive date du 2020-11-29. On ne connaît pas non plus la date exacte de l'intérêt ouvert utilisé pour la ligne t.
- Aucune étude relue par des pairs, trouvée dans cette recherche, ne mesure le momentum intraday conditionné au gamma de la veille après 2022.
