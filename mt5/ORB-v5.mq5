//+------------------------------------------------------------------+
//| ORB-v5.mq5 — Cassure du range d'ouverture de New York (5 min)    |
//| avec pyramide. Mêmes règles et mêmes paramètres que              |
//| pine/ORB-v5.pine (différences : voir le README)                   |
//+------------------------------------------------------------------+
//
// Règles (heure de New York, bougies M5 quel que soit l'horizon du graphique) :
//  1. Range    : high et low de la bougie M5 de 9:30.
//  2. Filtres  : achat permis si le RSI14 M5 de 9:30 > 50 ET si le high de 9:30 dépasse le plus haut de 9:00-9:30 ;
//                vente permise si le RSI < 50 ET si le low de 9:30 passe sous le plus bas de 9:00-9:30.
//  3. Entrée   : achat quand l'ask atteint le high du range, vente quand le bid atteint le low (ordres gérés par l'EA),
//                pendant les bougies de 9:35 et 9:40. Un seul trade par jour : le premier déclenché annule l'autre.
//                Si un seul côté est permis et qu'une bougie close touche l'autre côté d'abord, plus de trade ce jour-là.
//  4. Stop     : de l'autre côté du range, posé chez le broker dès l'entrée. 1R = somme perdue au stop (lots × range).
//  5. Gestion  : à la clôture d'une bougie (après celle de l'entrée) qui a atteint +1,5R, stop au prix d'entrée.
//                Sortie au marché à 15:50 NY (clôture de la bougie de 15:45) ; à 12:45 les jours fériés américains et
//                les demi-séances, où le marché ferme vers 13:00.
//  6. PYRAMIDE : quand une bougie M5 clôture à +2R ou plus, l'EA ajoute DEUX unités au marché et met le stop de
//                l'ensemble à 1R sous le prix de l'ajout (donc au moins à +1R pour la première unité). Après l'ajout,
//                le pire cas reste -1R, comme au départ : l'ajout perd 2R, la première unité gagne au moins 1R.
//                Un seul ajout par trade.
//  7. R affiché = résultat net de tout le trade (ajout, commission et swap compris) ÷ somme risquée au départ.
//
// Test de référence (NAS100 CFD Dukascopy, rejoué minute par minute, M1 bid et ask), 2018-01 → 2026-11, 1 391 trades :
//   2018-05 → 2022-08 (période de choix) : +0,52R par trade, +371R ; 2022-09 → 2026-11 (vérification) : +0,37R, +233R
//   Tout : +0,46R par trade, +643R, pire baisse -23R, 15 pertes de suite au pire (avec un ajout d'une seule unité :
//   +471R, pire baisse -22R). Avant 2018 l'ORB perdait (-55R sur 2015-2017) et l'ancien test 2015-2026 a connu une
//   baisse de 76R. Elle ne gagne sur aucun autre symbole testé (Dow Jones, or, EUR/USD,
//   bitcoin) : ne la trade que sur le Nasdaq. Les données et le spread de ton broker donneront un résultat un peu
//   différent : vérifie dans le testeur de stratégie (« Chaque tick basé sur des ticks réels »).
//
// INTERFACE ÉTRAVE (interface/etrave.py, lancée par Etrave.bat) : l'EA lit toutes les 2 secondes le fichier
// Etrave\reglages.txt du dossier commun de MetaTrader (risque par trade, levier, case du Nasdaq, Telegram, demande de
// clôture) et y écrit son état (Etrave\etat-<symbole>.txt) et ses trades (Etrave\trades-<symbole>.csv). Une clé absente
// du fichier laisse la valeur saisie ici. Dans le testeur de stratégie, seuls les réglages saisis ici comptent.
//
// Réglages à vérifier : décalage horaire du serveur (le panneau affiche l'heure de New York calculée : elle doit être
// juste), compte en mode « hedging » conseillé, et pour WhatsApp / Telegram autoriser l'adresse dans
// Outils > Options > Expert Advisors > « Autoriser WebRequest pour les URL listées ».
#property copyright   "Bot-Trading"
#property version     "5.11"
#property description "ORB New York 5 min v5 : cassure du range de 9:30 dans le sens de l'élan de l'ouverture, avec une pyramide à +2R."

#include <Trade\Trade.mqh>

enum ENUM_SRV_DST
  {
   SRV_DST_US   = 0, // Heure d'été américaine (la plupart des brokers GMT+2/+3)
   SRV_DST_EU   = 1, // Heure d'été européenne
   SRV_DST_NONE = 2  // Pas d'heure d'été
  };

//--- paramètres
input group "Risque"
input double       InpRiskPct   = 0.5;          // Risque par trade (% du solde), si l'interface n'en donne pas

input group "Interface Étrave"
input bool         InpUseUI     = true;         // Lire le risque, les cases et Telegram dans l'interface Étrave

