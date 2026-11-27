"""La photo de l'onglet Historique de MetaTrader : la preuve, en fin de vidéo récap, que les trades ont été pris et de combien ils ont
gagné ou perdu à leur clôture.

Un EA ne peut pas photographier l'onglet Historique (il ne sait capturer que son graphique) : c'est l'outil vidéo qui photographie la
fenêtre de MetaTrader, sur la machine où il tourne, le soir après la séance (le mode automatique le fait avant de monter la vidéo).

À régler une fois, dans MetaTrader :
- la Boîte à outils ouverte (Ctrl+T) sur l'onglet Historique, en « Positions », période « Aujourd'hui » ;
- seulement les colonnes utiles (clic droit sur l'en-tête) : Heure, Symbole, Type, Volume, Heure (de clôture), Profit. Moins de
  colonnes, c'est un tableau plus étroit, donc plus lisible dans la vidéo ;
- la fenêtre de MetaTrader ouverte, pas réduite. Sur un VPS, quitter le Bureau à distance avec `Deconnecter-sans-fermer.cmd`
  (tscon) : une session simplement déconnectée n'a plus d'écran, la photo serait noire.

Puis le cadre : `python video/outil.py historique --essai` photographie toute la fenêtre et pose l'image sur le Bureau. On y lit, en
pixels de cette image, le coin du tableau (x, y : le haut de la ligne d'en-tête), sa largeur, la hauteur de l'en-tête et celle d'une
ligne, à écrire dans `historique` de la configuration :
    "historique": {"x": 12, "y": 640, "largeur": 760, "entete": 22, "ligne": 20}
La photo du soir s'arrête après la dernière position du jour : la ligne de total, qui montre le solde, n'y est jamais.
"""
import datetime
import os
import shutil
import subprocess
import sys
import tempfile


class PhotoImpossible(Exception):
    pass


def _fenetre_windows(png):
    """La zone client de la plus grande fenêtre de terminal64.exe (sans barre de titre, donc sans numéro de compte ni serveur),
    rendue par PrintWindow même si une autre fenêtre la recouvre."""
    import ctypes
    from ctypes import wintypes
    user32, gdi32, kernel32 = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.kernel32
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    H = wintypes.HANDLE
    user32.GetDC.restype = H
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, H]
    user32.PrintWindow.argtypes = [wintypes.HWND, H, wintypes.UINT]
    gdi32.CreateCompatibleDC.restype = H
    gdi32.CreateCompatibleDC.argtypes = [H]
    gdi32.CreateCompatibleBitmap.restype = H
    gdi32.CreateCompatibleBitmap.argtypes = [H, ctypes.c_int, ctypes.c_int]
    gdi32.SelectObject.restype = H
    gdi32.SelectObject.argtypes = [H, H]
    gdi32.DeleteObject.argtypes = [H]
    gdi32.DeleteDC.argtypes = [H]
    kernel32.OpenProcess.restype = H
    kernel32.CloseHandle.argtypes = [H]
    trouvees = []
    Rappel = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def rappel(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        hp = kernel32.OpenProcess(0x1000, False, pid.value)          # PROCESS_QUERY_LIMITED_INFORMATION
        if hp:
            nom = ctypes.create_unicode_buffer(1024)
            n = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(hp, 0, nom, ctypes.byref(n)) and nom.value.lower().endswith("terminal64.exe"):
                r = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(r))
                trouvees.append((r.right * r.bottom, hwnd, r.right, r.bottom))
            kernel32.CloseHandle(hp)
        return True
    user32.EnumWindows(Rappel(rappel), 0)
    if not trouvees:
        raise PhotoImpossible("Fenêtre de MetaTrader introuvable (ouverte et pas réduite ?).")
    _, hwnd, w, h = max(trouvees)

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    hdc = user32.GetDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    ancien = gdi32.SelectObject(mdc, bmp)
    try:
        if not user32.PrintWindow(hwnd, mdc, 3):                    # PW_CLIENTONLY | PW_RENDERFULLCONTENT
            raise PhotoImpossible("PrintWindow a échoué (session Bureau à distance fermée ?).")
        bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        pixels = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits.argtypes = [H, H, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
        gdi32.GetDIBits(mdc, bmp, 0, h, pixels, ctypes.byref(bih), 0)
    finally:
        gdi32.SelectObject(mdc, ancien)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(hwnd, hdc)
    if not any(pixels.raw[i] for i in range(0, min(len(pixels.raw), 400000), 997)):
        raise PhotoImpossible("Photo noire : la session Windows n'a plus d'écran (quitter avec Deconnecter-sans-fermer.cmd).")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}", "-i", "-",
                    "-frames:v", "1", png], input=pixels.raw, check=True, timeout=60)


