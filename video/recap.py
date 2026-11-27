"""La vidéo récap d'une séance : le titre (la date et la couleur de la journée), une scène par marché, puis le bilan. Même habillage
que la présentation : la carte marine d'Étrave, DIN, bleu du logo.

Une scène de marché : le graphique M5 du jour se dessine, la zone de 15:30 apparaît, puis la caméra s'arrête sur chaque moment qui
compte, chacun sur le mot de la voix qui le dit :
- la cassure et l'entrée (« casse », « vend » / « achète ») ;
- les stops touchés (« stop ») ;
- les sorties de fin de séance (« fin »).
À chaque arrêt, la bougie est surlignée, une onde part du point et une étiquette dit ce qui se passe. Puis la caméra recule et le
résultat compte jusqu'à sa valeur, en vert pour un gain et en rouge pour une perte. Le vert et le rouge ne servent qu'au résultat
(R, ronds de sortie, étiquettes des sorties, total) ; le jaune surligne la cassure ; le bleu et l'encre disent achat et vente.

Tout se cale sur la voix : la durée de chaque scène vient de la durée de sa réplique, et chaque mouvement tombe sur le mot qui le dit
(heure de chaque mot rendue par ElevenLabs). Sans voix, des durées fixes.

Ce qui reste secret ne sort pas : ni le type d'entrée (seulement « Achat » ou « Vente »), ni les filtres, ni la raison d'un jour
sans trade. Aucune mention démo, réel ou testeur dans la vidéo ni dans le nom de ses fichiers : seule la description de la
publication le dit (publication.py).
"""
import datetime
import html
import json
import os
import shutil
import subprocess

import mixage
import nombres
import police
import voix

ICI = os.path.dirname(os.path.abspath(__file__))
# Correctif VID-01 (audit du 25/11/2026) : le chemin complet de npx. Sous Windows, npx est un « npx.cmd » que subprocess ne trouve
# pas sous le nom « npx » (seuls les .exe le sont) : chaque rendu échouait sur le VPS.
HYPERFRAMES = [shutil.which("npx") or "npx", "-y", "hyperframes@0.9.94"]
# Zones sûres de TikTok en 1080 x 1920 (celles du contrôle HyperFrames) : le texte entre y = 240 et y = 1260 ; jusqu'à x = 960 au-dessus
# de y = 840 ; sous y = 840, rien à droite de x = 780 (les boutons j'aime, commentaires, partage). Le graphique tient au-dessus de 840.
# V-14 (audit du 27/11/2026) : le graphique faisait 850 x 340 px, la moitié basse de l'écran restait vide presque toute la scène.
# Il fait 850 x 440 px (la date et le nom du marché remontent, la légende passe dans la ligne de la date) ; dessous, les sous-titres
# (calés sur les mots de la voix), puis le résumé et le résultat.
X0, X1, Y_HAUT, Y_BAS = 100, 950, 400, 840          # le graphique
Y_SOUS_TITRES = Y_BAS + 64                           # le haut des sous-titres (deux lignes de 40 px au plus)
Y_RESUME = Y_BAS + 176                               # les pastilles du résumé, puis le résultat
X_DROITE, X_DROITE_BAS, Y_FIN = 960, 780, 1260       # bords des zones sûres
X_GAUCHE = 120                                       # le bord gauche de la zone sûre de TikTok (check HyperFrames : 80 px sur 720)
# VID-26 (audit du 26/11/2026) : la dernière bougie finissait sur le bord droit, et les ronds des sorties de 21:50 (rayon 11, décalés
# de 7 quand un vert et un rouge se partagent l'endroit) étaient coupés à moitié par le cadre. Les bougies s'arrêtent avant.
GOUTTIERE = 22
# VID-31 (26/11/2026, choix de l'utilisateur) : le vert et le rouge sont réservés au résultat. Le chemin du prix (« Jusqu'à +106 pts »,
# trait et point) était vert même un jour perdant, et l'épingle des photos rouge même un jour gagnant : ils sont bleus (le bleu d'Étrave).
COUL_CHEMIN = "#2f7bd9"
ZOOM = 2.2                                           # la caméra sur une bougie
ARRET = 1.5                                          # durée minimale d'un arrêt de la caméra (le temps de lire l'étiquette)
COUL = {"papier": "#f6f8fa", "eau": "#e2edf5", "grille": "#dde4ea", "axe": "#94a3b2", "encre": "#18222e", "encre2": "#46546a",
        "bleu": "#2f7bd9", "vert": "#16a05a", "rouge": "#e23a3f", "jaune": "#ffd23f", "blanc": "#ffffff"}
POLICE_CSS = '@font-face { font-family: "DIN Etrave"; src: url("assets/fonts/din-alternate-bold.ttf") format("truetype"); font-weight: 700; }'
OUTILS_JS = """const wipe = (cible, t, d = 0.3) => tl.fromTo(cible, { clipPath: "inset(-30% 100% -40% 0)" }, { clipPath: "inset(-30% 0% -40% 0)", duration: d, ease: "power3.out" }, t);
    const pop = (cible, t, d = 0.34, o = "50% 50%") => tl.fromTo(cible, { opacity: 0, scale: 0.5, transformOrigin: o }, { opacity: 1, scale: 1, duration: d, ease: "back.out(2.4)" }, t);
    const nb = (v, d) => (v <= -0.5 * 10 ** -d ? "−" : v >= 0.5 * 10 ** -d ? "+" : "") + Math.abs(v).toFixed(d).replace(".", ",");
    const compte = (cible, fin, d, suffixe, t, duree = 0.8) => { const el = document.querySelector(cible); const o = { v: 0 };
      tl.to(o, { v: fin, duration: duree, ease: "power2.out", onUpdate: () => { el.textContent = nb(o.v, d) + suffixe; } }, t); };"""
V_ETRAVE = "M8 8c1.8 9.5 5.8 17.5 12 24 6.2-6.5 10.2-14.5 12-24"
TIGE, VAGUES = "M20 5v27", "M3 33c2.8-2.3 5.7-2.3 8.5 0M28.5 33c2.8-2.3 5.7-2.3 8.5 0"
POLICE = police.DEFAUT        # le fichier de la police, pour mesurer les textes (réglé par fabriquer)


class CommandeBloquee(RuntimeError):
    """V-06 : un rendu HyperFrames ou un ffmpeg qui dépasse son délai, arrêté (le mode automatique prévient et réessaie plus tard)."""


# V-24 (audit du 27/11/2026) : la CLI HyperFrames 0.9.94 contient une télémétrie (PostHog) et cherche ses mises à jour ; coupées pour
# chaque rendu (et dans l'agent launchd, installation.py).
ENV_HYPERFRAMES = {"HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1", "DO_NOT_TRACK": "1"}
# V-06 (audit du 27/11/2026) : aucun délai sur le rendu ni sur ffmpeg ; un Chrome sans tête bloqué gardait la tâche launchd « en
# cours » et les lancements suivants n'avaient pas lieu. Un rendu de 60 s prend 1 à 2 minutes : 15 minutes, c'est une panne.
DELAI_RENDU, DELAI_IMAGE = 15 * 60, 5 * 60


def executer(commande, dossier, delai, quoi):
    """Une commande longue (rendu HyperFrames : npx, node, puis Chrome sans tête) avec un délai. À l'expiration, tout le groupe de
    processus est arrêté (Chrome compris, que `subprocess.run(timeout=…)` laisserait tourner) et CommandeBloquee est levée. Une
    sortie en erreur lève CalledProcessError avec la fin de ce que la commande a écrit."""
    env = dict(os.environ, **ENV_HYPERFRAMES)
    options = {"start_new_session": True} if os.name != "nt" else {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    p = subprocess.Popen(commande, cwd=dossier, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **options)
    try:
        sortie, _ = p.communicate(timeout=delai)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            import signal
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
        else:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, timeout=30)
        p.communicate()
        raise CommandeBloquee(f"{quoi} bloqué plus de {delai // 60 if delai >= 60 else delai} {'min' if delai >= 60 else 's'} : arrêté")
    if p.returncode:
        fin = (sortie or b"").decode("utf-8", "replace").strip().splitlines()[-6:]
        raise subprocess.CalledProcessError(p.returncode, commande, output="\n".join(fin))
    return sortie


def e(texte):
    return html.escape(str(texte), quote=True)


# ───────────────────────── les bruitages ─────────────────────────
# V-16, V-17 (audit du 27/11/2026) : earshot jugeait click-select-1109 et sweep-small-fast-166 synthétisés (et la sonnerie
# bell-notification-933, swoosh-wind-short-1461 et whoosh-air-1489 incertains) ; le même swoosh revenait à chaque volet. Trois
# familles de sons répétés, dont les prises tournent dans l'ordre de la vidéo (sans aléatoire : refaire la vidéo redonne le même son),
# toutes de vrais enregistrements déjà dans le dossier des sons (earshot realness ≥ 0,77, « p_reel » de sons.json), rien de
# téléchargé. (prise, demi-tons)
PRISES = {
    "clic": [("click-typewriter-soft-1125", 0), ("click-classic-1117", 0), ("water-bubble-1317", 0), ("click-typewriter-soft-1125", -2),
             ("click-classic-1117", 2)],
    "camera": [("swoosh-wind-cinematic-1471", 0), ("air-zoom-vacuum-2608", 0), ("swoosh-wind-cinematic-1471", -2)],
    "volet": [("swoosh-fast-transitions-3115", 0), ("whoosh-fast-transition-1490", 0)],
}


def distribuer_prises(reperes):
    """Chaque son de famille (« @clic », « @camera », « @volet ») reçoit la prise suivante de sa famille, dans l'ordre de la vidéo."""
    compte = {}
    for r in sorted(reperes, key=lambda r: r["t"]):
        if r["son"].startswith("@"):
            famille = r["son"][1:]
            k = compte.get(famille, 0)
            compte[famille] = k + 1
            son, demi_tons = PRISES[famille][k % len(PRISES[famille])]
            r.update(son=son, famille=famille)
            if demi_tons:
                r["demi_tons"] = r.get("demi_tons", 0) + demi_tons
    return reperes


def pan_ecran(x):
    """V-18 : le panoramique léger d'un bruitage, d'après la place de l'action à l'écran (x de 0 à 1080)."""
    return round(max(-0.35, min(0.35, 0.35 * (x - 540) / 440)), 2)


def couleur(v):
    """Vert pour un gain, rouge pour une perte, encre pour zéro ou une valeur inconnue."""
    if v is None or round(v, 2) == 0:
        return COUL["encre2"]
    return COUL["vert"] if v > 0 else COUL["rouge"]


# ───────────────────────── chiffres et phrases ─────────────────────────
def unite_du_jour(j, demandee="r"):
    """« r » par défaut (le risque d'un trade : expliqué dans la vidéo) ; « pourcent » (du solde, journal des trades du compte),
    « points » si on le demande ; « auto » = le pourcentage quand il est connu, sinon R."""
    if demandee in ("pourcent", "r", "points"):
        return demandee
    avec = [m for m in j["marches"] if m["positions"]]
    return "pourcent" if avec and all(m["pct"] is not None for m in avec) else "r"


# Le petit mot du bilan : un par jour, choisi par la date (le même si on refait la vidéo), léger et sans moquerie.
MOTS_DU_JOUR = {
    "perte": ["Le marché a gagné cette manche. On revient demain.", "Pas notre jour : le stop a fait son travail.",
              "Une séance qui forge le caractère.", "Les pertes font partie du métier. On les montre aussi.",
              "Le stop a fait son boulot. On garde le cap."],
    "gain": ["Le robot a bien travaillé. Moi, j'ai surtout regardé.", "Belle séance, sans forcer.",
             "Le robot a fait sa part. On reste humble.", "Belle séance. Le robot a mérité son café."],
    # V-10 (27/11/2026) : « Le robot a préféré observer » était faux un jour bloqué (heure du serveur, compte non autorisé, férié)
    "rien": ["Pas de trade, pas de perte : parfois, attendre, c'est aussi trader.", "Pas de trade, pas de perte. On se retrouve à la prochaine séance."],
}


def mot_du_jour(j, t):
    cas = "rien" if not j["trades"] else ("gain" if (t if t is not None else (j["net"] or 0)) > 0 else "perte")
    liste = MOTS_DU_JOUR[cas]
    return liste[j["jour"].toordinal() % len(liste)]


def _une(n, mot_feminin=False):
    return ("une" if mot_feminin else "un") if n == 1 else nombres.entier(n)


def _s(n):
    return "s" if n > 1 else ""


def _majuscule(texte):
    return texte[:1].upper() + texte[1:]


