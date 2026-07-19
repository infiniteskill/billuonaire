"""geo_agg.py — aggregate geometry sweep: cells x geometries, 4-way holdouts, CIs."""
import numpy as np, pandas as pd, zlib

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
COST = 0.0006
KS = [1.5, 2.5, 4.0, 6.0, 10.0]
GEOS = [(k, t) for k in KS for t in [1.0, 1.5, 2.0]] + [(k, 'trail') for k in KS]
pd.set_option('display.width', 250)

first = pd.read_parquet(f'{SCR}/facts_first.parquet')
geo = pd.read_parquet(f'{SCR}/geo_trades.parquet')
df = first.join(geo)
df['T'] = np.where(df.session < '2026-06-08', 'T1', 'T2')
df['C'] = ['C' + str(zlib.crc32(s.encode()) % 2) for s in df.symbol]
nd = (df.born_date != df.session)
CELLS = {
    'base (all zones)': pd.Series(True, index=df.index),
    'nextday+': nd,
    'nextday+ & h1_nested': nd & df.h1_nested,
    'nextday+ & sweep_aligned': nd & df.sweep_aligned,
    'LADDER (nd+ & swp & h1n)': nd & df.sweep_aligned & df.h1_nested,
}

def tag(k, t): return f'k{k}_{t}' if t != 'trail' else f'k{k}_trail'

# per-trade cost per k
for k in KS:
    df[f'cost_k{k}'] = COST * df.entry / (k * df.atr)

rows = []
for cname, cm in CELLS.items():
    for k, t in GEOS:
        tg = tag(k, t)
        g = df.loc[cm & df[f'g_{tg}'].notna(), ['symbol', 'session', 'T', 'C',
                                                f'g_{tg}', f'h_{tg}', f'cost_k{k}']]
        gr = g[f'g_{tg}']; net = gr - g[f'cost_k{k}']
        n = len(g)
        se = net.std() / np.sqrt(n)
        ho = {}
        for col, val in [('T', 'T1'), ('T', 'T2'), ('C', 'C0'), ('C', 'C1')]:
            sub = g[g[col] == val]
            ho[val] = (sub[f'g_{tg}'] - sub[f'cost_k{k}']).mean()
        rows.append(dict(cell=cname, k=k, tgt=str(t), n=n,
                         hit=100 * g[f'h_{tg}'].mean(), gross=gr.mean(),
                         cost=g[f'cost_k{k}'].mean(), net=net.mean(),
                         lo=net.mean() - 1.96 * se, hi=net.mean() + 1.96 * se,
                         T1=ho['T1'], T2=ho['T2'], C0=ho['C0'], C1=ho['C1'],
                         pos4=all(v > 0 for v in ho.values()),
                         neg4=all(v < 0 for v in ho.values())))
res = pd.DataFrame(rows)
res.to_csv(f'{SCR}/geo_cells.csv', index=False)

fmt = dict(hit='{:.1f}'.format, gross='{:+.3f}'.format, cost='{:.3f}'.format,
           net='{:+.3f}'.format, lo='{:+.3f}'.format, hi='{:+.3f}'.format,
           T1='{:+.3f}'.format, T2='{:+.3f}'.format, C0='{:+.3f}'.format, C1='{:+.3f}'.format)
for cname in CELLS:
    print('=' * 30, cname)
    print(res[res.cell == cname].drop(columns='cell').to_string(index=False, formatters=fmt))

# hit-lift vs base at each k (1R target) — is +6.1pp stop-scale dependent?
print('\n--- LADDER hit-lift vs base, per geometry ---')
b = res[res.cell == 'base (all zones)'].set_index(['k', 'tgt'])
L = res[res.cell == 'LADDER (nd+ & swp & h1n)'].set_index(['k', 'tgt'])
for k, t in GEOS:
    print(f"k={k:<4} tgt={t}: base hit {b.loc[(k,str(t)),'hit']:.1f}  ladder hit {L.loc[(k,str(t)),'hit']:.1f}  "
          f"lift {L.loc[(k,str(t)),'hit']-b.loc[(k,str(t)),'hit']:+.1f}pp   "
          f"base gross {b.loc[(k,str(t)),'gross']:+.3f}  ladder gross {L.loc[(k,str(t)),'gross']:+.3f}  "
          f"gross-lift {L.loc[(k,str(t)),'gross']-b.loc[(k,str(t)),'gross']:+.3f}")

# arithmetic: cost vs gross per k, ladder cell
print('\n--- arithmetic (LADDER): mean cost_R per k vs best gross ---')
for k in KS:
    sub = L.loc[k]
    print(f"k={k}: cost {sub.cost.iloc[0]:.3f}R | gross by tgt: " +
          ' '.join(f"{t}={sub.loc[str(t),'gross']:+.3f}" for t in [1.0, 1.5, 2.0, 'trail']))

# bootstrap CI on net for ladder, all geometries
print('\n--- LADDER bootstrap 95% CI (10k) on netR ---')
rng = np.random.default_rng(0)
cm = CELLS['LADDER (nd+ & swp & h1n)']
for k, t in GEOS:
    tg = tag(k, t)
    v = (df.loc[cm, f'g_{tg}'] - df.loc[cm, f'cost_k{k}']).dropna().values
    bs = rng.choice(v, (10000, len(v))).mean(1)
    print(f"k={k:<4} tgt={t:<5}: net {v.mean():+.4f}  CI [{np.percentile(bs,2.5):+.4f}, {np.percentile(bs,97.5):+.4f}]")
