"""grade_sep.py — DOES OUR GRADE SEPARATE ANYTHING UNDER HONEST FILLS?

The grade ladder looked monotone (g1 negative .. g7 +9.5R) in the phantom-fill era.
Everything from that era is void, so the question is open again and it is the one
that decides whether we are bad at FINDING trades or bad at REJECTING them:

  if honest R is flat across grades, the ranking is worthless and every claim of
  "we select good setups" dies with it;
  if it climbs, we have a real selector that is simply not tight enough.

Also reports emission rate against the user's own ~2 setups/month, since a selector
that fires 100x more often than the trader it copies is not selecting.

Usage: python3 tools/grade_sep.py <tradebook.csv> <data_dir> <sl_h> <tgtR> [hold_days]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import target_opt as T  # noqa: E402

TB, DATA = sys.argv[1], sys.argv[2]
SL_H, TGT = float(sys.argv[3]), float(sys.argv[4])
HOLD = int(sys.argv[5]) if len(sys.argv) > 5 else 5

n = T.load(TB, DATA, SL_H, min_grade=1)
res = T.race(TGT, None, 0, HOLD)
g = np.array(T.GRADE)
r = np.array([np.nan if x is None else x for x in res], dtype=float)
ok = ~np.isnan(r)
print(f"tradeable signals {n} | filled {ok.sum()} | sl_h={SL_H} tgt={TGT}R hold={HOLD}d\n")
print(f"{'grade':>5} {'n':>6} {'win%':>6} {'meanR':>8} {'medR':>7} {'totR':>9}  {'t':>6}")
for gr in sorted(set(g)):
    m = ok & (g == gr)
    if m.sum() < 5:
        continue
    f = r[m]
    t = f.mean() / (f.std(ddof=1) / np.sqrt(len(f))) if f.std(ddof=1) > 0 else 0
    print(f"{gr:>5} {len(f):>6} {100*(f>0.02).mean():>5.1f}% {f.mean():>+8.3f} "
          f"{np.median(f):>+7.2f} {f.sum():>+9.0f}  {t:>+6.2f}")

hi, lo = ok & (g >= 5), ok & (g <= 2)
if hi.sum() > 5 and lo.sum() > 5:
    a, b = r[hi], r[lo]
    d = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    print(f"\nHIGH(>=5) minus LOW(<=2): {d:+.3f}R  t={d/se:+.2f}  "
          f"=> ranking {'WORKS' if d / se > 2 else 'does NOT separate'}")

SESS = 137
print(f"\nEMISSION RATE (7 months, 40 stocks, {SESS} sessions):")
for cut in [1, 4, 5, 6, 7]:
    c = int((g >= cut).sum())
    if c:
        print(f"  grade>={cut}: {c:5} signals = {c/7:6.1f}/month  "
              f"({c/7/2:5.0f}x the user's ~2/month)")
