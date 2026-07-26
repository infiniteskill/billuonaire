"""grammar_audit.py — the taught 4-STAGE GRAMMAR audit, independent of derive's sim.

The taught trade is a TEMPORAL sequence, not a single bar event:
  FORM    zone born at the swing origin
  DEPART  price LEAVES the zone and travels away in the trade direction
          (restudy: zone-birth -> penetration median ~8 SESSIONS)
  RETURN  price comes back and penetrates toward zone MID (restudy: median 0.85H)
  RESPOND price reverses out of the zone (post-hoc only; this IS the outcome)

Detectors fire on ANY retest — including same-session re-touches where price never
really left. Those are degenerate: the trade's costume without its structure.
This script classifies every signal by measured price geometry and re-races the
TAUGHT entry (mid fill, SL = sl_h x H, BE-move at be_r) honestly from raw 1m.

Usage: python3 tools/grammar_audit.py <tradebook.csv> <data_dir> [sl_h] [be_r]
"""
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

TB, DATA = sys.argv[1], sys.argv[2]
SL_H = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
BE_R = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
LOOKBACK = 375 * 25          # 25 sessions of 1m history for the FORM/DEPART scan
FWD = 375 * 5                # 5 sessions forward for RESPOND / the race
SESSION_MIN = 375

tb = pd.read_csv(TB)
k = (tb.sym + "|" + tb.entry.round(1).astype(str) + "|" + tb.sl.round(1).astype(str)
     + "|" + tb.target.round(1).astype(str))
tb = tb.assign(_k=k).drop_duplicates(["mode", "_k"])
sig = tb[(tb["mode"] == "eod")].copy()
sig["rr"] = (sig.target - sig.entry).abs() / (sig.entry - sig.sl).abs()
sig = sig[sig.zone_lo.notna()].copy()
sig["killshot"] = (sig.grade >= 5) & (sig.rr >= 3)
sig["ts"] = pd.to_datetime(sig["ts"]).dt.tz_localize(None)
print(f"grammar-auditing {len(sig)} killshot signals  (sl_h={SL_H}, be_r={BE_R})")

