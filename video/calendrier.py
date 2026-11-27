"""Les jours de séance attendus, à l'heure de New York : du lundi au vendredi, sauf les jours fériés américains et les demi-séances.

C'est la copie en Python de `ShortDay()` de l'EA (robot/Strategy-V11.mq5), règle pour règle, y compris ses choix « par prudence »
(le jeudi 2 juillet 2026 traité en demi-séance, le 31 décembre férié quand le 1er janvier suivant tombe un samedi) : ces jours-là,
l'EA ne trade pas (`InpSkipShort`). Un test vérifie l'accord avec le code de l'EA (test_video.py). Une fermeture exceptionnelle de la
Bourse (deuil national…) n'y est pas, comme dans l'EA : elle apparaît comme une séance absente des journaux, à acquitter
(`outil.py ignorer --jour AAAA-MM-JJ`).

V-01 et V-03 (audit du 27/11/2026) : sans ce calendrier, un jour où l'EA n'avait rien écrit (MetaTrader fermé, « JOUR MANQUÉ ») ne
se voyait pas, et une semaine pouvait être publiée avec un jour perdant en moins. V-10 : les fériés et les demi-séances ne comptent
pas comme séances dans la semaine et le mois.
"""
import datetime

UN_JOUR = datetime.timedelta(days=1)
LUNDI, JEUDI = 0, 3
# Heure de New York après laquelle la séance d'un jour doit être dans les journaux : la sortie de fin de journée est à 15:50 et l'EA
# écrit sa ligne « fin » vers 15:52 ; le mode automatique passe à 22:20 et 23:50 à Paris (16:20 à 17:50 à New York).
FIN_DE_SEANCE_NY = datetime.time(16, 15)


def _observe(d):
    """Un férié qui tombe un samedi est chômé le vendredi, un dimanche le lundi (Observed de l'EA)."""
    return d - UN_JOUR if d.weekday() == 5 else d + UN_JOUR if d.weekday() == 6 else d


def _nieme(annee, mois, jour_semaine, n):
    """Le n-ième jour « jour_semaine » (0 = lundi) du mois (NthDow de l'EA)."""
    d = datetime.date(annee, mois, 1)
    return d + datetime.timedelta(days=(jour_semaine - d.weekday()) % 7 + 7 * (n - 1))


def _dernier(annee, mois, jour_semaine):
    """Le dernier jour « jour_semaine » du mois (LastDow de l'EA)."""
    d = (datetime.date(annee + 1, 1, 1) if mois == 12 else datetime.date(annee, mois + 1, 1)) - UN_JOUR
    return d - datetime.timedelta(days=(d.weekday() - jour_semaine) % 7)


def vendredi_saint(annee):
    """Deux jours avant Pâques (calcul grégorien, le même que GoodFriday de l'EA)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return datetime.date(annee, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1) - 2 * UN_JOUR


def ferie_ou_demi(jour):
    """Vrai pour un jour férié américain ou une demi-séance (ShortDay de l'EA) : l'EA ne trade pas ce jour-là."""
    y = jour.year
    tg = _nieme(y, 11, JEUDI, 4)                       # Thanksgiving : 4e jeudi de novembre
    j4 = datetime.date(y, 7, 4)
    # veille du 4 juillet : demi-séance quand le 4 tombe du mardi au vendredi ; par prudence aussi le jeudi quand il tombe un samedi
    pre4 = j4 - UN_JOUR if 1 <= j4.weekday() <= 4 else (j4 - 2 * UN_JOUR if j4.weekday() == 5 else None)
    feries = (_observe(datetime.date(y, 1, 1)), _observe(datetime.date(y + 1, 1, 1)), _nieme(y, 1, LUNDI, 3), _nieme(y, 2, LUNDI, 3),
              vendredi_saint(y), _dernier(y, 5, LUNDI), _observe(datetime.date(y, 6, 19)), _observe(j4), _nieme(y, 9, LUNDI, 1),
              tg, _observe(datetime.date(y, 12, 25)))
    if jour in feries:
        return True
    return jour == tg + UN_JOUR or jour == datetime.date(y, 12, 24) or (pre4 is not None and jour == pre4)


def jour_de_seance(jour):
    """Un jour où l'EA doit écrire sa séance : du lundi au vendredi, ni férié ni demi-séance."""
    return jour.weekday() < 5 and not ferie_ou_demi(jour)


def jours_de_seance(debut, fin):
    """Les jours de séance de [debut, fin], dans l'ordre."""
    jours, d = [], debut
    while d <= fin:
        if jour_de_seance(d):
            jours.append(d)
        d += UN_JOUR
    return jours


def seance_due(jour, maintenant):
    """La séance du `jour` (date de New York) devrait-elle déjà être dans les journaux à l'instant `maintenant` (avec fuseau) ?"""
    import journee
    fin = datetime.datetime.combine(jour, FIN_DE_SEANCE_NY, tzinfo=journee.NEW_YORK)
    return maintenant >= fin
