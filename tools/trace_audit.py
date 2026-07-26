"""trace_audit.py — INDEPENDENT trade-validity audit (does NOT reuse derive's sim).

For each killshot trade re-derives, from RAW 1m, the answers to "is this a real,
fillable, correctly-scored trade or a sim artifact?":
  A. ENTRY REACHABLE  — did price actually trade at the entry (limit fillable) in
     the entry session? (un-fillable = phantom)
  B. RISK sane        — risk as % of price (absurdly tiny stop => R-inflation flag)
  C. TARGET printed   — for a recorded WIN, did price actually reach the target?
  D. RE-RACE match    — replay entry->(sl|target) gap-aware on 1m; independent R
     must match recorded R (mismatch => sim bug / lookahead / overshoot)
Usage: python3 tools/trace_audit.py <tradebook.csv> <data_dir>
"""
import sys
import numpy as np
import pandas as pd

TB, DATA = sys.argv[1], sys.argv[2]
tb = pd.read_csv(TB)
k = tb.sym + "|" + tb.entry.round(1).astype(str) + "|" + tb.sl.round(1).astype(str) + "|" + tb.target.round(1).astype(str)
tb = tb.assign(_k=k).drop_duplicates(["mode", "_k"])
e = tb[(tb["mode"] == "eod") & (tb.grade >= 5)].copy()
e["rr"] = (e.target - e.entry).abs() / (e.entry - e.sl).abs()
e = e[e.rr >= 3].copy()
e["ts"] = pd.to_datetime(e["ts"])
print(f"auditing {len(e)} killshots from {TB}")

cache = {}


def bars(sym):
    if sym not in cache:
        d = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["ts"])
        d["ts"] = d.ts.dt.tz_localize(None) if d.ts.dt.tz else d.ts
        cache[sym] = d
    return cache[sym]


rows = []
for _, t in e.iterrows():
    m = bars(t.sym)
    ts = t.ts.tz_localize(None) if t.ts.tz else t.ts
    long = t["dir"] == "LONG"
    risk = abs(t.entry - t.sl)
    fwd = m[m.ts >= ts]
    sess = fwd[fwd.ts.dt.date == ts.date()]
    # A. entry reachable this session (limit at entry price)
    reachable = ((sess.low <= t.entry) & (sess.high >= t.entry)).any() if len(sess) else False
    # B. risk %
    risk_pct = 100 * risk / t.entry
    # C+D. independent re-race, eod (squareoff 15:10), gap-aware
    R, outc, tgt_seen = None, "none", False
    hold = fwd[fwd.ts <= ts + pd.Timedelta(days=5)]
    for b in hold.itertuples():
        if (b.ts.hour * 60 + b.ts.minute) >= 15 * 60 + 10:
            R = float((b.close - t.entry) / risk) * (1 if long else -1); outc = "eod"; break
        gap = (b.open <= t.sl) if long else (b.open >= t.sl)
        if gap:
            R = float((b.open - t.entry) / risk) * (1 if long else -1); outc = "gap"; break
        hit_sl = (b.low <= t.sl) if long else (b.high >= t.sl)
        hit_tg = (b.high >= t.target) if long else (b.low <= t.target)
        if hit_tg:
            tgt_seen = True
        if hit_sl and hit_tg:                 # same bar: assume SL first (conservative)
            R = -1.0; outc = "stop_amb"; break
        if hit_sl:
            R = -1.0; outc = "stop"; break
        if hit_tg:
            R = round(float(abs(t.target - t.entry) / risk), 2); outc = "target"; break
    rows.append({"sym": t.sym, "ts": ts, "dir": t["dir"], "rr": round(t.rr, 1),
                 "risk_pct": round(risk_pct, 3), "reachable": reachable,
                 "rec_R": round(t.R, 2), "trace_R": None if R is None else round(R, 2),
                 "trace_outc": outc, "tgt_seen": tgt_seen})

a = pd.DataFrame(rows)
a["dR"] = (a.rec_R - a.trace_R).abs()
print("\n=== VALIDITY ===")
print(f"A entry-reachable-in-session : {100*a.reachable.mean():.1f}%  (unreachable = un-fillable limit)")
print(f"B risk<0.05% (R-inflation)   : {int((a.risk_pct<0.05).sum())} / {len(a)}  (median risk {a.risk_pct.median():.3f}%)")
wins = a[a.rec_R > 0]
print(f"C recorded WIN & target really printed : {100*wins.tgt_seen.mean():.1f}%  ({int((~wins.tgt_seen).sum())} winners never hit target)")
matched = a[a.trace_R.notna()]
print(f"D re-race matches sim (|dR|<0.5): {100*(matched.dR<0.5).mean():.1f}%  | median |dR| {matched.dR.median():.2f} | max {matched.dR.max():.1f}")
print(f"\nindependent trace SUM R = {matched.trace_R.sum():+.0f}  (sim recorded SUM = {a.rec_R.sum():+.0f})")
print("\n=== BIG WINNERS (>+50R) traced ===")
big = a[a.rec_R > 50].sort_values("rec_R", ascending=False)
print(big[["sym", "ts", "dir", "rr", "risk_pct", "reachable", "rec_R", "trace_R", "tgt_seen"]].head(12).to_string(index=False))
print("\n=== BIG LOSERS (<-10R) traced ===")
print(a[a.rec_R < -10][["sym", "ts", "dir", "risk_pct", "rec_R", "trace_R", "trace_outc"]].head(6).to_string(index=False))
a.to_csv("/tmp/trace_audit_out.csv", index=False)
