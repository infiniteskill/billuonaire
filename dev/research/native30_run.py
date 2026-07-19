#!/usr/bin/env python
"""native30_run.py — user's FINAL spec, run natively on 30-MINUTE charts.

SMC zone fade (FVG / OB / breaker / iFVG) + elimination ladder, positional
1-2 week holds (EOD NOT closed), delivery costs, 50 most-liquid stocks.

Conventions (stated once, applied uniformly):
  30m frame  = 09:15-anchored resample of data/long5m (offset 15min).
  D1 frame   = one bar per session date.
  Zones (30m): fvg_cb port (wick gap + c2-close displacement + running range%%
    threshold), ob_lux port, EmreKb breaker (hulinv port, zz=9 fib=0.33),
    iFVG = fvg_cb zone whose far edge is closed beyond -> flipped zone born at
    the invalidation bar. Death = close beyond far edge (trade-direction far).
  Retest: first bar after confirmation whose range overlaps the zone (wick
    touch); breakers use the EmreKb close-inside-box rule. A bar that kills
    the zone does not count as a retest. One trade per zone.
  Ladder (cumulative): r1 = zone ORIGIN candle session strictly before retest
    session. r2 = 30m zone overlaps a LIVE, trade-direction-aligned D1 fvg/ob
    zone (D1 zone confirmed on an earlier session, not yet closed beyond its
    far edge). r3 = zone origin within [0,3] 30m bars AFTER an aligned EQ-pool
    sweep (pools = >=2 same-side 5/5 fractal swings within 0.25*ATR(14,30m),
    sweep = wick through pool level + close back, first sweep per pool;
    EQH sweep -> short zones, EQL sweep -> long zones).
  Sim: enter next 30m OPEN after retest; stop k*ATR(14,30m at retest bar);
    target 2R; time-stop at close of Hth session counting entry session as 1
    (H=5 ~ 1wk, H=10 ~ 2wk). Every bar: open beyond stop/target fills AT OPEN
    (overnight gaps go THROUGH stops); intrabar stop-before-target.
    Trades whose H-session window runs off the data edge are dropped (counted).
  Costs (delivery): STT 0.1%% both legs + exch 0.004%% both legs + slip 2bp/leg
    + DP Rs15 per sell. Sizing Rs1L capital, 0.5%% risk (Rs500), notional cap
    5x (Rs5L). qty = min(floor(500/stop), floor(5L/entry)); qty=0 -> skipped.
    R denominated on ACTUAL rupee risk qty*stop (stop-out = -1R gross).
  MFE/MAE: in ATR(30m) units over the FULL H-session window from entry
    (exit-agnostic) — comparable to SWING.md's anchor ratio.
  Holdout: 4 quadrants = (entry session < / >= 2026-06-08) x crc32(symbol)%%2.
"""
import numpy as np, pandas as pd, zlib, glob, os, time
from collections import deque

ROOT = '/home/doom/Public/PROJECT/2026/trader'
SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
SPLIT = pd.Timestamp('2026-06-08').date()
RISK, NCAP = 500.0, 500_000.0
STT, EXCH, SLIP, DP = 0.001, 0.00004, 0.0002, 15.0
KS, HS = (1.5, 2.5), (5, 10)

# ---------- verified ports (chartpar_run.py) ----------
def atr_series(df):
    n = len(df); out = [None]*n
    trs = deque(maxlen=14); s = 0.0
    for i in range(n):
        if i:
            h, l, pc = df.high[i], df.low[i], df.close[i-1]
            tr = max(h-l, abs(h-pc), abs(l-pc))
            if len(trs) == trs.maxlen: s -= trs[0]
            trs.append(tr); s += tr
        if i >= 14: out[i] = s/14
    return out