def faits(m):
    """Ce qui s'est passé sur un marché, sans rien de la méthode : côté et heure de la cassure, sens, positions classées par sortie."""
    ps = m["positions"]
    stops = [p for p in ps if p["raison"].lower().startswith("stop")]
    fins = [p for p in ps if p["raison"].lower().startswith("fin de journ")]
    autres = [p for p in ps if p not in stops and p not in fins]
    return {"cote": "haut" if ps[0]["sens"] == 1 else "bas", "heure": ps[0]["entree"], "sens": {p["sens"] for p in ps},
            "n": len(ps), "stops": stops, "fins": fins, "autres": autres}


def pts_voix(x):
    """Des points dits à voix haute, exactement comme l'écran les montre : entiers à partir de 10 (« deux cent quatre-vingt-dix-sept
    points »), sinon un chiffre après la virgule (« zéro virgule six point ») ; « point » au singulier sous 2."""
    x = abs(x)
    mots = nombres.entier(round(x)) if x >= 9.95 else nombres.decimal(round(x, 1), 1)
    return f"{mots} point{'s' if round(x, 1) >= 2 else ''}"


def pts_ecran(x, signe=True):
    """+276 pts, −0,6 pt, +14 pts : entiers à partir de 10, une décimale en dessous."""
    texte = nombres.nombre_ecran(x, 0 if abs(x) >= 9.95 else 1, signe)
    return f"{texte} pt{'s' if round(abs(x), 1) >= 2 else ''}"


# V-28 (audit du 27/11/2026) : « jusqu'à zéro virgule sept point en notre faveur » (S&P du 09/06/2025) : un plus loin minuscule n'est
# ni dit ni montré.
MFE_DIT = 2.0


def _mfe_dit(p):
    return p.get("mfe") is not None and p["mfe"] >= MFE_DIT


def _avance(p):
    """La position est-elle allée dans notre sens avant de sortir (plus d'un dixième de son stop, et au moins MFE_DIT points) ?"""
    return p.get("mfe") is not None and p["mfe"] >= max(MFE_DIT, 0.1 * (p.get("risque") or 0))


def _heure_voix(instant):
    return nombres.heure(instant.hour, instant.minute) if instant else ""


def _nom_position(p, f):
    """« La première vente », « La dernière vente », « Une vente » (ou achat) : situer une position sans dire son type."""
    toutes = sorted(f["stops"] + f["fins"] + f["autres"], key=lambda q: q["entree"] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc))
    achat = p["sens"] == 1
    if p is toutes[0]:
        return "Le premier achat" if achat else "La première vente"
    if p is toutes[-1]:
        return "Le dernier achat" if achat else "La dernière vente"
    return "Un achat" if achat else "Une vente"


def phrase_stops(f):
    """Le chemin du prix jusqu'au premier stop : jusqu'où il est allé en notre faveur, puis le retournement (en points)."""
    st = sorted(f["stops"], key=lambda q: q["sortie"] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc))
    p = st[0]
    sujet = "Le prix" if f["n"] == 1 else _nom_position(p, f)
    a_heure = ""          # l'heure du stop est à l'écran : la voix ne la répète pas
    pts = p["points"]
    if pts is not None and pts > 0:            # un stop qui sort en gain
        debut = f"{sujet} va jusqu'à {pts_voix(p['mfe'])} en notre faveur, puis " if _mfe_dit(p) else f"{sujet} "
        texte = f"{debut}sort au stop{a_heure}, avec {pts_voix(pts)} de gain."
    elif _avance(p) and pts is not None:
        texte = (f"{sujet} va jusqu'à {pts_voix(p['mfe'])} en notre faveur… puis le marché se retourne de "
                 f"{pts_voix(p['mfe'] + abs(pts))} : stop touché{a_heure}.")
    elif pts is not None:
        cote = "plus bas" if p["sens"] == 1 else "plus haut"
        texte = f"{sujet} part aussitôt contre nous : stop touché{a_heure}, {pts_voix(pts)} {cote}."
    else:
        texte = f"{sujet} touche son stop{a_heure}."
    if len(st) > 1:
        k = len(st) - 1
        texte += f" {_majuscule(_une(k))} autre{_s(k)} stop{_s(k)} sui{'vent' if k > 1 else 't'}"
        # VID-27 : « Un autre stop suit. » ne disait pas s'il gagnait ou perdait, alors que l'écran le montrait (rond rouge ou vert)
        signes = {(_r_pos(q) or 0) > 0 for q in st[1:] if _r_pos(q)}
        texte += {frozenset({True}): ", en gain.", frozenset({False}): ", en perte."}.get(frozenset(signes), ".")
    return texte


def phrase_fins(f, sans_mfe=False):
    """Les positions gardées jusqu'à la fin de séance : jusqu'où le prix est allé en notre faveur, et s'il en a repris une partie.
    sans_mfe (VID-28) : ce plus loin est le même que celui déjà dit pour le stop (même bougie) ; deux chiffres différents
    (« +106 », puis « +108 » : chaque position compte depuis son prix d'entrée) pour le même creux embrouillaient."""
    fi, n = f["fins"], f["n"]
    k = len(fi)
    avec = [p for p in fi if _mfe_dit(p)]          # V-28 : pas de plus loin minuscule
    meilleure = max(avec, key=lambda p: p["mfe"]) if avec else None
    if n == 1:
        sujet = "Le prix"
    elif k == n:
        sujet = f"Les {nombres.entier(k)} positions tiennent jusqu'à la fin de séance"
    elif k == 1:
        sujet = "L'autre position tient jusqu'à la fin de séance"
    else:
        sujet = f"Les {nombres.entier(k)} autres tiennent jusqu'à la fin de séance"
    if meilleure is None or meilleure["mfe"] <= 0 or (sans_mfe and n > 1):
        return f"{sujet}." if n > 1 else f"Sortie en fin de séance, à {_heure_voix(fi[0]['sortie'])}."
    reprise = ""
    if meilleure["points"] is not None and meilleure["points"] < 0.5 * meilleure["mfe"]:
        # V-28 : « Le prix va jusqu'à … en notre faveur, puis le prix remonte » répétait « le prix »
        reprise = f", puis {'' if n == 1 else 'le prix '}{'redescend' if meilleure['sens'] == 1 else 'remonte'}"
    if n == 1:
        return f"Le prix va jusqu'à {pts_voix(meilleure['mfe'])} en notre faveur{reprise}. Sortie en fin de séance, à {_heure_voix(fi[0]['sortie'])}."
    return f"{sujet} : jusqu'à {pts_voix(meilleure['mfe'])} en notre faveur{reprise}."


def phrase_autres(f):
    ka = len(f["autres"])
    return f"{_majuscule(_une(ka, True))} sortie{_s(ka)} pendant la séance."


def _signe(ps):
    v = _somme(ps) if ps else 0
    return 0 if not v else (1 if v > 0 else -1)


def meme_scenario(a, b):
    """Deux marchés qui ont vécu la même séance (même côté, même sens, mêmes sorties, et chaque groupe de sorties du même côté du
    zéro) : la voix ne refait pas la présentation. VID-29 : le 18/11, « Même scénario » sur le S&P alors que ses sorties de fin de
    séance gagnaient et celles du Nasdaq perdaient."""
    cle = lambda x: (x["cote"], x["sens"], x["n"], len(x["stops"]), len(x["fins"]), _signe(x["stops"]), _signe(x["fins"]), _signe(x["autres"]))
    return cle(a) == cle(b)


def _bougie_extreme(m, p):
    """L'indice de la bougie où la position est allée le plus loin en notre faveur (None sans excursion connue)."""
    b = m["bougies"]
    if not b or not p.get("mfe") or p["entree"] is None or p["sortie"] is None:
        return None

    def indice(instant):
        return max(0, sum(1 for c in b if c["heure"] <= instant) - 1)
    bs = list(range(indice(p["entree"]), indice(p["sortie"]) + 1)) or [indice(p["entree"])]
    return min(bs, key=lambda q: b[q]["l"]) if p["sens"] == -1 else max(bs, key=lambda q: b[q]["h"])


def _stop_raconte(f):
    """Le stop dont la voix raconte le chemin (le premier sorti), et s'il dit jusqu'où le prix est allé en notre faveur."""
    st = sorted(f["stops"], key=lambda q: q["sortie"] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc))
    if not st:
        return None, False
    p = st[0]
    return p, _mfe_dit(p) and ((p["points"] is not None and p["points"] > 0) or (_avance(p) and p["points"] is not None))


def mfe_deja_dit(m, f):
    """VID-28 : la meilleure des positions de fin de séance a son plus loin sur la même bougie que le stop déjà raconté."""
    p, dit_mfe = _stop_raconte(f)
    avec = [q for q in f["fins"] if _mfe_dit(q)]
    if not dit_mfe or not avec:
        return False
    meilleure = max(avec, key=lambda q: q["mfe"])
    i = _bougie_extreme(m, p)
    return i is not None and i == _bougie_extreme(m, meilleure)


def couleur_groupe(ps):
    """VID-27 : vert si toutes les positions du groupe gagnent, rouge si toutes perdent, neutre si elles se partagent (« 2 stops » en
    rouge à côté d'un « Stop +51 pts » vert disait le contraire de l'écran)."""
    vals = [_r_pos(p) for p in ps]
    if vals and all(v is not None and v > 0 for v in vals):
        return COUL["vert"]
    if vals and all(v is not None and v < 0 for v in vals):
        return COUL["rouge"]
    return COUL["encre2"]


def valeur(m, unite):
    return {"pourcent": m.get("pct"), "r": m.get("r"), "points": m.get("points")}[unite]


DECIMALES = {"pourcent": 2, "r": 2, "points": 1}
SUFFIXE = {"pourcent": " %", "r": " R", "points": " pts"}


def ecran(v, unite):
    if v is None:
        return ""
    return nombres.nombre_ecran(v, DECIMALES[unite]) + SUFFIXE[unite]


def dit(v, unite):
    if v is None:
        return ""
    return nombres.decimal(v, DECIMALES[unite], signe=True) + {"pourcent": " pour cent", "r": " R", "points": " points"}[unite]


def total(j, unite):
    """Le total de la journée, tous marchés : en % ou en R (des points du Nasdaq et du S&P ne s'additionnent pas)."""
    if unite == "points":
        return None
    vals = [valeur(m, unite) for m in j["marches"] if m["positions"]]
    if not vals or any(v is None for v in vals):
        return None
    # la somme des valeurs telles qu'elles sont affichées : −1,50 R et −0,56 R font −2,06 R à l'écran comme à la voix
    return round(sum(round(v, 2) for v in vals), 2)


def accroche(j, unite):
    """La couleur de la journée, dite et montrée dès le titre : (mot de la voix, texte de l'écran, couleur)."""
    t = total(j, unite)
    v = t if t is not None else j["net"]
    if not j["trades"]:
        return "sans", "Journée sans trade", COUL["encre2"]
    if v is None or round(v, 2) == 0:
        return "blanche", "Journée blanche", COUL["encre2"]
    return ("verte", "Journée verte", COUL["vert"]) if v > 0 else ("rouge", "Journée rouge", COUL["rouge"])


SANS_TRADE = "le robot n'a pas tradé aujourd'hui."


def recit_marche(m, precedent, unite, expliquer_r):
    """Le texte d'une scène de marché et le rang (dans ses mots) du début de chaque partie : « intro », « stop », « fin », « autre »,
    « res ». La scène cale sa caméra sur ces mots. Rien de la méthode : ce que le prix a fait, et le résultat."""
    if not m["positions"]:
        # V-10 (audit du 27/11/2026, choix du propriétaire) : « les conditions n'étaient pas réunies » était faux un jour bloqué par
        # l'EA (heure du serveur pas sûre, compte réel non autorisé, marché décoché, férié). Vrai quelle que soit la raison, et
        # toujours sans la dire (secret des filtres).
        return f"{m['voix']} : {SANS_TRADE}", {}
    f = faits(m)
    parts = []
    if precedent is not None and precedent["positions"] and meme_scenario(faits(precedent), f):
        parts.append(("intro", f"Même scénario sur le {m['voix']}."))
    else:
        h = f"{_majuscule(_heure_voix(f['heure']))} : le prix" if f["heure"] else "Le prix"
        verbe = "entre" if len(f["sens"]) > 1 else ("achète" if 1 in f["sens"] else "vend")
        intro = f"{m['voix']}. {h} casse la zone par le {f['cote']}, le robot {verbe}."
        if f["n"] > 1:
            quoi = "positions" if len(f["sens"]) > 1 else ("achats" if 1 in f["sens"] else "ventes")
            intro += f" {_majuscule(nombres.entier(f['n']))} {quoi} en tout."
        parts.append(("intro", intro))
    if f["stops"]:
        parts.append(("stop", phrase_stops(f)))
    if f["fins"]:
        parts.append(("fin", phrase_fins(f, mfe_deja_dit(m, f))))
    if f["autres"]:
        parts.append(("autre", phrase_autres(f)))
    v = valeur(m, unite)
    if v is not None:
        parts.append(("res", f"Résultat : {dit(v, unite)}."))
    if expliquer_r:
        parts.append(("r", "Un R, c'est le risque pris sur un trade."))
    ancres, rang = {}, 0
    for cle, texte in parts:
        ancres[cle] = rang
        rang += len(texte.split())
    return " ".join(t for _, t in parts), ancres


