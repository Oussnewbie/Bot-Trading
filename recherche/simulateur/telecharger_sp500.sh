#!/bin/bash
# Télécharge le S&P 500 CFD de Dukascopy (usa500idxusd), M1 bid ET ask, du 2018-01-01 au jour FIN exclu, une année à la fois,
# puis réunit les années en deux CSV (bid, ask) dans donnees/brut/sp500/, au format des CSV du Nasdaq du Bureau.
# Session 5 (recherche/notes/idees-strategies.md) : ces données jugent les règles UNE seule fois.
#   recherche/simulateur/telecharger_sp500.sh
# Outil : dukascopy-node (npm), comme pour l'étude des stops v5. Un échec est listé dans ECHECS.txt et le script sort avec le code 1.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
DEPOT="$(cd "$ICI/../.." && pwd)"
DOSSIER="${BOT_TRADING_DONNEES:-$DEPOT/donnees}/brut/sp500"
ANNEES="$DOSSIER/annees"
OUTIL="dukascopy-node@1.51.1"
CODE="usa500idxusd"
FIN="${FIN:-2026-11-24}"
mkdir -p "$ANNEES"
: > "$DOSSIER/ECHECS.txt"
npx --yes "$OUTIL" --help > /dev/null || { echo "npx $OUTIL indisponible"; exit 2; }

for an in $(seq 2018 "${FIN:0:4}"); do
  de="$an-01-01"; a="$((an + 1))-01-01"; [ "$an" = "${FIN:0:4}" ] && a="$FIN"
  for cote in bid ask; do
    f="$CODE-m1-$cote-$an"
    [ -s "$ANNEES/$f.csv" ] && continue
    npx --yes "$OUTIL" -i "$CODE" -from "$de" -to "$a" -t m1 -p "$cote" -f csv -v \
        -dir "$ANNEES" -fn "$f" -r 5 -rp 2000 -s > "$ANNEES/$f.log" 2>&1 || echo "$f" >> "$DOSSIER/ECHECS.txt"
    [ -s "$ANNEES/$f.csv" ] && echo "ok    $f" || echo "VIDE  $f"
  done
done

if [ -s "$DOSSIER/ECHECS.txt" ]; then echo "ECHECS :"; cat "$DOSSIER/ECHECS.txt"; exit 1; fi
for cote in bid ask; do
  sortie="$DOSSIER/$CODE-m1-$cote-2018-01-01-$FIN.csv"
  first=1
  for f in "$ANNEES/$CODE-m1-$cote-"*.csv; do
    if [ $first = 1 ]; then cat "$f" > "$sortie.tmp"; first=0; else tail -n +2 "$f" >> "$sortie.tmp"; fi
  done
  mv "$sortie.tmp" "$sortie"
  echo "$(($(wc -l < "$sortie") - 1)) minutes -> $sortie"
done
echo "Terminé sans échec."
