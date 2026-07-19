"""Extract structure events + run behavioral respect tests per symbol.
Null = path-clean forward-window (H1GRID Null B style): per event, 5 random bars
from the event's own forward window (+1..+10 sessions), same direction, same test.
Output: events-level parquet with per-event respect r and null mean."""
import sys, numpy as np, pandas as pd
from zlib import crc32
sys.path.insert(0, "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad")
from ts1_struct import wilder_atr, zigzag_pct, structure_events, po3_flags, resample_d1, splice_mask

R = "/home/doom/Public/PROJECT/2026/trader"
SCR = "/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad"
H_H1, OFF_H1 = 300, (7, 70)     # respect horizon; null offsets (1..10 sessions x ~7 bars)
H_D1, OFF_D1 = 60, (2, 11)
RETEST_WIN, WARM = 500, 20

def respect(h, l, sp, t0, d, p0, a0, H):
    n = len(h); w0, w1 = t0 + 1, min(t0 + 1 + H, n)
    if w0 >= w1 or not np.isfinite(a0) or a0 <= 0: return None
    hw, lw = h[w0:w1], l[w0:w1]
    fav, adv = (hw - p0, p0 - lw) if d > 0 else (p0 - lw, hw - p0)
    f, a = fav >= a0, adv >= a0
    if not (f.any() or a.any()): return None
    fi = int(f.argmax()) if f.any() else 1 << 30
    ai = int(a.argmax()) if a.any() else 1 << 30
    if sp[w0:w0 + min(fi, ai) + 1].any(): return None
    return 1.0 if fi < ai else 0.0

def null_mean(h, l, c, atr, sp, t0, d, offs, H, rng, fn=None):
    vals = []
    for off in rng.integers(offs[0], offs[1] + 1, size=5):
        tn = t0 + int(off)
        if tn + 1 >= len(c) or sp[t0 + 1:tn + 1].any(): continue
        r = fn(tn, d) if fn else respect(h, l, sp, tn, d, c[tn], atr[tn], H)
        if r is not None: vals.append(r)
    return (float(np.mean(vals)), len(vals)) if len(vals) >= 2 else (np.nan, len(vals))

def sgn(x): return 1 if x > 0 else (-1 if x < 0 else 0)

