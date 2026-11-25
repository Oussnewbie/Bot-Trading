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
import subprocess
import tempfile

# Une voix qui a de l'énergie : moins stable (plus d'intonation), plus de style, un débit un peu plus rapide (1 = normal, 1,2 au plus)
REGLAGES = {"stability": 0.32, "similarity_boost": 0.85, "style": 0.45, "use_speaker_boost": True, "speed": 1.08}


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
    empreinte = hashlib.sha256(json.dumps([voix_id, modele, texte, avant, apres, REGLAGES], ensure_ascii=False).encode()).hexdigest()[:20]
    mp3, meta = os.path.join(cache, empreinte + ".mp3"), os.path.join(cache, empreinte + ".json")
    if os.path.exists(mp3) and os.path.exists(meta):
        return json.load(open(meta, encoding="utf-8"))
    chemin_cle = os.path.expanduser(config.get("cle_elevenlabs", "~/.config/elevenlabs/cle"))
    if not os.path.exists(chemin_cle):
        raise VoixIndisponible(f"Clé ElevenLabs introuvable ({chemin_cle}) : la vidéo sera faite sans voix.")
    cle = open(chemin_cle, encoding="utf-8").read().strip()
    corps = {"text": texte, "model_id": modele, "voice_settings": REGLAGES}
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


def instant(rep, *cherches, defaut=None):
    """Le début (s, dans la réplique) du premier mot qui commence par l'un des mots cherchés (sans majuscule ni ponctuation)."""
    for m in (rep or {}).get("mots", []):
        mot = m["mot"].lower().strip(".,:;!?…«»\"'")
        if any(mot.startswith(c.lower()) for c in cherches):
            return m["debut"]
    return defaut
