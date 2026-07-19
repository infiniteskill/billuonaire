#!/usr/bin/env python
"""DGRID shared lib: SMC zone detectors (ports of hulinv_run/chartpar_run),
flags F1-F4, trade sim with delivery costs, matched drift null.

Zone dict: sym-agnostic dict(type, dir, lo, hi, born_i, ev_i).
dir=+1 demand (fade long on retest), -1 supply (fade short).
"""
import numpy as np, pandas as pd, zlib
from collections import deque

R0, CAP, SLIP, STT, EXCH, DP = 500.0, 500_000.0, 2e-4, 1e-3, 4e-5, 15.0
NULL_DRAWS = 5

# ---------- ATR (repo formula: SMA of last 14 TRs incl current) ----------
def atr_series(H, L, C):
    n = len(H); out = np.full(n, np.nan)
    trs = deque(maxlen=14); s = 0.0
    for i in range(n):
        if i:
            tr = max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
            if len(trs) == trs.maxlen: s -= trs[0]
            trs.append(tr); s += tr
        if i >= 14: out[i] = s / 14
    return out

# ---------- ob_lux port ----------
def ob_lux(O, H, L, C, size=5, hv_mult=2.0):
    n = len(H); ev = []
    pH, pL = [], []
    trs = deque(maxlen=14); tr_sum = 0.0
    swH = swL = None; swHc = swLc = True
    for i in range(n):
        if i:
            tr = max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
            if len(trs) == trs.maxlen: tr_sum -= trs[0]
            trs.append(tr); tr_sum += tr
        atr = tr_sum / trs.maxlen if i >= trs.maxlen else None
        hv = atr is not None and H[i] - L[i] >= hv_mult * atr
        pH.append(L[i] if hv else H[i]); pL.append(H[i] if hv else L[i])
        if i >= size:
            p = i - size
            if H[p] > max(H[p + 1:i + 1]): swH, swHc = (H[p], p), False
            if L[p] < min(L[p + 1:i + 1]): swL, swLc = (L[p], p), False
        c, cp = C[i], C[i - 1] if i else None
        if swH and not swHc and c > swH[0] and (i == 0 or cp <= swH[0]):
            swHc = True
            idx = min(range(swH[1], i + 1), key=lambda j: pL[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            ev.append(dict(type="OB", dir=1, lo=lo, hi=hi, born_i=idx, ev_i=i))
        if swL and not swLc and c < swL[0] and (i == 0 or cp >= swL[0]):
            swLc = True
            idx = max(range(swL[1], i + 1), key=lambda j: pH[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            ev.append(dict(type="OB", dir=-1, lo=lo, hi=hi, born_i=idx, ev_i=i))
    return ev

# ---------- fvg_cb port (wick-valid 3-candle gap + displacement + adaptive thr) ----------
def fvg_cb(O, H, L, C, thr_mult=1.0):
    n = len(H); ev = []; rsum = 0.0
    atr = atr_series(H, L, C)
    for i in range(2, n):
        rsum += (H[i] - L[i]) / L[i] if L[i] else 0.0
        if np.isnan(atr[i]): continue
        thr = thr_mult * rsum / (i + 1)
        c1h, c1l, c2c = H[i - 2], L[i - 2], C[i - 1]
        lo, hi = c1h, L[i]
        if hi > lo and c2c > c1h and (hi - lo) / lo > thr:
            ev.append(dict(type="FVG", dir=1, lo=lo, hi=hi, born_i=i - 1, ev_i=i))
        lo, hi = H[i], c1l
        if hi > lo and c2c < c1l and (hi - lo) / lo > thr:
            ev.append(dict(type="FVG", dir=-1, lo=lo, hi=hi, born_i=i - 1, ev_i=i))
    return ev

# ---------- breaker (EmreKb MSB core port; born_i = origin candle) ----------
def breaker_msb(O, H, L, C, zz=9, fib=0.33, warm=25):
    n = len(H); trend, market = 1, 1
    hi = lo = None; highs, lows = [], []; l0p = h0p = None; out = []
    warm = max(warm, 14)
    for i in range(n):
        if hi is None or H[i] > hi[1]: hi = (i, H[i])
        if lo is None or L[i] < lo[1]: lo = (i, L[i])
        w0 = max(0, i - zz + 1); flipped = False
        if trend == 1 and L[i] <= min(L[w0:i + 1]):
            highs = (highs + [hi])[-2:]; flipped = True
        elif trend == -1 and H[i] >= max(H[w0:i + 1]):
            lows = (lows + [lo])[-2:]; flipped = True
        if flipped:
            trend = -trend; hi, lo = (i, H[i]), (i, L[i])
        if len(highs) == 2 and len(lows) == 2 and i >= warm:
            (h0i, h0), (h1i, h1) = highs[-1], highs[-2]
            (l0i, l0), (l1i, l1) = lows[-1], lows[-2]
            if not (l0 == l0p or h0 == h0p):
                if market == 1 and l0 < l1 and l0 < l1 - abs(h0 - l1) * fib:
                    market, l0p, h0p = -1, l0, h0
                    if h0 > h1:
                        j = next((j for j in range(l1i, max(0, h1i - zz) - 1, -1)
                                  if O[j] > C[j]), None)
                        if j is not None:
                            out.append(dict(type="BRK", dir=-1, lo=L[j], hi=H[j],
                                            born_i=j, ev_i=i))
                elif market == -1 and h0 > h1 and h0 > h1 + abs(h1 - l0) * fib:
                    market, l0p, h0p = 1, l0, h0
                    if l0 < l1:
                        j = next((j for j in range(h1i, max(0, l1i - zz) - 1, -1)
                                  if O[j] < C[j]), None)
                        if j is not None:
                            out.append(dict(type="BRK", dir=1, lo=L[j], hi=H[j],
                                            born_i=j, ev_i=i))
    return out

# ---------- iFVG: FVG closed beyond far edge -> flipped zone, born at invalidation ----
def ifvg_zones(fvgs, H, L, C):
    n = len(H); out = []
    for z in fvgs:
        bull = z["dir"] == 1
        k = next((t for t in range(z["ev_i"] + 1, n)
                  if (C[t] < z["lo"] if bull else C[t] > z["hi"])), None)
        if k is None: continue
        out.append(dict(type="IFVG", dir=-z["dir"], lo=z["lo"], hi=z["hi"],
                        born_i=k, ev_i=k))
    return out

# ---------- fractal swings + EQ pools + sweeps (task spec, hulinv port) ----------
def fractal_swings(H, L, N=5):
    n = len(H); out = []
    for i in range(N, n - N):
        wh = [H[j] for j in range(i - N, i + N + 1) if j != i]
        wl = [L[j] for j in range(i - N, i + N + 1) if j != i]
        if all(H[i] > v for v in wh): out.append(("H", i, H[i]))
        if all(L[i] < v for v in wl): out.append(("L", i, L[i]))
    return out

def sweep_events(swings, H, L, C, atr, tol_mult=0.25, confirm_lag=5):
    """First sweep of each EQ pool: (bar, aligned_dir). EQL sweep -> +1, EQH -> -1."""
    n = len(H); first_atr = atr[~np.isnan(atr)]
    first_atr = first_atr[0] if len(first_atr) else 0.0
    out = []
    for kind, take_hi, ad in (("H", True, -1), ("L", False, 1)):
        pts = sorted([s for s in swings if s[0] == kind], key=lambda s: s[2])
        pools, cur, anchor = [], [], None
        for s in pts:
            a = atr[s[1]] if not np.isnan(atr[s[1]]) else first_atr
            tol = tol_mult * (a or 0)
            if cur and abs(s[2] - anchor) <= tol: cur.append(s)
            else:
                if len(cur) >= 2: pools.append(cur)
                cur, anchor = [s], s[2]
        if len(cur) >= 2: pools.append(cur)
        for g in pools:
            level = max(x[2] for x in g) if take_hi else min(x[2] for x in g)
            start = min(n, max(x[1] for x in g) + confirm_lag + 1)
            hit = next((t for t in range(start, n)
                        if ((H[t] > level and C[t] < level) if take_hi
                            else (L[t] < level and C[t] > level))), None)
            if hit is not None: out.append((hit, ad))
    return out

# ---------- signal build: first retest -> next-bar-open entry + flags ----------
def build_signals(O, H, L, C, atr, zones, sweeps, period_id, htf_live):
    """period_id: array of ints per bar (F1). htf_live(bar_i, dir, mid)->bool (F2).
    Returns list of (e, dir, sd_atr, type, F1, F2, F3, F4)."""
    n = len(H)
    sw_by_dir = {1: sorted(s for s, d in sweeps if d == 1),
                 -1: sorted(s for s, d in sweeps if d == -1)}
    sigs, seen = [], set()
    for z in zones:
        lo, hi, d = z["lo"], z["hi"], z["dir"]
        t = next((t for t in range(z["ev_i"] + 1, n)
                  if L[t] <= hi and H[t] >= lo), None)
        if t is None or t + 1 >= n: continue
        if (C[t] < lo if d == 1 else C[t] > hi): continue   # zone broken on the touch
        a = atr[t]
        if np.isnan(a) or a <= 0: continue
        e = t + 1
        key = (z["type"], d, e)
        if key in seen: continue
        seen.add(key)
        b = z["born_i"]
        f1 = period_id[b] < period_id[t]
        f2 = htf_live(t, d, (lo + hi) / 2)
        f3 = any(s <= b <= s + 3 for s in sw_by_dir[d])
        f4 = (b >= 1 and not np.isnan(atr[b])
              and abs(O[b] - C[b - 1]) >= 0.5 * atr[b])
        sigs.append((e, d, a, z["type"], f1, f2, f3, f4))
    return sigs

# ---------- trade sim: gap-through fills at actual open, delivery costs ----------
def sim_trade(O, H, L, C, e, d, sd, tgtR, N):
    n = len(H); ent = O[e]
    stop, tgt = ent - d * sd, ent + d * tgtR * sd
    last = min(e + N, n) - 1; ex = None
    for b in range(e, last + 1):
        o = O[b]
        if b > e:
            if d * (o - stop) <= 0: ex = o; break
            if d * (o - tgt) >= 0: ex = o; break
        if d == 1:
            if L[b] <= stop: ex = stop; break
            if H[b] >= tgt: ex = tgt; break
        else:
            if H[b] >= stop: ex = stop; break
            if L[b] <= tgt: ex = tgt; break
    if ex is None: ex = C[last]
    qty = min(R0 / sd, CAP / ent)
    Rr = qty * sd
    pnl = d * (ex - ent) * qty
    cost = (SLIP + STT + EXCH) * qty * (ent + ex) + DP
    return pnl / Rr, cost / Rr

# ---------- matched drift null (two variants, same draws) ----------
def null_net(O, H, L, C, atr, pool, e, d, k, tgtR, N, seed, sd_real_pct):
    """pool: eligible entry bars in same (sym, quarter). Returns (null_atr, null_vol):
    null_atr = stop from the null bar's own ATR (task spec); null_vol = stop same
    %-of-price as the real trade (kills the ATR-denominated drift-dilution artifact)."""
    if not len(pool): return np.nan, np.nan
    rng = np.random.default_rng(seed)
    ta = tv = 0.0; m = 0
    for _ in range(NULL_DRAWS):
        e2 = int(pool[rng.integers(len(pool))])
        sd = k * atr[e2 - 1]
        g, c = sim_trade(O, H, L, C, e2, d, sd, tgtR, N)
        ta += g - c
        g2, c2 = sim_trade(O, H, L, C, e2, d, sd_real_pct * O[e2], tgtR, N)
        tv += g2 - c2; m += 1
    return ta / m, tv / m

def seed_of(sym, typ, e, k, cfg):
    return zlib.crc32(f"{sym}|{typ}|{e}|{k}|{cfg}".encode()) & 0xFFFFFFFF

def symhalf(sym):
    return zlib.crc32(sym.encode()) % 2
