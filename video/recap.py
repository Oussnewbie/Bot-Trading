"""La vidéo récap d'une séance : titre (la date), une scène par marché (le graphique du jour, la zone de 15:30, les entrées et les
sorties, le résultat), puis le bilan. Même habillage que la présentation : la carte marine d'Étrave, DIN, bleu du logo, coupes franches.

Tout se cale sur la voix : la durée de chaque scène vient de la durée de sa réplique, et les entrées, le résultat et les bruitages
tombent sur le mot qui les dit (heure de chaque mot rendue par ElevenLabs). Sans voix, des durées fixes.

Ce qui reste secret ne sort pas : ni le type d'entrée (seulement « Achat » ou « Vente »), ni les filtres, ni la raison d'un jour
sans trade. Une journée du testeur porte une mention « Exemple » incrustée : elle ne peut pas passer pour une séance réelle.
"""
import html
import json
import os
import shutil
import subprocess

import mixage
import nombres
import voix

ICI = os.path.dirname(os.path.abspath(__file__))
HYPERFRAMES = ["npx", "-y", "hyperframes@0.9.94"]
# Zones sûres de TikTok en 1080 x 1920 (celles du contrôle HyperFrames) : le texte entre y = 240 et y = 1260 ; sous y = 840, rien à
# droite de x = 780 (les boutons j'aime, commentaires, partage). Le graphique s'arrête donc à x = 780 : la fin de séance reste visible.
X0, X1, Y_HAUT, Y_BAS = 120, 780, 655, 925          # le graphique
LIGNES_MAX = 4                                       # lignes de positions sous le graphique (au-delà : « et N autres positions »)
COUL = {"papier": "#f6f8fa", "eau": "#e2edf5", "grille": "#dde4ea", "axe": "#94a3b2", "encre": "#18222e", "encre2": "#46546a",
        "bleu": "#2f7bd9"}
POLICE_CSS = '@font-face { font-family: "DIN Etrave"; src: url("assets/fonts/din-alternate-bold.ttf") format("truetype"); font-weight: 700; }'
ESSUIE = ('const wipe = (cible, t, d = 0.3) => tl.fromTo(cible, { clipPath: "inset(-30% 100% -40% 0)" }, '
          '{ clipPath: "inset(-30% 0% -40% 0)", duration: d, ease: "power3.out" }, t);')
V_ETRAVE = "M8 8c1.8 9.5 5.8 17.5 12 24 6.2-6.5 10.2-14.5 12-24"
TIGE, VAGUES = "M20 5v27", "M3 33c2.8-2.3 5.7-2.3 8.5 0M28.5 33c2.8-2.3 5.7-2.3 8.5 0"


def e(texte):
    return html.escape(str(texte), quote=True)


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
              "Une séance qui forge le caractère.", "Les pertes font partie du jeu. On les montre aussi."],
    "gain": ["Le robot a bien travaillé. Moi, j'ai surtout regardé.", "Belle séance, sans forcer.",
             "Le robot a fait sa part. On reste humble."],
    "rien": ["Pas de trade, pas de perte : parfois, attendre, c'est aussi trader.", "Le robot a préféré observer."],
}


def mot_du_jour(j, t):
    cas = "rien" if not j["trades"] else ("gain" if (t if t is not None else (j["net"] or 0)) > 0 else "perte")
    liste = MOTS_DU_JOUR[cas]
    return liste[j["jour"].toordinal() % len(liste)]


def _une(n, mot_feminin=False):
    return ("une" if mot_feminin else "un") if n == 1 else nombres.entier(n)


def description(m):
    """Ce qui s'est passé sur le marché, en mots simples, sans rien dire de la méthode : côté de la sortie de zone, positions,
    stops touchés et sorties en fin de séance. Rend (phrase de la voix, ligne de l'écran)."""
    ps = m["positions"]
    p = ps[0]
    cote = "par le haut" if p["sens"] == 1 else "par le bas"
    he = nombres.heure(p["entree"].hour, p["entree"].minute) if p["entree"] else ""
    ecran_txt = f"Sortie de zone {cote} à {p['entree']:%H:%M}" if p["entree"] else f"Sortie de zone {cote}"
    stops = sum(1 for x in ps if x["raison"].lower().startswith("stop"))
    fins = sum(1 for x in ps if x["raison"].lower().startswith("fin de journ"))
    if len(ps) == 1:
        hs = nombres.heure(p["sortie"].hour, p["sortie"].minute) if p["sortie"] else ""
        fin = (f"Le stop est touché à {hs}." if stops else f"Sortie en fin de séance, à {hs}." if fins else f"Sortie à {hs}.")
        return f"le prix sort de la zone {cote} à {he} : {sens_mot(p)}. {fin}", ecran_txt
    sens = {x["sens"] for x in ps}
    quoi = (f"{_une(len(ps), True)} positions {'à l' + chr(39) + 'achat' if p['sens'] == 1 else 'à la vente'}" if len(sens) == 1
            else f"{_une(len(ps), True)} positions, à l'achat et à la vente")
    issues = []
    if stops:
        issues.append(f"{_une(stops)} stop{'s' if stops > 1 else ''} touché{'s' if stops > 1 else ''}")
    if fins:
        issues.append(f"{_une(fins, True)} sortie{'s' if fins > 1 else ''} en fin de séance")
    autres = len(ps) - stops - fins
    if autres:
        issues.append(f"{_une(autres, True)} autre{'s' if autres > 1 else ''} sortie{'s' if autres > 1 else ''}")
    return f"le prix sort de la zone {cote} à {he}. {quoi[0].upper() + quoi[1:]} : {', '.join(issues)}.", ecran_txt


