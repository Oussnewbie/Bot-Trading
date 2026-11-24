//+------------------------------------------------------------------+
//| Strategy-V10.mq5 — Cassure du range d'ouverture de New York (M5)|
//| + repli sur le VWAP + continuations, avec un stop élargi.        |
//| Mêmes règles que Strategy-V10.pine. V10 = V9 + largeur du stop   |
//+------------------------------------------------------------------+
//
// Règles (heure de New York, bougies M5 quel que soit l'horizon du graphique) :
//  1. Range    : high et low de la bougie M5 de 9:30.
//  2. Filtres  : achat permis si le RSI14 M5 de 9:30 > 50 ET si le high de 9:30 dépasse le plus haut de 9:00-9:30 ;
//                vente permise si le RSI < 50 ET si le low de 9:30 passe sous le plus bas de 9:00-9:30.
//  3. Entrée   : à 9:35, ordres Buy Stop au high et Sell Stop au low posés CHEZ LE COURTIER, avec leur stop, valables
//                jusqu'à 9:45 : son serveur les exécute dès que l'ask (achat) ou le bid (vente) atteint le niveau, sans
//                attendre l'EA. Un côté dont le prix est déjà au niveau (ou trop près pour un ordre en attente) est
//                surveillé par l'EA, qui entre au marché. Une seule cassure par jour : le premier exécuté annule l'autre.
//                Si un seul côté est permis et que le prix touche l'autre côté d'abord, plus de trade ce jour-là.
//  4. Stop     : de l'autre côté du range, posé chez le broker dès l'entrée. 1R = somme perdue au stop (lots × range).
//  5. Gestion  : à la clôture d'une bougie (après celle de l'entrée) qui a atteint +1,5R, stop au prix d'entrée.
//                Sortie au marché à 15:50 NY (clôture de la bougie de 15:45) ; à 12:45 les jours fériés américains et
//                les demi-séances, où le marché ferme vers 13:00.
//  6. PYRAMIDE : quand une bougie M5 clôture à +2R ou plus, l'EA ajoute DEUX unités au marché et met le stop de
//                l'ensemble à 1R sous le prix de l'ajout (donc au moins à +1R pour la première unité). Après l'ajout,
//                le pire cas reste -1R, comme au départ : l'ajout perd 2R, la première unité gagne au moins 1R.
//                Un seul ajout par trade.
//  7. R affiché = résultat net de tout le trade (ajout, commission et swap compris) ÷ somme risquée au départ.
//  8. v7 — MÉMOIRE : après un trade pris qui finit gagnant (plus de +0,05R), le signal suivant n'est pas pris (un seul).
//                Ce jour-là l'EA ne pose aucun ordre : il observe seulement si la cassure permise se déclenche avant 9:45.
//                Si elle se déclenche, la règle est consommée et le trading reprend au signal d'après. Sinon (pas de
//                cassure, côté bloqué touché d'abord, filtres fermés), la règle reste en attente pour le jour suivant.
//  9. v7 — Aucun ordre les jours de décision de la Fed (FOMC) ni les jours fériés américains / demi-séances.
//                Ces jours-là ne changent rien à la règle mémoire.
//     Ces règles viennent de la recherche du 20 novembre 2026 (2018-2024, vérifiées sur 2025-2026 jamais utilisés).
//     Elles n'augmentent jamais le risque par trade : elles ne font que retirer des trades.
//
// STRATEGY V8 = la v7 ci-dessus (trade A, la cassure) + deux entrées de plus, les jours où la cassure est prise :
// 10. B — REPLI SUR LE VWAP : après la cassure, la première bougie M5 (après celle de la cassure) qui touche le prix
//                moyen de séance (VWAP depuis 9:30, à 0,1 range près), clôture du bon côté du VWAP et dans le sens du
//                trade déclenche une entrée au marché. Stop 1 point au-delà de l'extrême des 2 dernières bougies M5.
//                Même gestion que la cassure (stop à l'entrée à +1,5R, pyramide à +2R), en multiples du stop de cette
//                entrée. Jusqu'à 14:00 ; abandonné si une bougie M5 clôture de l'autre côté du range. Une fois par jour.
// 11. C — ENTRÉE À 10:00 : si à 10:00 le prix est toujours au-delà du niveau de cassure et que le stop du range n'a
//                pas été touché, entrée au marché, stop de l'autre côté du range, stop à l'entrée à +1,5R, sortie 15:50.
// 12. TAILLE   : B et C ne prennent jamais plus de lots que la cassure et ne risquent jamais plus qu'elle (1R).
//                Jusqu'à 3 positions ouvertes en même temps, dans le même sens : compte « hedging » obligatoire.
//                La règle mémoire ne regarde que le trade de cassure. Numéros magiques : A = InpMagic, B = +1, C = +2.
//
// STRATEGY V9 = la V8 ci-dessus, revue après un examen sur 7 années jamais vues pendant la recherche (2010-2017) :
// 13. D — CONTINUATIONS : tant que la cassure A est ouverte, à la clôture de chacune des 3 bougies M5 qui suivent celle
//                du range (bougies de 9:35, 9:40 et 9:45), l'EA guette pendant 10 minutes la cassure de l'extrême de
//                cette bougie dans le sens du trade (achat : son plus haut atteint par l'ask ; vente : son plus bas
//                atteint par le bid). Entrée au marché, stop à l'autre extrême de la bougie. Guet annulé si le prix
//                touche d'abord ce stop. Même gestion que la cassure (stop à l'entrée à +1,5R, pyramide à +2R), en
//                multiples du stop de cette entrée. Taille : comme B (jamais plus de lots que A, jamais plus de 1R).
// 14. C (entrée de 10:00) est COUPÉE PAR DÉFAUT : sur les données jamais vues elle ne gagne presque rien (+0,04 R par trade).
// 15. GARDE-FOU COÛT : aucun ordre si le spread du moment + 2 glissements supposés pèse plus de 25 % du range du jour.
//                Ces jours-là ne changent rien à la règle mémoire.
//     Numéros magiques : A = InpMagic, B = +1, C = +2, D1 = +3, D2 = +4, D3 = +5 (jusqu'à D7 = +9).
//     Jusqu'à 5 positions ouvertes en même temps dans le même sens et 15 lots de A pyramides comprises (7 pour la V8) :
//     compte « hedging » obligatoire, et risque par trade à régler plus bas qu'avec la V8.
//     Ce que disent les tests (détail dans rapport.md) :
//       2018-2026, période de recherche, spread réel + 1 point         : V9 +1 614 R, pire baisse  56 R (V8 : +986 R, 38 R).
//       2010-2017, JAMAIS VU, coûts ramenés à leur poids d'aujourd'hui : V9   +577 R, pire baisse 170 R (V8 : +281 R, 102 R).
//       2010-2017 avec les coûts au poids de 2018                       : V9   -157 R (V8 : -159 R).
//     Le backtest 2018-2026 est donc une vision optimiste, et la stratégie dépend du poids des coûts dans le range.
//     Aucun gain n'est garanti. Testeur de stratégie puis compte démo avant tout argent réel.
//
// STRATEGY V10 = la V9 ci-dessus + un réglage, « largeur du stop » (InpStopMult), né de l'autopsie des stops :
//     sur 16 ans, un stop sur trois est suivi d'un mouvement de +2R ou plus DANS LE SENS du trade. La première cause des stops
//     n'est pas le sens, c'est un stop trop court (un range de 5 minutes à l'heure la plus agitée).
// 16. PROFIL CONFORT (par défaut, InpStopMult = 3) : mêmes signaux et mêmes entrées, mais le stop est 3 fois plus loin (pour la
//                cassure : 3 ranges sous le niveau d'achat) et les lots 3 fois plus petits : la somme risquée par trade ne change pas.
//                Le stop à l'entrée (+1,5R) et la pyramide (+2R) se comptent avec ce nouveau R. Mémoire : après un trade de cassure à
//                plus de +1R, le signal suivant est sauté. Continuations D : armées seulement si l'autre bord du range n'a pas été
//                touché depuis la cassure. Au plus 5 lots de la V9 ouverts en même temps (15 pour la V9).
// 17. PROFIL TENDANCE = la V9 : InpStopMult = 1 et « gagnant au-delà de » = 0,05 R.
// 18. RISQUE PAR TRADE : 0,25 % par défaut, comme la V9. Le remonter (0,5 % était le réglage des V6 à V8) double les gains ET les
//                baisses : c'est ta décision. En Confort à 0,5 % : pire journée des tests -2,6 %, pire baisse 16 % (2018-2026) et 27 % (2010-2017).
//     Ce que disent les tests sur le Nasdaq (détail dans rapport.md) :
//                                                        TENDANCE (V9)                 CONFORT
//       2018-2026, spread réel + 1 point :   +1 614 R, 18 % de réussite, baisse 56 R | +477 R, 47 % de réussite, baisse 32 R
//       2018-2026, 3 points de glissement :    +799 R, baisse 157 R                  | +301 R, baisse 70 R
//       2010-2017, coûts au poids d'aujourd'hui : +577 R, 15 %, baisse 170 R         | +194 R, 44 %, baisse 53 R, 8 années sur 8
//       2010-2017, coûts au poids de 2018 :    -157 R                                |  +23 R
//     À pire baisse égale les deux profils rapportent à peu près autant ; le Confort gagne 2 à 3 fois plus souvent, a des séries
//     de pertes 3 fois plus courtes et dépend beaucoup moins des coûts. Il a été mis au point APRÈS avoir vu tout l'historique
//     du Nasdaq : ce n'est pas une preuve. NASDAQ UNIQUEMENT : appliqué tel quel au Dow Jones, au DAX, à l'or, au Bitcoin,
//     à l'EUR/USD et au GBP/USD (test écrit à l'avance), ce robot ne gagne sur aucun.
//
// Nasdaq (NAS100) uniquement. Les données et le spread de chaque courtier diffèrent : vérifie dans le testeur de
// stratégie (« Chaque tick basé sur des ticks réels ») et en démo avant le réel.
//
// INTERFACE ÉTRAVE (etrave/etrave.py, lancée par etrave/Etrave.bat) : l'EA lit toutes les 2 secondes le fichier
// Etrave\reglages.txt du dossier commun de MetaTrader (risque par trade, levier, case du Nasdaq, Telegram, demande de
// clôture) et y écrit son état (Etrave\etat-<symbole>.txt) et ses trades (Etrave\trades-<symbole>.csv). Une clé absente
// du fichier laisse la valeur saisie ici. Dans le testeur de stratégie, seuls les réglages saisis ici comptent.
//
// Réglages à vérifier : décalage horaire du serveur (le panneau affiche l'heure de New York calculée : elle doit être
// juste), compte en mode « hedging » OBLIGATOIRE pour les entrées B, C et D, et pour WhatsApp / Telegram autoriser l'adresse dans
// Outils > Options > Expert Advisors > « Autoriser WebRequest pour les URL listées ».
#property copyright   "Bot-Trading"
#property version     "10.00"
#property description "Strategy V10 : cassure du range de 9:30 (v7 : pyramide à +2R, règle mémoire, jours FOMC et fériés exclus) + repli sur le VWAP + 3 continuations (bougies de 9:35 à 9:45). Stop élargi (profil Confort) par défaut. Nasdaq uniquement."

#include <Trade\Trade.mqh>

enum ENUM_SRV_DST
  {
   SRV_DST_US   = 0, // Heure d'été américaine (la plupart des brokers GMT+2/+3)
   SRV_DST_EU   = 1, // Heure d'été européenne
   SRV_DST_NONE = 2  // Pas d'heure d'été
  };

//--- paramètres
input group "Risque"
input double       InpRiskPct   = 0.25;         // Risque par trade (% du solde), si l'interface n'en donne pas. 0,25 % comme la V9 ; le remonter est ta décision

input group "Interface Étrave"
input bool         InpUseUI     = true;         // Lire le risque, les cases et Telegram dans l'interface Étrave

input group "Heure du serveur du broker"
input int          InpSrvGMT    = 2;            // Décalage GMT du serveur en hiver (heures)
input ENUM_SRV_DST InpSrvDST    = SRV_DST_US;   // Heure d'été du serveur

input group "Règles de base (heure de New York) — valeurs du test"
input string       InpOR        = "09:30";      // Bougie M5 du range
input string       InpPre       = "09:00";      // Début de la fenêtre de l'élan (jusqu'au range)
input int          InpLiveBars  = 2;            // Ordres valables (bougies M5 après le range)
input string       InpFlat      = "15:50";      // Sortie de fin de journée
input string       InpFlatShort = "12:45";      // Sortie les jours fériés américains et les demi-séances
input bool         InpUseRSI    = true;         // Filtre RSI M5 (achat > 50, vente < 50)
input int          InpRSILen    = 14;           // Longueur du RSI
input bool         InpUseExt    = true;         // Filtre d'élan (le range de 9:30 dépasse 9:00-9:30)
input double       InpBeR       = 1.5;          // Stop au prix d'entrée dès (R), 0 = désactivé
input double       InpTgtR      = 0.0;          // Objectif (R), 0 = sortie en fin de journée

input group "Pyramide — valeurs du test"
input bool         InpUsePyr    = true;         // Pyramide sur gain
input double       InpPyrR      = 2.0;          // Ajout quand une bougie M5 clôture à (R)
input double       InpPyrSize   = 2.0;          // Taille de l'ajout (× la position de départ ; 2 = pire cas -1R)
input double       InpPyrGap    = 1.0;          // Stop de l'ensemble : distance sous le prix de l'ajout (R)

input group "Filtres v7 — valeurs du test"
input bool         InpUseMem    = true;         // Mémoire : après un trade gagnant, sauter le signal suivant
input double       InpMemR      = 1.0;          // Un trade compte comme gagnant au-delà de (R). Confort : 1 ; Tendance (V9) : 0,05
input bool         InpSkipFomc  = true;         // Aucun ordre les jours de décision de la Fed (FOMC)
input string       InpFomc      = "";           // Jours FOMC après 2026 : aaaa.mm.jj séparés par des virgules
input bool         InpSkipShort = true;         // Aucun ordre les jours fériés américains et demi-séances

input group "V8 — entrées de plus les jours où la cassure est prise (valeurs du test)"
input bool         InpUseB      = true;         // B : entrée sur repli vers le VWAP de séance
input double       InpBTol      = 0.10;         // B : tolérance autour du VWAP (part du range)
input string       InpBEnd      = "14:00";      // B : plus de repli après cette heure (New York)
input double       InpBBuf      = 1.0;          // B : marge du stop au-delà des 2 dernières bougies M5 (points d'indice)
input bool         InpUseC      = false;        // C : entrée à heure fixe si la cassure tient (coupée en V9 : n'a pas tenu sur 2010-2017)
input string       InpCAt       = "10:00";      // C : heure de l'entrée (New York)

input group "V9 — continuations (D) et garde-fou coût (valeurs du test)"
input bool         InpUseD      = true;         // D : cassure des bougies M5 qui suivent le range, tant que la cassure A est ouverte
input int          InpDCount    = 3;            // D : nombre de bougies après celle du range (3 = 9:35, 9:40, 9:45 ; 7 au plus)
input int          InpDValid    = 10;           // D : durée de validité de chaque guet (minutes)
input bool         InpDPyr      = true;         // D : pyramide à +2R sur ces entrées, comme la cassure
input double       InpMaxCostR  = 0.25;         // Garde-fou : pas d'ordre si spread + 2 glissements dépasse cette part du range (0 = coupé)
input double       InpCostSlip  = 1.0;          // Garde-fou : glissement supposé par exécution (points d'indice)

input group "V10 — largeur du stop (3 = profil Confort ; 1 = profil Tendance, la V9)"
input double       InpStopMult  = 3.0;          // Stop à N fois la distance normale ; les lots sont divisés d'autant (risque inchangé)

input group "Options (coupées par défaut : trouvées sur l'historique, pas encore vérifiées sur des données nouvelles)"
input bool         InpUseDI     = false;        // Tendance H4 : n'entrer que dans le sens du mouvement (DI+ contre DI-)
input int          InpDILen     = 14;           // Longueur du DI en H4 (lissage de Wilder)
input bool         InpUseSar    = false;        // SAR parabolique M5 (0,02 / 0,2) : n'entrer que s'il est du bon côté du prix
input bool         InpUseTime   = false;        // Sortie au temps : fermer le trade s'il n'a pas avancé à l'heure dite
input string       InpTimeAt    = "10:30";      // Heure de la sortie au temps (New York)
input double       InpTimeR     = 0.5;          // Sortie au temps si le trade est sous (R)

input group "Exécution"
input ulong        InpMagic     = 50930;        // Numéro magique
input int          InpDeviation = 30;           // Glissement maximal (points)
input string       InpComment   = "Strategy V10";     // Commentaire des ordres

input group "Notifications"
input bool         InpPush      = true;         // Notifications push MT5 (appli mobile MetaTrader 5)
input bool         InpWhatsApp  = false;        // WhatsApp via CallMeBot
input string       InpWaPhone   = "";           // Numéro WhatsApp au format international (+33…)
input string       InpWaKey     = "";           // Clé API CallMeBot
input bool         InpTelegram  = false;        // Telegram
input string       InpTgToken   = "";           // Jeton du bot Telegram
input string       InpTgChat    = "";           // Chat ID Telegram

input group "Affichage"
input bool         InpDraw      = true;         // Dessiner le range, la fenêtre de l'élan et les ordres
input bool         InpPanel     = true;         // Panneau d'information