def texte_marche(m, precedent, unite, expliquer_r):
    return recit_marche(m, precedent, unite, expliquer_r)[0]


def repliques(j, unite):
    """Le texte de chaque scène, dans l'ordre : titre, un par marché, bilan. Phrases courtes, heures et nombres en lettres."""
    date = _majuscule(nombres.date_longue(j["jour"]))
    cle = accroche(j, unite)[0]
    if cle == "sans":
        textes = [f"{date}. Journée sans trade pour le robot. Petit tour du marché !"]
    else:
        textes = [f"{date}. Journée {cle} pour le robot… on regarde ça !"]
    r_explique, precedent = False, None
    for m in j["marches"]:
        expliquer = unite == "r" and not r_explique and bool(m["positions"]) and valeur(m, unite) is not None
        textes.append(texte_marche(m, precedent, unite, expliquer))
        r_explique = r_explique or expliquer
        precedent = m
    if preuve_du_jour(j, unite):
        textes.append("Les trades du jour, dans l'historique de MetaTrader.")
    t = total(j, unite)
    mot = mot_du_jour(j, t)
    # Conformité TikTok (25/11/2026) : la vidéo garde les gens sur TikTok ; le Telegram n'est que dans la description
    fin = "Abonne-toi pour voir la séance de demain !"
    if not j["trades"]:
        textes.append(f"Bilan : {SANS_TRADE} {mot} {fin}")          # V-10
    elif t is not None:
        textes.append(f"Bilan du jour : {dit(t, unite)}. {mot} {fin}")
    else:
        textes.append(f"Bilan : journée {j['verdict'] or 'terminée'}. {mot} {fin}")
    return textes


# ───────────────────────── les scènes ─────────────────────────
def _composition(ident, style, corps, script):
    return f"""<template>
  <style>
    {POLICE_CSS}
    #root {{ position: absolute; inset: 0; font-family: "DIN Etrave", sans-serif; color: {COUL['encre']}; }}
    .date {{ position: absolute; left: 124px; top: 298px; font-size: 36px; color: {COUL['encre2']}; }}
    svg.plan {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: visible; }}
    svg.plan text {{ font-family: "DIN Etrave", sans-serif; }}
    .pastille {{ position: absolute; line-height: 1; padding: 0.2em 0.42em 0.14em; border-radius: 0.2em; white-space: nowrap; }}
{style}
  </style>
  <div id="root" data-composition-id="{ident}" data-width="1080" data-height="1920">
{corps}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {OUTILS_JS}
{script}
    window.__timelines["{ident}"] = tl;
  </script>
</template>
"""


def _l(texte, taille):
    """Largeur d'une pastille (texte + marges de .pastille)."""
    return police.largeur(texte, taille, POLICE) + 0.84 * taille


BIO_JOUR = "la séance de demain, ici"


def taille_bio(texte, taille=58):
    """La pastille du bas de l'écran de bilan bat (×1,07 depuis son bord gauche, x = 120) : elle reste dans la zone sûre de TikTok."""
    while taille > 40 and 120 + _l(texte, taille) * 1.07 > X_DROITE_BAS:
        taille -= 2
    return taille


def _pastille(ident, texte, fond, encre, taille, gauche, haut, classe=""):
    return (f'<div id="{ident}" class="pastille {classe}" style="left:{gauche:.0f}px; top:{haut:.0f}px; font-size:{taille}px; '
            f'background:{fond}; color:{encre}">{e(texte)}</div>')


def scene_titre(j, rep, unite):
    jour_sem, jour_mois, annee = nombres.date_ecran(j["jour"])
    cle, texte_badge, coul = accroche(j, unite)
    t_date = voix.instant(rep, nombres.JOURS[j["jour"].weekday()], defaut=0.5)
    t_badge = voix.instant(rep, cle, defaut=t_date + 1.4) - 0.05
    t_badge = max(t_badge, t_date + 0.8)
    taille_badge = 84
    while _l(texte_badge, taille_badge) > X_DROITE_BAS - 120 and taille_badge > 56:
        taille_badge -= 4
    style = f"""    #ti-logo {{ position: absolute; left: 100px; top: 290px; width: 180px; height: 180px; overflow: visible; }}
    .ti-ligne {{ position: absolute; left: 120px; line-height: 1; }}
    #ti-recap {{ top: 490px; font-size: 56px; color: {COUL['encre2']}; }}
    #ti-jour {{ top: 566px; font-size: 92px; }}
    #ti-date {{ top: 666px; font-size: 132px; }}
    #ti-annee {{ top: 812px; font-size: 80px; color: {COUL['encre2']}; }}"""
    corps = f"""    <svg id="ti-logo" viewBox="0 0 40 40">
      <path id="ti-v" d="{V_ETRAVE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
      <path id="ti-tige" d="{TIGE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" />
      <path id="ti-vagues" d="{VAGUES}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" opacity="0.55" />
    </svg>
    <div id="ti-recap" class="ti-ligne">Récap de la séance</div>
    <div id="ti-jour" class="ti-ligne">{e(jour_sem)}</div>
    <div id="ti-date" class="ti-ligne">{e(jour_mois)}</div>
    <div id="ti-annee" class="ti-ligne">{e(annee)}</div>
    {_pastille("ti-badge", texte_badge, coul, COUL["blanc"], taille_badge, 120, 960)}"""
    # V-13 (audit du 27/11/2026) : l'image 0 est la vignette du fil TikTok ; elle était vide (tout arrivait en volet) et la couleur du
    # jour n'arrivait qu'à 1,5-2 s. La date et la couleur sont posées dès l'image 0 ; le logo se trace, puis le jour et le tampon de
    # la couleur bougent sur les mots de la voix.
    script = f"""    const traits = ["#ti-tige", "#ti-v", "#ti-vagues"].map((id) => document.querySelector(id));
    traits.forEach((p) => {{ const l = p.getTotalLength(); gsap.set(p, {{ strokeDasharray: l, strokeDashoffset: l, opacity: 0 }}); }});
    gsap.set("#ti-recap", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("#ti-badge", {{ rotation: -3, transformOrigin: "0% 50%" }});
    // le bout arrondi d'un trait pas encore tracé ferait un point : le trait n'apparaît qu'au début de son tracé
    traits.forEach((p, i) => {{ tl.set(p, {{ opacity: i === 2 ? 0.55 : 1 }}, 0.05 + i * 0.18); tl.to(p, {{ strokeDashoffset: 0, duration: 0.34, ease: "power1.inOut" }}, 0.05 + i * 0.18); }});
    wipe("#ti-recap", 0.15);
    tl.to("#ti-jour", {{ scale: 1.06, transformOrigin: "0% 50%", duration: 0.14, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_date:.2f});
    tl.to("#ti-date", {{ scale: 1.04, transformOrigin: "0% 50%", duration: 0.16, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_date + 0.2:.2f});
    // la couleur de la journée, déjà posée, est tamponnée sur « rouge » / « verte »
    tl.fromTo("#ti-badge", {{ scale: 1.12, rotation: -7 }}, {{ scale: 1, rotation: -3, duration: 0.3, ease: "back.out(1.8)", immediateRender: false }}, {t_badge:.2f});
    tl.to("#ti-date", {{ y: 6, duration: 0.06, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_badge + 0.22:.2f});"""
    # V-15 : chaque instant est celui de l'image (le pic du son y tombe) ; V-17 : les coups secondaires plus bas ; V-18 : la place
    reperes = [{"t": 0.12, "son": "@volet", "gain_db": -6, "pan": -0.15},
               {"t": 0.55, "son": "water-splash-1311", "gain_db": -12, "max_dur": 0.6, "secondaire": True, "pan": -0.2},
               {"t": t_date + 0.2, "son": "typewriter-mechanical-hit-1365", "gain_db": -6, "secondaire": True, "pan": -0.15},
               {"t": t_badge + 0.08, "son": "hit-wood-hard-2182", "gain_db": -3, "passe_haut": 120, "pan": -0.1}]
    return style, corps, script, reperes, t_badge + 1.6


def _echelles(m):
    b = m["bougies"]
    prix = [x for c in b for x in (c["h"], c["l"]) if x is not None]
    for p in m["positions"]:
        prix += [x for x in (p["prix_entree"], p["prix_sortie"]) if x is not None]
    if m["zone"]:
        prix += [m["zone"]["bas"], m["zone"]["haut"]]
    bas, haut = min(prix), max(prix)
    marge = (haut - bas) * 0.07 or 1
    bas, haut = bas - marge, haut + marge
    pas = (X1 - GOUTTIERE - X0) / max(1, len(b))

    def y(p):
        return Y_BAS - (p - bas) / (haut - bas) * (Y_BAS - Y_HAUT)

    def indice(instant):
        return max(0, sum(1 for c in b if c["heure"] <= instant) - 1)

    def x(instant):
        if instant is None:
            return None
        i = indice(instant)
        fraction = min(1.0, max(0.0, (instant - b[i]["heure"]).total_seconds() / 300))
        return X0 + pas * (i + fraction)
    return x, y, pas, indice


def onde_repetee(ident, a_i, t_choc, fin, pas=2.2):
    """V-14 : l'onde du point repart toutes les 2,2 s pendant un long arrêt de la caméra (le check HyperFrames voyait 4,6 s sans
    aucun changement à l'écran)."""
    morceaux, tk = [], t_choc + pas
    while tk < fin - 0.6:
        morceaux.append(f'\n    tl.set("#{ident}-o{a_i}", {{ attr: {{ r: 4 }}, opacity: 1 }}, {tk:.2f});'
                        f'\n    tl.to("#{ident}-o{a_i}", {{ attr: {{ r: 34 }}, opacity: 0, duration: 0.75, ease: "power2.out" }}, {tk + 0.01:.2f});')
        tk += pas
    return "".join(morceaux)


def camera(px, py, s=ZOOM):
    """La caméra qui cadre le point (px, py) au zoom s sans sortir du graphique : (x, y, échelle) à donner à GSAP (origine 0 0), et la
    place du point à l'écran une fois cadré."""
    w, h = (X1 - X0) / s, (Y_BAS - Y_HAUT) / s
    cx = min(max(px, X0 + w / 2), X1 - w / 2)
    cy = min(max(py, Y_HAUT + h / 2), Y_BAS - h / 2)
    vx, vy = (X0 + X1) / 2, (Y_HAUT + Y_BAS) / 2
    tx, ty = vx - s * cx, vy - s * cy
    return (tx, ty, s), (s * px + tx, s * py + ty)


def _bulle(ident, pastilles, fx, fy, taille=34):
    """Les étiquettes d'un arrêt, posées à côté du point (fx, fy) à l'écran, dans le graphique : [(id, texte, fond, encre)]."""
    h, ecart = taille * 1.34, 10
    largeurs = [_l(t, taille) for _, t, _, _ in pastilles]
    W, H = max(largeurs), len(pastilles) * h + (len(pastilles) - 1) * ecart
    haut = fy - 40 - H if fy > (Y_HAUT + Y_BAS) / 2 else fy + 40
    haut = min(max(haut, Y_HAUT + 8), Y_BAS - H - 8)
    a_gauche = fx > (X0 + X1) / 2
    gauche = fx - 48 - W if a_gauche else fx + 48
    gauche = min(max(gauche, X_GAUCHE), X_DROITE - W)
    html_, ids = [], []
    for k, ((pid, texte, fond, encre), w) in enumerate(zip(pastilles, largeurs)):
        g = gauche + (W - w if a_gauche else 0)
        html_.append(_pastille(pid, texte, fond, encre, taille, g, haut + k * (h + ecart), f"{ident}-bulle"))
        ids.append(pid)
    return "\n    ".join(html_), ("100% 50%" if a_gauche else "0% 50%")


def _rangee(pastilles, taille, haut, gauche=124, droite=X_DROITE_BAS, ecart=14):
    """Des pastilles côte à côte, à la ligne quand la place manque : [(id, texte, fond, encre)] → (html, bas)."""
    h = taille * 1.34
    x, y, html_ = gauche, haut, []
    for pid, texte, fond, encre in pastilles:
        w = _l(texte, taille)
        if x > gauche and x + w > droite:
            x, y = gauche, y + h + ecart
        html_.append(_pastille(pid, texte, fond, encre, taille, x, y))
        x += w + ecart
    return "\n    ".join(html_), (y + h if pastilles else haut)


