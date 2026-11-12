//+------------------------------------------------------------------+
//| ORB-v4.mq5 — Cassure du range d'ouverture de New York (5 min)    |
//| Même règles et mêmes paramètres que pine/ORB-v4.pine et          |
//| backtest/nas100-10ans/orb_v4.py                                   |
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
//                Sortie au marché à 15:50 NY (clôture de la bougie de 15:45).
//  6. R affiché = résultat net du trade (commission et swap compris) ÷ somme risquée.
//
// Test de référence (NAS100 CFD Dukascopy, mai 2018 → octobre 2026, spread réel) : 1 369 trades, +0,193R par trade,
// +264R, pire baisse -27R, 9 années positives sur 9. Les données et le spread de ton broker donneront un résultat
// un peu différent : vérifie dans le testeur de stratégie (« Chaque tick basé sur des ticks réels »).
//
// Réglages à vérifier : décalage horaire du serveur (le panneau affiche l'heure de New York calculée : elle doit être
// juste), compte en mode « hedging » conseillé, et pour WhatsApp / Telegram autoriser l'adresse dans
// Outils > Options > Expert Advisors > « Autoriser WebRequest pour les URL listées ».
#property copyright   "Bot-Trading"
#property version     "4.00"
#property description "ORB New York 5 min v4 : cassure du range de 9:30 dans le sens de l'élan de l'ouverture (RSI14 + 9:00-9:30)."

#include <Trade\Trade.mqh>

enum ENUM_SRV_DST
  {
   SRV_DST_US   = 0, // Heure d'été américaine (la plupart des brokers GMT+2/+3)
   SRV_DST_EU   = 1, // Heure d'été européenne
   SRV_DST_NONE = 2  // Pas d'heure d'été
  };

//--- paramètres
input group "Risque"
input double       InpRiskPct   = 0.5;          // Risque par trade (% du solde)

input group "Heure du serveur du broker"
input int          InpSrvGMT    = 2;            // Décalage GMT du serveur en hiver (heures)
input ENUM_SRV_DST InpSrvDST    = SRV_DST_US;   // Heure d'été du serveur

input group "Règles v4 (heure de New York) — valeurs du test"
input string       InpOR        = "09:30";      // Bougie M5 du range
input string       InpPre       = "09:00";      // Début de la fenêtre de l'élan (jusqu'au range)
input int          InpLiveBars  = 2;            // Ordres valables (bougies M5 après le range)
input string       InpFlat      = "15:50";      // Sortie de fin de journée
input bool         InpUseRSI    = true;         // Filtre RSI M5 (achat > 50, vente < 50)
input int          InpRSILen    = 14;           // Longueur du RSI
input bool         InpUseExt    = true;         // Filtre d'élan (le range de 9:30 dépasse 9:00-9:30)
input double       InpBeR       = 1.5;          // Stop au prix d'entrée dès (R), 0 = désactivé
input double       InpTgtR      = 0.0;          // Objectif (R), 0 = sortie en fin de journée

input group "Exécution"
input ulong        InpMagic     = 40930;        // Numéro magique
input int          InpDeviation = 30;           // Glissement maximal (points)
input string       InpComment   = "ORB v4";     // Commentaire des ordres

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

//--- outils
CTrade trade;
int    hRSI = INVALID_HANDLE;
string GV;                      // préfixe des variables globales et des objets
int    mOR, mPre, mFlat;        // heures en minutes depuis minuit (New York)

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
//| Textes                                                            |
//+------------------------------------------------------------------+
string Px(double p)  { return DoubleToString(p, _Digits); }
string RTxt(double r) { return (r >= 0 ? "+" : "") + DoubleToString(r, 1) + "R"; }
string Pts(double d)  { return DoubleToString(d, _Digits) + " pts"; }

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

void SendTelegram(string msg)
  {
   string url  = "https://api.telegram.org/bot" + InpTgToken + "/sendMessage";
   string body = "chat_id=" + UrlEncode(InpTgChat) + "&text=" + UrlEncode(msg);
   char   data[], res[];
   string hdr;
   int len = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(data, len - 1);   // sans le zéro final
   ResetLastError();
   int code = WebRequest("POST", url, "Content-Type: application/x-www-form-urlencoded\r\n", 5000, data, res, hdr);
   if(code == -1)
      WebFail("Telegram", "https://api.telegram.org");
   else if(code != 200)
      PrintFormat("Telegram : réponse %d du serveur (vérifie le numéro, la clé ou le chat ID)", code);
  }