def valeur(m, unite):
    return {"pourcent": m.get("pct"), "r": m.get("r"), "points": m.get("points")}[unite]


def ecran(v, unite):
    if v is None:
        return ""
    if unite == "pourcent":
        return nombres.nombre_ecran(v, 2) + " %"
    if unite == "r":
        return nombres.nombre_ecran(v, 2) + " R"
    return nombres.nombre_ecran(v, 1) + " pts"


def dit(v, unite):
    if v is None:
        return ""
    if unite == "pourcent":
        return nombres.decimal(v, 2, signe=True) + " pour cent"
    if unite == "r":
        return nombres.decimal(v, 2, signe=True) + " R"
    return nombres.decimal(v, 1, signe=True) + " points"


def total(j, unite):
    """Le total de la journée, tous marchés : en % ou en R (des points du Nasdaq et du S&P ne s'additionnent pas)."""
    if unite == "points":
        return None
    vals = [valeur(m, unite) for m in j["marches"] if m["positions"]]
    if not vals or any(v is None for v in vals):
        return None
    # la somme des valeurs telles qu'elles sont affichées : −1,50 R et −0,56 R font −2,06 R à l'écran comme à la voix
    return round(sum(round(v, 2) for v in vals), 2)


def sens_mot(p):
    return "achat" if p["sens"] == 1 else "vente"


def repliques(j, unite):
    """Le texte de chaque scène, dans l'ordre : titre, un par marché, bilan. Heures et nombres en lettres."""
    textes = [f"Récap de la séance du {nombres.date_longue(j['jour'])}."]
    r_explique = False
    for m in j["marches"]:
        ps = m["positions"]
        if not ps:
            textes.append(f"{m['voix']} : pas de trade aujourd'hui, les conditions n'étaient pas réunies.")
            continue
        phrase, _ = description(m)
        res = dit(valeur(m, unite), unite)
        texte = f"{m['voix']} : {phrase} Résultat : {res}."
        if unite == "r" and not r_explique:
            texte += " Un R, c'est le risque pris sur un trade."
            r_explique = True
        textes.append(texte)
    t = total(j, unite)
    mot = mot_du_jour(j, t)
    if not j["trades"]:
        textes.append(f"Bilan : pas de trade aujourd'hui. {mot} Chaque séance est sur le Telegram, lien en bio.")
    elif t is not None:
        textes.append(f"Bilan du jour : {dit(t, unite)}. {mot} Chaque séance est sur le Telegram, lien en bio.")
    else:
        textes.append(f"Bilan : journée {j['verdict'] or 'terminée'}. {mot} Chaque séance est sur le Telegram, lien en bio.")
    return textes


# ───────────────────────── les scènes ─────────────────────────
def _composition(ident, style, corps, script):
    return f"""<template>
  <style>
    {POLICE_CSS}
    #root {{ position: absolute; inset: 0; font-family: "DIN Etrave", sans-serif; color: {COUL['encre']}; }}
    .date {{ position: absolute; left: 124px; top: 300px; font-size: 38px; color: {COUL['encre2']}; }}
    svg.plan {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: visible; }}
    svg.plan text {{ font-family: "DIN Etrave", sans-serif; }}
{style}
  </style>
  <div id="root" data-composition-id="{ident}" data-width="1080" data-height="1920">
{corps}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {ESSUIE}
{script}
    window.__timelines["{ident}"] = tl;
  </script>
</template>
"""


