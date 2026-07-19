"""rl_daily -- DAILY TARGET-R LADDER. Reuses asm_daily.run_symbol detection verbatim; patches
asm_sim.econ AND asm_daily._null_net so BOTH the real system and the matched-drift null sweep
tgtR 2..10. Emits asm_daily base COLS + per-tgtR real net/gross/win + per-tgtR null net.
Usage: rl_daily.py [nsyms]"""
import sys, time
from multiprocessing import Pool
import numpy as np, pandas as pd
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
sys.path.insert(0, "/home/doom/Public/PROJECT/2026/trader/dev/research")
import rl_lib as RL
import asm_daily as AD


def _init():
    AD.load_df()                          # sets AD._DF in worker
    RL.install()                          # patch asm_sim.econ -> ladder
    AD._null_net = RL.make_null_ladder()  # patch daily null -> ladder null


def _work(sym):
    RL.reset()
    g = AD._DF[AD._DF.symbol == sym].sort_values("ts").reset_index(drop=True)
    rows = AD.run_symbol(g, sym)
    assert len(rows) == len(RL.REAL), f"{sym}: rows {len(rows)} != real {len(RL.REAL)}"
    assert len(rows) == len(RL.NULL), f"{sym}: rows {len(rows)} != null {len(RL.NULL)}"
    return rows, list(RL.REAL), list(RL.NULL)


if __name__ == "__main__":
    syms = AD.load_df()
    if len(sys.argv) > 1:
        syms = syms[:int(sys.argv[1])]
    t0 = time.time()
    with Pool(8, initializer=_init) as p:
        res = p.map(_work, syms, chunksize=2)
    base, reals, nulls = [], [], []
    for rows, rl, nl in res:
        base += rows; reals += rl; nulls += nl
    ep = pd.DataFrame(base, columns=AD.COLS)
    for r in RL.TGTS:
        ep[f"lad{r}_net"] = [d[r][0] for d in reals]
        ep[f"lad{r}_gross"] = [d[r][1] for d in reals]
        ep[f"lad{r}_win"] = [d[r][2] for d in reals]
        ep[f"nul{r}_net"] = [d[r] for d in nulls]
    ep["ts0"] = pd.to_datetime(ep["ts0"])
    q = ep["ts0"].quantile([1/3, 2/3]).values
    ep["tt"] = np.where(ep.ts0 < q[0], 0, np.where(ep.ts0 < q[1], 1, 2))
    ep.to_parquet(f"{SCR}/rl_daily_trades.parquet")
    d1 = (ep.lad2_net - ep.t2_net).abs().max()
    d2 = (ep.nul2_net - ep.null_t2_net).abs().max()
    print(f"DAILY LADDER: {len(syms)} syms, {len(ep)} eps, {time.time()-t0:.0f}s  |lad2-t2|={d1:.2e} |nul2-null_t2|={d2:.2e}")
    for r in RL.TGTS:
        ex = (ep[f'lad{r}_net'] - ep[f'nul{r}_net']).mean()
        print(f"  tgt {r}R: hit={100*ep[f'lad{r}_win'].mean():.1f}%  net={ep[f'lad{r}_net'].mean():+.4f}  null={ep[f'nul{r}_net'].mean():+.4f}  EXCESS={ex:+.4f}")
