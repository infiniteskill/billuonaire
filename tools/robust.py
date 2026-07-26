"""robust.py — IS A POSITIVE CONFIG REAL EDGE, OR NOISE?

Every positive number found after the honest reset is thin (mean +0.05..+0.15R on
a few hundred trades with a -1.1R median), so it can be produced by luck, by two
lucky trades, or by payoff geometry alone. This runs the four checks that separate
those cases, on the shared honest race in target_opt:

  1. t-stat + bootstrap CI  -- is the mean distinguishable from zero at all?
  2. drop top-k winners     -- does it survive losing its best trades?
  3. time split             -- first half vs second half of the tape
  4. direction flip (NULL)  -- take every signal the WRONG way. A big-target /
     small-stop payoff on fat-tailed intraday data can be positive in BOTH
     directions; if the flip is positive too, the zone direction is adding nothing.

Usage: python3 tools/robust.py <tradebook.csv> <data_dir> <sl_h> <tgtR> [beR|none] [trail]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import target_opt as T  # noqa: E402

TB, DATA = sys.argv[1], sys.argv[2]
SL_H, TGT = float(sys.argv[3]), float(sys.argv[4])
BE = None if len(sys.argv) < 6 or sys.argv[5] == "none" else float(sys.argv[5])
TRAIL = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
HOLD = 5
RNG = np.random.default_rng(20260726)


def stats(r, label):
    f = np.array([x for x in r if x is not None])
    if len(f) < 2:
        print(f"{label:32} n<2"); return
    m, sd = f.mean(), f.std(ddof=1)
    t = m / (sd / np.sqrt(len(f)))
    bs = RNG.choice(f, (10000, len(f))).mean(1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"{label:32} n={len(f):4d} meanR={m:+.3f} sd={sd:4.2f} t={t:+5.2f} "
          f"95%CI[{lo:+.3f},{hi:+.3f}] {'SIG' if lo > 0 else 'not sig'}")


n = T.load(TB, DATA, SL_H)
res = T.race(TGT, BE, TRAIL, HOLD)
f = np.array([x for x in res if x is not None])
idx = [i for i, x in enumerate(res) if x is not None]
print(f"CONFIG sl_h={SL_H} target={TGT}R BE={BE} trail={TRAIL} hold={HOLD}d "
      f"| signals {n} | fills {len(f)}")

print("\n=== 1. SIGNIFICANCE ===")
stats(res, "as-is")

print("\n=== 2. DROP TOP-K WINNERS ===")
order = np.argsort(-f)
for k in [1, 2, 5, 10, 20]:
    keep = np.setdiff1d(np.arange(len(f)), order[:k])
    print(f"  drop top {k:2d}: meanR={f[keep].mean():+.3f}  "
          f"(top {k} contribute {f[order[:k]].sum():+6.1f}R of {f.sum():+6.1f}R)")

print("\n=== 3. TIME SPLIT ===")
ts = np.array([T.SIG[i][7] for i in idx])
cut = np.sort(ts)[len(ts) // 2]  # median by order: datetime64 has no mean
stats([x for x, t in zip(f, ts) if t <= cut], f"first half (<= {str(cut)[:10]})")
stats([x for x, t in zip(f, ts) if t > cut], "second half")

print("\n=== 4. PER-SYMBOL ===")
sym = np.array([T.SIG[i][0] for i in idx])
tot = {s: f[sym == s].sum() for s in set(sym)}
pos = sum(1 for v in tot.values() if v > 0)
top = sorted(tot.items(), key=lambda kv: -kv[1])
print(f"  symbols {len(tot)} | net positive {pos} ({100*pos/len(tot):.0f}%) | "
      f"top symbol {top[0][0]} {top[0][1]:+.1f}R of total {f.sum():+.1f}R")
print("  best :", ", ".join(f"{s} {v:+.0f}" for s, v in top[:5]))
print("  worst:", ", ".join(f"{s} {v:+.0f}" for s, v in top[-5:]))

print("\n=== 5. DIRECTION-FLIP NULL ===")
T.SIG = [(s, not lg, e, r, c, i, se, t) for s, lg, e, r, c, i, se, t in T.SIG]
flip = T.race(TGT, BE, TRAIL, HOLD)
stats(flip, "same entries, wrong way")
# Paired: same signal both ways. Removes the payoff-geometry and market-drift
# components that both directions share, so this isolates what the zone's
# direction call is worth -- and pairing cuts the variance enough to be testable.
d = np.array([a - b for a, b in zip(res, flip) if a is not None and b is not None])
m, sd = d.mean(), d.std(ddof=1)
bs = RNG.choice(d, (10000, len(d))).mean(1)
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"\n  PAIRED as-is minus flip: n={len(d)} mean={m:+.3f}R "
      f"t={m/(sd/np.sqrt(len(d))):+.2f} 95%CI[{lo:+.3f},{hi:+.3f}]  "
      f"=> direction worth {'SOMETHING' if lo > 0 else 'nothing provable'}")