def scene_titre(j, rep):
    jour_sem, jour_mois, annee = nombres.date_ecran(j["jour"])
    t_date = voix.instant(rep, nombres.JOURS[j["jour"].weekday()], defaut=0.9)
    style = f"""    #ti-logo {{ position: absolute; left: 100px; top: 290px; width: 180px; height: 180px; overflow: visible; }}
    .ti-ligne {{ position: absolute; left: 120px; line-height: 1; }}
    #ti-recap {{ top: 490px; font-size: 56px; color: {COUL['encre2']}; }}
    #ti-jour {{ top: 566px; font-size: 92px; }}
    #ti-date {{ top: 666px; font-size: 132px; }}
    #ti-annee {{ top: 836px; font-size: 92px; color: {COUL['encre2']}; }}"""
    corps = f"""    <svg id="ti-logo" viewBox="0 0 40 40">
      <path id="ti-v" d="{V_ETRAVE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
      <path id="ti-tige" d="{TIGE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" />
      <path id="ti-vagues" d="{VAGUES}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" opacity="0.55" />
    </svg>
    <div id="ti-recap" class="ti-ligne">Récap de la séance</div>
    <div id="ti-jour" class="ti-ligne">{e(jour_sem)}</div>
    <div id="ti-date" class="ti-ligne">{e(jour_mois)}</div>
    <div id="ti-annee" class="ti-ligne">{e(annee)}</div>"""
    script = f"""    const traits = ["#ti-tige", "#ti-v", "#ti-vagues"].map((id) => document.querySelector(id));
    traits.forEach((p) => {{ const l = p.getTotalLength(); gsap.set(p, {{ strokeDasharray: l, strokeDashoffset: l, opacity: 0 }}); }});
    gsap.set(".ti-ligne", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    // le bout arrondi d'un trait pas encore tracé ferait un point : le trait n'apparaît qu'au début de son tracé
    traits.forEach((p, i) => {{ tl.set(p, {{ opacity: i === 2 ? 0.55 : 1 }}, 0.05 + i * 0.22); tl.to(p, {{ strokeDashoffset: 0, duration: 0.4, ease: "power1.inOut" }}, 0.05 + i * 0.22); }});
    wipe("#ti-recap", 0.2);
    wipe("#ti-jour", {t_date:.2f});
    wipe("#ti-date", {t_date + 0.25:.2f}, 0.4);
    wipe("#ti-annee", {t_date + 0.5:.2f});"""
    reperes = [{"t": 0.05, "son": "swoosh-fast-transitions-3115", "gain_db": -6},
               {"t": 0.62, "son": "water-splash-1311", "gain_db": -10, "max_dur": 1.2},
               {"t": t_date + 0.25, "son": "typewriter-mechanical-hit-1365", "gain_db": -5}]
    return style, corps, script, reperes


def _echelles(m):
    b = m["bougies"]
    prix = [x for c in b for x in (c["h"], c["l"]) if x is not None]
    for p in m["positions"]:
        prix += [x for x in (p["prix_entree"], p["prix_sortie"]) if x is not None]
    if m["zone"]:
        prix += [m["zone"]["bas"], m["zone"]["haut"]]
    bas, haut = min(prix), max(prix)
    marge = (haut - bas) * 0.06 or 1
    bas, haut = bas - marge, haut + marge
    pas = (X1 - X0) / max(1, len(b))

    def y(p):
        return Y_BAS - (p - bas) / (haut - bas) * (Y_BAS - Y_HAUT)

    def x(instant):
        if instant is None:
            return None
        i = max(0, sum(1 for c in b if c["heure"] <= instant) - 1)
        fraction = min(1.0, max(0.0, (instant - b[i]["heure"]).total_seconds() / 300))
        return X0 + pas * (i + fraction)
    return x, y, pas


