#!/bin/sh
# Étrave sur Mac : double-clic. Met l'EA V11 et ses deux graphiques (Nasdaq 100 et S&P 500) à jour dans MetaTrader 5 pour Mac,
# ouvre MetaTrader avec le trading automatique s'il est fermé, garde le Mac éveillé tant qu'il tourne, puis ouvre la page
# d'Étrave, où tout se règle (risque, marchés, Telegram, compte). Laisse cette fenêtre ouverte tant que tu utilises la page.
# --session : lancement à l'ouverture de la session (case de la page) ; MetaTrader ne s'ouvre alors que si sa case est cochée.
cd "$(dirname "$0")/.." || exit 1
PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ "$1" = "--session" ]; then shift; set -- --sans-navigateur "$@"; else set -- --tout "$@"; fi
PY=""
if [ -x .venv/bin/python ] && .venv/bin/python -c "import sys" >/dev/null 2>&1; then PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1 && python3 -c "import sys; sys.exit(sys.version_info < (3, 8))" >/dev/null 2>&1; then PY=python3
fi
if [ -z "$PY" ]; then
  echo "Python 3 n'est pas installé sur ce Mac. Installe-le depuis https://www.python.org/downloads/ puis double-clique à nouveau sur Étrave."
  open "https://www.python.org/downloads/"
  exit 1
fi
exec "$PY" etrave/etrave.py "$@"
