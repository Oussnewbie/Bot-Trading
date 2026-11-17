#!/bin/bash
# Données de la recherche crypto (rien n'est versionné : tout va dans crypto/donnees/, hors git).
#  1. Dukascopy M1 bid+ask : bitcoin (repris de l'historique git, commit afb79de) et Ethereum (même source, téléchargé).
#  2. Binance (data.binance.vision, archives publiques) : bougies 1h spot et futures perpétuels avec le volume
#     ACHETEUR AGRESSIF (taker buy) = la vraie mesure d'order flow ; financement (funding) ; open interest (2021-12 ->).
#     + ETHBTC (spot) : la paire ETH/BTC elle-même, pour confirmer ou infirmer un signal du bitcoin.
#  3. Coin Metrics (API communautaire) : données on-chain journalières (adresses actives, flux vers/depuis les exchanges,
#     MVRV, hashrate...).
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"; D="$ICI/donnees"; mkdir -p "$D"
FIN_MOIS="2026-10"; JOURS_NOV=$(seq -w 1 16)

# 1. Dukascopy
mkdir -p "$D/dukascopy/btcusd" "$D/dukascopy/ethusd"
for an in $(seq 2018 2026); do
  f="$D/dukascopy/btcusd/btcusd-m1-$an.zip"
  [ -s "$f" ] || git -C "$ICI/.." show "afb79de:donnees/bitcoin/btcusd-m1-$an.zip" > "$f"
done
duka() {  # ethusd, une année : bid et ask
  local an=$1 de="$1-01-01" a="$(( $1 + 1 ))-01-01" c
  [ "$an" = 2026 ] && a="2026-11-17"
  local z="$D/dukascopy/ethusd/ethusd-m1-$an.zip"; [ -s "$z" ] && return
  for c in bid ask; do
    npx --yes dukascopy-node@1.51.1 -i ethusd -from "$de" -to "$a" -t m1 -p $c -f csv -v \
      -dir "$D/dukascopy/ethusd" -fn "ethusd-m1-$c-$an" -r 5 -rp 2000 -s > "$D/dukascopy/ethusd/$an-$c.log" 2>&1
  done
  (cd "$D/dukascopy/ethusd" && zip -9 -q -j "$z" "ethusd-m1-bid-$an.csv" "ethusd-m1-ask-$an.csv" && rm -f ethusd-m1-*-$an.csv)
}

# 2. Binance
bn() {  # bn <chemin relatif sans extension>  -> dézippe le csv
  local u="https://data.binance.vision/data/$1.zip" out="$D/binance/$1.csv"
  [ -s "$out" ] && return 0
  mkdir -p "$(dirname "$out")"
  curl -sf --retry 4 --max-time 120 "$u" -o "$out.zip" && unzip -p "$out.zip" > "$out" && rm -f "$out.zip" || { rm -f "$out.zip"; return 1; }
}
mois() { python3 -c "
import pandas as pd; print(' '.join(p.strftime('%Y-%m') for p in pd.period_range('$1','$FIN_MOIS',freq='M')))"; }
binance() {
  local s=$1 m j
  for m in $(mois 2017-08); do bn "spot/monthly/klines/$s/1h/$s-1h-$m"; done
  for j in $JOURS_NOV; do bn "spot/daily/klines/$s/1h/$s-1h-2026-11-$j"; done
  for m in $(mois 2019-09); do bn "futures/um/monthly/klines/$s/1h/$s-1h-$m"; bn "futures/um/monthly/fundingRate/$s/$s-fundingRate-$m"; done
  for j in $JOURS_NOV; do bn "futures/um/daily/klines/$s/1h/$s-1h-2026-11-$j"; done
  python3 -c "
import pandas as pd; print(' '.join(d.strftime('%Y-%m-%d') for d in pd.date_range('2021-12-01','2026-11-16')))" | tr ' ' '\n' \
    | xargs -P 8 -I{} bash -c "$(declare -f bn); D='$D'; bn futures/um/daily/metrics/$s/$s-metrics-{}"
}

# 3. Coin Metrics
cm() {
  local a=$1 out="$D/coinmetrics/$1.csv"; mkdir -p "$D/coinmetrics"; [ -s "$out" ] && return
  curl -sf --retry 4 "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=$a&metrics=PriceUSD,AdrActCnt,TxCnt,TxTfrCnt,FlowInExNtv,FlowOutExNtv,SplyExNtv,CapMVRVCur,HashRate,FeeTotNtv,CapMrktCurUSD&frequency=1d&start_time=2015-01-01&page_size=10000&format=csv" -o "$out"
}

export -f bn; export D FIN_MOIS
cm btc; cm eth
for an in $(seq 2018 2026); do duka $an & done
binance BTCUSDT & binance ETHUSDT &
( for m in $(mois 2017-08); do bn "spot/monthly/klines/ETHBTC/1h/ETHBTC-1h-$m"; done
  for j in $JOURS_NOV; do bn "spot/daily/klines/ETHBTC/1h/ETHBTC-1h-2026-11-$j"; done ) &
wait
echo "Terminé."