# V-04 (audit du 27/11/2026) : la photo était un RECTANGLE de l'écran (`screencapture -R` à la place de la « fenêtre de devant ») :
# une autre fenêtre posée sur MetaTrader, l'écran verrouillé ou un dialogue partaient épinglés comme « Historique MetaTrader ». La
# fenêtre est maintenant trouvée par son numéro (CoreGraphics, lu par osascript en JavaScript : rien à installer) et photographiée
# seule (`screencapture -l`, même recouverte par une autre fenêtre), puis l'image est contrôlée (presque unie ou noire : refusée).
LISTE_FENETRES = """ObjC.import('CoreGraphics'); ObjC.import('Foundation');
var l = ObjC.castRefToObject($.CGWindowListCopyWindowInfo($.kCGWindowListOptionAll | $.kCGWindowListExcludeDesktopElements, 0));
var r = [];
for (var i = 0; i < l.count; i++) { var w = l.objectAtIndex(i); var b = w.objectForKey('kCGWindowBounds');
  r.push([ObjC.unwrap(w.objectForKey('kCGWindowOwnerName')), ObjC.unwrap(w.objectForKey('kCGWindowNumber')),
          ObjC.unwrap(w.objectForKey('kCGWindowLayer')), ObjC.unwrap(b.objectForKey('Width')), ObjC.unwrap(b.objectForKey('Height'))].join('|')); }
r.join('\\n');"""
NOMS_METATRADER = ("metatrader", "terminal64", "wine")


def fenetre_metatrader(liste):
    """Le numéro de la plus grande fenêtre ordinaire (couche 0, au moins 400 x 300) de MetaTrader pour Mac dans la liste
    « propriétaire|numéro|couche|largeur|hauteur » ; une fenêtre dont le propriétaire dit MetaTrader passe avant une fenêtre Wine."""
    candidates = []
    for ligne in liste.splitlines():
        morceaux = ligne.split("|")
        if len(morceaux) != 5:
            continue
        nom, numero, couche, l, h = morceaux
        try:
            numero, couche, l, h = int(numero), int(couche), float(l), float(h)
        except ValueError:
            continue
        nom_ = nom.lower()
        if couche == 0 and l >= 400 and h >= 300 and any(n in nom_ for n in NOMS_METATRADER):
            candidates.append(("metatrader" in nom_ or "terminal64" in nom_, l * h, numero))
    return max(candidates)[2] if candidates else None


def _fenetre_mac(png):
    """La fenêtre de MetaTrader pour Mac (Wine), par son numéro ; macOS demande une fois l'autorisation d'enregistrer l'écran."""
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", LISTE_FENETRES], capture_output=True, text=True, timeout=60)
    numero = fenetre_metatrader(r.stdout or "")
    if numero is None:
        raise PhotoImpossible(f"Fenêtre de MetaTrader introuvable ({(r.stderr or '').strip()[:120] or 'ouverte, pas réduite ?'}).")
    subprocess.run(["screencapture", "-x", "-o", "-l", str(numero), png], check=True, timeout=60)
    if not os.path.exists(png):
        raise PhotoImpossible("screencapture n'a rien écrit (autorisation « Enregistrement de l'écran » ?).")


def image_presque_unie(chemin, ecart_min=6.0):
    """V-04 : une image presque unie (écran noir d'une session verrouillée, fenêtre vide) : l'écart type de sa luminosité, sur une
    réduction à 96 x 96, est sous `ecart_min` (sur 255), ou 97 % de ses points ont presque la même valeur."""
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", chemin, "-vf", "scale=96:96,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
                          capture_output=True, timeout=60).stdout
    if not brut:
        return True
    n = len(brut)
    moyenne = sum(brut) / n
    ecart = (sum((v - moyenne) ** 2 for v in brut) / n) ** 0.5
    proches = sum(1 for v in brut if abs(v - moyenne) <= 6) / n
    return ecart < ecart_min or proches > 0.97


def photographier_fenetre(png):
    if os.name == "nt":
        _fenetre_windows(png)
    elif sys.platform == "darwin":
        _fenetre_mac(png)
    else:
        raise PhotoImpossible("Photo de MetaTrader prévue sous Windows et sur Mac seulement.")
    return png


