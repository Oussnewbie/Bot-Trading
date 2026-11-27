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
import time

# Les réglages de la vidéo de présentation, que tu as validée. Plus d'intonation (stability plus basse, style plus haut) faisait
# changer la voix d'une réplique à l'autre. Le réglage « speed » d'ElevenLabs n'a aucun effet sur eleven_v4 (même durée à 1,0 et
# 1,2, mesuré le 25/11/2026) : le rythme se règle après coup (rythmer). La graine rend une prise reproductible.
REGLAGES = {"stability": 0.45, "similarity_boost": 0.85, "style": 0.25, "use_speaker_boost": True}
GRAINE = 2604
TEMPO, PAUSE_MAX = 1.1, 0.3      # la voix 10 % plus rapide (même hauteur), aucun silence de plus de 0,3 s entre deux mots


class VoixIndisponible(Exception):
    pass


# VID-18 à VID-21 (25/11/2026, « voix absolument ») : jamais de vidéo muette, et chaque panne de la voix dit sa cause et ce qu'il faut
# faire. Seules les pannes passagères (pas de réponse, 429, 5xx) sont réessayées tout de suite : chaque essai peut coûter des
# crédits. Une clé refusée, des crédits épuisés ou une voix introuvable ne guérissent pas seuls.
ATTENTES = (10, 30)      # secondes d'attente avant le 2e et le 3e essai d'une panne passagère
CAUSES = {
    "quota_exceeded": "crédits ElevenLabs épuisés pour ce mois-ci : attendre le renouvellement ou prendre l'offre au-dessus",
    "invalid_api_key": "clé ElevenLabs refusée : écrire une nouvelle clé dans le fichier de la clé",
    "missing_permissions": "la clé ElevenLabs n'a pas le droit « Text to Speech » : créer une clé avec ce droit",
    "voice_not_found": "voix introuvable chez ElevenLabs : vérifier voix_id dans la configuration",
    "payment_required": "abonnement ElevenLabs à régler",
    "detected_unusual_activity": "ElevenLabs a bloqué le compte (activité inhabituelle) : voir le site d'ElevenLabs",
    "too_many_concurrent_requests": "trop de demandes en même temps chez ElevenLabs",
    "system_busy": "ElevenLabs est surchargé",
}


def passagere(code):
    """Une panne qui peut guérir seule : pas de réponse (réseau), 429 (trop de demandes), 5xx (panne chez ElevenLabs)."""
    return code in ("", "000", "429") or code.startswith("5")


def cause(code, corps=b"", erreur=b""):
    """La raison d'un échec d'ElevenLabs en mots simples, avec ce qu'il faut faire, puis le code et le message d'origine."""
    if code in ("", "000"):
        lignes = erreur.decode("utf-8", "replace").strip().splitlines()
        return f"pas de réponse d'ElevenLabs, connexion Internet ? [{(lignes[-1] if lignes else 'aucune réponse')[:160]}]"
    statut, message = "", ""
    try:
        detail = json.loads(corps).get("detail")
        if isinstance(detail, dict):
            statut, message = str(detail.get("status") or ""), str(detail.get("message") or "")
        elif detail is not None:
            message = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
    except (ValueError, AttributeError):
        message = corps[:160].decode("utf-8", "replace")
    simple = CAUSES.get(statut) or {"401": "clé ElevenLabs refusée : écrire une nouvelle clé dans le fichier de la clé",
                                    "402": CAUSES["payment_required"],
                                    "429": "trop de demandes chez ElevenLabs"}.get(code)
    if not simple:
        simple = "panne chez ElevenLabs" if code.startswith("5") else "ElevenLabs a refusé la demande"
    return f"{simple} [HTTP {code}{', ' + statut if statut else ''}{' : ' + message[:160] if message else ''}]"


def _cle(config):
    chemin = os.path.expanduser(config.get("cle_elevenlabs", "~/.config/elevenlabs/cle"))
    if not os.path.exists(chemin):
        raise VoixIndisponible(f"clé ElevenLabs introuvable ({chemin}) : y écrire la clé seule, puis chmod 600")
    return open(chemin, encoding="utf-8").read().strip()


