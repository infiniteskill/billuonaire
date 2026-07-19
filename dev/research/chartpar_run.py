#!/usr/bin/env python
"""Chart-parity study: do repo detectors find the user's hand-drawn SMC zones,
and how much extra do they emit?

Route: core zone rules REPLICATED faithfully from detector sources (both are
documented ports of standalone scans):
  - ob_lux.py  : swing pivot (size=5) confirm -> close-cross structure break ->
                 anchor = min parsed-low (bull) / max parsed-high (bear) over
                 [pivot..confirm], hv bars (range >= 2 * own trailing ATR14,
                 rolling-TR SMA incl. current bar) get high/low swapped in the
                 search; zone = winning bar's sorted (pL, pH); born = that bar.
  - fvg_cb.py  : 3-candle gap, c2 close beyond origin edge, gap% > running
                 rsum/len threshold (rsum sums bar range% from bar index 2,
                 denominator = full bar count); creation gated on ATR14
                 availability (>=15 bars); zone bull (c1.high, c3.low) /
                 bear (c3.high, c1.lo... (c3.high, c1.low)); born = c2.ts.
  - swings.py  : fractal 2N+1 window, middle strictly extreme vs all others.
"""
import sys, math
import pandas as pd
from collections import deque
from datetime import timedelta

DATA = "/home/doom/Public/PROJECT/2026/trader/data/long5m/{}.csv"