input group "Heure du serveur du broker"
input int          InpSrvGMT    = 2;            // Décalage GMT du serveur en hiver (heures)
input ENUM_SRV_DST InpSrvDST    = SRV_DST_US;   // Heure d'été du serveur

input group "Règles v5 (heure de New York) — valeurs du test"
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

input group "Exécution"
input ulong        InpMagic     = 50930;        // Numéro magique
input int          InpDeviation = 30;           // Glissement maximal (points)
input string       InpComment   = "ORB v5";     // Commentaire des ordres

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
          "\nDepuis le début : " + (string)gN + " trades · " + RTxt(gSumR));
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
      gSL      = gDir == 1 ? gOrL : gOrH;
      gRisk    = MathAbs(gEntry - gSL);
      if(gRisk <= 0)
         gRisk = gOrH - gOrL;
      datetime t = (datetime)PositionGetInteger(POSITION_TIME);
      gFillBar = t - t % BAR;
      gPosDay  = NYDate(ToNY(t));
      gBE      = false;
      gPyr     = false;
      gUsePyrToday = true;
      gPosId2  = 0;
      gVStop   = 0;
      gTPset   = InpTgtR <= 0;
      gPend    = false;
      gCloseWhy = "";
      gBalStart = AccountInfoDouble(ACCOUNT_BALANCE);
      DropPendingDraw();
      string id = gDir == 1 ? I_BUY + "ACHAT exécuté" : I_SELL + "VENTE exécutée";
      Notify(id + " à " + Px(gEntry) + "\nStop : " + Px(gSL) + " (" + Money(-gRiskMoney) + ")" +
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
   bool rsiOk = CopyBuffer(hRSI, 0, 1, 1, rsi) == 1;
   if(InpUseRSI && !rsiOk)
      return false;

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
   bool   okL  = rsiL && extL;
   bool   okS  = rsiS && extS;
   string whyL = !rsiL ? "RSI" : !extL ? (preOk ? "élan" : "pas de bougies 9:00-9:30") : "";
   string whyS = !rsiS ? "RSI" : !extS ? (preOk ? "élan" : "pas de bougies 9:00-9:30") : "";
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

   // taille : risque en % du solde, arrondie au pas de volume du broker
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0)
      tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double perLot = (dist > 0 && ts > 0) ? dist / ts * tv : 0;
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double lots = perLot > 0 ? MathFloor(bal * gRiskPct / 100.0 / perLot / step) * step : 0;
   // marge : la position, ajout de la pyramide compris, ne demande pas plus que MARGIN_USE de la marge libre.
   // Si le risque demandé donne une position trop grosse pour le levier, la taille est réduite (le trade est gardé).
   double want  = lots;
   double units = 1.0 + (InpUsePyr ? InpPyrSize : 0.0);
   double mLot  = MarginPerLot();
   if(mLot > 0 && step > 0)
     {
      double cap = MathFloor(AccountInfoDouble(ACCOUNT_MARGIN_FREE) * MARGIN_USE / (mLot * units) / step) * step;
      if(cap < lots)
         lots = MathMax(cap, 0);
     }
   bool cut = lots < want - step / 2;   // réduite par la marge (et non par le volume maximal du symbole)
   lots = MathMin(lots, vmax);
   int vd = (int)MathMax(0, MathRound(-MathLog10(step)));
   lots = NormalizeDouble(lots, vd);

   string endT = TimeToString(ToNY(gOrTime) + (InpLiveBars + 1) * BAR, TIME_MINUTES);
   if(gPendDir == 2 || lots < vmin)
     {
      string why = gPendDir == 2 ? "achat bloqué (" + whyL + "), vente bloquée (" + whyS + ")" :
                   cut ? "marge insuffisante pour ouvrir le minimum de " + DoubleToString(vmin, vd) + " lot (pyramide comprise)" :
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
   Notify(I_ORDERS + "ORDRES PLACÉS\nRange 9:30 : " + Px(gOrL) + " – " + Px(gOrH) + " (" + Pts(dist) + " = 1R)" +
          (gPendDir != -1 ? "\nAchat stop : " + Px(gOrH) + " · stop " + Px(gOrL) : "\nAchat bloqué (" + whyL + ")") +
          (gPendDir != 1 ? "\nVente stop : " + Px(gOrL) + " · stop " + Px(gOrH) : "\nVente bloquée (" + whyS + ")") +
          "\nTaille : " + DoubleToString(lots, vd) + " lot · " + DoubleToString(gRiskMoney, 2) + " " + ccy + " risqués (" + RiskTxt(realPct) + ")" +
          (cut ? "\n" + I_WARN + "Taille réduite par la marge : " + RiskTxt(gRiskPct) + " demandés, il aurait fallu " + DoubleToString(want, vd) + " lot" : "") +
          "\nValables jusqu'à " + endT + " NY." + (gPendDir == 0 ? " Le premier déclenché annule l'autre." : " Annulé si le côté bloqué est touché d'abord."));
   SaveState();
   return true;
  }

