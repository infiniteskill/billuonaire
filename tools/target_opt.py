"""target_opt.py — WHAT TARGET DISTANCE ACTUALLY PAYS (offline, no re-derive).

The detector's target choice was measured wrong twice: nearest-opposite-extreme
gives sub-1R draws (costs eat them), range-extreme gives ~120R draws (never hit).
The user's own marks sit at 6-14.5R. Rather than guess a level-picking rule, this
sweeps the target DISTANCE directly (in R) over the honest taught race, so the rule
can then be built to hit the measured optimum.

Same honest machinery as trail_opt: mid-of-zone limit must be TOUCHED, SL = sl_h x H,
SL-first on the fill bar, exact Zerodha intraday costs, optional BE-at-cost + trail.

load()/race() are importable so robustness tests share one sim (see robust.py).
race() returns one slot per SIG entry, so results align across configs.

Usage: python3 tools/target_opt.py <tradebook.csv> <data_dir> [sl_h]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
CFG = json.loads((ROOT / "runs/validate/taught_meas/config.json").read_text())
CAP = float(CFG["capital"]); RISK_PCT = float(CFG["risk"]["per_trade_pct"])
LEV = float(CFG["risk"].get("leverage", 5.0))
BUDGET = CAP * RISK_PCT / 100
SESSION = 375
SL_H = 0.7
BARS, DR, SIG = {}, {}, []
GRADE = []          # grade per SIG entry, parallel list (see grade_sep.py)


def cost_per_share(px, qty):
    t = px * qty
    brok = 2 * min(20.0, 0.0003 * t)
    return (brok + 0.00025 * t + 0.0000297 * 2 * t + 0.000001 * 2 * t + 0.00003 * t
            + 0.18 * (brok + 0.0000297 * 2 * t)) / qty


def load(tb_path, data_dir, sl_h=0.7, min_grade=5):
    """Read tradebook + bars, precompute every tradeable signal. Returns len(SIG).

    Signals that can never be traded (zero-height zone, qty<1, no room in the
    tape) are dropped here rather than mid-race, so race() output stays aligned
    with SIG and fill% means "limit touched", not "was tradeable at all"."""
    global SL_H, SIG, GRADE
    SL_H = sl_h
    tb = pd.read_csv(tb_path)
    k = (tb.sym + "|" + tb.entry.round(1).astype(str) + "|" + tb.sl.round(1).astype(str)
         + "|" + tb.target.round(1).astype(str))
    tb = tb.assign(_k=k).drop_duplicates(["mode", "_k"])
    s = tb[(tb["mode"] == "eod") & tb.zone_lo.notna() & (tb.grade >= min_grade)].copy()
    s["ts"] = pd.to_datetime(s["ts"]).dt.tz_localize(None)
    for sym in s.sym.unique():
        if sym in BARS:
            continue
        d = pd.read_csv(f"{data_dir}/{sym}.csv", parse_dates=["ts"])
        tsv = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
        day = tsv.dt.normalize().values
        g = pd.DataFrame({"d": day, "h": d.high.values, "l": d.low.values}).groupby("d").agg(
            h=("h", "max"), l=("l", "min"))
        DR[sym] = float((g.h - g.l).median())
        BARS[sym] = (tsv.values, d.high.values, d.low.values, d.close.values,
                     (tsv.dt.hour * 60 + tsv.dt.minute).values, day)
    SIG, GRADE = [], []
    for t in s.itertuples():
        tsv, hi, lo, cl, mins, day = BARS[t.sym]
        zlo, zhi = float(min(t.zone_lo, t.zone_hi)), float(max(t.zone_lo, t.zone_hi))
        entry, risk = (zlo + zhi) / 2, sl_h * (zhi - zlo)
        if risk <= 0:
            continue
        qty = int(min(BUDGET // risk, (CAP * LEV) // entry))
        n = len(tsv)
        ts = np.datetime64(t.ts)
        i = int(np.searchsorted(tsv, ts))
        if qty < 1 or i <= 0 or i >= n - 2:
            continue
        se = i
        while se < n and day[se] == day[i]:
            se += 1
        SIG.append((t.sym, t.dir == "LONG", entry, risk,
                    cost_per_share(entry, qty), i, se, ts))
        GRADE.append(int(t.grade))
    return len(SIG)


def race(tgt_R, be_R, trail_frac, hold_days):
    """tgt_R: target distance in R (None = pure trail). be_R: BE trigger in R
    (None = no BE; BE price = entry + cost). trail_frac x daily range.
    One slot per SIG: None = limit never touched, else net R after costs."""
    out = []
    for sym, long, entry, risk, cps, i, se, _ts in SIG:
        tsv, hi, lo, cl, mins, day = BARS[sym]
        n = len(tsv)
        fill = -1
        for x in range(i, min(se, n)):
            if mins[x] >= 15 * 60 + 10:
                break
            if lo[x] <= entry <= hi[x]:
                fill = x
                break
        if fill < 0:
            out.append(None)
            continue
        stop = entry - risk if long else entry + risk
        tgt = (entry + tgt_R * risk if long else entry - tgt_R * risk) if tgt_R else None
        be_px = entry + cps if long else entry - cps
        tdist = trail_frac * DR[sym] if trail_frac else 0.0
        best = entry
        limit = min(n, se if hold_days == 0 else fill + 1 + hold_days * SESSION)
        if (lo[fill] <= stop) if long else (hi[fill] >= stop):
            out.append(-1.0 - cps / risk)
            continue
        g = None
        for x in range(fill + 1, limit):
            if hold_days == 0 and mins[x] >= 15 * 60 + 10:
                g = (cl[x] - entry) / risk * (1 if long else -1); break
            if (lo[x] <= stop) if long else (hi[x] >= stop):
                g = (stop - entry) / risk * (1 if long else -1); break
            if tgt is not None and ((hi[x] >= tgt) if long else (lo[x] <= tgt)):
                g = tgt_R; break
            fav = (hi[x] - entry) if long else (entry - lo[x])
            best = max(best, hi[x]) if long else min(best, lo[x])
            if be_R is not None and fav >= be_R * risk:
                stop = max(stop, be_px) if long else min(stop, be_px)
                if tdist:
                    tr = best - tdist if long else best + tdist
                    stop = max(stop, tr) if long else min(stop, tr)
        if g is None:
            g = (cl[limit - 1] - entry) / risk * (1 if long else -1)
        out.append(g - cps / risk)
    return out


def show(res, label):
    f = np.array([r for r in res if r is not None])
    if not len(f):
        print(f"{label:44} n=0"); return -99
    print(f"{label:44} fill={100*len(f)/len(res):3.0f}% win={100*(f>0.02).mean():5.1f}% "
          f"meanR={f.mean():+6.3f} medR={np.median(f):+6.2f} totR={f.sum():+8.0f}")
    return f.mean()


if __name__ == "__main__":
    n = load(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.7)
    print(f"signals(grade>=5): {n}   sl_h={SL_H}")

    print("\n=== TARGET DISTANCE (no BE, no trail, intraday) ===")
    for tr in [1, 2, 3, 5, 8, 12, 20]:
        show(race(tr, None, 0, 0), f"target={tr}R")
    print("\n=== TARGET DISTANCE (no BE, no trail, 5-day hold) ===")
    for tr in [3, 5, 8, 12, 20]:
        show(race(tr, None, 0, 5), f"target={tr}R hold5d")
    print("\n=== + BE at cost, trigger swept (target=best-ish 8R, intraday) ===")
    for be in [None, 0.5, 1.0, 2.0, 3.0]:
        show(race(8, be, 0, 0), f"target=8R BE@{be}R")
    print("\n=== PURE TRAIL (no target) ===")
    for tf in [0.15, 0.3, 0.5, 1.0]:
        for be in [1.0, 2.0]:
            show(race(None, be, tf, 5), f"trail={tf}xDR BE@{be}R hold5d")
    print("\n=== best-of grid (target x BE x trail, 5-day) ===")
    best = (-99, None)
    for tr in [3, 5, 8, 12]:
        for be in [None, 1.0, 2.0]:
            for tf in [0, 0.3]:
                m = show(race(tr, be, tf, 5), f"tgt={tr}R BE={be} trail={tf}")
                if m > best[0]:
                    best = (m, (tr, be, tf))
    print(f"\nBEST: meanR={best[0]:+.3f} at target={best[1][0]}R BE={best[1][1]} trail={best[1][2]}")
