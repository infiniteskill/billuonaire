"""rl_h1 -- H1 TARGET-R LADDER. Reuses asm_h1.run_symbol detection verbatim (patched econ
sweeps tgtR 2..10). Emits asm_h1 base COLS + per-tgtR ladder net/gross/win. Usage: rl_h1.py [nsyms]"""
import sys, time
from multiprocessing import Pool
import numpy as np, pandas as pd
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
import rl_lib as RL
import asm_h1 as H1


def _init():
    H1.load_df()          # sets H1._DF in worker
    RL.install()          # patch asm_sim.econ -> ladder


def _work(sym):
    RL.reset()
    g = H1._DF[H1._DF.symbol == sym].sort_values("ts").reset_index(drop=True)
    rows = H1.run_symbol(g, sym)
    assert len(rows) == len(RL.REAL), f"{sym}: rows {len(rows)} != ladder {len(RL.REAL)}"
    return rows, list(RL.REAL)


if __name__ == "__main__":
    syms = H1.load_df()
    if len(sys.argv) > 1:
        syms = syms[:int(sys.argv[1])]
    t0 = time.time()
    with Pool(8, initializer=_init) as p:
        res = p.map(_work, syms, chunksize=2)
    base, lads = [], []
    for rows, ld in res:
        base += rows; lads += ld
    ep = pd.DataFrame(base, columns=H1.COLS)
    for r in RL.TGTS:
        ep[f"lad{r}_net"] = [d[r][0] for d in lads]
        ep[f"lad{r}_gross"] = [d[r][1] for d in lads]
        ep[f"lad{r}_win"] = [d[r][2] for d in lads]
    ep["ts0"] = pd.to_datetime(ep["ts0"])
    ep["tt"] = np.where(ep.ts0 < H1.B1, 0, np.where(ep.ts0 < H1.B2, 1, 2))
    ep.to_parquet(f"{SCR}/rl_h1_trades.parquet")
    # sanity: ladder tgtR=2 must equal the frozen econ t2
    d = (ep.lad2_net - ep.t2_net).abs().max()
    print(f"H1 LADDER: {len(syms)} syms, {len(ep)} eps, {time.time()-t0:.0f}s  |lad2-t2|max={d:.2e}")
    for r in RL.TGTS:
        print(f"  tgt {r}R: hit={100*ep[f'lad{r}_win'].mean():.1f}%  net={ep[f'lad{r}_net'].mean():+.4f}  gross={ep[f'lad{r}_gross'].mean():+.4f}")
