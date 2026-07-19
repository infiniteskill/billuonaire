"""ts3_agg — T1..T4 stats: paired excess vs matched nulls, temporal-thirds + crc32-half holdouts."""
import zlib
import numpy as np, pandas as pd
SC = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'

T0 = pd.Timestamp('2023-08-04', tz='Asia/Kolkata')
T3_ = pd.Timestamp('2026-07-18', tz='Asia/Kolkata')
CUT1 = T0 + (T3_ - T0) / 3
CUT2 = T0 + 2 * (T3_ - T0) / 3


def cells(df):
    ts = pd.to_datetime(df['ts'])
    c1, c2 = CUT1, CUT2
    if ts.dt.tz is None:  # stored .values are UTC-naive
        c1, c2 = c1.tz_convert('UTC').tz_localize(None), c2.tz_convert('UTC').tz_localize(None)
    yr = np.where(ts < c1, 'y1', np.where(ts < c2, 'y2', 'y3'))
    hf = df['sym'].map(lambda s: 'h' + str(zlib.crc32(s.encode()) % 2))
    return yr, hf


def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 3: return np.nan, np.nan, len(x)
    return float(x.mean()), float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))), len(x)


def gauntlet(df, exc_col, label):
    yr, hf = cells(df)
    m, t, n = tstat(df[exc_col])
    parts = {}
    for tag, mask in [('y1', yr == 'y1'), ('y2', yr == 'y2'), ('y3', yr == 'y3'),
                      ('h0', hf == 'h0'), ('h1', hf == 'h1')]:
        mm, _, nn = tstat(df.loc[mask, exc_col])
        parts[tag] = mm
    signs = [np.sign(v) for v in parts.values() if not np.isnan(v)]
    ok = len(signs) == 5 and all(s == np.sign(m) for s in signs) and m != 0
    cellstr = ' '.join(f"{k}:{v:+.3f}" for k, v in parts.items())
    print(f"  {label:34s} n={n:6d} excess={m:+.4f} t={t:+6.2f} | {cellstr} | {'PASS' if ok else 'fail'}")
    return dict(label=label, n=n, excess=m, t=t, **parts, ok=ok)


R = {}
print("=" * 100)
print("T1 — POOL MAGNETISM (reach pool level vs matched random level, same distance/ATR/side)")
p1 = pd.read_parquet(f'{SC}/ts3_t1_pools.parquet')
p1 = p1[p1['nn'] > 0]
for N in (50, 100, 200):
    p1[f'exc{N}'] = p1[f'r{N}'].astype(float) - p1[f'nk{N}'] / p1['nn']
    r, nl = p1[f'r{N}'].mean(), (p1[f'nk{N}'] / p1['nn']).mean()
    print(f"  N={N}: reach_pool={r:.3f} reach_null={nl:.3f}")
R['t1_100'] = gauntlet(p1, 'exc100', 'T1 birth N=100')
R['t1_200'] = gauntlet(p1, 'exc200', 'T1 birth N=200')
p1v = p1[p1['nnv'] > 0].copy()
for N in (100, 200):
    p1v[f'excv{N}'] = p1v[f'r{N}'].astype(float) - p1v[f'nkv{N}'] / p1v['nnv']
    print(f"  virgin null N={N}: reach_pool={p1v[f'r{N}'].mean():.3f} reach_vnull={(p1v[f'nkv{N}']/p1v['nnv']).mean():.3f}")
R['t1v_100'] = gauntlet(p1v, 'excv100', 'T1 birth N=100 VIRGIN null')
for sd in 'HL':
    gauntlet(p1[p1['side'] == sd], 'exc100', f'T1 birth N=100 side={sd}')
print("  fatness split (N=100): excess by tier")
tiers = [('f0', p1['fat'] == 0), ('f1', p1['fat'] == 1), ('f2+', p1['fat'] >= 2)]
for tag, m in tiers:
    sub = p1[m]
    e, t, n = tstat(sub['exc100'])
    print(f"    {tag:3s} n={n:5d} reach={sub['r100'].mean():.3f} null={(sub['nk100']/sub['nn']).mean():.3f} excess={e:+.4f} t={t:+.2f}")
R['t1_fat'] = [tstat(p1[m]['exc100'])[0] for _, m in tiers]

print("\nT1b — approach events (first close within 3 ATR of pool)")
pa = pd.read_parquet(f'{SC}/ts3_t1_app.parquet')
pa = pa[pa['nn'] > 0]
for N in (24, 50):
    pa[f'exc{N}'] = pa[f'r{N}'].astype(float) - pa[f'nk{N}'] / pa['nn']
    print(f"  N={N}: reach_pool={pa[f'r{N}'].mean():.3f} reach_null={(pa[f'nk{N}']/pa['nn']).mean():.3f}")