//--- constantes
#define BAR 300   // une bougie M5 en secondes
#define BOT         "Étrave"
#define UI_DIR      "Etrave\\"   // sous-dossier du dossier commun de MetaTrader, partagé avec l'interface
#define UI_PERIOD   2            // secondes entre deux lectures des réglages et deux écritures de l'état
#define RISK_MIN    0.05         // bornes du risque lu dans l'interface (% du solde) ; hors bornes, la valeur est ignorée
#define RISK_MAX    20.0
#define LEVER_MAX   2000.0
#define MARGIN_USE  0.90         // part de la marge libre que la position, pyramide comprise, peut demander
#define CMD_MAX_AGE 120          // secondes : une demande de l'interface plus vieille est ignorée
#define QUEUE_MAX   20           // messages en attente d'envoi, au plus

//--- outils
CTrade trade;
int    hRSI = INVALID_HANDLE;
int    hDI  = INVALID_HANDLE;   // v7 option : DI de Wilder en H4
int    hSAR = INVALID_HANDLE;   // v7 option : SAR parabolique en M5
int    mTimeAt = 0;             // v7 option : heure de la sortie au temps, en minutes depuis minuit (New York)
string GV;                      // préfixe des variables globales et des objets
int    mOR, mPre, mFlat, mFlatShort;   // heures en minutes depuis minuit (New York)

//--- état du jour
int      gDay       = 0;        // date NY (aaaammjj) du dernier range traité
bool     gSetupDue  = false;    // range à préparer (au besoin sur plusieurs ticks si le RSI n'est pas prêt)
bool     gPend      = false;    // ordres en attente (gérés par l'EA)
int      gPendDir   = 0;        // 0 = les deux côtés, 1 = achat seulement, -1 = vente seulement
datetime gOrTime    = 0;        // heure serveur de la bougie du range
double   gOrH = 0, gOrL = 0;
double   gLots      = 0;
double   gRiskMoney = 0;        // somme risquée (lots × range), devise du compte
int      gFails     = 0;
bool     gSrvL      = false;    // ordre Buy Stop posé chez le courtier aujourd'hui (sinon l'EA surveille le côté achat)
bool     gSrvS      = false;    // ordre Sell Stop posé chez le courtier aujourd'hui
bool     gDelDue    = false;    // des ordres en attente restent à supprimer (refus du courtier : réessayé à chaque cotation)
datetime gGoneAt    = 0;        // heure où les ordres posés ont disparu sans position (exécution en cours ou annulation)
bool     gSkipNext  = false;    // v7 mémoire : le dernier trade pris était gagnant, le prochain signal déclenché sera sauté
bool     gObserve   = false;    // v7 mémoire : jour d'observation (aucun ordre posé, l'EA regarde si la cassure se déclenche)
bool     gTimeDone  = false;    // v7 option : la sortie au temps a déjà été examinée pour le trade en cours

//--- position
bool     gIn      = false;
ulong    gPos     = 0;
long     gPosId   = 0;
int      gDir     = 0;
double   gEntry   = 0, gSL = 0, gRisk = 0;
bool     gBE      = false;
bool     gTPset   = true;
datetime gFillBar = 0;
int      gPosDay  = 0;
string   gCloseWhy = "";
int      gWaitClose = 0;
bool     gPyr     = false;      // l'ajout a été fait
bool     gUsePyrToday = true;   // faux si le broker a refusé l'ajout : pas de nouvel essai sur ce trade
long     gPosId2  = 0;          // position de l'ajout (compte hedging)
double   gVStop   = 0;          // stop remonté (prix d'entrée ou +1R), surveillé aussi par l'EA ; 0 = aucun

//--- V8 : entrées B (repli VWAP) et C (heure fixe), chacune gérée comme une « jambe » indépendante du trade de cassure
struct SLeg
  {
   string   nom;         // "B" ou "C"
   string   titre;       // texte des messages
   ulong    magic;       // numéro magique de la jambe (InpMagic + 1 ou + 2)
   bool     pyrOk;       // cette jambe peut-elle recevoir une pyramide ?
   bool     pyrFree;     // la pyramide n'a pas encore été tentée sur ce trade
   bool     enPos;       // position ouverte
   bool     done;        // jambe déjà jouée ou abandonnée aujourd'hui
   int      dir;
   double   entry;
   double   sl;
   double   risk;        // distance au stop de départ (1R de la jambe, en prix)
   double   lots;
   double   vstop;       // stop remonté, surveillé aussi par l'EA ; 0 = aucun
   double   riskMoney;   // somme risquée par le trade de cassure du jour : le R de la jambe s'y rapporte
   double   balStart;
   bool     be;
   bool     pyr;
   datetime fillBar;
   int      day;
   long     id;
   long     id2;
   string   closeWhy;
   int      wait;
   bool     arm;         // V9 (D) : guet armé, l'EA surveille le niveau de déclenchement
   double   trig;        // V9 (D) : niveau de déclenchement (extrême de la bougie)
   double   stp;         // V9 (D) : stop prévu (autre extrême de la bougie)
   datetime exp;         // V9 (D) : fin de validité du guet
  };
SLeg     gB, gC;
#define  D_MAX 7
SLeg     gD[D_MAX];              // V9 : entrées de continuation D1 à D7 (InpDCount premières utilisées)
int      gV8Day       = 0;       // date NY du jour où la cassure a été prise : les jambes ne vivent que ce jour-là
int      gV8Dir       = 0;
double   gV8OrH = 0, gV8OrL = 0; // range du jour de la cassure
double   gV8Lots      = 0;       // lots du trade de cassure (plafond des jambes)
double   gV8RiskMoney = 0;       // somme risquée par le trade de cassure (plafond du risque des jambes)
datetime gV8BreakBar  = 0;       // bougie M5 de la cassure
bool     gV8Invalid   = false;   // une bougie M5 a clôturé de l'autre côté du range : plus de repli VWAP aujourd'hui
bool     gV8StopHit   = false;   // le stop du range a été touché depuis la cassure : pas d'entrée C
bool     gLegsOk      = true;    // compte « hedging » : les jambes B et C sont possibles
int      mBEnd = 0, mCAt = 0;    // heures de fin de B et d'entrée de C, en minutes depuis minuit (New York)

//--- interface Étrave : valeurs en vigueur (celles de l'interface, sinon celles saisies dans MetaTrader)
double   gRiskPct   = 0;        // risque par trade, % du solde
string   gRiskSrc   = "mt5";    // d'où il vient : "interface" ou "mt5"
double   gLever     = 0;        // levier du courtier saisi dans l'interface (0 = non saisi)
bool     gActive    = true;     // faux = case de l'instrument décochée : plus de nouveau trade
string   gInstr     = "autre";  // "nasdaq" (commandé par la case de l'interface) ou "autre", d'après le nom du symbole
string   gSymFile   = "";       // nom du symbole, réduit aux caractères sûrs (nom des fichiers, demandes de l'interface)
bool     gUiLoaded  = false;    // les réglages ont été lus au moins une fois
bool     gTgOn      = false;    // Telegram actif
string   gTgToken   = "", gTgChat = "";
string   gTgLast    = "jamais"; // résultat du dernier envoi Telegram : ok, bloque (WebRequest interdit) ou refus <code>
string   gTgTest    = "";       // réponse à la dernière demande d'essai : <numéro>:<résultat>
long     gTestSeen  = -1;       // dernière demande d'essai vue (-1 = fichier jamais lu)
long     gCloseSeen = 0;        // dernière demande de clôture traitée
bool     gCloseDue  = false;
bool     gClockOk   = true;     // l'heure du serveur correspond aux réglages
double   gBalStart  = 0;        // solde au moment de l'entrée (résultat du trade en %)
string   gQueue[];              // messages WhatsApp / Telegram en attente : envoyés APRÈS le passage des ordres

//--- statistiques en R
int    gN = 0, gWin = 0, gStreak = 0, gWorst = 0;
double gSumR = 0, gPeak = 0, gDD = 0;
string gDayTxt  = "En attente de 9:35 NY";
string gFiltTxt = "—";
datetime gLastBar = 0;

//+------------------------------------------------------------------+
//| Heure de New York                                                |
//+------------------------------------------------------------------+
datetime MakeDate(int y, int m, int d)
  {
   MqlDateTime s;
   ZeroMemory(s);
   s.year = y;
   s.mon  = m;
   s.day  = d;
   return StructToTime(s);
  }

datetime NthSunday(int y, int m, int n)
  {
   datetime t = MakeDate(y, m, 1);
   MqlDateTime s;
   TimeToStruct(t, s);
   int add = (7 - s.day_of_week) % 7;
   return t + (add + 7 * (n - 1)) * 86400;
  }

datetime LastSunday(int y, int m)
  {
   datetime t = (m == 12 ? MakeDate(y + 1, 1, 1) : MakeDate(y, m + 1, 1)) - 86400;
   MqlDateTime s;
   TimeToStruct(t, s);
   return t - s.day_of_week * 86400;
  }

bool UsDst(datetime utc)   // du 2e dimanche de mars 2:00 au 1er dimanche de novembre 2:00 (heure locale)
  {
   MqlDateTime s;
   TimeToStruct(utc, s);
   return utc >= NthSunday(s.year, 3, 2) + 7 * 3600 && utc < NthSunday(s.year, 11, 1) + 6 * 3600;
  }

bool EuDst(datetime utc)   // du dernier dimanche de mars au dernier dimanche d'octobre, 1:00 UTC
  {
   MqlDateTime s;
   TimeToStruct(utc, s);
   return utc >= LastSunday(s.year, 3) + 3600 && utc < LastSunday(s.year, 10) + 3600;
  }

long ServerOffsetSec(datetime srv)
  {
   long     base = (long)InpSrvGMT * 3600;
   datetime utc  = (datetime)(srv - base);
   bool     dst  = InpSrvDST == SRV_DST_US ? UsDst(utc) : InpSrvDST == SRV_DST_EU ? EuDst(utc) : false;
   return base + (dst ? 3600 : 0);
  }

datetime ToNY(datetime srv)
  {
   datetime utc = (datetime)(srv - ServerOffsetSec(srv));
   return (datetime)(utc - 5 * 3600 + (UsDst(utc) ? 3600 : 0));
  }

int NYDate(datetime ny)
  {
   MqlDateTime s;
   TimeToStruct(ny, s);
   return s.year * 10000 + s.mon * 100 + s.day;
  }

int NYMin(datetime ny)
  {
   MqlDateTime s;
   TimeToStruct(ny, s);
   return s.hour * 60 + s.min;
  }

int ParseHM(string s)
  {
   string p[];
   if(StringSplit(s, ':', p) != 2)
      return -1;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
  }

//+------------------------------------------------------------------+
//| Jours fériés américains et demi-séances                           |
//+------------------------------------------------------------------+
// Ces jours-là l'indice ne cote au mieux que jusqu'à 13:00 New York : la sortie de 15:50 tomberait marché fermé et la
// position passerait la fermeture. La sortie se fait donc à InpFlatShort. Règles de la Bourse de New York, calculées
// (aucune liste à tenir à jour) ; contrôlées sur 2022-2025. Une fermeture exceptionnelle (deuil national…) n'y est pas.
datetime NthDow(int y, int m, int dow, int n)   // n-ième jour « dow » du mois (0 = dimanche … 6 = samedi)
  {
   datetime t = MakeDate(y, m, 1);
   MqlDateTime s;
   TimeToStruct(t, s);
   return t + ((dow - s.day_of_week + 7) % 7 + 7 * (n - 1)) * 86400;
  }

datetime LastDow(int y, int m, int dow)   // dernier jour « dow » du mois
  {
   datetime t = (m == 12 ? MakeDate(y + 1, 1, 1) : MakeDate(y, m + 1, 1)) - 86400;
   MqlDateTime s;
   TimeToStruct(t, s);
   return t - ((s.day_of_week - dow + 7) % 7) * 86400;
  }

datetime Observed(datetime d)   // un férié qui tombe un samedi est chômé le vendredi, un dimanche le lundi
  {
   MqlDateTime s;
   TimeToStruct(d, s);
   return s.day_of_week == 6 ? d - 86400 : s.day_of_week == 0 ? d + 86400 : d;
  }

datetime GoodFriday(int y)   // vendredi saint : deux jours avant Pâques (calcul grégorien)
  {
   int a = y % 19, b = y / 100, c = y % 100, d = b / 4, e = b % 4, f = (b + 8) / 25, g = (b - f + 1) / 3;
   int h = (19 * a + b - d - g + 15) % 30, i = c / 4, k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7;
   int m = (a + 11 * h + 22 * l) / 451;
   int mo = (h + l - 7 * m + 114) / 31, da = (h + l - 7 * m + 114) % 31 + 1;
   return MakeDate(y, mo, da) - 2 * 86400;
  }

bool ShortDay(datetime ny)   // « ny » : une heure de New York quelconque du jour à juger
  {
   MqlDateTime s;
   TimeToStruct(ny, s);
   int      y  = s.year;
   datetime d  = MakeDate(y, s.mon, s.day);
   datetime tg = NthDow(y, 11, 4, 4);          // Thanksgiving : 4e jeudi de novembre
   datetime j4 = MakeDate(y, 7, 4);
   MqlDateTime s4;
   TimeToStruct(j4, s4);
   // veille du 4 juillet : demi-séance quand le 4 tombe du mardi au vendredi ; par prudence aussi le jeudi quand il tombe un samedi
   datetime pre4 = (s4.day_of_week >= 2 && s4.day_of_week <= 5) ? j4 - 86400 : s4.day_of_week == 6 ? j4 - 2 * 86400 : (datetime)0;
   // fériés : jour de l'an (et celui de l'année suivante chômé le 31 décembre), Martin Luther King, Presidents' Day,
   // vendredi saint, Memorial Day, Juneteenth, 4 juillet, Labor Day, Thanksgiving, Noël
   if(d == Observed(MakeDate(y, 1, 1)) || d == Observed(MakeDate(y + 1, 1, 1)) || d == NthDow(y, 1, 1, 3) || d == NthDow(y, 2, 1, 3) ||
      d == GoodFriday(y) || d == LastDow(y, 5, 1) || d == Observed(MakeDate(y, 6, 19)) || d == Observed(j4) || d == NthDow(y, 9, 1, 1) ||
      d == tg || d == Observed(MakeDate(y, 12, 25)))
      return true;
   // demi-séances : lendemain de Thanksgiving, veille de Noël, veille du 4 juillet
   return d == tg + 86400 || d == MakeDate(y, 12, 24) || (pre4 != 0 && d == pre4);
  }

int FlatMin(datetime ny) { return ShortDay(ny) ? mFlatShort : mFlat; }   // heure de sortie du jour, en minutes

//+------------------------------------------------------------------+
//| v7 : jours de décision de la Fed (FOMC)                           |
//+------------------------------------------------------------------+
// Réunions prévues de 2018 à 2026 (dates publiées à l'avance par la Réserve fédérale ; les réunions d'urgence de mars
// 2020 n'y sont pas). Les années suivantes se saisissent dans « Jours FOMC après 2026 » : aaaa.mm.jj séparés par des
// virgules. Sans mise à jour, l'EA trade simplement ces jours-là comme la v6.
const int FOMC_DATES[] =
  {
   20180131, 20180321, 20180502, 20180613, 20180801, 20180926, 20181108, 20181219,
   20190130, 20190320, 20190501, 20190619, 20190731, 20190918, 20191030, 20191211,
   20200129, 20200429, 20200610, 20200729, 20200916, 20201105, 20201216, 20210127,
   20210317, 20210428, 20210616, 20210728, 20210922, 20211103, 20211215, 20220126,
   20220316, 20220504, 20220615, 20220727, 20220921, 20221102, 20221214, 20230201,
   20230322, 20230503, 20230614, 20230726, 20230920, 20231101, 20231213, 20240131,
   20240320, 20240501, 20240612, 20240731, 20240918, 20241107, 20241218, 20250129,
   20250319, 20250507, 20250618, 20250730, 20250917, 20251029, 20251210, 20260128,
   20260318, 20260429, 20260617, 20260729, 20260916, 20261028, 20261209
  };

