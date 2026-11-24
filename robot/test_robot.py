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
    assert "InpStopMult * (gOrH - gOrL)" in EA and "costPts / (stopMult * dist)" in PINE


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
