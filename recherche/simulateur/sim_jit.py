"""njit de numba, ou un décorateur qui ne fait rien si numba n'est pas installé.

Sans numba les résultats sont les mêmes (Python pur), seulement beaucoup plus lents.
Pour forcer le Python pur alors que numba est installé : variable d'environnement NUMBA_DISABLE_JIT=1.
"""
try:
    from numba import njit
    AVEC_NUMBA = True
except ImportError:                     # pragma: no cover - dépend de l'installation
    AVEC_NUMBA = False

    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return lambda f: f
