"""Refined runner: band-aware matching, cluster spans, K=5 bonus, lag stats."""
import numpy as np, pandas as pd
from ext_zigzag import (wilder_atr, zigzag, fractal_33, load_chart_a, load_chart_b,
                        TARGETS_A, TARGETS_B)

def cluster_span(df, pivots):
    # recompute cluster bar index range per pivot (mirror of band logic)
    h, l = df["high"].values, df["low"].values; n = len(df)
    spans = []
    for j, p in enumerate(pivots):
        a = None
        import ext_zigzag
        atr = p._atr  # attached below
        half = 0.5 * atr
        lo_b = pivots[j-1].idx if j > 0 else 0
        hi_b = pivots[j+1].idx if j < len(pivots)-1 else n-1
        arr = h if p.side == "H" else l
        s = e = p.idx
        if p.side == "H":
            while s-1 > lo_b and arr[s-1] >= p.price - half: s -= 1
            while e+1 < hi_b and arr[e+1] >= p.price - half: e += 1
        else:
            while s-1 > lo_b and arr[s-1] <= p.price + half: s -= 1
            while e+1 < hi_b and arr[e+1] <= p.price + half: e += 1
        spans.append((df["ts"].iloc[s], df["ts"].iloc[e]))
    return spans

def match2(pivots, spans, targets, tol_days=3, tol_pct=1.2):
    """price: distance from target price to pivot band (pct). date: cluster span
    padded +-tol_days must overlap target range."""
    used, rows = set(), []
    for tid, side, price, d0, d1 in targets:
        t0 = pd.Timestamp(d0, tz="Asia/Kolkata")
        t1 = pd.Timestamp(d1, tz="Asia/Kolkata") + pd.Timedelta(hours=23)
        best = None
        for j, p in enumerate(pivots):
            if j in used or p.side != side: continue
            s0 = spans[j][0] - pd.Timedelta(days=tol_days)
            s1 = spans[j][1] + pd.Timedelta(days=tol_days)
            if s1 < t0 or s0 > t1: continue
            lo, hi = p.band
            d = 0.0 if lo <= price <= hi else min(abs(price-lo), abs(price-hi))/price*100
            if d > tol_pct: continue
            if best is None or d < best[1]: best = (j, d)
        if best: used.add(best[0]); rows.append((tid, *best))
        else: rows.append((tid, None, None))
    return rows, [j for j in range(len(pivots)) if j not in used]

def nearest_miss(pivots, spans, df, target):
    tid, side, price, d0, d1 = target
    t0 = pd.Timestamp(d0, tz="Asia/Kolkata")
    out = []
    for j, p in enumerate(pivots):
        if p.side != side: continue
        ts = df["ts"].iloc[p.idx]
        dd = abs((ts - t0).days)
        dp = abs(p.price - price)/price*100
        out.append((dd+dp, j, ts, p.price, dp, dd))
    out.sort()
    return out[:2]

def run(df, atr, targets, name, Ks=(4,5,6,8,10)):
    res = {}
    for K in Ks:
        piv = zigzag(df, K, atr)
        for p in piv: p._atr = atr[p.idx]
        spans = cluster_span(df, piv)
        rows, extras = match2(piv, spans, targets)
        tp = sum(1 for r in rows if r[1] is not None)
        fp, fn = len(extras), len(rows)-tp
        f1 = 2*tp/(2*tp+fn+fp) if tp else 0.0
        lags = [p.confirm_idx-p.idx for p in piv if p.confirm_idx is not None]
        res[K] = dict(piv=piv, spans=spans, rows=rows, extras=extras, tp=tp, fp=fp,
                      fn=fn, f1=f1, lag_med=float(np.median(lags)), lag_max=max(lags))
        print(f"\n== {name} K={K}: {tp}/8 matched, {fp} extras, F1={f1:.3f}, "
              f"lag med={np.median(lags):.0f} max={max(lags)} bars ==")
        m = {j: tid for tid, j, _ in rows if j is not None}
        for j, p in enumerate(piv):
            ts = df["ts"].iloc[p.idx]; sp = spans[j]
            lag = p.confirm_idx-p.idx if p.confirm_idx is not None else None
            tag = m.get(j, "extra")
            fl = ("M" if p.master else "")+("b" if p.boundary else "")+("?" if p.pending else "")
            print(f"  [{j:2d}] {p.side} {ts:%m-%d %H:%M} {p.price:7.1f} "
                  f"band=[{p.band[0]:7.1f},{p.band[1]:7.1f}] span={sp[0]:%m-%d}..{sp[1]:%m-%d} "
                  f"rank={p.rank_atr:4.1f} lag={str(lag):>4} {fl:3s} <- {tag}")
        for r in rows:
            if r[1] is None:
                t = [t for t in targets if t[0]==r[0]][0]
                print(f"  MISS {r[0]}: nearest same-side:")
                for _, j, ts, pr, dp, dd in nearest_miss(piv, spans, df, t):
                    print(f"        [{j}] {ts:%m-%d} {pr:.1f} dprice={dp:.2f}% ddays={dd}")
    return res

dfa = load_chart_a(); atr_a = wilder_atr(dfa)
dfb_full = load_chart_b()
w0 = pd.Timestamp("2025-11-04", tz="Asia/Kolkata")
w1 = pd.Timestamp("2026-03-16 23:59", tz="Asia/Kolkata")
lead = pd.Timestamp("2025-10-01", tz="Asia/Kolkata")
dfl = dfb_full[(dfb_full["ts"]>=lead)&(dfb_full["ts"]<=w1)].reset_index(drop=True)
atr_l = wilder_atr(dfl); mask = (dfl["ts"]>=w0).values
dfb = dfl[mask].reset_index(drop=True); atr_b = atr_l[mask]

print("#### CHART A 30m ####"); ra = run(dfa, atr_a, TARGETS_A, "A")
print("\n#### CHART B H1 ####"); rb = run(dfb, atr_b, TARGETS_B, "B")
print("\n#### COMBINED ####")
for K in (4,5,6,8,10):
    tp = ra[K]["tp"]+rb[K]["tp"]; fn = ra[K]["fn"]+rb[K]["fn"]; fp = ra[K]["fp"]+rb[K]["fp"]
    print(f"K={K}: TP={tp}/16 FP={fp} F1={2*tp/(2*tp+fn+fp):.3f}")
nh, nl = fractal_33(dfa)
print(f"\nFractal 3/3 chart A: {nh} H + {nl} L = {nh+nl}")
print(f"ATR medians: A30m={np.nanmedian(atr_a):.1f}  B_H1={np.nanmedian(atr_b):.1f}")
