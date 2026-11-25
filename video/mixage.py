"""Le son de la vidéo avec ffmpeg seul : la voix, les bruitages posés sur leur image et baissés quand la voix parle, puis le niveau final.

Les bruitages sont de vrais enregistrements (banque Mixkit, gratuite, usage commercial permis, mais pas de redistribution des fichiers
seuls) : ils ne sont pas dans le dépôt. `sons.json` donne leur nom et la page où les télécharger ; le dossier `sons` de la configuration
les contient. Un son absent est sauté (la vidéo se fait quand même, et la liste des sons manquants est affichée).

La musique de fond (facultative, réglage `musique` : un fichier ou un dossier de morceaux, jamais dans le dépôt) est coupée à la durée
de la vidéo, avec une entrée et une fin en fondu, sa basse est allégée, et elle est posée sous la voix (réglée sur ce qu'un
téléphone en fait entendre) ; elle baisse encore quand la voix parle.

Étapes : chaque son est ramené à un même pic (-6 dBFS) puis réglé par son gain, coupé à sa durée, filtré (passe-haut) et posé à son
instant ; le groupe des bruitages passe dans un compresseur commandé par la voix (il baisse quand elle parle), la musique aussi (plus
doucement) ; le tout est mesuré (LUFS intégrés) et amené au niveau visé par un simple gain, puis un limiteur garde le pic sous
-1,5 dBFS. Sortie en 48 kHz.
"""
import json
import os
import re
import subprocess

ICI = os.path.dirname(os.path.abspath(__file__))
NIVEAU_VISE = -15.0         # LUFS : la voix au premier plan, comme sur TikTok
NIVEAU_SANS_VOIX = -18.0    # LUFS : les bruitages seuls restent discrets
NIVEAU_VOIX = -15.0         # LUFS de la piste de voix avant le mélange : les gains des bruitages sont réglés pour elle
# La musique se règle sur ce qu'un téléphone en fait entendre (au-dessus de 250 Hz) : 18 dB sous la voix dans cette bande, et
# jamais plus de -26 LUFS en tout (11 dB sous la voix), pour qu'une basse forte ne couvre pas la voix au casque.
NIVEAU_MUSIQUE_AIGUS, NIVEAU_MUSIQUE_MAX = -33.0, -26.0
EQ_MUSIQUE = "highpass=f=50,bass=g=-5:f=150:w=0.7"     # moins de basse : elle ne s'entend pas sur un téléphone et brouille la voix
FORMATS_MUSIQUE = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def catalogue():
    return json.load(open(os.path.join(ICI, "sons.json"), encoding="utf-8"))["sons"]


def _pic(fichier, cache={}):
    if fichier not in cache:
        sortie = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", fichier, "-af", "volumedetect", "-f", "null", "-"],
                                capture_output=True, text=True).stderr
        m = re.search(r"max_volume: (-?[\d.]+) dB", sortie)
        cache[fichier] = float(m.group(1)) if m else 0.0
    return cache[fichier]


def _lufs(fichier):
    sortie = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", fichier, "-af", "ebur128", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    valeurs = re.findall(r"I:\s+(-?[\d.]+) LUFS", sortie)
    return float(valeurs[-1]) if valeurs else None


