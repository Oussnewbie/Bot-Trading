"""VID-30 (audit du 26/11/2026) : le contrôle de chaque vidéo finie, écrit dans `controle.txt` à côté du rendu et dans le journal.

Il mesure ce qui a déjà raté une fois, pour qu'un défaut se voie le jour même au lieu d'être entendu sur TikTok :
- les bruitages et la musique ne doivent jamais être hachés par la voix (le gain ne saute pas de plus de 3 dB en 10 ms) ;
- la voix ne coupe jamais net (de la parole au silence total, ou l'inverse, en 5 ms) ;
- le niveau final (-15 LUFS ± 1,5) et le pic (sous -1 dBTP).
Il prévient sans bloquer (un faux positif ne doit pas arrêter la vidéo du soir). Python seul et ffmpeg : rien à installer.
"""
import array
import math
import os
import re
import subprocess

TAUX = 8000                         # assez pour des niveaux par tranches de 5 à 10 ms


def niveaux(chemin, tranche=0.01):
    """Le niveau (dBFS) de chaque tranche de `tranche` s, en mono."""
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", chemin, "-ac", "1", "-ar", str(TAUX), "-f", "s16le", "-"],
                          capture_output=True).stdout
    x = array.array("h")
    x.frombytes(brut[:len(brut) // 2 * 2])
    n = max(1, int(TAUX * tranche))
    res = []
    for i in range(0, len(x) - n + 1, n):
        s = sum(v * v for v in x[i:i + n]) / n
        res.append(10 * math.log10(s / 32768 ** 2 + 1e-12))
    return res


def hachage(avant, apres, actif=-60.0):
    """Le plus grand saut de gain (dB) d'une tranche de 10 ms à la suivante, là où la piste d'origine s'entend."""
    a, b = niveaux(avant), niveaux(apres)
    k = min(len(a), len(b))
    pire = 0.0
    for i in range(1, k):
        if a[i] > actif and a[i - 1] > actif:
            pire = max(pire, abs((b[i] - a[i]) - (b[i - 1] - a[i - 1])))
    return pire


def bords_durs(voix):
    """Les instants où la voix passe de la parole (> -30 dBFS) au silence total (< -60) ou l'inverse, en 5 ms."""
    v = niveaux(voix, 0.005)
    return [round(i * 0.005, 2) for i in range(1, len(v)) if (v[i - 1] > -30 and v[i] < -60) or (v[i - 1] < -60 and v[i] > -30)]


def niveau_final(video):
    sortie = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-af", "ebur128=peak=true", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", sortie)
    pic = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", sortie)
    return (float(lufs[-1]) if lufs else None), (float(pic[-1]) if pic else None)


def verifier(video, travail, journal=print):
    """Les remarques sur la vidéo finie (liste vide : tout va bien). `travail` : le dossier des pistes (voix.wav, bruitages.wav…)."""
    remarques = []
    for nom, avant, apres, seuil in (("bruitages", "bruitages.wav", "bruitages-sous-voix.wav", 3.0),
                                     ("musique", "musique.wav", "musique-sous-voix.wav", 3.0)):
        a, b = os.path.join(travail, avant), os.path.join(travail, apres)
        if os.path.exists(a) and os.path.exists(b):
            saut = hachage(a, b)
            if saut > seuil:
                remarques.append(f"{nom} {'hachés' if nom == 'bruitages' else 'hachée'} par la voix (saut de {saut:.1f} dB en 10 ms)")
    voix = os.path.join(travail, "voix.wav")
    if os.path.exists(voix):
        durs = bords_durs(voix)
        if durs:
            remarques.append(f"voix coupée net à {', '.join(f'{t:.2f} s' for t in durs[:5])}")
    lufs, pic = niveau_final(video)
    if lufs is not None and not -16.5 <= lufs <= -13.5:
        remarques.append(f"niveau final {lufs:.1f} LUFS (visé -15)")
    if pic is not None and pic > -1.0:
        remarques.append(f"pic à {pic:.1f} dBFS (au-dessus de -1)")
    with open(os.path.join(travail, "controle.txt"), "w", encoding="utf-8") as f:
        f.write((f"Niveau {lufs} LUFS, pic {pic} dBFS.\n" if lufs is not None else "")
                + ("\n".join("À vérifier : " + r for r in remarques) if remarques else "Contrôle : rien à signaler.") + "\n")
    for r in remarques:
        journal(f"Contrôle de la vidéo : {r} (détail dans {os.path.join(travail, 'controle.txt')}).")
    return remarques