bool IsFomc(int ymd)   // ymd : date de New York au format aaaammjj
  {
   for(int i = 0; i < ArraySize(FOMC_DATES); i++)
      if(FOMC_DATES[i] == ymd)
         return true;
   string parts[];
   int n = StringSplit(InpFomc, ',', parts);
   for(int i = 0; i < n; i++)
     {
      string p = parts[i];
      StringTrimLeft(p);
      StringTrimRight(p);
      StringReplace(p, ".", "");
      StringReplace(p, "-", "");
      StringReplace(p, "/", "");
      if(StringLen(p) == 8 && (int)StringToInteger(p) == ymd)
         return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Textes                                                            |
//+------------------------------------------------------------------+
string Px(double p)  { return DoubleToString(p, _Digits); }
string RTxt(double r) { return (r >= 0 ? "+" : "") + DoubleToString(r, 1) + "R"; }
string Pts(double d)  { return DoubleToString(d, _Digits) + " pts"; }
string PctS(double v)   { return (v >= 0 ? "+" : "") + DoubleToString(v, 2) + " %"; }
string RiskTxt(double v) { return DoubleToString(v, 2) + " %"; }
string Money(double v)  { return (v >= 0 ? "+" : "") + DoubleToString(v, 2) + " " + AccountInfoString(ACCOUNT_CURRENCY); }
// Pictogrammes des messages, écrits par leur numéro pour ne pas dépendre de l'encodage de ce fichier
string Ico(ushort code) { return ShortToString(code) + " "; }
#define I_ORDERS  Ico(0x23F0)   // réveil
#define I_BUY     Ico(0x2B06)   // flèche vers le haut
#define I_SELL    Ico(0x2B07)   // flèche vers le bas
#define I_LOCK    Ico(0x26A1)   // éclair
#define I_ADD     Ico(0x2795)   // plus
#define I_WIN     Ico(0x2705)   // coche verte
#define I_LOSS    Ico(0x274C)   // croix rouge
#define I_FLAT    Ico(0x26AA)   // rond blanc
#define I_NONE    Ico(0x26D4)   // sens interdit
#define I_WARN    Ico(0x26A0)   // attention
#define I_GEAR    Ico(0x2699)   // réglage
#define I_HAND    Ico(0x270B)   // main

//+------------------------------------------------------------------+
//| Notifications : journal, push MT5, WhatsApp (CallMeBot), Telegram |
//+------------------------------------------------------------------+
string UrlEncode(string s)
  {
   uchar b[];
   int   n = StringToCharArray(s, b, 0, WHOLE_ARRAY, CP_UTF8);
   string out = "";
   for(int i = 0; i < n; i++)
     {
      uchar c = b[i];
      if(c == 0)
         break;
      if((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~')
         out += CharToString(c);
      else
         out += StringFormat("%%%02X", c);
     }
   return out;
  }

void WebFail(string who, string host)
  {
   PrintFormat("%s : envoi impossible (erreur %d). Ajoute %s dans Outils > Options > Expert Advisors > Autoriser WebRequest.", who, GetLastError(), host);
  }

void SendWhatsApp(string msg)
  {
   string url = "https://api.callmebot.com/whatsapp.php?phone=" + UrlEncode(InpWaPhone) + "&text=" + UrlEncode(msg) + "&apikey=" + UrlEncode(InpWaKey);
   char   data[], res[];
   string hdr;
   ResetLastError();
   int code = WebRequest("GET", url, "", 5000, data, res, hdr);
   if(code == -1)
      WebFail("WhatsApp", "https://api.callmebot.com");
   else if(code != 200)
      PrintFormat("WhatsApp : réponse %d du serveur (vérifie le numéro, la clé ou le chat ID)", code);
  }

string SendTelegram(string msg)   // "ok", "bloque" (MetaTrader interdit l'adresse) ou "refus <code>"
  {
   string url  = "https://api.telegram.org/bot" + gTgToken + "/sendMessage";
   string body = "chat_id=" + UrlEncode(gTgChat) + "&text=" + UrlEncode(msg);
   char   data[], res[];
   string hdr;
   int len = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(data, len - 1);   // sans le zéro final
   ResetLastError();
   int code = WebRequest("POST", url, "Content-Type: application/x-www-form-urlencoded\r\n", 5000, data, res, hdr);
   if(code == -1)
     {
      WebFail("Telegram", "https://api.telegram.org");
      return "bloque";
     }
   if(code != 200)
     {
      PrintFormat("Telegram : réponse %d du serveur (vérifie le jeton et la discussion)", code);
      return "refus " + IntegerToString(code);
     }
   return "ok";
  }

// Journal et notification push tout de suite ; WhatsApp et Telegram passent par une file, vidée par FlushNotifs()
// en fin de OnTick : un envoi lent (WebRequest attend jusqu'à 5 secondes) ne retarde plus ni l'entrée ni un stop.
void Notify(string msg)
  {
   string full = BOT + " · " + _Symbol + "\n" + msg;
   Print(full);
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return;
   if(InpPush)
     {
      string p = full;
      StringReplace(p, "\n", " · ");
      SendNotification(StringSubstr(p, 0, 255));
     }
   bool wa = InpWhatsApp && InpWaPhone != "" && InpWaKey != "";
   int  n  = ArraySize(gQueue);
   if((wa || gTgOn) && n < QUEUE_MAX)
     {
      ArrayResize(gQueue, n + 1);
      gQueue[n] = full;
     }
  }

void FlushNotifs()
  {
   int n = ArraySize(gQueue);
   if(n == 0)
      return;
   bool wa = InpWhatsApp && InpWaPhone != "" && InpWaKey != "";
   for(int i = 0; i < n; i++)
     {
      if(wa)
         SendWhatsApp(gQueue[i]);
      if(gTgOn)
         gTgLast = SendTelegram(gQueue[i]);
     }
   ArrayResize(gQueue, 0);
  }

//+------------------------------------------------------------------+
//| Sauvegarde de l'état (redémarrage de MT5 ou de l'EA)             |
//+------------------------------------------------------------------+
void   Sv(string k, double v) { GlobalVariableSet(GV + k, v); }
double Ld(string k, double d) { return GlobalVariableCheck(GV + k) ? GlobalVariableGet(GV + k) : d; }

void SaveState()
  {
   if(MQLInfoInteger(MQL_TESTER))
      return;
   Sv("day", gDay); Sv("pend", gPend); Sv("pdir", gPendDir); Sv("ortime", (double)gOrTime);
   Sv("srvl", gSrvL); Sv("srvs", gSrvS);
   Sv("skipnext", gSkipNext); Sv("observe", gObserve); Sv("timedone", gTimeDone);
   Sv("v8day", gV8Day); Sv("v8dir", gV8Dir); Sv("v8orh", gV8OrH); Sv("v8orl", gV8OrL); Sv("v8lots", gV8Lots);
   Sv("v8rm", gV8RiskMoney); Sv("v8bar", (double)gV8BreakBar); Sv("v8inv", gV8Invalid); Sv("v8hit", gV8StopHit);
   Sv("orh", gOrH); Sv("orl", gOrL); Sv("lots", gLots); Sv("rm", gRiskMoney);
   Sv("in", gIn); Sv("pos", (double)gPos); Sv("posid", (double)gPosId); Sv("dir", gDir);
   Sv("entry", gEntry); Sv("sl", gSL); Sv("risk", gRisk); Sv("be", gBE); Sv("tpset", gTPset);
   Sv("fillbar", (double)gFillBar); Sv("posday", gPosDay);
   Sv("pyr", gPyr); Sv("posid2", (double)gPosId2); Sv("vstop", gVStop); Sv("bal0", gBalStart);
   Sv("n", gN); Sv("win", gWin); Sv("streak", gStreak); Sv("worst", gWorst);
   Sv("sumr", gSumR); Sv("peak", gPeak); Sv("dd", gDD);
  }

void LoadState()
  {
   gDay = (int)Ld("day", 0); gPend = Ld("pend", 0) != 0; gPendDir = (int)Ld("pdir", 0); gOrTime = (datetime)Ld("ortime", 0);
   gSrvL = Ld("srvl", 0) != 0; gSrvS = Ld("srvs", 0) != 0;
   gSkipNext = Ld("skipnext", 0) != 0; gObserve = Ld("observe", 0) != 0; gTimeDone = Ld("timedone", 0) != 0;
   gV8Day = (int)Ld("v8day", 0); gV8Dir = (int)Ld("v8dir", 0); gV8OrH = Ld("v8orh", 0); gV8OrL = Ld("v8orl", 0); gV8Lots = Ld("v8lots", 0);
   gV8RiskMoney = Ld("v8rm", 0); gV8BreakBar = (datetime)Ld("v8bar", 0); gV8Invalid = Ld("v8inv", 0) != 0; gV8StopHit = Ld("v8hit", 0) != 0;
   LegLoad(gB); LegLoad(gC);
   for(int kd = 0; kd < D_MAX; kd++)
      LegLoad(gD[kd]);
   gOrH = Ld("orh", 0); gOrL = Ld("orl", 0); gLots = Ld("lots", 0); gRiskMoney = Ld("rm", 0);
   gIn = Ld("in", 0) != 0; gPos = (ulong)Ld("pos", 0); gPosId = (long)Ld("posid", 0); gDir = (int)Ld("dir", 0);
   gEntry = Ld("entry", 0); gSL = Ld("sl", 0); gRisk = Ld("risk", 0); gBE = Ld("be", 0) != 0; gTPset = Ld("tpset", 1) != 0;
   gFillBar = (datetime)Ld("fillbar", 0); gPosDay = (int)Ld("posday", 0);
   gPyr = Ld("pyr", 0) != 0; gPosId2 = (long)Ld("posid2", 0); gVStop = Ld("vstop", 0); gBalStart = Ld("bal0", 0);
   gCloseSeen = (long)Ld("closeseen", 0);
   gN = (int)Ld("n", 0); gWin = (int)Ld("win", 0); gStreak = (int)Ld("streak", 0); gWorst = (int)Ld("worst", 0);
   gSumR = Ld("sumr", 0); gPeak = Ld("peak", 0); gDD = Ld("dd", 0);
  }

//+------------------------------------------------------------------+
//| Dessins                                                           |
//+------------------------------------------------------------------+
void Box(string name, datetime t1, double p1, datetime t2, double p2, color c, bool fill, ENUM_LINE_STYLE st)
  {
   if(!InpDraw)
      return;
   ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

void Seg(string name, datetime t1, datetime t2, double p, color c, ENUM_LINE_STYLE st, int w)
  {
   if(!InpDraw)
      return;
   ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_TREND, 0, t1, p, t2, p);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, w);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

void Txt(string name, datetime t, double p, string s, color c, ENUM_ANCHOR_POINT a)
  {
   if(!InpDraw)
      return;
   ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
   ObjectSetString(0, name, OBJPROP_TEXT, s);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, a);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
  }

string ObjDay(string k) { return GV + k + "_" + (string)gDay; }

void DropPendingDraw()
  {
   string k[] = {"pH", "pL", "tH", "tL", "bk", "tb"};
   for(int i = 0; i < ArraySize(k); i++)
      ObjectDelete(0, ObjDay(k[i]));
  }

void DropDayDraw()
  {
   DropPendingDraw();
   ObjectDelete(0, ObjDay("or"));
   ObjectDelete(0, ObjDay("pre"));
   ObjectDelete(0, ObjDay("ort"));
  }

//+------------------------------------------------------------------+
//| Position                                                          |
//+------------------------------------------------------------------+
ulong FindPos()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return tk;
     }
   return 0;
  }

//+------------------------------------------------------------------+
//| Ordres stop posés chez le courtier                                |
//+------------------------------------------------------------------+
bool MyOrder(ulong tk)   // ordre en attente de cet EA sur ce symbole (OrderGetTicket l'a déjà sélectionné)
  {
   return tk != 0 && OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic;
  }

bool HasPending(int d)   // l'ordre stop du côté d (1 achat, -1 vente) est-il encore posé chez le courtier ?
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(!MyOrder(tk))
         continue;
      ENUM_ORDER_TYPE t = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if((d == 1 && t == ORDER_TYPE_BUY_STOP) || (d == -1 && t == ORDER_TYPE_SELL_STOP))
         return true;
     }
   return false;
  }

// Supprime les ordres stop de l'EA encore posés ; false si le courtier en a refusé une suppression (réessayé ensuite)
bool DeletePendings()
  {
   bool ok = true;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(!MyOrder(tk))
         continue;
      ENUM_ORDER_TYPE t = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(t != ORDER_TYPE_BUY_STOP && t != ORDER_TYPE_SELL_STOP)
         continue;
      if(!trade.OrderDelete(tk))
        {
         ok = false;
         PrintFormat("Suppression de l'ordre %I64u refusée (%d) : %s", tk, trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
     }
   return ok;
  }

// V10 : stop du trade de cassure = InpStopMult fois le range, compté depuis le niveau de cassure (1 = l'autre bord du range, la V9)
double StopA(int d)
  {
   double rg = gOrH - gOrL;
   return d == 1 ? gOrH - InpStopMult * rg : gOrL + InpStopMult * rg;
  }

// Pose l'ordre stop du côté d chez le courtier (achat au high, vente au low), avec son stop de l'autre côté du range et
// une expiration à la fin de validité. false = pas posé (prix déjà au niveau ou trop près, refus) : l'EA surveille
// alors ce côté et entre au marché quand le prix l'atteint, comme les versions précédentes.
bool PlaceStop(int d)
  {
   double price = NormalizeDouble(d == 1 ? gOrH : gOrL, _Digits);
   double sl    = NormalizeDouble(StopA(d), _Digits);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double gap   = MathMax(SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL), SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL)) * _Point;
   if(d == 1 ? price - ask <= gap : bid - price <= gap)
      return false;
   int em = (int)SymbolInfoInteger(_Symbol, SYMBOL_EXPIRATION_MODE);
   ENUM_ORDER_TYPE_TIME tt = (em & SYMBOL_EXPIRATION_SPECIFIED) != 0 ? ORDER_TIME_SPECIFIED : (em & SYMBOL_EXPIRATION_GTC) != 0 ? ORDER_TIME_GTC : ORDER_TIME_DAY;
   datetime exp = tt == ORDER_TIME_SPECIFIED ? gOrTime + (InpLiveBars + 1) * BAR : 0;   // l'EA annule de toute façon à cette heure
   bool placed = false;
   for(int k = 0; k < 2 && !placed; k++)
     {
      bool ok = d == 1 ? trade.BuyStop(gLots, price, _Symbol, sl, 0, tt, exp, InpComment) : trade.SellStop(gLots, price, _Symbol, sl, 0, tt, exp, InpComment);
      uint rc = trade.ResultRetcode();
      placed = ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED);
      if(placed)
         break;
      PrintFormat("Ordre %s refusé (%d) : %s", d == 1 ? "Buy Stop" : "Sell Stop", rc, trade.ResultRetcodeDescription());
      if(rc != TRADE_RETCODE_INVALID_FILL)
         break;
      trade.SetTypeFilling(ORDER_FILLING_RETURN);   // certains courtiers n'acceptent que ce mode pour un ordre en attente
     }
   trade.SetTypeFillingBySymbol(_Symbol);
   return placed;
  }

// Plus de trade aujourd'hui : ordres supprimés chez le courtier, dessins effacés, message
void CancelDay(string why, string title)
  {
   bool obs = gObserve;   // v7 : jour d'observation de la règle mémoire (aucun ordre n'avait été posé)
   gObserve = false;
   gPend = false;
   gDelDue = !DeletePendings();
   DropDayDraw();
   if(obs)
     {
      // le signal ne s'est pas déclenché : gSkipNext reste vrai, la règle attend le prochain signal
      gDayTxt = "Pas de signal (" + why + ") : la règle mémoire reste en attente";
      Notify(I_NONE + "PAS DE SIGNAL aujourd'hui\n" + why + "\nRègle mémoire : le prochain signal déclenché sera encore sauté");
      SaveState();
      return;
     }
   gDayTxt = "Pas de trade : " + why;
   Notify(title + "\n" + why);
   SaveState();
  }

// Compte hedging : si les deux ordres ont été exécutés avant que l'EA supprime le second, la position de sens contraire
// est fermée au marché (règle : le premier exécuté annule l'autre).
void CloseOpposite()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      int dir = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      if(dir == gDir || PositionGetInteger(POSITION_IDENTIFIER) == gPosId2)
         continue;
      if(trade.PositionClose(tk, InpDeviation))
         Notify(I_WARN + "Les deux ordres ont été exécutés : la position " + (dir == 1 ? "d'achat" : "de vente") + " en trop est fermée au marché");
     }
  }

void ClosePos(string why)   // ferme l'unité de départ et l'ajout
  {
   if(!gIn)
      return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      gCloseWhy = why;
      if(!trade.PositionClose(tk, InpDeviation))
         PrintFormat("Fermeture refusée (%d) : %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }

// Pose le même stop sur toutes les positions de l'EA ; false si une pose a été refusée (l'EA surveille alors lui-même)
bool SetStopAll(double sl)
  {
   bool ok = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      if(MathAbs(PositionGetDouble(POSITION_SL) - sl) < _Point / 2)
         continue;
      if(!trade.PositionModify(tk, sl, PositionGetDouble(POSITION_TP)))
        {
         ok = false;
         PrintFormat("Stop à %s refusé (%d), surveillé par l'EA", DoubleToString(sl, _Digits), trade.ResultRetcode());
        }
     }
   return ok;
  }

double OpenProfit()   // résultat latent de toutes les positions de l'EA
  {
   double p = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      p += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   return p;
  }

bool RecordClose(bool force)   // false = un deal de sortie n'est pas encore dans l'historique, réessayer
  {
   double net = 0, px = 0;
   long   reason = DEAL_REASON_EXPERT;
   datetime tx = TimeCurrent();
   long ids[2];
   ids[0] = gPosId;
   ids[1] = (gPosId2 != 0 && gPosId2 != gPosId) ? gPosId2 : 0;
   for(int p = 0; p < 2; p++)
     {
      if(ids[p] == 0)
         continue;
      bool out = false;
      if(HistorySelectByPosition(ids[p]))
        {
         for(int i = 0; i < HistoryDealsTotal(); i++)
           {
            ulong d = HistoryDealGetTicket(i);
            net += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_COMMISSION) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_FEE);
            long e = HistoryDealGetInteger(d, DEAL_ENTRY);
            if(e == DEAL_ENTRY_OUT || e == DEAL_ENTRY_OUT_BY)
              {
               out    = true;
               reason = HistoryDealGetInteger(d, DEAL_REASON);
               px     = HistoryDealGetDouble(d, DEAL_PRICE);
               tx     = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
              }
           }
        }
      if(!out && !force)
         return false;
     }
   double r   = gRiskMoney > 0 ? net / gRiskMoney : 0;
   string why = reason == DEAL_REASON_SL ? (gPyr ? "Stop remonté" : gBE ? "Stop à l'entrée" : "Stop") : reason == DEAL_REASON_TP ? "Objectif" : gCloseWhy != "" ? gCloseWhy : "Fermeture manuelle";
   gN++;
   gSumR += r;
   if(r > 0.05)
      gWin++;
   // v7 mémoire : après un trade gagnant, le prochain signal déclenché sera sauté (un seul)
   if(InpUseMem)
      gSkipNext = r > InpMemR;
   // série de pertes, comme dans le test : une sortie au prix d'entrée l'interrompt même si les frais la rendent négative
   gStreak = (why != "Stop à l'entrée" && r < -0.05) ? gStreak + 1 : 0;
   gWorst  = MathMax(gWorst, gStreak);
   gPeak   = MathMax(gPeak, gSumR);
   gDD     = MathMax(gDD, gPeak - gSumR);
   string id = (gDir == 1 ? "Achat" : "Vente");
   Txt(GV + "res_" + (string)gPosId, tx, px > 0 ? px : gEntry, " " + RTxt(r), r > 0.05 ? clrSeaGreen : r < -0.05 ? clrTomato : clrGray, ANCHOR_LEFT);
   double pct = gBalStart > 0 ? 100.0 * net / gBalStart : 0;
   AppendTrade(tx, r, net, why);
   Notify((r > 0.05 ? I_WIN : r < -0.05 ? I_LOSS : I_FLAT) + (gDir == 1 ? "ACHAT CLÔTURÉ : " : "VENTE CLÔTURÉE : ") + RTxt(r) + " · " + PctS(pct) + " · " + Money(net) +
          "\n" + why + (gPyr ? ", avec pyramide" : "") + (px > 0 ? " · sortie à " + Px(px) : "") +
          "\nSolde : " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + " " + AccountInfoString(ACCOUNT_CURRENCY) +
          "\nDepuis le début : " + (string)gN + " trades · " + RTxt(gSumR) +
          (InpUseMem && gSkipNext ? "\nRègle mémoire : trade gagnant, le prochain signal ne sera pas pris" : ""));
   gDayTxt = id + " terminé (" + why + ") : " + RTxt(r);
   return true;
  }

