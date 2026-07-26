"""trail_opt.py — TAUGHT trade-management simulator + per-stock trail optimiser.

Models the user's ACTUAL management (taught 2026-07-26), with EXACT Zerodha
intraday equity costs, on honest fills:

  fill    limit at ZONE MID, must be TOUCHED (no phantom); SL-first on fill bar
  stop    SL = sl_h x zone-height H  (taught: "bigger than half the block")
  BE      once favourable >= be_trigger, stop -> entry + cost_offset
          ("fix SL at buying price so broker charges get covered; failed trade
            doesn't lose") — cost_offset = be_mult x round-trip cost per share
  trail   after BE, stop trails the running extreme by trail_frac x DAILY-ATR
          (per-stock scaling: "2000rs stock moves 0.8%/day = 16rs; trail 2-3rs")
  exit    target | trail | hybrid(target as backstop) ; intraday(15:10) or N-day hold

Costs (Zerodha intraday equity, per executed order):
  brokerage min(Rs20, 0.03% turnover) x2 legs; STT 0.025% sell; exchange 0.00297%;
  SEBI Rs10/cr; stamp 0.003% buy; GST 18% on (brokerage+exchange+SEBI).
Size: qty = min(risk_budget / risk_per_share, capital x leverage / price).

Usage: python3 tools/trail_opt.py <tradebook.csv> <data_dir> [config.json] [killshot_only]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/doom/Public/PROJECT/2026/trader")
TB, DATA = sys.argv[1], sys.argv[2]
CFG = json.loads(Path(sys.argv[3] if len(sys.argv) > 3
                      else ROOT / "runs/validate/taught_meas/config.json").read_text())
KS_ONLY = (sys.argv[4] if len(sys.argv) > 4 else "1") == "1"
CAP = float(CFG["capital"]); RISK_PCT = float(CFG["risk"]["per_trade_pct"])
LEV = float(CFG["risk"].get("leverage", 5.0))
BUDGET = CAP * RISK_PCT / 100
SESSION = 375


def costs(entry_px, exit_px, qty):
    """Zerodha intraday equity, rupees, round trip."""
    tb_, ts_ = entry_px * qty, exit_px * qty
    brok = min(20.0, 0.0003 * tb_) + min(20.0, 0.0003 * ts_)
    stt = 0.00025 * ts_
    exch = 0.0000297 * (tb_ + ts_)
    sebi = 0.000001 * (tb_ + ts_)
    stamp = 0.00003 * tb_
    gst = 0.18 * (brok + exch + sebi)
    return brok + stt + exch + sebi + stamp + gst


# ---------- load signals ----------
tb = pd.read_csv(TB)
k = (tb.sym + "|" + tb.entry.round(1).astype(str) + "|" + tb.sl.round(1).astype(str)
     + "|" + tb.target.round(1).astype(str))
tb = tb.assign(_k=k).drop_duplicates(["mode", "_k"])
s = tb[(tb["mode"] == "eod") & tb.zone_lo.notna()].copy()
s["rr"] = (s.target - s.entry).abs() / (s.entry - s.sl).abs()
if KS_ONLY:
    s = s[(s.grade >= 5) & (s.rr >= 3)]
s["ts"] = pd.to_datetime(s["ts"]).dt.tz_localize(None)
print(f"signals: {len(s)}  (killshot_only={KS_ONLY})  budget=Rs{BUDGET:.0f}/trade")

# ---------- load bars + per-stock daily ATR ----------
BARS, DATR = {}, {}
for sym in s.sym.unique():
    d = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["ts"])
    tsv = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
    day = tsv.dt.normalize().values
    hi, lo, cl = d.high.values, d.low.values, d.close.values
    mins = (tsv.dt.hour * 60 + tsv.dt.minute).values
    g = pd.DataFrame({"d": day, "h": hi, "l": lo}).groupby("d").agg(h=("h", "max"), l=("l", "min"))
    DATR[sym] = float((g.h - g.l).median())            # typical daily range, rupees
    BARS[sym] = (tsv.values, hi, lo, cl, mins, day)
print("per-stock daily range (median): "
      + ", ".join(f"{k2}:{v:.1f}" for k2, v in list(DATR.items())[:6]) + " ...")

SIG = []
for t in s.itertuples():
    zlo, zhi = float(min(t.zone_lo, t.zone_hi)), float(max(t.zone_lo, t.zone_hi))
    if zhi <= zlo:
        continue
    SIG.append((t.sym, np.datetime64(t.ts), t.dir == "LONG", zlo, zhi, float(t.target),
                int(t.grade)))


def race(sl_h, be_mode, be_mult, trail_frac, exit_mode, hold_days):
    """One parameter set over every signal. Returns per-trade net-R list + stats."""
    out = []
    for sym, ts, long, zlo, zhi, tgt, grade in SIG:
        tsv, hi, lo, cl, mins, day = BARS[sym]
        H = zhi - zlo
        entry = (zlo + zhi) / 2
        risk = sl_h * H
        if risk <= 0:
            continue
        qty = int(min(BUDGET // risk, (CAP * LEV) // entry))
        if qty < 1:
            continue
        cps = costs(entry, entry, qty) / qty                  # cost per share (round trip)
        i = int(np.searchsorted(tsv, ts))
        n = len(tsv)
        if i <= 0 or i >= n - 2:
            continue
        sess_end = i
        while sess_end < n and day[sess_end] == day[i]:
            sess_end += 1
        # ---- honest fill: limit at mid must trade, same session, before 15:10
        fill = -1
        for x in range(i, min(sess_end, n)):
            if mins[x] >= 15 * 60 + 10:
                break
            if lo[x] <= entry <= hi[x]:
                fill = x
                break
        if fill < 0:
            out.append(("unfilled", 0.0, grade, sym))
            continue
        stop = entry - risk if long else entry + risk
        be_px = entry + be_mult * cps if long else entry - be_mult * cps
        be_trig = (be_mult * cps if be_mode == "cost"
                   else (risk if be_mode == "1R" else float("inf")))
        tdist = trail_frac * DATR[sym] if trail_frac else 0.0
        best = entry
        # intraday: race to the session end (hold_days=0 previously gave limit=fill+1
        # = an empty loop -> every param produced the identical fill-bar close)
        limit = min(n, sess_end if hold_days == 0 else fill + 1 + hold_days * SESSION)
        # SL-first on the fill bar (pessimistic)
        if (lo[fill] <= stop) if long else (hi[fill] >= stop):
            out.append(("stop", -1.0 - cps / risk, grade, sym))
            continue
        outc, gross = "timeout", 0.0
        for x in range(fill + 1, limit):
            if hold_days == 0 and mins[x] >= 15 * 60 + 10:
                outc, gross = "eod", (cl[x] - entry) / risk * (1 if long else -1)
                break
            if (lo[x] <= stop) if long else (hi[x] >= stop):
                gross = (stop - entry) / risk * (1 if long else -1)
                outc = "be/trail" if abs(gross) < 0.999 else "stop"
                break
            if exit_mode != "trail" and ((hi[x] >= tgt) if long else (lo[x] <= tgt)):
                outc, gross = "target", abs(tgt - entry) / risk
                break
            fav = (hi[x] - entry) if long else (entry - lo[x])
            best = max(best, hi[x]) if long else min(best, lo[x])
            if fav >= be_trig:                                 # BE-move (cost-covered)
                stop = max(stop, be_px) if long else min(stop, be_px)
                if tdist:                                      # then trail
                    ts_ = best - tdist if long else best + tdist
                    stop = max(stop, ts_) if long else min(stop, ts_)
        else:
            gross = (cl[limit - 1] - entry) / risk * (1 if long else -1)
        out.append((outc, gross - cps / risk, grade, sym))
    return out


def summ(res, label):
    fl = [r for r in res if r[0] != "unfilled"]
    if not fl:
        print(f"{label:52} n=0"); return None
    R = np.array([r[1] for r in fl])
    win = (R > 0.02).mean(); scr = (np.abs(R) <= 0.02).mean()
    print(f"{label:52} fill={100*len(fl)/len(res):4.0f}% win={100*win:4.1f}% "
          f"scr={100*scr:4.1f}% meanR={R.mean():+6.2f} medR={np.median(R):+5.2f} "
          f"totR={R.sum():+8.0f}")
    return R.mean(), R.sum(), len(fl)


print("\n=== EXIT MODE x TRAIL (sl_h=0.7, BE=cost x1.5) ===")
grid = {}
for hold, hl in [(0, "intraday"), (5, "5-day")]:
    for ex in ["target", "hybrid", "trail"]:
        for tf in [0.0, 0.15, 0.3, 0.5, 1.0]:
            if ex == "trail" and tf == 0.0:
                continue
            r = race(0.7, "cost", 1.5, tf, ex, hold)
            got = summ(r, f"{hl:9} exit={ex:7} trail={tf:.2f}xDATR")
            if got:
                grid[(hold, ex, tf)] = got

print("\n=== BE MODE (best exit config) ===")
best_key = max(grid, key=lambda k2: grid[k2][1])
hold, ex, tf = best_key
print(f"(carrying exit={ex} trail={tf} hold={'intraday' if hold==0 else '5-day'})")
for bem, bm in [("none", 0), ("cost", 1.0), ("cost", 1.5), ("cost", 3.0), ("1R", 1.0)]:
    summ(race(0.7, bem, bm, tf, ex, hold), f"BE={bem:5} mult={bm}")

print("\n=== SL WIDTH (taught: >0.5H) ===")
for slh in [0.5, 0.7, 1.0, 1.5]:
    summ(race(slh, "cost", 1.5, tf, ex, hold), f"sl_h={slh}xH")

print("\n=== PER-STOCK TRAIL OPTIMUM (exit=%s, hold=%s) ===" % (ex, hold))
per = {}
for tf2 in [0.0, 0.15, 0.3, 0.5, 1.0]:
    if ex == "trail" and tf2 == 0.0:
        continue
    for outc, R, grade, sym in race(0.7, "cost", 1.5, tf2, ex, hold):
        if outc != "unfilled":
            per.setdefault(sym, {}).setdefault(tf2, []).append(R)
rows = []
for sym, m in per.items():
    b = max(m, key=lambda t2: float(np.mean(m[t2])))
    rows.append((sym, DATR[sym], round(100 * b * DATR[sym] / 1000, 3), b,
                 round(float(np.mean(m[b])), 2), len(m[b]),
                 round(float(np.mean(m.get(0.0, m[b]))), 2)))
p = pd.DataFrame(rows, columns=["sym", "dailyRange", "trailRs_per_1000px", "best_frac",
                                "meanR", "n", "meanR_notrail"]).sort_values("meanR",
                                                                            ascending=False)
print(p.head(15).to_string(index=False))
print(f"\nmedian best trail_frac = {p.best_frac.median():.2f} x daily range")
p.to_csv("/tmp/trail_per_stock.csv", index=False)