rows = []
for symbol, grp in sig.groupby("sym"):
    d = pd.read_csv(f"{DATA}/{symbol}.csv", parse_dates=["ts"])
    ts = d.ts.dt.tz_localize(None).values if d.ts.dt.tz else d.ts.values
    hi, lo, cl = d.high.values, d.low.values, d.close.values
    mins = (pd.DatetimeIndex(ts).hour * 60 + pd.DatetimeIndex(ts).minute).values
    day = pd.DatetimeIndex(ts).normalize().values
    n = len(ts)
    # rolling ATR proxy: mean 1m true range over 375 bars (1 session), for scale-free
    # departure measurement (zone heights are ~9bps -> H-units are meaningless)
    tr = pd.Series(hi - lo).rolling(SESSION_MIN, min_periods=50).mean().values
    # first-touch bookkeeping: signals on the SAME zone, ordered by ts
    grp = grp.sort_values("ts")
    zkey = (grp.zone_lo.round(1).astype(str) + "_" + grp.zone_hi.round(1).astype(str)
            + "_" + grp.dir)
    seen_zone = defaultdict(int)
    for t, zk in zip(grp.itertuples(), zkey):
        touch_no = seen_zone[zk]; seen_zone[zk] += 1
        zlo, zhi = float(min(t.zone_lo, t.zone_hi)), float(max(t.zone_lo, t.zone_hi))
        H = zhi - zlo
        if H <= 0:
            continue
        long = t.dir == "LONG"
        i = int(np.searchsorted(ts, np.datetime64(t.ts)))
        if i <= 0 or i >= n - 10:
            continue
        # ---------- FORM / DEPART (backwards scan) ----------
        a = max(0, i - LOOKBACK)
        h_w, l_w = hi[a:i], lo[a:i]
        inside = (l_w <= zhi) & (h_w >= zlo)
        j = i - 1 - a                                   # index within window
        while j >= 0 and inside[j]:                     # skip the return contact
            j -= 1
        dep_end = j
        while j >= 0 and not inside[j]:                 # the away stretch
            j -= 1
        dep_start, form_end = j + 1, j
        if dep_end < dep_start:                         # never left: pure degenerate
            dep_bars, dep_dist, dep_atr, dep_sess, wrong = 0, 0.0, 0.0, 0, False
        else:
            seg_h, seg_l = h_w[dep_start:dep_end + 1], l_w[dep_start:dep_end + 1]
            dep_bars = dep_end - dep_start + 1
            atr_i = tr[i] if not np.isnan(tr[i]) else (zhi - zlo)
            if long:                                    # demand zone: away = ABOVE
                far = seg_h.max() - zhi
                wrong = bool(seg_l.min() < zlo - 0.1 * H)
            else:                                       # supply zone: away = BELOW
                far = zlo - seg_l.min()
                wrong = bool(seg_h.max() > zhi + 0.1 * H)
            dep_dist = far / H
            dep_atr = far / atr_i if atr_i > 0 else 0.0
            dep_sess = len(np.unique(day[a + dep_start:a + dep_end + 1]))
        old_zone = form_end < 0                          # formation older than window
        atr_sig = float(tr[i]) if not np.isnan(tr[i]) else H   # 1-session mean 1m TR
        # ---------- RETURN (penetration this session) ----------
        sess_end = i
        while sess_end < n and day[sess_end] == day[i]:
            sess_end += 1
        c_end = min(i + 60, sess_end)                    # FIRST contact window
        pen = ((zhi - lo[i:c_end].min()) / H if long
               else (hi[i:c_end].max() - zlo) / H)
        pen = float(max(0.0, min(pen, 1.5)))
        # ---------- RESPOND (post-hoc zone reaction) ----------
        mid = (zlo + zhi) / 2
        f = min(n, i + FWD)
        seg_h, seg_l = hi[i:f], lo[i:f]
        if long:
            fav_i = np.argmax(seg_h >= mid + H) if (seg_h >= mid + H).any() else -1
            adv_i = np.argmax(seg_l <= mid - SL_H * H) if (seg_l <= mid - SL_H * H).any() else -1
        else:
            fav_i = np.argmax(seg_l <= mid - H) if (seg_l <= mid - H).any() else -1
            adv_i = np.argmax(seg_h >= mid + SL_H * H) if (seg_h >= mid + SL_H * H).any() else -1
        respond = bool(fav_i >= 0 and (adv_i < 0 or fav_i < adv_i))
        # ---------- TAUGHT-ENTRY honest race ----------
        # limit at MID, must be TOUCHED this session; SL = SL_H x H; BE at +BE_R x risk
        entry, risk = mid, SL_H * H
        stop = entry - risk if long else entry + risk
        tgt = float(t.target)
        fill = -1
        for x in range(i, min(sess_end, n)):
            if mins[x] >= 15 * 60 + 10:
                break
            if lo[x] <= entry <= hi[x]:
                fill = x
                break
        if fill < 0:
            outc, R = "unfilled", None
        else:
            outc, R = "timeout", None
            hit_sl = (lo[fill] <= stop) if long else (hi[fill] >= stop)
            if hit_sl:
                outc, R = "stop", -1.0                   # SL-first on fill bar
            else:
                for x in range(fill + 1, min(f, n)):
                    if mins[x] >= 15 * 60 + 10:
                        outc = "eod"; R = float((cl[x] - entry) / risk) * (1 if long else -1)
                        break
                    if (lo[x] <= stop) if long else (hi[x] >= stop):
                        outc = "be" if stop == entry else "stop"
                        R = 0.0 if stop == entry else -1.0
                        break
                    if (hi[x] >= tgt) if long else (lo[x] <= tgt):
                        outc = "target"; R = float(abs(tgt - entry) / risk)
                        break
                    fav = (hi[x] - entry) if long else (entry - lo[x])
                    if stop != entry and fav >= BE_R * risk:
                        stop = entry
        rows.append({"sym": symbol, "ts": t.ts, "dir": t.dir, "grade": t.grade,
                     "killshot": bool(t.killshot), "touch_no": touch_no,
                     "atr": round(atr_sig, 4), "H_atr": round(H / atr_sig, 2) if atr_sig > 0 else 0,
                     "entry_px": float(t.entry), "zlo": zlo, "zhi": zhi,
                     "dep_atr": round(float(dep_atr), 2), "dep_sess": int(dep_sess),
                     "H": H, "dep_bars": dep_bars, "dep_dist_H": round(float(dep_dist), 2),
                     "wrong_side": wrong, "old_zone": old_zone, "pen_H": round(pen, 2),
                     "respond": respond, "t_outc": outc,
                     "t_R": None if R is None else round(R, 2), "phantom_R": t.R})