void SyncPosition()
  {
   ulong tk = FindPos();
   if(tk > 0 && !gIn)
     {
      if(!PositionSelectByTicket(tk))
         return;
      gIn      = true;
      gPos     = tk;
      gPosId   = PositionGetInteger(POSITION_IDENTIFIER);
      gDir     = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1;
      gEntry   = PositionGetDouble(POSITION_PRICE_OPEN);
      gSL      = StopA(gDir);
      gRisk    = MathAbs(gEntry - gSL);
      if(gRisk <= 0)
         gRisk = gOrH - gOrL;
      datetime t = (datetime)PositionGetInteger(POSITION_TIME);
      gFillBar = t - t % BAR;
      gPosDay  = NYDate(ToNY(t));
      gBE      = false;
      gTimeDone = false;   // v7 option : sortie au temps à examiner pour ce nouveau trade
      // V8 : la cassure du jour est prise, les entrées B et C deviennent possibles (même sens, même range, lots plafonnés)
      if(gOrH > gOrL && gOrL > 0 && gLots > 0 && gRiskMoney > 0 && gPosDay == gDay)
        {
         gV8Day = gPosDay; gV8Dir = gDir; gV8OrH = gOrH; gV8OrL = gOrL; gV8Lots = gLots; gV8RiskMoney = gRiskMoney;
         gV8BreakBar = gFillBar; gV8Invalid = false; gV8StopHit = false;
         gB.done = false; gC.done = false;
         LegSave(gB); LegSave(gC);
         for(int kd = 0; kd < D_MAX; kd++)
           {
            gD[kd].done = false;
            gD[kd].arm  = false;
            LegSave(gD[kd]);
           }
        }
      gPyr     = false;
      gUsePyrToday = true;
      gPosId2  = 0;
      gVStop   = 0;
      gTPset   = InpTgtR <= 0;
      gPend    = false;
      gDelDue  = !DeletePendings();   // le premier exécuté annule l'autre
      gGoneAt  = 0;
      gCloseWhy = "";
      gBalStart = AccountInfoDouble(ACCOUNT_BALANCE);
      DropPendingDraw();
      string id = gDir == 1 ? I_BUY + "ACHAT exécuté" : I_SELL + "VENTE exécutée";
      double lvlIn = gDir == 1 ? gOrH : gOrL;
      Notify(id + " à " + Px(gEntry) + " (glissement " + Pts((gEntry - lvlIn) * gDir) + " par rapport au niveau " + Px(lvlIn) + ")" +
             "\nStop : " + Px(gSL) + " (" + Money(-gRiskMoney) + ")" +
             (InpBeR > 0 ? "\nStop au prix d'entrée dès " + Px(gEntry + gDir * InpBeR * gRisk) + " (+" + DoubleToString(InpBeR, 1) + "R)" : "") +
             (InpUsePyr ? "\nPyramide : ajout si une bougie clôture à " + Px(gEntry + gDir * InpPyrR * gRisk) + " (" + RTxt(InpPyrR) + "), stop de l'ensemble " + DoubleToString(InpPyrGap, 1) + "R sous l'ajout" : "") +
             (InpTgtR > 0 ? "\nObjectif : " + Px(gEntry + gDir * InpTgtR * gRisk) : "") +
             (ShortDay(ToNY(t)) ? "\n" + I_WARN + "Jour férié ou demi-séance : sortie à " + InpFlatShort + " NY" : "\nSortie à " + InpFlat + " NY"));
      gDayTxt = (gDir == 1 ? "Achat" : "Vente") + " en cours";
      SaveState();
     }
   else if(tk == 0 && gIn)
     {
      gWaitClose++;
      if(RecordClose(gWaitClose > 50))
        {
         gIn  = false;
         gPos = 0;
         gWaitClose = 0;
         SaveState();
        }
     }
  }

//+------------------------------------------------------------------+
//| 9:35 NY : range, filtres, taille                                  |
//+------------------------------------------------------------------+
bool Setup()   // true = terminé (trade préparé ou pas de trade), false = données pas prêtes, réessayer au tick suivant
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   int n = CopyRates(_Symbol, PERIOD_M5, 0, 20, r);
   if(n < 3)
      return false;
   datetime ny1 = ToNY(r[1].time);
   int day = NYDate(ny1);
   if(NYMin(ny1) != mOR || day == gDay)
      return true;
   double rsi[];
   // Correctif EA-04 RSI (revue du 17/11/2026) : au premier tick de 9:35, l'indicateur peut ne pas avoir encore calculé
   // la nouvelle bougie ; la valeur lue en position 1 serait alors celle de 9:25. On attend qu'il soit à jour.
   if(InpUseRSI && BarsCalculated(hRSI) < Bars(_Symbol, PERIOD_M5))
      return false;
   bool rsiOk = CopyBuffer(hRSI, 0, 1, 1, rsi) == 1;
   if(InpUseRSI && !rsiOk)
      return false;
   // v7 options : indicateurs lus sur la dernière bougie entièrement close (H4 pour le DI, M5 de 9:30 pour le SAR)
   double diP[], diM[], sarV[];
   if(InpUseDI && (CopyBuffer(hDI, 1, 1, 1, diP) != 1 || CopyBuffer(hDI, 2, 1, 1, diM) != 1))
      return false;
   if(InpUseSar && CopyBuffer(hSAR, 0, 1, 1, sarV) != 1)
      return false;
   bool diOk  = InpUseDI && diP[0] != EMPTY_VALUE && diM[0] != EMPTY_VALUE;
   bool sarOk = InpUseSar && sarV[0] != EMPTY_VALUE && sarV[0] > 0;

   gDay    = day;
   gOrTime = r[1].time;
   gOrH    = r[1].high;
   gOrL    = r[1].low;
   double dist = gOrH - gOrL;

   // fenêtre de l'élan : bougies de 9:00 à 9:25 du même jour
   double   pH = -DBL_MAX, pL = DBL_MAX;
   int      cnt = 0;
   datetime pT0 = 0;
   for(int s = 2; s < n; s++)
     {
      datetime ny = ToNY(r[s].time);
      if(NYDate(ny) != day || NYMin(ny) < mPre)
         break;
      if(NYMin(ny) >= mOR)
         continue;
      pH  = MathMax(pH, r[s].high);
      pL  = MathMin(pL, r[s].low);
      pT0 = r[s].time;
      cnt++;
     }
   bool preOk = cnt >= 2;

   double rv   = rsiOk ? rsi[0] : 50;
   bool   rsiL = !InpUseRSI || rv > 50;
   bool   rsiS = !InpUseRSI || rv < 50;
   bool   extL = !InpUseExt || (preOk && gOrH >= pH);
   bool   extS = !InpUseExt || (preOk && gOrL <= pL);
   // v7 options : tendance H4 (DI+ au-dessus de DI- pour un achat) et SAR parabolique M5 (sous le prix pour un achat).
   // Un jour écarté par ces filtres n'est pas un signal : la règle mémoire n'est ni consommée ni armée.
   bool   trL  = (!InpUseDI || (diOk && diP[0] > diM[0])) && (!InpUseSar || (sarOk && sarV[0] < r[1].close));
   bool   trS  = (!InpUseDI || (diOk && diP[0] < diM[0])) && (!InpUseSar || (sarOk && sarV[0] > r[1].close));
   bool   okL  = rsiL && extL && trL;
   bool   okS  = rsiS && extS && trS;
   string whyL = !rsiL ? "RSI" : !extL ? (preOk ? "élan" : "pas de bougies 9:00-9:30") : !trL ? "tendance" : "";
   string whyS = !rsiS ? "RSI" : !extS ? (preOk ? "élan" : "pas de bougies 9:00-9:30") : !trS ? "tendance" : "";
   gPendDir = okL && okS ? 0 : okL ? 1 : okS ? -1 : 2;
   gFiltTxt = "Achat " + (okL ? "oui" : "non (" + whyL + ")") + " · Vente " + (okS ? "oui" : "non (" + whyS + ")") + (InpUseRSI ? " · RSI " + DoubleToString(rv, 0) : "");

   // case de l'instrument décochée dans l'interface : le range est relevé, aucun ordre n'est préparé
   if(!gActive)
     {
      gDayTxt = "Pas de trade : instrument désactivé dans l'interface";
      Print(BOT + " · " + _Symbol + " · " + gDayTxt);
      SaveState();
      return true;
     }

   // Correctif EA-01 (revue du 17/11/2026) : si l'heure du serveur ne correspond pas aux réglages, l'heure de New York
   // calculée est fausse et le range serait pris sur la mauvaise bougie (ex. : serveur à l'heure d'été européenne réglé
   // « US »). Aucun ordre ce jour-là ; la règle mémoire n'est pas touchée. Pas de contrôle dans le testeur (heure simulée).
   if(!MQLInfoInteger(MQL_TESTER))
     {
      CheckClock();
      if(!gClockOk)
        {
         string whyH = "l'heure du serveur ne correspond pas aux réglages « Décalage GMT du serveur » et « Heure d'été du serveur »";
         gDayTxt = "Pas de trade : " + whyH;
         Notify(I_WARN + "PAS DE TRADE aujourd'hui\n" + whyH + ". Corrige-les : sinon le range serait pris sur la mauvaise bougie.");
         SaveState();
         return true;
        }
     }

   // v7 : aucun ordre les jours de décision de la Fed ni les jours fériés américains / demi-séances.
   // La règle mémoire n'est ni consommée ni armée ces jours-là.
   bool fomcD  = InpSkipFomc && IsFomc(day);
   bool shortD = InpSkipShort && ShortDay(ny1);
   if(fomcD || shortD)
     {
      string whyD = fomcD ? "jour de décision de la Fed (FOMC)" : "jour férié américain ou demi-séance";
      gDayTxt = "Pas de trade : " + whyD;
      Notify(I_NONE + "PAS DE TRADE aujourd'hui\n" + whyD);
      SaveState();
      return true;
     }

   // V9 garde-fou coût : si le spread du moment + 2 glissements supposés pèse plus de InpMaxCostR du range, aucun ordre.
   // Comme les jours FOMC, ce jour-là ne change rien à la règle mémoire.
   if(InpMaxCostR > 0 && gOrH > gOrL)
     {
      double sprNow = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double costR  = (sprNow + 2.0 * InpCostSlip) / (InpStopMult * (gOrH - gOrL));   // V10 : rapporté au risque (stop élargi)
      if(costR > InpMaxCostR)
        {
         string whyC = "coût trop lourd pour ce range : spread " + Pts(sprNow) + " + 2 glissements de " + Pts(InpCostSlip) + " = " +
                       DoubleToString(100.0 * costR, 0) + " % du risque (limite " + DoubleToString(100.0 * InpMaxCostR, 0) + " %)";
         gDayTxt = "Pas de trade : " + whyC;
         Notify(I_NONE + "PAS DE TRADE aujourd'hui\n" + whyC);
         SaveState();
         return true;
        }
     }

   // v7 mémoire : le dernier trade pris était gagnant, ce signal n'est pas pris. Aucun ordre n'est posé ; l'EA observe
   // seulement (dans CheckEntries) si la cassure permise se déclenche avant la fin de validité : si oui, la règle est
   // consommée. Un jour où aucun côté n'est permis n'est pas un signal : il suit le chemin normal ci-dessous.
   if(InpUseMem && gSkipNext && gPendDir != 2)
     {
      string endObs = TimeToString(ToNY(gOrTime) + (InpLiveBars + 1) * BAR, TIME_MINUTES);
      gObserve   = true;
      gPend      = true;
      gFails     = 0;
      gGoneAt    = 0;
      gSrvL      = false;
      gSrvS      = false;
      gLots      = 0;
      gRiskMoney = 0;
      gDayTxt = "Règle mémoire : signal du jour non pris (observation jusqu'à " + endObs + " NY)";
      Notify(I_NONE + "PAS D'ORDRE aujourd'hui (règle mémoire)\nLe trade précédent était gagnant : le signal du jour n'est pas pris." +
             "\nRange 9:30 : " + Px(gOrL) + " – " + Px(gOrH) +
             "\n" + (gPendDir == 1 ? "Achat observé" : gPendDir == -1 ? "Vente observée" : "Achat ou vente observés") + " sans ordre jusqu'à " + endObs + " NY.");
      SaveState();
      return true;
     }

   // taille : risque en % du solde, arrondie au pas de volume du broker
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0)
      tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double perLot = (dist > 0 && ts > 0) ? dist * InpStopMult / ts * tv : 0;   // V10 : 1R = InpStopMult ranges
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double lots = perLot > 0 ? MathFloor(bal * gRiskPct / 100.0 / perLot / step) * step : 0;
   // marge : la position, ajout de la pyramide compris, ne demande pas plus que MARGIN_USE de la marge libre.
   // Si le risque demandé donne une position trop grosse pour le levier, la taille est réduite (le trade est gardé).
   double want  = lots;
   double units = 1.0 + (InpUsePyr ? InpPyrSize : 0.0);
   // V8 : la marge est prévue aussi pour l'entrée B (avec sa pyramide) et l'entrée C, qui prennent au plus les mêmes lots
   if(gLegsOk && InpUseB)
      units += 1.0 + (InpUsePyr ? InpPyrSize : 0.0);
   if(gLegsOk && InpUseC)
      units += 1.0;
   // V9 : et pour les entrées de continuation D (avec leur pyramide)
   if(gLegsOk && InpUseD)
      units += MathMin(InpDCount, D_MAX) * (1.0 + ((InpUsePyr && InpDPyr) ? InpPyrSize : 0.0));
   double mLot  = MarginPerLot();
   if(mLot > 0 && step > 0)
     {
      double cap = MathFloor(AccountInfoDouble(ACCOUNT_MARGIN_FREE) * MARGIN_USE / (mLot * units) / step) * step;
      if(cap < lots)
         lots = MathMax(cap, 0);
     }
   bool cut = lots < want - step / 2;   // réduite par la marge (et non par le volume maximal du symbole)
   lots = MathMin(lots, vmax);
   int vd = VolDigits(step);
   lots = NormalizeDouble(lots, vd);

   string endT = TimeToString(ToNY(gOrTime) + (InpLiveBars + 1) * BAR, TIME_MINUTES);
   if(gPendDir == 2 || lots < vmin)
     {
      string why = gPendDir == 2 ? "achat bloqué (" + whyL + "), vente bloquée (" + whyS + ")" :
                   cut ? "marge insuffisante pour ouvrir le minimum de " + DoubleToString(vmin, vd) + " lot (pyramide et entrées B, C, D comprises)" :
                   "taille trop petite pour " + RiskTxt(gRiskPct) + " (minimum " + DoubleToString(vmin, vd) + " lot)";
      gDayTxt = "Pas de trade : " + why;
      Notify(I_NONE + "PAS DE TRADE aujourd'hui\n" + why);
      SaveState();
      return true;
     }

   gLots      = lots;
   gRiskMoney = lots * perLot;
   gPend      = true;
   gFails     = 0;
   gGoneAt    = 0;
   // ordres stop posés chez le courtier : exécutés par son serveur dès que le prix touche le niveau, sans attendre l'EA
   // (moins de glissement qu'un ordre au marché envoyé après la cassure).
   gSrvL = gPendDir != -1 && PlaceStop(1);
   gSrvS = gPendDir != 1 && PlaceStop(-1);

   datetime xEnd = gOrTime + (InpLiveBars + 1) * BAR;
   if(InpUseExt && preOk)
      Box(ObjDay("pre"), pT0, pH, xEnd, pL, clrCornflowerBlue, false, STYLE_DOT);
   Box(ObjDay("or"), gOrTime, gOrH, xEnd, gOrL, C'225,227,232', true, STYLE_SOLID);
   Txt(ObjDay("ort"), gOrTime, gOrH, "9:30 · " + Pts(dist), clrGray, ANCHOR_LEFT_LOWER);
   if(gPendDir != -1)
     {
      Seg(ObjDay("pH"), gOrTime, xEnd, gOrH, clrSeaGreen, STYLE_DASH, 1);
      Txt(ObjDay("tH"), xEnd, gOrH, " Achat stop " + Px(gOrH), clrSeaGreen, ANCHOR_LEFT);
     }
   if(gPendDir != 1)
     {
      Seg(ObjDay("pL"), gOrTime, xEnd, gOrL, clrTomato, STYLE_DASH, 1);
      Txt(ObjDay("tL"), xEnd, gOrL, " Vente stop " + Px(gOrL), clrTomato, ANCHOR_LEFT);
     }
   if(gPendDir != 0)
     {
      double yb = gPendDir == 1 ? gOrL : gOrH;
      Seg(ObjDay("bk"), gOrTime, xEnd, yb, clrSilver, STYLE_DOT, 1);
      Txt(ObjDay("tb"), xEnd, yb, gPendDir == 1 ? " Vente bloquée (" + whyS + ")" : " Achat bloqué (" + whyL + ")", clrGray, ANCHOR_LEFT);
     }

   gDayTxt = (gPendDir == 1 ? "Achat stop " + Px(gOrH) : gPendDir == -1 ? "Vente stop " + Px(gOrL) : "Achat " + Px(gOrH) + " · Vente " + Px(gOrL)) + " · jusqu'à " + endT;
   string ccy = AccountInfoString(ACCOUNT_CURRENCY);
   double realPct = bal > 0 ? 100.0 * gRiskMoney / bal : 0;
   Notify(I_ORDERS + "ORDRES PLACÉS\nRange 9:30 : " + Px(gOrL) + " – " + Px(gOrH) + " (" + Pts(dist) + ") · 1R = " + Pts(dist * InpStopMult) +
          (gPendDir != -1 ? "\nAchat stop : " + Px(gOrH) + " · stop " + Px(StopA(1)) : "\nAchat bloqué (" + whyL + ")") +
          (gPendDir != 1 ? "\nVente stop : " + Px(gOrL) + " · stop " + Px(StopA(-1)) : "\nVente bloquée (" + whyS + ")") +
          "\nTaille : " + DoubleToString(lots, vd) + " lot · " + DoubleToString(gRiskMoney, 2) + " " + ccy + " risqués (" + RiskTxt(realPct) + ")" +
          (cut ? "\n" + I_WARN + "Taille réduite par la marge : " + RiskTxt(gRiskPct) + " demandés, il aurait fallu " + DoubleToString(want, vd) + " lot" : "") +
          "\nValables jusqu'à " + endT + " NY." + (gPendDir == 0 ? " Le premier déclenché annule l'autre." : " Annulé si le côté bloqué est touché d'abord.") +
          ((gPendDir != -1 && !gSrvL) || (gPendDir != 1 && !gSrvS) ? "\n" + I_WARN + "Prix déjà au niveau ou trop près pour un ordre en attente : ce côté est surveillé par l'EA (entrée au marché)" :
           "\nOrdres posés chez le courtier"));
   SaveState();
   return true;
  }

