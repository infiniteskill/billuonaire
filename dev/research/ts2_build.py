"""ts2 build: run all symbols -> episodes parquet + zone-count csv."""
import sys, time
import numpy as np, pandas as pd
sys.path.insert(0, "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
import ts2_lib as T

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
df = pd.read_parquet("/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet")
syms = sorted(df["symbol"].unique())
if len(sys.argv) > 1: syms = syms[:int(sys.argv[1])]

rows, cnts, unres = [], {}, 0
t0 = time.time()
for k, s in enumerate(syms):
    g = df[df["symbol"] == s].sort_values("ts").reset_index(drop=True)
    r, c, u = T.run_symbol(g, s)
    rows += r; unres += u
    for ty, v in c.items(): cnts[ty] = cnts.get(ty, 0) + v
    print(f"[{k+1}/{len(syms)}] {s} eps={len(r)} t={time.time()-t0:.0f}s", flush=True)

ep = pd.DataFrame(rows, columns=T.COLS)
ep.to_parquet(f"{SCR}/ts2_eps.parquet")
pd.Series(cnts).to_csv(f"{SCR}/ts2_zone_counts.csv")
print("zones:", cnts)
print("episodes:", len(ep), "unresolved:", unres)