def appeler(url, cle, corps=None):
    """Un appel à ElevenLabs par curl (POST JSON si `corps`, sinon GET). Rend (code HTTP en texte, réponse, erreur de curl)."""
    descripteur, entetes = tempfile.mkstemp(prefix="entetes-", text=True)     # créé en 600 : lisible par toi seul
    try:
        with os.fdopen(descripteur, "w") as f:
            f.write(f"xi-api-key: {cle}\n")
        commande = ["curl", "-sS", "--max-time", "120", "-H", f"@{entetes}", "-H", "Accept: application/json", "-w", "\n%{http_code}"]
        if corps is not None:
            commande += ["-X", "POST", "-H", "Content-Type: application/json", "--data-binary", "@-"]
        sortie = subprocess.run(commande + [url], input=None if corps is None else json.dumps(corps).encode("utf-8"),
                                capture_output=True, timeout=150)
    finally:
        os.remove(entetes)
    reponse, _, code = (sortie.stdout or b"").rpartition(b"\n")
    return code.strip().decode("ascii", "replace"), reponse, sortie.stderr or b""


def _ecrire(chemin, donnees, binaire):
    """Écrit sous un nom provisoire puis renomme : un arrêt en cours d'écriture ne laisse jamais un fichier tronqué dans le cache."""
    provisoire = chemin + ".part"
    with open(provisoire, "wb" if binaire else "w", **({} if binaire else {"encoding": "utf-8"})) as f:
        if binaire:
            f.write(donnees)
        else:
            json.dump(donnees, f, ensure_ascii=False, indent=1)
    os.replace(provisoire, chemin)


def _ffmpeg(arguments, sortie):
    """ffmpeg vers un nom provisoire, puis renommé (VID-21 : un ffmpeg arrêté laissait une voix tronquée, reprise telle quelle)."""
    provisoire = sortie[:-4] + ".part.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + arguments + [provisoire], check=True, timeout=300)
    if not os.path.exists(provisoire) or duree(provisoire) < 0.2:
        if os.path.exists(provisoire):
            os.remove(provisoire)
        raise VoixIndisponible(f"morceau de voix vide après ffmpeg ({os.path.basename(sortie)})")
    os.replace(provisoire, sortie)


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
                            capture_output=True, text=True, timeout=60)
    return float(sortie.stdout.strip() or 0)


def replique(texte, config, avant="", apres=""):
    """Le fichier MP3 de la réplique et ses mots horodatés : {"fichier", "duree", "mots"}. Depuis le cache si elle existe déjà."""
    voix_id, modele = config.get("voix_id"), config.get("modele_voix", "eleven_v4")
    if not voix_id:
        raise VoixIndisponible("pas de voix_id dans la configuration (l'identifiant du clone de ta voix chez ElevenLabs)")
    cache = os.path.expanduser(config.get("cache_voix", "~/.cache/etrave-video/voix"))
    os.makedirs(cache, exist_ok=True)
    graine = int(config.get("voix_graine", GRAINE))
    empreinte = hashlib.sha256(json.dumps([voix_id, modele, texte, avant, apres, REGLAGES, graine], ensure_ascii=False).encode()).hexdigest()[:20]
    mp3, meta = os.path.join(cache, empreinte + ".mp3"), os.path.join(cache, empreinte + ".json")
    if os.path.exists(mp3) and os.path.exists(meta):
        with open(meta, encoding="utf-8") as f:
            return json.load(f)
    cle = _cle(config)
    corps = {"text": texte, "model_id": modele, "voice_settings": REGLAGES, "seed": graine}
    if avant:
        corps["previous_text"] = avant
    if apres:
        corps["next_text"] = apres
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voix_id}/with-timestamps?output_format=mp3_44100_128"
    for essai in range(len(ATTENTES) + 1):
        code, reponse, erreur = appeler(url, cle, corps)
        if code == "200" or not passagere(code) or essai == len(ATTENTES):
            break
        time.sleep(ATTENTES[essai])
    if code != "200":
        raise VoixIndisponible(cause(code, reponse, erreur) + (f" ({essai + 1} essais)" if essai else ""))
    # VID-20 : une réponse 200 illisible ou sans l'heure des mots levait KeyError (pas de notification) ou entrait dans le cache, et
    # chaque lancement suivant échouait sur la même prise. Elle est vérifiée avant d'être gardée.
    try:
        donnees = json.loads(reponse)
        audio = base64.b64decode(donnees["audio_base64"])
    except (ValueError, KeyError, TypeError) as err:
        raise VoixIndisponible(f"réponse d'ElevenLabs illisible ({type(err).__name__}) : nouvel essai au prochain lancement")
    mots = mots_horodates(donnees.get("alignment") or {})
    if not audio or not mots:
        raise VoixIndisponible("ElevenLabs a rendu une prise vide ou sans l'heure des mots : nouvel essai au prochain lancement")
    _ecrire(mp3 + ".mp3", audio, True)            # le .mp3 provisoire garde une extension que ffprobe reconnaît
    if duree(mp3 + ".mp3") < 0.2:
        os.remove(mp3 + ".mp3")
        raise VoixIndisponible("ElevenLabs a rendu un fichier son illisible : nouvel essai au prochain lancement")
    os.replace(mp3 + ".mp3", mp3)
    resultat = {"fichier": mp3, "duree": round(duree(mp3), 3), "mots": mots, "texte": texte}
    _ecrire(meta, resultat, False)
    return resultat


