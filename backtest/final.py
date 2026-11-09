from best import *
F = {**B, "tgt": "liq", "pm": True, "pools": ("asia", "pd", "lon", "ny")}
print("---- combinaisons")
agg(F, "v2 finale (liq + après-midi)", show=True)
agg({**F, "pools": ("asia", "pd")}, "v2 finale, poches Asie + veille", show=True)
agg({**F, "maxLoss": 1}, "v2 finale, 1 perte max")
# moitiés et par mois
import pandas as pd
rs = []
for k in T:
    sim.SLIP = 2 * T[k]
    tr, st, n = run(D[k], F)
    rs += [(t["tsig"], k, t["rr"]) for t in tr]
df = pd.DataFrame(rs, columns=["t", "m", "r"])
df["mois"] = df.t.apply(lambda x: x.strftime("%Y-%m"))
print(df.groupby("mois").r.agg(["count", "sum", "mean"]).round(2))
print(df.groupby("m").r.agg(["count", "sum", "mean"]).round(2))
