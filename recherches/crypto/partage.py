"""Le code commun au bot et à la recherche (donnees.py, indicateurs.py, btc.py) est dans bitcoin/, avec le bot.
`import partage` le rend importable depuis les scripts de recherches/crypto/ (il est ajouté en fin de sys.path : un
module de ce dossier garde la priorité)."""
import os
import sys

BITCOIN = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bitcoin"))
if BITCOIN not in sys.path:
    sys.path.append(BITCOIN)