def controle_compte(config):
    """Pour `outil.py verifier` : la clé et la voix marchent-elles, et combien de caractères restent ce mois-ci ? Deux lectures
    gratuites (aucun crédit dépensé). Rend une liste de (bon, texte)."""
    try:
        cle = _cle(config)
    except VoixIndisponible as err:
        return [(False, str(err))]
    res = []
    code, reponse, erreur = appeler(f"https://api.elevenlabs.io/v1/voices/{config.get('voix_id')}", cle)
    res.append((code == "200", "voix trouvée chez ElevenLabs" if code == "200" else "voix : " + cause(code, reponse, erreur)))
    code, reponse, erreur = appeler("https://api.elevenlabs.io/v1/user/subscription", cle)
    if code == "200":
        try:
            d = json.loads(reponse)
            reste = int(d["character_limit"]) - int(d["character_count"])
            res.append((reste > 3000, f"crédits ElevenLabs : {reste} caractères restants ce mois-ci (une vidéo en prend environ 1 000)"))
        except (ValueError, KeyError, TypeError):
            res.append((True, "crédits ElevenLabs : réponse illisible (sans gravité pour la voix)"))
    elif "missing_permissions" in reponse.decode("utf-8", "replace"):
        res.append((True, "crédits ElevenLabs : la clé n'a pas le droit de lire le compte (sans gravité pour la voix)"))
    else:
        res.append((False, "crédits : " + cause(code, reponse, erreur)))
    return res


SEPARATEUR = "\n\n"


def recit(textes, config):
    """Toutes les répliques d'une vidéo en UNE demande à ElevenLabs, puis coupées scène par scène. Des demandes séparées donnent
    des prises dont le timbre change un peu d'une scène à l'autre ; une seule prise garde la même voix du début à la fin, et
    l'intonation suit le fil du texte. Rend une réplique par scène ({"fichier", "duree", "mots", "texte"}), comme replique()."""
    complet = replique(SEPARATEUR.join(textes), config)
    mots = complet["mots"]
    comptes = [len(t.split()) for t in textes]
    if not all(comptes):
        raise VoixIndisponible("une scène n'a pas de texte à lire : à corriger dans l'outil (repliques)")
    if sum(comptes) != len(mots):
        # VID-21 : la prise était gardée dans le cache et chaque lancement échouait sur elle. Elle est mise de côté (« -ecart ») et
        # une seule nouvelle prise est demandée ; si l'écart revient, la prise reste (pas de crédits dépensés à chaque lancement).
        base = os.path.splitext(complet["fichier"])[0]
        ecart = f"{len(mots)} mots lus pour {sum(comptes)} écrits"
        if os.path.exists(base + "-ecart.json"):
            raise VoixIndisponible(f"la voix ne retrouve pas le texte des scènes ({ecart}), deux prises de suite : à corriger dans "
                                   f"l'outil (voix.recit) ; prises gardées dans {os.path.dirname(base)}")
        for ext in (".mp3", ".json"):
            os.replace(base + ext, base + "-ecart" + ext)
        raise VoixIndisponible(f"la voix ne retrouve pas le texte des scènes ({ecart}) : nouvelle prise au prochain lancement")
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
            _ffmpeg(["-i", complet["fichier"], "-af",
                     f"atrim=start={d:.3f}:end={f:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,areverse,afade=t=in:d=0.02,areverse",
                     "-ar", "44100", "-c:a", "pcm_s16le"], sortie)
        reps.append({"fichier": sortie, "duree": round(f - d, 3), "texte": t,
                     "mots": [dict(m, debut=round(m["debut"] - d, 3), fin=round(m["fin"] - d, 3))
                              for m in mots[debuts[i]:debuts[i] + comptes[i]]]})
    return reps


