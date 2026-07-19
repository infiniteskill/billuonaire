#!/usr/bin/env python
"""h1grid step 2b: time-local null (variant B) — robustness check on the
month-matched null. For each real trade, 5 random entry bars drawn from the
trade's own forward window [entry, entry + 10 sessions], same direction,
geometry, costs. This removes the within-month path-selection bias (zone
retests happen after the adverse leg of the month; month-uniform nulls sit
inside it). Excess_B measures pure entry-bar timing skill.
"""
import sys, math, zlib
import numpy as np
import pandas as pd

SCRATCH = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
TF = sys.argv[1]
NDRAW = 5
SLIP = 0.0002
CAP, RISK = 100_000.0, 500.0
GEOMS = [(k, r, ns) for k in (1.5, 2.5) for r, ns in ((2.0, 10), (1.5, 5))]
WSESS = 10  # forward draw window, sessions

bars = pd.read_parquet(f"{SCRATCH}/h1grid_bars_{TF}.parquet")
trades = pd.read_parquet(f"{SCRATCH}/h1grid_trades_{TF}.parquet")
uniq = trades[["symbol", "entry_i", "entry_ts", "dir"]].drop_duplicates()

def simulate(A, e, d, k, rmult, nsess):
    O, H, L, C, ATR, SESS, SPL, n = A[:8]
    a = ATR[e - 1]
    if not (a > 0):
        return None
    sd = k * a
    ent_raw = O[e]
    qty = min(math.floor(RISK / sd), math.floor(CAP / ent_raw)) if ent_raw > 0 else 0
    if qty < 1:
        return None
    ent = ent_raw * (1 + SLIP * d)
    stop = ent - d * sd
    tgt = ent + d * rmult * sd
    s0 = SESS[e]
    exit_px = None
    t = e
    while t < n:
        if t > e and SPL[t]:
            break
        o, h, l = O[t], H[t], L[t]
        if SESS[t] - s0 >= nsess:
            exit_px = o; break
        if t > e:
            if (d == 1 and o <= stop) or (d == -1 and o >= stop):
                exit_px = o; break
            if (d == 1 and o >= tgt) or (d == -1 and o <= tgt):
                exit_px = o; break
        if (d == 1 and l <= stop) or (d == -1 and h >= stop):
            exit_px = stop; break
        if (d == 1 and h >= tgt) or (d == -1 and l <= tgt):
            exit_px = tgt; break
        if t + 1 < n and SPL[t + 1]:
            exit_px = C[t]; break
        t += 1
    if exit_px is None:
        exit_px = C[n - 1]
    exit_px *= (1 - SLIP * d)
    pnl = d * (exit_px - ent) * qty
    buy_n = qty * (ent if d == 1 else exit_px)
    sell_n = qty * (exit_px if d == 1 else ent)
    costs = 0.001 * (buy_n + sell_n) + 0.00004 * (buy_n + sell_n) + 15.0
    return (pnl - costs) / (qty * sd)

arrs = {}
for sym, b in bars.groupby("symbol"):
    b = b.sort_values("i")
    atrv = b.atr.values
    ok = np.zeros(len(b), bool)
    ok[1:] = ~np.isnan(atrv[:-1]) & (atrv[:-1] > 0)
    ok &= ~b.splice.values
    arrs[sym] = (b.open.tolist(), b.high.tolist(), b.low.tolist(), b.close.tolist(),
                 atrv.tolist(), b.sess.tolist(), b.splice.tolist(), len(b),
                 np.cumsum(b.splice.values).tolist(), ok, np.asarray(b.sess.values))

rows = []
for gi, (k, rmult, nsess) in enumerate(GEOMS):
    for r in uniq.itertuples():
        A = arrs[r.symbol]
        okm, sessv, n = A[9], A[10], A[7]
        e = int(r.entry_i)
        # forward window: bars e+1..last bar within e's session + WSESS
        hi = int(np.searchsorted(sessv, sessv[e] + WSESS, side="right"))
        cand = np.arange(e + 1, min(hi, n))
        cand = cand[okm[cand] & (np.asarray(A[8])[cand] == A[8][e])]
        if len(cand) == 0:
            continue
        trng = np.random.default_rng(
            zlib.crc32(f"B|{r.symbol}|{e}|{r.dir}".encode()) + gi)
        draws = cand[trng.integers(0, len(cand), NDRAW)]
        nulls = [x for e2 in draws
                 if (x := simulate(A, int(e2), r.dir, k, rmult, nsess)) is not None]
        if not nulls:
            continue
        rows.append(dict(symbol=r.symbol, entry_ts=r.entry_ts, dir=r.dir, geom=gi,
                         nullB_R=float(np.mean(nulls))))
    print(f"geom {gi}: done", flush=True)

out = pd.DataFrame(rows)
out.to_parquet(f"{SCRATCH}/h1grid_nullb_{TF}.parquet")
print(f"TOTAL {TF}: rows={len(out)}")
print(out.groupby("geom").nullB_R.mean())
