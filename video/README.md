# Étrave vidéo

L'outil qui fabrique les vidéos TikTok d'Étrave en motion design, dans l'habillage de l'interface (la carte marine : papier,
encre, bleu du logo, chiffres en DIN) :

- **le récap de chaque séance** :
  - la date et la couleur de la journée (« Journée rouge », « Journée verte ») ;
  - une scène par marché (Nasdaq 100, S&P 500) : le graphique M5 du jour, la zone des 5 premières minutes, puis la caméra qui
    s'arrête sur la cassure et l'entrée, sur les stops, sur les sorties de fin de séance, et le résultat en R qui compte jusqu'à
    sa valeur ;
  - le bilan de la journée ;
- **la présentation de la chaîne** : 47,6 s, rejouée à l'identique à partir d'un profil local.

La voix off est le clone ElevenLabs de ta voix, **en une seule prise par vidéo** (toutes les scènes demandées ensemble, puis
coupées dans les silences) : des demandes séparées changeaient un peu le timbre d'une scène à l'autre. Mêmes réglages que la vidéo
de présentation, une graine fixe (`voix_graine`), puis le rythme : aucun silence de plus de 0,3 s entre deux mots et 10 % plus
rapide sans changer la hauteur (`voix_tempo`, `voix_pause_max`). Les bruitages
sont de vrais enregistrements (Mixkit). La musique de fond est un morceau à toi, posé sous la voix. L'image est rendue par
[HyperFrames](https://hyperframes.dev), le son est mixé par ffmpeg.

## Ce que dit un récap

Exemple de texte lu (tout est écrit à partir des journaux de l'EA, les heures en heure de Paris) :

> Mercredi dix-huit novembre. Journée rouge pour le robot… on regarde ça !
> Nasdaq. Quinze heures trente-cinq : le prix casse la zone par le bas, le robot vend. Cinq ventes en tout. Une vente part aussitôt
> contre nous : stop touché, environ trois cents points plus haut. Les quatre autres tiennent jusqu'à la fin de séance : jusqu'à
> environ deux cent quatre-vingts points en notre faveur, puis le prix remonte. Résultat : moins un virgule cinq R. Un R, c'est le
> risque pris sur un trade.
> Même scénario sur le S et P cinq cents. Une vente part aussitôt contre nous : stop touché, soixante-trois points plus haut. Les
> quatre autres tiennent jusqu'à la fin de séance : jusqu'à soixante points en notre faveur, puis le prix remonte. Résultat : moins
> zéro virgule cinquante-six R.
> Bilan du jour : moins deux virgule zéro six R. Les pertes font partie du jeu. On les montre aussi. Chaque séance est sur le
> Telegram : lien en bio !

- Les gains et les pertes sont montrés de la même façon.
- **Les couleurs ont un seul sens chacune** :
  - le vert et le rouge disent le résultat (le R, les ronds de sortie, les étiquettes des sorties, le total) ;
  - le jaune surligne la cassure et la bougie où la caméra s'arrête ;
  - le bleu et l'encre disent achat et vente.
- Chaque arrêt de la caméra tombe sur la phrase qui le raconte, et dure au moins 1,5 s : le temps de lire l'étiquette.
- **Le chemin du prix est raconté en points** (journal d'exécution de l'EA) : jusqu'où il est allé en notre faveur avant un stop
  (trait vert sur le graphique, « Jusqu'à +106 pts »), de combien il s'est retourné, ou s'il est parti aussitôt contre nous ; pour
  les positions gardées jusqu'au soir, le plus loin atteint en notre faveur. Les grands nombres sont arrondis à la voix (« environ
  trois cents points »), exacts à l'écran.
- Quand le deuxième marché a vécu la même séance que le premier, la voix dit « Même scénario » au lieu de tout répéter.
- Un petit mot léger termine le bilan. Il change selon le résultat (perte, gain, pas de trade) et selon la date : refaire la même
  vidéo redonne le même mot.
- **Ce qui reste secret ne sort jamais** :
  - le type d'entrée (seulement « Achat » ou « Vente ») ;
  - les filtres et les réglages ;
  - la raison d'un jour sans trade (« les conditions n'étaient pas réunies »).
- **Démo, réel ou testeur : seulement dans la description** (`description.txt`, la bio de la publication), d'après le journal de
  l'EA. Ni la vidéo, ni la couverture, ni le nom des fichiers n'en parlent.

## Installation (une fois)

1. **Logiciels** :
   - Python 3.11 ou plus ;
   - [Node.js](https://nodejs.org) 20 ou plus (HyperFrames se télécharge tout seul au premier rendu) ;
   - ffmpeg (`brew install ffmpeg` sur Mac).
2. **Configuration privée** : copie `video/config.exemple.json` dans `~/.config/etrave-video/config.json` et remplis-la. Ce fichier
   n'est jamais dans le dépôt.
3. **Clé ElevenLabs** :
   - écris-la seule dans `~/.config/elevenlabs/cle`, puis `chmod 600 ~/.config/elevenlabs/cle` ;
   - les droits nécessaires sont `text_to_speech` et `voices_read` ;
   - `voix_id` est l'identifiant de ton clone (page Voices d'ElevenLabs).
4. **Bruitages** : `python3 video/outil.py sons` télécharge les 31 sons Mixkit dans le dossier `sons` de ta configuration. Leur
   licence permet l'usage commercial dans des vidéos, mais pas de les redistribuer seuls : c'est pourquoi ils ne sont pas dans le dépôt.
5. **Musique de fond** (facultative) : un morceau, ou un dossier de morceaux (un par jour, choisi par la date), dans `musique`.
   Elle est coupée à la durée de la vidéo, en fondu, sa basse allégée, réglée sur ce qu'un téléphone en fait entendre (18 dB sous
   la voix au-dessus de 250 Hz, jamais plus de 11 dB sous la voix en tout), et elle baisse encore quand la voix parle. Elle n'est jamais
   dans le dépôt. Un morceau fait avec ElevenLabs Music sur un plan payant peut servir sur les réseaux sociaux (pas au cinéma, à
   la télévision ni à la radio : conditions d'ElevenLabs). Sans morceau, la vidéo est faite sans musique ; tu peux aussi ajouter un
   son de TikTok à la publication.
6. **Police** : DIN Alternate Bold, fournie avec macOS (`/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf`). Sous Windows,
   indique dans `police` le chemin d'un fichier DIN que tu possèdes.
7. **L'EA** : le récap a besoin du journal des bougies (`bougies-<symbole>.csv`). Il est écrit par l'EA de cette branche, une fois
   par jour, avec la ligne « fin » de la séance. Installe-le, compile-le (F7) : le premier récap sera possible après la séance suivante.
8. `python3 video/outil.py verifier` dit ce qui est prêt et ce qui manque.

## Utilisation

```
python3 video/outil.py jours                       # les séances finies trouvées dans les journaux
python3 video/outil.py recap                       # le récap de la dernière séance finie
python3 video/outil.py recap --jour 2026-11-26     # une séance précise (date de New York)
python3 video/outil.py recap --testeur --jour 2026-11-18   # une journée du testeur (marquée « Exemple »)
python3 video/outil.py presentation                # la vidéo de présentation (profil « presentation » de la configuration)
```

La vidéo arrive dans le dossier `sortie` de la configuration, `recap-AAAA-MM-JJ/recap-AAAA-MM-JJ.mp4`. Elle est en 1080 x 1920,
30 images par seconde, son à -15 LUFS. À côté se trouvent :

- `image-muette.mp4` : l'image seule ;
- `recap.json` : les scènes, les textes lus et les instants des bruitages ;
- `projet/` : le projet HyperFrames, à ouvrir avec `npx hyperframes preview` pour retoucher une scène à la main.

Compte 1 à 3 minutes par vidéo. Une réplique déjà dite n'est pas redemandée à ElevenLabs : elles sont gardées en cache dans
`~/.cache/etrave-video/voix`.

## Tout seul chaque soir

```
python3 video/outil.py installer
```

- L'outil est copié hors du dépôt, avec ses sons et sa musique : changer de branche ne le casse pas. Après une mise à jour de
  l'outil, relance `installer`.
- Il est lancé du lundi au vendredi à 22:20 et 23:50 (heure de l'ordinateur). Un Mac en veille le lance à son réveil, et un
  soir manqué est rattrapé au lancement suivant.
- Pour chaque séance finie avec au moins un trade (`auto_sans_trade` : aussi les autres), il crée sur le Bureau un dossier
  `Étrave TikTok/AAAA-MM-JJ/` qui contient :
  - `recap-AAAA-MM-JJ.mp4`, la vidéo ;
  - `description.txt`, le texte à coller dans TikTok : l'accroche, le petit mot, les résultats, le compte (réel ou démo,
    d'après le journal de l'EA), les mentions et les hashtags ;
  - `couverture.jpg`, l'écran titre.
- **Le récap de la semaine** (lundi-vendredi) et **le récap du mois** se font de la même façon, une fois la période finie :
  dossiers `Semaine du AAAA-MM-JJ/` et `Mois AAAA-MM/`. Une barre par séance, la courbe du cumul en R, le total de chaque marché,
  le meilleur et le pire jour. Leurs chiffres sont ceux des récaps de chaque jour (le total de la semaine est la somme des bilans
  quotidiens). `auto_hebdo` / `auto_mensuel` : false pour les couper.
- Une notification prévient quand c'est prêt.
- Seules les séances à partir du jour de l'installation sont faites (`auto_depuis` pour remonter plus loin).
- Le journal du mode automatique est `recap-auto.log`, dans le dossier de l'outil copié
  (`~/Library/Application Support/Etrave/outil-video`).
- `python3 video/outil.py auto` fait la même chose à la main. `desinstaller` retire la programmation.
- Sur Mac, la première fois, macOS peut demander d'autoriser python3 à écrire sur le Bureau.

**Où tournent l'EA et l'outil.** L'outil lit les journaux de l'EA (`dossier_journaux`). Ils doivent donc être sur la même machine
que lui :
- l'EA tourne sur ce Mac : rien à faire ;
- l'EA tourne sur un VPS Windows : soit l'outil y est installé aussi (Python, Node.js, ffmpeg, une police DIN dans `police`, puis
  `installer`, qui crée deux tâches planifiées ; non testé sous Windows), soit les journaux sont copiés chaque soir dans un dossier
  synchronisé lu par ce Mac.

## Configuration

| Réglage | Rôle |
|---|---|
| `dossier_journaux` | le dossier `…\Common\Files\Etrave` de MetaTrader (trouvé tout seul sous Windows et avec MetaTrader pour Mac) |
| `voix_id`, `modele_voix`, `cle_elevenlabs` | la voix (sans `voix_id`, la vidéo est faite sans voix) |
| `voix_tempo`, `voix_pause_max` | le rythme de la voix : 1,1 (10 % plus rapide) et 0,3 s de silence au plus entre deux mots |
| `sons` | le dossier des bruitages Mixkit |
| `musique` | un morceau ou un dossier de morceaux pour la musique de fond (facultatif) |
| `police` | le fichier DIN Alternate Bold |
| `unite` | `r` (par défaut), `pourcent` (du solde, d'après le journal des trades du compte), `points`, ou `auto` |
| `sortie` | où écrire les vidéos (les rendus de travail) |
| `dossier_publication` | le dossier des vidéos prêtes à publier, un sous-dossier par jour (`~/Desktop/Étrave TikTok`) |
| `auto_depuis`, `auto_sans_trade` | mode automatique : première séance à faire (AAAA-MM-JJ) ; aussi les jours sans trade |
| `mention_compte`, `hashtags` | la ligne sur le compte dans la description (sinon d'après le journal) ; les hashtags |
| `presentation` | ton profil pour la vidéo de présentation (voir `presentation.py`) |

## Fichiers

```
outil.py         la commande (verifier, jours, recap, presentation, sons)
journee.py       lit une séance dans les journaux de l'EA (heures de Paris par les fuseaux horaires, jamais +6 h en dur)
recap.py         écrit les scènes du récap et le minutage calé sur la voix, rend l'image, assemble le son
presentation.py  remplit le modèle de la présentation avec le profil, rend et mixe
voix.py          ElevenLabs (clone de ta voix) : une prise par vidéo coupée par scène, heure de chaque mot, rythme, cache
publication.py   le dossier du jour (vidéo, description TikTok, couverture) et le mode automatique
recap_periode.py les récaps de la semaine et du mois (barres, courbe, bilan)
installation.py  la copie de l'outil et le lancement chaque soir (launchd sur Mac, tâches planifiées sous Windows)
mixage.py        ffmpeg : voix, bruitages et musique baissés sous la voix, niveau final
police.py        largeur des textes dans la police DIN, pour que les étiquettes restent dans les zones sûres de TikTok
nombres.py       nombres, heures et dates en toutes lettres pour la voix
sons.json        le catalogue des bruitages (nom, adresse Mixkit)
modeles/presentation/   le projet HyperFrames de la présentation, avec des {{…}} à la place de ce qui est personnel
modeles/couverture-presentation/   la couverture de la présentation (accroche, logo, marchés, certificat)
test_video.py    les contrôles (dont : rien de personnel ni de fichier sous licence dans ce dossier)
```

Tests : `.venv/bin/python -m pytest robot etrave video -q`.

Mention à garder dans chaque vidéo : « Pas un conseil en investissement. Le trading comporte un risque de perte en capital. » Elle
est dans le bilan du récap et dans la carte de fin de la présentation.
