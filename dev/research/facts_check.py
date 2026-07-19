"""facts_check.py — robustness follow-ups: gap x fast-retest cell, stack ladder
netR-signs, concentration, binomial significance, cost-in-R breakeven."""
import numpy as np, pandas as pd, zlib
from scipy import stats as st

SCR = '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
first = pd.read_parquet(f'{SCR}/facts_first.parquet')
first['T'] = np.where(first.session < '2026-06-08', 'T1', 'T2')
first['C'] = ['C'+str(zlib.crc32(s.encode()) % 2) for s in first.symbol]
first['delay_min'] = (first.sig_i - first.born_i)*5
first['same_day'] = first.born_date == first.session
def bucket(d, s):
    if not s: return 'nextday+'
    return '<30m' if d < 30 else '30-60m' if d < 60 else '1-4h' if d < 240 else '>4h'
first['bucket'] = [bucket(d, s) for d, s in zip(first.delay_min, first.same_day)]
go = first.gap_open | first.gap_overlap

def stats_(g):
    v = g.dropna(subset=['net_r'])
    return dict(n=len(g), hit=100*v.hit.mean(), netR=v.net_r.mean())
BASE = stats_(first)
def holdout(cond, label):
    rows = []
    for col, val in [('T','T1'),('T','T2'),('C','C0'),('C','C1')]:
        g = first[first[col] == val]
        b, cm = stats_(g), stats_(g[cond[g.index]])
        rows.append(f"{val}: hit{cm['hit']-b['hit']:+.1f}pp netR{cm['netR']-b['netR']:+.3f} (n={cm['n']})")
    print(f"{label}: pooled n={cond.sum()}, hit {stats_(first[cond])['hit']:.1f} "
          f"({stats_(first[cond])['hit']-BASE['hit']:+.1f}pp), netR {stats_(first[cond])['netR']:.3f}")
    print('   ' + ' | '.join(rows))

print('--- A. gap-origin x <30m fast retest ---')
holdout(go & (first.bucket == '<30m'), 'gap-origin & <30m')
holdout(~go & (first.bucket == '<30m'), 'intraday & <30m')
holdout(go & first.bucket.isin(['<30m','30-60m']), 'gap-origin & <60m')

print('\n--- B. stack ladder with netR signs ---')
sw = first.sweep_aligned.astype(bool); hn = first.h1_nested.astype(bool)
nd = first.bucket == 'nextday+'
for label, cond in [('nextday+', nd), ('nextday+ & h1_nested', nd & hn),
                    ('nextday+ & sweep_aligned', nd & sw),
                    ('nextday+ & sweep_aligned & h1_nested', nd & sw & hn)]:
    holdout(cond, label)

print('\n--- C. concentration of the 557-cell ---')
cell = nd & sw & hn
g = first[cell]
print('per detector:', g.detector.value_counts().to_dict())
print('top symbols:', g.symbol.value_counts().head(8).to_dict())
print('sessions covered:', g.session.nunique(), 'max in one session:', g.session.value_counts().max())
print('direction:', g.direction.value_counts().to_dict())
v = g.dropna(subset=['net_r'])
z = (v.hit.mean() - BASE['hit']/100) / np.sqrt(0.25/len(v))
print(f"binomial z vs base = {z:.2f}, p(two-sided) = {2*(1-st.norm.cdf(abs(z))):.4f} "
      f"(pre-selection; ~19 stack combos were examined)")

print('\n--- D. cost in R and implied breakeven ---')
sig = pd.read_parquet('runs/artifacts-data/signals60.parquet', columns=['detector','entry','atr'])
sig = sig[sig.detector.isin(['fvg_cb','ob_lux','mitigation'])]
cost_r = 0.0006*sig.entry/(1.5*sig.atr)
print(f"mean cost = {cost_r.mean():.3f}R (median {cost_r.median():.3f}R)")
# empirical slope: netR per hit pp across delay buckets
print(f"observed slope ~ (netR_stack - netR_base)/(hit_stack - hit_base) = "
      f"{(stats_(first[cell])['netR']-BASE['netR'])/(stats_(first[cell])['hit']-BASE['hit']):.4f} R/pp")
be = BASE['hit'] - BASE['netR']/((stats_(first[cell])['netR']-BASE['netR'])/(stats_(first[cell])['hit']-BASE['hit']))
print(f"implied breakeven hit ~ {be:.1f}%")

print('\n--- E. alternative simple stacks (larger n) ---')
for label, cond in [('nextday+ & h1_nested & impulse>=1', nd & hn & (first.impulse >= 1)),
                    ('nextday+ & gap-origin & h1_nested', nd & go & hn),
                    ('nextday+ & sweep_born(any)', nd & first.sweep_born.astype(bool))]:
    holdout(cond, label)