def load_tf(sym, minutes):
    df = pd.read_csv(DATA.format(sym), parse_dates=["ts"])
    df = df.set_index("ts").sort_index()
    off = "15min" if minutes == 30 else "0min"   # align bins to 09:15 session open
    agg = df.resample(f"{minutes}min", offset=off, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna(subset=["open"])
    agg = agg.reset_index()
    return agg

# ---------------- trailing ATR (repo formula: SMA of last 14 TRs, incl. current bar) ---
def atr_series(df):
    n = len(df); out = [None] * n
    trs = deque(maxlen=14); s = 0.0
    for i in range(n):
        if i:
            h, l, pc = df.high[i], df.low[i], df.close[i - 1]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            if len(trs) == trs.maxlen:
                s -= trs[0]
            trs.append(tr); s += tr
        if i >= 14:
            out[i] = s / 14
    return out

# ---------------- ob_lux replication ----------------
def ob_lux(df, size=5, hv_mult=2.0):
    n = len(df); events = []
    pH, pL = [], []
    trs = deque(maxlen=14); tr_sum = 0.0
    swH = swL = None; swHc = swLc = True
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    TS = df.ts.tolist()
    for i in range(n):
        if i:
            tr = max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
            if len(trs) == trs.maxlen:
                tr_sum -= trs[0]
            trs.append(tr); tr_sum += tr
        atr = tr_sum / trs.maxlen if i >= trs.maxlen else None
        hv = atr is not None and H[i] - L[i] >= hv_mult * atr
        pH.append(L[i] if hv else H[i])
        pL.append(H[i] if hv else L[i])
        if i >= size:
            p = i - size
            if H[p] > max(H[p + 1:i + 1]):
                swH, swHc = (H[p], p), False
            if L[p] < min(L[p + 1:i + 1]):
                swL, swLc = (L[p], p), False
        c, cp = C[i], C[i - 1] if i else None
        if swH and not swHc and c > swH[0] and (i == 0 or cp <= swH[0]):
            swHc = True
            idx = min(range(swH[1], i + 1), key=lambda j: pL[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            q = 0.5 if not atr else min((c - swH[0]) / atr, 1.0)
            events.append(dict(det="ob_lux", kind="OB_BULL", lo=lo, hi=hi,
                               born=TS[idx], born_i=idx, ev_i=i, ev_ts=TS[i], q=q))
        if swL and not swLc and c < swL[0] and (i == 0 or cp >= swL[0]):
            swLc = True
            idx = max(range(swL[1], i + 1), key=lambda j: pH[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            q = 0.5 if not atr else min((swL[0] - c) / atr, 1.0)
            events.append(dict(det="ob_lux", kind="OB_BEAR", lo=lo, hi=hi,
                               born=TS[idx], born_i=idx, ev_i=i, ev_ts=TS[i], q=q))
    return events

# ---------------- fvg_cb replication ----------------
def fvg_cb(df, thr_mult=1.0):
    n = len(df); events = []
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    TS = df.ts.tolist()
    rsum = 0.0
    atr = atr_series(df)
    for i in range(2, n):
        # fold bar i's range% (rsum spans bars 2..i, matching the cursor fold)
        rsum += (H[i] - L[i]) / L[i] if L[i] else 0.0
        if atr[i] is None:          # ctx.atr gate: no creation until ATR exists
            continue
        thr = thr_mult * rsum / (i + 1)
        c1h, c1l, c2c = H[i - 2], L[i - 2], C[i - 1]
        # bull: c3.low > c1.high, displacement c2.close > c1.high
        lo, hi = c1h, L[i]
        if hi > lo and c2c > c1h and (hi - lo) / lo > thr:
            events.append(dict(det="fvg_cb", kind="FVG_BULL", lo=lo, hi=hi,
                               born=TS[i - 1], born_i=i - 1, ev_i=i, ev_ts=TS[i], q=0.6))
        lo, hi = H[i], c1l
        if hi > lo and c2c < c1l and (hi - lo) / lo > thr:
            events.append(dict(det="fvg_cb", kind="FVG_BEAR", lo=lo, hi=hi,
                               born=TS[i - 1], born_i=i - 1, ev_i=i, ev_ts=TS[i], q=0.6))
    return events

# ---------------- fractal swings (repo rule, strength N) ----------------
def fractal_swings(df, N=5):
    n = len(df); out = []
    H, L, TS = df.high.tolist(), df.low.tolist(), df.ts.tolist()
    for i in range(N, n - N):
        win_h = [H[j] for j in range(i - N, i + N + 1) if j != i]
        win_l = [L[j] for j in range(i - N, i + N + 1) if j != i]
        if all(H[i] > v for v in win_h):
            out.append(dict(kind="SWING_H", i=i, ts=TS[i], px=H[i]))
        if all(L[i] < v for v in win_l):
            out.append(dict(kind="SWING_L", i=i, ts=TS[i], px=L[i]))
    return out

def swing_prominence(sw, df):
    """min(left drop, right drop) over the 5-bar flanks, in price units."""
    i, N = sw["i"], 5
    H, L = df.high.tolist(), df.low.tolist()
    if sw["kind"] == "SWING_H":
        ldrop = sw["px"] - min(L[max(0, i - N):i])
        rdrop = sw["px"] - min(L[i + 1:i + N + 1])
    else:
        ldrop = max(H[max(0, i - N):i]) - sw["px"]
        rdrop = max(H[i + 1:i + N + 1]) - sw["px"]
    return min(ldrop, rdrop)

# ---------------- retest + reaction ----------------
def first_retest(z, df):
    H, L = df.high.tolist(), df.low.tolist()
    for t in range(z["ev_i"] + 1, len(df)):
        if L[t] <= z["hi"] and H[t] >= z["lo"]:
            return t
    return None

def reaction_ok(z, t, df, atr, look=12, mult=2.0):
    if t is None or atr[t] is None:
        return None
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    end = min(len(df), t + 1 + look)
    if end <= t + 1:
        return None
    bull = "BULL" in z["kind"]
    move = (max(H[t + 1:end]) - C[t]) if bull else (C[t] - min(L[t + 1:end]))
    return move >= mult * atr[t]

# ---------------- matching user zones ----------------
def overlap_frac(z, band):
    lo = max(z["lo"], band[0]); hi = min(z["hi"], band[1])
    return max(0.0, hi - lo) / (band[1] - band[0])

def match(zones, band, b0, b1, sessions, side=None):
    """FOUND: >=50% of user band covered & born within +-3 sessions of window.
    PARTIAL: >=50% cover but born outside, or 20-50% cover in-window.
    side: 'demand' restricts to *_BULL kinds, 'supply' to *_BEAR."""
    if side:
        want = "BULL" if side == "demand" else "BEAR"
        zones = [z for z in zones if want in z["kind"]]
    lo3 = shift_sessions(sessions, b0, -3); hi3 = shift_sessions(sessions, b1, +3)
    best, bestscore = None, (-1, -1)
    for z in zones:
        f = overlap_frac(z, band)
        if f <= 0:
            continue
        inwin = lo3 <= z["born"].date() <= hi3
        score = (f >= .5 and inwin, f)
        if score > bestscore:
            bestscore, best = score, (z, f, inwin)
    if best is None:
        return "MISSED", None
    z, f, inwin = best
    if f >= .5 and inwin:
        return "FOUND", best
    if f >= .5 or (f >= .2 and inwin):
        return "PARTIAL", best
    return "MISSED", best

def union_cover(zones, band, b0, b1, sessions, side):
    """Fraction of user band covered by the UNION of side-correct in-window zones."""
    want = "BULL" if side == "demand" else "BEAR"
    lo3 = shift_sessions(sessions, b0, -3); hi3 = shift_sessions(sessions, b1, +3)
    ivs = sorted((max(z["lo"], band[0]), min(z["hi"], band[1])) for z in zones
                 if want in z["kind"] and lo3 <= z["born"].date() <= hi3
                 and z["hi"] > band[0] and z["lo"] < band[1])
    cov, cur = 0.0, None
    for lo, hi in ivs:
        if cur is None or lo > cur[1]:
            if cur: cov += cur[1] - cur[0]
            cur = [lo, hi]
        else:
            cur[1] = max(cur[1], hi)
    if cur: cov += cur[1] - cur[0]
    return cov / (band[1] - band[0])

def shift_sessions(sessions, d, k):
    """d = date; move k trading sessions (clamped)."""
    if d < sessions[0]:
        idx = 0
    elif d > sessions[-1]:
        idx = len(sessions) - 1
    else:
        idx = next(i for i, s in enumerate(sessions) if s >= d)
    return sessions[max(0, min(len(sessions) - 1, idx + k))]

# ---------------- filters ----------------
def near_prom_swing(z, proms, bars=5):
    return any(abs(s["i"] - z["born_i"]) <= bars for s in proms)

def revisit_delay_ok(z, t, bars_per_hr):
    return t is None or (t - z["ev_i"]) >= bars_per_hr

# =====================================================================
import datetime as dt
D = dt.date

USER = {
    "ASIANPAINT": dict(tf=15, zones=[
        ("A1 supply",  (2755, 2778), D(2026, 6, 12), D(2026, 6, 17), "supply"),
        ("A2 demand",  (2605, 2628), D(2026, 6, 5),  D(2026, 6, 8),  "demand"),
        ("A3 demand",  (2558, 2578), D(2026, 5, 15), D(2026, 5, 21), "demand"),
        ("A4 demand",  (2408, 2440), D(2026, 4, 27), D(2026, 5, 4),  "demand"),
        ("A5 demand",  (2115, 2155), D(2026, 3, 23), D(2026, 3, 30), "demand"),
    ]),
    "HINDUNILVR": dict(tf=30, zones=[
        ("H1 FVG",     (2185, 2212), D(2026, 7, 3),  D(2026, 7, 6),  "supply"),
        ("H2 OB/prop", (2103, 2132), D(2026, 6, 9),  D(2026, 6, 12), "demand"),
        ("H3 FVG",     (2108, 2136), D(2026, 7, 16), D(2026, 7, 17), "demand"),
        ("H4 demand",  (2050, 2097), D(2026, 6, 1),  D(2026, 6, 5),  "demand"),
    ]),
}
USER_SWINGS = [  # HINDUNILVR 30m
    ("SH ~2225 mid-Jun",  "SWING_H", (2216, 2234), D(2026, 6, 10), D(2026, 6, 20)),
    ("SH ~2245 early-Jul","SWING_H", (2233, 2257), D(2026, 6, 30), D(2026, 7, 8)),
    ("SL ~2085 early-Jun","SWING_L", (2077, 2093), D(2026, 6, 1),  D(2026, 6, 9)),
    ("SL ~2100 17-Jul",   "SWING_L", (2087, 2113), D(2026, 7, 15), D(2026, 7, 17)),
]

for sym, spec in USER.items():
    tf = spec["tf"]
    df = load_tf(sym, tf)
    sessions = sorted(set(t.date() for t in df.ts))
    atr = atr_series(df)
    obs = ob_lux(df)
    fvgs = fvg_cb(df)
    zones = obs + fvgs
    bars_hr = 60 // tf
    swings = fractal_swings(df, 5)
    proms = [s for s in swings if atr[s["i"]] and swing_prominence(s, df) >= 2 * atr[s["i"]]]

    print(f"\n=== {sym} {tf}m  bars={len(df)}  {df.ts.iloc[0]} .. {df.ts.iloc[-1]}  sessions={len(sessions)}")
    print(f"emitted: OB={len(obs)} (bull={sum(1 for z in obs if z['kind']=='OB_BULL')} "
          f"bear={sum(1 for z in obs if z['kind']=='OB_BEAR')})  "
          f"FVG={len(fvgs)} (bull={sum(1 for z in fvgs if z['kind']=='FVG_BULL')} "
          f"bear={sum(1 for z in fvgs if z['kind']=='FVG_BEAR')})  total={len(zones)}")
    print(f"fractal swings(5/5)={len(swings)}  prominent(>=2ATR)={len(proms)}")

    # per-zone verdicts
    for name, band, b0, b1, side in spec["zones"]:
        if b1 < sessions[0] or b0 > sessions[-1]:
            print(f"  {name:12s} band={band}  -> OUT-OF-DATA (window {sessions[0]}..{sessions[-1]})")
            continue
        for tag, sd in (("any-side", None), ("side-ok ", side)):
            verdict, best = match(zones, band, b0, b1, sessions, sd)
            if best:
                z, f, inwin = best
                print(f"  {name:12s} band={band} [{tag}] -> {verdict}  our={z['det']}/{z['kind']} "
                      f"[{z['lo']:.1f},{z['hi']:.1f}] born={z['born']} cover={f:.0%} inwin={inwin} q={z['q']:.2f}")
            else:
                print(f"  {name:12s} band={band} [{tag}] -> {verdict} (no overlapping zone)")
        uc = union_cover(zones, band, b0, b1, sessions, side)
        print(f"  {name:12s} union cover by side-correct in-window zones = {uc:.0%}")

    # noise + genuine proxy + filters
    stats = dict(total=len(zones), genuine=0, no_retest=0, f_swing=0, f_delay=0, f_both=0)
    kept_zones = {"f_swing": [], "f_delay": [], "f_both": []}
    for z in zones:
        t = first_retest(z, df)
        z["retest_i"] = t
        if t is None:
            stats["no_retest"] += 1
        r = reaction_ok(z, t, df, atr)
        z["genuine"] = r
        if r:
            stats["genuine"] += 1
        fs = near_prom_swing(z, proms)
        fd = revisit_delay_ok(z, t, bars_hr)
        z["f_swing"], z["f_delay"] = fs, fd
        if fs: stats["f_swing"] += 1; kept_zones["f_swing"].append(z)
        if fd: stats["f_delay"] += 1; kept_zones["f_delay"].append(z)
        if fs and fd: stats["f_both"] += 1; kept_zones["f_both"].append(z)
    print(f"  noise: total={stats['total']}  genuine(2ATR first-retest reaction)={stats['genuine']}"
          f"  never-retested={stats['no_retest']}")
    print(f"  filters: swing-adjacent={stats['f_swing']}  delay>=1hr={stats['f_delay']}  both={stats['f_both']}")

    # do filters keep the user's matched zones?
    for name, band, b0, b1, side in spec["zones"]:
        if b1 < sessions[0] or b0 > sessions[-1]:
            continue
        for tag, sd in (("any-side", None), ("side-ok", side)):
            verdict, best = match(zones, band, b0, b1, sessions, sd)
            if best and verdict in ("FOUND", "PARTIAL"):
                z = best[0]
                print(f"    {name} [{tag}]: matched zone survives swing-filter={z['f_swing']} "
                      f"delay-filter={z['f_delay']} genuine={z['genuine']}")

    # dump all zones for the report
    print("  ALL ZONES:")
    for z in sorted(zones, key=lambda z: z["born"]):
        print(f"    {z['det']:6s} {z['kind']:8s} [{z['lo']:7.1f},{z['hi']:7.1f}] born={z['born']} "
              f"ev={z['ev_ts']} q={z['q']:.2f} retest_i={z['retest_i']} genuine={z['genuine']} "
              f"fs={z['f_swing']} fd={z['f_delay']}")

    if sym == "HINDUNILVR":
        print("  SWINGS (all):")
        for s in swings:
            p = swing_prominence(s, df)
            a = atr[s["i"]]
            print(f"    {s['kind']:7s} {s['ts']}  px={s['px']:.1f}  prom={p:.1f} "
                  f"atr={a and round(a,1)}  prominent={a is not None and p >= 2*a}")
        print("  USER SWING CHECK:")
        for name, kind, band, d0, d1 in USER_SWINGS:
            hits = [s for s in swings if s["kind"] == kind and band[0] <= s["px"] <= band[1]
                    and d0 - timedelta(days=4) <= s["ts"].date() <= d1 + timedelta(days=4)]
            ph = [s for s in hits if atr[s["i"]] and swing_prominence(s, df) >= 2 * atr[s["i"]]]
            print(f"    {name}: found={len(hits)>0} ({[str(s['ts'])+'@'+format(s['px'],'.1f') for s in hits]}) "
                  f"prominent_among={len(ph)}")