def do_symbol(sym, g, rows):
    o, h, l, c = (g[k].values.astype(float) for k in ("open", "high", "low", "close"))
    ts = g["ts"].values; n = len(c)
    atr = wilder_atr(h, l, c); sp = splice_mask(o, c)
    rng = np.random.default_rng(crc32(sym.encode()) & 0xffffffff)
    ev, pivots = structure_events(o, h, l, c, atr)
    add = lambda **kw: rows.append(dict(symbol=sym, **kw))

    # T1/T2: CHoCH (+ BOS bonus) follow-through
    majors = {1: [], -1: []}; minors = {1: [], -1: []}
    for e in ev:
        t, d = e["t"], e["d"]
        if e["kind"] == "CHOCH": (majors if e["deg"] == "major" else minors)[d].append(t)
        if t < WARM or t + 1 >= n: continue
        r = respect(h, l, sp, t, d, c[t], atr[t], H_H1)
        if r is None: continue
        nm, nn = null_mean(h, l, c, atr, sp, t, d, OFF_H1, H_H1, rng)
        if np.isnan(nm): continue
        add(test="T1", tag=f"{e['kind']}_{e['deg']}", ts=ts[t], d=d, pos=e["pos"], r=r, nullm=nm, nn=nn)

    # T3: pivot band retests (wick vs atr band)
    for p in pivots:
        if p.boundary or p.confirm_idx is None or p.idx < WARM: continue
        for bk, band in (("wick", p.band_wick), ("atr", p.band_atr)):
            blo, bhi = band
            if not np.isfinite(blo): continue
            t0 = p.confirm_idx; t1 = min(t0 + RETEST_WIN, n)
            if p.side == "H":
                touch = np.nonzero(h[t0 + 1:t1] >= blo)[0]; d = -1
            else:
                touch = np.nonzero(l[t0 + 1:t1] <= bhi)[0]; d = 1
            if len(touch) == 0: continue
            t = t0 + 1 + int(touch[0])
            if sp[t0 + 1:t + 1].any(): continue
            if (p.side == "H" and c[t] > bhi) or (p.side == "L" and c[t] < blo): continue  # blast-through
            r = respect(h, l, sp, t, d, c[t], atr[t], H_H1)
            if r is None: continue
            nm, nn = null_mean(h, l, c, atr, sp, t, d, OFF_H1, H_H1, rng)
            if np.isnan(nm): continue
            add(test="T3", tag=bk, ts=ts[t], d=d, pos=np.nan, r=r, nullm=nm, nn=nn,
                x1=float(bhi - blo) / atr[p.idx])

    # T5: minor -> major sequencing
    for d in (1, -1):
        mnt = np.array(minors[d]); mjt = np.array(majors[d])
        for t in majors[d]:  # backward descriptive
            pre = ((mnt >= t - 50) & (mnt < t)).any() if len(mnt) else False
            add(test="T5B", tag="maj", ts=ts[t], d=d, pos=np.nan, r=float(pre), nullm=np.nan, nn=0)
        def fwd(tn, dd):  # any same-d major CHoCH in (tn, tn+50]
            if sp[tn + 1:min(tn + 51, n)].any(): return None
            return float(((mjt > tn) & (mjt <= tn + 50)).any()) if len(mjt) else 0.0
        for t in minors[d]:
            if t + 1 >= n: continue
            r = fwd(t, d)
            if r is None: continue
            nm, nn = null_mean(h, l, c, atr, sp, t, d, OFF_H1, H_H1, rng, fn=fwd)
            if np.isnan(nm): continue
            add(test="T5P", tag="min", ts=ts[t], d=d, pos=np.nan, r=r, nullm=nm, nn=nn)

    # T4: PO3 on D1
    d1 = resample_d1(g)
    o1, h1, l1, c1 = (d1[k].values.astype(float) for k in ("open", "high", "low", "close"))
    ts1 = d1["ts"].values; n1 = len(c1)
    atr1 = wilder_atr(h1, l1, c1); sp1 = splice_mask(o1, c1)
    fl = po3_flags(o1, h1, l1, c1)
    def align(tn, dd):
        if tn >= n1: return None
        s = sgn(c1[tn] - o1[tn])
        return 1.0 if s == dd else 0.0
    for i in np.nonzero(fl != 0)[0]:
        if i < WARM or i + 2 >= n1: continue
        d = int(fl[i])
        r = align(i + 1, d)
        if r is not None and not sp1[i + 1]:
            nm, nn = null_mean(h1, l1, c1, atr1, sp1, i, d, OFF_D1, 0, rng, fn=align)
            if not np.isnan(nm):
                add(test="T4A", tag="next", ts=ts1[i], d=d, pos=np.nan, r=r, nullm=nm, nn=nn)
        # zone: wick range retest
        zlo, zhi = (max(o1[i], c1[i]), h1[i]) if d == -1 else (l1[i], min(o1[i], c1[i]))
        t1z = min(i + 1 + H_D1, n1)
        touch = np.nonzero(h1[i + 1:t1z] >= zlo)[0] if d == -1 else np.nonzero(l1[i + 1:t1z] <= zhi)[0]
        if len(touch) == 0: continue
        t = i + 1 + int(touch[0])
        if sp1[i + 1:t + 1].any(): continue
        if (d == -1 and c1[t] > zhi) or (d == 1 and c1[t] < zlo): continue
        r = respect(h1, l1, sp1, t, d, c1[t], atr1[t], H_D1)
        if r is None: continue
        nm, nn = null_mean(h1, l1, c1, atr1, sp1, t, d, OFF_D1, H_D1, rng)
        if np.isnan(nm): continue
        add(test="T4B", tag="zone", ts=ts1[t], d=d, pos=np.nan, r=r, nullm=nm, nn=nn)

if __name__ == "__main__":
    df = pd.read_parquet(f"{R}/runs/artifacts-data/l4_h1.parquet")
    rows = []
    for i, (sym, g) in enumerate(df.groupby("symbol")):
        do_symbol(sym, g.sort_values("ts").reset_index(drop=True), rows)
        if i % 20 == 0: print(i, sym, len(rows), flush=True)
    out = pd.DataFrame(rows)
    out.to_parquet(f"{SCR}/ts1_events.parquet")
    print("saved", len(out), "event rows")
    print(out.groupby(["test", "tag"]).size())
