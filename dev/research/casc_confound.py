import numpy as np, pandas as pd
SCR='/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad'
r=pd.read_parquet(f'{SCR}/casc_signals.parquet'); r=r[r.born_i>=0].copy()
sig=pd.read_parquet('runs/artifacts-data/signals60.parquet',columns=['ts']).loc[r.ri]
r['hour']=pd.to_datetime(sig.ts.values).hour
r['delay_min']=(r.sig_i-r.born_i)*5; r['same_day']=r.born_date==r.session
r=r.sort_values('sig_i')
first=r.groupby(['symbol','detector','direction','born_ts'],as_index=False).first()
first['nd']=~first.same_day
print('signal hour distribution: next-day+ vs same-day first-retests')
print(pd.crosstab(first.hour, first.nd, normalize='columns').round(3))
print()
print('hit%% / netR by hour x nextday (pooled, n>=300 cells):')
g=first.dropna(subset=['net_r']).groupby(['hour','nd']).agg(n=('hit','size'),hit=('hit','mean'),netR=('net_r','mean'))
g=g[g.n>=300]; print((g.assign(hit=100*g.hit)).round(3).to_string())
print()
# within-hour lift, weighted
piv=g.reset_index().pivot(index='hour',columns='nd',values=['hit','netR','n'])
piv=piv.dropna()
w=piv[('n',True)]
print('mean within-hour lift (weighted by nextday n): hit %+.2fpp netR %+.4fR'%(
 np.average(100*(piv[('hit',True)]-piv[('hit',False)]),weights=w)/100*100 if False else np.average(piv[('hit',True)]-piv[('hit',False)],weights=w),
 np.average(piv[('netR',True)]-piv[('netR',False)],weights=w)))
