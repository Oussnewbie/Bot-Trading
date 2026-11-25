"""Les récaps de la semaine et du mois, dans le même habillage que le récap de chaque séance.

    titre    « Récap de la semaine », les dates, la couleur de la période (« Semaine verte », « Mois rouge »)
    barres   une barre par séance (vert : gain, rouge : perte, gris : pas de trade) ; la semaine est dite jour par jour, le mois
             en une phrase (séances, jours de trade, gagnants, perdants)
    courbe   le cumul en R séance après séance, le total qui compte jusqu'à sa valeur, le total de chaque marché
    bilan    jours de trade, jours gagnants, meilleur et pire jour, le petit mot, l'abonnement, la mention

Les chiffres sont ceux des récaps de chaque jour : le résultat de chaque marché arrondi comme à l'écran (−1,50 R), le total d'un
jour = la somme de ces valeurs, le total de la période = la somme des totaux des jours. Une période se lit dans les mêmes journaux
de l'EA (sans les bougies, inutiles ici). Rien de la méthode n'y figure.
"""
import calendar
import datetime
import json
import os
import shutil
import subprocess

import journee
import mixage
import nombres
import police
import recap
import voix
from recap import COUL, e, _pastille, _composition, couleur, ecran, dit

X0, X1, Y_HAUT, Y_BAS = 130, 950, 470, 790          # le graphique (au-dessus de y = 840 : jusqu'à x = 960)

MOTS_PERIODE = {
    "perte": ["{une} difficile. On la montre aussi, comme les autres.", "Le marché a gagné cette manche. On garde le cap.",
              "Les pertes font partie du métier. {la} suivante est déjà là."],
    "gain": ["Le robot a fait sa part. On reste humble.", "{une} propre, sans forcer.", "Belle régularité. On continue."],
    "rien": ["Pas de trade, pas de perte : attendre, c'est aussi trader."],
}


def mot_periode(p):
    cas = "rien" if not p["avec"] else ("gain" if p["total"] > 0 else "perte")
    liste = MOTS_PERIODE[cas]
    mot = liste[p["debut"].toordinal() % len(liste)]
    semaine = p["genre"] == "semaine"
    return mot.format(une="Une semaine" if semaine else "Un mois", la="La semaine" if semaine else "Le mois")


def charger(dossier, debut, fin, genre):
    """La période [debut, fin] (dates de New York) : chaque séance finie avec ses résultats, les totaux et les records."""
    jours = []
    for jour in journee.jours_finis(dossier):
        if not debut <= jour <= fin:
            continue
        # Correctif VID-07 (audit du 25/11/2026) : une séance illisible disparaissait en silence de la période, et une séance tradée au
        # R inconnu était dite « pas de trade » : « Semaine verte » avec un jour perdant en moins. La période attend d'être complète.
        try:
            j = journee.charger(dossier, jour, bougies_requises=False)
        except journee.JourneeIncomplete as err:
            raise journee.JourneeIncomplete(f"séance du {jour.isoformat()} incomplète ({err}) : récap de la période remis à plus tard")
        marches = {}
        for m in j["marches"]:
            v = m.get("r")
            marches[m["nom"]] = {"voix": m["voix"], "trades": len(m["positions"]),
                                 "r": (round(v, 2) if v is not None else None) if m["positions"] else 0.0}
        t = recap.total(j, "r")
        if j["trades"] and t is None:
            raise journee.JourneeIncomplete(f"résultat en R inconnu pour la séance du {jour.isoformat()} : récap de la période remis à "
                                            "plus tard")
        jours.append({"jour": jour, "trades": j["trades"], "marches": marches, "source": j["source"], "historique": j.get("historique"),
                      "total": t if t is not None else (0.0 if not j["trades"] else None)})
    avec = [d for d in jours if d["trades"] and d["total"] is not None]
    noms = []
    for d in jours:
        noms += [n for n in d["marches"] if n not in noms]
    par_marche = {n: round(sum(d["marches"][n]["r"] for d in avec if n in d["marches"] and d["marches"][n]["r"] is not None), 2)
                  for n in noms if any(n in d["marches"] and d["marches"][n]["trades"] for d in avec)}
    voix_marche = {n: next(d["marches"][n]["voix"] for d in jours if n in d["marches"]) for n in noms}
    sources = {d["source"] for d in jours}
    return {"genre": genre, "debut": debut, "fin": fin, "jours": jours, "avec": avec,
            "total": round(sum(d["total"] for d in avec), 2), "par_marche": par_marche, "voix_marche": voix_marche,
            "gagnants": [d for d in avec if d["total"] > 0], "perdants": [d for d in avec if d["total"] < 0],
            "meilleur": max(avec, key=lambda d: d["total"]) if avec else None,
            "pire": min(avec, key=lambda d: d["total"]) if avec else None,
            "source": "testeur" if "testeur" in sources else ("reel" if "reel" in sources else (sorted(sources) or [""])[0])}


