#!/bin/bash
# Séries macro FRED (gratuites, sans clé) pour optimisation.py.
D="$(cd "$(dirname "$0")" && pwd)/donnees/macro"; mkdir -p "$D"
for s in WM2NS WALCL DTWEXBGS NASDAQCOM DGS10 SP500; do
  curl -s --retry 4 "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s&cosd=2015-01-01" -o "$D/$s.csv"
done
