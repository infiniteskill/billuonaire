#!/usr/bin/env python
"""h1grid: shared constructors — verified ports from dev/research/hulinv_run.py /
chartpar_run.py (ob_lux, fvg_cb, fractal 5/5 swings, breaker EmreKb, EQ pools
0.25xATR + sweeps), plus session/D1 helpers for the H1/2H grid sweep."""
import numpy as np
import pandas as pd
from collections import deque

# ---------------- trailing ATR (repo formula: SMA of last 14 TRs, incl. current bar)
def atr_series(H, L, C):
    n = len(H); out = [None] * n
    trs = deque(maxlen=14); s = 0.0
    for i in range(n):
        if i:
            tr = max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
            if len(trs) == trs.maxlen:
                s -= trs[0]
            trs.append(tr); s += tr
        if i >= 14:
            out[i] = s / 14
    return out

# ---------------- ob_lux replication (chartpar port)
def ob_lux(O, H, L, C, size=5, hv_mult=2.0):
    n = len(H); events = []
    pH, pL = [], []
    trs = deque(maxlen=14); tr_sum = 0.0
    swH = swL = None; swHc = swLc = True
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
            events.append(dict(kind="OB", d=1, lo=lo, hi=hi, born_i=idx, ev_i=i))
        if swL and not swLc and c < swL[0] and (i == 0 or cp >= swL[0]):
            swLc = True
            idx = max(range(swL[1], i + 1), key=lambda j: pH[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            events.append(dict(kind="OB", d=-1, lo=lo, hi=hi, born_i=idx, ev_i=i))
    return events

# ---------------- fvg_cb replication (chartpar port; wick-valid retests downstream)
def fvg_cb(O, H, L, C, thr_mult=1.0):
    n = len(H); events = []
    rsum = 0.0
    atr = atr_series(H, L, C)
    for i in range(2, n):
        rsum += (H[i] - L[i]) / L[i] if L[i] else 0.0
        if atr[i] is None:
            continue
        thr = thr_mult * rsum / (i + 1)
        c1h, c1l, c2c = H[i - 2], L[i - 2], C[i - 1]
        lo, hi = c1h, L[i]
        if hi > lo and c2c > c1h and (hi - lo) / lo > thr:
            events.append(dict(kind="FVG", d=1, lo=lo, hi=hi, born_i=i - 1, ev_i=i))
        lo, hi = H[i], c1l
        if hi > lo and c2c < c1l and (hi - lo) / lo > thr:
            events.append(dict(kind="FVG", d=-1, lo=lo, hi=hi, born_i=i - 1, ev_i=i))
    return events

# ---------------- fractal swings (5/5)
def fractal_swings(H, L, N=5):
    n = len(H); out = []
    for i in range(N, n - N):
        win = range(i - N, i + N + 1)
        if all(H[i] > H[j] for j in win if j != i):
            out.append(dict(kind="H", i=i, px=H[i]))
        if all(L[i] < L[j] for j in win if j != i):
            out.append(dict(kind="L", i=i, px=L[i]))
    return out

# ---------------- breaker (EmreKb MSB core; hulinv port + origin index kept)
def breaker_msb(O, H, L, C, zz=9, fib=0.33, warm=25):
    n = len(H)
    trend, market = 1, 1
    hi = lo = None
    highs, lows = [], []
    l0p = h0p = None
    boxes, fired = [], []
    warm = max(warm, 14)
    for i in range(n):
        if hi is None or H[i] > hi[1]: hi = (i, H[i])
        if lo is None or L[i] < lo[1]: lo = (i, L[i])
        w0 = max(0, i - zz + 1)
        flipped = False
        if trend == 1 and L[i] <= min(L[w0:i + 1]):
            highs = (highs + [hi])[-2:]; flipped = True
        elif trend == -1 and H[i] >= max(H[w0:i + 1]):
            lows = (lows + [lo])[-2:]; flipped = True
        if flipped:
            trend = -trend
            hi, lo = (i, H[i]), (i, L[i])
        if len(highs) == 2 and len(lows) == 2 and i >= warm:
            (h0i, h0), (h1i, h1) = highs[-1], highs[-2]
            (l0i, l0), (l1i, l1) = lows[-1], lows[-2]
            if not (l0 == l0p or h0 == h0p):
                if market == 1 and l0 < l1 and l0 < l1 - abs(h0 - l1) * fib:
                    market, l0p, h0p = -1, l0, h0
                    if h0 > h1:  # swing high swept -> bearish breaker
                        j = next((j for j in range(l1i, max(0, h1i - zz) - 1, -1)
                                  if O[j] > C[j]), None)
                        if j is not None:
                            boxes.append(dict(top=H[j], bot=L[j], d=-1, born=i,
                                              origin_i=j, fired=False))
                elif market == -1 and h0 > h1 and h0 > h1 + abs(h1 - l0) * fib:
                    market, l0p, h0p = 1, l0, h0
                    if l0 < l1:  # swing low swept -> bullish breaker
                        j = next((j for j in range(h1i, max(0, l1i - zz) - 1, -1)
                                  if O[j] < C[j]), None)
                        if j is not None:
                            boxes.append(dict(top=H[j], bot=L[j], d=1, born=i,
                                              origin_i=j, fired=False))
        keep = []
        for b in boxes:
            if (b["d"] == 1 and C[i] < b["bot"]) or (b["d"] == -1 and C[i] > b["top"]):
                continue
            if not b["fired"] and i > b["born"] and (
                    b["bot"] <= C[i] < b["top"] if b["d"] == 1 else b["bot"] < C[i] <= b["top"]):
                b["fired"] = True
                fired.append(dict(kind="BREAKER", d=b["d"], lo=b["bot"], hi=b["top"],
                                  born_i=b["origin_i"], ev_i=b["born"], retest_i=i))
            keep.append(b)
        boxes = keep
    return fired

# ---------------- EQ pools (0.25xATR cluster of >=2 same-side 5/5 swings) + sweep events
def sweep_events(swings, H, L, C, atr, tol_mult=0.25, lag=5):
    n = len(H)
    first_atr = next((a for a in atr if a is not None), None)
    events = []  # (bar_t, side) side=+1 EQL-sweep (bullish), -1 EQH-sweep (bearish)
    for kind, take_hi in (("H", True), ("L", False)):
        pts = sorted([s for s in swings if s["kind"] == kind], key=lambda s: s["px"])
        pools, cur, anchor = [], [], None
        for s in pts:
            a = atr[s["i"]] if atr[s["i"]] is not None else first_atr
            tol = tol_mult * (a or 0)
            if cur and abs(s["px"] - anchor) <= tol:
                cur.append(s)
            else:
                if len(cur) >= 2: pools.append(cur)
                cur, anchor = [s], s["px"]
        if len(cur) >= 2: pools.append(cur)
        for g in pools:
            level = max(x["px"] for x in g) if take_hi else min(x["px"] for x in g)
            start = min(n, max(x["i"] for x in g) + lag + 1)
            hit = next((t for t in range(start, n)
                        if ((H[t] > level and C[t] < level) if take_hi
                            else (L[t] < level and C[t] > level))), None)
            if hit is not None:
                events.append((hit, -1 if take_hi else 1))
    return sorted(events)

# ---------------- retest / invalidation helpers (wick-valid touch, close-kill)
def first_touch(z, H, L, start):
    """first bar >= start whose wick overlaps [lo,hi]"""
    lo, hi = z["lo"], z["hi"]
    for t in range(start, len(H)):
        if L[t] <= hi and H[t] >= lo:
            return t
    return None

def invalidation_bar(z, C, start):
    """first close beyond far edge (bull: close<lo, bear: close>hi)"""
    lo, hi, d = z["lo"], z["hi"], z["d"]
    for t in range(start, len(C)):
        if (d == 1 and C[t] < lo) or (d == -1 and C[t] > hi):
            return t
    return None

# ---------------- resampling
def to_2h(df):
    """pair H1 bars within each session: bucket = idx_in_session // 2 (4 buckets/day)"""
    d = df.copy()
    d["date"] = d.ts.dt.date
    d["bkt"] = d.groupby("date").cumcount() // 2
    g = d.groupby(["date", "bkt"], sort=True)
    out = pd.DataFrame({"ts": g.ts.first(), "open": g.open.first(), "high": g.high.max(),
                        "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum()}).reset_index(drop=True)
    return out.sort_values("ts").reset_index(drop=True)

def to_daily(df):
    d = df.copy()
    d["date"] = d.ts.dt.date
    g = d.groupby("date", sort=True)
    return pd.DataFrame({"date": list(g.groups.keys()), "open": g.open.first().values,
                         "high": g.high.max().values, "low": g.low.min().values,
                         "close": g.close.last().values}).reset_index(drop=True)

def d1_zones(daily):
    """D1 OB+FVG with liveness window for F2 nesting. Causal: zone known after ev
    date's close; live until first daily close beyond far edge."""
    O, H, L, C = (daily[c].tolist() for c in ("open", "high", "low", "close"))
    dates = daily.date.tolist()
    zs = fvg_cb(O, H, L, C) + ob_lux(O, H, L, C)
    out = []
    for z in zs:
        inv = invalidation_bar(z, C, z["ev_i"] + 1)
        out.append(dict(lo=z["lo"], hi=z["hi"], d=z["d"], ev_date=dates[z["ev_i"]],
                        inv_date=dates[inv] if inv is not None else None))
    return out