def scene_marche(j, m, k, rep, unite, duree):
    ident = f"m{k}"
    x, y, pas = _echelles(m)
    b = m["bougies"]
    corps_b = []
    for i, c in enumerate(b):
        cx = X0 + pas * (i + 0.5)
        haussiere = c["c"] >= c["o"]
        coul = COUL["axe"] if haussiere else COUL["encre2"]
        haut_corps, bas_corps = y(max(c["o"], c["c"])), y(min(c["o"], c["c"]))
        corps_b.append(f'<g class="{ident}-b"><line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(c["h"]):.1f}" y2="{y(c["l"]):.1f}" stroke="{coul}" stroke-width="2" />'
                       f'<rect x="{cx - max(1.5, pas * 0.31):.1f}" y="{haut_corps:.1f}" width="{max(3, pas * 0.62):.1f}" height="{max(2, bas_corps - haut_corps):.1f}" fill="{coul}" /></g>')
    # la zone de 15:30 : de la bougie de l'ouverture jusqu'au bout de la séance
    ouverture = next((i for i, c in enumerate(b) if c["heure"].astimezone(nombres_tz()).strftime("%H:%M") == "09:30"), None)
    zone = ""
    if m["zone"] and ouverture is not None:
        zx, zh, zb = X0 + pas * ouverture, y(m["zone"]["haut"]), y(m["zone"]["bas"])
        zone = (f'<g id="{ident}-zone"><rect x="{zx:.1f}" y="{zh:.1f}" width="{X1 - zx:.1f}" height="{zb - zh:.1f}" fill="{COUL["eau"]}" />'
                f'<line x1="{zx:.1f}" x2="{X1}" y1="{zh:.1f}" y2="{zh:.1f}" stroke="{COUL["encre2"]}" stroke-width="3" stroke-dasharray="14 10" />'
                f'<line x1="{zx:.1f}" x2="{X1}" y1="{zb:.1f}" y2="{zb:.1f}" stroke="{COUL["encre2"]}" stroke-width="3" stroke-dasharray="14 10" /></g>')
    # les heures sous le graphique : l'ouverture et les heures paires, sans chevauchement
    etiquettes, derniere = [], -999
    for i, c in enumerate(b):
        h = c["heure"]
        if (i == ouverture or (h.minute == 0 and h.hour % 2 == 0)) and X0 + pas * i - derniere > 110:
            derniere = X0 + pas * i
            etiquettes.append(f'<text x="{derniere:.1f}" y="{Y_BAS + 52}" font-size="30" fill="{COUL["encre2"]}" text-anchor="middle">{h:%H:%M}</text>')
    # les positions : triangle d'entrée (bleu pour un achat, encre pour une vente), rond de sortie, trait entre les deux
    marques, lignes_txt, dessinees = [], [], []
    montrees = len(m["positions"]) if len(m["positions"]) <= LIGNES_MAX else LIGNES_MAX - 1
    for i, p in enumerate(m["positions"]):
        xe, xs = x(p["entree"]), x(p["sortie"])
        if xe is None or p["prix_entree"] is None:
            continue
        ye = y(p["prix_entree"])
        coul = COUL["bleu"] if p["sens"] == 1 else COUL["encre"]
        tri = (f"{xe:.1f},{ye + 4:.1f} {xe - 13:.1f},{ye + 28:.1f} {xe + 13:.1f},{ye + 28:.1f}" if p["sens"] == 1
               else f"{xe:.1f},{ye - 4:.1f} {xe - 13:.1f},{ye - 28:.1f} {xe + 13:.1f},{ye - 28:.1f}")
        sortie = ""
        if xs is not None and p["prix_sortie"] is not None:
            ys = y(p["prix_sortie"])
            sortie = (f'<line class="{ident}-trait" x1="{xe:.1f}" y1="{ye:.1f}" x2="{xs:.1f}" y2="{ys:.1f}" stroke="{COUL["encre2"]}" stroke-width="2" stroke-dasharray="6 6" />'
                      f'<circle class="{ident}-sortie" cx="{xs:.1f}" cy="{ys:.1f}" r="9" fill="{COUL["papier"]}" stroke="{COUL["encre"]}" stroke-width="4" />')
        marques.append(f'<g id="{ident}-p{i}">{sortie}<polygon class="{ident}-entree" points="{tri}" fill="{coul}" /></g>')
        dessinees.append(i)
        if i < montrees:
            pts = "" if p["points"] is None else nombres.nombre_ecran(p["points"], 1) + " pts"
            heures = f'{p["entree"]:%H:%M} – {p["sortie"]:%H:%M}' if p["sortie"] else f'{p["entree"]:%H:%M}'
            stop = p["raison"].lower().startswith("stop")
            lignes_txt.append(f'<div id="{ident}-l{i}" class="{ident}-ligne" style="top:{1055 + 46 * i}px">'
                              f'<span class="sens">{"Achat" if p["sens"] == 1 else "Vente"}</span><span class="heures">{e(heures)}</span>'
                              f'<span class="tag">{"stop" if stop else ""}</span><span class="pts">{e(pts)}</span></div>')
    autres = len(m["positions"]) - montrees
    if autres > 0:
        lignes_txt.append(f'<div id="{ident}-autres" class="{ident}-ligne" style="top:{1055 + 46 * montrees}px; color:{COUL["encre2"]}">'
                          f'et {autres} autre{"s" if autres > 1 else ""} position{"s" if autres > 1 else ""}</div>')
    desc = ""
    if m["positions"]:
        desc = f'<div id="{ident}-desc" class="desc">{e(description(m)[1])}</div>'
    legende = []
    if m["positions"]:
        yl = Y_BAS + 92
        legende += [f'<polygon points="124,{yl - 22} 112,{yl} 136,{yl}" fill="{COUL["bleu"]}" /><text x="146" y="{yl}" font-size="28" fill="{COUL["encre2"]}">achat</text>',
                    f'<polygon points="248,{yl} 236,{yl - 22} 260,{yl - 22}" fill="{COUL["encre"]}" /><text x="270" y="{yl}" font-size="28" fill="{COUL["encre2"]}">vente</text>',
                    f'<circle cx="368" cy="{yl - 10}" r="9" fill="{COUL["papier"]}" stroke="{COUL["encre"]}" stroke-width="4" /><text x="386" y="{yl}" font-size="28" fill="{COUL["encre2"]}">sortie</text>']
    if zone:
        x_z = 476 if m["positions"] else 124
        yl = Y_BAS + 92
        legende.append(f'<rect x="{x_z}" y="{yl - 22}" width="34" height="22" fill="{COUL["eau"]}" stroke="{COUL["encre2"]}" stroke-width="2" stroke-dasharray="6 4" />'
                       f'<text x="{x_z + 44}" y="{yl}" font-size="28" fill="{COUL["encre2"]}">zone de {b[ouverture]["heure"]:%H:%M}</text>')
    v = valeur(m, unite)
    rappel = ""
    if m["positions"] and unite == "r":
        rappel = '<div id="%s-rappel" class="rappel">1 R = le risque<br>pris sur un trade</div>' % ident
    resultat = ""
    if m["positions"] and v is not None:
        resultat = f'<div id="{ident}-res" class="res" style="color:{COUL["bleu"] if v >= 0 else COUL["encre"]}">{e(ecran(v, unite))}</div>'
    sans = ""
    if not m["positions"]:
        sans = (f'<div id="{ident}-sans1" class="{ident}-sans" style="top:1055px; font-size:52px">Pas de trade aujourd\'hui.</div>'
                f'<div id="{ident}-sans2" class="{ident}-sans" style="top:1125px; font-size:36px; color:{COUL["encre2"]}">Les conditions n\'étaient pas réunies.</div>')
    style = f"""    #{ident}-nom {{ position: absolute; left: 120px; top: 345px; font-size: 96px; line-height: 1; }}
    #{ident} .desc, #{ident}-desc {{ position: absolute; left: 124px; top: 452px; font-size: 40px; color: {COUL['encre2']}; }}
    #{ident} .res, #{ident}-res {{ position: absolute; left: 120px; top: 506px; font-size: 112px; line-height: 1; }}
    #{ident}-rappel {{ position: absolute; left: 620px; top: 520px; font-size: 30px; line-height: 1.25; color: {COUL['encre2']}; }}
    .{ident}-ligne {{ position: absolute; left: 124px; font-size: 36px; line-height: 1; display: flex; gap: 0; }}
    .{ident}-ligne .sens {{ width: 110px; }}
    .{ident}-ligne .heures {{ width: 215px; color: {COUL['encre2']}; }}
    .{ident}-ligne .tag {{ width: 80px; color: {COUL['encre2']}; }}
    .{ident}-sans {{ position: absolute; left: 124px; line-height: 1; }}"""
    corps = f"""    <div class="date" id="{ident}-date">{e(nombres.date_courte(j['jour']))}</div>
    <div id="{ident}-nom">{e(m['nom'])}</div>
    {desc}
    {resultat}
    {rappel}
    <svg class="plan" viewBox="0 0 1080 1920" data-layout-allow-overflow>
      <line id="{ident}-axe" x1="{X0}" x2="{X1}" y1="{Y_BAS + 12}" y2="{Y_BAS + 12}" stroke="{COUL['axe']}" stroke-width="3" />
      <g id="{ident}-heures">{''.join(etiquettes)}</g>
      {zone}
      <g id="{ident}-bougies">{''.join(corps_b)}</g>
      <g id="{ident}-positions">{''.join(marques)}</g>
      <g id="{ident}-legende">{''.join(legende)}</g>
    </svg>
    {''.join(lignes_txt)}
    {sans}"""
    # le minutage : le graphique se dessine, les entrées tombent sur « achat » / « vente », le résultat sur « Résultat »
    debut_b, duree_b = 0.45, 1.5
    t_desc = voix.instant(rep, "prix", defaut=1.9)
    t_entree = voix.instant(rep, "achat", "vente", "positions", defaut=2.3)
    t_entree = max(t_entree, debut_b + duree_b + 0.1)
    # les sorties (ronds, traits, lignes du tableau) tombent sur « stop touché » / « sorties en fin de séance »
    t_sorties = voix.instant(rep, "stop", "sortie", defaut=t_entree + 1.2)
    t_sorties = max(t_sorties, t_entree + 0.22 * min(len(m["positions"]), 6) + 0.25)
    t_res = voix.instant(rep, "résultat", defaut=duree - 2.0)
    t_res = max(t_res + 0.55, t_sorties + 0.15 * min(len(m["positions"]), 6) + 0.4)
    t_zone = debut_b + duree_b * (ouverture or 0) / max(1, len(b)) + 0.15
    script = [f"""    gsap.set(["#{ident}-date", "#{ident}-nom", ".{ident}-ligne", ".{ident}-sans"], {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set(".{ident}-b", {{ opacity: 0, scaleY: 0.2, transformOrigin: "50% 50%" }});
    gsap.set("#{ident}-axe", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    gsap.set(["#{ident}-heures", "#{ident}-legende"], {{ opacity: 0 }});
    wipe("#{ident}-date", 0.05);
    wipe("#{ident}-nom", 0.12, 0.35);
    tl.to("#{ident}-axe", {{ scaleX: 1, duration: 0.5, ease: "power2.out" }}, 0.35);
    tl.to("#{ident}-heures", {{ opacity: 1, duration: 0.3 }}, 0.6);
    tl.to("#{ident}-legende", {{ opacity: 1, duration: 0.3 }}, {debut_b + duree_b:.2f});
    tl.to(".{ident}-b", {{ opacity: 1, scaleY: 1, duration: 0.16, ease: "power2.out", stagger: {duree_b / max(1, len(b)):.4f} }}, {debut_b});"""]
    if zone:
        script.append(f"""    gsap.set("#{ident}-zone", {{ scaleX: 0, transformOrigin: "{X0 + pas * (ouverture or 0):.1f}px 50%" }});
    tl.to("#{ident}-zone", {{ scaleX: 1, duration: 0.5, ease: "power1.inOut" }}, {t_zone:.2f});""")
    reperes = [{"t": 0.12, "son": "paper-quick-movement-2380", "gain_db": -8, "max_dur": 0.6},
               {"t": debut_b, "son": "tick-wall-clock-fast-1063", "gain_db": -12, "max_dur": duree_b}]
    if zone:
        reperes.append({"t": t_zone, "son": "whoosh-cinematic-fast-1492", "gain_db": -13, "max_dur": 0.7})
    for rang, i in enumerate(dessinees):
        te = t_entree + 0.22 * min(rang, 6)
        ts = t_sorties + 0.15 * min(rang, 6)
        script.append(f"""    gsap.set("#{ident}-p{i} .{ident}-entree", {{ opacity: 0, scale: 0.3, transformOrigin: "50% 50%" }});
    gsap.set(["#{ident}-p{i} .{ident}-trait", "#{ident}-p{i} .{ident}-sortie"], {{ opacity: 0 }});
    tl.to("#{ident}-p{i} .{ident}-entree", {{ opacity: 1, scale: 1, duration: 0.22, ease: "back.out(2)" }}, {te:.2f});
    tl.to(["#{ident}-p{i} .{ident}-trait", "#{ident}-p{i} .{ident}-sortie"], {{ opacity: 1, duration: 0.2 }}, {ts:.2f});""")
        if i < montrees:
            script.append(f'    wipe("#{ident}-l{i}", {ts:.2f});')
        if rang < 4:
            reperes.append({"t": te, "son": "click-select-1109", "gain_db": -7, "max_dur": 0.3})
            reperes.append({"t": ts, "son": "click-light-switch-2585", "gain_db": -10, "max_dur": 0.3})
    if autres > 0:
        script.append(f'    wipe("#{ident}-autres", {t_sorties + 0.15 * montrees + 0.1:.2f});')
    if desc:
        script.append(f"""    gsap.set("#{ident}-desc", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    wipe("#{ident}-desc", {max(t_desc, 0.5):.2f});""")
    if resultat:
        script.append(f"""    gsap.set("#{ident}-res", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    wipe("#{ident}-res", {t_res:.2f}, 0.35);""")
    if rappel:
        script.append(f"""    gsap.set("#{ident}-rappel", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    wipe("#{ident}-rappel", {max(t_res + 0.4, voix.instant(rep, "risque", defaut=t_res + 0.8) - 0.4):.2f});""")
        reperes.append({"t": t_res, "son": "hit-wood-hard-2182", "gain_db": -5, "passe_haut": 140})
    if sans:
        t_sans = voix.instant(rep, "pas", defaut=2.3)
        t_sans = max(t_sans, debut_b + duree_b)
        script.append(f'    wipe("#{ident}-sans1", {t_sans:.2f});\n    wipe("#{ident}-sans2", {voix.instant(rep, "conditions", defaut=t_sans + 1.0):.2f});')
    return style, corps, "\n".join(script), reperes


