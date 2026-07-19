"""facts_main.py — zone-level fact mining on top of casc_* reconstruction.
Computes per-zone birth features: gap-origin, birth impulse, H1 anchor/nesting,
sweep-born; touch ranks; and an iFVG inversion sim (full FVG-birth universe).
Saves facts_first.parquet (zone level), facts_all.parquet (per touch),
facts_ifvg.parquet."""
import numpy as np, pandas as pd, time

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
SIG = 'runs/artifacts-data/signals60.parquet'
DETS = ['fvg_cb', 'ob_lux', 'mitigation']
K = 1.5; COST = 0.0006; CUT = 15*60 + 5

sig = pd.read_parquet(SIG, columns=['detector','symbol','ts','direction','zone_lo','zone_hi','atr'])
sig = sig[sig.detector.isin(DETS)].reset_index(drop=True)

casc = pd.read_parquet(f'{SCR}/casc_signals.parquet')
casc = casc[casc.born_i >= 0].copy()
casc = casc.join(sig[['zone_lo','zone_hi','atr']], on='ri')
chk = casc.sample(500, random_state=0)
assert (sig.loc[chk.ri, 'symbol'].values == chk.symbol.values).all()

# touch rank per zone (dense over sig_i so fvg dual-events share a touch)
zk = ['symbol','detector','direction','born_ts']
casc = casc.sort_values(zk + ['sig_i']).reset_index(drop=True)
casc['touch'] = casc.groupby(zk).sig_i.rank(method='dense').astype(int)
casc['n_touch'] = casc.groupby(zk).sig_i.transform('nunique')

first = casc[casc.touch == 1].groupby(zk, as_index=False).first()
print('zones:', len(first), 'signals:', len(casc))

