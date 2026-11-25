"""Contrôles statiques de l'EA Strategy V10 : `python -m pytest robot`.

Ce ne sont pas des tests de compilation (impossible sans MetaEditor) : ils vérifient, dans le texte du code, que les
correctifs d'exécution sont en place et que les calculs recopiés ici donnent le bon résultat.
"""
import math
import os
import re

ICI = os.path.dirname(os.path.abspath(__file__))
EA = open(os.path.join(ICI, "Strategy-V10.mq5"), encoding="utf-8-sig").read()


def vol_digits(step):
    """Copie en Python de VolDigits() de l'EA."""
    d = 0
    while d < 8 and abs(step * 10 ** d - round(step * 10 ** d)) > 1e-6:
        d += 1
    return d


def normaliser(lots, digits):
    """NormalizeDouble de MQL5 : arrondi au plus proche, la moitié s'éloignant de zéro."""
    facteur = 10 ** digits
    return math.floor(lots * facteur + 0.5) / facteur


def test_decimales_du_pas_de_volume():
    attendu = {1.0: 0, 0.1: 1, 0.5: 1, 0.01: 2, 0.05: 2, 0.25: 2, 0.001: 3, 2.0: 0}
    for pas, decimales in attendu.items():
        assert vol_digits(pas) == decimales, pas


def test_le_lot_arrondi_ne_depasse_jamais_le_lot_calcule():
    """EA-04 : avec un pas de 0,5, l'ancien calcul arrondissait 0,5 lot à 1 lot (le double du risque)."""
    for pas in (1.0, 0.5, 0.25, 0.1, 0.05, 0.01):
        for brut in (0.37, 0.5, 0.74, 1.26, 2.9, 7.77):
            lots = math.floor(brut / pas) * pas
            assert normaliser(lots, vol_digits(pas)) <= brut + 1e-9, (pas, brut)
    ancien = int(max(0, round(-math.log10(0.5))))
    assert normaliser(0.5, ancien) == 1.0          # le défaut corrigé, reproduit


def test_l_ea_utilise_volDigits_partout():
    assert "MathLog10(step)" not in EA
    assert re.search(r"^int VolDigits\(double step\)", EA, re.M)
    assert EA.count("VolDigits(step)") == 4        # cassure, pyramide de la cassure, jambes B/C/D, pyramide des jambes


def corps(fonction):
    return re.search(rf"^bool {fonction}\(\).*?\n  }}\n", EA, re.S | re.M).group(0)


def test_pas_d_ordre_si_l_heure_du_serveur_est_fausse():
    """EA-01 : un mauvais réglage d'heure d'été n'était que signalé ; l'EA tradait la mauvaise bougie."""
    setup = corps("Setup")
    garde = setup.index("if(!gClockOk)")
    assert "CheckClock();" in setup[:garde]
    assert setup.index("if(!gActive)") < garde < setup.index("gObserve   = true;")   # avant tout ordre et avant la mémoire
    assert "!MQLInfoInteger(MQL_TESTER)" in setup[:garde]                            # pas dans le testeur (heure simulée)


def test_le_rsi_est_lu_une_fois_l_indicateur_a_jour():
    """EA-04 (RSI) : au premier tick de 9:35, le RSI pouvait être celui de 9:25."""
    setup = corps("Setup")
    attente = setup.index("BarsCalculated(hRSI) < Bars(_Symbol, PERIOD_M5)")
    assert "!MQLInfoInteger(MQL_TESTER) && BarsCalculated(hRSI)" in setup          # le testeur ne calcule qu'à la lecture
    assert attente < setup.index("CopyBuffer(hRSI, 0, 1, 1, rsi)")
    assert setup[attente:attente + 120].count("return false;") == 1                  # réessayé au tick suivant


def test_les_ordres_stop_ne_survivent_pas_a_l_ea():
    """Revue du 17/11/2026 : ordres GTC préférés aux ordres DAY, et jamais supprimés quand l'EA s'arrête."""
    choix = re.search(r"ENUM_ORDER_TYPE_TIME tt = (.*?);", EA, re.S).group(1)
    assert choix.index("ORDER_TIME_SPECIFIED") < choix.index("ORDER_TIME_DAY") < choix.index("ORDER_TIME_GTC")
    fin = re.search(r"void OnDeinit\(const int reason\)(.*?)\n  }\n", EA, re.S).group(1)
    assert "DeletePendings()" in fin
    for raison in ("REASON_REMOVE", "REASON_CHARTCLOSE", "REASON_CLOSE"):
        assert raison in fin
    for raison in ("REASON_PARAMETERS", "REASON_RECOMPILE", "REASON_CHARTCHANGE"):   # l'EA repart aussitôt : on garde
        assert raison not in fin


