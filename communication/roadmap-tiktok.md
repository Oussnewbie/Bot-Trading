# Étrave — Roadmap de com TikTok

Mise à jour : 25 novembre 2026. Ce dossier est à part du code : il ne touche ni au robot, ni à Étrave, ni à la recherche.

**Objectif** : 1 000 abonnés vers le 17 janvier 2027 pour débloquer les lives, puis une liste d'attente qualifiée avant
d'ouvrir le branchement des comptes MT5.

## Principes

- **Positionnement** : Étrave, le robot qui trade la cassure de l'ouverture de New York sur le Nasdaq, construit avec
  Claude Code par un trader qui a 6 ans d'expérience.
- **Transparence totale** : chaque séance est publiée, gains comme pertes. C'est ce qui te distingue des vendeurs de robots.
- **La preuve avant la promesse** : historique vérifié (Myfxbook ou FX Blue) en lien, jamais de rendement promis.
- **Identité** : logo dans `logo/`, bleu #3987e5 sur noir #0b0b0b, même habillage sur chaque vidéo.

> **À savoir avant de publier des résultats** : d'après `CLAUDE.md`, la V10 n'a encore tourné ni dans le testeur MT5, ni en
> démo. Les vidéos « résultat du jour » commencent donc avec la démo, en affichant « compte démo » à l'écran, puis passent au
> compte réel. Les 3 612 trades du backtest servent de contenu pédagogique, pas de preuve.

## Les phases

| Phase | Dates | Condition pour passer à la suite |
|---|---|---|
| 0 · Préparer | 25 nov. → 6 déc. 2026 | Compte prêt, 10 vidéos d'avance, V10 en démo |
| 1 · Lancer | 7 déc. 2026 → 17 janv. 2027 | 1 000 abonnés |
| 2 · Lives | dès 1 000 abonnés | 4 semaines de lives réguliers |
| 3 · Convertir | après 3 mois d'historique vérifié | Bêta fermée pleine, puis ouverture par vagues |

### Phase 0 — Préparer (25 nov. → 6 déc.)

- [ ] V10 dans le testeur MT5, puis en démo (prochaine action de `CLAUDE.md`)
- [ ] Compte TikTok dédié (ex. `@etrave.bot`), passé en compte Business
- [ ] Photo de profil : l'icône Étrave retravaillée avec Nano Banana (prompt dans `logo/README.md`)
- [ ] Bio : « Mon robot trade l'ouverture de New York. Résultats publiés chaque soir. »
- [ ] Lien en bio : page d'accueil avec liste d'attente (e-mail, taille de compte, courtier)
- [ ] Compte du robot relié à Myfxbook ou FX Blue en mode vérifié
- [ ] Canal Telegram public qui reçoit les alertes d'Étrave (la fonction Telegram existe déjà)
- [ ] Habillage : intro d'une seconde avec le logo, sous-titres automatiques, même police partout
- [ ] 10 vidéos tournées d'avance (voir les idées plus bas)

### Phase 1 — Lancer (7 déc. → 17 janv.)

Une vidéo par jour minimum, deux en semaine quand c'est possible. 20 à 45 secondes, accroche dans les 2 premières secondes.

| Pilier | Part | Format | Quand |
|---|---|---|---|
| Résultat du jour | 40 % | Dashboard Étrave + écran MT5, 20 s, voix off | Vers 22 h, après la sortie de 21:50 (15:50 NY) |
| Coulisses du code | 25 % | Écran Claude Code, avant / après d'une amélioration | Week-end |
| La stratégie expliquée | 20 % | Range de 9:30, RSI, VWAP, pyramide, en 30 s | Mardi, jeudi |
| Ton parcours | 15 % | Face caméra : 6 ans de trading, étudiant en compta, alternance | Mercredi |

- Réponds à tous les commentaires dans la première heure ; transforme les meilleures questions en vidéos-réponses.
- Fêtes : marché américain fermé le 25 décembre et le 1er janvier, et tu es à Saint-Laurent le 24. Programme les vidéos
  de cette période à l'avance (TikTok permet de planifier depuis l'ordinateur).

### Phase 2 — Lives (dès 1 000 abonnés)

