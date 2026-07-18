"""Build CAUSAL daily POIs (OB / FVG / swing S/R) and tag each intraday signal.

Causality: for a signal on session D, only daily bars with date < D are used —
both for POI formation (form_idx <= j) and invalidation (kill_idx > j), where
j = index of last daily bar strictly before D.

POI rules (simplified parity rules):
- OB:   displacement bar i with body >= 1.5*ATR14[i-1]; zone = range of the last
        opposite-color candle within 5 bars back; live until daily close beyond
        far edge (bull: close < zone_lo, bear: close > zone_hi).
- FVG:  3-candle gap >= 0.3*ATR14[i-1]; bull: low[i] > high[i-2]; live until
        daily close beyond far edge (bull: close < zone_lo).
- SWING: 2-2 fractal high/low, confirmed at i+2; level zone (zero width);
        live until daily close beyond the level.

Tag: direction-consistent only (bull zone -> LONG, bear zone -> SHORT);
inside = entry within [lo - 0.25*ATR14[j], hi + 0.25*ATR14[j]].
"""
import numpy as np
import pandas as pd
from pathlib import Path

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")

bars = pd.read_parquet(SP / "daily2y.parquet")
sig = pd.read_parquet(SP / "signals60.parquet",
                      columns=["detector", "symbol", "session", "direction", "entry", "hit", "b_hit"])
sig = sig.reset_index().rename(columns={"index": "sig_id"})

OB_DISP_K, FVG_MIN_K, TOL_K = 1.5, 0.3, 0.25
NEVER = 10**9


def zones_for_symbol(o, h, l, c):
    """Return list of dicts: type, dir, lo, hi, form_idx, kill_idx."""
    n = len(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
    zones, seen = [], set()

    def add(zt, zd, lo, hi, form, origin):
        key = (zt, zd, round(lo, 4), round(hi, 4), origin)
        if key in seen:
            return
        seen.add(key)
        far_lo = zd == 1  # bull zone dies on close < lo; bear dies on close > hi
        kill = NEVER
        for j in range(form + 1, n):
            if (far_lo and c[j] < lo) or (not far_lo and c[j] > hi):
                kill = j
                break
        zones.append((zt, zd, lo, hi, form, kill))

    body = np.abs(c - o)
    for i in range(15, n):
        a = atr[i - 1]
        if not np.isfinite(a) or a <= 0:
            continue
        # --- OB: displacement bar i
        if body[i] >= OB_DISP_K * a:
            up = c[i] > o[i]
            for k in range(i - 1, max(i - 6, -1), -1):
                if (up and c[k] < o[k]) or (not up and c[k] > o[k]):
                    add("ob", 1 if up else -1, l[k], h[k], i, k)
                    break
        # --- FVG: 3-candle gap ending at i
        if i >= 2:
            if l[i] - h[i - 2] >= FVG_MIN_K * a:
                add("fvg", 1, h[i - 2], l[i], i, i)
            if l[i - 2] - h[i] >= FVG_MIN_K * a:
                add("fvg", -1, h[i], l[i - 2], i, i)
        # --- SWING 2-2 fractal centered at i-2, confirmed at i
        m = i - 2
        if m >= 2:
            if h[m] > max(h[m - 2], h[m - 1]) and h[m] > max(h[m + 1], h[m + 2]):
                add("swing", -1, h[m], h[m], i, m)  # resistance -> SHORT
            if l[m] < min(l[m - 2], l[m - 1]) and l[m] < min(l[m + 1], l[m + 2]):
                add("swing", 1, l[m], l[m], i, m)   # support -> LONG
    return zones, atr


TYPES = ["ob", "fvg", "swing"]
out = []
no_hist = 0
for sym, g in sig.groupby("symbol", sort=True):
    b = bars[bars.symbol == sym].sort_values("date")
    if len(b) < 30:
        no_hist += len(g)
        for _, r in g.iterrows():
            out.append((r.sig_id, False, False, "", -1, False, False, False, False))
        continue
    dates = b.date.dt.strftime("%Y-%m-%d").to_numpy()
    o, h, l, c = (b[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    zl, atr = zones_for_symbol(o, h, l, c)
    zt = np.array([z[0] for z in zl])
    zd = np.array([z[1] for z in zl])
    zlo = np.array([z[2] for z in zl])
    zhi = np.array([z[3] for z in zl])
    zform = np.array([z[4] for z in zl])
    zkill = np.array([z[5] for z in zl])

    for sess, gs in g.groupby("session", sort=True):
        j = int(np.searchsorted(dates, sess)) - 1  # last bar strictly before session
        if j < 15 or not np.isfinite(atr[j]) or atr[j] <= 0 or len(zl) == 0:
            for _, r in gs.iterrows():
                out.append((r.sig_id, False, False, "", -1, False, False, False, False))
            continue
        tol = TOL_K * atr[j]
        live = (zform <= j) & (zkill > j)
        for _, r in gs.iterrows():
            m = live & (zd == r.direction) & (zlo - tol <= r.entry) & (r.entry <= zhi + tol)
            if not m.any():
                out.append((r.sig_id, True, False, "", -1, False, False, False, False))
                continue
            types = set(zt[m])
            ptype = next(t for t in TYPES if t in types)
            age = int((j - zform[m]).min())
            deep = bool(((zlo[m] <= r.entry) & (r.entry <= zhi[m]) & (zhi[m] > zlo[m])).any())
            out.append((r.sig_id, True, True, ptype, age,
                        "ob" in types, "fvg" in types, "swing" in types, deep))

tags = pd.DataFrame(out, columns=["sig_id", "has_daily", "in_daily_poi", "poi_type",
                                  "poi_age_days", "in_ob", "in_fvg", "in_swing", "deep"])
tags.to_parquet(SP / "dailypoi_tags.parquet", index=False)
print(f"signals={len(tags)} no_hist={no_hist} has_daily={tags.has_daily.mean():.3f} "
      f"in_poi={tags.in_daily_poi.mean():.4f}")
print(tags[tags.in_daily_poi].poi_type.value_counts())
print("type booleans:", tags.in_ob.mean(), tags.in_fvg.mean(), tags.in_swing.mean())