def test_entree_au_marche_bornee_a_1_25_R():
    """EA-06 : entrée au marché « quelle que soit la distance » quand l'EA démarre en retard."""
    entrees = re.search(r"void CheckEntries\(\)(.*?)\n  }\n", EA, re.S).group(1)
    garde = entrees.index("riskN > 1.25 * riskP")
    assert entrees.index("if(gObserve)") < garde < entrees.index("trade.Buy(gLots")    # après la règle mémoire, avant l'ordre
    assert "CancelDay(" in entrees[garde:garde + 200]


def pyr_lock(direction, entree, risque, marche, ecart=1.0, taille=2.0, niveau=0.0):
    """Copie en Python de PyrLock() de l'EA (0 = pyramide abandonnée)."""
    lock = marche - direction * ecart * risque
    plancher = entree + direction * (taille * ecart - 1.0) * risque
    if (lock - plancher) * direction < 0:
        lock = plancher
    if (marche - lock) * direction <= max(niveau, 0.1 * risque):
        return 0
    return lock


def test_pyramide_pire_cas_jamais_sous_moins_1R():
    """EA-07 / EA-10 : si le prix recule entre la clôture à +2R et l'ajout, le pire cas dépassait -1R."""
    for direction in (1, -1):
        entree, risque = 20000.0, 90.0
        for r_marche in (3.0, 2.4, 2.0, 1.8, 1.5, 1.2, 1.1, 1.05, 0.9):
            marche = entree + direction * r_marche * risque
            lock = pyr_lock(direction, entree, risque, marche)
            if lock == 0:
                continue                                    # ajout abandonné : le pire cas reste celui d'avant (-1R)
            unite = (lock - entree) * direction / risque                   # première unité, stoppée au lock
            ajout = 2.0 * (lock - marche) * direction / risque             # deux unités ajoutées, stoppées au lock
            assert unite + ajout >= -1.0 - 1e-9, (direction, r_marche, unite + ajout)


def test_les_deux_pyramides_ont_le_plancher():
    assert re.search(r"^double PyrLock\(int dir, double entry, double risk, double mkt\)", EA, re.M)
    assert "PyrLock(gDir, gEntry, gRisk, mkt)" in EA                     # trade de cassure
    assert "PyrLock(g.dir, g.entry, g.risk, mkt)" in EA                  # entrées B, C, D
    assert "mkt - gDir * InpPyrGap * gRisk" not in EA and "mkt - g.dir * InpPyrGap * g.risk" not in EA


PINE = open(os.path.join(ICI, "Strategy-V10.pine"), encoding="utf-8").read()


def test_l_alerte_tradingview_donne_le_stop_elargi():
    """Relecture du 24/11/2026 : l'alerte « ORDRES ORB placés » donnait le stop de la V9 (l'autre bord du range)."""
    alerte = PINE[PINE.index('notify("ORDRES ORB placés'):]
    alerte = alerte[:alerte.index("\n\n")]
    assert '"\\nAchat stop : " + fmt(orH) + " · stop " + fmt(orH - stopMult * dist)' in alerte
    assert '"\\nVente stop : " + fmt(orL) + " · stop " + fmt(orL + stopMult * dist)' in alerte
    assert "15:45" not in alerte and "15:45 NY" not in PINE


def test_le_garde_fou_cout_est_decrit_par_rapport_au_risque():
    assert "part du range (0 = coupé)" not in PINE and "cette part du range (0 = coupé)" not in EA
    assert "gStopMult * (gOrH - gOrL)" in EA and "(close * COST_BP * 1e-4) / (stopMult * dist)" in PINE


def fonction(signature):
    """Corps d'une fonction de l'EA, de sa signature à l'accolade fermante en début de ligne."""
    debut = EA.index(signature)
    return EA[debut:EA.index("\n  }\n", debut) + 4]


