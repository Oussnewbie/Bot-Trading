"""Les sous-titres des scènes de marché, calés sur les mots de la voix (V-14, audit du 27/11/2026).

L'histoire en points (« jusqu'à cent trois points en notre faveur, puis le prix redescend ») n'était dite qu'à la voix, alors que
beaucoup regardent TikTok sans le son. Chaque réplique est coupée en groupes de quelques mots (fin de phrase, pause de 0,15 s ou
plus, deux lignes au plus), affichés un à la fois sous le graphique, dans la zone sûre de TikTok ; chaque mot passe du gris à l'encre
quand la voix le dit (l'heure de chaque mot vient de la voix : voix.instant, rep["mots"]).

La voix lit les nombres en lettres ; l'écran les montre en chiffres, comme les étiquettes : « quatorze heures trente-cinq » → 14:35,
« cent trois points » → 103 pts, « moins zéro virgule six R » → −0,60 R, « S et P cinq cents » → S&P 500. Un nombre sans unité
(« Trois achats en tout ») reste en lettres. Rien d'autre que ce que dit la voix : aucun secret de la stratégie.
"""
import nombres
import police

PONCTUATION = ".,:;!?…"
FIN_DE_PHRASE = (".", "!", "?", "…")
PAUSE = 0.15                 # une pause de la voix d'au moins 0,15 s coupe le groupe (HyperFrames, captions.md)
MOTS_MAX = 6
TAILLE, LIGNES_MAX = 40, 2


def _dictionnaire():
    entiers = {nombres.entier(n): n for n in range(0, 10000)}
    for n in range(1, 60):                     # les minutes au féminin : « quarante et une »
        t = nombres.entier(n)
        if t.endswith("un"):
            entiers.setdefault(t[:-2] + "une", n)
    return entiers


ENTIERS = _dictionnaire()


def _propre(mot):
    return mot.strip(PONCTUATION + "«»\"'").lower()


def _entier(mots, i):
    """(valeur, nombre de mots lus) de l'entier écrit en lettres qui commence au mot i, ou (None, 0). Le plus long d'abord."""
    for n in range(min(6, len(mots) - i), 0, -1):
        morceau = [_propre(m) for m in mots[i:i + n]]
        # la ponctuation n'est permise qu'à la fin du dernier mot
        if any(m[-1:] in PONCTUATION for m in mots[i:i + n - 1]):
            continue
        texte = " ".join(morceau)
        if texte in ENTIERS:
            return ENTIERS[texte], n
    return None, 0


def _fin(mot):
    """La ponctuation qui suit un mot (gardée à l'écran)."""
    k = len(mot)
    while k and mot[k - 1] in PONCTUATION:
        k -= 1
    return mot[k:]


