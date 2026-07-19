"""Aggregate cascade study: delay buckets, extreme-swing cross-tab, composite,
holdouts. Prints markdown tables."""
import numpy as np, pandas as pd, zlib

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
r = pd.read_parquet(f'{SCR}/casc_signals.parquet')
r = r[r.born_i >= 0].copy()
r['delay_min'] = (r.sig_i - r.born_i) * 5
r['same_day'] = r.born_date == r.session
BUCKETS = ['<30m', '30-60m', '1-4h', '>4h', 'nextday+']
def bucket(row_delay, same):
    if not same: return 'nextday+'
    if row_delay < 30: return '<30m'
    if row_delay < 60: return '30-60m'
    if row_delay < 240: return '1-4h'
    return '>4h'
r['bucket'] = [bucket(d, s) for d, s in zip(r.delay_min, r.same_day)]
r['T'] = np.where(r.session < '2026-06-08', 'T1', 'T2')
r['C'] = ['C' + str(zlib.crc32(s.encode()) % 2) for s in r.symbol]

# first signal per zone
r = r.sort_values('sig_i')
zone_key = ['symbol', 'detector', 'direction', 'born_ts']
first = r.groupby(zone_key, as_index=False).first()
first['bucket'] = pd.Categorical(first.bucket, BUCKETS)
r['bucket'] = pd.Categorical(r.bucket, BUCKETS)

def stats(g):
    v = g.dropna(subset=['net_r'])
    return pd.Series({'n': len(g), 'n_tr': len(v), 'hit%': 100*v.hit.mean(),
                      'netR': v.net_r.mean(), 'MFE': v.mfe.mean(), 'MAE': v.mae.mean()})

pd.set_option('display.width', 250); pd.set_option('display.float_format', lambda x: f'{x:.3f}')

print('=== A. Delay distribution (FIRST retest per zone) ===')
for det, g in first.groupby('detector'):
    sd = g[g.same_day]
    q = sd.delay_min.quantile([.25, .5, .75]).values
    fr = g.bucket.value_counts(normalize=True).reindex(BUCKETS) * 100
    print(f'{det}: zones={len(g)}, same-day delay q25/med/q75 = {q[0]:.0f}/{q[1]:.0f}/{q[2]:.0f} min')
    print('  bucket %: ' + '  '.join(f'{b}={fr[b]:.1f}' for b in BUCKETS))
print()
print('=== A2. All-signals bucket shares ===')
for det, g in r.groupby('detector'):
    fr = g.bucket.value_counts(normalize=True).reindex(BUCKETS) * 100
    print(f'{det}: n={len(g)}: ' + '  '.join(f'{b}={fr[b]:.1f}' for b in BUCKETS))
print()

print('=== B. Bucket outcomes, FIRST retest per zone ===')
for det, g in first.groupby('detector'):
    print(f'-- {det} (base: {stats(g).to_dict()})')
    print(g.groupby('bucket', observed=False).apply(stats, include_groups=False))
print('-- POOLED (3 detectors)')
print(first.groupby('bucket', observed=False).apply(stats, include_groups=False))
print('base pooled:', stats(first).to_dict())
print()

print('=== B2. Bucket outcomes, ALL signals (tradeable universe) ===')
for det, g in r.groupby('detector'):
    print(f'-- {det} base hit% {100*g.hit.mean():.1f} netR {g.net_r.mean():.3f} n={len(g)}')
    print(g.groupby('bucket', observed=False).apply(stats, include_groups=False))
print()

print('=== C. Cross-tab bucket x near-extreme-swing (FIRST retest, pooled) ===')
for ne in [False, True]:
    print(f'-- near_ext={ne}')
    print(first[first.near_ext == ne].groupby('bucket', observed=False).apply(stats, include_groups=False))
print('near_ext share overall:', first.near_ext.mean())
print()

