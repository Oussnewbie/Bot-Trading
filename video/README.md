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

La voix off est le clone ElevenLabs de ta voix, réglée pour avoir de l'énergie (débit 1,08, plus d'intonation). Les bruitages
sont de vrais enregistrements (Mixkit). La musique de fond est un morceau à toi, posé sous la voix. L'image est rendue par
[HyperFrames](https://hyperframes.dev), le son est mixé par ffmpeg.

## Ce que dit un récap

Exemple de texte lu (tout est écrit à partir des journaux de l'EA, les heures en heure de Paris) :

> Mercredi dix-huit novembre. Journée rouge pour le robot… on regarde ça !
> Nasdaq. Quinze heures trente-cinq : le prix casse la zone par le bas. Le robot vend : cinq positions. Un stop touché… et quatre
> sorties en fin de séance. Résultat : moins un virgule cinq R. Un R, c'est le risque pris sur un trade.
> Même scénario sur le S et P cinq cents : un stop touché… et quatre sorties en fin de séance. Résultat : moins zéro virgule
> cinquante-six R.
> Bilan du jour : moins deux virgule zéro six R. Les pertes font partie du jeu. On les montre aussi. Chaque séance est sur le
> Telegram : lien en bio !

- Les gains et les pertes sont montrés de la même façon.
- **Les couleurs ont un seul sens chacune** :
  - le vert et le rouge disent le résultat (le R, les ronds de sortie, les étiquettes des sorties, le total) ;
  - le jaune surligne la cassure et la bougie où la caméra s'arrête ;
  - le bleu et l'encre disent achat et vente.
- Chaque arrêt de la caméra tombe sur le mot de la voix qui le dit, et dure au moins 1,5 s : le temps de lire l'étiquette.
- Quand le deuxième marché a vécu la même séance que le premier, la voix dit « Même scénario » au lieu de tout répéter.
- Un petit mot léger termine le bilan. Il change selon le résultat (perte, gain, pas de trade) et selon la date : refaire la même
  vidéo redonne le même mot.
- **Ce qui reste secret ne sort jamais** :
  - le type d'entrée (seulement « Achat » ou « Vente ») ;
  - les filtres et les réglages ;
  - la raison d'un jour sans trade (« les conditions n'étaient pas réunies »).
- Une journée du **testeur** porte la mention incrustée « Exemple : journée du testeur, pas un trade réel ». Une journée du compte
  n'a aucune mention.

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
   Elle est coupée à la durée de la vidéo, en fondu, 16 dB sous la voix, et baisse encore quand la voix parle. Elle n'est jamais
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

**Tout seul chaque soir** : la séance finit à 21:50 (heure de Paris), et l'EA écrit sa ligne « fin » deux minutes plus tard. Sur Mac,
`crontab -e` puis :

```
10 22 * * 1-5 cd ~/Documents/GitHub/Bot-Trading && python3 video/outil.py recap >> ~/Documents/Etrave-video/recap.log 2>&1
```

Avec cron, utilise le même Python que dans le Terminal (`which python3` donne son chemin, par exemple `/usr/local/bin/python3`,
à écrire à la place de `python3`). L'outil retrouve seul Node et ffmpeg dans `/usr/local/bin` et `/opt/homebrew/bin`. Sur Mac, la
première fois, macOS peut demander d'autoriser cron à lire le dossier Documents (Réglages Système, Confidentialité, Accès complet
au disque, ajouter `/usr/sbin/cron`).

Le Mac doit être allumé à cette heure-là. Si l'EA tourne sur un autre ordinateur (un serveur Windows), copie ses journaux ou
indique leur dossier dans `dossier_journaux`.

## Configuration

| Réglage | Rôle |
|---|---|
| `dossier_journaux` | le dossier `…\Common\Files\Etrave` de MetaTrader (trouvé tout seul sous Windows et avec MetaTrader pour Mac) |
| `voix_id`, `modele_voix`, `cle_elevenlabs` | la voix (sans `voix_id`, la vidéo est faite sans voix) |
| `sons` | le dossier des bruitages Mixkit |
| `musique` | un morceau ou un dossier de morceaux pour la musique de fond (facultatif) |
| `police` | le fichier DIN Alternate Bold |
| `unite` | `r` (par défaut), `pourcent` (du solde, d'après le journal des trades du compte), `points`, ou `auto` |
| `sortie` | où écrire les vidéos |
| `presentation` | ton profil pour la vidéo de présentation (voir `presentation.py`) |

## Fichiers

```
outil.py         la commande (verifier, jours, recap, presentation, sons)
journee.py       lit une séance dans les journaux de l'EA (heures de Paris par les fuseaux horaires, jamais +6 h en dur)
recap.py         écrit les scènes du récap et le minutage calé sur la voix, rend l'image, assemble le son
presentation.py  remplit le modèle de la présentation avec le profil, rend et mixe
voix.py          ElevenLabs (clone de ta voix), heure de chaque mot, cache des répliques
mixage.py        ffmpeg : voix, bruitages et musique baissés sous la voix, niveau final
police.py        largeur des textes dans la police DIN, pour que les étiquettes restent dans les zones sûres de TikTok
nombres.py       nombres, heures et dates en toutes lettres pour la voix
sons.json        le catalogue des bruitages (nom, adresse Mixkit)
modeles/presentation/   le projet HyperFrames de la présentation, avec des {{…}} à la place de ce qui est personnel
test_video.py    les contrôles (dont : rien de personnel ni de fichier sous licence dans ce dossier)
```

Tests : `.venv/bin/python -m pytest robot etrave video -q`.

Mention à garder dans chaque vidéo : « Pas un conseil en investissement. Le trading comporte un risque de perte en capital. » Elle
est dans le bilan du récap et dans la carte de fin de la présentation.
