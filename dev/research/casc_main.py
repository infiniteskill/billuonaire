"""Elimination-cascade study: reconstruct zone birth per signal (fvg_cb, ob_lux,
mitigation), compute revisit delay, extreme-swing proximity, and a uniform
k=1.5 ATR stop / 1R target outcome sim. Saves augmented per-signal parquet."""
import numpy as np, pandas as pd, time, sys

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
SIG = 'runs/artifacts-data/signals60.parquet'
DETS = ['fvg_cb', 'ob_lux', 'mitigation']
K = 1.5           # stop = K * ATR(5m,14)
COST = 0.0006     # round-trip cost as fraction of notional
CUTOFF = (15, 5)  # last tradeable bar label (closes 15:10)

df = pd.read_parquet(SIG, columns=['detector','event','symbol','session','ts',
                                   'direction','entry','zone_lo','zone_hi','atr'])
df = df[df.detector.isin(DETS)].reset_index(drop=True)
df['ts'] = pd.to_datetime(df.ts).dt.tz_localize(None)
r2 = lambda x: np.round(x, 2)

out_rows = []
t0 = time.time()
symbols = sorted(df.symbol.unique())
for si, sym in enumerate(symbols):
    b = pd.read_csv(f'data/long5m/{sym}.csv')
    ts = pd.to_datetime(b.ts).dt.tz_localize(None).values
    o, h, l, c = (b[k].values for k in ('open','high','low','close'))
    n = len(b)
    dates = ts.astype('datetime64[D]')
    o2, h2, l2, c2 = r2(o), r2(h), r2(l), r2(c)
    # trailing ATR(14) = SMA of TR, value at bar i uses bars <= i
    tr = np.empty(n); tr[0] = h[0]-l[0]
    tr[1:] = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr = np.full(n, np.nan)
    if n > 14:
        cs = np.cumsum(tr); atr[14:] = (cs[14:]-cs[:-14])/14.0
    # eod index per date: last bar with time <= 15:05
    tod = (ts - dates).astype('timedelta64[m]').astype(int)
    ok_eod = tod <= CUTOFF[0]*60 + CUTOFF[1]
    eod_of = {}
    for d in np.unique(dates):
        m = (dates == d) & ok_eod
        eod_of[d] = np.where(m)[0][-1] if m.any() else -1

    # ---- birth candidate maps ----
    ob_map, fvg_map, mit_map = {}, {}, {}
    for i in range(n):
        ob_map.setdefault((l2[i], h2[i]), []).append(i)
        if c[i] < o[i]: mit_map.setdefault((c2[i], o2[i], 1), []).append(i)
        elif c[i] > o[i]: mit_map.setdefault((o2[i], c2[i], -1), []).append(i)
    for i in range(1, n-1):
        if l[i+1] > h[i-1] and c[i] > h[i-1]:   # bull gap w/ displacement, c2=i
            fvg_map.setdefault((h2[i-1], l2[i+1], 1), []).append(i)
        if h[i+1] < l[i-1] and c[i] < l[i-1]:   # bear gap
            fvg_map.setdefault((h2[i+1], l2[i-1], -1), []).append(i)

    # ---- swings (fractal 5/5) + extreme-reach precompute ----
    sw_idx, sw_price, sw_reach, sw_reach3 = [], [], [], []
    def _reach(seg_ok):
        return  # placeholder
    for s in range(5, n-5):
        if np.isnan(atr[s]): continue
        if h[s] > h[s-5:s].max() and h[s] > h[s+1:s+6].max():
            fut = h[s+1:]
            viol = np.argmax(fut > h[s]) if (fut > h[s]).any() else len(fut)
            seg = l[s+1:s+1+viol]
            m2 = seg <= h[s] - 2.0*atr[s]; m3 = seg <= h[s] - 3.0*atr[s]
            sw_idx.append(s); sw_price.append(h[s])
            sw_reach.append(s+1+int(np.argmax(m2)) if m2.any() else -1)
            sw_reach3.append(s+1+int(np.argmax(m3)) if m3.any() else -1)
        if l[s] < l[s-5:s].min() and l[s] < l[s+1:s+6].min():
            fut = l[s+1:]
            viol = np.argmax(fut < l[s]) if (fut < l[s]).any() else len(fut)
            seg = h[s+1:s+1+viol]
            m2 = seg >= l[s] + 2.0*atr[s]; m3 = seg >= l[s] + 3.0*atr[s]
            sw_idx.append(s); sw_price.append(l[s])
            sw_reach.append(s+1+int(np.argmax(m2)) if m2.any() else -1)
            sw_reach3.append(s+1+int(np.argmax(m3)) if m3.any() else -1)
    sw_idx = np.array(sw_idx, int); sw_price = np.array(sw_price)
    sw_reach = np.array(sw_reach, int); sw_reach3 = np.array(sw_reach3, int)

    sub = df[df.symbol == sym]
    sidx = np.searchsorted(ts, sub.ts.values)
    for (ri, row), sig_i in zip(sub.iterrows(), sidx):
        if sig_i >= n or ts[sig_i] != row.ts.to_datetime64():
            continue
        zl, zh, d = r2(row.zone_lo), r2(row.zone_hi), int(row.direction)
        # ---- birth match (most recent candidate satisfying causality) ----
        if row.detector == 'ob_lux':
            cand, lim = ob_map.get((zl, zh), []), sig_i - 1
        elif row.detector == 'fvg_cb':
            cand, lim = fvg_map.get((zl, zh, d), []), sig_i - 2
        else:
            cand, lim = mit_map.get((zl, zh, d), []), sig_i - 4
        born_i = -1
        for j in reversed(cand):
            if j <= lim: born_i = j; break
        # ---- outcome sim: entry next-bar open, k=1.5 ATR stop, 1R target ----
        a = row.atr
        e_i = sig_i + 1
        eod = eod_of.get(dates[sig_i], -1)
        hit = gross = mfe = mae = np.nan
        if e_i < n and e_i <= eod and dates[e_i] == dates[sig_i] and a > 0:
            entry = o[e_i]; R = K * a
            tgt, stp = entry + d*R, entry - d*R
            hh, ll = h[e_i:eod+1], l[e_i:eod+1]
            if d == 1: t_hit, s_hit = hh >= tgt, ll <= stp
            else:      t_hit, s_hit = ll <= tgt, hh >= stp
            ti = np.argmax(t_hit) if t_hit.any() else 10**9
            si_ = np.argmax(s_hit) if s_hit.any() else 10**9
            if ti < si_:   hit, gross = 1.0, 1.0
            elif si_ < 10**9: hit, gross = 0.0, -1.0   # tie -> stop first
            else:          hit, gross = 0.0, d*(c[eod]-entry)/R
            mfe = (hh.max()-entry)/a if d == 1 else (entry-ll.min())/a
            mae = (entry-ll.min())/a if d == 1 else (hh.max()-entry)/a
            gross -= COST * entry / R
        # ---- extreme-swing proximity (2ATR/1ATR loose; 3ATR/0.5ATR strict) ----
        near_ext = near_ext3 = False
        if born_i >= 0 and len(sw_idx):
            base_m = (sw_idx <= born_i) & (sw_idx + 5 <= sig_i)
            for reach_arr, dtol, which in ((sw_reach, 1.0, 'l'), (sw_reach3, 0.5, 's')):
                m = base_m & (reach_arr >= 0) & (reach_arr <= sig_i)
                if m.any():
                    p = sw_price[m]
                    dist = np.where((p >= row.zone_lo) & (p <= row.zone_hi), 0.0,
                                    np.minimum(abs(p-row.zone_lo), abs(p-row.zone_hi)))
                    if (dist <= dtol*a).any():
                        if which == 'l': near_ext = True
                        else: near_ext3 = True
        out_rows.append((ri, sym, row.detector, row.event, row.session, d,
                         sig_i, born_i,
                         str(ts[born_i]) if born_i >= 0 else '',
                         str(dates[born_i]) if born_i >= 0 else '',
                         near_ext, near_ext3, hit, gross, mfe, mae))
    if si % 20 == 0:
        print(f'{si}/{len(symbols)} {sym} {time.time()-t0:.0f}s', flush=True)

res = pd.DataFrame(out_rows, columns=['ri','symbol','detector','event','session',
    'direction','sig_i','born_i','born_ts','born_date','near_ext','near_ext3','hit','net_r','mfe','mae'])
res.to_parquet(f'{SCR}/casc_signals.parquet')
print('saved', res.shape, f'{time.time()-t0:.0f}s')
print('match rate per detector:')
print(res.assign(m=res.born_i >= 0).groupby('detector').m.mean())
