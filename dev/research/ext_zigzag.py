"""EXTREME-SWING detector prototype: ATR-scaled causal zigzag with cluster bands.

Algorithm (user-taught, continuous tape, no session logic):
- ATR(14, TF) Wilder smoothing on the working timeframe bars.
- Pivot valid iff leg_in and leg_out each >= K*ATR, opposite directions.
- Alternation enforced: a higher high replaces the last high while seeking a low
  (and symmetrically), so never two same-side pivots in a row.
- Causal: pivot confirmed once the reversal leg from its extreme reaches K*ATR
  (ATR taken at the confirming bar). Confirmation lag recorded in bars.
- Cluster band: contiguous bars around the pivot whose relevant extreme is
  within 0.5*ATR(pivot bar) of the pivot price -> zone [band_lo, band_hi].
- Rank metric: min(leg_in, leg_out) / ATR(pivot bar). master = window max/min.
"""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
import numpy as np
import pandas as pd


def wilder_atr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = np.full(len(tr), np.nan)
    if len(tr) < n: return atr
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    # backfill warm-up so early bars are usable (approximation, noted in report)
    atr[: n - 1] = atr[n - 1]
    return atr


@dataclass
class Pivot:
    idx: int            # bar index of the extreme
    price: float
    side: str           # 'H' or 'L'
    confirm_idx: int | None = None
    boundary: bool = False   # first pivot: leg_in truncated by window start
    pending: bool = False    # last extreme: leg_out not yet >= K*ATR
    leg_in: float = np.nan   # price units
    leg_out: float = np.nan
    band: tuple = (np.nan, np.nan)
    band_bars: int = 1
    rank_atr: float = np.nan
    master: bool = False


