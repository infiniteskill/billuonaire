"""ts3_check — independent brute-force invariant verification of built events vs raw bars."""
import sys
import numpy as np, pandas as pd
SC = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
sys.path.insert(0, SC)
import ts3_lib as L

data = L.load()
rng = np.random.default_rng(7)
fails = 0
for sym in ['HEROMOTOCO', 'RELIANCE', 'INFY']:
    g = data[sym]
    for a, b in L.segments(g):
        d, atr, piv = L.prep(g, a, b)
        n = len(d)
        h, l, c, o = d['high'].values, d['low'].values, d['close'].values, d['open'].values
        pools = L.build_pools(d, atr, piv, n)
        # pool invariants
        for p in rng.choice(pools, size=min(25, len(pools)), replace=False):
            P, sd, bi, de = p['P'], p['side'], p['birth'], p['death']
            ext = h if sd == 'H' else l
            assert abs(ext[p['pividx']] - P) < 1e-9, 'pivot price mismatch'
            hi_end = de if de >= 0 else n
            seg_ = h[bi + 1:hi_end] if sd == 'H' else l[bi + 1:hi_end]
            if sd == 'H': assert not np.any(seg_ >= P), 'penetration before death'
            else: assert not np.any(seg_ <= P), 'penetration before death'
            if de >= 0:
                pen = h[de] >= P if sd == 'H' else l[de] <= P
                assert pen, 'death bar does not penetrate'
                back = c[de] < P if sd == 'H' else c[de] > P
                assert (p['dtyp'] == 'sweep') == back, 'sweep/break tag wrong'
            # two-sided leg >= max(6*ATR, 4.7%) around the pivot (approx: vs neighbours in piv list)
        # zigzag leg floor: check every confirmed pivot's legs
        pv = [p for p in piv if not p.pending]
        for j in range(1, len(pv) - 1):
            leg_in = abs(pv[j].price - pv[j - 1].price)
            thr = 0.9 * max(L.K * atr[pv[j].idx], L.PCT * c[pv[j].idx])  # 10% slack: ATR at confirm differs
            if leg_in < thr:
                fails += 1
        # voids
        voids = L.build_voids(d, atr, n)
        for v in rng.choice(voids, size=min(25, len(voids)), replace=False):
            s, e, dirn = v['s'], v['e'], v['dirn']
            sg = np.sign(c[s:e + 1] - o[s:e + 1])
            assert np.all(sg == dirn), 'mixed-direction run'
            trav = (c[e] - o[s]) * dirn
            assert trav >= L.VTRAV * atr[e] - 1e-9, 'travel too small'
            if e > s:
                assert trav / (h[s:e + 1].max() - l[s:e + 1].min()) >= L.VEFF - 1e-9, 'efficiency'
        # coils
        coils, comp, r14, hs, ls = L.build_coils(d, atr, n)
        for co in coils:
            t = co['t']
            assert h[t - L.CMPM + 1:t + 1].max() - l[t - L.CMPM + 1:t + 1].min() <= L.CMPK * atr[t] + 1e-9, 'not compressed'
            assert abs(co['top'] - h[t - L.CMPM + 1:t + 1].max()) < 1e-9, 'top mismatch'
    print(f"{sym}: invariants OK ({len(pools)} pools, {len(voids)} voids, {len(coils)} coils last seg)")
print(f"zigzag leg-floor soft violations (confirm-bar ATR drift): {fails}")

# extra splits on built tables
e2 = pd.read_parquet(f'{SC}/ts3_t2_events.parquet')
dec = e2[(e2['out'] != 0) & (e2['ndec'] > 0)].copy()
dec['resp'] = (dec['out'] == dec['rev']).astype(float)
dec['exc'] = dec['resp'] - dec['nhit'] / dec['ndec']
sw = dec[dec['typ'] == 'sweep']
for sd in 'HL':
    s2 = sw[sw['side'] == sd]
    print(f"T2 sweep side={sd}: n={len(s2)} respect={s2['resp'].mean():.3f} excess={s2['exc'].mean():+.4f} "
          f"t={s2['exc'].mean()/(s2['exc'].std()/np.sqrt(len(s2))):+.2f}")
p1 = pd.read_parquet(f'{SC}/ts3_t1_pools.parquet')
print("pool inventory: n=%d  sweep%%=%.1f break%%=%.1f eos%%=%.1f  fat: f0=%.2f f1=%.2f f2+=%.2f  d_atr med=%.1f  life med=%d" % (
    len(p1), *(100 * (p1['dtyp'] == k).mean() for k in ('sweep', 'break', 'eos')),
    (p1['fat'] == 0).mean(), (p1['fat'] == 1).mean(), (p1['fat'] >= 2).mean(),
    p1['d_atr'].median(), p1.loc[p1['life'] > 0, 'life'].median()))
v = pd.read_parquet(f'{SC}/ts3_t3_voids.parquet')
print("void inventory: n=%d trav med=%.2f ATR, nfvg>0 %.0f%%, refill(re-entry)%%=%.1f" % (
    len(v), v['trav_atr'].median(), 100 * (v['nfvg'] > 0).mean(), 100 * (v['tre'] >= 0).mean()))
c4 = pd.read_parquet(f'{SC}/ts3_t4_coils.parquet')
print("coil inventory: n=%d swept%%=%.1f depth med=%.2f" % (len(c4), 100 * c4['swept'].mean(), c4['depth'].median()))
