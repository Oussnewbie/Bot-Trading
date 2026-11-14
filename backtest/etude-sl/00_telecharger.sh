#!/bin/bash
# Télécharge le M1 bid ET ask de Dukascopy, un fichier par année, pour le Nasdaq CFD et l'or.
#   ./00_telecharger.sh            tout (2010 -> FIN)
# Les fichiers vont dans donnees/brut/<instrument>/ (ignoré par git). Un fichier déjà présent n'est pas retéléchargé.
# Une année sans aucune donnée chez Dukascopy laisse un fichier <nom>.vide : c'est une information, pas une erreur.
# Un téléchargement raté laisse une ligne dans donnees/brut/ECHECS.txt et le script sort avec le code 1.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
BRUT="$ICI/donnees/brut"
CACHE="$ICI/donnees/.cache-dukascopy"
OUTIL="dukascopy-node@1.51.1"
DEBUT=2010
FIN="2026-11-14"          # exclu : dernière journée demandée = 2026-11-13
AN_FIN=${FIN:0:4}
mkdir -p "$BRUT"
: > "$BRUT/ECHECS.txt"
npx --yes "$OUTIL" --help > /dev/null || { echo "npx $OUTIL indisponible"; exit 2; }

serie() {   # serie <instrument> <bid|ask>
  local instr=$1 cote=$2 an de a nom dest
  mkdir -p "$BRUT/$instr"
  for an in $(seq $DEBUT "$AN_FIN"); do
    nom="$instr-m1-$cote-$an"; dest="$BRUT/$instr/$nom.csv"
    [ -s "$dest" ] || [ -e "$BRUT/$instr/$nom.vide" ] && continue
    de="$an-01-01"; a="$((an + 1))-01-01"; [ "$an" = "$AN_FIN" ] && a="$FIN"
    if npx --yes "$OUTIL" -i "$instr" -from "$de" -to "$a" -t m1 -p "$cote" -f csv -v \
         -dir "$BRUT/$instr" -fn "$nom" -r 5 -rp 2000 -ch -chpath "$CACHE" -s > "$BRUT/$instr/$nom.log" 2>&1; then
      if [ -s "$dest" ]; then echo "ok    $nom $(wc -l < "$dest" | tr -d ' ') lignes"
      else rm -f "$dest"; touch "$BRUT/$instr/$nom.vide"; echo "vide  $nom"; fi
    else
      rm -f "$dest"; echo "$nom" >> "$BRUT/ECHECS.txt"; echo "ECHEC $nom (voir $nom.log)"
    fi
  done
}

for instr in usatechidxusd xauusd; do
  for cote in bid ask; do serie "$instr" "$cote" & done
done
wait
if [ -s "$BRUT/ECHECS.txt" ]; then echo "ECHECS :"; cat "$BRUT/ECHECS.txt"; exit 1; fi
echo "Terminé sans échec."
