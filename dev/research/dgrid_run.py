#!/usr/bin/env python
"""DGRID runner. Usage: dgrid_run.py {h4|d1}
h4: session-aware 4H from l4_h1 (2 buckets/day 09:15-12:15 / 12:15-15:30);
    F2 HTF = daily bars resampled from the same H1 (causal: prior sessions only).
d1: dailymax, NIFTY dropped, cut >= 2001-07-01 (25y, early-universe thin years
    excluded); F2 HTF = W-FRI weekly resample (zones usable after week close).
Per signal x geometry: real trade + matched drift null (same sym, same quarter,
same dir/geometry/costs, 5 draws).
"""
import sys, time
import numpy as np, pandas as pd
sys.path.insert(0, "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
from dgrid_lib import (atr_series, ob_lux, fvg_cb, breaker_msb, ifvg_zones,
                       fractal_swings, sweep_events, build_signals, sim_trade,
                       null_net, seed_of)

ROOT = "/home/doom/Public/PROJECT/2026/trader"
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
GEOMS = [(k, tgt, N, f"{tgt}Rx{N}") for k in (1.5, 2.5) for tgt, N in ((2, 10), (3, 20))]
FLOOR = {"h4": 0.0014, "d1": 0.002}   # ATR-eligibility floor (frac of close), LADDER values

def segments(g, minbars):
    """Splice guard (LADDER rule): cut at >25% close->open jumps; bad single-row
    spikes become 1-bar segments and are dropped; nothing spans a splice."""
    jump = (g.open / g.close.shift(1) - 1).abs() > 0.25
    for _, s in g.groupby(jump.cumsum()):
        if len(s) >= minbars:
            yield s

def htf_table(O, H, L, C, dates):
    zs = ob_lux(O, H, L, C) + fvg_cb(O, H, L, C)
    n = len(C); tbl = []
    for z in zs:
        if z["dir"] == 1:
            inv = next((t for t in range(z["ev_i"] + 1, n) if C[t] < z["lo"]), None)
        else:
            inv = next((t for t in range(z["ev_i"] + 1, n) if C[t] > z["hi"]), None)
        tbl.append((dates[z["ev_i"]], None if inv is None else dates[inv],
                    z["dir"], z["lo"], z["hi"]))
    return tbl

def load_arm(arm):
    """yield (sym, df[o,h,l,c,ts], period_id array, htf zone table, ltf_dates)."""
    if arm == "h4":
        h = pd.read_parquet(f"{ROOT}/runs/artifacts-data/l4_h1.parquet")
        h["date"] = h.ts.dt.date
        h["b"] = (h.ts.dt.hour >= 12).astype(int)
        h4 = (h.groupby(["symbol", "date", "b"], sort=False)
                .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                     close=("close", "last"), ts=("ts", "first")).reset_index()
                .sort_values(["symbol", "ts"]))
        dly = (h.groupby(["symbol", "date"], sort=False)
                 .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                      close=("close", "last")).reset_index().sort_values(["symbol", "date"]))
        for sym, g0 in h4.groupby("symbol"):
            gd0 = dly[dly.symbol == sym]
            for g in segments(g0, 120):
                gd = gd0[(gd0.date >= g.date.iloc[0]) & (gd0.date <= g.date.iloc[-1])]
                tbl = htf_table(gd.open.to_numpy(), gd.high.to_numpy(), gd.low.to_numpy(),
                                gd.close.to_numpy(), gd.date.tolist())
                dates = g.date.tolist()
                pid = np.array([d.toordinal() for d in dates])
                yield sym, g, pid, tbl, dates
    else:
        d = pd.read_parquet(f"{ROOT}/runs/artifacts-data/dailymax.parquet")
        d = d[(d.symbol != "NIFTY") & (d.date >= "2001-07-01")].sort_values(["symbol", "date"])
        d["ts"] = d.date
        for sym, g0 in d.groupby("symbol"):
          for g in segments(g0, 300):
            w = (g.set_index("date").resample("W-FRI")
                   .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                   .dropna(subset=["open"]))
            wd = [x.date() for x in w.index]
            tbl = htf_table(w.open.to_numpy(), w.high.to_numpy(), w.low.to_numpy(),
                            w.close.to_numpy(), wd)
            dates = [x.date() for x in g.date]
            iso = [x.isocalendar() for x in dates]
            pid = np.array([y * 54 + wk for y, wk, _ in iso])
            yield sym, g, pid, tbl, dates

def run(arm):
    t0 = time.time(); rows = []
    nsym = 0
    for sym, g, pid, tbl, dates in load_arm(arm):
        nsym += 1
        O, H, L, C = (g[c].to_numpy() for c in ("open", "high", "low", "close"))
        TS = g.ts.tolist(); n = len(O)
        atr = atr_series(H, L, C)
        atr[atr < FLOOR[arm] * C] = np.nan   # tiny-SL guard: real + null, symmetric
        fv = fvg_cb(O, H, L, C)
        zones = fv + ob_lux(O, H, L, C) + breaker_msb(O, H, L, C) + ifvg_zones(fv, H, L, C)
        sweeps = sweep_events(fractal_swings(H, L), H, L, C, atr)

        def live(t, d, mid, _tbl=tbl, _dt=dates):
            D = _dt[t]
            return any(ev < D and (iv is None or D <= iv) and zd == d and lo <= mid <= hi
                       for ev, iv, zd, lo, hi in _tbl)
        sigs = build_signals(O, H, L, C, atr, zones, sweeps, pid, live)

        qkey = [(t.year, (t.month - 1) // 3) for t in TS]
        pools = {}
        for i in range(15, n):
            if not np.isnan(atr[i - 1]) and atr[i - 1] > 0:
                pools.setdefault(qkey[i], []).append(i)
        pools = {q: np.array(v) for q, v in pools.items()}

        for e, d, a, typ, f1, f2, f3, f4 in sigs:
            for k, tgt, N, cfg in GEOMS:
                sd = k * a
                gr, cr = sim_trade(O, H, L, C, e, d, sd, tgt, N)
                nn, nv = null_net(O, H, L, C, atr, pools.get(qkey[e], []), e, d, k, tgt, N,
                                  seed_of(sym, typ, e, k, cfg), sd / O[e])
                rows.append((sym, typ, d, e, TS[e], k, cfg, f1, f2, f3, f4,
                             gr, cr, gr - cr, nn, nv))
        if nsym % 20 == 0:
            print(f"[{arm}] {nsym} syms, {len(rows)} trade-rows, {time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows, columns=["sym", "type", "dir", "e", "ts", "k", "cfg",
                                     "f1", "f2", "f3", "f4", "gross_R", "cost_R",
                                     "net_R", "null_net", "null_vol"])
    df.to_parquet(f"{SCR}/dgrid_trades_{arm}.parquet")
    print(f"[{arm}] DONE syms={nsym} rows={len(df)} sigs={len(df)//4} {time.time()-t0:.0f}s")

if __name__ == "__main__":
    run(sys.argv[1])
