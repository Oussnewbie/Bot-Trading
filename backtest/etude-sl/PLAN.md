# Étude des stops de l'ORB v5 — plan de l'étape 1 (données et reproduction)

> **État au 14 novembre 2026 : étape 1 terminée.** Ce plan est celui qui a été suivi. Deux décisions ont changé depuis :
> l'étude et les données vont du 2018-01-01 au 2026-11-13 (le M1 est dans `donnees/`, dans git), et le dépôt a été nettoyé,
> tout est sur `main`. Les scripts `03_comparer_m5.py` et `04_reproduction.py` cités plus bas ont été remplacés par
> `03_reference.py` ; leurs rapports sont dans `sorties/historique-2011-2026/`. La demande complète est dans `DEMANDE.md`,
> le résumé dans `ETAPE1.md`. Le plan de l'étape 2 sera écrit après le « go ».

**But :** disposer d'un historique M1 bid + ask contrôlé (Nasdaq CFD et or), et prouver que la v5 du dépôt redonne les
chiffres du README avant toute analyse des stops.

**Architecture :** un script par tâche, numéroté, dans `backtest/etude-sl/`. Chaque script lit les fichiers du script
précédent et écrit un rapport dans `sorties/`. Le simulateur `v5_lab.py` est importé tel quel, jamais copié ni modifié.

**Outils :** `npx dukascopy-node@1.51.1`, Python du dépôt (`.venv`, pandas, numpy, pytest). Aucune dépendance ajoutée.

**Portée :** l'étape 1 seulement. Les étapes 2 et 3 seront planifiées après le « go », parce qu'elles dépendent de ce que
l'étape 1 trouve et que le texte de la demande est coupé au milieu de l'étape 3.

## Règles (copiées de la demande)

- Aucun fichier existant n'est modifié. Tout est dans `backtest/etude-sl/`, branche `etude-sl`, un commit par étape.
- Les données brutes ne vont jamais dans git (`backtest/etude-sl/.gitignore`).
- Achat : entrée sur l'ask, sortie sur le bid. Vente : l'inverse. Spread réel.
- Heures de New York, heure d'été américaine gérée.
- Résultats en R : trades, R par trade, total, pire baisse, pire série de pertes.
- Arrêt à la fin de chaque étape, résumé court, attente du « go ».

## Décisions prises pour l'étape 1