R['t1a_24'] = gauntlet(pa, 'exc24', 'T1 approach N=24')
R['t1a_50'] = gauntlet(pa, 'exc50', 'T1 approach N=50')
pav = pa[pa['nnv'] > 0].copy()
for N in (24, 50):
    pav[f'excv{N}'] = pav[f'r{N}'].astype(float) - pav[f'nkv{N}'] / pav['nnv']
    print(f"  virgin null N={N}: reach_pool={pav[f'r{N}'].mean():.3f} reach_vnull={(pav[f'nkv{N}']/pav['nnv']).mean():.3f}")
R['t1av_24'] = gauntlet(pav, 'excv24', 'T1 approach N=24 VIRGIN null')
R['t1av_50'] = gauntlet(pav, 'excv50', 'T1 approach N=50 VIRGIN null')
for tag, m in [('f0', pa['fat'] == 0), ('f1', pa['fat'] == 1), ('f2+', pa['fat'] >= 2)]:
    sub = pa[m]
    e, t, n = tstat(sub['exc24'])
    sv = pav[pav['fat'].eq(0) if tag == 'f0' else (pav['fat'].eq(1) if tag == 'f1' else pav['fat'].ge(2))]
    ev, tv, _ = tstat(sv['excv24'])
    print(f"    {tag:3s} n={n:5d} reach={sub['r24'].mean():.3f} excess={e:+.4f} t={t:+.2f} | virgin excess={ev:+.4f} t={tv:+.2f}")

print("\n" + "=" * 100)
print("T2 — SWEEP -> REVERSAL PROPHECY (1-ATR first-crossing race in reversal direction)")
e2 = pd.read_parquet(f'{SC}/ts3_t2_events.parquet')
dec = e2[(e2['out'] != 0) & (e2['ndec'] > 0)].copy()
dec['resp'] = (dec['out'] == dec['rev']).astype(float)
dec['exc'] = dec['resp'] - dec['nhit'] / dec['ndec']
for typ in ('sweep', 'touch'):
    sub = dec[dec['typ'] == typ]
    print(f"  {typ}: n={len(sub)} respect={sub['resp'].mean():.3f} null={(sub['nhit']/sub['ndec']).mean():.3f}")
R['t2_sweep'] = gauntlet(dec[dec['typ'] == 'sweep'], 'exc', 'T2 sweep vs null')
R['t2_touch'] = gauntlet(dec[dec['typ'] == 'touch'], 'exc', 'T2 touch vs null')
# sweep-vs-touch contrast per cell
sw, tc = dec[dec['typ'] == 'sweep'], dec[dec['typ'] == 'touch']
yrs_s, hf_s = cells(sw); yrs_t, hf_t = cells(tc)
d_all = sw['resp'].mean() - tc['resp'].mean()
parts = {}
for tag in ('y1', 'y2', 'y3'):
    parts[tag] = sw.loc[yrs_s == tag, 'resp'].mean() - tc.loc[yrs_t == tag, 'resp'].mean()
for tag in ('h0', 'h1'):
    parts[tag] = sw.loc[hf_s == tag, 'resp'].mean() - tc.loc[hf_t == tag, 'resp'].mean()
se = np.sqrt(sw['resp'].var() / len(sw) + tc['resp'].var() / len(tc))
ok = all(np.sign(v) == np.sign(d_all) for v in parts.values())
print(f"  {'T2 sweep minus touch':34s} n={len(sw)}/{len(tc)} diff={d_all:+.4f} z={d_all/se:+.2f} | "
      + ' '.join(f'{k}:{v:+.3f}' for k, v in parts.items()) + f" | {'PASS' if ok else 'fail'}")
R['t2_svt'] = dict(label='T2 sweep-touch', n=len(sw), excess=d_all, t=d_all / se, **parts, ok=ok)
swr = sw[sw['resp'] == 1]
print(f"  sweep timing (bars to 1-ATR reversal, respecting sweeps n={len(swr)}): "
      f"med={swr['bars'].median():.0f} <=3:{(swr['bars']<=3).mean():.2f} <=6:{(swr['bars']<=6).mean():.2f} <=12:{(swr['bars']<=12).mean():.2f}")
und = e2[e2['typ'] == 'sweep']
print(f"  sweeps total={len(und)} decided={(und['out']!=0).mean():.2f}")
print(f"  sweep respect by fatness: " + ' '.join(
    f"{tag}:{sw[m2]['resp'].mean():.3f}(n={m2.sum()})" for tag, m2 in
    [('f0', sw['fat'] == 0), ('f1', sw['fat'] == 1), ('f2+', sw['fat'] >= 2)]))

