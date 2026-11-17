#!/bin/bash
# Bougies 5 minutes Binance spot BTCUSDT et ETHUSDT (avec volume acheteur agressif), 2017-08 -> 2026-11-16.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"; D="$ICI/../../donnees/crypto"
source <(sed -n "/^bn()/,/^}/p" "$ICI/00_telecharger.sh")
for s in BTCUSDT ETHUSDT; do
  python3 -c "import pandas as pd; print(' '.join(p.strftime('%Y-%m') for p in pd.period_range('2017-08','2026-10',freq='M')))" \
    | tr ' ' '\n' | xargs -P 8 -I{} bash -c "$(declare -f bn); D='$D'; bn spot/monthly/klines/$s/5m/$s-5m-{}"
  seq -w 1 16 | xargs -P 8 -I{} bash -c "$(declare -f bn); D='$D'; bn spot/daily/klines/$s/5m/$s-5m-2026-11-{}"
done
echo fini
