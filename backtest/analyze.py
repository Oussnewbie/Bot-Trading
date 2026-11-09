import json
res = json.load(open("grid.json"))
M = ["NQ", "ES", "YM", "RTY", "GC", "6E"]
rows = []
for r in res:
    n = sum(r[m]["n"] for m in M)
    tot = sum(r[m]["total"] for m in M)
    pos = sum(r[m]["total"] > 0 for m in M)
    h1 = sum(r[m]["h1"] for m in M); h2 = sum(r[m]["h2"] for m in M)
    pday = sum(r[m]["pd"] for m in M)
    rows.append((r, n, tot, tot / n if n else 0, pos, h1, h2, pday))
def key(r):
    g = r[0]
    return f'{g["conf"]}{g["confMax"]} disp{g["disp"]} {"conso" if g["consume"] else "noconso"} {g["entry"]} biais={g["biasK"]} pd={int(g["pd"])} poches={g["poolsK"]}'
print("== robustes : positif sur >=5 marchés, 2 moitiés positives, >=60 trades au total ==")
ok = [x for x in rows if x[4] >= 5 and x[5] > 0 and x[6] > 0 and x[1] >= 60]
for x in sorted(ok, key=lambda x: -x[3])[:25]:
    print(f"{key(x):75s} n={x[1]:4d} ({x[7]:.2f}/j sur 6 marchés) exp={x[3]:+.2f}R tot={x[2]:+.1f}R pos={x[4]} h1={x[5]:+.1f} h2={x[6]:+.1f} NQ={x[0]['NQ']['total']:+.1f}/{x[0]['NQ']['n']}")
print(len(ok), "configs robustes sur", len(rows))
print("== meilleures par espérance, tous ==")
for x in sorted([x for x in rows if x[1] >= 60], key=lambda x: -x[3])[:10]:
    print(f"{key(x):75s} n={x[1]:4d} exp={x[3]:+.2f}R pos={x[4]} h1={x[5]:+.1f} h2={x[6]:+.1f}")
# effet moyen de chaque option
import collections
print("== effet moyen de chaque option (espérance moyenne, trades moyens) ==")
for f in ["conf", "confMax", "disp", "consume", "entry", "biasK", "pd", "poolsK"]:
    agg = collections.defaultdict(list)
    for x in rows:
        agg[x[0][f]].append((x[3], x[1]))
    print(f, {k: (round(sum(a for a, _ in v) / len(v), 3), round(sum(b for _, b in v) / len(v))) for k, v in agg.items()})