void Notify(string msg)
  {
   string full = "ORB v4 · " + _Symbol + " · " + msg;
   Print(full);
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return;
   if(InpPush)
     {
      string p = full;
      StringReplace(p, "\n", " · ");
      SendNotification(StringSubstr(p, 0, 255));
     }
   if(InpWhatsApp && InpWaPhone != "" && InpWaKey != "")
      SendWhatsApp(full);
   if(InpTelegram && InpTgToken != "" && InpTgChat != "")
      SendTelegram(full);
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

void ClosePos(string why)
  {
   if(!gIn || !PositionSelectByTicket(gPos))
      return;
   gCloseWhy = why;
   if(!trade.PositionClose(gPos, InpDeviation))
      PrintFormat("Fermeture refusée (%d) : %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

bool RecordClose(bool force)   // false = le deal de sortie n'est pas encore dans l'historique, réessayer
  {
   double net = 0, px = 0;
   long   reason = DEAL_REASON_EXPERT;
   datetime tx = TimeCurrent();
   bool   out = false;
   if(HistorySelectByPosition(gPosId))
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
   double r   = gRiskMoney > 0 ? net / gRiskMoney : 0;
   string why = reason == DEAL_REASON_SL ? (gBE ? "Stop à l'entrée" : "Stop") : reason == DEAL_REASON_TP ? "Objectif" : gCloseWhy != "" ? gCloseWhy : "Fermeture manuelle";
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
   Notify(id + " clôturé (" + why + ") : " + RTxt(r) + (px > 0 ? " à " + Px(px) : ""));
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
      gTPset   = InpTgtR <= 0;
      gPend    = false;
      gCloseWhy = "";
      DropPendingDraw();
      string id = gDir == 1 ? "ACHAT" : "VENTE";
      Notify(id + " exécuté à " + Px(gEntry) + "\nStop : " + Px(gSL) +
             (InpBeR > 0 ? "\nStop au prix d'entrée dès " + Px(gEntry + gDir * InpBeR * gRisk) + " (+" + DoubleToString(InpBeR, 1) + "R)" : "") +
             (InpTgtR > 0 ? "\nObjectif : " + Px(gEntry + gDir * InpTgtR * gRisk) : "\nSortie à " + InpFlat + " NY"));
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

   // taille : risque en % du solde, arrondie au pas de volume du broker
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0)
      tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double perLot = (dist > 0 && ts > 0) ? dist / ts * tv : 0;
   double lots = perLot > 0 ? MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0 / perLot / step) * step : 0;
   lots = MathMin(lots, vmax);
   int vd = (int)MathMax(0, MathRound(-MathLog10(step)));
   lots = NormalizeDouble(lots, vd);

   string endT = TimeToString(ToNY(gOrTime) + (InpLiveBars + 1) * BAR, TIME_MINUTES);
   if(gPendDir == 2 || lots < vmin)
     {
      string why = gPendDir == 2 ? "achat bloqué (" + whyL + "), vente bloquée (" + whyS + ")" : "taille trop petite pour " + DoubleToString(InpRiskPct, 1) + " % (minimum " + DoubleToString(vmin, vd) + " lot)";
      gDayTxt = "Pas de trade : " + why;
      Notify("pas de trade aujourd'hui : " + why);
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
   Notify("ORDRES ORB placés\nRange 9:30 : " + Px(gOrL) + " – " + Px(gOrH) + " (" + Pts(dist) + " = 1R)" +
          (gPendDir != -1 ? "\nAchat stop : " + Px(gOrH) + " · stop " + Px(gOrL) : "\nAchat bloqué (" + whyL + ")") +
          (gPendDir != 1 ? "\nVente stop : " + Px(gOrL) + " · stop " + Px(gOrH) : "\nVente bloquée (" + whyS + ")") +
          "\nTaille : " + DoubleToString(lots, vd) + " lot · " + DoubleToString(gRiskMoney, 2) + " " + ccy + " risqués (" + DoubleToString(InpRiskPct, 1) + " %)" +
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
      Notify("entrée refusée par le broker (" + trade.ResultRetcodeDescription() + ")");
      SaveState();
     }
  }

//+------------------------------------------------------------------+
//| Stop au prix d'entrée                                             |
//+------------------------------------------------------------------+
void MoveToBE()
  {
   if(!PositionSelectByTicket(gPos))
      return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double lvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   double be  = NormalizeDouble(gEntry, _Digits);
   double tp  = PositionGetDouble(POSITION_TP);
   // prix déjà revenu au-delà de l'entrée : comme dans le test, sortie à l'ouverture de la bougie suivante
   if((gDir == 1 && bid <= be) || (gDir == -1 && ask >= be))
     {
      ClosePos("Stop à l'entrée");
      return;
     }
   // trop près pour le broker : le stop reste géré par l'EA (OnTick)
   if((gDir == 1 && bid - be > lvl) || (gDir == -1 && be - ask > lvl))
      if(!trade.PositionModify(gPos, be, tp))
         PrintFormat("Stop à l'entrée refusé (%d), géré par l'EA", trade.ResultRetcode());
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
            Notify("+" + DoubleToString(InpBeR, 1) + "R atteint, stop déplacé au prix d'entrée (" + Px(gEntry) + ")");
            MoveToBE();
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
         Notify("ordres annulés : " + why);
         SaveState();
        }
     }

   // 3. la bougie qui vient de clôturer est celle du range
   datetime ny1 = ToNY(r[1].time);
   if(NYMin(ny1) == mOR && NYDate(ny1) != gDay && !gIn && !gPend)
      gSetupDue = true;
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
   if(gIn && PositionSelectByTicket(gPos) && gRiskMoney > 0)
     {
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      live = (gDir == 1 ? "Achat" : "Vente") + " en cours · " + RTxt(pr / gRiskMoney) + (gBE ? " · stop à l'entrée" : "");
     }
   string s = "ORB v4 · " + _Symbol + " · " + DoubleToString(InpRiskPct, 1) + " % par trade\n" +
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
   if(mOR < 0 || mPre < 0 || mFlat < 0 || mPre >= mOR || mFlat <= mOR)
     {
      Alert("ORB v4 : heures invalides (format HH:MM, début de l'élan < range < sortie).");
      return INIT_PARAMETERS_INCORRECT;
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);
   hRSI = iRSI(_Symbol, PERIOD_M5, InpRSILen, PRICE_CLOSE);
   if(hRSI == INVALID_HANDLE)
      return INIT_FAILED;
   GV = "ORBv4_" + _Symbol + "_" + (string)InpMagic + "_";
   if(MQLInfoInteger(MQL_TESTER))
      GlobalVariablesDeleteAll(GV);
   else
     {
      LoadState();
      // contrôle du décalage horaire saisi
      long real = (long)(TimeTradeServer() - TimeGMT());
      if(MathAbs(real - ServerOffsetSec(TimeTradeServer())) > 1800)
         Alert(StringFormat("ORB v4 : le serveur est à GMT%+.1f maintenant, les réglages donnent GMT%+.1f. Corrige « Décalage GMT du serveur » ou « Heure d'été », sinon les heures de New York seront fausses.",
                            real / 3600.0, ServerOffsetSec(TimeTradeServer()) / 3600.0));
      if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
         Print("ORB v4 : compte en mode netting. L'EA fonctionne, mais n'ouvre rien d'autre sur ce symbole en même temps.");
     }
   gLastBar = 0;   // la première bougie est contrôlée tout de suite (EA lancé à 9:35 : le range du jour est pris)
   Panel();
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(hRSI != INVALID_HANDLE)
      IndicatorRelease(hRSI);
   Comment("");
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
      if(gBE && ((gDir == 1 && bid <= gEntry) || (gDir == -1 && ask >= gEntry)))
         ClosePos("Stop à l'entrée");
      datetime ny = ToNY(TimeCurrent());
      if(gIn && (NYMin(ny) >= mFlat || NYDate(ny) != gPosDay))
         ClosePos("Fin de journée");
     }
   Panel();
  }
//+------------------------------------------------------------------+
