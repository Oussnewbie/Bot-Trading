"""Regles communes a toute la recherche : periodes, registre des essais, calendrier FOMC, affichage."""
import os, json, numpy as np, pandas as pd, datetime as dt
import moteur as M, sim_chemins as SC

RECH_DEBUT = '2018-01-01'
RECH_FIN = '2024-12-31'      # la recherche s'arrete ici
COFFRE_DEBUT = '2025-01-01'  # coffre-fort : 2025-01-01 -> 2026-11-18, juge une seule fois a la fin
REG_DIR = SC.REGISTRE_DIR    # archive : dossier du bac a sable
REG_CSV = SC.REGISTRE_CSV    # ici donnees/, jamais le registre du depot (recherche/resultats/registre_essais.csv)

def rech(T):
    """Ne garde que la periode de recherche."""
    return T[(T.date >= RECH_DEBUT) & (T.date <= RECH_FIN)]
def coffre(T):
    return T[T.date >= COFFRE_DEBUT]

def enregistrer(D, nom, famille, params, T):
    """Inscrit un essai au registre : serie quotidienne de R (0 les jours sans trade) + mesures sur la periode de recherche seulement."""
    os.makedirs(REG_DIR, exist_ok=True)   # archive : fait a l'import
    v = np.zeros(D.nj)
    np.add.at(v, T.j.values.astype(int), T.r.values)
    np.save(f'{REG_DIR}/{nom}.npy', v)
    m = M.mesures(rech(T).r.values)
    row = dict(nom=nom, famille=famille, params=json.dumps(params, ensure_ascii=False), **{k: (round(x, 4) if isinstance(x, float) else x) for k, x in m.items()})
    df = pd.read_csv(REG_CSV) if os.path.exists(REG_CSV) else pd.DataFrame()
    if len(df) and nom in set(df.nom): df = df[df.nom != nom]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(REG_CSV, index=False)
    return m

def n_essais():
    return len(pd.read_csv(REG_CSV)) if os.path.exists(REG_CSV) else 0

def par_annee(T, col='r'):
    g = T.groupby('annee')[col]
    return pd.DataFrame({'n': g.size(), 'esp': g.mean(), 'total': g.sum(), 'gagnants': g.apply(lambda x: 100 * (x > 0.05).mean()),
                         'stops': g.apply(lambda x: 100 * (x <= -0.9).mean())}).round(3)

def ligne(nom, m):
    if m.get('n', 0) == 0: return f'{nom:42s} aucun trade'
    return (f"{nom:42s} n={m['n']:5d}  esp={m['esp']:+.3f}R  total={m['total']:+8.1f}R  gagnants={m['gagnants']:5.1f}%  stops={m['stops']:5.1f}%  "
            f"PF={m['pf']:.2f}  pire baisse={m['dd']:5.1f}R  pire serie={m['serie']:3d}  t={m['t']:.2f}")

# Jours de decision de la Fed (FOMC), reunions prevues a l'avance uniquement (les reunions d'urgence de mars 2020 sont exclues)
FOMC = ['2018-01-31','2018-03-21','2018-05-02','2018-06-13','2018-08-01','2018-09-26','2018-11-08','2018-12-19',
        '2019-01-30','2019-03-20','2019-05-01','2019-06-19','2019-07-31','2019-09-18','2019-10-30','2019-12-11',
        '2020-01-29','2020-04-29','2020-06-10','2020-07-29','2020-09-16','2020-11-05','2020-12-16',
        '2021-01-27','2021-03-17','2021-04-28','2021-06-16','2021-07-28','2021-09-22','2021-11-03','2021-12-15',
        '2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27','2022-09-21','2022-11-02','2022-12-14',
        '2023-02-01','2023-03-22','2023-05-03','2023-06-14','2023-07-26','2023-09-20','2023-11-01','2023-12-13',
        '2024-01-31','2024-03-20','2024-05-01','2024-06-12','2024-07-31','2024-09-18','2024-11-07','2024-12-18',
        '2025-01-29','2025-03-19','2025-05-07','2025-06-18','2025-07-30','2025-09-17','2025-10-29','2025-12-10',
        '2026-01-28','2026-03-18','2026-04-29','2026-06-17','2026-07-29','2026-09-16','2026-10-28','2026-12-09']
FOMC_SET = set(FOMC)