def preuve_periode(p):
    """Les photos de l'historique du meilleur et du pire jour (s'il y en a), et les totaux en R à épingler dessous ; None sans photo."""
    photos = []
    for d in (p["meilleur"], p["pire"]):
        if d and d.get("historique") and all(d["historique"] != x for x, _ in photos):
            photos.append((d["historique"], f"Historique MetaTrader, {_jour_court(d['jour'])} {nombres.mois_ecran(d['jour'].month, True)}  {ecran(d['total'], 'r')}"))
    if not photos:
        return None
    notes = [(f"{nom}  {ecran(v, 'r')}", couleur(v)) for nom, v in p["par_marche"].items()]
    notes.append((f"Total  {ecran(p['total'], 'r')}", couleur(p["total"])))
    return {"photos": photos, "notes": notes}


def semaine_de(jour):
    lundi = jour - datetime.timedelta(days=jour.weekday())
    return lundi, lundi + datetime.timedelta(days=4)


def mois_de(jour):
    return jour.replace(day=1), jour.replace(day=calendar.monthrange(jour.year, jour.month)[1])


def accroche(p):
    semaine = p["genre"] == "semaine"
    nom = "Semaine" if semaine else "Mois"
    if not p["avec"]:
        return "sans", f"{nom} sans trade", COUL["encre2"]
    if round(p["total"], 2) == 0:
        return "à l'équilibre", f"{nom} à l'équilibre", COUL["encre2"]
    if p["total"] > 0:
        return ("verte" if semaine else "vert"), f"{nom} {'verte' if semaine else 'vert'}", COUL["vert"]
    return "rouge", f"{nom} rouge", COUL["rouge"]


def _jour_court(jour):
    return f"{nombres.JOURS[jour.weekday()][:3]}. {jour.day}"


def _jour_voix(jour, genre):
    """« mardi » dans une semaine, « le mardi dix-sept » dans un mois."""
    if genre == "semaine":
        return nombres.JOURS[jour.weekday()]
    return f"le {nombres.JOURS[jour.weekday()]} {'premier' if jour.day == 1 else nombres.entier(jour.day)}"


def repliques(p):
    """Le texte de chaque scène : titre, barres, courbe, bilan."""
    d0, d1, semaine = p["debut"], p["fin"], p["genre"] == "semaine"
    cle = accroche(p)[0]
    if semaine:
        if d0.month == d1.month:
            dates = f"du {nombres.entier(d0.day)} au {nombres.entier(d1.day)} {nombres.MOIS[d1.month - 1]}"
        else:
            dates = f"du {nombres.entier(d0.day)} {nombres.MOIS[d0.month - 1]} au {nombres.entier(d1.day)} {nombres.MOIS[d1.month - 1]}"
        titre = f"Récap de la semaine, {dates}."
        titre += " Semaine sans trade pour le robot." if cle == "sans" else f" Semaine {cle} pour le robot !"
    else:
        mois = nombres.MOIS[d0.month - 1]
        titre = f"Récap du mois {'d' + chr(39) if mois[0] in 'aeiouéè' else 'de '}{mois}."
        titre += " Mois sans trade pour le robot." if cle == "sans" else f" Mois {cle} pour le robot !"
    n, k, g, pe = len(p["jours"]), len(p["avec"]), len(p["gagnants"]), len(p["perdants"])
    if semaine:
        morceaux = []
        for d in p["jours"]:
            jour = recap._majuscule(_jour_voix(d["jour"], "semaine"))
            morceaux.append(f"{jour} : {dit(d['total'], 'r')}." if d["trades"] and d["total"] is not None else f"{jour} : pas de trade.")
        barres = " ".join(morceaux)
    else:
        barres = (f"{recap._majuscule(recap._une(n, True))} séance{recap._s(n)}, {recap._une(k)} jour{recap._s(k)} de trade : "
                  f"{recap._une(g)} gagnant{recap._s(g)}, {recap._une(pe)} perdant{recap._s(pe)}.")
    courbe = f"Au total : {dit(p['total'], 'r')}."
    for nom, v in p["par_marche"].items():
        courbe += f" {p['voix_marche'][nom]} : {dit(v, 'r')}."
    courbe += " Un R, c'est le risque pris sur un trade."
    preuve = ([f"Le meilleur et le pire jour {'de la semaine' if semaine else 'du mois'}, dans l'historique de MetaTrader."]
              if preuve_periode(p) else [])
    bilan = ""
    if p["meilleur"] and p["meilleur"]["total"] > 0:
        bilan += f"Meilleur jour : {_jour_voix(p['meilleur']['jour'], p['genre'])}, {dit(p['meilleur']['total'], 'r')}. "
    if p["pire"] and p["pire"]["total"] < 0:
        bilan += f"Pire jour : {_jour_voix(p['pire']['jour'], p['genre'])}, {dit(p['pire']['total'], 'r')}. "
    bilan += f"{mot_periode(p)} Abonne-toi pour la suite !"          # conformité TikTok : le Telegram seulement dans la description
    return [titre, barres, courbe] + preuve + [bilan]