def test_filet_de_securite_ferme_les_positions_oubliees():
    """Tri du 24/11/2026 : une jambe B/D perdue de vue (réponse perdue, redémarrage) n'avait ni sortie de 15:50 ni clôture."""
    filet = fonction("int CloseOrphans(string why, bool toutes)")
    assert "mg < InpMagic || mg > InpMagic + 2 + D_MAX" in filet                    # cassure, B, C, D1 à D7
    assert "trade.PositionClose(tk, InpDeviation)" in filet
    tick = fonction("void OnTick()")
    assert tick.index("V8OnTick();") < tick.index("CloseOrphans(") < tick.index("FlushNotifs();")
    assert "NYMin(nyS) >= FlatMin(nyS)" in tick and "TimeCurrent() - sweepAt >= 60" in tick
    assert "gSweepAllAt = TimeCurrent() + 10;" in fonction("void UiClose()")       # balayage 10 s après une clôture demandée
    assert "NYMin(nyS) >= FlatMin(nyS) + 1" in tick                                 # une minute après la sortie normale
    assert "gCloseWhy = why;" in filet                                              # la raison reste dans le journal


def test_pas_d_entree_doublee_apres_une_reponse_perdue():
    """X-12 : ordre stop posé malgré un délai dépassé, puis ordre au marché en plus."""
    pose = fonction("bool PlaceStop(int d)")
    assert pose.index("if(!placed && HasPending(d))") < pose.index("return placed;")
    entrees = fonction("void CheckEntries()")
    assert entrees.index("if(HasPending(d))") < entrees.index("trade.Buy(gLots")


def test_jambe_reprise_quand_la_reponse_est_perdue():
    ouverture = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi)")
    assert "LegFindOpen(g.magic, volPos)" in ouverture
    assert ouverture.index("LegFindOpen(g.magic, volPos)") < ouverture.index("g.enPos = true;")


def test_redemarrage_etat_ecrit_et_pyramide_comptee():
    """X-03 : état non écrit sur le disque, ajout repris comme trade de départ, second ajout possible."""
    assert 'Sv("pyrtoday", gUsePyrToday);' in fonction("void SaveState()")
    assert 'gUsePyrToday = Ld("pyrtoday", 1) != 0;' in fonction("void LoadState()")
    assert "gGvDirty = true;" in EA[EA.index("void   Sv("):EA.index("double Ld(")]      # cassure ET jambes (LegSave passe par Sv)
    assert "GlobalVariablesFlush();" in fonction("void FlushState()")
    for evenement in ("void OnTick()", "void OnTimer()"):
        assert "FlushState();" in fonction(evenement)
    assert "t < t0" in fonction("ulong FindPos()")                                  # la plus ancienne
    adoption = fonction("void SyncPosition()")
    assert "gPyr     = CountPos(gDir) > 1;" in adoption                             # même sens seulement
    assert "POSITION_TYPE_BUY ? 1 : -1) == dir" in fonction("int CountPos(int dir)")


def test_ajout_calcule_sur_le_volume_reellement_ouvert():
    """X-15 : après une exécution partielle, l'ajout restait de 2 fois le volume demandé."""
    assert "base = MathMin(gLots, PositionGetDouble(POSITION_VOLUME));" in fonction("void DoPyramid(double curR)")
    assert "base = MathMin(g.lots, volPos);" in fonction("void LegPyramid(SLeg &g, double curR)")


def test_un_message_a_la_fois():
    """X-08 : toute la file de messages partait d'un coup, jusqu'à 5 s par message, pendant que les sorties attendaient."""
    envoi = fonction("void FlushNotifs()")
    assert "for(int i = 0; i < n; i++)" not in envoi and "ArrayResize(gQueue, n - 1);" in envoi
    assert ", 5000, data, res, hdr)" not in EA


def test_le_script_affiche_les_ordres_meme_si_la_taille_tradingview_s_arrondit_a_zero():
    """PINE-03 : stop ×3 et 0,25 % : la taille du backtest TradingView tombait à 0, et le jour était marqué « taille nulle »."""
    assert "float qty    = qtyMin ? qtyStep : qtyRaw" in PINE
    assert PINE.index("bool  qtyMin = not na(qtyRaw) and qtyRaw <= 0") < PINE.index("bool  go  = pDir != 2 and not na(qty) and qty > 0")



def test_les_entrees_b_c_d_du_script_restent_affichees():
    """PINE-03 : la taille d'une entrée B, C ou D du backtest TradingView ne tombe plus à zéro."""
    corps = PINE[PINE.index("legQty(float dist) =>"):]
    corps = corps[:corps.index("\n\n")]
    assert "math.max(qtyStep," in corps