def zigzag(df: pd.DataFrame, K: float, atr: np.ndarray) -> list[Pivot]:
    h, l = df["high"].values, df["low"].values
    n = len(df)
    pivots: list[Pivot] = []

    # ---- init: find first leg of K*ATR from running extremes
    imax = imin = 0
    i = 1
    state = None  # 'up' = last pivot LOW, seeking HIGH; 'down' = last pivot HIGH
    while i < n:
        if h[i] > h[imax]: imax = i
        if l[i] < l[imin]: imin = i
        k = K * atr[i]
        if h[i] - l[imin] >= k and imin < i:
            p = Pivot(imin, l[imin], "L", confirm_idx=i, boundary=True)
            pivots.append(p); state = "up"
            j0 = imin + 1
            pend = j0 + int(np.argmax(h[j0:i + 1]))
            break
        if h[imax] - l[i] >= k and imax < i:
            p = Pivot(imax, h[imax], "H", confirm_idx=i, boundary=True)
            pivots.append(p); state = "down"
            j0 = imax + 1
            pend = j0 + int(np.argmin(l[j0:i + 1]))
            break
        i += 1
    if state is None:
        return []

    last = pivots[-1]
    last_confirmed = True
    i += 1
    while i < n:
        k = K * atr[i]
        if state == "up":  # last pivot LOW, pend is running HIGH
            if h[i] > h[pend]: pend = i
            # alternation replace: lower low than last LOW pivot before HIGH confirms
            if l[i] < last.price:
                if h[pend] - l[i] >= k and pend > last.idx:
                    # pending HIGH confirms this bar, then new LOW starts
                    piv = Pivot(pend, h[pend], "H", confirm_idx=i)
                    pivots.append(piv); last, last_confirmed = piv, True
                    state = "down"; pend = i
                else:
                    last.idx, last.price = i, l[i]
                    last.confirm_idx = None; last_confirmed = False
                    pend = i  # restart high tracking from here
            else:
                if not last_confirmed and h[i] - last.price >= k:
                    last.confirm_idx = i; last_confirmed = True
                if h[pend] - l[i] >= k and pend > last.idx:
                    piv = Pivot(pend, h[pend], "H", confirm_idx=i)
                    pivots.append(piv); last, last_confirmed = piv, True
                    state = "down"
                    j0 = pend + 1
                    pend = j0 + int(np.argmin(l[j0:i + 1]))
        else:  # state == 'down': last pivot HIGH, pend is running LOW
            if l[i] < l[pend]: pend = i
            if h[i] > last.price:
                if h[i] - l[pend] >= k and pend > last.idx:
                    piv = Pivot(pend, l[pend], "L", confirm_idx=i)
                    pivots.append(piv); last, last_confirmed = piv, True
                    state = "up"; pend = i
                else:
                    last.idx, last.price = i, h[i]
                    last.confirm_idx = None; last_confirmed = False
                    pend = i
            else:
                if not last_confirmed and last.price - l[i] >= k:
                    last.confirm_idx = i; last_confirmed = True
                if h[i] - l[pend] >= k and pend > last.idx:
                    piv = Pivot(pend, l[pend], "L", confirm_idx=i)
                    pivots.append(piv); last, last_confirmed = piv, True
                    state = "up"
                    j0 = pend + 1
                    pend = j0 + int(np.argmax(h[j0:i + 1]))
        i += 1

    # trailing pending extreme (leg_out incomplete)
    if pend > last.idx:
        side = "H" if state == "up" else "L"
        price = h[pend] if state == "up" else l[pend]
        pivots.append(Pivot(pend, price, side, confirm_idx=None, pending=True))

    # drop unconfirmed replaced pivot at tail? keep, flag as pending
    for p in pivots:
        if p.confirm_idx is None and not p.pending:
            p.pending = True

    # ---- legs, rank, band, master
    for j, p in enumerate(pivots):
        if j > 0:
            p.leg_in = abs(p.price - pivots[j - 1].price)
        if j < len(pivots) - 1:
            p.leg_out = abs(pivots[j + 1].price - p.price)
        elif not p.pending:
            # last confirmed pivot: leg_out = to running extreme at window end
            if p.side == "H":
                p.leg_out = p.price - l[p.idx + 1:].min() if p.idx + 1 < n else np.nan
            else:
                p.leg_out = h[p.idx + 1:].max() - p.price if p.idx + 1 < n else np.nan
        a = atr[p.idx]
        legs = [x for x in (p.leg_in, p.leg_out) if not np.isnan(x)]
        p.rank_atr = (min(legs) / a) if legs else np.nan
        # cluster band
        half = 0.5 * a
        lo_b = pivots[j - 1].idx if j > 0 else 0
        hi_b = pivots[j + 1].idx if j < len(pivots) - 1 else n - 1
        arr = h if p.side == "H" else l
        s = e = p.idx
        if p.side == "H":
            while s - 1 > lo_b and arr[s - 1] >= p.price - half: s -= 1
            while e + 1 < hi_b and arr[e + 1] >= p.price - half: e += 1
            p.band = (float(arr[s:e + 1].min()), float(p.price))
        else:
            while s - 1 > lo_b and arr[s - 1] <= p.price + half: s -= 1
            while e + 1 < hi_b and arr[e + 1] <= p.price + half: e += 1
            p.band = (float(p.price), float(arr[s:e + 1].max()))
        p.band_bars = e - s + 1

    highs = [p for p in pivots if p.side == "H"]
    lows = [p for p in pivots if p.side == "L"]
    if highs: max(highs, key=lambda p: p.price).master = True
    if lows: min(lows, key=lambda p: p.price).master = True
    return pivots


def fractal_33(df: pd.DataFrame) -> tuple[int, int]:
    """swings.py rule: strength 3, middle strictly extreme in 7-bar window."""
    h, l = df["high"].values, df["low"].values
    nh = nl = 0
    for m in range(3, len(df) - 3):
        w = list(range(m - 3, m + 4)); w.remove(m)
        if all(h[m] > h[j] for j in w): nh += 1
        if all(l[m] < l[j] for j in w): nl += 1
    return nh, nl