def purger_cache(config, jours=30, journal=print):
    """V-08 (audit du 27/11/2026) : le cache des voix grossissait sans fin (116 Mo pour une dizaine d'essais). Les morceaux WAV
    recalculables (coupe par scène « -s0.wav », rythme « -t1.1-p0.3.wav ») de plus de `jours` jours sont effacés ; les prises payées
    (MP3 et heures des mots) restent : refaire une vieille vidéo ne recoûte rien."""
    import re
    cache = os.path.expanduser(config.get("cache_voix", "~/.cache/etrave-video/voix"))
    if not os.path.isdir(cache):
        return []
    limite, effaces = time.time() - jours * 86400, []
    for nom in os.listdir(cache):
        chemin = os.path.join(cache, nom)
        if re.search(r"-s\d+(-t[\d.]+-p[\d.]+)?\.wav$", nom) and os.path.getmtime(chemin) < limite:
            try:
                os.remove(chemin)
                effaces.append(nom)
            except OSError as err:
                journal(f"Cache des voix : {nom} pas effacé ({err})")
    return effaces


def controle_pistes(reps):
    """VID-18 : le dernier contrôle avant le montage. Chaque scène a son fichier de voix, d'une durée plausible ; sinon pas de vidéo."""
    for i, r in enumerate(reps):
        if not r or not os.path.exists(r.get("fichier", "")) or r.get("duree", 0) < 0.2:
            raise VoixIndisponible(f"la voix de la scène {i + 1} manque ou est vide")


def silences(fichier, seuil_db=-40, duree_min=0.18):
    """Les silences d'un fichier [(début, fin)], lus par ffmpeg (silencedetect). Les heures des mots d'ElevenLabs comptent le silence
    qui suit un point dans le mot lui-même : on ne peut pas s'en servir pour trouver les pauses."""
    sortie = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", fichier, "-af", f"silencedetect=noise={seuil_db}dB:d={duree_min}",
                             "-f", "null", "-"], capture_output=True, text=True, timeout=300).stderr
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
        _ffmpeg(["-i", rep["fichier"], "-filter_complex", ";".join(filtres), "-map", "[o]", "-ar", "44100", "-c:a", "pcm_s16le"], sortie)
    return dict(rep, fichier=sortie, duree=round(duree(sortie), 3),
                mots=[dict(m, debut=round(apres(m["debut"]), 3), fin=round(apres(m["fin"]), 3)) for m in rep["mots"]])


def instant(rep, *cherches, defaut=None, apres=None):
    """Le début (s, dans la réplique) du premier mot qui commence par l'un des mots cherchés (sans majuscule ni ponctuation) ;
    avec `apres`, seulement parmi les mots qui commencent à cet instant ou après (le petit mot peut dire « demain » avant la fin)."""
    for m in (rep or {}).get("mots", []):
        if apres is not None and m["debut"] < apres:
            continue
        mot = m["mot"].lower().strip(".,:;!?…«»\"'")
        if any(mot.startswith(c.lower()) for c in cherches):
            return m["debut"]
    return defaut
