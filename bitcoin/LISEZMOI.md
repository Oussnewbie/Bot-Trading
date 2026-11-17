# Le bot BTC

Il exécute la stratégie de `recherches/crypto/RAPPORT-BTC.md` sur Binance, sans intervention, et prévient sur Telegram. C'est un
**programme à part** de l'EA MetaTrader : il se pilote depuis **Étrave, espace « ₿ Bitcoin »** (démarrer, arrêter,
pause, tout fermer, levier, clé API), ou à la main en ligne de commande.

Ce n'est pas un conseil en investissement. Commence en mode **papier**, puis **testnet**, et passe en **réel** avec un
petit capital seulement après plusieurs semaines conformes au test.

## Ce qu'il fait

**Toutes les 4 heures**, 90 secondes après la clôture d'une bougie (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC) :

1. **Données** (sans clé) :
   - bougies Binance BTCUSDT (1 000 jours, 1 500 bougies 4h) avec le volume acheteur agressif ;
   - ETH/BTC ;
   - flux on-chain de Coin Metrics.

   La bougie en cours est retirée : seules les bougies **clôturées** comptent.
2. **Contrôles** : pas de décision si les données sont en retard, trouées, trop courtes, ou s'il manque plus de 2
   votes. Le bot envoie alors une alerte et ne passe aucun ordre.
3. **Décision** : exactement le système testé. Le bot appelle le même code que le backtest (`btc.py`) ; un test vérifie
   que ses décisions sont identiques au backtest, à 10⁻¹² près.
   - 9 votes journaliers → score.
   - **Achat** si score ≥ +0,25 et tendance 4h haussière (EMA50 > EMA200, prix > EMA200).
   - **Vente** si score ≤ −0,25 et tendance 4h baissière.
   - Sinon **rien**.
   - **Taille** = min(1 ; volatilité cible ÷ volatilité du BTC sur 30 jours). La vente est à un quart de cette taille.
4. **Compte** : capital total = USDT au comptant + BTC au comptant + portefeuille futures (gains latents compris).
5. **Coupe-circuit** : si le capital tombe à plus de 40 % sous son plus haut, le bot ferme tout et s'arrête. La pire
   baisse du test est de −25 %, et −48 % au pire dans le rééchantillonnage.
6. **Ordres**, dans cet ordre :
   - d'abord réduire ce qui doit baisser ;
   - puis déplacer la marge ;
   - puis ouvrir ou augmenter.

   Un ajustement de moins de 5 % du capital est ignoré pour ne pas payer de frais pour rien. Fermer, ouvrir ou changer
   de sens se fait toujours.
7. **Traces** :
   - `etat/journal.csv` : une ligne par cycle (prix, score, cible, capital, exposition, ordres) ;
   - `etat/bot.log` : le journal détaillé ;
   - `etat/etat.json` : la dernière bougie traitée (un redémarrage ne rejoue rien), le plus haut du capital, le compte
     papier.
8. **Telegram** : un message à chaque ordre, changement de sens, alerte ou erreur.

## Le montage chez Binance (choisi par le test)

**Levier ×1 (montage « comptant », recommandé)** :

| Position | Où | Pourquoi |
|---|---|---|
| **Achat** | BTC au comptant (spot) | Pas de financement à payer. Faire les achats en perpétuel aurait coûté 6 à 10 % par an. Aucune liquidation possible |
| **Vente** | Perpétuel USDⓈ-M BTCUSDT, marge isolée, levier 1 | La marge déposée = la taille de la vente : liquidation seulement si le BTC double |
| Le reste | USDT au comptant | — |

**Levier ×2 à ×10 (montage « perpétuel »)** : la position du profil est multipliée par le levier. Tout passe en
perpétuel USDⓈ-M BTCUSDT, marge croisée, tout le capital en USDT sur le portefeuille futures. Les achats paient
alors le financement. Un **stop de protection** (stop au marché sur le prix de marque, qui ferme toute la position)
est posé chez Binance à mi-chemin de la liquidation, et replacé à chaque cycle : sans lui, le test liquide le compte
dès ×4.