Il faut 1 000 abonnés et 18 ans pour lancer un live, selon les guides 2026 (le seuil peut varier selon les pays). Sur Mac,
**TikTok LIVE Studio** permet d'afficher le dashboard d'Étrave et ta caméra en même temps.

| Live | Quand (heure de Paris) | Durée | Contenu |
|---|---|---|---|
| Ouverture de New York | 15:15 → 16:15, les jours où l'alternance le permet | 1 h | Le range de 9:30 se forme, les ordres partent, tu commentes en direct |
| Bilan de la semaine | Vendredi 22 h | 45 min | Résultats, courbe, questions-réponses |
| Code en direct | Samedi après-midi | 1 h | Tu améliores Étrave avec Claude Code devant tout le monde |

- Mêmes jours, mêmes heures chaque semaine : l'algorithme et le public s'habituent au rendez-vous.
- Annonce chaque live la veille en vidéo et sur Telegram.
- Lien de la liste d'attente épinglé en commentaire pendant chaque live.

### Phase 3 — Convertir (après 3 mois d'historique vérifié)

1. **Liste d'attente** ouverte dès la phase 0, relancée à chaque live.
2. **Bêta fermée** : 10 à 20 comptes choisis dans la liste, appel de 15 minutes avec chacun pour le branchement.
3. **Mécanique** : copy trading chez un courtier ou MetaApi CopyFactory, 40 % des gains calculés sur le high-water mark.
4. **Ouverture par vagues**, annoncée en live, avec un nombre de places limité à chaque vague.

## Semaine type (à partir de la phase 2)

| Jour | Vidéo(s) | Live |
|---|---|---|
| Lundi | Résultat + « le plan de la semaine » (jours de Fed, fériés) | — |
| Mardi | Résultat + stratégie expliquée | Ouverture de New York (si dispo) |
| Mercredi | Résultat + parcours | — |
| Jeudi | Résultat + stratégie expliquée | Ouverture de New York (si dispo) |
| Vendredi | Résultat + bilan de la semaine | Bilan de la semaine, 22 h |
| Samedi | Coulisses du code | Code en direct |
| Dimanche | Récap de la semaine en 30 s + annonce de la suivante | — |

## Indicateurs à suivre

| Phase | Indicateur | Cible proposée |
|---|---|---|
| 1 | Abonnés | 1 000 vers le 17 janvier |
| 1 | Vues moyennes par vidéo | En hausse semaine après semaine |
| 1 | Taux de visionnage complet | Au-dessus de 40 % |
| 1 | Inscrits sur la liste d'attente | 100 |
| 2 | Spectateurs en même temps pendant un live | 30, puis 100 |
| 2 | Nouveaux abonnés par live | Au moins 20 |
| 3 | Inscrits sur la liste d'attente | 300 avant la bêta |
| 3 | Comptes branchés et restés au bout d'un mois | 10 à 20 pour la bêta |

## 15 premières idées de vidéos

1. « J'ai codé un robot qui trade à ma place à 15:30. Voici son résultat du jour. »
2. « Pourquoi mon robot ne trade que pendant 15 minutes »
3. « Le range de 9:30 expliqué en 30 secondes »
4. « La règle qui empêche mon robot de trader les jours de Fed »
5. « J'ai codé ce robot sans être développeur : voici comment » (Claude Code)
6. « Ce que voit mon robot avant de prendre un trade » (dashboard Étrave)
7. « Pourquoi mon robot ajoute des positions quand il gagne » (la pyramide)
8. « Version 9 contre version 10 : ce qui a changé » (`recherche/resultats/v10_confort_contre_v9.png`)
9. « Le garde-fou qui bloque tout quand le spread est trop large »
10. « Combien mon robot risque par trade, et pourquoi si peu » (0,25 %)
11. « 2 000 essais avant de garder une seule stratégie »
12. « Ce qu'il s'est passé quand mon robot a perdu plusieurs jours d'affilée »
13. « 6 ans de trading résumés dans un robot »
14. « Étudiant en compta le jour, robot de trading le soir »
15. « On me demande si c'est une arnaque : voici tous mes trades »

## Sources

- [Exigences TikTok LIVE 2026 — Tikfinity](https://blog.tikfinity.com/?p=3719)
- [Exigences TikTok LIVE 2026 — SocialBu](https://socialbu.com/blog/?p=27534)