| Sujet | Décision | Raison |
|---|---|---|
| Branche | `etude-sl` créée depuis `main` local | `main` contient le correctif de l'audit (1 925 trades) ; `recherche/stops` n'est pas fusionnée |
| Bougies plates | non téléchargées | le M5 du dépôt n'en a pas ; une minute sans cotation ne peut ni toucher un stop ni l'éviter |
| H4 et D1 | alignées sur 17:00 New York | c'est minuit du serveur MT5 réglé dans l'EA (`InpSrvGMT = 2`, heure d'été américaine) |
| M3 à H1 | alignées sur l'heure ronde | comme Dukascopy et MT5 |
| Stockage | un fichier `.npz` par instrument et par horizon | numpy suffit, pas de nouvelle dépendance |
| Période finale | verrou dans `commun.charger` : 2023 → 2026 n'est rendue que pour la qualité des données, la v5 non modifiée, ou avec `ETUDE_SL_FINALE=ouverte` | règle anti-bruit : la période finale n'est testée qu'une fois |
| Calendrier US | jours fériés et demi-séances calculés par règles, puis recoupés avec les séances courtes vues dans les données | pas de source officielle dans le dépôt |

## Fichiers

| Fichier | Rôle |
|---|---|
| `00_telecharger.sh` | M1 bid et ask, un fichier par année, 2010 → 2026-11-13, reprise possible, échecs listés |
| `commun.py` | chemins, heure de New York, `agreger`, `charger` (avec le verrou), les cinq chiffres en R |
| `01_construire.py` | assemble bid + ask, reconstruit M3 → D1, écrit `sorties/etape1_inventaire.md` |
| `02_qualite.py` | jours manquants, trous, spreads, jours fériés, demi-séances → `sorties/etape1_qualite.md` |
| `03_comparer_m5.py` | M5 reconstruit contre `donnees/`, bougie par bougie → `sorties/etape1_m5.md` |
| `04_reproduction.py` | la v5 sur les données du dépôt, puis sur le M5 reconstruit → `sorties/etape1_reproduction.md` |
| `test_etude.py` | tests de `commun.py` |

## Tâches

### 1. Téléchargement
- [x] Essai sur un mois (Nasdaq, janvier 2015) : le M5 reconstruit est identique au M5 du dépôt (5 554 bougies, 0 écart).
- [x] `./00_telecharger.sh` : attendu « Terminé sans échec. ». Les années vides sont notées `.vide`.
- [x] Vraie date de départ de chaque instrument lue dans les fichiers, pas dans la documentation.

### 2. Reconstruction
- [x] `python -m pytest test_etude.py` : 8 tests (M3, M5, ancrage H4/D1 hiver et été, verrou, périodes, chiffres en R).
- [x] `python 01_construire.py` : 8 horizons par instrument, inventaire par année.

### 3. Qualité
- [x] `python 02_qualite.py`. Pour chaque instrument : jours ouvrés sans cotation, trous dans la séance, fenêtre
      9:00-9:45 incomplète, spreads (médiane, extrêmes, ask sous le bid), sauts de prix, jours fériés et demi-séances.
- [x] Le Nasdaq d'avant 2013 est contrôlé à part : Dukascopy n'a de ticks qu'à partir de 2013.

### 4. Comparaison du M5
- [x] `python 03_comparer_m5.py` : nombre de bougies présentes d'un seul côté et de bougies dont un prix diffère,
      bid et ask, sur 2015-01-01 → 2026-10-30. Attendu : 0 et 0. Sinon, liste et explication.

### 5. Reproduction de la v5
- [x] `python 04_reproduction.py`, trois mesures :
  1. `v5_lab` sur les données du dépôt : attendu 1 925 trades, +372R, pire baisse -74R (README de `main`).
  2. Le même sans les jours de janvier 2015 que l'ancien code écartait : attendu 1 915 trades, +373R, -69R
     (chiffres de l'en-tête de l'EA et de la demande). Cela explique l'écart entre les deux jeux de chiffres.
  3. `v5_lab.prep(data=...)` sur le M5 reconstruit, coupé aux mêmes dates : mêmes trades, un par un.
- [x] Si une de ces mesures ne colle pas : arrêt, explication de l'écart, pas d'étape 2.

### 6. Fin d'étape
- [x] Commit sur `etude-sl` (scripts et rapports, pas de données), résumé court, attente du « go ».

## Points de vigilance

- Les heures des fichiers sont en UTC, début de bougie. Une erreur d'une heure à un changement d'heure déplacerait la
  bougie de 9:30 : le test H4/D1 et la comparaison du M5 le détecteraient.
- Un téléchargement incomplet ressemble à un marché fermé. Le contrôle qualité liste donc tous les jours ouvrés sans
  cotation qui ne sont pas des jours fériés.
- Le volume Dukascopy est un volume coté, pas un nombre de ticks. Le « volume en ticks de la bougie de 9:30 » de
  l'étape 2 demandera un téléchargement de ticks à part.
- La période finale 2023-2026 n'est pas vierge : le README et `research/RAPPORT.md` (branche `recherche/stops`) y ont
  déjà mesuré la v5 et plusieurs règles de stop. À dire dans le résumé de l'étape 1.
- Lancer `orb_v5.py` réécrit `v5_trades.pkl` et peut refaire le cache : `04_reproduction.py` importe donc `v5_lab` et
  redirige `CACHE_DIR` vers un dossier temporaire, comme `tests/conftest.py`.
