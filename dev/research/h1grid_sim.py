#!/usr/bin/env python
"""h1grid step 2: simulate every trade + matched drift null under 4 geometries.

Geometry: stop k in {1.5,2.5} x ATR(14,TF at retest bar); exits (2R tgt, 10-sess
time-stop) and (1.5R tgt, 5-sess time-stop). Entry next-bar open, fade direction.
Conservative intrabar order: time-stop at open -> gap-through fill at open
(mandatory) -> stop before target. Splice guard: force-exit at close of bar
before any >20% close->open jump (applied to real and null alike).
Costs (delivery, RS1L capital, 0.5% risk sizing): STT 0.1% both legs, exch
0.004% both legs, DP RS15/sell, slip 2bp/leg (in price). qty = min(500/stop,
1L/entry) floored; qty=0 -> skipped (both arms).
Null: per real trade, NDRAW random entry bars from the same symbol+calendar
month, same direction/geometry/costs; cell null = mean over draws.
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

bars = pd.read_parquet(f"{SCRATCH}/h1grid_bars_{TF}.parquet")
trades = pd.read_parquet(f"{SCRATCH}/h1grid_trades_{TF}.parquet")

def simulate(A, e, d, k, rmult, nsess):
    """A = (O,H,L,C,ATR,SESS,SPLICE,n). Returns net_R or None (skip)."""
    O, H, L, C, ATR, SESS, SPL, n = A[:8]
    a = ATR[e - 1]
    if not (a > 0):
        return None
    sd = k * a
    ent_raw = O[e]
    qty = min(math.floor(RISK / sd), math.floor(CAP / ent_raw)) if ent_raw > 0 else 0
    if qty < 1:
        return None
    ent = ent_raw * (1 + SLIP * d)          # entry slip against
    stop = ent - d * sd
    tgt = ent + d * rmult * sd
    s0 = SESS[e]
    exit_px = None
    t = e
    while t < n:
        if t > e and SPL[t]:                # splice ahead: already exited at t-1 close
            break
        o, h, l = O[t], H[t], L[t]
        if SESS[t] - s0 >= nsess:           # time-stop: out at this open
            exit_px = o; break
        if t > e:                           # gap-through at open (mandatory)
            if (d == 1 and o <= stop) or (d == -1 and o >= stop):
                exit_px = o; break
            if (d == 1 and o >= tgt) or (d == -1 and o <= tgt):
                exit_px = o; break
        if (d == 1 and l <= stop) or (d == -1 and h >= stop):   # stop first
            exit_px = stop; break
        if (d == 1 and h >= tgt) or (d == -1 and l <= tgt):
            exit_px = tgt; break
        if t + 1 < n and SPL[t + 1]:        # force-exit before splice
            exit_px = C[t]; break
        t += 1
    if exit_px is None:
        exit_px = C[n - 1]
    exit_px *= (1 - SLIP * d)               # exit slip against
    pnl = d * (exit_px - ent) * qty
    buy_n = qty * (ent if d == 1 else exit_px)
    sell_n = qty * (exit_px if d == 1 else ent)
    costs = 0.001 * (buy_n + sell_n) + 0.00004 * (buy_n + sell_n) + 15.0
    return (pnl - costs) / (qty * sd)

# per-symbol arrays + per-month eligible entry bars
arrs, elig = {}, {}
for sym, b in bars.groupby("symbol"):
    b = b.sort_values("i")
    atrv = b.atr.values
    A = (b.open.tolist(), b.high.tolist(), b.low.tolist(), b.close.tolist(),
         atrv.tolist(), b.sess.tolist(), b.splice.tolist(), len(b))
    arrs[sym] = A
    mo = b.ts.dt.year.values * 100 + b.ts.dt.month.values
    ok = np.zeros(len(b), bool)
    ok[1:] = ~np.isnan(atrv[:-1]) & (atrv[:-1] > 0)   # need ATR at e-1
    ok &= ~b.splice.values                            # no entries on a splice bar
    for m in np.unique(mo):
        idx = np.where((mo == m) & ok)[0]
        elig[(sym, m)] = idx
    arrs[sym] += (np.cumsum(b.splice.values).tolist(),)  # A[8] = splice cumsum

rows = []
rng = np.random.default_rng(7)
for gi, (k, rmult, nsess) in enumerate(GEOMS):
    skipped = 0
    for r in trades.itertuples():
        A = arrs[r.symbol]
        if A[8][r.entry_i] != A[8][r.born_i] or A[6][r.entry_i]:
            skipped += 1          # zone born across a splice / entry on splice bar
            continue
        real = simulate(A, r.entry_i, r.dir, k, rmult, nsess)
        if real is None:
            skipped += 1
            continue
        m = r.entry_ts.year * 100 + r.entry_ts.month
        pool = elig[(r.symbol, m)]
        # deterministic per-trade seed so all geoms/subsets share null draws
        trng = np.random.default_rng(
            zlib.crc32(f"{r.symbol}|{r.entry_i}|{r.dir}".encode()) + gi)
        draws = pool[trng.integers(0, len(pool), NDRAW)] if len(pool) else []
        nulls = [x for e2 in draws
                 if (x := simulate(A, int(e2), r.dir, k, rmult, nsess)) is not None]
        if not nulls:
            skipped += 1
            continue
        rows.append(dict(symbol=r.symbol, ztype=r.ztype, dir=r.dir, geom=gi,
                         entry_ts=r.entry_ts, F1=r.F1, F2=r.F2, F3=r.F3, F4=r.F4,
                         symhalf=r.symhalf, net_R=real, null_R=float(np.mean(nulls))))
    print(f"geom {gi} (k={k} r={rmult} ns={nsess}): done, skipped={skipped}", flush=True)

res = pd.DataFrame(rows)
res.to_parquet(f"{SCRATCH}/h1grid_res_{TF}.parquet")
print(f"TOTAL {TF}: rows={len(res)}")
print(res.groupby("geom")[["net_R", "null_R"]].mean())
