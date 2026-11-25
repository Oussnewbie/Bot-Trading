"""La voix off : ElevenLabs (le clone de ta voix), une réplique par scène, avec l'heure de chaque mot pour caler l'image dessus.

La clé n'est jamais dans le dépôt ni dans une commande : elle est lue dans un fichier privé (`cle_elevenlabs` de la configuration,
par défaut ~/.config/elevenlabs/cle) et passée à curl par un fichier d'en-têtes temporaire lisible par toi seul. Chaque réplique est
gardée en cache (même texte, même voix, même modèle = même fichier) : refaire une vidéo ne recoûte rien, et une prise validée ne
change pas. Le Python de python.org n'a pas toujours ses certificats : l'appel passe par curl.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile

# Les réglages de la vidéo de présentation, que tu as validée. Plus d'intonation (stability plus basse, style plus haut) faisait
# changer la voix d'une réplique à l'autre. Le réglage « speed » d'ElevenLabs n'a aucun effet sur eleven_v4 (même durée à 1,0 et
# 1,2, mesuré le 25/11/2026) : le rythme se règle après coup (rythmer). La graine rend une prise reproductible.
REGLAGES = {"stability": 0.45, "similarity_boost": 0.85, "style": 0.25, "use_speaker_boost": True}
GRAINE = 2604
TEMPO, PAUSE_MAX = 1.1, 0.3      # la voix 10 % plus rapide (même hauteur), aucun silence de plus de 0,3 s entre deux mots


class VoixIndisponible(Exception):
    pass


def mots_horodates(alignement):
    """Les mots d'une réplique avec leur début et leur fin (s), à partir de l'heure de chaque caractère rendue par ElevenLabs."""
    mots, courant, debut, fin = [], "", None, None
    for c, d, f in zip(alignement.get("characters", []), alignement.get("character_start_times_seconds", []),
                       alignement.get("character_end_times_seconds", [])):
        if c.isspace():
            if courant:
                mots.append({"mot": courant, "debut": round(debut, 3), "fin": round(fin, 3)})
            courant, debut = "", None
            continue
        if debut is None:
            debut = d
        courant += c
        fin = f
    if courant:
        mots.append({"mot": courant, "debut": round(debut, 3), "fin": round(fin, 3)})
    return mots


def duree(chemin):
    sortie = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", chemin],
                            capture_output=True, text=True)
    return float(sortie.stdout.strip() or 0)


def replique(texte, config, avant="", apres=""):
    """Le fichier MP3 de la réplique et ses mots horodatés : {"fichier", "duree", "mots"}. Depuis le cache si elle existe déjà."""
    voix_id, modele = config.get("voix_id"), config.get("modele_voix", "eleven_v4")
    if not voix_id:
        raise VoixIndisponible("Pas de voix_id dans la configuration : la vidéo sera faite sans voix.")
    cache = os.path.expanduser(config.get("cache_voix", "~/.cache/etrave-video/voix"))
    os.makedirs(cache, exist_ok=True)
    graine = int(config.get("voix_graine", GRAINE))
    empreinte = hashlib.sha256(json.dumps([voix_id, modele, texte, avant, apres, REGLAGES, graine], ensure_ascii=False).encode()).hexdigest()[:20]
    mp3, meta = os.path.join(cache, empreinte + ".mp3"), os.path.join(cache, empreinte + ".json")
    if os.path.exists(mp3) and os.path.exists(meta):
        return json.load(open(meta, encoding="utf-8"))
    chemin_cle = os.path.expanduser(config.get("cle_elevenlabs", "~/.config/elevenlabs/cle"))
    if not os.path.exists(chemin_cle):
        raise VoixIndisponible(f"Clé ElevenLabs introuvable ({chemin_cle}) : la vidéo sera faite sans voix.")
    cle = open(chemin_cle, encoding="utf-8").read().strip()
    corps = {"text": texte, "model_id": modele, "voice_settings": REGLAGES, "seed": graine}
    if avant:
        corps["previous_text"] = avant
    if apres:
        corps["next_text"] = apres
    descripteur, entetes = tempfile.mkstemp(prefix="entetes-", text=True)     # créé en 600 : lisible par toi seul
    try:
        with os.fdopen(descripteur, "w") as f:
            f.write(f"xi-api-key: {cle}\n")
        sortie = subprocess.run(
            ["curl", "-sS", "--max-time", "120", "-X", "POST", "-H", f"@{entetes}", "-H", "Content-Type: application/json",
             "-H", "Accept: application/json", "-w", "\n%{http_code}", "--data-binary", "@-",
             f"https://api.elevenlabs.io/v1/text-to-speech/{voix_id}/with-timestamps?output_format=mp3_44100_128"],
            input=json.dumps(corps).encode("utf-8"), capture_output=True)
    finally:
        os.remove(entetes)
    reponse, _, code = sortie.stdout.rpartition(b"\n")
    if code.strip() != b"200":
        raise VoixIndisponible(f"ElevenLabs a refusé la réplique ({code.decode().strip() or 'pas de réponse'}) : "
                               f"{reponse[:200].decode('utf-8', 'replace')}")
    donnees = json.loads(reponse)
    with open(mp3, "wb") as f:
        f.write(base64.b64decode(donnees["audio_base64"]))
    resultat = {"fichier": mp3, "duree": round(duree(mp3), 3), "mots": mots_horodates(donnees.get("alignment") or {}), "texte": texte}
    json.dump(resultat, open(meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return resultat


SEPARATEUR = "\n\n"


def recit(textes, config):
    """Toutes les répliques d'une vidéo en UNE demande à ElevenLabs, puis coupées scène par scène. Des demandes séparées donnent
    des prises dont le timbre change un peu d'une scène à l'autre ; une seule prise garde la même voix du début à la fin, et
    l'intonation suit le fil du texte. Rend une réplique par scène ({"fichier", "duree", "mots", "texte"}), comme replique()."""
    complet = replique(SEPARATEUR.join(textes), config)
    mots = complet["mots"]
    comptes = [len(t.split()) for t in textes]
    if sum(comptes) != len(mots):
        raise VoixIndisponible(f"La prise unique ne retrouve pas les mots des scènes ({len(mots)} mots lus, {sum(comptes)} attendus).")
    debuts = [sum(comptes[:i]) for i in range(len(textes))]
    total = complet["duree"]
    trous = silences(complet["fichier"])
    coupes = [0.0]
    for i in range(1, len(textes)):
        fin_avant, debut = mots[debuts[i] - 1]["debut"], mots[debuts[i]]["debut"]
        # le silence entre les deux scènes (le dernier qui finit avant le premier mot de la scène suivante), coupé en son milieu
        dans = [(d, f) for d, f in trous if f is not None and d >= fin_avant and f <= debut + 0.08]
        coupes.append((dans[-1][0] + dans[-1][1]) / 2 if dans else max(fin_avant, debut - 0.06))
    coupes.append(total)
    base, _ = os.path.splitext(complet["fichier"])
    reps = []
    for i, t in enumerate(textes):
        d, f = coupes[i], coupes[i + 1]
        sortie = f"{base}-s{i}.wav"
        if not os.path.exists(sortie):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", complet["fichier"], "-af",
                            f"atrim=start={d:.3f}:end={f:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,areverse,afade=t=in:d=0.02,areverse",
                            "-ar", "44100", "-c:a", "pcm_s16le", sortie], check=True)
        reps.append({"fichier": sortie, "duree": round(f - d, 3), "texte": t,
                     "mots": [dict(m, debut=round(m["debut"] - d, 3), fin=round(m["fin"] - d, 3))
                              for m in mots[debuts[i]:debuts[i] + comptes[i]]]})
    return reps


