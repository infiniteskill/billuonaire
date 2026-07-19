# 30 — THE TAUGHT STRATEGY (user's lessons, 2026-07-19, session "teach me one by one")

Ground rules the user set before lesson 1:
- **CONTINUOUS TAPE. No day/session logic anywhere.** Zones/structure live until resolved; "later"
  is measured in bars/time/distance, not calendar sessions.
- Nothing counts until verified against the user's own hand-marked charts (parity with the eye).

## Lesson 1 — EXTREME SWINGS (the skeleton)
- A swing is VALID only if it ENDS a big leg AND STARTS a big opposite leg (two-sided excursion).
- Alternation enforced: H-L-H-L; a higher high before a valid reversal REPLACES the pending pivot.
- Extreme = CLUSTER BAND (bars near the extreme), not a tick.
- Rank: master (window max/min) > major; rank metric = min(leg_in, leg_out).
- **MEASURED DISCOVERY: the user's eye applies a TF-invariant ~4.7% minimum leg**
  (8×ATR on 30m = 4.64%, 6×ATR on H1 = 4.72%). Implement as percent-leg floor.
- Parity: 16/16 hand circles reproduced (runs/long60/EXTREMES.md); fractal 3/3 emitted 135 swings
  on the same window → zigzag emits 8. Confirmation lag median 2–6 days → pivots are ANCHORS,
  never entry signals.
- Code: dev/research/ext_zigzag.py (prototype, validated). Engine swings.py (3/3 fractal) is
  furniture-grade — to be replaced/supplemented.

## Lesson 2 — FVG (fair value gap)
- Definition: flanking WICKS don't overlap across a displacement burst of **1..N candles**
  (not just strict 3): gap = [wick of candle before burst, wick of candle after burst].
  Strict 3-candle (current fvg_cb, parity-locked) is the special case; generalize to N.
- WHY: SPEED — price moved too fast, orders unfilled → gap is "owed", price returns.
- Grade A qualifier (PFG): the gap forms just after TAPPING S/R / an extreme (structure-anchored
  birth). Mid-air gaps = furniture.
- MIDPOINT (CE) is the gap's working internal level: retraces often terminate exactly there.
  Edge = first contact; fill past midpoint = zone weakening.
- Trade = CONTINUATION of the impulse that made the gap (bull gap → long on refill).
  SL below the pattern (zone/launch low). TP at the prior pivot/SR (the liquidity destination).
- Lives until visited (visits typically days–weeks later); close through far edge → iFVG.

## Lesson 3 — ORDER BLOCK
- "A downward-move candle in an uptrend continuation is the order block" (and mirror):
  the OPPOSITE-direction candle OR consolidation cluster (overlapping ranges) pausing a leg.
- Box = FULL high–low of the cluster (the whole shelf, wide), single candle at high TF =
  cluster at low TF (fractal, TF-invariant).
- **POWER = NEARNESS TO SWING**: OB born at/adjacent to a zigzag extreme = strongest;
  mid-leg = weaker. Gradient, not binary.
- Context: liquidity pools above/below are the destination; OBs ladder pool-to-pool.
- Trade: price returns (often weeks; "visit after month"), TOUCHES, goes — continuation.
- Entry: box edge, or slightly inside — OTE 0.705 fib pocket. CE/midline drawn on the boxes.
- Code: ob_lux has the opposite-candle core; missing = wide cluster box, swing-nearness rank,
  N-candle cluster generalization.

## Lesson 4 — iFVG / BREAKER / OVERLAP (the flip family)
- iFVG: FVG closed through its far edge → SAME gap now works from the OPPOSITE side on retest.
- BREAKER = a FAILED OB: price closes through an OB → the zone flips direction; retest from the
  other side = entry, SL just beyond the breaker, continue in the break direction ("OB Failed" →
  breaker support/resistance).
- **USER'S STRUCTURAL LAW: the middle of an M or W — where the two V's join (the neckline
  pivot) — is usually the breaker.** In zigzag terms: the internal pivot between two adjacent
  same-side extremes of a double top/bottom.
- OB vs Breaker: OB = pause in a continuation (never violated). Breaker = violated structure
  zone (proven-wrong side, now works the other way).
- OVERLAPPING BLOCK: intersection band of any two zones (OB∩OB, OB∩BB, FVG∩FVG = BPR) =
  highest grade. Trade the intersection.
- Code: breaker_msb (EmreKb port, +19.6pp hit-edge — strongest measured ingredient) is this
  family; bpr = the FVG∩FVG case.

## Lesson 5 — LIQUIDITY POOLS
- A pool is the band **just BEYOND an old extreme** — above Old Highs, below Old Lows:
  "liquidity at extremes/breakouts, where the SLs mostly lie."
  Above old high = shorts' stops + breakout buy orders; below old low = longs' stops +
  breakout sells. Both are resting order clusters = fuel.
- Pools anchor at Lesson-1 extremes (and equal-high/low clusters): the more times a level held,
  the fatter the pool behind it.
- Dual role: (a) TARGET — "price goes" to the pool after a zone touch (TP at pivot SR);
  (b) SWEEP SITE — the wick-through-and-close-back that births grade-A zones (the stop-hunt
  that starts the whole setup tree).
- Code: liquidity.py EQH/EQL pools + ladder.py sweep events exist; re-anchor to zigzag extremes
  (percent-leg floor) instead of fractal furniture.

## The unified law (user's grammar, one sentence)
**Impulse off structure → zone left behind (OB = pause cluster, FVG = speed gap) → price leaves →
returns LATER on continuous tape → touch → continues the impulse direction → target = the next
liquidity pool / prior pivot; SL beyond the zone; broken zones flip (iFVG/breaker); overlapping
zones outrank; everything is graded by nearness to a valid (~4.7% two-sided) extreme.**

## Verification status
- Extremes: DONE, 16/16 parity (EXTREMES.md).
- Taught-OB + FVG on user's Jan–Apr 2026 HEROMOTOCO zones + entry-depth (edge vs CE vs OTE 0.705)
  + swing-nearness-vs-outcome: agent running, report → runs/long60/TAUGHT_OB.md.
- Next to teach/verify: liquidity pools & sweeps grammar, CHoCH, zone selection when several
  coexist, position management.

## Standing honesty note
Detection parity is the goal of this phase. Economics stay governed by the measured record
(FACTS/GEO/NATIVE30/H1GRID/DGRID): recognition real (t to 21.7), net after toll ≈ 0 on free
OHLCV. Every taught refinement gets measured before any profit language.