def piste_voix(repliques, duree, sortie):
    """Les répliques posées à leur instant ({"fichier", "t", "coupe"?}) en une piste WAV stéréo 48 kHz de la durée de la vidéo."""
    if not repliques:
        return None
    entrees, filtres, noms = [], [], []
    for i, r in enumerate(repliques):
        entrees += ["-i", r["fichier"]]
        chaine = f"[{i}]"
        if r.get("coupe"):
            chaine += f"atrim=0:{r['coupe']:.3f},afade=t=out:st={max(0, r['coupe'] - 0.05):.3f}:d=0.05,"
        ms = int(round(r["t"] * 1000))
        filtres.append(f"{chaine}aresample=48000,adelay={ms}:all=1[v{i}]")
        noms.append(f"[v{i}]")
    filtres.append("".join(noms) + f"amix=inputs={len(noms)}:normalize=0,apad=whole_dur={duree:.3f},pan=stereo|c0=c0|c1=c0[o]")
    brute = sortie[:-4] + "-brute.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", ";".join(filtres), "-map", "[o]", "-t", f"{duree:.3f}",
                    "-ar", "48000", "-c:a", "pcm_s24le", brute], check=True)
    # un gain simple mesuré (pas de normalisation dynamique), puis un limiteur à -1 dBFS pour les pics
    mesure = _lufs(brute)
    gain = (NIVEAU_VOIX - mesure) if mesure is not None and mesure > -70 else 0.0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brute, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
                    "-ar", "48000", "-c:a", "pcm_s24le", sortie], check=True)
    os.remove(brute)
    return sortie


def piste_bruitages(reperes, dossier_sons, duree, sortie):
    """Les bruitages posés : {"t" (départ), "son", "gain_db", "max_dur", "passe_haut", "tranche", "demi_tons", "avance"}.
    Rend (fichier, sons manquants)."""
    sons = catalogue()
    entrees, filtres, noms, manquants = [], [], [], []
    for r in reperes:
        nom = sons.get(r["son"], {}).get("fichier", r["son"] + ".wav")
        fichier = os.path.join(os.path.expanduser(dossier_sons or ""), nom)
        if not os.path.exists(fichier):
            manquants.append(nom)
            continue
        i = len(noms)
        entrees += ["-i", fichier]
        gain = -6.0 - _pic(fichier) + r.get("gain_db", 0.0)
        chaine = f"[{i}]aresample=48000,aformat=channel_layouts=stereo"
        if r.get("tranche"):                    # un morceau du fichier : [début, durée] en secondes
            d0, dl = r["tranche"]
            chaine += f",atrim=start={d0:.3f}:duration={dl:.3f},asetpts=PTS-STARTPTS"
        if r.get("demi_tons"):                  # hauteur changée, durée gardée
            f = 2 ** (r["demi_tons"] / 12)
            chaine += f",asetrate={48000 * f:.0f},aresample=48000,atempo={1 / f:.5f}"
        if r.get("max_dur"):
            d = r["max_dur"]
            chaine += f",atrim=0:{d:.3f},afade=t=out:st={max(0, d - 0.06):.3f}:d=0.06"
        if r.get("passe_haut"):
            chaine += f",highpass=f={int(r['passe_haut'])}"
        t = max(0.0, r["t"] - r.get("avance", 0.0))
        chaine += f",volume={gain:.2f}dB,adelay={int(round(t * 1000))}:all=1"
        filtres.append(chaine + f"[s{i}]")
        noms.append(f"[s{i}]")
    if not noms:
        return None, sorted(set(manquants))
    filtres.append("".join(noms) + f"amix=inputs={len(noms)}:normalize=0,apad=whole_dur={duree:.3f}[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", ";".join(filtres), "-map", "[o]", "-t", f"{duree:.3f}",
                    "-ar", "48000", "-c:a", "pcm_s24le", sortie], check=True)
    return sortie, sorted(set(manquants))


def choisir_musique(reglage, jour):
    """Le morceau du jour : le fichier donné, ou, pour un dossier, un de ses morceaux choisi par la date (le même si on refait la vidéo)."""
    if not reglage:
        return None
    chemin = os.path.expanduser(reglage)
    if os.path.isdir(chemin):
        morceaux = sorted(f for f in os.listdir(chemin) if f.lower().endswith(FORMATS_MUSIQUE) and not f.startswith("."))
        return os.path.join(chemin, morceaux[jour.toordinal() % len(morceaux)]) if morceaux else None
    return chemin if os.path.exists(chemin) else None