def _bougie(cx, c, y, pas, coul, classe="", epais=2):
    haut_corps, bas_corps = y(max(c["o"], c["c"])), y(min(c["o"], c["c"]))
    return (f'<g class="{classe}"><line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(c["h"]):.1f}" y2="{y(c["l"]):.1f}" stroke="{coul}" stroke-width="{epais}" />'
            f'<rect x="{cx - max(1.5, pas * 0.31):.1f}" y="{haut_corps:.1f}" width="{max(3, pas * 0.62):.1f}" height="{max(2, bas_corps - haut_corps):.1f}" fill="{coul}" /></g>')


def _r_pos(p):
    return p["r"] if p["r"] is not None else p["points"]


def _somme(ps):
    vals = [_r_pos(p) for p in ps]
    return None if any(v is None for v in vals) else sum(vals)


def _mot(rep, i, defaut=None):
    """L'heure du i-ème mot de la réplique (défaut si la réplique ou le mot manque)."""
    mots = (rep or {}).get("mots", [])
    return mots[i]["debut"] if i is not None and 0 <= i < len(mots) else defaut


def _instant_apres(rep, i, *cherches, defaut=None):
    """L'heure du premier mot qui commence par l'un des mots cherchés, à partir du i-ème mot."""
    for m in (rep or {}).get("mots", [])[i or 0:]:
        mot = m["mot"].lower().strip(".,:;!?…«»\"'")
        if any(mot.startswith(c) for c in cherches):
            return m["debut"]
    return defaut