print("\n" + "=" * 100)
print("T3 — VOID CORRIDOR LAW")
v = pd.read_parquet(f'{SC}/ts3_t3_voids.parquet')
f = pd.read_parquet(f'{SC}/ts3_t3_fvgs.parquet')
print(f"  voids n={len(v)} trav_atr med={v['trav_atr'].median():.2f} nfvg med={v['nfvg'].median():.0f} "
      f"len med={v['nbars'].median():.0f}; lone FVGs n={len(f)} gap_atr med={f['gap_atr'].median():.2f}")
# speed
vs = v[(v['n_in'] > 0) & (v['n_out'] > 0)].copy()
vs['dspd'] = vs['spd_in'] - vs['spd_out']
print(f"  corridor speed: inside={vs['spd_in'].mean():.3f} ATR/bar  matched-outside={vs['spd_out'].mean():.3f} ATR/bar "
      f"ratio={vs['spd_in'].mean()/vs['spd_out'].mean():.2f}  [close-in-zone conditioning biases slow]")
R['t3_speed'] = gauntlet(vs, 'dspd', 'T3 per-bar speed in-out (biased)')
# traversal-time test (primary): P(cross void span <= K bars) vs momentum-matched null same span
vt = v[(v['ntrv'] > 0) & (v['d_trav'].notna())].copy()
for K, col in [(30, 'ntrv30'), (100, 'ntrv100')]:
    vt[f'excT{K}'] = ((vt['trav_bars'] >= 0) & (vt['trav_bars'] <= K)).astype(float) - vt[col] / vt['ntrv']
    r = ((vt['trav_bars'] >= 0) & (vt['trav_bars'] <= K)).mean()
    nl = (vt[col] / vt['ntrv']).mean()
    print(f"  traversal <= {K} bars (span med={vt['d_trav'].median():.2f} ATR): void={r:.3f} null={nl:.3f}")
R['t3_trav30'] = gauntlet(vt, 'excT30', 'T3 traversal<=30 vs null')
R['t3_trav100'] = gauntlet(vt, 'excT100', 'T3 traversal<=100 vs null')
# fill time
vf, ff = v[v['bars_fill'] >= 0], f[f['bars_fill'] >= 0]
print(f"  fill: void filled%={len(vf)/len(v)*100:.1f} med_bars={vf['bars_fill'].median():.0f} | "
      f"loneFVG filled%={len(ff)/len(f)*100:.1f} med_bars={ff['bars_fill'].median():.0f}")
for tag, m in [('gap<0.25', f['gap_atr'] < 0.25), ('0.25-0.5', (f['gap_atr'] >= 0.25) & (f['gap_atr'] < 0.5)),
               ('gap>=0.5', f['gap_atr'] >= 0.5)]:
    sub = f[m & (f['bars_fill'] >= 0)]
    print(f"    FVG {tag:9s} n={len(sub):6d} filled%={len(sub)/max(1,m.sum())*100:.1f} med={sub['bars_fill'].median():.0f}")
# per-cell median fill diff
yrv, hfv = cells(v); yrf, hff = cells(f)
parts = {}
for tag, mv, mf in [('y1', yrv == 'y1', yrf == 'y1'), ('y2', yrv == 'y2', yrf == 'y2'),
                    ('y3', yrv == 'y3', yrf == 'y3'), ('h0', hfv == 'h0', hff == 'h0'), ('h1', hfv == 'h1', hff == 'h1')]:
    a = v.loc[mv & (v['bars_fill'] >= 0), 'bars_fill'].median()
    b = f.loc[mf & (f['bars_fill'] >= 0), 'bars_fill'].median()
    parts[tag] = a - b
d_all = vf['bars_fill'].median() - ff['bars_fill'].median()
ok = all(np.sign(x) == np.sign(d_all) for x in parts.values())
print(f"  {'T3 void-FVG med fill diff':34s} diff={d_all:+.0f} bars | " +
      ' '.join(f'{k}:{x:+.0f}' for k, x in parts.items()) + f" | {'PASS' if ok else 'fail'}")
R['t3_fill'] = dict(label='T3 fill diff', n=len(vf), excess=d_all, t=np.nan, **parts, ok=ok)
# edge vs mid
ve = v[v['edge_out'].isin([1, -1])].copy(); vm = v[v['mid_out'].isin([1, -1])].copy()
ve['re'] = (ve['edge_out'] == 1).astype(float); vm['rm'] = (vm['mid_out'] == 1).astype(float)
print(f"  edge respect={ve['re'].mean():.3f} (n={len(ve)})  mid respect={vm['rm'].mean():.3f} (n={len(vm)})")
yre, hfe = cells(ve); yrm, hfm = cells(vm)
parts = {}
for tag in ('y1', 'y2', 'y3'):
    parts[tag] = ve.loc[yre == tag, 're'].mean() - vm.loc[yrm == tag, 'rm'].mean()