def scene_bilan(j, rep, unite, texte):
    t = total(j, unite)
    mot = mot_du_jour(j, t)
    k_mot = len(texte.split(mot)[0].split())          # le rang du premier mot du petit mot dans la réplique
    lignes, script, reperes = [], [], [{"t": 0.05, "son": "paper-page-turn-1104", "gain_db": -6}]
    for i, m in enumerate(j["marches"]):
        v = valeur(m, unite)
        txt = ecran(v, unite) if m["positions"] and v is not None else "pas de trade"
        coul = COUL["encre2"] if not m["positions"] or v is None else (COUL["bleu"] if v >= 0 else COUL["encre"])
        lignes.append(f'<div id="bi-l{i}" class="bi-ligne" style="top:{475 + 76 * i}px"><span class="nom">{e(m["nom"])}</span>'
                      f'<span style="color:{coul}">{e(txt)}</span></div>')
        script.append(f'    wipe("#bi-l{i}", {0.35 + 0.15 * i:.2f});')
    y_total = 475 + 76 * len(j["marches"]) + 30
    if t is not None:
        gros = f'<div id="bi-total-t" class="bi-label" style="top:{y_total}px">Total</div><div id="bi-total" class="bi-gros" style="top:{y_total + 54}px; color:{COUL["bleu"] if t >= 0 else COUL["encre"]}">{e(ecran(t, unite))}</div>'
        t_total = max(voix.instant(rep, "bilan", defaut=0.4) + 1.0, 0.9)
    else:
        verdict = "Pas de trade" if not j["trades"] else f"Journée {j['verdict'] or 'terminée'}"
        gros = f'<div id="bi-total" class="bi-gros" style="top:{y_total + 20}px; font-size:96px">{e(verdict)}</div>'
        t_total = max(voix.instant(rep, "journée", "pas", defaut=1.0), 0.9)
    if t is not None:
        script.append(f'    wipe("#bi-total-t", {t_total - 0.2:.2f});')
    script.append(f'    wipe("#bi-total", {t_total:.2f}, 0.4);')
    reperes.append({"t": t_total, "son": "hit-deep-heartbeat-498", "gain_db": -6, "passe_haut": 180, "max_dur": 1.3})
    mots = (rep or {}).get("mots", [])
    t_gains = mots[k_mot]["debut"] if len(mots) > k_mot else t_total + 1.2
    t_tel = voix.instant(rep, "telegram", defaut=t_gains + 1.2)
    t_bio = voix.instant(rep, "bio", defaut=t_tel + 0.8)
    y_bas = 880                    # le bas du bilan, sous la ligne y = 840 : rien à droite de x = 780
    style = f"""    #bi-titre {{ position: absolute; left: 120px; top: 345px; font-size: 96px; line-height: 1; }}
    .bi-ligne {{ position: absolute; left: 124px; font-size: 56px; line-height: 1; display: flex; }}
    .bi-ligne .nom {{ width: 380px; }}
    .bi-label {{ position: absolute; left: 124px; font-size: 40px; color: {COUL['encre2']}; }}
    .bi-gros {{ position: absolute; left: 120px; font-size: 128px; line-height: 1; }}
    .bi-bas {{ position: absolute; left: 124px; line-height: 1.15; width: 650px; }}
    #bi-mention {{ font-family: "Inter", sans-serif; font-weight: 400; font-size: 28px; line-height: 1.35; color: {COUL['encre2']}; }}"""
    corps = f"""    <div class="date" id="bi-date">{e(nombres.date_courte(j['jour']))}</div>
    <div id="bi-titre">Bilan du jour</div>
    {''.join(lignes)}
    {gros}
    <div id="bi-gains" class="bi-bas" style="top:{y_bas}px; font-size:44px; color:{COUL['encre2']}">{e(mot)}</div>
    <div id="bi-tel" class="bi-bas" style="top:{y_bas + 128}px; font-size:58px">Rejoins le Telegram :</div>
    <div id="bi-bio" class="bi-bas" style="top:{y_bas + 196}px; font-size:58px; color:{COUL['bleu']}">lien en bio</div>
    <div id="bi-mention" class="bi-bas" style="top:{y_bas + 278}px">Pas un conseil en investissement. Le trading comporte un risque de perte en capital.</div>"""
    script_tete = """    gsap.set(["#bi-date", "#bi-titre", ".bi-ligne", ".bi-label", ".bi-gros", "#bi-gains", "#bi-tel", "#bi-bio"], { clipPath: "inset(-30% 100% -40% 0)" });
    gsap.set("#bi-mention", { opacity: 0 });
    wipe("#bi-date", 0.05);
    wipe("#bi-titre", 0.12, 0.35);"""
    script.append(f"""    wipe("#bi-gains", {t_gains:.2f});
    wipe("#bi-tel", {t_tel - 0.1:.2f});
    wipe("#bi-bio", {t_bio:.2f});
    tl.to("#bi-mention", {{ opacity: 1, duration: 0.3 }}, {t_tel:.2f});""")      # la mention reste au moins 3,5 s à l'écran
    reperes.append({"t": t_bio, "son": "bell-notification-933", "gain_db": -6, "max_dur": 2.0})
    return style, corps, script_tete + "\n" + "\n".join(script), reperes


