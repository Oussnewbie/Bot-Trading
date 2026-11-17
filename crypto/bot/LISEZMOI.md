# Le bot BTC

Il exécute la stratégie de `crypto/RAPPORT-BTC.md` sur Binance, sans intervention, et prévient sur Telegram.

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

| Position | Où | Pourquoi |
|---|---|---|
| **Achat** | BTC au comptant (spot) | Pas de financement à payer. Faire les achats en perpétuel aurait coûté 6 à 10 % par an. Aucune liquidation possible |
| **Vente** | Perpétuel USDⓈ-M BTCUSDT, marge isolée, levier 1 | La marge déposée = la taille de la vente : liquidation seulement si le BTC double |
| Le reste | USDT au comptant | — |

**Pas de levier dans cette version.** Avec des portefeuilles spot et futures séparés, un levier de 2× mettrait la
liquidation à environ −20 %, ce qu'un krach du BTC atteint en une journée. Le profil « dynamique » du rapport viendra
plus tard, avec le mode multi-actifs de Binance (le BTC sert alors de garantie), après la démo.

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

2. **Configuration** : copie `crypto/bot/config.exemple.json` en `crypto/bot/config.json` (hors git) :

   | Clé | Valeurs | Défaut |
   |---|---|---|
   | `mode` | `papier` (compte fictif), `testnet` (Binance de test), `reel` | `papier` |
   | `profil` | `prudent`, `equilibre` | `prudent` |
   | `vente` | taille de la vente (`0` = pas de vente, `null` = celle du profil) | `null` |
   | `bande` | ajustement minimal | `0.05` |
   | `perte_max` | coupe-circuit | `0.40` |
   | `capital_papier` | capital du mode papier | `10000` |

3. **Clés Binance** (modes `testnet` et `reel`), **dans l'environnement, jamais dans un fichier du dépôt** :

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
python crypto/bot/bot.py --etat        # compte + décision du moment, AUCUN ordre
python crypto/bot/bot.py --une-fois    # un cycle complet, puis arrêt
python crypto/bot/bot.py               # la boucle : un cycle toutes les 4 h
```

**Arrêts** (dans `crypto/bot/etat/`) :
- créer un fichier `PAUSE` : plus aucun ordre, le bot continue d'analyser et d'alerter ;
- créer un fichier `FERMER` : tout est fermé au prochain cycle, puis pause.

Supprime le fichier pour reprendre. Après un coupe-circuit, il faut retirer `"arrete"` de `etat/etat.json` pour
relancer.

**Faire tourner en continu** :
- **Windows** : `crypto/bot/lancer_bot.bat`. Pour un démarrage automatique, ajoute-le au Planificateur de tâches,
  déclencheur « à l'ouverture de session ».
- **Linux / VPS** : `crypto/bot/bot-btc.service`, un service systemd qui redémarre le bot s'il s'arrête.

La machine doit rester allumée. Un VPS à 5 €/mois suffit. Choisis un pays où Binance est autorisé : depuis certains
pays, l'API répond « restricted location ».

## Tests

```bash
python -m pip install pytest
python -m pytest crypto/bot -q
```

15 tests :
- plan d'ordres ;
- comptabilité du compte papier, y compris le gain d'une vente quand le prix baisse ;
- PAUSE, FERMER, coupe-circuit, données en retard ;
- **décisions identiques au backtest** sur 20 instants tirés au hasard ;
- **rejeu 2018-2026** de l'exécution (frais, glissement, bande, marge) : Sharpe 1,36, comme le backtest (1,36),
  +37 % par an, pire baisse −23 % ;
- concordance des prix Binance et Bitstamp : même sens de position 98,5 % du temps.

## Ce qui n'a PAS encore été vérifié

- **Aucun ordre réel ni testnet n'a été passé** : l'API de trading de Binance est bloquée depuis la machine où le bot a
  été écrit. Le courtier Binance (`courtier.py`, `CourtierBinance`) passe par ccxt, mais ses appels n'ont pas encore
  tourné contre Binance : transferts spot ↔ futures, marge isolée, levier 1, ordres au marché, lecture des soldes.
  **Première étape : le testnet**, puis lire le journal ligne par ligne.
- Le testnet spot de Binance est séparé de celui des futures. Si l'un des deux manque, le bot s'arrête sur une erreur
  et alerte : il ne passe pas d'ordre à moitié.
- Ordres au marché (preneur, 0,10 % spot, 0,05 % futures) : c'est l'hypothèse du test. Des ordres limites
  économiseraient un peu, à faire plus tard.
- Si un ordre échoue au milieu d'un rééquilibrage, le cycle s'arrête avec une alerte. Le cycle suivant repart de
  l'état réel du compte : le plan est toujours calculé à partir des soldes lus chez Binance, jamais de mémoire.
