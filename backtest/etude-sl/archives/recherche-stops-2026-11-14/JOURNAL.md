# Journal de la recherche sur les stops

Branche `recherche/stops`. Rien de ce dossier ne va sur `main` sans accord.

## Pour reprendre si la session est coupée

1. `python -m venv .venv && .venv/bin/pip install -r requirements.txt`, puis dézipper `donnees/NAS100-M5-bid-ask-2015-2026.zip` dans `donnees/`.
2. Depuis `research/` : `../.venv/bin/python -m pytest tests_moteur.py` (le moteur doit rendre les mêmes trades que `v5_lab.py`).
3. Relancer les scripts dans l'ordre : `00_qualite_donnees.py`, `01_reference.py`, `02_diagnostic_stops.py`, `03_variantes.py`,
   `04_combinaisons.py`, `05_validation.py`. Chacun réécrit ses lignes dans `resultats.csv` et son fichier dans `sorties/`.
4. `06_verification_finale.py` ouvre la période de vérification. **Il ne doit tourner qu'une fois, sur les finalistes de
   `finalistes.py`.** S'il a déjà tourné (voir plus bas), ne plus toucher aux finalistes.

## Cadre

- Dépôt : une seule stratégie, l'ORB v5 sur NAS100. Pas d'or, pas de M1, pas de calendrier économique.
- Découpage : mise au point = 2015-01-01 → 2023-04-12 (70 % du calendrier) ; vérification = 2023-04-13 → 2026-10-30.
- Le moteur (`moteur.py`) ne charge que la mise au point tant que la variable d'environnement `RECHERCHE_VERIFICATION`
  ne vaut pas `ouverte`.
- La période de vérification n'est PAS vierge : le README du dépôt et la branche `claude/compassionate-cannon-ydoll7`
  (33 règles de stop) ont déjà mesuré la v5 sur tout 2015-2026. Ces chiffres ont été lus au début de l'audit.
- Coûts : spread réel des données ; glissement d'un demi-spread par exécution au marché (référence), avec contrôle à
  0,1 point (code actuel) et à un spread entier (sévère). Commission 0, swap 0 (aucune position ne passe la nuit).
- R = points gagnés / distance entre le niveau de l'ordre et le stop (taille calculée avant l'exécution, comme l'EA).

## Ce qui a été fait, dans l'ordre

- 2026-11-14 18:38 — 00_qualite_donnees.py : qualité des données (toute la période, sans jouer de trade).
- 2026-11-14 18:29 — 01_reference.py : références « code actuel » et « doc stricte » sur la mise au point, 7 hypothèses de coûts. Référence retenue : doc stricte + glissement d'un demi-spread.
- 2026-11-14 18:30 — 02_diagnostic_stops.py : 837 stops pleins de la référence diagnostiqués (mise au point). 9 définitions de la mèche testées ; retenue : dépassement ≤ 0,5R puis +1R. Détail par trade dans sorties/02_diagnostic_stops.csv.
- 2026-11-14 18:34 — 03_variantes.py : 319 variantes seules jouées sur la mise au point (coûts réalistes), familles A à F. Résultats dans resultats.csv, R par jour dans sorties/03_par_jour.npz.
- 2026-11-14 18:35 — 04_combinaisons.py : 147 combinaisons (par 2 et par 3) de 10 briques, mise au point, coûts réalistes.
- 2026-11-14 18:36 — 05_validation.py : 466 variantes ; meilleur t 3.47 (V299), probabilité par hasard 33 % (bootstrap par blocs, 3000 tirages). Test glissant, plateaux, coûts et Monte Carlo dans sorties/05_validation.md.
- 2026-11-14 18:38 — Finalistes figés dans `finalistes.py` (F1 à F5, plus F1b à risque égal), choisis sur la mise au point seulement. Enregistrés dans git (commit `9de6559`, 18:38:29) AVANT l'ouverture de la vérification (18:39).
- 2026-11-14 18:39 — OUVERTURE DE LA PÉRIODE DE VÉRIFICATION par 06_verification_finale.py, sur REF, F1 à F5 et F1b uniquement.
- 2026-11-14 18:39 — 06_verification_finale.py terminé : résultats dans sorties/06_verification.md et resultats.csv (famille « finaliste »). La vérification a été lue UNE fois. Ne plus modifier les finalistes.
- 2026-11-14 18:40 — 07_bougie_entree.py : décomposition du gain de F1/F1b/F5 selon que la v5 est stoppée dans la bougie d'entrée (ordre inconnu en M5) ou plus tard. Mise au point seulement ; la même décomposition sur la vérification n'a PAS été faite (ce serait une seconde lecture).
- 2026-11-14, après 07_bougie_entree.py — Une seconde lecture de la vérification (pour décomposer le gain de F1 par cas) a été tentée puis abandonnée : elle aurait enfreint la règle « une seule fois ». Aucun chiffre n'en est sorti.
- 2026-11-14 18:43 — RAPPORT.md écrit. Fin de la recherche : aucun changement n a été porté dans le bot.