def test_reglages_de_pyramide_compatibles_avec_le_plancher():
    """Revue du 24/11/2026 : avec taille × écart trop grands, PyrLock abandonnait toutes les pyramides."""
    init = fonction("int OnInit()")
    assert "InpPyrSize * InpPyrGap - 1.0 > InpPyrR - 0.1" in init
    for taille, ecart, seuil in ((2.0, 1.0, 2.0),):                                 # valeurs du test : acceptées
        assert not (taille * ecart - 1.0 > seuil - 0.1 - 1e-9)


def test_un_ordre_d_un_autre_jour_n_est_pas_celui_du_jour():
    assert "(datetime)OrderGetInteger(ORDER_TIME_SETUP) < gOrTime" in fonction("bool HasPending(int d)")


def test_lots_fixes_pour_un_petit_compte():
    """Session 6 (25/11/2026) : sur 1 000 $ chez TradinGlobal (minimum 0,1 lot, 1 $ par point), le calcul au risque ne trouve
    aucune taille. InpFixedLots > 0 impose la taille de la cassure ; 0 garde le calcul au risque (comportement d'avant)."""
    assert re.search(r"input double\s+InpFixedLots\s*=\s*0\.0;", EA)
    assert "InpFixedLots > 0 ? MathFloor(InpFixedLots / step + 0.000001) * step :" in EA
    assert "MathFloor(bal * gRiskPct / 100.0 / perLot / step) * step;" in EA        # calcul au risque inchangé quand InpFixedLots = 0
    # B et D restent plafonnées par les lots et le risque de la cassure : rien n'est forcé pour elles
    assert "lots = MathMin(lots, gV8Lots);" in EA
    assert "gV8Lots = gLots; gV8RiskMoney = gRiskMoney;" in EA
    for pas in (0.1, 0.01):
        assert normaliser(math.floor(0.1 / pas + 0.000001) * pas, vol_digits(pas)) == 0.1


def test_ajout_de_pyramide_borne_au_volume_maximal():
    """Testeur MT5 du 25/11/2026 (TradinGlobal, dépôt de 1 000 000 $) : un ajout de 30,8 lots a été refusé « invalid volume »."""
    assert EA.count("MathMin(MathFloor(base * InpPyrSize / step + 0.000001) * step, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX))") == 2


def test_plancher_de_bruit_h1():
    """Règle H1 retenue le 25/11/2026 (S&P 500 et Dow TradinGlobal) : multiple du stop du jour = max(3 ; 2,5 × moyenne des ranges de
    9:30 des 20 séances d'avant ÷ range du jour), appliqué à A, B et D comme le k de la V10 (simulateur de la recherche, hors dépôt)."""
    assert re.search(r"const bool\s+InpNoiseFloor\s*=\s*false;", EA)      # verrouillé coupé le 25/11/2026 (profil le plus rentable)
    assert "#define  NOISE_C 2.5" in EA and "#define  NOISE_N 20" in EA
    assert "return avg > 0 ? MathMax(InpStopMult, NOISE_C * avg / rg) : InpStopMult;" in EA
    assert "gStopMult = DayStopMult(dist);" in EA
    # tous les calculs de stop et de taille passent par le multiple du jour
    for morceau in ("gOrH - gStopMult * rg", "dist * gStopMult / ts * tv", "dist *= gStopMult;", "(gStopMult * (gOrH - gOrL))"):
        assert morceau in EA, morceau
    assert 'Sv("smult", gStopMult)' in EA and 'gStopMult = Ld("smult", InpStopMult)' in EA


def test_plancher_de_bruit_calcul():
    """Copie en Python du calcul de l'EA, contre la référence du simulateur."""
    def multiple(ranges_avant, rg, k=3.0, c=2.5, n=20):
        r = [x for x in ranges_avant if x > 0][:n]
        return max(k, c * sum(r) / n / rg) if len(r) == n and rg > 0 else k
    assert multiple([10.0] * 20, 5.0) == 5.0            # jour calme : 2,5 × 10 / 5 = 5 ranges
    assert multiple([10.0] * 20, 10.0) == 3.0           # jour normal : on garde 3
    assert multiple([10.0] * 19, 2.0) == 3.0            # moins de 20 séances connues : 3
    assert multiple([10.0] * 19 + [0.0, 10.0], 5.0) == 5.0   # un range nul ne compte pas