//+------------------------------------------------------------------+
//| Entrées : ordres posés chez le courtier, ou côté surveillé        |
//+------------------------------------------------------------------+
void CheckEntries()
  {
   if(!gPend || gIn)
      return;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   // côté bloqué touché avant toute entrée : plus de trade aujourd'hui (vérifié à chaque cotation, comme le test à la minute)
   if((gPendDir == 1 && bid <= gOrL) || (gPendDir == -1 && ask >= gOrH))
     {
      CancelDay("l'autre côté du range a été touché d'abord", I_NONE + "ORDRES ANNULÉS");
      return;
     }
   if(!gActive)
     {
      CancelDay("instrument désactivé dans l'interface", I_NONE + "ORDRES ANNULÉS");
      return;
     }
   // ordres posés disparus sans position (refus à l'exécution, suppression à la main) : après 10 s, plus de trade
   bool live = (gSrvL && HasPending(1)) || (gSrvS && HasPending(-1));
   bool watch = (gPendDir != -1 && !gSrvL) || (gPendDir != 1 && !gSrvS);
   if((gSrvL || gSrvS) && !live && !watch)
     {
      if(gGoneAt == 0)
         gGoneAt = TimeCurrent();
      else if(TimeCurrent() - gGoneAt > 10)
         CancelDay("l'ordre posé chez le courtier a disparu sans exécution", I_WARN + "ORDRE DISPARU");
      return;
     }
   int d = 0;
   if(gPendDir != -1 && !gSrvL && ask >= gOrH)
      d = 1;
   else if(gPendDir != 1 && !gSrvS && bid <= gOrL)
      d = -1;
   if(d == 0)
      return;
   if(gObserve)
     {
      // v7 mémoire : la cassure permise s'est déclenchée un jour d'observation. Elle n'est pas prise ; la règle est
      // consommée et le trading reprend au prochain signal.
      gObserve  = false;
      gSkipNext = false;
      gPend     = false;
      DropPendingDraw();
      gDayTxt = "Signal sauté (règle mémoire) : " + (d == 1 ? "achat" : "vente") + " non pris";
      Notify(I_NONE + "SIGNAL SAUTÉ (règle mémoire)\nLa cassure " + (d == 1 ? "à l'achat" : "à la vente") + " s'est déclenchée et n'a pas été prise." +
             "\nLe trading reprend au prochain signal.");
      SaveState();
      return;
     }
   double sl = NormalizeDouble(StopA(d), _Digits);
   bool ok = d == 1 ? trade.Buy(gLots, _Symbol, 0, sl, 0, InpComment) : trade.Sell(gLots, _Symbol, 0, sl, 0, InpComment);
   uint rc = trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED))
     {
      gPend = false;
      SaveState();
      return;
     }
   gFails++;
   PrintFormat("Entrée refusée (%d) : %s", rc, trade.ResultRetcodeDescription());
   if(gFails >= 3)
     {
      gPend = false;
      gDelDue = !DeletePendings();
      DropPendingDraw();
      gDayTxt = "Pas de trade : entrée refusée par le broker";
      Notify(I_WARN + "ENTRÉE REFUSÉE par le courtier\n" + trade.ResultRetcodeDescription());
      SaveState();
     }
  }

//+------------------------------------------------------------------+
//| Stop au prix d'entrée                                             |
//+------------------------------------------------------------------+
// Remonte le stop de toutes les positions à « lvlPx ». Si le prix est déjà revenu derrière, sortie au marché
// (comme dans le test : sortie à l'ouverture de la bougie suivante). Si le broker refuse, l'EA surveille le niveau.
void RaiseStop(double lvlPx, string why)
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double lvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double sl  = NormalizeDouble(lvlPx, _Digits);
   gVStop = sl;
   if((gDir == 1 && bid <= sl) || (gDir == -1 && ask >= sl))
     {
      ClosePos(why);
      return;
     }
   if((gDir == 1 && bid - sl > lvl) || (gDir == -1 && sl - ask > lvl))
      SetStopAll(sl);
  }

// Pyramide : ajout au marché, avec son stop, puis stop de l'ensemble au même niveau
void DoPyramid(double curR)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   int    vd   = VolDigits(step);
   double lots = NormalizeDouble(MathFloor(gLots * InpPyrSize / step + 0.000001) * step, vd);
   gPyr = true;   // une seule tentative par trade
   gBE  = true;
   // stop de l'ensemble : InpPyrGap R sous le prix de l'ajout (ask pour un achat, bid pour une vente)
   double mkt  = gDir == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double lock = NormalizeDouble(mkt - gDir * InpPyrGap * gRisk, _Digits);
   double lockR = (lock - gEntry) * gDir / gRisk;
   if(lots < vmin)
     {
      // ajout trop petit pour le broker : le trade continue comme sans pyramide
      Notify(I_WARN + "Pyramide impossible : taille trop petite pour le courtier, le trade continue sans ajout");
      gPyr = false;
      gUsePyrToday = false;
      gBE  = gVStop > 0;
      SaveState();
      return;
     }
   double tp = InpTgtR > 0 ? NormalizeDouble(gEntry + gDir * InpTgtR * gRisk, _Digits) : 0;
   bool ok = gDir == 1 ? trade.Buy(lots, _Symbol, 0, lock, tp, InpComment + " pyramide") : trade.Sell(lots, _Symbol, 0, lock, tp, InpComment + " pyramide");
   uint rc = trade.ResultRetcode();
   if(!(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED)))
     {
      // ajout refusé : le trade continue sans pyramide, avec le stop au prix d'entrée s'il était déjà acquis
      PrintFormat("Pyramide refusée (%d) : %s", rc, trade.ResultRetcodeDescription());
      Notify(I_WARN + "Pyramide refusée par le courtier (" + trade.ResultRetcodeDescription() + "), le trade continue sans ajout");
      gPyr = false;
      gUsePyrToday = false;
      gBE  = gVStop > 0;
      SaveState();
      return;
     }
   double apx = trade.ResultPrice();
   // identifiant de la position de l'ajout (compte hedging : une deuxième position)
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      long id = PositionGetInteger(POSITION_IDENTIFIER);
      if(id != gPosId)
         gPosId2 = id;
     }
   RaiseStop(lock, "Stop remonté");
   Notify(I_ADD + "PYRAMIDE : clôture à " + RTxt(curR) + "\nAjout de " + DoubleToString(lots, vd) + " lot" + (apx > 0 ? " à " + Px(apx) : "") +
          "\nStop de l'ensemble : " + Px(lock) + " (" + RTxt(lockR) + ")" +
          "\nPire cas du trade : " + RTxt(lockR - InpPyrSize * InpPyrGap));
   SaveState();
  }

//+------------------------------------------------------------------+
//| V8 : entrées B (repli VWAP) et C (heure fixe)                     |
//+------------------------------------------------------------------+
// Les jours où le trade de cassure (A) est pris, deux entrées de plus sont possibles dans le même sens. Chacune est une
// « jambe » indépendante : son numéro magique, son stop, sa taille, son suivi. Taille : jamais plus de lots que le trade
// de cassure, jamais plus que la somme qu'il risque (1R). Le R d'une jambe = son résultat net ÷ la somme risquée par le
// trade de cassure du jour. La règle mémoire ne regarde que le trade de cassure.

void LegReset(SLeg &g)
  {
   g.enPos = false; g.done = false; g.pyrFree = true; g.dir = 0; g.entry = 0; g.sl = 0; g.risk = 0; g.lots = 0;
   g.vstop = 0; g.riskMoney = 0; g.balStart = 0; g.be = false; g.pyr = false; g.fillBar = 0; g.day = 0;
   g.id = 0; g.id2 = 0; g.closeWhy = ""; g.wait = 0;
   g.arm = false; g.trig = 0; g.stp = 0; g.exp = 0;
  }

void LegSave(SLeg &g)
  {
   if(MQLInfoInteger(MQL_TESTER))
      return;
   string k = "L" + g.nom + "_";
   Sv(k + "in", g.enPos); Sv(k + "done", g.done); Sv(k + "pfree", g.pyrFree); Sv(k + "dir", g.dir);
   Sv(k + "entry", g.entry); Sv(k + "sl", g.sl); Sv(k + "risk", g.risk); Sv(k + "lots", g.lots);
   Sv(k + "vstop", g.vstop); Sv(k + "rm", g.riskMoney); Sv(k + "bal", g.balStart); Sv(k + "be", g.be);
   Sv(k + "pyr", g.pyr); Sv(k + "bar", (double)g.fillBar); Sv(k + "day", g.day);
   Sv(k + "id", (double)g.id); Sv(k + "id2", (double)g.id2);
   Sv(k + "arm", g.arm); Sv(k + "trig", g.trig); Sv(k + "stp", g.stp); Sv(k + "exp", (double)g.exp);
  }

void LegLoad(SLeg &g)
  {
   string k = "L" + g.nom + "_";
   g.enPos = Ld(k + "in", 0) != 0; g.done = Ld(k + "done", 0) != 0; g.pyrFree = Ld(k + "pfree", 1) != 0;
   g.dir = (int)Ld(k + "dir", 0); g.entry = Ld(k + "entry", 0); g.sl = Ld(k + "sl", 0); g.risk = Ld(k + "risk", 0);
   g.lots = Ld(k + "lots", 0); g.vstop = Ld(k + "vstop", 0); g.riskMoney = Ld(k + "rm", 0); g.balStart = Ld(k + "bal", 0);
   g.be = Ld(k + "be", 0) != 0; g.pyr = Ld(k + "pyr", 0) != 0; g.fillBar = (datetime)Ld(k + "bar", 0);
   g.day = (int)Ld(k + "day", 0); g.id = (long)Ld(k + "id", 0); g.id2 = (long)Ld(k + "id2", 0);
   g.arm = Ld(k + "arm", 0) != 0; g.trig = Ld(k + "trig", 0); g.stp = Ld(k + "stp", 0); g.exp = (datetime)Ld(k + "exp", 0);
  }

// La position que PositionGetTicket vient de sélectionner appartient-elle à cette jambe ?
bool LegMine(SLeg &g)
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == g.magic;
  }

bool LegHasPos(SLeg &g)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk != 0 && LegMine(g))
         return true;
     }
   return false;
  }

// Relève les identifiants des positions de la jambe (unité de départ, puis ajout de la pyramide)
void LegIds(SLeg &g)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !LegMine(g))
         continue;
      long id = PositionGetInteger(POSITION_IDENTIFIER);
      if(g.id == 0)
         g.id = id;
      else if(id != g.id)
         g.id2 = id;
     }
  }

double LegOpenProfit(SLeg &g)
  {
   double p = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !LegMine(g))
         continue;
      p += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   return p;
  }

// Pose le même stop sur toutes les positions de la jambe ; false si une pose a été refusée (l'EA surveille alors lui-même)
bool LegSetStop(SLeg &g, double sl)
  {
   bool ok = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !LegMine(g))
         continue;
      if(MathAbs(PositionGetDouble(POSITION_SL) - sl) < _Point / 2)
         continue;
      if(!trade.PositionModify(tk, sl, PositionGetDouble(POSITION_TP)))
        {
         ok = false;
         PrintFormat("Entrée %s : stop à %s refusé (%d), surveillé par l'EA", g.nom, DoubleToString(sl, _Digits), trade.ResultRetcode());
        }
     }
   return ok;
  }

void LegClose(SLeg &g, string why)   // ferme la jambe (unité de départ et ajout)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !LegMine(g))
         continue;
      g.closeWhy = why;
      if(!trade.PositionClose(tk, InpDeviation))
         PrintFormat("Entrée %s : fermeture refusée (%d) : %s", g.nom, trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }

// Remonte le stop de la jambe à « lvlPx ». Si le prix est déjà revenu derrière, sortie au marché.
void LegRaiseStop(SLeg &g, double lvlPx, string why)
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double lvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double sl  = NormalizeDouble(lvlPx, _Digits);
   g.vstop = sl;
   if((g.dir == 1 && bid <= sl) || (g.dir == -1 && ask >= sl))
     {
      LegClose(g, why);
      return;
     }
   if((g.dir == 1 && bid - sl > lvl) || (g.dir == -1 && sl - ask > lvl))
      LegSetStop(g, sl);
  }