def taille_png(chemin):
    """(largeur, hauteur) lues dans l'en-tête du PNG."""
    with open(chemin, "rb") as f:
        tete = f.read(24)
    if tete[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{chemin} n'est pas un PNG")
    return int.from_bytes(tete[16:20], "big"), int.from_bytes(tete[20:24], "big")


def chemin(dossier_journaux, jour):
    return os.path.join(dossier_journaux, "captures", f"historique-{jour.isoformat()}.png")


# Heure de New York à laquelle le serveur du courtier change de jour (GMT+2 / GMT+3 avec l'heure d'été américaine : minuit du
# serveur = 17:00 à New York, toute l'année). « Aujourd'hui » de l'onglet Historique suit le jour du serveur.
CHANGEMENT_DE_JOUR_NY = 17


def trop_tard(jour, maintenant=None):
    """Correctif VID-05 (audit du 25/11/2026) : après le changement de jour du serveur, l'onglet Historique « Aujourd'hui » montre
    le jour suivant, vide, et la ligne de total (le SOLDE du compte) tombait dans le cadre de la photo, publiée comme preuve. Cela
    arrivait au lancement de 23:50 et, les semaines où l'heure d'été américaine et européenne diffèrent, à celui de 22:20."""
    import journee
    ny = (maintenant or datetime.datetime.now(datetime.timezone.utc)).astimezone(journee.NEW_YORK)
    return ny.date() != jour or ny.hour >= CHANGEMENT_DE_JOUR_NY


def photographier_jour(config, dossier_journaux, jour, n_positions, journal=print, maintenant=None):
    """La photo du tableau de l'historique du jour : l'en-tête et les n_positions lignes, sans la ligne de total (le solde).
    Rend son chemin, ou None (pas réglée, trop tard, MetaTrader absent, fenêtre trop petite : la vidéo se fait sans)."""
    cadre = config.get("historique") or {}
    if not all(cadre.get(k) for k in ("y", "largeur", "entete", "ligne")):
        journal("Photo de l'historique pas encore réglée (python video/outil.py historique --essai, puis « historique » de la "
                "configuration) : la vidéo se fait sans.")
        return None
    if trop_tard(jour, maintenant):
        journal(f"Photo de l'historique : trop tard, le serveur du courtier est passé au jour suivant à {CHANGEMENT_DE_JOUR_NY}:00 "
                "New York (l'onglet montrerait le solde) : la vidéo se fait sans.")
        return None
    sortie = chemin(dossier_journaux, jour)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    # la photo de toute la fenêtre (sur Mac, avec la barre de titre et le numéro de compte) est effacée dans tous les cas
    temporaire = tempfile.mkdtemp(prefix="historique-")
    plein = os.path.join(temporaire, "fenetre.png")
    try:
        try:
            photographier_fenetre(plein)
            w, h = taille_png(plein)
        except (PhotoImpossible, subprocess.CalledProcessError, OSError, ValueError) as err:
            journal(f"Photo de l'historique impossible : {err}")
            return None
        x, y, l = int(cadre.get("x", 0)), int(cadre["y"]), int(cadre["largeur"])
        haut = int(cadre["entete"]) + int(n_positions) * int(cadre["ligne"])
        # une fenêtre plus petite que le cadre couperait le tableau : jamais de preuve tronquée
        if x < 0 or y < 0 or x + l > w or y + haut > h:
            journal(f"Photo de l'historique : la fenêtre ({w} x {h}) est plus petite que le cadre réglé : la vidéo se fait sans.")
            return None
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", plein, "-vf", f"crop={l}:{haut}:{x}:{y}", "-frames:v", "1", sortie],
                           check=True, timeout=60)
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as err:
            journal(f"Photo de l'historique impossible (recadrage) : {err}")
            return None
        # V-04 : jamais une image noire ou vide épinglée comme preuve
        if image_presque_unie(sortie):
            os.remove(sortie)
            journal("Photo de l'historique refusée : l'image est presque unie (écran verrouillé, fenêtre vide ou cachée ?) : "
                    "la vidéo se fait sans.")
            return None
        return sortie
    finally:
        shutil.rmtree(temporaire, ignore_errors=True)


def essai(sortie_bureau="~/Desktop/metatrader-fenetre-essai.png"):
    """Photographie toute la fenêtre de MetaTrader et la pose sur le Bureau, pour lire le cadre du tableau."""
    chemin_ = os.path.expanduser(sortie_bureau)
    photographier_fenetre(chemin_)
    w, h = taille_png(chemin_)
    return chemin_, w, h
