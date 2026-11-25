"""Nombres, heures et dates en toutes lettres, pour que la voix les lise sans hésiter (« 21:50 » → « vingt et une heures cinquante »).

Orthographe traditionnelle (traits d'union sous cent, « et » pour 21, 31… 71, « quatre-vingts » et « cents » au pluriel seulement en
fin de nombre). Les nombres décimaux se lisent « virgule » suivi de leurs chiffres : 0,05 → « zéro virgule zéro cinq ».
"""
import datetime

UNITES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize",
          "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"]
DIZAINES = {2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _moins_de_cent(n, fin=True):
    if n < 20:
        return UNITES[n]
    d, u = divmod(n, 10)
    if d in (7, 9):                      # 70-79 = soixante-dix…, 90-99 = quatre-vingt-dix…
        base = "soixante" if d == 7 else "quatre-vingt"
        if d == 7 and u == 1:
            return "soixante et onze"
        return base + "-" + UNITES[10 + u]
    if d == 8:
        return "quatre-vingts" if u == 0 and fin else "quatre-vingt" + ("-" + UNITES[u] if u else "")
    if u == 0:
        return DIZAINES[d]
    if u == 1:
        return DIZAINES[d] + " et un"
    return DIZAINES[d] + "-" + UNITES[u]


def _moins_de_mille(n, fin=True):
    c, r = divmod(n, 100)
    if c == 0:
        return _moins_de_cent(r, fin)
    tete = "cent" if c == 1 else UNITES[c] + (" cents" if r == 0 and fin else " cent")
    return tete if r == 0 else tete + " " + _moins_de_cent(r, fin)


def entier(n):
    """Un entier en lettres (jusqu'au milliard exclu), négatifs compris."""
    n = int(n)
    if n < 0:
        return "moins " + entier(-n)
    if n < 1000:
        return _moins_de_mille(n)
    millions, reste = divmod(n, 1_000_000)
    milliers, unites = divmod(reste, 1000)
    morceaux = []
    if millions:
        morceaux.append(_moins_de_mille(millions, False) + (" million" if millions == 1 else " millions"))
    if milliers:
        morceaux.append("mille" if milliers == 1 else _moins_de_mille(milliers, False) + " mille")
    if unites:
        morceaux.append(_moins_de_mille(unites))
    return " ".join(morceaux)


def decimal(x, decimales=2, signe=False):
    """« 0,42 » → « zéro virgule quarante-deux » ; avec signe=True, « plus » ou « moins » devant (zéro n'a pas de signe)."""
    texte = f"{abs(x):.{decimales}f}".rstrip("0").rstrip(".") if decimales else str(round(abs(x)))
    ent, _, dec = texte.partition(".")
    mots = entier(int(ent))
    if dec:
        zeros = len(dec) - len(dec.lstrip("0"))
        mots += " virgule " + " ".join(["zéro"] * zeros + ([entier(int(dec))] if dec.lstrip("0") else []))
    if signe and float(texte) != 0:
        mots = ("plus " if x > 0 else "moins ") + mots
    elif not signe and x < 0 and float(texte) != 0:
        mots = "moins " + mots
    return mots


def heure(h, m):
    """15:37 → « quinze heures trente-sept » ; 21:00 → « vingt et une heures » ; 1:05 → « une heure cinq »."""
    heures = "une" if h == 1 else ("vingt et une" if h == 21 else entier(h))
    texte = heures + (" heure" if h in (0, 1) else " heures")
    return texte + (" " + entier(m) if m else "")


def date_longue(jour):
    """2026-11-18 → « mercredi dix-huit novembre » (premier : « premier »)."""
    quantieme = "premier" if jour.day == 1 else entier(jour.day)
    return f"{JOURS[jour.weekday()]} {quantieme} {MOIS[jour.month - 1]}"


def mois_ecran(mois, court=False):
    """Le mois tel qu'il s'écrit à l'écran et dans les descriptions : avec une majuscule (« Novembre », « Nov. »), à ta demande.
    La voix garde MOIS, en minuscules."""
    return (MOIS_COURTS if court else MOIS)[mois - 1].capitalize()


def date_ecran(jour):
    """2026-11-18 → (« mercredi », « 18 Novembre », « 2026 ») pour l'écran titre ; « 1er » pour le premier du mois."""
    return JOURS[jour.weekday()], f"{'1er' if jour.day == 1 else jour.day} {mois_ecran(jour.month)}", str(jour.year)


def date_courte(jour):
    """2026-11-18 → « mer. 18 Nov. 2026 », la date qui reste en haut des scènes."""
    return f"{JOURS[jour.weekday()][:3]}. {'1er' if jour.day == 1 else jour.day} {mois_ecran(jour.month, True)} {jour.year}"


def nombre_ecran(x, decimales=2, signe=True):
    """0.4237 → « +0,42 » ; -1.5 → « −1,50 » (vrai signe moins) ; 0 → « 0,00 »."""
    texte = f"{abs(x):.{decimales}f}".replace(".", ",")
    if round(x, decimales) == 0:
        return texte
    return (("+" if x > 0 else "−") if signe else ("−" if x < 0 else "")) + texte


if __name__ == "__main__":
    for n in (0, 1, 21, 71, 80, 81, 91, 100, 180, 200, 201, 1000, 2026, 1_200_000):
        print(n, entier(n))
    print(decimal(0.42, signe=True), "|", decimal(-0.05, signe=True), "|", heure(21, 50), "|", date_longue(datetime.date(2026, 11, 18)))
