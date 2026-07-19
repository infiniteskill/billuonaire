#!/usr/bin/env python
"""h1grid step 1: build zones + elimination flags + first-retest per symbol per TF.

Zone types: FVG, OB (wick-touch retest, close-beyond-far-edge kill), BREAKER
(EmreKb fired = close back inside box), iFVG (FVG close-invalidated then wick-
retested from the other side; trade direction flips).
Flags: F1 born>=1 session before retest; F2 zone nested in live same-direction
D1 OB/FVG at retest date (causal: D1 zone from completed dailies only);
F3 zone ev within <=3 bars after direction-aligned EQ-pool sweep;
F4 zone born on session-open bar.
Outputs: h1grid_trades_{tf}.parquet, h1grid_bars_{tf}.parquet.
"""
import sys, zlib
import numpy as np
import pandas as pd

SCRATCH = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCRATCH)
from h1grid_lib import (atr_series, ob_lux, fvg_cb, fractal_swings, breaker_msb,
                        sweep_events, first_touch, invalidation_bar, to_2h,
                        to_daily, d1_zones)

TF = sys.argv[1]  # h1 | h2
assert TF in ("h1", "h2")
DATA = "/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet"

raw = pd.read_parquet(DATA).sort_values(["symbol", "ts"]).reset_index(drop=True)
symbols = sorted(raw.symbol.unique())

bar_rows, trade_rows = [], []
for sym in symbols:
    d = raw[raw.symbol == sym].reset_index(drop=True)
    df = d if TF == "h1" else to_2h(d)
    O, H, L, C = (df[c].tolist() for c in ("open", "high", "low", "close"))
    ts = df.ts.tolist()
    n = len(df)
    atr = atr_series(H, L, C)
    dates = [t.date() for t in ts]
    udates = sorted(set(dates))
    dord = {dt: k for k, dt in enumerate(udates)}
    sess = [dord[dt] for dt in dates]
    sopen = [i == 0 or dates[i] != dates[i - 1] for i in range(n)]
    # splice guard: close->open jump >20% => segment boundary at bar i (open side)
    splice = [False] * n
    for i in range(1, n):
        if C[i - 1] and abs(O[i] / C[i - 1] - 1) > 0.20:
            splice[i] = True

    # ---- context: sweeps, D1 zones
    sw = fractal_swings(H, L, 5)
    sweeps = sweep_events(sw, H, L, C, atr)
    sw_by_side = {1: sorted(t for t, s in sweeps if s == 1),
                  -1: sorted(t for t, s in sweeps if s == -1)}
    dz = d1_zones(to_daily(d))  # always from the same H1 data's dailies

    # ---- zones
    zones = []
    fvgs = fvg_cb(O, H, L, C)
    obs = ob_lux(O, H, L, C)
    brks = breaker_msb(O, H, L, C)
    for z in fvgs + obs:
        t = first_touch(z, H, L, z["ev_i"] + 1)
        if t is None:
            continue
        zones.append(dict(z, retest_i=t, tdir=z["d"]))
    for b in brks:  # fired = close back inside box = the retest
        zones.append(dict(b, tdir=b["d"]))
    for z in fvgs:  # iFVG: close-invalidated FVG, retested from the other side
        k = invalidation_bar(z, C, z["ev_i"] + 1)
        if k is None:
            continue
        nd = -z["d"]
        lo, hi = z["lo"], z["hi"]
        t = None
        for u in range(k + 1, n):  # wick back into zone; dead if close beyond new far edge
            if (nd == -1 and C[u] > hi) or (nd == 1 and C[u] < lo):
                break
            if L[u] <= hi and H[u] >= lo:
                t = u; break
        if t is None:
            continue
        zones.append(dict(kind="IFVG", d=nd, lo=lo, hi=hi, born_i=k, ev_i=k,
                          retest_i=t, tdir=nd))

    # ---- flags + trade rows
    for z in zones:
        rt = z["retest_i"]
        e = rt + 1  # entry bar
        if e >= n or atr[rt] is None:
            continue
        d1ok = False
        rd = dates[rt]
        for dzz in dz:
            if dzz["d"] != z["tdir"] or dzz["ev_date"] >= rd:
                continue
            if dzz["inv_date"] is not None and dzz["inv_date"] < rd:
                continue
            if z["lo"] >= dzz["lo"] and z["hi"] <= dzz["hi"]:
                d1ok = True; break
        ev = z["ev_i"]
        al = sw_by_side[z["tdir"]]
        j = np.searchsorted(al, ev, side="right") - 1
        f3 = j >= 0 and ev - al[j] <= 3
        trade_rows.append(dict(
            symbol=sym, ztype=z["kind"], dir=z["tdir"], lo=z["lo"], hi=z["hi"],
            born_i=z["born_i"], ev_i=ev, retest_i=rt, entry_i=e,
            entry_ts=ts[e], entry_sess=sess[e],
            F1=sess[rt] - sess[z["born_i"]] >= 1, F2=d1ok, F3=bool(f3),
            F4=bool(sopen[z["born_i"]]),
            symhalf=zlib.crc32(sym.encode()) % 2))
    bd = pd.DataFrame(dict(symbol=sym, i=range(n), ts=ts, open=O, high=H, low=L,
                           close=C, atr=[a if a is not None else np.nan for a in atr],
                           sess=sess, splice=splice))
    bar_rows.append(bd)
    print(f"{sym}: bars={n} fvg={len(fvgs)} ob={len(obs)} brk={len(brks)} "
          f"trades={sum(1 for r in trade_rows if r['symbol']==sym)}", flush=True)

bars = pd.concat(bar_rows, ignore_index=True)
trades = pd.DataFrame(trade_rows)
bars.to_parquet(f"{SCRATCH}/h1grid_bars_{TF}.parquet")
trades.to_parquet(f"{SCRATCH}/h1grid_trades_{TF}.parquet")
print(f"\nTOTAL {TF}: trades={len(trades)}")
print(trades.groupby("ztype").size())
print(trades[["F1", "F2", "F3", "F4"]].mean())