for tag in ('h0', 'h1'):
    parts[tag] = ve.loc[hfe == tag, 're'].mean() - vm.loc[hfm == tag, 'rm'].mean()
d_all = ve['re'].mean() - vm['rm'].mean()
se = np.sqrt(ve['re'].var() / len(ve) + vm['rm'].var() / len(vm))
ok = all(np.sign(x) == np.sign(d_all) for x in parts.values())
print(f"  {'T3 edge minus mid respect':34s} diff={d_all:+.4f} z={d_all/se:+.2f} | " +
      ' '.join(f'{k}:{x:+.3f}' for k, x in parts.items()) + f" | {'PASS' if ok else 'fail'}")
R['t3_edge'] = dict(label='T3 edge-mid', n=len(ve), excess=d_all, t=d_all / se, **parts, ok=ok)

print("\n" + "=" * 100)
print("T4 — ACCUMULATION -> MANIPULATION (coil break reversal vs matched non-coil range break)")
c4 = pd.read_parquet(f'{SC}/ts3_t4_coils.parquet')
d4 = c4[c4['res'].isin(['rev', 'cont'])].copy()
d4['isrev'] = (d4['res'] == 'rev').astype(float)
d4['nulldec'] = d4['nrev'] + d4['ncont']
d4p = d4[d4['nulldec'] > 0].copy()
d4p['exc'] = d4p['isrev'] - d4p['nrev'] / d4p['nulldec']
print(f"  coil breaks n={len(c4)} decided={len(d4)} rev_rate={d4['isrev'].mean():.3f} "
      f"null_rev_rate={(d4p['nrev']/d4p['nulldec']).mean():.3f} undecided={(c4['res']=='und').mean():.2f}")
R['t4_null'] = gauntlet(d4p, 'exc', 'T4 coil rev vs non-coil null')
swp, pln = d4[d4['swept']], d4[~d4['swept']]
print(f"  swept-break rev={swp['isrev'].mean():.3f} (n={len(swp)})  plain-break rev={pln['isrev'].mean():.3f} (n={len(pln)})")
yrs, hfs = cells(swp); yrp, hfp = cells(pln)
parts = {}
for tag in ('y1', 'y2', 'y3'):
    parts[tag] = swp.loc[yrs == tag, 'isrev'].mean() - pln.loc[yrp == tag, 'isrev'].mean()
for tag in ('h0', 'h1'):
    parts[tag] = swp.loc[hfs == tag, 'isrev'].mean() - pln.loc[hfp == tag, 'isrev'].mean()
d_all = swp['isrev'].mean() - pln['isrev'].mean()
se = np.sqrt(swp['isrev'].var() / max(1, len(swp)) + pln['isrev'].var() / max(1, len(pln)))
ok = all(np.sign(x) == np.sign(d_all) for x in parts.values())
print(f"  {'T4 swept minus plain rev':34s} n={len(swp)}/{len(pln)} diff={d_all:+.4f} z={d_all/se:+.2f} | " +
      ' '.join(f'{k}:{x:+.3f}' for k, x in parts.items()) + f" | {'PASS' if ok else 'fail'}")
R['t4_swept'] = dict(label='T4 swept-plain', n=len(swp), excess=d_all, t=d_all / se, **parts, ok=ok)
print(f"  break lag med={d4['lag'].median():.0f} bars; sides: up={100*(d4['side']==1).mean():.0f}%")
print("  depth-controlled swept vs plain (break-wick penetration beyond edge, ATR):")
for tag, m in [('<0.5', d4['depth'] < 0.5), ('0.5-1', (d4['depth'] >= 0.5) & (d4['depth'] < 1)),
               ('1-2', (d4['depth'] >= 1) & (d4['depth'] < 2)), ('>=2', d4['depth'] >= 2)]:
    s2, p2 = d4[m & d4['swept']], d4[m & ~d4['swept']]
    print(f"    depth {tag:5s} swept rev={s2['isrev'].mean() if len(s2) else float('nan'):.3f} (n={len(s2):4d})  "
          f"plain rev={p2['isrev'].mean() if len(p2) else float('nan'):.3f} (n={len(p2):5d})")

print("\n" + "=" * 100)
print("PASS/FAIL SUMMARY")
for k, r in R.items():
    if isinstance(r, dict):
        print(f"  {r['label']:34s} excess={r['excess']:+.4f} t/z={r['t']:+6.2f} {'PASS' if r['ok'] else 'FAIL'}")
print(f"  T1 fatness monotone (f0,f1,f2+ excess): {['%+.4f' % x for x in R['t1_fat']]}")