def ob_lux(df, size=5, hv_mult=2.0):
    n = len(df); events = []
    pH, pL = [], []
    trs = deque(maxlen=14); tr_sum = 0.0
    swH = swL = None; swHc = swLc = True
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    for i in range(n):
        if i:
            tr = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
            if len(trs) == trs.maxlen: tr_sum -= trs[0]
            trs.append(tr); tr_sum += tr
        atr = tr_sum/trs.maxlen if i >= trs.maxlen else None
        hv = atr is not None and H[i]-L[i] >= hv_mult*atr
        pH.append(L[i] if hv else H[i]); pL.append(H[i] if hv else L[i])
        if i >= size:
            p = i-size
            if H[p] > max(H[p+1:i+1]): swH, swHc = (H[p], p), False
            if L[p] < min(L[p+1:i+1]): swL, swLc = (L[p], p), False
        c, cp = C[i], C[i-1] if i else None
        if swH and not swHc and c > swH[0] and (i == 0 or cp <= swH[0]):
            swHc = True
            idx = min(range(swH[1], i+1), key=lambda j: pL[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            events.append(dict(det='ob', dir=1, lo=lo, hi=hi, born_i=idx, conf_i=i))
        if swL and not swLc and c < swL[0] and (i == 0 or cp >= swL[0]):
            swLc = True
            idx = max(range(swL[1], i+1), key=lambda j: pH[j])
            lo, hi = sorted((pL[idx], pH[idx]))
            events.append(dict(det='ob', dir=-1, lo=lo, hi=hi, born_i=idx, conf_i=i))
    return events

def fvg_cb(df, thr_mult=1.0):
    n = len(df); events = []
    H, L, C = df.high.tolist(), df.low.tolist(), df.close.tolist()
    rsum = 0.0; atr = atr_series(df)
    for i in range(2, n):
        rsum += (H[i]-L[i])/L[i] if L[i] else 0.0
        if atr[i] is None: continue
        thr = thr_mult*rsum/(i+1)
        c1h, c1l, c2c = H[i-2], L[i-2], C[i-1]
        lo, hi = c1h, L[i]
        if hi > lo and c2c > c1h and (hi-lo)/lo > thr:
            events.append(dict(det='fvg', dir=1, lo=lo, hi=hi, born_i=i-1, conf_i=i))
        lo, hi = H[i], c1l
        if hi > lo and c2c < c1l and (hi-lo)/lo > thr:
            events.append(dict(det='fvg', dir=-1, lo=lo, hi=hi, born_i=i-1, conf_i=i))
    return events

def fractal_swings(df, N=5):
    n = len(df); out = []
    H, L = df.high.tolist(), df.low.tolist()
    for i in range(N, n-N):
        win_h = [H[j] for j in range(i-N, i+N+1) if j != i]
        win_l = [L[j] for j in range(i-N, i+N+1) if j != i]
        if all(H[i] > v for v in win_h): out.append(dict(kind='SWING_H', i=i, px=H[i]))
        if all(L[i] < v for v in win_l): out.append(dict(kind='SWING_L', i=i, px=L[i]))
    return out

# ---------- EmreKb breaker (hulinv port; creation events only) ----------
def breaker_msb(O, H, L, C, zz=9, fib=0.33, warm=25):
    n = len(C); trend, market = 1, 1
    hi = lo = None; highs, lows = [], []
    l0p = h0p = None; out = []
    warm = max(warm, 14)
    for i in range(n):
        if hi is None or H[i] > hi[1]: hi = (i, H[i])
        if lo is None or L[i] < lo[1]: lo = (i, L[i])
        w0 = max(0, i-zz+1); flipped = False
        if trend == 1 and L[i] <= min(L[w0:i+1]):
            highs = (highs+[hi])[-2:]; flipped = True
        elif trend == -1 and H[i] >= max(H[w0:i+1]):
            lows = (lows+[lo])[-2:]; flipped = True
        if flipped:
            trend = -trend; hi, lo = (i, H[i]), (i, L[i])
        if len(highs) == 2 and len(lows) == 2 and i >= warm:
            (h0i, h0), (h1i, h1) = highs[-1], highs[-2]
            (l0i, l0), (l1i, l1) = lows[-1], lows[-2]
            if not (l0 == l0p or h0 == h0p):
                if market == 1 and l0 < l1 and l0 < l1 - abs(h0-l1)*fib:
                    market, l0p, h0p = -1, l0, h0
                    if h0 > h1:
                        j = next((j for j in range(l1i, max(0, h1i-zz)-1, -1) if O[j] > C[j]), None)
                        if j is not None:
                            out.append(dict(det='breaker', dir=-1, lo=L[j], hi=H[j], born_i=j, conf_i=i))
                elif market == -1 and h0 > h1 and h0 > h1 + abs(h1-l0)*fib:
                    market, l0p, h0p = 1, l0, h0
                    if l0 < l1:
                        j = next((j for j in range(h1i, max(0, l1i-zz)-1, -1) if O[j] < C[j]), None)
                        if j is not None:
                            out.append(dict(det='breaker', dir=1, lo=L[j], hi=H[j], born_i=j, conf_i=i))
    return out

# ---------- EQ-pool first-sweep events (hulinv rule, tol 0.25) ----------
def sweep_events(swings, H, L, C, atr, tol_mult=0.25, confirm_lag=5):
    n = len(C); evs = []
    first_atr = next((a for a in atr if a is not None), None)
    for take_hi in (True, False):
        pts = sorted([s for s in swings if s['kind'] == ('SWING_H' if take_hi else 'SWING_L')],
                     key=lambda s: s['px'])
        pools, cur, anchor = [], [], None
        for s in pts:
            a = atr[s['i']] if atr[s['i']] is not None else first_atr
            tol = tol_mult*(a or 0)
            if cur and abs(s['px']-anchor) <= tol: cur.append(s)
            else:
                if len(cur) >= 2: pools.append(cur)
                cur, anchor = [s], s['px']
        if len(cur) >= 2: pools.append(cur)
        for g in pools:
            level = max(x['px'] for x in g) if take_hi else min(x['px'] for x in g)
            start = min(n, max(x['i'] for x in g) + confirm_lag + 1)
            hit = next((t for t in range(start, n)
                        if ((H[t] > level and C[t] < level) if take_hi
                            else (L[t] < level and C[t] > level))), None)
            if hit is not None:
                evs.append((hit, -1 if take_hi else 1))   # aligned trade dir
    return evs

# ---------- load ----------
def load(path):
    df = pd.read_csv(path, parse_dates=['ts']).set_index('ts').sort_index()
    agg = df.resample('30min', offset='15min', label='left', closed='left').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    ).dropna(subset=['open']).reset_index()
    g = df.groupby(df.index.date)
    d1 = pd.DataFrame({'open': g.open.first().values, 'high': g.high.max().values,
                       'low': g.low.min().values, 'close': g.close.last().values,
                       'volume': g.volume.sum().values})
    d1_dates = list(g.size().index)
    return agg, d1, d1_dates

# ---------- symbol selection: turnover proxy ----------
files = sorted(glob.glob(f'{ROOT}/data/long5m/*.csv'))
t0 = time.time()
turn = []
for f in files:
    b = pd.read_csv(f, usecols=['close', 'volume'])
    turn.append((os.path.basename(f)[:-4], float((b.close*b.volume).sum())))
turn.sort(key=lambda x: -x[1])
SYMS = [s for s, _ in turn[:50]]
print(f'universe: top-50 of {len(files)} by total traded value (close*volume); '
      f'range {turn[0][0]}={turn[0][1]/1e9:.1f}B .. {turn[49][0]}={turn[49][1]/1e9:.1f}B  '
      f'[{time.time()-t0:.0f}s]')

# ---------- main ----------
rows, zstats = [], dict(fvg=0, ob=0, breaker=0, ifvg=0, retested=0, dead_unret=0, untouched=0)
d1_zone_counts, d1_zone_syms = [], 0
skipped_qty = skipped_atr = censored = 0
atr_pcts = []
for sym in SYMS:
    m30, d1, d1_dates = load(f'{ROOT}/data/long5m/{sym}.csv')
    n = len(m30)
    O, H, L, C = (m30[k].tolist() for k in ('open', 'high', 'low', 'close'))
    sess = [t.date() for t in m30.ts]
    udates = sorted(set(sess))
    sess_idx = {d: i for i, d in enumerate(udates)}
    si = [sess_idx[d] for d in sess]
    fb = [i == 0 or sess[i] != sess[i-1] for i in range(n)]
    last_bar = {}
    for i in range(n): last_bar[si[i]] = i
    atr = atr_series(m30)
    atr_pcts += [a/c for a, c in zip(atr, C) if a is not None]

    # --- 30m zones ---
    zones = fvg_cb(m30) + ob_lux(m30) + breaker_msb(O, H, L, C)
    fvgs = [z for z in zones if z['det'] == 'fvg']
    # iFVG: flipped zone born at invalidation bar
    for z in fvgs:
        d0 = z['dir']
        k = next((t for t in range(z['conf_i']+1, n)
                  if (C[t] < z['lo'] if d0 == 1 else C[t] > z['hi'])), None)
        if k is not None:
            zones.append(dict(det='ifvg', dir=-d0, lo=z['lo'], hi=z['hi'], born_i=k, conf_i=k))
    for z in zones: zstats[z['det']] += 1

    # --- D1 zones (fvg_cb + ob_lux constructors on the D1 frame) ---
    dz = fvg_cb(d1) + ob_lux(d1)
    for z in dz:
        z['conf_d'] = d1_dates[z['conf_i']]
        dc = d1.close.tolist()
        kd = next((j for j in range(z['conf_i']+1, len(d1))
                   if (dc[j] < z['lo'] if z['dir'] == 1 else dc[j] > z['hi'])), None)
        z['death_d'] = d1_dates[kd] if kd is not None else None
    d1_zone_counts.append(len(dz)); d1_zone_syms += len(dz) > 0

    # --- EQ-pool sweeps ---
    sw = fractal_swings(m30, 5)
    sweeps = sweep_events(sw, H, L, C, atr)

    half = zlib.crc32(sym.encode()) % 2
    for z in zones:
        d, lo, hi = z['dir'], z['lo'], z['hi']
        wick = z['det'] != 'breaker'
        rt = None; dead = False
        for t in range(z['conf_i']+1, n):
            if (C[t] < lo if d == 1 else C[t] > hi): dead = True; break
            if wick: touched = L[t] <= hi and H[t] >= lo
            else: touched = (lo <= C[t] < hi) if d == 1 else (lo < C[t] <= hi)
            if touched: rt = t; break
        if rt is None:
            zstats['dead_unret' if dead else 'untouched'] += 1
            continue
        zstats['retested'] += 1
        if atr[rt] is None: skipped_atr += 1; continue
        e = rt + 1
        if e >= n: continue
        a = atr[rt]; entry = O[e]
        sd = sess[e]
        # ladder flags
        r1 = sess[z['born_i']] < sess[rt]
        r2_any = any(x['dir'] == d and x['conf_d'] < sd and
                     (x['death_d'] is None or sd <= x['death_d']) for x in dz)
        r2 = any(x['dir'] == d and x['conf_d'] < sd and
                 (x['death_d'] is None or sd <= x['death_d']) and
                 x['lo'] <= hi and x['hi'] >= lo for x in dz)
        r3 = any(sdir == d and 0 <= z['born_i'] - swi <= 3 for swi, sdir in sweeps)
        for K in KS:
            stop_dist = K*a
            qty = int(min(RISK//stop_dist, NCAP//entry))
            if qty < 1: skipped_qty += 1; continue
            stop, tgt = entry - d*stop_dist, entry + d*2*stop_dist
            for Hs in HS:
                dls = si[e] + Hs - 1
                if dls not in last_bar: censored += 1; continue
                dl = last_bar[dls]
                exit_px, kind, gap_thru = None, None, False
                for i in range(e, dl+1):
                    if i > e:
                        op = O[i]
                        if (op - stop)*d <= 0:
                            exit_px, kind = op, 'stop'
                            gap_thru = fb[i] and (op - stop)*d < 0
                            break
                        if (op - tgt)*d >= 0:
                            exit_px, kind = op, 'target'; break
                    if d == 1: s_hit, t_hit = L[i] <= stop, H[i] >= tgt
                    else: s_hit, t_hit = H[i] >= stop, L[i] <= tgt
                    if s_hit: exit_px, kind = stop, 'stop'; break
                    if t_hit: exit_px, kind = tgt, 'target'; break
                if exit_px is None:
                    exit_px, kind = C[dl], 'time'
                gross_r = d*(exit_px - entry)/stop_dist
                costs = (STT + EXCH + SLIP)*qty*(entry + exit_px) + DP
                net_r = (qty*d*(exit_px - entry) - costs)/(qty*stop_dist)
                hh, ll = max(H[e:dl+1]), min(L[e:dl+1])
                mfe = (hh - entry)/a if d == 1 else (entry - ll)/a
                mae = (entry - ll)/a if d == 1 else (hh - entry)/a
                rows.append(dict(symbol=sym, det=z['det'], dir=d, k=K, H=Hs,
                                 entry_d=sd, r1=r1, r2=r2, r3=r3, r2_any=r2_any,
                                 gross_r=gross_r, net_r=net_r, exit=kind,
                                 gap_thru=gap_thru,
                                 gap_excess=(stop - exit_px)*d/stop_dist if gap_thru else np.nan,
                                 mfe=mfe, mae=mae,
                                 th='T1' if sd < SPLIT else 'T2', Chalf=half))

df = pd.DataFrame(rows)
df.to_parquet(f'{SCR}/native30_trades.parquet')
NS = df.entry_d.nunique()
print(f'\nsessions(any entry)={NS}  30m-zone stats: {zstats}')
print(f'D1 zones: total={sum(d1_zone_counts)} mean/sym={np.mean(d1_zone_counts):.1f} '
      f'syms_with>=1={d1_zone_syms}/50  min={min(d1_zone_counts)} max={max(d1_zone_counts)}')
print(f'skipped: atr_warmup={skipped_atr} qty0={skipped_qty} censored(window off data)={censored}')
print(f'ATR(14,30m) as % of price: median={np.median(atr_pcts)*100:.2f}% '
      f'p25={np.percentile(atr_pcts,25)*100:.2f}% p75={np.percentile(atr_pcts,75)*100:.2f}%')
b1 = df[(df.k == 1.5) & (df.H == 5)]
print(f'r2_any coverage (a live aligned D1 zone existed, overlap not required): '
      f'{b1.r2_any.mean()*100:.1f}% of trade candidates')
print(f'per-det trade mix (k1.5 H5): {b1.det.value_counts().to_dict()}')
print(f'dir mix (k1.5 H5): {b1["dir"].value_counts().to_dict()}')

# ---------- cell table ----------
print('\n## CELLS  (rungs cumulative; win% = netR>0; ratio = meanMFE/meanMAE over full H window)')
hdr = '| cell | n | win% | grossR | netR | netR_long | MFE/MAE | T1C0 | T1C1 | T2C0 | T2C1 | alive |'
print(hdr); print('|' + '---|'*12)
quads = [('T1', 0), ('T1', 1), ('T2', 0), ('T2', 1)]
for K in KS:
    for Hs in HS:
        sub = df[(df.k == K) & (df.H == Hs)]
        for name, m in (('all', pd.Series(True, sub.index)), ('r1', sub.r1),
                        ('r1+2', sub.r1 & sub.r2), ('r1+2+3', sub.r1 & sub.r2 & sub.r3)):
            s = sub[m]
            if not len(s):
                print(f'| k{K} H{Hs} {name} | 0 | — | — | — | — | — | — | — | — | — | — |'); continue
            qvals = []
            for t, c in quads:
                q = s[(s.th == t) & (s.Chalf == c)]
                qvals.append(q.net_r.mean() if len(q) else np.nan)
            alive = s.net_r.mean() > 0 and all(np.isfinite(v) and v > 0 for v in qvals)
            print(f'| k{K} H{Hs} {name} | {len(s)} | {100*(s.net_r>0).mean():.1f} '
                  f'| {s.gross_r.mean():+.3f} | {s.net_r.mean():+.3f} '
                  f'| {s[s["dir"]==1].net_r.mean():+.3f} '
                  f'| {s.mfe.mean()/s.mae.mean():.3f} '
                  + ''.join(f'| {v:+.3f} ' if np.isfinite(v) else '| n/a ' for v in qvals)
                  + f'| {"ALIVE" if alive else "dead"} |')

# ---------- gap + cost + cadence stats ----------
print('\n## GAPS / COSTS / CADENCE')
for K in KS:
    for Hs in HS:
        s = df[(df.k == K) & (df.H == Hs)]
        st = s[s.exit == 'stop']
        g = s[s.gap_thru]
        print(f'k{K} H{Hs}: stops={len(st)}/{len(s)} ({100*len(st)/len(s):.1f}%)  '
              f'overnight-gap-through={len(g)} ({100*len(g)/len(s):.1f}% of trades, '
              f'{100*len(g)/max(1,len(st)):.1f}% of stops)  mean_excess={g.gap_excess.mean():.2f}R  '
              f'max_excess={g.gap_excess.max():.2f}R  cost_drag={(s.gross_r-s.net_r).mean():.3f}R')
r3c = df[(df.k == 1.5) & (df.H == 5) & df.r1 & df.r2 & df.r3]
r3c10 = df[(df.k == 1.5) & (df.H == 10) & df.r1 & df.r2 & df.r3]
Q = NS/63.0
print(f'\nrung-3 cadence: k1.5 H5 n={len(r3c)} -> {len(r3c)/Q:.1f} trades/quarter '
      f'(50-stock portfolio); H10 n={len(r3c10)} -> {len(r3c10)/Q:.1f}/qtr')
print(f'exit mix k1.5 H5 all: {df[(df.k==1.5)&(df.H==5)].exit.value_counts().to_dict()}')
print(f'exit mix k1.5 H10 all: {df[(df.k==1.5)&(df.H==10)].exit.value_counts().to_dict()}')
print(f'\ntotal runtime {time.time()-t0:.0f}s')
