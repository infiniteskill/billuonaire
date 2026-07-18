"""NESTED FRACTAL CONFLUENCE — build per-signal nest flags (leak-free).

Daily nest:  L1 = signal in live dir-consistent daily zone (parity w/ dailypoi_build).
             L2 = L1 AND entry in live dir-consistent H1 OB/FVG whose midpoint sits
                  inside the matched daily zone +/- 0.25*daily-ATR14 (zone-in-zone).
             L3 = L2 AND m5_dir == h1_dir == daily_dir.
Controls:    L2' = entry in live dir-consistent H1 OB/FVG (daily ignored).
             L3' = all three directions agree (no zones).
Liquidity:   pools = unswept H1 2-2 fractal swings, equal-H/L clusters
             (within 0.15*ATR_H1), PDH/PDL, prior-week H/L.
             L1_liq_away / L1_liq_into = signal zone within 0.5*ATR_H1 of an UNSWEPT
             pool, trading away from / into it.
             L1_swept = pool swept (5m wick beyond + close back inside) within last
             6 H1 bars, signal fires in reclaim direction.
             L2_liq = L1_swept AND entry inside live dir-consistent H1 zone that
             overlaps that pool (+/-0.25*ATR_H1).  L3_liq = L2_liq AND h1_dir==m5_dir.

Directions (documented choice): close > SMA20 of closes => +1 else -1; 0 if <20 bars.
  daily_dir from daily bars strictly before session; h1_dir from closed H1 bars only.
H1 bars: session-anchored 5m->H1 (9:15..), final 15:15-15:30 stub merged into the
  14:15 bar => 6 bars/session (avoids stub bars poisoning ATR).
Causality: per signal only bars with end_time <= ts are used everywhere.
"""
import numpy as np
import pandas as pd
from pathlib import Path