t0 = time.time()
feat = {}   # first-frame row idx -> feature tuple
ifvg_rows = []
symbols = sorted(first.symbol.unique())
for si, sym in enumerate(symbols):
    zf = first[first.symbol == sym]
    b = pd.read_csv(f'data/long5m/{sym}.csv')
    ts = pd.to_datetime(b.ts).dt.tz_localize(None).values
    o, h, l, c = (b[k].values for k in ('open','high','low','close'))
    n = len(b)
    dates = ts.astype('datetime64[D]')
    tod = (ts - dates).astype('timedelta64[m]').astype(int)
    tr = np.empty(n); tr[0] = h[0]-l[0]
    tr[1:] = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr = np.full(n, np.nan); cs = np.cumsum(tr)
    if n > 14: atr[14:] = (cs[14:]-cs[:-14])/14.0
    udates = np.unique(dates)
    ok = tod <= CUT
    first_of, eod_of = {}, {}
    for d_ in udates:
        m = dates == d_; idx = np.where(m)[0]
        first_of[d_] = idx[0]
        me = m & ok; eod_of[d_] = np.where(me)[0][-1] if me.any() else -1
    gaplo, gaphi, gapsz = {}, {}, {}
    for d_ in udates:
        fi = first_of[d_]
        if fi == 0: continue
        pc, op = c[fi-1], o[fi]
        gapsz[d_] = op - pc; gaplo[d_] = min(pc, op); gaphi[d_] = max(pc, op)

    # ---- H1 resample (bins anchored 09:15) ----
    key = dates.astype('int64')*10 + (tod-555)//60
    ch = np.where(np.diff(key) != 0)[0]
    starts = np.r_[0, ch+1]; ends = np.r_[ch, n-1]
    n1 = len(starts)
    o1, c1 = o[starts], c[ends]
    h1 = np.array([h[s:e+1].max() for s, e in zip(starts, ends)])
    l1 = np.array([l[s:e+1].min() for s, e in zip(starts, ends)])
    end5 = ends
    tr1 = np.empty(n1); tr1[0] = h1[0]-l1[0]
    tr1[1:] = np.maximum(h1[1:]-l1[1:], np.maximum(abs(h1[1:]-c1[:-1]), abs(l1[1:]-c1[:-1])))
    atr1 = np.full(n1, np.nan); cs1 = np.cumsum(tr1)
    if n1 > 14: atr1[14:] = (cs1[14:]-cs1[:-14])/14.0

    # ---- H1 fractal 3/3 swings with run-to-violation >= 3 ATR(H1), causal via 5m idx ----
    swp, swconf5, swreach5 = [], [], []
    for s in range(3, n1-3):
        if np.isnan(atr1[s]): continue
        if h1[s] > h1[s-3:s].max() and h1[s] > h1[s+1:s+4].max():
            fut = h1[s+1:]; viol = np.argmax(fut > h1[s]) if (fut > h1[s]).any() else len(fut)
            seg = l1[s+1:s+1+viol]; m3 = seg <= h1[s]-3*atr1[s]
            rz = s+1+int(np.argmax(m3)) if m3.any() else -1
            swp.append(h1[s]); swconf5.append(end5[s+3]); swreach5.append(end5[rz] if rz >= 0 else -1)
        if l1[s] < l1[s-3:s].min() and l1[s] < l1[s+1:s+4].min():
            fut = l1[s+1:]; viol = np.argmax(fut < l1[s]) if (fut < l1[s]).any() else len(fut)
            seg = h1[s+1:s+1+viol]; m3 = seg >= l1[s]+3*atr1[s]
            rz = s+1+int(np.argmax(m3)) if m3.any() else -1
            swp.append(l1[s]); swconf5.append(end5[s+3]); swreach5.append(end5[rz] if rz >= 0 else -1)
    swp = np.array(swp); swconf5 = np.array(swconf5, int); swreach5 = np.array(swreach5, int)

    # ---- H1 zones: FVG (displacement) + OB (opp candle before >=1.5 ATR(H1) 3-bar impulse) ----
    hz = []  # lo, hi, dir, birth5, invalid5
    for i in range(1, n1-1):
        if l1[i+1] > h1[i-1] and c1[i] > h1[i-1]:
            lo, hi = h1[i-1], l1[i+1]
            fut = np.where(c1[i+2:] < lo)[0]
            hz.append((lo, hi, 1, end5[i+1], end5[i+2+fut[0]] if len(fut) else 10**9))
        if h1[i+1] < l1[i-1] and c1[i] < l1[i-1]:
            lo, hi = h1[i+1], l1[i-1]
            fut = np.where(c1[i+2:] > hi)[0]
            hz.append((lo, hi, -1, end5[i+1], end5[i+2+fut[0]] if len(fut) else 10**9))
    for i in range(n1-3):
        if np.isnan(atr1[i]): continue
        imp1 = c1[i+3] - c1[i]
        if abs(imp1) >= 1.5*atr1[i]:
            d_ = 1 if imp1 > 0 else -1
            if (c1[i]-o1[i])*d_ < 0:
                lo, hi = l1[i], h1[i]
                fut = np.where((c1[i+4:] < lo) if d_ == 1 else (c1[i+4:] > hi))[0]
                hz.append((lo, hi, d_, end5[i+3], end5[i+4+fut[0]] if len(fut) else 10**9))
    hz = np.array(hz) if hz else np.zeros((0, 5))

    # ---- EQ-pool sweep events (fractal 2/2 pivots, cluster tol 0.15 ATR, pool intact) ----
    ph_i, ph_p, pl_i, pl_p = [], [], [], []
    for p in range(2, n-2):
        if h[p] > h[p-2:p].max() and h[p] > h[p+1:p+3].max(): ph_i.append(p); ph_p.append(h[p])
        if l[p] < l[p-2:p].min() and l[p] < l[p+1:p+3].min(): pl_i.append(p); pl_p.append(l[p])
    ph_i = np.array(ph_i, int); ph_p = np.array(ph_p)
    pl_i = np.array(pl_i, int); pl_p = np.array(pl_p)
    sweep_hi = np.zeros(n, bool); sweep_lo = np.zeros(n, bool)
    for j in range(20, n):
        a_ = atr[j]
        if np.isnan(a_): continue
        tol = 0.15*a_
        m = (ph_i+2 < j) & (ph_i >= j-60)
        if m.sum() >= 2:
            order = np.argsort(ph_p[m]); prs = ph_p[m][order]; pis = ph_i[m][order]
            for a0 in range(len(prs)-1):
                if prs[a0+1]-prs[a0] <= tol:
                    L = prs[a0+1]; last = max(pis[a0], pis[a0+1])
                    if h[j] > L and c[j] < L and h[last+1:j].max() <= L:
                        sweep_hi[j] = True; break
        m = (pl_i+2 < j) & (pl_i >= j-60)
        if m.sum() >= 2:
            order = np.argsort(pl_p[m]); prs = pl_p[m][order]; pis = pl_i[m][order]
            for a0 in range(len(prs)-1):
                if prs[a0+1]-prs[a0] <= tol:
                    L = prs[a0]; last = max(pis[a0], pis[a0+1])
                    if l[j] < L and c[j] > L and l[last+1:j].min() >= L:
                        sweep_lo[j] = True; break

    def simfun(sigb, d_, a_):
        e = sigb+1; eod = eod_of.get(dates[sigb], -1)
        if e >= n or e > eod or dates[e] != dates[sigb] or not a_ > 0: return np.nan, np.nan
        entry = o[e]; R = K*a_; tgt, stp = entry+d_*R, entry-d_*R
        hh, ll = h[e:eod+1], l[e:eod+1]
        th, sh = (hh >= tgt, ll <= stp) if d_ == 1 else (ll <= tgt, hh >= stp)
        ti = np.argmax(th) if th.any() else 10**9
        si_ = np.argmax(sh) if sh.any() else 10**9
        if ti < si_: hitv, g = 1.0, 1.0
        elif si_ < 10**9: hitv, g = 0.0, -1.0
        else: hitv, g = 0.0, d_*(c[eod]-entry)/R
        return hitv, g - COST*entry/R

    # ---- per-zone features ----
    for idx, row in zf.iterrows():
        bi, sgi, d = int(row.born_i), int(row.sig_i), int(row.direction)
        zl, zh, ra = row.zone_lo, row.zone_hi, row.atr
        ab = atr[bi] if np.isfinite(atr[bi]) else ra
        bd = dates[bi]
        gap_open = bi == first_of[bd]
        gsz = gapsz.get(bd, 0.0)
        gov = bool(bd in gaplo and abs(gsz) > 0.3*ab and zl <= gaphi[bd] and zh >= gaplo[bd])
        if row.detector == 'fvg_cb': imp = d*(c[min(bi+1, n-1)]-c[bi-1])/ab
        else: imp = d*(c[min(bi+3, n-1)]-c[bi])/ab
        anch = False
        if len(swp):
            m = (swconf5 <= sgi) & (swreach5 >= 0) & (swreach5 <= sgi)
            if m.any():
                p = swp[m]
                dist = np.where((p >= zl) & (p <= zh), 0.0, np.minimum(abs(p-zl), abs(p-zh)))
                anch = bool((dist <= 1.0*ra).any())
        nest = nest_any = False
        if len(hz):
            m = (hz[:, 3] <= sgi) & (hz[:, 4] > sgi) & (hz[:, 0] <= zh) & (hz[:, 1] >= zl)
            nest_any = bool(m.any()); nest = bool((m & (hz[:, 2] == d)).any())
        j0 = max(0, bi-3)
        sb_hi = bool(sweep_hi[j0:bi+1].any()); sb_lo = bool(sweep_lo[j0:bi+1].any())
        feat[idx] = (gap_open, gov, gsz/ab if ab > 0 else np.nan, int(tod[bi]), imp,
                     anch, nest, nest_any, sb_hi or sb_lo,
                     (sb_hi and d == -1) or (sb_lo and d == 1))

    # ---- iFVG: full FVG-birth universe, invalidation -> re-retest, trade both sides ----
    for i in range(1, n-1):
        if l[i+1] > h[i-1] and c[i] > h[i-1]: zl_, zh_, d_ = h[i-1], l[i+1], 1
        elif h[i+1] < l[i-1] and c[i] < l[i-1]: zl_, zh_, d_ = h[i+1], l[i-1], -1
        else: continue
        seg = np.where((c[i+2:] < zl_) if d_ == 1 else (c[i+2:] > zh_))[0]
        if not len(seg): continue
        kk = i+2+seg[0]
        if not np.isfinite(atr[kk]): continue
        big = (zl_-c[kk] >= atr[kk]) if d_ == 1 else (c[kk]-zh_ >= atr[kk])
        seg2 = np.where((h[kk+1:] >= zl_) if d_ == 1 else (l[kk+1:] <= zh_))[0]
        if not len(seg2): continue
        mI = kk+1+seg2[0]
        a_ = atr[mI]
        ih, ig = simfun(mI, -d_, a_)
        oh, og = simfun(mI, d_, a_)
        ifvg_rows.append((sym, str(ts[i]), d_, str(dates[mI]), (mI-kk)*5,
                          bool(dates[mI] == dates[kk]), big, ih, ig, oh, og))
    if si % 20 == 0:
        print(f'{si}/{len(symbols)} {sym} {time.time()-t0:.0f}s', flush=True)

fcols = ['gap_open','gap_overlap','gap_atr','born_tod','impulse','h1_anchor',
         'h1_nested','h1_nested_any','sweep_born','sweep_aligned']
fdf = pd.DataFrame.from_dict(feat, orient='index', columns=fcols)
first = first.join(fdf)
first.to_parquet(f'{SCR}/facts_first.parquet')
casc.to_parquet(f'{SCR}/facts_all.parquet')
ifvg = pd.DataFrame(ifvg_rows, columns=['symbol','born_ts','direction','session',
    'latency_min','same_day','big_inval','inv_hit','inv_netR','orig_hit','orig_netR'])
ifvg.to_parquet(f'{SCR}/facts_ifvg.parquet')
print('saved first', first.shape, 'all', casc.shape, 'ifvg', ifvg.shape,
      f'{time.time()-t0:.0f}s')
print(first[fcols].describe().to_string())