def silences(fichier, seuil_db=-40, duree_min=0.18):
    """Les silences d'un fichier [(début, fin)], lus par ffmpeg (silencedetect). Les heures des mots d'ElevenLabs comptent le silence
    qui suit un point dans le mot lui-même : on ne peut pas s'en servir pour trouver les pauses."""
    sortie = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", fichier, "-af", f"silencedetect=noise={seuil_db}dB:d={duree_min}",
                             "-f", "null", "-"], capture_output=True, text=True).stderr
    debuts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", sortie)]
    fins = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", sortie)]
    return [(max(0.0, d), f) for d, f in zip(debuts, fins + [None] * (len(debuts) - len(fins)))]


def rythmer(rep, tempo=TEMPO, pause_max=PAUSE_MAX):
    """La réplique plus vive : chaque silence ramené à pause_max (on coupe son milieu : la fin du mot et la prise d'air avant le
    suivant restent), le silence du début et de la fin retiré, puis la voix accélérée par `tempo` sans changer sa hauteur (atempo).
    Les heures des mots suivent. Le fichier est gardé à côté de la réplique : rien n'est redemandé à ElevenLabs."""
    if not rep or (tempo == 1 and not pause_max):
        return rep
    total = rep["duree"]
    coupes = []                 # (début, fin) des morceaux de silence retirés
    for d, f in silences(rep["fichier"]):
        if d <= 0.02:                                   # silence du début
            coupes.append((0.0, max(0.0, (f or total) - 0.05)))
        elif f is None or f >= total - 0.02:            # silence de la fin
            coupes.append((d + 0.12, total))
        elif pause_max and f - d > pause_max:
            coupes.append((d + pause_max / 2, f - pause_max / 2))
    coupes = [(d, f) for d, f in coupes if f - d > 0.01]

    def apres(t):
        retire = sum(min(f, t) - d for d, f in coupes if d < t)
        return max(0.0, t - retire) / tempo
    base, _ = os.path.splitext(rep["fichier"])
    sortie = f"{base}-t{tempo:g}-p{pause_max:g}.wav"
    if not os.path.exists(sortie):
        gardes, t = [], 0.0
        for d, f in coupes:
            if d > t:
                gardes.append((t, d))
            t = f
        if t < total - 0.01:
            gardes.append((t, None))
        filtres = []
        for i, (d, f) in enumerate(gardes):
            fin = f":end={f:.3f}" if f is not None else ""
            filtres.append(f"[0:a]atrim=start={d:.3f}{fin},asetpts=PTS-STARTPTS,afade=t=in:d=0.006,"
                           f"areverse,afade=t=in:d=0.006,areverse[g{i}]")
        filtres.append("".join(f"[g{i}]" for i in range(len(gardes))) + f"concat=n={len(gardes)}:v=0:a=1,atempo={tempo:.4f}[o]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", rep["fichier"], "-filter_complex", ";".join(filtres), "-map", "[o]",
                        "-ar", "44100", "-c:a", "pcm_s16le", sortie], check=True)
    return dict(rep, fichier=sortie, duree=round(duree(sortie), 3),
                mots=[dict(m, debut=round(apres(m["debut"]), 3), fin=round(apres(m["fin"]), 3)) for m in rep["mots"]])


def instant(rep, *cherches, defaut=None):
    """Le début (s, dans la réplique) du premier mot qui commence par l'un des mots cherchés (sans majuscule ni ponctuation)."""
    for m in (rep or {}).get("mots", []):
        mot = m["mot"].lower().strip(".,:;!?…«»\"'")
        if any(mot.startswith(c.lower()) for c in cherches):
            return m["debut"]
    return defaut
