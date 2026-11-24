# Registre des essais de la session 4 (21 novembre 2026)

Suite de registre_session3.md (environ 1 770 essais à la fin de la session 3).

| Famille | Script | Cellules testées | Écrit à l'avance ? | Verdict |
|---|---|---|---|---|
| Autopsie des stops (description, pas une stratégie) | 70 | 0 | — | 1 stop sur 3 est suivi de +2R dans le bon sens : stop trop court |
| Remèdes de gestion (objectifs, moitié à +1R, stop à l'entrée, clôture M5, sorties horaires, sans pyramide) | 71 | 14 remèdes x 3 groupes d'entrées = 42 | non (exploration sur Nasdaq déjà vu) | tous font baisser le total |
| Largeur du stop k = 1 à 8 | 72 | 9 largeurs x 3 gestions x 2 groupes = 54 | non | plateau k = 2,5 à 4 |
| Règle de mémoire avec stop large, rejoué comme le robot | 73 | 13 | non | les variantes se valent |
| Gabarit transposé aux 6 autres marchés, séances principales | 75 | 36 | **oui** | aucun marché confirmé |
| Idem, séances secondaires (pour information) | 75 | 42 | **oui** | DAX à 9:30 New York seul positif, non significatif |
| Le Dow confirme le Nasdaq | 76 | 3 (1 jugée) | **oui** | aucun effet |
| Tournoi S1 à S5 sur bougies jour et H1, 7 marchés | 78 | 35 | **oui** | aucun candidat |
| S6 cassure du range asiatique à Londres | 79 | 9 | **oui** | négatif ou nul |
| Profils finaux Confort (A seule, A + B + D, avec objectif) | 80 | 4 | non | Confort retenu comme profil par défaut de la V10 |

Total de la session 4 : environ 240 cellules, dont 125 écrites à l'avance et jugées sur des marchés jamais regardés auparavant.
Total depuis le début : environ 2 000.

Ce que ce comptage implique :
- Le profil Confort (largeur 3) a été choisi parmi 54 + 13 variantes regardées sur des données du Nasdaq déjà vues. Son résultat est donc
  flatteur par construction. Ce qui le soutient : un plateau large (2,5 à 4), présent sur les deux périodes et aux deux niveaux de coût,
  et une explication simple (le stop d'un range de 5 minutes est trop court). Ce qui lui manque : une preuve sur des données vierges.
  Le test sur les 6 autres marchés devait la fournir : il a échoué (l'avantage de départ n'y existe pas).
- Sur les autres marchés, 125 cellules et aucun résultat significatif : avec ce nombre d'essais, le hasard seul aurait pu en laisser
  passer 2 ou 3 à t >= 2. Le fait qu'aucune ne passe est un résultat net.
- Coffre 3 (2024-2026 des 6 autres marchés) : jamais ouvert.