def nombres_tz():
    import journee
    return journee.NEW_YORK


# ───────────────────────── fabrication ─────────────────────────
def _index(scenes, duree, exemple):
    hotes = []
    for i, s in enumerate(scenes):
        hotes.append(f'      <div id="{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
                     f'data-start="{s["debut"]:.3f}" data-duration="{s["duree"]:.3f}" data-track-index="{i + 1}" data-track-kind="graphics" '
                     f'data-width="1080" data-height="1920" style="z-index: {i + 2}"></div>')
    bandeau = ""
    if exemple:
        bandeau = (f'      <div id="exemple" class="clip" data-start="0" data-duration="{duree:.3f}" data-track-index="{len(scenes) + 1}" '
                   f'style="z-index: 50">Exemple : journée du testeur, pas un trade réel.</div>')
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
      /* la mention des journées du testeur : en haut de la zone sûre de TikTok, au-dessus de la date */
      #exemple {{ position: absolute; left: 120px; top: 238px; padding: 6px 16px; border: 3px solid {COUL['encre']};
        background: {COUL['papier']}; font-size: 30px; line-height: 1.2; color: {COUL['encre']}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duree:.3f}" data-width="1080" data-height="1920">
      <div id="fond" class="clip" data-start="0" data-duration="{duree:.3f}" data-track-index="0" data-layout-ignore></div>
{chr(10).join(hotes)}
{bandeau}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""


