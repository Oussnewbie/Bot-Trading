"""Tests de l'export trimestriel d'Étrave (etrave/export.py) et de son accord avec les journaux de l'EA : `python -m pytest etrave`."""
import datetime
import json
import os
import re
import sys
import threading

import pytest

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import etrave  # noqa: E402
import export  # noqa: E402

EA = open(os.path.join(os.path.dirname(ICI), "robot", "Strategy-V10.mq5"), encoding="utf-8-sig").read()
EXEC = re.search(r'#define EXEC_COLONNES\s+"([^"]+)"', EA).group(1).split(";")
SEANCE = re.search(r'#define SEANCE_COLONNES\s+"([^"]+)"', EA).group(1).split(";")


def ecrire(chemin, lignes):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write("".join(l + "\r\n" for l in lignes))


def ligne(colonnes, **valeurs):
    base = {c: "" for c in colonnes}
    base.update({"version": "1", "source": "demo", "complet": "1"}, **{k: str(v) for k, v in valeurs.items()})
    return ";".join(base[c] for c in colonnes)


def trade(jour, symbole, r, net):
    sortie = int(datetime.datetime.fromisoformat(jour + "T20:50:00").timestamp())
    return f"{sortie};{jour};15:50;{symbole};1;0.1;{r};{net};1000.00;Stop;0;USD"


@pytest.fixture()
def dossier(tmp_path):
    d = str(tmp_path)
    # Nasdaq : deux jours de trade en janvier 2027 (A et son ajout le 4, une B le 5), une séance FOMC, une séance sans cassure
    ecrire(os.path.join(d, "trades-NDX100.csv"), [trade("2027-01-04", "NDX100", 1.5, 41.0), trade("2027-01-05", "NDX100", -1.0, -27.0),
                                                   trade("2026-12-30", "NDX100", 0.5, 13.0)])
    ecrire(os.path.join(d, "execution-NDX100.csv"), [";".join(EXEC),
        ligne(EXEC, id_position=11, jour_ny="2027-01-04", symbole="NDX100", entree="A", sens=1, glissement_entree="0.6", spread_entree="1.2",
              glissement_sortie="", mfe_r="2.4", mae_r="0.3", resultat_net="30.00", frais="-0.50", swap="0", r="1.1"),
        ligne(EXEC, id_position=12, jour_ny="2027-01-04", symbole="NDX100", entree="A+", sens=1, glissement_entree="1.4", spread_entree="1.0",
              mfe_r="0.8", mae_r="0.5", resultat_net="11.00", r="0.4"),
        ligne(EXEC, id_position=13, jour_ny="2027-01-05", symbole="NDX100", entree="B", sens=1, glissement_entree="0.2", spread_entree="1.1",
              glissement_sortie="2.0", raison="Stop", mfe_r="0.1", mae_r="1.0", resultat_net="-20.00", r="-0.74"),
        "1;demo;99;ligne;abîmée"])
    ecrire(os.path.join(d, "seances-NDX100.csv"), [";".join(SEANCE),
        ligne(SEANCE, jour_ny="2027-01-04", symbole="NDX100", moment="decision", etat="Achat stop 21000.5 · jusqu'à 09:45"),
        ligne(SEANCE, jour_ny="2027-01-05", symbole="NDX100", moment="decision", etat="Achat stop 21100.5 · jusqu'à 09:45"),
        ligne(SEANCE, jour_ny="2027-01-06", symbole="NDX100", moment="decision", etat="Pas de trade : jour de décision de la Fed (FOMC)"),
        ligne(SEANCE, jour_ny="2027-01-07", symbole="NDX100", moment="decision", etat="Achat stop 21200.5 · Vente stop 21150.0 · jusqu'à 09:45"),
        ligne(SEANCE, jour_ny="2027-01-07", symbole="NDX100", moment="fin", etat="Pas de trade : pas de cassure avant 09:45 NY")])
    # le testeur de stratégie : jamais exporté, même s'il tombe dans le trimestre
    ecrire(os.path.join(d, "testeur", "execution-NDX100.csv"), [";".join(EXEC),
        ligne(EXEC, source="testeur", id_position=1, jour_ny="2027-01-04", symbole="NDX100", entree="A", resultat_net="999")])
    return d