print('=== D. Composite cell: (>=1h same-day OR next-day+) AND near-extreme ===')
first['delayed'] = first.bucket.isin(['1-4h', '>4h', 'nextday+'])
first['composite'] = first.delayed & first.near_ext
for det, g in first.groupby('detector'):
    base = stats(g); comp = stats(g[g.composite])
    print(f'{det}: base hit {base["hit%"]:.1f} netR {base["netR"]:.3f} | composite n={comp["n"]:.0f} '
          f'hit {comp["hit%"]:.1f} netR {comp["netR"]:.3f} | lift {comp["hit%"]-base["hit%"]:+.1f}pp {comp["netR"]-base["netR"]:+.3f}R')
g = first; base = stats(g); comp = stats(g[g.composite])
print(f'POOLED: base hit {base["hit%"]:.1f} netR {base["netR"]:.3f} | composite n={comp["n"]:.0f} '
      f'hit {comp["hit%"]:.1f} netR {comp["netR"]:.3f} MFE {comp["MFE"]:.2f} MAE {comp["MAE"]:.2f} | lift {comp["hit%"]-base["hit%"]:+.1f}pp')
# variants
for name, cond in [('nextday+ only', first.bucket == 'nextday+'),
                   ('nextday+ & near_ext', (first.bucket == 'nextday+') & first.near_ext),
                   ('>=1h same-day only', first.bucket.isin(['1-4h', '>4h'])),
                   ('delayed (no ext filter)', first.delayed),
                   ('near_ext only', first.near_ext),
                   ('STRICT ext only (3ATR/0.5ATR)', first.near_ext3),
                   ('delayed & STRICT ext', first.delayed & first.near_ext3),
                   ('nextday+ & STRICT ext', (first.bucket == 'nextday+') & first.near_ext3)]:
    comp = stats(first[cond])
    print(f'variant {name}: n={comp["n"]:.0f} hit {comp["hit%"]:.1f} netR {comp["netR"]:.3f} lift {comp["hit%"]-base["hit%"]:+.1f}pp')
print()

print('=== E. Holdouts (pooled, FIRST retest): composite vs base per cell ===')
def cell_table(cond, label):
    rows = []
    for col, val in [('T', 'T1'), ('T', 'T2'), ('C', 'C0'), ('C', 'C1')]:
        g = first[first[col] == val]
        b = stats(g); cmp_ = stats(g[cond[g.index]])
        rows.append({'cell': val, 'n': int(cmp_['n']), 'base_hit': b['hit%'], 'hit': cmp_['hit%'],
                     'lift_pp': cmp_['hit%'] - b['hit%'], 'base_netR': b['netR'],
                     'netR': cmp_['netR'], 'liftR': cmp_['netR'] - b['netR']})
    t = pd.DataFrame(rows)
    print(f'-- {label}'); print(t.to_string(index=False))
    same_hit = (np.sign(t.lift_pp) == np.sign(t.lift_pp.iloc[0])).all() and t.lift_pp.iloc[0] != 0
    same_R = (np.sign(t.liftR) == np.sign(t.liftR.iloc[0])).all()
    print(f'   same-sign all 4 cells: hit-lift={same_hit}, netR-lift={same_R}')
cell_table(first.composite, 'composite (delayed & near_ext)')
cell_table(first.delayed, 'delayed only')
cell_table(first.bucket == 'nextday+', 'nextday+ only')
cell_table((first.bucket == 'nextday+') & first.near_ext, 'nextday+ & near_ext')
cell_table((first.bucket == 'nextday+') & first.near_ext3, 'nextday+ & STRICT ext')
print()

print('=== E2. Per-detector composite holdout sign check ===')
for det in ['fvg_cb', 'ob_lux', 'mitigation']:
    g0 = first[first.detector == det]
    signs = []
    for col, val in [('T','T1'),('T','T2'),('C','C0'),('C','C1')]:
        g = g0[g0[col] == val]
        b = stats(g); cm = stats(g[g.composite])
        signs.append((val, round(cm['hit%']-b['hit%'],1), round(cm['netR']-b['netR'],3), int(cm['n'])))
    print(det, signs)
