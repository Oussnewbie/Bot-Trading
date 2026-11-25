"""Largeur d'un texte dans la police des vidéos (DIN Alternate Bold), lue dans le fichier de la police (tables cmap format 4 et hmtx,
sans crénage) : de quoi poser les étiquettes et couper les lignes sans déborder des zones sûres de TikTok. La police n'est pas dans le
dépôt (sous licence) : sans fichier lisible, une estimation de 0,56 em par caractère, un peu large, donc sans débordement."""
import os
import struct

DEFAUT = "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf"
_polices = {}


def _charger(chemin):
    d = open(chemin, "rb").read()
    tables = {}
    for i in range(struct.unpack(">H", d[4:6])[0]):
        tag, _, off, _ = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
        tables[tag.decode("latin-1")] = off
    upm = struct.unpack(">H", d[tables["head"] + 18:tables["head"] + 20])[0]
    nhm = struct.unpack(">H", d[tables["hhea"] + 34:tables["hhea"] + 36])[0]
    co = tables["cmap"]
    st = None
    for i in range(struct.unpack(">H", d[co + 2:co + 4])[0]):
        _, _, off = struct.unpack(">HHI", d[co + 4 + 8 * i:co + 12 + 8 * i])
        if struct.unpack(">H", d[co + off:co + off + 2])[0] == 4:
            st = co + off
            break
    if st is None:
        return None
    segx2 = struct.unpack(">H", d[st + 6:st + 8])[0]
    n = segx2 // 2
    fins = struct.unpack(f">{n}H", d[st + 14:st + 14 + segx2])
    p = st + 16 + segx2
    debuts = struct.unpack(f">{n}H", d[p:p + segx2])
    deltas = struct.unpack(f">{n}h", d[p + segx2:p + 2 * segx2])
    ro = p + 2 * segx2
    decalages = struct.unpack(f">{n}H", d[ro:ro + segx2])
    hm = tables["hmtx"]

    def avance(c):
        g = 0
        for k in range(n):
            if debuts[k] <= c <= fins[k]:
                if decalages[k] == 0:
                    g = (c + deltas[k]) & 0xFFFF
                else:
                    a = ro + 2 * k + decalages[k] + 2 * (c - debuts[k])
                    g0 = struct.unpack(">H", d[a:a + 2])[0]
                    g = (g0 + deltas[k]) & 0xFFFF if g0 else 0
                break
        g = min(g, nhm - 1)
        return struct.unpack(">H", d[hm + 4 * g:hm + 4 * g + 2])[0] / upm
    return avance


def largeur(texte, taille, chemin=None):
    """Largeur en pixels de `texte` à `taille` px."""
    chemin = os.path.expanduser(chemin or DEFAUT)
    if chemin not in _polices:
        try:
            _polices[chemin] = _charger(chemin)
        except (OSError, KeyError, struct.error):
            _polices[chemin] = None
    avance = _polices[chemin]
    if avance is None:
        return 0.56 * taille * len(texte)
    return sum(avance(ord(c)) for c in texte) * taille


def couper(texte, taille, largeur_max, chemin=None):
    """Les lignes de `texte` coupé aux espaces pour tenir dans `largeur_max` px."""
    lignes, courante = [], ""
    for mot in texte.split():
        essai = f"{courante} {mot}".strip()
        if courante and largeur(essai, taille, chemin) > largeur_max:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes
