"""Taught-spec STRUCTURE tools (lessons 1,6,7,8,13,15).

- zigzag_pct: ext_zigzag causal zigzag, threshold = PCT*close[i] (percent-leg floor,
  TF-invariant ~4.7%) instead of K*ATR. Dual bands per confirmed pivot:
  band_wick (lesson 13: highest body edge -> wick extreme, self-scaling cluster)
  and band_atr (old 0.5*ATR cluster guess). Bands built only from bars <= confirm_idx.
- fractal internal swings 3/3 (confirm lag 3 bars) = minor pivots.
- structure_events: causal CHoCH/BOS state machine (major = zigzag pivot break,
  minor = internal pivot break) + premium/discount position in dealing range
  (hi = max last-2 confirmed major H, lo = min last-2 confirmed major L).
- po3: HTF (D1) candle classifier: body<0.35*range & dominant wick>0.5*range,
  predicted direction opposite the big wick.
"""
from __future__ import annotations
import numpy as np, pandas as pd

PCT = 0.047

def wilder_atr(h, l, c, n=14):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = np.full(len(tr), np.nan)
    if len(tr) < n: return atr
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)): atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    atr[: n - 1] = atr[n - 1]
    return atr

class Pivot:
    __slots__ = ("idx", "price", "side", "confirm_idx", "boundary", "pending",
                 "band_wick", "band_atr")
    def __init__(s, idx, price, side, confirm_idx=None, boundary=False, pending=False):
        s.idx, s.price, s.side, s.confirm_idx = idx, price, side, confirm_idx
        s.boundary, s.pending = boundary, pending
        s.band_wick = s.band_atr = (np.nan, np.nan)

def zigzag_pct(o, h, l, c, atr, pct=PCT):
    n = len(c); pivots = []
    imax = imin = 0; i = 1; state = None
    while i < n:
        if h[i] > h[imax]: imax = i
        if l[i] < l[imin]: imin = i
        k = pct * c[i]
        if h[i] - l[imin] >= k and imin < i:
            pivots.append(Pivot(imin, l[imin], "L", i, True)); state = "up"
            j0 = imin + 1; pend = j0 + int(np.argmax(h[j0:i + 1])); break
        if h[imax] - l[i] >= k and imax < i:
            pivots.append(Pivot(imax, h[imax], "H", i, True)); state = "down"
            j0 = imax + 1; pend = j0 + int(np.argmin(l[j0:i + 1])); break
        i += 1
    if state is None: return []
    last = pivots[-1]; last_confirmed = True; i += 1
    while i < n:
        k = pct * c[i]
        if state == "up":
            if h[i] > h[pend]: pend = i
            if l[i] < last.price:
                if h[pend] - l[i] >= k and pend > last.idx:
                    piv = Pivot(pend, h[pend], "H", i); pivots.append(piv)
                    last, last_confirmed = piv, True; state = "down"; pend = i
                else:
                    last.idx, last.price = i, l[i]
                    last.confirm_idx = None; last_confirmed = False; pend = i
            else:
                if not last_confirmed and h[i] - last.price >= k:
                    last.confirm_idx = i; last_confirmed = True
                if h[pend] - l[i] >= k and pend > last.idx:
                    piv = Pivot(pend, h[pend], "H", i); pivots.append(piv)
                    last, last_confirmed = piv, True; state = "down"
                    j0 = pend + 1; pend = j0 + int(np.argmin(l[j0:i + 1])) if j0 <= i else i
        else:
            if l[i] < l[pend]: pend = i
            if h[i] > last.price:
                if h[i] - l[pend] >= k and pend > last.idx:
                    piv = Pivot(pend, l[pend], "L", i); pivots.append(piv)
                    last, last_confirmed = piv, True; state = "up"; pend = i
                else:
                    last.idx, last.price = i, h[i]
                    last.confirm_idx = None; last_confirmed = False; pend = i
            else:
                if not last_confirmed and last.price - l[i] >= k:
                    last.confirm_idx = i; last_confirmed = True
                if h[i] - l[pend] >= k and pend > last.idx:
                    piv = Pivot(pend, l[pend], "L", i); pivots.append(piv)
                    last, last_confirmed = piv, True; state = "up"
                    j0 = pend + 1; pend = j0 + int(np.argmax(h[j0:i + 1])) if j0 <= i else i
        i += 1
    if pend > last.idx:
        side = "H" if state == "up" else "L"
        pivots.append(Pivot(pend, h[pend] if state == "up" else l[pend], side, None, pending=True))
    for p in pivots:
        if p.confirm_idx is None: p.pending = True
    # bands (causal: bars in [prev_pivot .. min(next_pivot, confirm_idx)])
    for j, p in enumerate(pivots):
        if p.pending: continue
        lo_b = pivots[j - 1].idx if j > 0 else 0
        hi_b = pivots[j + 1].idx if j < len(pivots) - 1 else n - 1
        hi_b = min(hi_b, p.confirm_idx)
        # wick band (lesson 13): highest body edge among cluster -> wick extreme
        if p.side == "H":
            bt = max(o[p.idx], c[p.idx]); s = e = p.idx
            while s - 1 > lo_b and h[s - 1] >= bt:
                s -= 1; bt = max(bt, o[s], c[s])
            while e + 1 < hi_b and h[e + 1] >= bt:
                e += 1; bt = max(bt, o[e], c[e])
            p.band_wick = (bt, p.price)
        else:
            bt = min(o[p.idx], c[p.idx]); s = e = p.idx
            while s - 1 > lo_b and l[s - 1] <= bt:
                s -= 1; bt = min(bt, o[s], c[s])
            while e + 1 < hi_b and l[e + 1] <= bt:
                e += 1; bt = min(bt, o[e], c[e])
            p.band_wick = (p.price, bt)
        # old ATR band (0.5*ATR at pivot bar)
        half = 0.5 * atr[p.idx]; s = e = p.idx
        if p.side == "H":
            while s - 1 > lo_b and h[s - 1] >= p.price - half: s -= 1
            while e + 1 < hi_b and h[e + 1] >= p.price - half: e += 1
            p.band_atr = (float(h[s:e + 1].min()), p.price)
        else:
            while s - 1 > lo_b and l[s - 1] <= p.price + half: s -= 1
            while e + 1 < hi_b and l[e + 1] <= p.price + half: e += 1
            p.band_atr = (p.price, float(l[s:e + 1].max()))
    return pivots

def fractals(h, l, k=3):
    """3/3 fractal internal swings; returns lists of (confirm_idx, price, idx)."""
    n = len(h); hs, ls = [], []
    for m in range(k, n - k):
        w = np.r_[m - k:m, m + 1:m + k + 1]
        if (h[m] > h[w]).all(): hs.append((m + k, h[m], m))
        if (l[m] < l[w]).all(): ls.append((m + k, l[m], m))
    return hs, ls

def structure_events(o, h, l, c, atr, pct=PCT):
    """Causal CHoCH/BOS events. Returns (events, pivots).
    event = dict(t, kind in {CHOCH,BOS}, deg in {major,minor}, d in {+1,-1},
                 pos = position of close in dealing range (nan if no range), level)."""
    n = len(c)
    pivots = [p for p in zigzag_pct(o, h, l, c, atr, pct) if not p.pending]
    majH = [(p.confirm_idx, p.price) for p in pivots if p.side == "H"]
    majL = [(p.confirm_idx, p.price) for p in pivots if p.side == "L"]
    minH, minL = fractals(h, l)
    events = []
    iH = iL = imh = iml = 0
    lastH = []; lastL = []          # confirmed major H/L prices (append order)
    mh = ml = None                  # last confirmed minor swing high/low price
    bH = bL = bmh = bml = True      # broken flags (True = nothing to break)
    trend = 0
    for t in range(n):
        while iH < len(majH) and majH[iH][0] <= t:
            lastH.append(majH[iH][1]); bH = False
            if trend == 0: trend = -1
            iH += 1
        while iL < len(majL) and majL[iL][0] <= t:
            lastL.append(majL[iL][1]); bL = False
            if trend == 0: trend = 1
            iL += 1
        while imh < len(minH) and minH[imh][0] <= t:
            mh = minH[imh][1]; bmh = False; imh += 1
        while iml < len(minL) and minL[iml][0] <= t:
            ml = minL[iml][1]; bml = False; iml += 1
        if trend == 0: continue
        hi = max(lastH[-2:]) if lastH else np.nan
        lo = min(lastL[-2:]) if lastL else np.nan
        pos = (c[t] - lo) / (hi - lo) if lastH and lastL and hi > lo else np.nan
        if trend == 1:
            if not bmh and mh is not None and c[t] > mh: bmh = True  # with-trend minor, ignore
            if not bml and ml is not None and c[t] < ml:
                events.append(dict(t=t, kind="CHOCH", deg="minor", d=-1, pos=pos, level=ml)); bml = True
            if not bH and lastH and c[t] > lastH[-1]:
                events.append(dict(t=t, kind="BOS", deg="major", d=1, pos=pos, level=lastH[-1])); bH = True
            if not bL and lastL and c[t] < lastL[-1]:
                events.append(dict(t=t, kind="CHOCH", deg="major", d=-1, pos=pos, level=lastL[-1]))
                bL = True; trend = -1
        else:
            if not bml and ml is not None and c[t] < ml: bml = True
            if not bmh and mh is not None and c[t] > mh:
                events.append(dict(t=t, kind="CHOCH", deg="minor", d=1, pos=pos, level=mh)); bmh = True
            if not bL and lastL and c[t] < lastL[-1]:
                events.append(dict(t=t, kind="BOS", deg="major", d=-1, pos=pos, level=lastL[-1])); bL = True
            if not bH and lastH and c[t] > lastH[-1]:
                events.append(dict(t=t, kind="CHOCH", deg="major", d=1, pos=pos, level=lastH[-1]))
                bH = True; trend = 1
    return events, pivots

def po3_flags(o, h, l, c, body_max=0.35, wick_min=0.50):
    rng = h - l; body = np.abs(c - o)
    uw = h - np.maximum(o, c); lw = np.minimum(o, c) - l
    ok = rng > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        small = np.where(ok, body / rng < body_max, False)
        upd = np.where(ok, uw / rng > wick_min, False)
        lod = np.where(ok, lw / rng > wick_min, False)
    d = np.where(small & upd, -1, np.where(small & lod, 1, 0))
    return d  # per-candle: -1 big upper wick (pred down), +1 big lower wick (pred up), 0 none

def resample_d1(g):
    d = g.groupby(g["ts"].dt.date).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), ts=("ts", "first"))
    return d.reset_index(drop=True)

def splice_mask(o, c, thr=0.20):
    pc = np.roll(c, 1); pc[0] = c[0]
    return np.abs(o / pc - 1) > thr