# ───────────────────────── les scènes ─────────────────────────
def _entete(ident, p, titre):
    # VID-14 : le mois du lundi aussi quand la semaine est à cheval sur deux mois
    lundi = _jour_court(p["debut"]) + ("" if p["debut"].month == p["fin"].month else f" {nombres.mois_ecran(p['debut'].month, True)}")
    date = (f"semaine du {lundi} au {_jour_court(p['fin'])} {nombres.mois_ecran(p['fin'].month, True)} {p['fin'].year}"
            if p["genre"] == "semaine" else f"{nombres.mois_ecran(p['debut'].month)} {p['debut'].year}")
    return (f'    <div class="date" id="{ident}-date">{e(date)}</div>\n    <div id="{ident}-nom" class="nom">{e(titre)}</div>',
            f'    wipe("#{ident}-date", 0.05);\n    wipe("#{ident}-nom", 0.1, 0.32);')


STYLE_COMMUN = f"""    .nom {{ position: absolute; left: 120px; top: 340px; font-size: 92px; line-height: 1; }}
    .label {{ position: absolute; left: 124px; font-size: 34px; color: {COUL['encre2']}; line-height: 1; }}"""


def scene_titre(p, rep):
    cle, texte_badge, coul = accroche(p)
    d0, d1 = p["debut"], p["fin"]
    if p["genre"] == "semaine":
        haut = "Récap de la semaine"
        gros = f"{d0.day} – {d1.day}" if d0.month == d1.month else f"{d0.day}/{d0.month} – {d1.day}/{d1.month}"
        bas = f"{nombres.mois_ecran(d1.month)} {d1.year}"
    else:
        haut, gros, bas = "Récap du mois", nombres.mois_ecran(d0.month), str(d0.year)
    t_date = voix.instant(rep, "semaine", "mois", defaut=0.6)
    t_badge = max(voix.instant(rep, cle.split()[0] if cle != "sans" else "sans", defaut=t_date + 1.6) - 0.05, t_date + 0.9)
    style = f"""    #pt-logo {{ position: absolute; left: 100px; top: 290px; width: 180px; height: 180px; overflow: visible; }}
    .pt-ligne {{ position: absolute; left: 120px; line-height: 1; }}
    #pt-haut {{ top: 490px; font-size: 56px; color: {COUL['encre2']}; }}
    #pt-gros {{ top: 580px; font-size: 150px; }}
    #pt-bas {{ top: 750px; font-size: 80px; color: {COUL['encre2']}; }}"""
    corps = f"""    <svg id="pt-logo" viewBox="0 0 40 40">
      <path d="{recap.V_ETRAVE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
      <path d="{recap.TIGE}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" />
      <path d="{recap.VAGUES}" fill="none" stroke="{COUL['bleu']}" stroke-width="2.4" stroke-linecap="round" opacity="0.55" />
    </svg>
    <div id="pt-haut" class="pt-ligne">{e(haut)}</div>
    <div id="pt-gros" class="pt-ligne">{e(gros)}</div>
    <div id="pt-bas" class="pt-ligne">{e(bas)}</div>
    {_pastille("pt-badge", texte_badge, coul, COUL["blanc"], 84, 120, 960)}"""
    script = f"""    gsap.set(".pt-ligne", {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("#pt-logo path", {{ opacity: 0 }});
    tl.to("#pt-logo path", {{ opacity: 1, duration: 0.3, stagger: 0.12 }}, 0.05);
    wipe("#pt-haut", 0.15);
    wipe("#pt-gros", {t_date:.2f}, 0.4);
    wipe("#pt-bas", {t_date + 0.3:.2f});
    tl.fromTo("#pt-badge", {{ opacity: 0, scale: 1.12, rotation: -7, transformOrigin: "0% 50%" }}, {{ opacity: 1, scale: 1, rotation: -3, duration: 0.3, ease: "back.out(1.8)" }}, {t_badge:.2f});"""
    reperes = [{"t": 0.05, "son": "swoosh-fast-transitions-3115", "gain_db": -6},
               {"t": t_date, "son": "typewriter-mechanical-hit-1365", "gain_db": -6},
               {"t": t_badge + 0.2, "son": "hit-wood-hard-2182", "gain_db": -3, "passe_haut": 120}]
    return style, corps, script, reperes, t_badge + 1.6


