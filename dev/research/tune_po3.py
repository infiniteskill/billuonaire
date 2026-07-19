"""tune_po3 — stage H: PO3 gate sweep on D1 (body fraction x wick dominance).
Event = flagged D1 candle; race from its close, predicted direction (opposite big
wick), 1x/2x ATR(D1,14) favorable vs 1x adverse, 60-bar cap. Null = 5 time-local
draws in the event's own forward window (+2..+11 D1 bars), same direction (ts1
method). Selection = train (t1∩half0) paired lift."""
import sys, zlib
import numpy as np, pandas as pd

SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
sys.path.insert(0, SCR)
import tune_lib as T
from tune_lib import first_true

CAP = 60


def atr14(h, l, c, n=14):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    a = np.full(len(tr), np.nan)
    if len(tr) < n: return a
    a[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)): a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    a[:n - 1] = a[n - 1]
    return a


def drace(h, l, c, a, t, d, n):
    end = min(n, t + 1 + CAP)
    hs, ls = h[t + 1:end], l[t + 1:end]
    F1 = c[t] + d * a[t]; F2 = c[t] + 2 * d * a[t]; A = c[t] - d * a[t]
    f1 = first_true(hs >= F1) if d == 1 else first_true(ls <= F1)
    f2 = first_true(hs >= F2) if d == 1 else first_true(ls <= F2)
    ad = first_true(ls <= A) if d == 1 else first_true(hs >= A)
    if f1 is None and ad is None: return None, None
    r = 1 if (ad is None or (f1 is not None and f1 < ad)) else 0
    r2 = int(f2 is not None and (ad is None or f2 < ad))
    return r, r2


df, syms = T.load()
GRID = [(b, w) for b in (0.35, 0.50) for w in (0.50, 0.60)]
rows = []
for sym in syms:
    g = df[df.symbol == sym].sort_values("ts")
    d1 = g.groupby(g.ts.dt.date).agg(open=("open", "first"), high=("high", "max"),
                                     low=("low", "min"), close=("close", "last"),
                                     ts=("ts", "first")).reset_index(drop=True)
    o, h, l, c = (d1[x].values for x in ("open", "high", "low", "close"))
    n = len(c); a = atr14(h, l, c)
    ts = T.to_naive(d1.ts)
    half = zlib.crc32(sym.encode()) % 2
    rng_ = h - l; body = np.abs(c - o)
    uw = h - np.maximum(o, c); lw = np.minimum(o, c) - l
    spl = np.where(np.abs(o[1:] / np.where(c[:-1] > 0, c[:-1], np.nan) - 1) > 0.2)[0] + 1
    for ci, (bmax, wmin) in enumerate(GRID):
        with np.errstate(invalid="ignore", divide="ignore"):
            ok = rng_ > 0
            small = np.where(ok, body / rng_ < bmax, False)
            flag = np.where(small & np.where(ok, uw / rng_ > wmin, False), -1,
                            np.where(small & np.where(ok, lw / rng_ > wmin, False), 1, 0))
        for t in np.where(flag != 0)[0]:
            if t < 14 or t + 2 >= n or not np.isfinite(a[t]) or a[t] <= 0: continue
            if len(spl) and ((spl >= t) & (spl <= min(n - 1, t + CAP))).any(): continue
            d = int(flag[t])
            r, r2 = drace(h, l, c, a, t, d, n)
            if r is None: continue
            rng = np.random.default_rng(zlib.crc32(f"{sym}|{t}|{ci}".encode()))
            acc, acc2 = [], []
            hi_u = min(t + 12, n - 1)
            if hi_u <= t + 2: continue
            for u in rng.integers(t + 2, hi_u, size=5):
                if not np.isfinite(a[u]) or a[u] <= 0: continue
                nr, nr2 = drace(h, l, c, a, int(u), d, n)
                if nr is not None: acc.append(nr); acc2.append(nr2)
            nul, nul2 = (np.mean(acc), np.mean(acc2)) if acc else (np.nan, np.nan)
            rows.append((ci, sym, half, ts[t], d, r, r2, nul, nul2, len(acc),
                         int(c[t + 1] * d > c[t] * d if t + 1 < n else 0)))

ep = pd.DataFrame(rows, columns=["cfg", "sym", "half", "ts", "d", "resp", "r2",
                                 "null", "null2", "nn", "nextdir"])
ep["ts"] = pd.to_datetime(ep.ts)
ep["tt"] = np.where(ep.ts < T.B1, 0, np.where(ep.ts < T.B2, 1, 2))
ep.to_parquet(f"{SCR}/tune_po3.parquet")
tr = ep[(ep.half == 0) & (ep.tt == 0)]
print("===== H PO3 gate (train t1∩half0) =====")
for ci, (b, w) in enumerate(GRID):
    s = tr[tr.cfg == ci]; v = s[s.nn > 0]
    print(f"cfg{ci} body<{b} wick>{w}: n={len(s)} resp={100*s.resp.mean():.2f} "
          f"r2={100*s.r2.mean():.2f} null={100*v.null.mean():.2f} "
          f"lift={100*(v.resp-v.null).mean():+.2f} nextdir={100*s.nextdir.mean():.2f}")
