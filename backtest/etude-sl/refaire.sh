#!/bin/bash
# Refait toute l'étude avec une seule commande, à partir des zips M1 de donnees/ :
#   backtest/etude-sl/refaire.sh
# (étape 1 pour l'instant ; les étapes suivantes s'ajoutent ici au fur et à mesure)
# Pour retélécharger ou prolonger les données avant : backtest/etude-sl/00_telecharger.sh
set -eu
ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
PY="$RACINE/.venv/bin/python"
[ -x "$PY" ] || { python3 -m venv "$RACINE/.venv" && "$RACINE/.venv/bin/pip" install -q -r "$RACINE/requirements.txt"; }
cd "$ICI"
"$PY" -m pytest -q -p no:cacheprovider test_etude.py
"$PY" 01_construire.py > /dev/null     # bougies M1 -> D1 et sorties/etape1_inventaire.md
"$PY" 02_qualite.py > /dev/null        # sorties/etape1_qualite.md
"$PY" 03_reference.py > /dev/null      # sorties/etape1_reference.md
echo "Étude refaite : voir $ICI/sorties/"