def _echelle(valeurs, marge_bas=0.12):
    """L'échelle verticale ; marge_bas laisse sous les barres négatives la place de leur étiquette (au-dessus des jours)."""
    hauts = max([v for v in valeurs if v is not None] + [0.0])
    bas = min([v for v in valeurs if v is not None] + [0.0])
    etendue = max(hauts - bas, 0.5)
    hauts, bas = hauts + 0.12 * etendue, bas - marge_bas * etendue if bas < 0 else bas

    def y(v):
        return Y_BAS - (v - bas) / (hauts - bas) * (Y_BAS - Y_HAUT)
    return y


def scene_barres(p, rep):
    ident, jours, semaine = "pb", p["jours"], p["genre"] == "semaine"
    entete, script_entete = _entete(ident, p, "Jour par jour" if semaine else "Séance par séance")
    y = _echelle([d["total"] for d in jours], marge_bas=0.45)
    y0 = y(0.0)
    n = max(1, len(jours))
    pas = (X1 - X0) / n
    larg = min(90.0, pas * 0.58)
    mots = (rep or {}).get("mots", [])
    barres, etiquettes, script, reperes = [], [], [], []
    # la semaine : chaque barre pousse sur son jour, dit par la voix ; le mois : les barres poussent l'une après l'autre
    rangs, k, temps = [], 0, []
    if semaine:
        for d in jours:
            rangs.append(k)
            k += len((f"X : {dit(d['total'], 'r')}." if d["trades"] and d["total"] is not None else "X : pas de trade.").split())
    for i, d in enumerate(jours):
        cx = X0 + pas * (i + 0.5)
        t_i = (mots[rangs[i]]["debut"] if semaine and len(mots) > rangs[i] else 0.6 + (1.1 if semaine else 1.6) * i / n * (3 if semaine else 1))
        temps.append(t_i)
        v = d["total"] if d["trades"] else None
        if v is None:
            barres.append(f'<circle id="{ident}-b{i}" cx="{cx:.1f}" cy="{y0:.1f}" r="9" fill="{COUL["axe"]}" />')
        else:
            yv = y(v)
            haut, h = min(yv, y0), max(3.0, abs(y0 - yv))
            barres.append(f'<rect id="{ident}-b{i}" x="{cx - larg / 2:.1f}" y="{haut:.1f}" width="{larg:.1f}" height="{h:.1f}" rx="6" fill="{couleur(v)}" />')
        script.append(f'    tl.fromTo("#{ident}-b{i}", {{ scaleY: 0, opacity: 0, transformOrigin: "50% {0 if v is not None and v < 0 else 100}%" }}, '
                      f'{{ scaleY: 1, opacity: 1, duration: 0.35, ease: "back.out(1.6)" }}, {t_i:.2f});')
        if semaine or (p["meilleur"] is d) or (p["pire"] is d):
            texte = ecran(v, "r") if v is not None else "—"
            taille = 30 if semaine else 28
            w = recap._l(texte, taille)
            gauche = min(max(cx - w / 2, X0 - 20), 960 - w)
            haut_p = (y(v) - taille * 1.34 - 10 if (v or 0) >= 0 else y(v) + 10) if v is not None else y0 - taille * 1.34 - 14
            etiquettes.append(_pastille(f"{ident}-v{i}", texte, couleur(v) if v is not None else COUL["grille"],
                                        COUL["blanc"] if v is not None else COUL["encre2"], taille, gauche, haut_p))
            script.append(f'    pop("#{ident}-v{i}", {t_i + 0.25:.2f}, 0.3);')
        if semaine or (i % 5 == 0 and len(jours) - 1 - i >= 3) or i == len(jours) - 1:
            etiquettes.append(f'<text x="{cx:.1f}" y="{Y_BAS + 36}" font-size="28" fill="{COUL["encre2"]}" text-anchor="middle">'
                              f'{e(_jour_court(d["jour"]) if semaine else str(d["jour"].day))}</text>')
        if semaine and i < 5:
            reperes.append({"t": t_i, "son": "click-select-1109", "gain_db": -8, "max_dur": 0.3})
    if not semaine:
        reperes.append({"t": 0.6, "son": "tick-wall-clock-fast-1063", "gain_db": -13, "max_dur": 1.6})
    textes_svg = "".join(x for x in etiquettes if x.startswith("<text"))
    pastilles = "\n    ".join(x for x in etiquettes if not x.startswith("<text"))
    # sous le graphique : jours de trade, gagnants, perdants (sous y = 840, à gauche de x = 780)
    g, pe, k_t = len(p["gagnants"]), len(p["perdants"]), len(p["avec"])
    resume, _ = recap._rangee([("pb-r-trade", f"{k_t} jour{recap._s(k_t)} de trade", COUL["encre"], COUL["blanc"]),
                               ("pb-r-g", f"{g} gagnant{recap._s(g)}", COUL["vert"], COUL["blanc"]),
                               ("pb-r-p", f"{pe} perdant{recap._s(pe)}", COUL["rouge"], COUL["blanc"])], 36, Y_BAS + 90)
    t_resume = voix.instant(rep, "gagnant", defaut=None) if not semaine else None
    fin_barres = max(temps + [1.0])
    t_resume = max(t_resume or 0.0, fin_barres + 0.5)
    style = STYLE_COMMUN
    corps = f"""{entete}
    <svg class="plan" viewBox="0 0 1080 1920" data-layout-allow-overflow>
      <line id="{ident}-zero" x1="{X0 - 20}" x2="{X1 + 10}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="{COUL['axe']}" stroke-width="3" />
      {''.join(barres)}
      <g id="{ident}-jours">{textes_svg}</g>
    </svg>
    {pastilles}
    {resume}"""
    script_tete = f"""    gsap.set(["#{ident}-date", "#{ident}-nom"], {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("#{ident}-zero", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    gsap.set(["#{ident}-jours"], {{ opacity: 0 }});
    gsap.set("[id^='pb-r-']", {{ opacity: 0 }});
{script_entete}
    tl.to("#{ident}-zero", {{ scaleX: 1, duration: 0.45, ease: "power2.out" }}, 0.25);
    tl.to("#{ident}-jours", {{ opacity: 1, duration: 0.3 }}, 0.45);
    pop("#pb-r-trade", {t_resume:.2f}, 0.34, "0% 50%");
    pop("#pb-r-g", {t_resume + 0.25:.2f}, 0.34, "0% 50%");
    pop("#pb-r-p", {t_resume + 0.5:.2f}, 0.34, "0% 50%");"""
    reperes.append({"t": t_resume, "son": "click-light-switch-2585", "gain_db": -9})
    return style, corps, script_tete + "\n" + "\n".join(script), reperes, t_resume + 2.4