a = pd.DataFrame(rows)
a.to_csv("/tmp/grammar_audit_out.csv", index=False)
print(f"\naudited {len(a)}")


def blk(x, label):
    if not len(x):
        print(f"{label:28} n=0"); return
    f = x[x.t_R.notna()]
    fill = 100 * len(f) / len(x)
    line = (f"{label:28} n={len(x):5} respond={100*x.respond.mean():5.1f}% "
            f"fill={fill:5.1f}%")
    if len(f):
        line += (f" win={100*(f.t_R > 0).mean():5.1f}% scr={100*(f.t_R == 0).mean():4.1f}%"
                 f" meanR={f.t_R.mean():+6.2f} totR={f.t_R.sum():+8.0f}")
    print(line)


print("\n=== DEPART distribution (ATR-scaled + first-touch) ===")
print(f"  median dep_atr={a.dep_atr.median():.2f}ATR  median dep_sess={a.dep_sess.median():.0f}"
      f"  first-touch signals={int((a.touch_no==0).sum())} ({100*(a.touch_no==0).mean():.1f}%)")
print("\n=== DEPART distribution ===")
print(f"  never-left (dep_bars=0)     : {int((a.dep_bars == 0).sum())} ({100*(a.dep_bars==0).mean():.1f}%)")
print(f"  dep_bars < 1 session (375)  : {int((a.dep_bars < 375).sum())} ({100*(a.dep_bars<375).mean():.1f}%)")
print(f"  median dep_bars={a.dep_bars.median():.0f} ({a.dep_bars.median()/375:.1f} sessions)"
      f"  median dep_dist={a.dep_dist_H.median():.2f}H  wrong_side={100*a.wrong_side.mean():.1f}%")
print(f"  median penetration={a.pen_H.median():.2f}H  (restudy: 0.85H)")

print("\n=== CLASS SPLIT (taught-entry honest race: mid fill, %.1fH SL, BE@+%.1fR) ===" % (SL_H, BE_R))
blk(a, "ALL signals")
for lbl, mask in [
    ("never-left (degenerate)", a.dep_bars == 0),
    ("shallow (<0.5H away)", (a.dep_bars > 0) & (a.dep_dist_H < 0.5)),
    ("wrong-side (zone broken)", a.wrong_side),
    ("DEPART>=0.5H", (a.dep_dist_H >= 0.5) & ~a.wrong_side),
    ("DEPART>=1H", (a.dep_dist_H >= 1.0) & ~a.wrong_side),
    ("DEPART>=1H +1sess", (a.dep_dist_H >= 1.0) & (a.dep_bars >= 375) & ~a.wrong_side),
    ("DEPART>=2H +1sess", (a.dep_dist_H >= 2.0) & (a.dep_bars >= 375) & ~a.wrong_side),
    ("DEPART>=1H +5sess", (a.dep_dist_H >= 1.0) & (a.dep_bars >= 1875) & ~a.wrong_side),
    ("DEPART>=1H +8sess (taught)", (a.dep_dist_H >= 1.0) & (a.dep_bars >= 3000) & ~a.wrong_side),
]:
    blk(a[mask], lbl)

print("\n--- ATR-scaled departure ---")
for lbl, mask in [("dep>=1 ATR", a.dep_atr >= 1), ("dep>=2 ATR", a.dep_atr >= 2),
                  ("dep>=4 ATR", a.dep_atr >= 4), ("dep>=8 ATR", a.dep_atr >= 8)]:
    blk(a[mask & ~a.wrong_side], lbl)