def scene_marche(j, m, k, rep, unite, duree, expliquer_r=False, precedent=None):
    ident = f"m{k}"
    x, y, pas, indice = _echelles(m)
    b = m["bougies"]
    ps = m["positions"]
    f = faits(m) if ps else None
    ancres = recit_marche(m, precedent, unite, expliquer_r)[1]
    corps_b = []
    for i, c in enumerate(b):
        corps_b.append(_bougie(X0 + pas * (i + 0.5), c, y, pas, COUL["axe"] if c["c"] >= c["o"] else COUL["encre2"], f"{ident}-b"))
    # la zone de 15:30 : de la bougie de l'ouverture jusqu'au bout de la séance
    ouverture = next((i for i, c in enumerate(b) if c["heure"].astimezone(nombres_tz()).strftime("%H:%M") == "09:30"), None)
    zone, bord = "", ""
    if m["zone"] and ouverture is not None:
        zx, zh, zb = X0 + pas * ouverture, y(m["zone"]["haut"]), y(m["zone"]["bas"])
        trait = f'stroke="{COUL["encre2"]}" stroke-width="3" stroke-dasharray="14 10" vector-effect="non-scaling-stroke"'
        zone = (f'<g id="{ident}-zone"><rect x="{zx:.1f}" y="{zh:.1f}" width="{X1 - zx:.1f}" height="{zb - zh:.1f}" fill="{COUL["eau"]}" />'
                f'<line x1="{zx:.1f}" x2="{X1}" y1="{zh:.1f}" y2="{zh:.1f}" {trait} />'
                f'<line x1="{zx:.1f}" x2="{X1}" y1="{zb:.1f}" y2="{zb:.1f}" {trait} /></g>')
        if f:      # le bord que le prix casse, surligné en jaune au mot « casse »
            yb = zh if f["cote"] == "haut" else zb
            bord = (f'<line id="{ident}-bord" x1="{zx:.1f}" x2="{X1}" y1="{yb:.1f}" y2="{yb:.1f}" stroke="{COUL["jaune"]}" stroke-width="7" '
                    f'vector-effect="non-scaling-stroke" opacity="0" />')
    # les heures sous le graphique : l'ouverture et les heures paires, sans chevauchement ni débord à droite (zone des boutons)
    etiquettes, derniere = [], -999
    for i, c in enumerate(b):
        h = c["heure"]
        xh = X0 + pas * i
        # V-14 : ni sous les boutons de TikTok (à droite), ni contre le bord gauche (le check HyperFrames signalait « 14:00 »)
        if (i == ouverture or (h.minute == 0 and h.hour % 2 == 0)) and xh - derniere > 110 and xh + 40 <= X_DROITE_BAS and xh - 34 >= X_GAUCHE:
            derniere = xh
            etiquettes.append(f'<text x="{xh:.1f}" y="{Y_BAS + 44}" font-size="28" fill="{COUL["encre2"]}" text-anchor="middle">{h:%H:%M}</text>')
    # les positions : triangle d'entrée (bleu pour un achat, encre pour une vente) et trait jusqu'à la sortie
    marques, dessinees = [], []
    for i, p in enumerate(ps):
        xe = x(p["entree"])
        if xe is None or p["prix_entree"] is None:
            continue
        ye = y(p["prix_entree"])
        coul = COUL["bleu"] if p["sens"] == 1 else COUL["encre"]
        tri = (f"{xe:.1f},{ye + 3:.1f} {xe - 11:.1f},{ye + 23:.1f} {xe + 11:.1f},{ye + 23:.1f}" if p["sens"] == 1
               else f"{xe:.1f},{ye - 3:.1f} {xe - 11:.1f},{ye - 23:.1f} {xe + 11:.1f},{ye - 23:.1f}")
        trait, point_sortie = "", None
        xs = x(p["sortie"])
        if xs is not None and p["prix_sortie"] is not None:
            point_sortie = (xs, y(p["prix_sortie"]))
            trait = (f'<line class="{ident}-trait" x1="{xe:.1f}" y1="{ye:.1f}" x2="{xs:.1f}" y2="{point_sortie[1]:.1f}" stroke="{COUL["encre2"]}" '
                     f'stroke-width="2" stroke-dasharray="6 6" vector-effect="non-scaling-stroke" />')
        marques.append(f'<g id="{ident}-p{i}">{trait}<polygon class="{ident}-entree" points="{tri}" fill="{coul}" /></g>')
        dessinees.append({"i": i, "p": p, "entree": (xe, ye), "sortie": point_sortie})
    # les sorties : un rond par endroit et par signe (les positions qui sortent ensemble au même prix ne font qu'un rond, avec leur
    # nombre) : vert pour les gagnantes, rouge pour les perdantes ; au même endroit, le vert et le rouge se posent côte à côte
    groupes_sortie = {}
    for d in dessinees:
        if d["sortie"]:
            groupes_sortie.setdefault((round(d["sortie"][0]), round(d["sortie"][1]), (_r_pos(d["p"]) or 0) > 0), []).append(d)
    ronds = []
    for g_i, (cle, ds) in enumerate(groupes_sortie.items()):
        (xs, ys), n = ds[0]["sortie"], len(ds)
        if (cle[0], cle[1], not cle[2]) in groupes_sortie:
            xs += 7 if cle[2] else -7
        xs = min(xs, X1 - (8 if n == 1 else 11) - 2)          # VID-26 : le rond reste entier dans le cadre
        chiffre = (f'<text x="{xs:.1f}" y="{ys + 4.5:.1f}" font-size="13" fill="{COUL["blanc"]}" text-anchor="middle" data-layout-ignore>{n}</text>'
                   if n > 1 else "")
        ronds.append(f'<g id="{ident}-s{g_i}"><circle cx="{xs:.1f}" cy="{ys:.1f}" r="{8 if n == 1 else 11}" fill="{couleur(_somme([d["p"] for d in ds]))}" '
                     f'stroke="{COUL["blanc"]}" stroke-width="3" />{chiffre}</g>')
        for d in ds:
            d["rond"] = g_i

    def extreme(p):
        """Le point le plus loin en notre faveur pendant la position (prix du journal de l'EA, bougie où il a été atteint)."""
        i_x = _bougie_extreme(m, p)
        if i_x is None or p["prix_entree"] is None:
            return None
        return (X0 + pas * (i_x + 0.5), y(p["prix_entree"] + p["sens"] * p["mfe"]))

    # ── les arrêts de la caméra, chacun sur la phrase qui le raconte ──
    debut_b, duree_b = 0.35, 1.1
    t_zone = debut_b + duree_b + 0.05
    arrets = []
    if dessinees:
        d0 = dessinees[0]
        sens_txt = "Achat" if d0["p"]["sens"] == 1 else "Vente"
        # la caméra attend la fin de l'apparition de la zone (t_zone + 1,0 s) avant de zoomer
        t_casse = max(voix.instant(rep, "casse", "scénario", defaut=2.3), t_zone + 1.3)
        t_entree = max(_instant_apres(rep, ancres.get("intro"), "vend", "achète", "entre", "même", defaut=t_casse + 0.8), t_casse + 0.45)
        arrets.append({"nom": "entree", "t": t_casse, "cadre": [d0["entree"]], "ancre": d0["entree"], "rep": None,
                       "pastilles": [["cassure", f"Le prix casse par le {f['cote']}", COUL["jaune"], COUL["encre"], t_casse + 0.05],
                                     ["sens", f"{sens_txt} {d0['p']['entree']:%H:%M}",
                                      COUL["bleu"] if d0["p"]["sens"] == 1 else COUL["encre"], COUL["blanc"], t_entree]],
                       "ronds": []})
        for nom, liste in (("stop", f["stops"]), ("fin", f["fins"]), ("autre", f["autres"])):
            ds = [d for d in dessinees if any(d["p"] is q for q in liste) and d["sortie"]]
            if not ds:
                continue
            t0 = _mot(rep, ancres.get(nom))
            ronds_a = sorted({d["rond"] for d in ds})
            if nom == "stop":
                cible = min(ds, key=lambda d: d["p"]["sortie"])
                p, rep_p = cible["p"], cible
                pts = p["points"]
                ex = extreme(p) if (pts is not None and pts > 0 and _mfe_dit(p)) or _avance(p) else None
                pastilles = []
                if ex:
                    pastilles.append(["exc", f"Jusqu'à {pts_ecran(p['mfe'])}", COUL_CHEMIN, COUL["blanc"],
                                      _instant_apres(rep, ancres.get(nom), "jusqu", "va")])
                texte = f"Stop {pts_ecran(pts)}" if pts is not None else f"Stop {p['sortie']:%H:%M}"
                pastilles.append(["sortie", texte, couleur(_r_pos(p)), COUL["blanc"], _instant_apres(rep, ancres.get(nom), "stop", "sort")])
            else:
                avec = [d for d in ds if _mfe_dit(d["p"])]
                rep_p = max(avec, key=lambda d: d["p"]["mfe"]) if avec else ds[-1]
                cible = max(ds, key=lambda d: d["p"]["sortie"])
                ex = extreme(rep_p["p"]) if avec and nom == "fin" and not mfe_deja_dit(m, f) else None
                n = len(ds)
                hh = f"{cible['p']['sortie']:%H:%M}"
                pastilles = [["sortie", f"Sortie {hh}" if n == 1 else f"{n} sorties {hh}", couleur_groupe([d["p"] for d in ds]), COUL["blanc"], t0]]
                if ex:
                    mots_fin = phrase_fins(f, mfe_deja_dit(m, f)).split()      # le dernier « jusqu'à » : celui des points, pas « jusqu'à la fin »
                    rang_jusqu = max((r for r, w in enumerate(mots_fin) if w == "jusqu'à"), default=None)
                    pastilles.append(["exc", f"Jusqu'à {pts_ecran(rep_p['p']['mfe'])}", COUL_CHEMIN, COUL["blanc"],
                                      _mot(rep, ancres[nom] + rang_jusqu) if rang_jusqu is not None and ancres.get(nom) is not None else None])
            cadre = [rep_p["entree"], cible["sortie"]] + ([ex] if ex else [])
            arrets.append({"nom": nom, "t": t0, "cadre": cadre, "ancre": cible["sortie"], "rep": rep_p if ex else None, "ex": ex,
                           "pastilles": pastilles, "ronds": ronds_a, "positions": ds})
        # dans l'ordre de la voix ; un mot introuvable prend la suite ; chaque arrêt dure au moins ARRET s après sa dernière étiquette
        suite = sorted(arrets[1:], key=lambda a: (a["t"] is None, a["t"] or 0))
        arrets = arrets[:1] + suite
        for a, avant in zip(arrets[1:], arrets[:-1]):
            mini = max(q[4] for q in avant["pastilles"]) + ARRET
            if avant is arrets[0]:      # « Le prix casse par le … » : 6 mots, au moins 2,3 s à l'écran
                mini = max(mini, avant["t"] + 2.3)
            t0 = a["t"] if a["t"] is not None else mini
            decale = max(0.0, mini - t0)
            a["t"] = t0 + decale
            precedente = None
            for q in a["pastilles"]:
                tq = q[4] + decale if q[4] is not None else (precedente + 0.8 if precedente is not None else a["t"] + 0.1)
                q[4] = max(tq, a["t"] + 0.1, (precedente + 0.6) if precedente is not None else 0.0)
                precedente = q[4]
    derniere_etiquette = max(q[4] for q in arrets[-1]["pastilles"]) if arrets else 0.0
    t_res_mot = _mot(rep, ancres.get("res"), (derniere_etiquette + 1.6) if arrets else duree - 2.0)
    t_recul = max(t_res_mot - 0.2, (derniere_etiquette + ARRET) if arrets else 0, (arrets[0]["t"] + 2.3) if arrets else 0)
    t_res = t_recul + 0.4

    # ── la légende (V-14 : dans la ligne de la date, à droite), puis sous le graphique les pastilles qui comptent et le résultat ──
    yl, tl_ = 276, 28                                  # ligne de base et taille de la légende (28 px : ce qu'un téléphone lit)
    gauche_min = 124 + police.largeur(nombres.date_courte(j["jour"]), 36, POLICE) + 28
    legende = []

    def item(dessin, texte, largeur_dessin=26):
        return (dessin, texte, largeur_dessin)

    def poser(items):
        k = tl_ / 28
        larg = sum(ld * k + 6 + police.largeur(t, tl_, POLICE) for _, t, ld in items) + 18 * max(0, len(items) - 1)
        xl, blocs = X1 - larg, []
        for dessin, texte, ld in items:
            blocs.append(f'<g transform="translate({xl:.0f},{yl})"><g transform="scale({k:.3f})">{dessin}</g>'
                         f'<text x="{ld * k + 6:.0f}" y="0" font-size="{tl_}" fill="{COUL["encre2"]}">{e(texte)}</text></g>')
            xl += ld * k + 6 + police.largeur(texte, tl_, POLICE) + 18
        return blocs, X1 - larg
    if ps:
        if 1 in f["sens"]:
            legende.append(item(f'<polygon points="13,-21 2,-1 24,-1" fill="{COUL["bleu"]}" />', "achat"))
        if -1 in f["sens"]:
            legende.append(item(f'<polygon points="13,-1 2,-21 24,-21" fill="{COUL["encre"]}" />', "vente"))
        signes = {(_somme([d["p"] for d in ds]) or 0) > 0 for ds in groupes_sortie.values()}
        if True in signes:
            legende.append(item(f'<circle cx="11" cy="-10" r="9" fill="{COUL["vert"]}" />', "sortie gagnante", 22))
        if False in signes:
            legende.append(item(f'<circle cx="11" cy="-10" r="9" fill="{COUL["rouge"]}" />', "sortie perdante", 22))
    if zone:
        legende.append(item(f'<rect x="0" y="-21" width="30" height="20" fill="{COUL["eau"]}" stroke="{COUL["encre2"]}" stroke-width="2" stroke-dasharray="6 4" />',
                            f"zone de {b[ouverture]['heure']:%H:%M}", 30))
    # la légende tient à droite de la date : sinon « gain / perte » au lieu de « sortie gagnante / perdante », sinon sans elles
    blocs, gauche = poser(legende)
    if gauche < gauche_min:
        legende = [(d, {"sortie gagnante": "gain", "sortie perdante": "perte"}.get(t, t), ld) for d, t, ld in legende]
        blocs, gauche = poser(legende)
    if gauche < gauche_min:
        blocs, gauche = poser([x for x in legende if x[1] not in ("gain", "perte")])
    if gauche < gauche_min:
        blocs = []
    legende = blocs

    resume, bas_resume = "", Y_RESUME - 4
    if ps:
        n_e = len(ps)
        entree_txt = (f"{n_e} achat{_s(n_e)}" if f["sens"] == {1} else f"{n_e} vente{_s(n_e)}" if f["sens"] == {-1} else f"{n_e} positions")
        pastilles = [(f"{ident}-r-entree", entree_txt, COUL["bleu"] if f["sens"] == {1} else COUL["encre"], COUL["blanc"])]
        for nom, liste in (("stop", f["stops"]), ("fin", f["fins"]), ("autre", f["autres"])):
            if liste:
                n = len(liste)
                hs = {f"{p['sortie']:%H:%M}" for p in liste if p["sortie"]}
                texte = {"stop": f"{n} stop{_s(n)}",
                         "fin": f"{n} sortie{_s(n)} à {hs.pop()}" if len(hs) == 1 else f"{n} en fin de séance",
                         "autre": f"{n} autre{_s(n)} sortie{_s(n)}"}[nom]
                pastilles.append((f"{ident}-r-{nom}", texte, couleur_groupe(liste), COUL["blanc"]))
        resume, bas_resume = _rangee(pastilles, 34, Y_RESUME)
    v = valeur(m, unite)
    resultat, t_rappel = "", None
    if ps and v is not None:
        y_label = bas_resume + 20
        place = Y_FIN - (y_label + 42)
        taille = min(104, int((place - 8) / 1.34))
        vr = round(v, DECIMALES[unite])
        rappel = ""
        if expliquer_r and unite == "r":
            rappel = f'<div id="{ident}-rappel" class="rappel" style="top:{y_label + 4}px">1 R = le risque pris sur un trade</div>'
            t_rappel = max(t_res + 0.6, _mot(rep, ancres.get("r"), t_res + 1.0) - 0.2)
        resultat = (f'<div id="{ident}-res-t" class="label" style="top:{y_label}px">Résultat</div>{rappel}'
                    + _pastille(f"{ident}-res", ecran(vr, unite), couleur(vr), COUL["blanc"], taille, 120, y_label + 42))
    sans = ""
    if not ps:           # V-10 : ce que dit la voix, sans raison
        sans = (f'<div id="{ident}-sans1" class="{ident}-sans" style="top:{Y_RESUME}px; font-size:56px">Le robot n\'a pas tradé</div>'
                f'<div id="{ident}-sans2" class="{ident}-sans" style="top:{Y_RESUME + 70}px; font-size:56px">aujourd\'hui.</div>')

    # les arrêts : cadrage, bougie surlignée, onde, chemin du prix en vert, étiquettes posées là où la caméra met le point
    colonnes, focus, bulles = [], [], []
    for a_i, a in enumerate(arrets):
        xs_, ys_ = [q[0] for q in a["cadre"]], [q[1] for q in a["cadre"]]
        s = max(1.25, min(ZOOM, 0.8 * (X1 - X0) / (max(xs_) - min(xs_) + 60), 0.8 * (Y_BAS - Y_HAUT) / (max(ys_) - min(ys_) + 60)))
        cam, _ = camera((max(xs_) + min(xs_)) / 2, (max(ys_) + min(ys_)) / 2, s)
        a["cam"] = cam
        px, py = a["ancre"]
        fx, fy = cam[2] * px + cam[0], cam[2] * py + cam[1]
        a["fx"] = fx                     # V-18 : la place de l'action à l'écran, pour le panoramique de ses bruitages
        i_b = min(len(b) - 1, max(0, int((px - X0) / pas)))
        cb = X0 + pas * (i_b + 0.5)
        # la colonne jaune passe sous les bougies ; la bougie surlignée, le chemin du prix et l'onde passent dessus
        colonnes.append(f'<rect id="{ident}-c{a_i}" x="{cb - pas * 0.7:.1f}" y="{Y_HAUT - 20}" width="{pas * 1.4:.1f}" '
                        f'height="{Y_BAS - Y_HAUT + 40}" fill="{COUL["jaune"]}" opacity="0" />')
        focus.append(f'<g id="{ident}-f{a_i}" opacity="0">{_bougie(cb, b[i_b], y, pas, COUL["encre"])}</g>')
        if a.get("ex"):
            (xe, ye), (xx, yx) = a["rep"]["entree"], a["ex"]
            focus.append(f'<g id="{ident}-x{a_i}" opacity="0"><line x1="{xe:.1f}" y1="{ye:.1f}" x2="{xx:.1f}" y2="{yx:.1f}" stroke="{COUL_CHEMIN}" '
                         f'stroke-width="4" stroke-dasharray="10 7" vector-effect="non-scaling-stroke" />'
                         f'<circle cx="{xx:.1f}" cy="{yx:.1f}" r="6" fill="{COUL_CHEMIN}" stroke="{COUL["blanc"]}" stroke-width="2" /></g>')
        focus.append(f'<circle id="{ident}-o{a_i}" cx="{px:.1f}" cy="{py:.1f}" r="4" fill="none" stroke="{a["pastilles"][-1][2] if a["nom"] == "entree" else next(q[2] for q in a["pastilles"] if q[0] == "sortie")}" '
                     f'stroke-width="3" vector-effect="non-scaling-stroke" opacity="0" />')
        pastilles = [(f"{ident}-a{a_i}-{q[0]}", q[1], q[2], q[3]) for q in a["pastilles"]]
        html_b, origine = _bulle(ident, pastilles, fx, fy)
        a["origine"] = origine
        for q in a["pastilles"]:
            q.append(f"{ident}-a{a_i}-{q[0]}")
        bulles.append(html_b)
    style = f"""    #{ident}-date {{ top: 244px; }}
    #{ident}-nom {{ position: absolute; left: 120px; top: 284px; font-size: 76px; line-height: 1; }}
    #{ident} .label, .label {{ position: absolute; left: 124px; font-size: 34px; color: {COUL['encre2']}; line-height: 1; }}
    .rappel {{ position: absolute; left: 290px; font-size: 28px; color: {COUL['encre2']}; line-height: 1; }}
    .{ident}-sans {{ position: absolute; left: 124px; line-height: 1; }}
    #{ident}-cadre {{ fill: none; stroke: {COUL['axe']}; stroke-opacity: 0.35; stroke-width: 2; }}"""
    # VID-25 (audit du 26/11/2026) : la découpe descendait 10 px sous l'axe des heures ; caméra zoomée, les bougies et la colonne
    # jaune passaient sur l'axe. Elle s'arrête maintenant au-dessus (Y_BAS + 10, l'axe est à Y_BAS + 12).
    corps = f"""    <div class="date" id="{ident}-date">{e(nombres.date_courte(j['jour']))}</div>
    <div id="{ident}-nom">{e(m['nom'])}</div>
    <svg class="plan" viewBox="0 0 1080 1920" data-layout-allow-overflow>
      <defs><clipPath id="{ident}-clip"><rect x="{X0 - 12}" y="{Y_HAUT - 22}" width="{X1 - X0 + 22}" height="{Y_BAS - Y_HAUT + 32}" /></clipPath></defs>
      <rect id="{ident}-cadre" x="{X0 - 12}" y="{Y_HAUT - 22}" width="{X1 - X0 + 22}" height="{Y_BAS - Y_HAUT + 44}" rx="10" />
      <line id="{ident}-axe" x1="{X0}" x2="{X1}" y1="{Y_BAS + 12}" y2="{Y_BAS + 12}" stroke="{COUL['axe']}" stroke-width="3" />
      <g id="{ident}-heures">{''.join(etiquettes)}</g>
      <g clip-path="url(#{ident}-clip)">
        <g id="{ident}-cam">
          {zone}
          {''.join(colonnes)}
          {bord}
          <g id="{ident}-bougies">{''.join(corps_b)}</g>
          {''.join(focus)}
          <g id="{ident}-positions">{''.join(marques)}</g>
          <g id="{ident}-ronds">{''.join(ronds)}</g>
        </g>
      </g>
      <g id="{ident}-legende">{''.join(legende)}</g>
    </svg>
    {chr(10).join(bulles)}
    {resume}
    {resultat}
    {sans}"""
    a_couper = [f"#{ident}-date", f"#{ident}-nom"] + ([f".{ident}-sans"] if sans else []) + ([f"#{ident}-res-t"] if resultat else []) \
        + ([f"#{ident}-rappel"] if t_rappel is not None else [])
    script = [f"""    gsap.set({json.dumps(a_couper)}, {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set(".{ident}-b", {{ opacity: 0, scaleY: 0.2, transformOrigin: "50% 50%" }});
    gsap.set("#{ident}-axe", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    gsap.set(["#{ident}-heures", "#{ident}-legende", "#{ident}-cadre"], {{ opacity: 0 }});
    gsap.set("#{ident}-cam", {{ svgOrigin: "0 0", x: 0, y: 0, scale: 1 }});
    wipe("#{ident}-date", 0.05);
    wipe("#{ident}-nom", 0.1, 0.32);
    tl.to("#{ident}-cadre", {{ opacity: 1, duration: 0.3 }}, 0.2);
    tl.to("#{ident}-axe", {{ scaleX: 1, duration: 0.45, ease: "power2.out" }}, 0.25);
    tl.to("#{ident}-heures", {{ opacity: 1, duration: 0.3 }}, 0.5);
    tl.to(".{ident}-b", {{ opacity: 1, scaleY: 1, duration: 0.14, ease: "power2.out", stagger: {duree_b / max(1, len(b)):.4f} }}, {debut_b});
    tl.to("#{ident}-legende", {{ opacity: 1, duration: 0.3 }}, {t_zone:.2f});"""]
    reperes = [{"t": 0.2, "son": "paper-quick-movement-2380", "gain_db": -9, "max_dur": 0.3, "secondaire": True, "pan": -0.2},
               {"t": debut_b, "son": "tick-wall-clock-fast-1063", "gain_db": -13, "max_dur": duree_b, "secondaire": True}]
    if zone:
        # la zone apparaît avec un léger reflet bleu, fini avant que la caméra ne zoome
        script.append(f"""    gsap.set("#{ident}-zone", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    tl.to("#{ident}-zone", {{ scaleX: 1, duration: 0.45, ease: "power2.inOut" }}, {t_zone:.2f});
    tl.fromTo("#{ident}-zone rect", {{ fill: "#b9d3f0" }}, {{ fill: "{COUL['eau']}", duration: 0.5, ease: "power1.out", immediateRender: false }}, {t_zone + 0.25:.2f});""")
        reperes.append({"t": t_zone + 0.22, "son": "whoosh-cinematic-fast-1492", "gain_db": -13, "max_dur": 0.3, "secondaire": True,
                        "pan": 0.15})
    for d in dessinees:
        script.append(f"""    gsap.set(["#{ident}-p{d['i']} .{ident}-entree", "#{ident}-p{d['i']} .{ident}-trait"], {{ opacity: 0 }});""")
    if ronds:
        script.append(f'    gsap.set("#{ident}-ronds > g", {{ opacity: 0 }});')
    if resume:
        script.append(f'    gsap.set("[id^=\'{ident}-r-\']", {{ opacity: 0 }});')
    for a_i, a in enumerate(arrets):
        tx, ty, s = a["cam"]
        t = a["t"]
        t_cam = t - (0.3 if a_i == 0 else 0.35)
        fin = arrets[a_i + 1]["t"] - 0.25 if a_i + 1 < len(arrets) else t_recul
        ids = [q[5] for q in a["pastilles"]]
        t_choc = next((q[4] for q in a["pastilles"] if q[0] == "sortie"), t)     # l'instant de la sortie (ou de la cassure)
        script.append(f"""    gsap.set({json.dumps(['#' + i for i in ids])}, {{ opacity: 0 }});
    tl.to("#{ident}-cam", {{ x: {tx:.1f}, y: {ty:.1f}, scale: {s:.3f}, duration: {0.6 if a_i == 0 else 0.5}, ease: "power3.inOut" }}, {t_cam:.2f});
    tl.to("#{ident}-f{a_i}", {{ opacity: 1, duration: 0.2 }}, {t:.2f});
    tl.to("#{ident}-c{a_i}", {{ opacity: 0.55, duration: 0.2 }}, {t:.2f});
    tl.set("#{ident}-o{a_i}", {{ attr: {{ r: 4 }}, opacity: 1 }}, {t_choc:.2f});
    tl.to("#{ident}-o{a_i}", {{ attr: {{ r: 34 }}, opacity: 0, duration: 0.75, ease: "power2.out" }}, {t_choc + 0.01:.2f});{onde_repetee(ident, a_i, t_choc, fin)}
    tl.to(["#{ident}-f{a_i}", "#{ident}-c{a_i}"], {{ opacity: 0, duration: 0.2 }}, {fin:.2f});
    tl.to({json.dumps(['#' + i for i in ids])}, {{ opacity: 0, duration: 0.15 }}, {fin:.2f});""")
        for q in a["pastilles"]:
            script.append(f'    pop("#{q[5]}", {q[4]:.2f}, 0.34, "{a["origine"]}");')
        if a.get("ex"):
            t_ex = next(q[4] for q in a["pastilles"] if q[0] == "exc")
            script.append(f"""    tl.fromTo("#{ident}-x{a_i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, immediateRender: false }}, {t_ex - 0.1:.2f});
    tl.to("#{ident}-x{a_i}", {{ opacity: 0, duration: 0.2 }}, {fin:.2f});""")
            reperes.append({"t": t_ex, "son": "@clic", "gain_db": -10, "max_dur": 0.25, "secondaire": True, "pan": pan_ecran(a["fx"])})
        if a_i == 0:
            script.append(f"""    tl.to("#{ident}-bougies", {{ opacity: 0.3, duration: 0.3 }}, {t_cam:.2f});
    tl.to("#{ident}-heures", {{ opacity: 0, duration: 0.2 }}, {t_cam:.2f});""")
            if bord:
                script.append(f'    tl.fromTo("#{ident}-bord", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12, yoyo: true, repeat: 3, immediateRender: false }}, {t:.2f});'
                              f'\n    tl.to("#{ident}-bord", {{ opacity: 0.85, duration: 0.1 }}, {t + 0.5:.2f});\n    tl.to("#{ident}-bord", {{ opacity: 0, duration: 0.3 }}, {t_recul:.2f});')
            t_e = a["pastilles"][1][4]
            for rang, d in enumerate(dessinees):
                script.append(f'    pop("#{ident}-p{d["i"]} .{ident}-entree", {t_e + 0.1 * min(rang, 8):.2f}, 0.3);'
                              f'\n    tl.to("#{ident}-p{d["i"]} .{ident}-trait", {{ opacity: 1, duration: 0.3 }}, {t_e + 0.1 * min(rang, 8) + 0.2:.2f});')
            if resume:
                script.append(f'    pop("#{ident}-r-entree", {t_e:.2f}, 0.34, "0% 50%");')
            reperes += [{"t": t_cam + 0.3, "son": "@camera", "gain_db": -12, "max_dur": 0.4, "secondaire": True, "pan": pan_ecran(a["fx"])},
                        {"t": t, "son": "click-metal-button-1830", "gain_db": -7, "secondaire": True, "pan": pan_ecran(a["fx"])},
                        {"t": t_e, "son": "@clic", "gain_db": -6, "max_dur": 0.25, "secondaire": True, "pan": pan_ecran(a["fx"])}]
        else:
            for rang, g_i in enumerate(a["ronds"]):
                script.append(f'    pop("#{ident}-s{g_i}", {t_choc + 0.07 * min(rang, 8):.2f}, 0.3);')
            if resume:
                script.append(f'    pop("#{ident}-r-{a["nom"]}", {t_choc:.2f}, 0.34, "0% 50%");')
            stop_perdant = a["nom"] == "stop" and next(q[2] for q in a["pastilles"] if q[0] == "sortie") == COUL["rouge"]
            reperes += [{"t": t_cam + 0.25, "son": "@camera", "gain_db": -13, "max_dur": 0.35, "secondaire": True, "pan": pan_ecran(a["fx"])},
                        {"t": t_choc, "son": "hit-wood-hard-2182" if stop_perdant else "click-light-switch-2585",
                         "gain_db": -4 if stop_perdant else -8, "pan": pan_ecran(a["fx"]),
                         **({"passe_haut": 140} if stop_perdant else {"secondaire": True})}]
    if arrets:
        script.append(f"""    tl.to("#{ident}-cam", {{ x: 0, y: 0, scale: 1, duration: 0.55, ease: "power3.inOut" }}, {t_recul:.2f});
    tl.to(["#{ident}-bougies", "#{ident}-heures"], {{ opacity: 1, duration: 0.35 }}, {t_recul + 0.2:.2f});""")
        reperes.append({"t": t_recul + 0.27, "son": "@camera", "gain_db": -13, "max_dur": 0.4, "secondaire": True})
        montres = {g for a in arrets[1:] for g in a["ronds"]}       # un rond sans arrêt (rare) apparaît au recul
        for g_i in range(len(ronds)):
            if g_i not in montres:
                script.append(f'    tl.to("#{ident}-s{g_i}", {{ opacity: 1, duration: 0.3 }}, {t_recul:.2f});')
    fin_min = 0.0
    if resultat:
        vr = round(v, DECIMALES[unite])
        script.append(f"""    wipe("#{ident}-res-t", {t_res - 0.15:.2f});
    pop("#{ident}-res", {t_res:.2f}, 0.4, "0% 50%");
    compte("#{ident}-res", {vr}, {DECIMALES[unite]}, "{SUFFIXE[unite]}", {t_res:.2f}, 0.8);
    tl.to("#{ident}-res", {{ scale: 1.08, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_res + 0.82:.2f});""")
        reperes += [{"t": t_res, "son": "ticking-timer-1056", "gain_db": -16, "max_dur": 0.8, "secondaire": True, "pan": -0.2},
                    {"t": t_res + 0.8, "son": "hit-deep-heartbeat-498", "gain_db": -6, "passe_haut": 160, "max_dur": 1.1, "pan": -0.15}]
        fin_min = t_res + 0.8 + 1.8
        if t_rappel is not None:
            script.append(f'    wipe("#{ident}-rappel", {t_rappel:.2f});')
            fin_min = max(fin_min, t_rappel + 2.0)
    if sans:
        t_sans = max(voix.instant(rep, "robot", defaut=2.3), t_zone + 0.4)
        script.append(f'    wipe("#{ident}-sans1", {t_sans:.2f});\n    wipe("#{ident}-sans2", {max(t_sans + 0.5, voix.instant(rep, "aujourd", defaut=t_sans + 1.0)):.2f});')
        reperes.append({"t": t_sans, "son": "click-light-switch-2585", "gain_db": -10, "secondaire": True, "pan": -0.2})
        fin_min = max(fin_min, t_sans + 2.5)
    return style, corps, "\n".join(script), reperes, fin_min