def scene_courbe(p, rep):
    ident, jours = "pc", p["jours"]
    entete, script_entete = _entete(ident, p, "Courbe de la semaine" if p["genre"] == "semaine" else "Courbe du mois")
    cumul, c = [0.0], 0.0
    for d in jours:
        c = round(c + (d["total"] if d["trades"] and d["total"] is not None else 0.0), 2)
        cumul.append(c)
    y = _echelle(cumul)
    n = len(cumul) - 1
    pas = (X1 - X0) / max(1, n)
    points = [(X0 + pas * i, y(v)) for i, v in enumerate(cumul)]
    trace = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in points)
    y0 = y(0.0)
    aire = trace + f" L{points[-1][0]:.1f},{y0:.1f} L{points[0][0]:.1f},{y0:.1f} Z"
    total = p["total"]
    coul = couleur(total)
    xf, yf = points[-1]
    texte_f = ecran(total, "r")
    w = recap._l(texte_f, 34)
    pastille_fin = _pastille("pc-fin", texte_f, coul, COUL["blanc"], 34, min(xf - w / 2, 960 - w), yf - 34 * 1.34 - 16 if total >= 0 else yf + 16)
    t_total = voix.instant(rep, "total", defaut=1.6)
    y_label = Y_BAS + 70
    gros = _pastille("pc-total", texte_f, coul, COUL["blanc"], 104, 120, y_label + 44)
    marches, x_m, y_m = [], 124, y_label + 44 + 104 * 1.34 + 26
    script_m, reperes = [], []
    rang = len(f"Au total : {dit(total, 'r')}.".split())      # le rang du premier mot de chaque marché dans la réplique
    mots = (rep or {}).get("mots", [])
    for i, (nom, v) in enumerate(p["par_marche"].items()):
        t = f"{nom} : {ecran(v, 'r')}"
        marches.append(_pastille(f"pc-m{i}", t, couleur(v), COUL["blanc"], 36, x_m, y_m))
        t_m = mots[rang]["debut"] if len(mots) > rang else t_total + 1.6 + i
        rang += len(f"{p['voix_marche'][nom]} : {dit(v, 'r')}.".split())
        script_m.append(f'    pop("#pc-m{i}", {max(t_m, t_total + 1.0):.2f}, 0.34, "0% 50%");')
        x_m += recap._l(t, 36) + 14
    t_rappel = max(voix.instant(rep, "risque", defaut=t_total + 3.5) - 0.4, t_total + 1.2)
    style = STYLE_COMMUN + f"""
    #pc-rappel {{ position: absolute; left: 124px; top: {y_m + 36 * 1.34 + 22:.0f}px; font-size: 28px; color: {COUL['encre2']}; line-height: 1; }}"""
    corps = f"""{entete}
    <svg class="plan" viewBox="0 0 1080 1920" data-layout-allow-overflow>
      <line id="pc-zero" x1="{X0 - 20}" x2="{X1 + 10}" y1="{y0:.1f}" y2="{y0:.1f}" stroke="{COUL['axe']}" stroke-width="3" stroke-dasharray="12 9" />
      <path id="pc-aire" d="{aire}" fill="{coul}" opacity="0" />
      <path id="pc-trace" d="{trace}" fill="none" stroke="{COUL['encre']}" stroke-width="6" stroke-linejoin="round" stroke-linecap="round" />
      {''.join(f'<circle class="pc-pt" cx="{px:.1f}" cy="{py:.1f}" r="7" fill="{COUL["encre"]}" />' for px, py in points[1:])}
      <circle id="pc-bout" cx="{xf:.1f}" cy="{yf:.1f}" r="13" fill="{coul}" stroke="{COUL['blanc']}" stroke-width="4" />
    </svg>
    {pastille_fin}
    <div id="pc-total-t" class="label" style="top:{y_label}px">{'Résultat de la semaine' if p['genre'] == 'semaine' else 'Résultat du mois'}</div>
    {gros}
    {''.join(marches)}
    <div id="pc-rappel">1 R = le risque pris sur un trade</div>"""
    duree_trace = 1.5
    script = f"""    gsap.set(["#pc-date", "#pc-nom", "#pc-total-t", "#pc-rappel"], {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("#pc-zero", {{ scaleX: 0, transformOrigin: "0% 50%" }});
    gsap.set(["#pc-bout", ".pc-pt", "#pc-fin"], {{ opacity: 0 }});
    gsap.set("[id^='pc-m']", {{ opacity: 0 }});
{script_entete}
    tl.to("#pc-zero", {{ scaleX: 1, duration: 0.45, ease: "power2.out" }}, 0.25);
    const trace = document.querySelector("#pc-trace"); const lg = trace.getTotalLength();
    gsap.set(trace, {{ strokeDasharray: lg, strokeDashoffset: lg }});
    tl.to(trace, {{ strokeDashoffset: 0, duration: {duree_trace}, ease: "power1.inOut" }}, 0.5);
    tl.to(".pc-pt", {{ opacity: 1, duration: 0.15, stagger: {duree_trace / max(1, n):.3f} }}, 0.5);
    tl.to("#pc-aire", {{ opacity: 0.14, duration: 0.5 }}, {0.5 + duree_trace:.2f});
    pop("#pc-bout", {0.5 + duree_trace:.2f}, 0.4);
    pop("#pc-fin", {0.6 + duree_trace:.2f}, 0.34);
    wipe("#pc-total-t", {t_total - 0.2:.2f});
    pop("#pc-total", {t_total:.2f}, 0.4, "0% 50%");
    compte("#pc-total", {total}, 2, " R", {t_total:.2f}, 0.9);
    tl.to("#pc-total", {{ scale: 1.08, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.inOut" }}, {t_total + 0.92:.2f});
    wipe("#pc-rappel", {t_rappel:.2f});
""" + "\n".join(script_m)
    reperes += [{"t": 0.5, "son": "whoosh-cinematic-fast-1492", "gain_db": -13, "max_dur": 0.7},
                {"t": t_total, "son": "ticking-timer-1056", "gain_db": -15, "max_dur": 0.9},
                {"t": t_total + 0.9, "son": "hit-deep-heartbeat-498", "gain_db": -5, "passe_haut": 180, "max_dur": 1.3}]
    return style, corps, script, reperes, max(t_total + 3.0, t_rappel + 2.0)