print("\n--- FIRST-TOUCH (the taught trade) vs RE-TOUCH ---")
blk(a[a.touch_no == 0], "first touch of zone")
blk(a[a.touch_no > 0], "re-touch (2nd+)")
blk(a[(a.touch_no == 0) & (a.dep_atr >= 2) & ~a.wrong_side], "1st touch + dep>=2ATR")
blk(a[(a.touch_no == 0) & (a.dep_atr >= 2) & ~a.wrong_side & a.killshot], "  ^ + killshot tier")
blk(a[(a.touch_no == 0) & (a.dep_sess >= 1) & ~a.wrong_side], "1st touch + dep>=1 session")

print("\n--- KILLSHOT tier only (grade>=5, rr>=3) ---")
blk(a[a.killshot], "killshot ALL")
blk(a[a.killshot & (a.dep_atr >= 2) & ~a.wrong_side], "killshot + dep>=2ATR")

print("\n--- penetration ---")
print(f"  median first-contact penetration = {a.pen_H.median():.2f}H (restudy 0.85H)")
for lo_, hi_ in [(0, .5), (.5, .9), (.9, 1.1), (1.1, 1.6)]:
    m = a[(a.pen_H >= lo_) & (a.pen_H < hi_)]
    blk(m, f"pen {lo_}-{hi_}H")

print("\n--- ZONE THICKNESS vs VOLATILITY (ex-ante!) ---")
print(f"  median H/ATR = {a.H_atr.median():.2f}  (zone height in 1-session-mean-1m-TR units)")
for lo_, hi_ in [(0, 1), (1, 2), (2, 4), (4, 8), (8, 1e9)]:
    m = a[(a.H_atr >= lo_) & (a.H_atr < hi_)]
    blk(m, f"H/ATR {lo_}-{hi_ if hi_ < 1e9 else 'inf'}")
print("  killshot tier only:")
for lo_, hi_ in [(0, 1), (1, 2), (2, 4), (4, 1e9)]:
    m = a[a.killshot & (a.H_atr >= lo_) & (a.H_atr < hi_)]
    blk(m, f"  KS H/ATR {lo_}-{hi_ if hi_ < 1e9 else 'inf'}")
print("  best-stack: killshot + 1st touch + dep>=2ATR + H/ATR>=1:")
blk(a[a.killshot & (a.touch_no == 0) & (a.dep_atr >= 2) & ~a.wrong_side & (a.H_atr >= 1)], "  STACK")

print("\n=== CALIBRATION vs user's own marks ===")
for sym, d0, d1 in [("HAVELLS", "2026-07-07", "2026-07-10"), ("DABUR", "2026-07-07", "2026-07-09")]:
    m = a[(a.sym == sym) & (a.ts.astype(str).str[:10] >= d0) & (a.ts.astype(str).str[:10] <= d1)]
    print(f"  {sym} {d0}..{d1}: {len(m)} signals")
    for r in m.head(8).itertuples():
        print(f"    {str(r.ts)[:16]} {r.dir:5} g{r.grade} entry={r.entry_px:.1f} zone={r.zlo:.1f}-{r.zhi:.1f} "
              f"H/ATR={r.H_atr} dep={r.dep_atr}ATR touch#{r.touch_no} pen={r.pen_H} resp={r.respond} R={r.t_R}")
for sym, date, dr in [("HAVELLS", "2026-07-09", "SHORT"), ("DABUR", "2026-07-08", "SHORT")]:
    m = a[(a.sym == sym) & (a.ts.astype(str).str[:10] == date) & (a.dir == dr)]
    if len(m):
        r = m.iloc[0]
        print(f"  {sym} {date} {dr}: dep_bars={r.dep_bars} ({r.dep_bars/375:.1f}sess) "
              f"dep_dist={r.dep_dist_H}H wrong={r.wrong_side} pen={r.pen_H}H "
              f"respond={r.respond} taught_outc={r.t_outc} R={r.t_R}")
    else:
        print(f"  {sym} {date} {dr}: not in signal set")