def piste_musique(reglage, jour, duree, sortie, journal=print):
    """La musique de fond coupée à la durée de la vidéo (fondu d'entrée 0,4 s, de sortie 1,8 s), basse allégée, au niveau des
    NIVEAU_MUSIQUE_*. None sans musique."""
    morceau = choisir_musique(reglage, jour)
    if not morceau:
        if reglage:
            journal(f"Musique introuvable ({reglage}) : la vidéo est faite sans musique.")
        return None
    fin = max(0.0, duree - 1.8)
    brute = sortie[:-4] + "-brute.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", morceau, "-t", f"{duree:.3f}", "-af",
                    f"aresample=48000,aformat=channel_layouts=stereo,{EQ_MUSIQUE},afade=t=in:d=0.4,afade=t=out:st={fin:.3f}:d=1.8",
                    "-ar", "48000", "-c:a", "pcm_s24le", brute], check=True)
    aigus = sortie[:-4] + "-aigus.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brute, "-af", "highpass=f=250,highpass=f=250", "-c:a", "pcm_s24le", aigus], check=True)
    tout, haut = _lufs(brute), _lufs(aigus)
    gains = [NIVEAU_MUSIQUE_AIGUS - haut if haut is not None and haut > -70 else None,
             NIVEAU_MUSIQUE_MAX - tout if tout is not None and tout > -70 else None]
    gain = min([g for g in gains if g is not None], default=0.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brute, "-af", f"volume={gain:.2f}dB", "-ar", "48000", "-c:a", "pcm_s24le", sortie],
                   check=True)
    os.remove(brute)
    os.remove(aigus)
    return sortie


def assembler(video_muette, voix, bruitages, sortie, dossier_travail, musique=None):
    """La vidéo finale : l'image muette + la voix + les bruitages et la musique baissés sous la voix, au niveau visé, en AAC 48 kHz."""
    pistes = [p for p in (voix, bruitages, musique) if p]
    if not pistes:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video_muette, "-c", "copy", sortie], check=True)
        return sortie
    melange = os.path.join(dossier_travail, "melange.wav")
    entrees, filtres, a_mixer, extra = [], [], [], []
    for p in pistes:
        entrees += ["-i", p]
    k = 0
    if voix:
        cles = (1 if bruitages else 0) + (1 if musique else 0)
        filtres.append(f"[0:a]asplit={cles + 1}[vx]" + "".join(f"[cle{c}]" for c in range(cles)) if cles else "[0:a]anull[vx]")
        a_mixer.append("[vx]")
        k = 1
    c = 0
    if bruitages:
        if voix:
            filtres.append(f"[{k}:a][cle{c}]sidechaincompress=threshold=0.03:ratio=8:attack=8:release=280:makeup=1,asplit=2[sfx][sfx_seuls]")
            extra = ["-map", "[sfx_seuls]", "-ar", "48000", "-c:a", "pcm_s24le", os.path.join(dossier_travail, "bruitages-sous-voix.wav")]
            c += 1
        else:
            filtres.append(f"[{k}:a]anull[sfx]")
        a_mixer.append("[sfx]")
        k += 1
    if musique:
        if voix:      # la musique baisse d'environ 4 dB quand la voix parle, et remonte doucement entre les phrases
            filtres.append(f"[{k}:a][cle{c}]sidechaincompress=threshold=0.02:ratio=3:attack=30:release=600:makeup=1[mus]")
        else:
            filtres.append(f"[{k}:a]anull[mus]")
        a_mixer.append("[mus]")
    filtres.append("".join(a_mixer) + f"amix=inputs={len(a_mixer)}:normalize=0[o]" if len(a_mixer) > 1 else f"{a_mixer[0]}anull[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", ";".join(filtres), "-map", "[o]", "-ar", "48000",
                    "-c:a", "pcm_s24le", melange, *extra], check=True)
    mesure = _lufs(melange)
    vise = NIVEAU_VISE if voix else NIVEAU_SANS_VOIX
    gain = (vise - mesure) if mesure is not None and mesure > -70 else 0.0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video_muette, "-i", melange, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", sortie], check=True)
    return sortie
