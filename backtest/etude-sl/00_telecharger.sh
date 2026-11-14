#!/bin/bash
# Télécharge le M1 bid ET ask de Dukascopy pour le Nasdaq CFD et l'or, et range un zip par année dans donnees/ :
#   donnees/nas100/usatechidxusd-m1-<année>.zip   (bid et ask dans le même zip)
#   donnees/or/xauusd-m1-<année>.zip
#
#   ./00_telecharger.sh                 les années manquantes, de DEBUT (2018) à FIN
#   ./00_telecharger.sh 2026            refait l'année 2026 même si son zip existe (pour prolonger les données : change FIN)
#   DEBUT=2010 ./00_telecharger.sh      tout l'historique Dukascopy (voir sorties/historique-2011-2026/)
#
# Les données du dépôt vont du 2018-01-01 au 2026-11-13 : ce script ne sert qu'à les refaire ou à les prolonger.
# Une année sans aucune donnée chez Dukascopy laisse un fichier .vide dans donnees/cache/brut/ : c'est une information.
# Un téléchargement raté est listé dans donnees/cache/brut/ECHECS.txt et le script sort avec le code 1.
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
DONNEES="$(cd "$ICI/../.." && pwd)/donnees"
BRUT="$DONNEES/cache/brut"
OUTIL="dukascopy-node@1.51.1"
DEBUT=${DEBUT:-2018}
FIN="2026-11-14"          # exclu : dernière journée demandée = 2026-11-13
AN_FIN=${FIN:0:4}
REFAIRE="${1:-}"
mkdir -p "$BRUT"
: > "$BRUT/ECHECS.txt"
npx --yes "$OUTIL" --help > /dev/null || { echo "npx $OUTIL indisponible"; exit 2; }

serie() {   # serie <nom du dossier> <code Dukascopy>
  local nom=$1 code=$2 an cote de a f zip ok
  mkdir -p "$DONNEES/$nom" "$BRUT/$code"
  for an in $(seq "$DEBUT" "$AN_FIN"); do
    zip="$DONNEES/$nom/$code-m1-$an.zip"
    [ "$an" = "$REFAIRE" ] && rm -f "$zip" "$BRUT/$code/$code-m1-"*"-$an."*
    [ -s "$zip" ] || [ -e "$BRUT/$code/$code-m1-$an.vide" ] && continue
    de="$an-01-01"; a="$((an + 1))-01-01"; [ "$an" = "$AN_FIN" ] && a="$FIN"
    ok=1
    for cote in bid ask; do
      f="$code-m1-$cote-$an"
      npx --yes "$OUTIL" -i "$code" -from "$de" -to "$a" -t m1 -p "$cote" -f csv -v \
          -dir "$BRUT/$code" -fn "$f" -r 5 -rp 2000 -s > "$BRUT/$code/$f.log" 2>&1 || ok=0
    done
    if [ $ok = 0 ]; then
      echo "$code-m1-$an" >> "$BRUT/ECHECS.txt"; echo "ECHEC $code $an (voir $BRUT/$code/)"
    elif [ -s "$BRUT/$code/$code-m1-bid-$an.csv" ] && [ -s "$BRUT/$code/$code-m1-ask-$an.csv" ]; then
      zip -9 -q -j -X "$zip" "$BRUT/$code/$code-m1-bid-$an.csv" "$BRUT/$code/$code-m1-ask-$an.csv" \
        && rm -f "$BRUT/$code/$code-m1-bid-$an.csv" "$BRUT/$code/$code-m1-ask-$an.csv" && echo "ok    $code $an"
    else
      rm -f "$BRUT/$code/$code-m1-"*"-$an.csv"; touch "$BRUT/$code/$code-m1-$an.vide"; echo "vide  $code $an"
    fi
  done
}

serie nas100 usatechidxusd &
serie or xauusd &
wait
if [ -s "$BRUT/ECHECS.txt" ]; then echo "ECHECS :"; cat "$BRUT/ECHECS.txt"; exit 1; fi
echo "Terminé sans échec."
