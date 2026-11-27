"""Contrôles statiques de l'EA Strategy V11 : `python -m pytest robot`.

Ce ne sont pas des tests de compilation (impossible sans MetaEditor) : ils vérifient, dans le texte du code, que les
correctifs d'exécution sont en place et que les calculs recopiés ici donnent le bon résultat.
"""
import math
import os
import re
import urllib.parse

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
EA = open(os.path.join(ICI, "Strategy-V11.mq5"), encoding="utf-8-sig").read()


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


PINE = open(os.path.join(ICI, "Strategy-V11.pine"), encoding="utf-8").read()


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
    ouverture = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
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



def test_commentaire_des_ordres_sans_type_d_entree():
    """X-14 : le commentaire des ordres (visible dans l'onglet Historique, photographié pour la vidéo) ne dit ni B, ni D, ni
    « pyramide » : le type d'entrée reste secret."""
    assert 'InpComment + " "' not in EA and 'InpComment + " pyramide"' not in EA
    assert "CaptureJour" not in EA and "InpCapture" not in EA


def test_stop_des_continuations_depuis_le_declenchement():
    """X-13 : le stop d'un D se compte depuis son niveau de déclenchement (Pine, simulateur), plus depuis le prix obtenu."""
    corps = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert "double base = ref > 0 ? ref : px;" in corps and "stop  = base - dir * dist;" in corps and "dist = (px - stop) * dir;" in corps
    assert "Px(gD[k].trig), gD[k].trig);" in EA


def test_le_script_compte_la_bougie_de_cassure_pour_le_bord_oppose():
    """PINE-05 : comme l'EA, le bord opposé touché dès la bougie de la cassure empêche d'armer les D."""
    assert "if not v8.stopHit and bar_index >= v8.breakBar and (v8.dir == 1 ? low <= orL : high >= orH)" in PINE