def fabriquer(j, config, dossier_sortie, journal=print):
    """Écrit le projet HyperFrames, le rend, pose la voix et les bruitages. Rend le chemin de la vidéo finale."""
    unite = unite_du_jour(j, config.get("unite", "auto"))
    textes = repliques(j, unite)
    reps, sans_voix = [], None
    for i, t in enumerate(textes):
        try:
            reps.append(voix.replique(t, config, textes[i - 1] if i else "", textes[i + 1] if i + 1 < len(textes) else ""))
        except voix.VoixIndisponible as err:
            sans_voix, reps = str(err), [None] * len(textes)
            break
    if sans_voix:
        journal(sans_voix)
    # durées : la réplique posée à 0,3 s du début de la scène, puis un temps pour lire
    offset = [0.25] + [0.3] * (len(textes) - 1)
    minimum = [3.0] + [6.5] * len(j["marches"]) + [5.5 if not sans_voix else 7.5]   # sans voix : 2 s pour lire la fin
    queue = [0.6] + [0.9] * len(j["marches"]) + [2.4]
    scenes, debut = [], 0.0
    for i, t in enumerate(textes):
        r = reps[i]
        d = max(minimum[i], offset[i] + (r["duree"] if r else 0) + queue[i])
        ident = "titre" if i == 0 else ("bilan" if i == len(textes) - 1 else f"m{i - 1}")
        scenes.append({"id": ident, "debut": debut, "duree": round(d, 3), "texte": t, "rep": r, "offset": offset[i]})
        debut += round(d, 3)
    duree = round(debut, 3)
    projet = os.path.join(dossier_sortie, "projet")
    if os.path.isdir(projet):
        shutil.rmtree(projet)
    os.makedirs(os.path.join(projet, "compositions"))
    os.makedirs(os.path.join(projet, "assets", "fonts"))
    police = os.path.expanduser(config.get("police", "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf"))
    if not os.path.exists(police):
        raise FileNotFoundError(f"Police DIN introuvable : {police} (réglage « police » de la configuration).")
    shutil.copy(police, os.path.join(projet, "assets", "fonts", "din-alternate-bold.ttf"))
    reperes = []
    for s in scenes:
        # les mots sont décalés de l'offset de la réplique : une scène lit les instants dans son propre temps
        rep = None
        if s["rep"]:
            rep = dict(s["rep"], mots=[dict(m, debut=m["debut"] + s["offset"]) for m in s["rep"]["mots"]])
        if s["id"] == "titre":
            style, corps, script, rs = scene_titre(j, rep)
        elif s["id"] == "bilan":
            style, corps, script, rs = scene_bilan(j, rep, unite, s["texte"])
        else:
            k = int(s["id"][1:])
            style, corps, script, rs = scene_marche(j, j["marches"][k], k, rep, unite, s["duree"])
        with open(os.path.join(projet, "compositions", s["id"] + ".html"), "w", encoding="utf-8") as f:
            f.write(_composition(s["id"], style, corps, script))
        reperes += [dict(r, t=round(s["debut"] + r["t"], 3)) for r in rs if r["t"] < s["duree"]]
    exemple = j["source"] == "testeur"
    with open(os.path.join(projet, "index.html"), "w", encoding="utf-8") as f:
        f.write(_index(scenes, duree, exemple))
    json.dump({"jour": j["jour"].isoformat(), "source": j["source"], "unite": unite, "duree": duree,
               "scenes": [{k: s[k] for k in ("id", "debut", "duree", "texte")} for s in scenes], "bruitages": reperes},
              open(os.path.join(dossier_sortie, "recap.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    journal(f"Rendu de l'image ({duree:.1f} s)…")
    muette = os.path.abspath(os.path.join(dossier_sortie, "image-muette.mp4"))
    subprocess.run(HYPERFRAMES + ["render", "--quality", "delivery", "--output", muette], cwd=projet, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    travail = os.path.join(dossier_sortie, "son")
    os.makedirs(travail, exist_ok=True)
    piste_v = mixage.piste_voix([{"fichier": s["rep"]["fichier"], "t": s["debut"] + s["offset"]} for s in scenes if s["rep"]],
                                duree, os.path.join(travail, "voix.wav"))
    piste_b, manquants = mixage.piste_bruitages(reperes, config.get("sons"), duree, os.path.join(travail, "bruitages.wav"))
    if manquants:
        journal(f"{len(manquants)} bruitage(s) absent(s) du dossier de sons ({', '.join(manquants[:4])}…) : `outil.py sons` les télécharge.")
    nom = f"recap-{j['jour'].isoformat()}{'-exemple' if exemple else ''}.mp4"
    finale = os.path.join(dossier_sortie, nom)
    mixage.assembler(muette, piste_v, piste_b, finale, travail)
    return finale