def test_plancher_de_bruit_dans_le_script():
    """Le Pine suit l'EA : même règle H1, calculée sur la bougie de 9:30, avant les ordres."""
    assert 'noiseFloor = false' in PINE
    assert "stopMult := math.max(stopMultIn, 2.5 * array.avg(rng930) / rgOR)" in PINE
    assert "if array.size(rng930) > 20" in PINE
    assert PINE.index("stopMult := math.max(stopMultIn") < PINE.index("if isOR and strategy.position_size == 0 and not pend and na(cur)")


def test_regles_verrouillees_et_marches():
    """Verrou du 25/11/2026 : les règles ne sont plus des paramètres ; seuls le compte, l'heure du serveur, les FOMC, l'exécution, les
    notifications et l'affichage restent réglables. Nasdaq 100 et S&P 500 seulement, dans l'EA comme dans le script."""
    reglables = set(re.findall(r"^input\s+\S+\s+(Inp\w+)", EA, re.M))
    assert reglables == {"InpRiskPct", "InpFixedLots", "InpUseUI", "InpSrvGMT", "InpSrvDST", "InpFomc", "InpMagic", "InpDeviation",
                         "InpComment", "InpPush", "InpWhatsApp", "InpWaPhone", "InpWaKey", "InpTelegram", "InpTgToken", "InpTgChat",
                         "InpDraw", "InpPanel"}, reglables
    for nom, valeur in (("InpUseB", "true"), ("InpUseD", "true"), ("InpUseC", "false"), ("InpStopMult", "3.0"), ("InpNoiseFloor", "false")):
        assert re.search(rf"^const \S+\s+{nom}\s*=\s*{re.escape(valeur)};", EA, re.M), nom
    assert "if(!MarcheAutorise(_Symbol))" in EA and "return INIT_FAILED;" in EA
    assert 'StringFind(s, "US500")' in EA and 'StringFind(s, "US30")' not in EA
    assert "r[1].close * B_BUF_PB * 1e-4" in EA and "COST_SLIP_PB * 1e-4" in EA
    entrees_pine = set(re.findall(r"^(\w+)\s*=\s*input\.", PINE, re.M))
    assert entrees_pine <= {"riskPct", "qtyStepIn", "showLots", "lotSize", "lotStep", "lotBal", "fomcExtra", "tgChat", "showOrders",
                            "showZones", "showPre", "showBlocked", "showVwap", "showZoneB", "showGuide", "keepEmpty", "showTable",
                            "tblPosIn"} | {n for n in entrees_pine if n.startswith(("show", "tbl", "col", "txt"))}, entrees_pine
    assert "runtime.error(\"Strategy V10 : ce script ne trade que le Nasdaq 100 et le S&P 500" in PINE
    assert "useB      = true" in PINE and "useD      = true" in PINE and "stopMultIn = 3.0" in PINE


# ───────────────────────── revue cloud du 25/11/2026 ─────────────────────────
def test_le_balayage_complet_apres_cloturer_n_est_plus_efface():
    """Le balayage d'une minute tombé dans les 10 s d'après un « Clôturer » effaçait la demande de balayage complet."""
    tick = fonction("void OnTick()")
    assert "if(sweepUi)\n         gSweepAllAt = 0;" in tick
    assert tick.count("gSweepAllAt = 0;") == 1                                     # plus d'effacement sans condition
    assert "if(TimeCurrent() - sweepAt >= 60 || sweepUi)" in tick                   # le balayage complet passe à son heure


def instrument(symbole):
    """Copie en Python de InstrumentOf() de l'EA."""
    s = symbole.upper()
    if any(m in s for m in ("NAS", "NDX", "NQ", "USTEC", "US100", "USATECH", "TECH100")):
        return "nasdaq"
    if any(m in s for m in ("SPX", "SP500", "US500", "USA500", "S&P", "SPI500")):
        return "sp500"
    return "autre"