def test_chaque_sortie_du_script_ferme_sa_propre_position():
    """PINE-04 : sans close_entries_rule = "ANY", TradingView ferme la plus ancienne position (FIFO) : le stop d'une continuation
    fermait la cassure A, et le script suivait le mauvais trade (résultat, règle mémoire, stop à l'entrée)."""
    entete = PINE[PINE.index("strategy(\"Strategy V11"):]
    entete = entete[:entete.index(")\n")]
    assert 'close_entries_rule = "ANY"' in entete
    # le script retrouve chaque sortie par le nom de son entrée : c'est ce que « ANY » rend juste
    assert "legIdx(strategy.closedtrades.entry_id(i)) == leg" in PINE


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
    assert reglables == {"InpRiskPct", "InpFixedLots", "InpUseUI", "InpSrvAuto", "InpSrvGMT", "InpSrvDST", "InpFomc", "InpMagic", "InpDeviation",
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
    assert "runtime.error(\"Strategy V11 : ce script ne trade que le Nasdaq 100 et le S&P 500" in PINE
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
    assert 'g.plan = StringSubstr(g.nom, 0, 1) == "D" ? g.trig : px;' in fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
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


# ───────────────────────── audit du 25/11/2026 (X-16 à X-20) ─────────────────────────
def test_identifiant_de_l_ajout_de_A_retrouve():
    """X-16 : l'ajout n'était cherché qu'au retour de l'ordre ; resté inconnu, il manquait au R (mémoire armée à tort)."""
    pyr = fonction("void DoPyramid(double curR)")
    assert "gPosId2 = HistoryDealGetInteger(adeal, DEAL_POSITION_ID);" in pyr and "FindAddId();" in pyr
    cherche = fonction("void FindAddId()")
    assert "if(!gIn || !gPyr || (gPosId2 != 0 && gPosId2 != gPosId))" in cherche
    assert "id != gPosId && (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1) == gDir" in cherche
    tick = fonction("void OnTick()")
    assert tick.index("CloseOpposite();") < tick.index("FindAddId();") < tick.index("// 4. trade ouvert")


def test_pas_de_deuxieme_entree_A_apres_une_reponse_perdue():
    """X-17 : après une réponse sans verdict, l'EA attend 3 s avant de renvoyer un ordre au marché ; un refus net est réessayé."""
    corps_entrees = EA[EA.index("// Correctif X-17"):EA.index("gFails++;", EA.index("// Correctif X-17"))]
    assert "if(gAmbigMs != 0 && GetTickCount() - gAmbigMs < 3000)\n      return;" in corps_entrees
    assert corps_entrees.index("GetTickCount() - gAmbigMs < 3000") < corps_entrees.index("trade.Buy(gLots")
    assert "if(rc == 0 || rc == TRADE_RETCODE_TIMEOUT || rc == TRADE_RETCODE_ERROR)" in corps_entrees
    assert "TRADE_RETCODE_REQUOTE" not in corps_entrees


def test_jambe_deja_ouverte_reprise_sans_nouvel_ordre():
    """X-18 : après un plantage juste après une entrée B ou D, le même signal relu n'envoie pas une deuxième position."""
    leg = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert leg.index("double pxOld  = LegFindOpen(g.magic, volOld);") < leg.index("trade.Buy(lots")
    assert "if(pxOld > 0)" in leg and "sl = slOld;" in leg and leg.index("if(pxOld > 0)") < leg.index("   else\n")
    assert "double LegOpenStop(ulong magic)" in EA


def test_arrondi_des_jambes_comme_la_cassure():
    """X-19 : sans la marge +0,000001, une jambe au risque égal à celui de A (lots fixes) pouvait tomber à 0 lot."""
    leg = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert "lots = MathFloor(gV8RiskMoney / perLot / step + 0.000001) * step;" in leg
    perlot = 40.12 / 0.01 * 0.01                                      # stop de 40,12 points, tick de 0,01 à 0,01 $
    risque, pas = 0.1 * perlot, 0.1                                    # 1R de A : 0,1 lot fixe au même stop
    assert math.floor(risque / perlot / pas) * pas == 0                # l'ancien calcul : 0,999… pas, donc 0 lot
    assert abs(math.floor(risque / perlot / pas + 0.000001) * pas - 0.1) < 1e-12


def test_journaux_verrouilles_ecrits_plus_tard():
    """X-20 : un fichier ouvert dans Excel est verrouillé sous Windows : les lignes attendent au lieu d'être perdues."""
    flush = fonction("void JournalFlush(bool force)")
    assert flush.index('if(!JournalOpenable("execution"))') < flush.index("ExecRow(") < flush.index("ArrayResize(gExecQ, 0);")
    ecrit = fonction("void TradesWrite(string line)")
    assert "ArrayResize(gTradeWait, 0);" in ecrit and ecrit.index("FileClose(h);") < ecrit.index("ArrayResize(gTradeWait, 0);")
    assert 'TradesWrite("");' in fonction("void OnTimer()")
    for f in ("void AppendTrade(datetime tx, double r, double net, string why)", "void AppendLegTrade(SLeg &g, datetime tx, double r, double net, string why)"):
        assert "TradesWrite(" in fonction(f) and "FileOpen(" not in fonction(f), f


def test_en_tete_a_jour():
    """Audit du 25/11/2026 : l'en-tête et la description disaient « Nasdaq uniquement », « stop de l'autre côté du range »,
    « mémoire à +0,05R » et « version non compilée »."""
    entete = EA[:EA.index("#property copyright")]
    for ancien in ("NASDAQ UNIQUEMENT", "uniquement", "Version non compilée", "+0,05R", "de l'autre côté du range. 1R"):
        assert ancien not in entete, ancien
    assert "Nasdaq 100 et S&P 500" in entete and "3 ranges" in entete
    assert "Nasdaq uniquement" not in re.search(r'#property description "([^"]*)"', EA).group(1)


def test_alertes_du_pine_pour_trader_a_la_main():
    """PINE-06 à PINE-08 : annulation d'une D guettée annoncée (avec son niveau dès l'alerte « GUETTÉE »), alerte à la sortie de
    15:50, lot de l'ajout des jambes chez le courtier. Non passé par l'analyseur de TradingView."""
    pine = open(os.path.join(ICI, "Strategy-V11.pine"), encoding="utf-8").read()
    assert "Annule l'ordre si le prix touche \" + fmt(nz(inval, stop))" in pine
    annule = pine.index('notify(g.name + " ANNULÉE : supprime l\'ordre stop "')
    assert pine.rindex('strategy.cancel(g.id)', 0, annule) > pine.rindex("if g.pend\n", 0, annule)
    fin = pine.index('strategy.close_all(comment = "Fin de journée")')
    assert pine.index('notify("FIN DE JOURNÉE', fin) - fin < 300
    assert 'float lotsAdd = legLots(g.risk)' in pine and '" (" + lotTxt(lotsAdd) + " chez le courtier)"' in pine


def test_en_tete_du_pine_a_jour():
    pine = open(os.path.join(ICI, "Strategy-V11.pine"), encoding="utf-8").read()
    entete = pine[:pine.index('strategy("Strategy V11')]
    assert entete.startswith("//@version=6\n")
    for ancien in ("NASDAQ UNIQUEMENT", "(NAS100) uniquement", "Version non passée", "+0,05R", "Stop     : de l'autre côté du range"):
        assert ancien not in entete, ancien
    assert "Nasdaq 100 et S&P 500" in entete and "3 ranges" in entete


# Les noms de prop firm à ne jamais écrire dans le dépôt public, par leur empreinte (sha256 du nom en minuscules, sans espace) : le
# test ne les écrit pas lui-même.
PROP_FIRMS = {"c86658c1a56457d2"}


def noms_de_prop_firm(texte):
    """Les mots (ou paires de mots collées) du texte dont l'empreinte est celle d'une prop firm."""
    import hashlib
    import re
    mots = re.findall(r"[a-z0-9]+", texte.lower())
    candidats = set(mots) | {a + b for a, b in zip(mots, mots[1:])}
    return [m for m in candidats if hashlib.sha256(m.encode()).hexdigest()[:16] in PROP_FIRMS]


def test_aucune_prop_firm_nommee_dans_le_depot_public():
    """Le dépôt est public : les infobulles du Pine disent « prop firm » sans nommer d'entreprise (choix de l'utilisateur, 25/11/2026)."""
    racine = os.path.dirname(ICI)
    for chemin in ("robot/Strategy-V11.pine", "robot/Strategy-V11.mq5", "README.md", "CLAUDE.md"):
        assert not noms_de_prop_firm(open(os.path.join(racine, chemin), encoding="utf-8-sig").read()), chemin
    assert noms_de_prop_firm("un certificat " + "Funding" + "Pips") and not noms_de_prop_firm("une prop firm")
    assert "chez une prop firm" in PINE and "compte de prop firm" in PINE


def test_v11_stop_des_continuations_a_l_entree_de_a_ea():
    """V11 (choix de l'utilisateur, 26/11/2026) : le stop posé d'une continuation D est le prix d'entrée de A ; sa taille et ses
    seuils (+1,5 R, +2 R) restent ceux de la V10 ; une D dont le niveau n'est pas au-delà de l'entrée de A n'est pas armée."""
    arm = fonction("void V9ArmD(MqlRates &r[])")
    assert "V11" in arm and "trigD - sprD <= gEntry + gapD" in arm and "trigD + sprD >= gEntry - gapD" in arm
    corps = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert "double slV10 = sl;" in corps
    assert "sl = NormalizeDouble(gEntry, _Digits);" in corps
    assert "g.risk = MathAbs(g.entry - (estD ? slV10 : sl));" in corps


def test_ex1_stop_d_controle_contre_le_bon_prix():
    """EX-1 (audit du 26/11/2026) : le stop d'un achat est contrôlé contre le bid, celui d'une vente contre l'ask, avec la distance
    minimale et le gel du courtier ; une D trop près de l'entrée de A n'est pas armée (un spread de marge)."""
    corps = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert "double refQ = dir == 1 ? bid : ask;" in corps and "(refQ - gEntry) * dir <= gapD" in corps
    assert "SYMBOL_TRADE_FREEZE_LEVEL" in corps
    arm = fonction("void V9ArmD(MqlRates &r[])")
    assert "SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)" in arm and "SYMBOL_TRADE_FREEZE_LEVEL" in arm


def test_ex2_risque_reel_d_plafonne():
    """EX-2 : le risque réel d'une D (jusqu'à l'entrée de A) ne dépasse pas celui de la cassure, et la notification l'affiche."""
    corps = fonction("bool LegOpen(SLeg &g, int dir, double stop, string quoi, double ref = 0)")
    assert "MathAbs(px - gEntry) / ts * tv" in corps
    assert "double capR = MathFloor(gV8RiskMoney / perLotReal / step + 0.000001) * step;" in corps
    assert "Dollars(-lots * (estD && perLotReal > 0 ? perLotReal : perLot))" in corps   # format des messages du 27/11/2026


def test_ex3_journal_version_2():
    """EX-3 : le journal d'exécution passe en version 2 (le stop initial d'une D est l'entrée de A)."""
    assert '#define JOURNAL_VERSION "2"' in EA


def test_ex5_envois_differes_pendant_les_entrees_surveillees():
    """EX-5 : pas d'envoi WhatsApp / Telegram (bloquant) pendant qu'une D est guettée ou qu'un côté de la cassure est surveillé."""
    corps = fonction("void FlushNotifs()")
    assert "n == 0 || EnvoiDiffere()" in corps
    diff = fonction("bool EnvoiDiffere()")
    assert "gD[k].arm" in diff and "!gSrvL" in diff and "!gSrvS" in diff


def test_ex7_glissement_de_la_sortie_de_fin_de_journee():
    """EX-7 : la sortie de 15:50 a un prix de référence (bid ou ask au moment de la décision) pour mesurer son glissement."""
    assert EA.count("FlatRef();") == 2
    ligne = fonction("void ExecRow(long posId, string type, int dirHint, double plan, double vstop, string why, double riskMoney, double rangeJour, double smultJour, int dayJour)")
    assert "finJ && !stopExit ? (refF - outPx) * dir : (ref - outPx) * dir" in ligne


def test_v11_stop_des_continuations_a_l_entree_de_a_pine():
    """V11 dans le Pine : même règle que l'EA."""
    assert "float  rsl" in PINE
    assert "openLegStop(string nm, int d, float trig, float stop, float inval, float q, bool pyrOk, int nBars, float slOrdre) =>" in PINE
    assert "strategy.exit(\"X\" + g.id, from_entry = g.id, stop = slOrdre," in PINE
    assert "(v8.dir == 1 ? high > cur.entry : low < cur.entry)" in PINE
    assert "g.risk  := math.abs(ep - nz(g.rsl, g.sl))" in PINE


def test_heure_du_serveur_detectee_automatiquement():
    """Automatisme du 26/11/2026 : hors testeur, le décalage du serveur se déduit de TimeTradeServer() - TimeGMT() ; les
    réglages ne servent plus que dans le testeur (où TimeGMT() vaut l'heure du serveur) ou si la détection est coupée."""
    assert "input bool         InpSrvAuto   = true;" in EA
    det = fonction("void DetecterHeureServeur()")
    assert "MQLInfoInteger(MQL_TESTER)" in det and "MathRound((double)brut / 3600.0) * 3600" in det and "MathAbs(brut - reel) > 600" in det
    assert "long     base = gSrvBaseOk ? gSrvBaseSec : (long)InpSrvGMT * 3600;" in EA
    assert "DetecterHeureServeur();" in fonction("void CheckClock()")


def test_fomc_lus_dans_le_calendrier_au_dela_de_la_liste():
    """Automatisme du 26/11/2026 : après le dernier jour codé, les décisions de la Fed viennent du calendrier de MetaTrader."""
    cal = fonction("bool FomcCalendrier(int ymd)")
    assert '"fed-interest-rate-decision"' in cal and "MQLInfoInteger(MQL_TESTER)" in cal
    assert "return ymd > FOMC_DATES[ArraySize(FOMC_DATES) - 1] && FomcCalendrier(ymd);" in fonction("bool IsFomc(int ymd)")


def test_etiquettes_v11():
    """26/11/2026 : la version, l'état lu par Étrave, la raison des trades et le panneau disaient encore « V10 »."""
    for texte in ('#property version     "11.00"', 'Kv(h, "ea", "11.00");', 'string w = "V11 " + g.nom', '"Entrées V11 : "'):
        assert texte in EA, texte


# ───────────────────────── audit du 26/11/2026 (AUD-xx) ─────────────────────────
def mql_round(x):
    """MathRound de MQL5 : la moitié s'éloigne de zéro."""
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


def horloge(avance_min, srv_gmt_h=2, dst=False):
    """Copie en Python de DetecterHeureServeur() + CheckClock() (détection automatique) : l'horloge de l'ordinateur est en
    avance de `avance_min` minutes sur l'heure vraie ; le serveur est réellement à GMT+srv_gmt_h (+1 h en été).
    Renvoie (heure du serveur jugée bonne, écart annoncé en minutes : positif = horloge de l'ordinateur en avance)."""
    vrai = (srv_gmt_h + (1 if dst else 0)) * 3600
    brut = vrai - avance_min * 60                  # TimeTradeServer() - TimeGMT() : l'ordinateur en avance réduit l'écart
    reel = mql_round(brut / 3600.0) * 3600
    base = reel - (3600 if dst else 0)
    attendu = srv_gmt_h * 3600 + (3600 if dst else 0)
    decalage = base + (3600 if dst else 0)         # ServerOffsetSec avec la base détectée
    ok = abs(brut - decalage) <= 1800 and base == srv_gmt_h * 3600
    return ok, round((attendu - brut) / 60)


def test_aud03_horloge_decalee_d_une_heure_bloque_le_trading():
    """AUD-03 : avec une horloge d'ordinateur décalée de 50 à 70 min, la détection prenait la bougie de 8:30 ou de 10:30 sans
    alerte : CheckClock comparait la détection à elle-même. Elle doit concorder avec le décalage réglé (InpSrvGMT)."""
    for avance in (40, 50, 60, 70, 80, -40, -60, -80):
        assert horloge(avance)[0] is False, avance
        assert horloge(avance, dst=True)[0] is False, avance
    for avance in (0, 10, 20, 29, -20, -29):
        assert horloge(avance)[0] is True, avance
    clock = fonction("void CheckClock()")
    assert "InpSrvAuto && gSrvBaseOk && gSrvBaseSec != (long)InpSrvGMT * 3600" in clock
    assert clock.index("DetecterHeureServeur();") < clock.index("gSrvBaseSec != (long)InpSrvGMT * 3600")


def test_aud04_ecart_de_l_horloge_annonce_par_rapport_a_l_heure_attendue():
    """AUD-04 : à +40 min, le message disait « décalée de 20 min » (écart à l'heure pleine la plus proche)."""
    assert horloge(40)[1] == 40 and horloge(80)[1] == 80 and horloge(30)[1] == 30 and horloge(-25)[1] == -25
    det = fonction("void DetecterHeureServeur()")
    assert "long attendu = (long)InpSrvGMT * 3600 + (dst ? 3600 : 0);" in det
    assert "(attendu - brut) / 60.0" in det and '"en avance"' in det and '"en retard"' in det


def compte_autorise(testeur, demo, login, fichier):
    """Copie en Python de CompteAutorise()."""
    if testeur or demo:
        return True
    return login > 0 and login == fichier


def test_aud01_compte_reel_jamais_trade_sans_autorisation():
    """AUD-01 : le double-clic lançait le trading automatique sur le compte enregistré, réel compris, sans contrôle."""
    assert compte_autorise(True, False, 123, 0) and compte_autorise(False, True, 123, 0)
    assert not compte_autorise(False, False, 123, 0)
    assert not compte_autorise(False, False, 123, 456) and not compte_autorise(False, False, 0, 0)
    assert compte_autorise(False, False, 123, 123)
    f = fonction("bool CompteAutorise()")
    assert "MQLInfoInteger(MQL_TESTER)" in f and "ACCOUNT_TRADE_MODE_DEMO" in f
    assert "return login > 0 && login == gReelAutorise;" in f
    setup = corps("Setup")
    garde = setup.index("if(!CompteAutorise())")
    assert setup.index("if(!gClockOk)") < garde < setup.index("gObserve   = true;") < setup.index("PlaceStop(1)")
    assert 'k == "reel_autorise"' in fonction("void ReadSettings()")
    assert 'Kv(h, "compte_autorise", CompteAutorise() ? "1" : "0");' in fonction("void WriteState()")
    entrees = fonction("void CheckEntries()")
    assert entrees.index("if(!CompteAutorise())") < entrees.index("trade.Buy(gLots")
    assert "InpCompteReel" not in EA                     # rien à régler dans MetaTrader : l'autorisation vient d'Étrave


def test_aud02_l_etat_appartient_a_un_compte():
    """AUD-02 : l'état (règle mémoire, jour, trade ouvert, statistiques) d'un compte démo était relu tel quel sur un compte réel."""
    charge = fonction("void ChargerEtatDuCompte()")
    assert "if(login <= 0)\n      return;" in charge                      # compte pas encore connu au démarrage : réessayé
    assert "(long)lu == login || (lu == 0 && demo)" in charge and "LoadState();" in charge
    assert "GlobalVariablesDeleteAll(GV);" in charge and 'Sv("login", (double)login);' in charge
    assert 'Sv("login", (double)AccountInfoInteger(ACCOUNT_LOGIN));' in fonction("void SaveState()")
    assert "if(MQLInfoInteger(MQL_TESTER) || !gEtatCharge)\n      return;" in fonction("void SaveState()")
    init = fonction("int OnInit()")
    assert "ChargerEtatDuCompte();" in init and "      LoadState();\n" not in init
    tick = fonction("void OnTick()")
    assert tick.index("if(!gEtatCharge)") < tick.index("SyncPosition();")


def test_aud05_risque_plafonne_a_20_pct():
    """AUD-05 : au-delà du plafond, le risque est ramené au plafond. Plafond de 1 % du 27/11/2026 (audit), remonté à 20 % le même
    jour par décision de l'utilisateur (« pour des tests », tous comptes, mot RISQUE dans Étrave au-delà de 0,5 %)."""
    assert re.search(r"#define RISK_MAX\s+20\.0\b", EA)
    assert re.search(r"#define RISK_MIN\s+0\.05\b", EA)
    lecture = fonction("void ReadSettings()")
    assert "risk = MathMin(x, RISK_MAX);" in lecture
    assert "double risk   = MathMin(InpRiskPct, RISK_MAX);" in lecture


def test_aud06_pas_de_renvoi_tant_que_l_historique_n_a_pas_ete_relu():
    """AUD-06 : après une réponse perdue, l'ordre A repartait au bout de 3 s si la position n'était pas encore visible."""
    trouve = fonction("bool EntreeATrouvee(datetime depuis)")
    assert "HistorySelect(" in trouve and "DEAL_ENTRY_IN" in trouve and "HistoryOrdersTotal()" in trouve and "OrdersTotal()" in trouve
    entrees = fonction("void CheckEntries()")
    assert entrees.index("GetTickCount() - gAmbigMs < 3000") < entrees.index("EntreeATrouvee(gAmbigT)") < entrees.index("trade.Buy(gLots")
    assert "gAmbigT = TimeCurrent();" in entrees


def test_aud06_doublon_de_a_ferme_et_pas_pris_pour_une_pyramide():
    """AUD-06 : deux positions A de même taille ouvertes à quelques secondes d'écart passaient pour une pyramide."""
    doublon = fonction("int FermerDoublonsA()")
    assert "POSITION_TIME_MSC" in doublon and "DOUBLON_S" in doublon and "trade.PositionClose(" in doublon
    assert "MathAbs(vol - volRef) < step / 2" in doublon
    sync = fonction("void SyncPosition()")
    assert sync.index("FermerDoublonsA() > 0") < sync.index("gPyr     = CountPos(gDir) > 1;")
    tick = fonction("void OnTick()")
    assert "FermerDoublonsA();" in tick


def test_aud07_ordre_stop_deja_pose_repris_a_la_relance():
    """AUD-07 : relancé pendant la bougie de 9:35 avant l'écriture de l'état, l'EA reposait les deux ordres stop."""
    pose = fonction("bool PlaceStop(int d)")
    assert pose.index("if(HasPending(d))\n      return true;") < pose.index("trade.BuyStop(")
    setup = corps("Setup")
    assert setup.index("GlobalVariablesFlush();") < setup.index("PlaceStop(1)")


def test_aud08_stop_du_courtier_relu_chaque_minute():
    """AUD-08 : une position sans stop chez le courtier n'était jamais repérée."""
    verif = fonction("void VerifierStops()")
    assert "PositionGetDouble(POSITION_SL) > 0" in verif and "trade.PositionModify(" in verif and "trade.PositionClose(" in verif
    assert "mg < InpMagic || mg > InpMagic + 2 + D_MAX" in verif
    tick = fonction("void OnTick()")
    assert tick.index("TimeCurrent() - sweepAt >= 60") < tick.index("VerifierStops();") < tick.index("CloseOrphans(")


def test_aud11_un_seul_graphique_par_symbole():
    """AUD-11 : la V11 posée sur deux graphiques du même symbole doublait le risque et partageait le même état."""
    init = fonction("int OnInit()")
    assert "if(!PrendreVerrou())" in init and "INIT_FAILED" in init[init.index("if(!PrendreVerrou())"):]
    verrou = fonction("bool PrendreVerrou()")
    assert "GlobalVariableSetOnCondition(" in verrou and "GlobalVariableTemp(" in verrou and "VERROU_MUET_S" in verrou
    assert "RelacherVerrou();" in fonction("void OnDeinit(const int reason)")
    assert "BattreVerrou();" in fonction("void OnTimer()")


def test_aud17_jour_manque_signale():
    """AUD-17 : EA lancé ou relancé après la bougie de 9:35 : le jour disparaissait sans message."""
    barre = fonction("void OnNewBar()")
    assert "JOUR MANQUÉ" in barre and "NYMin(ny1) > mOR" in barre and "gManque != NYDate(ny1)" in barre


def test_aud18_jambe_inconnue_de_l_etat_reprise():
    """AUD-18 : une jambe B/D marquée refusée ou perdue alors que sa position existe restait sans gestion jusqu'à 15:51."""
    tick = fonction("void LegOnTick(SLeg &g)")
    assert tick.index("if(!g.enPos && has)") < tick.index("if(g.enPos && !has)")
    adopt = fonction("void LegAdopt(SLeg &g)")
    assert "POSITION_PRICE_OPEN" in adopt and "POSITION_SL" in adopt and "g.enPos = true;" in adopt and "LegSave(g);" in adopt


def test_aud20_cloture_demandee_reessayee():
    """AUD-20 : si la clôture demandée et le balayage de 10 s étaient refusés, plus aucun essai jusqu'à 15:51."""
    tick = fonction("void OnTick()")
    assert "if(sweepUi && nS > 0)" in tick and "gSweepAllAt = TimeCurrent() + 10;" in tick
    assert "CLÔTURE PAS ENCORE FAITE" in tick


def test_aud22_version_compilee_publiee():
    assert 'Kv(h, "ea_build", TimeToString(__DATETIME__, TIME_DATE | TIME_SECONDS));' in fonction("void WriteState()")


def test_aud23_pas_d_essai_telegram_pendant_un_trade():
    lecture = fonction("void ReadSettings()")
    assert "(gPend || gSetupDue || gIn || OpenLegs() > 0 || EnvoiDiffere())" in lecture


def test_aud24_lot_minimum_et_pas_publies():
    etat = fonction("void WriteState()")
    for cle in ("lot_min", "lot_pas", "valeur_point_lot", "prix"):
        assert f'Kd(h, "{cle}"' in etat, cle


def marches_du_code(texte, motif):
    return set(re.findall(motif, texte))


def test_aud28_meme_liste_de_marches_dans_l_ea_et_le_script():
    """AUD-28 : « USATECHIDXUSD » ou « ES1! » étaient acceptés par l'un et refusés par l'autre."""
    ea = marches_du_code(fonction("string InstrumentOf(string sym)"), r'StringFind\(s, "([A-Z0-9&]+)"\)')
    pine_ligne = PINE[PINE.index("bool marcheOk ="):PINE.index("\n", PINE.index("bool marcheOk ="))]
    pine = marches_du_code(pine_ligne, r'str\.(?:contains|startswith)\(tkU, "([A-Z0-9&]+)"\)')
    assert ea == pine, (ea ^ pine)
    assert 'StringFind(s, "ES1") == 0' in fonction("string InstrumentOf(string sym)") and 'str.startswith(tkU, "ES1")' in pine_ligne


def test_aud12_le_script_plafonne_le_risque_reel_des_d_comme_l_ea():
    """AUD-12 : l'EA plafonne le risque réel d'une D (jusqu'à l'entrée de A) à celui de la cassure (EX-2) ; le Pine prenait toute
    la taille, et une D étroite loin de l'entrée de A risquait plus que la cassure."""
    assert "float capD  = distA > 0 and not na(v8.usd) ? math.floor(v8.usd / (distA * syminfo.pointvalue * fx) / qtyStep + 0.000001) * qtyStep : 0.0" in PINE
    assert "qD := math.min(qD, capD)" in PINE
    assert PINE.index("qD := math.min(qD, capD)") < PINE.index("if qD > 0 and (v8.dir == 1 ? high > cur.entry : low < cur.entry)")
    assert "float  lots = math.min(legLots(g.risk), legLots(math.abs(trig - slOrdre)))" in PINE


# ───────────────────────── notifications (demande de l'utilisateur du 27/11/2026) ─────────────────────────
# Telegram (et WhatsApp, push) ne reçoit plus que : la connexion réussie, les ordres posés, les entrées exécutées et les clôtures
# avec leur résultat en R et en dollars. Les alertes de sécurité (⚠) vont dans Étrave. Le reste ne va plus que dans le journal.

def appels(nom):
    """Le texte de chaque appel `nom(...)` de l'EA (définition exclue), parenthèses des chaînes ignorées."""
    resultat, debut = [], 0
    while True:
        i = EA.find(nom + "(", debut)
        if i < 0:
            return resultat
        debut = i + 1
        if EA[i - 1].isalnum() or EA[i - 1] == "_" or EA[max(0, i - 5):i] == "void ":
            continue
        profondeur, chaine, j = 0, False, i + len(nom)
        while True:
            c = EA[j]
            if chaine:
                if c == "\\":
                    j += 1
                elif c == '"':
                    chaine = False
            elif c == '"':
                chaine = True
            elif c == "(":
                profondeur += 1
            elif c == ")":
                profondeur -= 1
                if profondeur == 0:
                    break
            j += 1
        resultat.append(EA[i:j + 1])


def test_telegram_ne_recoit_que_connexion_ordres_entrees_et_clotures():
    vers_telegram = [a for a in appels("Notify") if re.search(r",\s*true\)$", a)]
    reperes = ["Connexion réussie", "ORDRES PLACÉS", "Notify(id + \" à \" + PxF(gEntry)", " exécuté(e) : ", "\"ACHAT CLÔTURÉ · \"", "\"ENTRÉE \" + g.nom + \" CLÔTURÉE · \""]
    assert len(vers_telegram) == len(reperes)
    for repere in reperes:
        assert sum(repere in a for a in vers_telegram) == 1, repere
    corps = fonction("void Notify(string msg, bool tg = false)")
    # tout va au journal ; push, WhatsApp et Telegram seulement sur demande
    assert corps.index("Print(full);") < corps.index("if(!tg)") < corps.index("SendNotification(") < corps.index("gQueue[n] = full;")


def test_les_alertes_de_securite_vont_dans_etrave():
    corps = fonction("void Notify(string msg, bool tg = false)")
    assert "if(StringFind(msg, I_WARN) == 0)\n      AlerteEtrave(msg);" in corps
    assert corps.index("AlerteEtrave(msg);") < corps.index("if(!tg)")
    ecriture = fonction("void AlertesWrite(string line)")
    assert 'UI_DIR + "alertes-" + gSymFile + ".csv"' in ecriture and "FileSeek(h, 0, SEEK_END);" in ecriture
    assert "ArrayResize(gAlertWait, 0);" in ecriture                          # écrites, la file se vide
    alerte = fonction("void AlerteEtrave(string msg)")
    assert "string txt = StringSubstr(msg, StringLen(I_WARN));" in alerte      # sans le pictogramme ⚠ (la page n'en a pas)
    # une ligne : secondes UTC ; symbole ; texte sans pictogramme, sans retour à la ligne ni point-virgule
    assert "IntegerToString((long)TimeGMT()) + \";\" + gSymFile + \";\" + txt" in alerte
    assert 'StringReplace(txt, ";", ",");' in alerte and 'StringReplace(txt, "\\n", " · ");' in alerte
    assert "if(MQLInfoInteger(MQL_TESTER) || !InpUseUI)" in alerte
    minuteur = fonction("void OnTimer()")
    assert 'AlertesWrite("");' in minuteur                                   # fichier verrouillé : réessayé toutes les 2 s


def test_aucune_alerte_de_securite_n_est_envoyee_sur_telegram():
    for appel in appels("Notify"):
        if appel.startswith("Notify(I_WARN"):
            assert not re.search(r",\s*true\)$", appel), appel


def test_message_de_connexion_une_fois_par_configuration():
    lecture = fonction("void ReadSettings()")
    assert 'if(gTgOn && gTgHello != gTgToken + "|" + gTgChat)' in lecture
    bloc = lecture[lecture.index('if(gTgOn && gTgHello'):]
    assert bloc.index('gTgHello = gTgToken + "|" + gTgChat;') < bloc.index("Notify(I_PLUG")
    assert lecture.index("gRiskPct  = risk;") < lecture.index("if(gTgOn && gTgHello")   # le risque annoncé est celui appliqué
    message = [a for a in appels("Notify") if "Connexion réussie" in a][0]
    assert "ACCOUNT_LOGIN" not in message                                    # pas de numéro de compte sur Telegram


def test_les_clotures_donnent_le_resultat_en_R_et_en_dollars():
    for appel in appels("Notify"):
        if "CLÔTUR" in appel and re.search(r",\s*true\)$", appel):
            assert "RTxt2(r)" in appel and "Dollars(net)" in appel and "IcoSortie(why)" in appel


def nombre_fr(v, dec):
    """Copie en Python de Nombre() : valeur absolue, espaces entre milliers, virgule décimale."""
    s = f"{abs(v):.{dec}f}"
    ent, _, fra = s.partition(".")
    groupes = []
    while len(ent) > 3:
        groupes.insert(0, ent[-3:])
        ent = ent[:-3]
    groupes.insert(0, ent)
    return " ".join(groupes) + ("," + fra if fra else "")


def signe(v, dec):
    """Copie de Signe() : rien pour une valeur qui s'arrondit à zéro (jamais « -0,00 »)."""
    a = round(v, dec)
    return "+" if a > 0 else "-" if a < 0 else ""


def dollars(v, devise="USD"):
    return signe(v, 2) + nombre_fr(v, 2) + (" $" if devise == "USD" else " " + devise)


@pytest.mark.parametrize("v, attendu", [(0, "0,00 $"), (-0.004, "0,00 $"), (0.004, "0,00 $"), (65.2, "+65,20 $"), (-51, "-51,00 $"),
                                        (-1234.5, "-1 234,50 $"), (999.999, "+1 000,00 $"), (1e9, "+1 000 000 000,00 $")])
def test_montant_en_dollars(v, attendu):
    assert dollars(v) == attendu


def test_montant_dans_une_autre_devise():
    assert dollars(65.2, "EUR") == "+65,20 EUR"


@pytest.mark.parametrize("r, attendu", [(0, "0,00 R"), (-0.001, "0,00 R"), (-1.02, "-1,02 R"), (2.5, "+2,50 R"), (12345.6, "+12 345,60 R")])
def test_resultat_en_R(r, attendu):
    assert signe(r, 2) + nombre_fr(r, 2) + " R" == attendu


def test_les_textes_de_l_ea_sont_ceux_recopies_ici():
    assert "string Signe(double v, int dec) { double a = NormalizeDouble(v, dec); return a > 0 ? \"+\" : a < 0 ? \"-\" : \"\"; }" in EA
    assert "string RTxt2(double r)   { return Signe(r, 2) + Nombre(r, 2) + \" R\"; }" in EA
    assert "return Signe(v, 2) + Nombre(v, 2) + (c == \"USD\" ? \" $\" : \" \" + c);" in fonction("string Dollars(double v)")
    nombre = fonction("string Nombre(double v, int dec)")
    assert "DoubleToString(MathAbs(v), dec)" in nombre and "(n - i) % 3 == 0" in nombre and '"," + StringSubstr(s, p + 1)' in nombre


def utf16(code):
    """Copie de Ico() : un pictogramme au-delà de 0xFFFF s'écrit en deux unités UTF-16 (paire de substitution)."""
    if code <= 0xFFFF:
        return [code]
    return [0xD800 + ((code - 0x10000) >> 10), 0xDC00 + ((code - 0x10000) & 0x3FF)]


@pytest.mark.parametrize("code", [0x26A0, 0x1F4CC, 0x1F3AF, 0x1F6D1, 0x1F552, 0x1F50C, 0x1F4C8])
def test_pictogrammes_au_dela_de_0xffff(code):
    unites = utf16(code)
    assert b"".join(u.to_bytes(2, "little") for u in unites).decode("utf-16-le") == chr(code)
    ico = fonction("string Ico(uint code)")
    assert "0xD800 + ((code - 0x10000) >> 10)" in ico and "0xDC00 + ((code - 0x10000) & 0x3FF)" in ico


def test_pictogramme_du_motif_de_sortie():
    motif = fonction("string IcoSortie(string why)")
    for why, ico in (("Objectif", "I_TARGET"), ("Stop", "I_STOP"), ("Stop à l'entrée", "I_SCALE"), ("Stop remonté", "I_LOCKED"),
                     ("Fin de journée", "I_CLOCK"), ("Sortie au temps", "I_CLOCK"), ("Fermeture manuelle", "I_HAND")):
        assert f'if(why == "{why}")\n      return {ico};' in motif, why
    assert 'if(StringFind(why, "nterface") >= 0)\n      return I_HAND;' in motif   # clôture depuis Étrave
    assert motif.rstrip().endswith("return I_WARN;\n  }")                       # filet de sécurité, stop absent chez le courtier


def test_les_messages_telegram_sont_au_format_francais():
    """Prix, points, pourcentages, lots, R et montants : espaces entre milliers et virgule, comme les R et les dollars."""
    for appel in appels("Notify"):
        if re.search(r",\s*true\)$", appel):
            for ancien in ("Px(", "Pts(", "PctS(", "RTxt(", "RiskTxt(", "Money(", "DoubleToString("):
                assert not re.search(r"(?<![A-Za-z])" + re.escape(ancien), appel), (ancien, appel[:60])
            assert '" trades"' not in appel or "gN > 1" in appel                    # « 1 trade », « 2 trades »
    assert "string PxF(double p)  { return (NormalizeDouble(p, _Digits) < 0 ? \"-\" : \"\") + Nombre(p, _Digits); }" in EA
    assert "string PtsF(double d) { return (NormalizeDouble(d, _Digits) < 0 ? \"-\" : \"\") + Nombre(d, _Digits) + \" pts\"; }" in EA
    assert "string PctF(double v) { return Signe(v, 2) + Nombre(v, 2) + \" %\"; }" in EA


def url_encode(texte):
    """Copie de UrlEncode() : tout le texte converti en UTF-8 d'un seul coup, puis chaque octet hors A-Z a-z 0-9 - _ . ~ en %XX."""
    return "".join(chr(o) if (chr(o).isascii() and (chr(o).isalnum() or chr(o) in "-_.~")) else f"%{o:02X}" for o in texte.encode("utf-8"))


@pytest.mark.parametrize("code", [0x1F4CC, 0x1F4C9, 0x1F50C, 0x1F6D1, 0x1F552, 0x1F4B0, 0x26A0, 0x2705])
def test_les_pictogrammes_partent_en_utf8_complet_vers_telegram(code):
    """Les pictogrammes au-delà de 0xFFFF sont deux unités UTF-16 dans l'EA : convertis ensemble (texte entier), ils donnent les
    4 octets UTF-8 du caractère. Convertis unité par unité, Telegram recevrait des octets invalides."""
    unites = utf16(code)
    texte = b"".join(u.to_bytes(2, "little") for u in unites).decode("utf-16-le") + " Connexion réussie"
    encode = url_encode(texte)
    assert encode == urllib.parse.quote(texte, safe="-_.~")
    assert urllib.parse.unquote(encode) == chr(code) + " Connexion réussie"
    corps = fonction("string UrlEncode(string s)")
    assert "int   n = StringToCharArray(s, b, 0, WHOLE_ARRAY, CP_UTF8);" in corps          # le texte entier, pas caractère par caractère
    assert '"&text=" + UrlEncode(msg)' in fonction("string SendTelegram(string msg)")