// Ouvre la jambe au marché avec son stop. Taille plafonnée : pas plus de lots que le trade de cassure, pas plus de 1R de
// risque, et la marge nécessaire (pyramide comprise). La jambe est marquée « jouée » quoi qu'il arrive : une seule
// tentative par jour.
bool LegOpen(SLeg &g, int dir, double stop, string quoi)
  {
   g.done = true;
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double px   = dir == 1 ? ask : bid;
   double dist = (px - stop) * dir;
   // V10 : stop élargi, du même multiple que la cassure ; la taille calculée plus bas est réduite d'autant (risque plafonné à 1R)
   if(InpStopMult != 1.0 && dist > 0)
     {
      dist *= InpStopMult;
      stop  = px - dir * dist;
     }
   double lvl  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0)
      tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   int    vd   = VolDigits(step);
   if(dist <= 0 || dist <= lvl || ts <= 0 || tv <= 0 || step <= 0)
     {
      Notify(I_NONE + "PAS D'ENTRÉE " + g.nom + " (" + g.titre + ")\nStop trop proche du prix ou symbole mal décrit par le courtier");
      LegSave(g);
      return false;
     }
   double perLot = dist / ts * tv;
   double lots   = MathFloor(gV8RiskMoney / perLot / step) * step;   // au plus 1R de risque
   lots = MathMin(lots, gV8Lots);                                    // au plus les lots du trade de cassure
   double mLot  = MarginPerLot();
   double units = 1.0 + ((g.pyrOk && InpUsePyr) ? InpPyrSize : 0.0);
   if(mLot > 0)
     {
      double cap = MathFloor(AccountInfoDouble(ACCOUNT_MARGIN_FREE) * MARGIN_USE / (mLot * units) / step) * step;
      if(cap < lots)
         lots = MathMax(cap, 0);
     }
   lots = NormalizeDouble(MathMin(lots, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX)), vd);
   if(lots < vmin)
     {
      Notify(I_NONE + "PAS D'ENTRÉE " + g.nom + " (" + g.titre + ")\nTaille trop petite pour le courtier (stop de " + Pts(dist) + ") ou marge insuffisante");
      LegSave(g);
      return false;
     }
   double sl = NormalizeDouble(stop, _Digits);
   trade.SetExpertMagicNumber(g.magic);
   bool   ok   = dir == 1 ? trade.Buy(lots, _Symbol, 0, sl, 0, InpComment + " " + g.nom) : trade.Sell(lots, _Symbol, 0, sl, 0, InpComment + " " + g.nom);
   uint   rc   = trade.ResultRetcode();
   double fill = trade.ResultPrice();
   ulong  deal = trade.ResultDeal();
   string rcTx = trade.ResultRetcodeDescription();
   trade.SetExpertMagicNumber(InpMagic);
   if(!(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED)))
     {
      Notify(I_WARN + "ENTRÉE " + g.nom + " REFUSÉE par le courtier\n" + rcTx);
      LegSave(g);
      return false;
     }
   g.enPos = true; g.dir = dir; g.entry = fill > 0 ? fill : px; g.sl = sl; g.risk = MathAbs(g.entry - sl);
   if(g.risk <= 0)
      g.risk = dist;
   g.lots = lots; g.vstop = 0; g.riskMoney = gV8RiskMoney; g.balStart = AccountInfoDouble(ACCOUNT_BALANCE);
   g.be = false; g.pyr = false; g.pyrFree = true; g.closeWhy = ""; g.wait = 0; g.id = 0; g.id2 = 0;
   datetime t = TimeCurrent();
   g.fillBar = t - t % BAR;
   g.day = NYDate(ToNY(t));
   // identifiant de la position : par le deal d'entrée, sinon par la liste des positions (relu ensuite à chaque cotation)
   if(deal != 0 && HistoryDealSelect(deal))
      g.id = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   if(g.id == 0)
      LegIds(g);
   Notify((dir == 1 ? I_BUY + "ACHAT " : I_SELL + "VENTE ") + g.nom + " exécuté(e) : " + quoi +
          "\nEntrée : " + Px(g.entry) + " · stop : " + Px(sl) + " (" + Pts(g.risk) + ")" +
          "\nTaille : " + DoubleToString(lots, vd) + " lot · risque " + Money(-lots * perLot) + " (au plus celui de la cassure : " + Money(-gV8RiskMoney) + ")" +
          (InpBeR > 0 ? "\nStop au prix d'entrée dès " + Px(g.entry + dir * InpBeR * g.risk) : "") +
          ((g.pyrOk && InpUsePyr) ? "\nPyramide si une bougie clôture à " + Px(g.entry + dir * InpPyrR * g.risk) : "") +
          "\nSortie à " + InpFlat + " NY");
   // repères sur le graphique : lettre de l'entrée et stop de départ
   color lc = g.nom == "B" ? clrDodgerBlue : StringSubstr(g.nom, 0, 1) == "D" ? clrTeal : clrMediumOrchid;
   Txt(GV + "in" + g.nom + "_" + (string)g.day, t, g.entry, " " + g.nom + " " + Px(g.entry), lc, (ENUM_ANCHOR_POINT)(dir == 1 ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER));
   Seg(GV + "sl" + g.nom + "_" + (string)g.day, t, t + 12 * BAR, sl, lc, STYLE_DOT, 1);
   LegSave(g);
   return true;
  }

// Pyramide de la jambe : ajout au marché, puis stop de l'ensemble InpPyrGap R (de la jambe) sous le prix de l'ajout
void LegPyramid(SLeg &g, double curR)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   int    vd   = VolDigits(step);
   double lots = NormalizeDouble(MathFloor(g.lots * InpPyrSize / step + 0.000001) * step, vd);
   g.pyrFree = false;   // une seule tentative par trade
   double mkt  = g.dir == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double lock = NormalizeDouble(mkt - g.dir * InpPyrGap * g.risk, _Digits);
   if(lots < vmin)
     {
      Notify(I_WARN + "Entrée " + g.nom + " : pyramide impossible (taille trop petite), le trade continue sans ajout");
      LegSave(g);
      return;
     }
   trade.SetExpertMagicNumber(g.magic);
   bool   ok   = g.dir == 1 ? trade.Buy(lots, _Symbol, 0, lock, 0, InpComment + " " + g.nom + " pyramide") : trade.Sell(lots, _Symbol, 0, lock, 0, InpComment + " " + g.nom + " pyramide");
   uint   rc   = trade.ResultRetcode();
   double apx  = trade.ResultPrice();
   string rcTx = trade.ResultRetcodeDescription();
   trade.SetExpertMagicNumber(InpMagic);
   if(!(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED)))
     {
      Notify(I_WARN + "Entrée " + g.nom + " : pyramide refusée par le courtier (" + rcTx + "), le trade continue sans ajout");
      LegSave(g);
      return;
     }
   g.pyr = true;
   g.be  = true;
   LegIds(g);
   LegRaiseStop(g, lock, "Stop remonté");
   Notify(I_ADD + "PYRAMIDE sur l'entrée " + g.nom + " : clôture à " + RTxt(curR) + " (R de cette entrée)" +
          "\nAjout de " + DoubleToString(lots, vd) + " lot" + (apx > 0 ? " à " + Px(apx) : "") + "\nStop de l'ensemble : " + Px(lock));
   LegSave(g);
  }

// À la clôture de chaque bougie M5 : pyramide puis stop à l'entrée, comme pour le trade de cassure
void LegOnNewBar(SLeg &g, MqlRates &r[])
  {
   if(!g.enPos || g.risk <= 0)
      return;
   datetime ny0 = ToNY(r[0].time);
   if(g.pyrOk && InpUsePyr && g.pyrFree && !g.pyr && r[1].time >= g.fillBar && NYMin(ny0) < FlatMin(ny0) && NYDate(ny0) == g.day)
     {
      double curR = g.dir == 1 ? (r[1].close - g.entry) / g.risk : (g.entry - (r[1].close + r[1].spread * _Point)) / g.risk;
      if(curR >= InpPyrR)
         LegPyramid(g, curR);
     }
   if(InpBeR > 0 && !g.be && r[1].time > g.fillBar)
     {
      double fav = g.dir == 1 ? r[1].high : r[1].low + r[1].spread * _Point;
      if(g.dir == 1 ? fav >= g.entry + InpBeR * g.risk : fav <= g.entry - InpBeR * g.risk)
        {
         g.be = true;
         Notify(I_LOCK + "Entrée " + g.nom + " : +" + DoubleToString(InpBeR, 1) + "R atteint\nStop déplacé au prix d'entrée (" + Px(g.entry) + ")");
         LegRaiseStop(g, g.entry, "Stop à l'entrée");
         LegSave(g);
        }
     }
  }

// Ajoute le trade d'une jambe au journal de l'interface (même format que le trade de cassure)
void AppendLegTrade(SLeg &g, datetime tx, double r, double net, string why)
  {
   if(MQLInfoInteger(MQL_TESTER) || !InpUseUI)
      return;
   int h = FileOpen(UI_DIR + "trades-" + gSymFile + ".csv", FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, 0, CP_UTF8);
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   datetime ny = ToNY(tx);
   string day = TimeToString(ny, TIME_DATE);
   StringReplace(day, ".", "-");
   string w = "V10 " + g.nom + " : " + why;
   StringReplace(w, ";", ",");
   FileWrite(h, IntegerToString((long)(tx - ServerOffsetSec(tx))) + ";" + day + ";" + TimeToString(ny, TIME_MINUTES) + ";" + gSymFile + ";" +
             IntegerToString(g.dir) + ";" + DoubleToString(g.lots, 2) + ";" + DoubleToString(r, 4) + ";" + DoubleToString(net, 2) + ";" +
             DoubleToString(g.balStart, 2) + ";" + w + ";" + (g.pyr ? "1" : "0") + ";" + AccountInfoString(ACCOUNT_CURRENCY));
   FileClose(h);
  }

// La jambe n'a plus de position : résultat, statistiques, message. false = un deal de sortie manque encore, réessayer.
bool LegRecord(SLeg &g, bool force)
  {
   double net = 0, px = 0;
   long   reason = DEAL_REASON_EXPERT;
   datetime tx = TimeCurrent();
   long ids[2];
   ids[0] = g.id;
   ids[1] = (g.id2 != 0 && g.id2 != g.id) ? g.id2 : 0;
   for(int p = 0; p < 2; p++)
     {
      if(ids[p] == 0)
         continue;
      bool out = false;
      if(HistorySelectByPosition(ids[p]))
        {
         for(int i = 0; i < HistoryDealsTotal(); i++)
           {
            ulong d = HistoryDealGetTicket(i);
            net += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_COMMISSION) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_FEE);
            long e = HistoryDealGetInteger(d, DEAL_ENTRY);
            if(e == DEAL_ENTRY_OUT || e == DEAL_ENTRY_OUT_BY)
              {
               out    = true;
               reason = HistoryDealGetInteger(d, DEAL_REASON);
               px     = HistoryDealGetDouble(d, DEAL_PRICE);
               tx     = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
              }
           }
        }
      if(!out && !force)
         return false;
     }
   double r   = g.riskMoney > 0 ? net / g.riskMoney : 0;
   string why = reason == DEAL_REASON_SL ? (g.pyr ? "Stop remonté" : g.be ? "Stop à l'entrée" : "Stop") : g.closeWhy != "" ? g.closeWhy : "Fermeture manuelle";
   gN++;
   gSumR += r;
   if(r > 0.05)
      gWin++;
   gStreak = (why != "Stop à l'entrée" && r < -0.05) ? gStreak + 1 : 0;
   gWorst  = MathMax(gWorst, gStreak);
   gPeak   = MathMax(gPeak, gSumR);
   gDD     = MathMax(gDD, gPeak - gSumR);
   double pct = g.balStart > 0 ? 100.0 * net / g.balStart : 0;
   Txt(GV + "res" + g.nom + "_" + (string)g.day, tx, px > 0 ? px : g.entry, " " + g.nom + " " + RTxt(r), r > 0.05 ? clrSeaGreen : r < -0.05 ? clrTomato : clrGray, ANCHOR_LEFT);
   AppendLegTrade(g, tx, r, net, why);
   Notify((r > 0.05 ? I_WIN : r < -0.05 ? I_LOSS : I_FLAT) + "ENTRÉE " + g.nom + " CLÔTURÉE : " + RTxt(r) + " · " + PctS(pct) + " · " + Money(net) +
          "\n" + why + (g.pyr ? ", avec pyramide" : "") + (px > 0 ? " · sortie à " + Px(px) : "") +
          "\nDepuis le début : " + (string)gN + " trades · " + RTxt(gSumR));
   return true;
  }

// À chaque cotation : fermeture détectée, stop surveillé par l'EA, sortie de fin de journée
void LegOnTick(SLeg &g)
  {
   bool has = LegHasPos(g);
   if(g.enPos && has && (g.id == 0 || (g.pyr && g.id2 == 0)))
      LegIds(g);
   if(g.enPos && !has)
     {
      g.wait++;
      if(g.id == 0 && g.wait <= 50)
         return;   // la position vient d'être ouverte et n'est pas encore visible dans le terminal
      if(LegRecord(g, g.wait > 50))
        {
         g.enPos = false;
         g.wait  = 0;
         LegSave(g);
         SaveState();
        }
      return;
     }
   if(!g.enPos)
      return;
   g.wait = 0;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(g.vstop > 0 && ((g.dir == 1 && bid <= g.vstop) || (g.dir == -1 && ask >= g.vstop)))
      LegClose(g, g.pyr ? "Stop remonté" : "Stop à l'entrée");
   datetime ny = ToNY(TimeCurrent());
   if(NYMin(ny) >= FlatMin(ny) || NYDate(ny) != g.day)
      LegClose(g, "Fin de journée");
  }

// Prix moyen de la séance pondéré par le volume (VWAP), de la bougie du range (9:30) jusqu'à « fin » exclu, calculé sur
// les bougies M1. Le volume d'un CFD est un nombre de cotations : sans volume, moyenne simple des prix. 0 = indisponible.
double SessionVwap(datetime fin)
  {
   if(gOrTime == 0 || fin <= gOrTime)
      return 0;
   MqlRates m1[];
   int n = CopyRates(_Symbol, PERIOD_M1, gOrTime, fin - 1, m1);
   if(n <= 0)
      return 0;
   double pv = 0, v = 0, s = 0;
   for(int i = 0; i < n; i++)
     {
      double tp  = (m1[i].high + m1[i].low + m1[i].close) / 3.0;
      double vol = (double)m1[i].tick_volume;
      pv += tp * vol;
      v  += vol;
      s  += tp;
     }
   return v > 0 ? pv / v : s / n;
  }

string LegTxt(SLeg &g, bool use)
  {
   if(!use || !gLegsOk)
      return g.nom + " coupée";
   if(g.enPos)
      return g.nom + " en cours" + (g.riskMoney > 0 ? " " + RTxt(LegOpenProfit(g) / g.riskMoney) : "") + (g.pyr ? " (pyramide)" : g.be ? " (stop à l'entrée)" : "");
   if(gV8Day == 0 || NYDate(ToNY(TimeCurrent())) != gV8Day)
      return g.nom + " attend la cassure";
   return g.nom + (g.done ? " terminée" : " guettée");
  }

//+------------------------------------------------------------------+
//| V9 : entrées D (continuations)                                    |
//+------------------------------------------------------------------+
bool DAny()   // une entrée D est-elle en position ?
  {
   for(int k = 0; k < D_MAX; k++)
      if(gD[k].enPos)
         return true;
   return false;
  }

double DOpenProfit()
  {
   double p = 0;
   for(int k = 0; k < D_MAX; k++)
      if(gD[k].enPos)
         p += LegOpenProfit(gD[k]);
   return p;
  }

string DTxt()   // résumé des entrées D pour le panneau et l'interface
  {
   if(!InpUseD || !gLegsOk)
      return "D coupées";
   int n = (int)MathMin(InpDCount, D_MAX), enc = 0, arm = 0, fin = 0;
   double p = 0, rm = 0;
   for(int k = 0; k < n; k++)
     {
      if(gD[k].enPos)
        {
         enc++;
         p += LegOpenProfit(gD[k]);
         rm = gD[k].riskMoney;
        }
      else if(gD[k].arm)
         arm++;
      else if(gD[k].done)
         fin++;
     }
   if(enc > 0)
      return "D : " + (string)enc + " en cours" + (rm > 0 ? " " + RTxt(p / rm) : "") + (arm > 0 ? ", " + (string)arm + " guettée(s)" : "");
   if(arm > 0)
      return "D : " + (string)arm + " guettée(s)";
   if(gV8Day == 0 || NYDate(ToNY(TimeCurrent())) != gV8Day)
      return "D attendent la cassure";
   return fin >= n ? "D terminées" : "D : " + (string)fin + " sur " + (string)n + " jouées";
  }

// À la clôture d'une bougie M5 : si c'est l'une des bougies qui suivent celle du range et que la cassure A est ouverte,
// l'EA guette la cassure de son extrême (ordre stop surveillé par l'EA, comme pour un côté trop proche du prix).
void V9ArmD(MqlRates &r[])
  {
   if(!InpUseD || !gLegsOk || !gActive || gV8Day == 0 || !gIn || gV8StopHit)   // V10 : pas de continuation si l'autre bord du range a été touché
      return;
   datetime ny1 = ToNY(r[1].time);
   datetime ny0 = ToNY(r[0].time);
   if(NYDate(ny1) != gV8Day || NYDate(ny0) != gV8Day || NYMin(ny0) >= FlatMin(ny0))
      return;
   int dm = NYMin(ny1) - mOR;
   if(dm <= 0 || dm % 5 != 0)
      return;
   int k = dm / 5 - 1;   // bougie de 9:35 -> D1, 9:40 -> D2, 9:45 -> D3...
   if(k < 0 || k >= MathMin(InpDCount, D_MAX))
      return;
   if(r[1].time < gV8BreakBar || gD[k].done || gD[k].enPos || gD[k].arm || r[1].high - r[1].low <= 0)
      return;
   gD[k].arm  = true;
   gD[k].trig = gV8Dir == 1 ? r[1].high : r[1].low;
   gD[k].stp  = gV8Dir == 1 ? r[1].low : r[1].high;
   gD[k].exp  = r[0].time + InpDValid * 60;
   LegSave(gD[k]);
   Seg(GV + "trg" + gD[k].nom + "_" + (string)gV8Day, r[0].time, gD[k].exp, gD[k].trig, clrTeal, STYLE_DASH, 1);
   Print(BOT + " · " + _Symbol + " · entrée " + gD[k].nom + " guettée " + (string)InpDValid + " min : " +
         (gV8Dir == 1 ? "achat si l'ask atteint " : "vente si le bid atteint ") + Px(gD[k].trig) + ", stop " + Px(gD[k].stp));
  }

// À chaque cotation : un guet D se déclenche, expire, ou est annulé parce que le prix a touché son stop d'abord
void V9TrigD()
  {
   if(gV8Day == 0)
      return;
   datetime now = TimeCurrent();
   datetime ny  = ToNY(now);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   for(int k = 0; k < D_MAX; k++)
     {
      if(!gD[k].arm)
         continue;
      bool fin = now >= gD[k].exp || NYDate(ny) != gV8Day || NYMin(ny) >= FlatMin(ny) || !gActive;
      bool blk = gV8Dir == 1 ? bid <= gD[k].stp : ask >= gD[k].stp;
      bool trg = gV8Dir == 1 ? ask >= gD[k].trig : bid <= gD[k].trig;
      if(fin || (blk && !trg))
        {
         gD[k].arm  = false;
         gD[k].done = true;
         LegSave(gD[k]);
         continue;
        }
      if(trg)
        {
         gD[k].arm = false;
         LegOpen(gD[k], gV8Dir, gD[k].stp, "continuation, cassure de la bougie M5 à " + Px(gD[k].trig));
        }
     }
  }