//+------------------------------------------------------------------+
//| Entrée quand le prix atteint le niveau (comme un ordre stop)      |
//+------------------------------------------------------------------+
void CheckEntries()
  {
   if(!gPend || gIn)
      return;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   int d = 0;
   if(gPendDir != -1 && ask >= gOrH)
      d = 1;
   else if(gPendDir != 1 && bid <= gOrL)
      d = -1;
   if(d == 0)
      return;
   double sl = NormalizeDouble(d == 1 ? gOrL : gOrH, _Digits);
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
   int    vd   = (int)MathMax(0, MathRound(-MathLog10(step)));
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
        {
         gPend = false;
         DropDayDraw();
         string why = opp ? "l'autre côté du range a été touché d'abord" : "pas de cassure avant " + TimeToString(ToNY(r[0].time), TIME_MINUTES) + " NY";
         gDayTxt = "Pas de trade : " + why;
         Notify(I_NONE + "ORDRES ANNULÉS\n" + why);
         SaveState();
        }
     }

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
          MathAbs(InpPyrSize - 2.0) < 1e-9 && MathAbs(InpPyrGap - 1.0) < 1e-9;
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
   if(gIn)
     {
      Notify(I_HAND + "CLÔTURE demandée depuis l'interface");
      ClosePos("Fermeture depuis l'interface");
     }
   else if(gPend)
     {
      gPend = false;
      DropDayDraw();
      gDayTxt = "Pas de trade : ordres annulés depuis l'interface";
      Notify(I_HAND + "ORDRES ANNULÉS depuis l'interface\nPas de trade aujourd'hui");
      SaveState();
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
   Kv(h, "ea", "5.11");
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
   string s = BOT + " · ORB v5 · " + _Symbol + " · " + RiskTxt(gRiskPct) + " par trade (" + (gRiskSrc == "interface" ? "interface" : "MetaTrader") + ")" +
              (gActive ? "" : " · DÉSACTIVÉ dans l'interface") + "\n" +
              "Heure NY : " + TimeToString(ny, TIME_DATE | TIME_MINUTES) + " (serveur " + TimeToString(TimeCurrent(), TIME_MINUTES) + ") — à vérifier\n" +
              "Range 9:30 : " + (gOrH > 0 ? Px(gOrL) + " – " + Px(gOrH) + " (" + Pts(gOrH - gOrL) + ")" : "—") + "\n" +
              "Filtres : " + ((InpUseRSI || InpUseExt) ? gFiltTxt : "désactivés") + "\n" +
              "Aujourd'hui : " + (live != "" ? live : gDayTxt) + "\n" +
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
      Alert("ORB v5 : heures invalides (format HH:MM, début de l'élan < range < sortie des jours fériés <= sortie).");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpUsePyr && (InpPyrGap <= 0 || InpPyrGap > InpPyrR || InpPyrSize <= 0))
     {
      Alert("ORB v5 : pyramide invalide (la distance du stop doit être positive et ne pas dépasser le seuil d'ajout).");
      return INIT_PARAMETERS_INCORRECT;
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   hRSI = iRSI(_Symbol, PERIOD_M5, InpRSILen, PRICE_CLOSE);
   if(hRSI == INVALID_HANDLE)
      return INIT_FAILED;
   GV = "ORBv5_" + _Symbol + "_" + (string)InpMagic + "_";
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
         Alert(StringFormat("ORB v5 : le serveur est à GMT%+.1f maintenant, les réglages donnent GMT%+.1f. Corrige « Décalage GMT du serveur » ou « Heure d'été », sinon les heures de New York seront fausses.",
                            real / 3600.0, ServerOffsetSec(TimeTradeServer()) / 3600.0));
      if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
         Print("ORB v5 : compte en mode netting. L'EA fonctionne, mais n'ouvre rien d'autre sur ce symbole en même temps.");
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

   // 3. entrée quand le prix atteint le niveau
   CheckEntries();
   SyncPosition();

   // 4. trade ouvert : stop à l'entrée géré par l'EA si le broker l'a refusé, sortie de fin de journée
   if(gIn)
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(gVStop > 0 && ((gDir == 1 && bid <= gVStop) || (gDir == -1 && ask >= gVStop)))
         ClosePos(gPyr ? "Stop remonté" : "Stop à l'entrée");
      datetime ny = ToNY(TimeCurrent());
      if(gIn && (NYMin(ny) >= FlatMin(ny) || NYDate(ny) != gPosDay))
         ClosePos("Fin de journée");
     }
   // 5. messages WhatsApp / Telegram, une fois les ordres passés
   FlushNotifs();
   Panel();
  }
//+------------------------------------------------------------------+
