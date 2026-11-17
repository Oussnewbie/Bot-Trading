# Vue d'ensemble : ce qui biaise le jugement, ce que valent les indicateurs, comment optimiser — 17 novembre 2026

Ce n'est pas un conseil en investissement.

## 1. La vue d'ensemble, en une page

Après ~85 000 tests sur BTC, ETH et 54 cryptos, de M5 au journalier, voici ce qui tient.

1. **La crypto est un marché à un seul facteur.** Le BTC, l'ETH et les autres cryptos montent et baissent ensemble.
   Même nos trois stratégies, pourtant différentes, ont des rendements corrélés de 0,67 à 0,77 entre elles. Presque
   tout ce qui gagne gagne pour la même raison : **être dedans quand la tendance de fond est haussière, dehors (ou
   légèrement vendeur) quand elle est baissière.**
2. **On ne prédit pas les retournements, on les constate.** Aucun signal de sommet ou de creux ne fait mieux que le
   hasard, ni en M5 ni en journalier (RAPPORT-3). L'avantage vient de suivre la tendance de l'unité supérieure, pas
   de l'anticiper.
3. **Les supports et résistances ne sont pas des murs mais des zones de stops** : ils cassent plus souvent que le
   hasard (RAPPORT-2). Ils servent à placer un stop, pas à entrer.
4. **La vente existe, mais petite et seulement dans le sens d'un fond baissier** : un quart de la taille d'un achat
   (RAPPORT-3).
5. **Les frais décident de l'unité de temps.** En dessous du H4, ils mangent tout.
6. **La diversification entre cryptos marche, à une condition** : n'acheter les autres cryptos que quand le BTC est
   en tendance haussière. Sans ce filtre, pire baisse de −50 à −89 %.

## 2. Ce qui peut biaiser mon jugement

| Biais | Effet | Ce qui a été fait |
|---|---|---|
| **Tests très stricts** (choix sur 2018-2022, vérification ensuite, frais, comptage des essais) | Je rejette sans doute quelques bonnes idées : avec seulement deux marchés baissiers en 9 ans, un vrai petit avantage peut ne pas « passer » | Assumé : mieux vaut rater une bonne idée que trader une illusion. Les chiffres « avant frais » et « sans dérive » sont donnés pour ne rien cacher |
| **Uniquement des règles codables** | Un trader discrétionnaire combine des choses qu'on ne code pas : contexte, actualité, positionnement, lecture du carnet d'ordres en direct | Impossible à tester sans historique de ses décisions |
| **Peu de cycles** | 2018 et 2022 font l'essentiel de la différence avec l'achat-conservation | Signalé partout ; d'où la démo avant le réel |
| **Choix faits après avoir vu les données** | Croisement EMA50/200 en H4, module de vente de RAPPORT-2, liste des 54 cryptos (choisie en 2026, même si elle inclut des mortes) | Signalé à chaque fois. Le Sharpe « dégonflé » donne 90 % de chances d'un avantage réel pour 15 essais, 11 % si on compte tous les essais de l'étude |
| **Données** | Pas d'historique du carnet d'ordres, des liquidations ni des options | Le volume acheteur/vendeur, le financement, l'open interest, les primes, l'on-chain et le sentiment ont été testés |
| **Frais supposés au marché (0,07-0,15 %)** | Un trader en ordres limites ou avec des remises paie moins | Les résultats en ordres limites (0,02 %) sont donnés : même ainsi, rien ne passe sous le H4 |

**Ta piste de départ était-elle mauvaise ?** En partie, et pas sur les indicateurs.
- **Ce qui était juste** : RSI, MACD, VWAP, Ichimoku, MA200, Fibonacci et order flow ont tous leur place, à condition
  de s'en servir pour **lire la tendance**. C'est le cœur du système.
- **Ce qui ne marche pas** : s'en servir pour **anticiper les retournements**, **trouver des niveaux de rebond** ou
  **trader les petites unités**.

## 3. Les indicateurs marchent-ils pour le BTC ?

**Seuls, à peine. Ensemble, oui.**
- Un RSI, un MACD ou un Ichimoku seul a un t de l'alpha médian entre −0,5 et +1,9 : c'est du bruit ou un avantage
  faible.
- Neuf indicateurs qui votent ensemble pour dire « la tendance de fond est haussière ou baissière » donnent un
  Sharpe de 1,2-1,3, contre 0,6 pour l'achat-conservation. La même conclusion revient dans la littérature (Detzel et
  al. 2021, Hudson-Urquhart 2021, Zarattini 2025).
- L'erreur classique est de les lire comme des signaux de retournement : « RSI à 70 → je vends », « divergence →
  sommet ». Ça, ça ne marche pas.

## 4. Le trader de Twitter qui « a toujours raison »

Je n'ai pas pu lire ses publications : X demande une connexion. Je ne contourne pas ça. Son profil public dit
seulement « PvP enjoyer // NFA » (« NFA » = pas un conseil financier). La recherche web ne trouve rien sur sa méthode.

**Personne n'a toujours raison en trading.** Quand quelqu'un en donne l'impression, c'est presque toujours un mélange
de :
- **Survivant** : des milliers de comptes publient des prévisions. On voit ceux qui ont eu raison récemment ; les
  autres disparaissent ou changent de nom.
- **Sélection** : les bons trades sont montrés, les mauvais sont effacés ou jamais publiés.
- **Prévisions élastiques** : « je regarde 60 k, sinon 70 k » a toujours raison après coup.
- **Pas d'historique vérifié** : sans dates, entrées, stops et tailles, on ne peut pas mesurer.