def scene_bilan(p, rep, texte):
    """Les records de la période, le petit mot, l'abonnement et la mention : la même fin que le récap de chaque séance."""
    ident = "pi"
    entete, script_entete = _entete(ident, p, "Bilan de la semaine" if p["genre"] == "semaine" else "Bilan du mois")
    lignes, script, reperes = [], [], [{"t": 0.05, "son": "paper-page-turn-1104", "gain_db": -6}]
    k_t, n = len(p["avec"]), len(p["jours"])
    rangs = [("Jours de trade", f"{k_t} sur {n}", COUL["encre"]), ("Jours gagnants", str(len(p["gagnants"])), COUL["vert"])]
    if p["meilleur"] and p["meilleur"]["total"] > 0:
        rangs.append(("Meilleur jour", f"{_jour_court(p['meilleur']['jour'])}   {ecran(p['meilleur']['total'], 'r')}", COUL["vert"]))
    if p["pire"] and p["pire"]["total"] < 0:
        rangs.append(("Pire jour", f"{_jour_court(p['pire']['jour'])}   {ecran(p['pire']['total'], 'r')}", COUL["rouge"]))
    for i, (nom, valeur, fond) in enumerate(rangs):
        top = 470 + 76 * i
        lignes.append(f'<div id="pi-l{i}" class="pi-ligne" style="top:{top + 6}px">{e(nom)}</div>'
                      + _pastille(f"pi-v{i}", valeur, fond, COUL["blanc"], 42, 470, top))
        t_i = 0.3 + 0.18 * i
        if nom == "Meilleur jour":
            t_i = max(voix.instant(rep, "meilleur", defaut=t_i), t_i)
        if nom == "Pire jour":
            t_i = max(voix.instant(rep, "pire", defaut=t_i), t_i)
        script.append(f'    wipe("#pi-l{i}", {t_i:.2f});\n    pop("#pi-v{i}", {t_i + 0.12:.2f}, 0.32, "0% 50%");')
        reperes.append({"t": t_i + 0.12, "son": "click-select-1109", "gain_db": -9, "max_dur": 0.3})
    mot = mot_periode(p)
    k_mot = len(texte.split(mot)[0].split())
    mots = (rep or {}).get("mots", [])
    t_mot = max(mots[k_mot]["debut"] if len(mots) > k_mot else 2.4, 0.3 + 0.18 * len(rangs) + 0.6)
    t_tel = max(voix.instant(rep, "abonne", apres=t_mot, defaut=t_mot + 1.6), t_mot + 0.8)
    t_bio = max(voix.instant(rep, "suite", apres=t_tel, defaut=t_tel + 0.8), t_tel + 0.4)
    y_mention = recap.Y_FIN - 8 - 2 * 28 * 1.32
    y_bio = y_mention - 16 - 58 * 1.34
    y_tel = y_bio - 68
    y_mot = 470 + 76 * len(rangs) + 40
    lignes_mot = police.couper(mot, 42, recap.X_DROITE_BAS - 120 - 0.84 * 42 - 4, recap.POLICE)
    style = STYLE_COMMUN + f"""
    .pi-ligne {{ position: absolute; left: 124px; font-size: 44px; line-height: 1; }}
    #pi-mot {{ line-height: 1.18; white-space: normal; }}
    .pi-bas {{ position: absolute; left: 124px; line-height: 1.15; width: 650px; }}
    #pi-mention {{ font-family: "Inter", sans-serif; font-weight: 400; font-size: 28px; line-height: 1.32; color: {COUL['encre2']}; }}"""
    corps = f"""{entete}
    {''.join(lignes)}
    <div id="pi-mot" class="pastille" style="left:120px; top:{y_mot:.0f}px; font-size:42px; background:{COUL['jaune']}; color:{COUL['encre']}">{'<br>'.join(e(l) for l in lignes_mot)}</div>
    <div id="pi-tel" class="pi-bas" style="top:{y_tel:.0f}px; font-size:56px">Abonne-toi :</div>
    {_pastille("pi-bio", "la suite, ici", COUL["bleu"], COUL["blanc"], recap.taille_bio("la suite, ici"), 120, y_bio)}
    <div id="pi-mention" class="pi-bas" style="top:{y_mention:.0f}px">Pas un conseil en investissement. Le trading comporte un risque de perte en capital.</div>"""
    script_tete = f"""    gsap.set(["#pi-date", "#pi-nom", ".pi-ligne", "#pi-tel"], {{ clipPath: "inset(-30% 100% -40% 0)" }});
    gsap.set("#pi-mention", {{ opacity: 0 }});
{script_entete}"""
    script.append(f"""    tl.fromTo("#pi-mot", {{ opacity: 0, scale: 1.4, rotation: 4, transformOrigin: "20% 50%" }}, {{ opacity: 1, scale: 1, rotation: -2, duration: 0.32, ease: "back.out(1.8)" }}, {t_mot:.2f});
    wipe("#pi-tel", {t_tel - 0.1:.2f});
    pop("#pi-bio", {t_bio:.2f}, 0.36, "0% 50%");
    tl.to("#pi-bio", {{ scale: 1.07, duration: 0.28, yoyo: true, repeat: 3, ease: "sine.inOut", transformOrigin: "0% 50%" }}, {t_bio + 0.5:.2f});
    tl.to("#pi-mention", {{ opacity: 1, duration: 0.3 }}, {t_tel:.2f});""")
    reperes += [{"t": t_mot, "son": "paper-slide-1530", "gain_db": -8, "max_dur": 0.6},
                {"t": t_bio, "son": "bell-notification-933", "gain_db": -6, "max_dur": 2.0}]
    return style, corps, script_tete + "\n" + "\n".join(script), reperes, max(t_bio + 2.4, t_tel + 3.9)