def test_le_s_p_500_a_sa_case_dans_l_interface():
    """Le S&P 500 était classé « autre » : la case marche / arrêt d'Étrave ne l'arrêtait pas."""
    corps = fonction("string InstrumentOf(string sym)")
    for motif in ("NAS", "NDX", "NQ", "USTEC", "US100", "USATECH", "TECH100", "SPX", "SP500", "US500", "USA500", "S&P", "SPI500"):
        assert f'StringFind(s, "{motif}") >= 0' in corps, motif
    assert 'return "sp500";' in corps
    assert 'return InstrumentOf(sym) != "autre";' in fonction("bool MarcheAutorise(string sym)")   # une seule liste de symboles
    for symbole, attendu in (("NDX100", "nasdaq"), ("US100.cash", "nasdaq"), ("SPX500", "sp500"), ("US500", "sp500"),
                             ("DJI30", "autre"), ("US30", "autre"), ("XAUUSD", "autre"), ("GER40", "autre")):
        assert instrument(symbole) == attendu, symbole


def test_lots_fixes_publies_pour_l_interface():
    """En lots fixes, le risque réglé dans Étrave n'est pas utilisé : l'EA le dit dans son état et dans son alerte."""
    assert 'Kd(h, "lots_fixes", InpFixedLots, 2);' in fonction("void WriteState()")
    assert "Sans effet tant que les lots fixes" in fonction("void ReadSettings()")


def test_cloture_par_symbole_et_ancienne_cle():
    """Deux demandes de clôture rapprochées pour deux marchés s'effaçaient (une seule clé « cloturer »)."""
    corps = fonction("void ReadSettings()")
    assert 'else if(k == "cloturer" || k == "cloturer_" + gSymFile)' in corps
    assert "if(id > gCloseSeen && part[1] == gSymFile)" in corps                   # une même demande n'est exécutée qu'une fois


def dates_fomc(code, debut, fin):
    bloc = code[code.index(debut):]
    return [int(d) for d in re.findall(r"\b(20\d{6})\b", bloc[:bloc.index(fin)])]


def test_dates_fomc_2027_identiques_dans_l_ea_et_le_script():
    """Calendrier révisé de la Fed du 12/11/2026 : jours de décision de 2027 et du 26/01/2028. Pas le 27/10/2027 (aucune décision)."""
    ea = dates_fomc(EA, "const int FOMC_DATES[] =", "};")
    pine = dates_fomc(PINE, "var array<int> FOMC = array.from(", ")\n")
    assert ea == pine and ea == sorted(ea) and len(set(ea)) == len(ea)
    assert [d for d in ea if d >= 20270101] == [20270127, 20270317, 20270428, 20270609, 20270728, 20270915, 20271117, 20280126]
    assert 20271027 not in ea and 20261209 in ea


def test_aucun_chat_id_dans_le_script():
    """Dépôt public : le chat ID Telegram de l'utilisateur était la valeur par défaut du script (R-22, retiré le 25/11/2026)."""
    assert 'tgChat    = input.string("", "Chat ID"' in PINE
    assert not re.search(r"-100\d{10}", PINE + EA)


# ───────────────────────── journaux d'exécution et des séances (25/11/2026) ─────────────────────────
def test_journal_d_execution_ecrit_apres_la_comptabilite():
    """Une ligne par position fermée, écrite une fois le trade compté, hors des boucles sur les deals (qui changent l'historique choisi)."""
    a = fonction("bool RecordClose(bool force)")
    assert a.index("AppendTrade(tx, r, net, why);") < a.index('ExecQueue(gPosId, "A", gDir, lvl, gVStop, why, gRiskMoney);') < a.rindex("return true;")
    assert 'ExecQueue(gPosId2, "A+", gDir, gPyrPlan, gVStop, why, gRiskMoney);' in a
    jambe = fonction("bool LegRecord(SLeg &g, bool force)")
    assert jambe.index("AppendLegTrade(g, tx, r, net, why);") < jambe.index("ExecQueue(g.id, g.nom, g.dir, g.plan, g.vstop, why, g.riskMoney);")
    assert 'ExecQueue(g.id2, g.nom + "+", g.dir, g.pplan, g.vstop, why, g.riskMoney);' in jambe
    filet = fonction("int CloseOrphans(string why, bool toutes)")
    assert filet.index("for(int k = 0; k < ArraySize(orphId); k++)") > filet.index("trade.PositionClose(tk, InpDeviation)")
    assert '" orpheline"' in filet and "!PosTracked(pid)" in filet


