# Historique complet 2011 → 2026 : pourquoi le dépôt commence en 2018

Rapports de l'étape 1 faits le 14 novembre 2026 sur tout ce que Dukascopy fournit (Nasdaq CFD depuis 2011, or depuis
2010) et sur l'ancien fichier M5 2015-2026 du dépôt, avant que les données soient réduites à 2018-01-01 → 2026-11-13.
Ils ne sont plus refaits par les scripts actuels : les scripts et les données qui les ont produits sont dans
l'historique git (commit `25aa321`), et l'historique se retélécharge avec `DEBUT=2010 ../../00_telecharger.sh`.

| Rapport | Ce qu'il prouve |
|---|---|
| `etape1_inventaire.md` | les vraies dates de départ : Nasdaq 2011-09-19, or 2010-01-01 |
| `etape1_qualite.md` | Nasdaq inutilisable avant le 2013-05-22 (spread nul, puis trou), moyen jusqu'en mai 2014, sans cotation de nuit de 2015 à avril 2018 |
| `etape1_m5.md` | le M5 reconstruit depuis le M1 est identique à l'ancien fichier M5 : 733 078 bougies bid et ask, 0 écart |
| `etape1_reproduction.md` | la v5 redonne le README d'alors (1 925 trades, +372R, -74R) et l'ancien chiffre (1 915 trades, +373R) ; résultats de 2013-2017 |