## Le levier : ce que dit le test (`profils.py`, `profils.json`)

Tableau calculé sur 2012-2026, bougies 4h Bitstamp, avec frais, financement, stops et liquidations :

| Levier | Gain par an 2018-2026 | Pire baisse 2018-2026 | Pire baisse 2012-2026 | Sharpe 2012-2026 |
|---|---|---|---|---|
| **×1** | +35 % | −21 % | −25 % | 1,91 |
| ×2 | +62 % | −42 % | −65 % | 1,72 |
| ×3 | +88 % | −59 % | −71 % | 1,72 |
| ×4 | +107 % | −72 % | −82 % | 1,63 |
| ×5 | +77 % | −92 % | −96 % | 1,56 |
| ×6 à ×8 | +62 % à +17 % | −95 % à −99 % | −96 % à −99 % | 1,44 |
| ×9 | −13 % | −100 % | −100 % | 1,39 |
| ×10 | −46 % | −100 % | −100 % | 1,32 |

- Au-delà de ×4, le gain **baisse** : les frais, le financement, les stops et l'usure due à la volatilité dévorent
  tout. À ×9 et ×10, le test perd de l'argent.
- Étrave demande de taper LEVIER pour dépasser ×3.

## Ordres limites

Par défaut, chaque ordre est d'abord un **ordre limite « post-only »** au meilleur prix du carnet, re-placé jusqu'à
8 fois (environ 2 minutes). Le reste part au marché. En perpétuel, les frais tombent de 0,05 % à 0,02 %. Au comptant,
les frais Binance sont les mêmes, mais on évite l'écart achat-vente. `"ordres": "marche"` revient aux ordres au
marché.

## Profils

| `profil` | Volatilité cible | Sharpe 2012-2026 | Gain par an 2018-2026 | Pire baisse |
|---|---|---|---|---|
| `prudent` (par défaut) | 40 % | 1,89 | +34 % | −25 % |
| `equilibre` | 60 % | 1,80 | +40 % | −32 % |

