# Dossier `revue/` : scripts de la revue indépendante

Le rapport est dans [RAPPORT.md](RAPPORT.md). Les sorties brutes des scripts sont dans `resultats/`.

Rien ici ne modifie les bots. Les données et les caches vont dans `donnees/` (ignoré par git).

## Nasdaq (ORB v6)

1. Extraire les données (seule lecture de l'historique git, autorisée par la consigne) :

   ```bash
   git archive afb79de donnees/nas100 | tar -x
   ```

2. Lancer les scripts, depuis la racine du dépôt :

   | Script | Rôle |
   |---|---|
   | `nasdaq_donnees.py` | lit les zips Dukascopy M1 bid/ask et les passe en heure de New York (cache `donnees/revue/`) |
   | `orb.py` | le simulateur, écrit à partir des seules règles du README (modèle « EA » : bid/ask, minute par minute) |
   | `run_base.py` | le backtest de base, sans glissement ajouté |
   | `analyse1.py` | répartition des R, années, composants (filtres, stop à l'entrée, pyramide) |
   | `analyse2.py` | coûts, réglages voisins, années, fenêtres glissantes |
   | `analyse3.py` | rééchantillonnage, retrait des meilleurs trades, marge, limites d'un compte financé |
   | `croise/orb_croise.py` | seconde implémentation, écrite à part par un autre agent à partir du README : mêmes 1 391 trades au centime de R près |

**Avant 2018** : `datafeed.dukascopy.com` a refusé les téléchargements depuis l'environnement de la revue
(« 429 Too Many Requests »). Pour faire le test toi-même :
- récupère les M1 bid et ask de USATECHIDXUSD 2013-2017, au même format (`timestamp,open,high,low,close,volume`, ms UTC) ;
- range-les en `donnees/nas100/usatechidxusd-m1-AAAA.zip`, avec dans chaque zip `...-bid-AAAA.csv` et `...-ask-AAAA.csv` ;
- efface `donnees/revue/`, puis relance `run_base.py` et `analyse2.py`.

Pour isoler la période, appelle `orb.backtest(..., debut=..., fin=...)`.

## BTC

| Script | Rôle |
|---|---|
| `btc_telecharger.py` | télécharge Bitstamp (1d, 4h), Coin Metrics (flux des plateformes), Binance Vision (1h BTCUSDT et ETHBTC, financement) dans `donnees/crypto/` |
| `btc_backtest.py` | ma comptabilité de compte : décisions prises par `bitcoin/btc.py` (le code du bot), rendements recalculés ici (bande de 5 %, frais, financement aux heures de paiement, coupe-circuit, levier, stop et liquidation) |
| `btc_analyse.py` | le bot face à achat-et-garde, MA200, et aux variantes de coûts |
| `btc_analyse2.py` | grille de réglages du code, retrait de chaque vote, prix Binance contre Bitstamp, dates de départ, rééchantillonnage |
| `btc_levier.py` | levier ×1 à ×10, avec le coupe-circuit du bot |
