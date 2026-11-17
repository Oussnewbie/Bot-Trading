#!/bin/bash
# Bougies journalières Binance spot de ~40 cryptos, dont des cryptos mortes ou radiées (LUNA, FTT, ...) pour limiter le
# biais du survivant. Rien n'est lu au-delà de ce que Binance a réellement coté.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"; D="$ICI/donnees"
source <(sed -n "/^bn()/,/^}/p" "$ICI/00_telecharger.sh")
SYMS="BTC ETH BNB XRP ADA SOL DOGE DOT MATIC POL LTC TRX AVAX LINK ATOM UNI XLM ETC BCH FIL NEAR ALGO VET ICP EOS XTZ THETA AAVE LUNA FTT SHIB APT ARB OP SUI PEPE WLD INJ RUNE SAND MANA AXS EGLD FTM HBAR XMR NEO WAVES ZEC DASH IOTA ONT QTUM ICX"
MOIS=$(python3 -c "import pandas as pd; print(' '.join(p.strftime('%Y-%m') for p in pd.period_range('2017-08','2026-10',freq='M')))")
for s in $SYMS; do for m in $MOIS; do echo "$s $m"; done; done | xargs -P 16 -n 2 bash -c "$(declare -f bn); D='$D'; bn spot/monthly/klines/\${0}USDT/1d/\${0}USDT-1d-\$1 2>/dev/null; true"
for s in $SYMS; do seq -w 1 16 | while read j; do echo "$s $j"; done; done | xargs -P 16 -n 2 bash -c "$(declare -f bn); D='$D'; bn spot/daily/klines/\${0}USDT/1d/\${0}USDT-1d-2026-11-\$1 2>/dev/null; true"
echo fini