def load_chart_a() -> pd.DataFrame:
    df = pd.read_csv("/home/doom/Public/PROJECT/2026/trader/data/long5m/HEROMOTOCO.csv",
                     parse_dates=["ts"])
    g = df.groupby(pd.Grouper(key="ts", freq="30min", offset="15min"))
    out = g.agg(open=("open", "first"), high=("high", "max"),
                low=("low", "min"), close=("close", "last")).dropna().reset_index()
    return out


def load_chart_b() -> pd.DataFrame:
    df = pd.read_parquet("/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/l4_h1.parquet")
    df = df[df["symbol"] == "HEROMOTOCO"].sort_values("ts").reset_index(drop=True)
    return df[["ts", "open", "high", "low", "close"]]


TARGETS_A = [  # (id, side, price, d0, d1)
    ("A1", "L", 5000, "2026-05-05", "2026-05-06"),
    ("A2", "H", 5480, "2026-05-08", "2026-05-09"),
    ("A3", "L", 4900, "2026-05-14", "2026-05-15"),
    ("A4", "H", 5060, "2026-05-26", "2026-05-27"),
    ("A5", "L", 4780, "2026-05-30", "2026-06-01"),
    ("A6", "H", 5010, "2026-06-26", "2026-06-27"),
    ("A7", "L", 4700, "2026-06-29", "2026-06-30"),
    ("A8", "H", 5050, "2026-07-07", "2026-07-08"),
]
TARGETS_B = [
    ("B1", "H", 6300, "2025-12-05", "2025-12-08"),
    ("B2", "L", 5600, "2025-12-29", "2025-12-29"),
    ("B3", "H", 6020, "2026-01-05", "2026-01-07"),
    ("B4", "L", 5370, "2026-01-19", "2026-01-20"),
    ("B5", "H", 5930, "2026-02-09", "2026-02-10"),
    ("B6", "L", 5420, "2026-02-23", "2026-02-23"),
    ("B7", "H", 5820, "2026-02-25", "2026-03-01"),
    ("B8", "H", 5750, "2026-03-09", "2026-03-09"),
]


def match(pivots, df, targets, tol_days=3, tol_pct=1.2):
    used = set()
    rows = []
    for tid, side, price, d0, d1 in targets:
        lo = pd.Timestamp(d0, tz="Asia/Kolkata") - pd.Timedelta(days=tol_days)
        hi = pd.Timestamp(d1, tz="Asia/Kolkata") + pd.Timedelta(days=tol_days, hours=23)
        best = None
        for j, p in enumerate(pivots):
            if j in used or p.side != side: continue
            ts = df["ts"].iloc[p.idx]
            if not (lo <= ts <= hi): continue
            dp = abs(p.price - price) / price * 100
            if dp > tol_pct: continue
            if best is None or dp < best[1]: best = (j, dp)
        if best is not None:
            used.add(best[0])
            rows.append((tid, best[0], best[1]))
        else:
            rows.append((tid, None, None))
    extras = [j for j in range(len(pivots)) if j not in used]
    return rows, extras


def report(df, pivots, name):
    print(f"--- {name}: {len(pivots)} pivots ---")
    for j, p in enumerate(pivots):
        ts = df["ts"].iloc[p.idx]
        cts = df["ts"].iloc[p.confirm_idx] if p.confirm_idx is not None else None
        lag = (p.confirm_idx - p.idx) if p.confirm_idx is not None else None
        flags = ("M" if p.master else "") + ("b" if p.boundary else "") + ("?" if p.pending else "")
        print(f"[{j}] {p.side} {ts:%Y-%m-%d %H:%M} {p.price:8.1f} band=({p.band[0]:.1f},{p.band[1]:.1f}) "
              f"rank={p.rank_atr:5.1f} lag={lag} conf={cts:%m-%d %H:%M} {flags}" if cts is not None else
              f"[{j}] {p.side} {ts:%Y-%m-%d %H:%M} {p.price:8.1f} band=({p.band[0]:.1f},{p.band[1]:.1f}) "
              f"rank={p.rank_atr:5.1f} lag=None conf=None {flags}")