Il peut être bon : un trader discrétionnaire talentueux existe. Mais on ne peut le savoir qu'en le mesurant. Deux
façons de le faire :
1. **Relever ses appels pendant 2 à 3 mois** : date et heure, sens, entrée, stop, objectif. Sur 50 trades ou plus, je
   calcule son taux de réussite, son R moyen et sa pire série. On saura si c'est de la compétence ou de la chance.
2. **Me décrire sa méthode** : les indicateurs, les niveaux et les unités de temps qu'il regarde, avec des exemples
   de trades. Je la code et je la passe au même test que le reste.

## 5. Les optimisations testées (`optimisation.py`, `alts.py`, `portefeuille.py`)

| Idée | Résultat 2018-2022 / 2023-2026 | Verdict |
|---|---|---|
| Placer le capital qui dort (≈ 35 %) en cash-and-carry | BTC+ETH : Sharpe 1,50 → 1,58 puis 1,17 → 1,11 ; +1 %/an puis −2 %/an | ❌ Presque rien : le financement a baissé depuis 2023 et les allers-retours coûtent |
| Filtre macro : M2 en hausse | BTC 1,32 / 0,96 ; ETH 1,35 / 0,91 (contre 1,22 / 1,13 et 1,24 / 0,80) | 🟡 Aide l'ETH, pas le BTC |
| Filtres macro : bilan de la Fed, dollar, Nasdaq, taux à 10 ans | Dégradent la vérification (BTC 0,30 à 0,76 contre 1,13) | ❌ |
| **Tendance sur chacune des 20 plus grosses cryptos, si le BTC est haussier** | 1,44 / 1,00 ; +41 %/an, pire baisse −32 % (2018-2026) | ✅ |
| **Momentum entre cryptos** (chaque lundi, les 5 meilleures sur 7 jours, si le BTC est haussier) | 1,45 / 0,87 ; les 12 variantes sont positives dans les deux périodes | ✅ |
| Les mêmes **sans** le filtre BTC | 0,44 à 0,88 ; pire baisse −51 à −57 % | ❌ Le filtre BTC fait tout |
| 20 cryptos gardées à poids égaux | 0,49 / 0,46 ; pire baisse −89 % | ❌ |

**Le portefeuille d'ensemble** (2018-2026, frais compris) :

| | Sharpe (R / V / total) | Gain par an | Pire baisse |
|---|---|---|---|
| BTC acheté et gardé | 0,43 / 0,99 / 0,60 | +19 % | −81 % |
| Système BTC + ETH seul (RAPPORT-3) | 1,50 / 1,17 / 1,36 | +33 % | −21 % |
| Système 50 % + tendance sur 20 cryptos 50 % | 1,60 / 1,18 / 1,42 | **+38 %** | −24 % |
| **Système 50 % + tendance 25 % + momentum 25 %** | **1,64 / 1,17 / 1,44** | +34 % | −24 % |
| Un tiers chacun | 1,62 / 1,12 / 1,41 | +34 % | −26 % |

- **Gain réel mais modeste** : Sharpe 1,36 → 1,42-1,44. Les trois poches sont corrélées (0,67-0,77) parce qu'elles
  dépendent toutes du régime du BTC.
- **Ce que la diversification apporte surtout** : moins de dépendance au BTC seul, et une poche (les autres
  cryptos) qui capte les phases où elles montent plus vite que le BTC.
- **Réserve** : les 54 cryptos ont été choisies aujourd'hui. Elles incluent des mortes (LUNA, FTT, WAVES, EOS, XMR
  radiées), mais pas les centaines de petites cryptos disparues. Le résultat des autres cryptos est donc un peu
  flatteur.

## 6. Ce qui pourrait encore changer la donne (non fait)

- **Exécution en ordres limites** sur le BTC et l'ETH : moins de frais, un peu plus de rendement, sans changer la
  stratégie.
- **Levier modéré sur le portefeuille** : avec un Sharpe de 1,4 et une pire baisse de −24 %, un levier de 1,5 donnerait
  environ +50 % par an et −35 % de pire baisse. Le risque de queue (krach éclair, exchange) augmente plus vite que le
  rendement. À ne faire qu'après la démo.
- **Protection par options** (achat de puts sur Deribit pendant les achats) : réduirait les krachs éclairs, mais
  coûte la prime de volatilité (≈ 8 points en moyenne).
- **Données de carnet d'ordres et de liquidations** (payantes) : ce que les études publiées en tirent porte surtout
  sur le très court terme, là où les frais tuent déjà tout.

## 7. La stratégie finale, mise à jour

1. **Poche principale (50 %)** — système multi-unités BTC + ETH (RAPPORT-3) : journalier pour le sens, H4 pour
   l'entrée, achat en taille pleine, vente à quart de taille.
2. **Poche « cryptos » (50 %)**, seulement quand le score journalier du BTC est ≥ 0,25 :
   - **25 %** : tendance sur chacune des 20 plus grosses cryptos (prix > MA200, MACD > signal, RSI > 50), taille dosée
     par la volatilité ;
   - **25 %** : momentum, les 5 meilleures cryptos sur 7 jours, rebalancé chaque lundi.
3. Sinon, liquidités (stablecoins).

2018-2026 : Sharpe 1,44, +34 % par an, pire baisse −24 %. Avant tout argent réel : démo de plusieurs mois.

## Refaire

```bash
bash crypto/03_telecharger_alts.sh     # bougies journalières de 54 cryptos (dont mortes)
python crypto/optimisation.py          # capital qui dort en cash-and-carry, filtres macro (FRED)
python crypto/alts.py                  # tendance et momentum sur 54 cryptos
python crypto/portefeuille.py          # portefeuille d'ensemble
```

`bash crypto/04_telecharger_macro.sh` télécharge les séries macro (FRED, sans clé) avant `optimisation.py`.