def test_les_colonnes_de_l_ea_sont_celles_de_l_export():
    """L'export lit les journaux par le nom de leurs colonnes : ces noms doivent être ceux que l'EA écrit."""
    lues = {"version", "source", "jour_ny", "symbole", "entree", "glissement_entree", "spread_entree", "glissement_sortie", "mfe_r",
            "mae_r", "r", "resultat_net", "frais", "swap", "complet"}
    assert lues <= set(EXEC) and {"version", "source", "jour_ny", "symbole", "moment", "etat"} <= set(SEANCE)
    documentees = {nom.strip() for noms, _ in export.COLONNES_DOC["execution"] for nom in noms.split(",")}
    assert documentees <= set(EXEC), documentees - set(EXEC)
    documentees = {nom.strip() for noms, _ in export.COLONNES_DOC["seances"] for nom in noms.split(",")}
    assert documentees <= set(SEANCE), documentees - set(SEANCE)


def test_trimestres_en_dates_de_new_york():
    assert export.trimestre_de(datetime.date(2027, 3, 31)) == "2027-T1" and export.trimestre_de(datetime.date(2026, 12, 31)) == "2026-T4"
    assert export.bornes("2026-T4") == (datetime.date(2026, 10, 1), datetime.date(2026, 12, 31))
    assert export.bornes("2027-T2") == (datetime.date(2027, 4, 1), datetime.date(2027, 6, 30))
    assert not export.termine("2027-T1", datetime.date(2027, 4, 3))     # dernière séance peut-être pas encore écrite
    assert export.termine("2027-T1", datetime.date(2027, 4, 4))


def test_journal_lu_par_en_tete_et_ligne_abimee_ignoree(dossier):
    lignes, entete = export.lire_journal(dossier, "execution")
    assert entete == EXEC and len(lignes) == 3                                 # la ligne abîmée et le testeur sont écartés
    assert {l["entree"] for l in lignes} == {"A", "A+", "B"}


def test_export_du_trimestre(dossier):
    chemin, r = export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 4, 10))
    assert os.path.basename(chemin) == "2027-T1" and not r["en_cours"]
    assert sorted(os.listdir(chemin)) == ["colonnes.md", "execution.csv", "resume.json", "resume.md", "seances.csv", "trades.csv"]
    assert r["trades"]["n"] == 2 and r["trades"]["total_r"] == 0.5 and r["trades"]["total_net"] == 14.0   # décembre 2026 exclu
    assert r["jours"]["n"] == 2 and r["jours"]["pire_r"] == -1.0 and r["jours"]["baisse_max_r"] == 1.0
    a = r["execution"]["A"]
    assert a["positions"] == 1 and a["glissement_entree"]["moyenne"] == 0.6 and a["spread_entree"]["moyenne"] == 1.2
    assert r["execution"]["B"]["sorties_au_stop"] == 1 and r["execution"]["B"]["glissement_sortie_stop"]["pire"] == 2.0
    s = r["seances"]
    assert s["decisions"] == 4 and s["familles"] == {"ordres posés": 3, "pas de trade : FOMC": 1}
    assert s["ordres_poses_sans_trade"] == {"pas de trade : pas de cassure avant 9:45": 1}
    assert "2027-01-01" in s["jours_de_semaine_sans_seance"]["NDX100"] and "2027-01-06" not in s["jours_de_semaine_sans_seance"]["NDX100"]
    # rapprochement : le 4, les trades disent 41 $, l'exécution 30 + 11 ; le 5, -27 contre -20 : un écart, signalé
    assert r["rapprochement"]["ecarts"] == [{"jour": "2027-01-05", "symbole": "NDX100", "trades": -27.0, "execution": -20.0}]
    lisible = open(os.path.join(chemin, "resume.md"), encoding="utf-8").read()
    assert "2027-T1" in lisible and "| A | 1 |" in lisible and "1 écart(s)" in lisible
    assert json.load(open(os.path.join(chemin, "resume.json"), encoding="utf-8"))["trimestre"] == "2027-T1"
    execution = open(os.path.join(chemin, "execution.csv"), encoding="utf-8").read().splitlines()
    assert execution[0] == ";".join(EXEC) and len(execution) == 4 and "999" not in "".join(execution)
    trades = open(os.path.join(chemin, "trades.csv"), encoding="utf-8").read().splitlines()
    assert trades[0].startswith("sortie;date;heure;symbole") and len(trades) == 3


