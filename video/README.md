# Étrave vidéo

L'outil qui fabrique les vidéos TikTok d'Étrave en motion design, dans l'habillage de l'interface (la carte marine : papier,
encre, bleu du logo, chiffres en DIN) :

- **le récap de chaque séance** : la date, puis une scène par marché (Nasdaq 100, S&P 500) avec le graphique M5 du jour, la zone
  des 5 premières minutes, chaque entrée et chaque sortie, le résultat en R, puis le bilan de la journée ;
- **la présentation de la chaîne** : 47,6 s, rejouée à l'identique à partir d'un profil local.

La voix off est le clone ElevenLabs de ta voix. Les bruitages sont de vrais enregistrements (Mixkit). L'image est rendue par
[HyperFrames](https://hyperframes.dev), le son est mixé par ffmpeg.

## Ce que dit un récap

Exemple de texte lu (tout est écrit à partir des journaux de l'EA, les heures en heure de Paris) :

> Récap de la séance du jeudi seize avril.
> Nasdaq : le prix sort de la zone par le bas à quinze heures trente-six. Cinq positions à la vente : trois stops touchés, deux
> sorties en fin de séance. Résultat : moins deux virgule soixante-sept R. Un R, c'est le risque pris sur un trade.
> Bilan du jour : moins deux virgule soixante-sept R. Une séance qui forge le caractère. Chaque séance est sur le Telegram, lien en bio.

- Les gains et les pertes sont montrés de la même façon.
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
5. **Police** : DIN Alternate Bold, fournie avec macOS (`/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf`). Sous Windows,
   indique dans `police` le chemin d'un fichier DIN que tu possèdes.
6. **L'EA** : le récap a besoin du journal des bougies (`bougies-<symbole>.csv`). Il est écrit par l'EA de cette branche, une fois
   par jour, avec la ligne « fin » de la séance. Installe-le, compile-le (F7) : le premier récap sera possible après la séance suivante.
7. `python3 video/outil.py verifier` dit ce qui est prêt et ce qui manque.

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
10 22 * * 1-5 cd ~/Documents/GitHub/Bot-Trading && /usr/bin/python3 video/outil.py recap >> ~/Documents/Etrave-video/recap.log 2>&1
```

Le Mac doit être allumé à cette heure-là. Si l'EA tourne sur un autre ordinateur (un serveur Windows), copie ses journaux ou
indique leur dossier dans `dossier_journaux`.

## Configuration

| Réglage | Rôle |
|---|---|
| `dossier_journaux` | le dossier `…\Common\Files\Etrave` de MetaTrader (trouvé tout seul sous Windows et avec MetaTrader pour Mac) |
| `voix_id`, `modele_voix`, `cle_elevenlabs` | la voix (sans `voix_id`, la vidéo est faite sans voix) |
| `sons` | le dossier des bruitages Mixkit |
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
mixage.py        ffmpeg : voix, bruitages baissés sous la voix, niveau final
nombres.py       nombres, heures et dates en toutes lettres pour la voix
sons.json        le catalogue des bruitages (nom, adresse Mixkit)
modeles/presentation/   le projet HyperFrames de la présentation, avec des {{…}} à la place de ce qui est personnel
test_video.py    les contrôles (dont : rien de personnel ni de fichier sous licence dans ce dossier)
```

Tests : `.venv/bin/python -m pytest robot etrave video -q`.

Mention à garder dans chaque vidéo : « Pas un conseil en investissement. Le trading comporte un risque de perte en capital. » Elle
est dans le bilan du récap et dans la carte de fin de la présentation.