SP = Path("/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
D5 = Path("/home/doom/Public/PROJECT/2026/trader/data/long5m")

OB_K, FVG_K, TOL_K = 1.5, 0.3, 0.25       # same as daily builder
EQ_K, LIQ_K, SWEEP_N = 0.15, 0.5, 6
NEVER = 10 ** 9

sig = pd.read_parquet(SP / "signals60.parquet",
                      columns=["detector", "symbol", "session", "ts", "direction",
                               "entry", "zone_lo", "zone_hi"])
sig = sig.reset_index().rename(columns={"index": "sig_id"})
sig["ts_dt"] = pd.to_datetime(sig.ts).dt.tz_localize(None)
import os
if os.environ.get("SYMS"):
    sig = sig[sig.symbol.isin(os.environ["SYMS"].split(","))]
daily = pd.read_parquet(SP / "daily2y.parquet")


def atr14(h, l, c):
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    return pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()


def sma_dir(c, w=20):
    s = pd.Series(c).rolling(w, min_periods=w).mean().to_numpy()
    d = np.where(c > s, 1, -1)
    d[~np.isfinite(s)] = 0
    return d


def daily_zones(o, h, l, c, atr):
    """Copy of dailypoi_build.zones_for_symbol rules (OB/FVG/SWING)."""
    n = len(c)
    zones, seen = [], set()

    def add(zt, zd, lo, hi, form, origin):
        key = (zt, zd, round(lo, 4), round(hi, 4), origin)
        if key in seen:
            return
        seen.add(key)
        far_lo = zd == 1
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
        if body[i] >= OB_K * a:
            up = c[i] > o[i]
            for k in range(i - 1, max(i - 6, -1), -1):
                if (up and c[k] < o[k]) or (not up and c[k] > o[k]):
                    add("ob", 1 if up else -1, l[k], h[k], i, k)
                    break
        if i >= 2:
            if l[i] - h[i - 2] >= FVG_K * a:
                add("fvg", 1, h[i - 2], l[i], i, i)
            if l[i - 2] - h[i] >= FVG_K * a:
                add("fvg", -1, h[i], l[i - 2], i, i)
        m = i - 2
        if m >= 2:
            if h[m] > max(h[m - 2], h[m - 1]) and h[m] > max(h[m + 1], h[m + 2]):
                add("swing", -1, h[m], h[m], i, m)
            if l[m] < min(l[m - 2], l[m - 1]) and l[m] < min(l[m + 1], l[m + 2]):
                add("swing", 1, l[m], l[m], i, m)
    return zones


def h1_zones(o, h, l, c, atr):
    """H1 OB (dies on close beyond far edge) + FVG (dies when wick fully fills gap)."""
    n = len(c)
    zones, seen = [], set()
    body = np.abs(c - o)

    def kill_close(zd, lo, hi, form):
        for j in range(form + 1, n):
            if (zd == 1 and c[j] < lo) or (zd == -1 and c[j] > hi):
                return j
        return NEVER

    def kill_fill(zd, lo, hi, form):
        for j in range(form + 1, n):
            if (zd == 1 and l[j] <= lo) or (zd == -1 and h[j] >= hi):
                return j
        return NEVER

    for i in range(15, n):
        a = atr[i - 1]
        if not np.isfinite(a) or a <= 0:
            continue
        if body[i] >= OB_K * a:
            up = c[i] > o[i]
            for k in range(i - 1, max(i - 6, -1), -1):
                if (up and c[k] < o[k]) or (not up and c[k] > o[k]):
                    key = ("ob", 1 if up else -1, k)
                    if key not in seen:
                        seen.add(key)
                        zd = 1 if up else -1
                        zones.append(("ob", zd, l[k], h[k], i, kill_close(zd, l[k], h[k], i)))
                    break
        if i >= 2:
            if l[i] - h[i - 2] >= FVG_K * a:
                zones.append(("fvg", 1, h[i - 2], l[i], i, kill_fill(1, h[i - 2], l[i], i)))
            if l[i - 2] - h[i] >= FVG_K * a:
                zones.append(("fvg", -1, h[i], l[i - 2], i, kill_fill(-1, h[i], l[i - 2], i)))
    return zones


def build_pools(h1h, h1l, h1atr, h1_end, b5_hi, b5_lo, b5_cl, b5_end):
    """Liquidity pools: (side, level, form_time, sweep_time, closeback_time).
    side=+1: highs (stops above; sweep = 5m high > level; reclaim SHORT)
    side=-1: lows  (stops below; sweep = 5m low  < level; reclaim LONG)
    Sweep/closeback detected on closed 5m bars (causal via end times)."""
    n = len(h1h)
    pools = []

    def sweep_of(side, level, t_from):
        i0 = np.searchsorted(b5_end, t_from, "left")
        if side == 1:
            idx = np.nonzero(b5_hi[i0:] > level)[0]
        else:
            idx = np.nonzero(b5_lo[i0:] < level)[0]
        if len(idx) == 0:
            return None, None
        s = i0 + idx[0]
        if side == 1:
            cb = np.nonzero(b5_cl[s:] < level)[0]
        else:
            cb = np.nonzero(b5_cl[s:] > level)[0]
        return b5_end[s], (b5_end[s + cb[0]] if len(cb) else None)

    def add(side, level, form_t, sweep_from):
        sw, cb = sweep_of(side, level, sweep_from)
        pools.append((side, level, form_t, sw, cb))

    # 2-2 fractal swings, confirmed at m+2; sweep search starts after swing bar m
    sw_hi, sw_lo = [], []          # (m, level) confirmed, in time order
    for m in range(2, n - 2):
        conf = m + 2
        if h1h[m] > max(h1h[m - 2], h1h[m - 1]) and h1h[m] > max(h1h[m + 1], h1h[m + 2]):
            add(1, h1h[m], h1_end[conf], h1_end[m])
            sw_hi.append((m, conf, h1h[m]))
        if h1l[m] < min(h1l[m - 2], h1l[m - 1]) and h1l[m] < min(h1l[m + 1], h1l[m + 2]):
            add(-1, h1l[m], h1_end[conf], h1_end[m])
            sw_lo.append((m, conf, h1l[m]))
    # equal highs/lows: new swing within 0.15*ATR of a prior unswept same-side swing
    for lst, side in ((sw_hi, 1), (sw_lo, -1)):
        for i in range(1, len(lst)):
            m, conf, lv = lst[i]
            a = h1atr[conf - 1] if conf >= 1 else np.nan
            if not np.isfinite(a) or a <= 0:
                continue
            for m2, conf2, lv2 in lst[:i]:
                if abs(lv - lv2) <= EQ_K * a:
                    # prior swing must still be unswept at confirmation of the later one
                    sw, _ = sweep_of(side, lv2, h1_end[m2])
                    if sw is not None and sw <= h1_end[conf]:
                        continue
                    ext = max(lv, lv2) if side == 1 else min(lv, lv2)
                    add(side, ext, h1_end[conf], h1_end[max(m, m2)])
                    break
    return pools


# ---------- per-symbol precomputation + per-signal flags ----------
rows = []
sig["session_dt"] = pd.to_datetime(sig.session)
daily["week"] = daily.date.dt.isocalendar().week.astype(int) + daily.date.dt.isocalendar().year.astype(int) * 100

for sym, g in sig.groupby("symbol", sort=True):
    # --- daily arrays
    db = daily[daily.symbol == sym].sort_values("date")
    d_dates = db.date.dt.strftime("%Y-%m-%d").to_numpy()
    d_o, d_h, d_l, d_c = (db[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    d_atr = atr14(d_h, d_l, d_c)
    d_dir = sma_dir(d_c)
    dz = daily_zones(d_o, d_h, d_l, d_c, d_atr) if len(db) >= 30 else []
    dzt = np.array([z[0] for z in dz]) if dz else np.empty(0, dtype=object)
    dzd = np.array([z[1] for z in dz], dtype=int) if dz else np.empty(0, int)
    dzlo = np.array([z[2] for z in dz]) if dz else np.empty(0)
    dzhi = np.array([z[3] for z in dz]) if dz else np.empty(0)
    dzf = np.array([z[4] for z in dz], dtype=int) if dz else np.empty(0, int)
    dzk = np.array([z[5] for z in dz], dtype=int) if dz else np.empty(0, int)

    # --- 5m bars -> H1
    b5 = pd.read_csv(D5 / f"{sym}.csv")
    b5["ts"] = pd.to_datetime(b5.ts).dt.tz_localize(None)
    b5 = b5.sort_values("ts").reset_index(drop=True)
    b5["end"] = b5.ts + pd.Timedelta(minutes=5)
    b5["sess"] = b5.ts.dt.strftime("%Y-%m-%d")
    mins = (b5.ts.dt.hour * 60 + b5.ts.dt.minute) - (9 * 60 + 15)
    b5["bucket"] = np.minimum(mins // 60, 5)
    h1 = (b5.groupby(["sess", "bucket"], sort=True)
            .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"),
                 c=("close", "last"), end=("end", "max")).reset_index())
    h1o, h1h_, h1l_, h1c = (h1[x].to_numpy(float) for x in ("o", "h", "l", "c"))
    h1_end = h1.end.to_numpy()
    h1atr = atr14(h1h_, h1l_, h1c)
    h1dir = sma_dir(h1c)
    hz = h1_zones(h1o, h1h_, h1l_, h1c, h1atr)
    hzd = np.array([z[1] for z in hz], dtype=int) if hz else np.empty(0, int)
    hzlo = np.array([z[2] for z in hz]) if hz else np.empty(0)
    hzhi = np.array([z[3] for z in hz]) if hz else np.empty(0)
    hzf = np.array([z[4] for z in hz], dtype=int) if hz else np.empty(0, int)
    hzk = np.array([z[5] for z in hz], dtype=int) if hz else np.empty(0, int)
    hzmid = (hzlo + hzhi) / 2 if hz else np.empty(0)

    b5_hi, b5_lo, b5_cl = b5.high.to_numpy(), b5.low.to_numpy(), b5.close.to_numpy()
    b5_end = b5.end.to_numpy()

    pools = build_pools(h1h_, h1l_, h1atr, h1_end, b5_hi, b5_lo, b5_cl, b5_end)
    # PDH/PDL + prior-week H/L from daily bars; sweep within current session/week
    sessions = sorted(g.session.unique())
    sess_week = {s: pd.Timestamp(s).isocalendar().week + pd.Timestamp(s).isocalendar().year * 100
                 for s in sessions}
    s5_start = {s: b5_end[b5.sess.to_numpy() == s].min() - np.timedelta64(5, "m")
                for s in b5.sess.unique()}
    wk_daily = daily[daily.symbol == sym]
    for s in sessions:
        j = int(np.searchsorted(d_dates, s)) - 1
        t0 = s5_start.get(s)
        if t0 is None:
            continue
        if j >= 0:
            for side, lv in ((1, d_h[j]), (-1, d_l[j])):
                pools.append(("PD", side, lv, t0))
        pw = wk_daily[wk_daily.week == sess_week[s] - 1]
        if len(pw):
            pools.append(("PW", 1, pw.high.max(), t0))
            pools.append(("PW", -1, pw.low.min(), t0))
    # normalize: session-scoped pools get sweep computed from t0 like the others
    norm = []
    for p in pools:
        if p[0] in ("PD", "PW"):
            _, side, lv, t0 = p
            i0 = np.searchsorted(b5_end, t0, "left")
            if side == 1:
                idx = np.nonzero(b5_hi[i0:] > lv)[0]
            else:
                idx = np.nonzero(b5_lo[i0:] < lv)[0]
            sw = cb = None
            if len(idx):
                si = i0 + idx[0]
                sw = b5_end[si]
                cbi = np.nonzero((b5_cl[si:] < lv) if side == 1 else (b5_cl[si:] > lv))[0]
                cb = b5_end[si + cbi[0]] if len(cbi) else None
            norm.append((side, lv, t0, sw, cb))
        else:
            norm.append(p)
    P_side = np.array([p[0] for p in norm], dtype=int) if norm else np.empty(0, int)
    P_lv = np.array([p[1] for p in norm]) if norm else np.empty(0)
    P_form = np.array([p[2] for p in norm]) if norm else np.empty(0, "datetime64[ns]")
    NAT = np.datetime64("2100-01-01")
    P_sw = np.array([p[3] if p[3] is not None else NAT for p in norm]) if norm else np.empty(0, "datetime64[ns]")
    P_cb = np.array([p[4] if p[4] is not None else NAT for p in norm]) if norm else np.empty(0, "datetime64[ns]")
    # H1 index containing each sweep time (for recency in H1 bars)
    P_sw_h1 = np.searchsorted(h1_end, P_sw, "left") if norm else np.empty(0, int)

    # --- per-signal
    gg = g.sort_values("ts_dt")
    ts_arr = gg.ts_dt.to_numpy()
    jh_arr = np.searchsorted(h1_end, ts_arr, "right")
    sess_arr = gg.session.to_numpy()
    jd_map = {s: int(np.searchsorted(d_dates, s)) - 1 for s in sessions}

    for (sid, det, sess, dirn, entry, zlo_s, zhi_s, ts, jh) in zip(
            gg.sig_id, gg.detector, gg.session, gg.direction, gg.entry,
            gg.zone_lo, gg.zone_hi, ts_arr, jh_arr):
        jd = jd_map[sess]
        ddir = int(d_dir[jd]) if jd >= 0 else 0
        hdir = int(h1dir[jh - 1]) if jh >= 20 else 0
        ha = h1atr[jh - 1] if jh >= 15 else np.nan
        da = d_atr[jd] if jd >= 14 else np.nan
        ok_h = np.isfinite(ha) and ha > 0
        ok_d = jd >= 15 and np.isfinite(da) and da > 0

        # daily match (parity with dailypoi tag)
        l1 = False
        dm = np.empty(0, int)
        if ok_d and len(dz):
            tol = TOL_K * da
            m = ((dzf <= jd) & (dzk > jd) & (dzd == dirn)
                 & (dzlo - tol <= entry) & (entry <= dzhi + tol))
            dm = np.nonzero(m)[0]
            l1 = len(dm) > 0

        # H1 zone match
        in_h1z = False
        hm = np.empty(0, int)
        if ok_h and len(hz) and jh >= 1:
            tolh = TOL_K * ha
            m = ((hzf <= jh - 1) & (hzk > jh - 1) & (hzd == dirn)
                 & (hzlo - tolh <= entry) & (entry <= hzhi + tolh))
            hm = np.nonzero(m)[0]
            in_h1z = len(hm) > 0

        # L2: zone-in-zone (h1 mid inside matched daily zone +/- 0.25*dATR)
        l2 = False
        if l1 and in_h1z:
            told = TOL_K * da
            for hi_ in hm:
                mid = hzmid[hi_]
                if np.any((dzlo[dm] - told <= mid) & (mid <= dzhi[dm] + told)):
                    l2 = True
                    break

        # liquidity pools
        liq_away = liq_into = swept_rec = l2_liq = False
        if ok_h and len(norm):
            formed = P_form <= ts
            unswept = formed & (P_sw > ts)
            if unswept.any():
                lv = P_lv[unswept]
                dist = np.maximum(0, np.maximum(zlo_s - lv, lv - zhi_s))
                near = dist <= LIQ_K * ha
                if near.any():
                    rel = np.sign(entry - lv[near])
                    liq_away = bool(np.any(rel == dirn))
                    liq_into = bool(np.any(rel == -dirn))
            # swept recently + closed back + reclaim direction (side==dirn*-1... high pool reclaim SHORT)
            sw_ok = formed & (P_sw <= ts) & (P_cb <= ts) & (P_side == -dirn) \
                & (jh - P_sw_h1 <= SWEEP_N)
            if sw_ok.any():
                swept_rec = True
                if in_h1z:
                    tolh = TOL_K * ha
                    for lv in P_lv[sw_ok]:
                        if np.any((hzlo[hm] - tolh <= lv) & (lv <= hzhi[hm] + tolh)):
                            l2_liq = True
                            break

        rows.append((sid, l1, in_h1z, l2, ddir, hdir,
                     liq_away, liq_into, swept_rec, l2_liq))

out = pd.DataFrame(rows, columns=["sig_id", "l1", "in_h1z", "l2", "daily_dir", "h1_dir",
                                  "liq_away", "liq_into", "swept_rec", "l2_liq"])
out.to_parquet(SP / "nested_flags.parquet", index=False)
print(f"n={len(out)} l1={out.l1.mean():.3f} in_h1z={out.in_h1z.mean():.3f} "
      f"l2={out.l2.mean():.4f} liq_away={out.liq_away.mean():.3f} "
      f"liq_into={out.liq_into.mean():.3f} swept={out.swept_rec.mean():.3f} "
      f"l2_liq={out.l2_liq.mean():.4f}")