# ───────────────────────── fabrication ─────────────────────────
def nom_dossier(p):
    return f"Semaine du {p['debut'].isoformat()}" if p["genre"] == "semaine" else f"Mois {p['debut']:%Y-%m}"


def fabriquer(p, config, dossier_sortie, journal=print, rendre=True, exiger_voix=True):
    """Le projet HyperFrames, le rendu, la voix (une prise), les bruitages et la musique. Rend le chemin de la vidéo.
    exiger_voix : comme recap.fabriquer (VID-03, VID-18)."""
    textes = repliques(p)
    try:
        reps = [voix.rythmer(r, config.get("voix_tempo", voix.TEMPO), config.get("voix_pause_max", voix.PAUSE_MAX))
                for r in voix.recit(textes, config)]
        sans_voix = False
    except voix.VoixIndisponible as err:
        if exiger_voix:
            raise
        journal(f"{err} : vidéo sans voix (--sans-voix).")
        reps, sans_voix = [None] * len(textes), True
    voix.controle_pistes(reps if exiger_voix else [])
    police_fichier = os.path.expanduser(config.get("police", police.DEFAUT))
    recap.POLICE = police_fichier
    projet = os.path.join(dossier_sortie, "projet")
    if os.path.isdir(projet):
        shutil.rmtree(projet)
    os.makedirs(os.path.join(projet, "compositions"))
    os.makedirs(os.path.join(projet, "assets", "fonts"))
    shutil.copy(police_fichier, os.path.join(projet, "assets", "fonts", "din-alternate-bold.ttf"))
    preuve = len(textes) == 5
    offset = [0.15, 0.25, 0.25] + [0.25] * preuve + [0.25]
    minimum = [2.6, 5.0, 5.0] + [4.0] * preuve + [5.5 if not sans_voix else 7.5]
    queue = [0.35, 0.6, 0.6] + [0.6] * preuve + [2.0]
    idents = ["titre", "barres", "courbe"] + ["preuve"] * preuve + ["bilan"]
    date_txt = (f"semaine du {_jour_court(p['debut'])} au {_jour_court(p['fin'])} {nombres.mois_ecran(p['fin'].month, True)} {p['fin'].year}"
                if p["genre"] == "semaine" else f"{nombres.mois_ecran(p['debut'].month)} {p['debut'].year}")
    scenes, reperes, debut = [], [], 0.0
    for i, t in enumerate(textes):
        r = reps[i]
        d = max(minimum[i], offset[i] + (r["duree"] if r else 0) + queue[i])
        rep = dict(r, mots=[dict(m, debut=m["debut"] + offset[i]) for m in r["mots"]]) if r else None
        if idents[i] == "preuve":
            style, corps, script, rs, fin_min, images = recap.scene_preuve("pv", preuve_periode(p), rep, date_txt)
            os.makedirs(os.path.join(projet, "assets", "captures"), exist_ok=True)
            for source, nom in images:
                shutil.copy(source, os.path.join(projet, "assets", "captures", nom))
        else:
            style, corps, script, rs, fin_min = (scene_titre(p, rep) if i == 0 else scene_barres(p, rep) if i == 1
                                                 else scene_courbe(p, rep) if i == 2 else scene_bilan(p, rep, t))
        d = round(max(d, fin_min), 3)
        with open(os.path.join(projet, "compositions", idents[i] + ".html"), "w", encoding="utf-8") as f:
            f.write(_composition(idents[i], style, corps, script))
        reperes += [dict(x, t=round(debut + x["t"], 3)) for x in rs if x["t"] < d]
        scenes.append({"id": idents[i], "debut": round(debut, 3), "duree": d, "texte": t, "rep": r, "offset": offset[i]})
        debut += d
    duree = round(debut, 3)
    for s in scenes[1:]:
        reperes.append({"t": round(s["debut"] - recap.VOLET - 0.05, 3), "son": "swoosh-fast-transitions-3115", "gain_db": -11})
    with open(os.path.join(projet, "index.html"), "w", encoding="utf-8") as f:
        f.write(recap._index(scenes, duree))
    json.dump({"genre": p["genre"], "debut": p["debut"].isoformat(), "fin": p["fin"].isoformat(), "duree": duree,
               "scenes": [{k: s[k] for k in ("id", "debut", "duree", "texte")} for s in scenes]},
              open(os.path.join(dossier_sortie, "recap.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not rendre:
        return projet
    journal(f"Rendu de l'image ({duree:.1f} s)…")
    muette = os.path.abspath(os.path.join(dossier_sortie, "image-muette.mp4"))
    subprocess.run(recap.HYPERFRAMES + ["render", "--quality", "delivery", "--output", muette], cwd=projet, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    travail = os.path.join(dossier_sortie, "son")
    os.makedirs(travail, exist_ok=True)
    piste_v = mixage.piste_voix([{"fichier": s["rep"]["fichier"], "t": s["debut"] + s["offset"]} for s in scenes if s["rep"]],
                                duree, os.path.join(travail, "voix.wav"))
    piste_b, _ = mixage.piste_bruitages(reperes, config.get("sons"), duree, os.path.join(travail, "bruitages.wav"))
    piste_m = mixage.piste_musique(config.get("musique"), p["fin"], duree, os.path.join(travail, "musique.wav"), journal)
    finale = os.path.join(dossier_sortie, ("recap-semaine-" if p["genre"] == "semaine" else "recap-mois-") + p["debut"].isoformat()[:10 if p["genre"] == "semaine" else 7] + ".mp4")
    mixage.assembler(muette, piste_v, piste_b, finale, travail, piste_m)
    import controle
    controle.verifier(finale, travail, journal)          # VID-30 : prévient, ne bloque pas
    return finale
