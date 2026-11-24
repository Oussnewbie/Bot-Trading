"""Le seul endroit où sont réglés les dossiers du simulateur.

- DOSSIER_BRUT : les CSV Dukascopy M1 du Nasdaq (bid et ask, horodatage en ms UTC), lus sans jamais être modifiés.
  Par défaut ~/Desktop/Nasdaq 8 ans. Se change avec la variable d'environnement BOT_TRADING_BRUT.
- DOSSIER_DONNEES : tout ce qui est fabriqué (parquet, trades simulés, registre). Par défaut le dossier donnees/ à la racine
  du dépôt, ignoré par git. Se change avec la variable d'environnement BOT_TRADING_DONNEES.
Dans l'archive, ces chemins étaient écrits en dur (bac à sable de la plateforme Claude).
"""
import os

ICI = os.path.dirname(os.path.abspath(__file__))
DEPOT = os.path.dirname(os.path.dirname(ICI))

DOSSIER_BRUT = os.environ.get('BOT_TRADING_BRUT') or os.path.expanduser('~/Desktop/Nasdaq 8 ans')
DOSSIER_DONNEES = os.environ.get('BOT_TRADING_DONNEES') or os.path.join(DEPOT, 'donnees')

M1_NASDAQ = os.path.join(DOSSIER_DONNEES, 'nasdaq_m1.parquet')          # = m1.parquet de l'archive
REGISTRE_DIR = os.path.join(DOSSIER_DONNEES, 'registre')                # séries quotidiennes de commun.enregistrer
REGISTRE_CSV = os.path.join(DOSSIER_DONNEES, 'registre_essais.csv')     # registre local (celui du dépôt n'est pas touché)

REFERENCE_V10 = os.path.join(DEPOT, 'recherche', 'resultats', 'trades_V10_confort_2018_2026_1pt.csv')