def scene_bilan(j, rep, unite, texte):
    t = total(j, unite)
    mot = mot_du_jour(j, t)
    k_mot = len(texte.split(mot)[0].split())          # le rang du premier mot du petit mot dans la réplique
    lignes, script, reperes = [], [], [{"t": 0.15, "son": "paper-page-turn-1104", "gain_db": -6, "secondaire": True, "pan": -0.15}]
    for i, m in enumerate(j["marches"]):
        v = valeur(m, unite)
        vr = round(v, DECIMALES[unite]) if v is not None else None
        txt = ecran(vr, unite) if m["positions"] and v is not None else "pas de trade"
        fond = COUL["grille"] if not m["positions"] or v is None else couleur(vr)
        encre = COUL["encre2"] if not m["positions"] or v is None else COUL["blanc"]
        lignes.append(f'<div id="bi-l{i}" class="bi-ligne" style="top:{475 + 76 * i}px">{e(m["nom"])}</div>'
                      + _pastille(f"bi-v{i}", txt, fond, encre, 46, 520, 470 + 76 * i))
        script.append(f'    wipe("#bi-l{i}", {0.3 + 0.18 * i:.2f});\n    pop("#bi-v{i}", {0.42 + 0.18 * i:.2f}, 0.32, "0% 50%");')
        reperes.append({"t": 0.5 + 0.18 * i, "son": "@clic", "gain_db": -9, "max_dur": 0.25, "secondaire": True, "pan": 0.05})
    y_total = 475 + 76 * len(j["marches"]) + 16
    t_total = max(voix.instant(rep, "moins", "plus", "zéro", "pas", "journée", defaut=1.0), 0.9)
    if t is not None:
        tr = round(t, DECIMALES[unite])
        gros = (f'<div id="bi-total-t" class="bi-label" style="top:{y_total}px">Total</div>'
                + _pastille("bi-total", ecran(tr, unite), couleur(tr), COUL["blanc"], 104, 120, y_total + 46))
        script.append(f"""    wipe("#bi-total-t", {t_total - 0.25:.2f});
    pop("#bi-total", {t_total:.2f}, 0.4, "0% 50%");
    compte("#bi-total", {tr}, {DECIMALES[unite]}, "{SUFFIXE[unite]}", {t_total:.2f}, 0.9);
    tl.to("#bi-total", {{ scale: 1.08, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_total + 0.92:.2f});""")
        reperes += [{"t": t_total, "son": "ticking-timer-1056", "gain_db": -15, "max_dur": 0.9, "secondaire": True, "pan": -0.2},
                    {"t": t_total + 0.9, "son": "hit-deep-heartbeat-498", "gain_db": -5, "passe_haut": 180, "max_dur": 1.2, "pan": -0.15}]
    else:
        verdict = "Pas de trade" if not j["trades"] else f"Journée {j['verdict'] or 'terminée'}"
        gros = _pastille("bi-total", verdict, COUL["grille"] if not j["trades"] else couleur(j["net"]),
                         COUL["encre"] if not j["trades"] else COUL["blanc"], 80, 120, y_total + 20)
        script.append(f'    pop("#bi-total", {t_total:.2f}, 0.4, "0% 50%");')
        reperes.append({"t": t_total + 0.1, "son": "hit-deep-heartbeat-498", "gain_db": -6, "passe_haut": 180, "max_dur": 1.2, "pan": -0.15})
    mots = (rep or {}).get("mots", [])
    t_mot = mots[k_mot]["debut"] if len(mots) > k_mot else t_total + 1.4
    t_mot = max(t_mot, t_total + 1.0)
    t_tel = max(voix.instant(rep, "abonne", apres=t_mot, defaut=t_mot + 1.6), t_mot + 0.8)
    t_bio = max(voix.instant(rep, "demain", apres=t_tel, defaut=t_tel + 0.8), t_tel + 0.4)
    # le bas de l'écran se pose depuis la limite de TikTok (y = 1260) : la mention, la pastille, « Abonne-toi » ; le petit mot (un
    # autocollant jaune posé de travers, une phrase par ligne, chaque phrase sur ses mots) prend la place qui reste au-dessus.
    # Sous y = 840, tout reste à gauche de x = 780.
    y_mention = Y_FIN - 8 - 2 * 28 * 1.32
    y_bio = y_mention - 16 - 58 * 1.34
    y_tel = y_bio - 68
    y_mot = y_total + 46 + 104 * 1.34 + 26
    phrases = [p.strip() + ("" if p.strip().endswith((".", "!", "?")) else ".") for p in mot.replace("! ", "!|").replace(". ", ".|").split("|") if p.strip()]
    for taille_mot in (42, 40, 38, 36, 34, 32, 30):
        lignes_mot = [(k, l) for k, p in enumerate(phrases) for l in police.couper(p, taille_mot, X_DROITE_BAS - 120 - 0.84 * taille_mot - 4, POLICE)]
        h_mot = taille_mot * 1.18 * len(lignes_mot) + taille_mot * 0.34
        if y_mot + h_mot <= y_tel - 24:
            break
    mots_avant = [len(p.split()) for p in phrases]
    style = f"""    #bi-titre {{ position: absolute; left: 120px; top: 340px; font-size: 92px; line-height: 1; }}
    .bi-ligne {{ position: absolute; left: 124px; font-size: 56px; line-height: 1; }}
    .bi-label {{ position: absolute; left: 124px; font-size: 38px; color: {COUL['encre2']}; line-height: 1; }}
    #bi-mot {{ line-height: 1.18; white-space: normal; }}
    .bi-bas {{ position: absolute; left: 124px; line-height: 1.15; width: 650px; }}
    #bi-mention {{ font-family: "Inter", sans-serif; font-weight: 400; font-size: 28px; line-height: 1.32; color: {COUL['encre2']}; }}"""
    corps = f"""    <div class="date" id="bi-date">{e(nombres.date_courte(j['jour']))}</div>
    <div id="bi-titre">Bilan du jour</div>
    {''.join(lignes)}
    {gros}
    <div id="bi-mot" class="pastille" style="left:120px; top:{y_mot:.0f}px; font-size:{taille_mot}px; background:{COUL['jaune']}; color:{COUL['encre']}">{'<br>'.join(f'<span class="bi-p{k}">{e(l)}</span>' for k, l in lignes_mot)}</div>
    <div id="bi-tel" class="bi-bas" style="top:{y_tel:.0f}px; font-size:56px">Abonne-toi :</div>
    {_pastille("bi-bio", BIO_JOUR, COUL["bleu"], COUL["blanc"], taille_bio(BIO_JOUR), 120, y_bio)}
    <div id="bi-mention" class="bi-bas" style="top:{y_mention:.0f}px">Pas un conseil en investissement. Le trading comporte un risque de perte en capital.</div>"""
    script_tete = """    gsap.set(["#bi-date", "#bi-titre", ".bi-ligne", ".bi-label", "#bi-tel"], { clipPath: "inset(-30% 100% -40% 0)" });
    gsap.set("#bi-mention", { opacity: 0 });
    wipe("#bi-date", 0.05);
    wipe("#bi-titre", 0.1, 0.32);"""
    # la deuxième phrase du petit mot (s'il y en a une) apparaît sur son premier mot, avec un petit coup sur l'autocollant
    for k in range(1, len(phrases)):
        rang = k_mot + sum(mots_avant[:k])
        t_k = max(mots[rang]["debut"] if len(mots) > rang else t_mot + 1.4 * k, t_mot + 0.6 * k)
        script.append(f'    gsap.set(".bi-p{k}", {{ opacity: 0 }});\n    tl.to(".bi-p{k}", {{ opacity: 1, duration: 0.2 }}, {t_k:.2f});'
                      f'\n    tl.to("#bi-mot", {{ scale: 1.05, duration: 0.1, yoyo: true, repeat: 1 }}, {t_k:.2f});')
        reperes.append({"t": t_k, "son": "@clic", "gain_db": -10, "max_dur": 0.25, "secondaire": True, "pan": -0.1})
    script.append(f"""    tl.fromTo("#bi-mot", {{ opacity: 0, scale: 1.4, rotation: 4, transformOrigin: "20% 50%" }}, {{ opacity: 1, scale: 1, rotation: -2, duration: 0.32, ease: "back.out(1.8)" }}, {t_mot:.2f});
    wipe("#bi-tel", {t_tel - 0.1:.2f});
    pop("#bi-bio", {t_bio:.2f}, 0.36, "0% 50%");
    tl.to("#bi-bio", {{ scale: 1.07, duration: 0.28, yoyo: true, repeat: 3, ease: "sine.inOut", transformOrigin: "0% 50%" }}, {t_bio + 0.5:.2f});
    tl.to("#bi-mention", {{ opacity: 1, duration: 0.3 }}, {t_tel:.2f});""")      # la mention reste au moins 3,5 s à l'écran
    # V-16 : plus de sonnerie (bell-notification-933, incertaine pour earshot, proscrite par sound.md) : une bulle qui éclate
    reperes += [{"t": t_mot + 0.12, "son": "paper-slide-1530", "gain_db": -8, "max_dur": 0.4, "secondaire": True, "pan": -0.1},
                {"t": t_bio + 0.15, "son": "water-bubble-1317", "gain_db": -6, "max_dur": 0.3, "pan": -0.15}]
    return style, corps, script_tete + "\n" + "\n".join(script), reperes, max(t_bio + 2.4, t_tel + 3.9)


