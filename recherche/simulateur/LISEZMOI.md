# Simulateur de la Strategy V10

Le simulateur à la minute de la recherche (archive `Strategy v10.zip`, dossier `scripts/`), repris pour tourner dans le dépôt.
Il rejoue la V10, profil Confort, sur les bougies M1 Dukascopy du Nasdaq (bid et ask) et retrouve exactement les trades de
référence. C'est la base pour tester de nouvelles idées, par exemple sur le S&P 500.

## Lancer

Depuis la racine du dépôt :

```
.venv/bin/pip install -r recherche/simulateur/requirements.txt     # une seule fois
.venv/bin/python recherche/simulateur/reproduire_v10.py             # reproduction et comparaison
.venv/bin/python -m pytest recherche/simulateur -q -p no:cacheprovider
```

`reproduire_v10.py` fabrique `donnees/nasdaq_m1.parquet` s'il manque, rejoue la V10 Confort 2018-2026 à 1 point, écrit les
trades dans `donnees/trades_V10_confort_2018_2026_1pt.csv` et les compare un par un à
`recherche/resultats/trades_V10_confort_2018_2026_1pt.csv`. Il rend le code 0 si tout concorde, 1 sinon. Il tourne en environ
7 s la première fois, puis en 2 s.

Les dossiers se règlent dans `sim_chemins.py`, ou par deux variables d'environnement :
- `BOT_TRADING_BRUT` : les CSV bruts, lus sans être modifiés. Par défaut `~/Desktop/Nasdaq 8 ans`.
- `BOT_TRADING_DONNEES` : ce qui est fabriqué. Par défaut `donnees/`, que git ignore.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `moteur.py` | Moteur à la minute : `sim_trade`, calendrier des fériés, RSI, chargement (`Donnees`). Repris de l'archive. |
| `v9lib.py` | `Jeu` (données, coûts, VWAP), cassure `orb_v6`, `sim_gen`, repli VWAP, mémoire v7, V8, jambes. Repris de l'archive. |
| `v10lib.py` | `strategie` : A, B, D1-D3 avec stop élargi, plus `bilan`. Repris de l'archive. |
| `commun.py` | Dates FOMC, périodes, registre des essais. Le registre s'écrit dans `donnees/`, jamais dans `recherche/resultats/`. |
| `sim_chemins.py` | Le seul réglage des dossiers. |
| `sim_donnees.py` | Les CSV Dukascopy bid et ask deviennent le parquet du moteur (étapes de `01_charger_donnees.py` et `74_marches.py`). |
| `sim_jit.py` | Le `njit` de numba, ou rien si numba manque. Les résultats sont les mêmes. |
| `reproduire_v10.py`, `test_simulateur.py` | La reproduction, et les tests : journées synthétiques calculées à la main, début 2018 et fin 2026 réels. |

## Ce qui est reproduit (24/11/2026)

- **Données** : 3 002 322 minutes communes bid et ask, comme dans l'archive.
- **Contrôles de l'archive** : v6 +475,96 R, v7 +591,33 R, V8 +986,17 R.
- **V10 Confort 2018-2026, à 1 point** :
  - 3 612 trades sur 3 612, aucun manquant, aucun en trop ;
  - mêmes sens, mêmes sorties, mêmes pyramides ;
  - total +477,17 R, comme la référence ;
  - le fichier écrit est identique, octet pour octet, à celui de `recherche/resultats/`.

**Changements par rapport à l'archive.** Seulement les imports et les chemins. On peut le vérifier avec `diff` contre
`~/Desktop/sortie 3/scripts/`. Deux ajouts :
- `Donnees` et `Jeu` acceptent aussi un tableau déjà chargé, ce qui sert aux tests ;
- la création du dossier du registre se fait à l'écriture, et non plus à l'import.

Aucune règle de simulation n'a été modifiée.

## Différences connues et limites

- **Ce simulateur reproduit la recherche, pas l'EA d'aujourd'hui.** Les correctifs d'exécution du 24/11/2026 ne sont pas
  dedans : heure du serveur, entrée au marché bornée à 1,25 R, plancher de la pyramide. Le testeur MT5 peut donc avoir
  quelques trades de moins.
- **Hypothèses du moteur** :
  - bougies M1, pas de ticks ;
  - quand l'ordre des prix dans une minute est inconnu, l'entrée suit le chemin probable de la bougie et le stop passe
    avant l'objectif (pire cas) ;
  - le glissement est fixe, 1 point par exécution.
- **2010-2017 (HistData) et les autres marchés ne sont pas repris.** `preparer_hd` attend un `donnees/hd_NSXUSD.parquet`
  qui n'existe pas ici. Pour un autre marché, `sim_donnees.fusionner_bid_ask` accepte n'importe quelle paire de CSV
  Dukascopy bid et ask, avec son fuseau et son heure d'ouverture.
- **Avant le S&P 500**, deux réglages sont en points et calibrés pour le Nasdaq : la marge de 1 point du stop de B (dans
  `repli_vwap`) et le glissement de 1 point. Un point y pèse bien plus lourd par rapport au range.
- **Rappel** : tout l'historique du Nasdaq a déjà été vu. Ce simulateur sert à vérifier et à tester ailleurs, pas à régler
  la V10 sur le passé du Nasdaq.
