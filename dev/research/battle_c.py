"""BATTLE C: ladder trades filtered to momentum top-half (12-1 rank at prior month-end)."""
import pandas as pd, numpy as np, zlib

df = pd.read_parquet('/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/facts_first.parquet')
nd = df.session > df.born_date
lad = df[nd & df.h1_nested & df.sweep_aligned].copy()

d = pd.read_parquet('/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/dailymax.parquet')
d['date'] = pd.to_datetime(d['date'])
px = d[d.symbol != 'NIFTY'].pivot_table(index='date', columns='symbol', values='close')
me = px.resample('ME').last()
mom = (me.shift(1) / me.shift(12) - 1).where(me.notna() & me.shift(1).notna() & me.shift(12).notna())

print("ladder symbols not in dailymax universe:", sorted(set(lad.symbol) - set(px.columns)) or "none")

# momentum percentile rank at prior month-end for each trade session
sess = pd.to_datetime(lad.session)
form = pd.Series(me.index[np.searchsorted(me.index, sess) - 1], index=lad.index)
pct = mom.rank(axis=1, pct=True)  # 1 = strongest
lad['mom_pct'] = [pct.at[f, s] if s in pct.columns else np.nan for f, s in zip(form, lad.symbol)]
lad['tophalf'] = lad.mom_pct >= 0.5
print(f"trades with momentum rank: {lad.mom_pct.notna().sum()}/{len(lad)}")

def cell(t, name):
    r = t.net_r
    print(f"{name:34s} n={len(t):4d}  resolved={r.notna().sum():4d}  hit={t.hit.mean()*100:5.1f}%  "
          f"netR={r.mean():+.4f}  sumR={r.sum():+.1f}")

print("\n== MOMENTUM ALIGNMENT ==")
cell(lad, "FULL ladder cell")
cell(lad[lad.tophalf], "mom TOP-half")
cell(lad[~lad.tophalf & lad.mom_pct.notna()], "mom BOTTOM-half")

# 4-way holdout: temporal split at 2026-06-08 x crc32(symbol)%2
lad['late'] = lad.session >= '2026-06-08'
lad['sgrp'] = lad.symbol.map(lambda s: zlib.crc32(s.encode()) % 2)
print("\n== 4-WAY HOLDOUT (top-half combo vs full cell) ==")
for late in (False, True):
    for g in (0, 1):
        q = lad[(lad.late == late) & (lad.sgrp == g)]
        tag = f"{'late' if late else 'early'}/sym{g}"
        cell(q, f"  full  {tag}")
        cell(q[q.tophalf], f"  combo {tag}")