def test_export_refait_d_un_seul_coup(dossier):
    export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 2, 1))
    chemin, r = export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 4, 10))
    assert not r["en_cours"]
    assert os.listdir(export.dossier_exports(dossier)) == ["2027-T1"]          # ni dossier provisoire ni ancien export qui traîne


def test_export_automatique_des_trimestres_finis(dossier):
    # le 2 avril 2027, 2027-T1 n'est pas encore terminé ; 2026-T4 (un trade le 30/12) l'est
    assert export.exporter_trimestres_finis(dossier, datetime.date(2027, 4, 2)) == ["2026-T4"]
    assert export.exporter_trimestres_finis(dossier, datetime.date(2027, 4, 2)) == []                 # jamais deux fois
    assert export.exporter_trimestres_finis(dossier, datetime.date(2027, 4, 10)) == ["2027-T1"]
    # un export « en cours » fait à la main est refait une fois le trimestre terminé
    export.exporter(dossier, "2027-T2", aujourdhui=datetime.date(2027, 5, 1))
    ecrire(os.path.join(dossier, "trades-SPX500.csv"), [trade("2027-05-03", "SPX500", 0.5, 4.0)])
    assert export.exporter_trimestres_finis(dossier, datetime.date(2027, 7, 10)) == ["2027-T2"]
    assert [e["nom"] for e in export.exports_faits(dossier)] == ["2027-T2", "2027-T1", "2026-T4"]


def test_interrupteur_sur_60_jours():
    trades = [{"date": (datetime.date(2027, 1, 1) + datetime.timedelta(days=i)).isoformat(), "r": -1.0} for i in range(60)]
    i = export.interrupteur(trades, datetime.date(2027, 12, 31))
    assert i["jours"] == 60 and i["complet"] and i["total_r"] == -60.0 and set(i["franchi"]) == {"jours gagnants", "total"}
    assert export.interrupteur([], datetime.date(2027, 1, 1)) == {"jours": 0}


def test_routes_des_exports(dossier):
    app = etrave.Application(dossier)
    assert app.traiter("GET", "/api/exports", {}, None)["exports"] == []
    resultat = app.traiter("POST", "/api/exports", {}, {"trimestre": "2027-T1"})
    assert resultat["ok"] and resultat["trimestre"] == "2027-T1" and resultat["exports"][0]["nom"] == "2027-T1"
    with pytest.raises(etrave.Erreur):
        app.traiter("POST", "/api/exports", {}, {"trimestre": "../../etc"})
    app.exporter_trimestres_finis()                                           # ne lève jamais d'erreur
    page = open(os.path.join(ICI, "page.html"), encoding="utf-8").read()
    assert "api('/api/exports'" in page and "$('export-now').addEventListener('click', () => exportNow(null));" in page


def test_interrupteur_indicatif_avant_60_jours(tmp_path):
    """ET-11 : deux jours perdants ne disent pas « coupe le robot » ; à 60 jours, si."""
    dossier = str(tmp_path)
    ecrire(os.path.join(dossier, "trades-NDX100.csv"), [trade("2027-01-04", "NDX100", -1.0, -27.0), trade("2027-01-05", "NDX100", -1.0, -27.0)])
    chemin, _ = export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 4, 10))
    texte = open(os.path.join(chemin, "resume.md"), encoding="utf-8").read()
    assert "coupe le robot" not in texte and "à juger sur 60 jours de trade" in texte
    trades = [{"date": (datetime.date(2027, 1, 1) + datetime.timedelta(days=i)).isoformat(), "r": -1.0} for i in range(60)]
    assert export.interrupteur(trades, datetime.date(2027, 12, 31))["complet"]
    assert 'verdict = "SEUIL FRANCHI : "' in open(os.path.join(ICI, "export.py"), encoding="utf-8").read()


