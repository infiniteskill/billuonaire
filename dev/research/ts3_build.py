"""ts3_build — detect pools/sweeps/voids/coils on all 138 syms + outcomes + matched time-local nulls."""
import sys, zlib, time
import numpy as np, pandas as pd
SC = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
sys.path.insert(0, SC)
import ts3_lib as L

FILLCAP = 1000
T1N = (50, 100, 200)   # horizons from pool birth
T1AN = (24, 50)        # horizons from first approach (<=3 ATR)
TOUCH_CAP = 5


def reach(h, l, t0, P, side, N, nseg):
    e = min(nseg, t0 + 1 + N)
    if t0 + 1 >= e: return False
    return bool(h[t0 + 1:e].max() >= P) if side == 'H' else bool(l[t0 + 1:e].min() <= P)


def main():
    data = L.load()
    P1, P1A, P2, P3V, P3F, P4 = [], [], [], [], [], []
    t_start = time.time()
    for si, sym in enumerate(sorted(data)):
        g = data[sym]
        rng = np.random.default_rng(zlib.crc32(sym.encode()))
        for seg_id, (a, b) in enumerate(L.segments(g)):
            d, atr, piv = L.prep(g, a, b)
            n = len(d)
            h, l, c, o = d['high'].values, d['low'].values, d['close'].values, d['open'].values
            ts = d['ts'].values
            pools = L.build_pools(d, atr, piv, n)
            voids = L.build_voids(d, atr, n)
            fvgs = L.build_fvgs(d, n)
            coils, comp, r14, hs, ls = L.build_coils(d, atr, n)
            base = dict(sym=sym, seg=seg_id)
            rmaxh = pd.Series(h).rolling(100, min_periods=20).max().values
            rminl = pd.Series(l).rolling(100, min_periods=20).min().values

            def virgin_nulls(t0, d_atr, side):
                cand = np.arange(max(14, t0 - 150), min(n - 1, t0 + 150))
                cand = cand[np.abs(cand - t0) > 3]
                if side == 'H':
                    lv = c[cand] + d_atr * atr[cand]
                    cand = cand[lv > rmaxh[cand]]
                else:
                    lv = c[cand] - d_atr * atr[cand]
                    cand = cand[lv < rminl[cand]]
                if not len(cand): return np.array([], int)
                return rng.choice(cand, size=min(L.NNULL, len(cand)), replace=len(cand) < L.NNULL)

            # ---------- T1 pools: magnetism ----------
            for pi, p in enumerate(pools):
                fat = p['eq'] + p['hist']
                row = dict(base, ts=ts[p['birth']], side=p['side'], d_atr=p['d_atr'],
                           fat=fat, eq=p['eq'], hist=p['hist'], dtyp=p['dtyp'],
                           life=(p['death'] - p['birth']) if p['death'] >= 0 else -1)
                nb = L.null_bars(rng, p['birth'], 14, n - 1)
                nbv = virgin_nulls(p['birth'], p['d_atr'], p['side'])
                sgn = 1 if p['side'] == 'H' else -1
                for N in T1N:
                    row[f'r{N}'] = p['death'] >= 0 and p['death'] - p['birth'] <= N
                    row[f'nk{N}'] = sum(reach(h, l, t2, c[t2] + sgn * p['d_atr'] * atr[t2], p['side'], N, n) for t2 in nb)
                    row[f'nkv{N}'] = sum(reach(h, l, t2, c[t2] + sgn * p['d_atr'] * atr[t2], p['side'], N, n) for t2 in nbv)
                row['nn'], row['nnv'] = len(nb), len(nbv)
                P1.append(row)
                # approach events
                if p['t_app'] >= 0:
                    ta = p['t_app']
                    rowa = dict(base, ts=ts[ta], side=p['side'], d_atr=p['d_app'], fat=fat)
                    nba = L.null_bars(rng, ta, 14, n - 1)
                    nbav = virgin_nulls(ta, p['d_app'], p['side'])
                    for N in T1AN:
                        rowa[f'r{N}'] = p['death'] >= 0 and p['death'] - ta <= N
                        rowa[f'nk{N}'] = sum(reach(h, l, t2, c[t2] + sgn * p['d_app'] * atr[t2], p['side'], N, n) for t2 in nba)
                        rowa[f'nkv{N}'] = sum(reach(h, l, t2, c[t2] + sgn * p['d_app'] * atr[t2], p['side'], N, n) for t2 in nbav)
                    rowa['nn'], rowa['nnv'] = len(nba), len(nbav)
                    P1A.append(rowa)

                # ---------- T2 sweep / touch respect ----------
                rev = -1 if p['side'] == 'H' else 1
                evs = []
                if p['dtyp'] == 'sweep': evs.append(('sweep', p['death']))
                evs += [('touch', tb) for tb in p['touch_bars'][:TOUCH_CAP]]
                for typ, t0 in evs:
                    dirn, bars = L.race(h, l, c, atr, t0)
                    ndec = nhit = 0
                    for t2 in L.null_bars(rng, t0, 14, n - 1):
                        d2, _ = L.race(h, l, c, atr, t2)
                        if d2 != 0:
                            ndec += 1; nhit += d2 == rev
                    P2.append(dict(base, ts=ts[t0], typ=typ, side=p['side'], rev=rev,
                                   out=dirn, bars=bars, fat=fat, ndec=ndec, nhit=nhit))

            # ---------- T3 voids ----------
            inside_mask = np.zeros(n, bool)
            vrows = []
            for v in voids:
                e, lo_, hi_, dirn = v['e'], v['lo'], v['hi'], v['dirn']
                end = min(n, e + 1 + FILLCAP)
                far = lo_ if dirn > 0 else hi_
                mid = 0.5 * (lo_ + hi_)
                w_l, w_h, w_c = l[e + 1:end], h[e + 1:end], c[e + 1:end]
                hitfar = np.nonzero(w_l <= far)[0] if dirn > 0 else np.nonzero(w_h >= far)[0]
                fill = e + 1 + hitfar[0] if len(hitfar) else -1
                hitmid = np.nonzero(w_l <= mid)[0] if dirn > 0 else np.nonzero(w_h >= mid)[0]
                tmid = e + 1 + hitmid[0] if len(hitmid) else -1
                inz = np.nonzero((w_c > lo_) & (w_c < hi_))[0]
                tre = e + 1 + inz[0] if len(inz) else -1
                row = dict(base, ts=ts[e], dirn=dirn, trav_atr=v['trav_atr'], nfvg=v['nfvg'],
                           nbars=v['e'] - v['s'] + 1, fill=fill, bars_fill=(fill - e) if fill >= 0 else -1,
                           tre=tre)
                # inside-corridor speed (post re-entry, pre fill)
                if tre >= 0:
                    lim = fill if fill >= 0 else min(n, tre + 300)
                    idx = np.arange(tre + 1, max(tre + 1, min(lim + 1, n)))
                    if len(idx):
                        m = (c[idx] > lo_) & (c[idx] < hi_)
                        idx = idx[m]
                    if len(idx):
                        row['spd_in'] = float(np.mean(np.abs(c[idx] - c[idx - 1]) / atr[idx]))
                        row['n_in'] = len(idx)
                        inside_mask[idx] = True
                    else:
                        row['spd_in'], row['n_in'] = np.nan, 0
                else:
                    row['spd_in'], row['n_in'] = np.nan, 0
                # traversal-time test: from first close-inside to far edge, vs momentum-matched
                # null travelling the same ATR distance in the same direction
                row['d_trav'], row['trav_bars'] = np.nan, -1
                row['ntrv'], row['ntrv30'], row['ntrv100'] = 0, 0, 0
                if tre >= 0 and (fill < 0 or fill > tre):
                    dtv = abs(c[tre] - far) / atr[tre]
                    row['d_trav'] = dtv
                    row['trav_bars'] = fill - tre if fill >= 0 else -1
                    step = np.sign(c[1:] - c[:-1])
                    want = -1 if dirn > 0 else 1        # traversal direction opposes void direction
                    cand = np.arange(max(15, tre - 150), min(n - 301, tre + 150))
                    if len(cand):
                        cand = cand[step[cand - 1] == want]
                    if len(cand):
                        for t2 in rng.choice(cand, size=min(L.NNULL, len(cand)), replace=len(cand) < L.NNULL):
                            tgt = c[t2] + want * dtv * atr[t2]
                            wl = l[t2 + 1:t2 + 301] if want < 0 else h[t2 + 1:t2 + 301]
                            hitn = np.nonzero(wl <= tgt)[0] if want < 0 else np.nonzero(wl >= tgt)[0]
                            row['ntrv'] += 1
                            if len(hitn):
                                row['ntrv30'] += hitn[0] + 1 <= 30
                                row['ntrv100'] += hitn[0] + 1 <= 100
                # edge vs mid respect races (bounce back INTO void direction)
                bounce = 1 if dirn > 0 else -1
                if fill >= 0:
                    de, _ = L.race(h, l, c, atr, fill)
                    row['edge_out'] = de * bounce   # +1 respect, -1 violate, 0 undecided
                else: row['edge_out'] = 9
                if tmid >= 0 and (fill < 0 or tmid < fill):
                    dm, _ = L.race(h, l, c, atr, tmid)
                    row['mid_out'] = dm * bounce
                else: row['mid_out'] = 9
                vrows.append((row, tre))
            # null speed: matched non-void bars, time-local
            for row, tre in vrows:
                if row['n_in'] > 0:
                    w0, w1 = max(15, tre - 250), min(n, tre + 250)
                    candm = ~inside_mask[w0:w1]
                    cand = np.arange(w0, w1)[candm]
                    cand = cand[cand > 15]
                    if len(cand):
                        pick = rng.choice(cand, size=min(40, len(cand)), replace=False)
                        row['spd_out'] = float(np.mean(np.abs(c[pick] - c[pick - 1]) / atr[pick]))
                        row['n_out'] = len(pick)
                    else:
                        row['spd_out'], row['n_out'] = np.nan, 0
                else:
                    row['spd_out'], row['n_out'] = np.nan, 0
                P3V.append(row)

            # ---------- T3 lone FVGs ----------
            vspans = [(v['s'] - 1, v['e'] + 1) for v in voids]
            for f in fvgs:
                m = f['m']
                if any(s <= m <= e for s, e in vspans): continue
                end = min(n, m + 2 + FILLCAP)
                w_l, w_h = l[m + 2:end], h[m + 2:end]
                hit = np.nonzero(w_l <= f['far'])[0] if f['dirn'] > 0 else np.nonzero(w_h >= f['far'])[0]
                P3F.append(dict(base, ts=ts[m], dirn=f['dirn'], gap_atr=f['gap'] / atr[m],
                                bars_fill=(hit[0] + 1) if len(hit) else -1))

            # ---------- T4 coils ----------
            ratio = np.where(atr > 0, r14 / atr, np.nan)
            okn = np.nonzero((~np.isnan(ratio)) & (ratio >= L.NCK) & (np.arange(n) >= 28))[0]
            for co in coils:
                t0 = co['t']
                oc = L.coil_outcome(h, l, c, atr, t0, co['top'], co['bot'], n)
                if oc is None: continue
                tb, side = oc['tb'], oc['side']
                tol = 0.25 * atr[tb]
                if side > 0:
                    swept = any(p['side'] == 'H' and p['birth'] < tb and (p['death'] == -1 or p['death'] >= tb)
                                and co['top'] - tol <= p['P'] <= h[tb] for p in pools)
                else:
                    swept = any(p['side'] == 'L' and p['birth'] < tb and (p['death'] == -1 or p['death'] >= tb)
                                and l[tb] <= p['P'] <= co['bot'] + tol for p in pools)
                nrev = ncont = nund = 0
                loc = okn[np.abs(okn - t0) <= 250]
                if len(loc):
                    for t2 in rng.choice(loc, size=min(L.NNULL, len(loc)), replace=len(loc) < L.NNULL):
                        oc2 = L.coil_outcome(h, l, c, atr, int(t2), hs[t2], ls[t2], n)
                        if oc2 is None: continue
                        nrev += oc2['res'] == 'rev'; ncont += oc2['res'] == 'cont'; nund += oc2['res'] == 'und'
                depth = (h[tb] - co['top']) / atr[tb] if side > 0 else (co['bot'] - l[tb]) / atr[tb]
                P4.append(dict(base, ts=ts[t0], t=t0, tb=tb, side=side, res=oc['res'], lag=oc['lag'],
                               swept=bool(swept), depth=depth, nrev=nrev, ncont=ncont, nund=nund))
        if si % 20 == 0:
            print(f"[{si:3d}/138] {sym} t={time.time()-t_start:.0f}s "
                  f"P1={len(P1)} P2={len(P2)} V={len(P3V)} F={len(P3F)} C={len(P4)}", flush=True)

    for name, rows in [('t1_pools', P1), ('t1_app', P1A), ('t2_events', P2),
                       ('t3_voids', P3V), ('t3_fvgs', P3F), ('t4_coils', P4)]:
        df = pd.DataFrame(rows)
        df.to_parquet(f'{SC}/ts3_{name}.parquet')
        print(name, df.shape)
    print(f"done in {time.time()-t_start:.0f}s")


if __name__ == '__main__':
    main()