// À la clôture de chaque bougie M5 : gestion des jambes ouvertes, puis recherche de l'entrée B (repli sur le VWAP)
void V8OnNewBar(MqlRates &r[])
  {
   LegOnNewBar(gB, r);
   LegOnNewBar(gC, r);
   // V9 : entrées D ouvertes, puis nouveau guet si la bougie qui vient de clôturer est l'une de celles qui suivent le range
   for(int kd = 0; kd < D_MAX; kd++)
      LegOnNewBar(gD[kd], r);
   V9ArmD(r);
   datetime ny0 = ToNY(r[0].time);
   if(!InpUseB || !gLegsOk || !gActive || gV8Day == 0 || NYDate(ny0) != gV8Day || gB.done || gB.enPos || gV8Invalid)
      return;
   if(r[1].time < gV8BreakBar)
      return;
   // une bougie M5 qui clôture de l'autre côté du range : plus de repli aujourd'hui
   if((gV8Dir == 1 && r[1].close < gV8OrL) || (gV8Dir == -1 && r[1].close > gV8OrH))
     {
      gV8Invalid = true;
      Notify(I_NONE + "ENTRÉE B abandonnée pour aujourd'hui\nUne bougie M5 a clôturé de l'autre côté du range");
      SaveState();
      return;
     }
   if(NYMin(ny0) >= MathMin(mBEnd, FlatMin(ny0)))
     {
      gB.done = true;
      LegSave(gB);
      return;
     }
   if(r[1].time <= gV8BreakBar)   // la bougie de la cassure elle-même ne compte pas
      return;
   double vw = SessionVwap(r[0].time);
   if(vw <= 0)
      return;
   double tol = InpBTol * (gV8OrH - gV8OrL);
   bool sig = gV8Dir == 1 ? (r[1].low <= vw + tol && r[1].close > vw && r[1].close > r[1].open)
                          : (r[1].high >= vw - tol && r[1].close < vw && r[1].close < r[1].open);
   if(!sig)
      return;
   double stop = gV8Dir == 1 ? MathMin(r[1].low, r[2].low) - InpBBuf : MathMax(r[1].high, r[2].high) + InpBBuf;
   Seg(GV + "vw_" + (string)gV8Day, r[1].time, r[0].time + BAR, vw, clrOrange, STYLE_SOLID, 2);   // VWAP au moment du signal
   LegOpen(gB, gV8Dir, stop, "repli sur le VWAP (" + Px(vw) + ")");
  }

// À chaque cotation : suivi des jambes, stop du range touché ou non, puis entrée C à l'heure dite
void V8OnTick()
  {
   LegOnTick(gB);
   LegOnTick(gC);
   // V9 : entrées D (sorties, stops surveillés, fin de journée), puis guets en cours
   for(int kd = 0; kd < D_MAX; kd++)
      LegOnTick(gD[kd]);
   V9TrigD();
   if(gV8Day == 0)
      return;
   datetime ny = ToNY(TimeCurrent());
   if(NYDate(ny) != gV8Day)
      return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(!gV8StopHit && ((gV8Dir == 1 && bid <= gV8OrL) || (gV8Dir == -1 && ask >= gV8OrH)))
     {
      gV8StopHit = true;
      SaveState();
     }
   if(!InpUseC || !gLegsOk || !gActive || gC.done || gC.enPos || NYMin(ny) < mCAt)
      return;
   gC.done = true;   // examinée une seule fois par jour
   bool tient = gV8Dir == 1 ? bid > gV8OrH : bid < gV8OrL;
   bool tard = NYMin(ny) > mCAt + 3 || NYMin(ny) >= FlatMin(ny);
   if(tard || !tient || gV8StopHit)
     {
      Notify(I_NONE + "PAS D'ENTRÉE C aujourd'hui\n" + (tard ? "L'heure de l'entrée est passée" : gV8StopHit ? "Le stop du range a été touché depuis la cassure" : "Le prix n'est plus au-delà du niveau de cassure"));
      LegSave(gC);
      return;
     }
   LegOpen(gC, gV8Dir, gV8Dir == 1 ? gV8OrL : gV8OrH, "la cassure tient à " + InpCAt + " NY");
  }

//+------------------------------------------------------------------+
//| Nouvelle bougie M5 : contrôles à la clôture de la bougie          |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   MqlRates r[];
   ArraySetAsSeries(r, true);
   if(CopyRates(_Symbol, PERIOD_M5, 0, 3, r) < 3)
      return;

   // 0. pyramide : la bougie qui vient de clôturer (celle de l'entrée comprise) est à +2R ou plus
   if(gIn && InpUsePyr && gUsePyrToday && !gPyr && r[1].time >= gFillBar && NYMin(ToNY(r[0].time)) < FlatMin(ToNY(r[0].time)) && NYDate(ToNY(r[0].time)) == gPosDay)
     {
      double curR = gDir == 1 ? (r[1].close - gEntry) / gRisk : (gEntry - (r[1].close + r[1].spread * _Point)) / gRisk;
      if(curR >= InpPyrR)
         DoPyramid(curR);
     }

   // 1. trade ouvert, à partir de la bougie qui suit l'entrée
   if(gIn && r[1].time > gFillBar)
     {
      if(!gTPset && PositionSelectByTicket(gPos))
        {
         double tp = NormalizeDouble(gEntry + gDir * InpTgtR * gRisk, _Digits);
         if(trade.PositionModify(gPos, PositionGetDouble(POSITION_SL), tp))
            gTPset = true;
        }
      if(InpBeR > 0 && !gBE)
        {
         double fav = gDir == 1 ? r[1].high : r[1].low + r[1].spread * _Point;   // bid haut (achat), ask bas (vente)
         if(gDir == 1 ? fav >= gEntry + InpBeR * gRisk : fav <= gEntry - InpBeR * gRisk)
           {
            gBE = true;
            Notify(I_LOCK + "+" + DoubleToString(InpBeR, 1) + "R atteint\nStop déplacé au prix d'entrée (" + Px(gEntry) + ") : ce trade ne peut plus perdre que les frais");
            RaiseStop(gEntry, "Stop à l'entrée");
            SaveState();
           }
        }
     }

   // 2. ordres en attente : fin de validité, ou côté bloqué touché d'abord
   if(gPend && !gIn && r[1].time > gOrTime)
     {
      bool late = r[0].time >= gOrTime + (InpLiveBars + 1) * BAR;
      bool opp  = gPendDir == 1 ? r[1].low <= gOrL : gPendDir == -1 ? r[1].high + r[1].spread * _Point >= gOrH : false;
      if(late || opp)
         CancelDay(opp ? "l'autre côté du range a été touché d'abord" : "pas de cassure avant " + TimeToString(ToNY(r[0].time), TIME_MINUTES) + " NY", I_NONE + "ORDRES ANNULÉS");
     }

   // V8. entrées B et C : gestion à la clôture de la bougie, puis recherche du repli sur le VWAP
   V8OnNewBar(r);

   // 3. la bougie qui vient de clôturer est celle du range
   datetime ny1 = ToNY(r[1].time);
   if(NYMin(ny1) == mOR && NYDate(ny1) != gDay && !gIn && !gPend)
      gSetupDue = true;
  }

//+------------------------------------------------------------------+
//| Interface Étrave : réglages lus, état et trades écrits            |
//+------------------------------------------------------------------+
string StringToUpperCopy(string s)
  {
   StringToUpper(s);
   return s;
  }

string InstrumentOf(string sym)   // quelle case de l'interface commande ce symbole
  {
   string s = StringToUpperCopy(sym);
   if(StringFind(s, "NAS") >= 0 || StringFind(s, "NDX") >= 0 || StringFind(s, "NQ") >= 0 || StringFind(s, "USTEC") >= 0 || StringFind(s, "US100") >= 0 || StringFind(s, "USATECH") >= 0 || StringFind(s, "TECH100") >= 0)
      return "nasdaq";
   return "autre";
  }

// Nombre de décimales du pas de volume du courtier : 1 -> 0 ; 0,1 et 0,5 -> 1 ; 0,01, 0,05 et 0,25 -> 2.
// (Correctif EA-04 de la revue du 17/11/2026 : l'ancien calcul round(-log10(pas)) donnait 0 décimale pour un pas de 0,5
// ou 0,25, et NormalizeDouble arrondissait alors 0,5 lot à 1 lot : le double du risque prévu.)
int VolDigits(double step)
  {
   int d = 0;
   while(d < 8 && MathAbs(step * MathPow(10, d) - MathRound(step * MathPow(10, d))) > 1e-6)
      d++;
   return d;
  }

string SafeName(string sym)   // lettres, chiffres et . _ - # + ; tout autre caractère devient _
  {
   string out = "";
   for(int i = 0; i < StringLen(sym); i++)
     {
      ushort c = StringGetCharacter(sym, i);
      bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-' || c == '#' || c == '+';
      out += ok ? ShortToString(c) : "_";
     }
   return out;
  }

bool OnlyChars(string v, string extra)   // chiffres, lettres et les caractères de « extra », au moins un caractère
  {
   int n = StringLen(v);
   for(int i = 0; i < n; i++)
     {
      ushort c = StringGetCharacter(v, i);
      bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || StringFind(extra, ShortToString(c)) >= 0;
      if(!ok)
         return false;
     }
   return n > 0;
  }

double NotionalPerLot()   // valeur d'un lot au prix du moment, devise du compte
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double tv  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   return (ask > 0 && tv > 0 && ts > 0) ? ask / ts * tv : 0;
  }

double BrokerMarginPerLot()   // marge que MetaTrader demande pour 1 lot ; 0 = inconnue
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double m   = 0;
   if(ask <= 0 || !OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, 1.0, ask, m) || m <= 0)
      return 0;
   return m;
  }

// Marge retenue pour 1 lot : la plus grande entre celle de MetaTrader et celle du levier saisi dans l'interface
double MarginPerLot()
  {
   double m = BrokerMarginPerLot();
   double n = NotionalPerLot();
   if(gLever > 0 && n > 0)
      m = MathMax(m, n / gLever);
   return m;
  }

double OpenLots()
  {
   double v = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      v += PositionGetDouble(POSITION_VOLUME);
     }
   return v;
  }

bool TestRules()   // les règles saisies sont-elles celles du test ?
  {
   return InpOR == "09:30" && InpPre == "09:00" && InpLiveBars == 2 && InpFlat == "15:50" && InpUseRSI && InpRSILen == 14 && InpUseExt &&
          MathAbs(InpBeR - 1.5) < 1e-9 && InpTgtR == 0 && InpUsePyr && MathAbs(InpPyrR - 2.0) < 1e-9 &&
          MathAbs(InpPyrSize - 2.0) < 1e-9 && MathAbs(InpPyrGap - 1.0) < 1e-9 &&
          InpUseMem && MathAbs(InpMemR - 1.0) < 1e-9 && MathAbs(InpStopMult - 3.0) < 1e-9 && InpSkipFomc && InpSkipShort && !InpUseDI && !InpUseSar && !InpUseTime &&   // v7
          InpUseB && MathAbs(InpBTol - 0.10) < 1e-9 && InpBEnd == "14:00" && MathAbs(InpBBuf - 1.0) < 1e-9 && !InpUseC &&   // V8 sans C
          InpUseD && InpDCount == 3 && InpDValid == 10 && InpDPyr && MathAbs(InpMaxCostR - 0.25) < 1e-9;   // V9
  }

// Lit Etrave\reglages.txt. Une clé absente ou invalide laisse la valeur de MetaTrader ; un fichier illisible à cet
// instant (l'interface est en train de l'écrire) laisse tout en l'état jusqu'à la lecture suivante.
void ReadSettings()
  {
   double risk   = InpRiskPct;
   string src    = "mt5";
   double lever  = 0;
   bool   active = true;
   bool   tgOn   = InpTelegram && InpTgToken != "" && InpTgChat != "";
   string tok    = InpTgToken, chat = InpTgChat;
   bool   ui     = InpUseUI && !MQLInfoInteger(MQL_TESTER);
   if(ui)
     {
      active = true;   // sans réglage dans le fichier : la case du Nasdaq est cochée
      string name = UI_DIR + "reglages.txt";
      if(FileIsExist(name, FILE_COMMON))
        {
         int h = FileOpen(name, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE, 0, CP_UTF8);
         if(h == INVALID_HANDLE)
           {
            if(gUiLoaded)
               return;
           }
         else
           {
            string fTok = "", fChat = "";
            long   test = 0;
            while(!FileIsEnding(h))
              {
               string line = FileReadString(h);
               int p = StringFind(line, "=");
               if(p <= 0)
                  continue;
               string k = StringSubstr(line, 0, p);
               string v = StringSubstr(line, p + 1);
               StringTrimLeft(k);
               StringTrimRight(k);
               StringTrimLeft(v);
               StringTrimRight(v);
               if(k == "risque_pct")
                 {
                  double x = StringToDouble(v);
                  if(x >= RISK_MIN - 1e-9 && x <= RISK_MAX + 1e-9)
                    {
                     risk = x;
                     src  = "interface";
                    }
                 }
               else if(k == "levier")
                 {
                  double x = StringToDouble(v);
                  if(x >= 1 && x <= LEVER_MAX)
                     lever = x;
                 }
               else if(k == gInstr && (v == "0" || v == "1"))
                  active = v == "1";
               else if(k == "telegram_jeton")
                  fTok = v;
               else if(k == "telegram_discussion")
                  fChat = v;
               else if(k == "essai_telegram")
                  test = StringToInteger(v);
               else if(k == "cloturer")
                 {
                  string part[];
                  if(StringSplit(v, ';', part) == 2)
                    {
                     long id = StringToInteger(part[0]);
                     if(id > gCloseSeen && part[1] == gSymFile)
                       {
                        gCloseSeen = id;
                        Sv("closeseen", (double)id);
                        // une demande ancienne (fichier oublié, MetaTrader relancé) n'est jamais exécutée
                        if(MathAbs((long)TimeGMT() - id) <= CMD_MAX_AGE)
                           gCloseDue = true;
                       }
                    }
                 }
              }
            FileClose(h);
            if(OnlyChars(fTok, ":_-") && OnlyChars(fChat, "-"))
              {
               tgOn = true;
               tok  = fTok;
               chat = fChat;
              }
            gTgToken = tok;
            gTgChat  = chat;
            gTgOn    = tgOn;
            // demande d'essai : au premier passage on retient seulement son numéro (pas d'essai rejoué au lancement)
            if(gTestSeen < 0)
               gTestSeen = test;
            else if(test != gTestSeen)
              {
               gTestSeen = test;
               string res = !gTgOn ? "inactif" : (gPend || gSetupDue) ? "occupe" : MathAbs((long)TimeGMT() - test) > CMD_MAX_AGE ? "expire" :
                            SendTelegram(BOT + " · " + _Symbol + "\n" + I_WIN + "Essai réussi : MetaTrader envoie bien les alertes.");
               gTgTest = IntegerToString(test) + ":" + res;
               if(res == "ok" || res == "bloque" || StringFind(res, "refus") == 0)
                  gTgLast = res;
              }
           }
        }
     }
   gTgToken = tok;
   gTgChat  = chat;
   gTgOn    = tgOn;
   gLever   = lever;
   if(gUiLoaded && MathAbs(risk - gRiskPct) > 1e-9)
      Notify(I_GEAR + "RISQUE PAR TRADE : " + RiskTxt(gRiskPct) + " → " + RiskTxt(risk) + "\nRéglé dans " + (src == "interface" ? "l'interface" : "MetaTrader") + ", à partir du prochain trade");
   if(gUiLoaded && active != gActive)
      Notify(I_GEAR + (active ? "INSTRUMENT ACTIVÉ dans l'interface" : "INSTRUMENT DÉSACTIVÉ dans l'interface\nPlus de nouveau trade ; un trade ouvert reste géré jusqu'à sa sortie"));
   gRiskPct  = risk;
   gRiskSrc  = src;
   gActive   = active;
   gUiLoaded = true;
  }

// Demande « Clôturer » de l'interface : ferme le trade au marché, ou annule les ordres du jour
void UiClose()
  {
   if(gIn || gB.enPos || gC.enPos || DAny())
     {
      Notify(I_HAND + "CLÔTURE demandée depuis l'interface");
      if(gIn)
         ClosePos("Fermeture depuis l'interface");
      if(gB.enPos)
         LegClose(gB, "Fermeture depuis l'interface");
      if(gC.enPos)
         LegClose(gC, "Fermeture depuis l'interface");
      for(int kd = 0; kd < D_MAX; kd++)
         if(gD[kd].enPos)
            LegClose(gD[kd], "Fermeture depuis l'interface");
     }
   else if(gPend)
      CancelDay("ordres annulés depuis l'interface", I_HAND + "ORDRES ANNULÉS depuis l'interface");
   // V8 : après une demande de clôture, plus d'entrée B ni C aujourd'hui
   gB.done = true;
   gC.done = true;
   LegSave(gB);
   LegSave(gC);
   for(int kd = 0; kd < D_MAX; kd++)
     {
      gD[kd].done = true;
      gD[kd].arm  = false;
      LegSave(gD[kd]);
     }
  }