def jetons(mots):
    """Les mots de la voix → les mots de l'écran : [(texte, rang du premier mot de voix, nombre de mots de voix)]."""
    res, i = [], 0
    while i < len(mots):
        m = _propre(mots[i])
        # « S et P cinq cents » → « S&P 500 »
        if m == "s" and i + 2 < len(mots) and _propre(mots[i + 1]) == "et" and _propre(mots[i + 2]) == "p":
            v, n = _entier(mots, i + 3) if not _fin(mots[i + 2]) else (None, 0)
            if v == 500:
                res.append(("S&P 500" + _fin(mots[i + 2 + n]), i, 3 + n))
                i += 3 + n
            else:
                res.append(("S&P" + _fin(mots[i + 2]), i, 3))
                i += 3
            continue
        signe = ""
        j = i
        if m in ("moins", "plus") and _entier(mots, i + 1)[1]:
            signe, j = ("−" if m == "moins" else "+"), i + 1
        v, n = _entier(mots, j)
        if v is None:
            res.append((mots[i], i, 1))
            i += 1
            continue
        k = j + n
        texte, unite, decimales = str(v), None, ""
        dernier = mots[k - 1]
        # l'heure : « quinze heures trente-cinq », « vingt et une heures »
        if k < len(mots) and _propre(mots[k]) in ("heure", "heures") and not _fin(dernier) and not signe:
            mm, nm = _entier(mots, k + 1) if not _fin(mots[k]) else (None, 0)
            if mm is not None and mm < 60:
                fin = mots[k + nm]
                res.append((f"{v}:{mm:02d}{_fin(fin)}", i, k + 1 + nm - i))
                i = k + 1 + nm
            else:
                res.append((f"{v}:00{_fin(mots[k])}", i, k + 1 - i))
                i = k + 1
            continue
        # la virgule : « zéro virgule zéro quatre »
        if k < len(mots) and _propre(mots[k]) == "virgule" and not _fin(dernier):
            zeros, q = 0, k + 1
            while q < len(mots) and _propre(mots[q]) == "zéro" and not _fin(mots[q]):
                zeros, q = zeros + 1, q + 1
            d, nd = _entier(mots, q)
            if d is not None and d < 100:
                decimales = "0" * zeros + str(d)
                dernier, k = mots[q + nd - 1], q + nd
            elif zeros:
                decimales = "0" * zeros
                dernier, k = mots[q - 1], q
        apres = _propre(mots[k]) if k < len(mots) and not _fin(dernier) else ""
        if apres in ("point", "points"):
            unite = "pt" if float(f"{v}.{decimales or 0}") < 2 else "pts"
        elif apres == "r":
            unite = "R"
        elif apres == "pour" and k + 1 < len(mots) and _propre(mots[k + 1]) == "cent":
            unite = "%"
        if not (unite or decimales or signe):
            res.append((mots[i], i, 1))             # un nombre sans unité reste en lettres (« Trois achats »)
            i += 1
            continue
        if unite == "R" and decimales:
            decimales = (decimales + "00")[:2]      # le R s'écrit avec deux décimales, comme à l'écran (−0,60 R)
        texte = signe + (f"{v},{decimales}" if decimales else str(v))
        if unite:
            n_unite = 2 if unite == "%" else 1
            fin_unite = mots[k + n_unite - 1]
            res.append((f"{texte} {unite}{_fin(fin_unite)}", i, k + n_unite - i))
            i = k + n_unite
        else:
            res.append((texte + _fin(dernier), i, k - i))
            i = k
    return res


def lignes(textes, taille=TAILLE, largeur_max=656, police_fichier=None):
    """Les jetons rangés en lignes (un jeton n'est jamais coupé) : [[indices des jetons de la ligne]]."""
    res, courante = [], []
    for k, t in enumerate(textes):
        essai = " ".join(textes[i] for i in courante + [k])
        if courante and police.largeur(essai, taille, police_fichier) > largeur_max:
            res.append(courante)
            courante = [k]
        else:
            courante.append(k)
    if courante:
        res.append(courante)
    return res


def groupes(mots_voix, police_fichier=None, largeur_max=656, taille=TAILLE):
    """Les groupes de sous-titres d'une réplique : [{"jetons": [(texte, début)], "debut", "fin", "lignes"}] (secondes de la
    réplique ; « lignes » : les indices des jetons de chaque ligne). Coupés à la fin d'une phrase (ou après « : » passé trois
    jetons), à une pause de la voix d'au moins PAUSE s, à MOTS_MAX jetons, ou quand le texte dépasserait LIGNES_MAX lignes."""
    mots = [m["mot"] for m in mots_voix]
    res, courant = [], []

    def n_lignes(js):
        return len(lignes([t for t, _, _ in js], taille, largeur_max, police_fichier))

    def clore():
        if courant:
            premier, dernier = courant[0], courant[-1]
            res.append({"jetons": [(t, mots_voix[r]["debut"]) for t, r, _ in courant], "debut": mots_voix[premier[1]]["debut"],
                        "fin": mots_voix[dernier[1] + dernier[2] - 1]["fin"],
                        "lignes": lignes([t for t, _, _ in courant], taille, largeur_max, police_fichier)})
            courant.clear()
    for jt in jetons(mots):
        texte, rang, n = jt
        if courant:
            precedent = courant[-1]
            fin_prec = mots_voix[precedent[1] + precedent[2] - 1]["fin"]
            if mots_voix[rang]["debut"] - fin_prec >= PAUSE or len(courant) >= MOTS_MAX or n_lignes(courant + [jt]) > LIGNES_MAX:
                clore()
        courant.append(jt)
        if texte.endswith(FIN_DE_PHRASE) or (texte.endswith(":") and len(courant) >= 3):
            clore()
    clore()
    return res
