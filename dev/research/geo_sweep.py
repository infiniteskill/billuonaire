"""geo_sweep.py — geometry sweep on the FACTS ladder cells.
Rebuilds every zone's trade from data/long5m under stop k*ATR5 (k in 1.5/2.5/4/6/10),
targets 1R/1.5R/2R + trail-after-1R. Realistic fills: next-bar-open entry, intrabar
stop-first, GAP-THROUGH stop/target fill at bar open beyond level, EOD 15:10 close.
Also recomputes the exact-fill uniform sim (k=1.5,1R) as a parity check vs facts_first.
Saves geo_trades.parquet (one row per zone, aligned with facts_first)."""
import numpy as np, pandas as pd, time

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
COST = 0.0006; CUT = 15*60 + 5; BIG = 10**9
KS = [1.5, 2.5, 4.0, 6.0, 10.0]
GEOS = [(k, t) for k in KS for t in [1.0, 1.5, 2.0]] + [(k, 'trail') for k in KS]

first = pd.read_parquet(f'{SCR}/facts_first.parquet',
                        columns=['symbol', 'sig_i', 'direction', 'atr'])
N = len(first)
G = len(GEOS)
gross = np.full((N, G), np.nan); hit = np.full((N, G), np.nan)
par_g = np.full(N, np.nan); par_h = np.full(N, np.nan)
entry_px = np.full(N, np.nan)

t0 = time.time()
for si_, (sym, zf) in enumerate(first.groupby('symbol')):
    b = pd.read_csv(f'data/long5m/{sym}.csv')
    ts = pd.to_datetime(b.ts).dt.tz_localize(None).values
    o, h, l, c = (b[k].values for k in ('open', 'high', 'low', 'close'))
    n = len(b)
    dates = ts.astype('datetime64[D]')
    tod = (ts - dates).astype('timedelta64[m]').astype(int)
    ok = tod <= CUT
    eod_of = {}
    for d_ in np.unique(dates):
        m = (dates == d_) & ok
        eod_of[d_] = np.where(m)[0][-1] if m.any() else -1

    pos = first.index.get_indexer(zf.index)
    sig = zf.sig_i.values.astype(int); dv = zf.direction.values.astype(float)
    av = zf.atr.values.astype(float)
    e = sig + 1
    eod = np.array([eod_of.get(dates[s], -1) for s in sig])
    valid = (e < n) & (eod >= 0) & (e <= eod) & (av > 0)
    valid &= dates[np.clip(e, 0, n - 1)] == dates[sig]
    if not valid.any():
        continue
    pos, sig, dv, av, e, eod = (a[valid] for a in (pos, sig, dv, av, e, eod))
    M = len(pos)
    W = eod - e + 1; maxW = int(W.max())
    cols = np.arange(maxW)
    take = np.clip(e[:, None] + cols[None, :], 0, n - 1)
    mask = cols[None, :] < W[:, None]
    dd = dv[:, None]
    ph = np.where(mask, np.where(dd == 1, h[take], -l[take]), -np.inf)   # favorable extreme
    pl = np.where(mask, np.where(dd == 1, l[take], -h[take]), np.inf)    # adverse extreme
    po = dd * o[take]
    entry = o[e]
    pe = dv * entry
    pceod = dv * c[eod]
    entry_px[pos] = entry
    rows = np.arange(M)

    for gi, (k, t) in enumerate(GEOS):
        R = k * av
        stp = pe - R
        if t == 'trail':
            cm = np.maximum.accumulate(ph, axis=1)
            runmax_prev = np.concatenate([pe[:, None], cm[:, :-1]], axis=1)
            runmax_prev = np.maximum(runmax_prev, pe[:, None])
            armed = runmax_prev >= (pe + R)[:, None]
            tstop = np.where(armed, runmax_prev - R[:, None], stp[:, None])
            hm = mask & (pl <= tstop)
            has = hm.any(1); j = hm.argmax(1)
            fill = np.minimum(po[rows, j], tstop[rows, j])
            g_ = np.where(has, (fill - pe) / R, (pceod - pe) / R)
            h_ = (g_ > 0).astype(float)
        else:
            tgt = pe + t * R
            th = ph >= tgt[:, None]; sh = pl <= stp[:, None]
            ti = np.where(th.any(1), th.argmax(1), BIG)
            si = np.where(sh.any(1), sh.argmax(1), BIG)
            jt = np.clip(ti, 0, maxW - 1); js = np.clip(si, 0, maxW - 1)
            fill_t = np.maximum(po[rows, jt], tgt)      # gap past target -> better fill
            fill_s = np.minimum(po[rows, js], stp)      # gap through stop -> worse fill
            g_ = np.where(ti < si, (fill_t - pe) / R,
                 np.where(si < BIG, (fill_s - pe) / R, (pceod - pe) / R))
            h_ = (ti < si).astype(float)
            if k == 1.5 and t == 1.0:                   # parity: exact fills, casc rule
                par_g[pos] = np.where(ti < si, 1.0,
                             np.where(si < BIG, -1.0, (pceod - pe) / R)) - COST * entry / R
                par_h[pos] = h_
        gross[pos, gi] = g_
        hit[pos, gi] = h_
    if si_ % 20 == 0:
        print(f'{si_}/138 {sym} {time.time()-t0:.0f}s', flush=True)

out = pd.DataFrame(index=first.index)
out['entry'] = entry_px
out['par_net'] = par_g; out['par_hit'] = par_h
for gi, (k, t) in enumerate(GEOS):
    tag = f'k{k}_{t}' if t != 'trail' else f'k{k}_trail'
    out[f'g_{tag}'] = gross[:, gi]
    out[f'h_{tag}'] = hit[:, gi]
out.to_parquet(f'{SCR}/geo_trades.parquet')
print('saved', out.shape, f'{time.time()-t0:.0f}s')
print('valid trades:', np.isfinite(gross[:, 0]).sum(), 'of', N)