def test_journal_valeurs_inconnues_vides_et_divisions_gardees():
    """Une valeur inconnue reste vide, jamais calculée contre 0 ; aucune division sans garde (une erreur critique arrêterait l'EA)."""
    ligne = fonction("void ExecRow(long posId, string type, int dirHint, double plan, double vstop, string why, double riskMoney, double rangeJour, double smultJour, int dayJour)")
    assert "NumOpt((inPx - plan) * dir, plan > 0 && inPx > 0, _Digits)" in ligne
    assert "NumOpt(riskMoney > 0 ? net / riskMoney : 0, riskMoney > 0, 4)" in ligne
    assert "risk > 0 ? mfe / risk : 0, exc && risk > 0" in ligne
    assert "inVol > 0 ? inVal / inVol : 0" in ligne and "outVol > 0 ? outVal / outVol : 0" in ligne
    assert "HistoryDealGetDouble(d, DEAL_SL)" in ligne                       # stop en place lu sur le deal de sortie
    assert "cost = (spr >= 0 && rg > 0 && gStopMult > 0)" in fonction("void SeanceRow(string moment)")
    exc = fonction("bool Excursions(int dir, double entry, long inMsc, long outMsc, double &mfe, double &mae, double &spr, string &src)")
    assert "CopyTicksRange(_Symbol, tk, COPY_TICKS_INFO" in exc and "if(!any)" in exc


def test_journal_prix_vises_gardes_au_redemarrage():
    assert 'Sv(k + "plan", g.plan); Sv(k + "pplan", g.pplan);' in EA and 'g.plan = Ld(k + "plan", 0); g.pplan = Ld(k + "pplan", 0);' in EA
    assert 'Sv("pyrplan", gPyrPlan);' in EA and 'gPyrPlan = Ld("pyrplan", 0);' in EA
    assert 'g.plan = StringSubstr(g.nom, 0, 1) == "D" ? g.trig : px;' in fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi)")
    assert "gPyrPlan = mkt;" in fonction("void DoPyramid(double curR)") and "g.pplan = mkt;" in fonction("void LegPyramid(SLeg &g, double curR)")


def test_journal_des_seances_et_dossier_du_testeur():
    tick = fonction("void OnTick()")
    assert 'if(gDay != dayAvant)\n         SeanceRow("decision");' in tick
    assert 'NYMin(nyS) >= FlatMin(nyS) + 2 && gSessFin != gDay' in tick and 'SeanceRow("fin");' in tick
    assert 'return UI_DIR + (MQLInfoInteger(MQL_TESTER) ? "testeur\\\\" : "")' in EA
    init = fonction("int OnInit()")
    assert 'FileDelete(JournalName("execution"), FILE_COMMON);' in init and 'FolderCreate("Etrave\\\\testeur", FILE_COMMON);' in init


def test_journal_des_bougies_une_fois_par_jour_hors_de_la_seance():
    """Bougies M5 de la séance pour la vidéo récap : écrites avec la ligne « fin » (après la sortie), une lecture, une écriture."""
    bougies = fonction("void BougiesRow()")
    assert "CopyRates(_Symbol, PERIOD_M5, gOrTime - 30 * 60, TimeCurrent(), r)" in bougies
    assert "if(NYDate(ny) != gDay)" in bougies                       # seulement les bougies du jour de la séance
    assert bougies.count("JournalWrite(") == 1 and 'JournalWrite("bougies", BOUGIES_COLONNES, lines)' in bougies
    tick = fonction("void OnTick()")
    assert tick.index('SeanceRow("fin");') < tick.index("BougiesRow();") < tick.index("gSessFin = gDay;")
    assert EA.count("BougiesRow();") == 1
    assert 'FileDelete(JournalName("bougies"), FILE_COMMON);' in fonction("int OnInit()")
    assert '#define BOUGIES_COLONNES "version;source;jour_ny;symbole;heure_ny;ouverture;haut;bas;cloture;ticks"' in EA


def test_journal_ecrit_hors_de_la_seance():
    """Lire les ticks d'une entrée ancienne peut faire attendre l'EA jusqu'à 45 s : jamais pendant la séance, jamais avec une position."""
    flush = fonction("void JournalFlush(bool force)")
    assert "if(!(m >= FlatMin(ny) + 1 || m < mPre - 5) || gPend || EaPositions() > 0)" in flush
    assert EA.count("ExecRow(") == 2                      # la définition et l'unique appel, dans JournalFlush
    assert "JournalFlush(false);" in fonction("void OnTick()") and "JournalFlush(true);" in fonction("void OnDeinit(const int reason)")
    deinit = fonction("void OnDeinit(const int reason)")
    assert deinit.index("DeletePendings()") < deinit.index("JournalFlush(true);")   # les ordres d'abord
