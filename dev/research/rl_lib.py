"""rl_lib -- TARGET-R LADDER: sweep the fixed-target multiple tgtR in {2..10} over the
ASSEMBLED taught system WITHOUT rebuilding detection. Monkeypatches asm_sim.econ (and,
for daily, asm_daily._null_net) so the EXACT same zone build (asm_h1/asm_daily.run_symbol)
runs; only the exit target is swept. Geometry is reused verbatim: econ already fixes the
edge-entry fill fp and the zone-height/1.5xATR stop distance sd, hence stop = fp - d*sd and
tgt = fp + d*tgtR*sd -- identical to asm_sim's own target construction. Per-episode ladder
outcomes are stashed 1:1 with run_symbol's rows (every non-None econ -> exactly one row)."""
import sys
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
RES = "/home/doom/Public/PROJECT/2026/trader/dev/research"
sys.path.insert(0, SCR); sys.path.insert(0, RES)
import numpy as np
import asm_sim as S

TGTS = [2, 3, 4, 5, 6, 7, 8, 9, 10]
_orig_econ = S.econ
REAL = []   # per-episode dict {tgtR: (net, gross, win)}  (real system)
NULL = []   # per-episode dict {tgtR: null_net_mean}       (daily matched-drift null)


def econ_ladder(O, H, L, C, atr, t0, d, E, F, N):
    """wraps the frozen econ (unchanged geometry), then walks every tgtR to fixed target."""
    ec = _orig_econ(O, H, L, C, atr, t0, d, E, F, N)
    if ec is None:
        return None
    fp, sd = ec["fp"], ec["sd"]
    stop = fp - d * sd
    lad = {}
    for r in TGTS:
        tgt = fp + d * r * sd
        ex, win, _ = S._walk(O, H, L, C, t0, d, fp, stop, tgt, N)
        net, gross = S._acct(fp, ex, d, sd)
        lad[r] = (float(net), float(gross), bool(win))
    REAL.append(lad)
    return ec


def make_null_ladder():
    """daily matched-drift null swept over tgtR. Same rng draws (one integers() per draw)
    as asm_daily._null_net, so tgtR=2 reproduces the original null_t2_net exactly."""
    import asm_daily as AD

    def null_ladder(O, H, L, C, atr, n, d, sd_pct, pool, rng):
        acc = {r: 0.0 for r in TGTS}
        tr = 0.0
        m = 0
        for _ in range(AD.NULL_DRAWS):
            u = int(pool[rng.integers(len(pool))])
            fp = O[u]
            if fp <= 0:
                continue
            sd = sd_pct * fp
            if sd <= 0:
                continue
            stop = fp - d * sd
            for r in TGTS:
                tgt = fp + d * r * sd
                ex, win, _ = S._walk(O, H, L, C, u, d, fp, stop, tgt, AD.N_TRADE)
                nt, _ = S._acct(fp, ex, d, sd)
                acc[r] += nt
            ex2, _, _ = S._trail(O, H, L, C, u, d, fp, stop, sd, AD.N_TRADE)
            ntr, _ = S._acct(fp, ex2, d, sd)
            tr += ntr
            m += 1
        if m:
            NULL.append({r: acc[r] / m for r in TGTS})
            return acc[2] / m, tr / m, m
        NULL.append({r: np.nan for r in TGTS})
        return np.nan, np.nan, 0

    return null_ladder


def install():
    S.econ = econ_ladder


def reset():
    REAL.clear(); NULL.clear()