// L'heure du serveur correspond-elle toujours aux réglages ? (contrôlé au lancement, puis en continu : un mauvais
// réglage d'heure d'été ne se voit que les semaines où les États-Unis et l'Europe sont décalés)
void CheckClock()
  {
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
      return;
   long real = (long)(TimeTradeServer() - TimeGMT());
   bool ok   = MathAbs(real - ServerOffsetSec(TimeTradeServer())) <= 1800;
   if(!ok && gClockOk)
      Notify(I_WARN + "HEURE DU SERVEUR : les réglages de l'EA ne correspondent plus à l'heure réelle du serveur.\nCorrige « Décalage GMT du serveur » ou « Heure d'été du serveur », sinon le range sera pris sur la mauvaise bougie.");
   gClockOk = ok;
  }

void Kv(int h, string k, string v)
  {
   StringReplace(v, "\r", " ");
   StringReplace(v, "\n", " · ");
   FileWrite(h, k + "=" + v);
  }

void Kd(int h, string k, double v, int digits) { Kv(h, k, DoubleToString(v, digits)); }

// Écrit Etrave\etat-<symbole>.txt : fichier provisoire, puis remplacement d'un seul coup
void WriteState()
  {
   string tmp = UI_DIR + "etat-" + gSymFile + ".tmp";
   int h = FileOpen(tmp, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON, 0, CP_UTF8);
   if(h == INVALID_HANDLE)
      return;
   ENUM_ACCOUNT_TRADE_MODE tm = (ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   double n  = NotionalPerLot();
   double m  = BrokerMarginPerLot();
   double pl = gIn ? OpenProfit() : 0;
   Kv(h, "version", "1");
   Kv(h, "ea", "10.00");
   Kv(h, "symbole", gSymFile);
   Kv(h, "instrument", gInstr);
   Kv(h, "actif", gActive ? "1" : "0");
   Kv(h, "terminal", TerminalInfoString(TERMINAL_PATH));
   Kv(h, "compte_type", tm == ACCOUNT_TRADE_MODE_REAL ? "reel" : tm == ACCOUNT_TRADE_MODE_CONTEST ? "concours" : "demo");
   Kv(h, "compte_serveur", AccountInfoString(ACCOUNT_SERVER));
   Kv(h, "compte_login", IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)));
   Kv(h, "devise", AccountInfoString(ACCOUNT_CURRENCY));
   Kd(h, "solde", AccountInfoDouble(ACCOUNT_BALANCE), 2);
   Kd(h, "capital", AccountInfoDouble(ACCOUNT_EQUITY), 2);
   Kd(h, "marge_libre", AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2);
   Kv(h, "levier_compte", IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE)));
   Kd(h, "levier_symbole", (n > 0 && m > 0) ? n / m : 0, 1);
   Kv(h, "connecte", TerminalInfoInteger(TERMINAL_CONNECTED) ? "1" : "0");
   Kv(h, "trading_auto", (TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED)) ? "1" : "0");
   Kv(h, "heure_ny", TimeToString(ToNY(TimeTradeServer()), TIME_DATE | TIME_MINUTES));
   Kv(h, "heure_serveur", TimeToString(TimeTradeServer(), TIME_MINUTES));
   Kv(h, "horloge_ok", gClockOk ? "1" : "0");
   Kv(h, "regles_test", TestRules() ? "1" : "0");
   Kd(h, "risque_pct", gRiskPct, 4);
   Kv(h, "risque_source", gRiskSrc);
   Kd(h, "range_bas", gOrL, _Digits);
   Kd(h, "range_haut", gOrH, _Digits);
   Kv(h, "filtres", gFiltTxt);
   Kv(h, "jour", gIn ? (gDir == 1 ? "Achat" : "Vente") + " en cours" + (gPyr ? " · pyramide faite" : gBE ? " · stop à l'entrée" : "") : gDayTxt);
   // V8 : état des entrées B et C, dans des clés à part (la ligne « jour » reste celle de la cassure, comme en v7)
   Kv(h, "v8_b", LegTxt(gB, InpUseB));
   Kv(h, "v8_c", LegTxt(gC, InpUseC));
   Kv(h, "v9_d", DTxt());
   Kd(h, "v8_resultat", (gB.enPos ? LegOpenProfit(gB) : 0) + (gC.enPos ? LegOpenProfit(gC) : 0) + DOpenProfit(), 2);
   Kv(h, "attente", gPend ? "1" : "0");
   Kv(h, "position", gIn ? "1" : "0");
   Kv(h, "pos_sens", IntegerToString(gIn ? gDir : 0));
   Kd(h, "pos_entree", gIn ? gEntry : 0, _Digits);
   Kd(h, "pos_stop", gIn ? (gVStop > 0 ? gVStop : gSL) : 0, _Digits);
   Kd(h, "pos_lots", gIn ? OpenLots() : 0, 2);
   Kd(h, "pos_resultat", pl, 2);
   Kd(h, "pos_r", (gIn && gRiskMoney > 0) ? pl / gRiskMoney : 0, 2);
   Kv(h, "pos_pyramide", (gIn && gPyr) ? "1" : "0");
   Kd(h, "risque_argent", gIn ? gRiskMoney : 0, 2);
   Kd(h, "solde_depart", gIn ? gBalStart : 0, 2);
   Kv(h, "stats_n", IntegerToString(gN));
   Kv(h, "stats_gagnants", IntegerToString(gWin));
   Kd(h, "stats_r", gSumR, 2);
   Kd(h, "stats_baisse", gDD, 2);
   Kv(h, "stats_serie", IntegerToString(gWorst));
   Kv(h, "telegram", gTgOn ? "1" : "0");
   Kv(h, "telegram_envoi", gTgLast);
   Kv(h, "telegram_essai", gTgTest);
   FileClose(h);
   FileMove(tmp, FILE_COMMON, UI_DIR + "etat-" + gSymFile + ".txt", FILE_COMMON | FILE_REWRITE);
  }

// Ajoute le trade clôturé à Etrave\trades-<symbole>.csv :
// sortie (secondes UTC) ; date NY ; heure NY ; symbole ; sens ; lots ; R ; résultat net ; solde avant ; raison ; pyramide ; devise
void AppendTrade(datetime tx, double r, double net, string why)
  {
   if(MQLInfoInteger(MQL_TESTER) || !InpUseUI)
      return;
   int h = FileOpen(UI_DIR + "trades-" + gSymFile + ".csv", FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ, 0, CP_UTF8);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("Journal des trades de l'interface : écriture impossible (erreur %d)", GetLastError());
      return;
     }
   FileSeek(h, 0, SEEK_END);
   datetime ny = ToNY(tx);
   string day = TimeToString(ny, TIME_DATE);
   StringReplace(day, ".", "-");
   StringReplace(why, ";", ",");
   FileWrite(h, IntegerToString((long)(tx - ServerOffsetSec(tx))) + ";" + day + ";" + TimeToString(ny, TIME_MINUTES) + ";" + gSymFile + ";" +
             IntegerToString(gDir) + ";" + DoubleToString(gLots, 2) + ";" + DoubleToString(r, 4) + ";" + DoubleToString(net, 2) + ";" +
             DoubleToString(gBalStart, 2) + ";" + why + ";" + (gPyr ? "1" : "0") + ";" + AccountInfoString(ACCOUNT_CURRENCY));
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Panneau                                                           |
//+------------------------------------------------------------------+
void Panel()
  {
   if(!InpPanel)
      return;
   datetime ny = ToNY(TimeCurrent());
   string live = "";
   if(gIn && gRiskMoney > 0)
      live = (gDir == 1 ? "Achat" : "Vente") + " en cours · " + RTxt(OpenProfit() / gRiskMoney) + (gPyr ? " · pyramide, stop à " + Px(gVStop) : gBE ? " · stop à l'entrée" : "");
   string s = BOT + " · Strategy V10 · " + _Symbol + " · " + RiskTxt(gRiskPct) + " par trade (" + (gRiskSrc == "interface" ? "interface" : "MetaTrader") + ")" +
              (gActive ? "" : " · DÉSACTIVÉ dans l'interface") + "\n" +
              "Heure NY : " + TimeToString(ny, TIME_DATE | TIME_MINUTES) + " (serveur " + TimeToString(TimeCurrent(), TIME_MINUTES) + ") — à vérifier\n" +
              "Range 9:30 : " + (gOrH > 0 ? Px(gOrL) + " – " + Px(gOrH) + " (" + Pts(gOrH - gOrL) + ")" : "—") + "\n" +
              "Filtres : " + ((InpUseRSI || InpUseExt) ? gFiltTxt : "désactivés") + "\n" +
              "Cassure (A) : " + (live != "" ? live : gDayTxt) + "\n" +
              "Entrées V10 : " + LegTxt(gB, InpUseB) + " · " + LegTxt(gC, InpUseC) + " · " + DTxt() + "\n" +
              "Historique : " + (gN == 0 ? "aucun trade" : (string)gN + " trades · " + DoubleToString(100.0 * gWin / gN, 0) + " % gagnants · " + RTxt(gSumR) +
              " · " + (gSumR >= 0 ? "+" : "") + DoubleToString(gSumR / gN, 2) + "R par trade · pire baisse -" + DoubleToString(gDD, 1) + "R · " + (string)gWorst + " pertes de suite");
   Comment(s);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   mOR = ParseHM(InpOR);
   mPre = ParseHM(InpPre);
   mFlat = ParseHM(InpFlat);
   mFlatShort = ParseHM(InpFlatShort);
   if(mOR < 0 || mPre < 0 || mFlat < 0 || mPre >= mOR || mFlat <= mOR || mFlatShort <= mOR || mFlatShort > mFlat)
     {
      Alert("Strategy V10 : heures invalides (format HH:MM, début de l'élan < range < sortie des jours fériés <= sortie).");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpUsePyr && (InpPyrGap <= 0 || InpPyrGap > InpPyrR || InpPyrSize <= 0))
     {
      Alert("Strategy V10 : pyramide invalide (la distance du stop doit être positive et ne pas dépasser le seuil d'ajout).");
      return INIT_PARAMETERS_INCORRECT;
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   hRSI = iRSI(_Symbol, PERIOD_M5, InpRSILen, PRICE_CLOSE);
   if(hRSI == INVALID_HANDLE)
      return INIT_FAILED;
   // v7 options
   if(InpUseDI)
     {
      hDI = iADXWilder(_Symbol, PERIOD_H4, InpDILen);
      if(hDI == INVALID_HANDLE)
         return INIT_FAILED;
     }
   if(InpUseSar)
     {
      hSAR = iSAR(_Symbol, PERIOD_M5, 0.02, 0.2);
      if(hSAR == INVALID_HANDLE)
         return INIT_FAILED;
     }
   mTimeAt = ParseHM(InpTimeAt);
   if(InpUseTime && (mTimeAt <= mOR || mTimeAt >= mFlat))
     {
      Alert("Strategy V10 : heure de la sortie au temps invalide (format HH:MM, entre le range et la sortie de fin de journée).");
      return INIT_PARAMETERS_INCORRECT;
     }
   GV = "StratV10_" + _Symbol + "_" + (string)InpMagic + "_";
   // V8 : entrées B (repli sur le VWAP) et C (heure fixe)
   gB.nom = "B"; gB.titre = "repli sur le VWAP"; gB.magic = InpMagic + 1; gB.pyrOk = true;
   gC.nom = "C"; gC.titre = "entrée de " + InpCAt; gC.magic = InpMagic + 2; gC.pyrOk = false;
   LegReset(gB);
   LegReset(gC);
   for(int kd = 0; kd < D_MAX; kd++)
     {
      gD[kd].nom = "D" + (string)(kd + 1); gD[kd].titre = "continuation n° " + (string)(kd + 1); gD[kd].magic = InpMagic + 3 + kd; gD[kd].pyrOk = InpDPyr;
      LegReset(gD[kd]);
     }
   if((InpUseD && (InpDCount < 1 || InpDCount > D_MAX || InpDValid < 1)) || InpMaxCostR < 0 || InpCostSlip < 0 || InpStopMult < 1.0 || InpStopMult > 10.0)
     {
      Alert("Strategy V10 : réglages des entrées D, du garde-fou coût ou de la largeur du stop invalides (1 à 7 bougies, validité d'au moins 1 minute, valeurs positives, largeur du stop entre 1 et 10).");
      return INIT_PARAMETERS_INCORRECT;
     }
   mBEnd = ParseHM(InpBEnd);
   mCAt  = ParseHM(InpCAt);
   if((InpUseB && (mBEnd <= mOR || mBEnd > mFlat || InpBTol < 0 || InpBBuf < 0)) || (InpUseC && (mCAt <= mOR + 5 || mCAt >= mFlat)))
     {
      Alert("Strategy V10 : réglages des entrées B ou C invalides (heures au format HH:MM, entre le range et la sortie ; tolérance et marge positives).");
      return INIT_PARAMETERS_INCORRECT;
     }
   gLegsOk = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   if(!gLegsOk && (InpUseB || InpUseC || InpUseD))
      Alert("Strategy V10 : compte en mode netting. Les entrées B, C et D demandent un compte « hedging » : elles sont coupées, seul le trade de cassure est pris.");
   gInstr   = InstrumentOf(_Symbol);
   gSymFile = SafeName(_Symbol);
   gRiskPct = InpRiskPct;
   if(MQLInfoInteger(MQL_TESTER))
      GlobalVariablesDeleteAll(GV);
   else
     {
      LoadState();
      // contrôle du décalage horaire saisi
      long real = (long)(TimeTradeServer() - TimeGMT());
      if(MathAbs(real - ServerOffsetSec(TimeTradeServer())) > 1800)
         Alert(StringFormat("Strategy V10 : le serveur est à GMT%+.1f maintenant, les réglages donnent GMT%+.1f. Corrige « Décalage GMT du serveur » ou « Heure d'été », sinon les heures de New York seront fausses.",
                            real / 3600.0, ServerOffsetSec(TimeTradeServer()) / 3600.0));
      if(!gLegsOk)
         Print("Strategy V10 : compte en mode netting. L'EA ne prend que le trade de cassure et n'ouvre rien d'autre sur ce symbole en même temps.");
     }
   gLastBar = 0;   // la première bougie est contrôlée tout de suite (EA lancé à 9:35 : le range du jour est pris)
   ReadSettings();
   if(!MQLInfoInteger(MQL_TESTER) && InpUseUI)
     {
      FolderCreate("Etrave", FILE_COMMON);
      EventSetTimer(UI_PERIOD);
      WriteState();
     }
   Panel();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(hRSI != INVALID_HANDLE)
      IndicatorRelease(hRSI);
   if(hDI != INVALID_HANDLE)
      IndicatorRelease(hDI);
   if(hSAR != INVALID_HANDLE)
      IndicatorRelease(hSAR);
   Comment("");
  }

// Toutes les 2 secondes, même sans cotation : réglages et demandes de l'interface, état pour l'interface, messages en
// attente. Aucune décision d'entrée ou de gestion n'est prise ici : elles restent dans OnTick.
void OnTimer()
  {
   if(MQLInfoInteger(MQL_TESTER) || !InpUseUI)
      return;
   ReadSettings();
   if(gCloseDue)
     {
      gCloseDue = false;
      UiClose();
     }
   CheckClock();
   FlushNotifs();
   WriteState();
   Panel();
  }

void OnTick()
  {
   // 1. exécutions et sorties (stop, objectif, fermeture)
   SyncPosition();

   // 2. contrôles de clôture de bougie (comme le test : stop à l'entrée, annulation des ordres, range de 9:30)
   datetime bt = iTime(_Symbol, PERIOD_M5, 0);
   if(bt != 0 && bt != gLastBar)
     {
      gLastBar = bt;
      OnNewBar();
     }
   if(gSetupDue && Setup())
      gSetupDue = false;

   // 3. entrée : ordres posés chez le courtier, ou côté surveillé par l'EA ; ordres à supprimer encore posés
   if(gDelDue && !gPend)
      gDelDue = !DeletePendings();
   CheckEntries();
   SyncPosition();
   if(gIn)
      CloseOpposite();

   // 4. trade ouvert : stop à l'entrée géré par l'EA si le broker l'a refusé, sortie de fin de journée
   if(gIn)
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(gVStop > 0 && ((gDir == 1 && bid <= gVStop) || (gDir == -1 && ask >= gVStop)))
         ClosePos(gPyr ? "Stop remonté" : "Stop à l'entrée");
      datetime ny = ToNY(TimeCurrent());
      // v7 option : sortie au temps. À l'heure dite, un trade encore dans sa phase initiale (ni stop à l'entrée ni
      // pyramide) et sous le seuil est fermé au marché. Examiné une seule fois par trade.
      if(InpUseTime && !gTimeDone && NYMin(ny) >= mTimeAt && NYDate(ny) == gPosDay)
        {
         gTimeDone = true;
         double curR = gRisk > 0 ? (gDir == 1 ? (bid - gEntry) / gRisk : (gEntry - ask) / gRisk) : 0;
         if(!gBE && !gPyr && curR < InpTimeR)
            ClosePos("Sortie au temps");
         SaveState();
        }
      if(gIn && (NYMin(ny) >= FlatMin(ny) || NYDate(ny) != gPosDay))
         ClosePos("Fin de journée");
     }
   // V8. entrées B et C : sorties, stops surveillés, fin de journée, entrée C à l'heure dite
   V8OnTick();

   // 5. messages WhatsApp / Telegram, une fois les ordres passés
   FlushNotifs();
   Panel();
  }
//+------------------------------------------------------------------+