# ───────────────────────── la preuve : la photo de l'historique de MetaTrader, épinglée avec le R ─────────────────────────
def preuve_du_jour(j, unite):
    """La photo de l'onglet Historique du jour et les résultats en R à épingler dessous, ou None sans photo."""
    if not j.get("historique") or not j["trades"]:
        return None
    notes = []
    for m in j["marches"]:
        v = valeur(m, unite)
        if m["positions"] and v is not None:
            vr = round(v, DECIMALES[unite])
            notes.append((f"{m['nom']}  {ecran(vr, unite)}", couleur(vr)))
    t = total(j, unite)
    if t is not None and len(notes) > 1:
        notes.append((f"Total  {ecran(t, unite)}", couleur(t)))
    return {"photos": [(j["historique"], f"Historique MetaTrader, {nombres.date_courte(j['jour'])}")], "notes": notes}


def scene_preuve(ident, preuve, rep, date_txt, titre="Dans MetaTrader"):
    """La photo de l'historique (une, ou deux pour une semaine ou un mois) épinglée comme une photo sur la carte, puis les
    résultats en R épinglés dessous. Rend aussi les images à copier dans le projet : (chemin, nom dans assets/captures)."""
    import historique
    corps, script, reperes, images = [], [], [], []
    t0 = max(voix.instant(rep, "metatrader", "trades", "historique", defaut=0.6) - 0.2, 0.45)
    photos = preuve["photos"][:2]
    # les photos tiennent entre y = 460 et y = 1040 ; dessous, la place des résultats épinglés (jusqu'à y = 1260)
    hauteur_max = (1040 - 460 - 40 * (len(photos) - 1)) / max(1, len(photos))
    y, t = 460.0, t0
    for i, (image, legende) in enumerate(photos):
        iw, ih = historique.taille_png(image)
        largeur = 840.0
        if y + (largeur - 28) * ih / iw + 66 > 840:      # sous y = 840, rien à droite de x = 780 (les boutons de TikTok)
            largeur = 670.0
        if (largeur - 28) * ih / iw + 66 > hauteur_max:  # trop haute : plus étroite, même proportion
            largeur = max(300.0, (hauteur_max - 66) * iw / ih + 28)
        hauteur = (largeur - 28) * ih / iw + 14 + 52
        rot = -1.5 if i % 2 == 0 else 1.2
        nom = f"{ident}-{i}.png"
        images.append((image, nom))
        corps.append(f'''<div id="{ident}-c{i}" class="{ident}-carte" style="left:110px; top:{y:.0f}px; width:{largeur:.0f}px">
      <img src="assets/captures/{nom}" alt="{e(legende)}" />
      <div class="{ident}-legende">{e(legende)}</div>
      <div id="{ident}-e{i}" class="{ident}-epingle"></div>
    </div>''')
        script.append(f'''    gsap.set("#{ident}-c{i}", {{ rotation: {rot} }});
    tl.fromTo("#{ident}-c{i}", {{ opacity: 0, y: -70, scale: 1.05, rotation: {rot - 6} }}, {{ opacity: 1, y: 0, scale: 1, rotation: {rot}, duration: 0.45, ease: "back.out(1.5)" }}, {t:.2f});
    pop("#{ident}-e{i}", {t + 0.38:.2f}, 0.25);''')
        reperes += [{"t": t + 0.3, "son": "paper-slide-1530", "gain_db": -9, "max_dur": 0.4, "secondaire": True, "pan": -0.05},
                    {"t": t + 0.45, "son": "click-metal-button-1830", "gain_db": -8, "secondaire": True}]
        y += hauteur + 40
        t += 0.8
    # les résultats en R, épinglés sous la photo comme des notes
    pastilles, bas = _rangee([(f"{ident}-n{k}", texte, fond, COUL["blanc"]) for k, (texte, fond) in enumerate(preuve["notes"])],
                             40, y + 6, ecart=22)
    for k in range(len(preuve["notes"])):
        script.append(f'''    gsap.set("#{ident}-n{k}", {{ rotation: {(-2, 1.5, -1)[k % 3]} }});
    pop("#{ident}-n{k}", {t + 0.35 * k:.2f}, 0.34, "0% 50%");''')
        reperes.append({"t": t + 0.35 * k + 0.1, "son": "@clic", "gain_db": -8, "max_dur": 0.25, "secondaire": True, "pan": -0.15 + 0.12 * k})
    style = f"""    #{ident}-nom {{ position: absolute; left: 120px; top: 340px; font-size: 92px; line-height: 1; }}
    .{ident}-carte {{ position: absolute; background: #ffffff; padding: 14px 14px 0; border-radius: 6px;
      box-shadow: 0 18px 40px rgba(24,34,46,0.28), 0 2px 6px rgba(24,34,46,0.18); }}
    .{ident}-carte img {{ display: block; width: 100%; border: 1px solid {COUL['grille']}; }}
    .{ident}-legende {{ font-size: 28px; line-height: 52px; color: {COUL['encre2']}; white-space: nowrap; }}
    .{ident}-epingle {{ position: absolute; left: 50%; top: -16px; width: 32px; height: 32px; margin-left: -16px; border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #8fbcf2 0, {COUL['bleu']} 45%, #1c4f8f 100%); box-shadow: 0 6px 10px rgba(0,0,0,0.35); }}"""
    html_ = f"""    <div class="date" id="{ident}-date">{e(date_txt)}</div>
    <div id="{ident}-nom">{e(titre)}</div>
    {chr(10).join(corps)}
    {pastilles}"""
    js = f"""    gsap.set(["#{ident}-date", "#{ident}-nom"], {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("[id^='{ident}-n']", {{ opacity: 0 }});
    wipe("#{ident}-date", 0.05);
    wipe("#{ident}-nom", 0.1, 0.32);
""" + "\n".join(script)
    return style, html_, js, reperes, t + 0.35 * len(preuve["notes"]) + 2.4, images


def nombres_tz():
    import journee
    return journee.NEW_YORK


# ───────────────────────── les sous-titres (V-14) ─────────────────────────
GRIS_A_DIRE = "#768396"          # un mot pas encore dit (contraste 3,6:1) ; il passe à l'encre quand la voix le dit


