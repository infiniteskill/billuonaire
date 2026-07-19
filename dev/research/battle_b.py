"""BATTLE B: 12-1 monthly top-10 EW momentum rotation on dailymax, crash rules, same-window slice.
Formation start 2003-07 (universe jumps to ~85 names 2002-07; needs 12m lookback), min 50 ranked names.
Crash-rule index: NIFTY from 2007-09, EW universe index (scaled splice) before."""
import pandas as pd, numpy as np

CAP = 100_000.0
COST = 0.002  # round-trip per unit turnover
K = 10
START = pd.Timestamp('2003-06-30')

d = pd.read_parquet('/home/doom/Public/PROJECT/2026/trader/runs/artifacts-data/dailymax.parquet')
d['date'] = pd.to_datetime(d['date'])
px = d.pivot_table(index='date', columns='symbol', values='close')
nifty = px.pop('NIFTY')

me = px.resample('ME').last()
mom = me.shift(1) / me.shift(12) - 1
mom = mom.where(me.notna() & me.shift(1).notna() & me.shift(12).notna())
fwd = me.shift(-1) / me - 1

# spliced index for crash rules: EW universe index scaled onto NIFTY at 2007-09-17
ew_idx = (1 + px.pct_change().mean(axis=1, skipna=True)).cumprod()
n0 = nifty.first_valid_index()
splice = pd.concat([ew_idx.loc[:n0] * (nifty.loc[n0] / ew_idx.loc[n0]), nifty.loc[n0:].iloc[1:]])
splice = splice[~splice.index.duplicated()]

def run(regime=None):
    dates = me.index
    hold, rows = set(), []
    for i in range(len(dates) - 1):
        t = dates[i]
        if t < START:
            continue
        m = mom.loc[t].dropna()
        if len(m) < 50:
            continue
        top = set(m.nlargest(K).index)
        invested = True if regime is None else bool(regime.loc[t])
        if invested:
            turn = len(top - hold) / K if hold else 1.0
            ret = fwd.loc[t, list(top)].mean() - COST * turn
            hold = top
        else:
            ret = -COST * (len(hold) / K)
            hold = set()
        rows.append((dates[i + 1], ret, invested))
    r = pd.DataFrame(rows, columns=['month', 'ret', 'invested']).set_index('month')
    eq = (1 + r.ret).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    ann = r.ret.groupby(r.index.year).apply(lambda x: (1 + x).prod() - 1)
    return r, eq, cagr, dd, ann

r0, eq0, cagr0, dd0, ann0 = run()
print(f"== MOMENTUM 12-1 top-{K} EW, {r0.index[0].date()}..{r0.index[-1].date()} ({len(r0)} months) ==")
print(f"CAGR={cagr0*100:.2f}%  maxDD={dd0*100:.1f}%  final multiple = {eq0.iloc[-1]:.1f}x  (₹1L -> ₹{CAP*eq0.iloc[-1]:,.0f})")
print(f"worst year: {ann0.idxmin()} {ann0.min()*100:+.1f}%   best year: {ann0.idxmax()} {ann0.max()*100:+.1f}%")
print("annual:", "  ".join(f"{y}:{v*100:+.0f}%" for y, v in ann0.items()))
# EW buy-hold same window for the survivorship-neutral spread
ewm = ew_idx.resample('ME').last()
ew_slice = ewm.loc[r0.index[0]:r0.index[-1]]
yrs = (ew_slice.index[-1] - ew_slice.index[0]).days / 365.25
ew_cagr = (ew_slice.iloc[-1] / ew_slice.iloc[0]) ** (1 / yrs) - 1
print(f"EW buy-hold same universe/window: CAGR={ew_cagr*100:.2f}%  -> active spread {cagr0*100-ew_cagr*100:+.2f}pp/yr")

# ---- crash rules ----
me_ix = splice.resample('ME').last()
rules = {
    'none': None,
    'abs-mom idx 12m<0 (NIFTY, EW pre-08)': (me_ix / me_ix.shift(12) - 1) >= 0,
    'abs-mom EW-idx 12m<0': (ewm / ewm.shift(12) - 1) >= 0,
    'drawdown idx >15% off 52w-hi': (splice / splice.rolling(252, min_periods=60).max()).resample('ME').last() >= 0.85,
    '200DMA idx<200dma': (splice >= splice.rolling(200, min_periods=100).mean()).resample('ME').last(),
}
print(f"\n== CRASH-RULE TABLE ==")
print(f"{'rule':40s} {'CAGR':>8s} {'maxDD':>8s} {'mo-cash':>8s} {'worst-yr':>12s}")
for name, reg in rules.items():
    if reg is not None:
        reg = reg.reindex(me.index).astype('object').fillna(True).astype(bool)
    r, eq, cagr, dd, ann = run(regime=reg)
    ncash = int((~r.invested).sum())
    print(f"{name:40s} {cagr*100:7.2f}% {dd*100:7.1f}% {ncash:8d} {ann.idxmin()} {ann.min()*100:+.1f}%")

# ---- same-window slice 2026-04-27..2026-07-17 ----
W0, W1 = pd.Timestamp('2026-04-27'), pd.Timestamp('2026-07-17')
days = px.loc[W0:W1].index
eq, hold, prev = CAP, None, None
curve = []
for day in days:
    form = me.index[me.index < day][-1]
    top = list(mom.loc[form].dropna().nlargest(K).index)
    if hold is None:
        hold = top
        eq *= (1 - COST / 2)          # initial buy, half round-trip
        prev = px.loc[day, hold]
        curve.append((day, eq)); continue
    if set(top) != set(hold):
        turn = len(set(top) - set(hold)) / K
        eq *= (1 - COST * turn)
        hold = top
        prev = px.loc[:day].iloc[-2][hold]
    eq *= (1 + (px.loc[day, hold] / prev - 1).mean())
    prev = px.loc[day, hold]
    curve.append((day, eq))
c = pd.Series(dict(curve))
dd_w = (c / c.cummax() - 1).min()
print(f"\n== SAME-WINDOW SLICE {W0.date()}..{W1.date()} ==")
print(f"final=₹{c.iloc[-1]:,.0f}  total={(c.iloc[-1]/CAP-1)*100:+.2f}%  maxDD={dd_w*100:.2f}%  days={len(c)}")
print(f"daily min ₹{c.min():,.0f} on {c.idxmin().date()}, max ₹{c.max():,.0f} on {c.idxmax().date()}")
for w, v in c.groupby(c.index.strftime('%G-W%V')).last().items():
    print(f"  {w}  ₹{v:,.0f}")
nf = nifty.loc[W0:W1]; ew_w = ew_idx.loc[W0:W1]
print(f"NIFTY same window: {(nf.iloc[-1]/nf.iloc[0]-1)*100:+.2f}%   EW universe: {(ew_w.iloc[-1]/ew_w.iloc[0]-1)*100:+.2f}%")