def test_interrupteur_marche_par_marche(tmp_path):
    """ET-16 : les seuils (calculés pour un marché) se jugent marché par marché. 60 jours à -0,6 R sur chacun : -36 R par marché,
    au-dessus du seuil de -40 R ; additionnés, -72 R auraient franchi le seuil du total à tort."""
    jours = [(datetime.date(2027, 1, 1) + datetime.timedelta(days=i)).isoformat() for i in range(60)]
    trades = [{"date": j, "symbole": s, "r": -0.6} for j in jours for s in ("NDX100", "SPX500")]
    par_marche = export.interrupteurs(trades, datetime.date(2027, 12, 31))
    assert set(par_marche) == {"NDX100", "SPX500"} and all(i["complet"] and "total" not in i["franchi"] for i in par_marche.values())
    assert "total" in export.interrupteur(trades, datetime.date(2027, 12, 31))["franchi"]       # l'ancienne addition
    dossier = str(tmp_path)
    ecrire(os.path.join(dossier, "trades-NDX100.csv"), [trade("2027-01-04", "NDX100", -1.0, -27.0)])
    ecrire(os.path.join(dossier, "trades-SPX500.csv"), [trade("2027-01-04", "SPX500", 0.5, 4.0)])
    chemin, _ = export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 4, 10))
    texte = open(os.path.join(chemin, "resume.md"), encoding="utf-8").read()
    assert "Interrupteur NDX100, sur ses 1 derniers jours" in texte and "Interrupteur SPX500" in texte


def test_date_du_jour_a_new_york():
    """ET-10 : la date de New York, pas celle de l'ordinateur (Paris, VPS), et sans zoneinfo (Windows sans tzdata)."""
    utc = lambda *a: datetime.datetime(*a, tzinfo=datetime.timezone.utc)
    assert export.aujourdhui_ny(utc(2027, 4, 1, 3, 0)) == datetime.date(2027, 3, 31)     # 23:00 à New York, heure d'été
    assert export.aujourdhui_ny(utc(2027, 1, 1, 4, 59)) == datetime.date(2026, 12, 31)   # 23:59 à New York, heure d'hiver
    assert export.aujourdhui_ny(utc(2027, 3, 14, 6, 59)) == datetime.date(2027, 3, 14)   # 1:59, juste avant le passage à l'heure d'été
    assert export.aujourdhui_ny(utc(2027, 11, 7, 4, 30)) == datetime.date(2027, 11, 7)   # 0:30, encore en heure d'été
    source = open(os.path.join(ICI, "export.py"), encoding="utf-8").read() + open(os.path.join(ICI, "etrave.py"), encoding="utf-8").read()
    assert "date.today()" not in source and "import zoneinfo" not in source and "from zoneinfo" not in source


def test_un_export_a_la_fois(dossier):
    """ET-12 : un double clic lançait deux exports sur le même dossier provisoire ; le renommage réessaie sous Windows."""
    resultats = []
    fils = [threading.Thread(target=lambda: resultats.append(export.exporter(dossier, "2027-T1", aujourdhui=datetime.date(2027, 4, 10))))
            for _ in range(3)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert len(resultats) == 3 and sorted(os.listdir(os.path.join(dossier, export.SOUS_DOSSIER))) == ["2027-T1"]
    source = open(os.path.join(ICI, "export.py"), encoding="utf-8").read()
    assert "with _VERROU_EXPORT:" in source and "_remplacer(provisoire, final)" in source and "os.replace(provisoire" not in source
    page = open(os.path.join(ICI, "page.html"), encoding="utf-8").read()
    assert "if (exportBusy) return;" in page
