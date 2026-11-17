import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np
import btc_backtest as BT
from btc_backtest import Frais
import btc
B = BT.charger(); E = btc.elements(B); idx = E["c4"].index
pos = btc.position(E, **btc.FINAL)
P = {"2012-07 → 2017": ("2012-07-01", "2018-01-01"), "2018 → 13/11/2026": ("2018-01-01", "2026-11-14"),
     "2022 → 13/11/2026": ("2022-01-01", "2026-11-14"), "après 13/11/2026": ("2026-11-14", None)}
def ligne(p, **kw):
    out = {}
    for k, (a, b) in P.items():
        r = BT.simuler(p, B, debut=a, fin=b, **kw); m = BT.mesures(r["eq"])
        out[k] = f"{m['cagr']:+.0%}/an Sh {m['sharpe']:.2f} dd {m['mdd']:.0%}" if k != "après 13/11/2026" else f"{m['fin']-1 if m['fin']==m['fin'] else (r['eq'].iloc[-1]/r['eq'].iloc[0]-1):+.2%}"
        if k == "2018 → 13/11/2026":
            out["expo moy 2018+"] = round(float(r["expo"].abs().mean()), 2); out["ordres/an"] = round(r["ordres_an"]); out["rotation/an"] = round(r["rotation_an"], 1)
    return out
T = {}
T["bot ×1 (prudent)"] = ligne(pos)
T["bot ×1 sans coupe-circuit"] = ligne(pos, coupe=0)
T["bot ×1 coûts ×0"] = ligne(pos, F=Frais(mult=0, avant2017=0))
T["bot ×1 coûts ×2"] = ligne(pos, F=Frais(mult=2, avant2017=0.007))
T["bot ×1 coûts ×3"] = ligne(pos, F=Frais(mult=3, avant2017=0.0105))
T["bot ×1 vente paie 10 %/an avant 2020"] = ligne(pos, F=Frais(fund_avant2020=-0.10))
T["bot ×1 sans bande"] = ligne(pos, bande=0.0)
T["bot équilibré (60 %)"] = ligne(btc.position(E, seuil=.25, confirmation="ema50/200", vente=.25, vol_cible=.6))
T["bot sans vente"] = ligne(btc.position(E, seuil=.25, confirmation="ema50/200", vente=0, vol_cible=.4))
T["achat et garde"] = ligne(BT.achat_garde(idx), coupe=0)
T["MA200 journalière (100 %)"] = ligne(BT.ma200(B, idx), coupe=0)
T["MA200 + même dosage vol 40 %"] = ligne(BT.ma200_vol(B, E, idx), coupe=0)
T["dosage vol 40 % seul (toujours acheteur)"] = ligne((0.4 / E["vol4"]).clip(upper=1).fillna(0), coupe=0)
T["EMA50/200 4h seule + dosage"] = ligne((E["conf"]["ema50/200"][0].astype(float) * (0.4 / E["vol4"]).clip(upper=1)).fillna(0), coupe=0)
T["votes seuls (sans tendance 4h)"] = ligne(btc.position(E, seuil=.25, confirmation="aucune", vente=.25, vol_cible=.4))
df = pd.DataFrame(T).T
pd.set_option("display.width", 250)
print(df.to_string())
pickle.dump(df, open("donnees/revue/btc_table.pkl", "wb"))
