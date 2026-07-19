"""Run taught-OB detection + entry-policy measurement across all 138 symbols (H1)."""
import time, numpy as np, pandas as pd
from tob_lib import run_symbol

DATA = "/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet"
OUT = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/"

df = pd.read_parquet(DATA)
syms = sorted(df.symbol.unique())
all_eps, metas, zcnt = [], {}, {}
t00 = time.time()
for i, sym in enumerate(syms):
    g = df[df.symbol == sym].sort_values("ts").reset_index(drop=True)
    if len(g) < 500: continue
    zones, eps, meta = run_symbol(g, sym)
    all_eps += eps
    metas[sym] = meta
    for z in zones:
        zcnt[z["type"]] = zcnt.get(z["type"], 0) + 1
    if i % 20 == 0:
        print(f"[{i}/{len(syms)}] {sym}: K={meta['K']:.1f} zones={len(zones)} "
              f"eps={len(eps)} elapsed={time.time()-t00:.0f}s", flush=True)

ep = pd.DataFrame(all_eps)
ep.to_parquet(OUT + "tob_episodes.parquet")
Ks = [m["K"] for m in metas.values()]
print(f"\ndone {time.time()-t00:.0f}s. episodes={len(ep)} zones={zcnt}")
print(f"K: median={np.median(Ks):.1f} min={min(Ks):.1f} max={max(Ks):.1f} "
      f"clipped_hi={sum(k >= 13.99 for k in Ks)} clipped_lo={sum(k <= 3.01 for k in Ks)}")
print(ep.groupby("type").size())
