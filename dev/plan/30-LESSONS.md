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

## Lesson 6 — CHoCH / BOS (structure grammar)
- BOS = break WITH the prevailing trend (continuation: new HH in uptrend, new LL in downtrend).
- **CHoCH = the FIRST break AGAINST structure**: uptrend breaks its last Higher Low → bearish
  CHoCH; downtrend breaks its last Lower High → bullish CHoCH. Character changes there.
- MINOR vs MAJOR CH: minor = internal/LTF counter-swing breaks (early whisper);
  major = the dominant swing level breaks (confirmed flip). Sequence: minor CH → major CH.
- Zigzag relation: CHoCH is the STRUCTURAL confirm trigger — often earlier than the 4.7%
  leg-distance confirm; both should coexist (distance confirm OR structure confirm, whichever
  first — measure which).
- Code: structure detector (CHoCH/BOS) + inducement (CHoCH+grab FSM) already exist; re-anchor
  their swing inputs to zigzag extremes.

## Lesson 7 — THE PERFECT ENTRY (the full composite, user's textbook img 57)
Numbered exactly as the setup unfolds:
1. Price taps an **HTF demand** zone (top-down context first).
2. **Sweep of the liquidity pool** under the lows there (the stop-hunt fishhook).
3. (Possibly a second sweep/low.) **Minor CH** breaks.
4. **Major CH breaks** — displacement leg (structure flipped with force).
5. The displacement leaves an **inefficiency (FVG) to fill** — price retraces into it.
6. Entry at the **LTF demand** born inside/at that fill (HTF zone → LTF zone refinement).
→ Ride to the **UNMITIGATED SUPPLY** (the far untouched zone / opposite pool) = target.
SL beyond the swept low. This is the complete tree: context → sweep → CHoCH → FVG → nested
LTF zone → far-liquidity target. Every prior lesson is one organ of this animal.

## Lesson 8 — PREMIUM / DISCOUNT (the dealing range)
- Range = between the current dealing-range HIGH and LOW (the last opposing pair of valid
  zigzag extremes). Equilibrium = 50% (fib). Above = PREMIUM (expensive), below = DISCOUNT (cheap).
- **Rules: buy only in discount, sell only in premium. MID = NEUTRAL — no trade.**
- At the range extremes price "likely goes opposite — premium and discount travel toward each
  other", manufacturing the features (swings, FVG, OB, iFVG) on the way.
- **CHoCH validity is GATED by location**: bullish CHoCH in PREMIUM = false signal; bullish
  CHoCH in DISCOUNT = high-probability HL. (Photon rule — structure signal only counts in the
  right half of the range.)
- The range cycles over TIME: BSL grab in premium → travel → sell-side liquidity in discount.
- Code: pd_pos/pd_cls context exists in engine; re-anchor the range to zigzag extremes
  (currently session/window-based). Gate CHoCH-family evidence by half.

## Lesson 9 — ZONE SELECTION + ENTRY CONSTRUCTION
- Zones COINCIDE/cross/sit very near — OB, FVG, breaker stack into one cluster; "which zone"
  is moot. The stacked cluster's MIDPOINT = safest entry level at HTF.
- The REAL entry is built on a SMALLER TF inside the HTF cluster: find the LTF FVG/OB that
  price tests but does NOT violate. LONG: entry = LTF zone top, SL = below LTF zone bottom.
  SHORT: entry = LTF zone bottom, SL = above LTF zone top.
- The LTF zone's height IS the stop distance: tiny structural risk nested inside the HTF area
  (the 1:9 anatomy). HTF cluster = WHERE; LTF zone = the exact entry+SL pair.

## Lesson 10 — TF LADDER (adaptive) + HOLD HORIZON
- POSITIONAL: holds 2–3 weeks to 2–3 months. Weekly and monthly trade scales scanned in parallel.
- Structure TF = whichever of 1D / 1H / 30m gives the CLEANEST swings + features for that stock
  now (structure-clarity selection, not fixed pairs). Entry = smaller-TF OB/swings that respect /
  sit under the big-TF zone (lesson 9 nesting).
- MEASURED NOTE: this exact shape (D1 zones + ladder flags + weeks holds) = the one net-positive
  Bonferroni survivor in DGRID (+0.09R net, 2.3 tr/qtr; cost 0.06R < gross 0.13R at daily scale).
  Fragile/drift-flavored but the only cell where the taught grammar clears toll. Full assembled
  positional backtest pending once lessons complete.

## Lesson 11 — MANAGEMENT
- Trail SL SLOWLY (lag it, never choke). 1:3 is good; KEEP TRAILING toward 1:5+ when it runs.
  The trail does the exiting, not a greedy fixed target.

## Lesson 12 — MITIGATION vs BREAKER (the one-question test)
- Did the failing swing TAKE the old extreme first?
  YES (grab then structure break) → BREAKER. NO ("failure to swing", no-break lower high /
  higher low) → MITIGATION block. Same flip mechanics on retest; breaker ranks above mitigation
  (liquidity taken = more fuel). M/W neckline law usually births breakers (second peak sweeps
  the first). Flip family complete: OB (never violated) / breaker (violated, swept) /
  mitigation (violated, unswept) / iFVG (violated gap) / overlap (intersection outranks).

## Lesson 13 — REJECTION BLOCK (wick zone at extremes)
- Top: zone = highest OPEN/CLOSE (body top) → wick HIGH. Bottom: lowest body edge → wick LOW.
  The pure-wick territory where the push was rejected. Lives at SWEPT extremes; retest = entry.
- UPGRADES lesson 1: the extreme's cluster band should be its wick-beyond-bodies range
  (principled), replacing the 0.5×ATR guess in ext_zigzag.

## Lesson 14 — PROPULSION BLOCK
- The candle that TRADES INTO a parent OB and propels away = its range is the propulsion block,
  sitting in front of the parent. Entry-grade: first defense, closer to price, inherits the
  parent's authority (the tap PROVED the parent). Child dies with the parent (parent linkage
  mandatory — old detector lost this; fix required).

## Lesson 15 — POWER OF 3 / AMD (the Rosetta stone)
- PO3 = the anatomy of ONE higher-TF candle opened at LTF: Open = accumulation (coil around
  open, pools build), WICK = manipulation ("wicks are big" — the sweep/Judas beyond the range),
  BODY = distribution (the real move, opposite the manipulation, leaves FVGs).
- Phase→organ map: accumulation births ranges/EQ pools/compression; manipulation births
  rejection blocks/OBs/breaker fuel at the swept extreme; distribution births FVG/propulsion/
  BOS/CHoCH.
- THE LADDER ALREADY ENCODES IT: rung 3 (sweep-aligned birth) = the manipulation→distribution
  turn = the PO3 entry. compression_fade = accumulation detector.
- Signatures: small-body/big-wick HTF candle = completed PO3, wick side reveals true direction;
  live entry = manipulation ending (break beyond range edge + reversal back inside), never
  mid-accumulation, never chasing distribution.

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
