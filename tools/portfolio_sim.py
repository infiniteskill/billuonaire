"""portfolio_sim.py — CAPACITY-REAL P&L (the "total-R is meaningless" fix).

Sum-of-all-signals answers a question nobody can trade: 226 signals/month across
40 stocks while the account holds 1-2 positions. This sim walks the tape in time
order, ranks the day's candidates ex-ante, and takes only what the risk rules allow
(max concurrent, max/day, one per stock, daily loss stop) — then reports the account
curve in R and in rupees.

Consumes the per-trade outcomes produced by trail_opt-style management (recomputed
here so ranking and capacity interact correctly).

Usage: python3 tools/portfolio_sim.py <tradebook.csv> <data_dir> [rank] [max_conc]
  rank: grade | rr | grade_rr  (ex-ante only — never outcome)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
TB, DATA = sys.argv[1], sys.argv[2]
RANK = sys.argv[3] if len(sys.argv) > 3 else "grade_rr"
MAXC = int(sys.argv[4]) if len(sys.argv) > 4 else 2
CFG = json.loads((ROOT / "runs/validate/taught_meas/config.json").read_text())
CAP, RISK_PCT = float(CFG["capital"]), float(CFG["risk"]["per_trade_pct"])
LEV = float(CFG["risk"].get("leverage", 5.0))
MAX_DAY = int(CFG["risk"].get("max_trades_day", 3))
DAILY_STOP = float(CFG["risk"].get("daily_loss_pct", 1.5)) / RISK_PCT   # in R
SL_H, BE_MULT, TRAIL_FRAC, HOLD = 0.7, 1.5, 0.3, 0
SESSION = 375


def costs(e, x, q):
    tb_, ts_ = e * q, x * q
    brok = min(20.0, 0.0003 * tb_) + min(20.0, 0.0003 * ts_)
    return (brok + 0.00025 * ts_ + 0.0000297 * (tb_ + ts_) + 0.000001 * (tb_ + ts_)
            + 0.00003 * tb_ + 0.18 * (brok + 0.0000297 * (tb_ + ts_)))


tb = pd.read_csv(TB)
k = (tb.sym + "|" + tb.entry.round(1).astype(str) + "|" + tb.sl.round(1).astype(str)
     + "|" + tb.target.round(1).astype(str))
tb = tb.assign(_k=k).drop_duplicates(["mode", "_k"])
s = tb[(tb["mode"] == "eod") & tb.zone_lo.notna()].copy()
s["rr"] = (s.target - s.entry).abs() / (s.entry - s.sl).abs()
s = s[(s.grade >= 5) & (s.rr >= 3)].copy()
s["ts"] = pd.to_datetime(s["ts"]).dt.tz_localize(None)
s = s.sort_values("ts")
print(f"candidate killshots: {len(s)}   rank={RANK} max_concurrent={MAXC}")

BARS, DATR = {}, {}
for sym in s.sym.unique():
    d = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["ts"])
    tsv = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
    day = tsv.dt.normalize().values
    g = pd.DataFrame({"d": day, "h": d.high.values, "l": d.low.values}).groupby("d").agg(
        h=("h", "max"), l=("l", "min"))
    DATR[sym] = float((g.h - g.l).median())
    BARS[sym] = (tsv.values, d.high.values, d.low.values, d.close.values,
                 (tsv.dt.hour * 60 + tsv.dt.minute).values, day)


def run_trade(sym, ts, long, zlo, zhi, tgt):
    """Returns (fill_ts, exit_ts, net_R) or None if never filled."""
    tsv, hi, lo, cl, mins, day = BARS[sym]
    H = zhi - zlo
    entry, risk = (zlo + zhi) / 2, SL_H * (zhi - zlo)
    if risk <= 0:
        return None
    qty = int(min((CAP * RISK_PCT / 100) // risk, (CAP * LEV) // entry))
    if qty < 1:
        return None
    cps = costs(entry, entry, qty) / qty
    i = int(np.searchsorted(tsv, np.datetime64(ts)))
    n = len(tsv)
    if i <= 0 or i >= n - 2:
        return None
    sess_end = i
    while sess_end < n and day[sess_end] == day[i]:
        sess_end += 1
    fill = -1
    for x in range(i, min(sess_end, n)):
        if mins[x] >= 15 * 60 + 10:
            break
        if lo[x] <= entry <= hi[x]:
            fill = x
            break
    if fill < 0:
        return None
    stop = entry - risk if long else entry + risk
    be_px = entry + BE_MULT * cps if long else entry - BE_MULT * cps
    tdist = TRAIL_FRAC * DATR[sym]
    best = entry
    limit = min(n, fill + 1 + max(HOLD, 1) * SESSION)
    if (lo[fill] <= stop) if long else (hi[fill] >= stop):
        return tsv[fill], tsv[fill], -1.0 - cps / risk
    for x in range(fill + 1, limit):
        if HOLD == 0 and mins[x] >= 15 * 60 + 10:
            return tsv[fill], tsv[x], (cl[x] - entry) / risk * (1 if long else -1) - cps / risk
        if (lo[x] <= stop) if long else (hi[x] >= stop):
            return tsv[fill], tsv[x], (stop - entry) / risk * (1 if long else -1) - cps / risk
        if (hi[x] >= tgt) if long else (lo[x] <= tgt):
            return tsv[fill], tsv[x], abs(tgt - entry) / risk - cps / risk
        fav = (hi[x] - entry) if long else (entry - lo[x])
        best = max(best, hi[x]) if long else min(best, lo[x])
        if fav >= BE_MULT * cps:
            stop = max(stop, be_px) if long else min(stop, be_px)
            t_ = best - tdist if long else best + tdist
            stop = max(stop, t_) if long else min(stop, t_)
    return tsv[fill], tsv[limit - 1], (cl[limit - 1] - entry) / risk * (1 if long else -1) - cps / risk


s["score"] = (s.grade + s.rr.clip(upper=20) / 20 if RANK == "grade_rr"
              else (s.grade if RANK == "grade" else s.rr))
open_pos, taken, day_state = [], [], {}
for t in s.itertuples():
    d0 = t.ts.normalize()
    st = day_state.setdefault(d0, {"n": 0, "R": 0.0})
    open_pos = [p for p in open_pos if p[0] > np.datetime64(t.ts)]      # expire closed
    if len(open_pos) >= MAXC or st["n"] >= MAX_DAY or st["R"] <= -DAILY_STOP:
        continue
    if any(p[1] == t.sym for p in open_pos):
        continue
    r = run_trade(t.sym, t.ts, t.dir == "LONG", float(min(t.zone_lo, t.zone_hi)),
                  float(max(t.zone_lo, t.zone_hi)), float(t.target))
    if r is None:
        continue
    fill_ts, exit_ts, R = r
    open_pos.append((exit_ts, t.sym))
    st["n"] += 1; st["R"] += R
    taken.append({"ts": t.ts, "sym": t.sym, "dir": t.dir, "grade": t.grade,
                  "rr": round(t.rr, 1), "R": round(R, 2)})

a = pd.DataFrame(taken)
if not len(a):
    print("no trades taken"); sys.exit()
R = a.R.values
rupee = R * (CAP * RISK_PCT / 100)
eq = CAP + np.cumsum(rupee)
dd = (np.maximum.accumulate(eq) - eq).max()
days = (a.ts.max() - a.ts.min()).days or 1
print(f"\nTAKEN {len(a)} trades over {days}d  ({len(a)/(days/30.4):.1f}/month)")
print(f"  win={100*(R>0.02).mean():.1f}%  scratch={100*(np.abs(R)<=0.02).mean():.1f}%  "
      f"meanR={R.mean():+.2f}  medR={np.median(R):+.2f}  totR={R.sum():+.0f}")
print(f"  Rs: start {CAP:,.0f} -> end {eq[-1]:,.0f}  ({100*(eq[-1]/CAP-1):+.1f}%)  "
      f"maxDD Rs{dd:,.0f} ({100*dd/CAP:.1f}%)")
print(f"  per month: {100*((eq[-1]/CAP)**(30.4/days)-1):+.1f}%")
print(f"\nby grade:\n{a.groupby('grade').R.agg(['count','mean','sum']).round(2).to_string()}")
a.to_csv("/tmp/portfolio_taken.csv", index=False)
print("\nfirst 10 taken:\n" + a.head(10).to_string(index=False))