def run_chart(df, targets, name, Ks=(4, 6, 8, 10), verbose=True):
    atr = wilder_atr(df)
    results = {}
    for K in Ks:
        piv = zigzag(df, K, atr)
        rows, extras = match(piv, df, targets)
        tp = sum(1 for r in rows if r[1] is not None)
        fn = len(rows) - tp
        fp = len(extras)
        f1 = 2 * tp / (2 * tp + fn + fp) if tp else 0.0
        results[K] = dict(pivots=piv, rows=rows, extras=extras, tp=tp, fn=fn, fp=fp, f1=f1)
        if verbose:
            print(f"\n===== {name} K={K}: matched {tp}/8, extras {fp}, F1={f1:.3f} =====")
            report(df, piv, name)
            for tid, j, dp in rows:
                if j is None: print(f"  {tid}: MISSED")
                else: print(f"  {tid}: pivot[{j}] dp={dp:.2f}%")
            if extras: print(f"  extras: {extras}")
    return results, atr


if __name__ == "__main__":
    dfa = load_chart_a()
    dfb_full = load_chart_b()
    print("chart A bars:", len(dfa), dfa["ts"].min(), dfa["ts"].max())
    print("chart B full:", len(dfb_full), dfb_full["ts"].min(), dfb_full["ts"].max())
    # chart B: ATR lead-in of ~1 month before window, zigzag on window only
    w0 = pd.Timestamp("2025-11-04", tz="Asia/Kolkata")
    w1 = pd.Timestamp("2026-03-16 23:59", tz="Asia/Kolkata")
    lead = pd.Timestamp("2025-10-01", tz="Asia/Kolkata")
    dfb_lead = dfb_full[(dfb_full["ts"] >= lead) & (dfb_full["ts"] <= w1)].reset_index(drop=True)
    atr_lead = wilder_atr(dfb_lead)
    mask = dfb_lead["ts"] >= w0
    dfb = dfb_lead[mask].reset_index(drop=True)
    atr_b = atr_lead[mask.values]

    print("\n################ CHART A (30m) ################")
    res_a, atr_a = run_chart(dfa, TARGETS_A, "A")

    print("\n################ CHART B (H1) ################")
    res_b = {}
    for K in (4, 6, 8, 10):
        piv = zigzag(dfb, K, atr_b)
        rows, extras = match(piv, dfb, TARGETS_B)
        tp = sum(1 for r in rows if r[1] is not None)
        fp = len(extras); fn = len(rows) - tp
        f1 = 2 * tp / (2 * tp + fn + fp) if tp else 0.0
        res_b[K] = dict(pivots=piv, rows=rows, extras=extras, tp=tp, fn=fn, fp=fp, f1=f1)
        print(f"\n===== B K={K}: matched {tp}/8, extras {fp}, F1={f1:.3f} =====")
        report(dfb, piv, "B")
        for tid, j, dp in rows:
            if j is None: print(f"  {tid}: MISSED")
            else: print(f"  {tid}: pivot[{j}] dp={dp:.2f}%")

    print("\n######## COMBINED F1 ########")
    for K in (4, 6, 8, 10):
        tp = res_a[K]["tp"] + res_b[K]["tp"]
        fn = res_a[K]["fn"] + res_b[K]["fn"]
        fp = res_a[K]["fp"] + res_b[K]["fp"]
        f1 = 2 * tp / (2 * tp + fn + fp)
        print(f"K={K}: TP={tp}/16 FP={fp} F1={f1:.3f}")

    nh, nl = fractal_33(dfa)
    print(f"\nFractal 3/3 on chart A window: {nh} highs + {nl} lows = {nh + nl}")
