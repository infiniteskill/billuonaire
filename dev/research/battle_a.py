"""BATTLE A: ladder account sim, 0.5% risk of current equity per trade, compounding."""
import pandas as pd, numpy as np

CAP = 100_000.0
RISK = 0.005

df = pd.read_parquet('/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad/facts_first.parquet')
nd = df.session > df.born_date
lad = df[nd & df.h1_nested & df.sweep_aligned].copy()
print(f"LADDER cell: n={len(lad)} hit={lad.hit.mean():.4f} netR={lad.net_r.mean():.4f}")

def sim(t, name):
    n0 = len(t)
    t = t.dropna(subset=['net_r'])
    if len(t) < n0:
        print(f"[{name}] dropped {n0-len(t)} unresolved trades (NaN net_r)")
    t = t.sort_values(['session', 'ri']).reset_index(drop=True)  # ri = per-symbol bar idx, intra-session proxy
    eq = CAP
    curve = []
    for _, r in t.iterrows():
        eq *= (1 + RISK * r.net_r)
        curve.append((r.session, eq))
    c = pd.DataFrame(curve, columns=['session', 'equity'])
    peak = c['equity'].cummax()
    dd = ((c['equity'] - peak) / peak).min() * 100
    tot = (eq / CAP - 1) * 100
    sumR = t.net_r.sum()
    simple_pnl = CAP * RISK * sumR  # non-compounded, fixed 0.5% of 1L per trade
    print(f"\n== {name} ==")
    print(f"n={len(t)}  win%={t.hit.mean()*100:.1f}  sumR={sumR:+.2f}")
    print(f"final=₹{eq:,.0f}  total={tot:+.3f}%  maxDD={dd:.3f}%")
    print(f"best trade R={t.net_r.max():+.2f} (₹~{CAP*RISK*t.net_r.max():+,.0f} at 1L base)  "
          f"worst R={t.net_r.min():+.2f} (₹~{CAP*RISK*t.net_r.min():+,.0f})")
    print(f"simple sum-of-R P&L on fixed ₹1L: ₹{simple_pnl:+,.0f} ({simple_pnl/CAP*100:+.3f}%)")
    # weekly curve (end of ISO week)
    c['wk'] = pd.to_datetime(c.session).dt.strftime('%G-W%V')
    wk = c.groupby('wk').agg(last_session=('session', 'last'), equity=('equity','last'), n=('equity','size'))
    print("weekly equity (end of week):")
    for w, r in wk.iterrows():
        print(f"  {w}  {r.last_session}  ₹{r.equity:,.0f}  ({r.n} trades)")
    return eq, tot, dd

sim(lad, "FULL LADDER 557 (all trades, 0.5% compounding)")

# 50-stock top-4 variant: top-50 symbols by ladder row count, top-4 per symbol by gap_atr desc, impulse desc
top50 = lad.symbol.value_counts().head(50).index
sub = lad[lad.symbol.isin(top50)].copy()
sub = (sub.sort_values(['gap_atr', 'impulse'], ascending=False)
          .groupby('symbol', sort=False).head(4))
sim(sub, "50-STOCK TOP-4 (rank gap_atr desc, impulse tiebreak; in-sample selection)")