def scene_sous_titres(scenes):
    """V-14 (audit du 27/11/2026) : les sous-titres des scènes de marché, dans une seule composition (la piste « captions » de
    HyperFrames), sous le graphique et dans la zone sûre de TikTok (x de 124 à 780, sous les heures de l'axe). Un groupe à la fois,
    calé sur les mots de la voix (sous_titres.py), éteint d'un coup à sa fin ; aucun pendant le volet. Les scènes du titre, de la
    photo et du bilan montrent déjà à l'écran ce que dit la voix. scenes : [{"id", "debut", "duree", "rep", "offset"}] ; rend
    (style, corps, script, groupes) avec les instants dans le temps de la vidéo."""
    import sous_titres
    groupes, corps, script = [], [], []
    for s in scenes:
        rep, off = s.get("rep"), s.get("offset", 0.0)
        if not rep or not rep.get("mots"):
            continue
        mots = [dict(m, debut=m["debut"] + off, fin=m["fin"] + off) for m in rep["mots"]]
        liste = sous_titres.groupes(mots, POLICE, X_DROITE_BAS - 124, sous_titres.TAILLE)
        fin_scene = s["debut"] + s["duree"] - VOLET - 0.05
        for k, g in enumerate(liste):
            debut = max(s["debut"] + 0.15, s["debut"] + g["debut"] - 0.06)
            suivant = s["debut"] + liste[k + 1]["debut"] - 0.06 if k + 1 < len(liste) else fin_scene
            fin = min(max(s["debut"] + g["fin"] + 0.35, debut + 0.5), suivant, fin_scene)
            if fin - debut < 0.2:
                continue
            gid = f"st-{s['id']}-{k}"
            textes = [t for t, _ in g["jetons"]]
            html_lignes = "<br>".join(" ".join(f'<span id="{gid}-{i}" class="st-m">{e(textes[i])}</span>' for i in ligne)
                                      for ligne in g["lignes"])
            corps.append(f'<div id="{gid}" class="st-g" style="top:{Y_SOUS_TITRES}px">{html_lignes}</div>')
            script.append(f'    tl.set("#{gid}", {{ visibility: "visible" }}, {debut:.2f});\n'
                          f'    tl.to("#{gid}", {{ opacity: 1, duration: 0.08 }}, {debut:.2f});')
            for i, (_, t_mot) in enumerate(g["jetons"]):
                script.append(f'    tl.to("#{gid}-{i}", {{ color: "{COUL["encre"]}", duration: 0.06 }}, {max(debut, s["debut"] + t_mot):.2f});')
            script.append(f'    tl.to("#{gid}", {{ opacity: 0, duration: 0.1, ease: "power2.in" }}, {fin - 0.1:.2f});\n'
                          f'    tl.set("#{gid}", {{ opacity: 0, visibility: "hidden" }}, {fin:.2f});')
            groupes.append({"id": gid, "texte": " ".join(textes), "lignes": [" ".join(textes[i] for i in l) for l in g["lignes"]],
                            "taille": sous_titres.TAILLE, "haut": Y_SOUS_TITRES, "debut": round(debut, 3), "fin": round(fin, 3)})
    style = f"""    .st-g {{ position: absolute; left: 124px; width: {X_DROITE_BAS - 124}px; font-size: {sous_titres.TAILLE}px; line-height: 1.2;
      white-space: nowrap; color: {GRIS_A_DIRE}; opacity: 0; visibility: hidden; }}"""
    return style, "\n    ".join(corps), "\n".join(script), groupes


# ───────────────────────── fabrication ─────────────────────────
VOLET = 0.17       # le volet bleu qui passe entre deux scènes : il couvre l'écran 0,17 s avant la coupe et repart en 0,2 s


def couverture_titre(titre):
    """V-21 : l'instant de la couverture, l'écran titre posé (le tampon de la couleur fini), toujours avant le volet."""
    return round(max(0.5, min(titre["fin_min"] - 1.1, titre["duree"] - VOLET - 0.15)), 3)


def _index(scenes, duree, sous_titres=False):
    hotes = []
    for i, s in enumerate(scenes):
        hotes.append(f'      <div id="{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
                     f'data-start="{s["debut"]:.3f}" data-duration="{s["duree"]:.3f}" data-track-index="{i + 1}" data-track-kind="graphics" '
                     f'data-width="1080" data-height="1920" style="z-index: {i + 2}"></div>')
    if sous_titres:                 # V-14 : un seul hôte pour tous les sous-titres (piste « captions »), sous le volet
        hotes.append(f'      <div id="sous-titres" data-composition-id="sous-titres" data-composition-src="compositions/sous-titres.html" '
                     f'data-start="0" data-duration="{duree:.3f}" data-track-index="{len(scenes) + 2}" data-track-kind="captions" '
                     f'data-width="1080" data-height="1920" style="z-index: 30"></div>')
    coupes = [s["debut"] for s in scenes[1:]]
    volets = "\n".join(f'      tl.to("#volet-panneau", {{ xPercent: 0, duration: {VOLET}, ease: "power2.in" }}, {c - VOLET:.3f});\n'
                       f'      tl.to("#volet-panneau", {{ xPercent: 115, duration: 0.2, ease: "power2.out" }}, {c:.3f});\n'
                       f'      tl.set("#volet-panneau", {{ xPercent: -115 }}, {c + 0.21:.3f});' for c in coupes)
    return f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      /* Étrave, la carte marine : papier, encre, bleu du logo. */
      {POLICE_CSS}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: {COUL['papier']}; }}
      #root {{ position: relative; width: 100%; height: 100%; font-family: "DIN Etrave", sans-serif; }}
      #fond {{ position: absolute; inset: 0; background-color: {COUL['papier']};
        background-image: linear-gradient({COUL['grille']} 2px, transparent 2px), linear-gradient(90deg, {COUL['grille']} 2px, transparent 2px);
        background-size: 90px 90px; background-position: 42px 40px; }}
      #volet {{ position: absolute; inset: 0; overflow: hidden; pointer-events: none; }}
      #volet-panneau {{ position: absolute; left: -420px; top: 0; width: 1920px; height: 1920px; background: {COUL['bleu']}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duree:.3f}" data-width="1080" data-height="1920">
      <div id="fond" class="clip" data-start="0" data-duration="{duree:.3f}" data-track-index="0" data-layout-ignore></div>
{chr(10).join(hotes)}
      <div id="volet" class="clip" data-start="0" data-duration="{duree:.3f}" data-track-index="{len(scenes) + 1}" data-layout-ignore style="z-index: 40"><div id="volet-panneau"></div></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      gsap.set("#volet-panneau", {{ xPercent: -115, skewX: -10 }});
{volets}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def fabriquer(j, config, dossier_sortie, journal=print, rendre=True, exiger_voix=True):
    """Écrit le projet HyperFrames, le rend, pose la voix, les bruitages et la musique. Rend le chemin de la vidéo finale (avec
    rendre=False : s'arrête au projet écrit, pour le regarder dans HyperFrames, et rend son dossier). exiger_voix : une voix
    indisponible lève VoixIndisponible au lieu de faire une vidéo muette (VID-03 ; VID-18 : par défaut, seul --sans-voix l'ôte)."""
    global POLICE
    unite = unite_du_jour(j, config.get("unite", "auto"))
    textes = repliques(j, unite)
    # une seule prise pour toute la vidéo (la même voix d'un bout à l'autre), coupée par scène, puis rythmée
    reps, sans_voix = [], None
    try:
        reps = [voix.rythmer(r, config.get("voix_tempo", voix.TEMPO), config.get("voix_pause_max", voix.PAUSE_MAX))
                for r in voix.recit(textes, config)]
    except voix.VoixIndisponible as err:
        if exiger_voix:
            raise
        sans_voix, reps = f"{err} : vidéo sans voix (--sans-voix).", [None] * len(textes)
    voix.controle_pistes(reps if exiger_voix else [])
    if sans_voix:
        journal(sans_voix)
    police_fichier = os.path.expanduser(config.get("police", police.DEFAUT))
    if not os.path.exists(police_fichier):
        raise FileNotFoundError(f"Police DIN introuvable : {police_fichier} (réglage « police » de la configuration).")
    POLICE = police_fichier
    projet = os.path.join(dossier_sortie, "projet")
    if os.path.isdir(projet):
        shutil.rmtree(projet)
    os.makedirs(os.path.join(projet, "compositions"))
    os.makedirs(os.path.join(projet, "assets", "fonts"))
    shutil.copy(police_fichier, os.path.join(projet, "assets", "fonts", "din-alternate-bold.ttf"))
    # durées : la réplique posée peu après le début de la scène, puis un temps pour lire ; une scène dure au moins jusqu'à la fin
    # de ses mouvements (fin_min rendue par la scène)
    offset = [0.15] + [0.25] * (len(textes) - 1)
    preuve = len(textes) - len(j["marches"]) - 2         # 1 si la scène des captures est là
    minimum = [2.6] + [5.0] * len(j["marches"]) + [4.0] * preuve + [5.5 if not sans_voix else 7.5]
    queue = [0.35] + [0.6] * len(j["marches"]) + [0.6] * preuve + [2.0]
    scenes, reperes, debut, r_explique = [], [], 0.0, False
    for i, t in enumerate(textes):
        r = reps[i]
        d = max(minimum[i], offset[i] + (r["duree"] if r else 0) + queue[i])
        preuve = bool(preuve_du_jour(j, unite))
        ident = ("titre" if i == 0 else "bilan" if i == len(textes) - 1 else "preuve" if preuve and i == len(textes) - 2
                 else f"m{i - 1}")
        # les mots sont décalés de l'offset de la réplique : une scène lit les instants dans son propre temps
        rep = dict(r, mots=[dict(m, debut=m["debut"] + offset[i]) for m in r["mots"]]) if r else None
        if ident == "preuve":
            style, corps, script, rs, fin_min, images = scene_preuve("pv", preuve_du_jour(j, unite), rep, nombres.date_courte(j["jour"]))
            os.makedirs(os.path.join(projet, "assets", "captures"), exist_ok=True)
            for source, nom in images:
                shutil.copy(source, os.path.join(projet, "assets", "captures", nom))
        elif ident == "titre":
            style, corps, script, rs, fin_min = scene_titre(j, rep, unite)
        elif ident == "bilan":
            style, corps, script, rs, fin_min = scene_bilan(j, rep, unite, t)
        else:
            m = j["marches"][i - 1]
            expliquer = unite == "r" and not r_explique and bool(m["positions"]) and valeur(m, unite) is not None
            r_explique = r_explique or expliquer
            style, corps, script, rs, fin_min = scene_marche(j, m, i - 1, rep, unite, d, expliquer,
                                                             j["marches"][i - 2] if i >= 2 else None)
        d = round(max(d, fin_min), 3)
        with open(os.path.join(projet, "compositions", ident + ".html"), "w", encoding="utf-8") as f:
            f.write(_composition(ident, style, corps, script))
        reperes += [dict(x, t=round(debut + x["t"], 3)) for x in rs if x["t"] < d]
        scenes.append({"id": ident, "debut": round(debut, 3), "duree": d, "texte": t, "rep": r, "offset": offset[i], "fin_min": fin_min})
        debut += d
    duree = round(debut, 3)
    for k, s in enumerate(scenes[1:]):            # le volet entre deux scènes : son pic sur la coupe (V-15), prises en rotation (V-17)
        reperes.append({"t": round(s["debut"], 3), "son": "@volet", "gain_db": -11, "pan": 0.15 if k % 2 else -0.15})
    distribuer_prises(reperes)
    st_style, st_corps, st_script, groupes = scene_sous_titres([s for s in scenes if s["id"].startswith("m")])
    if groupes:
        with open(os.path.join(projet, "compositions", "sous-titres.html"), "w", encoding="utf-8") as f:
            f.write(_composition("sous-titres", st_style, "    " + st_corps, st_script))
    with open(os.path.join(projet, "index.html"), "w", encoding="utf-8") as f:
        f.write(_index(scenes, duree, bool(groupes)))
    json.dump({"jour": j["jour"].isoformat(), "source": j["source"], "unite": unite, "duree": duree,
               "couverture": couverture_titre(scenes[0]),
               "scenes": [{k: s[k] for k in ("id", "debut", "duree", "texte")} for s in scenes],
               "bruitages": sorted(reperes, key=lambda r: r["t"])},
              open(os.path.join(dossier_sortie, "recap.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not rendre:
        return projet
    journal(f"Rendu de l'image ({duree:.1f} s)…")
    muette = os.path.abspath(os.path.join(dossier_sortie, "image-muette.mp4"))
    executer(HYPERFRAMES + ["render", "--quality", "delivery", "--output", muette], projet, DELAI_RENDU, "rendu HyperFrames")
    travail = os.path.join(dossier_sortie, "son")
    os.makedirs(travail, exist_ok=True)
    piste_v = mixage.piste_voix([{"fichier": s["rep"]["fichier"], "t": s["debut"] + s["offset"]} for s in scenes if s["rep"]],
                                duree, os.path.join(travail, "voix.wav"))
    piste_b, manquants = mixage.piste_bruitages(reperes, config.get("sons"), duree, os.path.join(travail, "bruitages.wav"), caler=True)
    if manquants:
        journal(f"{len(manquants)} bruitage(s) absent(s) du dossier de sons ({', '.join(manquants[:4])}…) : `outil.py sons` les télécharge.")
    piste_m = mixage.piste_musique(config.get("musique"), j["jour"], duree, os.path.join(travail, "musique.wav"), journal)
    nom = f"recap-{j['jour'].isoformat()}.mp4"
    finale = os.path.join(dossier_sortie, nom)
    mixage.assembler(muette, piste_v, piste_b, finale, travail, piste_m)
    import controle
    controle.verifier(finale, travail, journal)          # VID-30 : prévient, ne bloque pas
    return finale
