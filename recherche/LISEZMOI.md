# Recherche — d'où vient la Strategy V10

Ce dossier garde la partie utile de la recherche menée sur la plateforme Claude du 20 au 21 novembre 2026 : 4 sessions, environ
2 000 essais. Ces travaux ont mené de l'ORB v6 à la V10. Commence par **`rapport-session4.md`**.

| Fichier | Contenu |
|---|---|
| `critique-v10.md` | **La critique de la V10 (24/11/2026)** : ce qu'elle lit du marché, ce que disent ses trades (ventes plus faibles, stops des jours à petit range), ce qui a déjà été essayé et 5 axes d'amélioration. Chiffres refaits par `scripts/critique_v10.py`. |
| `rapport-session4.md` | Le rapport de la V10 : cause des stops, profil Confort, test sur 6 autres marchés, interrupteur. C'était `rapport.md` dans l'archive. |
| `rapport-session3.md` | L'examen sur 2010-2017 (données jamais vues à l'époque), les continuations D et la V9, le contrôle sur le S&P 500 |
| `rapport-session2.md` | La V7 (mémoire, FOMC, fériés) et la V8 (repli VWAP B, entrée de 10:00 C) |
| `notice-v7-a-v10.md` | La notice d'installation des V7 à V10, telle que livrée (`strategies/LISEZMOI.md` dans l'archive) |
| `notes/nasdaq-progress.md` | **Le journal complet** : protocoles écrits avant chaque test, résultats, coffres-forts ouverts, prochaines actions |
| `notes/idees-strategies.md` | Les idées et critères écrits **avant** les tests |
| `notes/recherche-web.md` | Les sources consultées |
| `resultats/trades_V10_confort_2018_2026_1pt.csv` | Les trades de la V10 simulés sur 2018-2026 (spread réel + 1 point) : la référence pour le testeur MT5 et la démo |
| `resultats/trades_V10_confort_2010_2017_couts_aujourdhui.csv` | Les mêmes sur 2010-2017 |
| `resultats/80_confort_final.md`, `83_surveillance.md` | Les chiffres du profil Confort et les seuils de l'interrupteur |
| `resultats/62_sp500.md` | Le contrôle de la V9 sur le S&P 500 (HistData, 2015-2025) |
| `resultats/75_multi_marches_principal_2023-12-31.md`, `76_confirmation_dow.md` | Le test écrit à l'avance sur 6 autres marchés, dont le Dow, et l'hypothèse « le Dow confirme le Nasdaq » |
| `resultats/registre_*` | Le comptage des essais |
| `resultats/v10_confort_contre_v9.png` | La figure du rapport |

**Le simulateur de la V10** (`simulateur/`, depuis le 24/11/2026) : les modules de l'archive (`moteur.py`, `commun.py`, `v9lib.py`,
`v10lib.py`), adaptés seulement pour leurs chemins. `simulateur/reproduire_v10.py` reconstruit les données à partir des CSV du Bureau
et retrouve les 3 612 trades de référence à l'identique (+477 R). Mode d'emploi : `simulateur/LISEZMOI.md`.

**Ce qui n'est pas ici.** Le reste des résultats, les autres scripts (téléchargement Dukascopy, préparation des autres marchés,
HistData 2010-2017…) et les versions V7 à V9 sont dans l'archive `Strategy v10.zip`, sur le Bureau. Les rapports citent parfois ces
fichiers : ils sont là-bas.

**Règle à garder en tête.** Tout l'historique du Nasdaq de 2010 à 2026 a déjà été vu. Un nouveau réglage trouvé dessus serait
de l'ajustement sur le passé. Le détail est dans `../CLAUDE.md`.