`"vente": 0` dans la configuration désactive la vente (neutre sur l'historique long, voir le rapport).

## Installation

1. **Python 3.10 ou plus**, puis, depuis la racine du dépôt :

   ```bash
   pip install pandas numpy ccxt
   ```

2. **Configuration** : copie `bitcoin/config.exemple.json` en `bitcoin/config.json` (hors git) :

   | Clé | Valeurs | Défaut |
   |---|---|---|
   | `mode` | `papier` (compte fictif), `testnet` (Binance de test), `reel` | `papier` |
   | `profil` | `prudent`, `equilibre` | `prudent` |
| `levier` | 1 à 10 | `1` |
| `ordres` | `limite`, `marche` | `limite` |
   | `vente` | taille de la vente (`0` = pas de vente, `null` = celle du profil) | `null` |
   | `bande` | ajustement minimal | `0.05` |
   | `perte_max` | coupe-circuit | `0.40` |
   | `capital_papier` | capital du mode papier | `10000` |

3. **Clés Binance** (modes `testnet` et `reel`). Le plus simple : **Étrave, espace Bitcoin, onglet « Connexion
   Binance »**. La clé est rangée dans `btc-secrets.json` du dossier d'Étrave (hors dépôt, jamais renvoyée à la page).
   Sinon, dans l'environnement, jamais dans un fichier du dépôt :

   ```bash
   export BINANCE_API_KEY="..."
   export BINANCE_API_SECRET="..."
   ```

   Sous Windows, lance `setx BINANCE_API_KEY "..."` puis rouvre la fenêtre.

   Crée la clé dans Binance > Gestion des API avec :
   - lecture, trading spot et trading futures ;
   - **retrait désactivé** ;
   - **accès limité à l'adresse IP** de la machine du bot.

   Active les futures USDⓈ-M sur le compte.
4. **Telegram** (facultatif) : `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID` dans l'environnement.
5. **Mode réel** : garde-fou supplémentaire, `BOT_REEL_CONFIRME=oui` dans l'environnement.

## Utilisation

```bash
python bitcoin/bot.py --etat        # compte + décision du moment, AUCUN ordre
python bitcoin/bot.py --une-fois    # un cycle complet, puis arrêt
python bitcoin/bot.py               # la boucle : un cycle toutes les 4 h
```

**Depuis Étrave** (espace Bitcoin) :
- Démarrer, Arrêter ;
- Analyser maintenant ;
- Pause, Reprendre ;
- Tout fermer (mot FERMER) ;
- Réarmer après un coupe-circuit.

**À la main**, dans `bitcoin/etat/` :
- créer un fichier `PAUSE` : plus aucun ordre, le bot continue d'analyser et d'alerter ;
- créer un fichier `FERMER` : tout est fermé au prochain cycle, puis pause ;
- créer un fichier `MAINTENANT` : un cycle tout de suite, vu en moins de 15 secondes ;
- créer un fichier `REARMER` : repartir après un coupe-circuit.

Supprime le fichier pour reprendre. Après un coupe-circuit, il faut retirer `"arrete"` de `etat/etat.json` pour
relancer.

**Faire tourner en continu** :
- **Windows** : `bitcoin/lancer_bot.bat`. Pour un démarrage automatique, ajoute-le au Planificateur de tâches,
  déclencheur « à l'ouverture de session ».
- **Linux / VPS** : `bitcoin/bot-btc.service`, un service systemd qui redémarre le bot s'il s'arrête.

La machine doit rester allumée. Un VPS à 5 €/mois suffit. Choisis un pays où Binance est autorisé : depuis certains
pays, l'API répond « restricted location ».

## Tests

```bash
python -m pip install pytest
python -m pytest bitcoin -q
```

25 tests :
- plan d'ordres ;
- comptabilité du compte papier, y compris le gain d'une vente quand le prix baisse ;
- PAUSE, FERMER, coupe-circuit, données en retard ;
- **décisions identiques au backtest** sur 20 instants tirés au hasard ;
- **rejeu 2018-2026** de l'exécution (frais, glissement, bande, marge) : Sharpe 1,36, comme le backtest (1,36),
  +37 % par an, pire baisse −23 % ;
- concordance des prix Binance et Bitstamp : même sens de position 98,5 % du temps ;
- levier : montage perpétuel, retournement de position, stop de protection (placé et touché), cible multipliée ;
- ordres limites, puis le reste au marché (avec un faux exchange), et des frais plus bas qu'au marché ;
- commande « maintenant », secrets lus dans le fichier d'Étrave.

Côté Étrave, `python -m pytest etrave` (34 tests) couvre l'espace Bitcoin :
- réglages et leurs bornes ;
- mots de confirmation REEL, LEVIER et FERMER ;
- clé en écriture seule : jamais renvoyée, même par le serveur HTTP ;
- démarrer, arrêter, pause, fermer, réarmer ;
- un bot muet depuis plus d'une minute est vu comme arrêté.

## Ce qui n'a PAS encore été vérifié

- **Aucun ordre réel ni testnet n'a été passé** : l'API de trading de Binance est bloquée depuis la machine où le bot a
  été écrit. Le courtier Binance (`courtier.py`, `CourtierBinance`) passe par ccxt, mais ses appels n'ont pas encore
  tourné contre Binance : transferts spot ↔ futures, marge isolée, levier 1, ordres au marché, lecture des soldes.
  **Première étape : le testnet**, puis lire le journal ligne par ligne.
- Le testnet spot de Binance est séparé de celui des futures. Si l'un des deux manque, le bot s'arrête sur une erreur
  et alerte : il ne passe pas d'ordre à moitié.
- Ordres limites post-only : la logique (re-placement, annulation, reste au marché) est testée avec un faux exchange,
  pas encore contre Binance.
- Le stop de protection (STOP_MARKET, closePosition, prix de marque) n'a pas encore été posé chez Binance.
- Si un ordre échoue au milieu d'un rééquilibrage, le cycle s'arrête avec une alerte. Le cycle suivant repart de
  l'état réel du compte : le plan est toujours calculé à partir des soldes lus chez Binance, jamais de mémoire.
